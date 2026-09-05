# -*- coding: utf-8 -*-
"""Fas 22: korpusen och de trasiga fallen, pa ETT stalle.

Bade acceptanskorningen (`tests/protocol/kor_fas22_modellagret.py`) och
enhetsproven (`tests/enhet/test_kontextbudget.py` med syskon) laser harifran.
Skalet ar att en fixtur som finns i tva kopior blir tva fixturer sa fort nagon
rattar den ena - samma regel som repot redan har om ordlistor (M-98).

KORPUSEN AR RIKTIG, INTE PAHITTAD
---------------------------------
Verktygssvaren kommer ur repots egna DATA_HANDLERS, anropade med argument som
ocksa kommer ur repot: katalogens 65 URI:er, bankens 51 uppgifter,
API-indexets typnamn, hjalpmodulernas egen uppraekning. Ingen brygga och ingen
VC ar inblandad - de verktyg som kraver en levande VC ar KODGENERERANDE och
lamnar en kodstrang, inte ett svar, sa deras svarsform kommer i stallet ur
deras DEKLARERADE `returns`.

Ogonrapporterna ar bankens egna: nio riktiga rapporter ur `bank/uppgifter/`.
"""
from __future__ import annotations

import glob
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import oga_kontrakt as K                                        # noqa: E402
from vc_assist_svc import verktyg as V                          # noqa: E402
from vc_assist_svc.llm.kapning import Ratext, Verktygssvar      # noqa: E402


# ---------------------------------------------------------------------------
# 1. Riktiga verktygssvar
# ---------------------------------------------------------------------------

