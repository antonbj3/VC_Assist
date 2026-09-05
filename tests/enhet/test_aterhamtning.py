# -*- coding: utf-8 -*-
"""L1: lägena, avläsningarna och tabellen som avgör om ett försök kan lyckas.

Fas 17 stängde ytan som visar vad som händer MEDAN en körning går. Den här
filen prövar den andra halvan: **vad användaren ser när något har dött, och om
det kommer tillbaka.**

## Den tredje nollade klockan

Två gånger har samma fel mätts i det här systemet, och båda gångerna var det ett
tal som skulle åldras och inte gjorde det.

* `M-64`: ett hjärtslag räknades som framsteg. ARBETAR i **600 av 600**.
* `M-93`: en läsare frös klockan vid bildens egen skrivtid. ARBETAR i
  **60 av 60**.

Den tredje formen bor här: en avläsning som återanvänds efter att den blivit
gammal. Frågan ställdes en gång, svaret var ja, och sedan slutade någon fråga.
`test_en_harledning_som_fryser_klockan_...` mäter den med samma nämnare som
M-93 — och det är avsiktligt: två fel med samma form ska gå att jämföra.

## Och den fjärde: en socket som inte är ett livstecken

Bryggan accepterar anslutningar inuti `tick()`. Är pumpen död fullbordar
kärnans lyssningskö handskakningen ändå. `test_connect_lyckas_mot_...` mäter
det mot en RIKTIG socket som ingen accepterar, i den här processen — inte mot
en attrapp, och inte mot ett antagande.
"""
import os
import socket
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.aterhamtning import bild as B          # noqa: E402
from vc_assist_svc.aterhamtning import lagen as L         # noqa: E402


def _bild(nu=100.0, **kw):
    return B.Systembild(klocka=lambda: nu, **kw)


# ------------------------------------------------------------ lägena

def test_ett_svar_ar_ett_livstecken_en_anslutning_ar_det_inte():
    """Regel L-1, och den är hela skillnaden mellan liv och en öppen socket."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, None, anslutning_oppnades=True))
    assert B.lage_for(b, "bryggan", 100.1) == L.OBESTAMT
    b2 = _bild()
    b2.notera(B.Avlasning("bryggan", 100.0, True))
    assert B.lage_for(b2, "bryggan", 100.1) == L.ANSLUTEN


def test_en_gammal_avlasning_bar_inget_lage():
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True))
    assert B.lage_for(b, "bryggan", 102.9) == L.ANSLUTEN
    assert B.lage_for(b, "bryggan", 103.1) == L.OBESTAMT


def test_en_avlasning_i_framtiden_ar_obestamd_aldrig_arbetande():
    """En klocka som gått bakåt gör varje död körning evig (M-93, S5)."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 200.0, True))
    assert B.lage_for(b, "bryggan", 100.0) == L.OBESTAMT


def test_nere_kraver_att_det_svarat_forut():
    """§1: nere = svarar inte, OCH gjorde det nyss. Annars är vi frånkopplade."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, False, fel="E_TIMEOUT"))
    assert B.lage_for(b, "bryggan", 100.1) == L.FRANKOPPLAD
    b.notera(B.Avlasning("bryggan", 100.2, True))
    b.notera(B.Avlasning("bryggan", 100.3, False, fel="E_TIMEOUT"))
    assert B.lage_for(b, "bryggan", 100.4) == L.NERE


@pytest.mark.parametrize("falt,vantat", [
    ({"degraded": True}, L.DEGRADERAD),
    ({"provtagning": True}, L.PROVTAGNING_PAGAR),
    ({"ko_vantande": 2}, L.KO_VANTAR),
    ({"kor": True}, L.SIMULERING_IGANG),
    ({}, L.ANSLUTEN),
])
def test_foretradet_ar_specens(falt, vantat):
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True, **falt))
    assert B.lage_for(b, "bryggan", 100.1) == vantat


def test_degraderad_slar_provtagning_som_slar_ko():
    """Flera gäller samtidigt; §1.1 säger vilket ord som står."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True, degraded=True,
                         provtagning=True, ko_vantande=5, kor=True))
    assert B.lage_for(b, "bryggan", 100.1) == L.DEGRADERAD


