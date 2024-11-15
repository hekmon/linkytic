"""Sensors for Linky TIC integration."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Generic, Optional, TypeVar, cast

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
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import LinkyTICEntity
from .const import (
    DID_CONSTRUCTOR,
    DID_CONSTRUCTOR_CODE,
    DID_REGNUMBER,
    DID_TYPE,
    DID_TYPE_CODE,
    DID_YEAR,
    DOMAIN,
    SETUP_PRODUCER,
    SETUP_THREEPHASE,
    SETUP_TICMODE,
    TICMODE_STANDARD,
    EXPERIMENTAL_DEVICES,
)
from .serial_reader import LinkyTICReader
from .status_register import StatusRegister

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
        serial_reader: LinkyTICReader = hass.data[DOMAIN][config_entry.entry_id]
    except KeyError:
        _LOGGER.error(
            "%s: can not init sensors: failed to get the serial reader object",
            config_entry.title,
        )
        return

    # Flag for experimental counters which have slightly different tags.
    is_pilot: bool = serial_reader.device_identification[DID_TYPE_CODE] in EXPERIMENTAL_DEVICES

    # Init sensors
    sensors = []
    if config_entry.data.get(SETUP_TICMODE) == TICMODE_STANDARD:
        # standard mode
        sensors = [
            ADSSensor(
                config_title=config_entry.title,
                tag="ADSC",
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            LinkyTICStringSensor(
                tag="VTIC",
                name="Version de la TIC",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
            ),
            DateEtHeureSensor(
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            LinkyTICStringSensor(
                tag="NGTF",
                name="Nom du calendrier tarifaire fournisseur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
            ),
            LinkyTICStringSensor(
                tag="LTARF",
                name="Libellé tarif fournisseur en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
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
            CurrentSensor(
                tag="IRMS1",
                name="Courant efficace, phase 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            VoltageSensor(
                tag="URMS1",
                name="Tension efficace, phase 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            ApparentPowerSensor(
                tag="PREF",
                name="Puissance app. de référence",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                register_callback=True,
                category=EntityCategory.DIAGNOSTIC,
                conversion_function=(lambda x: x * 1000),  # kVA conversion
            ),
            ApparentPowerSensor(
                tag="PCOUP",
                name="Puissance app. de coupure",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                register_callback=True,
                category=EntityCategory.DIAGNOSTIC,
                conversion_function=(lambda x: x * 1000),  # kVA conversion
            ),
            ApparentPowerSensor(
                tag="SINST1" if is_pilot else "SINSTS",
                name="Puissance app. instantanée soutirée",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            ApparentPowerSensor(
                tag="SMAXN" if is_pilot else "SMAXSN",
                name="Puissance app. max. soutirée n",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                register_callback=True,
            ),
            ApparentPowerSensor(
                tag="SMAXN-1" if is_pilot else "SMAXSN-1",
                name="Puissance app. max. soutirée n-1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                register_callback=True,
            ),
            PowerSensor(
                tag="CCASN",
                name="Point n de la courbe de charge active soutirée",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            PowerSensor(
                tag="CCASN-1",
                name="Point n-1 de la courbe de charge active soutirée",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            VoltageSensor(
                tag="UMOY1",
                name="Tension moy. ph. 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                state_class=SensorStateClass.MEASUREMENT,  # Is this a curent value?
                register_callback=True,
            ),
            LinkyTICStringSensor(
                tag="DPM1",
                name="Début pointe mobile 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-start",
            ),
            LinkyTICStringSensor(
                tag="FPM1",
                name="Fin pointe mobile 1",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-end",
            ),
            LinkyTICStringSensor(
                tag="DPM2",
                name="Début pointe mobile 2",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-start",
            ),
            LinkyTICStringSensor(
                tag="FPM2",
                name="Fin pointe mobile 2",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-end",
            ),
            LinkyTICStringSensor(
                tag="DPM3",
                name="Début pointe mobile 3",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-start",
            ),
            LinkyTICStringSensor(
                tag="FPM3",
                name="Fin pointe mobile 3",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-end",
            ),
            LinkyTICStringSensor(
                tag="MSG1",
                name="Message court",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:message-text-outline",
            ),
            LinkyTICStringSensor(
                tag="MSG2",
                name="Message Ultra court",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:message-text-outline",
            ),
            LinkyTICStringSensor(
                tag="PRM",
                name="PRM",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
            ),
            LinkyTICStringSensor(
                tag="RELAIS",
                name="Relais",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:electric-switch",
            ),
            LinkyTICStringSensor(
                tag="NTARF",
                name="Numéro de l’index tarifaire en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
            ),
            LinkyTICStringSensor(
                tag="NJOURF",
                name="Numéro du jour en cours calendrier fournisseur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-month-outline",
            ),
            LinkyTICStringSensor(
                tag="NJOURF+1",
                name="Numéro du prochain jour calendrier fournisseur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-month-outline",
            ),
            ProfilDuProchainJourCalendrierFournisseurSensor(
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            LinkyTICStringSensor(
                tag="PPOINTE",
                name="Profil du prochain jour de pointe",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-month-outline",
            ),
            LinkyTICStringSensor(
                tag="STGE",
                name="Registre de statuts",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:list-status",
            ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut contact sec",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:electric-switch",
            #     field=StatusRegister.CONTACT_SEC,
            # ),
            LinkyTICStatusRegisterSensor(
                name="Statut organe de coupure",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:connection",
                field=StatusRegister.ORGANE_DE_COUPURE,
            ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut état du cache-bornes distributeur",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:toy-brick-outline",
            #     field=StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR,
            # ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut surtension sur une des phases",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:flash-alert",
            #     field=StatusRegister.SURTENSION_SUR_UNE_DES_PHASES,
            # ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut dépassement de la puissance de référence",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:flash-alert",
            #     field=StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE,
            # ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut producteur/consommateur",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:transmission-tower",
            #     field=StatusRegister.PRODUCTEUR_CONSOMMATEUR,
            # ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut sens de l’énergie active",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:transmission-tower",
            #     field=StatusRegister.SENS_ENERGIE_ACTIVE,
            # ),
            LinkyTICStatusRegisterSensor(
                name="Statut tarif contrat fourniture",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                field=StatusRegister.TARIF_CONTRAT_FOURNITURE,
            ),
            LinkyTICStatusRegisterSensor(
                name="Statut tarif contrat distributeur",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                field=StatusRegister.TARIF_CONTRAT_DISTRIBUTEUR,
            ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut mode dégradée de l'horloge",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:clock-alert-outline",
            #     field=StatusRegister.MODE_DEGRADE_HORLOGE,
            # ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut sortie télé-information",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:tag",
            #     field=StatusRegister.MODE_TIC,
            # ),
            LinkyTICStatusRegisterSensor(
                name="Statut sortie communication Euridis",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                field=StatusRegister.ETAT_SORTIE_COMMUNICATION_EURIDIS,
            ),
            LinkyTICStatusRegisterSensor(
                name="Statut CPL",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:tag",
                field=StatusRegister.STATUS_CPL,
            ),
            # LinkyTICStatusRegisterSensor(
            #     name="Statut synchronisation CPL",
            #     config_title=config_entry.title,
            #     config_uniq_id=config_entry.entry_id,
            #     serial_reader=serial_reader,
            #     icon="mdi:sync",
            #     field=StatusRegister.SYNCHRO_CPL,
            # ),
            LinkyTICStatusRegisterSensor(
                name="Statut couleur du jour tempo",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
                field=StatusRegister.COULEUR_JOUR_CONTRAT_TEMPO,
            ),
            LinkyTICStatusRegisterSensor(
                name="Statut couleur du lendemain tempo",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
                field=StatusRegister.COULEUR_LENDEMAIN_CONTRAT_TEMPO,
            ),
            LinkyTICStatusRegisterSensor(
                name="Statut préavis pointes mobiles",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-alert-outline",
                field=StatusRegister.PREAVIS_POINTES_MOBILES,
            ),
            LinkyTICStatusRegisterSensor(
                name="Statut pointe mobile",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:progress-clock",
                field=StatusRegister.POINTE_MOBILE,
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
                ApparentPowerSensor(
                    tag="SINSTI",
                    name="Puissance app. instantanée injectée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXIN",
                    name="Puissance app. max. injectée n",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXIN-1",
                    name="Puissance app. max. injectée n-1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                PowerSensor(
                    tag="CCAIN",
                    name="Point n de la courbe de charge active injectée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
            sensors.append(
                PowerSensor(
                    tag="CCAIN-1",
                    name="Point n-1 de la courbe de charge active injectée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    icon="mdi:transmission-tower-import",
                )
            )
        # Add three-phase specific sensors
        if bool(config_entry.data.get(SETUP_THREEPHASE)):
            sensors.append(
                CurrentSensor(
                    tag="IRMS2",
                    name="Courant efficace, phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IRMS3",
                    name="Courant efficace, phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                VoltageSensor(
                    tag="URMS2",
                    name="Tension efficace, phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                VoltageSensor(
                    tag="URMS3",
                    name="Tension efficace, phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SINSTS1",
                    name="Puissance app. instantanée soutirée phase 1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SINSTS2",
                    name="Puissance app. instantanée soutirée phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SINSTS3",
                    name="Puissance app. instantanée soutirée phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXSN1",
                    name="Puissance app max. soutirée n phase 1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXSN2",
                    name="Puissance app max. soutirée n phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXSN3",
                    name="Puissance app max. soutirée n phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXSN1-1",
                    name="Puissance app max. soutirée n-1 phase 1",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXSN2-1",
                    name="Puissance app max. soutirée n-1 phase 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                ApparentPowerSensor(
                    tag="SMAXSN3-1",
                    name="Puissance app max. soutirée n-1 phase 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                VoltageSensor(
                    tag="UMOY2",
                    name="Tension moy. ph. 2",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                VoltageSensor(
                    tag="UMOY3",
                    name="Tension moy. ph. 3",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )

    else:
        # historic mode
        sensors = [
            ADSSensor(
                config_title=config_entry.title,
                tag="ADCO",
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
            ),
            LinkyTICStringSensor(
                tag="OPTARIF",
                name="Option tarifaire choisie",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:cash-check",
                category=EntityCategory.DIAGNOSTIC,
            ),
            CurrentSensor(
                tag="ISOUSC",
                name="Intensité souscrite",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                category=EntityCategory.DIAGNOSTIC,
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
                name="Index option EJP - Heures Normal" + "es",  # workaround for codespell in HA pre commit hook
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
            LinkyTICStringSensor(
                tag="PTEC",
                name="Période Tarifaire en cours",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:calendar-expand-horizontal",
            ),
            LinkyTICStringSensor(
                tag="DEMAIN",
                name="Couleur du lendemain",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:palette",
            ),
            ApparentPowerSensor(
                tag="PAPP",
                name="Puissance apparente",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                state_class=SensorStateClass.MEASUREMENT,
                register_callback=True,
            ),
            LinkyTICStringSensor(
                tag="HHPHC",
                name="Horaire Heures Pleines Heures Creuses",
                config_title=config_entry.title,
                config_uniq_id=config_entry.entry_id,
                serial_reader=serial_reader,
                icon="mdi:clock-outline",
                enabled_by_default=False,
            ),
            LinkyTICStringSensor(
                tag="MOTDETAT",
                name="Mo" + "t d'état du compteur",  # workaround for codespell in HA pre commit hook
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
                CurrentSensor(
                    tag="IINST1",
                    name="Intensité Instantanée (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IINST2",
                    name="Intensité Instantanée (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IINST3",
                    name="Intensité Instantanée (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IMAX1",
                    name="Intensité maximale appelée (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IMAX2",
                    name="Intensité maximale appelée (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IMAX3",
                    name="Intensité maximale appelée (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                )
            )
            sensors.append(
                PowerSensor(  # documentation says unit is Watt but description talks about VoltAmp :/
                    tag="PMAX",
                    name="Puissance maximale triphasée atteinte (jour n-1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                )
            )
            sensors.append(
                LinkyTICStringSensor(
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
                CurrentSensor(
                    tag="ADIR1",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 1)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="ADIR2",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 2)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="ADIR3",
                    name="Avertissement de Dépassement d'intensité de réglage (phase 3)",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    register_callback=True,
                )
            )
            _LOGGER.info("Adding %d sensors for the three phase historic mode", len(sensors))
        else:
            # single phase - concat specific sensors
            sensors.append(
                CurrentSensor(
                    tag="IINST",
                    name="Intensité Instantanée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="ADPS",
                    name="Avertissement de Dépassement De Puissance Souscrite",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                    state_class=SensorStateClass.MEASUREMENT,
                    register_callback=True,
                )
            )
            sensors.append(
                CurrentSensor(
                    tag="IMAX",
                    name="Intensité maximale appelée",
                    config_title=config_entry.title,
                    config_uniq_id=config_entry.entry_id,
                    serial_reader=serial_reader,
                )
            )
            _LOGGER.info("Adding %d sensors for the single phase historic mode", len(sensors))
    # Add the entities to HA
    if len(sensors) > 0:
        async_add_entities(sensors, True)


T = TypeVar("T")


class LinkyTICSensor(LinkyTICEntity, SensorEntity, Generic[T]):
    """Base class for all Linky TIC sensor entities."""

    _attr_should_poll = True
    _last_value: T | None

    def __init__(self, tag: str, config_title: str, reader: LinkyTICReader) -> None:
        """Init sensor entity."""
        super().__init__(reader)
        self._last_value = None
        self._tag = tag
        self._config_title = config_title

    @property
    def native_value(self) -> T | None:
        """Value of the sensor."""
        return self._last_value

    def _update(self) -> tuple[Optional[str], Optional[str]]:
        """Get value and/or timestamp from cached data. Responsible for updating sensor availability."""
        value, timestamp = self._serial_controller.get_values(self._tag)
        _LOGGER.debug(
            "%s: retrieved %s value from serial controller: (%s, %s)",
            self._config_title,
            self._tag,
            value,
            timestamp
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


class ADSSensor(LinkyTICSensor[str]):
    """Ad resse du compteur entity."""

    # ADSSensor is a subclass and not an instance of StringSensor because it binds to two tags.

    # Generic properties
    #   https://developers.home-assistant.io/docs/core/entity#generic-properties

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "A" + "dress" + "e du compteur"  # workaround for codespell in HA pre commit hook
    _attr_icon = "mdi:tag"

    def __init__(self, config_title: str, tag: str, config_uniq_id: str, serial_reader: LinkyTICReader) -> None:
        """Initialize an ADCO/ADSC Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag)
        super().__init__(tag, config_title, serial_reader)
        # Generic entity properties
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_adco"
        self._extra: dict[str, str] = {}

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Get HA sensor extra attributes."""
        return self._extra

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()

        if not value:
            return

        # Set this sensor extra attributes
        did = self._serial_controller.device_identification
        self._extra = {
            "constructeur": f"{did[DID_CONSTRUCTOR] or 'Inconnu'} ({did[DID_CONSTRUCTOR_CODE]})",
            "année de construction": f"20{did[DID_YEAR]}",
            "type de l'appareil": f"{did[DID_TYPE] or 'Inconnu'} ({did[DID_TYPE_CODE]})",
            "matricule de l'appareil": did[DID_REGNUMBER] or "Inconnu",
        }
        # Save value
        self._last_value = value


class LinkyTICStringSensor(LinkyTICSensor[str]):
    """Common class for text sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
        super().__init__(tag, config_title, serial_reader)

        # Generic Entity properties
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{tag.lower()}"
        if icon:
            self._attr_icon = icon
        if category:
            self._attr_entity_category = category
        self._attr_entity_registry_enabled_default = enabled_by_default

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()
        if not value:
            return
        self._last_value = " ".join(value.split())


