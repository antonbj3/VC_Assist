# -*- coding: utf-8 -*-
"""L3: flodesgrinden. En produkt ska matas fram AV SIG SJALV och aka.

M-40 matte varfor det inte gick, M-41 matte att det gar. Den har korningen ar
den grind som halller det matta pa plats:

  1. skriver ett startskript som bygger tre linjer med receptet flodeslinje
     -- A ratt, B utan bana.update(), C okopplad -- FORE startSimulation(),
  2. startar om VC (beteenden som laggs till i en KORANDE simulering
     initieras aldrig, M-32/M-40),
  3. provtar banorna over tid genom bryggan och domer.

GRONT kraver bada halvorna: A matar i takt och ror sig i Speed mm/s, OCH
B och C matar ingenting. En grind som bara sag A hade varit gron aven for en
matare som skapar produkter av fel skal.

    python3 tests/protocol/kor_m41_flode.py [--starta-om] [--prov N]

Utan --starta-om skrivs startskriptet och korningen sager till att VC maste
startas om for hand innan mätningen betyder nagot.
"""

BANKPOST = {
    "pastar":
        "En matare skapar produkter av sig sjalv i takt och banan flyttar dem "
        "i Speed mm/s, medan en linje utan bana.update() och en okopplad "
        "linje matar ingenting.",
    "under_prov": ("svc/vc_assist_svc/byggrecept/recept.py",),
    "facit":
        "linje A: mellanrum 4,000 s och hastighet 250 mm/s inom 0,001; "
        "linjerna B och C: noll produkter over minst fem intervall",
    "facitkalla":
        "riggens egna deklarerade tal - intervall och fart satts av korningen "
        "fore bygget - matta mot VC:s egna avlasningar av CreationTime och "
        "getPathDistance. Toleranserna ar M-41:s uppmatta spridning och "
        "M-40:s sju tysta intervall.",
    "facitkalla_filer": (
        "docs/matningar/M-41_produkten_flodar.md",
        "docs/matningar/M-40_varfor_mataren_aldrig_fyrade.md",
    ),
    "trasiga_fall": (
        "linje B utan bana.update() maste mata noll produkter",
        "linje C utan kopplingssteget maste mata noll produkter",
        "har kopplingsraden i receptet bytt form kastas RuntimeError - annars "
        "hade den trasiga fixturen tyst blivit hel",
    ),
    "kraver": ("vc",),
    "matningar": ("M-41",),
}
import argparse
import json
import os
import subprocess
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

from vc_assist_svc.byggrecept import recept as R          # noqa: E402
from vc_assist_svc.klient import Klient                   # noqa: E402

# Mataren och banan. Talen ar den korningens val, inte trosklar: grinden
# jamfor mot dem, den antar dem inte.
INTERVALL_S = 4.0          # matarens Interval; grinden jamfor skapelsetider mot den.
HASTIGHET_MM_S = 250.0     # banans Speed; grinden jamfor rorelsen mot den.
BANLANGD_MM = 2500.0       # banans langd i VC:s varldsenhet (mm, M-33).

# Hur mycket en uppmatt skapelsetakt eller hastighet far avvika. MATT i M-41:
# over 25 differenskvoter var spridningen 0.0000 mm/s och alla atta
# mellanrum exakt 4.000 s. Marginalen ar alltsa ren avrundningsmarginal.
TAKT_TOLERANS_S = 0.001        # Satt av M-41 (uppmatt avvikelse 0.000 s).
HASTIGHET_TOLERANS = 0.001     # Satt av M-41 (uppmatt spridning 0.0000 mm/s).
# Sa manga intervall B och C maste tiga for att tystnaden ska betyda nagot.
TYSTA_INTERVALL = 5            # Satt av M-40 (sju intervall matta, noll produkter).

TOKEN = os.path.expanduser("~/.wine-vc-test/drive_c/users/anton/vc_assist_token")
STARTSKRIPT = os.path.expanduser(
    "~/.wine-vc-test/drive_c/users/anton/vc_assist_startskript.py")

# Provtagningen: en lasning per anrop genom bryggans ko.
PROVKOD = """import json
app = getApplication()
sim = getSimulation()
linjer = {}
for pre in %r:
    b = app.findComponent(str(pre + '_Bana'))
    if b is None:
        continue
    p = b.findBehaviour(str('Path'))
    rad = {'PathLength': p.PathLength, 'Speed': p.Speed,
           'antal': p.ComponentCount, 'produkter': []}
    for c in p.Components:
        w = c.WorldPositionMatrix
        rad['produkter'].append({'skapad': c.CreationTime,
                                 'banavstand': c.getPathDistance(),
                                 'x': w.P.X})
    linjer[pre] = rad
print(json.dumps({'t': sim.SimTime, 'linjer': linjer}))
"""

