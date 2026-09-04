# -*- coding: utf-8 -*-
"""M-03: mater om OnRender fyrar och i vilken takt.

Detta ar ANNU INTE bryggan. Det ar matningen som avgor om OnRender duger
som pump. Byggs ut till full brygga forst nar takten ar kand.

Giltig i bade Python 2.7 och 3.x.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import time

from vcCommand import *

app = getApplication()

_OUT = os.path.join(os.path.expanduser("~"), "vc_assist_m03.log")
_state = {"n": 0, "t0": time.time(), "last_write": 0.0, "sim_ticks": 0}
_prev_handler = getattr(app, "OnRender", None)


def _write(msg):
    try:
        f = open(_OUT, "a")
        f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
        f.close()
    except Exception:
        pass


def _pump(sim=None):
    _state["n"] += 1
    try:
        if sim is not None and getattr(sim, "IsRunning", False):
            _state["sim_ticks"] += 1
    except Exception:
        pass
    now = time.time()
    if now - _state["last_write"] >= 5.0:
        elapsed = now - _state["t0"]
        rate = _state["n"] / elapsed if elapsed > 0 else 0.0
        _write("ticks=%d elapsed=%.1fs rate=%.2fHz sim_ticks=%d"
               % (_state["n"], elapsed, rate, _state["sim_ticks"]))
        _state["last_write"] = now
    # kedja vidare sa vi inte klipper nagon annans hanterare
    if callable(_prev_handler):
        try:
            _prev_handler(sim)
        except Exception:
            pass


def _capability():
    ytor = ("findComponent", "load", "render", "executeFrameGrab", "beginFrameGrab",
            "findCamera", "createView", "getSimulation", "Components", "Simulation",
            "loadCommand", "addMenuItem", "saveBitmap")
    rows = ["=== M-03 START %s ===" % time.strftime("%Y-%m-%d %H:%M:%S")]
    try:
        import sys
        rows.append("python=%s" % sys.version.split()[0])
    except Exception:
        pass
    for n in ytor:
        rows.append("has.%s=%s" % (n, hasattr(app, n)))
    rows.append("prev_OnRender_callable=%s" % callable(_prev_handler))
    _write("\n".join(rows))


_capability()
try:
    app.OnRender = _pump
    _write("OnRender bunden")
except Exception as e:
    _write("KUNDE INTE BINDA OnRender: %r" % (e,))
