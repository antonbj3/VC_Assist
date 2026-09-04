# -*- coding: utf-8 -*-
"""Verktygsschemat och valideringen av argument och svar.

Form ARVD ur Isaac Assist (20_arv.md): OpenAI:s function-calling-schema som
en ren datalista. Utover name/description/parameters bar varje verktyg fyra
obligatoriska falt ur 45_verktyg.md:

    effect   read | write   -> AVGOR exekveringslage. Se utforare.py
    mode     data | codegen -> vilket register
    returns  JSON-schema for resultatet
    since    VC-version

plus ett femte som foljer av 36_versioner.md:

    kraver   vilka ytor i formaga.YTOR verktyget ror

Valideringen har ar det forsta av de tva lagren i 45_verktyg.md: anropsnamn,
argumentnamn, typer och enum-varden provas mot schemat INNAN nagon kod
genereras eller skickas. Det ar den starkaste anti-hallucinationen som finns
byggd i kallprojektet, och den enda som inte kraver att VC kor.
"""
from __future__ import annotations

import re

from .fel import Argumentfel, Schemafel, Svarsfel
from .formagegrind import KANDA_YTOR

LAGEN = ("data", "codegen")
VERKAN = ("read", "write")

# JSON-schematyper vi stodjer. Listan ar avsiktligt kort: allt som inte gar
# att prova mekaniskt hor inte hemma i ett verktygsschema.
TYPER = ("string", "integer", "number", "boolean", "array", "object", "null")

_NAMN = re.compile(r"^[a-z][a-z0-9_]*$")
_VERSION = re.compile(r"^\d+\.\d+$")

# Nycklar som ar VARA, inte OpenAI:s. De strippas ur det schema som skickas
# till modellen sa att de aldrig kan tolkas som en instruktion.
_EGNA_NYCKLAR = ("x-minst-en-av", "x-tillsammans")


class Verktyg(object):
    """En verktygsdefinition. Oforanderlig efter konstruktion."""

    __slots__ = ("namn", "beskrivning", "mode", "effect", "parameters",
                 "returns", "since", "kraver", "doman", "timeout_ms")

    def __init__(self, namn, beskrivning, mode, effect, parameters, returns,
                 since, kraver, doman, timeout_ms):
        object.__setattr__(self, "namn", namn)
        object.__setattr__(self, "beskrivning", beskrivning)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "effect", effect)
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "returns", returns)
        object.__setattr__(self, "since", since)
        object.__setattr__(self, "kraver", tuple(kraver))
        object.__setattr__(self, "doman", doman)
        object.__setattr__(self, "timeout_ms", int(timeout_ms))
        self._granska()

    def __setattr__(self, namn, varde):
        raise AttributeError(
            "verktygsdefinitioner ar oforanderliga; effect far inte kunna "
            "andras efter registrering (I12)")

    def __repr__(self):
        return "Verktyg(%s, %s/%s)" % (self.namn, self.mode, self.effect)

    # ---- kontroll av definitionen sjalv ---------------------------------

    def _granska(self):
        f = []
        if not _NAMN.match(self.namn or ""):
            f.append("namnet %r maste vara gemener, siffror och understreck"
                     % (self.namn,))
        if not (self.beskrivning or "").strip():
            f.append("beskrivningen saknas; modellen valjer verktyg pa den")
        if self.mode not in LAGEN:
            f.append("mode %r ar inte data eller codegen" % (self.mode,))
        if self.effect not in VERKAN:
            f.append("effect %r ar inte read eller write" % (self.effect,))
        if self.mode == "data" and self.effect == "write":
            # I12 sager att allt som skriver gar genom en godkannandeko.
            # For kodgenererande verktyg AR den kon bryggans exec_queue.
            # Ett data-verktyg gar aldrig via bryggan och skulle darfor
            # kringga kon helt. Tjanstens egen ko byggs i fas 6 (60_plc.md);
            # tills den finns far ett sadant verktyg inte ens definieras.
            f.append("data+write kringgar godkannandekon (I12); tjanstens "
                     "egen ko byggs i fas 6 och verktyget far vanta pa den")
        if not _VERSION.match(self.since or ""):
            f.append("since %r ar ingen VC-version pa formen 4.10" % (self.since,))
        if not self.kraver:
            f.append("kraver ar tom; ett verktyg som inte ror nagon yta "
                     "kan formagegrinden inte doma om")
        for yta in self.kraver:
            if yta not in KANDA_YTOR:
                f.append("kravd yta %r finns inte i formaga.YTOR; grinden "
                         "kan inte prova den" % (yta,))
        f += _granska_parameterschema(self.parameters)
        f += _granska_returschema(self.returns)
        if f:
            raise Schemafel("%s: %s" % (self.namn, "; ".join(f)))

    # ---- utat -----------------------------------------------------------

    def som_openai(self):
        """OpenAI function-calling-form. Bara det modellen ska se."""
        return {
            "type": "function",
            "function": {
                "name": self.namn,
                "description": self.beskrivning,
                "parameters": _utan_egna_nycklar(self.parameters),
            },
        }

    def beskriv_anrop(self, argument):
        """En rad for kolistan. Operatoren godkanner pa den har texten."""
        delar = ["%s=%r" % (k, argument[k]) for k in sorted(argument)]
        return "%s(%s)" % (self.namn, ", ".join(delar))


