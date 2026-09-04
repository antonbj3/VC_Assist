# -*- coding: utf-8 -*-
"""Byggstenar for den kod som skickas till bryggan.

Koden kors av pump.py:_kor med exec() i VC:s inbaddade Python. Det ar
Stackless Python 2.7.1 pa VC 4.10 och 3.x pa VC 5.0 (36_versioner.md), sa
allt harifran maste vara giltigt i BADA. Darav:

* inga f-strangar, ingen print-sats, ingen except E, e
* ingen "from __future__ import unicode_literals". Varje strang som gar IN i
  VC:s API skickas i stallet genom _s(). MATT M-05: VC 4.10:s bindning tar
  bara bytestrangar och kastar SystemError pa unicode.
* _s tillhandahalls av bryggan, inte av mallen: pump.py lagger den i
  exec-globalerna vid varje korning. Kontraktet provas i test_verktyg.py sa
  att en flytt av _s inte kan ga obemarkt.

Svaret lamnas som JSON pa SISTA raden av stdout. Det ar bryggans svarskanal
(31_brygga_protokoll.md), och skalet ar att exec inte har nagot returvarde.

LASANDE kod maste dessutom passera skrivgrind.granska() inne i bryggan
(pump.py:_op_exec). Grinden ar syntaktisk och konservativ, sa mallarna
undviker de konstruktioner den maste doma som skrivande:
  - getattr/setattr/eval/exec  (den kan inte se vad de gor)
  - tilldelning till ett attribut  (obj.x = v)
  - anrop vars namn borjar pa set/add/create/delete/... utom pa en behallare
    koden sjalv byggt
Det ar inte en begransning vi lider av utan grinden vi valde: en lasande mall
som INTE gar igenom har en verklig sidoeffekt, eller ar for svar att se igenom.
"""
from __future__ import annotations

import json

# Tak for hur manga poster ett listande verktyg lamnar ifran sig.
# Harkomst: bryggans kropp far vara hogst MAX_KROPP = 1048576 byte
# (protokoll.py, ur 31_brygga_protokoll.md). En post ur list_components ar
# ~200 byte JSON, sa 500 poster blir ~100 kB = en tiondel av taket, med
# marginal for att posterna vaxer. Verktyget svarar alltid "avkortad": true
# nar det klipper, sa en for lag grans syns i svaret i stallet for att tyst
# forsvinna (I3, fail-closed).
MAX_POSTER = 500

_INLEDNING = "from __future__ import print_function\nimport json\n"

