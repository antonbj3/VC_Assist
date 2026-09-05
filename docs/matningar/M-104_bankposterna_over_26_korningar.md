# M-104 — bänkposterna över repots körningar

**Datum:** 2026-09-05
**Kontrakt:** `docs/spec/85_bankkontraktet.md`
**Körs av:** `tests/enhet/test_bankkontrakt.py` (grinden),
`tests/protocol/kor_allt.py` (den aggregerade körningen)
**beskriver:** `svc/vc_assist_svc/bankkontrakt.py`, samtliga
`tests/protocol/kor_*.py`

## Vad som gjordes

Varje körning under `tests/protocol/` fick en modulnivå-`BANKPOST`: ett
påstående, modulerna som döms, facit, **var facit kommer ifrån**, de fall som
måste fällas, vad körningen kräver för att alls gå att köra, och vilka
mätningar den bär. Deklarationen läses med AST, aldrig genom import — flera
körningar sätter `sys.path` eller startar processer redan på modulnivå.

Uppdraget sade 26 körningar. Under arbetets gång landade nio till från andra
agenter; fem av dem skrev sina egna poster, fyra fick sina av den här
mätningen. Talen nedan är räknade **2026-09-05 kväll** och de rör sig:
registret är körningarnas egna filer, inte en lista någon för.

| Storhet | Tal |
|---|---|
| poster i registret | **36** |
| odeklarerade körningar | **0** |
| poster med ogiltig facitkälla | **1** (se nedan) |
| körningar utan trasigt fall | **2**, deklarerade med ordet `SAKNAS` |
| facitkällor som är okända | **0** |

## Fyndet: en körning vars facit räknas fram av koden den dömer

`tests/protocol/kor_m85_databladets_tackning.py` mäter hur stor andel av
bibliotekets 3201 komponenter som bär egenskapsnamn, storhet och
standardvärde. Biblioteket är externt — det är VC:s egna filer på disk — men
**varje tal läses ut ur dem av `komponentdatablad.py`, samma modul som döms.**

Ett fält parsern missar rapporteras som ett fält filen inte bär. De två
utfallen går inte att skilja åt, för ingen annan läsare av samma
`component.rsc` finns i körningen. Det är BENCH-4:s form: talet kan vara
perfekt och ändå inte mäta något.

Posten är skriven som den är, grinden faller på den, och den står namngiven i
`TAUTOLOGISKA` i `tests/enhet/test_bankkontrakt.py` med ett tak som bara får
krympa. Vägen ut är en oberoende läsare av samma fält. **Den landade samma kväll:**
`tests/protocol/kor_m85_oberoende_lasare.py` skannar samma `component.rsc`
med ren radskanning, utan en rad delad kod, och ger täckningen en övre
gräns utifrån. Fyndet står kvar tills själva folkräkningen dömer mot den
läsaren: `kor_m85_databladets_tackning.py` läser fortfarande sina egna tal
genom modulen den dömer.

## Var facit kommer ifrån, körning för körning

Klasserna är `85_bankkontraktet.md` §2, i fallande styrka.

