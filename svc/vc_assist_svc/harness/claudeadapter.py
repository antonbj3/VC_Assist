# -*- coding: utf-8 -*-
"""En riktig modell bakom `Modell`-ytan, byggd pa `claude -p`.

`AttrappModell` har alltid funnits; en riktig har aldrig gjort det. Det ar
precis det halet fas 9 star oppen pa - `tests/protocol/fas9_banken.md` sager
"det finns ingen nyckel och ingen modellklient i repot", och darfor drevs
reparationsslingan for hand.

## Vad adaptern INTE kan, och varfor den sager ifran i stallet for att gissa

`claude -p` kors med TOM verktygslista, sa modellen kan inte lasa nagon fil -
det ar sparren som gor fas 9:s matning giltig (modellen far inte se facit).
Foljden ar att adaptern aldrig kan producera ett `Verktygsanrop`.

En harness som skickar med verktyg och far ett rent textsvar tillbaka skulle
mata det som **modellens** oformaga att anvanda sina verktyg. Det vore en falsk
matning om modellen, orsakad av adaptern. Darfor kastar `svara()` nar den fatt
verktyg den inte kan bara. Reparationsslingan skickar inga verktyg - text in,
ST ut - och det ar den slingan adaptern finns for.
"""
from __future__ import annotations

from typing import Any, Sequence

from .. import modellklient
from .modell import Meddelande, Modell, Modellsvar


class Adapterfel(Exception):
    """Adaptern kan inte bara uppdraget. ALDRIG ett tomt svar i stallet."""


class ClaudeModell(Modell):
    """`claude -p` bakom `Modell`. Ren text in, ren text ut."""

    leverantor = "anthropic/claude-cli"

    def __init__(self, klient=None, modell="sonnet", namn=None):
        self._klient = klient or modellklient.ClaudeCLI(modell=modell)
        self.namn = namn or getattr(self._klient, "modell", modell)
        # Vad turen kostade. Ett tak pa fyra varv ar ett pastaende om ingen
        # kan saga vad varven kostade.
        self.kostnad_usd = 0.0
        self.anrop = 0

    def svara(self, systemprompt: str, meddelanden: Sequence[Meddelande],
              verktyg: Sequence[Any]) -> Modellsvar:
        if verktyg:
            raise Adapterfel(
                "ClaudeModell fick %d verktyg men kan inte anropa nagot: "
                "klienten kor med tom verktygslista sa modellen inte ska kunna "
                "lasa facit. Ett textsvar har hade matts som att MODELLEN lat "
                "bli att anvanda sina verktyg." % len(verktyg))
        fraga = _en_strang(systemprompt, meddelanden)
        svar = self._klient.fraga(fraga)
        self.kostnad_usd += svar.kostnad_usd
        self.anrop += 1
        return Modellsvar(text=svar.text, anrop=(), leverantor=self.leverantor)


def _en_strang(systemprompt: str, meddelanden: Sequence[Meddelande]) -> str:
    """Systemprompt och historik till EN fraga.

    `claude -p` tar en strang. Rollerna markeras ut i klartext i stallet for
    att slas ihop tyst - en modell som inte ser var grindens ord slutar och
    uppgiften borjar svarar pa fel sak.
    """
    delar = []
    if (systemprompt or "").strip():
        delar.append(systemprompt.strip())
    for m in meddelanden:
        roll = getattr(m, "roll", None) or getattr(m, "avsandare", "") or ""
        text = getattr(m, "text", None)
        if text is None:
            text = getattr(m, "innehall", "")
        text = (text or "").strip()
        if not text:
            continue
        delar.append(("[%s]\n%s" % (roll.upper(), text)) if roll else text)
    return "\n\n".join(delar)
