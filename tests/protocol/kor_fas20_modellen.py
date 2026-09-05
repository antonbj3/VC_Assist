# -*- coding: utf-8 -*-
"""Fas 20: bygg specens fyra minsta uppsattningar i riktig VC och mat dem.

`docs/spec/49_komponentmodellen.md` sager vad en TRANSPORTOR, en MATARE, en
SANKA och en BUFFERT minst behover. Den har korningen bygger dem UR SPECEN --
`svc/vc_assist_svc/komponentmodell.py` genererar koden ur kravlistorna, inte ur
en handskriven mall -- och matter tre saker:

  1. Blir canConnect SANT mellan de par specen sager ska ga ihop?
  2. ROR SIG MATERIAL igenom? Det ar det som skiljer en koppling fran en
     fungerande kedja. Kedjan ar MATARE -> TRANSPORTOR -> BUFFERT -> SANKA,
     alltsa alla fyra klasserna i ETT flode.
  3. Faller de trasiga fixturerna, och sager felet VILKET beteende som fattas?

DEN TRASIGA FIXTUREN ar fasens poang, och den ar provad PARVIS. Samma motpart
provas forst mot en komponent dar exakt ett kravt beteende utelamnats (ska ge
False) och sedan mot en HEL tvilling pa SAMMA PLATS i varlden (ska ge True).
Da ar skillnaden mellan utfallen exakt det utelamnade beteendet -- inte
geometrin, inte motparten, inte ordningen. En trasig fixtur utan den hela
tvillingen hade matt "nagonting gick fel", inte "det har kravet ar ett krav".

Tre tysta villkor styr uppstallningen, alla matta i M-40/M-41:
  * beteendena maste finnas NAR SIMULERINGEN STARTAR -- darfor byggs allt i
    ett startskript som bridge_cmd kor FORE startSimulation(), och darfor
    startas VC om,
  * banans ramar maste vara ombyggda (rebuild) och banbeteendet uppdaterat
    efter att Path satts, annars ar PathLength 0.0 och banan bar ingenting,
  * matarens Limit maste vara satt, annars slutar den tyst.

    python3 tests/protocol/kor_fas20_modellen.py --starta-om
    python3 tests/protocol/kor_fas20_modellen.py --bara-skriv   (ingen VC)

Utan --starta-om skrivs startskriptet och korningen sager till att VC maste
startas om for hand innan matningen betyder nagot.
"""

BANKPOST = {
    "pastar":
        "Specens fyra minsta uppsattningar - transportor, matare, sanka och "
        "buffert - gar att bygga UR kravlistorna, koppla ihop i VC och lata "
        "material rora sig genom hela kedjan.",
    "under_prov": ("svc/vc_assist_svc/komponentmodell.py",),
    "facit":
        "de par specen sager ska ga ihop ska ge canConnect sant, och material "
        "ska ha rort sig genom kedjan matare, transportor, buffert och sanka",
    "facitkalla":
        "docs/spec/49_komponentmodellen.md sager vad varje klass minst "
        "behover och ar skriven fore korningen; svaret pa om det haller "
        "kommer ur VC:s eget canConnect och ur produkternas verkliga "
        "banavstand",
    "facitkalla_filer": ("docs/spec/49_komponentmodellen.md",),
    "trasiga_fall": (
        "en komponent dar exakt ett kravt beteende utelamnats ska ge "
        "canConnect FALSKT",
        "en HEL tvilling pa SAMMA plats i varlden ska ge SANT - utan den "
        "mater fixturen 'nagonting gick fel' och inte 'det har kravet ar ett "
        "krav'",
        "felet ska saga VILKET beteende som fattas",
    ),
    "kraver": ("vc",),
    "matningar": ("M-101",),
}
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import komponentmodell as K            # noqa: E402
from vc_assist_svc.klient import Klient                   # noqa: E402