def test_en_oppen_statusruta_blir_blockerad_men_inte_for_evigt():
    """§3.6:s undantag, med en gräns: efter taket går det inte att skilja en
    öppen ruta från en brygga som dog bakom den."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True))
    b.notera(B.Avlasning("bryggan", 100.1, False, fel="inget svar",
                         sista_loggrad=B.MODAL_OPPEN_RAD))
    assert B.lage_for(b, "bryggan", 100.2) == L.BLOCKERAD
    b2 = _bild(t_nere=1e6, t_modal=5.0)
    b2.notera(B.Avlasning("bryggan", 100.0, True))
    b2.notera(B.Avlasning("bryggan", 100.1, False, fel="inget svar",
                          sista_loggrad=B.MODAL_OPPEN_RAD))
    assert B.lage_for(b2, "bryggan", 110.0) == L.OBESTAMT


def test_utan_avlasning_ar_frankopplad_ett_besked_om_oss():
    b = _bild()
    assert B.lage_for(b, "OpenPLC", 100.0) == L.FRANKOPPLAD


def test_okant_delsystem_kastar():
    b = _bild()
    with pytest.raises(L.Aterhamtningsfel):
        B.lage_for(b, "kaffemaskinen", 100.0)


# --------------------------------------------- den tredje nollade klockan

def _frusen_harledning(bild, delsystem, _nu):
    """TRASIG FIXTUR: räknar åldern med avläsningens EGEN tid som nu.

    Det ser ut som omsorg — allt mäts mot samma klocka — och det är precis
    M-93:s fel i en ny skepnad. Åldern blir noll i varje avläsning, och läget
    står kvar på det sista svaret för alltid.
    """
    sista = bild.sista(delsystem)
    if sista is None:
        return L.FRANKOPPLAD
    return B.lage_for(bild, delsystem, sista.t)


def test_en_harledning_som_fryser_klockan_sager_ansluten_i_60_av_60():
    """Måltavlan, med M-93:s nämnare så att de två går att jämföra.

    Sonden svarade en gång och dog sedan. Ingen ny avläsning kommer. Den
    ärliga härledningen tappar läget efter `T_NERE_S`; den frusna säger
    ANSLUTEN i varenda avläsning, i timmar.
    """
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True))
    frusna = [_frusen_harledning(b, "bryggan", 100.0 + k) for k in range(1, 61)]
    arliga = [B.lage_for(b, "bryggan", 100.0 + k) for k in range(1, 61)]
    assert frusna.count(L.ANSLUTEN) == 60
    assert arliga.count(L.ANSLUTEN) == 3      # k = 1, 2, 3 ligger under taket
    assert arliga.count(L.OBESTAMT) == 57


def _connect_som_liv(bild, delsystem, nu):
    """TRASIG FIXTUR: en lyckad anslutning räknas som ett livstecken."""
    sista = bild.sista(delsystem)
    if sista is None:
        return L.FRANKOPPLAD
    if sista.anslutning_oppnades:
        return L.ANSLUTEN
    return B.lage_for(bild, delsystem, nu)


def test_connect_lyckas_mot_en_socket_ingen_accepterar():
    """Premissen bakom regel L-1, mätt mot en RIKTIG socket i den här processen.

    Servern binder och lyssnar men accepterar aldrig — precis som en brygga
    vars pump dog, eftersom `accept()` sker inuti `tick()`. Mätningen säger
    vad kärnan gör på den här värden. Att Wines winsock gör samma sak är
    OPRÖVAT och står som M-25.
    """
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(128)
    port = srv.getsockname()[1]
    anslot = svarade = 0
    b = _bild(nu=0.0)
    try:
        for k in range(20):
            s = socket.create_connection(("127.0.0.1", port), timeout=1.0)
            anslot += 1
            s.settimeout(0.05)
            try:
                s.sendall(b'{"op":"ping"}\n')
                svar = s.recv(100)
            except (socket.timeout, OSError):
                svar = b""
            if svar:
                svarade += 1
            s.close()
            b.notera(B.Avlasning("bryggan", float(k), False if not svar
                                 else True,
                                 fel="" if svar else "inget svar inom 0,05 s",
                                 anslutning_oppnades=True))
    finally:
        srv.close()
    assert anslot == 20, "anslutningen gick inte att öppna 20 gånger"
    assert svarade == 0, "något svarade, och då mäter provet inte det det tror"

    # Och det är just skillnaden de två härledningarna gör.
    falska = [_connect_som_liv(b, "bryggan", 20.0 + k) for k in range(20)]
    arliga = [B.lage_for(b, "bryggan", float(k) + 0.1) for k in range(20)]
    assert falska.count(L.ANSLUTEN) == 20
    assert arliga.count(L.ANSLUTEN) == 0


# ------------------------------------------------------ avläsningens krav

def test_en_tystnad_utan_ord_gar_inte_att_notera():
    with pytest.raises(L.Aterhamtningsfel):
        B.Avlasning("bryggan", 100.0, False, fel="")


def test_en_okand_orsak_gar_inte_att_notera():
    with pytest.raises(L.Aterhamtningsfel):
        B.Avlasning("bryggan", 100.0, True, orsak="natet_var_trott")


# ------------------------------------------------------------- försöken

def test_ett_forsok_som_inte_kan_lyckas_gar_inte_att_paborja():
    """Regeln mekaniserad där försöket skapas.

    `M-13`: för `app.save()` finns ingen väg tillbaka utan operatören.
    Självstarten kan alltså inte lyckas, och att registrera den som pågående
    vore att be någon vänta på ingenting.
    """
    b = _bild()
    with pytest.raises(L.Aterhamtningsfel) as fel:
        b.borja_forsok(L.SJALVSTART, L.SPARAD_LAYOUT)
    assert "kan inte lyckas" in str(fel.value)
    assert b.forsoken == []


def test_ett_forsok_som_kan_lyckas_gar_att_paborja_och_avsluta():
    b = _bild()
    f = b.borja_forsok(L.ANSLUT_IGEN, L.SOCKET_BRUTEN)
    assert f.pagar and f.kanskap == L.KAN_JA
    b.avsluta_forsok(f, True, "ping svarade")
    assert not f.pagar and f.lyckades is True


def test_ett_misslyckat_forsok_utan_ord_kastar():
    b = _bild()
    f = b.borja_forsok(L.ANSLUT_IGEN, L.SOCKET_BRUTEN)
    with pytest.raises(L.Aterhamtningsfel):
        b.avsluta_forsok(f, False, "")


def test_en_avslagen_sjalvstart_gor_varje_sjalvstartsforsok_omojligt():
    """Omstartsstormen är mätt till tusentals varv i sekunden (M-13)."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True, keepalive=False))
    assert b.utan_sjalvstart is True
    assert L.kan_lyckas(L.OPERATOREN_STOPPADE, L.SJALVSTART, True) == L.KAN_NEJ
    with pytest.raises(L.Aterhamtningsfel):
        b.borja_forsok(L.SJALVSTART, L.OPERATOREN_STOPPADE)


