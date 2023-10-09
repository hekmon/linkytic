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
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONSTRUCTORS_CODES,
    DEVICE_TYPES,
    DID_CONNECTION_TYPE,
    DID_CONSTRUCTOR,
    DID_DEFAULT_NAME,
    DID_REGNUMBER,
    DID_TYPE,
    DID_YEAR,
    DOMAIN,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    SETUP_PRODUCER,
    TICMODE_STANDARD,
)

from .serial_reader import LinkyTICReader

from enum import Enum
class StatusRegister(Enum):
    CONTACT_SEC=1,
    ORGANE_DE_COUPURE=2,
    ETAT_DU_CACHE_BORNE_DISTRIBUTEUR=3,
    SURTENSION_SUR_UNE_DES_PHASES=4,
    DEPASSEMENT_PUISSANCE_REFERENCE=5,
    PRODUCTEUR_CONSOMMATEUR=6,
    SENS_ENERGIE_ACTIVE=7,
    TARIF_CONTRAT_FOURNITURE=8,
    TARIF_CONTRAT_DISTRIBUTEUR=9,
    MODE_DEGRADE_HORLOGE=10,
    MODE_TIC=11,
    ETAT_SORTIE_COMMUNICATION_EURIDIS=12,
    STATUS_CPL=13,
    SYNCHRO_CPL=14,
    COULEUR_JOUR_CONTRAT_TEMPO=15,
    COULEUR_LENDEMAIN_CONTRAT_TEMPO=16,
    PREAVIS_POINTES_MOBILES=17,
    POINTE_MOBILE=18
    
_LOGGER = logging.getLogger(__name__)


