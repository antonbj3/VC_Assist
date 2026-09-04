# -*- coding: utf-8 -*-
"""Domanen eyes: lasa ogats rapport och en bankuppgifts facit (45_verktyg.md).

Tre verktyg, alla DATA. De ror INTE scenen: de laser en rapport ogat redan
skrivit och ett facit banken redan bar, sa de kor i tjansten och gar aldrig
via bryggan.

eyes_start och eyes_stop hor INTE hit. De ar bryggoperationer med
effect=write och maste ga genom godkannandekon (I12); 45_verktyg.md lagger
dem i kodgenereringsgrenen och dar hor de hemma.

I1: OGAT FALLER DOMEN. Inget har raknar om ett matt. eyes_report parsar
ogats egen utdata genom ext/vc_addon/vc_assist/oga_kontrakt.py - samma
modulinstans som ogat sjalv skriver med och som banken jamfor mot, sa
skrivare och lasare kan inte drifta isar. bench_compare anropar bankens egen
Uppgift.jamfor(); den regeln star pa ett stalle och kopieras inte hit.

I3 FAIL-CLOSED. En rapport som inte gar att lasa - fel version, avhuggen,
okand rad i en kand sektion - ger ok=false och kontraktets EGEN grinddom
("NOT GOLD (...)"). Verktyget kastar inte och det tolkar inte; tystnad och
trasighet ar aldrig ett godkannande. INCONCLUSIVE ar inte heller godkant,
och ett PASS med en HONESTY-overtradelse domes aldrig om till godkant.

Kallor: docs/spec/40_ogat.md, 41_ogat_kontrakt.md, 80_bank.md.
Banken laddas har vid import med strikt=True (matt: 47 uppgifter, 0,02 s).
En bank dar en post inte gar att validera ar inte en halvbra bank.
"""
from __future__ import annotations

import os
import sys

from .bas import SINCE, TIMEOUT_MS, params, returns
from .register import registrera
from .schema import Verktyg

DOMAN = "eyes"

# bank/ ar ingen paketkatalog utan nas genom sokvagen, precis som
# formagegrind.py gor med ext/vc_addon/vc_assist. Samma fil, en enda sanning
# om bankens form.
_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", "..", ".."))
_BANK = os.path.join(ROT, "bank")
if _BANK not in sys.path:
    sys.path.insert(0, _BANK)

import lasare  # noqa: E402

# Ogats kontrakt. Hamtat GENOM banken (lasare.K) och inte importerat en gang
# till: da ar det garanterat samma modulinstans som bankens facitvalidering
# och ogats egen skrivare anvander.
K = lasare.K

BANK = lasare.ladda()
UPPGIFTS_ID = tuple(sorted(u.id for u in BANK))


# ---- registrering --------------------------------------------------------

# bas.laggare() ger mode="codegen"; den har domanen ar data, sa laggaren star
# har. effect ar INTE en parameter: alla tre laser, och ett data-verktyg som
# skriver avvisas anda av schemat (I12).
#
# KRAVER for ett data-verktyg. Schemat kraver minst en yta ur formaga.YTOR
# och formagegrinden slar av verktyget nar ytan saknas. De har verktygen ror
# ingen VC-yta alls - de laser text. Vi deklarerar darfor de ytor svaret ar
# TILL FOR, en per verktyg, och foljden ar uttalad: utan formagerapport fran
# bryggan ar ocksa ogonverktygen avslagna (I3 fail-closed), med ytan
# namngiven i skalet.
#
# KRAVER_RAPPORT: ytorna ogat provtar GENOM (oga_provtagning.py rad 75 och
# 99: app.findComponent for att hitta det sparade objektet, och
# node.WorldPositionMatrix for dess pose per prov). En rapport ar ett matt
# genom precis de tva ytorna; saknas de finns ingen rapport att lasa.
#
# KRAVER_UPPGIFT: en bankuppgifts scen ar en lista URI:er som ska laddas
# innan uppgiften kan koras, alltsa app.load - samma yta som load_component.
KRAVER_RAPPORT = ("app.findComponent", "node.WorldPositionMatrix")
KRAVER_UPPGIFT = ("app.load",)