# Operatoren arbetar pa skarmen. VC kors headless pa :99 och DISPLAY arvs
# ALDRIG ur miljon: en arvd DISPLAY landade en gang pa operatorens :1 mitt i
# hans arbete. Varden star har, och _verifiera_prefix laser tillbaka den ur
# /proc/<pid>/environ efter starten.
DISPLAY = ":99"
PREFIX = os.path.expanduser("~/.wine-vc-test")
FORBJUDET_PREFIX = os.path.expanduser("~/.wine-vc")

TOKEN = os.path.join(PREFIX, "drive_c/users/anton/vc_assist_token")
STARTSKRIPT = os.path.join(PREFIX, "drive_c/users/anton/vc_assist_startskript.py")
LOGG = os.path.join(PREFIX, "drive_c/users/anton/vc_assist_fas20.json")

# Uppstallningens matt. Inga trosklar: domarna jamfor MOT dem i stallet for
# att anta dem. Talen ar valda sa att en produkt hinner hela kedjan flera
# ganger inom provfonstret.
INTERVALL_S = 3.0        # matarens Interval
HASTIGHET_MM_S = 400.0   # banornas Speed
MATARLANGD_MM = 400.0
BANLANGD_MM = 2000.0
BUFFERTLANGD_MM = 1000.0
SANKLANGD_MM = 400.0
BUFFERTPLATSER = 10

# Sa manga intervall provfonstret minst maste spanna for att en tystnad ska
# betyda nagot. Satt av M-40, dar sju intervall utan produkt var det som
# skilde en trasig linje fran en hel.
TYSTA_INTERVALL = 5

# Kedjan: alla fyra klasserna i ETT flode.
KEDJA = (
    ("matare", "F20_Matare", MATARLANGD_MM),
    ("transportor", "F20_Bana", BANLANGD_MM),
    ("buffert", "F20_Buffert", BUFFERTLANGD_MM),
    ("sanka", "F20_Sanka", SANKLANGD_MM),
)
# Vilket beteende som BAR material i varje klass -- det provet laser antal ur.
BARARE = {"matare": "Creator", "transportor": "Path", "buffert": "Path",
          "sanka": "Sink"}

MALL = "F20_Produkt"

MALLKOD = """
app = getApplication()
_g = app.findComponent(str(%(mall)r))
if _g is not None:
    app.deleteComponent(_g)
_p = app.createComponent()
_p.Name = str(%(mall)r)
_f = _p.RootFeature.createFeature(VC_BLOCK, str('Kropp'))
for _q in _f.Properties:
    if _q.Name in ('Length', 'Width', 'Height'):
        _q.Value = 200.0
_p.RootFeature.rebuild()
_m = _p.PositionMatrix
_m.translateAbs(-6000.0 - _m.P.X, 0.0 - _m.P.Y, 0.0 - _m.P.Z)
_p.PositionMatrix = _m
""" % {"mall": MALL}

# Provkoden: LASANDE, en avlasning per anrop genom bryggans ko.
PROVKOD = """import json
app = getApplication()
sim = getSimulation()
ut = {"t": sim.SimTime, "kedja": [], "komponenter": len(app.Components)}
for namn, beh in %r:
    k = app.findComponent(str(namn))
    if k is None:
        continue
    b = k.findBehaviour(str(beh))
    if b is None:
        continue
    rad = {"komponent": namn, "beteende": beh, "antal": b.ComponentCount,
           "produkter": []}
    for c in b.Components:
        w = c.WorldPositionMatrix
        try:
            d = c.getPathDistance()
        except Exception:
            d = None
        rad["produkter"].append({"namn": c.Name, "skapad": c.CreationTime,
                                 "banavstand": d, "x": w.P.X})
    ut["kedja"].append(rad)
print(json.dumps(ut))
"""