def _utan_egna_nycklar(schema):
    if not isinstance(schema, dict):
        return schema
    ut = {}
    for k, v in schema.items():
        if k in _EGNA_NYCKLAR:
            continue
        ut[k] = _utan_egna_nycklar(v) if isinstance(v, dict) else v
    return ut


def _granska_typ(typ, stig, f):
    typer = typ if isinstance(typ, list) else [typ]
    if not typer:
        f.append("%s: type ar tom" % stig)
    for t in typer:
        if t not in TYPER:
            f.append("%s: okand type %r" % (stig, t))


def _granska_egenskap(namn, s, stig, f):
    if not isinstance(s, dict):
        f.append("%s: egenskapen %s ar inget schema" % (stig, namn))
        return
    if "type" not in s:
        f.append("%s.%s: saknar type" % (stig, namn))
    else:
        _granska_typ(s["type"], "%s.%s" % (stig, namn), f)
    if not (s.get("description") or "").strip():
        f.append("%s.%s: saknar description; modellen fyller i den sjalv "
                 "annars" % (stig, namn))
    if "items" in s:
        _granska_egenskap("items", s["items"], "%s.%s" % (stig, namn), f)
    if "properties" in s:
        for u, us in s["properties"].items():
            _granska_egenskap(u, us, "%s.%s" % (stig, namn), f)


def _granska_parameterschema(p):
    f = []
    if not isinstance(p, dict):
        return ["parameters ar ingen ordbok"]
    if p.get("type") != "object":
        f.append("parameters.type maste vara object")
    if p.get("additionalProperties") is not False:
        # Utan detta blir ett uppfunnet argumentnamn tyst tillatet. I9.
        f.append("parameters.additionalProperties maste vara false")
    egenskaper = p.get("properties")
    if not isinstance(egenskaper, dict):
        return f + ["parameters.properties saknas"]
    for namn, s in egenskaper.items():
        if not _NAMN.match(namn):
            f.append("argumentnamnet %r maste vara gemener och understreck"
                     % (namn,))
        _granska_egenskap(namn, s, "parameters", f)
    for namn in p.get("required", []):
        if namn not in egenskaper:
            f.append("required namnger %r som inte finns bland properties"
                     % (namn,))
    for nyckel in ("x-minst-en-av", "x-tillsammans"):
        for grupp in p.get(nyckel, []):
            for namn in grupp:
                if namn not in egenskaper:
                    f.append("%s namnger %r som inte finns" % (nyckel, namn))
    return f


def _granska_returschema(r):
    f = []
    if not isinstance(r, dict):
        return ["returns ar ingen ordbok"]
    if r.get("type") != "object":
        f.append("returns.type maste vara object; svaret ar alltid ett objekt "
                 "pa sista raden av stdout (31_brygga_protokoll.md)")
    egenskaper = r.get("properties")
    if not isinstance(egenskaper, dict) or not egenskaper:
        return f + ["returns.properties saknas; da gar svaret inte att prova"]
    for namn, s in egenskaper.items():
        _granska_egenskap(namn, s, "returns", f)
    if not r.get("required"):
        f.append("returns.required ar tom; da kan ett tomt svar passera (I3)")
    for namn in r.get("required", []):
        if namn not in egenskaper:
            f.append("returns.required namnger %r som inte finns" % (namn,))
    return f


# ---- validering av varden ------------------------------------------------

