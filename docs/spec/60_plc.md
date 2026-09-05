# PLC-benet

Status: fas 6 är stängd. Två påståenden i den tidigare versionen av detta
dokument har mätts falska och är rättade här, med boxar som säger vad som stod
och varför det föll. Den öppna frågan om signalmappning är besvarad.

## Uppsättning

| Del | Val | Motiv |
|---|---|---|
| Mjuk-PLC | **OpenPLC v4** (Autonomy Logic) | enda gratis som är OPC UA-**server** och har headless inladdning |
| Transport | OPC UA | PLC:n är server, vår kopplare är klient |
| Inladdning | REST + JWT | `/api/login`, `/api/upload-file`, `/api/compilation-status`, `/api/start-plc` |
| Kompilator | `STruC++` CLI | fristående, körs som grind 1 |

**Avvisade:** OpenPLC v3 (ingen OPC UA), Beremiz (endast klient),
CODESYS (IDE är Windows), Modbus-brygga (onödig med v4).

Mätt uppsättning i fas 6: containern `vcassist-openplc-v4`, OPC UA nådd på
`127.0.0.1:14840` från värden. Porten är containerns mappning, inte en egenskap
hos OpenPLC — hårdkoda den inte, läs den ur uppsättningen.

## Vem som talar med PLC:n

> **RÄTTELSE.** Den tidigare versionen sa: *"Via komponentsignaler — Python
> sätter och läser komponenternas egna signaler, och VC:s connectivity-lager
> mappar dem mot OPC UA. Ingen .NET-kod behövs. **Föredras.** Prövas först."*
>
> Den vägen finns inte. **M-38** sökte igenom API-indexets 3444 symboler efter
> `opc`, `server`, `variable` och `subscri` och fick noll äkta träffar.
> Uppkopplingen bor bara i `VisualComponents.Connectivity.*.dll`, alltså i .NET,
> och VC:s Python når inte .NET (**M-07**: `import clr` och `import System` ger
> båda `ImportError`). VC:s egen OPC UA-klient går därför inte att konfigurera
> programmatiskt. Den kräver gränssnittet, eller en layout där kopplingen redan
> är sparad.

Slingan sluts i stället **utanför VC**, i tjänsten:

```
scenens givarsignal ──► bryggan ──► kopplaren ──► OPC UA ──► PLC:ns logik
scenens donsignal   ◄── bryggan ◄── kopplaren ◄── OPC UA ◄──┘
```

Kopplaren är `svc/vc_assist_svc/plc/kopplare.py`. Den kör i CPython 3 i tjänsten
och äger båda sidorna av varvet. VC-sidan når den bara genom bryggan, och
scenskrivningar går genom **kön**, aldrig genom `exec` (I12).

Det gör en tredje väg möjlig som specen tidigare inte hade: ett eget
.NET-plugin behövs inte för att sluta slingan. Det står kvar som ett alternativ
för den dag VC:s egen uppkoppling ska konfigureras från kod, men det är inte
längre en förutsättning för att köra.

## Signalmappningen — den öppna frågan är besvarad

> **RÄTTELSE.** Den tidigare versionen sa: *"Öppen fråga: hur mappningen mellan
> VC-signal och OPC UA-nod ska deklareras. Kandidater: namnkonvention, eller en
> explicit mappfil per station. Avgörs i fas 6."*

Svaret är **explicit deklaration**, inte namnkonvention. Namnkonventionen
avvisades av ett skäl som väger tyngre än bekvämligheten: en konvention kan inte
avvisa en signal. Den producerar alltid ett namn, också för en signal som är
felstavad eller inte finns, och felet dyker upp först som ett värde som aldrig
rör sig.

Bäraren är `Signalkarta` i `svc/vc_assist_svc/plc/signalkarta.py`. En rad är:

| Fält | Betydelse |
|---|---|
| `komponent` + `scensignal` | identiteten i VC-scenen |
| `tagg` | variabelnamnet i ST-koden |
| `typ` | ST-typen; styr både deklaration och adressbredd |
| `riktning` | `TILL_PLC` eller `FRAN_PLC`, ur PLC:ns synvinkel |
| `adress` | den lokaliserade adressen, `%I` för in, `%Q` för ut |
| `skyddad` | säkerhetsmärkt: agenten får läsa, aldrig skriva (I15) |

Kartan avvisar vid konstruktion: tagg som inte är en giltig identifierare,
saknat komponent- eller signalnamn, icke-ASCII i något namn som ska hela vägen
ut som OPC UA-namn, okänd riktning, icke-elementär typ, och adress i fel område
för riktningen. På kartnivå avvisas dessutom dubblerad tagg (skiftlägesokänsligt,
för ST är det), delad adress, och samma scensignal mappad två gånger.

Detta är en **fail-closed-punkt**, och den bär en konsekvens uppåt: kopplaren har
ingen gren för trasiga signaler, eftersom en trasig signal aldrig kan bli en
`Signal`. Garantin bor på ett ställe och provas där.

## Deklarationer genereras, skrivs aldrig

```
VC-scen ──► signalkarta ──► OPC UA-nodlista ──► ST VAR-block
```

Modellen får **aldrig** skriva variabeldeklarationer eller taggnamn. Den får en
färdig deklarationsdel och skriver bara sekvenslogiken. Det tar bort hela
felklassen "fel taggnamn" mekaniskt i stället för att be modellen vara noggrann.

