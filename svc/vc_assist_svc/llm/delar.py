# -*- coding: utf-8 -*-
"""Delarna: hur turens innehall blir poster i budgeten.

Modulen ar limmet mellan de tre mekanismerna (kapning, ogontrim, scenvy) och
budgetens trimsteg. Den innehaller ingen egen policy - varje del far sin
trimmare ur den modul som ager just den storheten, sa att regeln finns pa ETT
stalle.

Att huvudboksraden byggs HAR och inte i kapningen ar ett medvetet val: raden ar
tjanstens egen text om vad som hande, och den ska aldrig kunna bli en
omskrivning av verktygets svar. Den bar anropet, utfallet och koden - inget
annat.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from . import ogontrim, scenvy
from .budget import (P_AVSTANGDA, P_HUVUDBOK, P_OGAT, P_RESULTAT, P_SCEN,
                     P_SCHEMA, P_SIGNALKARTA, P_SYSTEMPROMPT, P_UPPGIFT, Del)
from .kapning import Verktygssvar, kapa


def huvudboksrad(svar: Verktygssvar, verktyg=None) -> str:
    """En rad per verktygsanrop. Append-only, skrivs aldrig om.

    En omskriven huvudbok ar ett andra omdome om vad som hande.
    """
    if verktyg is not None:
        anrop = verktyg.beskriv_anrop(svar.argument)
    else:
        delar = ["%s=%r" % (k, svar.argument[k]) for k in sorted(svar.argument)]
        anrop = "%s(%s)" % (svar.verktyg, ", ".join(delar))
    if not svar.ok:
        return "%s  ->  FEL %s" % (anrop, svar.felnyckel)
    poster = None
    if isinstance(svar.resultat, dict):
        for n, v in sorted(svar.resultat.items()):
            if isinstance(v, list):
                poster = len(v)
                break
    if poster is None:
        return "%s  ->  ok" % anrop
    return "%s  ->  ok, %d poster" % (anrop, poster)


def systempromptdel(text: str) -> Del:
    """B1-B3, B5-B7. Skyddad: utan B5 resonerar modellen om en brygga som
    kanske ligger nere."""
    return Del(post=P_SYSTEMPROMPT, id="systemprompt", text=text, skyddad=True)


def uppgiftsdel(text: str) -> Del:
    """Uppgiften och planens aktuella steg. Det turen ska gora."""
    return Del(post=P_UPPGIFT, id="uppgift", text=text, skyddad=True)


def signalkartedel(text: str) -> Del:
    """Signalkartan. Tas den bort HITTAR MODELLEN PA TAGGNAMN (F3, I10)."""
    return Del(post=P_SIGNALKARTA, id="signalkarta", text=text, skyddad=True)


def avstangdadel(namn: Sequence[str], skal: Dict[str, str] = None) -> Del:
    """B4. Trimmas ned till en raknare, aldrig till tystnad."""
    skal = skal or {}
    rader = ["%s: %s" % (n, skal.get(n, "ytan saknas")) for n in sorted(namn)]
    return Del(post=P_AVSTANGDA, id="avstangda",
               text="\n".join(rader),
               ersattning=("%d verktyg avstangda; fraga om nagot saknas"
                           % len(namn)),
               data=tuple(sorted(namn)))


def schemadel(register: Dict[str, Any], namn: Sequence[str], text: str,
              urvalsfunktion) -> Del:
    """Verktygsschemat. Trimmas genom URVAL, aldrig genom att klippa schemat.

    Ett halvt schema ar ett verktyg med ett halvt argument, och det ar ett
    uppfunnet argumentnamn i nasta runda.
    """

    def trimmare(mal_byte: int):
        valda = urvalsfunktion(mal_byte)
        if not valda:
            return None
        from .urval import schematext
        ny = schematext(register, valda)
        if len(ny.encode("utf-8")) >= len(text.encode("utf-8")):
            return None
        return ny, ("semantiskt urval: %d av %d verktyg exponeras"
                    % (len(valda), len(namn)))

    return Del(post=P_SCHEMA, id="schema", text=text, trimmare=trimmare,
               data=tuple(namn))


def ogondel(rapport: str) -> Del:
    """Ogats rapport. Trimmas bara enligt ogontrim, med notisen UTANFOR blocket."""

    def trimmare(mal_byte: int):
        if mal_byte < 1:
            return None
        ny, notiser = ogontrim.trimma(rapport, mal_byte)
        if not notiser:
            return None
        return (ogontrim.block(ny, notiser),
                "; ".join(n.rad() for n in notiser))

    return Del(post=P_OGAT, id="ogat", text=rapport, trimmare=trimmare,
               data=rapport)


def scendel(svar: Verktygssvar, plannamn: Iterable[str],
            kopplingar: Sequence[Tuple[str, str]] = ()) -> Del:
    """Scenvyn. Over taket kokas den enligt scenvy, aldrig genom att klippa."""

    def trimmare(_mal_byte: int):
        vy = scenvy.sammanfatta(svar, plannamn, kopplingar)
        if vy is svar:
            return None
        return vy.text(), (vy.resultat or {}).get("kaprad", "scenvyn kokades")

    return Del(post=P_SCEN, id="scen", text=svar.text(), trimmare=trimmare,
               data=svar)


def resultatdel(svar: Verktygssvar, returns_schema=None, nr: int = 0) -> Del:
    """Ett verktygsresultat.

    Tva vagar bort, i den ordning budgeten kor dem:
      steg 2  hela resultatet ersatts av sin huvudboksrad
      steg 7  det som ar kvar kapas PA POSTER med avkortad=true
    """

    def trimmare(mal_byte: int):
        if mal_byte < 1:
            return None
        kapad, notis = kapa(svar, mal_byte, returns_schema)
        if not notis.kapat:
            return None
        return kapad.text(), notis.rad()

    return Del(post=P_RESULTAT, id="resultat:%d" % nr, text=svar.text(),
               trimmare=trimmare, ersattning=huvudboksrad(svar), data=svar)


def huvudboksdelar(rader: Sequence[str]) -> List[Del]:
    return [Del(post=P_HUVUDBOK, id="huvudbok:%d" % i, text=r)
            for i, r in enumerate(rader)]
