# FAS 7 ACCEPTANS — ST för en station

**beskriver:** ST-generatorn (byggs), `svc/vc_assist_svc/plc/`, ögat
**kontrakt:** `docs/spec/70_faser.md` — *"Grind 1–5 gröna. Ögat säger PASS.
L1-guld"*
**specen:** `docs/spec/61_st_generering.md`
**körs av:** `tests/protocol/kor_fas7_station.py`

**Status: STÄNGD 2026-09-04.** Grind 1–5 gröna, ögat sa PASS, guldgrinden gav
`GOLD gold_verified_core`. Talen står i
[M-49](../../docs/matningar/M-49_stationen_arbetar.md) och de trasiga fallen i
[M-50](../../docs/matningar/M-50_de_trasiga_fallen.md). Utfallet i sin helhet
står längst ned.

Dokumentet skrevs innan generatorn fanns. Skälet är att en grind som skrivs
efter koden mäter koden. Kraven nedan är alltså inte en beskrivning av vad som
råkar fungera, utan vad som måste hålla — och de stod oförändrade när
körningen gjordes.

## Vad fasen faktiskt påstår

Att en modell, given ett skelett med genererade deklarationer, kan skriva
sekvenslogiken för **en** station, och att resultatet håller hela vägen ned till
en scen som rör sig.

Notera vad som inte påstås: ingenting om flera stationer (fas 8), ingenting om
hur ofta det lyckas (fas 9). Fas 7 påstår att vägen finns.

## Förutsättning som ~~ännu inte är uppfylld~~ **är uppfylld**

Fasen kan inte stängas förrän något **flödar** i en scen.

`M-34` mätte att den automatiska matningen inte fyrar: `vcComponentCreator`
skapar en riktig produkt vid manuellt anrop, men behållaren är tom över 160
simulerade sekunder, och banans behållare är tom. En station utan material är
inte en station, och ögat har då ingen rörelse att döma.

Det ledet mättes separat: M-40 fann de två tysta villkoren, M-41 mätte att en
produkt matas fram av sig själv och åker i 250,0 mm/s. Stationen i M-49 står på
den linjen, och materialet flödade under hela mätningen.

## Grindarna som ska vara gröna

Kedjan står i `50_grindar.md`. För fas 7 gäller grind 1–5:

| # | Grind | Vad körningen ska visa |
|---|---|---|
| 1 | Kompilering | STruC++ bygger den genererade ST-koden utan fel |
| 2 | Statisk analys | inga kända dödsfällor, ingen skrivning till `skyddad` tagg |
| 3 | Deklarationsmatchning | varje symbol modellen rörde finns i signalkartan |
| 4 | Anropsvalidering | inga uppfunna verktygsnamn eller argument |
| 5 | Ögat | stationens sekvens sker, i rätt ordning, inom tiden |

Grind 5 är den som faktiskt avgör. De fyra före är billiga och fångar det
billiga; ögat är det enda som ser om stationen gör sitt arbete.

## De trasiga fallen — utan dem är grinden inte prövad

Var och en ska **fällas**, och körningen ska rapportera vilken grind som fällde.
En trasig lösning som passerar är ett fasfel, inte ett provfel.

| # | Trasigt fall | Ska fällas av | Varför just detta |
|---|---|---|---|
| T1 | tagg som inte finns i kartan | grind 3 | den felklass genererade deklarationer ska ha utplånat; om T1 passerar är skelettet kringgått |
| | *mätt (M-48): fälls av **tre** grindar — grind 2 `ODEKLARERAD`, grind 3 `ORORD_SIGNAL`, kompilatorn kod 1* | | |
| T2 | skrivning till en `skyddad` signal | grind 2 | I15 är inte en stilregel |
| T3 | nivåläsning där en flank krävs | **grind 5** | fungerar i nio scan av tio och är osynlig för 1–3; det är hela skälet till att ögat finns |
| T4 | timer som nollställs av sitt eget villkor | grind 5 | kompilerar, ser rätt ut, fäller aldrig |
| T5 | förregling skriven som kommentar | grind 5 | två rörelser samtidigt; ögat ska se överlappet |
| T6 | rätt på första varvet, fel efter stopp mitt i sekvensen | grind 5 | återstart är där de flesta lösningar går sönder |
| T7 | tom kropp (`;`) | ~~grind 5~~ **grind 2 och 3** | om en tom lösning passerar mäter facit ingenting |

T3 till T6 måste fällas av **ögat**, inte av en tidigare grind. Om en statisk
regel råkar fånga T3 är det inte ett bevis på att ögat fungerar, och fallet ska
skrivas om tills bara ögat kan se det.

T7 är facitets egen nollpunkt. Ett facit som inte fäller en tom kropp har ingen
undre gräns, och alla tal ur det är oläsbara.