def _parvis_uppstallning():
    """De fyra trasiga fallen, ett per klass, vart och ett med motpart och
    hel tvilling. Returnerar poster som beskriver hela provet."""
    fall = []
    for i, klass in enumerate(("transportor", "matare", "sanka", "buffert")):
        y = -3000.0 * (i + 1)
        nyckel = K.TRASIG_UTELAMNING[klass]
        krav = [b for b in K.KLASSER[klass].beteenden if b.nyckel == nyckel][0]
        if klass == "matare":
            # Malet ar en matare: motparten maste sta NEDSTROMS.
            motpart = ("transportor", "F20_P%d" % i,
                       {"langd": BANLANGD_MM, "hastighet": HASTIGHET_MM_S,
                        "x": MATARLANGD_MM, "y": y})
            mal_arg = {"langd": MATARLANGD_MM, "mall": MALL,
                       "intervall": 100000.0, "grans": 1000, "x": 0.0, "y": y}
            riktning = "mal_till_motpart"
        else:
            motpart_langd = MATARLANGD_MM if klass == "transportor" else BANLANGD_MM
            motpart_klass = "matare" if klass == "transportor" else "transportor"
            arg = {"langd": motpart_langd, "x": 0.0, "y": y}
            if motpart_klass == "matare":
                arg.update({"mall": MALL, "intervall": 100000.0, "grans": 1000})
            else:
                arg["hastighet"] = HASTIGHET_MM_S
            motpart = (motpart_klass, "F20_P%d" % i, arg)
            mal_arg = {"x": motpart_langd, "y": y}
            if klass == "buffert":
                mal_arg.update({"langd": BUFFERTLANGD_MM,
                                "hastighet": HASTIGHET_MM_S,
                                "kapacitet": BUFFERTPLATSER})
            elif klass == "transportor":
                mal_arg.update({"langd": BANLANGD_MM,
                                "hastighet": HASTIGHET_MM_S})
            else:
                mal_arg["langd"] = SANKLANGD_MM
            riktning = "motpart_till_mal"
        fall.append({
            "klass": klass, "utelamnat": nyckel,
            "beteende": krav.namn, "konstant": krav.konstant,
            "motpart": motpart,
            "trasig": "F20_B%d" % i, "hel": "F20_G%d" % i,
            "argument": mal_arg, "riktning": riktning, "y": y,
        })
    return fall


FALL = _parvis_uppstallning()


def _koppling(fall, malnamn):
    motpart_namn = fall["motpart"][1]
    if fall["riktning"] == "mal_till_motpart":
        return malnamn, motpart_namn
    return motpart_namn, malnamn


# Sista raden i komponentmodellens hjalpardel. Varje genererad kodblock bar
# HELA hjalparfoljet (~7 kB), och 27 block ger ett startskript pa 232 kB. Att
# skriva foljet en gang ar en ren omflyttning -- allt i det ar funktionsdefar
# och idempotenta tilldelningar -- men den maste vara BEVISAD, inte antagen:
# hittas inte markoren skrivs allt ut som det ar.
_FOLJETS_SLUT = "    return [m.P.X, m.P.Y, m.P.Z]\n"


def _dedupera(delar):
    """Ett gemensamt hjalparfolje, sedan varje blocks egen kropp."""
    rena = [d.replace("from __future__ import print_function\n", "")
            for d in delar]
    genererade = [d for d in rena if _FOLJETS_SLUT in d]
    if len(genererade) < 2:
        return "\n".join(rena)
    folje = genererade[0][:genererade[0].index(_FOLJETS_SLUT) + len(_FOLJETS_SLUT)]
    for d in genererade:
        if not d.startswith(folje):
            # Foljet ser inte likadant ut i alla block: skriv ut allt hellre
            # an att klippa fel.
            return "\n".join(rena)
    ut = [folje]
    for d in rena:
        ut.append(d[len(folje):] if d.startswith(folje) else d)
    return "\n".join(ut)


