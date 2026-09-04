# -*- coding: utf-8 -*-
"""Mätharness för fas 6: tur och retur genom hela PLC-bandet.

**Det här är inte tjänstelager.** Filen kör en mätning och får därför bero på
`asyncua`, som inte ingår i standardbiblioteket. Resten av `plc/` gör det inte
och ska inte göra det. Importen är lat och felet är uttryckligt: en saknad
OPC UA-klient ska säga vad som saknas, inte fela på en attributrad.

Vad som mäts, och varför i den ordningen:

1. **Golvet.** Hur lång tid en läsning tar när ingenting ändras. Utan det talet
   går det inte att säga hur mycket av tur-och-retur-tiden som är PLC:n och hur
   mycket som är klienten och nätet. Mät mätmetoden innan du anklagar systemet.
2. **Tur och retur.** Skriv en insignal, läs tills utsignalen följt med.
   Rapporteras som fördelning, aldrig som ett tal: median, p95, min och max
   över minst 100 mätningar, i minst tre oberoende serier (invariant I5).

Vad mätningen INTE innehåller: Visual Components. Fas 6:s grind i
docs/spec/70_faser.md heter "handskriven ST styr scenen genom OPC UA", och
scenen ingår inte här. Det som mäts är PLC-halvan av bandet: OPC UA-klient ->
plugin -> bildtabell -> scancykel -> tillbaka.

Körs som:  python3 -m vc_assist_svc.plc.matning --hjalp
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from . import opcuakonfig, paket
from .deklarationsgrind import granska
from .openplc import OpenPlcV4
from .signalkarta import Signalkarta, karta_av_rader

# Uppvärmningen räknas inte (I5). Tio varv räcker för att första anslutningens
# sessionsuppsättning och pythonsidans uppvärmning ska ligga utanför serien.
UPPVARMNING = 10
# Minst 100 mätningar per serie, tre serier: kravet i uppgiften och i I5.
PER_SERIE = 120
SERIER = 3
# Läsningar för golvmätningen. Fler än en serie behövs inte: golvet mäter
# klienten och nätet, inte PLC:ns tillstånd.
GOLVLASNINGAR = 200
# Hur ofta utsignalen läses medan vi väntar på att den ska följa med. 0 = så
# fort klienten orkar. En paus här hade lagt sin egen kvantisering ovanpå
# scancykeln och gjort fördelningen omätbar.
POLLPAUS = 0.0
# Tidsgräns på OPC UA-anslutningen. Servern svarade på 6,7 ms i mätningen; fem
# sekunder är alltså en gräns mot att hänga, inte en förväntan.
ANSLUTNINGSGRANS = 5.0
# Hur länge vi väntar på att OPC UA-servern ska komma upp efter att PLC:n
# rapporterat RUNNING. Mätt glapp i körningen 2026-09-04: 1,5 s. 30 s är
# marginal mot en långsammare maskin, inte en förväntan.
OPCUA_UPPSTART = 30.0
# Tak per enskild tur och retur. PLC-uppgiften går var 20:e ms och pluginets
# synkloop var 10:e; en tur och retur som tar över en sekund betyder att något
# har slutat gå, inte att den är långsam.
TAK_S = 1.0


class MatFel(Exception):
    """Mätningen vägrar rapportera ett tal den inte kan stå för."""


def _asyncua():
    """Den **asynkrona** klienten, aldrig asyncua.sync.

    MÄTT 2026-09-04: `asyncua.sync.Client.connect()` mot den här servern blev
    stående utan att förbruka en millisekund CPU — processen låg kvar i fem och
    en halv minut och togs bort för hand. Samma server, samma URL, med den
    asynkrona klienten: ansluten på 6,7 ms. Omslaget är alltså problemet, inte
    protokollet, och mätningen kör därför asyncio direkt.
    """
    try:
        from asyncua import Client, ua
    except ImportError as fel:
        raise MatFel("mätningen kräver paketet asyncua (pip install asyncua): %s"
                     % fel)
    return Client, ua


@dataclass(frozen=True)
class Fordelning:
    """En serie, sammanfattad. Aldrig ett tal — ett tal döljer svansen."""

    namn: str
    antal: int
    median_ms: float
    medel_ms: float
    p95_ms: float
    min_ms: float
    max_ms: float
    stdav_ms: float

    def rad(self) -> str:
        return ("%-22s n=%-4d median %6.2f  medel %6.2f  p95 %6.2f  "
                "min %6.2f  max %7.2f  s %5.2f"
                % (self.namn, self.antal, self.median_ms, self.medel_ms,
                   self.p95_ms, self.min_ms, self.max_ms, self.stdav_ms))

    def till_json(self) -> Dict[str, object]:
        return {"namn": self.namn, "antal": self.antal,
                "median_ms": round(self.median_ms, 3),
                "medel_ms": round(self.medel_ms, 3),
                "p95_ms": round(self.p95_ms, 3),
                "min_ms": round(self.min_ms, 3),
                "max_ms": round(self.max_ms, 3),
                "stdav_ms": round(self.stdav_ms, 3)}


def sammanfatta(namn: str, varden_s: Sequence[float]) -> Fordelning:
    if not varden_s:
        raise MatFel("serien %s är tom; en tom serie är ingen mätning" % namn)
    ms = sorted(v * 1000.0 for v in varden_s)
    # p95 med närmaste-rang: index ceil(0.95*n)-1. Ingen interpolation, så
    # talet är ett värde som faktiskt uppmättes.
    p95 = ms[max(0, int(math.ceil(0.95 * len(ms))) - 1)]
    return Fordelning(namn, len(ms), statistics.median(ms),
                      statistics.fmean(ms), p95, ms[0], ms[-1],
                      statistics.stdev(ms) if len(ms) > 1 else 0.0)


# ---- provstationen -------------------------------------------------------

def provkarta(station: str = "Matstation") -> Signalkarta:
    """Två signaler: en in, en ut. Mindre går inte att mäta en tur och retur på."""
    return karta_av_rader(station, [
        ("Matgivare", "Puls", "matin", "BOOL", "TILL_PLC", "%IX0.0"),
        ("Matdon", "Svar", "matut", "BOOL", "FRAN_PLC", "%QX0.0"),
    ])


def provprogram(karta: Signalkarta) -> str:
    """POU:n. Genomsläpp: utsignalen är insignalen.

    Kroppen är med flit den kortaste som finns: allt annat hade lagt sin egen
    fördröjning i mätningen och gjort talet till något annat än bandets.
    Deklarationerna kommer ur kartan, aldrig ur den här funktionen (I10).
    """
    return (("PROGRAM %s\n" % karta.station) + karta.deklarationstext()
            + "    matut := matin;\n" + "END_PROGRAM\n")


def provkalla(karta: Signalkarta, intervall: str = paket.TASKINTERVALL) -> str:
    """POU + CONFIGURATION, alltså den fil kompilatorn får.

    Delningen är inte kosmetisk. **MÄTT:** ST-lagrets läsare kan POU:er men
    inte CONFIGURATION — den fäller `väntade PROGRAM, FUNCTION_BLOCK, ...
    men fick 'CONFIGURATION'`. Grind 2 och grind 3 döms därför på POU-delen,
    som är den enda del modellen skriver. CONFIGURATION-delen genereras av
    paket.konfigurationstext() och kommer aldrig från en modell.
    """
    return provprogram(karta) + paket.konfigurationstext(karta.station,
                                                        intervall=intervall)


# ---- mätningarna ---------------------------------------------------------

async def mat_golv(nod_in, antal: int = GOLVLASNINGAR) -> Fordelning:
    tider: List[float] = []
    for i in range(antal + UPPVARMNING):
        t0 = time.perf_counter()
        await nod_in.read_value()
        t1 = time.perf_counter()
        if i >= UPPVARMNING:
            tider.append(t1 - t0)
    return sammanfatta("golv: en lasning", tider)


async def mat_tur_och_retur(nod_in, nod_ut, ua, antal: int = PER_SERIE,
                            namn: str = "tur och retur") -> Fordelning:
    """Skriv insignalen, mät tills utsignalen följt med.

    Varje mätning växlar värde. Att alltid skriva samma värde hade mätt
    ingenting: PLC:n hade redan haft rätt svar på utgången.
    """
    tider: List[float] = []
    vantat = bool(await nod_ut.read_value())
    for i in range(antal + UPPVARMNING):
        nytt = not vantat
        t0 = time.perf_counter()
        await nod_in.write_value(
            ua.DataValue(ua.Variant(nytt, ua.VariantType.Boolean)))
        while True:
            if bool(await nod_ut.read_value()) == nytt:
                break
            if time.perf_counter() - t0 > TAK_S:
                raise MatFel("utsignalen följde inte med inom %.1f s vid varv %d"
                             % (TAK_S, i))
        t1 = time.perf_counter()
        vantat = nytt
        if i >= UPPVARMNING:
            tider.append(t1 - t0)
    return sammanfatta(namn, tider)


async def _anslut(klient, tidsgrans: float = OPCUA_UPPSTART, paus: float = 0.5):
    """Anslut, med tålamod för att servern startar efter PLC:n.

    MÄTT: runtimen rapporterar RUNNING och startar OPC UA-servern **efter**
    det. I körningen 2026-09-04 låg 1,5 s mellan "PLC State: RUNNING" och
    "OPC-UA server started". Ansluter man i det glappet får man
    ConnectionRefused, och den skulle felaktigt se ut som att servern inte
    finns. Därför försöker vi om, och först när tiden gått är svaret nej.
    """
    import asyncio
    slut = time.time() + tidsgrans
    senaste = None
    while time.time() < slut:
        try:
            await klient.connect()
            return
        except (ConnectionRefusedError, OSError, asyncio.TimeoutError) as fel:
            senaste = fel
            await asyncio.sleep(paus)
    raise MatFel("nådde inte OPC UA-servern inom %.0f s: %s"
                 % (tidsgrans, senaste))


async def _mat(endpoint: str, station: str, serier: int,
               per_serie: int) -> Dict[str, object]:
    Client, ua = _asyncua()
    ut: Dict[str, object] = {"endpoint": endpoint, "station": station}
    klient = Client(url=endpoint, timeout=ANSLUTNINGSGRANS)
    t0 = time.perf_counter()
    await _anslut(klient)
    ut["anslutning_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    try:
        nod_in = klient.get_node("ns=2;s=%s"
                                 % opcuakonfig.nodid(station, "matin"))
        nod_ut = klient.get_node("ns=2;s=%s"
                                 % opcuakonfig.nodid(station, "matut"))
        golv = await mat_golv(nod_in)
        print(golv.rad(), file=sys.stderr)
        ut["golv"] = golv.till_json()
        serielista = []
        for n in range(serier):
            f = await mat_tur_och_retur(nod_in, nod_ut, ua, per_serie,
                                        "tur och retur %d" % (n + 1))
            serielista.append(f.till_json())
            print(f.rad(), file=sys.stderr)
        ut["serier"] = serielista
    finally:
        await klient.disconnect()
    return ut


def mat(endpoint: str, station: str, serier: int = SERIER,
        per_serie: int = PER_SERIE) -> Dict[str, object]:
    import asyncio
    return asyncio.run(_mat(endpoint, station, serier, per_serie))


# ---- hela kedjan ---------------------------------------------------------

def kor(bas: str, anvandare: str, losenord: str, strucpp_paket: str,
        runtime_include: str, byggkatalog: str, endpoint: str,
        station: str = "Matstation", serier: int = SERIER,
        per_serie: int = PER_SERIE, node: str = "node",
        intervall: str = paket.TASKINTERVALL) -> Dict[str, object]:
    """Hela kedjan: grind 3, kompilering, uppladdning, start, mätning."""
    karta = provkarta(station)
    kalla_pou = provprogram(karta)
    kalla = provkalla(karta, intervall)

    # Grind 3 före grind 1: en tagg som inte finns i kartan ska aldrig hinna
    # bli C++. Kostar millisekunder, sparar en byggcykel.
    dom = granska(kalla_pou, karta)
    if not dom.ok:
        raise MatFel("grind 3 fällde provprogrammet:\n%s" % dom)

    # Kedjan är tvådelad, och det går inte att undvika: OPC UA-konfigurationen
    # behöver (arr, elem) ur kompilatorns debugkarta, men konfigurationen ska
    # ligga i det arkiv som kompileras. Alltså kompilera först för kartans
    # skull, bygg konfigurationen, och bygg sedan arkivet.
    forbygge = paket.kompilera(kalla, os.path.join(byggkatalog, "forbygge"),
                               strucpp_paket, node=node)
    konfig = opcuakonfig.konfiguration(karta, forbygge, endpoint)
    zipvag, debugkarta = paket.bygg_projekt(
        kalla, os.path.join(byggkatalog, "arkiv"), strucpp_paket,
        runtime_include, opcua_konfig=konfig, node=node)

    klient = OpenPlcV4(bas, anvandare, losenord, tillat_osignerat=True)
    klient.skapa_forsta_anvandare()
    version = klient.version()
    tillstand = klient.ladda_och_starta(zipvag)
    resultat = mat(endpoint, station, serier, per_serie)
    resultat["runtime"] = version
    resultat["plc_tillstand"] = tillstand
    resultat["debugkarta"] = [l.sokvag for l in debugkarta.lov]
    resultat["taskintervall"] = intervall
    return resultat


def _argument(argv=None):
    p = argparse.ArgumentParser(
        description="Mät tur och retur genom OpenPLC v4 och OPC UA.")
    p.add_argument("--bas", required=True,
                   help="REST-basadress, t.ex. https://127.0.0.1:18443")
    p.add_argument("--anvandare", default="vcassist")
    p.add_argument("--losenord", default="vcassist")
    p.add_argument("--strucpp", required=True,
                   help="uppackad strucpp-npm-katalog (den med dist/ och libs/)")
    p.add_argument("--runtime-include", required=True,
                   help="strucpp runtime/include")
    p.add_argument("--byggkatalog", required=True)
    p.add_argument("--endpoint", required=True,
                   help="opc.tcp://<adress>:4840/openplc/opcua")
    p.add_argument("--station", default="Matstation")
    p.add_argument("--serier", type=int, default=SERIER)
    p.add_argument("--per-serie", type=int, default=PER_SERIE)
    p.add_argument("--node", default="node")
    p.add_argument("--intervall", default=paket.TASKINTERVALL,
                   help="PLC-uppgiftens period som TIME-literal, t.ex. T#20ms")
    return p.parse_args(argv)


def main(argv=None) -> int:
    a = _argument(argv)
    resultat = kor(a.bas, a.anvandare, a.losenord, a.strucpp,
                   a.runtime_include, a.byggkatalog, a.endpoint, a.station,
                   a.serier, a.per_serie, a.node, a.intervall)
    print(json.dumps(resultat, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
