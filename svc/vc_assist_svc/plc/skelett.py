# -*- coding: utf-8 -*-
"""Skelettet: deklarationerna är låsta, och låset går att kontrollera.

`docs/spec/61_st_generering.md` säger att modellen aldrig får skriva
deklarationer eller taggnamn, och att den bara skriver kroppen. Fram tills nu
var det en **uppmaning**: kartan kunde bygga ett program, men ingenting tog emot
modellens svar och bevisade att den höll sig i sitt fack.

Skillnaden är hela poängen. En regel som står i en promptsträng är en bön. En
regel som avvisar mekaniskt är en grind. Det här är grinden.

## Formen

    PROGRAM Press
    VAR ... END_VAR                          <- ramen, genererad ur kartan
    (* VC_ASSIST KROPP BORJAR *)
        modellens rader                      <- facket
    (* VC_ASSIST KROPP SLUTAR *)
    END_PROGRAM

Ramen är allt utanför facket. `plocka_ur` jämför den mottagna ramen **tecken för
tecken** mot den genererade. Skiljer sig ett enda tecken avvisas svaret, och
avvisandet pekar ut raden.

## Två sätt att svara, båda hanterade

En modell svarar antingen med **bara kroppen** eller med **hela filen**. Båda
förekommer, och att kräva det ena är att bygga en grind som fäller på form i
stället för på innehåll. `las_svar` tar emot båda och skiljer dem åt på om
svaret bär ramens ord.

## Att fly ur facket

En modell som skriver `END_PROGRAM` mitt i sin kropp, eller som skriver
markörerna själv, skulle kunna sluta facket tidigt och fortsätta utanför.
Därför avvisas en kropp som bär någon av markörerna, och ramjämförelsen fäller
resten: raden hamnar i ramen, och ramen stämmer inte.

ASCII genomgående, av samma skäl som signalkartan kräver det.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .signalkarta import Signalkarta

BORJAN = "(* VC_ASSIST KROPP BORJAR *)"
SLUTET = "(* VC_ASSIST KROPP SLUTAR *)"

# Ett ANDRA fack, for modellens egna arbetsvariabler.
#
# VARFOR DET BEHOVS - MATT I M-62. Ramen var last nar slingan startade, sa en
# reparation som behovde en ny arbetsvariabel (en TON, en flankdetektor, en
# diagnosbit) inte gick att gora inifran slingan. Grind 2 fallde nasta varv pa
# ODEKLARERAD. Pa den snava ramen slutade 16 AV 24 slingor sa - en kod som inte
# handlar om styrlogik alls, utan om att ramen saknade en variabel.
#
# Med andra ord: den snava ramen matte RAMENS STYVHET och inte metoden. Och det
# galler en sprakmodell precis lika hart som baslinjen.
#
# VAD SOM INTE ANDRAS. Modellen far fortfarande ALDRIG skriva en signal.
# Signalernas deklarationer kommer ur kartan och ligger i ramen; det har facket
# tar bara variabler som ar lokala for programmet. Skillnaden ar mekanisk och
# provas: en adress (AT %IX0.0) eller ett namn som krockar med en tagg avvisas.
ARBETSVAR_BORJAN = "(* VC_ASSIST ARBETSVARIABLER BORJAR *)"
ARBETSVAR_SLUTET = "(* VC_ASSIST ARBETSVARIABLER SLUTAR *)"

# De typer en arbetsvariabel far ha. Elementara typer ur ST-lagret plus
# standardfunktionsblocken - listorna ags dar och speglas har genom import, sa
# de inte kan glida isar.
def _tillatna_typer():
    from ..st import stdbibliotek as SB
    from ..st import typer as T
    return frozenset(T.ELEMENTARA) | frozenset(SB.BLOCK)


# En rad i arbetsvariabelfacket: NAMN : TYP ;
_ARBETSRAD = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s*;\s*$")
_HAR_ADRESS = re.compile(r"\bAT\s+%", re.I)


class Skelettfel(Exception):
    """Svaret går inte att lägga tillbaka i skelettet."""

    def __init__(self, text: str, rad: int = 0):
        Exception.__init__(self, text)
        self.rad = rad


@dataclass(frozen=True)
class Skelett:
    """Ramen runt modellens fack, för en station.

    `huvud` och `svans` är ramens två halvor, båda med avslutande radbrytning.
    De genereras ur kartan och ägs aldrig av modellen.
    """

    station: str
    huvud: str
    svans: str
    # Mellan arbetsvariabelfacket och kroppsfacket. Tom nar skelettet byggts
    # utan arbetsvariabelfack (aldre form; las_svar tar da bara en kropp).
    mitt: str = ""

    # ---- byggande ------------------------------------------------------

    @staticmethod
    def av_karta(karta: Signalkarta, extra_deklarationer: str = "",
                 arbetsvariabler: bool = False) -> "Skelett":
        """Skelettet för en karta.

        `arbetsvariabler=True` ger modellen ett **eget** VAR-fack. Skälet är
        mätt (M-62): med en låst ram slutade 16 av 24 reparationsslingor i
        `ODEKLARERAD` — inte för att logiken var fel, utan för att reparationen
        behövde en variabel ramen inte hade. Den ramen mätte sin egen styvhet.

        `extra_deklarationer` är arbetsvariabler som stationen behöver men som
        inte är signaler — timers till exempel. De hör till ramen och inte till
        modellen, av samma skäl som signalerna gör det: en tagg som modellen
        hittar på kan inte bindas till något.
        """
        delar = ["PROGRAM %s\n" % karta.station, karta.deklarationstext()]
        if extra_deklarationer:
            if not extra_deklarationer.endswith("\n"):
                extra_deklarationer += "\n"
            delar.append(extra_deklarationer)
        if not arbetsvariabler:
            delar.append(BORJAN + "\n")
            return Skelett(karta.station, "".join(delar),
                           SLUTET + "\nEND_PROGRAM\n")
        delar.append("VAR\n" + ARBETSVAR_BORJAN + "\n")
        return Skelett(karta.station, "".join(delar),
                       SLUTET + "\nEND_PROGRAM\n",
                       mitt=ARBETSVAR_SLUTET + "\nEND_VAR\n" + BORJAN + "\n")

    @property
    def har_arbetsvariabler(self) -> bool:
        return bool(self.mitt)

    def text(self) -> str:
        """Skelettet som det visas för modellen, med tomma fack."""
        return self.huvud + self.mitt + self.svans

    # ---- isättning -----------------------------------------------------

    def satt_in(self, kropp: str, arbetsvariabler: str = "") -> str:
        """Lägg kroppen (och arbetsvariablerna) i sina fack.

        Avvisar text som bär markörerna: den skulle sluta ett fack tidigt.
        """
        _vagra_markorer(kropp)
        if kropp and not kropp.endswith("\n"):
            kropp += "\n"
        if not self.har_arbetsvariabler:
            if arbetsvariabler.strip():
                raise Skelettfel("the skeleton has no work-variable slot; "
                                 "build it with arbetsvariabler=True")
            return self.huvud + kropp + self.svans
        _vagra_markorer(arbetsvariabler)
        if arbetsvariabler and not arbetsvariabler.endswith("\n"):
            arbetsvariabler += "\n"
        return self.huvud + arbetsvariabler + self.mitt + kropp + self.svans

    # ---- uttagning -----------------------------------------------------

    def granska_arbetsvariabler(self, text: str, karta: Signalkarta) -> None:
        """Fäller ett arbetsvariabelfack som inte är arbetsvariabler.

        Fyra fall, alla fail-closed. Facket finns för att modellen ska kunna ge
        sig själv en timer — inte för att smyga in en signal genom bakdörren.

        1. **En adress.** `AT %IX0.0` gör variabeln till en plats i bildtabellen,
           alltså en signal. Signaler kommer ur kartan, punkt.
        2. **Ett namn kartan redan äger.** ST är skiftlägesokänsligt, så `Don`
           och `don` är samma variabel; en lokal med samma namn hade skuggat
           signalen och koden hade sett rätt ut medan ingenting nådde scenen.
        3. **En okänd typ.** Bara elementära typer och standardfunktionsblocken.
           Listorna ägs av ST-lagret och speglas hit genom import.
        4. **En rad som inte är en deklaration.** Det som inte går att läsa
           avvisas; att hoppa över den vore ett tyst bortfall.
        """
        if _HAR_ADRESS.search(text):
            raise Skelettfel("a work variable may not have an address (AT %...); "
                             "that makes it a signal, and signals come "
                             "from the map")
        taggar = set(s.tagg.upper() for s in karta.signaler)
        tillatna = _tillatna_typer()
        sedda = set()
        for n, rad in enumerate(text.splitlines(), 1):
            if not rad.strip() or rad.strip().startswith("(*"):
                continue
            m = _ARBETSRAD.match(rad)
            if not m:
                raise Skelettfel("line %d of the work variables cannot be read "
                                 "as a declaration: %r" % (n, rad.strip()), n)
            namn, typ = m.group(1), m.group(2)
            if namn.upper() in taggar:
                raise Skelettfel("work variable %s has the same name as a "
                                 "signal in the map; ST is case-insensitive "
                                 "and it would have shadowed the signal" % namn, n)
            if namn.upper() in sedda:
                raise Skelettfel("work variable %s is declared twice"
                                 % namn, n)
            sedda.add(namn.upper())
            if typ.upper() not in tillatna:
                raise Skelettfel(
                    "okand typ %s for arbetsvariabeln %s; tillatna ar de "
                    "elementara typerna och standardfunktionsblocken"
                    % (typ, namn), n)

    def plocka_arbetsvariabler(self, kalla: str) -> str:
        """Arbetsvariabelfackets innehåll ur en hel ST-källa."""
        if not self.har_arbetsvariabler:
            return ""
        i = kalla.find(ARBETSVAR_BORJAN)
        j = kalla.find(ARBETSVAR_SLUTET, i + len(ARBETSVAR_BORJAN)) if i >= 0 else -1
        if i < 0 or j < 0:
            raise Skelettfel("the response is missing the work-variable slot's markers")
        return kalla[i + len(ARBETSVAR_BORJAN) + 1:j]

    def plocka_ur(self, kalla: str) -> str:
        """Kroppen ur en hel ST-källa, efter att ramen bevisats orörd.

        Fäller på första skiljande raden och säger vilken. Ett svar där
        deklarationerna ändrats är inte en kropp med ett skönhetsfel; det är en
        annan station.
        """
        i = kalla.find(BORJAN)
        if i < 0:
            raise Skelettfel("the response is missing the marker %s; this is "
                             "not the frame that was handed out" % BORJAN)
        j = kalla.find(SLUTET, i + len(BORJAN))
        if j < 0:
            raise Skelettfel("the response is missing the marker %s" % SLUTET)
        if kalla.find(BORJAN, i + len(BORJAN)) >= 0:
            raise Skelettfel("the response carries %s more than once" % BORJAN)
        if kalla.find(SLUTET, j + len(SLUTET)) >= 0:
            raise Skelettfel("the response carries %s more than once" % SLUTET)

        fatt_svans = kalla[j:]
        _jamfor("svansen", self.svans, fatt_svans)
        if not self.har_arbetsvariabler:
            _jamfor("huvudet", self.huvud, kalla[:i + len(BORJAN) + 1])
            return kalla[i + len(BORJAN) + 1:j]
        # Med ett arbetsvariabelfack delas ramen i tva: huvudet fram till
        # arbetsvariabelmarkoren, och mitten mellan facken. Det som ligger
        # DAREMELLAN ar modellens, och jamfors inte - det ar hela poangen.
        a = kalla.find(ARBETSVAR_BORJAN)
        b = kalla.find(ARBETSVAR_SLUTET, a + len(ARBETSVAR_BORJAN)) if a >= 0 else -1
        if a < 0 or b < 0:
            raise Skelettfel("the response is missing the work-variable slot's markers")
        _jamfor("huvudet", self.huvud, kalla[:a + len(ARBETSVAR_BORJAN) + 1])
        _jamfor("mitten", self.mitt, kalla[b:i + len(BORJAN) + 1])
        return kalla[i + len(BORJAN) + 1:j]

    # ---- modellsvar ----------------------------------------------------

    def las_svar(self, svar: str) -> str:
        """Ta emot antingen bara kroppen eller hela filen; lämna hela källan.

        Skiljer på de två genom att se om svaret bär markören. En modell som
        svarar med hela filen får sin ram kontrollerad; en som svarar med bara
        kroppen får den kontrollerad genom att markörerna avvisas i `satt_in`.
        """
        if BORJAN in svar or SLUTET in svar:
            if self.har_arbetsvariabler:
                return self.satt_in(self.plocka_ur(svar),
                                    self.plocka_arbetsvariabler(svar))
            return self.satt_in(self.plocka_ur(svar))
        if "END_PROGRAM" in svar.upper() or svar.upper().lstrip().startswith(
                "PROGRAM "):
            # Hela filen, men utan markorerna. Da gar ramen inte att jamfora,
            # och att gissa var kroppen borjar vore att uppfinna en gräns
            # modellen inte respekterade. Fail-closed (I3).
            raise Skelettfel("the response looks like a whole POU but is "
                             "missing the markers; the frame cannot be checked")
        return self.satt_in(svar)


def _vagra_markorer(kropp: str) -> None:
    for markor in (BORJAN, SLUTET):
        if markor in kropp:
            rad = kropp[:kropp.find(markor)].count("\n") + 1
            raise Skelettfel("the body carries the marker %s; it would end "
                             "the slot too early" % markor, rad)


def _jamfor(vad: str, vantat: str, fatt: str) -> None:
    """Tecken för tecken, och peka ut raden. Ingen normalisering.

    Att jämföra normaliserat hade varit vänligare och sämre: ett borttaget
    indrag i en deklaration är en ändrad deklaration, och grinden ska inte ha en
    åsikt om vilka ändringar som är oskyldiga.
    """
    if vantat == fatt:
        return
    v = vantat.splitlines()
    f = fatt.splitlines()
    for n in range(max(len(v), len(f))):
        rv = v[n] if n < len(v) else None
        rf = f[n] if n < len(f) else None
        if rv != rf:
            raise Skelettfel(
                "%s ar andrat pa rad %d: vantade %r, fick %r"
                % (vad, n + 1, rv, rf), n + 1)
    raise Skelettfel("%s differs but no line stands out" % vad)