class RegularIntSensor(LinkyTICSensor[int]):
    """Common class for int sensors."""

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
        conversion_function: Callable[[int], int] | None = None,
    ) -> None:
        """Initialize a Regular Int Sensor."""
        _LOGGER.debug("%s: initializing %s sensor", config_title, tag.upper())
        super().__init__(tag, config_title, serial_reader)
        self._attr_name = name

        if register_callback:
            self._serial_controller.register_push_notif(self._tag, self.update_notification)
        # Generic Entity properties
        if category:
            self._attr_entity_category = category
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

        self._conversion_function = conversion_function

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        value, _ = self._update()
        if not value:
            return
        try:
            value_int = int(value)
        except ValueError:
            return
        self._last_value = self._conversion_function(value_int) if self._conversion_function else value_int

    def update_notification(self, realtime_option: bool) -> None:
        """Receive a notification from the serial reader when our tag has been read on the wire."""
        # Realtime off
        if not realtime_option:
            _LOGGER.debug(
                "received a push notification for new %s data but user has not activated real time: skipping",
                self._tag,
            )
            if not self._attr_should_poll:
                self._attr_should_poll = True  # realtime option disable, HA should poll us
            return
        # Realtime on
        _LOGGER.debug(
            "received a push notification for new %s data and user has activated real time: scheduling ha update",
            self._tag,
        )
        if self._attr_should_poll:
            self._attr_should_poll = (
                False  # now that user has activated realtime, we will push data, no need for HA to poll us
            )
        self.schedule_update_ha_state(force_refresh=True)


