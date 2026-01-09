"""The linkytic integration."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components import usb
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import (
    DOMAIN,
    LINKY_IO_ERRORS,
    OPTIONS_REALTIME,
    SETUP_PRODUCER,
    SETUP_SERIAL,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    TICMODE_STANDARD,
)
from .serial_reader import LinkyTICReader

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry[LinkyTICReader]
) -> bool:
    """Set up linkytic from a config entry."""
    # Create the serial reader thread and start it
    port = entry.data[SETUP_SERIAL]
    try:
        serial_reader = LinkyTICReader(
            title=entry.title,
            port=port,
            std_mode=entry.data[SETUP_TICMODE] == TICMODE_STANDARD,
            producer_mode=entry.data[SETUP_PRODUCER],
            three_phase=entry.data[SETUP_THREEPHASE],
            real_time=entry.options.get(OPTIONS_REALTIME),
        )
        serial_reader.start()

        async def read_serial_number(serial: LinkyTICReader) -> str:
            while serial.serial_number is None:
                await asyncio.sleep(1)
                # Check for any serial error that occurred in the serial thread context
                if serial.setup_error:
                    raise serial.setup_error
            return serial.serial_number

        s_n = await asyncio.wait_for(read_serial_number(serial_reader), timeout=5)
        # TODO: check if S/N is the one saved in config entry, if not this is a different meter!

    # Error when opening serial port.
    except LINKY_IO_ERRORS as e:
        raise ConfigEntryNotReady(f"Couldn't open serial port {port}: {e}") from e

    # Timeout waiting for S/N to be read.
    except TimeoutError as e:
        serial_reader.signalstop("linkytic_timeout")
        raise ConfigEntryNotReady(
            "Connected to serial port but coulnd't read serial number before timeout: check if TIC is connected and active."
        ) from e

    # entry.unique_id is the serial number read during the config flow, all data correspond to this meter s/n
    if s_n != entry.unique_id:
        serial_reader.signalstop("serial_number_mismatch")
        raise ConfigEntryError(
            f"Connected to a different meter with S/N: `{s_n}`, expected `{entry.unique_id}`. "
            "Aborting setup to prevent overwriting long term data."
        )

    _LOGGER.info(f"Device connected with serial number: {s_n}")

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, serial_reader.signalstop)
    # Add options callback
    entry.async_on_unload(entry.add_update_listener(update_listener))

    entry.runtime_data = serial_reader

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry[LinkyTICReader]
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        reader = entry.runtime_data
        reader.signalstop("unload")
    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""

    reader = entry.runtime_data
    reader.update_options(entry.options.get(OPTIONS_REALTIME))


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.info("Migrating from version %d.%d", entry.version, entry.minor_version)

    if entry.version == 1:
        new = {**entry.data}

        if entry.minor_version < 2:
            # Migrate to serial by-id.
            serial_by_id = await hass.async_add_executor_job(
                usb.get_serial_by_id, new[SETUP_SERIAL]
            )
            if serial_by_id == new[SETUP_SERIAL]:
                _LOGGER.warning(
                    f"Couldn't find a persistent /dev/serial/by-id alias for {serial_by_id}. "
                    "Problems might occur at startup if device names are not persistent."
                )
            else:
                new[SETUP_SERIAL] = serial_by_id

        # Migrate the unique ID to use the serial number, this is not backward compatible
        try:
            reader = LinkyTICReader(
                title=entry.title,
                port=new[SETUP_SERIAL],
                std_mode=new[SETUP_TICMODE] == TICMODE_STANDARD,
                producer_mode=new[SETUP_PRODUCER],
                three_phase=new[SETUP_THREEPHASE],
            )
            reader.start()

            async def read_serial_number(serial: LinkyTICReader) -> str:
                while serial.serial_number is None:
                    await asyncio.sleep(1)
                    # Check for any serial error that occurred in the serial thread context
                    if serial.setup_error:
                        raise serial.setup_error
                return serial.serial_number

            s_n = await asyncio.wait_for(read_serial_number(reader), timeout=5)

        except (*LINKY_IO_ERRORS, TimeoutError) as e:
            _LOGGER.error(
                "Error migrating config entry to version 2, could not read device serial number: (%s)",
                e,
            )
            _LOGGER.warning("Restart Home Assistant to retry migration")
            return False

        finally:
            reader.signalstop("probe_end")

        serial_number = slugify(s_n)

        # Explicitly pass serial number as config entry is not updated yet
        await _migrate_entities_unique_id(hass, entry, serial_number)

        hass.config_entries.async_update_entry(
            entry, data=new, version=2, minor_version=0, unique_id=serial_number
        )

    _LOGGER.info(
        "Migration to version %d.%d successful",
        entry.version,
        entry.minor_version,
    )
    return True


async def _migrate_entities_unique_id(
    hass: HomeAssistant, entry: ConfigEntry, serial_number: str
) -> None:
    """Migrate entities unique id to conform to HA specifications."""

    # Old entries are of format f"{DOMAIN}_{entry.config_id}_suffix"
    # which is not conform to HA unique ID requirements (https://developers.home-assistant.io/docs/entity_registry_index#unique-id-requirements)
    # domain should not appear in the unique id
    # ConfigEntry.config_id is a last resort unique id when no acceptable source is awailable
    # the meter serial number is a valid (and better) device unique id

    # Since we are migrating unique id, might as well migrate some suffixes for consistency
    _ENTITY_MIGRATION_SUFFIX = {
        # non-standard tic tags that were implemented as different sensors
        "smaxn": "smaxsn",
        "smaxn-1": "smaxsn-1",
        # status register sensors, due to field renaming
        "contact_sec": "dry_contact",
        "organe_de_coupure": "trip_unit",
        "etat_du_cache_borne_distributeur": "terminal_cover",
        "surtension_sur_une_des_phases": "overvoltage",
        "depassement_puissance_reference": "power_over_ref",
        "producteur_consommateur": "producer",
        "sens_energie_active": "injecting",
        "tarif_contrat_fourniture": "provider_index",
        "tarif_contrat_distributeur": "distributor_index",
        "mode_degrade_horloge": "rtc_degraded",
        "mode_tic": "tic_std",
        "etat_sortie_communication_euridis": "euridis",
        "synchro_cpl": "cpl_sync",
        "status_cpl": "cpl_status",
        "couleur_jour_contrat_tempo": "color_today",
        "couleur_lendemain_contrat_tempo": "color_next_day",
        "preavis_pointes_mobiles": "mobile_peak_notice",
        "pointe_mobile": "mobile_peak",
    }

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_reg, entry.entry_id)

    migrate_entities: dict[str, str] = {}

    for entity in entities:
        old_unique_id = entity.unique_id

        # Old ids all start with `linkytic_`
        if not old_unique_id.startswith(DOMAIN):
            continue

        # format `linkytic_ENTRYID_suffix
        old_suffix = old_unique_id.split(entry.entry_id + "_", maxsplit=1)[1]

        if (new_suffix := _ENTITY_MIGRATION_SUFFIX.get(old_suffix)) is None:
            # entity is not in the migration table, just remove the domain prefix and update the entry_id
            new_suffix = old_suffix

        migrate_entities[entity.entity_id] = slugify(f"{serial_number}_{new_suffix}")

        _LOGGER.debug(
            "Updating entity %s from unique id `%s` to `%s`",
            entity.entity_id,
            old_unique_id,
            migrate_entities[entity.entity_id],
        )

    for entity_id, unique_id in migrate_entities.items():
        entity_reg.async_update_entity(entity_id, new_unique_id=unique_id)
