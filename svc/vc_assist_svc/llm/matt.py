# -*- coding: utf-8 -*-
"""Storleken pa det som skickas, och de tva antaganden som mater den.

VARFOR MODULEN FINNS
--------------------
Repot bar i dag TVA olika omrakningar mellan text och tokens, och de star i
olika lager utan att kanna varandra:

    25_kontextbudget.md      4 byte per token      (ANTAGET)
    harness/sammansattning.py  3,0 tecken per token  (ANTAGET)

De ar inte samma storhet. Byte och tecken skiljer sig sa fort texten inte ar
ren ASCII, och var text ar svensk: varje a-ring och varje prick ar tva byte i
UTF-8. Ett tak satt i byte och ett tak satt i tecken sager alltsa olika saker
om samma strang, och den som satter det ena tror sig ha satt det andra.

Modulen gor tre saker och ingenting mer:

  1. Mater BADE byte och tecken. Bada ar deterministiska och kraver ingen
     leverantors tokenisering (att lasa in en tokenisering ar att lasa in en
     leverantor, L1 i 23_llm_granssnitt.md).
  2. Rakar om till tokens genom bada antagandena och tar det HOGSTA talet.
     Fail-closed: underskattar man tokens skickas en begaran som inte far
     plats, och det ar felet som upptacks av motparten (25_kontextbudget.md,
     grundregeln).
  3. Redovisar SPRIDNINGEN mellan de tva antagandena, sa att den som laser ett
     budgettal ser hur mycket av det som ar antagande.

INGEN AV DE TVA ANTAGANDENA AR MATT. Det ar hela poangen med att de star har,
tillsammans, med samma stampel: en siffra som ser exakt ut men vilar pa ett
omarkt antagande ar det som gor en spec farlig.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ANTAGET, 25_kontextbudget.md avsnitt 7 punkt 1: "4 byte per token - ingen
# raknare kord pa var text". Star har som ETT stalle i stallet for utspritt i
# harledda tal.
BYTE_PER_TOKEN = 4.0        # ANTAGET, 25_kontextbudget.md avsnitt 7

# ANTAGET, satt i harness/sammansattning.py och overtaget hit oforandrat:
# tecken per token for svensk text i en modern delordstokenisering. Talet ar
# lagt med flit - underskattas tecken per token blir budgeten for liten och
# nagot kapas i onodan, vilket ar det ofarliga felet.
# Harkomst: 25_kontextbudget.md (samma oppna punkt, avsnitt 7 punkt 1).
TECKEN_PER_TOKEN = 3.0      # ANTAGET, 25_kontextbudget.md avsnitt 7

# Hur mycket en UPPSKATTAD tokenraknare far avvika fran den faktiska begaran
# innan budgeten inte langre har nagon kand marginal.
# PRELIMINAR, satt av matning M-28 (adapterprovets punkt 4 i
# 23_llm_granssnitt.md avsnitt 1).
MARGINAL_UPPSKATTAD = 0.05  # PRELIMINAR, satts av M-28


@dataclass(frozen=True)
class Matt:
    """Storleken pa en text, i alla enheter lagret kanner.

    `tokens` ar det tal budgeten raknar med, och det ar det STORSTA av de tva
    uppskattningarna. `spridning` ar skillnaden mellan dem som andel av det
    storsta - las den som "sa mycket av det har talet ar antagande".
    """

    byte: int
    tecken: int
    tokens_ur_byte: int
    tokens_ur_tecken: int

    @property
    def tokens(self) -> int:
        return max(self.tokens_ur_byte, self.tokens_ur_tecken)

    @property
    def spridning(self) -> float:
        hogst = self.tokens
        if hogst <= 0:
            return 0.0
        return abs(self.tokens_ur_byte - self.tokens_ur_tecken) / float(hogst)

    def rad(self) -> str:
        return ("%d byte, %d tecken, %d tokens (%d ur byte, %d ur tecken, "
                "spridning %.1f %%)"
                % (self.byte, self.tecken, self.tokens, self.tokens_ur_byte,
                   self.tokens_ur_tecken, 100.0 * self.spridning))


def mat(text: str) -> Matt:
    """Mater en text i byte, tecken och tokens enligt bada antagandena."""
    if text is None:
        text = ""
    if not isinstance(text, str):
        raise TypeError("mat() tar text, inte %s" % type(text).__name__)
    b = len(text.encode("utf-8"))
    t = len(text)
    return Matt(byte=b, tecken=t,
                tokens_ur_byte=int(math.ceil(b / BYTE_PER_TOKEN)),
                tokens_ur_tecken=int(math.ceil(t / TECKEN_PER_TOKEN)))


def tokens(text: str) -> int:
    """Kortform for mat(text).tokens. Det tal budgeten haller sig till."""
    return mat(text).tokens


def med_marginal(antal: int, exakt: bool) -> int:
    """Tokentalet som budgeten ska rakna med, givet raknarens sort.

    En EXAKT raknare (profilens `tokenraknare`) tas som den ar. En UPPSKATTAD
    raknare far en marginal palagd, darfor att en uppskattning som ligger fel
    at fel hall ar precis den overskridning motparten upptacker at oss.
    """
    if antal < 0:
        raise ValueError("negativt tokental %r" % (antal,))
    if exakt:
        return antal
    return int(math.ceil(antal * (1.0 + MARGINAL_UPPSKATTAD)))
