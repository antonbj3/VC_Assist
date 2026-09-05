# -*- coding: utf-8 -*-
"""MARKERINGEN som indicium, och OGONBLICKSBILDEN som skickas varje tur.

Tva saker bor har, och de hor ihop:

    Ogonblicksbild   vad scenen bestar av: varje komponents namn, vilken SORT
                     den ar, och om anvandaren markerat den. Liten nog att
                     skickas i varje tur, i stallet for att fragas fram.
    Markering        vad anvandaren pekar pa just nu - och provningen av det
                     mot vad meningen faktiskt sager.

MARKERINGEN AR ETT INDICIUM, INTE EN AUKTORITET

Det ar hela konstruktionen, och den kommer ur operatorens egen invandning:

    "problemet ar ju bara om man rakar ha fel sak markerad som man syftar pa"

Att lata markeringen vara facit gor systemet SAMSTAMMIGT MED SIG SJALVT och
fel mot anvandaren: har han nagot annat markerat an det han talar om - och det
ar ett vanligare lage an motsatsen - byts fel komponent, med full
sjalvsakerhet och utan att nagon frigar. Det ar ett tyst fel, alltsa den
dyraste sorten.

Meningen och markeringen provas darfor MOT VARANDRA, och de kan sla ut at
fyra hall:

    AVGJORD       meningen sager en sort, markeringen bar den sorten, och
                  exakt en kandidat aterstar. Markeringen loste ut malet, och
                  belagget sager att det var den som gjorde det.
    MOTSAGELSE    meningen sager en sort, markeringen bar en ANNAN. Det ar
                  inte en upplosning - det ar ett besked: "du sager gripdon,
                  markeringen ar transportoren ST210_BAND; menade du den,
                  eller ett av gripdonen?" Battre an bada de tysta svaren.
    SMALNAD       markeringen pekar ut flera kandidater, eller meningen namner
                  ingen sort alls. Fragan star kvar, men med FARRE kandidater.
    SAKNAS        ingenting ar markerat. Det ar inget fel - fragan stalls som
                  forut. Tystnad ar aldrig ett godkannande (I3).
    OVIDKOMMANDE  markeringen pekar pa nagot meningens ord inte kan syfta pa.
                  Den bar da ingen upplysning om malet, och kandidatlistan
                  star kvar HEL. Att krympa den till tomt hade gjort en
                  ovidkommande markering till ett hinder.

VARFOR EN SORT I MENINGEN KRAVS FOR ATT LOSA UT

En upplosning ar ett pastaende om att tva OBEROENDE kallor pekar at samma
hall: operatorens ord och hans hand. Namner meningen ingen sort finns bara en
kalla, och en kalla kan inte styrka sig sjalv. Da far markeringen smalna av,
aldrig avgora. Det ar skillnaden mellan "du sa gripdon och pekar pa ett
gripdon" och "du pekar pa nagot".

SORTEN KOMMER UR STRUKTUREN, ALDRIG UR NAMNET

M-69 matte vad namnhardledning kostar i katalogen: namnet "Robots" ger 1736
komponenter, strukturen 2202. Samma fel gar att gora i en scen - M-171 matte
en komponent som HETER `Robot` och bara bar en boolsignal. Sorten lases darfor
ur beteendena (`verktyg/markering.py`), och en komponent vars sort inte gar
att avgora far OKAND. OKAND ar inte en familj, och den kan aldrig produceras
ur ett namn.

Endast standardbiblioteket plus tjanstens egna lager.
"""
from __future__ import annotations

from ..datablad import FAMILJEMARKORER
from ..llm import matt
from . import sparr

# Sorterna. HARLEDDA ur datablad.FAMILJEMARKORER och aldrig skrivna av - en
# tredje kopia av den listan ar precis den skuld S12 handlar om, och de tva
# som redan finns (datablad, katalogindex) bevakas av ett eget prov.
SORTER = tuple(namn for namn, _markorer in FAMILJEMARKORER)

# Sorten gick INTE att avgora. Det ar inte en familj och star darfor utanfor
# SORTER. Skalet ar katalogindex._familj:s eget: tomt betyder "fragan gick
# inte att besvara", medan "ovrig" later som ett svar. En modell som anger
# OKAND som malsort har alltsa inte namnt nagon sort - se prova().
OKAND = "okand"

