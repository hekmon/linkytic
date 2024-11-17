"""Constants for the linkytic integration."""

from termios import error
from serial import SerialException, SEVENBITS, PARITY_EVEN, STOPBITS_ONE

DOMAIN = "linkytic"

# Some termios exceptions are uncaught by pyserial
LINKY_IO_ERRORS = (SerialException, error)

# Config Flow

TICMODE_HISTORIC = "hist"
TICMODE_HISTORIC_LABEL = "Historique"
TICMODE_STANDARD = "std"
TICMODE_STANDARD_LABEL = "Standard"

SETUP_SERIAL = "serial_device"
SETUP_SERIAL_DEFAULT = "/dev/ttyUSB0"
SETUP_TICMODE = "tic_mode"
SETUP_PRODUCER = "producer_mode"
SETUP_PRODUCER_DEFAULT = False
SETUP_THREEPHASE = "three_phase"
SETUP_THREEPHASE_DEFAULT = False

OPTIONS_REALTIME = "real_time"

# Protocol configuration
# #  https://www.enedis.fr/media/2035/download

BYTESIZE = SEVENBITS
PARITY = PARITY_EVEN
STOPBITS = STOPBITS_ONE

MODE_STANDARD_BAUD_RATE = 9600
MODE_STANDARD_FIELD_SEPARATOR = b"\x09"

MODE_HISTORIC_BAUD_RATE = 1200
MODE_HISTORIC_FIELD_SEPARATOR = b"\x20"

LINE_END = b"\r\n"
FRAME_END = b"\r\x03\x02\n"

SHORT_FRAME_DETECTION_TAGS = ["ADIR1", "ADIR2", "ADIR3"]
SHORT_FRAME_FORCED_UPDATE_TAGS = [
    "ADIR1",
    "ADIR2",
    "ADIR3",
    "IINST1",
    "IINST2",
    "IINST3",
]


# Device identification

DID_CONSTRUCTOR = "constructor"
DID_CONSTRUCTOR_CODE = "constructor_code"
DID_YEAR = "year"
DID_TYPE = "device_type"
DID_TYPE_CODE = "device_type_code"
DID_REGNUMBER = "registration_number"

DID_DEFAULT_MANUFACTURER = "ENEDIS"
DID_DEFAULT_MODEL = "Compteur communiquant Linky"
DID_DEFAULT_NAME = "Linky"

DID_CONNECTION_TYPE = "serial"

# #  https://euridis.org/wp-content/uploads/IdentifiantsEuridisListeCCTTV304A_143027.pdf  (V3.04A du 27/03/2019)
CONSTRUCTORS_CODES = {
    "01": "CROUZET / MONETEL",
    "02": "SAGEM / SAGEMCOM",
    "03": "SCHLUMBERGER / ACTARIS / ITRON",
    "04": "LANDIS ET GYR / SIEMENS METERING / LANDIS+GYR",
    "05": "SAUTER / STEPPER ENERGIE France / ZELLWEGER",
    "06": "ITRON",
    "07": "MAEC",
    "08": "MATRA-CHAUVIN ARNOUX / ENERDIS",
    "09": "FAURE-HERMAN",
    "10": "SEVME / SIS",
    "11": "MAGNOL / ELSTER / HONEYWELL",
    "12": "GAZ THERMIQUE",
    # 13 Non attribué
    "14": "GHIELMETTI / DIALOG E.S. / MICRONIQUE",
    "15": "MECELEC",
    "16": "LEGRAND / BACO",
    "17": "SERD-SCHLUMBERGER",
    "18": "SCHNEIDER / MERLIN GERIN / GARDY",
    "19": "GENERAL ELECTRIC / POWER CONTROL",
    "20": "NUOVO PIGNONE / DRESSER",
    "21": "SCLE",
    "22": "EDF",
    "23": "GDF / GDF-SUEZ",
    "24": "HAGER – GENERAL ELECTRIC",
    "25": "DELTA-DORE",
    "26": "RIZ",
    "27": "ISKRAEMECO",
    "28": "GMT",
    "29": "ANALOG DEVICE",
    "30": "MICHAUD",
    "31": "HEXING ELECTRICAL CO. Ltd",
    "32": "SIAME",
    "33": "LARSEN & TOUBRO Limited",
    "34": "ELSTER / HONEYWELL",
    "35": "ELECTRONIC AFZAR AZMA",
    "36": "ADVANCED ELECTRONIC COMPANY Ldt",  # is actually COMPA G NY but codespell does not support inline ignore... https://github.com/codespell-project/codespell/issues/1212
    "37": "AEM",
    "38": "ZHEJIANG CHINT INSTRUMENT & METER CO. Ldt",
    "39": "ZIV",
    # 40 à 69 Non attribué
    "70": "LANDIS et GYR (export ou régie)",
    "71": "STEPPER ENERGIE France (export ou régie)",
    # 72 à 80 Non attribué
    "81": "SAGEM / SAGEMCOM",  # outre-million
    "82": "LANDIS ET GYR / SIEMENS METERING / LANDIS+GYR",  # outre-million
    "83": "ELSTER / HONEYWELL",  # outre-million
    "84": "SAGEM / SAGEMCOM",  # outre-million
    "85": "ITRON",  # outre-million
    # 86 à 89 Non attribué (réservé pour l’outre-million)
    # 90 à 99 Non attribué
}

