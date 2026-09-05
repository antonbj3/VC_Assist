# -*- coding: utf-8 -*-
"""Modellprofilen: hela ytan tjansten kanner av en modell.

23_llm_granssnitt.md: "Profilen ar DATA, lases vid start och loggas per tur."
Har ar den ytan sluten och mekanisk, och varje falt bar tre saker:

    vad faltet betyder
    vad det anvands till (vilken mekanism som slutar fungera utan det)
    vad som hander om det saknas

Det tredje ar det som gor kontraktet uttommande. Ett falt utan ett bestamt
ode ar ett falt nagon far gissa om, och gissningen blir ett standardvarde -
alltsa nagon annans fonster som var budget.

TRE SVARSFORMER, ALDRIG FLER (36_versioner.md, upprepad i 23):

    formagan finns   -> kor
    formagan saknas  -> kasta, med formagans NAMN i felet
    formagan ar okand -> behandlas som saknad

Darfor ar varje deklarerat falt obligatoriskt, och varde None eller texten
"okand"/"okant" raknas som saknat. Det ar inte stranghet for dess egen skull:
en profil dar `kontext_tokens` fick ett standardvarde skulle rakna hela
budgeten pa ett fonster ingen har matt.

VAD SOM INTE STAR HAR: nagon leverantors namn, nagon modells namn, nagon
url, nagon nyckel. L1 i 23_llm_granssnitt.md, och det provas mekaniskt.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from .fel import Profilfel

# Vardena som raknas som "okant" och alltsa som saknat.
OKANDA = (None, "", "okand", "okant", "unknown")

DIALEKTER = ("kanonisk", "namngiven_funktion", "verktygsblock")
SYSTEMFALT = ("eget", "forsta_meddelandet")
RAKNARSORTER = ("exakt", "uppskattad")


@dataclass(frozen=True)
class Falt:
    """Ett falt i profilen, med sitt ode nar det saknas."""

    namn: str
    typ: str
    anvands_till: str
    utan_det: str
    tillatna: Tuple[Any, ...] = ()


# Den slutna listan. Ordningen ar 23_llm_granssnitt.md:s egen tabell, med tre
# tillagg sist som specen namner i lopande text men inte i tabellen.
FALT = (
    Falt("id", "str", "loggen och reproducerbarhetsraden (95_testprotokoll.md)",
         "en matning gar inte att knyta till en modell, och da ar den ingen "
         "matning"),
    Falt("kontext_tokens", "int", "hela budgeten i 25_kontextbudget.md",
         "budgeten skulle rakna pa ett fonster ingen matt; overskridandet "
         "upptacks da av motparten"),
    Falt("svar_tokens_max", "int", "taket for ett svar",
         "svarsmarginalen gar inte att halla, och ett svar som klipps mitt i "
         "en mening ar en avhuggen rapport"),
    Falt("verktygsdialekt", "enum", "vilken oversattning A1 gor",
         "verktygen kan inte lamnas till modellen alls", DIALEKTER),
    Falt("systemfalt", "enum", "var systemprompten hamnar",
         "systemprompten kan hamna i ett falt motparten ignorerar, och da ar "
         "B2 tyst utan att nagon ser det", SYSTEMFALT),
    Falt("parallella_verktygsanrop", "bool",
         "om flera anrop kan komma i en runda",
         "loopen vet inte om den ska rakna en runda eller flera"),
    Falt("strommande", "bool", "A5 i 23_llm_granssnitt.md",
         "operatorens flode har ingen framstegssignal fran modellen; "
         "TYSTNADSTAK i 24_samtalsloopen.md kan da bara peka pa hela anropet"),
    Falt("tokenraknare", "enum", "om budgeten har en kand marginal",
         "budgetens marginal ar okand, och en okand marginal ar ingen "
         "marginal", RAKNARSORTER),
    Falt("seed", "bool", "om en korning gar att upprepa",
         "korningen ar inte upprepbar och talen far inte jamforas mellan "
         "korningar"),
    # --- tillagg: specen namner dem i text, inte i tabellen ---------------
    Falt("verktygsanrop", "bool", "A1-A3: att modellen kan anropa verktyg alls",
         "tjansten kan inte kora: en modell utan verktygsanrop kan inte styra "
         "det har systemet, och att tolka fritext till anrop vore precis den "
         "tysta nedgradering 36_versioner.md forbjuder"),
    Falt("temperatur_noll", "bool", "A6: deterministisk installning",
         "matvarden ur turen ar icke-repeterbara och ska markas sa"),
    Falt("svarsmarginal_andel", "float",
         "hur stor del av fonstret som halls undan for modellens svar",
         "marginalen blir en rest i stallet for ett krav, och en rest ats upp"),
)

FALTNAMN = tuple(f.namn for f in FALT)
_FALT = {f.namn: f for f in FALT}

# Minsta svarsmarginal som andel av kontext_tokens.
# Harkomst: 25_kontextbudget.md avsnitt 1 - summan av taken ar 86 %, och "de
# aterstaende 14 % ar svarsmarginal och far aldrig atas upp".
MINSTA_SVARSMARGINAL = 0.14   # 25_kontextbudget.md avsnitt 1


def _saknas(varde) -> bool:
    if varde is None:
        return True
    if isinstance(varde, str) and varde.strip().lower() in OKANDA:
        return True
    return False


@dataclass(frozen=True)
class Profil:
    """En last profil. Oforanderlig: en profil som andras mitt i en tur
    skulle gora turens budgetrapport oforklarlig."""

    id: str
    kontext_tokens: int
    svar_tokens_max: int
    verktygsdialekt: str
    systemfalt: str
    parallella_verktygsanrop: bool
    strommande: bool
    tokenraknare: str
    seed: bool
    verktygsanrop: bool
    temperatur_noll: bool
    svarsmarginal_andel: float
    anmarkningar: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def exakt_raknare(self) -> bool:
        return self.tokenraknare == "exakt"

    @property
    def svarsmarginal_tokens(self) -> int:
        return int(self.kontext_tokens * self.svarsmarginal_andel)

    @property
    def budget_tokens(self) -> int:
        """Det som far anvandas till begaran. Svarsmarginalen ar undantagen."""
        return self.kontext_tokens - self.svarsmarginal_tokens

    def rad(self) -> str:
        return ("profil %s: %d tokens fonster, %d till begaran, %d till svaret,"
                " raknare %s%s"
                % (self.id, self.kontext_tokens, self.budget_tokens,
                   self.svarsmarginal_tokens, self.tokenraknare,
                   (", " + ", ".join(self.anmarkningar))
                   if self.anmarkningar else ""))


def _granska(d: Dict[str, Any]):
    problem = []
    okanda = [n for n in sorted(d) if n not in _FALT]
    for n in okanda:
        problem.append(
            "okant falt %r; profilens yta ar sluten och ett falt tjansten "
            "inte kanner skulle tyst ignoreras" % n)
    for f in FALT:
        if f.namn not in d or _saknas(d.get(f.namn)):
            problem.append(
                "%s saknas (eller ar okant, vilket raknas som saknat). Det "
                "anvands till: %s. Utan det: %s"
                % (f.namn, f.anvands_till, f.utan_det))
            continue
        v = d[f.namn]
        if f.typ == "int":
            if isinstance(v, bool) or not isinstance(v, int):
                problem.append("%s ska vara ett heltal, inte %s"
                               % (f.namn, type(v).__name__))
            elif v < 1:
                problem.append("%s ar %r; ett fonster mindre an 1 token ar "
                               "inget fonster" % (f.namn, v))
        elif f.typ == "float":
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                problem.append("%s ska vara ett tal, inte %s"
                               % (f.namn, type(v).__name__))
        elif f.typ == "bool":
            if not isinstance(v, bool):
                problem.append(
                    "%s ska vara true eller false, inte %r. Ett annat varde "
                    "ar okant, och okant behandlas som saknat"
                    % (f.namn, v))
        elif f.typ == "enum":
            if v not in f.tillatna:
                problem.append("%s ar %r; tillatna varden ar %s"
                               % (f.namn, v, ", ".join(map(str, f.tillatna))))
        elif f.typ == "str":
            if not isinstance(v, str):
                problem.append("%s ska vara text, inte %s"
                               % (f.namn, type(v).__name__))
    return problem


def las(d: Dict[str, Any]) -> Profil:
    """Laser en profil ur data. Kastar Profilfel med HELA problemlistan.

    Kastar ocksa nar profilen ar formellt riktig men internt motsager sig:
    en svarsmarginal under golvet eller ett svarstak som inte far plats i
    marginalen ar en marginal som redan ar uppaten.
    """
    if not isinstance(d, dict):
        raise Profilfel("<ingen>", ["profilen ar %s, inte data"
                                    % type(d).__name__])
    problem = _granska(d)
    if problem:
        raise Profilfel(d.get("id", "<utan id>"), problem)

    id_ = d["id"]
    kontext = d["kontext_tokens"]
    andel = float(d["svarsmarginal_andel"])
    if andel < MINSTA_SVARSMARGINAL:
        problem.append(
            "svarsmarginal_andel ar %.3f, under golvet %.2f "
            "(25_kontextbudget.md avsnitt 1). En marginal under golvet ar "
            "redan uppaten" % (andel, MINSTA_SVARSMARGINAL))
    if andel >= 1.0:
        problem.append("svarsmarginal_andel ar %.3f; da finns inget kvar att "
                       "skicka" % andel)
    marginal = int(kontext * andel)
    if d["svar_tokens_max"] > marginal and not problem:
        problem.append(
            "svar_tokens_max ar %d men marginalen ar %d tokens (%.0f %% av "
            "%d). Ett svarstak over marginalen betyder att svaret kan klippas "
            "av fonstret, och en avhuggen rapport ar aldrig ett godkannande"
            % (d["svar_tokens_max"], marginal, 100.0 * andel, kontext))
    if not d["verktygsanrop"]:
        problem.append(
            "verktygsanrop ar false. Formagan som saknas heter "
            "VERKTYGSANROP (A1-A3). Tjansten kor inte utan den, och tolkar "
            "aldrig fritext till anrop i stallet")
    if problem:
        raise Profilfel(id_, problem)

    anm = []
    if not d["strommande"]:
        anm.append("icke-strommande: ingen framstegssignal fran modellen (A5)")
    if not d["temperatur_noll"]:
        anm.append("icke-repeterbara: temperaturen ar inte noll (A6)")
    if not d["seed"]:
        anm.append("icke-repeterbara: modellen tar ingen seed (A6)")
    if d["tokenraknare"] != "exakt":
        anm.append("uppskattad tokenraknare: budgeten laggs med marginal")
    return Profil(
        id=id_, kontext_tokens=kontext, svar_tokens_max=d["svar_tokens_max"],
        verktygsdialekt=d["verktygsdialekt"], systemfalt=d["systemfalt"],
        parallella_verktygsanrop=d["parallella_verktygsanrop"],
        strommande=d["strommande"], tokenraknare=d["tokenraknare"],
        seed=d["seed"], verktygsanrop=d["verktygsanrop"],
        temperatur_noll=d["temperatur_noll"], svarsmarginal_andel=andel,
        anmarkningar=tuple(anm))


def provprofil(**andringar) -> Profil:
    """En fullstandig profil for prov och for banken.

    Star har och inte i proven sa att en NY obligatorisk falt-rad faller pa
    ETT stalle i stallet for i tjugo prov - och sa att den som lagger till ett
    falt maste bestamma vad provprofilen sager om det.

    Fonstret 128 000 tokens ar 23_llm_granssnitt.md:s eget rakneexempel.
    """
    grund = {
        "id": "prov",
        "kontext_tokens": 128000,      # 23_llm_granssnitt.md, rakneexemplet
        "svar_tokens_max": 8000,       # 23_llm_granssnitt.md, under marginalen
        "verktygsdialekt": "kanonisk",
        "systemfalt": "eget",
        "parallella_verktygsanrop": False,
        "strommande": True,
        "tokenraknare": "uppskattad",
        "seed": True,
        "verktygsanrop": True,
        "temperatur_noll": True,
        "svarsmarginal_andel": 0.14,   # 25_kontextbudget.md avsnitt 1
    }
    grund.update(andringar)
    return las(grund)
