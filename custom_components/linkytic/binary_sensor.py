"""Binary sensors for linkytic integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SETUP_TICMODE, TICMODE_STANDARD
from .entity import LinkyTICEntity
from .serial_reader import LinkyTICReader
from .status_register import StatusRegister

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class StatusRegisterBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor entity description for status register fields."""

    key: str = "STGE"
    entity_category: EntityCategory | None = EntityCategory.DIAGNOSTIC
    field: StatusRegister
    inverted: bool = False


STATUS_REGISTER_SENSORS: tuple[StatusRegisterBinarySensorDescription, ...] = (
    StatusRegisterBinarySensorDescription(
        translation_key="status_dry_contact",
        field=StatusRegister.DRY_CONTACT,
        device_class=BinarySensorDeviceClass.OPENING,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_terminal_cover",
        field=StatusRegister.TERMINAL_COVER,
        device_class=BinarySensorDeviceClass.OPENING,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_overvoltage",
        field=StatusRegister.OVERVOLTAGE,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_power_over_ref",
        field=StatusRegister.POWER_OVER_REF,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_producer",
        field=StatusRegister.PRODUCER,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_injection",
        field=StatusRegister.INJECTING,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_rtc_sync",
        field=StatusRegister.RTC_DEGRADED,
        device_class=BinarySensorDeviceClass.LOCK,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_mode_tic",
        field=StatusRegister.TIC_STD,
    ),
    StatusRegisterBinarySensorDescription(
        translation_key="status_cpl_sync",
        field=StatusRegister.CPL_SYNC,
        device_class=BinarySensorDeviceClass.LOCK,
        inverted=True,
    ),
)

SERIAL_LINK_BINARY_SENSOR = BinarySensorEntityDescription(
    key="serial_link",
    translation_key="serial_link",
    entity_category=EntityCategory.DIAGNOSTIC,
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry[LinkyTICReader],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    _LOGGER.debug("%s: setting up binary sensor plateform", config_entry.title)
    # Retrieve the serial reader object
    reader = config_entry.runtime_data

    # Init sensors
    sensors: list[BinarySensorEntity] = [
        SerialConnectivity(SERIAL_LINK_BINARY_SENSOR, config_entry, reader)
    ]

    if config_entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD:
        sensors.extend(
            StatusRegisterBinarySensor(
                description=description, config_entry=config_entry, reader=reader
            )
            for description in STATUS_REGISTER_SENSORS
        )

    async_add_entities(sensors, True)


class SerialConnectivity(LinkyTICEntity, BinarySensorEntity):
    """Serial connectivity to the Linky TIC serial interface."""

    def __init__(
        self,
        description: BinarySensorEntityDescription,
        config_entry: ConfigEntry,
        reader: LinkyTICReader,
    ) -> None:
        """Initialize the SerialConnectivity binary sensor."""
        super().__init__(reader)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{config_entry.entry_id}_serial_connectivity"

    @property
    def is_on(self) -> bool:
        """Value of the sensor."""
        return self._serial_controller.is_connected


class StatusRegisterBinarySensor(LinkyTICEntity, BinarySensorEntity):
    """Binary sensor for binary status register fields."""

    _binary_state: bool
    _tag = "STGE"

    def __init__(
        self,
        description: StatusRegisterBinarySensorDescription,
        config_entry: ConfigEntry,
        reader: LinkyTICReader,
    ) -> None:
        """Initialize the status register binary sensor."""
        _LOGGER.debug(
            "%s: initializing %s binary sensor",
            config_entry.title,
            description.field.name,
        )
        super().__init__(reader)

        self.entity_description = description
        self._binary_state = False  # Default state.
        self._inverted = description.inverted
        self._field = description.field
        self._attr_unique_id = (
            f"{DOMAIN}_{config_entry.entry_id}_{description.field.name.lower()}"
        )

    @property
    def is_on(self) -> bool:
        """Value of the sensor."""
        return self._binary_state ^ self._inverted

    def update(self) -> None:
        """Update the state of the sensor."""
        value, _ = self._update()
        if not value:
            return
        self._binary_state = cast(bool, self._field.value.get_status(value))

    # TODO: factor _update function to remove copy from sensors entities
    def _update(self) -> tuple[str | None, str | None]:
        """Get value and/or timestamp from cached data. Responsible for updating sensor availability."""
        value, timestamp = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: (%s, %s)",
            self._serial_controller.name,
            self._tag,
            value,
            timestamp,
        )

        if not value and not timestamp:  # No data returned.
            if not self.available:
                # Sensor is already unavailable, no need to check why.
                return None, None
            if not self._serial_controller.is_connected:
                _LOGGER.debug(
                    "%s: marking the %s sensor as unavailable: serial connection lost",
                    self._serial_controller.name,
                    self._tag,
                )
                self._attr_available = False
            elif self._serial_controller.has_read_full_frame:
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._serial_controller.name,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
            else:
                # A frame has not been read yet (it should!) or is already unavailable and no new data was fetched.
                # Let sensor in current availability state.
                pass
            return None, None

        if not self.available:
            # Data is available, so is sensor
            self._attr_available = True
            _LOGGER.info(
                "%s: marking the %s sensor as available now !",
                self._serial_controller.name,
                self._tag,
            )

        return value, timestamp