# Hjalpare -> (beroenden, kalla). Bara de som faktiskt anvands skrivs ut;
# en mall som bar oanvand kod ar skuld aven nar den ar genererad.
_HJALPARE = {
    "_TEXT": ((), '''
try:
    _TEXT = (str, unicode)
except NameError:
    _TEXT = (str,)
'''),
    "_enkelt": (("_TEXT",), '''
def _enkelt(v):
    # Varden ur VC ar ofta egna objekt (vcVector, upprakningar). JSON tar
    # bara enkla typer; resten gar ut som repr sa att svaret aldrig faller
    # pa ett varde det inte kan beskriva.
    if v is None or isinstance(v, bool) or isinstance(v, float):
        return v
    if isinstance(v, int):
        return v
    if isinstance(v, _TEXT):
        return v
    return repr(v)
'''),
    "_svara": ((), '''
def _svara(o):
    # Sista raden pa stdout ar bryggans svarskanal (31_brygga_protokoll.md).
    # sort_keys gor utdata jamforbar byte for byte mot en guldfil.
    print(json.dumps(o, sort_keys=True))
'''),
    "_app": ((), '''
def _app():
    return getApplication()
'''),
    "_komp": (("_app",), '''
def _komp(namn):
    k = _app().findComponent(_s(namn))
    if k is None:
        raise ValueError("ingen komponent heter " + namn)
    return k
'''),
    "_nod": ((), '''
def _nod(komp, stig):
    if not stig:
        return komp
    n = komp.findNode(_s(stig))
    if n is None:
        raise ValueError("komponenten har ingen nod som heter " + stig)
    return n
'''),
    "_ar_grans": ((), '''
def _ar_grans(b):
    # Ett simuleringsgranssnitt kanns igen pa sin YTA, inte pa en konstant.
    # VC_ONETOONEINTERFACE gar inte att formageprova (formaga.py provar
    # attribut pa objekt, inte namn i en modul), medan canConnect och
    # Sections gar. Samma regel som resten av tillagget: fraga vad som finns.
    return hasattr(b, "canConnect") and hasattr(b, "Sections")
'''),
    "_grans": (("_ar_grans",), '''
def _grans(komp, namn):
    b = komp.findBehaviour(_s(namn))
    if b is None:
        raise ValueError(komp.Name + " har inget beteende som heter " + namn)
    if not _ar_grans(b):
        raise ValueError(namn + " ar inget simuleringsgranssnitt")
    return b
'''),
    "_anslutna": ((), '''
def _anslutna(b):
    ut = []
    if hasattr(b, "ConnectedComponents") and b.ConnectedComponents:
        for c in b.ConnectedComponents:
            ut.append(c.Name)
    elif hasattr(b, "ConnectedComponent") and b.ConnectedComponent is not None:
        ut.append(b.ConnectedComponent.Name)
    return ut
'''),
}

# Fast ordning: en hjalpare far bara bero pa nagon som redan skrivits ut.
_ORDNING = ("_TEXT", "_enkelt", "_svara", "_app", "_komp", "_nod",
            "_ar_grans", "_grans", "_anslutna")


def _stang(namn):
    """Hjalparna plus allt de beror av."""
    ut = set()
    kvar = list(namn)
    while kvar:
        n = kvar.pop()
        if n in ut:
            continue
        if n not in _HJALPARE:
            raise KeyError("okand hjalpare %r i kodmallen" % (n,))
        ut.add(n)
        kvar.extend(_HJALPARE[n][0])
    return ut


def bygg(hjalpare, rader, importer=()):
    """Satter ihop en korbar mall.

    hjalpare: namn ur _HJALPARE. Beroenden dras in automatiskt.
    rader:    kroppen, en lista rader utan avslutande radbrytning.
    importer: extra moduler kroppen behover, t.ex. vcVector.
    """
    behovs = _stang(hjalpare)
    delar = [_INLEDNING]
    for i in importer:
        delar.append("import %s\n" % i)
    for namn in _ORDNING:
        if namn in behovs:
            delar.append(_HJALPARE[namn][1])
    delar.append("\n")
    delar.append("\n".join(rader))
    delar.append("\n")
    return "".join(delar)


def lit(varde):
    """Ett Python-literal som betyder samma sak i 2.7 och 3.x.

    Strangar blir _s(u"..."): unicode-literal i kallan, bytestrang nar den
    nar VC:s API (M-05). json.dumps ger en ASCII-ren literal med samma
    escape-regler som Python, sa aven svenska tecken och citattecken
    overlever vagen genom bryggans JSON-kuvert.
    """
    if isinstance(varde, bool) or varde is None:
        return repr(varde)
    if isinstance(varde, (int, float)):
        return repr(varde)
    if isinstance(varde, str):
        return '_s(u%s)' % json.dumps(varde, ensure_ascii=True)
    if isinstance(varde, (list, tuple)):
        return "[%s]" % ", ".join(lit(v) for v in varde)
    raise TypeError("kan inte skriva %s som literal i mallen"
                    % type(varde).__name__)


def tal(varde):
    """Rent tal utan _s. Anvands dar VC vantar sig ett Real."""
    if isinstance(varde, bool) or not isinstance(varde, (int, float)):
        raise TypeError("%r ar inget tal" % (varde,))
    return repr(float(varde))
