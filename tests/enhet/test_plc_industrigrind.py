# -*- coding: utf-8 -*-
"""A7: grind 3b - tidsvakten, larmutgangen och forreglingen.

M-89 matte hallet: en modell som skriver kod som ATERGER inspelningen far
anda 0 av 2 mot manniskans facit, darfor att koden saknar tidsovervakningen,
larmen och forreglingarna. Det ar inte ett bankproblem utan ett produktfel -
koden ser ratt ut, kor ratt, och saknar allt som gor den industriell.

Provfilen ar skriven FORE mekanismen. Varje regel har

  * en TRASIG FIXTUR som ska falla, och
  * ett GRONT KONTROLLFALL som inte far falla.

Utan den andra halvan ser en grind som avvisar allt lika bra ut som en som
fangar ratt sak (M-89:s egen formulering om tackningsgrinden).
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bank import reparationsbank as RB                       # noqa: E402
from vc_assist_svc.plc import stationsgrind as SG            # noqa: E402
from vc_assist_svc.plc import industrigrind as IG            # noqa: E402
from vc_assist_svc.plc import forhandsregler as FR           # noqa: E402


# --------------------------------------------------------------- fixturen
#
# En liten station med allt tre reglerna behover: en kommenderad rorelse med
# sin kvittensingang, en larmutgang, och en forregling mellan ett don och en
# lagesgivare. Uppgiftsformen ar bankens egen (control.signals,
# control.interlocks, failure_modes), sa kraven lases pa samma vag i provet
# som i banken.

UPPGIFT = {
    "task_id": "X-01",
    "title": "Provstation for grind 3b",
    "failure_modes": [
        "styrningen vantar pa ST900_IDX_DONE utan tidsgrans, sa en fastnad "
        "matare star kvar tyst",
    ],
    "control": {
        "signals": [
            {"name": "ST900_CLP_CLOSE", "dir": "out", "type": "bool",
             "comment": "kommendera klamman till stangt lage"},
            {"name": "ST900_CLP_CLOSED", "dir": "in", "type": "bool",
             "comment": "lagesgivare, hog nar klamman haller"},
            {"name": "ST900_IDX_START", "dir": "out", "type": "bool",
             "comment": "kommendera ett index"},
            {"name": "ST900_IDX_DONE", "dir": "in", "type": "bool",
             "comment": "indexet klart"},
            {"name": "ST900_PRT_PRS", "dir": "in", "type": "bool",
             "comment": "detalj i stationen"},
            {"name": "EMG_OK", "dir": "in", "type": "bool",
             "comment": "nodstoppskretsen sluten"},
            {"name": "SYS_ALARM", "dir": "out", "type": "bool",
             "comment": "samlingslarm"},
        ],
        "interlocks": [
            "ST900_IDX_START far aldrig sta hog nar ST900_CLP_CLOSED ar lag",
        ],
    },
}

STATION = "ST900_PROV"


def _karta():
    return RB.karta_ur_uppgift(UPPGIFT, STATION)


def _krav():
    return IG.Krav.ur_uppgift(UPPGIFT, _karta())


# Signaldeklarationerna kommer ur KARTAN, inte ur handen: fixturen ska ga
# igenom grind 2 och 3 ocksa, sa att provet av grind 3b sager nagot om grind 3b
# och inte om en handskriven deklarationsrad.
_ARBETSVAR = """VAR
    steg     : INT;
    tmrIdx   : TON;
    xLarm    : BOOL;
    xIndex   : BOOL;
    xKlar    : BOOL;
END_VAR
"""


def _huvud(extra=""):
    return ("PROGRAM %s\n%s\n%s\n"
            % (STATION, _karta().deklarationstext(),
               _ARBETSVAR.replace("END_VAR", extra + "END_VAR")
               if extra else _ARBETSVAR))


def _kalla(kropp, extra=""):
    return _huvud(extra) + kropp + "\nEND_PROGRAM\n"


# Sekvensen ar densamma i alla sex fallen; bara den provade raden skiljer.
_SEKVENS = """
xKlar := EMG_OK AND NOT xLarm;
IF NOT xKlar THEN
    ST900_CLP_CLOSE := FALSE;
    xIndex := FALSE;
    steg := 0;
