"""Contributi previdenziali a carico del lavoratore dipendente."""

from __future__ import annotations

# Aliquota IVS a carico del dipendente nel settore privato: 9,19% dell'imponibile previdenziale.
ALIQUOTA_INPS_DIPENDENTE = 0.0919

# SEMPLIFICAZIONE: aliquota unica su tutta la RAL.
# Nella realta' esiste un massimale contributivo annuo (circa 120.000 euro, rivalutato ogni anno)
# oltre il quale i contributi IVS non sono piu' dovuti, e un'aliquota aggiuntiva dell'1% sulla
# quota di retribuzione eccedente la prima fascia di retribuzione pensionabile. Entrambi sono
# fuori dal perimetro del prototipo: per RAL molto alte i contributi risultano sovrastimati.


def contributi_inps(imponibile_previdenziale: float) -> float:
    """Contributi INPS a carico del dipendente sull'imponibile previdenziale (= RAL)."""
    if imponibile_previdenziale <= 0:
        return 0.0
    return imponibile_previdenziale * ALIQUOTA_INPS_DIPENDENTE