# config flow setup
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Modern (thru config entry) sensors setup."""
    _LOGGER.debug("%s: setting up sensor plateform", config_entry.title)
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
        sensors = [
            ADCOSensor(
                config_entry.title, "ADSC", config_entry.entry_id, serial_reader
            ),  # needs to be the first for ADS parsing
            RegularStrSensor(
                tag="VTIC",
                name="Version de la TIC",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                category=EntityCategory.CONFIG,
            ),
            DateEtHeureSensor(
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="NGTF",
                name="Nom du calendrier tarifaire fournisseur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                category=EntityCategory.CONFIG,
            ),
            RegularStrSensor(
                tag="LTARF",
                name="Libellé tarif fournisseur en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                category=EntityCategory.CONFIG,
            ),
            EnergyIndexSensor(
                tag="EAST",
                name="Energie active soutirée totale",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF01",
                name="Energie active soutirée fournisseur, index 01",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF02",
                name="Energie active soutirée fournisseur, index 02",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF03",
                name="Energie active soutirée fournisseur, index 03",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF04",
                name="Energie active soutirée fournisseur, index 04",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF05",
                name="Energie active soutirée fournisseur, index 05",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF06",
                name="Energie active soutirée fournisseur, index 06",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF07",
                name="Energie active soutirée fournisseur, index 07",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF08",
                name="Energie active soutirée fournisseur, index 08",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASF09",
                name="Energie active soutirée fournisseur, index 09",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASD01",
                name="Energie active soutirée distributeur, index 01",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASD02",
                name="Energie active soutirée distributeur, index 02",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASD03",
                name="Energie active soutirée distributeur, index 03",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EASD04",
                name="Energie active soutirée distributeur, index 04",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            RegularIntSensor(
                tag="IRMS1",
                name="Courant efficace, phase 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                tag="URMS1",
                name="Tension efficace, phase 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                # Should be kVA
                tag="PREF",
                name="Puissance app. de référence",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                # Should be kVA
                tag="PCOUP",
                name="Puissance app. de coupure",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                tag="SINSTS",
                name="Puissance app. instantanée soutirée",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                tag="SMAXSN",
                name="Puissance app. max. soutirée n",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                tag="SMAXSN-1",
                name="Puissance app. max. soutirée n-1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                tag="CCASN",
                name="Point n de la courbe de charge active soutirée",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
            ),
            RegularIntSensor(
                tag="CCASN-1",
                name="Point n-1 de la courbe de charge active soutirée",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
            ),
            RegularIntSensor(
                tag="UMOY1",
                name="Tension moy. ph. 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularStrSensor(
                tag="DPM1",
                name="Début pointe mobile 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-start",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="FPM1",
                name="Fin pointe mobile 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-end",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="DPM2",
                name="Début pointe mobile 2",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-start",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="FPM2",
                name="Fin pointe mobile 2",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-end",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="DPM3",
                name="Début pointe mobile 3",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-start",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="FPM3",
                name="Fin pointe mobile 3",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-end",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="MSG1",
                name="Message court",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:message-text-outline",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="MSG2",
                name="Message Ultra court",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:message-text-outline",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="PRM",
                name="PRM",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                category=EntityCategory.CONFIG,
            ),
            RegularStrSensor(
                tag="RELAIS",
                name="Relais",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:electric-switch",
                category=EntityCategory.CONFIG,
            ),
            RegularStrSensor(
                tag="NTARF",
                name="Numéro de l’index tarifaire en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="NJOURF",
                name="Numéro du jour en cours calendrier fournisseur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-month-outline",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="NJOURF+1",
                name="Numéro du prochain jour calendrier fournisseur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-month-outline",
                category=EntityCategory.DIAGNOSTIC,
            ),
            ProfilDuProchainJourCalendrierFournisseurSensor(
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                category=EntityCategory.DIAGNOSTIC,
            ),    
            RegularStrSensor(
                tag="PPOINTE",
                name="Profil du prochain jour de pointe",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-month-outline",
                category=EntityCategory.DIAGNOSTIC,
            ),
            RegularStrSensor(
                tag="STGE",
                name="Registre de statuts",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:list-status",
                category=EntityCategory.DIAGNOSTIC,
            ),    
            StatusRegisterData(
                name="Statut contact sec",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:electric-switch",
                data=StatusRegister.CONTACT_SEC,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut organe de coupure",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:connection",
                data=StatusRegister.ORGANE_DE_COUPURE,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut état du cache-bornes distributeur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:toy-brick-outline",
                data=StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut surtension sur une des phases",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:flash-alert",
                data=StatusRegister.SURTENSION_SUR_UNE_DES_PHASES,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut dépassement de la puissance de référence",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:flash-alert",
                data=StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut producteur/consommateur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:transmission-tower",
                data=StatusRegister.PRODUCTEUR_CONSOMMATEUR,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut sens de l’énergie active",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:transmission-tower",
                data=StatusRegister.SENS_ENERGIE_ACTIVE,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut tarif contrat fourniture",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                data=StatusRegister.TARIF_CONTRAT_FOURNITURE,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut tarif contrat distributeur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                data=StatusRegister.TARIF_CONTRAT_DISTRIBUTEUR,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut mode dégradée de l'horloge",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-alert-outline",
                data=StatusRegister.MODE_DEGRADE_HORLOGE,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut sortie télé-information",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                data=StatusRegister.MODE_TIC,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut sortie communication Euridis",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                data=StatusRegister.ETAT_SORTIE_COMMUNICATION_EURIDIS,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut CPL",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                data=StatusRegister.STATUS_CPL,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut synchronisation CPL",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:sync",
                data=StatusRegister.SYNCHRO_CPL,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut couleur du jour tempo",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
                data=StatusRegister.COULEUR_JOUR_CONTRAT_TEMPO,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut couleur du lendemain tempo",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
                data=StatusRegister.COULEUR_LENDEMAIN_CONTRAT_TEMPO,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut préavis pointes mobiles",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-alert-outline",
                data=StatusRegister.PREAVIS_POINTES_MOBILES,
                category=EntityCategory.DIAGNOSTIC,
            ),
            StatusRegisterData(
                name="Statut pointe mobile",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:progress-clock",
                data=StatusRegister.POINTE_MOBILE,
                category=EntityCategory.DIAGNOSTIC,
            ),
        ]

        # Add producer specific sensors
        if bool(config_entry.data.get(SETUP_PRODUCER)):
            sensors.append(
                EnergyIndexSensor(
                    tag="EAIT",
                    name="Energie active injectée totale",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                EnergyIndexSensor(
                    tag="ERQ1",
                    name="Energie réactive Q1 totale",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                EnergyIndexSensor(
                    tag="ERQ2",
                    name="Energie réactive Q2 totale",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                EnergyIndexSensor(
                    tag="ERQ3",
                    name="Energie réactive Q3 totale",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                EnergyIndexSensor(
                    tag="ERQ4",
                    name="Energie réactive Q4 totale",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SINSTI",
                    name="Puissance app. instantanée injectée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXIN",
                    name="Puissance app. max. injectée n",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXIN-1",
                    name="Puissance app. max. injectée n-1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="CCAIN",
                    name="Point n de la courbe de charge active injectée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.POWER,
                    native_unit_of_measurement=UnitOfPower.WATT,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="CCAIN-1",
                    name="Point n-1 de la courbe de charge active injectée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.POWER,
                    native_unit_of_measurement=UnitOfPower.WATT,
                    icon="mdi:transmission-tower-import",
                )
            )

        # Add three-phase specific sensors
        if bool(config_entry.data.get(SETUP_THREEPHASE)):
            sensors.append(
                RegularIntSensor(
                    tag="IRMS2",
                    name="Courant efficace, phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IRMS3",
                    name="Courant efficace, phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="URMS2",
                    name="Tension efficace, phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.VOLTAGE,
                    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="URMS3",
                    name="Tension efficace, phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.VOLTAGE,
                    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SINSTS1",
                    name="Puissance app. instantanée soutirée phase 1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SINSTS2",
                    name="Puissance app. instantanée soutirée phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SINSTS3",
                    name="Puissance app. instantanée soutirée phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXSN1",
                    name="Puissance app max. soutirée n phase 1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXSN2",
                    name="Puissance app max. soutirée n phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXSN3",
                    name="Puissance app max. soutirée n phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXSN1-1",
                    name="Puissance app max. soutirée n-1 phase 1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXSN2-1",
                    name="Puissance app max. soutirée n-1 phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="SMAXSN3-1",
                    name="Puissance app max. soutirée n-1 phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.APPARENT_POWER,
                    native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            RegularIntSensor(
                tag="UMOY2",
                name="Tension moy. ph. 2",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularIntSensor(
                tag="UMOY3",
                name="Tension moy. ph. 3",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),

    else:
        # historic mode
        sensors = [
            ADCOSensor(
                config_entry.title, "ADCO", config_entry.entry_id, serial_reader
            ),  # needs to be the first for ADS parsing
            RegularStrSensor(
                tag="OPTARIF",
                name="Option tarifaire choisie",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                category=EntityCategory.CONFIG,
            ),
            RegularIntSensor(
                tag="ISOUSC",
                name="Intensité souscrite",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                category=EntityCategory.CONFIG,
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            ),
            EnergyIndexSensor(
                tag="BASE",
                name="Index option Base",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="HCHC",
                name="Index option Heures Creuses - Heures Creuses",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="HCHP",
                name="Index option Heures Creuses - Heures Pleines",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EJPHN",
                name="Index option EJP - Heures Normal"
                + "es",  # workaround for codespell in HA pre commit hook
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="EJPHPM",
                name="Index option EJP - Heures de Pointe Mobile",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHCJB",
                name="Index option Tempo - Heures Creuses Jours Bleus",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHPJB",
                name="Index option Tempo - Heures Pleines Jours Bleus",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHCJW",
                name="Index option Tempo - Heures Creuses Jours Blancs",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHPJW",
                name="Index option Tempo - Heures Pleines Jours Blancs",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHCJR",
                name="Index option Tempo - Heures Creuses Jours Rouges",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            EnergyIndexSensor(
                tag="BBRHPJR",
                name="Index option Tempo - Heures Pleines Jours Rouges",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            PEJPSensor(
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            RegularStrSensor(
                tag="PTEC",
                name="Période Tarifaire en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-expand-horizontal",
            ),
            RegularStrSensor(
                tag="DEMAIN",
                name="Couleur du lendemain",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
            ),
            RegularIntSensor(
                tag="PAPP",
                name="Puissance apparente",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                device_class=SensorDeviceClass.APPARENT_POWER,
                native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            RegularStrSensor(
                tag="HHPHC",
                name="Horaire Heures Pleines Heures Creuses",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-outline",
                enabled_by_default=False,
            ),
            RegularStrSensor(
                tag="MOTDETAT",
                name="Mo"
                + "t d'état du compteur",  # workaround for codespell in HA pre commit hook
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:file-word-box-outline",
                category=EntityCategory.DIAGNOSTIC,
                enabled_by_default=False,
            ),
        ]
        # Add specific sensors
        if bool(config_entry.data.get(SETUP_THREEPHASE)):
            # three-phase - concat specific sensors
            sensors.append(
                RegularIntSensor(
                    tag="IINST1",
                    name="Intensité Instantanée (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IINST2",
                    name="Intensité Instantanée (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IINST3",
                    name="Intensité Instantanée (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX1",
                    name="Intensité maximale appelée (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX2",
                    name="Intensité maximale appelée (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX3",
                    name="Intensité maximale appelée (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="PMAX",
                    name="Puissance maximale triphasée atteinte (jour n-1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.POWER,
                    native_unit_of_measurement=UnitOfPower.WATT,  # documentation says unit is Watt but description talks about VoltAmp :/
                )
            )
            sensors.append(
                RegularStrSensor(
                    tag="PPOT",
                    name="Présence des potentiels",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    category=EntityCategory.DIAGNOSTIC,
                )
            )
            # Burst sensors
            sensors.append(
                RegularIntSensor(
                    tag="ADIR1",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="ADIR2",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="ADIR3",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
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
                    tag="IINST",
                    name="Intensité Instantanée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="ADPS",
                    name="Avertissement de Dépassement De Puissance Souscrite",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                RegularIntSensor(
                    tag="IMAX",
                    name="Intensité maximale appelée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                )
            )
            _LOGGER.info(
                "Adding %d sensors for the single phase historic mode", len(sensors)
            )
    # Add the entities to HA
    if len(sensors) > 0:
        async_add_entities(sensors, True)


class ADCOSensor(SensorEntity):
    """Ad resse du compteur entity."""

    _extra: dict[str, str] = {}

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = (
        "A" + "dress" + "e du compteur"
    )  # workaround for codespell in HA pre commit hook
    _attr_should_poll = True
    _attr_icon = "mdi:tag"

    def __init__(
        self, config_title: str, tag: str, config_uniq_id: str, serial_reader: LinkyTICReader
    ) -> None:
        """Initialize an ADCO/ADSC Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = tag
        # Generic entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_adco"
        # We need to parse the ADS value first thing to have correct values for the device identification
        self.update()

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            # connections={(DID_CONNECTION_TYPE, self._serial_controller._port)},
            identifiers={(DOMAIN, self._serial_controller.device_identification[DID_REGNUMBER])},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
            name=DID_DEFAULT_NAME,
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
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
        else:
            self.parse_ads(value)  # update extra info by parsing value
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value = value

    def parse_ads(self, ads):
        """Extract information contained in the ADS as EURIDIS."""
        _LOGGER.debug(
            "%s: parsing ADS: %s",
            self._config_title,
            ads,
        )
        if len(ads) != 12:
            _LOGGER.error(
                "%s: ADS should be 12 char long, actually %d cannot parse: %s",
                self._config_title,
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
                "%s: constructor code is unknown: %s",
                self._config_title,
                constructor_code,
            )
            device_identification[DID_CONSTRUCTOR] = None
        # # Parse device type code
        device_type = ads[4:6]
        try:
            device_identification[DID_TYPE] = f"{DEVICE_TYPES[device_type]}"
        except KeyError:
            _LOGGER.warning(
                "%s: ADS device type is unknown: %s", self._config_title, device_type
            )
            device_identification[DID_TYPE] = None
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
        # Parsing done
        _LOGGER.debug("%s: parsed ADS: %s", self._config_title, repr(self._extra))


