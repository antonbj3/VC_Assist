# -*- coding: utf-8 -*-
"""L3: FAS 15, PLC-axelns giltighet i en KORANDE VC. Mater M-97.

Fas 8 matte klockkvoten i varje korning och gjorde en korning utanfor
braketten OGILTIG - inte fallande, inte godkand. Har byggs motsvarande for
ogats PLC-axel: hopfogningens MATTA tak (M-87) stalls mot farskhetsfonstret
PLC_FARSK_S, rad for rad, och en korning dar taket tacker fonstret i mer an
PLC_AXEL_MAX_ANDEL av PLC-proven doms INCONCLUSIVE med orsaken "PLC-axeln gar
inte att lita pa".

En grind som aldrig fallt nagot ar en grind ingen har provat. Darfor har
korningen en KAND STORNING: VC-processen stoppas med SIGSTOP i `--stor-ms`
millisekunder var `--stor-var-s` sekund. Vaggklockan gar, simuleringstiden
star, kopplarens tur och retur blockeras - det ar samma felklass som fas 8:s
incident (en provsvit som tog pumpens tid och tryckte kvoten till 0,61), fast
styrd i storlek och tidpunkt.

STEGEN

  1. FRISK korning, 30 s, kopplare med 89 ms varv (M-39:s OpenPLC-varv,
     efterliknat). Andel otackta rader, fordelningen av tak och alder + tak,
     och ogats dom.
  2. STORD korning, samma sak med storningen pa. Andelen ska stiga och
     domen ska bli INCONCLUSIVE pa PLC-axeln. Blir den inte det har grinden
     inte fallt, och braketten ar inte matt.
  3. KAND CELL: station_bra (facit PASS, M-65) byggd i VC och PLC-driven
     genom bryggan - frisk och stord. Frisk ska ge PASS; stord far varken ge
     PASS eller FAIL.
  4. TAKET UNDER STORNING, med M-87:s klamma: haller hopfogningens tak
     nar processen stoppas mitt i en runda? Det ar det kanda svaret for
     TAKET, inte bara for grinden.

    python3 tests/protocol/kor_fas15_plcaxeln.py --json ut.json

Storningen riktas mot den VC som star i TESTPREFIXET pa :99, funnen genom en
/proc-scan pa kommandoraden OCH miljon - aldrig `pgrep -f`, som matchar sin
egen sokning. Operatorens VC (~/.wine-vc) rors inte.
"""

BANKPOST = {
    "pastar":
        "Ogat domer INCONCLUSIVE pa PLC-axeln nar hopfogningens matta tak "
        "tacker farskhetsfonstret i for manga prov, och en styrd storning av "
        "VC-processen driver fram just den domen.",
    "under_prov": (
        "ext/vc_addon/vc_assist/oga_analys.py",
        "ext/vc_addon/vc_assist/oga_harledning.py",
        "ext/vc_addon/vc_assist/oga_provtagning.py",
        "svc/vc_assist_svc/plc/ogonkoppling.py",
    ),
    "facit":
        "frisk korning: cellen station_bra ska ge PASS. Stord korning: "
        "andelen otackta rader ska stiga och domen bli INCONCLUSIVE med "
        "PLC-axeln som orsak - varken PASS eller FAIL.",
    "facitkalla":
        "storningen ar KAND och palagd av korningen sjalv (SIGSTOP mot "
        "VC-processen i matta millisekunder), cellens facit PASS ar "
        "handskrivet i tests/celler.py, och taket klams mot VC:s egen "
        "simuleringsklocka enligt M-87",
    "facitkalla_filer": (
        "tests/celler.py",
        "docs/matningar/M-87_hopfogningen_mot_vcs_egen_brygga.md",
        "docs/matningar/M-65_ogat_pa_djupet.md",
    ),
    "trasiga_fall": (
        "en stord korning som anda ger PASS betyder att grinden inte fallt "
        "och att braketten inte ar matt",
        "station_bra frisk maste ge PASS - annars mater storningsprovet nagot "
        "annat",
        "storningen far bara traffa VC i testprefixet pa :99, funnen genom en "
        "/proc-scan; pgrep -f matchar sin egen sokning",
    ),
    "kraver": ("vc",),
    "matningar": ("M-97",),
}
import argparse
import json
import os
import signal
import sys
import threading
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol"))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol", "stod"))

