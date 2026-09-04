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

import os
import time
import traceback

from vcCommand import *

app = getApplication()
_LOG = os.path.join(os.path.expanduser("~"), "vc_assist_boot.log")
PORT = int(os.environ.get("VC_ASSIST_PORT", "8901"))


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
    b.logg('pumpen igang')
    n = 0
    while not b.avslutad:
        b.tick()
        n += 1
        delay(b.nasta_paus())
    b.logg('pumpen stannade efter %%d varv' %% n)

def OnStop():
    # Sockeln stangs INTE har. Bryggan ska overleva att simuleringen stoppas
    # och startas om; den slutar bara betjana tills pumpen gar igen.
    try:
        pump.INSTANS.logg('simuleringen stoppad, sockeln lamnas oppen')
    except Exception:
        pass
"""


def _starta():
    _log("=== uppstart %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
    d = _tillaggsmapp()
    if d is None:
        _log("hittade inte tillaggsmappen; bryggan startar inte")
        return
    _log("tillaggsmapp: %s" % d)
    try:
        comp = app.createComponent()
        comp.Name = _s("VcAssistBridge")
        beh = comp.createBehaviour(VC_SCRIPT, _s("pump"))
        beh.Script = _s(SKRIPT % {"dir": d.replace("\\", "\\\\"), "port": PORT})
        _log("brygg-komponenten byggd")

        sim = app.getSimulation()
        sim.reset()
        t0 = time.time()
        app.startSimulation()
        _log("startSimulation() atervande efter %.3f s, IsRunning=%s"
             % (time.time() - t0, sim.IsRunning))
    except Exception:
        _log("FEL vid uppstart\n" + traceback.format_exc())


_starta()