class RegularStrSensor(SensorEntity):
    """Common class for text sensor."""

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(
        self,
        tag: str,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        icon: str | None = None,
        category: EntityCategory | None = None,
        enabled_by_default: bool = True,
    ) -> None:
        """Initialize a Regular Str Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag.upper())
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = tag.upper()
        # Generic Entity properties
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{tag.lower()}"
        if icon:
            self._attr_icon = icon
        if category:
            self._attr_entity_category = category
        self._attr_entity_registry_enabled_default = enabled_by_default

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            # connections={(DID_CONNECTION_TYPE, self._serial_controller._port)},
            identifiers={(DOMAIN, self._serial_controller.device_identification[DID_REGNUMBER])},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
            name=DID_DEFAULT_NAME,
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value = value


class RegularIntSensor(SensorEntity):
    """Common class for energy index counters."""

    # Generic entity properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties
    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(
        self,
        tag: str,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        icon: str | None = None,
        category: EntityCategory | None = None,
        device_class: SensorDeviceClass | None = None,
        native_unit_of_measurement: str | None = None,
        state_class: SensorStateClass | None = None,
        register_callback: bool = False,
    ) -> None:
        """Initialize a Regular Int Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag.upper())
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: int | None = None
        self._serial_controller = serial_reader
        self._tag = tag.upper()

        if register_callback:
            self._serial_controller.register_push_notif(
                self._tag, self.update_notification
            )
        # Generic Entity properties
        if category:
            self._attr_entity_category = category
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{tag.lower()}"
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
            # connections={(DID_CONNECTION_TYPE, self._serial_controller._port)},
            identifiers={(DOMAIN, self._serial_controller.device_identification[DID_REGNUMBER])},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
            name=DID_DEFAULT_NAME,
        )

    @property
    def native_value(self) -> int | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability and save value
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
            # Nullify value
            self._last_value = None
        else:
            self._last_value = int(value)
            if not self._attr_available:
                _LOGGER.debug(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True

    def update_notification(self, realtime_option: bool) -> None:
        """Receive a notification from the serial reader when our tag has been read on the wire."""
        # Realtime off
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
        # Realtime on
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
        tag: str,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        icon: str | None = "mdi:counter",
    ) -> None:
        """Initialize an Energy Index sensor."""
        super().__init__(
            tag=tag,
            name=name,
            config_title=config_title,
            config_uniq_id=config_uniq_id,
            serial_reader=serial_reader,
            icon=icon,
            device_class=SensorDeviceClass.ENERGY,
            native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
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
    _attr_has_entity_name = True
    _attr_name = "Préavis Début EJP"
    _attr_should_poll = True
    _attr_icon = "mdi:clock-start"

    def __init__(
        self, config_title: str, config_uniq_id: str, serial_reader: LinkyTICReader
    ) -> None:
        """Initialize a PEJP sensor."""
        _LOGGER.debug("%s: initializing PEJP sensor", config_title)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = "PEJP"
        # Generic Entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{self._tag.lower()}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            # connections={(DID_CONNECTION_TYPE, self._serial_controller._port)},
            identifiers={(DOMAIN, self._serial_controller.device_identification[DID_REGNUMBER])},
            manufacturer=self._serial_controller.device_identification[DID_CONSTRUCTOR],
            model=self._serial_controller.device_identification[DID_TYPE],
            name=DID_DEFAULT_NAME,
        )

    @property
    def native_value(self) -> str | None:
        """Value of the sensor."""
        return self._last_value

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value = value
        
