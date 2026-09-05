# -*- coding: utf-8 -*-
"""L1: grinden över återhämtningsytan, och de sjutton som måste falla.

Grinden dömer PARET avläsningar och text. Den frågar aldrig den som visar vad
läget är — den räknar om det själv ur de råa avläsningarna och läsarens klocka.
Det är därför den fäller tre olika sorters lögn med samma kod:

* en **renderare** som skriver något annat än protokollet säger,
* en **härledning** som drar fel slutsats ur avläsningarna,
* en **kanskap** som frusit fast medan världen ändrade sig.

Varje regel `Å1`–`Å14` har minst en trasig fixtur nedan, och
`test_alla_regler_har_minst_en_trasig_fixtur` läser sin egen källa och faller på
en regel som saknar en. En grind utan trasig fixtur är oprövad
(`95_testprotokoll.md`).
"""
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.aterhamtning import bild as B          # noqa: E402
from vc_assist_svc.aterhamtning import grind as G         # noqa: E402
from vc_assist_svc.aterhamtning import lagen as L         # noqa: E402
from vc_assist_svc.aterhamtning import yta as Y           # noqa: E402

BOOT = ("OnAppInitialized\nloadCommand uri=x\nbridge_cmd executed\n"
        "brygg-komponenten byggd, skriptet kompilerar\n")
BRYGG = ("startar pa 127.0.0.1:8901\nlyssnar pa 127.0.0.1:8901\n"
         "pumpen igang\nkoad q1: spara layouten\n"
         "  varning: q1 dodar pumpen (save)\nsimuleringen stoppad\n")
LOGGAR = {"vc_assist_boot.log": BOOT, "vc_assist_brygga.log": BRYGG}

FELET = "BryggFel: E_TIMEOUT: inget svar inom 3.0 s"


def _dod_brygga(nu=100.0):
    """En layout sparades, bryggan gick ned. Den dyraste av de mätta dödarna."""
    b = B.Systembild(klocka=lambda: nu)
    b.notera(B.Avlasning("bryggan", nu - 4.0, True, kor=True))
    b.notera(B.Avlasning("OpenPLC", nu - 0.5, True))
    b.notera(B.Avlasning("modellen", nu - 0.4, True))
    b.notera(B.Avlasning("bryggan", nu - 0.3, False, fel=FELET,
                         anslutning_oppnades=True, orsak="sparad_layout"))
    return B.blicka(b, klocka=lambda: nu)


def _gron(nu=100.0):
    b = B.Systembild(klocka=lambda: nu)
    for d in L.DELSYSTEM:
        b.notera(B.Avlasning(d, nu - 0.2, True, kor=True))
    return B.blicka(b, klocka=lambda: nu)


def test_den_arliga_ytan_haller_sin_egen_grind():
    assert G.granska(_dod_brygga(), None, LOGGAR).ok
    assert G.granska(_gron()).ok


def test_en_gron_yta_bar_rackvidden_anda():
    """Räckvidden betas inte av. Den gäller också en körning där allt svarar."""
    text = Y.rendera(_gron())
    for _n, namn, _s in Y.RACKVIDDEN:
        assert namn in text


# ------------------------------------------------------- trasiga renderare

def _r_fel_lage(blick, loggar):
    return Y.rendera(blick, loggar).replace(
        "%s bryggan %s" % (Y.RUBRIK_LAGE, L.NERE),
        "%s bryggan %s" % (Y.RUBRIK_LAGE, L.ANSLUTEN), 1)


def _r_snurrar_vidare(blick, loggar):
    rader = Y.rendera(blick, loggar).splitlines()
    rader.insert(1, "  steg fyra %s 12,4 s" % Y.PAGAR_MARKOR)
    return "\n".join(rader)


