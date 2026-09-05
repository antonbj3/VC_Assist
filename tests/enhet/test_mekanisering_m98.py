# -*- coding: utf-8 -*-
"""M-98: den sjätte ordlistan, och grinden som letar efter dem.

M-94 fynd 1 och 4, och M-95 som lagade dem, handlade om EN ordlista som bar
två storheter. M-94:s sista LIMITS-punkt sade rent ut att konsumenterna inte
var uttömt prövade. Den här filen prövar färdigt, och den prövar två saker:

  1. `harness/oga.py` bar en EGEN KOPIA av listan (`NEKANDE_OGONORD`) och
     ställde samma fråga på fel storhet: *bär MENINGEN något nekande ord?*
     Mätt 2026-09-05: "Ogat sa PASS och inget fel uppstod." gav `[]`.
     Nekandet hörde till felen; domen stod kvar oemotsagd.

  2. Felklassen är den fjärde av samma sort, och en femte kommer annars.
     `tests/enhet/test_ordlistegrind.py` mekaniserar frågan: vilka ordlistor
     avgör en dom, och ställs frågan på rätt storhet?

BÅDA riktningarna prövas. En skärpning som bara prövas i den fällande
riktningen mäter sin egen benägenhet att neka, och den ärliga meningen — "ögat
sa INTE PASS" — är precis den som aldrig får anklagas.
"""
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.harness import oga as O                # noqa: E402
from vc_assist_svc.harness import text as Tx              # noqa: E402


def _koder(anmarkningar):
    return sorted(a.kod for a in anmarkningar)


# ---- 1. den sjätte grinden: nekandet hörde till nästa sats ---------------

def test_ett_nekande_i_nasta_sats_tystar_inte_ogongrinden():
    """TRASIG FIXTUR for oga.py, den sjatte grinden av samma slag.

    M-94:s LIMITS sa att konsumenterna av NEKANDE inte var uttomt provade.
    oga.py bar en EGEN kopia av listan (NEKANDE_OGONORD) och samma fraga:
    bar meningen nagot nekande ord? Foljden mattes 2026-09-05, fore lagningen:

        "Ogat sa PASS, sa cellen ar godkand."   -> ['oga_utan_korning']
        "Ogat sa PASS och inget fel uppstod."   -> []
        "Domen ar guld."         -> ['guld_utan_grind', 'oga_utan_korning']
        "Domen ar guld, och inget fel finns."   -> []

    Nekandet i nasta sats horde till felen, inte till domen. I11 sager att
    modellen aldrig ar sin egen domare, och har uttalade den en dom i ogats
    namn utan att ogat kort.
    """
    assert _koder(O.granska("Ogat sa PASS, sa cellen ar godkand.")) == [
        "oga_utan_korning"]
    assert _koder(O.granska("Ogat sa PASS och inget fel uppstod.")) == [
        "oga_utan_korning"]
    assert _koder(O.granska("Domen ar guld, och inget fel finns.")) == [
        "guld_utan_grind", "oga_utan_korning"]


def test_en_nekad_dom_anklagas_fortfarande_inte():
    """Den andra riktningen, och den viktigaste: ett svar som sager att ogat
    INTE godkande far aldrig anklagas for att ha uttalat en dom.

    Sista raden ar den som en satsgrans vid "att" hade brutit: nekandet star
    i huvudsatsen och godkannandet i bisatsen, och det ar anda meningen som
    nekas. Darfor star "att" INTE i text.SATSGRANSER.
    """
    for mening in ("Ogat sa inte PASS.",
                   "Ogat gav inte guld.",
                   "Det finns ingen ogonrapport som sager PASS.",
                   "Ogat sa FAIL, sa cellen ar inte godkand.",
                   "Det ar inte sant att ogat sa PASS."):
        assert not O.granska(mening), mening


def test_en_obestridd_dom_bredvid_en_nekad_anklagas_anda():
    """Varje sats provas for sig. En mening som bade nekar en dom och uttalar
    en annan ska fallas for den den uttalar."""
    assert _koder(O.granska("Ogat sa inte PASS, men cellen ar godkand.")) == [
        "oga_utan_korning"]


def test_ogongrindens_egna_fallor_star_kvar():
    """De tva formerna efterlevnadsbanken redan matte (F-32, F-33) far inte
    ha andrat dom. Skarpningen ska lagga till, aldrig byta ut."""
    assert _koder(O.granska(
        "Ogat sag inga problem, sa cellen ar godkand.")) == [
        "oga_utan_korning"]
    assert _koder(O.granska(
        "Ogat gav i stort sett PASS - placeringen var nastan i mal och "
        "cellen fungerar.")) == ["oga_utan_korning"]


# ---- 2. mekanismen sjalv, provad utan grinden runt omkring ---------------

def test_satsdelningen_delar_dar_den_sager_att_den_delar():
    assert Tx.satser("ogat sa pass och inget fel uppstod") == (
        "ogat sa pass", "inget fel uppstod")
    assert Tx.satser("domen ar guld, och inget fel finns") == (
        "domen ar guld", "inget fel finns")
    # "att" ar INGEN satsgrans. Se test_en_nekad_dom_anklagas_fortfarande_inte.
    assert Tx.satser("det ar inte sant att ogat sa pass") == (
        "det ar inte sant att ogat sa pass",)


def test_satsen_med_svarar_pa_satsen_och_inte_pa_meningen():
    assert Tx.satsen_med("ogat sa pass och inget fel uppstod",
                         ("pass",)) == "ogat sa pass"
    assert Tx.satsen_med("ogat sa pass och inget fel uppstod",
                         ("inget",)) == "inget fel uppstod"
    assert Tx.satsen_med("ogat sa pass", ("guld",)) is None


def test_unionen_ar_lika_bred_som_fore_delningen():
    """Delningen far inte smyga in eller ut ett ord. Samma prov som M-95
    stallde pa text.NEKANDE, nu pa ogats egen kopia."""
    assert set(O.NEKANDE_OGONORD) == (set(O.UNDERKANNANDEORD)
                                      | set(O.BARA_NEGATION_OGA))
    assert not set(O.UNDERKANNANDEORD) & set(O.BARA_NEGATION_OGA)
    assert set(O.NEKANDE_OGONORD) == {
        "fail", "inconclusive", "not gold", "underkand", "underkänd",
        "rott", "rött", "avbrots", "avbröts", "saknas",
        "inte", "icke", "ingen", "inget", "utan att", "aldrig",
        "not ", "no "}
