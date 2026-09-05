# -*- coding: utf-8 -*-
"""M-169 (ko A, punkt A8): vad OpenPLC-kedjan gor som standarden inte sager.

Fyra omraden dar IEC 61131-3 antingen tiger eller lamnar utfallet till
implementationen, och dar var ST-tolk darfor kan sta ensam med en semantik
ingen motor har: **heltalsspill, division med noll, TIME-aritmetik over
dygnsgransen och strangar over sin deklarerade langd**.

For varje fall tre kolumner:

  * **standard** - vad IEC 61131-3 sager. Repot har INGEN kopia av standarden,
    sa varje rad ar antingen BELAGT (matiecs egna ord, citerade) eller
    OPROVAD PARAGRAF. Ett "bor fungera" ar inget belagg; M-125 satte den
    konventionen och den star kvar.
  * **matiec** - iec2c, OpenPLC:s egen IEC-kompilator, typauktoriteten sedan
    M-121. Kord i strikt lage (`-f`, inga avslappnande flaggor).
  * **tolken** - `svc/vc_assist_svc/st/tolk.py`, kord ett scan.

Klassningen ar den fran M-125 och `tests/enhet/test_plc_matiec.py`:
OVERENS, MATIEC_STRANGARE (farligast: var grind slapper det kedjan faller),
VI_STRANGARE, och - ny har - EJ_JAMFORBAR nar matiec inte ens kan uttrycka
konstruktionen.

Trasiga fallen, bada FORE mekanismen:

  1. `i : INT := 40000;` MASTE komma ut som MATIEC_STRANGARE. Tolken tar emot
     40000 i en 16-bitars INT utan ett ord; matiec avvisar med "Initial value
     has incompatible data type". Rapporterar korningen det som OVERENS ar
     jamforelsen trasig och inte motorerna.
  2. `i := 32766 + 1;` MASTE komma ut som OVERENS (bada godkanner). Utan ett
     kontrollfall som INTE divergerar mater svepet bara sin egen stranghet.

Kors:

    nice -n 19 ionice -c3 python3 tests/protocol/kor_A8_avvikelserna.py \\
        --json docs/matningar/radata/m169_avvikelser.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BANKPOST = {
    "pastar": (
        "OpenPLC-kedjans kompilator och var ST-tolk gar isar pa fyra omraden "
        "som IEC 61131-3 lamnar oreglerade eller implementationsberoende - "
        "heltalsspill, division med noll, TIME over dygnsgransen och strangar "
        "over deklarerad langd - och varje skillnad gar att peka ut med "
        "konstruktion, matiecs egna ord och tolkens varde."),
    "under_prov": ("svc/vc_assist_svc/st/tolk.py",
                   "svc/vc_assist_svc/st/validator.py"),
    "facit": (
        "matiec (iec2c) i strikt lage - OpenPLC:s egen IEC 61131-3-kompilator, "
        "skriven av nagon annan - plus handrakning av vad standarden lamnar "
        "oreglerat. Standardkolumnen ar BELAGT bara nar matiec sjalv sager "
        "det; annars OPROVAD PARAGRAF."),
    "facitkalla": (
        "matiec 0.1 ur OpenPLC:s docker-avbild (wzy318/openplc:latest), "
        "kord genom svc/vc_assist_svc/plc/matiec.py - en annan implementation, "
        "utanfor koden som provas"),
    "facitkalla_filer": ("svc/vc_assist_svc/plc/matiec.py",),
    "trasiga_fall": (
        "i : INT := 40000 MASTE klassas MATIEC_STRANGARE - tolken tar emot "
        "vardet, matiec avvisar det; blir det OVERENS ar jamforelsen trasig",
        "i := 32766 + 1 MASTE klassas OVERENS - ett svep utan ett fall som "
        "INTE divergerar mater bara sin egen stranghet",
        "noll korda fall ger returkod != 0",
    ),
    "kraver": ("openplc",),
    "matningar": ("M-169",),
}

from vc_assist_svc.plc import matiec as M      # noqa: E402
from vc_assist_svc.st import tolk as TK        # noqa: E402

KONFIGURATION = """
CONFIGURATION Conf
  RESOURCE Res ON PLC
    TASK T(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM Inst WITH T : Main;
  END_RESOURCE
END_CONFIGURATION
"""

# OPROVAD PARAGRAF = repot har ingen kopia av IEC 61131-3 och kan inte citera
# den. BELAGT = kompilatorn sager det sjalv, och citatet star i utfallet.
OPROVAD = "OPROVAD PARAGRAF"

# (namn, grupp, dekl, kropp, las, standard, forvantat)
FALL = [
    # ---------------------------------------------------------- heltalsspill
    ("spill_init_utanfor_vidd", "spill",
     "  i : INT := 40000;", "  i := i;", "I",
     OPROVAD + ": INT ar 16 bitar (tabell 10); vad ett initialvarde utanfor "
     "vidden betyder star inte i repot",
     "TRASIG FIXTUR: matiec avvisar, tolken tar emot 40000"),
    ("spill_kontroll_inom_vidd", "spill",
     "  i : INT;", "  i := 32766 + 1;", "I",
     OPROVAD + ": 32767 ryms i INT",
     "KONTROLLFALL: bada godkanner"),
    ("spill_konstantvikning", "spill",
     "  i : INT;", "  i := 32767 + 1;", "I",
     OPROVAD + ": summan 32768 ryms inte i INT",
     "matiec viker konstanten och avvisar tilldelningen; tolken ger 32768"),
    ("spill_variabel_int", "spill",
     "  i : INT := 32767;", "  i := i + 1;", "I",
     OPROVAD + ": spillets verkan ar implementationsberoende",
     "matiec godkanner (spillet sker vid korning); tolken ger 32768, "
     "OpenPLC sveper till -32768 (M-125 a10)"),
    ("spill_variabel_dint", "spill",
     "  d : DINT := 2147483647;", "  d := d + 1;", "D",
     OPROVAD,
     "matiec godkanner; tolken ger 2147483648, OpenPLC -2147483648 (M-125 a09)"),
    ("spill_sint", "spill",
     "  s : SINT := 127;", "  s := s + 1;", "S",
     OPROVAD,
     "matiec godkanner; tolken ger 128 (SINT ar 8 bitar)"),
    ("spill_uint_under_noll", "spill",
     "  u : UINT := 0;", "  u := u - 1;", "U",
     OPROVAD + ": UINT ar teckenlos",
     "matiec godkanner; tolken ger -1, alltsa ett NEGATIVT varde i en "
     "teckenlos typ"),
    ("spill_byte_plus_ett", "spill",
     "  b : BYTE := 255;", "  b := b + 1;", "B",
     OPROVAD + ": BYTE ar en bitstrang, inte ett tal; ADD ar definierad over "
     "ANY_NUM",
     "matiec avvisar '+' pa BYTE; tolken raknar 256"),

    # ------------------------------------------------------ division med noll
    ("noll_heltal_literal", "noll",
     "  i : INT;", "  i := 10 / 0;", "I",
     OPROVAD + ": DIV med noll ar ett feltillstand; ENO-semantiken star inte "
     "i repot",
     "matiec avvisar redan vid kompilering; tolken kastar Tolkfel"),
    ("noll_heltal_variabel", "noll",
     "  i : INT; n : INT := 0;", "  i := 10 / n;", "I",
     OPROVAD,
     "matiec GODKANNER - nollan syns forst vid korning; tolken kastar Tolkfel"),
    ("noll_mod_literal", "noll",
     "  i : INT;", "  i := 10 MOD 0;", "I",
     OPROVAD,
     "matiec GODKANNER trots att '/'-fallet avvisas - asymmetri i samma "
     "kompilator; tolken kastar Tolkfel"),
    ("noll_mod_variabel", "noll",
     "  i : INT; n : INT := 0;", "  i := 10 MOD n;", "I",
     OPROVAD,
     "matiec godkanner; tolken kastar Tolkfel"),
    ("noll_real_literal", "noll",
     "  r : REAL;", "  r := 1.0 / 0.0;", "R",
     OPROVAD + ": IEEE 754 ger +inf, IEC sager inget om det",
     "matiec godkanner; tolken kastar Tolkfel - ingen av dem ger inf"),
    ("noll_real_variabel", "noll",
     "  r : REAL; z : REAL := 0.0;", "  r := 1.0 / z;", "R",
     OPROVAD,
     "matiec godkanner; tolken kastar Tolkfel"),
    ("noll_real_noll_genom_noll", "noll",
     "  r : REAL; z : REAL := 0.0;", "  r := z / z;", "R",
     OPROVAD + ": IEEE 754 ger NaN",
     "matiec godkanner; tolken kastar Tolkfel"),

    # -------------------------------------------------- TIME over dygnsgransen
    ("tid_25h", "tid",
     "  t : TIME;", "  t := T#25h;", "T",
     OPROVAD + ": TIME ar en varaktighet utan ovre grans i standarden",
     "bada godkanner; tolken ger 90 000 000 ms"),
    ("tid_1d1h", "tid",
     "  t : TIME;", "  t := T#1d1h;", "T",
     OPROVAD,
     "bada godkanner; samma varde som T#25h"),
    ("tid_100d", "tid",
     "  t : TIME;", "  t := T#100d;", "T",
     OPROVAD,
     "bada godkanner; tolken ger 8 640 000 000 ms - over int32:s 2 147 483 647, "
     "och OpenPLC sveper (M-125 t07: TIME_TO_DINT(T#100d) = 50 065 408)"),
    ("tid_summa_over_dygn", "tid",
     "  t : TIME;", "  t := T#23h + T#2h;", "T",
     OPROVAD,
     "bada godkanner; ingen dygnsmodul - TIME ar en varaktighet"),
    ("tid_time_to_dint_25d", "tid",
     "  d : DINT;", "  d := TIME_TO_DINT(T#25d);", "D",
     OPROVAD,
     "2 160 000 000 ms ryms i DINT; kontrollfall precis under svepgransen"),
    ("tid_tod_utanfor_dygnet", "tid",
     "  q : TOD;", "  q := TOD#25:00:00;", "Q",
     OPROVAD + ": TIME_OF_DAY ar en tid PA DYGNET; 25:00:00 finns inte",
     "matiec GODKANNER en omojlig klockslag; tolkens lasare avvisar "
     "TOD-literaler helt"),
    ("tid_tod_ogiltig_minut", "tid",
     "  q : TOD;", "  q := TOD#12:99:00;", "Q",
     OPROVAD + ": 99 minuter finns inte",
     "matiec GODKANNER; tolkens lasare avvisar TOD-literaler helt"),
    ("tid_datum_som_inte_finns", "tid",
     "  dd : DATE;", "  dd := D#2026-02-30;", "DD",
     OPROVAD + ": 30 februari finns inte",
     "matiec GODKANNER; tolkens lasare avvisar DATE-literaler helt"),
    ("tid_enheter_i_fel_ordning", "tid",
     "  t : TIME;", "  t := T#5s10m;", "T",
     OPROVAD + ": enheterna ska sta i fallande ordning",
     "KONTROLLFALL at andra hallet: bada avvisar"),

    # ------------------------------------ strangar over sin deklarerade langd
    ("strang_deklarerad_langd", "strang",
     "  s : STRING[4];", "  s := 'abcd';", "S",
     OPROVAD + ": STRING[n] ar standardens form for en strang med maxlangd n",
     "matiec tappar variabeln ur scope; tolken har ingen langdmodell alls"),
    ("strang_for_langt_init", "strang",
     "  s : STRING[4] := 'abcdefgh';", "  s := s;", "S",
     OPROVAD,
     "matiec tappar variabeln ur scope; tolken lagrar hela strangen"),
    ("strang_for_lang_tilldelning", "strang",
     "  s : STRING[4]; n : INT;", "  s := 'abcdefgh';\n  n := LEN(s);", "N",
     OPROVAD,
     "matiec tappar variabeln; tolken ger LEN = 8 i en STRING[4]"),
    ("strang_utan_langd", "strang",
     "  s : STRING; n : INT;",
     "  s := '123456789012345678901234567890';\n  n := LEN(s);", "N",
     OPROVAD + ": STRING utan langd har en implementationsberoende maxlangd",
     "KONTROLLFALL: bada godkanner, tolken ger 30"),
    ("strang_deklaration_utan_bruk", "strang",
     "  s : STRING[4];\n  i : INT;", "  i := 1;", "I",
     OPROVAD,
     "matiec SEGMENTATION FAULT (rc -11) pa ren IEC-syntax; tolken godkanner"),
]


def _program(dekl, kropp):
    return "PROGRAM Main\nVAR\n%s\nEND_VAR\n%s\nEND_PROGRAM\n" % (dekl, kropp)


def matiec_svar(dekl, kropp):
    r = M.kompilera(_program(dekl, kropp) + KONFIGURATION)
    if r.accepterad:
        return {"utfall": "ACCEPTERAR", "ord": []}
    return {"utfall": "AVVISAR",
            "ord": ["rad %s kol %s: %s" % f for f in r.fel[:3]]}


def tolk_svar(dekl, kropp, las):
    try:
        t = TK.Tolk(_program(dekl, kropp), {}, {})
        t.scan()
        return {"utfall": "KOR", "varde": repr(t.las(las))}
    except TK.Tolkfel as fel:
        return {"utfall": "AVVISAR", "varde": None, "ord": [str(fel)[:300]]}


def klassa(m, t):
    """Klassningen fran M-125, utokad med EJ_JAMFORBAR.

    EJ_JAMFORBAR ar inte en mellanform: den ar for de fall dar matiec inte kan
    UTTRYCKA konstruktionen alls (STRING[n]), sa att "vem ar strangast" inte
    ar en meningsfull fraga. Att klassa dem som OVERENS eller som en oenighet
    hade bada varit fel.
    """
    if m["utfall"] == "AVVISAR" and t["utfall"] == "AVVISAR":
        return "OVERENS"
    if m["utfall"] == "ACCEPTERAR" and t["utfall"] == "KOR":
        return "OVERENS"
    if m["utfall"] == "AVVISAR" and t["utfall"] == "KOR":
        return "MATIEC_STRANGARE"
    return "VI_STRANGARE"


def kor(args):
    ut = []
    for namn, grupp, dekl, kropp, las, standard, forvantat in FALL:
        m = matiec_svar(dekl, kropp)
        t = tolk_svar(dekl, kropp, las)
        k = klassa(m, t)
        # STRING[n] gar inte att uttrycka i matiec (variabeln forsvinner ur
        # scope eller kompilatorn far segfault). Da ar "vem ar strangast" fel
        # fraga, och raden markeras for sig i stallet for att raknas som en
        # oenighet om semantiken.
        if grupp == "strang" and m["utfall"] == "AVVISAR" and any(
                "not declared in this scope" in o or "returkod -11" in o
                for o in m["ord"]):
            k = "EJ_JAMFORBAR"
        ut.append({"namn": namn, "grupp": grupp, "dekl": dekl, "kropp": kropp,
                   "standard": standard, "forvantat": forvantat,
                   "matiec": m, "tolk": t, "klass": k})
        print("%-32s %-7s %-11s %-24s %s"
              % (namn, grupp, m["utfall"], t["utfall"] + " " +
                 (t.get("varde") or ""), k))

    if not ut:
        print("noll korda fall")
        return 1

    # ---- de tva trasiga fallen ------------------------------------------
    per_namn = dict((r["namn"], r) for r in ut)
    fixtur = per_namn["spill_init_utanfor_vidd"]["klass"]
    kontroll = per_namn["spill_kontroll_inom_vidd"]["klass"]
    print("\n--- trasiga fallen ---")
    print("  spill_init_utanfor_vidd -> %s (ska vara MATIEC_STRANGARE)" % fixtur)
    print("  spill_kontroll_inom_vidd -> %s (ska vara OVERENS)" % kontroll)
    fel = 0
    if fixtur != "MATIEC_STRANGARE":
        print("TRASIG FIXTUR FOLL: `i : INT := 40000` klassades %s. "
              "Jamforelsen mater inte motorerna." % fixtur)
        fel = 1
    if kontroll != "OVERENS":
        print("KONTROLLFALLET FOLL: `i := 32766 + 1` klassades %s. Svepet "
              "mater sin egen stranghet." % kontroll)
        fel = 1

    raknat = {}
    for r in ut:
        raknat[r["klass"]] = raknat.get(r["klass"], 0) + 1
    print("\n--- klassning ---")
    for k in sorted(raknat):
        print("  %-18s %d" % (k, raknat[k]))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"fall": ut, "raknat": raknat,
                       "matiec": M.hitta_binar()[0]},
                      f, ensure_ascii=False, indent=1, sort_keys=True)
    return fel


# ------------------------------------------------------- den tredje kolumnen
#
# matiec ar OpenPLC:s TYPauktoritet, men den ar inte kompilatorn i VAR kedja -
# den ar `ST -> STruC++ -> OpenPLC v4`. Att matiec ACCEPTERAR en text sager
# alltsa ingenting om vad som HANDER nar den kors. De har proberna gar hela
# vagen: varje probe ar en syntetisk uppgift (INTE i banken) vars facit begar
# TOLKENS varde, och som darfor blir ROD hos OpenPLC-domaren om motorerna
# skiljer sig at - med OpenPLC:s eget varde i bristens text.
#
# En probe som spranger runtimen ger DOMSFEL, inte en dom, och det ar ett
# fullgott resultat: da ar svaret "runtimen overlevde inte", och det ar precis
# vad en anvandare behover veta innan koden gar ut i en cell.

RUNTIME_PROBER = [
    {
        "task_id": "A8-SPILL",
        "vad": "heltalsspill och REAL-bredd vid korning",
        "signals": [{"name": "TRIG", "type": "bool", "dir": "in"},
                    {"name": "O_SPILL", "type": "int", "dir": "out"},
                    {"name": "O_REAL", "type": "real", "dir": "out"}],
        "st": ("PROGRAM A8Spill\n"
               "VAR\n"
               "  iMax : INT := 32767;\n"
               "  rStor : REAL := 1.0E20;\n"
               "END_VAR\n"
               "IF TRIG THEN\n"
               "  O_SPILL := iMax + 1;\n"
               "  O_REAL := rStor * rStor;\n"
               "END_IF;\n"
               "END_PROGRAM\n"),
        "krav": {"O_SPILL": 32768, "O_REAL": 1.0e40},
        "tolkvarde": "tolken: O_SPILL = 32768, O_REAL = 1e40 (float64)",
    },
    {
        "task_id": "A8-HELTALSNOLL",
        "vad": "heltalsdivision med noll vid korning",
        "signals": [{"name": "TRIG", "type": "bool", "dir": "in"},
                    {"name": "O_DIV", "type": "int", "dir": "out"}],
        "st": ("PROGRAM A8Div\n"
               "VAR\n"
               "  iTio : INT := 10;\n"
               "  iNoll : INT := 0;\n"
               "END_VAR\n"
               "IF TRIG THEN\n"
               "  O_DIV := iTio / iNoll;\n"
               "END_IF;\n"
               "END_PROGRAM\n"),
        "krav": {"O_DIV": 0},
        "tolkvarde": "tolken: Tolkfel, 'division med noll' - ingen dom alls",
    },
    {
        # Skarpare an A8-HELTALSNOLL: dar kunde "O_DIV = 0" lika garna betyda
        # att satsen aldrig kordes. Har skrivs en sentinel FORE divisionen och
        # en markor EFTER den, sa att tre utfall gar att skilja at: 111 =
        # divisionen skrev inget, 0 = divisionen gav noll, O_EFTER = 0 =
        # scanet tog aldrig sig forbi divisionen.
        "task_id": "A8-HELTALSNOLL2",
        "vad": "heltalsdivision med noll: skrev den, och overlevde scanet?",
        "signals": [{"name": "TRIG", "type": "bool", "dir": "in"},
                    {"name": "O_DIV", "type": "int", "dir": "out"},
                    {"name": "O_EFTER", "type": "int", "dir": "out"}],
        "st": ("PROGRAM A8Div2\n"
               "VAR\n"
               "  iTio : INT := 10;\n"
               "  iNoll : INT := 0;\n"
               "END_VAR\n"
               "IF TRIG THEN\n"
               "  O_DIV := 111;\n"
               "  O_DIV := iTio / iNoll;\n"
               "  O_EFTER := 222;\n"
               "END_IF;\n"
               "END_PROGRAM\n"),
        "krav": {"O_DIV": 111, "O_EFTER": 222},
        "tolkvarde": ("tolken: Tolkfel vid divisionen - O_DIV star kvar pa "
                      "111 och O_EFTER nas aldrig"),
    },
    {
        # Tredje varvet pa samma fraga. A8-HELTALSNOLL2 visade att scanet inte
        # tar sig FORBI divisionen (O_EFTER blev aldrig 222). Kvar star om
        # scanet slutar kora HELT eller startar om varje cykel och dor pa nytt.
        # Pulsraknaren `n` skrivs FORE divisionen: fortsatter O_HB rakna ar
        # slingan vid liv och dor per scan; star den still ar hela
        # PLC-uppgiften dod. Kraven ar avsiktligt omojliga (999) sa att bada
        # avlasningarna hamnar i bristtexten.
        "task_id": "A8-HELTALSNOLL3",
        "vad": "heltalsdivision med noll: lever scanslingan efteråt?",
        "signals": [{"name": "TRIG", "type": "bool", "dir": "in"},
                    {"name": "O_HB", "type": "int", "dir": "out"},
                    {"name": "O_EFTER", "type": "int", "dir": "out"}],
        "st": ("PROGRAM A8Div3\n"
               "VAR\n"
               "  n : INT := 0;\n"
               "  iTio : INT := 10;\n"
               "  iNoll : INT := 0;\n"
               "  iSkrap : INT := 0;\n"
               "END_VAR\n"
               "n := n + 1;\n"
               "O_HB := n;\n"
               "IF TRIG THEN\n"
               "  iSkrap := iTio / iNoll;\n"
               "  O_EFTER := 222;\n"
               "END_IF;\n"
               "END_PROGRAM\n"),
        "krav": {"O_HB": 999, "O_EFTER": 999},
        "tolkvarde": ("tolken: Tolkfel vid divisionen i forsta scanet efter "
                      "TRIG; O_HB star kvar och O_EFTER nas aldrig"),
        "extra_punkt_ms": 200,
    },
    {
        "task_id": "A8-REALNOLL",
        "vad": "REAL-division med noll vid korning",
        "signals": [{"name": "TRIG", "type": "bool", "dir": "in"},
                    {"name": "O_RDIV", "type": "real", "dir": "out"}],
        "st": ("PROGRAM A8RDiv\n"
               "VAR\n"
               "  rEtt : REAL := 1.0;\n"
               "  rNoll : REAL := 0.0;\n"
               "END_VAR\n"
               "IF TRIG THEN\n"
               "  O_RDIV := rEtt / rNoll;\n"
               "END_IF;\n"
               "END_PROGRAM\n"),
        "krav": {"O_RDIV": 0.0},
        "tolkvarde": "tolken: Tolkfel, 'division med noll' - ingen dom alls",
    },
]


def _probe_post(p):
    steg = [{"t_ms": 0, "satt": {"TRIG": True}, "krav": {},
             "varfor": "rakningen utlost"}]
    if p.get("extra_punkt_ms"):
        steg.append({"t_ms": p["extra_punkt_ms"], "krav": dict(p["krav"]),
                     "varfor": "tidig avlasning; bristtexten bar vardet"})
    steg.append({"t_ms": 400, "krav": p["krav"],
                 "varfor": "kravet ar TOLKENS varde; ett rott utfall bar "
                           "OpenPLC:s varde i sin egen text"})
    return {
        "task_id": p["task_id"],
        "control": {"signals": p["signals"]},
        "facit_spar": {
            "scan_ms": 20,
            "referens": p["st"],
            "sekvenser": [{"id": "en_puls", "steg": steg}],
            "flanker": [], "invarianter": [], "motbevis": [],
        },
    }


def kor_runtime(args):
    import domare_openplc as DO                     # noqa: E402
    from vc_assist_svc.plc.openplc import OpenPlcFel  # noqa: E402

    rigg = DO.Rigg()
    rigg.kontrollera()
    klient = rigg.klient()
    ut = []
    for p in RUNTIME_PROBER:
        if args.probe and p["task_id"] not in args.probe.split(","):
            continue
        print("\n=== %s: %s ===" % (p["task_id"], p["vad"]))
        print("    %s" % p["tolkvarde"])
        post = _probe_post(p)
        rad = {"task_id": p["task_id"], "vad": p["vad"],
               "tolk": p["tolkvarde"], "st": p["st"]}
        try:
            d = DO.dom(post, p["st"], rigg=rigg)
            rad["utfall"] = "GODKAND" if d.godkand else "UNDERKAND"
            rad["brister"] = [{"kod": b.kod, "text": b.text[:600]}
                              for b in d.brister]
            print("    OpenPLC: %s" % rad["utfall"])
            for b in d.brister:
                print("      %s\n        %s" % (b.kod, b.text[:400]))
        except DO.Domsfel as fel:
            rad["utfall"] = "DOMSFEL"
            rad["skal"] = str(fel)[:1200]
            print("    OpenPLC: DOMSFEL (ingen dom - riggen eller runtimen "
                  "foll)\n      %s" % str(fel)[:600])
        # Overlevde runtimen? Ett svar har ar sjalva poangen med proben.
        try:
            rad["status_efter"] = klient.status()
        except OpenPlcFel as fel:
            rad["status_efter"] = "svarar inte: %s" % str(fel)[:200]
        print("    runtime efter proben: %s" % rad["status_efter"])
        ut.append(rad)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"prober": ut}, f, ensure_ascii=False, indent=1,
                      sort_keys=True)
    return 0 if ut else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-169: avvikelserna i kedjan")
    ap.add_argument("--json", help="skriv radata hit")
    ap.add_argument("--runtime", action="store_true",
                    help="kor den tredje kolumnen: probe genom OpenPLC v4")
    ap.add_argument("--probe", help="kommaseparerade probe-id")
    a = ap.parse_args(argv)
    if a.runtime:
        return kor_runtime(a)
    return kor(a)


if __name__ == "__main__":
    raise SystemExit(main())
