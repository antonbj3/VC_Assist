# -*- coding: utf-8 -*-
"""M-176 (ko A, punkt A10): flanken over skanngransen, pa BADA motorerna.

Den klassiskt svaraste buggen i PLC-kod ar att en flankdetektor konsumeras av
den FORSTA som laser den. `R_TRIG` har ett minne som uppdateras vid anropet:
anropas samma instans tva ganger i samma scan ar `Q` sann efter det forsta
anropet och falsk efter det andra. Vilken av tva konsumenter som far flanken
avgors alltsa av SATSORDNINGEN, inte av logiken.

Samma sak i sin andra form: `IF villkor THEN larm := TRUE; END_IF;` foljt av
`IF kvittens THEN larm := FALSE; END_IF;` ar reset-dominant, och byter man de
tva satserna blir den set-dominant. Bada raderna ar riktiga var for sig; det
ar ordningen som avgor om ett kvarstaende fel gar att kvittera bort.

Projektet har aldrig provat nagot av det. Korningen bygger fyra texter i
bankens form - en referens och tre motbevis over tva uppgifter - och domer dem
genom BADA motorerna: var ST-tolk (`bank/domare.py`) och OpenPLC Runtime v4
(`bank/domare_openplc.py`).

Uppgifterna ligger med avsikt HAR och inte i `bank/uppgifter/`: banken agas av
en annan ko och vaxer just nu. De ar skrivna i bankens form och gar att lyfta
in rakt av.

## Formen: n >= 3 pa OpenPLC-domaren

`M-153` matte att OpenPLC-domaren ar oense med SIG SJALV i 13 av 185 enheter
(7,0 %), varav 4 byter utfall. En korning ar darfor inget svar. Varje enhet
kors `--n` ganger (3 som standard) och en enhet med delade utfall redovisas som
INSTABIL, aldrig som gron och aldrig som rod.

## De trasiga fallen

1. **Referensen maste bli GRON hos bada.** Ett facit som inte ens referensen
   uppfyller faller alla.
2. **Motbevisen maste bli RODA hos bada, pa sin namngivna brist.** Ett
   motbevis som gar igenom mater ingenting.
3. **De tva spegelvanda motbevisen maste falla pa OLIKA brist.**
   `en_instans_tva_anrop_A` tappar UT_B och `..._B` tappar UT_A. Faller de pa
   samma kod har ordningen inte spelat nagon roll, och da ar uppgiften fel
   byggd - inte motorerna oense.

Kors:

    VC_ASSIST_STRUCPP_PAKET=... nice -n 19 ionice -c3 \\
      python3 tests/protocol/kor_A10_flanken.py --n 3 \\
        --jsonl docs/matningar/radata/m176_svep.jsonl \\
        --json docs/matningar/radata/m176_sammanstallning.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
for _p in (_HAR, os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BANKPOST = {
    "pastar": (
        "En R_TRIG-instans som anropas tva ganger i samma scan ger flanken "
        "till den FORSTA lasaren, och en set/reset-latch byter dominans nar "
        "satserna byter plats - och var ST-tolk och OpenPLC Runtime v4 ar "
        "eniga om bada, eller sa pekas oenigheten ut med bristkod per motor."),
    "under_prov": ("svc/vc_assist_svc/st/tolk.py", "bank/domare.py"),
    "facit": (
        "Handskrivna uppgifter i bankens form med facit raknat for hand fore "
        "korningen: fyra pulser pa KNAPP ska ge fyra rakningar hos BADA "
        "konsumenterna, och ett kvarstaende fel far inte ga att kvittera bort."),
    "facitkalla": (
        "OpenPLC Runtime v4.2.1 som andra motor (laglig kalla 1) mot ett "
        "manniskoskrivet facit (laglig kalla 4); facit ligger i korningen och "
        "aldrig i nagon av motorerna"),
    "facitkalla_filer": (),
    "trasiga_fall": (
        "referensen maste bli GRON hos bada motorerna - annars ar facit inte "
        "uppfyllbart och faller alla",
        "varje motbevis maste bli ROTT hos bada motorerna pa sin NAMNGIVNA "
        "brist",
        "de tva spegelvanda motbevisen maste falla pa OLIKA bristkod; samma "
        "kod betyder att satsordningen inte spelade nagon roll och att "
        "uppgiften ar fel byggd",
        "en enhet med delade utfall over n korningar redovisas som INSTABIL, "
        "aldrig som gron",
        "noll korda enheter ger returkod != 0",
    ),
    "kraver": ("openplc", "strucpp"),
    "matningar": ("M-176", "M-153"),
}

import domare as D                                  # noqa: E402


# ------------------------------------------------------------- uppgift 1
#
# En R_TRIG-instans, tva konsumenter. KNAPP pulsar fyra ganger; bada
# raknarna ska sta pa 4.
#
# Rakningen for hand, fore korningen: KNAPP gar hog vid 200, 600, 1000 och
# 1400 ms och lag 200 ms senare varje gang. Vid 20 ms scan ger det exakt fyra
# RISE. Referensen har EN detektor per konsument och racknar 4 + 4. Motbevisen
# delar en instans, och da far bara den FORSTA konsumenten flanken.

_FLANK_SIGNALER = [
    {"name": "KNAPP", "type": "bool", "dir": "in"},
    {"name": "UT_A", "type": "int", "dir": "out"},
    {"name": "UT_B", "type": "int", "dir": "out"},
]

REFERENS_FLANK = """PROGRAM Flankdelningen
VAR
    detA : R_TRIG;
    detB : R_TRIG;
    nA   : INT := 0;
    nB   : INT := 0;