def _r_lovar_nytt_forsok(blick, loggar):
    """Operatörens egen mening, ordagrant, om ingenting alls."""
    text = Y.rendera(blick, loggar)
    return text.replace(
        "%s inget försök pågår" % Y.RUBRIK_ATERHAMTNING,
        "%s Ett problem uppstod, vi försöker igen." % Y.RUBRIK_ATERHAMTNING
    ).replace(Y.INGET_FORSOK, "").replace(
        "Systemet gör ingenting av sig självt förrän du säger till.", "")


def _r_utan_orsak(blick, loggar):
    """"Ett problem uppstod" i stället för orsaken. N-5, och den är mätt:
    en visning som inte säger VILKEN post och VILKET anrop lämnar operatören
    med samma information som en tom logg."""
    return Y.rendera(blick, loggar).replace(
        "Layouten sparades.", "Ett problem uppstod.")


def _r_utelamnar_ett_delsystem(blick, loggar):
    rader = [r for r in Y.rendera(blick, loggar).splitlines()
             if not (r.startswith("  OpenPLC") or r.startswith("ORSAK: OpenPLC"))]
    return "\n".join(rader)


def _r_skriver_om_felet(blick, loggar):
    return Y.rendera(blick, loggar).replace(
        FELET, "Anslutningen till VC gick förlorad. Försök igen om en stund.")


def _r_utan_kanskap(blick, loggar):
    rader = [r for r in Y.rendera(blick, loggar).splitlines()
             if r.strip() not in L.KANSKAP]
    return "\n".join(rader)


def _r_tiger_om_att_inget_forsoker(blick, loggar):
    return Y.rendera(blick, loggar).replace(Y.INGET_FORSOK, "")


def _r_doljer_avlasningar(blick, loggar):
    return re.sub(r"  \.\.\. \d+ till, ej visade\.\n", "",
                  Y.rendera(blick, loggar))


def _r_utan_rackvidd(blick, loggar):
    text = Y.rendera(blick, loggar)
    return text[:text.index(Y.RUBRIK_VET_INTE)]


def _r_utan_stegen(blick, loggar):
    text = Y.rendera(blick, loggar)
    i, j = text.index(Y.RUBRIK_STEGEN), text.index(Y.RUBRIK_VET_INTE)
    return text[:i] + text[j:]


def _r_tiger_om_utan_sjalvstart(blick, loggar):
    return "\n".join(r for r in Y.rendera(blick, loggar).splitlines()
                     if L.UTAN_SJALVSTART not in r)


def _r_utan_alder(blick, loggar):
    return re.sub(r"avläst för \d+\.\d+ s sedan", "avläst nyligen",
                  Y.rendera(blick, loggar))


def _r_med_lang_rad(blick, loggar):
    rader = Y.rendera(blick, loggar).splitlines()
    rader.insert(2, "  " + "en mycket lang egen mening " * 6)
    return "\n".join(rader)


# ------------------------------------------------------ trasiga härledningar

def _tystnad_efter_ett_ja(nu=100.0):
    """Sonden fick ett ja och dog sedan. Ingen ny avläsning kommer.

    Det är läget en frusen klocka är blind för: allt i bilden säger ANSLUTEN,
    och det enda som talar om något annat är hur länge sedan det var.
    """
    b = B.Systembild(klocka=lambda: nu)
    for d in L.DELSYSTEM:
        b.notera(B.Avlasning(d, nu - 30.0, True, kor=True))
    return B.blicka(b, klocka=lambda: nu)


def _h_frusen_klocka(blick, loggar):
    """Renderar med BILDENS egen sista tid som nu. M-93:s fel, ny våning.

    Texten blir korrekt mot ett läge som är fel, och det är exakt vad grinden
    finns för: den räknar om läget ur avläsningarna och läsarens klocka.
    """
    sista = max(a.t for a in blick.bild.avlasningar)
    frusen = B.Blick(bild=blick.bild, nu=sista, kalla=blick.kalla)
    return Y.rendera(frusen, loggar)