Se `61_st_generering.md` för vad modellen får skriva och hur det döms.

## Varvet och dess tider

Kopplaren kör ett **varv**: läs scenen, skriv till PLC:n, läs PLC:n, skriv
scenen. Varje led tidtas för sig, så att en långsam sida går att peka ut.

Mätt i **M-39**, två signaler, levande OpenPLC v4 och levande VC:

| Storhet | Tal |
|---|---|
| kopplarvarv, median | 89,11 ms |
| kopplarvarv, p95 | 104,85 ms |
| genomslag givare → don | 109, 210 och 232 ms (ett till två varv) |

Talen gäller **två** signaler. Varvet växer med antalet, eftersom varje led är
ett bryggeanrop. Det är inte mätt för fler, och ska inte extrapoleras.

## Vad som händer när PLC:n tystnar

Kopplaren ger upp efter **tre raka fel** (`MAX_RAKA_FEL`, satt av M-39) och
fäller slingan. Ett lyckat varv nollställer räkningen.

Skälet är den dyraste felklassen i hela projektet: utan spärren fortsätter
kopplaren skriva sina senast kända värden till scenen, slingan **ser ut** att
arbeta, och ögat dömer på tal som inte längre kommer från någon PLC. En slinga
som tyst målar vidare är värre än en som stannar, eftersom den producerar ett
grönt som ingen har anledning att misstro.

Samma krav gäller uppåt: den som för PLC-värden vidare in i ögats tidsserier
måste märka avbrottet i serien, inte fylla igen det.

## Scan-cykeln

Modellen får inte en förklaring av scan-cykelsemantik. Den får **se** den:
PLC:ns variabelvärden loggas på samma tidslinje som scenen, så en flank som
missas mellan två scan blir synlig i serien.

Det förutsätter en gemensam tidsaxel över processgränsen. Ögat kör inne i VC
(Stackless 2.7.1, kooperativt schemalagt), kopplaren i tjänsten. En tidsstämpel
från den ena sidan betyder inte samma sak som en från den andra, och
hopfogningens osäkerhet är en mätt storhet, inte en detalj.

## Säkerhet

Se `50_grindar.md`. Kort: ingenting genererat i en säkerhetsfunktion. En signal
märkt `skyddad` får agenten läsa men aldrig skriva (I15), och kartan bär den
märkningen så att förbudet går att kontrollera mekaniskt i stället för att
förlita sig på att modellen låter bli.

## Vägen ut: PLCopen XML

Allt ovan handlar om att få koden **in** i vår egen kedja. Användaren behöver
också få ut den: koden ska lämna vårt verktyg och landa i hans.

`svc/vc_assist_svc/plc/plcopen.py` skriver en `st.Enhet` som ett **PLCopen
TC6 XML v2.01**-dokument (namnrymd `http://www.plcopen.org/xml/tc6_0201`) och
läser tillbaka det. Deklarationerna bor i `<interface>` som riktiga
`<variable>`-element med `address` och `constant`/`retain`; `<ST>` bär bara
satserna.

**Regeln som styr modulen: en export som inte överlever sin egen import är
ingen export.** `exportera()` skriver, läser tillbaka och jämför modellerna.
Skiljer de sig kastas `ExportFel` med varje avvikelse utskriven. Det finns
ingen växel som slår av kontrollen.

Mätt i `M-154`: 77 av 77 fall (bankens 63 program plus 14 konstruktioner)
överlever turen och retur, är giltiga mot det officiella schemat, godtas av
**Beremiz egen laddare**, och får **samma dom av matiec före och efter**.
En riktig ST-konstruktion överlever inte och fälls därför: `VAR NON_RETAIN
CONSTANT` blir två XML-attribut, och attribut har ingen ordning.

Två gränser hör hit och står utskrivna i `M-154 §LIMITS`:

* **Det är inte IEC 61131-10:2019.** PLCopen skriver själva att den nya
  versionen *"is not compatible to previous versions of PLCopen XML"*
  (`M-155 §0`). v2.01 är den version CODESYS och TwinCAT dokumenterar import
  av, och den enda vars schema är fritt tillgängligt.
* **`skyddad` har ingen plats i standarden.** Säkerhetsmärkningen (I15) skrivs
  i `addData` under vår egen namnrymd med `handleUnknown="preserve"` — en
  *rekommendation* i schemat, inte en garanti. Vår tur och retur bevarar den;
  att ett främmande verktyg gör det är oprövat.

Vad som faktiskt går att importera hos CODESYS, TIA Portal och TwinCAT — med
belägg, och med det oprövade utskrivet — står i `M-155`. Kort: CODESYS och
TwinCAT dokumenterar båda PLCopen XML-import; TIA Portals Openness-manual
nämner inte PLCopen med ett ord och tar i stället `.scl`/`.awl`/`.db`/`.udt`
som ren text. Ingen av de tre har öppnat vår fil — ingen licens, ingen
Windowsmaskin.

## Vad som inte är prövat

* **Fler än två signaler.** Varvets tider är mätta på två.
* **Rörelse.** Donet i M-39 är en boolesk signal, inte en transportör som går.
* **Windows.** Hela PLC-benet är kört på Linux.
* **Andra PLC:er.** Beckhoff ADS och S7 finns som .NET-dll:er i VC, men vi rör
  dem inte; vår väg går utanför VC:s uppkopplingslager.
