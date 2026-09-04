# -*- coding: utf-8 -*-
"""Baslinjen: en regelbaserad ST-generator utan språkmodell.

Fas 11 i `docs/spec/70_faser.md`. Talen står i
`docs/matningar/M-62_baslinjen.md`.

## Varför den finns

`docs/research/R-01_llm_st_och_softplc.md` slog fast att ingen har publicerat
vår loop, att ingen leverantör publicerar ett korrekthetstal, och att varje
akademiskt tal är kompileringsgrad på en annan uppgiftsmängd. Att ställa fas
9:s tal mot LLM4PLC:s 72 % vore ett kategorifel. Fas 9:s tal ska därför alltid
rapporteras som **par**: vårt mot en baslinje över samma bank och samma domare.

Den här modulen är baslinjen. Den skriver ST med mallar, mönster och en
stegkedja härledd ur signalkartan — ingen modell, ingen slump. Samma uppgift
ger alltid samma kod, byte för byte, och det provas mekaniskt.

## Den är byggd för att vara SVÅR att slå, inte lätt

En svag baslinje gör vårt tal meningslöst på ett annat sätt än ingen baslinje
alls: den ser ut att bevisa något. Baslinjen får därför:

* **mer** strukturerad indata än modellen — den läser `control.sequence` och
  `control.interlocks` som fält, medan modellen får samma innehåll som prosa,
* en färdig standardram för drift, larm, kvittens och tidsövervakning,
* en PackML-mall ur en publicerad standard,
* en morfologi som parar ihop kommandon och kvittenser ur hela bankens
  namnkonvention.

Att gynna baslinjen är det försiktiga valet för vårt EGET påstående: vinner
modellen ändå är vinsten verklig. Var baslinjen ger upp står i `Rapport` och
räknas i M-62 — det är den intressantaste delen av mätningen.

## Vad den ALDRIG läser

`facit_spar` i någon form: referenslösningen, punktkraven, invarianterna,
flankkraven, motbevisen. Den läser uppgiften, aldrig facit. Det provas
mekaniskt i `tests/enhet/test_baslinje.py`, liksom att ingen uppgifts-id
förekommer i den här källkoden: en generator som känner igen uppgiften mäter
ingenting.

beskriver: svc/vc_assist_svc/plc/baslinje/generator.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

from . import morfologi as Mo
from . import packml as Pm
from . import sprak as Sp

# ---- nivåerna ------------------------------------------------------------

NIVA_MAGER = "mager"    # bara signalkartan: en I/O-lista och ingenting mer
NIVA_PROSA = "prosa"    # kartan plus uppgiftstextens egna listor, ingen specfält
NIVA_SPEC = "spec"      # kartan plus den strukturerade uppgiftsspecen
NIVAER = (NIVA_MAGER, NIVA_PROSA, NIVA_SPEC)

# Variabelprefixet. Ett eget prefix så att en arbetsvariabel aldrig kan krocka
# med en tagg ur kartan; kartans taggar är stationsprefixade versaler.
PREFIX = "b"

# Standardtiden för en tidsövervakning när uppgiften inte anger någon. Talet är
# SATT och inte mätt, och det är med flit högt: en vakt som faller för tidigt
# stoppar linjen på normal drift, och det är ett lika allvarligt fel som en
# vakt som saknas (M-45, fönsterregeln). En generator som gissar en tid ska
# gissa åt det hållet som inte stoppar produktionen.
STANDARDVAKT_S = 30.0           # Satt av M-62.

# Hur många tecken en vaktstam måste dela med en kommentar för att räknas som
# samma don. Tre är kortaste ordstam som inte matchar halva ordlistan; värdet
# används bara när uppgiften INTE namnger vaktens signal.
MINSTA_STAM = 3                 # Satt av M-62.


class Baslinjefel(Exception):
    """Generatorn kan inte producera kod för den här specen."""


# ---- indata --------------------------------------------------------------

@dataclass(frozen=True)
class Spec:
    """Uppgiften som baslinjen ser den. Ingen facitdel finns i den här typen.

    `signaler` är I/O-listan på bankens form (`name`, `dir`, `type`,
    `comment`). `sekvens` och `forreglingar` är den strukturerade specen.
    `uppgiftstext` är prosan modellen får; baslinjen läser bara gränsvärden ur
    den.
    """

    signaler: Tuple[Dict[str, object], ...]
    sekvens: Tuple[str, ...] = ()
    forreglingar: Tuple[str, ...] = ()
    uppgiftstext: str = ""
    station: str = ""


# ---- utdata --------------------------------------------------------------

@dataclass
class Rapport:
    """Vad generatorn gjorde, och framför allt vad den INTE kunde göra.

    Varje lista här är en mätpunkt i M-62. En generator som inte redovisar sina
    hål ser ut att förstå allt, och då mäter bänken tystnaden.
    """

    niva: str = NIVA_SPEC
    mall: str = "stegkedja"
    olasta_rader: List[str] = field(default_factory=list)
    olasta_forreglingar: List[str] = field(default_factory=list)
    ramtackta: List[Tuple[str, str]] = field(default_factory=list)
    obundna_utgangar: List[str] = field(default_factory=list)
    ororda_ingangar: List[str] = field(default_factory=list)
    antaganden: List[str] = field(default_factory=list)
    steg: int = 0
    vakter: int = 0
    intervall: int = 0
    # Nämnarna. En lista över olästa rader utan sitt antal rader är ett tal
    # utan nämnare, och den regeln gäller generatorns egen redovisning också.
    rader_totalt: int = 0
    forreglingar_totalt: int = 0
    utgangar_totalt: int = 0
    ingangar_totalt: int = 0

    def text(self) -> str:
        rader = ["BASLINJE %s, mall %s, %d steg, %d vakter, %d intervall"
                 % (self.niva, self.mall, self.steg, self.vakter,
                    self.intervall)]
        for etikett, lista in (("olast sekvensrad", self.olasta_rader),
                               ("olast forregling", self.olasta_forreglingar),
                               ("obunden utgang", self.obundna_utgangar),
                               ("orord ingang", self.ororda_ingangar),
                               ("antagande", self.antaganden)):
            for x in lista:
                rader.append("  %-18s %s" % (etikett, x))
        for rad, skal in self.ramtackta:
            rader.append("  %-18s %s  [%s]" % ("ramtackt", rad, skal))
        return "\n".join(rader)


@dataclass
class Resultat:
    kropp: str
    deklarationer: str
    rapport: Rapport
    station: str = ""


# ---- generatorn ----------------------------------------------------------

class Baslinje(object):
    """Den regelbaserade generatorn. Deterministisk per konstruktion.

    `driv_obundna` och `las_obundna` är två avsiktligt skilda växlar. De
    tillfredsställer grind 3 (`ODRIVEN_UTGANG` och `ORORD_SIGNAL`) genom att
    röra varje signal en gång — utan att göra något funktionellt med den. Det
    är grindtillfredsställelse och inte styrning, och därför är de AV som
    standard och mäts som en egen rad i M-62. En grind som blir billig slutar
    mäta sin egen storhet, och en generator som klarar en grind genom att
    skriva `X := FALSE` har inte styrt X.
    """

    def __init__(self, niva: str = NIVA_SPEC, driv_obundna: bool = False,
                 las_obundna: bool = False):
        if niva not in NIVAER:
            raise Baslinjefel("okänd nivå %r; nivåerna är %s"
                              % (niva, ", ".join(NIVAER)))
        self.niva = niva
        self.driv_obundna = driv_obundna
        self.las_obundna = las_obundna

    # -- huvudingången --------------------------------------------------

    def generera(self, spec: Spec) -> Resultat:
        karta = Mo.Karta(Mo.klassa(list(spec.signaler)))
        station = spec.station or karta.station()
        rapport = Rapport(niva=self.niva)
        bygge = _Bygge(self, karta, spec, rapport)
        kropp = bygge.kor()
        return Resultat(kropp, bygge.deklarationstext(), rapport, station)


class _Bygge(object):
    """Ett enda bygge. Håller allt föränderligt så att Baslinje blir tillstånds-
    lös och två körningar med samma spec ger samma text."""

    def __init__(self, agare: Baslinje, karta: Mo.Karta, spec: Spec,
                 rapport: Rapport):
        self.agare = agare
        self.karta = karta
        self.spec = spec
        self.rapport = rapport
        self.dekl: List[Tuple[str, str]] = []      # (namn, typ med init)
        self._n = 0
        self.toppskrivna: Set[str] = set()
        self.lasta: Set[str] = set()
        # Uppehållstimrarna anropas på TOPPNIVÅ, aldrig inne i sin egen
        # CASE-gren: ett TON som bara anropas i den gren det bevakar fryser sin
        # ET när grenen lämnas, och nästa varv fortsätter räkna från den frusna
        # tiden i stället för från noll. Felet syns först som ett uppehåll som
        # blir kortare för varje cykel.
        self._dwellrader: List[str] = []
        self._antal_steg = 0

    # -- variabler ------------------------------------------------------

    def var(self, stam: str, typ: str) -> str:
        namn = PREFIX + stam
        if any(n == namn for n, _ in self.dekl):
            self._n += 1
            namn = "%s%s%d" % (PREFIX, stam, self._n)
        self.dekl.append((namn, typ))
        return namn

    def deklarationstext(self) -> str:
        if not self.dekl:
            return ""
        rader = ["VAR"]
        for namn, typ in self.dekl:
            rader.append("    %-14s : %s;" % (namn, typ))
        rader.append("END_VAR")
        return "\n".join(rader) + "\n"

    # -- körningen ------------------------------------------------------

    def kor(self) -> str:
        k = self.karta
        if self.agare.niva in (NIVA_SPEC, NIVA_PROSA):
            if self.agare.niva == NIVA_PROSA:
                # Samma grammatik, annan källa: uppgiftstextens numrerade
                # lista i stället för specfältet. Skillnaden mellan de två
                # talen ÄR svaret på om specfältet bär något prosan inte gör.
                numrerade, punkter = Sp.steg_ur_prompt(self.spec.uppgiftstext)
                sekvens = tuple(Sp.dela_meningar(numrerade))
                forreglingar = tuple(Sp.dela_meningar(punkter))
            else:
                sekvens, forreglingar = self.spec.sekvens, self.spec.forreglingar
            lasning = Sp.las(sekvens, forreglingar,
                             [t.namn for t in k.taggar])
            self.rapport.olasta_rader = list(lasning.olasta)
            self.rapport.olasta_forreglingar = list(lasning.olasta_forreglingar)
            self.rapport.ramtackta = list(lasning.ramtackta)
            intervall = Sp.las_intervall(
                self.spec.uppgiftstext, set(t.namn for t in k.taggar),
                [t.namn for t in k.med_roll(Mo.ROLL_MATNING)])
            trosklar = Sp.las_trosklar(
                self.spec.uppgiftstext, set(t.namn for t in k.taggar),
                [t.namn for t in k.med_roll(Mo.ROLL_MATNING)],
                [t.namn for t in k.utgangar()])
        else:
            # Magra nivån: bara I/O-listan. Stegkedjan kommer ur kartans egen
            # ordning, och ingen text läses alls.
            lasning = Sp.Lasning()
            lasning.direktiv = self._kedja_ur_kartan()
            intervall, trosklar = [], []
        self.rapport.intervall = len(intervall)
        self.rapport.rader_totalt = len(lasning.direktiv) + len(lasning.olasta)
        self.rapport.forreglingar_totalt = (len(lasning.forreglingar)
                                            + len(lasning.olasta_forreglingar)
                                            + len(lasning.ramtackta))
        self.rapport.utgangar_totalt = len(k.utgangar())
        self.rapport.ingangar_totalt = len(k.alla_ingangar())
        self.lasning = lasning
        self.intervall = intervall
        self.trosklar = trosklar

        self._gallra(lasning)
        if Pm.ar_packml(k):
            self.rapport.mall = "packml"
            return self._packmlkropp()
        return self._stegkedjekropp()

    def _gallra(self, lasning) -> None:
        """Fäll direktiv som inte går att uttrycka typriktigt. Fail-closed.

        MÄTT under bygget: det kontrollerade språket skriver `nar ST150_LYR_CNT`
        utan jämförelse, och en heltalssignal som boolesk term ger `BOOL AND
        INT` — som grind 2 fäller på TYP. Frestelsen är att tyst släppa termen
        och behålla steget. Det ger ett SVAGARE villkor som ändå kompilerar,
        alltså precis en falsk grön: koden ser färdig ut och kommenderar utan
        sin spärr. Direktivet stryks i stället, och raden räknas som oläst.
        """
        kvar = []
        for d in lasning.direktiv:
            skal = self._otypat(d)
            if skal:
                lasning.olasta.append("%s   [%s]" % (d.rad or str(d), skal))
                continue
            kvar.append(d)
        lasning.direktiv = kvar
        self.rapport.olasta_rader = list(lasning.olasta)

    def _otypat(self, d: Sp.Direktiv) -> str:
        for t in d.villkor.termer:
            tagg = self.karta.get(t.signal)
            if tagg is None or tagg.typ == "bool":
                continue
            if not t.jamforelse and not t.flank:
                return ("%s ar %s och lastes som en boolesk term utan "
                        "jamforelse" % (t.signal, tagg.typ))
        for h in d.handlingar:
            tagg = self.karta.get(h.signal)
            if tagg is None:
                continue
            if not tagg.ar_utgang:
                # MÄTT under bygget: läsaren tog `ST310_HSK_ACK` ur satsen
                # "nollstall den nar ST310_HSK_ACK gatt lag" som ett skrivmål.
                # En skrivning till en insignal är en logik som sätter sin egen
                # givare, och tolken fäller den — men först efter att koden sett
                # färdig ut. Direktivet stryks här i stället.
                return "%s ar en insignal och kan inte skrivas" % h.signal
            if tagg.typ == "bool" and h.sort == Sp.SATTVARDE:
                return ("%s ar bool och kan inte ges ett tal" % h.signal)
            if tagg.typ != "bool" and h.sort in (Sp.SATT, Sp.PULS) and h.varde:
                return ("%s ar %s och kan inte sattas hog" % (h.signal, tagg.typ))
        return ""

    # -- magra nivån ----------------------------------------------------

    def _kedja_ur_kartan(self) -> List[Sp.Direktiv]:
        """Stegkedjan när det enda som finns är en I/O-lista.

        Regeln är den enda en I/O-lista bär: kommendera don ETT i taget i
        kartans ordning, och vänta på varje dons kvittens innan nästa
        kommenderas. Det är en riktig klassisk regel — och den är blind för all
        ordning som inte råkar vara kartans.
        """
        ut: List[Sp.Direktiv] = []
        for kommando in self.karta.kommandon():
            if not ut:
                givare = [t for t in self.karta.med_roll(Mo.ROLL_GIVARE)]
                start = Sp.Villkor((Sp.Term(givare[0].namn),)) if givare \
                    else Sp.Villkor()
                ut.append(Sp.Direktiv(Sp.D_STEG, villkor=start,
                                      handlingar=(Sp.Handling(
                                          Sp.SATT, kommando.namn, True),)))
                forra = kommando
                continue
            ut.append(Sp.Direktiv(
                Sp.D_STEG,
                villkor=Sp.Villkor((Sp.Term(forra.par),)) if forra.par
                else Sp.Villkor(),
                handlingar=(Sp.Handling(Sp.SATT, forra.namn, False),
                            Sp.Handling(Sp.SATT, kommando.namn, True))))
            forra = kommando
        if ut and forra.par:
            ut.append(Sp.Direktiv(
                Sp.D_STEG, villkor=Sp.Villkor((Sp.Term(forra.par),)),
                handlingar=(Sp.Handling(Sp.SATT, forra.namn, False),)))
        return ut

    # -- gemensamma delar -----------------------------------------------

    def _permissiver(self, hand: bool) -> List[str]:
        """Signalerna som måste vara höga för att något ska kommenderas."""
        ut: List[str] = []
        for namn in (Mo.NODSTOPP, Mo.LUFT):
            if self.karta.har(namn):
                ut.append(namn)
        for f in self.lasning.forreglingar:
            if f.sort == Sp.F_PERMISSIV and f.b and f.b not in ut:
                if f.b == Mo.AUTOLAGE and hand:
                    continue      # automatläget är grenval, inte permissiv
                ut.append(f.b)
        if self.karta.har(Mo.AUTOLAGE) and not hand and Mo.AUTOLAGE not in ut:
            ut.append(Mo.AUTOLAGE)
        return ut

    def _villkorstext(self, villkor: Sp.Villkor, trigg: Dict[str, str]) -> str:
        delar = []
        for t in villkor.termer:
            self.lasta.add(t.signal)
            if t.flank:
                delar.append("%s.Q" % trigg[(t.signal, t.flank)])
            elif t.jamforelse:
                delar.append("%s %s %s"
                             % (t.signal, t.jamforelse,
                                self._tal(t.signal, t.varde)))
            elif t.sant:
                delar.append(t.signal)
            else:
                delar.append("NOT %s" % t.signal)
        if not delar:
            return "TRUE"
        return (" %s " % villkor.op).join(delar)

    def _tal(self, signal: str, varde: float) -> str:
        tagg = self.karta.get(signal)
        if tagg is not None and tagg.typ == "real":
            return "%.1f" % varde
        return "%d" % int(varde)

    def _tid(self, sekunder: float) -> str:
        return "T#%dms" % int(round(sekunder * 1000.0))

    # -- flankdetektorer -------------------------------------------------

    def _samla_flanker(self, direktiv: Sequence[Sp.Direktiv]) -> Dict:
        behov: List[Tuple[str, str]] = []
        for d in direktiv:
            for t in d.villkor.termer:
                if t.flank and (t.signal, t.flank) not in behov:
                    behov.append((t.signal, t.flank))
        ut = {}
        for signal, flank in behov:
            typ = "R_TRIG" if flank == Sp.FLANK_UPP else "F_TRIG"
            ut[(signal, flank)] = self.var(
                "Flank" + _kort(signal), typ)
        return ut

    # -- stegkedjan ------------------------------------------------------

    def _stegkedjekropp(self) -> str:
        k = self.karta
        d = self.lasning.direktiv
        handdirektiv = [x for x in d if x.lage == "hand"]
        hand = bool(handdirektiv) and k.har(Mo.AUTOLAGE)
        permissiver = self._permissiver(hand)

        trigg = self._samla_flanker(d)
        kvittenskrav = any(x.sort in (Sp.D_KVITTENSKRAV, Sp.D_ATERSTALL)
                           for x in d) and k.har(Mo.KVITTENS)
        larm_finns = k.har(Mo.LARM)

        rader: List[str] = []
        rader.append("(* Genererad av baslinjen (fas 11, M-62). Regelbaserad,")
        rader.append("   ingen sprakmodell. Samma spec ger samma kod. *)")

        namn_larm = self.var("Larm", "BOOL := FALSE") if larm_finns or \
            self.intervall or any(x.sort == Sp.D_VAKT for x in d) else ""
        namn_kvittens = self.var("Kvittens", "BOOL := TRUE") if kvittenskrav \
            else ""
        namn_drift = self.var("Drift", "BOOL := FALSE")
        namn_steg = self.var("Steg", "INT := 0")
        trig_reset = ""
        if kvittenskrav:
            trig_reset = self.var("TrigReset", "R_TRIG")

        # 1. flankdetektorerna, överst, så att alla ser samma flank.
        for (signal, _flank), inst in sorted(trigg.items(),
                                             key=lambda x: x[1]):
            rader.append("%s(CLK := %s);" % (inst, signal))
            self.lasta.add(signal)
        if trig_reset:
            rader.append("%s(CLK := %s);" % (trig_reset, Mo.KVITTENS))
            self.lasta.add(Mo.KVITTENS)

        # 2. räknare som ska gå oavsett driftläge. Alla regler för SAMMA
        #    räknare slås ihop till en enda IF/ELSIF-kedja: två skrivningar
        #    till samma utgång som båda kan köras i samma scan är grind 2:s
        #    DUBBELSKRIVNING, och grinden har rätt — en uppräkning och en
        #    nedräkning i samma scan tappar den ena.
        per_raknare: Dict[str, List[Sp.Direktiv]] = {}
        for x in d:
            if x.sort == Sp.D_RAKNA:
                per_raknare.setdefault(x.signal, []).append(x)
        for signal in sorted(per_raknare):
            for n, x in enumerate(per_raknare[signal]):
                villkor = self._villkorstext(x.villkor, trigg)
                tecken = "+" if x.handlingar and \
                    x.handlingar[0].sort == Sp.OKA else "-"
                rader.append("%s %s THEN" % ("IF" if n == 0 else "ELSIF",
                                             villkor))
                rader.append("    %s := %s %s 1;" % (signal, signal, tecken))
            rader.append("END_IF;")
            self.toppskrivna.add(signal)

        # 3. larmkällorna. Alla FÖRE domen, så att larmet aldrig släpar ett
        #    scan efter det don det ska stoppa.
        if namn_larm:
            rader.extend(self._larmkallor(namn_larm, trigg))
        if namn_kvittens:
            rader.append("IF NOT %s THEN" % Mo.NODSTOPP)
            rader.append("    %s := TRUE;   (* brutet nodstopp kraver "
                         "kvittens *)" % namn_kvittens)
            rader.append("END_IF;")
            self.lasta.add(Mo.NODSTOPP)

        # 4. återställningen. Efter larmkällorna: en kvittens i samma scan som
        #    ett fel får inte kvittera bort felet innan det ens setts.
        if trig_reset:
            villkor = ["%s.Q" % trig_reset] + list(permissiver)
            rader.append("IF %s THEN" % " AND ".join(villkor))
            if namn_larm:
                rader.append("    %s := FALSE;" % namn_larm)
            rader.append("    %s := FALSE;" % namn_kvittens)
            rader.append("END_IF;")

        # 5. larmutgången och driftsvillkoret.
        if larm_finns and namn_larm:
            rader.append("%s := %s;" % (Mo.LARM, namn_larm))
            self.toppskrivna.add(Mo.LARM)
        delar = list(permissiver)
        if namn_larm:
            delar.append("NOT %s" % namn_larm)
        if namn_kvittens:
            delar.append("NOT %s" % namn_kvittens)
        for p in permissiver:
            self.lasta.add(p)
        rader.append("%s := %s;" % (namn_drift, " AND ".join(delar) or "TRUE"))

        # 6. grenarna.
        auto_ut, hand_ut = self._utgangsmangder(d, handdirektiv)
        dwellplats = len(rader)
        rader.append("IF NOT %s THEN" % namn_drift)
        for namn in sorted(auto_ut | hand_ut):
            rader.append("    %s := %s;" % (namn, self._nollvarde(namn)))
        rader.append("    %s := 0;" % namn_steg)
        for namn in self._obundna(auto_ut | hand_ut):
            rader.append("    %s := %s;" % (namn, self._nollvarde(namn)))
        if hand:
            rader.append("ELSIF %s THEN" % Mo.AUTOLAGE)
        else:
            rader.append("ELSE")
        rader.extend("    " + r for r in self._autogren(d, trigg, namn_steg,
                                                        hand_ut))
        if hand:
            rader.append("ELSE")
            rader.extend("    " + r
                         for r in self._handgren(handdirektiv, trigg, auto_ut,
                                                 namn_steg))
        rader.append("END_IF;")
        rader[dwellplats:dwellplats] = self._dwellrader

        rader.extend(self._diagnosrad())
        self.rapport.steg = self._antal_steg
        return "\n".join(rader) + "\n"

    # -- larmkällorna ----------------------------------------------------

    def _larmkallor(self, namn_larm: str, trigg) -> List[str]:
        rader: List[str] = []
        for iv in self.intervall:
            villkor = "(%s < %s) OR (%s > %s)" % (
                iv.signal, self._tal(iv.signal, iv.lag),
                iv.signal, self._tal(iv.signal, iv.hog))
            if iv.nar:
                villkor = "%s AND (%s)" % (iv.nar, villkor)
                self.lasta.add(iv.nar)
            rader.append("IF %s THEN" % villkor)
            rader.append("    %s := TRUE;   (* utanfor arbetsomradet *)"
                         % namn_larm)
            rader.append("END_IF;")
            self.lasta.add(iv.signal)
        for x in self.lasning.direktiv:
            if x.sort != Sp.D_VAKT:
                continue
            inn = self._vaktingang(x)
            if not inn:
                self.rapport.antaganden.append(
                    "tidsovervakningen pa raden %r kunde inte bindas till "
                    "nagon signal; ingen vakt genererades" % x.rad)
                continue
            inst = self.var("Vakt", "TON")
            rader.append("%s(IN := %s, PT := %s);"
                         % (inst, inn, self._tid(x.tid_s or STANDARDVAKT_S)))
            rader.append("IF %s.Q THEN" % inst)
            rader.append("    %s := TRUE;   (* tidsovervakning *)" % namn_larm)
            rader.append("END_IF;")
            self.rapport.vakter += 1
        for f in self.lasning.forreglingar:
            rader.extend(self._forreglingslarm(f, namn_larm))
        return rader

    def _vaktingang(self, direktiv: Sp.Direktiv) -> str:
        """Uttrycket vakten ska räkna på."""
        if not direktiv.villkor.tomt:
            return self._villkorstext(direktiv.villkor, {})
        if direktiv.signal:
            self.lasta.add(direktiv.signal)
            return direktiv.signal
        if direktiv.stam and len(direktiv.stam) >= MINSTA_STAM:
            traffar = [t.namn for t in self.karta.utgangar()
                       if direktiv.stam in (t.kommentar or "").lower()]
            if traffar:
                self.rapport.antaganden.append(
                    "vakten %r namnger ingen tagg; stammen %r matchade "
                    "kommentaren hos %s" % (direktiv.rad, direktiv.stam,
                                            ", ".join(traffar)))
                for n in traffar:
                    self.lasta.add(n)
                return " OR ".join(traffar)
        return ""

    def _forreglingslarm(self, f: Sp.Forregling, namn_larm: str) -> List[str]:
        if f.sort == Sp.F_HALLVILLKOR:
            self.lasta.add(f.a)
            self.lasta.add(f.b)
            return ["IF %s AND NOT %s THEN" % (f.a, f.b),
                    "    %s := TRUE;   (* %s slapp under rorelsen *)"
                    % (namn_larm, f.b),
                    "END_IF;"]
        if f.sort == Sp.F_OMSESIDIG:
            if Mo.LARM in (f.a, f.b):
                # Ramen garanterar redan att ett larm stoppar allt.
                self.rapport.ramtackta.append(
                    (f.rad, "ramen: larmet ingar i driftsvillkoret"))
                return []
            self.lasta.add(f.a)
            self.lasta.add(f.b)
            return ["IF %s AND %s THEN" % (f.a, f.b),
                    "    %s := TRUE;   (* omsesidig uteslutning bruten *)"
                    % namn_larm,
                    "END_IF;"]
        return []

    # -- utgångsmängderna ------------------------------------------------

    def _utgangsmangder(self, direktiv, handdirektiv) -> Tuple[Set[str], Set[str]]:
        hand_ut: Set[str] = set()
        for x in handdirektiv:
            if x.signal:
                hand_ut.add(x.signal)
            for h in x.handlingar:
                hand_ut.add(h.signal)
        auto_ut: Set[str] = set()
        for x in direktiv:
            if x.lage == "hand":
                continue
            for h in x.handlingar:
                if h.signal in self.toppskrivna:
                    continue
                auto_ut.add(h.signal)
        for t in self.karta.med_roll(Mo.ROLL_DRIFTUTGANG):
            auto_ut.add(t.namn)
        for tr in self.trosklar:
            auto_ut.add(tr.utgang)
        auto_ut -= hand_ut
        auto_ut.discard(Mo.LARM)
        hand_ut.discard(Mo.LARM)
        return auto_ut, hand_ut

    def _nollvarde(self, namn: str) -> str:
        tagg = self.karta.get(namn)
        if tagg is None or tagg.typ == "bool":
            return "FALSE"
        return "0.0" if tagg.typ == "real" else "0"

    def _obundna(self, drivna: Set[str]) -> List[str]:
        """Utgångar ingen regel driver. Redovisas alltid, drivs bara på begäran."""
        ut = []
        for t in self.karta.utgangar():
            if t.namn in drivna or t.namn in self.toppskrivna:
                continue
            if t.namn not in self.rapport.obundna_utgangar:
                self.rapport.obundna_utgangar.append(t.namn)
            if self.agare.driv_obundna:
                ut.append(t.namn)
        return ut

    # -- automatikgrenen -------------------------------------------------

    def _autogren(self, direktiv, trigg, namn_steg: str,
                  hand_ut: Set[str]) -> List[str]:
        rader: List[str] = []
        for namn in sorted(hand_ut):
            rader.append("%s := %s;   (* handkorning sparrad i automatlage *)"
                         % (namn, self._nollvarde(namn)))
        for t in self.karta.med_roll(Mo.ROLL_DRIFTUTGANG):
            rader.append("%s := TRUE;" % t.namn)
        for x in direktiv:
            if x.sort == Sp.D_DRIFTUT:
                for h in x.handlingar:
                    if h.signal not in [t.namn for t in
                                        self.karta.med_roll(Mo.ROLL_DRIFTUTGANG)]:
                        rader.append("%s := %s;"
                                     % (h.signal,
                                        "TRUE" if h.varde else "FALSE"))
        for tr in self.trosklar:
            self.lasta.add(tr.matning)
            rader.append("%s := %s %s %s;"
                         % (tr.utgang, tr.matning, tr.tecken,
                            self._tal(tr.matning, tr.varde)))
        steg = self._stegen(direktiv)
        self._antal_steg = len(steg)
        if not steg:
            return rader
        rader.append("CASE %s OF" % namn_steg)
        for i, (villkor, handlingar, dwell) in enumerate(steg):
            rader.append("    %d:" % i)
            if dwell is not None:
                inst = self.var("Paus", "TON")
                self._dwellrader.append("%s(IN := (%s = %d), PT := %s);"
                                        % (inst, namn_steg, i, self._tid(dwell)))
                villkortext = "%s.Q" % inst
            else:
                villkortext = self._villkorstext(villkor, trigg)
            nasta = (i + 1) % len(steg)
            if villkortext == "TRUE":
                for h in handlingar:
                    rader.append("        " + self._handlingstext(h))
                rader.append("        %s := %d;" % (namn_steg, nasta))
            else:
                rader.append("        IF %s THEN" % villkortext)
                for h in handlingar:
                    rader.append("            " + self._handlingstext(h))
                rader.append("            %s := %d;" % (namn_steg, nasta))
                rader.append("        END_IF;")
        rader.append("ELSE")
        rader.append("    %s := 0;" % namn_steg)
        rader.append("END_CASE;")
        return rader

    def _handlingstext(self, h: Sp.Handling) -> str:
        if h.sort == Sp.SATTVARDE:
            return "%s := %s;" % (h.signal, self._tal(h.signal,
                                                      float(h.varde)))
        if h.sort == Sp.PULS:
            return "%s := TRUE;" % h.signal
        if h.sort == Sp.SATT:
            tagg = self.karta.get(h.signal)
            if tagg is not None and tagg.typ != "bool" and not h.varde:
                # "nollstall" på en räknare är noll, inte FALSE. Grind 2 fäller
                # annars på TYP, och den har rätt.
                return "%s := %s;" % (h.signal, self._nollvarde(h.signal))
            return "%s := %s;" % (h.signal, "TRUE" if h.varde else "FALSE")
        if h.sort == Sp.OKA:
            return "%s := %s + 1;" % (h.signal, h.signal)
        if h.sort == Sp.MINSKA:
            return "%s := %s - 1;" % (h.signal, h.signal)
        if h.sort == Sp.FOLJ:
            self.lasta.add(h.kalla)
            return "%s := %s;" % (h.signal, h.kalla)
        raise Baslinjefel("okänd handling %r" % (h.sort,))

    def _stegen(self, direktiv) -> List[Tuple[Sp.Villkor, Tuple, Optional[float]]]:
        """Stegkedjan: villkor, handlingar och ett eventuellt uppehåll.

        Sista steget är ALLTID ett återgångssteg som kräver att varje don som
        kedjan kommenderat har släppt. Det är GRAFCET:s initialvillkor och
        standardpraxis i en stegkedja: en ny cykel får inte börja på en maskin
        som ännu inte kommit hem. Utan det steget kommenderar kedjan ett andra
        slag på samma detalj så fort givaren står kvar hög, och det är precis
        felklass F15.
        """
        steg: List[Tuple[Sp.Villkor, Tuple, Optional[float]]] = []
        vantande_dwell: Optional[float] = None
        kommenderade: List[str] = []
        # En puls tas ner i NÄSTA steg. Lämnas den uppe är kommandot en nivå,
        # och en kamera som triggas på nivå tar en bild per scan.
        att_nolla: List[Sp.Handling] = []
        for x in direktiv:
            if x.sort == Sp.D_UPPEHALL:
                vantande_dwell = x.tid_s
                continue
            if x.sort != Sp.D_STEG or x.lage == "hand":
                continue
            villkor = self._med_forvillkor(x)
            handlingar = tuple(att_nolla) + tuple(x.handlingar)
            att_nolla = [Sp.Handling(Sp.SATT, h.signal, False)
                         for h in x.handlingar if h.sort == Sp.PULS]
            if vantande_dwell is not None:
                steg.append((Sp.Villkor(), (), vantande_dwell))
                vantande_dwell = None
            steg.append((villkor, handlingar, None))
            for h in x.handlingar:
                if h.sort == Sp.SATT and h.varde:
                    kommenderade.append(h.signal)
        if not steg:
            return steg
        if att_nolla:
            steg.append((Sp.Villkor(), tuple(att_nolla), None))
        termer = []
        for namn in kommenderade:
            tagg = self.karta.get(namn)
            if tagg is None or not tagg.par:
                continue
            kvittens = self.karta.get(tagg.par)
            if kvittens is not None and kvittens.typ != "bool":
                # MÄTT: `ST200_SCN_DEST` är destinationsnumret ur en skanner,
                # inte en klarsignal. `NOT <INT>` gick igenom generatorn och
                # fälldes först av STruC++ — återgångsvillkoret byggs efter
                # typgallringen och slapp därför förbi den. En kvittens som
                # inte är boolesk kan inte betyda "donet har slappt".
                self.rapport.antaganden.append(
                    "%s ar %s och kan inte bara ett atergangsvillkor"
                    % (kvittens.namn, kvittens.typ))
                continue
            t = Sp.Term(tagg.par, sant=False)
            if t not in termer:
                termer.append(t)
        steg.append((Sp.Villkor(tuple(termer)), (), None))
        return steg

    def _med_forvillkor(self, x: Sp.Direktiv) -> Sp.Villkor:
        """Stegets villkor plus de förreglingar som är förvillkor på dess don."""
        termer = list(x.villkor.termer)
        satta = [h.signal for h in x.handlingar
                 if h.sort == Sp.SATT and h.varde]
        for f in self.lasning.forreglingar:
            if f.sort == Sp.F_FORVILLKOR and f.a in satta:
                t = Sp.Term(f.b)
                if t not in termer:
                    termer.append(t)
            if f.sort == Sp.F_CYKELSPARR and x is self._forsta_steg():
                t = Sp.Term(f.a, jamforelse="<", varde=f.varde)
                if not any(u.signal == f.a for u in termer):
                    termer.append(t)
        return Sp.Villkor(tuple(termer), x.villkor.op)

    def _forsta_steg(self) -> Optional[Sp.Direktiv]:
        for x in self.lasning.direktiv:
            if x.sort == Sp.D_STEG and x.lage != "hand":
                return x
        return None

    # -- handgrenen ------------------------------------------------------

    def _handgren(self, handdirektiv, trigg, auto_ut: Set[str],
                  namn_steg: str) -> List[str]:
        rader = []
        for namn in sorted(auto_ut):
            rader.append("%s := %s;   (* automatiken star still i handlage *)"
                         % (namn, self._nollvarde(namn)))
        rader.append("%s := 0;" % namn_steg)
        for x in handdirektiv:
            if x.sort == Sp.D_FOLJ:
                villkor = x.kalla
                self.lasta.add(x.kalla)
                if x.tak:
                    villkor += " AND NOT %s" % x.tak
                    self.lasta.add(x.tak)
                rader.append("%s := %s;   (* hall-for-att-kora *)"
                             % (x.signal, villkor))
                continue
            if x.sort == Sp.D_STEG:
                rader.append("IF %s THEN" % self._villkorstext(x.villkor, trigg))
                for h in x.handlingar:
                    rader.append("    " + self._handlingstext(h))
                rader.append("END_IF;")
        return rader

    # -- diagnosraden ----------------------------------------------------

    def _diagnosrad(self) -> List[str]:
        """Ingångar ingen regel läser. Redovisas alltid, läses bara på begäran."""
        orord = []
        for t in self.karta.alla_ingangar():
            if t.namn in self.lasta:
                continue
            orord.append(t.namn)
        self.rapport.ororda_ingangar = list(orord)
        if not orord or not self.agare.las_obundna:
            return []
        delar = []
        for namn in orord:
            tagg = self.karta.get(namn)
            if tagg.typ == "bool":
                delar.append(namn)
            elif tagg.typ == "real":
                delar.append("(%s <> 0.0)" % namn)
            else:
                delar.append("(%s <> 0)" % namn)
        namn_diag = self.var("Oanvand", "BOOL := FALSE")
        return ["(* Signaler ingen regel binder. Raden ror dem for grind 3 och",
                "   styr ingenting. Det ar grindtillfredsstallelse, inte",
                "   styrning, och det star i baslinjens rapport. *)",
                "%s := %s;" % (namn_diag, " OR ".join(delar))]

    # -- PackML ----------------------------------------------------------

    def _packmlkropp(self) -> str:
        k = self.karta
        namn = Pm.taggar(k)
        rader = ["(* Genererad av baslinjen (fas 11, M-62): PackML-mallen ur",
                 "   ISA-TR88.00.02, instansierad mot kartans PML-taggar. *)"]
        trig_sc = self.var("TrigSc", "R_TRIG")
        # Startvärdet är standardens: efter spänningspåslag står maskinen i
        # STOPPED (2). En utgång ur signalkartan deklareras utan startvärde och
        # skulle börja på 0, som inte är ett PackML-tillstånd alls.
        statevar = self.var("State", "INT := %d" % Pm.STOPPED)
        rader.append("%s(CLK := %s);" % (trig_sc, namn["SC"]))
        self.lasta.add(namn["SC"])
        self.lasta.add(namn["CMD"])

        felvillkor: List[str] = []
        if k.har(Mo.NODSTOPP):
            felvillkor.append("NOT %s" % Mo.NODSTOPP)
            self.lasta.add(Mo.NODSTOPP)
        for iv in self.intervall:
            felvillkor.append("%s < %s OR %s > %s"
                              % (iv.signal, self._tal(iv.signal, iv.lag),
                                 iv.signal, self._tal(iv.signal, iv.hog)))
            self.lasta.add(iv.signal)
        rader.extend(Pm.kropp(k, felvillkor, trig_sc, statevar))
        rader.append("%s := %s;" % (namn["STATE"], statevar))

        # Donen binds till tillstånd genom förreglingsraderna, inte genom
        # gissningar om vad stationen gör.
        enbart: Dict[str, float] = {}
        for f in self.lasning.forreglingar:
            if f.sort == Sp.F_ENBART and f.b == namn["STATE"]:
                enbart[f.a] = f.varde
        drivna = set([namn["STATE"]])
        for utgang in sorted(enbart):
            villkor = "%s = %d" % (namn["STATE"], int(enbart[utgang]))
            for tr in self.trosklar:
                if tr.utgang == utgang:
                    villkor += " AND %s %s %s" % (
                        tr.matning, tr.tecken, self._tal(tr.matning, tr.varde))
                    self.lasta.add(tr.matning)
            rader.append("%s := %s;" % (utgang, villkor))
            drivna.add(utgang)
        if k.har(Mo.LARM):
            rader.append("%s := %s;"
                         % (Mo.LARM, " OR ".join(
                             "%s = %d" % (namn["STATE"], t)
                             for t in Pm.LARMTILLSTAND)))
            drivna.add(Mo.LARM)
        for extra in self._obundna(drivna):
            rader.append("%s := %s;" % (extra, self._nollvarde(extra)))
        rader.extend(self._diagnosrad())
        self.rapport.steg = len(Pm.TILLSTANDSNAMN)
        return "\n".join(rader) + "\n"


def _kort(namn: str) -> str:
    """Ett kort, unikt suffix ur ett taggnamn, för en instansvariabel."""
    delar = [d for d in re.split(r"[^A-Za-z0-9]", namn) if d]
    return "".join(d[:4].capitalize() for d in delar[-2:]) or "X"