END_VAR

(* En detektor per konsument. Det ar den enda formen som haller nar tva
   delar av logiken behover samma flank: instansens minne ar privat. *)
detA(CLK := KNAPP);
IF detA.Q THEN
    nA := nA + 1;
END_IF;

detB(CLK := KNAPP);
IF detB.Q THEN
    nB := nB + 1;
END_IF;

UT_A := nA;
UT_B := nB;
END_PROGRAM
"""

MOTBEVIS_A_FORST = """PROGRAM Flankdelningen
VAR
    det : R_TRIG;
    nA  : INT := 0;
    nB  : INT := 0;
END_VAR

(* EN instans, tva anrop i samma scan. Det andra anropet uppdaterar minnet
   igen, sa Q ar redan falsk nar den andra konsumenten laser den. *)
det(CLK := KNAPP);
IF det.Q THEN
    nA := nA + 1;
END_IF;

det(CLK := KNAPP);
IF det.Q THEN
    nB := nB + 1;
END_IF;

UT_A := nA;
UT_B := nB;
END_PROGRAM
"""

MOTBEVIS_B_FORST = """PROGRAM Flankdelningen
VAR
    det : R_TRIG;
    nA  : INT := 0;
    nB  : INT := 0;
END_VAR

(* Samma fel, speglat: nu ar det B som far flanken och A som blir utan.
   Texterna skiljer sig bara i ordningen mellan de tva IF-satserna. *)
det(CLK := KNAPP);
IF det.Q THEN
    nB := nB + 1;
END_IF;

det(CLK := KNAPP);
IF det.Q THEN
    nA := nA + 1;
END_IF;