import installationsgrind                                   # noqa: E402
import kor_fas15_domarna as D                               # noqa: E402
import kor_fas15_hopfogning as HOP                          # noqa: E402
import oga_analys as A                                      # noqa: E402
import oga_harledning as H                                  # noqa: E402
from oga_provtagning import PLC_FARSK_S                     # noqa: E402
from vc_assist_svc.klient import Klient                     # noqa: E402
from vc_assist_svc.plc.ogonkoppling import Ogonkoppling     # noqa: E402
from vc_assist_svc.tokenplats import tokenfil               # noqa: E402

TESTPREFIX = os.path.expanduser("~/.wine-vc-test")
p = HOP.p


def vc_pid(display=":99", prefix=TESTPREFIX):
    """VC-processen i TESTPREFIXET pa den headless skarmen, ur /proc.

    Kravet ar dubbelt: kommandoraden ska bara VisualComponents.Engine.exe
    OCH miljon ska saga ratt prefix och ratt DISPLAY. Ett av dem racker inte
    - operatorens VC bar samma exe-namn.
    """
    traffar = []
    for namn in os.listdir("/proc"):
        if not namn.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % namn, "rb") as f:
                cmd = f.read().replace(b"\0", b" ")
            if b"VisualComponents.Engine.exe" not in cmd:
                continue
            with open("/proc/%s/environ" % namn, "rb") as f:
                env = dict(x.split(b"=", 1) for x in f.read().split(b"\0") if b"=" in x)
        except (IOError, OSError):
            continue
        if (env.get(b"WINEPREFIX", b"").decode() == prefix
                and env.get(b"DISPLAY", b"").decode() == display):
            traffar.append(int(namn))
    if len(traffar) != 1:
        raise RuntimeError("fann %d VC-processer i %s pa %s: %r"
                           % (len(traffar), prefix, display, traffar))
    return traffar[0]


def _stoppad(pid):
    try:
        with open("/proc/%d/stat" % pid) as f:
            return f.read().split(")")[-1].split()[0] in ("T", "t")
    except (IOError, OSError):
        return False


class Storning(threading.Thread):
    """SIGSTOP/SIGCONT pa VC med kand langd och kant intervall.

    Alltid SIGCONT till slut, aven om nagot kastar: en VC som lamnas stoppad
    ar en dod brygga for alla som delar den.
    """

    def __init__(self, pid, stopp_s, var_s):
        threading.Thread.__init__(self)
        self.daemon = True
        self.pid = int(pid)
        self.stopp_s = float(stopp_s)
        self.var_s = float(var_s)
        self.slut = threading.Event()
        self.logg = []          # (vaggtid da stoppet borjade, uppmatt langd)

    def run(self):
        try:
            while not self.slut.wait(self.var_s):
                t0 = time.time()
                os.kill(self.pid, signal.SIGSTOP)
                try:
                    time.sleep(self.stopp_s)
                finally:
                    os.kill(self.pid, signal.SIGCONT)
                self.logg.append((t0, time.time() - t0))
        finally:
            try:
                os.kill(self.pid, signal.SIGCONT)
            except OSError:
                pass

    def avsluta(self):
        self.slut.set()
        self.join(timeout=5.0)
        for _ in range(20):
            if not _stoppad(self.pid):
                break
            os.kill(self.pid, signal.SIGCONT)
            time.sleep(0.05)


def _dist(v):
    v = [float(x) for x in v if x is not None]
    if not v:
        return None
    return {"n": len(v), "median": p(v, .5), "p95": p(v, .95),
            "min": min(v), "max": max(v)}


