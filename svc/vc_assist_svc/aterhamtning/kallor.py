# -*- coding: utf-8 -*-
"""Källorna: hur ett dött delsystem når ytan.

Fyra saker kan dö mitt i ett uppdrag, och operatören har namngett alla fyra:
*"VC stängs under en körning. Bryggan tappar sin socket. OpenPLC svarar inte.
Modellen tar slut mitt i en reparation."* Varje funktion nedan är den
översättningen för ett av dem, och var och en gör en enda sak: den
**registrerar vad som faktiskt observerades**, med felets egna ord, och låter
läget härledas ur det.

Ingen av dem sätter ett läge. Ett läge som går att sätta går att sätta fel, och
den som sätter det har alltid ett skäl att sätta det snällare än det är.

## Klassificeringen får kosta en fråga till

Ett brutet rör (`ECONNRESET`) betyder inte i sig att VC är borta. Det kan lika
gärna vara vår egen ände som tappade sockeln. Skillnaden avgör vilken väg
tillbaka användaren får, så den får kosta en fråga till: en ny anslutning och
ett nytt `ping`.

Och den frågan måste vara ett **ping**, aldrig en `connect()`. Bryggan
accepterar inuti `tick()`; är pumpen död fullbordar kärnans lyssningskö
handskakningen ändå. En klassificering som stannar vid att röret gick att öppna
skriver `socket_bruten` — alltså *"bryggan svarar fortfarande"* — om en brygga
som är stendöd.
"""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

from .bild import Avlasning, Systembild
from .lagen import (BRYGGAN, MODELLEN, PLC, SOCKET_BRUTEN, TIMEOUT,
                    VC_AVSLUTADES)
from .stegen import BOOTLOGG, BRYGGLOGG

# Felkoder ur `31_brygga_protokoll.md` som säger något om LÄGET, och orsaken
# var och en pekar ut. Koder som inte står här säger något om anropet, inte om
# bryggan, och de får därför ingen orsak alls — en gissad orsak skickar
# operatören åt fel håll med samma tonfall som en riktig.
ORSAK_UR_FELKOD = {
    "E_AUTH": "token_gammalt",
    "E_TIMEOUT": "timeout",
    "E_BUSY": "timeout",
}


# ----------------------------------------------------------------- bryggan

def sondera(bild: Systembild, anslut: Callable[[], Any],
            ping: Callable[[Any], Dict[str, Any]],
            sim: Optional[Callable[[Any], Dict[str, Any]]] = None,
            delsystem: str = BRYGGAN) -> Avlasning:
    """En avläsning som FRÅGAR. Tar callables så den går att prova utan VC.

    `anslut` ska returnera något `ping` kan användas på, eller kasta. Att
    anslutningen gick att öppna noteras — men bara som det den är, aldrig som
    ett livstecken (regel L-1).
    """
    from ..klient import BryggFel
    try:
        forbindelse = anslut()
    except OSError as fel:
        return bild.las_av(delsystem, None, anslutning_oppnades=False,
                           fel="%s: %s" % (type(fel).__name__, fel),
                           orsak="port_upptagen")
    try:
        svar = ping(forbindelse)
    except (BryggFel, OSError) as fel:
        kod = getattr(fel, "kod", "")
        return bild.las_av(delsystem, False, anslutning_oppnades=True,
                           fel="%s: %s" % (type(fel).__name__, fel),
                           orsak=ORSAK_UR_FELKOD.get(kod, ""))
    kor = keepalive = None
    if sim is not None:
        try:
            s = sim(forbindelse)
            kor, keepalive = s.get("kor"), s.get("keepalive")
        except (BryggFel, OSError) as fel:
            # Pingen svarade, alltså LEVER bryggan. Att `sim` inte svarade är
            # en ovisshet om simuleringen, inte ett dödsbesked, och den får
            # inte skrivas om till ett sådant.
            bild.las_av(delsystem, True, anslutning_oppnades=True,
                        fel="sim svarade inte: %s" % (fel,))
    return bild.las_av(delsystem, True, anslutning_oppnades=True,
                       degraded=svar.get("degraded"),
                       ko_vantande=svar.get("ko_vantande"),
                       kor=kor, keepalive=keepalive)


def fran_bryggfel(bild: Systembild, fel, anslutning_oppnades=None,
                  svarade_efterat: Optional[bool] = None) -> Avlasning:
    """Ett fel ur `klient.py` in i bilden, med den klassning som går att göra.

    `svarade_efterat` är svaret på den extra frågan: gick det att ansluta OCH
    få ett `ping` efteråt? Bara `True` betyder att bryggan lever och att det
    var vår ände som tappade sockeln. `None` betyder att ingen frågade, och då
    blir orsaken tom — inte gissad.
    """
    kod = getattr(fel, "kod", "")
    orsak = ORSAK_UR_FELKOD.get(kod, "")
    if svarade_efterat is True:
        orsak = SOCKET_BRUTEN.nyckel
    elif svarade_efterat is False and anslutning_oppnades is False:
        orsak = VC_AVSLUTADES.nyckel
    return bild.las_av(BRYGGAN, False,
                       anslutning_oppnades=anslutning_oppnades,
                       fel="%s: %s" % (type(fel).__name__, fel), orsak=orsak)


