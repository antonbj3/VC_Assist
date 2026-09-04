# -*- coding: utf-8 -*-
"""M-08: ar app.startSimulation() en vaggklockspump?

M-06: sim.run(t) kor i maxfart, SimSpeed paverkar inte.
M-07: motorn ar Stackless Python 2.7.1, och bakgrundstradar far CPU bara
medan huvudtraden star i ett anrop som slapper GIL. Tradmodellen ar dod.

Kvar star app.startSimulation() - gransnittets play-knapp. Till skillnad fran
sim.run() ska den atervanda direkt och lata simuleringen ga i realtid. Om det
stammer ar skriptets delay(0.05) en akta 20 Hz-pump mot vaggklockan.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import time

from vcCommand import *

app = getApplication()
_OUT = os.path.join(os.path.expanduser("~"), "vc_assist_m08.log")
_HB = os.path.join(os.path.expanduser("~"), "vc_assist_m08_hb.log")


def _log(msg):
    try:
        f = open(_OUT, "a")
        f.write(time.strftime("%H:%M:%S") + " " + str(msg) + "\n")
        f.close()
    except Exception:
        pass


def _s(x):
    """Bytestrang i py2, oforandrad i py3. MATT M-05."""
    try:
        if isinstance(x, unicode):
            return x.encode("utf-8")
    except NameError:
        pass
    return x


SCRIPT_SRC = "\n".join([
    "from vcScript import *",          # MATT M-06: utan denna dor OnRun tyst
    "import time",
    "HB = r'" + _HB + "'",
    "",
    "def _w(msg):",
    "    try:",
    "        f = open(HB, 'a')",
    "        f.write('%.3f ' % time.time() + str(msg) + '\\n')",
    "        f.close()",
    "    except Exception:",
    "        pass",
    "",
    "def OnRun():",
    "    sim = getSimulation()",
    "    t0 = time.time()",
    "    _w('ONRUN START')",
    "    n = 0",
    "    while n < 4000:",
    "        delay(0.05)",
    "        n += 1",
    "        if n % 20 == 0:",
    "            w = time.time() - t0",
    "            s = sim.SimTime",
    "            _w('n=%d sim=%.2f wall=%.2f kvot=%.3f' % (n, s, w, s / w if w > 0 else -1))",
    "    _w('ONRUN SLUT')",
])


def _sond():
    _log("=== M-08 " + time.strftime("%Y-%m-%d %H:%M:%S") + " ===")
    try:
        comp = app.createComponent()
        comp.Name = _s("vcAssistBridge")
        beh = comp.createBehaviour(VC_SCRIPT, _s("pump"))
        beh.Script = _s(SCRIPT_SRC)
        _log("brygga byggd")

        sim = app.getSimulation()
        sim.reset()

        t0 = time.time()
        app.startSimulation()
        dt = time.time() - t0
        _log("startSimulation() atervande efter %.3f s" % dt)
        _log("direkt efter: IsRunning=%s SimTime=%.3f" % (sim.IsRunning, sim.SimTime))

        # slapp GIL sa VC far kora; matning ligger i hjartslagsloggen
        time.sleep(2.0)
        _log("efter 2 s sleep: IsRunning=%s SimTime=%.3f" % (sim.IsRunning, sim.SimTime))
    except Exception as e:
        _log("FEL " + type(e).__name__ + ": " + str(e))
        import traceback
        _log(traceback.format_exc())
    _log("=== M-08 slut ===")


_sond()