def _lagg(namn, beskrivning, parameters, returns_, kraver, handlare):
    return registrera(
        Verktyg(namn=namn, beskrivning=beskrivning, mode="data", effect="read",
                parameters=parameters, returns=returns_, since=SINCE,
                kraver=kraver, doman=DOMAN,
                # timeout_ms ar inert pa data-vagen: utforaren skickar den
                # bara till bryggan for kodgenererande verktyg. Talet halls
                # anda pa bas.TIMEOUT_MS sa att ingen andra, tystare grans
                # uppstar i tjansten.
                timeout_ms=TIMEOUT_MS),
        handlare)


# ---- gemensamma schemabitar ---------------------------------------------

_FACITRAD = {
    "type": "object",
    "description": "En facitrad: en sektion och en radmall dar * star for vilket tal som helst.",
    "properties": {
        "section": {"type": "string",
                    "description": "Ogats sektion: MOTION, TIMING, THROUGHPUT, SAFETY eller HONESTY."},
        "template": {"type": "string", "description": "Radmallen, i ogats egen grammatik."},
    },
    "required": ["section", "template"],
}

_RET_UPPGIFTS_ID = {
    "type": "array",
    "description": ("Bankens VERKLIGA uppgifts-id. Fylls bara nar task_id inte "
                    "fanns, sa att ett id aldrig behover gissas fram."),
    "items": {"type": "string", "description": "Ett uppgifts-id som finns."},
}


# ---- eyes_report ---------------------------------------------------------

def _eyes_report(argument):
    text = argument["report"]
    tom = {
        "ok": False, "godkand": False, "version": None, "template": None,
        "started": None, "dur_s": None, "samples": None, "rate_hz": None,
        "sektioner": [], "dom": None, "orsak": None, "overtradelser": [],
        "okanda_sektioner": [], "grinddom": None, "fel": None,
    }
    try:
        rapport = K.las(text)
    except K.Kontraktsfel as fel:
        # Kontraktets EGEN grinddom, inte en egen formulering. En rapport som
        # inte gar att lasa ar inte ett godkannande (I3).
        return dict(tom, grinddom=fel.grinddom, fel=str(fel))
    return {
        "ok": True,
        "godkand": rapport.godkand(),
        "version": rapport.version,
        "template": rapport.template,
        "started": rapport.started,
        "dur_s": rapport.dur_s,
        "samples": rapport.samples,
        "rate_hz": rapport.rate_hz,
        "sektioner": [{"namn": namn, "rader": list(rader), "antal": len(rader)}
                      for namn, rader in rapport.sektioner],
        "dom": rapport.dom[0],
        "orsak": rapport.dom[1],
        "overtradelser": rapport.overtradelser(),
        "okanda_sektioner": list(rapport.okanda_sektioner),
        "grinddom": None,
        "fel": None,
    }


_lagg(
    "eyes_report",
    "Laser en ogonrapport genom ogats eget domskontrakt och ger dom, orsak, "
    "sektioner och HONESTY-overtradelser. godkand ar true bara vid ett rent "
    "PASS utan overtradelser; INCONCLUSIVE och avhuggen rapport ar inte "
    "godkant. En rapport som inte foljer grammatiken ger ok=false och "
    "kontraktets egen grinddom - aldrig en tolkning.",
    params({"report": {"type": "string",
                       "description": "Ogats utdata, hela texten fran EYES v1 till EYES VERDICT."}},
           ["report"]),
    returns({
        "ok": {"type": "boolean", "description": "Om rapporten gick att lasa alls."},
        "godkand": {"type": "boolean",
                    "description": "Rent PASS utan HONESTY-overtradelser. Fail-closed."},
        "version": {"type": ["integer", "null"], "description": "Ogats grammatikversion."},
        "template": {"type": ["string", "null"], "description": "Mallen korningen gallde."},
        "started": {"type": ["string", "null"], "description": "Starttid ur RUN-raden."},
        "dur_s": {"type": ["number", "null"], "description": "Korningens langd i sekunder."},
        "samples": {"type": ["integer", "null"], "description": "Antal prov."},
        "rate_hz": {"type": ["number", "null"], "description": "Provtagningsfrekvens i hertz."},
        "sektioner": {
            "type": "array", "description": "Rapportens sektioner i ordning.",
            "items": {"type": "object", "description": "En sektion med sina rader.",
                      "properties": {
                          "namn": {"type": "string", "description": "Sektionens namn."},
                          "rader": {"type": "array", "description": "Raderna ordagrant.",
                                    "items": {"type": "string", "description": "En rad."}},
                          "antal": {"type": "integer", "description": "Antal rader."}},
                      "required": ["namn", "rader", "antal"]}},
        "dom": {"type": ["string", "null"], "description": "PASS, FAIL eller INCONCLUSIVE."},
        "orsak": {"type": ["string", "null"], "description": "Ogats egen orsakstext."},
        "overtradelser": {"type": "array",
                          "description": "HONESTY-rader som star pa VIOLATION.",
                          "items": {"type": "string", "description": "Overtradelsens nyckelord."}},
        "okanda_sektioner": {"type": "array",
                             "description": "Sektioner ur en nyare grammatik som hoppades over.",
                             "items": {"type": "string", "description": "Sektionsnamn."}},
        "grinddom": {"type": ["string", "null"],
                     "description": "Kontraktets grinddom nar rapporten inte gick att lasa."},
        "fel": {"type": ["string", "null"], "description": "Vad som var fel i rapporten."},
    }, ["ok", "godkand", "sektioner", "overtradelser", "okanda_sektioner",
        "grinddom", "fel"]),
    KRAVER_RAPPORT,
    _eyes_report,
)