class DateEtHeureSensor(RegularStrSensor):
    """Date et heure courante sensor."""

    _attr_has_entity_name = True
    _attr_name = "Date et heure courante"
    _attr_should_poll = True
    _attr_icon = "mdi:clock-outline"

    def __init__(
        self, config_title: str, config_uniq_id: str, serial_reader: LinkyTICReader, category: EntityCategory | None = None,
    ) -> None:
        """Initialize a Date et heure sensor."""
        _LOGGER.debug("%s: initializing Date et heure courante sensor", config_title)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = "DATE"
        
        if category:
            self._attr_entity_category = category
        
        # Generic Entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{self._tag.lower()}"

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, horodate = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        saison="";
        if horodate[0:1]=='E':		
            saison=" (Eté)"
        elif horodate[0:1]=='H':
            saison=" (Hiver)"
                
        self._last_value = horodate[5:7] + "/" + horodate[3:5] + "/" + horodate[1:3] + " " + horodate[7:9] + ":" + horodate[9:11] + saison
        
class ProfilDuProchainJourCalendrierFournisseurSensor(RegularStrSensor):
    """Profil du prochain jour du calendrier fournisseur sensor."""

    _attr_has_entity_name = True
    _attr_name = "Profil du prochain jour calendrier fournisseur"
    _attr_should_poll = True
    _attr_icon = "mdi:calendar-month-outline"

    def __init__(
        self, config_title: str, config_uniq_id: str, serial_reader: LinkyTICReader, category: EntityCategory | None = None,
    ) -> None:
        """Initialize a Profil du prochain jour du calendrier fournisseur sensor."""
        _LOGGER.debug("%s: initializing Date et heure courante sensor", config_title)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = "PJOURF+1"
        
        if category:
            self._attr_entity_category = category
        
        # Generic Entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{self._tag.lower()}"

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, horodate = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
        # Save value
        self._last_value=value.replace(" NONUTILE", "")
        
