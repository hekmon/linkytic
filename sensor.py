"""Sensors for Linky TIC integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ELECTRIC_CURRENT_AMPERE,
    ENERGY_WATT_HOUR,
    POWER_VOLT_AMPERE,
    POWER_WATT,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONSTRUCTORS_CODES,
    DEVICE_TYPES,
    DID_CONSTRUCTOR,
    DID_DEFAULT_MANUFACTURER,
    DID_DEFAULT_MODEL,
    DID_DEFAULT_NAME,
    DID_REGNUMBER,
    DID_TYPE,
    DID_YEAR,
    DOMAIN,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    TICMODE_STANDARD,
)
from .serial_reader import LinkyTICReader

_LOGGER = logging.getLogger(__name__)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Modern (thru config entry) sensors setup."""
    _LOGGER.debug("%s: setting up binary sensor plateform", config_entry.title)
    # Retrieve the serial reader object
    try:
        serial_reader = hass.data[DOMAIN][config_entry.entry_id]
    except KeyError:
        _LOGGER.error(
            "%s: can not init sensors: failed to get the serial reader object",
            config_entry.title,
        )
        return
    # Wait a bit for the controller to feed on serial frames (home assistant warns after 10s)
    _LOGGER.debug(
        "%s: waiting at most 9s before setting up sensor plateform in order for the async serial reader to have time to parse a full frame",
        config_entry.title,
    )
    for i in range(9):
        await asyncio.sleep(1)
        if serial_reader.has_read_full_frame():
            _LOGGER.debug(
                "%s: a full frame has been read, initializing sensors",
                config_entry.title,
            )
            break
        if i == 8:
            _LOGGER.warning(
                "%s: wait time is over but a full frame has yet to be read: initializing sensors anyway",
                config_entry.title,
            )
    # Init sensors
    sensors = []
    if config_entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD:
        # standard mode
        _LOGGER.error(
            "%s: standard mode is not supported (yet ?): no entities will be spawned",
            config_entry.title,
        )
    else:
        # historic mode
        sensors = [
            ADCOSensor(
                config_entry.title, config_entry.entry_id, serial_reader
            ),  # needs to be the first for ADS parsing
            RegularStrSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "OPTARIF",
                "Option tarifaire choisie",
                "mdi:cash-check",
                category=EntityCategory.CONFIG,
            ),
            RegularIntSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "ISOUSC",
                "Intensité souscrite",
                category=EntityCategory.CONFIG,
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BASE",
                "Index option Base",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "HCHC",
                "Index option Heures Creuses - Heures Creuses",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "HCHP",
                "Index option Heures Creuses - Heures Pleines",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "EJPHN",
                "Index option EJP - Heures Normal"
                + "es",  # workaround for codespell in HA pre commit hook
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "EJPHPM",
                "Index option EJP - Heures de Pointe Mobile",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BBRHCJB",
                "Index option Tempo - Heures Creuses Jours Bleus",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BBRHPJB",
                "Index option Tempo - Heures Pleines Jours Bleus",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BBRHCJW",
                "Index option Tempo - Heures Creuses Jours Blancs",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BBRHPJW",
                "Index option Tempo - Heures Pleines Jours Blancs",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BBRHCJR",
                "Index option Tempo - Heures Creuses Jours Rouges",
            ),
            EnergyIndexSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "BBRHPJR",
                "Index option Tempo - Heures Pleines Jours Rouges",
            ),
            PEJPSensor(config_entry.title, config_entry.entry_id, serial_reader),
            RegularStrSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "PTEC",
                "Période Tarifaire en cours",
                "mdi:calendar-expand-horizontal",
            ),
            RegularStrSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "DEMAIN",
                "Couleur du lendemain",
                "mdi:palette",
            ),
            RegularIntSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "PAPP",
                "Puissance apparente",
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=POWER_VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularStrSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "HHPHC",
                "Horaire Heures Pleines Heures Creuses",
                "mdi:clock-outline",
                enabled_by_default=False,
            ),
            RegularStrSensor(
                config_entry.title,
                config_entry.entry_id,
                serial_reader,
                "MOTDETAT",
                "Mo"
                + "t d'état du compteur",  # workaround for codespell in HA pre commit hook
                "mdi:file-word-box-outline",
                category=EntityCategory.DIAGNOSTIC,
                enabled_by_default=False,
            ),
        ]
        # Add specific sensors
        if bool(config_entry.data.get(SETUP_THREEPHASE)):
            # three-phase - concat specific sensors
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IINST1",
                    "Intensité Instantanée (phase 1)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IINST2",
                    "Intensité Instantanée (phase 2)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IINST3",
                    "Intensité Instantanée (phase 3)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IMAX1",
                    "Intensité maximale appelée (phase 1)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IMAX2",
                    "Intensité maximale appelée (phase 2)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IMAX3",
                    "Intensité maximale appelée (phase 3)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "PMAX",
                    "Puissance maximale triphasée atteinte (jour n-1)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=POWER_WATT,  # documentation says unit is Watt but description talks about VoltAmp :/
                )
            )
            sensors.append(
                RegularStrSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "PPOT",
                    "Présence des potentiels",
                    category=EntityCategory.DIAGNOSTIC,
                )
            )
            # Burst sensors
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "ADIR1",
                    "Avertissement de Dépassement d'intensité de réglage (phase 1)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "ADIR2",
                    "Avertissement de Dépassement d'intensité de réglage (phase 2)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "ADIR3",
                    "Avertissement de Dépassement d'intensité de réglage (phase 3)",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    register_callback=True,
                )
            )
            _LOGGER.info(
                "Adding %d sensors for the three phase historic mode", len(sensors)
            )
        else:
            # single phase - concat specific sensors
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IINST",
                    "Intensité Instantanée",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "ADPS",
                    "Avertissement de Dépassement De Puissance Souscrite",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    config_entry.title,
                    config_entry.entry_id,
                    serial_reader,
                    "IMAX",
                    "Intensité maximale appelée",
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=ELECTRIC_CURRENT_AMPERE,
                )
            )
            _LOGGER.info(
                "Adding %d sensors for the single phase historic mode", len(sensors)
            )
    # Add the entities to HA
    if len(sensors) > 0:
        async_add_entities(sensors, False)


