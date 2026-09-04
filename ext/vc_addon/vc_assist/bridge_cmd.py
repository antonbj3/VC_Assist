# -*- coding: utf-8 -*-
"""M-05c: pumpen. vcScript.OnRun med delay(), driven av sim.run().

M-05b visade att createComponent, createBehaviour och sim.run alla fungerar
pa modulniva i kommandot vid uppstart. Denna sond mater om skriptets OnRun
verkligen kors och i vilken takt, samt hur vaggklocka forhaller sig till
simuleringstid.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import time

from vcCommand import *

app = getApplication()
_OUT = os.path.join(os.path.expanduser("~"), "vc_assist_m05.log")
_HB = os.path.join(os.path.expanduser("~"), "vc_assist_m05_hb.log")

SCRIPT_SRC = "\n".join([
    # MATT M-06: utan denna rad finns varken delay() eller getSimulation()
    # i skriptets scope. OnRun kastar da NameError och VC slukar felet tyst.
    "from vcScript import *",
    "import os, time",
    "HB = r'" + _HB + "'",
    "",
    "def _w(msg):",
    "    try:",
    "        f = open(HB, 'a')",
    "        f.write(time.strftime('%H:%M:%S') + ' ' + str(msg) + '\\n')",
    "        f.close()",
    "    except Exception:",
    "        pass",
    "",
    "def OnRun():",
    "    app = getApplication()",
    "    sim = getSimulation()",
    "    t0 = time.time()",
    "    _w('ONRUN START simtime=' + str(sim.SimTime))",
    "    n = 0",
    "    while n < 100:",
    "        try:",
    "            app.delayRealTime(0.05)",
    "        except Exception as e:",
    "            _w('delayRealTime FEL: ' + type(e).__name__); delay(0.05)",
    "        n = n + 1",
    "        if n % 40 == 0:",
    "            wall = time.time() - t0",
    "            st = sim.SimTime",
    "            _w('n=' + str(n) + ' sim=' + ('%.2f' % st) + ' wall=' + ('%.2f' % wall)"
    " + ' wallHz=' + ('%.1f' % (n / wall if wall > 0 else 0))"
    " + ' simHz=' + ('%.1f' % (n / st if st > 0 else 0)))",
    "    _w('ONRUN SLUT n=' + str(n))",
    "",
    "def OnStop():",
    "    _w('ONSTOP')",
    "",
    "def OnStart():",
    "    _w('ONSTART')",
    "",
    "def OnReset():",
    "    _w('ONRESET')",
])



def _s(x):
    """Bytestrang i py2, oforandrad i py3.

    HYPOTES M-05: unicode_literals gor varje strangliteral till unicode, och
    VC:s py2-bindning tar bara bytestrangar. Darav SystemError vid varje
    skrivning av en strang (comp.Name, property.Value).
    """
    try:
        if isinstance(x, unicode):          # noqa: F821  (finns bara i py2)
            return x.encode("utf-8")
    except NameError:
        pass
    return x


def _w(msg):
    try:
        f = open(_OUT, "a")
        f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
        f.close()
    except Exception:
        pass


_w("=== M-05c %s ===" % time.strftime("%Y-%m-%d %H:%M:%S"))
try:
    # HYPOTES: att rora kontexten forst ar det som gor createComponent giltig.
    # I M-05b lastes CurrentContext fore, och da lyckades den. Utan, misslyckas den.
    ctx = app.CurrentContext
    _w("kontext=%s antal=%d" % (ctx.Id, len(app.Components)))
    comp = app.createComponent()
    _w("komponent skapad")
    # MATT: comp.Name = "..." pa en nyskapad komponent kastar SystemError.
    # Vi provar den separat och later den inte falla resten.
    try:
        comp.Name = _s("vcAssistBridge")
        _w("Name satt OK")
    except Exception as e:
        _w("Name FEL (kant): %s" % type(e).__name__)
    try:
        _w("komponentens namn nu: %r" % comp.Name)
    except Exception as e:
        _w("las Name FEL: %s" % type(e).__name__)
    beh = comp.createBehaviour(VC_SCRIPT, _s("BridgePump"))
    _w("beteende typ=%s repr=%s" % (type(beh).__name__, repr(beh)[:60]))
    try:
        _w("beteendets attribut: %s" % ", ".join(sorted(
            [a for a in dir(beh) if not a.startswith("_")])[:40]))
    except Exception as e:
        _w("dir FEL: %s" % type(e).__name__)
    satt = False
    for attr in ("Script", "Code", "ScriptText", "Text"):
        try:
            setattr(beh, attr, _s(SCRIPT_SRC))
            _w("SATT via .%s OK" % attr)
            satt = True
            break
        except Exception as e:
            _w("  .%s -> %s" % (attr, type(e).__name__))
    if not satt:
        try:
            pr = beh.getProperty(_s("Script"))
            _w("getProperty('Script') -> %r" % pr)
            if pr is not None:
                pr.Value = _s(SCRIPT_SRC)
                _w("SATT via getProperty().Value OK")
                satt = True
        except Exception as e:
            _w("getProperty FEL: %s %s" % (type(e).__name__, str(e)[:50]))
    if not satt:
        raise RuntimeError("kunde inte satta skriptkoden")
    sim = app.getSimulation()
    _w("fore reset: IsRunning=%s SimTime=%s" % (sim.IsRunning, sim.SimTime))
    # HYPOTES: skriptet initieras forst vid reset. OnRun kordes inte utan den.
    try:
        sim.reset()
        _w("sim.reset() OK, SimTime=%s" % sim.SimTime)
    except Exception as e:
        _w("reset FEL: %s" % type(e).__name__)
    # MATT M-06: run() kor i maxfart, 30 simulerade sekunder pa 0.01s vaggklocka.
    # For bryggan behovs realtid. Provar SimSpeed.
    try:
        _w("SimSpeed fore: %s" % sim.SimSpeed)
        sim.SimSpeed = 1.0
        _w("SimSpeed satt till %s" % sim.SimSpeed)
    except Exception as e:
        _w("SimSpeed FEL: %s %s" % (type(e).__name__, str(e)[:60]))
    w0 = time.time()
    sim.run(20.0)
    _w("efter run(30): vaggklocka=%.2fs SimTime=%s IsRunning=%s"
       % (time.time() - w0, sim.SimTime, sim.IsRunning))
except Exception as e:
    import traceback
    _w("FEL: %r" % (e,))
    _w(traceback.format_exc())
_w("=== M-05c slut ===")