class EnergyIndexSensor(RegularIntSensor):
    """Common class for energy index counters, in Watt-hours."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING


class VoltageSensor(RegularIntSensor):
    """Common class for voltage sensors, in Volts."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT


class CurrentSensor(RegularIntSensor):
    """Common class for electric current sensors, in Amperes."""

    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE


class PowerSensor(RegularIntSensor):
    """Common class for real power sensors, in Watts."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT


class ApparentPowerSensor(RegularIntSensor):
    """Common class for apparent power sensors, in Volt-Amperes."""

    _attr_device_class = SensorDeviceClass.APPARENT_POWER
    _attr_native_unit_of_measurement = UnitOfApparentPower.VOLT_AMPERE


class PEJPSensor(LinkyTICStringSensor):
    """Préavis Début EJP (30 min) sensor."""

    #
    # This sensor could be improved I think (minutes as integer), but I do not have it to check and test its values
    # Leaving it as it is to facilitate future modifications
    #
    _attr_icon = "mdi:clock-start"

    def __init__(self, config_title: str, config_uniq_id: str, serial_reader: LinkyTICReader) -> None:
        """Initialize a PEJP sensor."""
        _LOGGER.debug("%s: initializing PEJP sensor", config_title)
        super().__init__(
            tag="PEJP",
            name="Préavis Début EJP",
            config_title=config_title,
            config_uniq_id=config_uniq_id,
            serial_reader=serial_reader,
        )

        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{self._tag.lower()}"


class DateEtHeureSensor(LinkyTICStringSensor):
    """Date et heure courante sensor."""

    _attr_icon = "mdi:clock-outline"

    def __init__(
        self,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
    ) -> None:
        """Initialize a Date et heure sensor."""
        _LOGGER.debug("%s: initializing Date et heure courante sensor", config_title)
        super().__init__(
            tag="DATE",
            name="Date et heure courante",
            config_title=config_title,
            config_uniq_id=config_uniq_id,
            serial_reader=serial_reader,
        )

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        _, timestamp = self._update()

        if not timestamp:
            return
        # Save value
        saison = ""
        try:
            if timestamp[0:1] == "E":
                saison = " (Eté)"
            elif timestamp[0:1] == "H":
                saison = " (Hiver)"
            self._last_value = (
                timestamp[5:7]
                + "/"
                + timestamp[3:5]
                + "/"
                + timestamp[1:3]
                + " "
                + timestamp[7:9]
                + ":"
                + timestamp[9:11]
                + saison
            )
        except IndexError:
            return


class ProfilDuProchainJourCalendrierFournisseurSensor(LinkyTICStringSensor):
    """Profil du prochain jour du calendrier fournisseur sensor."""

    _attr_icon = "mdi:calendar-month-outline"

    def __init__(
        self,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        category: EntityCategory | None = None,
    ) -> None:
        """Initialize a Profil du prochain jour du calendrier fournisseur sensor."""
        _LOGGER.debug("%s: initializing Date et heure courante sensor", config_title)
        super().__init__(
            tag="PJOURF+1",
            name="Profil du prochain jour calendrier fournisseur",
            config_title=config_title,
            config_uniq_id=config_uniq_id,
            serial_reader=serial_reader,
        )

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()
        if not value:
            return
        self._last_value = value.replace("NONUTILE", "").strip()


class LinkyTICStatusRegisterSensor(LinkyTICStringSensor):
    """Data from status register."""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(
        self,
        name: str,
        config_title: str,
        config_uniq_id: str,
        serial_reader: LinkyTICReader,
        field: StatusRegister,
        enabled_by_default: bool = True,
        icon: str | None = None,
    ) -> None:
        """Initialize a status register data sensor."""
        _LOGGER.debug("%s: initializing a status register data sensor", config_title)
        self._field = field
        super().__init__(
            tag="STGE",
            name=name,
            config_title=config_title,
            config_uniq_id=config_uniq_id,
            serial_reader=serial_reader,
            icon=icon,
            enabled_by_default=enabled_by_default,
        )
        self._attr_unique_id = f"{DOMAIN}_{config_uniq_id}_{field.name.lower()}"  # Breaking changes here.
        # For SensorDeviceClass.ENUM, _attr_options contains all the possible values for the sensor.
        self._attr_options = list(cast(dict[int, str], field.value.options).values())

    @callback
    def update(self):
        """Update the value of the sensor from the thread object memory cache."""
        # Get last seen value from controller
        value, _ = self._update()

        if not value:
            return

        try:
            self._last_value = cast(str, self._field.value.get_status(value))
        except IndexError:
            pass  # Failsafe, value is unchanged.
