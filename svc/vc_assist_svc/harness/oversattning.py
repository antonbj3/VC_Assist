# -*- coding: utf-8 -*-
"""Oversattning mellan harnessens form och leverantorernas.

DETTA AR DEN ENDA MODULEN I HARNESSEN SOM FAR NAMNA EN LEVERANTOR.
tests/enhet/test_harness.py provar det mekaniskt over harnessens alla filer.
Skalet: verktyget ska kunna koras av en annan leverantors modell utan att
nagon annan del av harnessen ror sig.

Kallstampel enligt docs/spec/01_kalldisciplin.md: formerna nedan ar **DOK**.
De ar skrivna ur leverantorernas publicerade granssnittsbeskrivningar och ar
INTE provade mot en levande tjanst harifran - den har koden oppnar ingen
socket, och testerna gor ingen natverkstrafik. Vad som DAREMOT ar provat ar
att en inkommande svarsform pa varje leverantors utseende blir samma
Modellsvar, och att ett svar som inte haller formen kastar i stallet for att
ge ett tomt Modellsvar. Ett tyst tomt svar hade sett ut som modellens tystnad
och domts som modellens fel.

En skillnad ar vard att kanna till, och den ar inte kosmetisk:

  OpenAI-formen bar `additionalProperties: false` i parameterschemat, vilket
  ar det som gor ett uppfunnet argumentnamn otillatet redan hos modellen.
  Geminis schemadel tar inte emot nyckeln. Oversattningen SLAPPER darfor den
  nyckeln for Gemini - och det ar ofarligt av en enda anledning: harnessen
  provar varje argument mot samma schema med verktyg.validera_argument innan
  nagot kors, oavsett leverantor. Den som lagger till en leverantor har maste
  veta att det ar tjanstens egen validering som ar spärren, inte
  leverantorens schema.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Sequence

from .fel import Modellfel
from .modell import Modellsvar, Verktygsanrop

LEVERANTORER = ("openai", "anthropic", "gemini")

# Nycklar som Geminis schemadel inte tar emot. Se modulens docstring.
_EJ_I_GEMINI = ("additionalProperties", "x-minst-en-av", "x-tillsammans")


def _utan(schema: Any, nycklar: Sequence[str]) -> Any:
    if not isinstance(schema, dict):
        return schema
    ut = {}
    for k, v in schema.items():
        if k in nycklar:
            continue
        ut[k] = _utan(v, nycklar) if isinstance(v, (dict, list)) else v
    return ut


# ---- verktyg ut ----------------------------------------------------------

def till_openai(verktyg: Sequence[Any]) -> List[Dict[str, Any]]:
    """OpenAI function calling. Anvander verktygets EGEN som_openai().

    Ingen andra form av samma schema: verktygslagret ager formen, harnessen
    kopierar den inte.
    """
    return [v.som_openai() for v in verktyg]


def till_anthropic(verktyg: Sequence[Any]) -> List[Dict[str, Any]]:
    ut = []
    for v in verktyg:
        oppen = v.som_openai()["function"]
        ut.append({"name": oppen["name"],
                   "description": oppen["description"],
                   "input_schema": oppen["parameters"]})
    return ut


def till_gemini(verktyg: Sequence[Any]) -> List[Dict[str, Any]]:
    ut = []
    for v in verktyg:
        oppen = v.som_openai()["function"]
        ut.append({"name": oppen["name"],
                   "description": oppen["description"],
                   "parameters": _utan(oppen["parameters"], _EJ_I_GEMINI)})
    return [{"function_declarations": ut}]


# ---- svar in -------------------------------------------------------------

def _argument(rad: Any, kalla: str) -> Dict[str, Any]:
    """Argumenten som ordbok. En strang avkodas som JSON, aldrig med eval."""
    if isinstance(rad, dict):
        return dict(rad)
    if isinstance(rad, str):
        if not rad.strip():
            return {}
        try:
            avkodat = json.loads(rad)
        except ValueError as e:
            raise Modellfel("%s: argumenten gar inte att avkoda som JSON: %s"
                            % (kalla, e))
        if not isinstance(avkodat, dict):
            raise Modellfel("%s: argumenten avkodades till %s, inte ett objekt"
                            % (kalla, type(avkodat).__name__))
        return avkodat
    if rad is None:
        return {}
    raise Modellfel("%s: argumenten ar %s, varken objekt eller strang"
                    % (kalla, type(rad).__name__))


def fran_openai(svar: Dict[str, Any]) -> Modellsvar:
    if not isinstance(svar, dict) or not svar.get("choices"):
        raise Modellfel("openai: svaret saknar choices")
    meddelande = (svar["choices"][0] or {}).get("message") or {}
    text = meddelande.get("content") or ""
    anrop = []
    for i, rad in enumerate(meddelande.get("tool_calls") or []):
        funktion = rad.get("function") or {}
        anrop.append(Verktygsanrop(
            namn=funktion.get("name") or "",
            argument=_argument(funktion.get("arguments"), "openai"),
            id=rad.get("id") or "openai-%d" % i))
    return Modellsvar(text=text, anrop=tuple(anrop), leverantor="openai")


def fran_anthropic(svar: Dict[str, Any]) -> Modellsvar:
    if not isinstance(svar, dict) or "content" not in svar:
        raise Modellfel("anthropic: svaret saknar content")
    texter, anrop = [], []
    for i, block in enumerate(svar.get("content") or []):
        sort = block.get("type")
        if sort == "text":
            texter.append(block.get("text") or "")
        elif sort == "tool_use":
            anrop.append(Verktygsanrop(
                namn=block.get("name") or "",
                argument=_argument(block.get("input"), "anthropic"),
                id=block.get("id") or "anthropic-%d" % i))
    return Modellsvar(text="\n".join(t for t in texter if t),
                      anrop=tuple(anrop), leverantor="anthropic")


def fran_gemini(svar: Dict[str, Any]) -> Modellsvar:
    if not isinstance(svar, dict) or not svar.get("candidates"):
        raise Modellfel("gemini: svaret saknar candidates")
    innehall = (svar["candidates"][0] or {}).get("content") or {}
    texter, anrop = [], []
    for i, del_ in enumerate(innehall.get("parts") or []):
        if "text" in del_:
            texter.append(del_.get("text") or "")
        if "functionCall" in del_:
            anropsrad = del_["functionCall"] or {}
            anrop.append(Verktygsanrop(
                namn=anropsrad.get("name") or "",
                argument=_argument(anropsrad.get("args"), "gemini"),
                id=anropsrad.get("id") or "gemini-%d" % i))
    return Modellsvar(text="\n".join(t for t in texter if t),
                      anrop=tuple(anrop), leverantor="gemini")


UT = {"openai": till_openai, "anthropic": till_anthropic, "gemini": till_gemini}
IN = {"openai": fran_openai, "anthropic": fran_anthropic, "gemini": fran_gemini}


def oversattare(leverantor: str):
    """(ut, in) for en leverantor. Kastar pa okand - aldrig en gissad form."""
    if leverantor not in UT:
        raise Modellfel("okand leverantor %r; kanda ar %s"
                        % (leverantor, ", ".join(LEVERANTORER)))
    return UT[leverantor], IN[leverantor]