# ---- bench_task ----------------------------------------------------------

def _uppgift(task_id):
    try:
        return BANK[task_id]
    except KeyError:
        return None


def _bench_task(argument):
    task_id = argument["task_id"].strip()
    u = _uppgift(task_id)
    if u is None:
        return {"found": False, "task_id": task_id, "uppgift": None,
                "facit": None, "scen": None, "kanda_id": list(UPPGIFTS_ID)}
    d = u.data
    e = d["expect"]
    return {
        "found": True,
        "task_id": u.id,
        "uppgift": {
            "titel": d["title"],
            "mal": d["goal"],
            "prompt": d["prompt"],
            "grupp": u.grupp,
            "bransch": u.bransch,
            "stege": d["stege"],
            "svarighet": u.svarighet,
            "svarighetsstampel": d["difficulty_stamp"],
            "klasser": u.klasser,
            "karnutgangar": list(d["core_outputs"]),
            "ar_variant": u.ar_variant,
            "variant_av": d["variant_av"],
        },
        "facit": {
            "grind": e["gate"],
            "grindkod": e["gate_code"],
            "dom": e["verdict"],
            "orsak_innehaller": e["reason_contains"],
            "kravda_rader": list(e["lines"]),
            "forbjudna_rader": list(e["forbidden_lines"]),
            "must_pass": list(e["must_pass"]),
            "max_kollisioner": e["max_collisions"],
            "min_frigang_mm": e["min_clearance_mm"],
            "takt_per_h": e["throughput_per_h"],
            "korningar": e["runs"],
            "uppvarmning_s": e["warmup_s"],
        },
        "scen": {
            "komponenter": [{"roll": k["role"], "uri": k["uri"], "antal": k["count"]}
                            for k in d["scene"]["components"]],
            "kopplingar": [{"fran": c["from_role"], "till": c["to_role"]}
                           for c in d["scene"]["connections"]],
            "layout_uri": d["scene"]["layout_uri"],
        },
        "kanda_id": [],
    }