def _h_connect_som_liv(blick, loggar):
    """En lyckad anslutning räknad som ett livstecken (regel L-1)."""
    return Y.rendera(blick, loggar).replace(
        "%s bryggan %s" % (Y.RUBRIK_LAGE, L.NERE),
        "%s bryggan %s" % (Y.RUBRIK_LAGE, L.ANSLUTEN), 1).replace(
        "  bryggan   %-17s" % L.NERE, "  bryggan   %-17s" % L.ANSLUTEN)


# Fjärde fältet är den bild fixturen behöver. De flesta lögner går att berätta
# om vilken bild som helst; en frusen klocka syns bara i en bild där tid gått
# sedan det sista jaet.
TRASIGA = (
    ("renderare_med_fel_lage", _r_fel_lage, ("Å1",), None),
    ("renderare_som_snurrar_vidare", _r_snurrar_vidare, ("Å3",), None),
    ("renderare_som_lovar_nytt_forsok", _r_lovar_nytt_forsok, ("Å6",), None),
    ("renderare_utan_orsak", _r_utan_orsak, ("Å4",), None),
    ("renderare_som_utelamnar_ett_delsystem", _r_utelamnar_ett_delsystem,
     ("Å2",), None),
    ("renderare_som_skriver_om_felet", _r_skriver_om_felet, ("Å5",), None),
    ("renderare_utan_kanskap", _r_utan_kanskap, ("Å7",), None),
    ("renderare_som_tiger_om_att_inget_forsoker",
     _r_tiger_om_att_inget_forsoker, ("Å8",), None),
    ("renderare_som_doljer_avlasningar", _r_doljer_avlasningar, ("Å9",), None),
    ("renderare_utan_rackvidd", _r_utan_rackvidd, ("Å10",), None),
    ("renderare_utan_stegen", _r_utan_stegen, ("Å11",), None),
    ("renderare_utan_alder", _r_utan_alder, ("Å13",), None),
    ("renderare_med_lang_rad", _r_med_lang_rad, ("Å14",), None),
    ("harledning_som_fryser_klockan", _h_frusen_klocka, ("Å1",),
     _tystnad_efter_ett_ja),
    ("harledning_som_raknar_connect_som_liv", _h_connect_som_liv, ("Å1",),
     None),
)


@pytest.mark.parametrize("namn,renderare,vantade,fabrik", TRASIGA,
                         ids=[t[0] for t in TRASIGA])
def test_varje_trasig_fixtur_falls(namn, renderare, vantade, fabrik):
    blick = (fabrik or _dod_brygga)()
    if namn == "renderare_som_doljer_avlasningar":
        for k in range(Y.MAX_AVLASNINGSRADER + 4):
            blick.bild.notera(B.Avlasning("modellen", blick.nu - 0.6, True))
    dom = G.granska(blick, renderare(blick, LOGGAR), LOGGAR)
    assert not dom.ok, "%s slapp igenom grinden" % namn
    for regel in vantade:
        assert regel in dom.brutna, (
            "%s fälldes, men inte av %s: %s" % (namn, regel, dom.brutna))


def test_ett_omojligt_forsok_far_inte_redovisas_som_pagaende():
    """Kanskapen frös när försöket började, och världen ändrade sig sedan.

    Bryggan slog av sin egen självstart efter taket 20 omstarter på en minut
    (M-13). Självstartsförsöket som pågick kan inte längre lyckas, och en
    visning som räknar det bland de pågående låter någon vänta förgäves.
    """
    nu = [100.0]
    b = B.Systembild(klocka=lambda: nu[0])
    b.notera(B.Avlasning("bryggan", 99.0, True, keepalive=True))
    b.notera(B.Avlasning("bryggan", 99.5, False, fel="inget svar",
                         orsak="operatoren_stoppade"))
    f = b.borja_forsok(L.SJALVSTART, L.OPERATOREN_STOPPADE)
    assert f.kanskap == L.KAN_OKAND
    b.notera(B.Avlasning("bryggan", 99.8, True, keepalive=False))
    b.notera(B.Avlasning("bryggan", 99.9, False, fel="inget svar",
                         orsak="operatoren_stoppade"))
    blick = B.blicka(b, klocka=lambda: 100.0)

    mojliga, omojliga = Y.mojliga_och_omojliga(blick)
    assert not mojliga and len(omojliga) == 1

    arlig = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, arlig, LOGGAR).ok
    assert L.KAN_NEJ in arlig

    trasig = arlig.replace(L.KAN_NEJ, "pågår")
    dom = G.granska(blick, trasig, LOGGAR)
    assert not dom.ok and "Å6" in dom.brutna