AVGJORD = "AVGJORD"
MOTSAGELSE = "MOTSAGELSE"
SMALNAD = "SMALNAD"
SAKNAS = "SAKNAS"
OVIDKOMMANDE = "OVIDKOMMANDE"
UTFALL = (AVGJORD, MOTSAGELSE, SMALNAD, SAKNAS, OVIDKOMMANDE)

# Utfall som loser ut ett mal. Exakt ett, och det ar med flit: en lista med
# tva poster har varje gang blivit tva vagar dar den ena inte var provad.
LOSER_UT = (AVGJORD,)

# Taket for ogonblicksbilden, i tokens. HARLETT och inte valt: bilden ar
# scenvyn, och scenvyn ar post 6 i 25_kontextbudget.md med tak 15 % av
# kontextfonstret. Det minsta fonster projektet har MATT mot ar 8 000 tokens
# (M-141, dar systemprompten spricker vid just det fonstret), och 15 % av
# 8 000 ar 1 200. En bild som inte haller det talet kan inte skickas varje
# tur i den minsta riggen - och en bild som inte kan skickas varje tur ar
# ingen bild, den ar ett verktygssvar till.
TAK_TOKENS = 1200      # 25_kontextbudget.md post 6 (15 %) av 8 000 (M-141)


# ---------------------------------------------------------------------------
# Markeringen
# ---------------------------------------------------------------------------

class Markering(object):
    """Vad anvandaren pekar pa. Ett INDICIUM, aldrig ett facit.

    `komponenter` ar (namn, sort)-par i scenens egen ordning, och `kalla`
    namner verktyget som gav dem. Dubbletter bevaras: MATT (M-171) att
    komponentnamn INTE ar unika i VC - provscenen bar fyra `ST8_Mall` - sa en
    lista som slar ihop dem pa namn ljuger om hur manga som ar markerade.
    """

    __slots__ = ("komponenter", "kalla")

    def __init__(self, komponenter=(), kalla=""):
        self.komponenter = tuple(
            (str(n), str(s) if s else OKAND) for n, s in komponenter)
        self.kalla = kalla

    def __repr__(self):
        return "Markering(%d markerade ur %s)" % (
            len(self.komponenter), self.kalla or "ingen lasning")

    def __len__(self):
        return len(self.komponenter)

    def tom(self):
        return not self.komponenter

    def namn(self):
        return tuple(n for n, _s in self.komponenter)

    def sorter(self):
        """De sorter markeringen bar, en gang var, i den ordning de kom."""
        ut = []
        for _n, s in self.komponenter:
            if s not in ut:
                ut.append(s)
        return tuple(ut)

    def av_sorten(self, sort):
        return tuple(n for n, s in self.komponenter if s == sort)

    def text(self):
        if self.tom():
            return SAKNAS
        return ", ".join("%s (%s)" % (n, s) for n, s in self.komponenter)


def markering_ur_svar(svar, kalla="get_selection"):
    """En Markering ur `get_selection`:s svar. Hittar ingenting pa."""
    if not isinstance(svar, dict):
        raise TypeError("markering_ur_svar vill ha verktygets svar som dict, "
                        "fick %s" % type(svar).__name__)
    poster = svar.get("selected")
    if poster is None:
        raise ValueError(
            "svaret bar inget 'selected'-falt. En markering ur ett svar som "
            "inte ar en markeringslasning vore en markering nagon hittat pa "
            "(I9).")
    return Markering(
        [(_namn(p, kalla), (p or {}).get("sort")) for p in poster], kalla=kalla)


def _namn(post, kalla):
    namn = (post or {}).get("name")
    if not namn:
        raise ValueError(
            "en komponent i %s saknar 'name'; den gar da inte att peka pa, "
            "och att hoppa over den tyst vore att krympa svaret utan att "
            "saga det" % kalla)
    return namn


# ---------------------------------------------------------------------------
# Provningen: meningen mot markeringen
# ---------------------------------------------------------------------------

