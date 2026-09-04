# Test- och verifieringsprotokoll

Regel: **ingen komponent räknas som klar utan sitt protokoll.** Protokollet
skrivs före koden, precis som facit skrivs före försöket.

## Fem nivåer

| Nivå | Vad | Kräver VC | Körtid |
|---|---|---|---|
| **L0** | statisk: linters, schemavalidering, AST-kontroll, tröskelhärkomst | nej | sekunder |
| **L1** | enhet: rena funktioner på syntetisk indata | nej | sekunder |
| **L2** | kontrakt: protokoll och grammatik mot attrapp | nej | sekunder |
| **L3** | integration: verklig VC i **testprefixet** | ja | minuter |
| **L4** | scenario: bänken med facit | ja | timmar |

**L0 till L2 måste kunna köras utan VC.** Det är ett arkitekturkrav, inte en
bekvämlighet: ögats härledning ska vara en **ren funktion över en serie**, så
den kan prövas på syntetiska serier utan att starta något.

## Vad varje modul måste ha

| Artefakt | Krav |
|---|---|
| Protokollfil | `tests/protocol/<modul>.md`: vad som prövas, hur, vad som är godkänt |
| L1-test | minst ett fall per publik funktion, plus ett randfall |
| L2-test | om modulen har ett kontrakt mot en annan sida |
| Trasigt fall | minst ett fall som **måste** falla. En grind som aldrig fällt är oprövad |
| Guldfil | förväntad utdata, byte för byte, där utdata är ett kontrakt |

## Kontraktstest, de två viktigaste

**Bryggan.** En attrapp som talar protokollet i `31_brygga_protokoll.md` utan VC.
Prövar: ramning, `id`-koppling, alla elva felkoder, timeout, köns fyra tillstånd,
och att en trasig ram inte fäller servern.

**Ögat mot grinden.** Ett tur-och-retur-prov: en känd serie ger en känd domstext,
och grinden ska läsa exakt den domen. Guldfiler för PASS, FAIL, INCONCLUSIVE,
okänd version och **avhuggen rapport**. Den sista är viktigast: en avhuggen
rapport ska bli "inte guld", aldrig ett godkännande.

## Trasiga fixturer

För varje grind finns en fixtur som **ska** fällas:

| Grind | Trasig fixtur |
|---|---|
| Kompilering | ST med syntaxfel |
| Okänt namn | anrop till funktionsblock som inte finns |
| Fel tagg | tagg utanför signalkartan |
| Sekvens | steg i fel ordning |
| Timing | uppehåll kortare än kravet |
| Kapplöpning | två utgångar i samma scan |
| Grepp | `transfer()` på 400 mm avstånd |
| Kollision | bana rakt genom en fixtur |
| Ohederlig | detalj som teleporteras till målet |

**En grind utan trasig fixtur är oprövad och får inte räknas i en fas.**

## Fasacceptans

Varje fas i `70_faser.md` stängs av ett protokoll med denna form:

```
FAS <n> ACCEPTANS
  förutsättning:  <vad som ska finnas>
  steg:           <numrerade, körbara>
  mätning:        <vad som avläses, med enhet>
  godkänt när:    <villkor, kvantitativt>
  trasigt fall:   <vad som ska falla, och att det föll>
  plattform:      Linux ☐   Windows ☐
```

Båda plattformsrutorna ska vara ifyllda innan fasen kallas klar.
Är bara den ena ifylld heter det "klar på Linux, oprövad på Windows".

## Reproducerbarhet

Varje L3- och L4-körning loggar: commit, VC-version, Wine-version eller Windows,
prefix, scenario, seed, och sökväg till ögats rapport. Ett tal utan den raden
är inte ett resultat.

## Regressionsregel

När en bugg hittas skrivs **först** ett test som fäller på den, sedan fixen.
Testet blir kvar. Ärvt arbetssätt: i källprojektet är motbevisning ett eget
levererbart, med egna commit-prefix för mätning och revidering.
