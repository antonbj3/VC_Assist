# -*- coding: utf-8 -*-
"""Uppstart av bryggan inne i VC. vcCommand-scope.

Bygger en dold komponent med ett VC_SCRIPT-beteende vars OnRun ar pumpen, och
startar simuleringen sa pumpen far ga i realtid.

Varfor just sa, kort - allt ar matt, inget antaget:

* app.startSimulation() atervander pa 8 ms och later simuleringen ga; skriptets
  delay(0.05) ger da 20,0 Hz mot vaggklockan (M-08). sim.run() daremot kor i
  maxfart och duger bara at ogat.
* Skriptets kallkod MASTE borja med "from vcScript import *", annars finns
  varken delay() eller getSimulation() och OnRun dor tyst (M-06).
* Allt som skrivs till VC:s py2-bindning maste vara bytestrang (M-05).
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
import sys as _sys
import time
import traceback

from vcCommand import *

vcCommand_modul = _sys.modules.get("vcCommand")

app = getApplication()
_LOG = os.path.join(os.path.expanduser("~"), "vc_assist_boot.log")
PORT = int(os.environ.get("VC_ASSIST_PORT", "8901"))
# Kortare an sa ar det inte en scenandring utan en loop.
OMSTART_MINSTA_MELLANRUM_S = 0.5    # PRELIMINAR. Satts av matning M-13.
_HANDLARE = []


def _log(msg):
    try:
        f = open(_LOG, "a")
        f.write("%s [cmd] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
        f.close()
    except Exception:
        pass


def _s(x):
    """Bytestrang i py2, oforandrad i py3. MATT M-05."""
    try:
        if isinstance(x, unicode):          # noqa: F821
            return x.encode("utf-8")
    except NameError:
        pass
    return x


def _tillaggsmapp():
    d = os.environ.get("VC_ASSIST_DIR")
    if d and os.path.isdir(d):
        return d
    # Reservvag: leta upp pump.py under Mina kommandon. Hellre en sokning som
    # syns i loggen an en gissad sokvag som tyst pekar fel.
    hem = os.path.expanduser("~")
    for rot, mappar, filer in os.walk(os.path.join(hem, "Documents")):
        if "pump.py" in filer and os.path.basename(rot) == "vc_assist":
            return rot
    return None


SKRIPT = """from vcScript import *
import sys, os

DIR = r'%(dir)s'
if DIR not in sys.path:
    sys.path.insert(0, DIR)
import pump

def _brygga():
    return pump.hamta_brygga(exec_globals=dict(globals()), port=%(port)d)

def _provobjekt():
    # Objekt att prova API-ytorna mot. Bryggans EGEN komponent anvands, sa
    # ingenting i operatorens layout rors. Ingen docstring har: hela SKRIPT
    # ar sjalv en trippelciterad strang.
    comp = getComponent()
    node = None
    try:
        barn = getattr(comp, 'Children', None)
        if barn:
            node = barn[0]
    except Exception:
        node = None
    if node is None:
        node = comp
    return {'app': getApplication(), 'sim': getSimulation(),
            'comp': comp, 'node': node}

def OnRun():
    b = _brygga()
    b.skriv_formaga(_provobjekt())
    b._markera_avbrutna()
    b.pumpen_igang()
    # Koppla om handlaren: en reset ser ut att nolla den.
    try:
        pump.INSTANS_KOPPLA()
    except Exception:
        pass
    b.logg('pumpen igang')
    sim = getSimulation()
    n = 0
    while not b.avslutad:
        # Simuleringstiden lases HAR. Kommandots scope ser en inaktuell
        # SimTime (M-08), sa den maste komma fran skriptets eget scope.
        b.tick(sim.SimTime)
        n += 1
        delay(b.nasta_paus())
    b.logg('pumpen stannade efter %%d varv' %% n)

def OnStop():
    # Sockeln stangs INTE har, och omstarten sker INTE har.
    #
    # MATT: ett OnStop som sjalvt anropade startSimulation() gjorde saken
    # VARRE. Utan reset() ateruppptas simuleringen bara, OnRun ater inte in,
    # och pumpen kommer aldrig tillbaka - men OnStartStop hade da redan fyrat
    # med igang=True, sa den handlare som KAN gora det ratt hoppade over.
    # Omstarten agas av OnStartStop-handlaren i kommandots scope.
    try:
        b = pump.INSTANS
        b.logg('simuleringen stoppad')
        if not b.begar_omstart():
            return
        # MATT: en omstart HARIFRAN aterupplivar inte pumpen. Vi star mitt i
        # nedmonteringen av skriptets egna tasklets, och OnRun ater inte in
        # hur vi an vander pa reset och start.
        #
        # Det enda startSimulation() harifran DUGER till ar att utlosa
        # vcSimulation.OnStartStop, vars handlare bor i KOMMANDOTS scope -
        # utanfor nedmonteringen. Dar, och bara dar, gors reset + start.
        b.omstartsfas = 1
        b.logg('ber om omstart (nr %%d) via OnStartStop' %% b.n_omstarter)
        getApplication().startSimulation()
    except Exception:
        try:
            import traceback
            pump.INSTANS.logg('OnStop-fel: ' + traceback.format_exc())
        except Exception:
            pass
