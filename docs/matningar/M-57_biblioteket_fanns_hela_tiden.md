# M-57 — komponentbiblioteket fanns hela tiden; jag mätte på fel ställe

**Datum:** 2026-09-04 · VC Premium 4.10 · testprefixet `~/.wine-vc-test`
**Rättar:** `verktyg/katalog.py`, `bank/katalog_index.json`, och slutsatsen i
`M-32` om att det inte finns något lokalt bibliotek.

## Vad som stod

`verktyg/katalog.py` säger, ordagrant:

> **MATT 2026-09-04 i testprefixet: NOLL .vcmx-layouter och FEM komponentfiler
> pa disk.** Det finns alltsa inget lokalt katalogbibliotek att soka i heller.

Slutsatsen blev att katalogverktygen fick servera **65 handskrivna poster**.

## Vad som faktiskt ligger på disken

```
3201 komponenter · 149 tillverkare · 0 oläsbara · 1,8 s att indexera
```

| Tillverkare | antal | | Kategori | antal |
|---|---:|---|---|---:|
| KUKA | 529 | | Robots | **1736** |
| TOYO | 182 | | Single Axis Linear Actuators | 180 |
| ABB | 181 | | Robot Tools | 96 |
| Epson | 180 | | Mobile Robots | 89 |
| Fanuc | 174 | | Conveyors | 58 |
| Mitsubishi Electric | 158 | | Robot Positioners | 50 |
| Kawasaki | 108 | | Machines | 35 |

De ligger under
`<Public Documents>/Visual Components/4.10/Models/Components/<tillverkare>/`,
325 MB, och varje `.vcmx` är ett zip-arkiv med `component.rsc` plus geometrier.

## Varför mätningen blev fel

Den letade på fel ställe. Fem komponentfiler stämmer — i **installationskatalogen**,
och de fem är ritningsmallar (`DrawingTemplateA0.vcm` och syskon). Biblioteket
ligger inte där. Det ligger i Public Documents, och den sökvägen är inte gissad:
VC:s **egen** eCatalog-uppdaterare skriver ut den i sin logg.

```
INFO - Start sync of eCat source:
    Index file: https://ecat.visualcomponents.net/elib/4.10/catalog.xml
    Local folder: C:\users\Public\Documents\Visual Components\4.10\Models
```

Det är samma felklass som `M-34`: ett tal som inte rör sig är inte ett bevis på
att ingenting finns — det kan lika gärna vara ett bevis på att man tittar på fel
ställe. Det är andra gången i det här bygget, och båda gångerna ledde det till
att en nödlösning byggdes runt ett problem som inte fanns.

## Vad felet kostade

Scenerna byggs i dag av **block**. Fas 5 stängdes på 18 layouter med 117
objektpar och noll kollisioner, och det är sant — men allt var lådor.

Fas 5 bevisade alltså **mekanismen**: skapa, placera, mäta avstånd med VC:s egen
geometri, koppla gränssnitt. Den bevisade inte att en riktig cell går att ställa
upp, eftersom den aldrig hade en riktig komponent att ställa upp.

En riktig komponent bär det en låda inte har: verklig omslutande volym i stället
för ett gissat rätblock, monteringsramar, gränssnitt med bestämda namn och
typer, robotens räckvidd, transportörens verkliga längd och riktning.

## Sökvägen antas aldrig

Operatörens invändning, och den är rätt: det ska vara standard oavsett
VC-installation.

`svc/vc_assist_svc/katalogindex.py` **söker** i stället för att anta, på samma
sätt som `install/upptackt.py` gör för tilläggsmappen, och rapporterar hur den
hittade det den hittade. På Windows provas `%PUBLIC%\Documents`, användarens
`Documents` och OneDrive-omdirigerade `Documents`; under Wine provas prefixets
Public Documents och användarkatalog. Versionen läses ur katalognamnet i stället
för att antas, så en maskin med två versioner sida vid sida ger **två fynd** —
vilket är rätt svar, för vilken som ska användas är inte indexbyggarens beslut.

Hittas ingenting blir svaret **tomt med en lista över vad som provades**, aldrig
en gissad sökväg.

VC:s Python-API kan inte hjälpa till: sökning efter `library` ger 0 träffar och
`catalog` ger 1, en utfasad `vcCommand.rebuildECatalog`. Samma vägg som M-38 och
M-55.

## Vad som INTE är gjort

* **Katalogverktygen använder fortfarande de 65 handskrivna posterna.** Indexet
  finns; ingenting läser det än. Det är nästa steg, och det är större än en
  rättelse: bankens uppgifter binder mot den gamla vokabulären
  (`M4_UNKNOWN_URI`), och en bredare vokabulär måste in utan att bryta dem.
* **Ingen komponent ur biblioteket är laddad i VC.** Att filen finns och går att
  läsa är inte samma sak som att `app.load()` ger en användbar komponent.
* **Gränssnitten är inte lästa.** Indexet räknar `rSimInterface`-förekomster
  bara i djupt läge, och djupt läge är inte kört över hela biblioteket.
* **Layoutlösaren har fortfarande aldrig sett en riktig komponent.**
