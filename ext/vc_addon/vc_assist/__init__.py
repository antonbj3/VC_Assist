# -*- coding: utf-8 -*-
"""VC Assist - uppstartskrok. vcApplication-scope: ingen logik, bara laddning.

Giltig i bade Python 2.7 (VC 4.x) och 3.x (VC 5.x).
Trasiga tillagg misslyckas TYST i VC (matt, M-01), darfor loggar vi sjalva.

Den har filen kor FORE nagot av vart eget ligger pa ``sys.path``, sa den kan
inte importera ``plats``. De tva funktionerna nedan ar darfor en avsiktlig
uppstartskopia av ``plats.sokvag_ur_uri`` och ``plats.anvandarmapp``. Att de
tva uppsattningarna svarar LIKA ar ett prov, inte en forhoppning:
``tests/enhet/test_plats.py`` plockar ut dem har med ast och kor dem mot
``plats`` over samma tabell miljoer.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from vcApplication import *

_LOG = "vc_assist_boot.log"


def _avkoda_procent(text):
    """%XX -> tecken. Uppstartskopia av plats._avkoda_procent."""
    if "%" not in text:
        return text
    ut = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "%" and i + 2 < n:
            try:
                ut.append(chr(int(text[i + 1:i + 3], 16)))
                i += 3
                continue
            except ValueError:
                pass
        ut.append(c)
        i += 1
    return "".join(ut)


def _sokvag_ur_uri(uri, avkoda=True):
    """``file:///C:/a%20b/`` -> ``C:\\a b``. Uppstartskopia av plats.sokvag_ur_uri.

    M-01: getApplicationPath() ger en URI, inte en sokvag. Utan den har
    oversattningen ar VC_ASSIST_DIR ALLTID ett varde som os.path.isdir sager
    nej till, och tillaggsmappen letas upp med ett os.walk som inte behovdes.
    """
    if not uri:
        return ""
    text = uri.replace("\\", "/")
    if text[:5].lower() != "file:":
        return uri
    text = text[5:]
    if text.startswith("///"):
        text = text[2:]
    elif text.startswith("//"):
        text = text[1:]
    if avkoda:
        text = _avkoda_procent(text)
    if len(text) >= 3 and text[0] == "/" and text[2] in ":|":
        text = text[1:]
        if text[1] == "|":
            text = text[0] + ":" + text[2:]
    if len(text) >= 2 and text[1] == ":":
        text = text.replace("/", "\\")
    if len(text) > 1 and text[-1] in "/\\":
        stam = text[:-1]
        if stam and not stam.endswith(":"):
            text = stam
    return text


def _anvandarmapp(env):
    """Mappen for token och loggar. Uppstartskopia av plats.anvandarmapp.

    USERPROFILE gar FORE HOME pa Windows med flit: Python 2.7:s expanduser
    laser HOME forst och Python 3.8+ gor det inte alls (bpo-36264), sa ett satt
    HOME hade lagt bryggans filer i en mapp tjansten inte tittar i.
    """
    import os
    uttryckligt = env.get("VC_ASSIST_HEM")
    if uttryckligt:
        return uttryckligt
    import sys
    plattform = sys.platform
    if plattform in ("win32", "cygwin", "msys") or plattform.startswith("win"):
        profil = env.get("USERPROFILE")
        if profil:
            return profil
        stig = env.get("HOMEPATH")
        if stig:
            return os.path.join(env.get("HOMEDRIVE", ""), stig)
        return os.path.expanduser("~")
    hem = env.get("HOME")
    if hem:
        return hem
    return os.path.expanduser("~")


def _log(msg):
    try:
        import os
        import time
        path = os.path.join(_anvandarmapp(os.environ), _LOG)
        f = open(path, "a")
        f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
        f.close()
    except Exception:
        pass


def _lagg_pa_sokvagen(uri):
    """Gor VC_ASSIST_DIR till en RIKTIG mapp och lagg den pa sys.path.

    Bada sakerna ar nya, och bada ar fallback-sakra: gar oversattningen inte
    att verifiera mot disk star VC_ASSIST_DIR kvar som URI:n, precis som forut,
    och bridge_cmd.py letar upp mappen sjalv.
    """
    import os
    import sys
    for kandidat in (_sokvag_ur_uri(uri, True), _sokvag_ur_uri(uri, False)):
        if kandidat and os.path.isdir(kandidat):
            if kandidat not in sys.path:
                sys.path.insert(0, kandidat)
            return kandidat
    return None


def OnAppInitialized():
    _log("OnAppInitialized")
    try:
        import os
        # I ett tilläggs vcApplication-scope ar getApplicationPath() tillaggets
        # EGEN mapp, som en file:///-URI (M-01). Kommandot kors i ett annat
        # scope dar samma namn betyder nagot annat, sa sokvagen skickas vidare
        # i miljon i stallet for att gissas om.
        uri = getApplicationPath()
        mapp = _lagg_pa_sokvagen(uri)
        os.environ["VC_ASSIST_DIR"] = mapp or uri
        _log("tillaggsmapp: %s (ur %s)" % (mapp or "OTOLKAD", uri))
        uri_cmd = uri + "bridge_cmd.py"
        _log("loadCommand uri=%s" % uri_cmd)
        cmd = loadCommand("vcAssistBridge", uri_cmd)
        if cmd is None:
            _log("loadCommand returnerade None")
            return
        cmd.execute()
        _log("bridge_cmd executed")
    except Exception as e:
        _log("FEL i OnAppInitialized: %r" % (e,))