| Körning | Kräver | Facitkällans klass | Var facit kommer ifrån |
|---|---|---|---|
| `kor_allt.py` | inget | 4 människas facit, före | bankkontraktet i docs/spec/85_bankkontraktet.md, skrivet fore registret, plus korningarnas … |
| `kor_bankens_facit.py` | inget | 4 människas facit, före | docs/spec/85_bankkontraktet.md §2 (facit hor utanfor koden som provas) och de … |
| `kor_fas1.py` | vc | 4 människas facit, före | protokollspecen och fasens acceptanslista, bada skrivna fore korningen: … |
| `kor_fas15_domarna.py` | vc | 4 människas facit, före | cellerna ar handskrivna scenarier med en felklass var och en vantad domare vardera, och det … |
| `kor_fas15_hopfogning.py` | vc | 2 mätning av verkligheten | VC:s egen simuleringsklocka, last genom bryggan fore och efter varje prov: den sanna tiden … |
| `kor_fas15_plcaxeln.py` | vc | 4 människas facit, före | storningen ar KAND och palagd av korningen sjalv (SIGSTOP mot VC-processen i matta … |
| `kor_fas15_scenen.py` | vc | 2 mätning av verkligheten | VC:s egen WorldPositionMatrix, last genom bryggan i VC:s varldsenhet millimeter (M-33) efter … |
| `kor_fas18_anlaggning.py` | inget | 4 människas facit, före | bankens fyra sparfacituppgifter: referenslosning, handskrivet facit och motbevis, alla … |
| `kor_fas19_tackning.py` | inget | 4 människas facit, före | specerna, skrivna fore analysen: profilernas steg och deras krav star i … |
| `kor_fas2.py` | vc | 4 människas facit, före | cellerna ar handskrivna scenarier med en felklass var, och deras ratta dom star i … |
| `kor_fas20_modellen.py` | vc | 4 människas facit, före | docs/spec/49_komponentmodellen.md sager vad varje klass minst behover och ar skriven fore … |
| `kor_fas5.py` | vc | 2 mätning av verkligheten | VC:s egen API-yta i en korande VC: anropet lyckas eller kastar, och talet som lases tillbaka … |
| `kor_fas5_layout.py` | vc | 2 mätning av verkligheten | VC:s egen geometri genom vcNode.measureDistance i en korande VC - en oberoende domare pa … |
| `kor_fas6_slinga.py` | vc, openplc | 1 annan implementation | OpenPLC kor genomslappsprogrammet matut := matin - ett annat program an var kod |
| `kor_fas7_grindar.py` | strucpp | 4 människas facit, före | protokollets egen falltabell, skriven fore korningen, och grind 3:s dom tas av … |
| `kor_fas7_station.py` | vc, openplc, strucpp | 3 geometri ur scenens mått | stationens krav raknade ur scenens egna matt: transporttiden ur banlangd och fart, … |
| `kor_fas8_linan.py` | vc, openplc, strucpp | 3 geometri ur scenens mått | linjens krav raknade ur scenens egna matt (banornas langd och fart, utmatningstiden), med … |
| `kor_fas9_modellen.py` | modell | 4 människas facit, före | bankens uppgifter: facit ar skrivet av en manniska i uppgiften, fore forsoket, efter IEC … |
| `kor_fas9_slingan.py` | modell | 4 människas facit, före | bankens uppgifter, med facit skrivet av en manniska fore forsoket; taket pa fyra varv kommer … |
| `kor_m107_berikningen.py` | vc | 2 mätning av verkligheten | VC 4.10:s eCatalog-innehall pa den har maskinen plus tillverkarnas egna publicerade datablad |
| `kor_m107_bygg_korpus.py` | inget | 2 mätning av verkligheten | tillverkarnas egna publicerade datablad (ABB, KUKA, FANUC med flera), hamtade en gang och … |
| `kor_m41_flode.py` | vc | 2 mätning av verkligheten | riggens egna deklarerade tal - intervall och fart satts av korningen fore bygget - matta mot … |
| `kor_m54_tolk_mot_strucpp.py` | strucpp | 1 annan implementation | STruC++ 0.6.6, en oberoende implementation av ST-semantiken som bygger samma kalla till en … |
| `kor_m62_baslinjen_mot_strucpp.py` | strucpp | 1 annan implementation | STruC++ ar den andra motorn: tva oberoende implementationer av ST-semantiken |
| `kor_m63_specglapp.py` | inget | 4 människas facit, före | docs/spec/22_planeringslagret.md, skriven fore koden; koderna lases ur specen med … |
| `kor_m67_kopplingens_geometri.py` | vc | 2 mätning av verkligheten | VC:s egen scengraf: WorldPositionMatrix last fore och efter connect() i en korande VC, efter … |
| `kor_m72_kvaternionens_ordning.py` | vc | 3 geometri ur scenens mått | kvaternionalgebran, raknad i korningen ur den palagda vinkeln - inte ur VC och inte ur … |
| `kor_m75_vad_ett_spar_avslojar.py` | inget | 4 människas facit, före | bankens uppgifter: referenslosningen ar kand och handskriven fore korningen, sa det gar att … |
| `kor_m82_scenkod.py` | modell | 2 mätning av verkligheten | docs/referens/vc_api/, utdraget ur VC 4.10:s egen 'Python 2/Auto Complete'-mapp - VC:s egen … |
| `kor_m85_databladets_tackning.py` | vc | **6 FÖRBJUDEN** | FACIT UR KODEN SOM DOMS |
| `kor_m85_halen_ur_m84.py` | vc | 5 tidigare mätning | M-84:s sista avsnitt, skrivet fore den har korningen, plus bankens egen katalog och … |
| `kor_m85_oberoende_lasare.py` | vc | 1 annan implementation | en andra lasare i den har filen, skriven utan kannedom om VC:s modell - bara zipfile och … |
| `kor_m95_ordlistan_pa_fel_storhet.py` | inget | 5 tidigare mätning | M-94, en tidigare matning med M-nummer, skriven fore den har korningen |
| `kor_m98_ordlistan_som_avgor_en_dom.py` | inget | 4 människas facit, före | docs/spec/90_invarianter.md (I11) och instruktionskorpusens arlighetsregler, bada skrivna … |
| `kor_svit_mot_head.py` | inget | 2 mätning av verkligheten | pytests egen slutkod i en git worktree av HEAD |
| `kor_tackning.py` | inget | 1 annan implementation | coverage.py, ett externt verktyg som mater vilka satser som faktiskt kordes |

**Fördelningen:** 5 dömer mot en annan implementation (STruC++, OpenPLC,
coverage.py, en andra läsare), 10 mot en mätning av verkligheten (VC:s egna
svar, tillverkarnas datablad), 3 mot geometri räknad ur scenens egna mått, 15
mot en människas facit skrivet före körningen, 2 mot en tidigare mätning med
M-nummer — och **1 mot koden den själv dömer.**

**Vad som går att köra var:** 11 poster kräver ingenting, 19 kräver VC, 5
STruC++, 3 OpenPLC och 3 en modellklient. Det är därför den aggregerade
körningen säger *"n körda här, resten hoppade och varför"* i stället för att
låtsas att sjutton körningar inte finns.

## De två körningarna utan trasigt fall

`kor_m63_specglapp.py` och `kor_m75_vad_ett_spar_avslojar.py` räknar och dömer
inte. De har inget som **måste** fällas, och det står i posten med ordet
`SAKNAS` i stället för en formulering som ser ut som en grind. De står
namngivna i `UTAN_TRASIGT_FALL` med ett tak som bara får krympa.

## Grinden

`tests/enhet/test_bankkontrakt.py`, 24 prov:

* **Ingen föräldralös körning.** Varje `kor_*.py` måste ha en post. Taket är
  `0`, satt till det som faktiskt lämnades.
* **Ingen post utan körning.** Varje fil i `under_prov` och
  `facitkalla_filer` måste finnas.
* **Facitkällan utanför koden som prövas** — exakt likhet räcker inte:
  `under_prov` får peka på en katalog, och ett facit läst ur en fil *därinne*
  är lika tautologiskt.
* **En post per fil.** Två `BANKPOST` i samma fil är två påståenden där ett
  läser: `las_bankpost` tar den första, Python kör den sista. Det hände under
  arbetet — två agenter deklarerade `kor_m98` — och det blev inte rött förrän
  kontrollen fanns.
* **Varje M-nummer** slås upp mot `docs/matningar/` eller `RESERVERADE.md`.
* **Trasiga fixturer** för var och en: en facitkälla inne i `under_prov`, en
  facitkälla i en katalog under `under_prov`, en post utan `trasiga_fall`, ett
  `pastar` som är en etikett, ett okänt `kraver`, en post som pekar på en fil
  som inte finns, en odeklarerad körning, en fil med två poster, och en
  kontroll som visar att den **hela** posten går igenom — utan den mäter
  fixturerna bara att granskningen säger nej till allt.

## Den aggregerade körningen

`tests/protocol/kor_allt.py` läser registret, upptäcker vad som finns här (VC
genom tokenfil plus en TCP-anslutning som stängs direkt — den startar aldrig
VC; OpenPLC genom OPC UA-porten; STruC++ genom `--strucpp-cli`; modellklient
genom `claude` i PATH) och kör varje post vars krav är uppfyllda. Resten
hoppas över **med skälet utskrivet**, och skälet kan också vara *"saknar
argument: --svar"*. Returkoden bär två ting och bara två: ett rött utfall
bland de körda, och ett register som inte håller. Ett hopp får aldrig färga
returkoden.

Torrkörning 2026-09-05, från en maskin där VC och OpenPLC lyssnade men ingen
STruC++-CLI var angiven:

```
=== BANKEN: 36 poster, 0 odeklarerade korningar ===
  BRISTER I REGISTRET (en ogiltig post ar ingen gron):
    kor_m85_databladets_tackning.py: facitkallan ligger i koden som provas ...
  vad som finns har:
    modell    JA  claude i PATH
    openplc   JA  OPC UA-port 14840 lyssnar
    strucpp   nej --strucpp-cli inte angiven
    vc        JA  tokenfil ..., port 8901 lyssnar
    windows   nej sys.platform=linux
```

## LIMITS

* **Ingen av de 36 körningarna kördes av den här mätningen.** Talen ovan är
  registrets, inte körningarnas: posterna är lästa och granskade, och
  `kor_allt.py` är provkörd **torrt**. Vad varje körning svarar när den körs
  skarpt står i dess egen mätning, inte här.
* **Facitkällans klass är min bedömning**, inte ett mätt tal. Gränsen mellan
  *"en mätning av verkligheten"* och *"en annan implementation"* är
  omdömesmässig när verkligheten är ett annat program (VC). Det mekaniska —
  och det enda grinden kontrollerar — är att källan ligger **utanför**
  `under_prov`.
* **Grinden kan inte se ett facit som är fel.** Den ser bara att facit kommer
  någon annanstans ifrån än koden. Det är exakt den kontroll som saknades när
  BENCH-4 stod grön i månader, och det är inte samma sak som att facit är
  riktigt.
* **Ett `under_prov` kan vara för smalt.** Ingen kontroll säger att modulerna
  en körning faktiskt rör står i posten; en körning kan importera mer än den
  deklarerar. En mekanisering av det vore en importanalys per körning, och den
  finns inte.
* **`kor_fas5.py`:s facit är svagt.** För de flesta verktygen är det rätta
  svaret *"anropet kastade inte"*. Bara `set_transform` följt av
  `get_transform` jämför ett **värde**. Att alla anrop går igenom är inte
  samma sak som att verktygen gör rätt.
* **Registret rör sig, och fort.** Under den här mätningens kväll gick det
  från 26 körningar till **38**: tolv landade från andra agenter medan
  posterna skrevs. Tabellen ovan är därför en ögonblicksbild räknad vid 36
  poster; sifferraderna i prosan är räknade ur samma ögonblick. De sista två
  körningarna kom med **egna** poster, skrivna av sina ägare — vilket är hela
  poängen med att kontraktet bor i körningarnas filer och inte i en lista.
  Taket `TAK_ODEKLARERADE = 0` gör sviten röd på nästa körning som landar
  utan post, och felmeddelandet säger vad som ska göras.
* **Tre filer var ospårade** när jag skrev i dem: `kor_tackning.py` och
  `kor_m107_bygg_korpus.py` fick sina poster, och `kor_m107_berikningen.py`
  fick sitt `kraver` rättat från `"installerat VC-bibliotek"` till `"vc"`
  — kontraktets ord för samma sak, och det enda som gick igenom grinden.
  Landar de aldrig i ett commit försvinner ändringarna med filerna.
* Klassificeringstabellen ovan är en **ögonblicksbild**. Den räknas fram ur
  posterna och kan räknas om; den underhålls inte för hand.
