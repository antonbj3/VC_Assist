# -*- coding: utf-8 -*-
"""Vilka verktyg som lamnas till modellen nar de inte langre far plats alla.

VARFOR MASKINERIET BYGGS NU, OCH INTE "DEN DAG DET BEHOVS"
----------------------------------------------------------
23_llm_granssnitt.md avsnitt 3 skrev: "Med dagens 21 verktyg och en profil pa
128 000 tokens ar kvoten cirka 2 %. Urvalsmaskineriet byggs alltsa inte nu."

MATT 2026-09-05 (M-102), med samma metod som specen sjalv anvande:

    registrerade verktyg      122       (var 21)
    verktygsschema totalt   98 080 byte (var 11 074)
    medel per verktyg          803 byte (var 527)

98 080 byte ar ~24 500 tokens vid 4 byte per token, alltsa ~19 % av ett
fonster pa 128 000 - mot postens tak pa 10 % (25_kontextbudget.md avsnitt 1).
Trosklen ar alltsa redan passerad. Villkoret i specen ar dessutom TVA
storheter, och bada ar brutna: 122 > 100 och 19 % > 10 %.

ALGORITMEN AR DETERMINISTISK, INGEN INBADDNING
Samma skal som 46_kunskapsindex.md: exakt namnuppslag och nyckelordssokning
racker och gar att prova. Rangordningen ar api_index._rang:s, ord for ord, sa
att tva rangordningar i samma repo inte glider isar.

TRE LAGER, I ORDNING
  1. ALLTID MED. Utan dem kan modellen inte ta reda pa var den ar.
  2. FASTNAGLADE. Ett verktyg som redan anvants med LYCKAT utfall i den har
     arbetsordern ligger kvar resten av arbetsordern. Ett verktyg som
     forsvinner mitt i ett bygge gor bygget omojligt att avsluta.
  3. TOPP N mot turens text.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# Domanerna och namnen som alltid foljer med.
# Harkomst: 23_llm_granssnitt.md avsnitt 3, "Urvalsalgoritmen, nar den behovs".
ALLTID_DOMANER = ("knowledge", "simulation")
ALLTID_NAMN = ("list_components", "find_component", "list_interfaces",
               "can_connect")

# Taket for hela urvalet. DOK ur 20_arv.md via 23_llm_granssnitt.md: "20-40
# verktyg". Talet ar kallprojektets, matt pa 448 verktyg och en annan doman -
# I7 galler, andras tal ar inte granser for oss, och taket ar darfor en
# STANDARD som anroparen far satta om.
URVAL_MAX = 40              # DOK ur 20_arv.md via 23_llm_granssnitt.md

# Kortaste ord ur turens text som far bara en sokning. Kortare ord ("av",
# "en", "st") traffar delstrangar i nastan varje beskrivning och gor
# rangordningen till brus.
MINSTA_SOKORD = 3           # 23_llm_granssnitt.md avsnitt 3

# Rangordningen LANAS ur api_index i stallet for att kopieras. En kopierad
# ordlista ar tva listor sa fort nagon rattar den ena, och den regeln har
# redan brutits tre ganger i det har repot (M-94, M-95, M-98). Stegen ar
# identiska; det som for en API-symbol ar TYPNAMNET ar for ett verktyg dess
# DOMAN, och `_rang` nedan laser domanen i det steget.
from ..api_index import _RANGORDNING as RANGORDNING  # noqa: E402

_ORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _rang(verktyg, fras: str, lag: str) -> Optional[str]:
    namn_lag = verktyg.namn.lower()
    if verktyg.namn == fras:
        return "exakt"
    if namn_lag == lag:
        return "exakt_skiftlagesokant"
    if namn_lag.startswith(lag):
        return "prefix"
    if lag in namn_lag:
        return "delstrang_namn"
    if lag in (verktyg.doman or "").lower():
        return "delstrang_typ"      # for ett verktyg AR domanen dess typ
    if lag in (verktyg.beskrivning or "").lower():
        return "delstrang_beskrivning"
    return None


def _poang(rang: str) -> int:
    return len(RANGORDNING) - RANGORDNING.index(rang)


def rangordna(register: Dict[str, object], text: str) -> List[Tuple[str, int]]:
    """[(verktygsnamn, poang)] mot turens text, hogst poang forst."""
    ord_ = [o for o in _ORD.findall(text or "") if len(o) >= MINSTA_SOKORD]
    bast: Dict[str, int] = {}
    for fras in ord_:
        lag = fras.lower()
        for namn, v in register.items():
            r = _rang(v, fras, lag)
            if r is None:
                continue
            p = _poang(r)
            if p > bast.get(namn, 0):
                bast[namn] = p
    return sorted(bast.items(), key=lambda kv: (-kv[1], kv[0]))


def alltid_med(register: Dict[str, object]) -> Tuple[str, ...]:
    ut = set(n for n in ALLTID_NAMN if n in register)
    for namn, v in register.items():
        if getattr(v, "doman", None) in ALLTID_DOMANER:
            ut.add(namn)
    return tuple(sorted(ut))


def valj(register: Dict[str, object], text: str,
         fastnaglade: Iterable[str] = (),
         tak: int = URVAL_MAX) -> Tuple[str, ...]:
    """De verktyg som exponeras i turen. Deterministiskt, alltid samma svar.

    Taket kan overskridas av lager 1 och 2 och det ar med flit: alltid-med och
    fastnaglade ar KRAV, inte onskemal. Ett tak som far kasta ut ett verktyg
    som redan anvants i arbetsordern gor bygget omojligt att avsluta, och det
    ar ett dyrare fel an ett stort schema.
    """
    valda = list(alltid_med(register))
    for n in fastnaglade:
        if n in register and n not in valda:
            valda.append(n)
    kvar = max(0, tak - len(valda))
    for namn, _p in rangordna(register, text):
        if kvar <= 0:
            break
        if namn in valda:
            continue
        valda.append(namn)
        kvar -= 1
    return tuple(sorted(valda))


def schematext(register: Dict[str, object], namn: Sequence[str]) -> str:
    """Verktygsschemat i kanonisk form, som text, for budgetens rakning."""
    import json
    delar = [register[n].som_openai() for n in namn if n in register]
    return json.dumps(delar, ensure_ascii=False, sort_keys=True)


def traff(behovda: Iterable[str], urval: Iterable[str]) -> Tuple[int, int]:
    """(traffade, behovda). Talet rapporteras ALLTID med urvalets storlek.

    Ett urval som traffar 100 % genom att skicka allt har inte matt nagot.
    """
    b = [n for n in behovda]
    u = set(urval)
    return sum(1 for n in b if n in u), len(b)
