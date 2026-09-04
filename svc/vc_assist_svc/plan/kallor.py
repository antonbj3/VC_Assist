# -*- coding: utf-8 -*-
"""Kallorna utanfor paketet, importerade pa ETT stalle.

Tva kallor ligger utanfor tjansten och far aldrig kopieras hit:

  oga_kontrakt   ext/vc_addon/vc_assist/oga_kontrakt.py
                 Ogats domsgrammatik. Samma fil laser och skriver domen, sa
                 grinden och ogat kan inte drifta isar (docs/spec/41_ogat_kontrakt.md).
                 Planens verifieringskrav uttrycks i DEN grammatiken, inte i
                 en egen.

  bankschema     bank/schema.py
                 Malldisciplinen: en facitrad med '*' dar talen star, och de
                 tva funktionerna som avgor om en sadan mall over huvud taget
                 kan uppsta ur ogats monster. En plans verifieringskrav och en
                 bankuppgifts facit MASTE betyda samma sak - annars ser tva
                 identiska rader lika ut men provas olika. Darfor delas
                 implementationen i stallet for att skrivas tva ganger.
                 bank/schema.py importerar sjalv oga_kontrakt, sa det ar
                 fortfarande en enda grammatik.

Samma vag in som guldgrind.py och bank/lasare.py redan anvander: sokvagen
laggs till, modulen importeras. Ingen kopia, ingen andra sanning.
"""
from __future__ import annotations

import os
import sys

ROT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))

_EXT = os.path.join(ROT, "ext", "vc_addon", "vc_assist")
_BANK = os.path.join(ROT, "bank")
for _katalog in (_EXT, _BANK):
    if _katalog not in sys.path:
        sys.path.insert(0, _katalog)

import oga_kontrakt as K          # noqa: E402
import schema as bankschema       # noqa: E402

UPPGIFTSKATALOG = bankschema.UPPGIFTSKATALOG

__all__ = ["K", "bankschema", "ROT", "UPPGIFTSKATALOG"]