_lagg(
    "bench_task",
    "Hamtar EN bankuppgift med sitt facit: uppgiftstext, scenens URI:er ur "
    "katalogindexet, vilken grind som ska falla den, vilken ogondom som "
    "vantas och vilka rader ogat maste respektive aldrig far skriva. "
    "found=false ar ett giltigt svar och listar da bankens verkliga id.",
    params({"task_id": {"type": "string",
                        "description": "Uppgiftens id, till exempel A-01 eller T-92."}},
           ["task_id"]),
    returns({
        "found": {"type": "boolean", "description": "Om uppgiften fanns i banken."},
        "task_id": {"type": "string", "description": "Id:t som slogs upp."},
        "uppgift": {
            "type": ["object", "null"], "description": "Uppgiftens text och form.",
            "properties": {
                "titel": {"type": "string", "description": "Uppgiftens titel."},
                "mal": {"type": "string", "description": "Vad som ska astadkommas."},
                "prompt": {"type": "string", "description": "Uppgiftstexten som ges till modellen."},
                "grupp": {"type": "string", "description": "Bankgrupp: T, P, L, S, A, H eller C."},
                "bransch": {"type": "string", "description": "Branschen uppgiften speglar."},
                "stege": {"type": "string", "description": "Steget i undervisningsprogressionen."},
                "svarighet": {"type": "integer", "description": "Svarighetsgrad 1 till 5."},
                "svarighetsstampel": {"type": "string",
                                      "description": "DEKLARERAD eller MATT - hur svarigheten satts."},
                "klasser": {"type": "array", "description": "Felklasser uppgiften siktar pa.",
                            "items": {"type": "string", "description": "En F-kod."}},
                "karnutgangar": {"type": "array",
                                 "description": "Utgangssignaler vars spar ar det som mats.",
                                 "items": {"type": "string", "description": "Ett signalnamn."}},
                "ar_variant": {"type": "boolean",
                               "description": "True for en medvetet trasig variant."},
                "variant_av": {"type": ["string", "null"],
                               "description": "Uppgiften varianten ar gjord ur."},
            },
            "required": ["titel", "mal", "prompt", "grupp", "svarighet", "klasser"],
        },
        "facit": {
            "type": ["object", "null"],
            "description": "Vad som kravs for att uppgiften ska raknas som lost.",
            "properties": {
                "grind": {"type": "string",
                          "description": "Grinden som ska falla uppgiften: G1-G4, OGAT, G6 eller G7."},
                "grindkod": {"type": ["string", "null"],
                             "description": "Vantad felkod nar grinden ligger fore ogat."},
                "dom": {"type": ["string", "null"],
                        "description": "Vantad ogondom: PASS, FAIL eller INCONCLUSIVE."},
                "orsak_innehaller": {"type": ["string", "null"],
                                     "description": "Text som maste finnas i ogats orsaksrad."},
                "kravda_rader": {"type": "array", "description": "Rader ogat MASTE skriva.",
                                 "items": _FACITRAD},
                "forbjudna_rader": {"type": "array", "description": "Rader ogat ALDRIG far skriva.",
                                    "items": _FACITRAD},
                "must_pass": {"type": "array", "description": "Sektioner som maste halla.",
                              "items": {"type": "string", "description": "En sektion."}},
                "max_kollisioner": {"type": "integer",
                                    "description": "Hogsta tillatna antal kollisioner."},
                "min_frigang_mm": {"type": ["number", "null"],
                                   "description": "Minsta frigang i millimeter."},
                "takt_per_h": {"type": ["number", "null"],
                               "description": "Kravd takt i enheter per timme."},
                "korningar": {"type": "integer",
                              "description": "Antal oberoende korningar bakom talet (I5)."},
                "uppvarmning_s": {"type": "number",
                                  "description": "Uppvarmning i sekunder som inte raknas."},
            },
            "required": ["grind", "kravda_rader", "forbjudna_rader"],
        },
        "scen": {
            "type": ["object", "null"],
            "description": "Scenen uppgiften ska byggas ur. URI:erna star i katalogindexet.",
            "properties": {
                "komponenter": {
                    "type": "array", "description": "Komponenterna med roll och URI.",
                    "items": {"type": "object", "description": "En komponent.",
                              "properties": {
                                  "roll": {"type": "string", "description": "Rollen i scenen."},
                                  "uri": {"type": "string", "description": "URI ur katalogindexet."},
                                  "antal": {"type": "integer", "description": "Antal exemplar."}},
                              "required": ["roll", "uri", "antal"]}},
                "kopplingar": {
                    "type": "array",
                    "description": ("Relationerna mellan rollerna. Modellen "
                                    "anger relationer, aldrig koordinater (I8)."),
                    "items": {"type": "object", "description": "En koppling.",
                              "properties": {
                                  "fran": {"type": "string", "description": "Rollen kopplingen gar fran."},
                                  "till": {"type": "string", "description": "Rollen kopplingen gar till."}},
                              "required": ["fran", "till"]}},
                "layout_uri": {"type": ["string", "null"],
                               "description": "Fardig layout att utga fran, null nar ingen finns."},
            },
            "required": ["komponenter", "kopplingar"],
        },
        "kanda_id": _RET_UPPGIFTS_ID,
    }, ["found", "task_id", "uppgift", "facit", "scen", "kanda_id"]),
    KRAVER_UPPGIFT,
    _bench_task,
)


# ---- bench_compare -------------------------------------------------------

