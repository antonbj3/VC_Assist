# -*- coding: utf-8 -*-
"""VC Assist - uppstartskrok. vcApplication-scope: ingen logik, bara laddning.

Giltig i bade Python 2.7 (VC 4.x) och 3.x (VC 5.x).
Trasiga tillagg misslyckas TYST i VC (matt, M-01), darfor loggar vi sjalva.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from vcApplication import *

_LOG = "vc_assist_boot.log"


def _log(msg):
    try:
        import os
        import time
        path = os.path.join(os.path.expanduser("~"), _LOG)
        f = open(path, "a")
        f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
        f.close()
    except Exception:
        pass


def OnAppInitialized():
    _log("OnAppInitialized")
    try:
        uri = getApplicationPath() + "bridge_cmd.py"
        _log("loadCommand uri=%s" % uri)
        cmd = loadCommand("vcAssistBridge", uri)
        if cmd is None:
            _log("loadCommand returnerade None")
            return
        cmd.execute()
        _log("bridge_cmd executed")
    except Exception as e:
        _log("FEL i OnAppInitialized: %r" % (e,))
