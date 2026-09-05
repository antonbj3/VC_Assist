# -*- coding: utf-8 -*-
"""M-178 (ko A, punkt A11): kod som ar riktig men inte hinner.

Cykeltiden ar ett TAK. En PLC-uppgift med `INTERVAL := T#20ms` ska vara klar
inom 20 ms; tar kroppen langre tid hinner den inte, och allt som hanger pa
tiden - timers, flankrakning, taktnummer, en sekvens mot en annan station -
glider. Koden ar fortfarande RIKTIG. Den ar bara for langsam for sitt eget tak.

Fragan ar inte om det gar att skriva sadan kod. Fragan ar om NAGON I KEDJAN
sager till. Gor ingen det kan en anvandare fa kod som ar gron i banken och
missar sin deadline i verkligheten - och det ar den dyraste sortens falska
gront, for den syns forst i cellen.

Korningen svarar i tre delar:

  * `--tolk`  Var ST-tolk har ingen exekveringstid alls. `Tolk.scan()` flyttar
              klockan `tid_ms += scan_ms` oavsett hur mycket arbete kroppen
              gjorde. Det VISAS har i stallet for att pastas: samma kropp kors
              med vaxande arbetsmangd, vaggtiden mats, och modellklockan star
              kvar pa exakt 20 ms per scan.
  * `--grindar` Vilka led i var egen kedja som over huvud taget NAMNER
              exekveringstid. Ren textsokning, alltsa en UNDRE grans - men en
              undre grans pa noll ar ett svar.
  * `--runtime` Ett svep av arbetsmangder genom OpenPLC Runtime v4. Effektiv
              cykeltid mats ur PLC:ns egen pulsraknare (scan per vaggsekund),
              och for varje niva lases runtimens `timing_stats`, dess
              `status` och dess `runtime-logs`.

## Trasiga fallet, fore mekanismen

Nivan `noll` (ingen loop) MASTE ge en effektiv cykeltid inom nagra procent av
20 ms, och den tyngsta nivan MASTE ge klart over 20 ms. Ger de samma tal
belastar svepet ingenting, och da mater det sin egen matare i stallet for
taket. Korningen sager det rakt ut och ger returkod != 0.

Kors:

    VC_ASSIST_STRUCPP_PAKET=... nice -n 19 ionice -c3 \\
      python3 tests/protocol/kor_A11_cykeltidstaket.py --runtime \\
        --json docs/matningar/radata/m178_runtime.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
for _p in (_HAR, os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BANKPOST = {
    "pastar": (
        "En ST-kropp som tar langre tid an PLC-uppgiftens intervall gor att "
        "den effektiva cykeltiden vaxer med arbetsmangden, och antalet led i "
        "kedjan som sager till om det ar ett rakat tal - inte ett antagande. "
        "Var ST-tolk kan per konstruktion inte saga till: dess klocka flyttas "
        "med scanperioden oavsett hur mycket arbete kroppen gjorde."),
    "under_prov": ("svc/vc_assist_svc/st/tolk.py",
                   "svc/vc_assist_svc/plc/",
                   "bank/domare.py"),
    "facit": (
        "OpenPLC Runtime v4:s egen effektiva cykeltid, matt ur en pulsraknare "
        "i PLC-programmet sjalvt (scan per vaggsekund) och jamford med "
        "PLC-uppgiftens deklarerade intervall T#20ms."),
    "facitkalla": (
        "OpenPLC Runtime v4.2.1 - en annan implementation, utanfor koden som "
        "provas - och dess egna timing_stats, status och runtime-logs"),
    "facitkalla_filer": (),
    "trasiga_fall": (
        "nivan utan arbete MASTE ge effektiv cykeltid nara 20 ms och den "
        "tyngsta nivan MASTE ge klart over; samma tal betyder att svepet inte "
        "belastar nagot och mater sin egen matare",
        "tolkdemonstrationen MASTE visa vaxande vaggtid och OFORANDRAD "
        "modellklocka; vaxer bada ar demonstrationen fel byggd",
        "noll matta nivaer ger returkod != 0",
    ),
    "kraver": ("openplc", "strucpp"),
    "matningar": ("M-178", "M-20"),
}

from vc_assist_svc.st import tolk as TK              # noqa: E402

# PLC-uppgiftens deklarerade intervall. `paket.TASKINTERVALL` ar "T#20ms" och
# `tolk.SCAN_MS` ar 20.0, bada ur M-20. Taket i den har matningen ar samma tal.
TAK_MS = 20.0                       # M-20: OpenPLC v4:s uppmatta scanperiod.

# Hur nara 20 ms den obelastade nivan maste ligga for att svepet ska raknas
# som kalibrerat. 25 % ar ingen prestandagrans utan en sparr mot en matare som
# inte mater: ligger tomkorningen langre bort an sa ar det inte arbetet som
# styr talet. Matt harnedan (m178_runtime.json, nivan "noll").
TOMGANG_TOLERANS = 0.25             # M-178: spärr mot en matare som inte mater.


# ------------------------------------------------------ del 1: tolkens klocka

TOLKMALL = """PROGRAM A11Tolk
VAR
    i   : DINT;
    j   : DINT;
    acc : REAL := 0.0;