def _startskript():
    """Koden bridge_cmd kor FORE startSimulation(). Bara dar initieras
    beteendena (M-40 villkor 1); en komponent byggd i en redan korande
    simulering fyrar aldrig."""
    delar = [MALLKOD]

    # ---- kedjan: alla fyra klasserna i ett flode ----
    x = 0.0
    for klass, namn, langd in KEDJA:
        arg = {"langd": langd, "x": x, "y": 0.0}
        if klass == "matare":
            arg.update({"mall": MALL, "intervall": INTERVALL_S, "grans": 1000000})
        elif klass in ("transportor", "buffert"):
            arg["hastighet"] = HASTIGHET_MM_S
            if klass == "buffert":
                arg["kapacitet"] = BUFFERTPLATSER
        else:
            arg["kapacitet"] = 1000000
        delar.append(K.bygg(klass, namn, arg))
        x += langd
    for (ka, na, _la), (kb, nb, _lb) in zip(KEDJA, KEDJA[1:]):
        delar.append(K.koppla(na, nb, etikett="kedja:%s->%s" % (ka, kb),
                              vantas_ga=True))

    # ---- de fyra trasiga fallen, parvis mot en hel tvilling ----
    for fall in FALL:
        mk, mn, ma = fall["motpart"]
        delar.append(K.bygg(mk, mn, ma))
        # Trasig och hel star pa SAMMA plats i varlden. Da kan skillnaden i
        # utfall inte skyllas pa geometrin.
        delar.append(K.bygg(fall["klass"], fall["trasig"], fall["argument"],
                            utelamna=fall["utelamnat"]))
        delar.append(K.bygg(fall["klass"], fall["hel"], fall["argument"]))
        a, b = _koppling(fall, fall["trasig"])
        delar.append(K.koppla(a, b, etikett="trasig:%s" % fall["klass"],
                              vantas_ga=False))
        a, b = _koppling(fall, fall["hel"])
        delar.append(K.koppla(a, b, etikett="hel:%s" % fall["klass"],
                              vantas_ga=True))

    kropp = _dedupera(delar)
    inne = "\n".join(("    " + r) if r.strip() else "" for r in kropp.splitlines())
    return (
        "from __future__ import print_function\n"
        "# Skrivet av tests/protocol/kor_fas20_modellen.py. Kors av bridge_cmd\n"
        "# FORE startSimulation(); dar, och bara dar, initieras beteendena.\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "import traceback\n"
        "\n"
        "_LOGG = os.path.join(os.path.expanduser('~'), 'vc_assist_fas20.json')\n"
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


# ---- VC-hanteringen --------------------------------------------------------

def _vc_processer():
    """(pid, environ) for varje korande VC-motor. Lases ur /proc, inte ur
    var egen miljo: det ar det enda stallet dar VC:s VERKLIGA DISPLAY star."""
    ut = []
    for post in os.listdir("/proc"):
        if not post.isdigit():
            continue
        try:
            with open("/proc/%s/cmdline" % post, "rb") as f:
                argv = f.read().decode("utf-8", "replace").split("\0")
            # argv[0], inte en delstrang av hela raden. En sokning som bara
            # fragar "star namnet nagonstans i kommandoraden" traffar sitt
            # EGET skal: skriptet som letar bar namnet i sin egen rad och
            # rapporterade sig sjalvt som en VC i fel prefix.
            if not argv or not argv[0].endswith("VisualComponents.Engine.exe"):
                continue
            miljo = {}
            with open("/proc/%s/environ" % post, "rb") as f:
                for rad in f.read().decode("utf-8", "replace").split("\0"):
                    if "=" in rad:
                        n, v = rad.split("=", 1)
                        miljo[n] = v
            ut.append((int(post), miljo))
        except (IOError, OSError):
            continue
    return ut


def _verifiera_prefix():
    """VC MASTE kora i testprefixet pa :99. Operatorens prefix rors aldrig,
    och hans skarm ar inte var."""
    fel = []
    processer = _vc_processer()
    if not processer:
        return ["ingen VisualComponents.Engine.exe hittad i /proc"]
    for pid, miljo in processer:
        pfx = miljo.get("WINEPREFIX", "")
        dsp = miljo.get("DISPLAY", "")
        if os.path.normpath(pfx) == os.path.normpath(FORBJUDET_PREFIX):
            fel.append("pid %d kor i OPERATORENS prefix %s" % (pid, pfx))
        elif os.path.normpath(pfx) != os.path.normpath(PREFIX):
            fel.append("pid %d kor i okant prefix %r" % (pid, pfx))
        if dsp != DISPLAY:
            fel.append("pid %d har DISPLAY=%r, inte %r" % (pid, dsp, DISPLAY))
    return fel


def _far_stoppa():
    """~/bin/vc-stoppa.sh dodar VARJE VisualComponents.Engine.exe, oavsett
    prefix. Kor operatoren VC i sitt eget prefix far vi INTE stoppa nagot --
    hans prefix rors aldrig av oprovad kod, och det galler ocksa att sla av
    det. Fail-closed: kan vi inte se prefixet stannar vi."""
    fel = []
    for pid, miljo in _vc_processer():
        pfx = miljo.get("WINEPREFIX", "")
        if os.path.normpath(pfx) != os.path.normpath(PREFIX):
            fel.append("pid %d kor i %r, inte i testprefixet -- stoppar inte"
                       % (pid, pfx))
    return fel


def _starta_om_vc():
    subprocess.call([os.path.expanduser("~/bin/vc-stoppa.sh")])
    miljo = dict(os.environ)
    miljo["DISPLAY"] = DISPLAY          # aldrig arvd
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


def _las_bygglogg():
    with open(LOGG, "r") as f:
        rad = json.load(f)
    poster = []
    for r in (rad.get("stdout") or "").splitlines():
        r = r.strip()
        if not r.startswith("{"):
            continue
        try:
            poster.append(json.loads(r))
        except ValueError:
            continue
    return rad, poster


def _prov(k):
    par = [(namn, BARARE[klass]) for klass, namn, _l in KEDJA]
    post = k.anrop("exec_queue", {"code": PROVKOD % (par,),
                                  "desc": "fas20: las kedjan"})["result"]
    ut = k.godkann_och_vanta(post["qid"], timeout=60.0)
    if ut["state"] != "done":
        raise RuntimeError("provet gick inte igenom: %s" % ut["state"])
    return ((ut.get("svar") or {}).get("result") or {}).get("result")


# ---- domarna ---------------------------------------------------------------

def _dom_bygget(poster):
    """Halv ett: byggdes de fyra minsta uppsattningarna, och ar de HELA
    enligt modellens egen granskning?"""
    fel = []
    rader = []
    byggda = {p["component"]: p for p in poster if p.get("built")}
    for klass, namn, _langd in KEDJA:
        p = byggda.get(namn)
        if p is None:
            fel.append("%s (%s) byggdes inte alls" % (namn, klass))
            continue
        r = K.granska(p)
        rader.append((namn, klass, r))
        if not r.hel:
            fel.append("%s (%s) ar inte hel:\n      %s"
                       % (namn, klass, r.text().replace("\n", "\n      ")))
    return fel, rader, byggda


def _dom_kopplingarna(poster):
    """Halv tva: blev canConnect sant mellan de par specen sager ska ga ihop,
    och FALSKT mot de trasiga?"""
    fel = []
    rader = []
    kopplingar = {p["koppling"]: p for p in poster if "koppling" in p}
    for etikett, post in sorted(kopplingar.items()):
        kan = post.get("canConnect")
        vantat = post.get("vantas_ga")
        stamde = bool(kan) == bool(vantat)
        rader.append((etikett, kan, post.get("connect"), vantat, stamde))
        if not stamde:
            fel.append("%s: canConnect=%s, vantat %s" % (etikett, kan, vantat))
        if vantat and kan and not post.get("connect"):
            fel.append("%s: canConnect var True men connect gav %r"
                       % (etikett, post.get("connect")))
    return fel, rader, kopplingar


def _dom_trasiga(byggda, kopplingar):
    """Fasens poang. Tva halvor, bada maste halla:
      1. VC sager nej (canConnect False) mot den trasiga, JA mot den hela
         tvillingen pa samma plats,
      2. var egen granskning NAMNGER det utelamnade beteendet.
    """
    fel = []
    rader = []
    for fall in FALL:
        klass = fall["klass"]
        trasig = kopplingar.get("trasig:%s" % klass)
        hel = kopplingar.get("hel:%s" % klass)
        byggd = byggda.get(fall["trasig"])
        namngivet = None
        if byggd is None:
            fel.append("%s: den trasiga fixturen byggdes inte" % klass)
        else:
            rapport = K.granska(byggd)
            namngivet = rapport.saknade_beteenden()
            if namngivet != [fall["beteende"]]:
                fel.append("%s: granskningen namngav %r, vantat [%r]"
                           % (klass, namngivet, fall["beteende"]))
            if fall["konstant"] not in rapport.text():
                fel.append("%s: felet namner inte konstanten %s"
                           % (klass, fall["konstant"]))
        regel = None
        if trasig is not None:
            r, text = K.varfor_inte(trasig.get("post_a"), trasig.get("post_b"))
            regel = None if r is None else (r.id, text)
            if not trasig.get("canConnect") and r is None:
                fel.append("%s: VC sa nej men var matchningsregel hittar inget "
                           "villkor som brast -- regeln forklarar inte utfallet"
                           % klass)
        if trasig is None:
            fel.append("%s: kopplingen mot den trasiga provades aldrig" % klass)
        elif trasig.get("canConnect"):
            fel.append("%s: den TRASIGA gick att koppla (canConnect True) -- "
                       "da ar %s inget krav, och kravlistan ljuger"
                       % (klass, fall["beteende"]))
        if hel is None:
            fel.append("%s: den hela tvillingen provades aldrig" % klass)
        elif not hel.get("canConnect"):
            fel.append("%s: den HELA tvillingen gick inte heller att koppla -- "
                       "da mater provet nagot annat an det utelamnade "
                       "beteendet" % klass)
        rader.append({
            "klass": klass, "beteende": fall["beteende"],
            "trasig_kan": None if trasig is None else trasig.get("canConnect"),
            "hel_kan": None if hel is None else hel.get("canConnect"),
            "namngivet": namngivet, "regel": regel,
        })
    return fel, rader


def _dom_flodet(serie):
    """Halv tre, och den som avgor: ROR SIG MATERIAL igenom kedjan?"""
    fel = []
    if len(serie) < 2:
        return ["for fa prov for att saga nagot om rorelse"], {}
    spann = serie[-1]["t"] - serie[0]["t"]
    per_komponent = {}
    for prov in serie:
        for rad in prov.get("kedja", []):
            per_komponent.setdefault(rad["komponent"], []).append((prov["t"], rad))

    # 1. skapades produkter?
    skapelser = sorted({p["skapad"]
                        for _t, rad in sum(per_komponent.values(), [])
                        for p in rad["produkter"]})
    if len(skapelser) < 2:
        fel.append("bara %d produkt(er) skapades -- mataren matar inte"
                   % len(skapelser))
    mellanrum = [b - a for a, b in zip(skapelser, skapelser[1:])]

    # 2. rorde sig nagon produkt langs en bana?
    kvoter = []
    banan = per_komponent.get("F20_Bana", [])
    for (t1, r1), (t2, r2) in zip(banan, banan[1:]):
        dt = t2 - t1
        if dt <= 0:
            continue
        for a in r1["produkter"]:
            for b in r2["produkter"]:
                if (a["namn"] == b["namn"] and a["banavstand"] is not None
                        and b["banavstand"] is not None
                        and b["banavstand"] > a["banavstand"]):
                    kvoter.append((b["banavstand"] - a["banavstand"]) / dt)
    if not kvoter:
        fel.append("ingen produkt flyttade sig mellan tva prov pa F20_Bana -- "
                   "kedjan ar kopplad men star still")

    # 3-4. nadde materialet buffert och sanka?
    nadde = {}
    for namn in ("F20_Bana", "F20_Buffert", "F20_Sanka"):
        nadde[namn] = max([rad["antal"] for _t, rad in per_komponent.get(namn, [])]
                          or [0])
        if not nadde[namn]:
            fel.append("ingen produkt nadde %s pa %.1f simulerade sekunder"
                       % (namn, spann))
    if spann < TYSTA_INTERVALL * INTERVALL_S:
        fel.append("provfonstret spanner bara %.1f s; en tystnad betyder "
                   "ingenting under %.1f s"
                   % (spann, TYSTA_INTERVALL * INTERVALL_S))
    return fel, {"spann": spann, "skapelser": skapelser, "mellanrum": mellanrum,
                 "kvoter": kvoter, "nadde": nadde}


STADKOD = """import json
app = getApplication()
_bort = []
for _c in list(app.Components):
    if _c.Name[:4] == 'F20_':
        _bort.append(_c.Name)
        app.deleteComponent(_c)
print(json.dumps({"bortagna": _bort}))
"""


def _stada(k):
    """VC ar DELAD, och en annan agents oga provtar `scen: all`. Lamnar vi
    sexton F20-komponenter kvar hamnar de i NAGON ANNANS matning. Mätt:
    medan den har korningen forbereddes stod `ogat startat ... parts:
    [F20_Produkt]` i bryggloggen -- vara komponenter i deras provtagning.
    """
    post = k.anrop("exec_queue", {"code": STADKOD,
                                  "desc": "fas20: stada bort F20-komponenterna",
                                  "tillat_skriptbeteende": False})["result"]
    ut = k.godkann_och_vanta(post["qid"], timeout=60.0)
    if ut["state"] != "done":
        return None
    svar = ((ut.get("svar") or {}).get("result") or {}).get("result") or {}
    return svar.get("bortagna")


def _aterstall_startskriptet():
    """VC ar DELAD. Lamnar vi vart startskript kvar bygger nasta omstart --
    nagon annans -- vara matkomponenter i deras scen. Komponenterna star kvar
    i den korande sessionen; det ar bara nasta start som ateratar sitt.
    """
    reserv = STARTSKRIPT + ".fore_fas20"
    if not os.path.exists(reserv):
        return
    with open(reserv, "r") as f:
        kalla = f.read()
    with open(STARTSKRIPT, "w") as f:
        f.write(kalla)
    os.remove(reserv)
    print("  startskriptet aterstallt till det som last fore korningen")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--starta-om", action="store_true",
                    help="stoppa och starta VC sjalv (kraver ~/bin/vc-*.sh)")
    ap.add_argument("--bara-skriv", action="store_true",
                    help="skriv startskriptet och sluta; ror inte VC")
    ap.add_argument("--prov", type=int, default=16)
    ap.add_argument("--paus", type=float, default=2.0)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    kalla = _startskript()
    if not a.bara_skriv:
        gammal = None
        if os.path.exists(STARTSKRIPT):
            with open(STARTSKRIPT, "r") as f:
                gammal = f.read()
        if gammal is not None:
            with open(STARTSKRIPT + ".fore_fas20", "w") as f:
                f.write(gammal)
    mal = (os.path.join(tempfile.gettempdir(), "fas20_startskript.py")
           if a.bara_skriv else STARTSKRIPT)
    with open(mal, "w") as f:
        f.write(kalla)
    print("  startskript: %d tecken, %d komponenter, %d kopplingar"
          % (len(kalla), len(KEDJA) + 3 * len(FALL),
             len(KEDJA) - 1 + 2 * len(FALL)))
    if a.bara_skriv:
        print("  (--bara-skriv: VC ororda)")
        return 0

    if a.starta_om:
        sparr = _far_stoppa()
        for r in sparr:
            print("  FEL  %s" % r)
        if sparr:
            return 1
        print("  startar om VC pa DISPLAY=%s i %s ..." % (DISPLAY, PREFIX))
        _starta_om_vc()
        if not _vanta_pa_bryggan(420.0):
            print("  FEL  bryggan kom aldrig upp")
            return 1
    else:
        print("  VC MASTE startas om for hand innan matningen betyder nagot:")
        print("      ~/bin/vc-stoppa.sh && DISPLAY=%s ~/bin/vc-test.sh &" % DISPLAY)
        if not _vanta_pa_bryggan(5.0):
            print("  FEL  ingen brygga svarar")
            return 1

    miljofel = _verifiera_prefix()
    for r in miljofel:
        print("  FEL  %s" % r)
    if miljofel:
        return 1
    print("  VC verifierad ur /proc: DISPLAY=%s, WINEPREFIX=%s" % (DISPLAY, PREFIX))

    rad, poster = _las_bygglogg()
    if rad.get("fel"):
        print("  startskriptet foll:\n%s" % rad["fel"])
    print("  startskriptet gav %d JSON-poster" % len(poster))

    byggfel, byggrader, byggda = _dom_bygget(poster)
    kopplingsfel, kopplingsrader, kopplingar = _dom_kopplingarna(poster)
    trasigfel, trasigrader = _dom_trasiga(byggda, kopplingar)

    k = Klient(port=8901, tokenfil=TOKEN, timeout=120.0).anslut()
    serie = []
    for _ in range(a.prov):
        serie.append(_prov(k))
        time.sleep(a.paus)
    bortagna = _stada(k)
    k.stang()
    flodesfel, flode = _dom_flodet(serie)
    _aterstall_startskriptet()
    print("  stadade bort %s F20-komponenter ur den delade scenen"
          % ("?" if bortagna is None else len(bortagna)))

    print("\n=== 1. de fyra minsta uppsattningarna, byggda ur specen ===")
    for namn, klass, r in byggrader:
        p = byggda[namn]
        print("  %-12s %-12s %s"
              % (namn, klass, "HEL" if r.hel else "BRISTER: " + r.text()))
        print("               beteenden: %s"
              % ", ".join(b["name"] for b in p.get("behaviours", [])))
    print("\n=== 2. kopplingarna ===")
    for etikett, kan, kopplad, vantat, stamde in kopplingsrader:
        print("  %-24s canConnect=%-5s connect=%-5s (vantat %s)  %s"
              % (etikett, kan, kopplad, vantat, "OK" if stamde else "FEL"))
    print("\n=== 3. de trasiga fixturerna (parvis mot en hel tvilling) ===")
    for r in trasigrader:
        print("  %-12s utan %-8s  trasig: canConnect=%-5s   hel: canConnect=%-5s"
              % (r["klass"], r["beteende"], r["trasig_kan"], r["hel_kan"]))
        print("               var granskning namnger: %s" % (r["namngivet"],))
        if r.get("regel"):
            print("               matchningsregeln brast pa %s: %s"
                  % (r["regel"][0], r["regel"][1][:110]))
    print("\n=== 4. ror sig material igenom? ===")
    if flode:
        print("  simtid %.2f -> %.2f (%.1f s)"
              % (serie[0]["t"], serie[-1]["t"], flode["spann"]))
        print("  skapelsetider: %s" % (flode["skapelser"],))
        if flode["mellanrum"]:
            print("  mellanrum: %.4f - %.4f s (Interval %.1f)"
                  % (min(flode["mellanrum"]), max(flode["mellanrum"]), INTERVALL_S))
        if flode["kvoter"]:
            print("  hastighet ur %d par: %.4f - %.4f mm/s (Speed %.1f)"
                  % (len(flode["kvoter"]), min(flode["kvoter"]),
                     max(flode["kvoter"]), HASTIGHET_MM_S))
        for namn, antal in sorted(flode["nadde"].items()):
            print("  %-12s hogsta antal samtidigt: %d" % (namn, antal))

    if a.json:
        with open(a.json, "w") as f:
            json.dump({"poster": poster, "serie": serie,
                       "trasiga": trasigrader}, f, indent=1, sort_keys=True)

    alla = byggfel + kopplingsfel + trasigfel + flodesfel
    print("")
    for r in alla:
        print("  FEL  %s" % r)
    if alla:
        print("\n%d FEL" % len(alla))
        return 1
    print("  OK   fyra uppsattningar byggda ur specen, kopplade, material "
          "flodar igenom, och alla fyra trasiga fixturer falls med namn")
    return 0


if __name__ == "__main__":
    sys.exit(main())
