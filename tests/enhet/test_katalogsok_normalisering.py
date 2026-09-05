# -*- coding: utf-8 -*-
"""L1 for namnstegen i sokskiktet - och for att stegen INTE hittar pa.

M-161 delade komponentsokets nolla i tva hal. Det har ar det andra:
bankens namn bar tillverkarledet ("ABB IRB 1200-5/0.9"), bibliotekets gor det
inte ("IRB 1200-5/0.9"), och en rak delstrangssokning traffar da noll pa alla
femton beteckningsfragor.

DE TRASIGA FALLEN AR SKRIVNA FORST och de ar hela poangen. En sokning som
gors mer tillatande far inte borja svara pa fragor den ska saga SAKNAS pa.
Fyra av dem kommer ur den riktiga matningen och inte ur fantasin:

  * `ABB IRB 660-180/3.15` finns INTE i biblioteket - det bar bara `IRB 660`.
  * `ABB IRB 360-1/1130 FlexPicker` finns inte heller - biblioteket bar
    `IRB 360-3/1130` och `IRB 360-1/1600`, tva grannar, ingen av dem den.
  * `VDA KLT 4147` finns inte i nagon stavning.
  * `Bandtransportor, bandbredd 400 mm` ar bankens egen svenska beskrivning
    och har ingen motsvarighet alls.

Alla fyra maste ge NOLL traffar efter lagningen ocksa. Ett SAKNAS ar battre
an en pahittad traff.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.katalogsok import Katalog  # noqa: E402


# Namnen ar de VERKLIGA namnen ur VC 4.10:s eCatalog pa den har maskinen,
# lasta i M-161. Ingen av dem ar hittepa.
_BIBLIOTEK = [
    ("IRB 1200-5/0.9", "ABB"),
    ("IRB 1200-5/0.9 Gen2", "ABB"),
    ("IRB 1200-7/0.7", "ABB"),
    ("IRB 120", "ABB"),
    ("IRB 2600-20/1.65", "ABB"),
    ("IRB 260", "ABB"),
    ("IRB 660", "ABB"),
    ("IRB 360-3/1130", "ABB"),
    ("IRB 360-1/1600", "ABB"),
    ("IRB 910SC-3/0.55", "ABB"),
    ("M-10iD/12", "Fanuc"),
    ("LR Mate 200iD/7L", "Fanuc"),
    ("KR 10 R1100 sixx", "KUKA"),
    ("KR 10 R1100 sixx C", "KUKA"),
    ("1", "KUKA"),
    ("KMP 1200-S", "KUKA"),
    ("Chain Conveyor", "Qimarox"),
]


def kat():
    return Katalog.fran_index({
        "format": 1, "rot": "/x", "djupt": True,
        "poster": [{"namn": n, "tillverkare": t, "kategori": "Robots",
                    "sokvag": "/x/%s.vcmx" % n, "granssnitt": 2,
                    "familj": "robot"}
                   for n, t in _BIBLIOTEK]})


def namn(svar):
    return [t.namn for t in svar.traffar]


# ==================================================================== TRASIGA
#
# De har ska vara NOLL bade fore och efter lagningen. De ar skrivna forst.

@pytest.mark.parametrize("fraga", [
    # Beteckningen finns inte - biblioteket bar bara grundmodellen `IRB 660`.
    "ABB IRB 660-180/3.15",
    # Varianten finns inte - tva grannar gor det, och de ar andra robotar.
    "ABB IRB 360-1/1130 FlexPicker",
    # Ingen stavning av den finns i biblioteket.
    "VDA KLT 4147",
    # Bankens egen svenska beskrivning. Biblioteket talar inte det spraket.
    u"Bandtransportör, bandbredd 400 mm",
    # Ratt beteckning, FEL tillverkarled. Tillverkaren ar ett filter, inte
    # ett ord som far strykas och glommas.
    "KUKA IRB 1200-5/0.9",
    # En pahittad beteckning i ratt form. Formen far aldrig racka.
    "ABB IRB 9997-99/9.99",
    # Tillverkarledet plus ett ENDA tecken. Biblioteket bar komponenter som
    # heter "0" .. "7" (8 av 3201, M-161), och utan sparr blir den har fragan
    # ett jokertecken over hela tillverkarens sortiment.
    "KUKA 1",
])
def test_en_fraga_som_ska_ge_SAKNAS_ger_noll_traffar(fraga):
    assert kat().sok(fraga=fraga).totalt == 0, fraga


def test_grannen_erbjuds_aldrig_i_stallet_for_den_som_fragades():
    """IRB 660 ar inte IRB 660-180/3.15, och IRB 260 ar inte IRB 2600."""
    assert namn(kat().sok(fraga="ABB IRB 660-180/3.15")) == []
    assert "IRB 260" not in namn(kat().sok(fraga="ABB IRB 2600-20/1.65"))
    assert "IRB 120" not in namn(kat().sok(fraga="ABB IRB 1200-5/0.9"))


# ================================================================== LAGNINGEN

def test_tillverkarledet_far_strykas_nar_biblioteket_inte_bar_det():
    """M-85: banken skriver `ABB IRB 1200-5/0.9`, biblioteket `IRB 1200-5/0.9`."""
    s = kat().sok(fraga="ABB IRB 1200-5/0.9")
    assert namn(s) == ["IRB 1200-5/0.9", "IRB 1200-5/0.9 Gen2"]


@pytest.mark.parametrize("fraga,vantat", [
    ("ABB IRB 2600-20/1.65", "IRB 2600-20/1.65"),
    ("FANUC M-10iD/12", "M-10iD/12"),
    ("FANUC LR Mate 200iD/7L", "LR Mate 200iD/7L"),
    ("KUKA KR 10 R1100 sixx", "KR 10 R1100 sixx"),
])
def test_de_riktiga_modellbeteckningarna_hittas(fraga, vantat):
    assert vantat in namn(kat().sok(fraga=fraga))


def test_ett_efterstallt_beskrivande_ord_far_slappas_och_sags_i_svaret():
    """`ABB IRB 910SC-3/0.55 SCARA` - biblioteket skriver ingen SCARA."""
    s = kat().sok(fraga="ABB IRB 910SC-3/0.55 SCARA")
    assert namn(s) == ["IRB 910SC-3/0.55"]
    assert "SCARA" in (s.lasning or ""), \
        "en bortsklippt del av fragan far aldrig vara tyst"


def test_skiljetecknen_far_stavas_om():
    """Samma beteckning med _ i stallet for mellanslag, - och /."""
    assert "IRB 1200-5/0.9" in namn(kat().sok(fraga="IRB1200_5_09"))
    assert "M-10iD/12" in namn(kat().sok(fraga="M10ID12"))


def test_svaret_sager_HUR_det_last_fragan():
    """Ingen bortprioritering ar tyst (25_kontextbudget.md)."""
    assert kat().sok(fraga="IRB 120").lasning is None, \
        "en rak traff ska inte pasta att nagot tolkades"
    l = kat().sok(fraga="ABB IRB 2600-20/1.65").lasning
    assert l and "ABB" in l


def test_den_raka_delstrangen_gar_alltid_forst():
    """Stegen ar en STEGE: en losare niva kors bara nar den strangare gav noll.

    Utan den ordningen breddas var fraga som redan traffar - matt i M-161:
    2,31 % av 3201 sjalvfragor fick fler traffar av en skiljeteckenslos
    matchning, och 'C4' hittade da 'EC-400'.
    """
    rakt = [n for n, _t in _BIBLIOTEK if "irb 120" in n.lower()]
    s = kat().sok(fraga="IRB 120")
    assert sorted(namn(s)) == sorted(rakt), \
        "en fraga som redan traffar rakt far inte breddas av ett losare steg"
    assert s.lasning is None
    assert "IRB 260" not in namn(kat().sok(fraga="IRB 2600"))


# ============================================== vokabularglappet: klass 1
#
# De 60 andra fragorna. Inget namnsteg loser dem, och M-161 mater varfor: de
# tva vokabularen beskriver inte samma sak. Bankens 60 ANTAGNA poster bar 31
# olika matta falt och de flesta ar TIDER (anslag_s, spanntid_s, svarstid_ms);
# bibliotekets deklarerade falt ar tva, Reach och MaxPayload. Ett alias-skikt
# hade brygga ORDEN och anda inte STORHETERNA - och det hade dessutom varit
# ett handskrivet register utan facitkalla (85_bankkontraktet.md §2).
#
# Det enda soket kan gora arligt ar att saga var de andra dorrarna sitter.

def test_noll_traffar_pa_ett_namn_pekar_ut_de_andra_dorrarna(monkeypatch):
    import vc_assist_svc.verktyg as V
    import vc_assist_svc.verktyg.katalog as KT

    KT._nollstall_bibliotek()
    monkeypatch.setattr(KT, "_bibliotek", lambda: (kat(), None))
    try:
        r = V.DATA_HANDLERS["search_installed_library"](
            {"query": u"Induktiv närvarogivare"})
        assert r["antal"] == 0
        assert r["notering"] and "family" in r["notering"]
        assert "sager INTE att komponenten saknas" in r["notering"], \
            "svaret far inte lasas som att komponenten inte finns"
        # ... och en traff far ALDRIG bara den raden.
        t = V.DATA_HANDLERS["search_installed_library"](
            {"query": "ABB IRB 1200-5/0.9"})
        assert t["antal"] == 2
        assert t["notering"] is None, "en traff far aldrig bara nollraden"
        assert t["lasning"] and "ABB" in t["lasning"]
    finally:
        KT._nollstall_bibliotek()


def test_nollraden_namner_inte_family_i_ett_GRUNT_index(monkeypatch):
    """M-163: `sok(familj="robot")` ger 0 av 3201 i ett grunt index.

    Familjemarkoren ligger vid median 14 215 byte och den grunda lasningen
    stannar vid 4 096 (M-69). Ett rad som skickar den som fragade till ett
    filter som svarar "ingenting i biblioteket" ar samre an inget rad alls.
    """
    import vc_assist_svc.verktyg as V
    import vc_assist_svc.verktyg.katalog as KT

    grunt = Katalog.fran_index({
        "format": 1, "rot": "/x", "djupt": False,
        "poster": [{"namn": n, "tillverkare": t, "kategori": "Robots",
                    "sokvag": "/x/%s.vcmx" % n}
                   for n, t in _BIBLIOTEK]})
    KT._nollstall_bibliotek()
    monkeypatch.setattr(KT, "_bibliotek", lambda: (grunt, None))
    try:
        r = V.DATA_HANDLERS["search_installed_library"](
            {"query": u"Induktiv närvarogivare"})
        assert r["antal"] == 0
        assert "family" not in r["notering"]
        assert "manufacturer" in r["notering"]
    finally:
        KT._nollstall_bibliotek()