class ADCOSensor(SensorEntity):
    """Ad resse du compteur entity."""

    _extra: dict[str, str] = {}

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = (
        "Linky - A" + "dress" + "e du compteur"
    )  # workaround for codespell in HA pre commit hook
    _attr_should_poll = True
    _attr_unique_id = "linky_adco"
    _attr_icon = "mdi:tag"

    def __init__(self, title: str, uniq_id: str, serial_reader: LinkyTICReader) -> None:
        """Initialize an ADCO Sensor."""
        _LOGGER.debug("%s: initializing ADCO sensor", title)
        self._title = title
        self._attr_unique_id = (
            "linky_adco" if uniq_id is None else f"{DOMAIN}_{uniq_id}_adco"
        )
        self._serial_controller = serial_reader
        self._tag = "ADCO"
        self._device_uniq_id = uniq_id
        self._last_value: str | None = None
        # We need to parse the ADS value first thing to have correct values for the device identification
        self.update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._device_uniq_id)},
            name=f"Linky ({self._title})",
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Get HA sensor extra attributes."""
        return self._extra

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._title,
            self._tag,
            repr(value),
        )
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
        else:
            self.parse_ads(value)  # update extra info by parsing value
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._title,
                    self._tag,
                )
                self._attr_available = True
        self._last_value = value

    def parse_ads(self, ads):
        """Extract information contained in the ADS as EURIDIS."""
        _LOGGER.debug(
            "%s: parsing ADS %s",
            self._title,
            ads,
        )
        if len(ads) != 12:
            _LOGGER.error(
                "%s: ADS should be 12 char long, actually %d cannot parse: %s",
                self._title,
                len(ads),
                ads,
            )
            self._extra = {}
            return
        # let's parse ADS as EURIDIS
        device_identification = {DID_YEAR: ads[2:4], DID_REGNUMBER: ads[6:]}
        # # Parse constructor code
        constructor_code = ads[0:2]
        try:
            device_identification[DID_CONSTRUCTOR] = CONSTRUCTORS_CODES[
                constructor_code
            ]
        except KeyError:
            _LOGGER.warning(
                "%s: constructor code is unknown: %s", self._title, constructor_code
            )
            device_identification[DID_CONSTRUCTOR] = None
        # # Parse device type code
        device_type = ads[4:6]
        try:
            device_identification[DID_TYPE] = f"{DEVICE_TYPES[device_type]}"
        except KeyError:
            _LOGGER.warning(
                "%s: ADS device type is unknown: %s", self._title, device_type
            )
            device_identification[DID_TYPE] = None
        # Parsing done
        _LOGGER.debug("%s: parsed ADS: %s", self._title, repr(device_identification))
        # # Update main thread with device infos
        self._serial_controller.device_identification = device_identification
        # # Set this sensor extra attributes
        constructor_str = (
            f"{device_identification[DID_CONSTRUCTOR]} ({constructor_code})"
            if device_identification[DID_CONSTRUCTOR] is not None
            else f"Inconnu ({constructor_code})"
        )
        type_str = (
            f"{device_identification[DID_TYPE]} ({device_type})"
            if device_identification[DID_TYPE] is not None
            else f"Inconnu ({device_type})"
        )
        self._extra = {
            "constructeur": constructor_str,
            "année de construction": f"20{device_identification[DID_YEAR]}",
            "type de l'appareil": type_str,
            "matricule de l'appareil": device_identification[DID_REGNUMBER],
        }


class RegularStrSensor(SensorEntity):
    """Common class for text sensor."""

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_should_poll = True

    def __init__(
        self,
        title: str,
        uniq_id: str,
        serial_reader: LinkyTICReader,
        tag: str,
        name: str,
        icon: str | None = None,
        category: EntityCategory | None = None,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize a Regular Str Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", title, tag.upper())
        self._title = title
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        self._device_uniq_id = uniq_id
        self._last_value: str | None = None
        # Generic entity properties
        if category:
            self._attr_entity_category = category
        self._attr_name = f"Linky - {name}"
        self._attr_unique_id = (
            f"linky_{tag.lower()}"
            if uniq_id is None
            else f"{DOMAIN}_{uniq_id}_{tag.lower()}"
        )
        if icon:
            self._attr_icon = icon
        self._attr_entity_registry_enabled_default = enabled_by_default

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._device_uniq_id)},
            name=f"Linky ({self._title})",
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._title,
            self._tag,
            repr(value),
        )
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._title,
                    self._tag,
                )
                self._attr_available = True
        self._last_value = value


class RegularIntSensor(SensorEntity):
    """Common class for energy index counters."""

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_should_poll = True

    def __init__(
        self,
        title: str,
        uniq_id: str,
        serial_reader: LinkyTICReader,
        tag: str,
        name: str,
        icon: str | None = None,
        category: EntityCategory | None = None,
        device_class: SensorDeviceClass | None = None,
        native_unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
        register_callback: bool = False,
    ) -> None:
        """Initialize a Regular Int Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", title, tag.upper())
        self._title = title
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        self._device_uniq_id = uniq_id
        if register_callback:
            self._serial_controller.register_push_notif(
                self._tag, self.update_notification
            )
        self._last_value: int | None = None
        # Generic entity properties
        if category:
            self._attr_entity_category = category
        self._attr_name = f"Linky - {name}"
        self._attr_unique_id = (
            f"linky_{tag.lower()}"
            if uniq_id is None
            else f"{DOMAIN}_{uniq_id}_{tag.lower()}"
        )
        if icon:
            self._attr_icon = icon
        # Sensor Entity Properties
        if device_class:
            self._attr_device_class = device_class
        if native_unit_of_measurement:
            self._attr_native_unit_of_measurement = native_unit_of_measurement
        if state_class:
            self._attr_state_class = state_class

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._device_uniq_id)},
            name=f"Linky ({self._title})",
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> int | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._title,
            self._tag,
            repr(value),
        )
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
            self._last_value = None
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._title,
                    self._tag,
                )
                self._attr_available = True
            self._last_value = int(value)

    def update_notification(self, realtime_option: bool) -> None:
        """Receive a notification from the serial reader when our tag has been read on the wire."""
        if not realtime_option:
            _LOGGER.debug(
                "received a push notification for new %s data but user has not activated real time: skipping",
                self._tag,
            )
            if not self._attr_should_poll:
                self._attr_should_poll = (
                    True  # realtime option disable, HA should poll us
                )
            return
        # Realtime activated by user
        _LOGGER.debug(
            "received a push notification for new %s data and user has activated real time: scheduling ha update",
            self._tag,
        )
        if self._attr_should_poll:
            self._attr_should_poll = False  # now that user has activated realtime, we will push data, no need for HA to poll us
        self.schedule_update_ha_state(force_refresh=True)


