# -*- coding: utf-8 -*-
"""En modell som gar att ANROPA, sa reparationsslingan kan kora sig sjalv.

Fas 9 stod oppen pa en enda punkt, och den star i `tests/protocol/fas9_banken.md`
med de orden: *"Slingan drevs for hand. Bryggan mellan grind och modell ar ett
meddelande, inte ett API-anrop. Det finns ingen nyckel och ingen modellklient i
repot."* Talen var matta, men `M-52`:s tak pa fyra varv var oprovat mot en
riktig modell eftersom nagon manniska relaade varje varv.

Modulen ar bryggan. Den bar tva transporter:

* `ClaudeCLI` - `claude -p`, alltsa en riktig modell, en riktig kostnad.
* `Inspelad` - fardiga svar ur en fil. Deterministisk och gratis, sa slingans
  EGEN logik gar att prova utan att kopa ett modellsvar per prov.

Tre saker ar invarianter och inte bekvamligheter:

1. **Modellen far inte kunna lasa repot.** Matningens giltighet star pa att den
   inte sett facit (fas 9 mater kontamineringen). Transporten kor darfor utan
   verktyg och i en TOM katalog utanfor repot. Ett forbud i en prompt ar en bon;
   det har ar en sparr.
2. **Ett misslyckat anrop far aldrig se ut som ett svar.** Tom utdata, `is_error`
   eller en nollskild slutkod kastar. En slinga som far tomma strangar tillbaka
   skulle rapportera "modellen lagade ingenting" i stallet for "modellen
   svarade aldrig", och de tva ar olika matningar.
3. **Kostnaden foljer med svaret.** En slinga med ett tak pa fyra varv maste
   kunna saga vad de fyra varven kostade, annars ar taket ett pastaende.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence


class Modellfel(Exception):
    """Modellen svarade inte. ALDRIG samma sak som att den svarade daligt."""


@dataclass
class Svar:
    """Ett modellsvar med det som gor det granskningsbart."""

    text: str
    modell: str
    kostnad_usd: float = 0.0
    varv: int = 1
    ratt: Dict = field(default_factory=dict)

    def __post_init__(self):
        # Fail-closed: ett tomt svar ar inget svar. Fangas har och inte hos
        # anroparen, sa ingen transport kan slippa undan regeln.
        if not (self.text or "").strip():
            raise Modellfel("modellen gav ett tomt svar (modell %s)" % self.modell)


class Modellklient(object):
    """Ytan slingan ser. En rad: fraga in, `Svar` ut, eller `Modellfel`."""

    namn = "abstrakt"

    def fraga(self, prompt: str) -> Svar:
        raise NotImplementedError


class ClaudeCLI(Modellklient):
    """`claude -p` som modellklient.

    Ingen API-nyckel behovs - CLI:t bar sin egen inloggning. Det ar skalet att
    den har vagen finns: repot kan kora slingan pa den maskin som redan har ett
    Claude Code installerat, utan en hemlighet i en fil.
    """

    namn = "claude-cli"

    def __init__(self, modell="sonnet", tidsgrans=600, korbar=None,
                 arbetskatalog=None):
        self.modell = modell
        self.tidsgrans = tidsgrans
        self.korbar = korbar or shutil.which("claude")
        # None betyder "skapa en tom katalog per fraga". En angiven katalog
        # finns bara for proven, och provas mot repot nedan.
        self.arbetskatalog = arbetskatalog

    def tillganglig(self) -> bool:
        return bool(self.korbar) and os.path.exists(self.korbar)

    def _kommando(self, prompt: str) -> List[str]:
        return [self.korbar, "-p", prompt,
                "--output-format", "json",
                # Tom verktygslista: modellen kan inte lasa nagon fil, alltsa
                # inte heller facit. Sparren, inte bonen.
                "--allowed-tools", "",
                "--model", self.modell]

    def fraga(self, prompt: str) -> Svar:
        if not self.tillganglig():
            raise Modellfel(
                "hittar ingen korbar `claude`. Installera Claude Code eller "
                "anvand Inspelad-transporten.")
        egen = self.arbetskatalog is None
        katalog = tempfile.mkdtemp(prefix="vcassist-modell-") if egen \
            else self.arbetskatalog
        try:
            _neka_repot(katalog)
            try:
                k = subprocess.run(self._kommando(prompt), cwd=katalog,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   timeout=self.tidsgrans)
            except subprocess.TimeoutExpired:
                raise Modellfel("modellen svarade inte inom %d s" % self.tidsgrans)
            if k.returncode != 0:
                raise Modellfel("claude gav slutkod %d: %s" % (
                    k.returncode, k.stderr.decode("utf-8", "replace")[:400]))
            try:
                d = json.loads(k.stdout.decode("utf-8", "replace"))
            except ValueError as e:
                raise Modellfel("kunde inte lasa svaret som JSON: %s" % e)
            if d.get("is_error") or d.get("subtype") != "success":
                raise Modellfel("claude rapporterade fel: %r"
                                % (d.get("subtype") or d.get("result"))[:300])
            return Svar(text=d.get("result") or "", modell=self.modell,
                        kostnad_usd=float(d.get("total_cost_usd") or 0.0),
                        varv=int(d.get("num_turns") or 1), ratt=d)
        finally:
            if egen:
                shutil.rmtree(katalog, ignore_errors=True)


def _neka_repot(katalog: str) -> None:
    """Arbetskatalogen far inte ligga i repot.

    Verktygslistan ar tom, men en katalog inne i repot skulle anda gora facit
    till modellens narmaste granne om nagon senare slapper pa den listan. Tva
    lager, for att det ena ar en flagga och det andra ar en sokvag.
    """
    rot = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", ".."))
    riktig = os.path.realpath(katalog)
    if riktig == os.path.realpath(rot) or riktig.startswith(
            os.path.realpath(rot) + os.sep):
        raise Modellfel(
            "arbetskatalogen %s ligger i repot. Modellen far inte kora dar: "
            "matningens giltighet star pa att den inte sett facit." % katalog)


class Inspelad(Modellklient):
    """Fardiga svar, i ordning. For att prova SLINGAN, inte modellen.

    Ett prov som koper ett modellsvar ar bade dyrt och ostabilt. Den har
    transporten gor slingans egen logik - taket, avbrottet, raknandet -
    provbar utan en enda token.
    """

    namn = "inspelad"

    def __init__(self, svar: Sequence[str], modell="inspelad"):
        self._svar = list(svar)
        self.modell = modell
        self.stalda: List[str] = []

    def fraga(self, prompt: str) -> Svar:
        self.stalda.append(prompt)
        if not self._svar:
            # Fail-closed. En inspelning som tar slut ar ett provfel, inte ett
            # tyst tomt varv - annars matte provet nagot annat an det trodde.
            raise Modellfel("inspelningen tog slut efter %d fragor"
                            % len(self.stalda))
        return Svar(text=self._svar.pop(0), modell=self.modell)


def standardklient(modell="sonnet") -> Optional[Modellklient]:
    """En riktig klient om maskinen har en, annars None.

    Returnerar medvetet None i stallet for en attrapp: en anropare som far en
    attrapp tror att den mater en modell.
    """
    k = ClaudeCLI(modell=modell)
    return k if k.tillganglig() else None
