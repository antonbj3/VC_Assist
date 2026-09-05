# -*- coding: utf-8 -*-
"""Mätningstabellen i `00_index.md` ska vara genererad ur katalogen.

Varför provet finns, mätt 2026-09-05: den handskrivna tabellen slutade vid
M-34 medan katalogen bar 108 filer. Sjuttiofyra mätningar var osynliga för
den som läser indexet - och indexet är det första en språkmodell läser.

De trasiga fallen nedan har var sin egen riggade katalog. Var och en var röd
innan mekanismen fanns, och var och en fäller en fälla som kostade något:
den sista, nollan i `M-01`, var min egen bugg i första utkastet.
"""
from __future__ import annotations

import io
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc import matningsindex as MI                    # noqa: E402

_MATNINGAR = os.path.join(_ROT, "docs", "matningar")
_INDEX = os.path.join(_ROT, "docs", "spec", "00_index.md")


def _rigga(tmp_path, filer):
    """filer: {namn: forsta_raden}. Returnerar katalogens sokvag."""
    d = tmp_path / "matningar"
    d.mkdir()
    for namn, rad in filer.items():
        (d / namn).write_text(rad + u"\n\nbrodtext\n", encoding="utf-8")
    return str(d)


# ---- kontrollfallet: en riktig katalog ska gå igenom ----------------------

def test_en_valformad_katalog_ger_alla_med_titel(tmp_path):
    """Kontrollriktningen. Fäller mekanismen allt är den värdelös."""
    k = _rigga(tmp_path, {
        u"M-01_ett.md": u"# M-01 — det första",
        u"M-07_sju.md": u"# M-07 — det sjunde",
        u"M-113_hundra.md": u"# M-113 — det hundratrettonde",
    })
    i = MI.las(k)
    assert len(i.matningar) == 3
    assert i.titellosa == () and i.kollisioner == ()
    assert [m.nummer for m in i.matningar] == [1, 7, 113], "sorteras numeriskt"


# ---- de trasiga fallen ---------------------------------------------------

def test_nollan_i_M01_bars_med(tmp_path):
    """MIN EGEN BUGG i första utkastet: numret lästes som int och skrevs som
    `M-1`. Repot hänvisar till `M-01` på 25 ställen och `M-03` på 46 - en
    tabell som skriver `M-1` gör varje sådant uppslag till en miss."""
    k = _rigga(tmp_path, {u"M-01_ett.md": u"# M-01 — det första"})
    t = MI.tabell(MI.las(k))
    assert "M-01 — det första" in t
    assert "M-1 —" not in t, "nollan tappades: " + t


def test_rubrik_med_kolon_i_stallet_for_tankstreck_namnges(tmp_path):
    """M-121 skrev `# M-121: ...` där de andra 107 skrev `# M-121 — ...`.
    En rad som inte går att läsa får ingen titel, och en rad utan titel är
    värdelös i ett index. Den ska namnges, aldrig hoppas över tyst."""
    k = _rigga(tmp_path, {u"M-55_kolon.md": u"# M-55: fel skiljetecken"})
    i = MI.las(k)
    assert i.matningar == ()
    assert i.titellosa == (u"M-55_kolon.md",)
    assert u"M-55_kolon.md" in MI.tabell(i), "den titellösa ska synas i tabellen"


def test_rubrikens_nummer_maste_stamma_med_filnamnets(tmp_path):
    """Filen heter M-60 och rubriken säger M-61. Uppslag sker på numret, så
    de två skulle peka åt olika håll. Tystnad här är värre än ett fel."""
    k = _rigga(tmp_path, {u"M-60_fel.md": u"# M-61 — numret stämmer inte"})
    i = MI.las(k)
    assert i.matningar == ()
    assert i.titellosa == (u"M-60_fel.md",)


def test_tva_filer_pa_samma_nummer_falls(tmp_path):
    """Numret är mätningens enda identitet. Två filer på samma nummer gör
    varje hänvisning tvetydig."""
    k = _rigga(tmp_path, {
        u"M-70_ett.md": u"# M-70 — den ena",
        u"M-70_tva.md": u"# M-70 — den andra",
    })
    i = MI.las(k)
    assert i.kollisioner == ((70, (u"M-70_ett.md", u"M-70_tva.md")),)
    assert u"Nummer 70" in MI.tabell(i)


def test_en_ny_matning_gor_tabellen_inaktuell(tmp_path):
    """Kärnan. Läggs en mätning till utan att tabellen byggs om ska provet
    falla och NAMNGE filen - inte bara säga att något skiljer sig."""
    k = _rigga(tmp_path, {u"M-01_ett.md": u"# M-01 — det första"})
    idx = tmp_path / "00_index.md"
    idx.write_text(u"# I\n\n%s\n\n%s\n\n%s\n"
                   % (MI.BORJAN, MI.tabell(MI.las(k)), MI.SLUT),
                   encoding="utf-8")
    ok, skal = MI.aktuell(str(idx), k)
    assert ok is True and skal == "", skal
    io.open(os.path.join(k, u"M-02_tva.md"), "w", encoding="utf-8").write(
        u"# M-02 — den andra\n")
    ok, skal = MI.aktuell(str(idx), k)
    assert ok is False
    assert u"M-02_tva.md" in skal, "skälet måste namnge filen: " + skal


def test_markorer_som_saknas_ar_ett_fel_inte_en_gissning(tmp_path):
    """Utan markörer vet mekanismen inte var tabellen hör hemma. Att skriva
    den någon annanstans vore att gissa i en fil andra läser."""
    idx = tmp_path / "00_index.md"
    idx.write_text(u"# I\n\ningen markör här\n", encoding="utf-8")
    with pytest.raises(ValueError):
        MI.skriv_in(str(idx), u"| a | b |")
    ok, skal = MI.aktuell(str(idx), _MATNINGAR)
    assert ok is False and u"markörerna saknas" in skal


# ---- grinden mot det riktiga repot ---------------------------------------

def test_tabellen_pa_disk_ar_aktuell():
    """Faller det här: kör
    `PYTHONPATH=svc python3 -m vc_assist_svc.matningsindex --rot .`
    """
    ok, skal = MI.aktuell(_INDEX, _MATNINGAR)
    assert ok, skal


def test_ingen_matning_saknar_lasbar_rubrik():
    i = MI.las(_MATNINGAR)
    assert i.titellosa == (), (
        "dessa mätningar har ingen läsbar rubrikrad `# M-NN — titel` och är "
        "därför utan titel i indexet: %s" % ", ".join(i.titellosa))
    assert i.kollisioner == (), (
        "fler än en fil gör anspråk på samma nummer: %r" % (i.kollisioner,))
