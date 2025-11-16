"""Test the status register decoding."""

from custom_components.linkytic.status_register import (
    StatusRegister,
    etat_euridis,
    organe_coupure,
    pointe_mobile,
    preavis_pm,
    statut_cpl,
    tarif_en_cours,
    tempo_color,
)


def test_parse():
    STGE = "013AC501"

    EXPECTED = {
        StatusRegister.CONTACT_SEC: 1,
        StatusRegister.ORGANE_DE_COUPURE: organe_coupure[0],
        StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR: 0,
        StatusRegister.SURTENSION_SUR_UNE_DES_PHASES: 0,
        StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE: 0,
        StatusRegister.PRODUCTEUR_CONSOMMATEUR: 1,
        StatusRegister.SENS_ENERGIE_ACTIVE: 0,
        StatusRegister.TARIF_CONTRAT_FOURNITURE: tarif_en_cours[1],
        StatusRegister.TARIF_CONTRAT_DISTRIBUTEUR: tarif_en_cours[3],
        StatusRegister.MODE_DEGRADE_HORLOGE: 0,
        StatusRegister.MODE_TIC: 1,
        StatusRegister.ETAT_SORTIE_COMMUNICATION_EURIDIS: etat_euridis[3],
        StatusRegister.STATUS_CPL: statut_cpl[1],
        StatusRegister.SYNCHRO_CPL: 0,
        StatusRegister.COULEUR_JOUR_CONTRAT_TEMPO: tempo_color[1],
        StatusRegister.COULEUR_LENDEMAIN_CONTRAT_TEMPO: tempo_color[0],
        StatusRegister.PREAVIS_POINTES_MOBILES: preavis_pm[0],
        StatusRegister.POINTE_MOBILE: pointe_mobile[0],
    }

    for element in StatusRegister:
        assert EXPECTED[element] == element.value.get_status(STGE)

    STGE = "003AC000"

    EXPECTED = {
        StatusRegister.CONTACT_SEC: 0,
        StatusRegister.ORGANE_DE_COUPURE: organe_coupure[0],
        StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR: 0,
        StatusRegister.SURTENSION_SUR_UNE_DES_PHASES: 0,
        StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE: 0,
        StatusRegister.PRODUCTEUR_CONSOMMATEUR: 0,
        StatusRegister.SENS_ENERGIE_ACTIVE: 0,
        StatusRegister.TARIF_CONTRAT_FOURNITURE: tarif_en_cours[0],
        StatusRegister.TARIF_CONTRAT_DISTRIBUTEUR: tarif_en_cours[3],
        StatusRegister.MODE_DEGRADE_HORLOGE: 0,
        StatusRegister.MODE_TIC: 1,
        StatusRegister.ETAT_SORTIE_COMMUNICATION_EURIDIS: etat_euridis[3],
        StatusRegister.STATUS_CPL: statut_cpl[1],
        StatusRegister.SYNCHRO_CPL: 0,
        StatusRegister.COULEUR_JOUR_CONTRAT_TEMPO: tempo_color[0],
        StatusRegister.COULEUR_LENDEMAIN_CONTRAT_TEMPO: tempo_color[0],
        StatusRegister.PREAVIS_POINTES_MOBILES: preavis_pm[0],
        StatusRegister.POINTE_MOBILE: pointe_mobile[0],
    }

    for element in StatusRegister:
        assert EXPECTED[element] == element.value.get_status(STGE)
    
    STGE = "FFDFE7FD"

    EXPECTED = {
        StatusRegister.CONTACT_SEC: 1,
        StatusRegister.ORGANE_DE_COUPURE: organe_coupure[6],
        StatusRegister.ETAT_DU_CACHE_BORNE_DISTRIBUTEUR: 1,
        StatusRegister.SURTENSION_SUR_UNE_DES_PHASES: 1,
        StatusRegister.DEPASSEMENT_PUISSANCE_REFERENCE: 1,
        StatusRegister.PRODUCTEUR_CONSOMMATEUR: 1,
        StatusRegister.SENS_ENERGIE_ACTIVE: 1,
        StatusRegister.TARIF_CONTRAT_FOURNITURE: tarif_en_cours[9],
        StatusRegister.TARIF_CONTRAT_DISTRIBUTEUR: tarif_en_cours[3],
        StatusRegister.MODE_DEGRADE_HORLOGE: 1,
        StatusRegister.MODE_TIC: 1,
        StatusRegister.ETAT_SORTIE_COMMUNICATION_EURIDIS: etat_euridis[3],
        StatusRegister.STATUS_CPL: statut_cpl[2],
        StatusRegister.SYNCHRO_CPL: 1,
        StatusRegister.COULEUR_JOUR_CONTRAT_TEMPO: tempo_color[3],
        StatusRegister.COULEUR_LENDEMAIN_CONTRAT_TEMPO: tempo_color[3],
        StatusRegister.PREAVIS_POINTES_MOBILES: preavis_pm[3],
        StatusRegister.POINTE_MOBILE: pointe_mobile[3],
    }

    for element in StatusRegister:
        assert EXPECTED[element] == element.value.get_status(STGE)

def parse_stge(stge: str):
    for element in StatusRegister:
        print(element.name, element.value.get_status(stge))

if __name__ == "__main__":
    # Parse STGE, call this file as a module (python -m tests.test_status_register <STGE>)
    import sys
    if len(sys.argv) <= 1:
        print("No stge to parse.")
        sys.exit(1)
    parse_stge(sys.argv[1])