def _sammanfatta(data, plan, kopplare, svar_logg):
    rader = data["rows"]
    ax = H.plc_axel(rader, PLC_FARSK_S)
    u = H.upplosning(rader, data["run"].get("rate_hz"), A.HOPFOGNING_PRIOR_S)
    _text, rapport, a = A.doma(data, plan)
    med = [r for r in rader if r.get("plc") is not None]
    return {
        "prov": len(rader),
        "rader_med_plc": len(med),
        "rader_gamla": len([r for r in med if r.get("plc_gammal")]),
        "rader_avbrott": len([r for r in rader if r.get("plc_avbrott")]),
        "axel": ax,
        "alder_ms": _dist([r["plc_alder_s"] * 1000.0 for r in med
                           if r.get("plc_alder_s") is not None]),
        "tak_ms": _dist([r["plc_hopfogning_s"] * 1000.0 for r in med
                         if r.get("plc_hopfogning_s") is not None]),
        "alder_plus_tak_ms": _dist([(r["plc_alder_s"] + r["plc_hopfogning_s"]) * 1000.0
                                    for r in med
                                    if r.get("plc_alder_s") is not None
                                    and r.get("plc_hopfogning_s") is not None]),
        # Pumpens egna tal per inskott: takten och dess spridning.
        "takt": _dist([s.get("takt") for s in svar_logg]),
        "takt_spridning": _dist([s.get("takt_spridning") for s in svar_logg]),
        "klockbakat": max([s.get("klockbakat") or 0 for s in svar_logg] or [0]),
        "kopplare": kopplare.sammanfattning(),
        "upplosning": {"prov_ms": None if u["prov_s"] is None else u["prov_s"] * 1000.0,
                       "las_ms": None if u["las_s"] is None else u["las_s"] * 1000.0,
                       "hopfogning_ms": u["hopfogning_s"] * 1000.0,
                       "kalla": u["hopfogning_kalla"]},
        "dom": list(rapport.dom),
        "domar": dict((k, v["utfall"]) for k, v in a.harledt["domar"].items()),
    }


def korning(k, objekt, sekunder, lasvarv_s, storning=None):
    """En PLC-driven korning: kopplaren vaxlar Start var `lasvarv_s`."""
    plan = {"template": "fas15_plcaxel", "parts": [objekt], "tools": [],
            "rate_hz": 20.0, "scen": "roles"}
    k.oga_start(plan, simtid=k.simtid())
    kopplare = Ogonkoppling(k)
    kopplare.synka()
    svar_logg = []
    n = 0
    varannan = True
    if storning is not None:
        storning.start()
    try:
        slut = time.time() + sekunder
        while time.time() < slut:
            t_las = time.time()
            svar_logg.append(kopplare.skjut_in({"Start": varannan}, t_last=t_las))
            varannan = not varannan
            n += 1
            time.sleep(max(0.0, lasvarv_s - (time.time() - t_las)))
    finally:
        if storning is not None:
            storning.avsluta()
        ut = k.oga_stopp()
    data = ut.get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret", "prov": ut.get("samples")}
    r = _sammanfatta(data, plan, kopplare, svar_logg)
    r["inskott"] = n
    if storning is not None:
        r["storningar"] = {"antal": len(storning.logg),
                           "langd_ms": _dist([x[1] * 1000.0 for x in storning.logg])}
    return r


def kand_cell(k, storning=None):
    """station_bra i VC, PLC-driven genom bryggan. Facit: PASS (M-65)."""
    kartor = [("produkt", "%s_produkt" % D.PREFIX, None),
              ("broms", "%s_broms" % D.PREFIX, "parts")]
    if storning is not None:
        storning.start()
    try:
        r = D.kor_cell_i_vc(k, "station_bra", kartor, med_plc=True)
    finally:
        if storning is not None:
            storning.avsluta()
    if "fel" in r:
        return r
    ut = {"dom": [r["dom"], r["orsak"]], "domar": r.get("domar"), "prov": r["prov"],
          "saknade": r.get("saknade")}
    if storning is not None:
        ut["storningar"] = len(storning.logg)
    return ut