class Markeringsdom(object):
    """Utfallet av att prova meningen mot markeringen."""

    __slots__ = ("utfall", "kandidater", "skal", "belagg", "markering")

    def __init__(self, utfall, kandidater=(), skal=(), belagg=None,
                 markering=None):
        if utfall not in UTFALL:
            raise ValueError("okant markeringsutfall %r" % (utfall,))
        if belagg is not None and utfall not in LOSER_UT:
            raise ValueError(
                "%s bar ett belagg om att markeringen avgjorde, men den "
                "avgjorde ingenting. Ett belagg utan upplosning ar precis det "
                "tysta valet grinden finns for" % utfall)
        self.utfall = utfall
        self.kandidater = tuple(kandidater)
        self.skal = tuple(skal)
        self.belagg = belagg
        self.markering = markering

    def __repr__(self):
        return "Markeringsdom(%s, %d kandidater)" % (self.utfall,
                                                     len(self.kandidater))

    def loste_ut(self):
        return self.utfall in LOSER_UT

    def text(self):
        rader = ["MARKERING: %s" % self.utfall]
        for s in self.skal:
            rader.append("    " + s)
        return "\n".join(rader)


def prova(markering, kandidater, malsort=""):
    """Provar meningen mot markeringen. Kastar aldrig (S10).

    `kandidater` ar de komponentnamn meningens ord kan syfta pa, ur den lasta
    scenen. `malsort` ar den SORT modellen sager att meningens substantiv
    betecknar - tom strang, eller OKAND, nar meningen inte namner nagon.

    Ordningen ar inte godtycklig. MOTSAGELSEN provas FORE allt annat, darfor
    att den ar det enda utfall som sager att de tva kallorna pekar at olika
    hall - och da far ingen av dem tysta den andra.
    """
    kandidater = tuple(kandidater)
    if markering is None or markering.tom():
        return Markeringsdom(SAKNAS, kandidater, [
            "ingenting ar markerat i scenen. Fragan stalls som forut - en tom "
            "markering ar inget fel, och den ar aldrig ett godkannande (I3)"],
            markering=markering)

    namngiven_sort = malsort in SORTER
    if namngiven_sort:
        ratt_sort = markering.av_sorten(malsort)
        if not ratt_sort:
            # MOTSAGELSE bara nar markeringen bar en KAND sort som ar en
            # ANNAN. Bar den bara OKAND sort sager den ingenting emot - den
            # sager ingenting alls, och att kalla det en motsagelse vore att
            # ropa varg: sorten kunde inte avgoras ur strukturen, och den
            # komponenten KAN vara det operatoren menar. Skillnaden mellan
            # "du pekar pa nagot annat" och "jag kan inte se vad du pekar pa"
            # ar hela skillnaden mellan ett besked och en gissning.
            kanda = tuple(s for s in markering.sorter() if s in SORTER)
            if kanda:
                return Markeringsdom(MOTSAGELSE, kandidater, [
                    "du sager %s, men det som ar markerat ar %s. Menade du "
                    "den, eller nagon av %s?"
                    % (malsort, markering.text(),
                       ", ".join(kandidater) or "kandidaterna i scenen"),
                    "markeringen och meningen pekar at olika hall, och da "
                    "avgor ingen av dem ensam"],
                    markering=markering)
            return Markeringsdom(OVIDKOMMANDE, kandidater, [
                "det markerade (%s) har ingen sort som gick att avgora ur "
                "strukturen, sa det gar inte att prova mot ordet %s. "
                "Markeringen kan varken styrka eller motsaga meningen, och "
                "kandidatlistan star kvar hel"
                % (markering.text(), malsort)],
                markering=markering)
        traff = tuple(n for n in kandidater if n in ratt_sort)
        if len(traff) == 1:
            return Markeringsdom(AVGJORD, traff, [
                "%s ar markerad, och den enda av kandidaterna med sorten %s "
                "som meningen namner. Markeringen och dina ord pekar at samma "
                "hall" % (traff[0], malsort)],
                belagg=_belagg(markering, traff[0], malsort),
                markering=markering)
        if len(traff) > 1:
            return Markeringsdom(SMALNAD, traff, [
                "%d av kandidaterna ar markerade. Markeringen smalnar av "
                "fragan men avgor den inte - farre kandidater, inte ett "
                "pahittat val" % len(traff)],
                markering=markering)
        return Markeringsdom(OVIDKOMMANDE, kandidater, [
            "det markerade (%s) ar av ratt sort men ar inte nagon av de "
            "komponenter dina ord kan syfta pa. Markeringen bar da ingen "
            "upplysning om malet, och kandidatlistan star kvar hel"
            % markering.text()],
            markering=markering)

    # Meningen namner ingen sort. Da finns bara EN kalla, och en kalla kan
    # inte styrka sig sjalv - markeringen far smalna av, aldrig avgora.
    traff = tuple(n for n in kandidater if n in markering.namn())
    if not traff:
        return Markeringsdom(OVIDKOMMANDE, kandidater, [
            "det markerade (%s) ar inte nagon av de komponenter dina ord kan "
            "syfta pa. Kandidatlistan star kvar hel" % markering.text()],
            markering=markering)
    return Markeringsdom(SMALNAD, traff, [
        "meningen namner ingen sort, sa markeringen far smalna av men inte "
        "avgora: en enda kalla kan inte styrka sig sjalv. Kvar star %s"
        % ", ".join(traff)],
        markering=markering)


