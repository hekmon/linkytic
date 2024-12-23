"""Definition of status register fields and handlers."""

from enum import Enum
from typing import NamedTuple


class StatusRegisterEnumValueType(NamedTuple):
    """Represent a field in the status register.
    lsb is the position of the least significant bit of the field in the status register.
    len if the length in bit of the field (default 1 bit).
    options is a dictionary mapping field int value to string. If no options, the value is treated as a boolean.
    """

    lsb: int
    len: int = 1
    options: dict[int, str] | None = None

    def get_status(self, register: str) -> str | bool:
        try:
            int_register = int(register, base=16)
        except TypeError:
            return False
        val = (int_register >> self.lsb) & ((1 << self.len) - 1)

        if self.options is None:
            return bool(val)

        return self.options[val]  # Let IndexError propagate if val is unknown.


organe_coupure = {
    0: "Fermé",
    1: "Ouvert sur surpuissance",
    2: "Ouvert sur surtension",
    3: "Ouvert sur délestage",
    4: "Ouvert sur ordre CPL ou Euridis",
    5: "Ouvert sur surchauffe (>Imax)",
    6: "Ouvert sur surchauffe (<Imax)",
}

tarif_en_cours = {i: f"Index {i+1}" for i in range(0, 10)}

etat_euridis = {
    0: "Désactivée",
    1: "Activée sans sécurité",
    2: "Valeur non valide",  # codespell:ignore
    3: "Activée avec sécurité",
}

statut_cpl = {
    0: "New/Unlock",
    1: "New/Lock",
    2: "Registered",
    3: "Valeur non valide",  # codespell:ignore
}

tempo_color = {
    0: "Pas d'annonce",
    1: "Bleu",
    2: "Blanc",
    3: "Rouge",  # codespell:ignore
}

preavis_pm = {
    0: "Pas de préavis en cours",
    1: "Préavis PM1 en cours",
    2: "Préavis PM2 en cours",
    3: "Préavis PM3 en cours",
}

pointe_mobile = {
    0: "Pas de pointe mobile",
    1: "PM 1 en cours",
    2: "PM 2 en cours",
    3: "PM 3 en cours",
}


class StatusRegister(Enum):
    """Field provided by status register.
    The value corresponds to the (position, bits).
    """

    CONTACT_SEC = StatusRegisterEnumValueType(0)
    ORGANE_DE_COUPURE = StatusRegisterEnumValueType(1, 3, organe_coupure)
    ETAT_DU_CACHE_BORNE_DISTRIBUTEUR = StatusRegisterEnumValueType(4)
    # bit 5 is reserved
    SURTENSION_SUR_UNE_DES_PHASES = StatusRegisterEnumValueType(6)
    DEPASSEMENT_PUISSANCE_REFERENCE = StatusRegisterEnumValueType(7)
    PRODUCTEUR_CONSOMMATEUR = StatusRegisterEnumValueType(8)
    SENS_ENERGIE_ACTIVE = StatusRegisterEnumValueType(9)
    TARIF_CONTRAT_FOURNITURE = StatusRegisterEnumValueType(10, 4, tarif_en_cours)
    TARIF_CONTRAT_DISTRIBUTEUR = StatusRegisterEnumValueType(14, 2, tarif_en_cours)
    MODE_DEGRADE_HORLOGE = StatusRegisterEnumValueType(16)
    MODE_TIC = StatusRegisterEnumValueType(17)
    # bit 18 is reserved
    ETAT_SORTIE_COMMUNICATION_EURIDIS = StatusRegisterEnumValueType(19, 2, etat_euridis)
    STATUS_CPL = StatusRegisterEnumValueType(21, 2, statut_cpl)
    SYNCHRO_CPL = StatusRegisterEnumValueType(23)
    COULEUR_JOUR_CONTRAT_TEMPO = StatusRegisterEnumValueType(24, 2, tempo_color)
    COULEUR_LENDEMAIN_CONTRAT_TEMPO = StatusRegisterEnumValueType(26, 2, tempo_color)
    PREAVIS_POINTES_MOBILES = StatusRegisterEnumValueType(28, 2, preavis_pm)
    POINTE_MOBILE = StatusRegisterEnumValueType(30, 2, pointe_mobile)