ELSE
    CASE steg OF
        0:
            IF ST900_PRT_PRS THEN
                ST900_CLP_CLOSE := TRUE;
                steg := 1;
            END_IF;
        1:
            IF ST900_CLP_CLOSED THEN
                xIndex := TRUE;
                steg := 2;
            END_IF;
        2:
            IF ST900_IDX_DONE THEN
                xIndex := FALSE;
                ST900_CLP_CLOSE := FALSE;
                steg := 0;
            END_IF;
    ELSE
        steg := 0;
    END_CASE;
END_IF;
"""

# Tidsvakten pa vantan i steg 2: kommandot ligger ute och kvittensen uteblir.
_VAKT = """
tmrIdx(IN := ST900_IDX_START AND NOT ST900_IDX_DONE, PT := T#2s);
IF tmrIdx.Q THEN
    xLarm := TRUE;
END_IF;
IF NOT ST900_PRT_PRS THEN
    xLarm := FALSE;
END_IF;
"""

_INGEN_VAKT = """
IF NOT ST900_PRT_PRS THEN
    xLarm := FALSE;
END_IF;
"""

_LARM_UT = "SYS_ALARM := xLarm;"
_INGET_LARM_UT = "SYS_ALARM := FALSE;"

_FORREGLAD = "ST900_IDX_START := xIndex AND ST900_CLP_CLOSED;"
_OFORREGLAD = "ST900_IDX_START := xIndex;"


def _bygg(vakt=_VAKT, larm=_LARM_UT, index=_FORREGLAD, extra=""):
    return _kalla(vakt + _SEKVENS + larm + "\n" + index, extra)


def _granska(kalla):
    return IG.granska(kalla, _karta(), _krav())


def _koder(rapport):
    return [a.kod for a in rapport.anmarkningar]


# ------------------------------------------------- regel 1: tidsvakten

def test_trasig_fixtur_vantan_utan_tidsgrans_falls():
    """En kommenderad rorelse utan tidsgrans ar en cell som hanger tyst."""
    r = _granska(_bygg(vakt=_INGEN_VAKT))
    assert "SAKNAD_TIDSVAKT" in _koder(r)
    assert not r.ok
    assert "ST900_IDX_DONE" in str(r)


def test_kontrollfall_vantan_med_tidsgrans_slapps_igenom():
    r = _granska(_bygg())
    assert "SAKNAD_TIDSVAKT" not in _koder(r)


def test_tidsvakt_pa_fel_signal_raknas_inte():
    """En TON som overvakar nagot annat ar ingen vakt pa den har vantan."""
    fel_vakt = _VAKT.replace("ST900_IDX_START AND NOT ST900_IDX_DONE",
                             "ST900_PRT_PRS AND NOT ST900_CLP_CLOSED")
    r = _granska(_bygg(vakt=fel_vakt))
    assert "SAKNAD_TIDSVAKT" in _koder(r)


def test_tidsvakt_med_noll_tid_ar_ingen_vakt():
    r = _granska(_bygg(vakt=_VAKT.replace("T#2s", "T#0s")))
    assert "SAKNAD_TIDSVAKT" in _koder(r)


def test_tidsvakt_vars_utfall_ingen_laser_ar_ingen_vakt():
    stum = _VAKT.replace("IF tmrIdx.Q THEN\n    xLarm := TRUE;\nEND_IF;", "")
    r = _granska(_bygg(vakt=stum))
    assert "SAKNAD_TIDSVAKT" in _koder(r)


# --------------------------------------------- regel 2: larmutgangen

def test_trasig_fixtur_feltillstand_utan_larmutgang_falls():
    """Ett feltillstand som bara satter en intern variabel syns for ingen."""
    r = _granska(_bygg(larm=_INGET_LARM_UT))
    assert "TYST_FELTILLSTAND" in _koder(r)
    assert not r.ok
    assert "xLarm" in str(r).lower() or "XLARM" in str(r)


def test_kontrollfall_feltillstand_som_nar_larmutgangen_slapps_igenom():
    r = _granska(_bygg())
    assert "TYST_FELTILLSTAND" not in _koder(r)


def test_negerat_bruk_av_feltillstandet_ar_ingen_larmutgang():
    """xLarm sparrar cellen men syns inte utat; sparren ar inte ett larm."""
    r = _granska(_bygg(larm="SYS_ALARM := NOT xLarm;"))
    assert "TYST_FELTILLSTAND" in _koder(r)


# --------------------------------------------- regel 3: forreglingen

def test_trasig_fixtur_don_utan_forregling_falls():
    r = _granska(_bygg(index=_OFORREGLAD))
    assert "SAKNAD_FORREGLING" in _koder(r)
    assert not r.ok
    assert "ST900_CLP_CLOSED" in str(r)


def test_kontrollfall_forreglat_don_slapps_igenom():
    r = _granska(_bygg())
    assert "SAKNAD_FORREGLING" not in _koder(r)


def test_forregling_genom_ren_mellanvariabel_slapps_igenom():
    """Samma uteslutningsdoktrin som M-121: rena mellanvariabler foljs."""
    kropp = (_VAKT + _SEKVENS + _LARM_UT + "\n"
             + "xSpant := ST900_CLP_CLOSED;\n"
             + "ST900_IDX_START := xIndex AND xSpant;")
    r = _granska(_kalla(kropp, "    xSpant   : BOOL;\n"))
    assert "SAKNAD_FORREGLING" not in _koder(r)


# ------------------------------------------------ hela grinden gron/rod

def test_hela_fixturen_gron_nar_alla_tre_finns():
    r = _granska(_bygg())
    assert r.ok, str(r)


def test_grinden_matter_sin_egen_storhet():
    """En grind som blir billig slutar mata sin egen storhet (M-111).

    Kontrollerade grinden noll saker har den inte matt nagot, och da ar
    svaret inte 'godkand' heller.
    """
    r = _granska(_bygg())
    assert r.matt["tidsvaktkrav"] >= 1
    assert r.matt["forreglingar"] >= 1
    assert r.matt["feltillstand"] >= 1


# ------------------------------------------------- reglerna nar modellen

def test_varje_kontroll_har_en_regel_i_systemprompten():
    """Samma falla som saknade_regler(): en kod utan regel ar en grind som
    faller pa nagot modellen aldrig fatt veta."""
    assert FR.saknade_regler() == ()


def test_ingen_foraldralos_regel():
    assert FR.foraldralosa_regler() == ()


def test_reglerna_star_i_promptexten():
    text = FR.text()
    for kod in IG.KONTROLLER_INDUSTRI:
        assert kod in text, kod


# ------------------------------------ banken: alla referenser genom grinden
#
# Falls en referens falls modellen pa samma sak, och varje sadan traff branner
# ett reparationsvarv (M-96: nio av sexton domar var var egen bugg). Domen per
# fall star i docs/matningar/M-159 och i KANDA_BRISTER nedan.

# task_id -> (vad grinden sager, domen). BADA referenserna bar samma brist:
# en forregling pa en INGANG som bara halls av att sekvensen kontrollerade den
# i ett tidigare steg. En ingang kan andra sig mitt i steget - det ar precis
# M-89:s "klamman slapper mitt i indexet" - sa sekvensens garanti racker inte.
# Formen ar densamma som M-121 skrev om fyra referenser till: en skrivning,
# forreglingen i uttrycket.
#
# Referenserna ar INTE rattade har: bank/uppgifter ar ko B:s yta, och en andrad
# referens andrar sitt eget spar. Bristen ar rapporterad, inte lagad.
KANDA_BRISTER = {
    "A-07": ("ST470_ARC_ON kan vara hog nar ST470_CLP_CLOSED ar lag",
             "verklig brist: ST470_ARC_ON := xBage AND ST470_GAS_ON saknar "
             "AND ST470_CLP_CLOSED. Uppgiftens egen interlockrad kraver det, "
             "och slapper spannaren mitt i svetsen brinner bagen vidare."),
    "C-06": ("ST560_RB_START kan vara hog nar ST560_DOR_OPENED ar lag och "
             "ST570_DOR_OPENED ar lag",
             "verklig brist: ST560_RB_START := xDrift AND (xStart1 OR xStart2) "
             "saknar AND (ST560_DOR_OPENED OR ST570_DOR_OPENED). Luckans "
             "lagesgivare provas i steg 1 och slapps sedan; faller den medan "
             "roboten ar inne star startsignalen kvar."),
}


def _referenser():
    return RB.uppgifter_med_sparfacit()


def _dom(post):
    station, _extra, _kropp = RB.dela_referens(post["facit_spar"]["referens"])
    karta = RB.karta_ur_uppgift(post, station)
    krav = IG.Krav.ur_uppgift(post, karta)
    return IG.granska(post["facit_spar"]["referens"], karta, krav), karta, krav


@pytest.mark.parametrize("post", _referenser(),
                         ids=[p["task_id"] for p in _referenser()])
def test_referensen_gar_igenom_grind_3b(post):
    r, _karta, _krav = _dom(post)
    if post["task_id"] in KANDA_BRISTER:
        # En kand brist ska fortsatta falla, och pa SAMMA sak. Blir den gron
        # har nagon lagat referensen - da ska raden tas bort har.
        vantad = KANDA_BRISTER[post["task_id"]][0]
        assert not r.ok, "%s ar gron; ta bort den ur KANDA_BRISTER" % post["task_id"]
        assert vantad in str(r), str(r)
        return
    assert r.ok, "%s: %s" % (post["task_id"], r)


def test_bara_de_kanda_bristerna_falls():
    """Talet i M-159, last: exakt tva av bankens referenser falls."""
    roda = [p["task_id"] for p in _referenser() if not _dom(p)[0].ok]
    assert sorted(roda) == sorted(KANDA_BRISTER)


# ------------------------- mutationer: den grona referensen ar en matning
#
# En grind som slapper igenom allt ser lika bra ut som en som fangar ratt sak,
# om man bara raknar godkannanden (M-89:s egen formulering). Tas forreglingen,
# tidsvakten eller larmvagen BORT ur en referens ska grinden bli rod igen.

MUTATIONER = (
    ("A-04", "SAKNAD_FORREGLING",
     "ST270_PRS_DOWN := xNed AND ST270_SAF_OK AND EMG_OK AND AIR_OK AND NOT xSparr;",
     "ST270_PRS_DOWN := xNed AND EMG_OK AND AIR_OK AND NOT xSparr;"),
    ("A-05", "SAKNAD_FORREGLING",
     "ST280_WLD_START := xSvet AND ST280_GUN_CLOSED AND EMG_OK AND AIR_OK;",
     "ST280_WLD_START := xSvet AND EMG_OK AND AIR_OK;"),
    ("A-05", "SAKNAD_FORREGLING",
     "ST280_GUN_CLOSE := xPistol AND ST280_PRT_PRS AND EMG_OK AND AIR_OK;",
     "ST280_GUN_CLOSE := xPistol AND EMG_OK AND AIR_OK;"),
    ("T-07", "SAKNAD_TIDSVAKT",
     "tmrIndex(IN := ST050_IDX_START, PT := T#2s);",
     "tmrIndex(IN := ST050_CNV_RUN, PT := T#2s);"),
    ("T-07", "TYST_FELTILLSTAND",
     "SYS_ALARM := xLarm;",
     "SYS_ALARM := FALSE;"),
)


@pytest.mark.parametrize("task_id,kod,fran,till", MUTATIONER,
                         ids=["%s:%s:%d" % (m[0], m[1], i)
                              for i, m in enumerate(MUTATIONER)])
def test_mutationen_som_tar_bort_skyddet_falls(task_id, kod, fran, till):
    post = dict((p["task_id"], p) for p in _referenser())[task_id]
    referens = post["facit_spar"]["referens"]
    assert fran in referens, "mutationens text finns inte i %s" % task_id
    station, _e, _k = RB.dela_referens(referens)
    karta = RB.karta_ur_uppgift(post, station)
    krav = IG.Krav.ur_uppgift(post, karta)
    r = IG.granska(referens.replace(fran, till), karta, krav)
    assert kod in [a.kod for a in r.anmarkningar], "%s: %s" % (task_id, r)


# ---------------------------------------------- prosaparsern mot ett facit

def test_prosaparsern_mot_invarianterna():
    """Instrumentet mot ett kant svar.

    `control.interlocks` ar klartext; `facit_spar.invarianter` ar samma
    forreglingar i maskinlasbar form. Parsern far lasa FARRE rader an
    invarianterna beskriver, men den far aldrig lasa en rad BAKVANT: en
    omvand forregling ar en falsk rodgrind pa en riktig losning, och tva
    sadana fanns (S-07 och T-04, M-159 §4).
    """
    fel = []
    for post in _referenser():
        station, _e, _k = RB.dela_referens(post["facit_spar"]["referens"])
        karta = RB.karta_ur_uppgift(post, station)
        inv = set((f.nar, f.kraver) for f in IG._ur_invarianter(post, karta))
        for f in IG._ur_interlocktext(post, karta):
            (n0, v0), = f.nar
            (k0, w0), = f.kraver
            # Motsatsen till en riktig lasning: samma par, omvand polaritet.
            omvand = (((n0, not v0),), ((k0, w0),))
            omvand2 = (((k0, not w0),), ((n0, v0),))
            if omvand in inv or omvand2 in inv:
                fel.append("%s: %s -> %s" % (post["task_id"], f.nar, f.kraver))
    assert fel == [], fel


# ------------------------------------------- inkopplingen i grindkedjan

def test_stationsgrinden_kor_grind_3b_bara_nar_krav_lamnas():
    """Utan `krav` ska domen vara bit for bit den forra.

    Skalet ar mekaniskt: guldgrinden raknar "alla fyra korda och alla fyra
    True". En femte nyckel i KORORDNING hade gjort varje befintlig cell rod
    over en natt, sa grind 3b ligger UTANFOR den listan och rakans in bara nar
    den kort.
    """
    kandidat = SG.Kandidat(STATION, _bygg())
    utan = SG.granska_station(kandidat, _karta())
    assert SG.NAMN_INDUSTRI not in utan.forgrindar
    assert SG.NAMN_INDUSTRI not in SG.KORORDNING

    med = SG.granska_station(kandidat, _karta(), krav=_krav())
    assert med.forgrindar[SG.NAMN_INDUSTRI] is True


def test_stationsgrinden_faller_pa_grind_3b():
    kandidat = SG.Kandidat(STATION, _bygg(index=_OFORREGLAD))
    dom = SG.granska_station(kandidat, _karta(), krav=_krav())
    assert dom.forgrindar[SG.NAMN_INDUSTRI] is not True
    assert "SAKNAD_FORREGLING" in dom.forgrindar[SG.NAMN_INDUSTRI]
    assert not dom.ok
    assert dom.forsta_fallande == SG.NAMN_INDUSTRI
    assert "ST900_CLP_CLOSED" in dom.text()