def test_en_avslagen_sjalvstart_star_som_tillagg_aldrig_i_stallet_for():
    b = B.Systembild(klocka=lambda: 100.0)
    b.notera(B.Avlasning("bryggan", 99.5, True, keepalive=False))
    b.notera(B.Avlasning("bryggan", 99.9, False, fel="inget svar",
                         orsak="operatoren_stoppade"))
    blick = B.blicka(b, klocka=lambda: 100.0)
    text = Y.rendera(blick, LOGGAR)
    assert text.splitlines()[0] == "%s bryggan %s" % (Y.RUBRIK_LAGE, L.NERE)
    assert L.UTAN_SJALVSTART in text
    assert G.granska(blick, text, LOGGAR).ok
    dom = G.granska(blick, _r_tiger_om_utan_sjalvstart(blick, LOGGAR), LOGGAR)
    assert not dom.ok and "Å12" in dom.brutna


def test_en_obestamd_bild_ar_obestamd_aldrig_lugn(tmp_path):
    p = tmp_path / "trasig.json"
    p.write_text("{halv", encoding="utf-8")
    blick = B.las_bild(str(p))
    text = Y.rendera(blick)
    assert text.splitlines()[0] == "%s systembilden %s" % (Y.RUBRIK_LAGE,
                                                           L.OBESTAMT)
    assert G.granska(blick, text).ok
    # Och ett läsfel som ser ut som en lugn början fälls.
    dom = G.granska(blick, text.replace(
        "%s systembilden %s" % (Y.RUBRIK_LAGE, L.OBESTAMT),
        "%s systembilden %s" % (Y.RUBRIK_LAGE, L.FRANKOPPLAD), 1))
    assert not dom.ok and "Å1" in dom.brutna


def test_en_renderare_som_inte_ar_text_kastar():
    with pytest.raises(L.Aterhamtningsfel):
        G.granska(_gron(), {"lage": "ANSLUTEN"})


def test_granska_eller_kasta_slapper_inte_igenom_en_trasig_yta():
    blick = _dod_brygga()
    with pytest.raises(L.Aterhamtningsfel):
        G.granska_eller_kasta(blick, _r_utan_orsak(blick, LOGGAR), LOGGAR)


def test_alla_regler_har_minst_en_trasig_fixtur():
    """Grinden läser sin egen källa. En regel utan trasig fixtur är oprövad."""
    kallan = open(__file__, encoding="utf-8").read()
    tackta = set()
    for _namn, _r, regler, _f in TRASIGA:
        tackta.update(regler)
    for regel in re.findall(r'"(Å\d+)" in dom\.brutna', kallan):
        tackta.add(regel)
    saknas = [r for r in G.REGLER if r not in tackta]
    assert not saknas, ("regler utan trasig fixtur: %s. En grind utan trasig "
                        "fixtur är oprövad" % ", ".join(saknas))


def test_grinden_faller_om_en_regel_stangs_av():
    """En grind som inte kan bli röd mäter ingenting.

    Provet tar bort ett brott ur domen och kontrollerar att domen då blir
    grön — alltså att det verkligen var regeln som bar fällningen, inte en
    slump i en annan.
    """
    blick = _dod_brygga()
    dom = G.granska(blick, _r_utan_orsak(blick, LOGGAR), LOGGAR)
    assert dom.brutna == ("Å4",)
    dom.brott = []
    assert dom.ok
