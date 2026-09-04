# -*- coding: utf-8 -*-
"""L2: laser det VERKLIGA komponentbiblioteket, om det finns pa maskinen.

Ingen VC startas. Provet skyddar M-61:s barande pastaende mot att ruttna:
**ingen komponentfil bar komponentens omslutande volym.** Star det pastaendet
i ett dokument och ingenstans annars, gar det att motsaga tyst genom att nagon
senare later `lada` fyllas i "for att det blev enklare sa".

Hittas inget bibliotek HOPPAS provet over med skal. Ett prov som tyst svarar
gront pa en maskin utan data ar varre an inget prov, sa skalet skrivs ut.
"""
import os
import random
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import katalogindex as KI                      # noqa: E402
from vc_assist_svc import komponentfil as K                       # noqa: E402

#: Sa manga filer ur biblioteket provet laser. Hela biblioteket ar 3201 filer
#: och tar over tio minuter med geometrin; 60 filer tar sekunder och racker
#: for ett pastaende som galler ALLA - ett enda motexempel faller det.
#: Urvalet ar slumpat med FAST fro, sa samma maskin ger samma filer.
URVAL = 60                      # Satt av M-61.
FRO = 61                        # Satt av M-61.


def _bibliotek():
    fynd = KI.hitta()
    return fynd[0].rot if fynd else None


_ROT_BIB = _bibliotek()
kraver_bibliotek = pytest.mark.skipif(
    _ROT_BIB is None,
    reason="inget VC-komponentbibliotek hittades; provade %s"
           % ", ".join(s for s, _h in KI.kandidatrotter()))


@pytest.fixture(scope="module")
def urval():
    filer = K._filer_under(_ROT_BIB)
    r = random.Random(FRO)
    return r.sample(filer, min(URVAL, len(filer)))


@kraver_bibliotek
def test_ingen_komponent_bar_sin_omslutande_volym(urval):
    """M-61:s barande rad. Ett enda motexempel faller den."""
    med_lada = []
    for f in urval:
        fakta = K.las(f, djupt=True, geometri=True)
        if fakta.lada is not None:
            med_lada.append((f, fakta.lada))
        assert fakta.lada_harkomst == K.Harkomst.SAKNAS
        assert "get_bounds" in fakta.lada_skal
    assert not med_lada, (
        "M-61 sager att ingen fil bar komponentens omslutande volym. Dessa "
        "gor det, och da ar matningen fel eller koden har borjat gissa:\n  %s"
        % "\n  ".join("%s -> %r" % x for x in med_lada))


@kraver_bibliotek
def test_varje_granssnitt_i_biblioteket_har_ett_namn(urval):
    """Ett namnlost granssnitt gar inte att koppla mot, och skulle gora
    `kopplingsbara` till en lista med tomma rader."""
    for f in urval:
        for g in K.las(f, djupt=True).granssnitt:
            assert g.namn, "namnlost granssnitt i %s" % f


@kraver_bibliotek
def test_en_avkodad_rackviddsprofil_har_alltid_en_positiv_radie(urval):
    """En profil som avkodas till radien noll ar en robot som pastas na noll
    millimeter. Det ser ut som en matning och ar ett avkodningsfel."""
    for f in urval:
        p = K.las(f, djupt=True, geometri=True).profil
        if p is not None:
            assert p.radie_mm > 0.0, "profil utan radie i %s" % f
            assert len(p) > 0


@kraver_bibliotek
def test_ett_ramlage_som_lases_har_hela_kedjan_konstant(urval):
    """Ett lage med harkomst LAST eller HARLEDD maste ha ett tal; ett med
    SAKNAS far inte ha nagot. Blandas de tva har indexet ljugit tyst."""
    for f in urval:
        for r in K.las(f, djupt=True).ramar:
            if r.harkomst == K.Harkomst.SAKNAS:
                assert r.lage_mm is None, "%s: %r bar bade saknas och ett lage" % (f, r.namn)
            else:
                assert r.lage_mm is not None and len(r.lage_mm) == 3


@kraver_bibliotek
def test_kategorin_kommer_ur_model_xml_och_inte_ur_katalognamnet(urval):
    """M-58:s tva storheter, nu provade mot varandra pa riktig data.

    M-58 lamnade fragan oppen: skiljer sig katalognamnet och komponentens
    eget `Category` nagonsin? Svaret ar ja, i 651 av 3201 (M-61) - alltsa en
    av fem. Kataloger heter "Archiv", "Legacy", "extra", "ultra", "sixx" och
    "TS 1", och ingen av dem ar en kategori.

    Provet gor tva saker: laser `Type` ur den RAA model.xml och kraver att
    lasaren gav samma sak, och kraver att urvalet innehaller minst ett fall
    dar katalognamnet skiljer sig - annars provar det ingenting.
    """
    import re
    import zipfile

    skilda = 0
    for f in urval:
        fakta = K.las(f)
        with zipfile.ZipFile(f) as z:
            xml = z.read("model.xml").decode("utf-8-sig", "replace")
        m = re.search(r'<Property name="Type">(.*?)</Property>', xml, re.S)
        assert m, "model.xml utan Type i %s" % f
        assert fakta.kategori == m.group(1).strip(), (
            "%s: lasaren gav %r men model.xml sager %r"
            % (f, fakta.kategori, m.group(1).strip()))
        if fakta.kategori != os.path.basename(os.path.dirname(f)):
            skilda += 1
    assert skilda > 0, (
        "inget fall i urvalet dar katalognamnet skiljer sig fran "
        "komponentens egen Type. Da provar raden ovan ingenting, och "
        "urvalet maste bli storre.")
