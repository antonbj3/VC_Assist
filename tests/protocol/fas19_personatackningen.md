# Fas 19 — Personatäckningen

**Grind som stänger fasen:** varje arbetssteg i profilerna är *antingen* täckt
av ett namngivet verktyg *eller* märkt `UI`/`.NET` med skäl. Andelen täckta
steg rapporteras per profil, och **nämnaren är alla steg** — inte bara de vi
råkar klara. Trasigt fall: ett steg som påstås täckt av ett verktyg som inte
gör det måste fällas.

Körs:

```
python3 tests/protocol/kor_fas19_tackning.py [--json ut.json]
```

Kräver **inte** att Visual Components kör. Domen är spec mot API-index och
verktygsregister, allt i repot.

Under sviten: `python3 -m pytest tests/enhet/test_personatackning.py -q`
(30 prov). Provfilen laddar körningen som modul, så protokollets femton
trasiga fall körs varje gång sviten körs — inte bara när någon minns att köra
skriptet.

---

## Vad fasen mäter

| Fråga | Var svaret står |
|---|---|
| Andel täckta steg per profil, med alla steg i nämnaren | avsnitt 1 i utskriften |
| Hur mycket som ligger utanför räckvidd (`UI`/`.NET`) | avsnitt 2 |
| Byggd kapacitet ingen profil behöver | avsnitt 3 |
| Om utbildaren verkligen delar API-yta med säljaren | avsnitt 3b |
| Om specen själv håller | avsnitt 4 |
| Om grinden fäller det den ska | avsnitt 5 |

Talen och deras tolkning: `docs/matningar/M-100_personatackningen.md`.
Nämnaren: `docs/spec/48_personaprofiler.md`. Domaren:
`svc/vc_assist_svc/personatackning.py`.

---

## Regeln bakom nämnaren

En täckningssiffra är den lättaste grinden att göra meningslös. Om nämnaren
får vara *"de steg vi råkade skriva ned"* stiger talet av att man **slutar
skriva steg**. Fyra spärrar, alla mekaniska:

1. **Golv per profil** (`GOLV` i `personatackning.py`). Antalet steg får bara
   gå uppåt.
2. **`KANDA_PROFILER`.** En struken profil fäller.
3. **Löpande numrering.** Ett urklippt mittsteg lämnar ett hål och fäller.
4. **`UI`/`.NET` är bevakade.** Ett steg får bara lyftas ur räckvidden om det
   pekar på ett namn som *inte* finns i Python-API:t, och `.NET`-namnet måste
   dessutom finnas i `docs/referens/vc_dotnet/`.

---

## Protokollpunkter

Var och en har ett förutbestämt grönt svar. Ingen får besvaras med "borde
fungera".

| # | Punkt | Grönt svar |
|---|---|---|
| 1 | Specen läses utan Specfel | sju profiler, 228 steg |
| 2 | Varje profil finns i `KANDA_PROFILER` | P1–P7 |
| 3 | Varje steg har krav, verkan och besked om täckning | inga tomma celler |
| 4 | Varje API-namn slås upp i indexet | 0 okända av 259 |
| 5 | Varje `.NET`-namn slås upp i `vc_dotnet/*.xml` | 0 okända |
| 6 | Varje `UI`-namn saknas i Python-indexet, även med annat skiftläge | 0 falska |
| 7 | Varje `TJÄNST`-modul finns på disk | 0 okända |
| 8 | Varje namngivet verktyg finns i registret | 0 okända av 122 |
| 9 | Varje `ändrar`-steg täcks av minst ett `write`-verktyg | 0 `FEL_VERKAN` |
| 10 | `tackta + utanfor + obyggda = steg` för varje profil | summerar |
| 11 | Antalet steg per profil ligger på eller över golvet | 7 av 7 |
| 12 | Domen över specen | 0 fällningar |
| 13 | Kontrollfixturen (den gröna) fälls inte | grön |
| 14 | De femton trasiga fallen fälls, var och en med sin egen kod | 15 av 15 |
| 15 | De tre oläsbara specerna avvisas i läsningen | 3 av 3 |
| 16 | Varje felkod i domaren har minst en trasig fixtur | 0 utan |