def _belagg(markering, namn, sort):
    """Belagget for att MARKERINGEN avgjorde. Uppslagbart, inte prosa.

    Formen ar TERS med flit. sparr.Scenharkomst granskar ett belagg med kallan
    "scen" genom att sla upp vart ord i turens verktygssvar
    (harness/verifiering.Grund). En prosames som "GRP_A ar markerad i scenen"
    faller darfor pa ordet "markerad", som inget verktygssvar bar - och ett
    belagg som inte gar att sla upp ar inte ett belagg.

    Orden nedan star alla i `get_selection`:s svar: faltnamnet `selected`,
    komponentens `name` och dess `sort`. Belagget gar alltsa att folja hela
    vagen tillbaka till lasningen. Den LASBARA meningen star i domens skal.
    """
    return sparr.ur_scenen("selected %s %s" % (namn, sort))


# ---------------------------------------------------------------------------
# Ogonblicksbilden
# ---------------------------------------------------------------------------

class Ogonblicksbild(object):
    """Scenen i kort form: namn, sort och markering, per komponent.

    `poster` ar (namn, sort, markerad). Den ar avsedd att skickas i VARJE tur,
    och det ar ett krav och inte en ambition: maste modellen fraga vad scenen
    innehaller maste den ocksa VETA att den ska fraga, och det ar precis det
    som inte fungerar for ett pekord. Se TAK_TOKENS.
    """

    __slots__ = ("poster", "kalla", "avkortad")

    def __init__(self, poster=(), kalla="", avkortad=False):
        self.poster = tuple(
            (str(n), str(s) if s else OKAND, bool(m)) for n, s, m in poster)
        self.kalla = kalla
        # Lasningen klipptes vid verktygets tak. Da ar bilden OFULLSTANDIG,
        # och den skillnaden far aldrig forsvinna tyst: "scenen har tre
        # gripdon" kan vara fel om ett fjarde lag i den bortklippta delen.
        self.avkortad = bool(avkortad)

    def __repr__(self):
        return "Ogonblicksbild(%d komponenter, %d markerade%s)" % (
            len(self.poster), len(self.markering()),
            ", AVKORTAD" if self.avkortad else "")

    def antal(self):
        return len(self.poster)

    def fullstandig(self):
        return bool(self.kalla) and not self.avkortad

    def sort(self, namn):
        """Sorten for ett namn, eller OKAND. Gissar aldrig."""
        for n, s, _m in self.poster:
            if n == namn:
                return s
        return OKAND

    def markering(self):
        return Markering([(n, s) for n, s, m in self.poster if m],
                         kalla=self.kalla)

    def scenlage(self):
        """Bilden som ett Scenlage, sa avsikt.granska kan sla upp i den.

        OKAND gar tillbaka till tom strang: det ar sparr.Scenlage:s egen form
        for "sorten gick inte att avgora", och de tva lagren ska inte bara var
        sitt ord for samma sak.
        """
        return sparr.Scenlage(
            [(n, "" if s == OKAND else s) for n, s, _m in self.poster],
            kalla=self.kalla, avkortad=self.avkortad)

    # ---- den form som skickas -------------------------------------------

    def _grupper(self):
        """Namnen per sort, med dubbletter raknade i stallet for upprepade."""
        ordning = []
        per_sort = {}
        for namn, sort, _m in self.poster:
            if sort not in per_sort:
                per_sort[sort] = []
                ordning.append(sort)
            per_sort[sort].append(namn)
        ut = []
        for sort in ordning:
            raknat = []
            sedda = {}
            for namn in per_sort[sort]:
                if namn not in sedda:
                    sedda[namn] = len([1 for n in per_sort[sort] if n == namn])
                    raknat.append(namn if sedda[namn] == 1
                                  else "%s x%d" % (namn, sedda[namn]))
            ut.append((sort, tuple(raknat), len(per_sort[sort])))
        return tuple(ut)

    def _huvud(self):
        m = self.markering()
        return "SCEN %d komponenter, %d markerade [%s]%s" % (
            self.antal(), len(m), self.kalla or "ingen lasning",
            " AVKORTAD" if self.avkortad else "")

    def _markeringsrad(self):
        m = self.markering()
        return "MARKERAT: %s" % (m.text() if not m.tom() else SAKNAS)

    def text(self):
        """Bilden som text. Haller ALLTID TAK_TOKENS.

        Krymper i tre steg, och ordningen sager vad som ar viktigast:
        namnlistan gar forst, rakningen per sort star kvar, och MARKERAT gar
        sist - det ar den raden pekordet faktiskt behover.
        """
        full = self._full_text()
        if matt.tokens(full) <= TAK_TOKENS:
            return full
        kort = self._kort_text()
        if matt.tokens(kort) <= TAK_TOKENS:
            return kort
        return self._nodtext()

    def _full_text(self):
        rader = [self._huvud()]
        for sort, namn, _antal in self._grupper():
            rader.append("%s: %s" % (sort, ", ".join(namn)))
        rader.append(self._markeringsrad())
        return "\n".join(rader)

    def _kort_text(self):
        rader = [self._huvud(),
                 "FOR STOR for att listas i sin helhet; sorterna raknade i "
                 "stallet. Fraga scene_snapshot for hela listan."]
        for sort, _namn, antal in self._grupper():
            rader.append("%s: %d st" % (sort, antal))
        rader.append(self._markeringsrad())
        return "\n".join(rader)

    def _nodtext(self):
        """Sista utvagen: aven markeringen ar for stor att skriva ut.

        Da klipps den, och att den klipptes STAR DAR. En rad som tyst visar
        de forsta tio av trettio markerade vore en markering som ljuger om
        sin egen storlek.
        """
        m = self.markering()
        rader = [self._huvud(),
                 "FOR STOR: bade komponentlistan och markeringen ar klippta."]
        kvar = TAK_TOKENS - matt.tokens("\n".join(rader) + "\nMARKERAT: ")
        namn = []
        for n, s in m.komponenter:
            post = "%s (%s)" % (n, s)
            if matt.tokens(", ".join(namn + [post])) > kvar:
                break
            namn.append(post)
        rader.append("MARKERAT: %s%s" % (
            ", ".join(namn) if namn else SAKNAS,
            " ... och %d till" % (len(m) - len(namn)) if len(m) > len(namn)
            else ""))
        return "\n".join(rader)

    def ryms(self):
        """Sant nar hela bilden far plats. Falskt = texten ar en kortform."""
        return matt.tokens(self._full_text()) <= TAK_TOKENS

    def matt(self):
        """Storleken pa den text som faktiskt skickas."""
        return matt.mat(self.text())


def ogonblicksbild_ur_svar(svar, kalla="scene_snapshot"):
    """En Ogonblicksbild ur `scene_snapshot`:s svar. Hittar ingenting pa."""
    if not isinstance(svar, dict):
        raise TypeError("ogonblicksbild_ur_svar vill ha verktygets svar som "
                        "dict, fick %s" % type(svar).__name__)
    poster = svar.get("components")
    if poster is None:
        raise ValueError(
            "svaret bar inget 'components'-falt. En bild ur ett svar som inte "
            "ar en scenlasning vore en scen nagon hittat pa (I9).")
    return Ogonblicksbild(
        [(_namn(p, kalla), (p or {}).get("sort"),
          bool((p or {}).get("selected"))) for p in poster],
        kalla=kalla, avkortad=bool(svar.get("avkortad")))
