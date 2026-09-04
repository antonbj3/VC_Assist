# -*- coding: utf-8 -*-
"""conf/opcua.json genererad ur signalkartan och kompilatorns debugkarta.

Det här är fas 6:s svar på den öppna frågan i docs/spec/60_plc.md. Svaret blev
inte "namnkonvention **eller** mappfil" utan båda delarna, var och en där den
hör hemma:

* **Nodnamnet** följer en konvention och genereras: ``PLC.<station>.<tagg>``.
  Ingen skriver det för hand, så det kan inte bli fel.
* **Minnesadressen** kommer ur en mappfil vi inte skriver: kompilatorns
  ``debug-map.json``. MÄTT 2026-09-04: OPC UA-plugin läser och skriver PLC:ns
  minne med heltalsparet ``(arr, elem)``
  (``core/src/drivers/plugins/python/opcua/opcua_memory.py``), och paret finns
  bara i debugkartan. Det går varken att härleda ur ``%IX0.0`` eller ur
  variabelnamnet. Gissar man det pekar noden på fel variabel — tyst.

Rättigheterna är inte kosmetik. En OPC UA-klient (VC) ska kunna skriva
scenens givarvärden **in** i PLC:n, men aldrig skriva PLC:ns utgångar: gör den
det styr scenen sig själv och ögat ser en sekvens som PLC:n aldrig körde.
Därför är FRAN_PLC skrivskyddad på nodnivå, och skyddade taggar likaså (I15).

Formatkraven är mätta genom att fältet togs bort och konfigladdaren kördes:
``format_version`` måste vara minst 2, sektionerna ``server``, ``security``,
``users`` och ``address_space`` måste finnas (``users`` får vara tom), och
varje variabel måste ha node_id, browse_name, display_name, datatype,
description, arr, elem, size och permissions.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from .paket import Byggfel, Debugkarta, INSTANSNAMN
from .signalkarta import FRAN_PLC, Signal, Signalkarta

# Konfigfilens formatversion. MÄTT: laddaren avvisar allt under 2 med
# "Unsupported opcua.json format_version 0 (this runtime requires >= 2)".
FORMAT_VERSION = 2

# Plugin-loopens period. Plugin defaultar till 100 ms; 10 ms är valt för att
# ligga under PLC-uppgiftens 20 ms så att synkroniseringen inte blir den
# långsammaste länken. Tur och retur mätt med det här värdet i
# docs/matningar/M-20_plcbandet.md; ändras det gäller inte mätningen.
CYKELTID_MS = 10

NAMESPACE_URI = "urn:openplc:opcua"

# Rättighetsmönstren. "r" = läsa, "rw" = läsa och skriva. Rollnamnen är
# pluginets egna (opcua/user_manager.py); en anonym klient får rollen engineer
# när användarlistan är tom, så engineer måste vara "r" för att en utgång ska
# vara skrivskyddad på riktigt.
LASBAR = {"viewer": "r", "operator": "r", "engineer": "r"}
SKRIVBAR = {"viewer": "r", "operator": "rw", "engineer": "rw"}


def nodid(station: str, tagg: str) -> str:
    """Nodens sträng-identifierare. Platt: punkterna är tecken, inte mappar.

    MÄTT: address_space.py hänger varje enkel variabel direkt under Objects,
    så `PLC.Station1.band_pa` blir NodeId ns=2;s=PLC.Station1.band_pa och
    BrowseName 2:band_pa. Punkterna skapar ingen trädstruktur.
    """
    return "PLC.%s.%s" % (station, tagg)


def variabel(signal: Signal, station: str, debugkarta: Debugkarta,
             instans: str = INSTANSNAMN) -> Dict[str, object]:
    lov = debugkarta.for_tagg(signal.tagg, instans)
    if lov.typ.upper() != signal.typ.namn:
        # Fail-closed: kompilatorn och kartan är oense om typen. Att skriva
        # noden ändå vore att lita på den ena utan att veta vilken.
        raise Byggfel("%s är %s i signalkartan men %s i kompilatorns debugkarta"
                      % (signal.tagg, signal.typ.namn, lov.typ))
    skrivbar = (signal.riktning != FRAN_PLC) and not signal.skyddad
    return {
        "node_id": nodid(station, signal.tagg),
        "browse_name": signal.tagg,
        "display_name": signal.tagg,
        "datatype": signal.typ.namn,
        "description": "%s.%s (%s)" % (signal.komponent, signal.scensignal,
                                       signal.adress.text()),
        "arr": lov.arr,
        "elem": lov.elem,
        "size": lov.storlek,
        "permissions": dict(SKRIVBAR if skrivbar else LASBAR),
    }


def konfiguration(karta: Signalkarta, debugkarta: Debugkarta, endpoint: str,
                  cykeltid_ms: int = CYKELTID_MS,
                  namespace_uri: str = NAMESPACE_URI,
                  instans: str = INSTANSNAMN) -> List[Dict[str, object]]:
    """Hela conf/opcua.json som Python-data, klar att serialiseras.

    `endpoint` är både annonserad adress **och** bindningsadress. MÄTT: server.py
    ger asyncua endpointens hostnamn att binda till, och pluginets
    normalize_endpoint_url skriver om 0.0.0.0 till containerns hostnamn — ett
    namn som ingen utanför containern kan slå upp. Skicka därför in en adress
    klienten faktiskt kan nå, till exempel containerns IP.
    """
    if not karta.signaler:
        raise Byggfel("en tom signalkarta ger en OPC UA-server utan noder")
    variabler = [variabel(s, karta.station, debugkarta, instans)
                 for s in karta.signaler]
    return [{
        "name": "opcua_server",
        "protocol": "OPC-UA",
        "config": {
            "format_version": FORMAT_VERSION,
            "server": {
                "name": "OpenPLC %s" % karta.station,
                "application_uri": "urn:openplc:%s" % karta.station,
                "product_uri": "urn:openplc:runtime",
                "endpoint_url": endpoint,
                "security_profiles": [{
                    "name": "insecure",
                    "enabled": True,
                    "security_policy": "None",
                    "security_mode": "None",
                    "auth_methods": ["Anonymous"],
                }],
            },
            "security": {
                "server_certificate_strategy": "auto_self_signed",
                "trusted_client_certificates": [],
            },
            "users": [],
            "cycle_time_ms": int(cykeltid_ms),
            "address_space": {
                "namespace_uri": namespace_uri,
                "variables": variabler,
                "structures": [],
                "arrays": [],
            },
        },
    }]