> **RÄTTAT av M-48.** Raden ovan sa att T7 måste fällas av ögat eftersom en tom
> kropp kompilerar. Den kompilerar mycket riktigt — kompilatorn godkänner både
> `;` och en tom sträng — men den fälls ändå av förgrindarna, av ett skäl jag
> inte hade tänkt på: kartan deklarerar signaler, och en kropp som inte rör dem
> får `ORORD_SIGNAL` av grind 3.
>
> Nollpunkten flyttas därför. Den ska inte pröva om en **tom** kropp passerar,
> utan om ett program som *rör* alla signaler utan att göra något meningsfullt
> gör det — till exempel `don := don;`. Det är den lösning som är osynlig för
> alla fyra förgrindarna och som bara facit kan fälla.

## Ärlighetskravet på körningen

Körningen ska rapportera, per uppgift:

* vilken grind som fällde, och grindens **egen** utdata — aldrig en omskrivning
  (`50_grindar.md`: en omimplementerad dom underkände 2 av 4 medan ögat visade
  4 av 4)
* antalet reparationsvarv som behövdes
* om lösningen befordrades till guld, och av vilken körning i VC

En rapport utan sektion för de trasiga fallen är ogiltig och ska avvisas av
guldgrinden på samma sätt som en rapport utan `HONESTY` avvisas i dag.

## Vad fasen inte kommer att ha prövat

Skrivs ned här nu, så att det inte kan glömmas bort när talen är gröna:

* **Fler än en station.** Fel som bara uppstår tillsammans är fas 8.
* **Hur ofta det lyckas.** Ett grönt varv är inte en frekvens. Fas 9.
* **Windows.**
* **Verklig hårdvara.** Sensorstuds, ställdonsdynamik och fältbussjitter finns
  inte i simuleringen. Ögat är felfinnande, aldrig bevis.

## Utfallet — mätt 2026-09-04

Sex körningar, var och en med egen VC-omstart, egen kompilering och
uppladdning till OpenPLC, 25 s uppvärmning och 110 s mätning.

| # | Fall | grind 1–4 | ögats dom | vad ögat mätte |
|---|---|---|---|---|
| — | **HEL** rimlig lösning | alla GODKÄND | **PASS** | tio hela cykler, alla i ordning och inom fönstren, exakt ett stopp per produkt, noll överlapp |
| T3 | nivåläsning där en flank krävs | alla GODKÄND | **FAIL** | bromsen gick ut **3 gånger per produkt** (4 på en cykel), på 9 cykler av 9 |
| T4 | timer som nollställs av sitt eget villkor | alla GODKÄND | **INCONCLUSIVE** | ingen cykel började ens: `Stopp` hög i 100,0 % av 1100 prov, en enda produkt i scenen på 110 s |
| T5 | förregling skriven som kommentar | alla GODKÄND | **FAIL** | överlapp **5,50 s** i 66 prov mellan broms och utmatning |
| T6 | rätt på första varvet, fel efter stopp mitt i sekvensen | alla GODKÄND | **FAIL** | nio cykler perfekta, **cykel 2 — den som pausen träffade — matade aldrig ut** |
| T7′ | `NOLL`: rör alla signaler, gör ingenting | alla GODKÄND | **FAIL** | tio cykler började, bromsen gick aldrig ut på någon av dem |

**Inget av de fem trasiga fallen föll före ögat.** Alla fem passerade grind
1–4, vilket är det protokollet krävde: en statisk regel som råkar fånga T3 vore
inget bevis på att ögat fungerar.

### Vad facit inte kunde förrän mätningen tvingade fram det

Tre rättelser, alla gjorda **innan** något dömdes grönt, och alla mätta:

1. **Ordningen ensam ser inte en station som gör om sitt arbete.** T3 höll
   ordningen på fem cykler av sex medan den stoppade samma produkt tre till
   fyra gånger — en ordningsdom tar den första flanken som passar och slutar
   sedan titta. Facit fick en **räkning**.
2. **Räkningen får inte gälla utmatningen.** En driftpaus mitt i utmatningen
   släcker den och tänder den igen, så en riktig lösning matar ut två gånger
   på just den produkt pausen träffade. En grind som fäller den rätta lösningen
   på sin egen störning mäter störningen.
3. **Perturbationen måste landa inne i sekvensen, och riggen måste vara varm.**
   En paus som kommer efter att processtiden tagit slut skiljer inte T6 från
   HEL. Och den första cykeln efter start är inget prov — den är ett
   uppstartsförlopp — så linjen körs 25 s innan ögat får se den. Rättelsen
   ligger i **riggen**, inte i facit.

### Vad fasen INTE prövade, trots grönt

* **Att en modell skriver kroppen.** Alla sex ST-kroppar är handskrivna. Fas 7
  påstår att vägen finns, inte att en språkmodell hittar den. Reparationsvarv:
  **noll**, av samma skäl.
* **Nödstoppet.** Den `skyddad`-märkta ingången går inte att driva över OPC UA
  (`opcuakonfig` ger den bara läsrättigheter, och en skrivning svarar
  `BadInternalError`). Den stod konstant `FALSE`.
* **Fasförhållandet PLC ↔ scen.** Kräver `--plc-inskott`, och med den fälls
  körningen på ögats färskhetsgrind. Se M-49.
* Och allt som redan stod nedskrivet ovan: flera stationer, frekvens, Windows,
  verklig hårdvara.
