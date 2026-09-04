# -*- coding: utf-8 -*-
"""Sammansattningen: hur en systemprompt byggs ur korpusen, och hur den kapas.

Tva beslut ligger har, och bada ar utskrivna i stallet for underforstadda.

**1. Vad som kapas, och i vilken ordning.**
Kapordningen ar korpusens prioritet: hogst tal kapas forst. Prioriteten ar
DATA (varje block bar sitt eget prioritet_skal), men golvet ar KOD: blocken i
OKAPBARA kapas aldrig, hur trang budgeten an ar.

Rangordningen foljer en enda fraga: VAD FANGAS INTE AV NAGON ANNAN MEKANISM?

  1 sakerhetsgransen  okapbar. I15 ar inte forhandlingsbar. Grinden avvisar
                      anropet anda, men en modell som inte vet varfor gar pa
                      samma vagg varv efter varv tills loopens tak slar, och
                      operatoren far ett stopp i stallet for ett svar.
  2 arlighet          okapbar. Harnessen vet vad som INTE stammer, aldrig vad
                      som ar sant. En modell utan arlighetsreglerna skriver
                      text som omskrivningsslingan bara kan avvisa, aldrig
                      laga.
  3 systemroll        okapbar, och avsiktligt bara tre regler lang. Utan
                      rollen gissar modellen bade verktygsvag och domsratt.
  4 matta_fallor      kapas sist av de kapbara. Kvaternionens ordning och
                      varldsmatrisens eftersslapning ger TAL SOM SER RIMLIGA
                      UT; ingen grind i kedjan fangar dem.
  5 verktygsbruk      varje regel har en grind bakom sig. Tappas blocket
                      kostar det rundor och avvisningar, inte en tyst fel
                      scen.
  6 arbetsordning     styr effektiviteten i turen, inte sanningshalten.
  7 domankunskap_vc   kapas forst: allt i blocket gar att sla upp med
                      kunskapsverktyget mitt i turen.

**2. Vad budgeten mats i.**
TECKEN, inte tokens. Ingen leverantors tokenisering ar tillganglig i
standardbiblioteket, och att lasa in en ar att lasa in en leverantor. Tecken
ar deterministiska och lika for alla adaptrar. Den som bara ett tokentak far
rakna om det med budget_ur_tokentak(), som ar ANTAGEN och markt som sadan.

Fail-closed: far inte ens de okapbara blocken plats kastas Budgetfel. En
prompt dar sakerhetsgransen tystnat far aldrig skickas.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from .fel import Budgetfel
from .instruktioner import Korpus

# Block som aldrig kapas. Skalen star i modulens docstring, ett per block.
# Golvet ligger i KOD och inte bara i data: en korpus som redigeras fel ska
# inte kunna tysta sakerhetsgransen.
OKAPBARA = frozenset(("sakerhetsgransen", "arlighet", "systemroll"))

# Inledningen. Kort med flit: varje tecken har konkurrerar med en regel.
HUVUD = (
    "Du arbetar under reglerna nedan. De ar numrerade och far citeras med sitt "
    "id.\nEn regel gar fore din egen bedomning. Star tva regler mot varandra "
    "vinner den som star hogst upp.\nRegler markta med id ur "
    "sakerhetsgransen och arligheten tvingas dessutom mekaniskt: bryter du "
    "mot dem avvisas anropet eller svaret, och du far skriva om det."
)

# ANTAGET, inte matt: tecken per token for svensk text i en modern BPE-
# tokenisering. Talet ar valt LAGT med flit - underskattas tecken per token
# blir budgeten for liten och prompten kapas i onodan, vilket ar det
# ofarliga felet. Overskattas den skickas en prompt som inte far plats, och
# det ar det farliga. Ersatts av en matning nar en tokenisering finns pa
# tjanstesidan.
TECKEN_PER_TOKEN = 3.0

# Standardbudget i tecken. Ur 45_verktyg.md: under ungefar hundra verktyg
# skickas alla, och verktygsschemat tar da storst plats i turen. 12000 tecken
# racker for hela korpusen 2026-09-04 (matt av
# test_hela_korpusen_far_plats_i_standardbudgeten) med marginal for att
# korpusen vaxer. Talet ar en STANDARD, inte en grans: den som kanner sin
# modells fonster skickar sitt eget.
STANDARDBUDGET = 12000


def budget_ur_tokentak(tokentak: int) -> int:
    """Tokentak -> teckenbudget. ANTAGET, se TECKEN_PER_TOKEN."""
    if tokentak < 1:
        raise Budgetfel("tokentaket %r ar inte ett tak" % (tokentak,))
    return int(tokentak * TECKEN_PER_TOKEN)


@dataclass(frozen=True)
class Systemprompt:
    """En byggd prompt, plus exakt vad som kapades ur den."""

    text: str
    budget: int
    med_regler: Tuple[str, ...]
    kapade_regler: Tuple[str, ...]
    kapade_block: Tuple[str, ...]
    fingeravtryck: str

    @property
    def tecken(self) -> int:
        return len(self.text)

    @property
    def hel(self) -> bool:
        return not self.kapade_regler

    def sammanfattning(self) -> str:
        if self.hel:
            return ("systemprompt %s: %d tecken av %d, hel"
                    % (self.fingeravtryck, self.tecken, self.budget))
        return ("systemprompt %s: %d tecken av %d, %d regler kapade (%s)"
                % (self.fingeravtryck, self.tecken, self.budget,
                   len(self.kapade_regler), ", ".join(self.kapade_regler)))


def _rendera(korpus: Korpus, behall: Dict[str, int], huvud: str) -> str:
    delar = [huvud]
    for block in korpus.block:
        antal = behall[block.id]
        if antal <= 0:
            continue
        delar.append(block.text(antal))
    return "\n\n".join(delar) + "\n"


def _kapordning(korpus: Korpus) -> List[Tuple[str, int, str]]:
    """De kapbara enheterna, i den ordning de offras.

    En enhet ar (block-id, regelindex, regel-id). Lagst prioritet forst, och
    inom ett block den SISTA regeln forst: reglernas ordning i filen ar
    viktighetsordning.
    """
    enheter: List[Tuple[str, int, str]] = []
    for block in sorted(korpus.block, key=lambda b: -b.prioritet):
        if block.id in OKAPBARA:
            continue
        for i in range(len(block.regler) - 1, -1, -1):
            enheter.append((block.id, i, block.regler[i].id))
    return enheter


def granska_golv(korpus: Korpus) -> List[str]:
    """Provar att korpusens kapbar-flaggor stammer med kodens golv.

    Ett block som DATAN sager ar okapbart men som koden inte skyddar skulle
    se sakert ut och kapas anda. Det ar den farliga riktningen, och den
    faller har. Motsatsen (koden skyddar mer an datan lovar) ar ofarlig men
    anmarks anda, sa att de tva aldrig glider isar.
    """
    problem = []
    for block in korpus.block:
        i_golvet = block.id in OKAPBARA
        if not block.kapbar and not i_golvet:
            problem.append(
                "%s ar markt kapbar=false i korpusen men star inte i "
                "sammansattning.OKAPBARA; koden skulle kapa det anda"
                % block.id)
        if block.kapbar and i_golvet:
            problem.append(
                "%s star i sammansattning.OKAPBARA men ar markt kapbar=true "
                "i korpusen; en av de tva ar fel" % block.id)
    return problem


def bygg_systemprompt(korpus: Korpus, budget: int = STANDARDBUDGET,
                      huvud: str = HUVUD) -> Systemprompt:
    """Bygger prompten for en tur och kapar den om den inte far plats.

    Kapar hela regler, aldrig halva meningar: en avhuggen regel ar en regel
    som betyder nagot annat an den skulle.
    """
    golvproblem = granska_golv(korpus)
    if golvproblem:
        raise Budgetfel("korpusen och kodens kapgolv star mot varandra: %s"
                        % "; ".join(golvproblem))
    if budget < 1:
        raise Budgetfel("budgeten %r ar ingen budget" % (budget,))

    behall = {b.id: len(b.regler) for b in korpus.block}
    kapade: List[str] = []
    text = _rendera(korpus, behall, huvud)
    for block_id, index, regel_id in _kapordning(korpus):
        if len(text) <= budget:
            break
        behall[block_id] = index
        kapade.append(regel_id)
        text = _rendera(korpus, behall, huvud)

    if len(text) > budget:
        raise Budgetfel(
            "de okapbara blocken (%s) ar %d tecken och budgeten ar %d. "
            "Hellre inget svar an ett svar dar sakerhetsgransen tystnat (I3)"
            % (", ".join(sorted(OKAPBARA)), len(text), budget))

    kapade_block = tuple(b.id for b in korpus.block if behall[b.id] <= 0)
    med = tuple(r.id for b in korpus.block for r in b.regler[:behall[b.id]])
    return Systemprompt(text=text, budget=budget, med_regler=med,
                        kapade_regler=tuple(kapade),
                        kapade_block=kapade_block,
                        fingeravtryck=korpus.fingeravtryck())


def regelrad(korpus: Korpus, regel_id: str) -> str:
    """Regeln som en rad att peka pa i ett omskrivningskrav.

    Omskrivningen ska namna regeln som brots, inte bara saga att nagot ar
    fel: en modell som inte far veta vilken regel den brot rattar gissningsvis.
    """
    regel = korpus.regel_med_id(regel_id)
    return "%s: %s" % (regel.id, regel.text)