def _ar_av_typ(varde, typ):
    if typ == "string":
        return isinstance(varde, str)
    if typ == "boolean":
        return isinstance(varde, bool)
    if typ == "integer":
        # bool ar en underklass till int i Python. True som antal ar ett
        # modellfel som annars slinker igenom.
        return isinstance(varde, int) and not isinstance(varde, bool)
    if typ == "number":
        return isinstance(varde, (int, float)) and not isinstance(varde, bool)
    if typ == "array":
        return isinstance(varde, list)
    if typ == "object":
        return isinstance(varde, dict)
    if typ == "null":
        return varde is None
    raise Schemafel("okand type %r; skulle ha fastnat i schemakontrollen" % (typ,))


def _typnamn(typ):
    return "/".join(typ) if isinstance(typ, list) else typ


def _granska_varde(varde, s, stig, f):
    typer = s["type"] if isinstance(s["type"], list) else [s["type"]]
    if not any(_ar_av_typ(varde, t) for t in typer):
        f.append("%s: forvantade %s, fick %s"
                 % (stig, _typnamn(s["type"]), type(varde).__name__))
        return
    if "enum" in s and varde not in s["enum"]:
        f.append("%s: %r ar inte ett av %s" % (stig, varde, s["enum"]))
    if isinstance(varde, list):
        if "minItems" in s and len(varde) < s["minItems"]:
            f.append("%s: minst %d varden, fick %d"
                     % (stig, s["minItems"], len(varde)))
        if "maxItems" in s and len(varde) > s["maxItems"]:
            f.append("%s: hogst %d varden, fick %d"
                     % (stig, s["maxItems"], len(varde)))
        if "items" in s:
            for i, v in enumerate(varde):
                _granska_varde(v, s["items"], "%s[%d]" % (stig, i), f)
    if isinstance(varde, dict) and "properties" in s:
        for namn in s.get("required", []):
            if namn not in varde:
                f.append("%s: nyckeln %s saknas" % (stig, namn))
        for namn, v in varde.items():
            if namn in s["properties"]:
                _granska_varde(v, s["properties"][namn], "%s.%s" % (stig, namn), f)


def validera_argument(verktyg, argument):
    """Returnerar argumenten kompletterade med default-varden.

    Kastar Argumentfel med HELA problemlistan. Tre klasser av fel avvisas
    fore korning, precis som 45_verktyg.md kraver: okant argument, saknat
    obligatoriskt argument, och fel typ.
    """
    if argument is None:
        argument = {}
    if not isinstance(argument, dict):
        raise Argumentfel(verktyg.namn,
                          ["argumenten maste vara ett objekt, fick %s"
                           % type(argument).__name__])
    p = verktyg.parameters
    egenskaper = p["properties"]
    krav = p.get("required", [])
    f = []

    for namn in sorted(argument):
        if namn not in egenskaper:
            kanda = ", ".join(sorted(egenskaper)) or "inga"
            f.append("okant argument %r; %s tar %s" % (namn, verktyg.namn, kanda))

    for namn in krav:
        if namn not in argument:
            f.append("obligatoriskt argument %r saknas" % namn)

    for namn, varde in sorted(argument.items()):
        if namn in egenskaper:
            _granska_varde(varde, egenskaper[namn], namn, f)

    for grupp in p.get("x-minst-en-av", []):
        if not any(n in argument for n in grupp):
            f.append("minst ett av %s maste anges" % ", ".join(grupp))

    for grupp in p.get("x-tillsammans", []):
        givna = [n for n in grupp if n in argument]
        if givna and len(givna) != len(grupp):
            f.append("%s hor ihop och maste anges tillsammans; %s saknas"
                     % (", ".join(grupp),
                        ", ".join(n for n in grupp if n not in argument)))

    if f:
        raise Argumentfel(verktyg.namn, f)

    ut = dict(argument)
    for namn, s in egenskaper.items():
        if namn not in ut and "default" in s:
            ut[namn] = s["default"]
    return ut


def validera_resultat(verktyg, resultat):
    """Provar bryggans svar mot verktygets returns-schema.

    Arvd som verify-contract-mekanism (20_arv.md): ett svar som inte haller
    sin egen form far aldrig raknas som en lyckad korning.
    """
    if not isinstance(resultat, dict):
        raise Svarsfel("%s: svaret ar %s, inte ett objekt"
                       % (verktyg.namn, type(resultat).__name__))
    f = []
    r = verktyg.returns
    for namn in r.get("required", []):
        if namn not in resultat:
            f.append("nyckeln %s saknas i svaret" % namn)
    for namn, varde in sorted(resultat.items()):
        if namn in r["properties"]:
            _granska_varde(varde, r["properties"][namn], namn, f)
    if f:
        raise Svarsfel("%s: %s" % (verktyg.namn, "; ".join(f)))
    return resultat