"""


def _koppla_startstopp(app, sim, pump):
    """Registrerar en handlare pa vcSimulation.OnStartStop.

    MATT 2026-09-04, och det ar tre fynd i rad som tvingar fram just den har
    losningen:

    1. Kod som andrar scenen STOPPAR den korande simuleringen.
    2. Pumpens tasklet dodas i samma ogonblick - ingenting efter exec-raden
       kors, inte ens skriptets eget OnStop hinner starta om i tid.
    3. app.startSimulation() ensamt ATERUPPTAR bara; skriptets OnRun har redan
       kort klart och ater inte in. Det kraver sim.reset() forst.

    Handlaren registreras i KOMMANDOTS scope och lever alltsa utanfor den
    tasklet som dor. Det ar hela poangen.
    """
    if not hasattr(sim, "OnStartStop"):
        _log("vcSimulation saknar OnStartStop; bryggan overlever inte en scenandring")
        return

    def pa_startstopp(vilken_sim, igang):
        b = pump.INSTANS
        if b is None or igang:
            return
        if b.omstartsfas != 1:
            # Fas 0: ett vanligt stopp som ingen bett om att aterstalla.
            # Fas 2: var egen reset() som fyrar handlaren igen.
            return
        b.omstartsfas = 2
        try:
            b.logg("handlaren gor reset + start (nr %d)" % b.n_omstarter)
            sim.reset()
            app.startSimulation()
            b.logg("efter reset+start: IsRunning=%s" % sim.IsRunning)
        except Exception:
            b.logg("kunde inte starta om: " + traceback.format_exc())
            b._startar_om = False
            b.omstartsfas = 0

    sim.OnStartStop = pa_startstopp
    # Referensen maste leva kvar, annars stads handlaren bort.
    _HANDLARE.append(pa_startstopp)
    if len(_HANDLARE) == 1:
        _log("OnStartStop-handlare registrerad")


def _tillampa_uppskjutet(app, pump):
    """Kor det som kots upp for att det inte gick medan simuleringen ledde.

    Har, vid uppstart och FORE startSimulation(), ar samma operation ofarlig:
    ingen pump lever an, sa det finns ingenting att doda (M-13).
    """
    fil = os.path.join(os.path.expanduser("~"), "vc_assist_uppskjutet.json")
    if not os.path.exists(fil):
        return
    try:
        f = open(fil)
        try:
            poster = (json.load(f) or {}).get("poster", [])
        finally:
            f.close()
    except Exception:
        _log("kunde inte lasa uppskjutna poster:\n" + traceback.format_exc())
        return
    _log("tillampar %d uppskjuten post" % len(poster))
    kvar = []
    for post in poster:
        try:
            g = {"getApplication": lambda: app, "__name__": "__uppskjutet__"}
            for namn in dir(vcCommand_modul):
                if namn.startswith("VC_"):
                    g[namn] = getattr(vcCommand_modul, namn)
            exec(post.get("code", ""), g)
            _log("  tillampad: %s" % post.get("desc"))
        except Exception:
            _log("  MISSLYCKADES: %s\n%s" % (post.get("desc"), traceback.format_exc()))
            kvar.append(post)
    try:
        if kvar:
            f = open(fil, "w")
            try:
                json.dump({"v": 1, "poster": kvar}, f)
            finally:
                f.close()
        else:
            os.remove(fil)
    except Exception:
        pass


def _starta():
    _log("=== uppstart %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    d = _tillaggsmapp()
    if d is None:
        _log("hittade inte tillaggsmappen; bryggan startar inte")
        return
    _log("tillaggsmapp: %s" % d)
    try:
        _tillampa_uppskjutet(app, None)
        comp = app.createComponent()
        comp.Name = _s("VcAssistBridge")
        kalla = SKRIPT % {"dir": d.replace("\\", "\\\\"), "port": PORT}
        # Kompilera FORE tilldelningen. VC svaljer ett trasigt skript helt
        # (M-09): OnRun finns da bara inte, och ingenting sags nagonstans.
        try:
            compile(kalla, "<vc_assist_pump>", "exec")
        except SyntaxError as e:
            _log("SKRIPTET GAR INTE ATT KOMPILERA: rad %s: %s" % (e.lineno, e.msg))
            for nr, rad in enumerate(kalla.splitlines(), 1):
                if abs(nr - (e.lineno or 0)) <= 2:
                    _log("   %4d %s" % (nr, rad))
            return
        beh = comp.createBehaviour(VC_SCRIPT, _s("pump"))
        beh.Script = _s(kalla)
        _log("brygg-komponenten byggd, skriptet kompilerar")

        sim = app.getSimulation()
        import sys
        if d not in sys.path:
            sys.path.insert(0, d)
        import pump
        sim.reset()
        t0 = time.time()
        app.startSimulation()
        # EFTER start, inte fore: sim.reset() ser ut att nolla handelse-
        # kopplingen. En handlare registrerad fore reset fyrade aldrig, medan
        # samma handlare registrerad pa en redan gaende simulering gjorde det.
        _koppla_startstopp(app, sim, pump)
        pump.INSTANS_KOPPLA = lambda: _koppla_startstopp(app, sim, pump)
        _log("startSimulation() atervande efter %.3f s, IsRunning=%s"
             % (time.time() - t0, sim.IsRunning))
    except Exception:
        _log("FEL vid uppstart\n" + traceback.format_exc())


_starta()