UT_A := nA;
UT_B := nB;
END_PROGRAM
"""

FLANKUPPGIFTEN = {
    "task_id": "A10-FLANK",
    "control": {"signals": _FLANK_SIGNALER},
    "facit_spar": {
        "scan_ms": 20,
        "referens": REFERENS_FLANK,
        "sekvenser": [{
            "id": "fyra_tryck_tva_konsumenter",
            "steg": [
                {"t_ms": 0, "satt": {"KNAPP": False}, "krav": {},
                 "varfor": "utgangslage"},
                {"t_ms": 200, "satt": {"KNAPP": True}, "krav": {}},
                {"t_ms": 400, "satt": {"KNAPP": False}, "krav": {}},
                {"t_ms": 600, "satt": {"KNAPP": True}, "krav": {}},
                {"t_ms": 800, "satt": {"KNAPP": False},
                 "krav": {"UT_A": 2, "UT_B": 2},
                 "varfor": "tva tryck; BADA konsumenterna har sett bada"},
                {"t_ms": 1000, "satt": {"KNAPP": True}, "krav": {}},
                {"t_ms": 1200, "satt": {"KNAPP": False}, "krav": {}},
                {"t_ms": 1400, "satt": {"KNAPP": True}, "krav": {}},
                {"t_ms": 1600, "satt": {"KNAPP": False}, "krav": {}},
                {"t_ms": 1800, "satt": {},
                 "krav": {"UT_A": 4, "UT_B": 4},
                 "varfor": "fyra tryck, fyra rakningar hos bada"},
            ],
        }],
        "flanker": [],
        "invarianter": [],
        "motbevis": [
            {"namn": "en_instans_tva_anrop_a_forst", "st": MOTBEVIS_A_FORST,
             "faller_pa": ["fyra_tryck_tva_konsumenter@800ms:UT_B",
                           "fyra_tryck_tva_konsumenter@1800ms:UT_B"]},
            {"namn": "en_instans_tva_anrop_b_forst", "st": MOTBEVIS_B_FORST,
             "faller_pa": ["fyra_tryck_tva_konsumenter@800ms:UT_A",
                           "fyra_tryck_tva_konsumenter@1800ms:UT_A"]},
        ],
    },
}


# ------------------------------------------------------------- uppgift 2
#
# Dominansen i en latch avgors av satsordningen, och skillnaden ar DURABEL sa
# lange bada villkoren star hoga - alltsa matbar over manga scan och inte
# beroende av att tva stimuli landar i samma scan (M-153 §4c: provtagningen
# racker inte for enskansfenomen).
#
# Rakningen for hand: FEL gar hog vid 200 ms och star kvar. KVITT gar hog vid
# 600 ms och star kvar. Ett kvarstaende fel far INTE ga att kvittera bort -
# larmet ska sta hogt sa lange FEL star hogt. Referensen skriver kvittensen
# FORST och larmet SIST (set-dominant). Motbeviset byter de tva raderna.

_LATCH_SIGNALER = [
    {"name": "FEL", "type": "bool", "dir": "in"},
    {"name": "KVITT", "type": "bool", "dir": "in"},
    {"name": "UT_LARM", "type": "bool", "dir": "out"},
]

REFERENS_LATCH = """PROGRAM Dominansen
VAR
    larm : BOOL := FALSE;
END_VAR

(* Kvittensen forst, larmet sist: SET dominerar. Ett fel som star kvar gar
   inte att kvittera bort, och det ar hela poangen med en larmlatch. *)
IF KVITT THEN
    larm := FALSE;
END_IF;
IF FEL THEN
    larm := TRUE;
END_IF;

UT_LARM := larm;
END_PROGRAM
"""

MOTBEVIS_LATCH = """PROGRAM Dominansen
VAR
    larm : BOOL := FALSE;
END_VAR

(* Samma tva satser, ombytta: RESET dominerar. En operator som haller
   kvittensknappen intryckt slacker larmet trots att felet star kvar. *)
IF FEL THEN
    larm := TRUE;
END_IF;
IF KVITT THEN
    larm := FALSE;
END_IF;