def taket_under_storning(k, objekt, storning, varv, alder_s=0.1, klocksekunder=10.0):
    """M-87:s klamma, med storningen pa: haller taket?

    Storningen ska vara TATARE har an i steg 1-3: klamman gor ett varv pa
    ~15 ms, sa 100 varv ar 1,5 s - den forsta korningen (M-97) hann bli klar
    innan det forsta stoppet kom och matte taket ostort. Anroparen ger en
    Storning med kortare intervall."""
    karta = HOP.Karta()
    kl = HOP.steg1_klockorna(k, klocksekunder, karta)
    k.oga_start(HOP._plan(objekt), simtid=k.simtid())
    storning.start()
    try:
        d = HOP.steg3_d(k, karta, alder_s, varv, kl.get("lang_kvot"))
    finally:
        storning.avsluta()
        k.oga_stopp()
    d["storningar"] = len(storning.logg)
    d["lang_kvot_fore"] = kl.get("lang_kvot")
    return d


def _skriv_korning(namn, r):
    if "fel" in r:
        print("  %s: MISSLYCKADES: %s" % (namn, r["fel"]))
        return
    ax = r["axel"]
    print("  %s: %d prov, %d inskott, %d rader med PLC (%d gamla, %d avbrott)"
          % (namn, r["prov"], r["inskott"], r["rader_med_plc"], r["rader_gamla"],
             r["rader_avbrott"]))
    print("    otackta: %d av %d = %.1f %%  (braketten %.0f %%)  utan tak: %d"
          % (ax["otackta"], ax["rader_med_plc"], 100.0 * ax["andel_otackt"],
             100.0 * A.PLC_AXEL_MAX_ANDEL, ax["utan_tak"]))
    for namn2, nyckel in (("alder", "alder_ms"), ("tak", "tak_ms"),
                          ("alder+tak", "alder_plus_tak_ms")):
        d = r[nyckel]
        if d:
            print("    %-10s median %7.1f  p95 %7.1f  max %8.1f ms"
                  % (namn2, d["median"], d["p95"], d["max"]))
    t = r["takt"]
    sp = r["takt_spridning"]
    if t and sp:
        print("    takt      median %.4f  min %.4f  max %.4f | spridning median %.4f  max %.4f"
              % (t["median"], t["min"], t["max"], sp["median"], sp["max"]))
    if "storningar" in r:
        print("    storningar: %d, langd median %.0f ms max %.0f ms"
              % (r["storningar"]["antal"], r["storningar"]["langd_ms"]["median"],
                 r["storningar"]["langd_ms"]["max"]))
    print("    dom: %s: %s" % (r["dom"][0], r["dom"][1][:120]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=None)
    ap.add_argument("--sekunder", type=float, default=30.0)
    ap.add_argument("--lasvarv-ms", type=float, default=89.0)
    ap.add_argument("--stor-ms", type=float, default=300.0)
    ap.add_argument("--stor-var-s", type=float, default=3.0)
    ap.add_argument("--varv", type=int, default=300)
    ap.add_argument("--stor-var-s-klamma", type=float, default=0.7,
                    help="storningens intervall i steg 4; klamman gor ~60 varv/s")
    ap.add_argument("--hoppa", default="")
    ap.add_argument("--json", default=None)
    ap.add_argument("--anda", action="store_true")
    a = ap.parse_args()
    hoppa = set(x for x in a.hoppa.split(",") if x.strip())

    print("STEG 0 - kor VC repots kod?")
    ok_installation, _ = installationsgrind.kontrollera(skriv=print)
    if not ok_installation and not a.anda:
        return 2
    pid = vc_pid()
    print("  VC-processen i testprefixet pa :99: pid %d" % pid)
    if _stoppad(pid):
        os.kill(pid, signal.SIGCONT)
        print("  (den stod stoppad - SIGCONT skickad)")

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=180.0).anslut()
    objekt = HOP._nagon_komponent(k)
    ut = {"tid": time.strftime("%Y-%m-%d %H:%M:%S"), "pid": pid, "objekt": objekt,
          "installationen_ar_repots": ok_installation,
          "PLC_FARSK_S": PLC_FARSK_S, "PLC_AXEL_MAX_ANDEL": A.PLC_AXEL_MAX_ANDEL,
          "storning": {"stopp_ms": a.stor_ms, "var_s": a.stor_var_s,
                       "var_s_klamma": a.stor_var_s_klamma}}

    def storning():
        return Storning(pid, a.stor_ms / 1000.0, a.stor_var_s)

    try:
        if "1" not in hoppa:
            print("\nSTEG 1 - frisk korning (%.0f s, kopplarvarv %.0f ms)"
                  % (a.sekunder, a.lasvarv_ms))
            ut["frisk"] = korning(k, objekt, a.sekunder, a.lasvarv_ms / 1000.0)
            _skriv_korning("frisk", ut["frisk"])
        if "2" not in hoppa:
            print("\nSTEG 2 - stord korning (SIGSTOP %.0f ms var %.1f s)"
                  % (a.stor_ms, a.stor_var_s))
            ut["stord"] = korning(k, objekt, a.sekunder, a.lasvarv_ms / 1000.0,
                                  storning())
            _skriv_korning("stord", ut["stord"])
        if "3" not in hoppa:
            print("\nSTEG 3 - kand cell station_bra i VC, frisk och stord")
            ut["cell_frisk"] = kand_cell(k)
            print("  frisk: %s" % (ut["cell_frisk"].get("dom") or ut["cell_frisk"].get("fel"),))
            ut["cell_stord"] = kand_cell(k, storning())
            print("  stord: %s  (%s storningar)"
                  % (ut["cell_stord"].get("dom") or ut["cell_stord"].get("fel"),
                     ut["cell_stord"].get("storningar")))
        if "4" not in hoppa:
            print("\nSTEG 4 - haller taket under storningen? (klamma, %d varv, alder 100 ms)"
                  % a.varv)
            ut["tak_stord"] = taket_under_storning(
                k, objekt, Storning(pid, a.stor_ms / 1000.0, a.stor_var_s_klamma), a.varv)
            d = ut["tak_stord"]
            if "fel" in d:
                print("  MISSLYCKADES: %r" % d["fel"])
            else:
                print("  varv %d | saker over taket %d (%.1f %%) | mojlig %d (%.1f %%) | "
                      "regression over %d (%.1f %%)"
                      % (d["varv"], d["saker_over_taket"], d["saker_over_taket_pct"],
                         d["mojlig_over_taket"], d["mojlig_over_taket_pct"],
                         d["reg_over_taket"], d["reg_over_taket_pct"]))
                print("  tak median %.1f ms max %.1f ms | klamma median %.1f max %.1f ms | "
                      "varsta overskridande %.1f ms | storningar %d"
                      % (d["tak_median_ms"], d["tak_max_ms"], d["klamma_median_ms"],
                         d["klamma_max_ms"], d["varsta_ms"], d["storningar"]))
    finally:
        if _stoppad(pid):
            os.kill(pid, signal.SIGCONT)
        try:
            print("\n  stadar: %r" % (D.stada(k),))
        except Exception as e:
            print("\n  STADNINGEN MISSLYCKADES: %s: %s" % (type(e).__name__, e))
        if a.json:
            with open(a.json, "w") as f:
                json.dump(ut, f, indent=2, default=str)
            print("  skrev %s" % a.json)
        k.stang()
    return 0


if __name__ == "__main__":
    sys.exit(main())
