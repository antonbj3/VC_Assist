# Reserverade mätningsnummer

En tröskel får peka på en mätning som **ännu inte är gjord**, men bara om numret
står här. Utan den regeln blir `# PRELIMINÄR. Sätts av mätning M-99.` en formel
som ser ut som härkomst utan att vara det.

Mätt 2026-09-04: av 125 tröskelkonstanter pekade **27 på mätningar som inte
fanns** — M-10 fjorton gånger, M-18 åtta, M-19 fem. Lintern godkände formen
`M-\d+` utan att slå upp den.

| Nr | Vad den ska mäta | Vad som väntar på den |
|---|---|---|
| M-10 | Ögats kalibrering mot handbyggda celler: greppfönster, stabilitetsmått, teleportgräns, bärningens vinkelgräns, placeringstolerans | `oga_analys.py` och `oga_provtagning.py`, fjorton trösklar |
| M-18 | Robotledernas provtagning: stillaståendegräns per led, hastighets- och accelerationströsklar, hur nära en ledgräns räknas som nådd | `oga_harledning.py`, ledanalysen |
| M-19 | Stationsstatistik och PLC-fas: hur färsk en PLC-avläsning måste vara för att höra till samma tidssteg, marginal i genomströmningsjämförelser | `oga_analys.py`, `oga_provtagning.py`, `oga_harledning.py` |
| M-21 | Menyytan i VC: registrerar `addMenuItem` ett synligt val, returtyp, fyrar kommandot, landar `print()` i utdatafönstret, stoppar en öppen `messageBox` pumpen | `26_appen.md`, hela menyavsnittet |
| M-22 | Går VC att använda medan pumpen går och ögat provtar — inte headless | fas 1:s sista öppna rad |
| M-23 | Tid från VC:s processtart till lyssnande port, över tio starter | grön-start-gränsen |
| M-24 | Hela vägen på Windows | I17 |
| M-25 | Lyckas `connect()` mot en död pump genom Wines winsock | återhämtningens tidsgränser |
| M-26 | Köns pollningströsklar mot en levande pump | `utforare.py` |
| M-27 | Svep över alla skrivande verktyg mot en levande pump: vilka fler som dödar pumpen | `skrivgrind.DODANDE_ANROP` |
| M-28 | Språkmodellagrets takt och kostnad | `23_llm_granssnitt.md` |
| M-29 | Kontextbudgeten över banken | `25_kontextbudget.md` |
| M-30 | Layoutmotorn mot en handbyggd VC-cell | `layout/`, samtliga trösklar |

## Regel

Ett reserverat nummer får användas **endast** tillsammans med ordet
`PRELIMINÄR`. När mätningen är gjord skrivs `docs/matningar/M-NN_<namn>.md`,
raden tas bort här, och trösklarna uppdateras med det mätta värdet.

Ett nummer som varken är en fil eller står här är ett **linterfel**.