---

## De trasiga fallen

Ett protokoll utan trasiga fall är en förhoppning som har fått ett filnamn.
Var och en av dessa är en **hel minispec** som körs mot samma domare som den
verkliga specen. Den gröna kontrollen står först: går den inte igenom mäter
fixturerna domaren i stället för specen.

| # | Fall | Vad det riggar | Kod som måste falla |
|---|---|---|---|
| K | kontrollen | en spec som håller | *ingen* |
| T1 | verktyget finns inte | `ladda_komponenten` som täckande | `OKANT_VERKTYG` |
| T2 | API-namnet finns inte | `vcApplication.loadLayoutFile` | `OKANT_API` |
| T3 | läsande verktyg på ändrande steg | `list_components` täcker en borttagning | `FEL_VERKAN` |
| T4 | nämnaren krympte | ett obyggt steg struket ur profilen | `NAMNAREN_KRYMPTE` |
| T5 | hel profil struken | P1 döpt till P9 | `PROFIL_SAKNAS` |
| T6 | falskt `UI` | `UI:findComponent` — namnet är skriptbart | `FALSK_UTANFOR` |
| T7 | falskt `UI` utan markerat krav | märkt `UI`, alla krav i Python-API:t | `FALSK_UTANFOR` |
| T8 | uppfunnet `.NET`-namn | `IPlcBridge` finns inte i XML:en | `OKANT_DOTNET` |
| T9 | hål i numreringen | steg 3 urklippt | `TRASIG_NUMRERING` |
| T10 | både täckt och utanför | `list_components`, UI i samma cell | `BADE_OCH` |
| T11 | tjänstemodulen finns inte | `TJÄNST:katalogorakel` | `OKAND_TJANST` |
| T12 | tjänstesteg täckt av ett VC-verktyg | `TJÄNST:` + `list_components` | `FEL_KALLA` |
| T13 | verkan går inte att läsa | kolumnen säger `kanske` | `OKAND_VERKAN` |
| T14 | profil utan steg | rubrik utan tabell | `TOM_PROFIL` |
| T15 | samma profil två gånger | P1 två gånger | `DUBBEL_PROFIL` |
| L1 | tom täckningskolumn | inget besked alls | `Specfel` i läsningen |
| L2 | tom kravkolumn | inget att döma mot | `Specfel` i läsningen |
| L3 | kolumn borttappad | fyra kolumner i stället för fem | `Specfel` i läsningen |

**T4 är fasens kärna.** `tests/enhet/test_personatackning.py::
test_ett_borttaget_steg_ger_rott_trots_hogre_procent` gör den skarp mot den
verkliga specen: den stryker ett *obyggt* steg ur P6, numrerar om resten så
att inget hål syns, mäter att täckningen därmed **steg** — och kräver ändå
ett rött. Utan spärren hade raderingen sett ut som framsteg.

---

## Vad körningen INTE visar

* **Stegen är oviktade.** Att spara en layout och att bygga ett helt
  processflöde räknas som ett steg var. Täckningen är ett antal steg, inte ett
  antal timmar.
* **`UI:`-markörer går att bevisa falska, inte sanna.** En påhittad
  `UI:`-token passerar. Den öppna riktningen kan bara göra nämnaren större,
  aldrig mindre — och det är den ofarliga riktningen.
* **Ingenting körs mot en levande VC.** Att ett verktyg står i registret
  betyder att det är definierat och prövat mot bryggan i fas 5, inte att det
  gör rätt sak i just det arbetssteg profilen beskriver. Fasen mäter
  **täckning**, inte **kvalitet**.
* **Sju profiler är inte alla.** En underhållstekniker, en säkerhetsansvarig
  och en inköpare finns inte i nämnaren.