def test_ingen_orsak_lovar_att_sjalvstarten_kan_lyckas():
    """Strukturell spärr: `okänt` får aldrig glida till `ja` den här vägen.

    Självstarten är den enda vägen systemet går utan att fråga. Skulle någon
    orsak stå som KAN_JA för den skulle en okänd keepalive kunna bli ett
    löfte, och ett löfte till någon som väntar på en död brygga är det
    dyraste vi kan ge.
    """
    lovande = [o.nyckel for o in L.ORSAKER
               if L.kan_lyckas(o, L.SJALVSTART) == L.KAN_JA]
    assert lovande == []


def test_en_automatisk_vag_gar_aldrig_genom_operatoren():
    for o in L.ORSAKER:
        if o.automatisk is not None:
            assert not o.automatisk.av_operatoren, o.nyckel


def test_de_flesta_orsaker_har_ingen_automatik_och_det_ar_talet():
    """Talet som gör regeln nödvändig, räknat ur tabellen.

    Är det ovanligt att något försöker igen blir varje mening om ett pågående
    försök misstänkt, och den ärliga ytan säger `Ingenting försöker igen` mycket
    oftare än den säger något annat.
    """
    med = [o for o in L.ORSAKER if o.automatisk is not None]
    assert len(L.ORSAKER) == 18
    assert len(med) == 3
    matt = [o for o in med
            if L.kan_lyckas(o, o.automatisk) == L.KAN_JA]
    assert len(matt) == 2