END_VAR
acc := 0.0;
FOR i := 1 TO %(yttre)d DO
    FOR j := 1 TO %(inre)d DO
        acc := acc + 1.0;
    END_FOR;
END_FOR;
UT_ACC := acc;
END_PROGRAM
"""


def tolkdemonstrationen(nivaer=((1, 1), (20, 20), (60, 60), (120, 120))):
    """Vaggtid mot modellklocka, per arbetsmangd.

    Poangen ar inte att tolken ar langsam - den ar en tolk i Python. Poangen
    ar att MODELLKLOCKAN inte ror sig av arbetet: `Tolk.scan()` gor
    `self.tid_ms += self.scan_ms` och det finns ingen annan tidskalla i
    tolken. En kropp som tar tio sekunder och en som tar en mikrosekund ger
    exakt samma spar, alltsa exakt samma dom.
    """
    ut = []
    for yttre, inre in nivaer:
        kalla = TOLKMALL % {"yttre": yttre, "inre": inre}
        t = TK.Tolk(kalla, {"UT_ACC": "real"}, {"UT_ACC": "out"}, TAK_MS)
        t0 = time.perf_counter()
        t.scan()
        vaggtid_ms = (time.perf_counter() - t0) * 1000.0
        ut.append({"varv": yttre * inre,
                   "vaggtid_ms": round(vaggtid_ms, 3),
                   "modellklocka_ms": t.tid_ms,
                   "acc": t.las("UT_ACC")})
    return ut


# --------------------------------------------------- del 2: vem som namner tid

# Ren textsokning efter det ordforrad ett led skulle behova for att kunna
# saga "for langsam". Det ar en UNDRE grans: en grind kan mata tid utan att
# anvanda nagot av orden. Att listan ar tom ar anda ett svar, for det finns
# ingen sadan grind att peka pa.
TIDSORD = re.compile(
    r"cycle_time|cykeltid|exekveringstid|scan_time|scantid|overrun|"
    r"deadline|for\s+langsam|budget_ms|max_ms|wcet", re.I)

# Filerna som star mellan modellens text och en korande PLC.
KEDJAN = (
    "svc/vc_assist_svc/st/validator.py",
    "svc/vc_assist_svc/st/tolk.py",
    "svc/vc_assist_svc/plc/deklarationsgrind.py",
    "svc/vc_assist_svc/plc/industrigrind.py",
    "svc/vc_assist_svc/plc/stationsgrind.py",
    "svc/vc_assist_svc/plc/forhandsregler.py",
    "svc/vc_assist_svc/plc/paket.py",
    "svc/vc_assist_svc/plc/openplc.py",
    "bank/domare.py",
    "bank/domare_openplc.py",
)


def grindinventeringen():
    ut = []
    for rel in KEDJAN:
        vag = os.path.join(_ROT, rel)
        if not os.path.exists(vag):
            ut.append({"fil": rel, "finns": False, "traffar": []})
            continue
        traffar = []
        with open(vag, "r", encoding="utf-8") as f:
            for n, rad in enumerate(f, 1):
                if TIDSORD.search(rad):
                    traffar.append({"rad": n, "text": rad.strip()[:160]})
        ut.append({"fil": rel, "finns": True, "traffar": traffar})
    return ut


# ------------------------------------------------- del 3: runtimen under last

RUNTIMEMALL = """PROGRAM A11Tung
VAR
    i   : DINT;
    j   : DINT;
    acc : REAL := 0.0;
    n   : INT := 0;
END_VAR

(* Pulsraknaren skrivs FORST i varje scan. Skillnaden mellan tva avlasningar
   delat med tiden emellan ar PLC:ns EFFEKTIVA cykeltid - matt ur PLC:n
   sjalv, inte ur var klocka. *)