class StatusRegisterData(RegularStrSensor):
    """Data from status register."""
    _attr_has_entity_name = True
    _attr_should_poll = True

    def __init__(
        self,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        data: StatusRegisterData,
        enabled_by_default: bool = True,        
        icon: str | None = None,
        category: EntityCategory | None = None,
    ) -> None:
        """Initialize a status register data sensor."""
        _LOGGER.debug("%s: initializing a status register data sensor", config_title)
        # Linky TIC sensor properties
        self._config_title = config_title
        self._config_uniq_id = config_uniq_id
        self._last_value: str | None = None
        self._serial_controller = serial_reader
        self._tag = "STGE"
        self._data = data

        # Generic Entity properties
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{self._tag.lower()}_{data.name.lower()}"
        _LOGGER.debug(
            "%s: uniq_id: %s",
            self._config_title,
            self._attr_unique_id,
        )
        
        if icon:
            self._attr_icon = icon
        if category:
            self._attr_entity_category = category
        self._attr_entity_registry_enabled_default = enabled_by_default
        
        if category:
            self._attr_entity_category = category

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: %s",
            self._config_title,
            self._tag,
            repr(value),
        )
        # Handle entity availability
        if value is None:
            if self._attr_available:
                if not self._serial_controller.is_connected():
                    _LOGGER.debug(
                        "%s: marking the %s sensor as unavailable: serial connection lost",
                        self._config_title,
                        self._tag,
                    )
                    self._attr_available = False
                elif self._serial_controller.has_read_full_frame():
                    _LOGGER.info(
                        "%s: marking the %s sensor as unavailable: a full frame has been read but %s has not been found",
                        self._config_title,
                        self._tag,
                        self._tag,
                    )
                    self._attr_available = False
                # else: we are connected but a full frame has not been read yet, let's wait a little longer before marking it unavailable
        else:
            if not self._attr_available:
                _LOGGER.info(
                    "%s: marking the %s sensor as available now !",
                    self._config_title,
                    self._tag,
                )
                self._attr_available = True
                  
        try:
            val = int(value, 16)

            # Save value        
            if self._data==StatusRegister.CONTACT_SEC:        
                self._last_value = "Ouvert" if (val&0x01) else "Fermé"
            
            elif self._data==StatusRegister.ORGANE_DE_COUPURE:
                val_organe_de_coupure=(val>>1)&0x07
                if val_organe_de_coupure==0:
                    self._last_value="Fermé"
                elif val_organe_de_coupure==1:
                    self._last_value="Ouvert sur surpuissance"
                elif val_organe_de_coupure==2:
                    self._last_value="Ouvert sur surtension"
                elif val_organe_de_coupure==3:
                    self._last_value="Ouvert sur délestage"
                elif val_organe_de_coupure==4:
                    self._last_value="Ouvert sur ordre CPL ou Euridis"
                elif val_organe_de_coupure==5:
                    self._last_value="Ouvert sur une surchauffe (>Imax)"
                elif val_organe_de_coupure==6:
                    self._last_value="Ouvert sur une surchauffe (<Imax)"

            elif self._data==StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR:
                self._last_value = "Ouvert" if ((val>>4)&0x01) else "Fermé"

            elif self._data==StatusRegister.SURTENSION_SUR_UNE_DES_PHASES:
                self._last_value = "Surtension" if ((val>>6)&0x01) else "Pas de surtension"

            elif self._data==StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE:
                self._last_value = "Dépassement en cours" if ((val>>7)&0x01) else "Pas de dépassement"

            elif self._data==StatusRegister.PRODUCTEUR_CONSOMMATEUR:
                self._last_value = "Producteur" if ((val>>8)&0x01) else "Consommateur"

            elif self._data==StatusRegister.SENS_ENERGIE_ACTIVE:
                self._last_value = "Energie active négative" if ((val>>9)&0x01) else "Energie active positive"

            elif self._data==StatusRegister.TARIF_CONTRAT_FOURNITURE:
                index=(val>>10)&0x0F
                self._last_value = "Energie ventillée sur index " + str(index+1)

            elif self._data==StatusRegister.TARIF_CONTRAT_DISTRIBUTEUR:
                index=(val>>14)&0x03
                self._last_value = "Energie ventillée sur index " + str(index+1)

            elif self._data==StatusRegister.MODE_DEGRADE_HORLOGE:
                self._last_value = "Horloge en mode dégradée" if ((val>>16)&0x01) else "Horloge correcte"

            elif self._data==StatusRegister.MODE_TIC:
                self._last_value = "Mode standard" if ((val>>17)&0x01) else "Mode historique"
                
            elif self._data==StatusRegister.ETAT_SORTIE_COMMUNICATION_EURIDIS:
                etat=(val>>19)&0x03
                if etat==0:
                    self._last_value = "Désactivée"
                elif etat==1:
                    self._last_value = "Activée sans sécurité"
                elif etat==3:
                    self._last_value = "Activée avec sécurité"
                else:
                    self._last_value = "Inconnue"
                            
            elif self._data==StatusRegister.STATUS_CPL:
                etat=(val>>21)&0x03
                if etat==0:
                    self._last_value = "New/Unlock"
                elif etat==1:
                    self._last_value = "New/Lock"
                elif etat==2:
                    self._last_value = "Registered"
                else:
                    self._last_value = "Inconnue"
                            
            elif self._data==StatusRegister.SYNCHRO_CPL:
                self._last_value = "Compteur synchronisé" if ((val>>23)&0x01) else "Compteur non synchronisé"

            elif self._data==StatusRegister.COULEUR_JOUR_CONTRAT_TEMPO:
                etat=(val>>24)&0x03
                if etat==0:
                    self._last_value = "Pas d'annonce"
                elif etat==1:
                    self._last_value = "Bleu"
                elif etat==2:
                    self._last_value = "Blanc"
                else:
                    self._last_value = "Rouge"
            
            elif self._data==StatusRegister.COULEUR_LENDEMAIN_CONTRAT_TEMPO:
                etat=(val>>26)&0x03
                if etat==0:
                    self._last_value = "Pas d'annonce"
                elif etat==1:
                    self._last_value = "Bleu"
                elif etat==2:
                    self._last_value = "Blanc"
                else:
                    self._last_value = "Rouge"
            
            elif self._data==StatusRegister.PREAVIS_POINTES_MOBILES:
                etat=(val>>28)&0x03
                if etat==0:
                    self._last_value = "Pas de préavis en cours"
                elif etat==1:
                    self._last_value = "Préavis PM1 en cours"
                elif etat==2:
                    self._last_value = "Préavis PM2 en cours"
                else:
                    self._last_value = "Préavis PM3 en cours"
            
            elif self._data==StatusRegister.POINTE_MOBILE:
                etat=(val>>28)&0x03
                if etat==0:
                    self._last_value = "Pas de pointe mobile"
                elif etat==1:
                    self._last_value = "PM1 en cours"
                elif etat==2:
                    self._last_value = "PM2 en cours"
                else:
                    self._last_value = "PM3 en cours"
                
            else:
                self._last_value = self._data.name
                
        except ValueError:
            _LOGGER.error(
                "%s: Invalid status register : %s",
                    self._config_title,
                    value,
                )
                