def _katalogurier(grans=None):
    with open(os.path.join(_ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        poster = json.load(f)["poster"]
    urier = [p["uri"] for p in poster]
    return urier[:grans] if grans else urier


def _uppgiftsid():
    ut = []
    for f in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter", "*.json"))):
        ut.append(os.path.basename(f)[:-5])
    return ut


def _typnamn(antal=25):
    """Riktiga typnamn ur API-indexet, de storsta ytorna forst."""
    from vc_assist_svc import api_index
    index = api_index.ApiIndex()
    typer = {}
    for s in index.symboler:
        typer[s.typ_namn] = typer.get(s.typ_namn, 0) + 1
    return [t for t, _n in sorted(typer.items(), key=lambda kv: -kv[1])[:antal]
            if t]


# (verktyg, [argumentordbok, ...]). Argumenten ar repots egna varden.
def anropslista():
    ut = [
        ("catalog_categories", [{}]),
        ("library_overview", [{}]),
        ("connectivity_status", [{"question": q}
                                 for q in ("servrar", "tillstand", "variabler",
                                           "allt")]),
        ("search_catalog", [{"query": q} for q in
                            ("robot", "transport", "gripdon", "givare",
                             "station", "sakerhet", "lastbarare", "don")]),
        ("catalog_item", [{"uri": u} for u in _katalogurier()]),
        ("bench_task", [{"task_id": t} for t in _uppgiftsid()]),
        ("type_surface", [{"type_name": t} for t in _typnamn()]),
        ("search_api", [{"query": q, "limit": 100} for q in
                        ("distance", "collision", "signal", "component",
                         "matrix", "behaviour", "interface", "robot")]),
        ("lookup_helper", [{"module": m} for m in
                           V.REGISTER["lookup_helper"].parameters
                           ["properties"]["module"]["enum"]]),
        ("lookup_api", [{"name": n} for n in
                        ("vcComponent", "vcApplication.load", "findBehaviour",
                         "vcMatrix", "vcSimInterface", "getProperty")]),
        ("search_installed_library", [{"query": q} for q in
                                      ("conveyor", "IRB", "sensor")]),
        ("component_datasheet", [{"name": n} for n in ("conveyor", "IRB")]),
        ("eyes_report", [{"report": r} for r in ogonrapporter()]),
    ]
    return ut


def korpus(grans=None):
    """[(Verktygssvar, returns-schema)] over riktiga svar ur repot."""
    ut = []
    for namn, argumentlista in anropslista():
        handlare = V.DATA_HANDLERS.get(namn)
        if handlare is None:
            continue
        for argument in argumentlista:
            try:
                resultat = handlare(argument)
            except Exception:     # noqa: BLE001 - ett verktyg som inte svarar
                continue          # har hor inte till korpusen, och det sags
            ut.append((Verktygssvar(verktyg=namn, argument=dict(argument),
                                    resultat=resultat),
                       V.REGISTER[namn].returns))
            if grans and len(ut) >= grans:
                return ut
    return ut


# ---------------------------------------------------------------------------
# 2. Riktiga ogonrapporter
# ---------------------------------------------------------------------------

def _plocka(x, ut):
    if isinstance(x, str) and x.startswith("EYES v"):
        ut.append(x)
    elif isinstance(x, dict):
        for v in x.values():
            _plocka(v, ut)
    elif isinstance(x, list):
        for v in x:
            _plocka(v, ut)


def ogonrapporter():
    """Bankens egna ogonrapporter, ordagrant."""
    ut = []
    for f in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            _plocka(json.load(fh), ut)
    return ut


# ---------------------------------------------------------------------------
# 3. Ogonrapporter riggade for ordliste-fallen
# ---------------------------------------------------------------------------

def _rapport(sektioner, dom, orsak, template="fas22", n_prov=6000):
    r = K.Rapport(template, "2026-09-05T00:00:00", 300.0, n_prov, 20.0)
    for namn, rader in sektioner:
        r.sektion(namn)
        for rad in rader:
            r.rad(rad)
    r.satt_dom(dom, orsak)
    return r.text()


def _limits():
    return ("LIMITS",
            ["NOT_SIMULATED %s" % n for n in K.EJ_SIMULERAT]
            + ["RESOLUTION sample=50.000ms read=unknown join=1.000ms RUN "
               "phase=unknown"])


def rapport_med_ok_i_namn(antal_mindist=8):
    """Den trasiga fixturen for ORDLISTAN.

    Tva rader bar bokstaverna OK utan att vara godkanda:

      MINDIST OK_ROBOT+STANGSEL ...   ett PARNAMN. Raden har ingen dom alls.
      STEP 3 ST010_OK_SENSOR RISE MISSING ...  ett SIGNALNAMN, och radens dom
                                               ar MISSING - ett fynd.

    En delstrangsmatchning pa "OK" trimmar bada. Den ena ar en safety-rad, den
    andra ar ett fynd.
    """
    mindist = ["MINDIST OK_ROBOT+STANGSEL %.3fmm t=%.3fs"
               % (400.0 + i, 1.0 + i) for i in range(antal_mindist)]
    mindist.append("MINDIST kritiska_paret 12.000mm t=9.000s")
    return _rapport(
        [("SEQUENCE",
          ["STEP 3 ST010_OK_SENSOR RISE MISSING win=0.000s..1.000s",
           "STEP 4 ST010_KLAR RISE OK t=1.500s win=1.000s..2.000s"]),
         ("SAFETY", mindist + ["COLLISION none"]),
         ("HONESTY", ["TELEPORT_TRANSFER OK", "BLOWUP OK", "UNDERGROUND OK",
                      "NEVER_GRIPPED OK"]),
         _limits()],
        "FAIL", "steg 3 uteblev: ST010_OK_SENSOR steg aldrig")


def lang_rapport(antal_edge=200, antal_mindist=40):
    """En rapport av den sort ingen lang korning annu gjort: EDGE och MINDIST
    vaxer med forloppet (25_kontextbudget.md avsnitt 7, antagande 6)."""
    edge = ["EDGE ST%03d_STA_DONE %s t=%.3fs"
            % (100 + (i % 9), "RISE" if i % 2 == 0 else "FALL", 0.5 * i)
            for i in range(antal_edge)]
    mindist = ["MINDIST par%02d+robot %.3fmm t=%.3fs"
               % (i, 300.0 + i * 7, 2.0 * i) for i in range(antal_mindist)]
    return _rapport(
        [("TIMING", edge + ["DWELL ST100 26.100s req=26.000s OK", "RACE none"]),
         ("SAFETY", mindist + ["COLLISION none"]),
         ("HONESTY", ["TELEPORT_TRANSFER OK", "BLOWUP OK", "UNDERGROUND OK",
                      "NEVER_GRIPPED OK"]),
         _limits()],
        "PASS", "allt inom marginal")


def naiv_ok(rad):
    """Den NAIVA domaren, som fixturerna finns for att falla.

    Den star har och inte i ett prov, sa att bade acceptanskorningen och
    enhetsproven mater SAMMA naiva domare. Den ar skriven som den brukar
    skrivas: "star det OK i raden ar raden OK".
    """
    return "OK" in rad or rad.strip().endswith("none")


# ---------------------------------------------------------------------------
# 4. De tre farliga kapningarna
# ---------------------------------------------------------------------------

def _forsta_listan(resultat, returns_schema):
    from vc_assist_svc.llm.kapning import listfalt
    for namn in listfalt(returns_schema):
        if isinstance(resultat.get(namn), list) and len(resultat[namn]) > 3:
            return namn
    return None


def ser_helt_ut(svar, returns_schema):
    """A: halva listan borta, `antal` OFORANDRAT, ingen `avkortad`.

    Parsar felfritt och laser som ett helt svar. Det ar den farliga formen:
    modellen drar en slutsats om det som inte kom med.
    """
    namn = _forsta_listan(svar.resultat, returns_schema)
    if namn is None:
        return None
    d = json.loads(json.dumps(svar.resultat))
    d[namn] = d[namn][:len(d[namn]) // 2]
    return Verktygssvar(verktyg=svar.verktyg, argument=dict(svar.argument),
                        resultat=d, id=svar.id)


def parsar_inte(svar, andel=0.5):
    """B: klippt PA TECKEN mitt i en struktur - lasbart for ett oga,
    oparsbart for allt annat. Det ar felet slaupp.py gjorde en gang."""
    text = json.dumps(svar.resultat, ensure_ascii=False, sort_keys=True)
    bit = text[:int(len(text) * andel)]
    return Verktygssvar(verktyg=svar.verktyg, argument=dict(svar.argument),
                        resultat=Ratext(bit), id=svar.id)


def helt_men_kort(svar, returns_schema):
    """C: halva listan borta, `antal` RATTAT, och anda ingen `avkortad`.

    Den tystaste formen: svaret ar internt konsistent och sager inte att det
    ar kort. Bara en jamforelse med RAVARAN kan fanga den.
    """
    namn = _forsta_listan(svar.resultat, returns_schema)
    if namn is None:
        return None
    d = json.loads(json.dumps(svar.resultat))
    d[namn] = d[namn][:len(d[namn]) // 2]
    if "antal" in d:
        d["antal"] = len(d[namn])
    return Verktygssvar(verktyg=svar.verktyg, argument=dict(svar.argument),
                        resultat=d, id=svar.id)


def storsta_svaret(par=None):
    """Det storsta riktiga verktygssvaret i korpusen. Anvands som
    'ett svar som ar dubbelt sa stort som budgeten'."""
    par = par if par is not None else korpus()
    return max(par, key=lambda p: p[0].byte())
