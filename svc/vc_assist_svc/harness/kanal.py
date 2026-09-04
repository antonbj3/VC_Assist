# -*- coding: utf-8 -*-
"""Verktygskanalen: dar ett godkant anrop faktiskt utfors.

Harnessen kanner bara Verktygskanal.utfor(). Det ar en tunn gräns med ett
bestamt syfte: forgranskningens grindar (forgranskning.py) ar desamma oavsett
om anropet sedan gar till en levande brygga eller till en attrapp i en bank.
Det ar det som gor efterlevnadsbanken vard nagot - den mater RIKTIGA grindar
mot en attrapp-varld, inte en attrapp av grindarna.

Utforarkanal lagger ingen egen routing ovanpa verktygslagret. effect -> exec
eller exec_queue avgors dar den ska avgoras, i verktyg/utforare.py, och den
tabellen ar den enda platsen i tjansten dar operationsnamnen star (I12).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..verktyg.fel import Verktygsfel
from .fel import Kanalfel


@dataclass(frozen=True)
class Anropsutfall:
    """Vad ett anrop lamnade efter sig. Formen ar densamma for alla kanaler."""

    verktyg: str
    argument: Dict[str, Any]
    ok: bool
    resultat: Any = None
    fel: str = ""
    koad: bool = False
    qid: str = ""
    varningar: Tuple[str, ...] = ()
    # Andrade anropet scenen? Satt av loopen ur den GENERERADE koden
    # (turordning.andrar_scenen), inte ur verktygets deklarerade effect:
    # matverktygen ar deklarerade write men andrar ingenting, eftersom deras
    # kod bara kor update() for att fa farska matt (M-36). Falt och inte
    # harledning, sa att arlighetsgrinden kan lasa det utan att kanna till
    # nagon kodmall. Satt av M-53.
    andrade: bool = False

    def beskrivning(self) -> str:
        if self.ok and self.koad:
            return "%s koades som %s och vantar pa godkannande" % (
                self.verktyg, self.qid)
        if self.ok:
            return "%s: %r" % (self.verktyg, self.resultat)
        return "%s FOLL: %s" % (self.verktyg, self.fel)


class Verktygskanal(object):
    """Basen. En kanal gor ett anrop och beskriver utfallet, inget mer."""

    def utfor(self, namn: str, argument: Dict[str, Any]) -> Anropsutfall:
        raise NotImplementedError(
            "en verktygskanal maste implementera utfor(); en kanal som "
            "returnerar nagot tomt skulle se ut som ett lyckat anrop utan "
            "resultat, och det ar ett godkannande ur tystnad (I3)")


class Utforarkanal(Verktygskanal):
    """Den skarpa kanalen: verktyg.Utforare mot en levande brygga."""

    def __init__(self, utforare):
        self.utforare = utforare

    def utfor(self, namn, argument) -> Anropsutfall:
        try:
            resultat = self.utforare.utfor(namn, argument)
        except Verktygsfel as e:
            # Verktygslagrets egna avslag ar ett UTFALL, inte ett haveri:
            # modellen ska fa veta vad som var fel och kunna ratta det.
            return Anropsutfall(verktyg=namn, argument=dict(argument),
                                ok=False, fel=str(e))
        except OSError as e:
            # Bryggan gick inte att na. Det ar inget modellen kan ratta, och
            # far darfor inte se ut som ett verktygsfel.
            raise Kanalfel("%s: bryggan gick inte att na: %s" % (namn, e))
        return Anropsutfall(
            verktyg=namn, argument=dict(argument), ok=True,
            resultat=resultat.resultat, koad=resultat.koad,
            qid=resultat.qid or "")


@dataclass(frozen=True)
class Faller:
    """Ett manusfel i en attrapp: anropet ska falla med den har texten."""

    fel: str


class Attrappkanal(Verktygskanal):
    """En kanal med ett manus. Endast for prov och for banken.

    Manuset ar {verktygsnamn: [svar, ...]} dar ett svar ar antingen ett
    resultat (ordbok) eller ett Faller(...). Svaren tas i ordning.

    Tar svaren slut, eller anropas ett verktyg som inte star i manuset,
    svarar kanalen med ett FEL och inte med ett tomt resultat. Ett tomt
    resultat hade sett ut som en lyckad korning utan matvarden, och det ar
    precis den falska framgang harnessen finns for att fanga.
    """

    def __init__(self, manus: Optional[Dict[str, Sequence[Any]]] = None):
        self.manus = {n: list(v) for n, v in (manus or {}).items()}
        self.anropade: List[Tuple[str, Dict[str, Any]]] = []

    def utfor(self, namn, argument) -> Anropsutfall:
        self.anropade.append((namn, dict(argument)))
        kvar = self.manus.get(namn)
        if not kvar:
            return Anropsutfall(
                verktyg=namn, argument=dict(argument), ok=False,
                fel=("attrappkanalen har inget svar kvar for %s; det ar ett "
                     "fel och inte ett tomt resultat" % namn))
        svar = kvar.pop(0)
        if isinstance(svar, Faller):
            return Anropsutfall(verktyg=namn, argument=dict(argument),
                                ok=False, fel=svar.fel)
        return Anropsutfall(verktyg=namn, argument=dict(argument), ok=True,
                            resultat=svar)