n := n + 1;

(* A11_TICK lases men satts aldrig av facit. Raden finns for att ingangen ska
   ANVANDAS: en mappad ingang som ingen sats laser gav BadInternalError vid
   skrivning over OPC UA (matt 2026-09-05), alltsa ett Domsfel i stallet for
   en matning. *)
IF A11_TICK THEN
    n := n + 1;
END_IF;

O_HB := n;

acc := 0.0;
FOR i := 1 TO %(yttre)d DO
    FOR j := 1 TO %(inre)d DO
        acc := acc + 1.0;
    END_FOR;
END_FOR;

(* acc lases ut sa att kompilatorn inte kan optimera bort loopen. *)
O_ACC := REAL_TO_INT(acc / 1000000.0);
END_PROGRAM
"""

NIVAER = [
    ("noll", 0, 0),
    ("1e6", 1000, 1000),
    ("5e6", 1000, 5000),
    ("1e7", 2000, 5000),
    ("2e7", 4000, 5000),
    ("1e8", 10000, 10000),
]

# Avlasningarna i pulsraknaren. Domaren laser punktkravet vid `t + 4 scan`,
# alltsa samma forskjutning i bada punkterna: differensen ar exakt 3000 ms
# vaggtid oavsett forskjutningen.
HB_T1_MS = 1000.0
HB_T2_MS = 4000.0
HB_FONSTER_MS = HB_T2_MS - HB_T1_MS


def _kalla(yttre, inre):
    if yttre <= 0 or inre <= 0:
        # Ingen loop alls: samma program utan FOR-satserna, sa att nivan
        # "noll" mater kedjans egen tomgang och inte en loop med noll varv.
        return (RUNTIMEMALL % {"yttre": 1, "inre": 1}).replace(
            "FOR i := 1 TO 1 DO", "IF FALSE THEN").replace(
            "    FOR j := 1 TO 1 DO\n        acc := acc + 1.0;\n    END_FOR;\n",
            "    acc := acc + 1.0;\n").replace("END_FOR;\n\n(* acc",
                                               "END_IF;\n\n(* acc")
    return RUNTIMEMALL % {"yttre": yttre, "inre": inre}


def _post(namn, kalla):
    """Ingangen finns men skrivs ALDRIG av facit, och bada halvorna ar matta.

    Forsta varvet hade en `START`-ingang som gatade loopen och skrevs vid
    t = 0. Vid 2e7 varv foll domaren da med Domsfel: *"kanalfel efter
    sekvensen: START skrevs sist True men lastes False"* - alltsa fick de tva
    tyngsta nivaerna inget tal alls, och det ar precis de nivaer matningen
    handlar om. `_kor_en_sekvens` efterkontrollerar bara de ingangar facit
    FAKTISKT skrev, sa en ingang som aldrig skrivs tar bort den fallan.

    Andra varvet tog bort ingangen helt. Da lases BADA utgangarna som `None`
    over OPC UA i varenda prov (353 av 353) - noderna finns, men de bar inget
    varde. En karta helt utan ingangar ger alltsa ingen lasbar bildtabell i
    OpenPLC v4:s OPC UA-plugin. Darfor star `A11_TICK` kvar har, oanvand av
    bade logiken och facit: den ar en forutsattning for att lasvagen alls ska
    bara varden, och det ar matt och inte antaget.
    """
    return {
        "task_id": "A11-%s" % namn.upper(),
        "control": {"signals": [
            {"name": "A11_TICK", "type": "bool", "dir": "in"},
            {"name": "O_HB", "type": "int", "dir": "out"},
            {"name": "O_ACC", "type": "int", "dir": "out"},
        ]},
        "facit_spar": {
            "scan_ms": 20,
            "referens": kalla,
            "sekvenser": [{
                "id": "pulsraknaren",
                "steg": [
                    # Omojliga krav med avsikt: bristtexten bar det UPPMATTA
                    # vardet, och det ar talet matningen behover.
                    {"t_ms": HB_T1_MS, "krav": {"O_HB": -1},
                     "varfor": "avlasning 1 av pulsraknaren"},
                    {"t_ms": HB_T2_MS, "krav": {"O_HB": -1},
                     "varfor": "avlasning 2 av pulsraknaren"},
                ],
            }],
            "flanker": [], "invarianter": [], "motbevis": [],
        },
    }


_HB = re.compile(r"O_HB skulle vara -1 men var (-?\d+)")


class _Vaktare(object):
    """Laser runtimens EGEN statistik MEDAN den kor.

    Skalet ar matt: `domare_openplc.dom` stoppar PLC:n nar den ar klar, och
    `timing_stats` ar da `{"tasks": []}`. Statistiken maste alltsa lasas under
    korningen, inte efter. Vaktaren rakar aldrig i domen - den laser bara.
    """

    def __init__(self, klient, paus=0.25):
        import threading
        self.klient = klient
        self.paus = paus
        self._stopp = threading.Event()
        self._trad = threading.Thread(target=self._loop, daemon=True)
        self.sista_stats = {}
        self.statusar = []

    def _loop(self):
        from vc_assist_svc.plc.openplc import OpenPlcFel
        while not self._stopp.is_set():
            try:
                st = self.klient.status()
                if not self.statusar or self.statusar[-1] != st:
                    self.statusar.append(st)
                    if st == "RUNNING":
                        # Statistiken nollstalls vid varje ny start. Utan den
                        # har raden bar nivan N runtimens siffror fran niva
                        # N-1: matt 2026-09-05, da nivan "noll" rapporterade
                        # 41 ms scan_time_avg som horde till foregaende
                        # program.
                        self.sista_stats = {}
                        self._kor = True
                    else:
                        self._kor = False
                if getattr(self, "_kor", False):
                    stats = self.klient.statistik()
                    if stats and stats.get("tasks"):
                        self.sista_stats = stats
            except (OpenPlcFel, Exception):
                pass
            self._stopp.wait(self.paus)

    def __enter__(self):
        self._trad.start()
        return self

    def __exit__(self, *a):
        self._stopp.set()
        self._trad.join(timeout=5.0)
        return False


def kor_runtime(args):
    import domare_openplc as DO
    from vc_assist_svc.plc.openplc import OpenPlcFel

    rigg = DO.Rigg()
    rigg.kontrollera()
    klient = rigg.klient()
    klient.skapa_forsta_anvandare()
    valda = set(args.nivaer.split(",")) if args.nivaer else None
    ut = []
    for namn, yttre, inre in NIVAER:
        if valda and namn not in valda:
            continue
        kalla = _kalla(yttre, inre)
        post = _post(namn, kalla)
        print("\n=== niva %s (%d x %d = %d varv per scan) ==="
              % (namn, yttre, inre, yttre * inre))
        rad = {"niva": namn, "varv": yttre * inre, "st": kalla}
        # Loggmarkor: bara rader som kommit EFTER den har punkten hor till
        # den har nivan.
        try:
            rad["logg_fore"] = klient.logg(rader=1)
        except OpenPlcFel:
            rad["logg_fore"] = ""
        with _Vaktare(klient) as vaktare:
            try:
                d = DO.dom(post, kalla, rigg=rigg,
                           byggkatalog=args.byggkatalog)
                tal = []
                for b in d.brister:
                    m = _HB.search(b.text)
                    if m:
                        tal.append((b.kod, int(m.group(1))))
                tal.sort(key=lambda x: x[0])
                rad["avlasningar"] = tal
                per_kod = dict(tal)
                n1 = per_kod.get("pulsraknaren@%.0fms:O_HB" % HB_T1_MS)
                n2 = per_kod.get("pulsraknaren@%.0fms:O_HB" % HB_T2_MS)
                if n1 is not None and n2 is not None:
                    scan = n2 - n1
                    rad["scan_i_fonstret"] = scan
                    rad["effektiv_cykel_ms"] = (
                        round(HB_FONSTER_MS / scan, 3) if scan > 0 else None)
                rad["brister"] = [b.kod for b in d.brister]
            except DO.Domsfel as fel:
                rad["domsfel"] = str(fel)[:800]
                print("    DOMSFEL: %s" % str(fel)[:400])
        rad["timing_stats_under_korning"] = vaktare.sista_stats
        rad["statusar_under_korning"] = vaktare.statusar
        try:
            rad["status_efter"] = klient.status()
        except OpenPlcFel as fel:
            rad["status_efter"] = "svarar inte: %s" % str(fel)[:200]
        try:
            logg = klient.logg(rader=200)
            rader_efter = logg.splitlines()
            if rad.get("logg_fore") and rad["logg_fore"] in rader_efter:
                rader_efter = rader_efter[rader_efter.index(rad["logg_fore"]) + 1:]
            rad["logg_varningar"] = [r for r in rader_efter
                                     if "[WARNING]" in r or "[ERROR]" in r]
        except OpenPlcFel as fel:
            rad["logg_varningar"] = ["logg gick inte att lasa: %s" % fel]
        stats = (rad["timing_stats_under_korning"].get("tasks") or [{}])[0]
        rad["scan_time_avg_ms"] = (stats.get("scan_time_avg", 0) / 1000.0
                                   if stats.get("scan_time_avg") else None)
        rad["overruns"] = stats.get("overruns")
        rad["scan_count"] = stats.get("scan_count")
        print("    scan i %0.0f ms fonster: %s -> effektiv cykel %s ms"
              % (HB_FONSTER_MS, rad.get("scan_i_fonstret"),
                 rad.get("effektiv_cykel_ms")))
        print("    runtimens egen: scan_time_avg %s ms, overruns %s av %s scan"
              % (rad["scan_time_avg_ms"], rad["overruns"], rad["scan_count"]))
        print("    status under: %s -> efter: %s"
              % (rad.get("statusar_under_korning"), rad.get("status_efter")))
        for r in (rad.get("logg_varningar") or [])[:4]:
            print("    logg: %s" % r[:170])
        if not rad.get("logg_varningar"):
            print("    logg: (inga WARNING/ERROR)")
        ut.append(rad)

    fel = _domsprovet(ut)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"nivaer": ut, "tak_ms": TAK_MS,
                       "tolk": tolkdemonstrationen(),
                       "grindar": grindinventeringen()},
                      f, ensure_ascii=False, indent=1, sort_keys=True)
    return fel


def _domsprovet(ut):
    """Trasiga fallet: tomgangen nara taket, tyngsta nivan klart over."""
    per_niva = dict((r["niva"], r.get("effektiv_cykel_ms")) for r in ut)
    print("\n--- trasiga fallet ---")
    noll = per_niva.get("noll")
    tunga = [r["niva"] for r in ut if r["niva"] != "noll"
             and r.get("effektiv_cykel_ms")]
    if noll is None:
        print("  nivan 'noll' kordes inte; kalibreringen gar inte att prova")
        return 0 if ut else 1
    avvikelse = abs(noll - TAK_MS) / TAK_MS
    print("  tomgang: %.3f ms mot taket %.1f ms (%.1f %% avvikelse, "
          "spärr %.0f %%)" % (noll, TAK_MS, 100 * avvikelse,
                              100 * TOMGANG_TOLERANS))
    fel = 0
    if avvikelse > TOMGANG_TOLERANS:
        print("  KALIBRERINGEN FOLL: tomgangen ligger inte vid taket, sa "
              "talet styrs av nagot annat an arbetet")
        fel = 1
    if not tunga:
        print("  ingen belastad niva mattes; taket ar inte provat")
        return 1
    tyngst = max(per_niva[n] for n in tunga)
    print("  tyngsta uppmatta cykel: %.3f ms" % tyngst)
    if tyngst <= TAK_MS * 1.5:
        print("  BELASTNINGEN FOLL: ingen niva kom over taket, alltsa mater "
              "svepet sin egen matare och inte cykeltiden")
        fel = 1
    if not ut:
        print("noll matta nivaer")
        return 1
    return fel


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-178: cykeltidstaket")
    ap.add_argument("--tolk", action="store_true")
    ap.add_argument("--grindar", action="store_true")
    ap.add_argument("--runtime", action="store_true")
    ap.add_argument("--nivaer", help="kommaseparerade nivanamn")
    ap.add_argument("--byggkatalog")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    if a.tolk:
        print("=== tolkens klocka mot vaggklockan ===")
        for r in tolkdemonstrationen():
            print("  %10d varv: vaggtid %9.3f ms, modellklocka %6.1f ms, "
                  "acc %s" % (r["varv"], r["vaggtid_ms"],
                              r["modellklocka_ms"], r["acc"]))
        return 0
    if a.grindar:
        print("=== vem i kedjan namner exekveringstid ===")
        n = 0
        for r in grindinventeringen():
            if not r["finns"]:
                print("  %-42s FINNS INTE" % r["fil"])
                continue
            print("  %-42s %d traffar" % (r["fil"], len(r["traffar"])))
            for t in r["traffar"]:
                print("      rad %-5d %s" % (t["rad"], t["text"]))
            n += len(r["traffar"])
        print("  summa: %d traffar (textsokning; en UNDRE grans)" % n)
        return 0
    if a.runtime:
        return kor_runtime(a)
    ap.error("valj --tolk, --grindar eller --runtime")


if __name__ == "__main__":
    raise SystemExit(main())
