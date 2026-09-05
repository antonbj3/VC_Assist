# -*- coding: utf-8 -*-
"""L1: de fyra sakerna som kan dö mitt i, och vad användaren ser av var och en.

Operatörens fråga, ordagrant: *"vad händer när något dör mitt i? VC stängs
under en körning. Bryggan tappar sin socket. OpenPLC svarar inte. Modellen tar
slut mitt i en reparation."*

Fyra dödsfall, fyra olika svar, och skillnaden mellan dem är hela poängen:

* **VC stängs** — ingen väg tillbaka utom att starta VC. Ingenting försöker.
* **sockeln tappas** — bryggan lever, och tjänsten kan ansluta om. Något
  försöker, och det kan lyckas.
* **OpenPLC tystnar** — kopplaren tål tre raka fel och ger sedan upp. Efter det
  försöker ingenting, och det är avsiktligt (M-39).
* **modellen tar slut** — varvet blev aldrig klart, och de grindar som skulle
  ha kört efter det kördes aldrig. Det som inte kördes får inte se ut som något
  som höll.

Det som INTE får hända är att alla fyra ser likadana ut. En yta som svarar
*"Ett problem uppstod, vi försöker igen"* på alla fyra har fyra fel: den
namnger inte saken, den lovar ett försök, den döljer att tre av fyra kräver en
människa, och den ger operatören ingenting att göra.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.aterhamtning import bild as B          # noqa: E402
from vc_assist_svc.aterhamtning import grind as G         # noqa: E402
from vc_assist_svc.aterhamtning import kallor as K        # noqa: E402
from vc_assist_svc.aterhamtning import lagen as L         # noqa: E402
from vc_assist_svc.aterhamtning import yta as Y           # noqa: E402
from vc_assist_svc.forlopp.spegel import Spegel           # noqa: E402

LOGGAR = {K.BOOTLOGG: ("OnAppInitialized\nloadCommand uri=x\n"
                       "bridge_cmd executed\n"
                       "brygg-komponenten byggd, skriptet kompilerar\n"),
          K.BRYGGLOGG: ("startar pa 127.0.0.1:8901\n"
                        "lyssnar pa 127.0.0.1:8901\npumpen igang\n")}


def _finns(text, fras):
    """Vår egen prosa radbryts i ytan; jämför med mellanrummen hopslagna."""
    return " ".join(fras.split()) in " ".join(text.split())


class _Varv(object):
    """Ett kopplarvarv, med kopplarens egna fältnamn."""

    def __init__(self, nr, fel=None, totalt_ms=1.0):
        self.nr = nr
        self.fel = fel
        self.totalt_ms = totalt_ms


class _Protokoll(object):
    def __init__(self, utfall, max_varv=4):
        self.utfall = utfall
        self.max_varv = max_varv


def _levande(nu=100.0):
    b = B.Systembild(klocka=lambda: nu)
    b.notera(B.Avlasning("bryggan", nu - 0.1, True, kor=True, keepalive=True))
    b.notera(B.Avlasning("OpenPLC", nu - 0.1, True))
    b.notera(B.Avlasning("modellen", nu - 0.1, True))
    return b


# ---------------------------------------------------- 1. VC stängs mitt i

def test_vc_stangs_under_en_korning():
    b = _levande()
    K.vc_avslutades(b, "ConnectionResetError: [Errno 104] Connection reset "
                       "by peer")
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.lage("bryggan") == L.NERE
    assert blick.orsak("bryggan") is L.VC_AVSLUTADES

    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    # Sagt, inte antytt: vad som hände, att ingenting försöker, och vad DU gör.
    assert _finns(text, "Visual Components avslutades")
    assert _finns(text, Y.INGET_FORSOK)
    assert _finns(text, "Starta om Visual Components.")
    # Och felets egna ord, tecken för tecken.
    assert "[Errno 104] Connection reset by peer" in text


# --------------------------------------------- 2. bryggan tappar sin socket

def test_bryggan_tappar_sin_socket_och_kommer_tillbaka():
    """Det enda av de fyra där systemet får försöka själv — och lyckas.

    Skillnaden mot fall 1 är att bryggan LEVER. Att skilja de två kostar en
    fråga till: en ny anslutning OCH ett nytt ping. Bara ett ping-svar duger
    (regel L-1).
    """
    b = _levande()
    fel = ConnectionResetError(104, "Connection reset by peer")
    K.fran_bryggfel(b, fel, anslutning_oppnades=True, svarade_efterat=True)
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.orsak("bryggan") is L.SOCKET_BRUTEN

    forsok = b.borja_forsok(L.ANSLUT_IGEN, L.SOCKET_BRUTEN)
    assert forsok.kanskap == L.KAN_JA
    blick = B.blicka(b, klocka=lambda: 100.0)
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    assert _finns(text, "1 försök pågår")
    assert not _finns(text, Y.INGET_FORSOK)

    b.avsluta_forsok(forsok, True, "ping svarade: tick=41233")
    b.notera(B.Avlasning("bryggan", 100.0, True, kor=True))
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.lage("bryggan") == L.SIMULERING_IGANG
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    assert "lyckades" in text and "ping svarade: tick=41233" in text


def test_en_socket_som_gick_att_oppna_racker_inte_for_att_kalla_bryggan_levande():
    """Utan det andra svaret skrivs ingen orsak. En gissning här hade sagt
    *"bryggan svarar fortfarande"* om en brygga som är stendöd."""
    b = _levande()
    fel = ConnectionResetError(104, "Connection reset by peer")
    a = K.fran_bryggfel(b, fel, anslutning_oppnades=True,
                        svarade_efterat=None)
    assert a.orsak == ""
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.orsak("bryggan") is None
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    assert _finns(text, L.OKAND.text.split(".")[0])


# ------------------------------------------------- 3. OpenPLC svarar inte

def test_ett_fallet_kopplarvarv_ar_inte_en_dod_plc():
    from vc_assist_svc.plc import kopplare
    assert kopplare.MAX_RAKA_FEL == 3
    b = _levande()
    K.fran_kopplarvarv(b, _Varv(1, fel="OPC UA svarade inte inom 5.0 s"))
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.orsak("OpenPLC") is L.PLC_SVARAR_INTE
    # Det är fortfarande OpenPLC som inte svarar — men kopplaren har inte gett
    # upp, och orsaken säger uttryckligen att den räknar raka fel.
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    assert _finns(text, "ger upp vid tredje")


def test_kopplaren_ger_upp_och_ingenting_forsoker_igen():
    b = _levande()
    for nr in (1, 2, 3):
        K.fran_kopplarvarv(b, _Varv(nr, fel="OPC UA svarade inte"))
    K.fran_kopplarfel(b, RuntimeError(
        "kopplaren gav upp efter 3 raka fel; sista: OPC UA svarade inte"))
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.orsak("OpenPLC") is L.KOPPLAREN_GAV_UPP
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    assert _finns(text, Y.INGET_FORSOK)
    assert "kopplaren gav upp efter 3 raka fel" in text  # kopplarens egna ord
    # Ingen av vägarna lovar något: OpenPLC:s omstart är inte mätt. Raden
    # jämförs hel — `KAN_JA` är en delsträng av `KAN_NEJ`, och ett `in` mot
    # hela texten hade svarat fel åt båda hållen.
    assert L.KAN_JA not in [r.strip() for r in text.splitlines()]
    assert L.KAN_OKAND in [r.strip() for r in text.splitlines()]


# ------------------------- 4. modellen tar slut mitt i en reparation

def test_modellen_tar_slut_mitt_i_en_reparation():
    from vc_assist_svc.modellklient import Modellfel
    b = _levande()
    K.fran_modellfel(b, Modellfel("inspelningen tog slut efter 3 fragor"))
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.lage("modellen") == L.NERE
    assert blick.orsak("modellen") is L.MODELLEN_TOG_SLUT
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok
    assert "inspelningen tog slut efter 3 fragor" in text
    # Det som INTE kördes får inte se ut som något som höll.
    assert _finns(text, "kördes aldrig")


@pytest.mark.parametrize("utfall,vantad", [
    ("TYSTNAD", L.MODELLEN_TYSTNADE),
    ("TAK", L.REPARATIONSTAKET),
])
def test_slingans_utfall_blir_en_orsak_med_egna_ord(utfall, vantad):
    b = _levande()
    K.fran_reparationsprotokoll(b, _Protokoll(utfall))
    blick = B.blicka(b, klocka=lambda: 100.0)
    assert blick.orsak("modellen") is vantad
    text = Y.rendera(blick, LOGGAR)
    assert G.granska(blick, text, LOGGAR).ok


def test_taket_lovar_inte_att_ett_nytt_varv_hjalper():
    """`M-52` satte taket. Fler varv hade inte gett en annan dom, och ytan får
    inte antyda något annat."""
    assert L.kan_lyckas(L.REPARATIONSTAKET, L.NY_KORNING) == L.KAN_NEJ


# ------------------------------------------- de fyra sida vid sida

def test_de_fyra_dodsfallen_ser_olika_ut():
    """En yta som svarar samma sak på alla fyra svarar ingenting på någon."""
    texter = {}
    for namn, satt in (
            ("vc", lambda b: K.vc_avslutades(b, "ECONNRESET")),
            ("socket", lambda b: K.fran_bryggfel(
                b, ConnectionResetError(104, "reset"),
                anslutning_oppnades=True, svarade_efterat=True)),
            ("plc", lambda b: K.fran_kopplarfel(
                b, RuntimeError("kopplaren gav upp efter 3 raka fel"))),
            ("modell", lambda b: K.fran_modellfel(
                b, RuntimeError("modellen svarade inte")))):
        b = _levande()
        satt(b)
        blick = B.blicka(b, klocka=lambda: 100.0)
        texter[namn] = Y.rendera(blick, LOGGAR)
        assert G.granska(blick, texter[namn], LOGGAR).ok
    forsta = [t.splitlines()[0] for t in texter.values()]
    assert len(set(forsta)) == 3, forsta   # socket-fallet lever ju
    orsaksrader = [t.split("\n\n")[1] for t in texter.values()]
    assert len(set(orsaksrader)) == 4


def test_ingen_orsak_sager_att_ett_problem_uppstod():
    """`operatoren-behover-klarsprak`: säg saken, inte etiketten.

    Listan är de meningar som ser hjälpsamma ut och inte är det: de namnger
    ingenting, de går inte att agera på, och de låter likadant vare sig VC dog
    eller modellen tog slut.
    """
    tomma = ("ett problem uppstod", "något gick fel", "nagot gick fel",
             "försök igen senare", "ett fel inträffade", "oväntat fel")
    for o in L.ORSAKER:
        lag = o.text.lower()
        for fras in tomma:
            assert fras not in lag, "%s säger %r" % (o.nyckel, fras)
        assert o.text.endswith(".")
        assert len(o.text) > 40, "%s är för kort för att säga saken" % o.nyckel
        assert o.stampel, "%s har ingen härkomst" % o.nyckel


# --------------------------------------------------------- sonden

def test_sonden_fragar_i_stallet_for_att_gissa_ur_en_socket():
    from vc_assist_svc.klient import BryggFel
    b = B.Systembild(klocka=lambda: 100.0)

    def anslut_ok():
        return object()

    def ping_tyst(_f):
        raise BryggFel("E_TIMEOUT", "inget svar inom 3.0 s")

    a = K.sondera(b, anslut_ok, ping_tyst)
    assert a.svarade is False and a.anslutning_oppnades is True
    assert a.orsak == "timeout"
    assert B.lage_for(b, "bryggan", 100.0) == L.FRANKOPPLAD   # har aldrig svarat

    def anslut_nekas():
        raise ConnectionRefusedError(111, "Connection refused")

    a2 = K.sondera(b, anslut_nekas, ping_tyst)
    assert a2.svarade is None and a2.anslutning_oppnades is False
    assert a2.orsak == "port_upptagen"


def test_sonden_skriver_inte_om_ett_tyst_sim_till_ett_dodsbesked():
    from vc_assist_svc.klient import BryggFel
    b = B.Systembild(klocka=lambda: 100.0)
    a = K.sondera(b, lambda: object(), lambda _f: {"degraded": False},
                  sim=lambda _f: (_ for _ in ()).throw(
                      BryggFel("E_EXEC", "sim svarade inte")))
    assert a.svarade is True
    assert B.lage_for(b, "bryggan", 100.0) == L.ANSLUTEN


# ------------------------------------------------------- ut ur processen

def test_ytan_gar_att_lasa_ur_en_annan_process_och_aldras_mot_lasarens_klocka(
        tmp_path):
    """Den som ska berätta att systemet dog får inte bo i det som dog.

    Speglingen är fas 17:s, återanvänd: `Spegel` tar vilket objekt som helst
    med `till_json`. Läsaren räknar åldern mot SIN klocka, och en bild vars
    sond slutade skriva blir därför obestämd i stället för evigt ansluten.
    """
    p = tmp_path / "systembild.json"
    b = B.Systembild(klocka=lambda: 100.0)
    b.spegla(Spegel(str(p)))
    b.notera(B.Avlasning("bryggan", 100.0, True, kor=True))
    assert p.exists()

    fardsk = B.las_bild(str(p), klocka=lambda: 100.5)
    assert fardsk.lage("bryggan") == L.SIMULERING_IGANG
    assert G.granska(fardsk, None, LOGGAR).ok

    gammal = B.las_bild(str(p), klocka=lambda: 400.0)
    assert gammal.lage("bryggan") == L.OBESTAMT
    text = Y.rendera(gammal, LOGGAR)
    assert G.granska(gammal, text, LOGGAR).ok
    assert _finns(text, "300.0 s gammal")


def test_loggarna_som_inte_gar_att_lasa_blir_None_inte_tomma(tmp_path):
    kallor = K.loggarna(str(tmp_path))
    assert kallor == {K.BOOTLOGG: None, K.BRYGGLOGG: None}
    (tmp_path / K.BOOTLOGG).write_text("OnAppInitialized\n", encoding="utf-8")
    kallor = K.loggarna(str(tmp_path))
    assert kallor[K.BOOTLOGG] == "OnAppInitialized\n"
    assert kallor[K.BRYGGLOGG] is None
