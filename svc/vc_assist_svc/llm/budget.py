# -*- coding: utf-8 -*-
"""Kontextbudgeten: vad som far plats, vad som gar bort, och i vilken ordning.

TVA GRUNDREGLER, OCH BADA AR MEKANISKA
--------------------------------------
1. **Rakna fore, aldrig fanga efter.** Budgeten halls fore anropet genom att
   rakna. Ett overskridande som upptacks av motparten ar samma felklass som
   ett tyst syntaxfel i VC (M-09): systemet sag ut att gora nagot och gjorde
   ingenting.
2. **Ingen trimning ar tyst.** Varje bortprioritering ger exakt en
   TRIMMAD-handelse med vilken post som trimmades och hur mycket. En trimning
   som ingen ser ar en andrad fraga som grinden inte vet om.

Regel 2 ar provbar at BADA hallen har: `granska()` jamfor delarna fore och
efter och faller bade pa en trimning utan handelse OCH pa en handelse utan
trimning. En bokforing som bara provas at ena hallet ar oprovad.

ORDNINGEN AR SLUTEN OCH NUMRERAD
--------------------------------
Trimningen gar uppifran och ned tills budgeten haller. Stegen 1-6 och 8 star i
25_kontextbudget.md avsnitt 2. Steg 7 ar ETT TILLAGG, och det finns darfor att
specen inte svarade pa fragan "vad hander nar ETT verktygssvar ar storre an
hela sin post?". Den fragan stod som oppen fraga 3 i samma dokument, och ett
lager som inte svarar pa den gor i praktiken det tystaste valet: skickar anda,
och later motparten kapa. Steg 7 kapar i stallet PA POSTER, hogljutt, och
aldrig pa tecken (kapning.py).

VAD SOM ALDRIG TRIMMAS
----------------------
Skyddade delar rors inte, hur trang budgeten an ar. Racker inte budgeten till
det skyddade kastas Budgetfel - ett fel, aldrig en tyst trimning (S1). Det ar
den trasiga fixtur som SKA falla.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import matt
from .fel import Budgetfel
from .profil import Profil

# ---------------------------------------------------------------------------
# Posterna
# ---------------------------------------------------------------------------

P_SYSTEMPROMPT = "systemprompt"
P_AVSTANGDA = "avstangda"
P_SCHEMA = "schema"
P_UPPGIFT = "uppgift"
P_SIGNALKARTA = "signalkarta"
P_SCEN = "scen"
P_OGAT = "ogat"
P_RESULTAT = "resultat"
P_HUVUDBOK = "huvudbok"


@dataclass(frozen=True)
class Post:
    nr: int
    id: str
    vad: str
    andel: float
    far_trimmas: bool
    harkomst: str


# 25_kontextbudget.md avsnitt 1, tabellen. Andelarna galler profilens
# kontext_tokens, oavsett hur stor den ar.
POSTER = (
    Post(1, P_SYSTEMPROMPT, "systemprompt B1-B3, B5-B7", 0.05, False,
         "PRELIMINAR, M-29: ingen tokenrakning over verkliga turer finns"),
    Post(2, P_AVSTANGDA, "B4, avstangda verktyg med skal", 0.01, True,
         "PRELIMINAR, M-29"),
    Post(3, P_SCHEMA, "verktygsschemat", 0.10, True,
         "MATT 2026-09-05: 122 registrerade verktyg ger 98 080 byte "
         "OpenAI-schema, medel 803 byte (M-102)"),
    Post(4, P_UPPGIFT, "uppgiften och planens aktuella steg", 0.05, False,
         "PRELIMINAR, M-29"),
    Post(5, P_SIGNALKARTA, "signalkartan och deklarationsdelen", 0.10, False,
         "MATT: bankens storsta signalkarta ar 13 signaler (M-45)"),
    Post(6, P_SCEN, "scenvyn", 0.15, True,
         "MATT: bankens storsta scen ar 9 komponenter (M-45)"),
    Post(7, P_OGAT, "ogats dom och rader", 0.10, True,
         "PRELIMINAR, M-29; EDGE och MINDIST vaxer med forloppet"),
    Post(8, P_RESULTAT, "de senaste K verktygsresultaten", 0.25, True,
         "PRELIMINAR, M-29"),
    Post(9, P_HUVUDBOK, "huvudboken over aldre anrop", 0.05, True,
         "PRELIMINAR, M-29"),
)
_POST = {p.id: p for p in POSTER}

# Hur manga verktygsanrop som behaller sitt FULLA resultat i en tur.
# PRELIMINART, matning M-29. Motivet ar RUNDOR_MAX = 10 med tva rundors
# marginal: i en NORMAL tur kastas alltsa ingenting alls.
K_HELA_RESULTAT = 8         # PRELIMINAR, satts av M-29

# Huvudbokens fem senaste rader trimmas aldrig.
# Harkomst: 25_kontextbudget.md avsnitt 2, steg 1.
HUVUDBOK_MINST = 5          # 25_kontextbudget.md avsnitt 2, steg 1


def summa_andelar() -> float:
    return sum(p.andel for p in POSTER)


# ---------------------------------------------------------------------------
# Delarna
# ---------------------------------------------------------------------------

@dataclass
class Del:
    """En bit innehall som hor till en post.

    `skyddad` ar KOD och inte data: en del som ar markt skyddad kan inte
    trimmas av nagot steg, aven om steget skulle rakna fel.

    `trimmare` far krympa delen till ett mal i byte och ska returnera
    (ny_text, vad_som_gick_bort) eller None nar den inte kan krympa mer.
    """

    post: str
    id: str
    text: str
    skyddad: bool = False
    trimmare: Optional[Callable[[int], Optional[Tuple[str, str]]]] = None
    ersattning: Optional[str] = None
    data: Any = None

    def tokens(self, exakt: bool = False) -> int:
        return matt.med_marginal(matt.tokens(self.text), exakt)

    def byte(self) -> int:
        return len(self.text.encode("utf-8"))


@dataclass(frozen=True)
class Trimmad:
    """En bortprioritering. Exakt en per trimning, aldrig noll."""

    steg: int
    post: str
    del_id: str
    fore_tokens: int
    efter_tokens: int
    vad: str

    def rad(self) -> str:
        return ("TRIMMAD steg %d post %s del %s: %d -> %d tokens, %s"
                % (self.steg, self.post, self.del_id, self.fore_tokens,
                   self.efter_tokens, self.vad))


@dataclass
class Plan:
    """Det som ska skickas, plus hela bokforingen over vad som togs bort."""

    profil: Profil
    delar: List[Del]
    handelser: List[Trimmad] = field(default_factory=list)
    delad: bool = False
    skal_for_delning: str = ""

    def tokens(self) -> int:
        exakt = self.profil.exakt_raknare
        return sum(d.tokens(exakt) for d in self.delar)

    def per_post(self) -> Dict[str, int]:
        exakt = self.profil.exakt_raknare
        ut: Dict[str, int] = {}
        for d in self.delar:
            ut[d.post] = ut.get(d.post, 0) + d.tokens(exakt)
        return ut

    def trimmade_per_post(self) -> Dict[str, int]:
        ut: Dict[str, int] = {}
        for h in self.handelser:
            ut[h.post] = ut.get(h.post, 0) + 1
        return ut

    def over_taket(self) -> List[str]:
        """Poster som ligger over sitt eget tak. Det ar det som BINDER."""
        ut = []
        per = self.per_post()
        for p in POSTER:
            tak = int(self.profil.kontext_tokens * p.andel)
            if per.get(p.id, 0) > tak:
                ut.append("%s: %d tokens over taket %d (%.0f %%)"
                          % (p.id, per[p.id], tak, 100 * p.andel))
        return ut

    def rapport(self) -> str:
        """Budgetrapporten per tur. Ett lager utan den gar inte att stalla in."""
        rader = ["BUDGET profil=%s fonster=%d begaran=%d tokens"
                 % (self.profil.id, self.profil.kontext_tokens, self.tokens())]
        per = self.per_post()
        trim = self.trimmade_per_post()
        for p in POSTER:
            rader.append("  post %d %-13s %6d tokens  tak %6d  trimmningar %d"
                         % (p.nr, p.id, per.get(p.id, 0),
                            int(self.profil.kontext_tokens * p.andel),
                            trim.get(p.id, 0)))
        rader.append("  marginal for svaret            %6d tokens"
                     % self.profil.svarsmarginal_tokens)
        for rad in self.over_taket():
            rader.append("  OVER TAKET %s" % rad)
        for h in self.handelser:
            rader.append("  " + h.rad())
        if self.delad:
            rader.append("  TUREN DELAS: %s" % self.skal_for_delning)
        return "\n".join(rader)


# ---------------------------------------------------------------------------
# Trimstegen
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Steg:
    nr: int
    post: str
    vad: str
    ersatts_av: str


TRIMSTEG = (
    Steg(1, P_HUVUDBOK, "huvudbokens aldsta rader, men aldrig de fem senaste",
         "inget"),
    Steg(2, P_RESULTAT, "det aldsta HELA verktygsresultatet",
         "en huvudboksrad: anropet, utfallet och koden"),
    Steg(3, P_AVSTANGDA, "B4, listan over avstangda verktyg",
         "N verktyg avstangda; fraga om nagot saknas"),
    Steg(4, P_OGAT, "ogats rader i sektioner dar VARJE rad ar utan fynd",
         "en rad UTANFOR ogats block"),
    Steg(5, P_SCEN, "scenvyn kokas harder",
         "planens komponenter hela, resten som rakningar per kategori"),
    Steg(6, P_SCHEMA, "verktygsschemat", "semantiskt urval"),
    Steg(7, P_RESULTAT,
         "det kvarvarande verktygsresultatet kapas PA POSTER",
         "samma svar med avkortad=true och en rad om hur mycket"),
    Steg(8, "", "racker det fortfarande inte delas turen", "tva turer"),
)


class Budget(object):
    """Budgeten for en profil. Ren rakning, ingen leverantor, inget natverk."""

    def __init__(self, profil: Profil):
        self.profil = profil

    def tak_tokens(self, post_id: str) -> int:
        return int(self.profil.kontext_tokens * _POST[post_id].andel)

    def tak_byte(self, post_id: str) -> int:
        """Postens tak i byte, genom det HOGSTA av de tva antagandena.

        Fail-closed: rakna om tokens till byte med det antagande som ger
        FARRE byte, sa att taket aldrig blir for generost.
        """
        tokens = self.tak_tokens(post_id)
        return int(min(tokens * matt.BYTE_PER_TOKEN,
                       tokens * matt.TECKEN_PER_TOKEN))

    # -- planeringen -----------------------------------------------------

    def planera(self, delar: Sequence[Del]) -> Plan:
        """Trimmar tills budgeten haller, i den slutna ordningen.

        Kastar Budgetfel nar inte ens det skyddade far plats. Det ar avsikten:
        hellre inget anrop an ett anrop dar signalkartan eller ogats dom
        tystnat.
        """
        plan = Plan(profil=self.profil, delar=[_kopia(d) for d in delar])
        exakt = self.profil.exakt_raknare
        budget = self.profil.budget_tokens

        skyddat = sum(d.tokens(exakt) for d in plan.delar
                      if d.skyddad or not _POST[d.post].far_trimmas)
        if skyddat > budget:
            raise Budgetfel(
                "det skyddade ar %d tokens och budgeten %d (fonster %d minus "
                "svarsmarginal %d). Poster som aldrig far trimmas: %s. "
                "Hellre inget anrop an ett anrop dar en av dem tystnat (S1)"
                % (skyddat, budget, self.profil.kontext_tokens,
                   self.profil.svarsmarginal_tokens,
                   ", ".join(sorted(set(d.post for d in plan.delar
                                        if d.skyddad
                                        or not _POST[d.post].far_trimmas)))))

        for steg in TRIMSTEG:
            if plan.tokens() <= budget and not self._binder(plan):
                break
            if steg.nr == 1:
                self._trimma_huvudbok(plan, budget)
            elif steg.nr == 2:
                self._slapp_aldsta_resultat(plan, budget)
            elif steg.nr == 3:
                self._ersatt(plan, steg, P_AVSTANGDA)
            elif steg.nr in (4, 5, 6, 7):
                self._krymp(plan, steg, budget)
            elif steg.nr == 8:
                if plan.tokens() > budget:
                    plan.delad = True
                    plan.skal_for_delning = (
                        "begaran ar %d tokens och budgeten %d efter att varje "
                        "trimsteg korts. Turen delas hellre an att nagot ur "
                        "listan 'aldrig bort' offras"
                        % (plan.tokens(), budget))
        return plan

    def _binder(self, plan: Plan) -> bool:
        """Ligger nagon TRIMBAR post over sitt eget tak?"""
        per = plan.per_post()
        for p in POSTER:
            if not p.far_trimmas:
                continue
            if per.get(p.id, 0) > self.tak_tokens(p.id):
                return True
        return False

    def _behov(self, plan: Plan, budget: int, post: str) -> int:
        """Hur manga tokens som maste bort ur den har posten."""
        totalt = max(0, plan.tokens() - budget)
        per = plan.per_post().get(post, 0)
        over_tak = max(0, per - self.tak_tokens(post))
        return max(totalt, over_tak)

    def _trimma_huvudbok(self, plan: Plan, budget: int) -> None:
        rader = [d for d in plan.delar if d.post == P_HUVUDBOK]
        behov = self._behov(plan, budget, P_HUVUDBOK)
        if behov <= 0:
            return
        exakt = self.profil.exakt_raknare
        # De fem senaste star kvar, hur trang budgeten an ar.
        kandidater = rader[:-HUVUDBOK_MINST] if len(rader) > HUVUDBOK_MINST \
            else []
        for d in kandidater:
            if plan.tokens() <= budget and not self._binder(plan):
                return
            fore = d.tokens(exakt)
            plan.delar.remove(d)
            plan.handelser.append(Trimmad(
                steg=1, post=P_HUVUDBOK, del_id=d.id, fore_tokens=fore,
                efter_tokens=0,
                vad="aldsta huvudboksraden slapptes; de %d senaste star kvar"
                    % HUVUDBOK_MINST))

    def _slapp_aldsta_resultat(self, plan: Plan, budget: int) -> None:
        exakt = self.profil.exakt_raknare
        while True:
            resultat = [d for d in plan.delar if d.post == P_RESULTAT]
            if len(resultat) <= 1:
                return
            if plan.tokens() <= budget and not self._binder(plan):
                return
            d = resultat[0]
            fore = d.tokens(exakt)
            i = plan.delar.index(d)
            if d.ersattning:
                ny = Del(post=P_HUVUDBOK, id=d.id + ":huvudbok",
                         text=d.ersattning)
                plan.delar[i] = ny
                efter = ny.tokens(exakt)
            else:
                plan.delar.pop(i)
                efter = 0
            plan.handelser.append(Trimmad(
                steg=2, post=P_RESULTAT, del_id=d.id, fore_tokens=fore,
                efter_tokens=efter,
                vad="aldsta hela verktygsresultatet ersattes av sin "
                    "huvudboksrad"))

    def _ersatt(self, plan: Plan, steg: Steg, post: str) -> None:
        exakt = self.profil.exakt_raknare
        for i, d in enumerate(plan.delar):
            if d.post != post or d.skyddad:
                continue
            ny_text = d.ersattning if d.ersattning is not None else ""
            if ny_text == d.text:
                continue
            fore = d.tokens(exakt)
            ny = Del(post=post, id=d.id, text=ny_text, data=d.data)
            plan.delar[i] = ny
            plan.handelser.append(Trimmad(
                steg=steg.nr, post=post, del_id=d.id, fore_tokens=fore,
                efter_tokens=ny.tokens(exakt), vad=steg.ersatts_av))

    def _krymp(self, plan: Plan, steg: Steg, budget: int) -> None:
        exakt = self.profil.exakt_raknare
        for i, d in enumerate(list(plan.delar)):
            if d.post != steg.post or d.skyddad or d.trimmare is None:
                continue
            if plan.tokens() <= budget and not self._binder(plan):
                return
            # Malet i byte: postens eget tak, minus vad postens ovriga delar
            # tar. Aldrig mindre an noll.
            andra = sum(x.byte() for x in plan.delar
                        if x.post == steg.post and x is not d)
            mal = max(0, self.tak_byte(steg.post) - andra)
            overskott = max(0, plan.tokens() - budget)
            if overskott:
                mal = min(mal, max(0, d.byte() - int(overskott
                                                     * matt.BYTE_PER_TOKEN)))
            svar = d.trimmare(mal)
            if svar is None:
                continue
            ny_text, vad = svar
            if ny_text == d.text:
                continue
            fore = d.tokens(exakt)
            ny = Del(post=d.post, id=d.id, text=ny_text, skyddad=d.skyddad,
                     trimmare=None, ersattning=d.ersattning, data=d.data)
            plan.delar[i] = ny
            plan.handelser.append(Trimmad(
                steg=steg.nr, post=d.post, del_id=d.id, fore_tokens=fore,
                efter_tokens=ny.tokens(exakt), vad=vad))


def _kopia(d: Del) -> Del:
    return Del(post=d.post, id=d.id, text=d.text, skyddad=d.skyddad,
               trimmare=d.trimmare, ersattning=d.ersattning, data=d.data)


# ---------------------------------------------------------------------------
# Granskningen: bokforingen provas at BADA hallen
# ---------------------------------------------------------------------------

B1_TYST_TRIMNING = "B1_TYST_TRIMNING"
B2_HANDELSE_UTAN_TRIMNING = "B2_HANDELSE_UTAN_TRIMNING"
B3_SKYDDAD_TRIMMAD = "B3_SKYDDAD_TRIMMAD"
B4_OVER_BUDGET = "B4_OVER_BUDGET"
B5_ORDNING_BRUTEN = "B5_ORDNING_BRUTEN"


def granska(fore: Sequence[Del], plan: Plan) -> List[str]:
    """Faller pa varje skillnad mellan det som skickades och bokforingen."""
    ut: List[str] = []
    fore_id = dict((d.id, d) for d in fore)
    efter_id = dict((d.id, d) for d in plan.delar)
    berorda = set(h.del_id for h in plan.handelser)

    for id_, d in fore_id.items():
        e = efter_id.get(id_)
        andrad = e is None or e.text != d.text
        if andrad and id_ not in berorda:
            ut.append("%s: delen %s (post %s) andrades eller foll bort utan "
                      "en TRIMMAD-handelse" % (B1_TYST_TRIMNING, id_, d.post))
        if andrad and (d.skyddad or not _POST[d.post].far_trimmas):
            ut.append("%s: delen %s hor till posten %s som aldrig far trimmas"
                      % (B3_SKYDDAD_TRIMMAD, id_, d.post))
    for h in plan.handelser:
        d = fore_id.get(h.del_id)
        if d is None:
            ut.append("%s: handelsen pekar pa delen %s som inte fanns fore"
                      % (B2_HANDELSE_UTAN_TRIMNING, h.del_id))
            continue
        e = efter_id.get(h.del_id)
        if e is not None and e.text == d.text:
            ut.append("%s: handelsen sager att %s trimmades, men texten ar "
                      "oforandrad" % (B2_HANDELSE_UTAN_TRIMNING, h.del_id))
    nummer = [h.steg for h in plan.handelser]
    if nummer != sorted(nummer):
        ut.append("%s: TRIMMAD-handelserna kom i ordningen %s; trimningen gar "
                  "uppifran och ned i den slutna tabellen"
                  % (B5_ORDNING_BRUTEN, nummer))
    if plan.tokens() > plan.profil.budget_tokens and not plan.delad:
        ut.append("%s: begaran ar %d tokens och budgeten %d, och turen ar inte "
                  "markt som delad" % (B4_OVER_BUDGET, plan.tokens(),
                                       plan.profil.budget_tokens))
    return ut