class EnergyIndexSensor(RegularIntSensor):
    """Common class for energy index counters."""

    def __init__(
        self,
        title: str,
        uniq_id: str,
        serial_reader: LinkyTICReader,
        tag: str,
        name: str,
    ) -> None:
        """Initialize an Energy Index sensor."""
        super().__init__(
            title,
            uniq_id,
            serial_reader,
            tag,
            name,
            icon="mdi:counter",
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=ENERGY_WATT_HOUR,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )


class PEJPSensor(SensorEntity):
    """Préavis Début EJP (30 min) sensor."""

    #
    # This sensor could be improved I think (minutes as integer), but I do not have it to check and test its values
    # Leaving it as it is to facilitate future modifications
    #

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_name = "Linky - Préavis Début EJP"
    _attr_should_poll = True
    _attr_unique_id = "linky_pejp"
    _attr_icon = "mdi:clock-start"

    def __init__(self, title: str, uniq_id: str, serial_reader: LinkyTICReader) -> None:
        """Initialize a PEJP sensor."""
        _LOGGER.debug("%s: initializing PEJP sensor", title)
        self._title = title
        self._serial_controller = serial_reader
        self._tag = "PEJP"
        self._attr_unique_id = (
            "linky_pejp" if uniq_id is None else f"{DOMAIN}_{uniq_id}_pejp"
        )
        self._device_uniq_id = uniq_id
        self._last_value: str | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            default_manufacturer=DID_DEFAULT_MANUFACTURER,
            default_model=DID_DEFAULT_MODEL,
            default_name=DID_DEFAULT_NAME,
            identifiers={(DOMAIN, self._device_uniq_id)},
            name=f"Linky ({self._title})",
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._title,
            self._tag,
            repr(value),
        )
        if value is None:
            if self._attr_available and self._serial_controller.has_read_full_frame():
                _LOGGER.info(
                    "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                    self._title,
                    self._tag,
                    self._tag,
                )
                self._attr_available = False
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now ! (was not previously)",
                    self._title,
                    self._tag,
                )
                self._attr_available = True
        self._last_value = value
