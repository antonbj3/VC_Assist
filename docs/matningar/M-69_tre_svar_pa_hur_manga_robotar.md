# M-69 — tre olika svar på "hur många robotar", och bara ett är sant

**Datum:** 2026-09-05 · biblioteket ur M-57, 3201 komponenter
**Rättar:** `svc/vc_assist_svc/katalogsok.py` och verktyget
`search_installed_library`, båda skrivna av mig samma kväll.
**Ursprung:** ett sidofynd i M-59, gjort av databladslagrets mätning.

## Talen

| Hur man räknar | robotar | transportörer |
|---|---:|---:|
| katalognamnet (grunt index) | 1736 | 58 |
| metadatans `Category`-fält (djupt index) | 2169 | 163 |
| **komponentens struktur** | **2202** | **227** |

Strukturen är den sanna: den frågar om komponenten *bär en robotstyrning* eller
*en transportbana*, inte vad någon råkade döpa katalogen till.

Ett sökskikt som filtrerar på katalognamn missar alltså **var fjärde robot och
fyra av fem transportörer**. Mitt gjorde det.

Skillnaden ligger i kataloger som heter `Archiv`, `Legacy`, `extra` och `ultra`.
De innehåller riktiga komponenter, inte skräp.

## Varför familjen bara finns i djupt läge

Familjemarkören (`rSimRobotController`, `rOneWayPath` …) ligger i metadatan vid:

| | byte |
|---|---:|
| min | 294 |
| median | **14 215** |
| p95 | 81 593 |
| max | 1 151 329 |

| Huvudläsning | familjen känd för |
|---:|---:|
| 4 096 B | **2 %** |
| 16 384 B | 53 % |
| 65 536 B | 94 % |
| 262 144 B | 96 % |

En huvudläsning på 4 096 byte — den som ger namnet i 100 % av fallen (M-58) —
hittar familjen i två procent. Den går alltså inte att få billigt.

## Priset, och varför det är värt det

| | sekunder över 3201 komponenter |
|---|---:|
| grunt index (namn, tillverkare, katalognamn) | 1,8 |
| **djupt index (parametrar, gränssnitt, familj)** | **12,8** |

Verktyget bygger nu **djupt**, en gång per process (mätt 8,1 s vid inkoppling
genom verktygslagret). Tolv sekunder för att sluta missa 164 transportörer är en
bra affär.

## Vad som ändrades

* `katalogindex` bär `familj`, läst ur strukturen i djupt läge. Tom sträng när
  ingen markör finns — **inte** `"ovrig"`, för tomt säger att frågan inte gick
  att besvara medan `"ovrig"` låter som ett svar.
* `katalogsok.sok(familj=...)`, och familjen står **före** kategorin på
  träffraden: den sanna storheten först, den härledda efter.
* Verktyget `search_installed_library` har `family`, och dess beskrivning säger
  rakt ut varför den ska föredras framför `category`.
* `has_parameter` beskrivs nu ärligt. M-59 fann att `katalogindex._parametrar`
  är **oscopead**: `Prorunner mk1` har namnet `Length` 24 gånger i sina
  geometrilådor och noll gånger i roten. Listan är en **namnlista**, inte
  komponentens egenskaper.

## Att felet hittades av en annan mätning är poängen

Jag byggde sökskiktet, mätte dess kostnad noggrant (M-60), skrev tretton prov —
och filtrerade på fel storhet. Inget av mina prov kunde upptäcka det, eftersom
alla attrapper hade komponenter i "rätt" katalog.

Det syntes först när databladslagret räknade familjen ur strukturen och fick ett
annat tal. **Två oberoende räkningar av samma sak är det enda som fångar en
räkning som är konsekvent fel.**

## Vad som INTE är mätt

* **699 komponenter har ingen familjemarkör alls.** De är varken robot,
  transportör eller verktyg enligt strukturen. Vad de är har ingen tagit reda
  på — de kan vara staket, bord, produkter eller något som kräver en fjärde
  markör.
* **Om markörlistan är fullständig.** Sju markörer, tagna ur M-59. En komponent
  som bär en robotstyrning under ett annat namn hamnar i de 699.
* **Ordningen mellan markörerna är oprövad.** Noll av 3201 bär både en
  robotstyrning och en transportbana, så prioritetsordningen har aldrig avgjort
  något.
* **Om `Category`-fältet någonsin är sannare än strukturen.** Antaget nej, inte
  mätt.