def _bench_compare(argument):
    task_id = argument["task_id"].strip()
    tom = {
        "found": False, "task_id": task_id, "jamforbar": False, "skal": None,
        "uppfyllt": False, "dom_stammer": False, "observerad_dom": None,
        "forvantad_dom": None, "orsak_stammer": False, "saknade_rader": [],
        "forbjudna_traffar": [], "fel": [], "kanda_id": [],
    }
    u = _uppgift(task_id)
    if u is None:
        return dict(tom, skal="uppgiften finns inte i banken",
                    kanda_id=list(UPPGIFTS_ID))
    e = u.data["expect"]
    if u.grind != "OGAT":
        # Bankens egen regel, inte en ny: Uppgift.jamfor kastar Bankfel har.
        # Vi svarar i stallet med skalet, for ett uteblivet svar ar inte ett
        # godkannande men inte heller ett undantag modellen kan ratta.
        return dict(tom, found=True, forvantad_dom=e["verdict"],
                    skal=("uppgiften falls av %s, fore ogat; den har ingen "
                          "ogondom att jamfora mot" % u.grind))
    res = u.jamfor(argument["report"])
    return {
        "found": True,
        "task_id": u.id,
        "jamforbar": True,
        "skal": None,
        "uppfyllt": res.uppfyllt,
        "dom_stammer": res.dom_stammer,
        "observerad_dom": res.observerad_dom,
        "forvantad_dom": e["verdict"],
        "orsak_stammer": res.orsak_stammer,
        "saknade_rader": list(res.saknade_rader),
        "forbjudna_traffar": [{"section": t["krav"]["section"],
                               "template": t["krav"]["template"],
                               "rader": list(t["rader"])}
                              for t in res.forbjudna_traffar],
        "fel": [{"grinddom": g, "text": t} for g, t in res.fel],
        "kanda_id": [],
    }


_lagg(
    "bench_compare",
    "Haller en ogonrapport mot en bankuppgifts facit och sager exakt vad som "
    "brister: fel dom, saknade rader, rader facit forbjod, eller en rapport "
    "som inte gar att lasa. Domen ar ogats egen - jamforelsen raknar aldrig "
    "om ett matt (I1). En uppgift som falls av en grind FORE ogat ger "
    "jamforbar=false med skalet.",
    params({
        "task_id": {"type": "string", "description": "Uppgiftens id, till exempel A-01."},
        "report": {"type": "string", "description": "Ogats utdata for korningen."},
    }, ["task_id", "report"]),
    returns({
        "found": {"type": "boolean", "description": "Om uppgiften fanns i banken."},
        "task_id": {"type": "string", "description": "Id:t som slogs upp."},
        "jamforbar": {"type": "boolean",
                      "description": "Om uppgiften alls har en ogondom att jamfora mot."},
        "skal": {"type": ["string", "null"],
                 "description": "Varfor jamforelsen inte gick att gora, null nar den gick."},
        "uppfyllt": {"type": "boolean",
                     "description": "Allt stammer: dom, orsak, kravda rader och inga forbjudna."},
        "dom_stammer": {"type": "boolean", "description": "Om ogats dom var den vantade."},
        "observerad_dom": {"type": ["string", "null"], "description": "Domen ogat faktiskt fallde."},
        "forvantad_dom": {"type": ["string", "null"], "description": "Domen facit vantade."},
        "orsak_stammer": {"type": "boolean",
                          "description": "Om ogats orsaksrad bar den text facit kravde."},
        "saknade_rader": {"type": "array",
                          "description": "Facitrader som ogat aldrig skrev.",
                          "items": _FACITRAD},
        "forbjudna_traffar": {
            "type": "array", "description": "Rader facit forbjod men ogat skrev.",
            "items": {"type": "object", "description": "En forbjuden rad och traffarna.",
                      "properties": {
                          "section": {"type": "string", "description": "Sektionen."},
                          "template": {"type": "string", "description": "Radmallen som forbjods."},
                          "rader": {"type": "array", "description": "Raderna ogat skrev.",
                                    "items": {"type": "string", "description": "En rad."}}},
                      "required": ["section", "template", "rader"]}},
        "fel": {"type": "array",
                "description": "Lasfel ur kontraktet nar rapporten inte gick att lasa.",
                "items": {"type": "object", "description": "Ett lasfel med sin grinddom.",
                          "properties": {
                              "grinddom": {"type": "string", "description": "Kontraktets grinddom."},
                              "text": {"type": "string", "description": "Vad som var fel."}},
                          "required": ["grinddom", "text"]}},
        "kanda_id": _RET_UPPGIFTS_ID,
    }, ["found", "task_id", "jamforbar", "skal", "uppfyllt", "dom_stammer",
        "observerad_dom", "forvantad_dom", "orsak_stammer", "saknade_rader",
        "forbjudna_traffar", "fel", "kanda_id"]),
    KRAVER_RAPPORT,
    _bench_compare,
)