DEVICE_TYPES = {
    # ---8<---
    ## res/landis_zcd126_02_siemens.pdf // but what about res/sagem_s1000_guide_technique.pdf ?
    "22": "Compteur monophasé 90 A ZCD126 - 175 Hz taux normal",
    "23": "Compteur monophasé 90 A ZCD126 - 175 Hz demi taux",
    # ---8<---
    ## res/notice-compteur-edf-monophase-landis-gyr-l16c6.pdf
    "25": "Compteur monophasé 90 A L16C6 - Simple tarif",
    # ---8<---
    ## res/sagem_c2000_guide_technique.pdf // but what about res/
    "26": "Compteur SAGEM C2000-4 – CE24MM10",
    "27": "Compteur SAGEM C2000-4 – CE24MM12",
    # ---8<---
    ## res/notice-compteur-edf-monophase-landis-gyr-l16c6.pdf
    "28": "Compteur monophasé 90 A L16C6 - 175 Hz taux normal",
    "29": "Compteur monophasé 90 A L16C6 - 175 Hz demi-taux",
    # ---8<---
    ## res/landis_zmd126_02_user.pdf
    "30": "Compteur Triphasé 60 A ZMD126 (L18C5) - 175 Hz taux normal",
    "31": "Compteur Triphasé 60 A ZMD126 (L18C5) - 175 Hz demi taux",
    # ---8<---
    ## res/Enedis-NOI-CPT_54E.pdf
    "61": "Compteur monophasé 60 A généralisation Linky G3 - arrivée puissance haute",
    "62": "Compteur monophasé 90 A généralisation Linky G1 - arrivée puissance basse",
    "63": "Compteur triphasé 60 A généralisation Linky G1 - arrivée puissance basse",
    "64": "Compteur monophasé 60 A généralisation Linky G3 - arrivée puissance basse",
    "65": "Compteur monophasé 90A LINKY expérimentation CPL G3",
    "66": "Module du compteur modulaire généralisation",
    "67": "Compteur monophasé 90A LINKY - pilote G1 - arrivée basse",
    "68": "Compteur triphasé 60A LINKY - pilote G1 - arrivée basse",
    "70": "Compteur monophasé Linky 60 A mise au point G3",
    "71": "Compteur triphasé Linky 60 A mise au point G3",
    "75": "Compteur monophasé 90 A généralisation Linky G3 - arrivée puissance basse",
    "76": "Compteur triphasé 60 A généralisation Linky G3 - arrivée puissance basse",
}

EXPERIMENTAL_DEVICES = ("67", "68")