MALLKOD = """
app = getApplication()
for _c in list(app.Components):
    if _c.Name[:4] == %(pre)r:
        app.deleteComponent(_c)
_p = app.createComponent()
_p.Name = %(mall)r
_f = _p.RootFeature.createFeature(VC_BLOCK, "kropp")
for _q in _f.Properties:
    if _q.Name == "Length":
        _q.Value = 200.0
    elif _q.Name == "Width":
        _q.Value = 200.0
    elif _q.Name == "Height":
        _q.Value = 200.0
_p.RootFeature.rebuild()
_m = _p.PositionMatrix
_m.translateAbs(-5000.0 - _m.P.X, 0.0 - _m.P.Y, 0.0 - _m.P.Z)
_p.PositionMatrix = _m
"""

PREFIX = "M41"
LINJER = ("M41A", "M41B", "M41C")


def _startskript():
    """Koden som bygger de tre linjerna, fore startSimulation()."""
    delar = [MALLKOD % {"pre": PREFIX, "mall": PREFIX + "_Produkt"}]
    for namn in LINJER:
        arg = {"name": namn, "mall": PREFIX + "_Produkt",
               "intervall": INTERVALL_S, "grans": 100000,
               "hastighet": HASTIGHET_MM_S, "banlangd": BANLANGD_MM,
               "y": 2000.0 * LINJER.index(namn)}
        kod = R.generera("flodeslinje", arg)
        kod = kod.replace("from __future__ import print_function\n", "")
        if namn == "M41B":
            # Den trasiga fixturen: utan bana.update() ar PathLength 0.0 och
            # ingenting flodar (M-40). Att ta bort raden ar hela skillnaden.
            kod = kod.replace("bana.update()\n", "")
        if namn == "M41C":
            # Den andra trasiga fixturen: sjalva kopplingssteget tas bort, sa
            # granssnitten aldrig kopplas ihop. Att bara nollstalla kan-flaggan
            # racker inte -- koppla_ihop() gor sin egen canConnect.
            gammal = '    ok_k, _r = _forsok(forsok, _s(u"E0"), koppla_ihop)'
            if gammal not in kod:
                raise RuntimeError("kopplingsraden i flodeslinje har bytt form; "
                                   "den trasiga fixturen skulle tyst blivit hel")
            kod = kod.replace(gammal, "    ok_k = False")
        delar.append(kod)
    kropp = "\n".join(delar)
    inne = "\n".join(("    " + r) if r.strip() else "" for r in kropp.splitlines())
    return (
        "# Skrivet av tests/protocol/kor_m41_flode.py. Kors av bridge_cmd\n"
        "# FORE startSimulation(); dar, och bara dar, initieras beteendena.\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "import traceback\n"
        "\n"
        "_LOGG = os.path.join(os.path.expanduser('~'), 'vc_assist_m41.json')\n"
        "\n"
        "\n"
        "class _Fangare(object):\n"
        "    def __init__(self):\n"
        "        self.rader = []\n"
        "\n"
        "    def write(self, s):\n"
        "        self.rader.append(s)\n"
        "\n"
        "    def flush(self):\n"
        "        pass\n"
        "\n"
        "\n"
        "_fang = _Fangare()\n"
        "_gammal = sys.stdout\n"
        "sys.stdout = _fang\n"
        "try:\n"
        + inne + "\n"
        "    _res = {'stdout': ''.join(_fang.rader)}\n"
        "except Exception:\n"
        "    _res = {'fel': traceback.format_exc(),\n"
        "            'stdout': ''.join(_fang.rader)}\n"
        "sys.stdout = _gammal\n"
        "_f = open(_LOGG, 'w')\n"
        "try:\n"
        "    _f.write(json.dumps(_res, sort_keys=True))\n"
        "finally:\n"
        "    _f.close()\n")


def _starta_om_vc():
    subprocess.call([os.path.expanduser("~/bin/vc-stoppa.sh")])
    miljo = dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":99"))
    subprocess.Popen([os.path.expanduser("~/bin/vc-test.sh")], env=miljo,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     stdin=subprocess.DEVNULL, start_new_session=True)


def _vanta_pa_bryggan(tak_s):
    slut = time.time() + tak_s
    while time.time() < slut:
        try:
            k = Klient(port=8901, tokenfil=TOKEN, timeout=5.0).anslut()
            k.ping()
            k.stang()
            return True
        except Exception:
            time.sleep(3.0)
    return False


