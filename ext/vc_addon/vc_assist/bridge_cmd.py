# -*- coding: utf-8 -*-
"""M-04: far VC:s API roras fran en bakgrundstrad?

Om ja: bryggan behover ingen pump alls. Socketservern kan anropa API:t direkt.
Om nej: vi maste hitta en tredje vag, eftersom M-03 visade att varken
OnRender eller OnIdle fyrar nar programmet star stilla.

Giltig i bade Python 2.7 och 3.x.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import os
import threading
import time

from vcCommand import *

app = getApplication()

_OUT = os.path.join(os.path.expanduser("~"), "vc_assist_m04.log")
_lock = threading.Lock()


def _write(msg):
    try:
        with _lock:
            f = open(_OUT, "a")
            f.write("%s %s\n" % (time.strftime("%H:%M:%S"), msg))
            f.close()
    except Exception:
        pass


def _probe(where):
    """Samma API-anrop fran huvudtrad och bakgrundstrad. Ska ge samma svar."""
    rows = []
    try:
        rows.append("%s components=%d" % (where, len(app.Components)))
    except Exception as e:
        rows.append("%s components_FEL=%r" % (where, e))
    try:
        sim = app.getSimulation()
        rows.append("%s SimTime=%s IsRunning=%s" % (where, sim.SimTime, sim.IsRunning))
    except Exception as e:
        rows.append("%s sim_FEL=%r" % (where, e))
    try:
        rows.append("%s findCamera=%s" % (where, app.findCamera() is not None))
    except Exception as e:
        rows.append("%s camera_FEL=%r" % (where, e))
    try:
        c = app.load("", False)
        rows.append("%s load_tom=%s" % (where, c))
    except Exception as e:
        rows.append("%s load_FEL=%r" % (where, type(e).__name__))
    _write("\n".join(rows))


def _bg():
    time.sleep(3.0)
    _write("--- BAKGRUNDSTRAD startad, ident=%s" % threading.current_thread().ident)
    for i in range(3):
        _probe("[bg%d]" % i)
        time.sleep(4.0)
    _write("--- BAKGRUNDSTRAD klar (VC lever fortfarande om denna rad finns "
           "och appen inte kraschade)")


_write("=== M-04 START %s  huvudtrad=%s ==="
       % (time.strftime("%Y-%m-%d %H:%M:%S"), threading.current_thread().ident))
_probe("[main]")
t = threading.Thread(target=_bg)
t.daemon = True
t.start()
_write("bakgrundstrad startad")