def test_ingen_kanskap_ar_delstrang_av_en_annan():
    """Mätt fel i den här filens egen historia.

    Första formuleringen var `okänt om den kan lyckas`, och den bär
    `kan lyckas` inuti sig. Grinden letar efter orden i en främmande
    renderares text — den hade alltså sagt att en väg som står som OKÄND bär
    ett JA, i precis det steg som finns för att förhindra att ett okänt blir
    ett löfte.
    """
    for a in L.KANSKAP:
        for b in L.KANSKAP:
            if a is not b:
                assert a not in b, "%r ligger inuti %r" % (a, b)


def test_kanskapen_har_tre_varden_och_tabellen_ar_oskrivbar():
    assert set(L.KAN.values()) <= set(L.KANSKAP)
    with pytest.raises(TypeError):
        L.KAN[("skriptbeteende", "sjalvstart")] = L.KAN_JA


def test_ett_par_som_saknas_i_tabellen_ar_okant_aldrig_ja():
    """Fail-closed (I3). En väg ingen prövat är inte en väg som fungerar."""
    assert L.kan_lyckas(L.MODELLEN_TOG_SLUT, L.MENYVAL2) == L.KAN_OKAND


# --------------------------------------------------------- ut ur processen

def test_bilden_gar_ut_och_tillbaka_med_LASARENS_klocka():
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True))
    f = b.borja_forsok(L.ANSLUT_IGEN, L.SOCKET_BRUTEN)
    b.avsluta_forsok(f, True, "ping svarade")
    tillbaka = B.Systembild.fran_json(b.till_json(), klocka=lambda: 200.0)
    assert len(tillbaka.avlasningar) == 1
    assert len(tillbaka.forsoken) == 1
    # Åldern räknas mot den som LÄSER, inte mot den som skrev.
    assert B.lage_for(tillbaka, "bryggan", 200.0) == L.OBESTAMT


@pytest.mark.parametrize("trasig", [
    {"v": 99},
    {"avlasningar": None},
    {"extra": 1},
])
def test_en_bild_som_inte_gar_att_lasa_kastar_i_stallet_for_att_bli_tom(trasig):
    """Ett tomt läge är ett lugnt besked, och ett läsfel får aldrig se lugnt ut."""
    b = _bild()
    b.notera(B.Avlasning("bryggan", 100.0, True))
    data = b.till_json()
    data.update(trasig)
    with pytest.raises((L.Aterhamtningsfel, TypeError)):
        B.Systembild.fran_json(data)


def test_las_bild_gor_ett_lasfel_till_obestamt_inte_till_ett_stacktrace(tmp_path):
    blick = B.las_bild(str(tmp_path / "finns-inte.json"))
    assert blick.obestamd
    assert "FileNotFoundError" in blick.fel


def test_las_bild_gor_en_avhuggen_fil_till_obestamt(tmp_path):
    p = tmp_path / "halv.json"
    p.write_text('{"v": 1, "uppdrag": "x", "t0"', encoding="utf-8")
    blick = B.las_bild(str(p))
    assert blick.obestamd
    assert "avhuggen" in blick.fel