def _prov(k):
    post = k.anrop("exec_queue", {"code": PROVKOD % (LINJER,),
                                  "desc": "M-41 prov"})["result"]
    ut = k.godkann_och_vanta(post["qid"], timeout=60.0)
    if ut["state"] != "done":
        raise RuntimeError("provet gick inte igenom: %s" % ut["state"])
    return ((ut.get("svar") or {}).get("result") or {}).get("result")


def _dom(serie):
    fel = []
    a = [r["linjer"].get("M41A", {}) for r in serie]
    skapelser = sorted({p["skapad"] for r in a for p in r.get("produkter", [])})
    if len(skapelser) < 3:
        fel.append("M41A skapade bara %d produkter; mataren matar inte"
                   % len(skapelser))
    mellanrum = [b - x for x, b in zip(skapelser, skapelser[1:])]
    for m in mellanrum:
        if abs(m - INTERVALL_S) > TAKT_TOLERANS_S:
            fel.append("M41A: mellanrum %.4f s, Interval ar %.4f s"
                       % (m, INTERVALL_S))
    kvoter = []
    for f, e in zip(serie, serie[1:]):
        for pf in f["linjer"].get("M41A", {}).get("produkter", []):
            for pe in e["linjer"].get("M41A", {}).get("produkter", []):
                if pf["skapad"] == pe["skapad"] and pe["banavstand"] > pf["banavstand"]:
                    dt = e["t"] - f["t"]
                    if dt > 0:
                        kvoter.append((pe["banavstand"] - pf["banavstand"]) / dt)
    if not kvoter:
        fel.append("M41A: ingen produkt flyttade sig mellan tva prov")
    for v in kvoter:
        if abs(v - HASTIGHET_MM_S) > HASTIGHET_TOLERANS:
            fel.append("M41A: hastighet %.4f mm/s, Speed ar %.4f mm/s"
                       % (v, HASTIGHET_MM_S))
    spann = serie[-1]["t"] - serie[0]["t"] if len(serie) > 1 else 0.0
    if spann < TYSTA_INTERVALL * INTERVALL_S:
        fel.append("serien spanner bara %.1f s; tystnaden i B och C betyder "
                   "ingenting under %.1f s"
                   % (spann, TYSTA_INTERVALL * INTERVALL_S))
    for trasig in ("M41B", "M41C"):
        n = sum(len(r["linjer"].get(trasig, {}).get("produkter", []))
                for r in serie)
        if n:
            fel.append("%s FLODADE (%d observationer) - den trasiga fixturen "
                       "faller inte, alltsa ar grinden ingen grind" % (trasig, n))
    return fel, skapelser, kvoter, spann


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--starta-om", action="store_true",
                    help="stoppa och starta VC sjalv (kraver ~/bin/vc-*.sh)")
    ap.add_argument("--prov", type=int, default=14)
    ap.add_argument("--paus", type=float, default=2.0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    kalla = _startskript()
    with open(STARTSKRIPT, "w") as f:
        f.write(kalla)
    print("  startskript skrivet: %s (%d tecken)" % (STARTSKRIPT, len(kalla)))

    if a.starta_om:
        print("  startar om VC ...")
        _starta_om_vc()
        if not _vanta_pa_bryggan(300.0):
            print("  FEL  bryggan kom aldrig upp")
            return 1
    else:
        print("  VC MASTE startas om for hand innan matningen betyder nagot:")
        print("      ~/bin/vc-stoppa.sh && DISPLAY=:99 ~/bin/vc-test.sh &")
        if not _vanta_pa_bryggan(5.0):
            print("  FEL  ingen brygga svarar")
            return 1

    k = Klient(port=8901, tokenfil=TOKEN, timeout=120.0).anslut()
    serie = []
    for _ in range(a.prov):
        serie.append(_prov(k))
        time.sleep(a.paus)
    k.stang()

    fel, skapelser, kvoter, spann = _dom(serie)
    print("  simtid %.2f -> %.2f (%.1f s)"
          % (serie[0]["t"], serie[-1]["t"], spann))
    print("  M41A skapelsetider: %s" % (skapelser,))
    if kvoter:
        print("  M41A hastighet ur %d par: %.4f - %.4f mm/s"
              % (len(kvoter), min(kvoter), max(kvoter)))
    for trasig in ("M41B", "M41C"):
        rad = serie[-1]["linjer"].get(trasig, {})
        print("  %s PathLength %.1f, %d observationer"
              % (trasig, rad.get("PathLength", -1.0),
                 sum(len(r["linjer"].get(trasig, {}).get("produkter", []))
                     for r in serie)))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(serie, f, indent=1, sort_keys=True)
    if fel:
        for r in fel:
            print("  FEL  %s" % r)
        return 1
    print("  OK   en produkt matas fram av sig sjalv och aker; bada trasiga "
          "fixturerna tiger")
    return 0


if __name__ == "__main__":
    sys.exit(main())
