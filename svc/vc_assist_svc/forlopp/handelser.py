# -*- coding: utf-8 -*-
"""Förloppets ordförråd: lägena, händelserna och ovissheten.

Fas 17 (`70_faser.md`) riktar sig till någon utanför bygget. Allt annat i
systemet rapporterar till loggar och mätfiler — alltså till oss. Den här
modulen äger orden som når den som väntar.

## Lägena är HÄRLEDDA, aldrig satta

Ett läge som går att sätta går att sätta fel. `Forlopp.lage` räknas därför
fram ur händelserna varje gång den läses, och `FALLET` är ABSORBERANDE: har
en körning fallit kan ingen senare händelse göra den arbetande igen.

Det är samma felklass kopplaren redan skyddar mot: den ger upp efter tre raka
fel i stället för att mala vidare mot en död PLC och se ut att arbeta
(`M-39`). En förloppsvisning som snurrar vidare efter ett fall gör exakt det
kopplaren vägrar göra.

## Ett hjärtslag är inte framsteg

`24_samtalsloopen.md` §7 kräver en hjärtslagshändelse när tystnaden
överskrider taket. Räknas den som en händelse i tystnadsmätningen blir en död
körning odödlig: varje hjärtslag nollställer klockan och läget står kvar på
ARBETAR för alltid. Tystnaden mäts därför från den senaste VERKLIGA händelsen,
och `HJARTSLAG` är inte en sådan. Mätt i M-64: med hjärtslaget inräknat stod
läget ARBETAR i 600 av 600 avläsningar av en körning där ingenting hände.

## Två tillägg till den slutna listan

`24_samtalsloopen.md` §7 listar sjutton händelser och kallar listan sluten.
Två saker går inte att säga med den, och båda behövs i just den här fasen:

* **att körningen SJÄLV föll.** `VERKTYG_FEL` är ett anrop som föll, inte en
  körning. `AVBRUTEN` är operatörens beslut. Kopplaren som ger upp efter tre
  raka fel har ingen händelse alls i listan.
* **vad grind 1–4 sa.** `DOM` är ögat (grind 5) och `GULD` är guldgrinden.
  Grindarna före dem har ingen händelse, trots att `27_operatorsflodet.md` §5
  steg 10 lovar operatören "fyra grindar med utfall".

`FALLET` och `GRIND` läggs därför till, och står i `TILLAGDA_SORTER` så att
tillägget syns i stället för att glida in. Förslaget till spec ligger i M-64.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

# ---------------------------------------------------------------- lägena

EJ_STARTAT = "EJ STARTAT"
ARBETAR = "ARBETAR"
VANTAR = "VÄNTAR PÅ OPERATÖREN"
TYST = "TYST"
FALLET = "FALLET"
AVBRUTET = "AVBRUTET"
KLART = "KLART"

LAGEN = (EJ_STARTAT, ARBETAR, VANTAR, TYST, FALLET, AVBRUTET, KLART)

# Lägen där ingenting arbetar. En pågåendemarkör i något av dem är precis den
# snurrande symbolen fasens grind förbjuder.
STILLA = (EJ_STARTAT, TYST, FALLET, AVBRUTET, KLART, VANTAR)

# Lägen körningen inte kan lämna. Ett fall går inte att arbeta bort.
ABSORBERANDE = (FALLET, AVBRUTET)

# ------------------------------------------------------------ händelserna

# Den slutna listan ur 24_samtalsloopen.md §7, i spectens egen ordning.
SPECADE_SORTER = (
    "PLAN", "VERKTYG_START", "VERKTYG_KLART", "VERKTYG_FEL",
    "KO_VANTAR", "KO_GODKAND", "KO_AVVISAD",
    "SIM_START", "SIM_STOPP", "OGAT_PROVTAR",
    "DOM", "GULD", "SVAR", "OMSKRIVNING", "DEGRADERAD",
    "AVBRUTEN", "HJARTSLAG",
)

# Våra två tillägg, med skälen i modulens huvud. De står separat för att ett
# tillägg till en sluten lista ska synas.
TILLAGDA_SORTER = ("FALLET", "GRIND")

SORTER = SPECADE_SORTER + TILLAGDA_SORTER

# Händelser som INTE räknas som framsteg när tystnaden mäts. Ett hjärtslag
# säger "jag lever", inte "något hände", och skillnaden är hela poängen.
EJ_FRAMSTEG = ("HJARTSLAG",)

# Händelser som avslutar körningen, och läget var och en leder till.
SLUTLIGA: Dict[str, str] = {
    "FALLET": FALLET,
    "AVBRUTEN": AVBRUTET,
    "SVAR": KLART,
}

# Frasen som betyder ATT NÅGOT ARBETAR JUST NU. Den står som en konstant för
# att grinden ska kunna leta efter den i en FRÄMMANDE renderares text.
PAGAR_MARKOR = "pågår sedan"


class Forloppsfel(Exception):
    """Förloppet går inte att föra, eller doktrinen bröts på vägen ut."""


@dataclass(frozen=True)
class Handelse:
    """En sak som hände, med tidpunkten och — ibland — någon annans ord.

    `ordagrant` är en grinds, ett ögas eller en kompilators EGEN utdata,
    tecken för tecken. Den får ramas in men aldrig skrivas om, och grinden i
    `grind.py` kontrollerar att den nådde ut oförvanskad. En omskrivning på
    vägen till användaren är samma fel som en omskrivning på vägen till
    modellen (`50_grindar.md`).
    """

    sort: str
    text: str
    t: float
    steg: str = ""
    ordagrant: str = ""

    def __post_init__(self):
        if self.sort not in SORTER:
            raise Forloppsfel(
                "okänd händelsesort %r; listan är sluten (%s)"
                % (self.sort, ", ".join(SORTER)))

    @property
    def framsteg(self) -> bool:
        return self.sort not in EJ_FRAMSTEG

    def rad(self, t0: float) -> str:
        namn = self.steg or ""
        if namn == self.text:
            namn = ""
        return "t+%-7.1f %-14s %s%s" % (
            self.t - t0, self.sort, ("%s: " % namn) if namn else "",
            self.text)


# -------------------------------------------------------------- ovissheten

# Klasserna av ovisshet. Skillnaden är inte kosmetisk: den ena går att beta
# av med en bättre körning, den andra gör det aldrig.
UTANFOR_RACKVIDD = "utanför räckvidd"
EJ_PROVAT = "ej prövat i den här körningen"
OVISSHETSKLASSER = (UTANFOR_RACKVIDD, EJ_PROVAT)

# Det ingen grind i kedjan fångar, ordagrant efter `50_grindar.md`:
# "sensorstuds, ställdonsdynamik, fältbussjitter, degraderade lägen och
# verklig hårdvara finns inte i simuleringen. Ögat är felfinnande, aldrig
# bevis." Listan är permanent. En körning kan inte beta av den, och därför
# står den i VARJE visning — också en som gick igenom.
#
# Första fältet är ÖGATS EGET NAMN på saken. Ögats kontrakt kräver sedan v2
# (M-65) en `NOT_SIMULATED`-rad per post i `oga_kontrakt.EJ_SIMULERAT`, och
# det är samma fem saker ur samma stycke i `50_grindar.md`. De två listorna
# får inte glida isär, och `test_forlopp.py::test_rackvidden_ar_ogats_egen_lista`
# håller ihop dem. Namnet står också i skälet, så att den som läser ögats
# rapport bredvid visningen ser att det är samma sak.
RACKVIDDEN = (
    ("sensor_bounce", "sensorstuds",
     "ingen sensormodell; en givare studsar inte här"),
    ("actuator_dynamics", "ställdonsdynamik",
     "don rör sig efter kinematik, inte efter tryck och tröghet"),
    ("fieldbus_jitter", "fältbussjitter",
     "kopplaren går över loopback; ingen fältbuss"),
    ("degraded_modes", "degraderade lägen",
     "brutna givare och nödstopp finns inte i scenen"),
    ("real_hardware", "verklig hårdvara",
     "ingen rad har körts mot en fysisk maskin"),
)


@dataclass(frozen=True)
class Ovisshet:
    """Något systemet inte vet, med skälet till att det inte vet det."""

    namn: str
    skal: str
    klass: str = EJ_PROVAT

    def __post_init__(self):
        if self.klass not in OVISSHETSKLASSER:
            raise Forloppsfel("okänd ovisshetsklass %r" % (self.klass,))
        if not (self.skal or "").strip():
            raise Forloppsfel(
                "ovissheten %r saknar skäl; ett 'vet inte' utan skäl går inte "
                "att göra något åt och är därför ingen upplysning"
                % (self.namn,))


# ------------------------------------------------------------------ stegen

STEG_VANTAR = "väntar"
STEG_PAGAR = "pågår"
STEG_KLART = "klart"
STEG_FOLL = "föll"
STEG_HOPPAT = "hoppat"
STEGSTATUSAR = (STEG_VANTAR, STEG_PAGAR, STEG_KLART, STEG_FOLL, STEG_HOPPAT)


@dataclass
class Steg:
    namn: str
    status: str = STEG_VANTAR
    skal: str = ""
    t_start: Optional[float] = None
    t_slut: Optional[float] = None

    def satt(self, status: str, skal: str = "") -> None:
        if status not in STEGSTATUSAR:
            raise Forloppsfel("okänd stegstatus %r" % (status,))
        self.status = status
        if skal:
            self.skal = skal