def vc_avslutades(bild: Systembild, ordagrant: str) -> Avlasning:
    """VC stängdes under körningen. Anslutningen bröts av att processen dog."""
    return bild.las_av(BRYGGAN, False, anslutning_oppnades=False,
                       fel=ordagrant, orsak=VC_AVSLUTADES.nyckel)


def degraderad(bild: Systembild, ordagrant: str) -> Avlasning:
    """Bryggan svarade, men markerade sig degraderad efter en timeout.

    Det är INTE ett dödsbesked, och visningen får inte göra det till ett:
    läget betyder att tillståndet är okänt tills en läsande körning lyckats.
    """
    return bild.las_av(BRYGGAN, True, anslutning_oppnades=True, degraded=True,
                       fel=ordagrant, orsak=TIMEOUT.nyckel)


def utan_sjalvstart(bild: Systembild, ordagrant: str) -> Avlasning:
    """Bryggan har slagit av sin egen omstart (20 på en minut, M-13)."""
    return bild.las_av(BRYGGAN, True, anslutning_oppnades=True,
                       keepalive=False, fel=ordagrant)


# ----------------------------------------------------------------- OpenPLC

def fran_kopplarvarv(bild: Systembild, varv) -> Avlasning:
    """Ett kopplarvarv. Ett fallet varv är INTE en död PLC.

    Kopplaren tål tre raka fel innan den ger upp (M-39). Ett enstaka fallet
    varv är ett anrop som föll, och att skriva `nere` på en hicka vore att
    döda något som lever — samma gränsdragning `forlopp.kallor` gör en våning
    upp.
    """
    if varv.fel:
        return bild.las_av(PLC, False, fel=str(varv.fel),
                           orsak="plc_svarar_inte")
    return bild.las_av(PLC, True)


def fran_kopplarfel(bild: Systembild, fel) -> Avlasning:
    """Kopplaren gav upp. Ingenting försöker igen, och det är avsiktligt."""
    return bild.las_av(PLC, False, fel=str(fel), orsak="kopplaren_gav_upp")


# ---------------------------------------------------------------- modellen

def fran_modellfel(bild: Systembild, fel) -> Avlasning:
    """Modellen tog slut mitt i en reparation.

    Varvet blev aldrig klart. De grindar som skulle ha kört efter det kördes
    aldrig, och det som INTE kördes får inte se ut som något som höll.
    """
    return bild.las_av(MODELLEN, False, fel=str(fel),
                       orsak="modellen_tog_slut")


def fran_reparationsprotokoll(bild: Systembild, protokoll) -> Avlasning:
    """Slingans utfall in i bilden, när det handlar om modellen."""
    from ..plc.reparation import UTFALL_TAK, UTFALL_TYSTNAD
    if protokoll.utfall == UTFALL_TYSTNAD:
        return bild.las_av(MODELLEN, False,
                           fel="slingan slutade som %s: modellen svarade "
                               "varken text eller anrop" % UTFALL_TYSTNAD,
                           orsak="modellen_tystnade")
    if protokoll.utfall == UTFALL_TAK:
        return bild.las_av(MODELLEN, False,
                           fel="slingan slutade som %s efter %d varv utan att "
                               "grindarna höll"
                               % (UTFALL_TAK, protokoll.max_varv),
                           orsak="reparationstaket")
    return bild.las_av(MODELLEN, True)


# ------------------------------------------------------------- loggarna

def loggarna(katalog: str) -> Dict[str, Optional[str]]:
    """Läser de två loggarna stegen behöver. Ett läsfel blir `None`.

    `None` betyder *gick inte att läsa*, och stegen stannar på den frågan i
    stället för att svara på nästa. En tom sträng vore ett svar — och det
    svaret hade varit fel.
    """
    ut: Dict[str, Optional[str]] = {}
    for namn in (BOOTLOGG, BRYGGLOGG):
        sokvag = os.path.join(katalog, namn)
        try:
            with open(sokvag, encoding="utf-8", errors="replace") as fh:
                ut[namn] = fh.read()
        except OSError:
            ut[namn] = None
    return ut


__all__ = ["ORSAK_UR_FELKOD", "degraderad", "fran_bryggfel",
           "fran_kopplarfel", "fran_kopplarvarv", "fran_modellfel",
           "fran_reparationsprotokoll", "loggarna", "sondera",
           "utan_sjalvstart", "vc_avslutades"]
