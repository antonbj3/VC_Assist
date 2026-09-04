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

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .signalkarta import Signalkarta

BORJAN = "(* VC_ASSIST KROPP BORJAR *)"
SLUTET = "(* VC_ASSIST KROPP SLUTAR *)"


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

    # ---- byggande ------------------------------------------------------

    @staticmethod
    def av_karta(karta: Signalkarta, extra_deklarationer: str = "") -> "Skelett":
        """Skelettet för en karta.

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
        delar.append(BORJAN + "\n")
        return Skelett(karta.station, "".join(delar),
                       SLUTET + "\nEND_PROGRAM\n")

    def text(self) -> str:
        """Skelettet som det visas för modellen, med ett tomt fack."""
        return self.huvud + self.svans

    # ---- isättning -----------------------------------------------------

    def satt_in(self, kropp: str) -> str:
        """Lägg kroppen i facket och lämna hela ST-källan.

        Avvisar en kropp som bär markörerna: den skulle sluta facket tidigt.
        """
        _vagra_markorer(kropp)
        if kropp and not kropp.endswith("\n"):
            kropp += "\n"
        return self.huvud + kropp + self.svans

    # ---- uttagning -----------------------------------------------------

    def plocka_ur(self, kalla: str) -> str:
        """Kroppen ur en hel ST-källa, efter att ramen bevisats orörd.

        Fäller på första skiljande raden och säger vilken. Ett svar där
        deklarationerna ändrats är inte en kropp med ett skönhetsfel; det är en
        annan station.
        """
        i = kalla.find(BORJAN)
        if i < 0:
            raise Skelettfel("svaret saknar markoren %s; ramen ar inte den "
                             "utlamnade" % BORJAN)
        j = kalla.find(SLUTET, i + len(BORJAN))
        if j < 0:
            raise Skelettfel("svaret saknar markoren %s" % SLUTET)
        if kalla.find(BORJAN, i + len(BORJAN)) >= 0:
            raise Skelettfel("svaret bar %s mer an en gang" % BORJAN)
        if kalla.find(SLUTET, j + len(SLUTET)) >= 0:
            raise Skelettfel("svaret bar %s mer an en gang" % SLUTET)

        fatt_huvud = kalla[:i + len(BORJAN) + 1]
        fatt_svans = kalla[j:]
        _jamfor("huvudet", self.huvud, fatt_huvud)
        _jamfor("svansen", self.svans, fatt_svans)
        return kalla[i + len(BORJAN) + 1:j]

    # ---- modellsvar ----------------------------------------------------

    def las_svar(self, svar: str) -> str:
        """Ta emot antingen bara kroppen eller hela filen; lämna hela källan.

        Skiljer på de två genom att se om svaret bär markören. En modell som
        svarar med hela filen får sin ram kontrollerad; en som svarar med bara
        kroppen får den kontrollerad genom att markörerna avvisas i `satt_in`.
        """
        if BORJAN in svar or SLUTET in svar:
            return self.satt_in(self.plocka_ur(svar))
        if "END_PROGRAM" in svar.upper() or svar.upper().lstrip().startswith(
                "PROGRAM "):
            # Hela filen, men utan markorerna. Da gar ramen inte att jamfora,
            # och att gissa var kroppen borjar vore att uppfinna en gräns
            # modellen inte respekterade. Fail-closed (I3).
            raise Skelettfel("svaret ser ut som en hel POU men saknar "
                             "markorerna; ramen gar inte att kontrollera")
        return self.satt_in(svar)


def _vagra_markorer(kropp: str) -> None:
    for markor in (BORJAN, SLUTET):
        if markor in kropp:
            rad = kropp[:kropp.find(markor)].count("\n") + 1
            raise Skelettfel("kroppen bar markoren %s; den skulle sluta facket "
                             "for tidigt" % markor, rad)


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
    raise Skelettfel("%s skiljer sig men ingen rad pekar ut sig" % vad)
