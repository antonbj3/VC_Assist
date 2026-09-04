# -*- coding: utf-8 -*-
"""Modelladaptern: den tunna gransen mot en sprakmodell.

Harnessen kanner bara det som star har. Ingen leverantor namns i nagon annan
modul i harnessen an oversattning.py, och det provas mekaniskt i
tests/enhet/test_harness.py. Skalet ar rakt: operatoren har sagt att en annan
leverantors modell kan komma att anvanda verktyget, och en harness som ar
byggd runt EN leverantors svarsform gar inte att flytta. Leverantorsnamnen
star darfor bara i oversattning.py, dar de hor hemma.

Kontraktet ar tre typer och en metod:

    Meddelande   en rad i turens historik, med en ROLL som ar var, inte
                 leverantorens
    Verktygsanrop   ett anrop modellen bett om
    Modellsvar   text och/eller anrop
    Modell.svara(systemprompt, meddelanden, verktyg) -> Modellsvar

`verktyg` ar VARA Verktyg-objekt, inte en leverantors schemaform. Adaptern
oversatter sjalv med oversattning.py. Sa slipper harnessen valja en
leverantors form som sin egen interna form.

AttrappModell langst ned ar for prov. Den ror inget natverk och kan inte
gora det: den har ingen socket och ingen url, bara en lista svar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence, Tuple

from .fel import Modellfel

# Rollerna i turens historik. VARA namn, inte en leverantors.
#
#   uppgift   operatorens uppgift
#   modell    modellens eget svar
#   verktyg   ett verktygssvar tillbaka till modellen
#   grind     harnessens egen text: ett avslag eller ett omskrivningskrav
ROLLER = ("uppgift", "modell", "verktyg", "grind")


@dataclass(frozen=True)
class Meddelande:
    roll: str
    text: str
    anrop_id: Optional[str] = None
    verktyg: Optional[str] = None

    def __post_init__(self):
        if self.roll not in ROLLER:
            raise Modellfel("okand roll %r; rollerna ar %s"
                            % (self.roll, ", ".join(ROLLER)))


@dataclass(frozen=True)
class Verktygsanrop:
    """Ett anrop modellen bad om. Argumenten ar redan avkodade till Python."""

    namn: str
    argument: Dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def beskrivning(self) -> str:
        delar = ["%s=%r" % (k, self.argument[k]) for k in sorted(self.argument)]
        return "%s(%s)" % (self.namn or "<utan namn>", ", ".join(delar))

    def nyckel(self) -> str:
        """Identitet for upprepningsregeln: samma namn OCH samma argument."""
        return self.beskrivning()


@dataclass(frozen=True)
class Modellsvar:
    text: str = ""
    anrop: Tuple[Verktygsanrop, ...] = ()
    leverantor: str = ""

    @property
    def tomt(self) -> bool:
        """Varken text eller anrop. Tystnad ar aldrig ett godkannande (I3)."""
        return not (self.text or "").strip() and not self.anrop

    @property
    def ar_slutsvar(self) -> bool:
        """Ett svar utan anrop ar turens slutsvar och provas av grindarna."""
        return not self.anrop


class Modell(object):
    """Basen for varje adapter. Underklassen implementerar bara svara()."""

    namn = "okand"
    leverantor = "okand"

    def svara(self, systemprompt: str, meddelanden: Sequence[Meddelande],
              verktyg: Sequence[Any]) -> Modellsvar:
        raise NotImplementedError(
            "en modelladapter maste implementera svara(); en adapter som "
            "returnerar nagot tomt i stallet skulle se ut som tystnad fran "
            "modellen och domas som modellens fel")


class AttrappModell(Modell):
    """En modell med ett manus. Endast for prov.

    Far ALDRIG anvandas i drift, och kan inte heller: den har ingen kanal ut.
    Konsument ar efterlevnadsbanken i fallor.py och tests/enhet/.

    Tar slut manuset svarar den tomt. Det ar med flit: ett slut manus ar en
    modell som slutade svara, och harnessen ska da stoppa turen som tystnad i
    stallet for att hitta pa ett svar.
    """

    leverantor = "attrapp"

    def __init__(self, svar: Sequence[Modellsvar], namn: str = "attrapp"):
        self.namn = namn
        self._svar = list(svar)
        self._i = 0
        # Vad adaptern faktiskt fick. Proven laser detta for att visa att
        # systemprompten och verktygen verkligen gick hela vagen ut.
        self.sedda_systemprompter = []
        self.sedda_historiker = []
        self.sedda_verktygsnamn = []

    def svara(self, systemprompt, meddelanden, verktyg) -> Modellsvar:
        self.sedda_systemprompter.append(systemprompt)
        self.sedda_historiker.append(tuple(meddelanden))
        self.sedda_verktygsnamn.append(
            tuple(getattr(v, "namn", str(v)) for v in verktyg))
        if self._i >= len(self._svar):
            return Modellsvar(text="", anrop=(), leverantor=self.leverantor)
        svar = self._svar[self._i]
        self._i += 1
        return svar

    @property
    def kvar(self) -> int:
        return max(0, len(self._svar) - self._i)


def sag(text: str) -> Modellsvar:
    """Kort form: ett slutsvar i ren text."""
    return Modellsvar(text=text)


def anropa(namn: str, argument: Optional[Dict[str, Any]] = None,
           text: str = "") -> Modellsvar:
    """Kort form: ett svar som ber om ett verktygsanrop.

    Utan id. Loopen satter ett lopande id per runda, sa att tva korningar av
    samma manus ger samma protokoll byte for byte - ett slumpat id hade gjort
    bankens utdata ojamforbar mellan korningar.
    """
    return Modellsvar(text=text,
                      anrop=(Verktygsanrop(namn=namn,
                                           argument=dict(argument or {})),))