UT_LARM := larm;
END_PROGRAM
"""

LATCHUPPGIFTEN = {
    "task_id": "A10-DOMINANS",
    "control": {"signals": _LATCH_SIGNALER},
    "facit_spar": {
        "scan_ms": 20,
        "referens": REFERENS_LATCH,
        "sekvenser": [{
            "id": "kvittens_pa_kvarstaende_fel",
            "steg": [
                {"t_ms": 0, "satt": {"FEL": False, "KVITT": False},
                 "krav": {}, "varfor": "utgangslage"},
                {"t_ms": 200, "satt": {"FEL": True}, "krav": {}},
                {"t_ms": 400, "satt": {},
                 "krav": {"UT_LARM": True},
                 "varfor": "felet har kommit; larmet ska sta"},
                {"t_ms": 600, "satt": {"KVITT": True}, "krav": {}},
                {"t_ms": 1000, "satt": {},
                 "krav": {"UT_LARM": True},
                 "varfor": "kvittens pa ett KVARSTAENDE fel far inte slacka "
                           "larmet"},
                {"t_ms": 1400, "satt": {},
                 "krav": {"UT_LARM": True},
                 "varfor": "och den far inte gora det efter en stund heller"},
            ],
        }],
        "flanker": [],
        "invarianter": [],
        "motbevis": [
            {"namn": "kvittensen_slacker_ett_kvarstaende_fel",
             "st": MOTBEVIS_LATCH,
             "faller_pa": ["kvittens_pa_kvarstaende_fel@1000ms:UT_LARM",
                           "kvittens_pa_kvarstaende_fel@1400ms:UT_LARM"]},
        ],
    },
}

UPPGIFTER = [FLANKUPPGIFTEN, LATCHUPPGIFTEN]


def enheter(post):
    fs = post["facit_spar"]
    ut = [("referens", fs["referens"], [])]
    for mb in fs["motbevis"]:
        ut.append(("motbevis:" + mb["namn"], mb["st"], list(mb["faller_pa"])))
    return ut


# --------------------------------------------------------------- korningen

def kor_tolk(post, st_text):
    t = time.time()
    try:
        d = D.dom(post, st_text)
        return {"utfall": "GODKAND" if d.godkand else "UNDERKAND",
                "koder": sorted(d.koder),
                "texter": [b.text[:300] for b in d.brister],
                "sekunder": round(time.time() - t, 2)}
    except D.Domsfel as fel:
        return {"utfall": "DOMSFEL", "koder": [], "skal": str(fel)[:600],
                "sekunder": round(time.time() - t, 2)}


def kor_openplc(post, st_text, rigg, byggkatalog):
    import domare_openplc as DO
    t = time.time()
    try:
        d = DO.dom(post, st_text, rigg=rigg, byggkatalog=byggkatalog)
        return {"utfall": "GODKAND" if d.godkand else "UNDERKAND",
                "koder": sorted(d.koder),
                "texter": [b.text[:300] for b in d.brister],
                "sekunder": round(time.time() - t, 2)}
    except DO.Domsfel as fel:
        return {"utfall": "DOMSFEL", "koder": [], "skal": str(fel)[:600],
                "sekunder": round(time.time() - t, 2)}


def svep(args):
    import domare_openplc as DO
    rigg = DO.Rigg()
    rigg.kontrollera()
    ut = open(args.jsonl, "a", encoding="utf-8") if args.jsonl else None
    rader = []
    for post in UPPGIFTER:
        for etikett, st_text, faller_pa in enheter(post):
            for varv in range(1, args.n + 1):
                rad = {"task": post["task_id"], "etikett": etikett,
                       "varv": varv, "faller_pa": faller_pa,
                       "tolk": kor_tolk(post, st_text)}
                if not args.bara_tolk:
                    rad["openplc"] = kor_openplc(post, st_text, rigg,
                                                 args.byggkatalog)
                rader.append(rad)
                if ut:
                    ut.write(json.dumps(rad, ensure_ascii=False) + "\n")
                    ut.flush()
                    os.fsync(ut.fileno())
                print("  %-13s %-38s varv %d  tolk=%-10s openplc=%s"
                      % (post["task_id"], etikett, varv,
                         rad["tolk"]["utfall"],
                         rad.get("openplc", {}).get("utfall", "-")))
    if ut:
        ut.close()
    return sammanstall(rader, args)


def _slaihop(korningar):
    """En enhets dom over n korningar. Delade utfall => INSTABIL."""
    utfall = set(k["utfall"] for k in korningar)
    koder = set(tuple(sorted(k["koder"])) for k in korningar)
    if len(utfall) > 1:
        return "INSTABIL", sorted(utfall), []
    if len(koder) > 1:
        return "%s_INSTABILA_KODER" % utfall.pop(), [], sorted(koder)
    return utfall.pop(), [], sorted(koder)


def sammanstall(rader, args):
    enhetsrader = {}
    for r in rader:
        enhetsrader.setdefault((r["task"], r["etikett"]), []).append(r)

    resultat = {"enheter": {}, "n": args.n}
    print("\n=== per enhet, n = %d ===" % args.n)
    for (task, etikett), lista in sorted(enhetsrader.items()):
        tolk = _slaihop([r["tolk"] for r in lista])
        post = {"task": task, "etikett": etikett,
                "faller_pa": lista[0]["faller_pa"],
                "tolk_utfall": tolk[0],
                "tolk_koder": sorted(set(
                    k for r in lista for k in r["tolk"]["koder"])),
                "tolk_texter": lista[0]["tolk"].get("texter", [])}
        if "openplc" in lista[0]:
            oplc = _slaihop([r["openplc"] for r in lista])
            post["openplc_utfall"] = oplc[0]
            post["openplc_koder"] = sorted(set(
                k for r in lista for k in r["openplc"]["koder"]))
            post["openplc_texter"] = lista[0]["openplc"].get("texter", [])
            post["eniga_om_utfall"] = (post["tolk_utfall"]
                                       == post["openplc_utfall"])
            post["eniga_om_koder"] = (post["tolk_koder"]
                                      == post["openplc_koder"])
        resultat["enheter"]["%s/%s" % (task, etikett)] = post
        print("  %-13s %-38s tolk=%-12s openplc=%s"
              % (task, etikett, post["tolk_utfall"],
                 post.get("openplc_utfall", "-")))

    fel = 0
    print("\n--- trasiga fallen ---")
    for post in resultat["enheter"].values():
        namn = "%s/%s" % (post["task"], post["etikett"])
        if post["etikett"] == "referens":
            for motor in ("tolk", "openplc"):
                nyckel = motor + "_utfall"
                if nyckel in post and post[nyckel] != "GODKAND":
                    print("  REFERENSEN FOLL hos %s: %s -> %s"
                          % (motor, namn, post[nyckel]))
                    fel = 1
            continue
        for motor in ("tolk", "openplc"):
            nyckel = motor + "_utfall"
            if nyckel not in post:
                continue
            if not post[nyckel].startswith("UNDERKAND"):
                print("  MOTBEVISET GICK IGENOM hos %s: %s -> %s"
                      % (motor, namn, post[nyckel]))
                fel = 1
                continue
            saknas = [k for k in post["faller_pa"]
                      if k not in post[motor + "_koder"]]
            if saknas:
                print("  %s foll hos %s men INTE pa sin namngivna brist: "
                      "saknar %s" % (namn, motor, ", ".join(saknas)))
                fel = 1

    # Spegelkontrollen: de tva flankmotbevisen maste falla pa OLIKA kod.
    a = resultat["enheter"].get("A10-FLANK/motbevis:en_instans_tva_anrop_a_forst")
    b = resultat["enheter"].get("A10-FLANK/motbevis:en_instans_tva_anrop_b_forst")
    if a and b:
        for motor in ("tolk", "openplc"):
            ka = set(a.get(motor + "_koder") or [])
            kb = set(b.get(motor + "_koder") or [])
            if not ka or not kb:
                continue
            print("  spegelkontroll (%s): A faller pa %s, B pa %s"
                  % (motor, ",".join(sorted(ka)), ",".join(sorted(kb))))
            if ka == kb:
                print("  SPEGELKONTROLLEN FOLL hos %s: samma bristkod, "
                      "alltsa spelade satsordningen ingen roll" % motor)
                fel = 1

    oeniga = [n for n, p in resultat["enheter"].items()
              if "eniga_om_utfall" in p and not p["eniga_om_utfall"]]
    kodoeniga = [n for n, p in resultat["enheter"].items()
                 if p.get("eniga_om_utfall") and not p["eniga_om_koder"]]
    resultat["utfallsoeniga"] = sorted(oeniga)
    resultat["kodoeniga"] = sorted(kodoeniga)
    print("\n=== motorerna mot varandra ===")
    print("  utfallsoenighet: %d av %d enheter %s"
          % (len(oeniga), len(resultat["enheter"]), oeniga or ""))
    print("  kodoenighet:     %d av %d enheter %s"
          % (len(kodoeniga), len(resultat["enheter"]), kodoeniga or ""))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=1,
                      sort_keys=True)
    if not resultat["enheter"]:
        print("noll korda enheter")
        return 1
    return fel


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-176: flanken over skanngransen")
    ap.add_argument("--n", type=int, default=3,
                    help="korningar per enhet; M-153 kraver n >= 3")
    ap.add_argument("--bara-tolk", action="store_true",
                    help="hoppa over OpenPLC (for att prova facit)")
    ap.add_argument("--byggkatalog")
    ap.add_argument("--jsonl")
    ap.add_argument("--json")
    return svep(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
