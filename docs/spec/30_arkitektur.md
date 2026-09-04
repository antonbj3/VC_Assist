# Arkitektur

## Tre processer

```
┌─ Visual Components 4.10 (Wine 11.16, prefix ~/.wine-vc) ──────────┐
│  My Commands/vc_assist/                                            │
│    __init__.py      OnAppInitialized() -> startar bryggan          │
│    bridge.py        TCP-server, kö till VC:s egen tråd             │
│    vc_eyes.py       provtagare + analys, skriver sin egen dom      │
│  OPC UA-KLIENT ────────────────────────────────────────┐           │
└────────────┬───────────────────────────────────────────┼───────────┘
             │ TCP 8901, kodsträngar in, JSON-rad ut     │
┌────────────┴───────────────────────────────────────────┼───────────┐
│  vc-assist service (Python 3, värden)                  │           │
│    orchestrator   verktygsloop, honesty, verify        │           │
│    tools/         schema + handlers (data / kodgen)     │           │
│    validator/     regelgrindar på genererad kod         │           │
│    knowledge/     API-index ur vc_python_api.json       │           │
│    gates/         grindkedjan, guldstegen               │           │
│    plc/           ST-generering, deklarationer, deploy  │           │
└────────────┬───────────────────────────────────────────┼───────────┘
             │ REST + JWT                                 │ OPC UA 4840
┌────────────┴───────────────────────────────────────────┴───────────┐
│  OpenPLC v4 (Docker)   OPC UA-SERVER + REST                        │
└────────────────────────────────────────────────────────────────────┘
```

## Sömmen — den bärande designen

**KOD@HEAD** i källprojektet: tjänsten talar aldrig med scenen direkt. Den skickar
Python-kodsträngar över HTTP till en RPC-server inne i applikationen, som kör dem
på applikationens egen tråd, en gång per bildruta, med stdout fångad.
Allt ovanför sömmen är generiskt; allt under är applikationsspecifikt.

Vi återskapar exakt den sömmen. Kraven på VC-sidan är tre:

1. en trådsäker kö till VC:s tråd
2. `exec` med stdout-fångst
3. en JSON-rad sist på stdout som svarskanal

## Varför bryggan måste ligga inne i VC

**MÄTT:** VC har inget externt API. Skripten kör i inbäddad Python **2.7**.
Tillägget startas av `OnAppInitialized()` ur en mapp under `My Commands`.
Agenten måste därför bo utanför, i modern Python, och prata med en tunn brygga inuti.

Bryggan ska vara så liten att den aldrig behöver ändras. All logik ligger utanför.

## Riktningar som är mätta, inte antagna

| Kanal | Riktning | Källa |
|---|---|---|
| Agent → VC | agenten ansluter till bryggan | vi äger båda ändar |
| VC → PLC | VC är **alltid OPC UA-klient** | `Connectivity.OpcUA.xml` |
| Agent → PLC | REST med JWT för inladdning | Autonomy Logic-dok, verifierad |

Att VC alltid är klient är avgörande: OpenPLC **måste** vara server. Det utesluter
OpenPLC v3 och alla klient-till-klient-uppsättningar.

## Portval

| Port | Tjänst | Motiv |
|---|---|---|
| 8901 | VC-bryggan | undviker 8001 och 8226 som källprojektet använder |
| 8902 | agenttjänsten | |
| 4840 | OpenPLC OPC UA | standard |
| 8080 | OpenPLC REST | standard |

## Två exekveringslägen

Ärvs från källan, men **med kön faktiskt kopplad**, vilket den inte är där.

- `/exec_sync` — kör direkt. Endast för läsande anrop och för riggar.
- `/exec_queue` — läggs i kö och kräver godkännande. **Allt som ändrar scenen
  eller laddar in styrkod går här.** Kön ska ha en tömmare från dag ett;
  i källprojektet har `pop_pending_patch` noll anropare och mekanismen är död.

## Öppen fråga som måste lösas i fas 1

Hur man kör kod **per simuleringssteg** ur ett Python-kommando, och vilken takt
det ger. Kandidater: en komponentbeteende-skript som körs på taket, eller en
loop i bryggan som anropar `sim.update()`. **Otestat.** Fas 1 stängs inte
förrän takten är mätt.
