"""Binary sensors for linkytic integration."""

from __future__ import annotations

import logging
from typing import Optional, cast

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
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

STATUS_REGISTER_SENSORS = (
    (
        StatusRegister.CONTACT_SEC,
        "Contact sec",
        BinarySensorDeviceClass.OPENING,
        "mdi:electric-switch-closed",
        "mdi:electric-switch",
        False,
    ),
    (
        StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR,
        "Cache-borne",
        BinarySensorDeviceClass.OPENING,
        "mdi:toy-brick",
        "mdi:toy-brick-outline",
        False,
    ),
    (
        StatusRegister.SURTENSION_SUR_UNE_DES_PHASES,
        "Surtension",
        BinarySensorDeviceClass.PRESENCE,
        "mdi:flash-triangle-outline",
        "mdi:flash-triangle",
        False,
    ),
    (
        StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE,
        "Dépassement puissance",
        BinarySensorDeviceClass.PRESENCE,
        "mdi:transmission-tower",
        "mdi:transmission-tower-off",
        False,
    ),
    (
        StatusRegister.PRODUCTEUR_CONSOMMATEUR,
        "Producteur",
        None,
        "mdi:transmission-tower-export",
        None,
        False,
    ),
    (
        StatusRegister.SENS_ENERGIE_ACTIVE,
        "Sens énergie active",
        None,
        "mdi:transmission-tower-export",
        None,
        False,
    ),
    (
        StatusRegister.MODE_DEGRADE_HORLOGE,
        "Synchronisation horloge",
        BinarySensorDeviceClass.LOCK,
        "mdi:sync",
        "mdi:sync-off",
        False,
    ),
    (StatusRegister.MODE_TIC, "Mode historique", None, "mdi:tag", None, False),
    (
        StatusRegister.SYNCHRO_CPL,
        "Synchronisation CPL",
        BinarySensorDeviceClass.LOCK,
        "mdi:sync",
        "mdi:sync-off",
        True,
    ),
)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up entry."""
    _LOGGER.debug("%s: setting up binary sensor plateform", config_entry.title)
    # Retrieve the serial reader object
    try:
        serial_reader = hass.data[DOMAIN][config_entry.entry_id]
    except KeyError:
        _LOGGER.error(
            "%s: can not init binaries sensors: failed to get the serial reader object",
            config_entry.title,
        )
        return
    # Init sensors
    sensors: list[BinarySensorEntity] = [
        SerialConnectivity(config_entry.title, config_entry.entry_id, serial_reader)
    ]

    if config_entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD:
        sensors.extend(
            StatusRegisterBinarySensor(
                name=name,
                config_title=config_entry.title,
                field=field,
                serial_reader=serial_reader,
                unique_id=config_entry.entry_id,
                device_class=devclass,
                icon_off=icon_off,
                icon_on=icon_on,
                inverted=inverted,
            )
            for field, name, devclass, icon_off, icon_on, inverted in STATUS_REGISTER_SENSORS
        )

    async_add_entities(sensors, True)


class SerialConnectivity(LinkyTICEntity, BinarySensorEntity):
    """Serial connectivity to the Linky TIC serial interface."""

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Connectivité du lien série"

    # Binary sensor properties
    #   https://developers.home-assistant.io/docs/core/entity/binary-sensor/#properties
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self, title: str, unique_id: str, serial_reader: LinkyTICReader
    ) -> None:
        """Initialize the SerialConnectivity binary sensor."""
        _LOGGER.debug("%s: initializing Serial Connectivity binary sensor", title)
        super().__init__(serial_reader)
        self._title = title
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_serial_connectivity"

    @property
    def is_on(self) -> bool:
        """Value of the sensor."""
        return self._serial_controller.is_connected


class StatusRegisterBinarySensor(LinkyTICEntity, BinarySensorEntity):
    """Binary sensor for binary status register fields."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _binary_state: bool
    _tag = "STGE"

    def __init__(
        self,
        name: str,
        config_title: str,
        unique_id: str,
        serial_reader: LinkyTICReader,
        field: StatusRegister,
        device_class: BinarySensorDeviceClass | None = None,
        icon_on: str | None = None,
        icon_off: str | None = None,
        inverted: bool = False,
    ) -> None:
        """Initialize the status register binary sensor."""
        _LOGGER.debug("%s: initializing %s binary sensor", config_title, field.name)
        super().__init__(serial_reader)

        self._config_title = config_title
        self._binary_state = False  # Default state.
        self._inverted = inverted
        self._field = field
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{unique_id}_{field.name.lower()}"
        if device_class:
            self._attr_device_class = device_class

        self._icon_on = icon_on
        self._icon_off = icon_off

    @property
    def is_on(self) -> bool:
        """Value of the sensor."""
        return self._binary_state ^ self._inverted

    @property
    def icon(self) -> str | None:
        """Return icon of the sensor."""
        if not self._icon_off or not self._icon_on:
            return self._icon_on or self._icon_off or super().icon

        if self.is_on:
            return self._icon_on
        else:
            return self._icon_off

    def update(self) -> None:
        """Update the state of the sensor."""
        value, _ = self._update()
        if not value:
            return
        self._binary_state = cast(bool, self._field.value.get_status(value))

    # TODO: factor _update function to remove copy from sensors entities
    def _update(self) -> tuple[Optional[str], Optional[str]]:
        """Get value and/or timestamp from cached data. Responsible for updating sensor availability."""
        value, timestamp = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: (%s, %s)",
            self._config_title,
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
                    self._config_title,
                    self._tag,
                )
                self._attr_available = False
            elif self._serial_controller.has_read_full_frame:
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._config_title,
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
                self._config_title,
                self._tag,
            )

        return value, timestamp
