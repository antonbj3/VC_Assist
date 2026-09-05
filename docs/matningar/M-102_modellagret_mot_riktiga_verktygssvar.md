# M-102 — modellagret mätt mot riktiga verktygssvar

**Datum:** 2026-09-05
**Status:** KLAR — fas 22 grön i L1.
**Prövar:** `svc/vc_assist_svc/llm/` (kontextbudgeten, verktygssvarets kapning,
ögontrimningen, urvalet, turens tillståndsmaskin) mot repots **egna**
verktygssvar och mot harnessens riktiga tur.
**Körs av:** `tests/protocol/kor_fas22_modellagret.py`, plus 96 enhetsprov i
`tests/enhet/test_kontextbudget.py`, `test_verktygssvarets_kapning.py`,
`test_ogontrimning.py` och `test_modellturen.py`.
**Protokoll:** `tests/protocol/fas22_modellagret.md`.

## Varför

`23_llm_granssnitt.md`, `24_samtalsloopen.md` och `25_kontextbudget.md` var
1 292 rader spec om hur en språkmodell ska tala med systemet, och ingen av dem
hade en fas — samma form som fas 16 hade innan den fick en. Frågan mätningen
ställer är den operatören ställde: **vad händer när ett verktygssvar är större
än budgeten, vad kapas, i vilken ordning, och vad får aldrig kapas?**

## LIMITS

* **Ingen språkmodell är anropad.** Turerna kommer ur en attrapp med manus.
  Talen mäter mekanismerna, inte en modells beteende.
* **Ingen brygga och ingen VC har svarat.** Verktygssvaren kommer ur de
  handlare som svarar utan brygga; de kodgenererande verktygens svarsform
  kommer ur deras **deklarerade** `returns`, inte ur en körning.
* **Tokentalen är en omräkning ur byte**, inte en leverantörs tokenisering.
  Båda omräkningarna är antaganden, och det är en del av fyndet.
* **Urvalsträffen mäter regeln, inte efterfrågan.** De 95 turerna är
  efterlevnadsbankens, byggda för att pröva grindarna — inte ett stickprov på
  vad en användare ber om.
* **Scensammanfattaren är mätt på konstruerade scener.** Ingen bankscen är
  över gränsen; den största är 9 komponenter.
* **Ingen lång körning finns.** Den långa ögonrapporten är byggd med ögats egen
  skrivare. Att `EDGE` och `MINDIST` växer som antaget är antaget.
* **`KO`-läget är oprövat.** Kön har inget lager i den byggda loopen.

## Korpusen

| Källa | Antal | Vad det är |
|---|---|---|
| `verktyg.DATA_HANDLERS` | **207 svar** | katalogens 65 URI:er, bankens 51 uppgifter, API-indexets 25 största typytor, åtta sökfraser, åtta hjälpmoduler, nio ögonrapporter |
| `bank/uppgifter/*.json` | **9 ögonrapporter** | bankens egna, ordagrant |
| `harness/fallor.ALLA` | **95 turer** | efterlevnadsbankens fixturer, med turens egna anrop som facit |
| egna turer | **13** | de vägar genom tillståndsmaskinen banken aldrig går |

---

## 1. Verktygsschemat får inte plats under sitt eget tak

| Storhet | Vid specens skrivning | MÄTT 2026-09-05 |
|---|---|---|
| Registrerade verktyg | 21 | **122** |
| Varav `effect=write` | 8 | **53** |
| Schema i kanonisk form, totalt | 11 074 byte | **98 324 byte** |
| Medel per verktyg | 527 byte | **805 byte** |
| Tokens (4 byte/token) | ~2 800 | **32 775** |
| Fönster som postens 10 %-tak kräver | ~28 000 | **327 750** |

`23_llm_granssnitt.md` skrev *"Urvalsmaskineriet byggs alltså inte nu"* vid en
kvot på 2 %. Kvoten är i dag **19 %** på ett fönster om 128 000 tokens, och
**båda** villkoren i specens egen tröskel är brutna: 122 > 100 verktyg och
19 % > 10 %.

**Talet som binder i praktiken:** alltid-med-listan — de verktyg utan vilka
modellen inte kan ta reda på var den är — är **28 verktyg och 4 792 tokens**.
Den ensam kräver ett fönster på **47 920 tokens** för att rymmas under 10 %.

**Följd:** urvalet byggdes (`llm/urval.py`), och postens tak på 10 % är
markerat som en **preliminär andel satt mot en katalog en sjättedel så stor**.

---

## 2. Riktiga verktygssvar mot budgeten

| Storhet | Värde |
|---|---|
| Svar | **207** |
| Minsta | **294 byte** |
| Median | **2 388 byte** |
| Största | **67 911 byte** (`type_surface` på `vcApplication`) |
| Svar som bär sin **egen** räkning | **19 av 207** |

| Fönster | Postens tak | Kapade | Hänvisningar | Anmärkningar |
|---|---|---|---|---|
| 8 000 tokens | 6 000 byte | **45** | 1 | **0** |
| 32 000 | 24 000 byte | **19** | 0 | **0** |
| 128 000 | 96 000 byte | **0** | 0 | **0** |
| 200 000 | 150 000 byte | **0** | 0 | **0** |

Kontrollen åt andra hållet: **0 av 207 hela svar anmärktes.** En grind som
faller på allt mäter ingenting.

**Att bara 19 av 207 svar kan kontrolleras utan råvaran** är mätningens
obekväma tal. För de övriga 188 går en kapning inte att upptäcka ur svaret
ensamt. Följden är en regel i koden: **kapning sker bara i `kapning.kapa()`,
där råvaran finns kvar.** Ett lager som kapar någon annanstans kan inte bevisa
att det inte ljög.

---

## 3. Tre fynd som ändrade specen, och alla tre är samma felklass

### 3.1 Repot bar två omräkningar till tokens

| Var | Antagande |
|---|---|
| `25_kontextbudget.md` | 4 **byte** per token |
| `harness/sammansattning.py` | 3,0 **tecken** per token |

De är inte samma storhet. Vår text är svensk, och varje å, ä och ö är två byte
i UTF-8. Ett tak satt i byte och ett tak satt i tecken säger olika saker om
samma sträng.

**Åtgärd:** `llm/matt.py` mäter båda och tar det **högsta** talet, och
rapporterar spridningen som *så mycket av det här talet är antagande*.

### 3.2 Fältet `antal` bär två storheter

| Verktyg | `antal` betyder |
|---|---|
| `list_components`, `search_api`, `list_interfaces`, … | poster i listan |
| `search_installed_library` | träffar **totalt**; `visade` är poster i listan |

Granskningen föll på ett **riktigt** verktyg innan den kände skillnaden, och
felet låg i granskningen. Den farliga riktningen är den motsatta: en kontroll
kalibrerad på `search_installed_library` skulle ha **missat en verklig
kapning** i alla de övriga verktygen.

**Åtgärd:** granskningen läser `visade` när det finns och `antal` annars, och
uppdelningen står utskriven i koden. **Öppet, som skuld:** två konventioner för
samma fältnamn i samma register borde lagas i verktygslagret, inte hanteras i
läsaren.

### 3.3 Ordlistan som skulle ha fyrat på fel storhet

Trimningen av ögats rapport är den enda plats i modellagret där en ordlista
avgör något. Den naiva domaren (`"OK" in rad`) har fel på minst tre riktiga
former:

| Rad | Naiv | Vår |
|---|---|---|
| `MINDIST OK_ROBOT+STANGSEL 412.000mm t=1.200s` | trimmar | raden har **ingen dom**; den bär ett avstånd |
| `STEP 3 ST010_OK_SENSOR RISE MISSING win=…` | trimmar | domen är `MISSING` — ett **fynd** |
| `EDGE ST100_STA_DONE RISE t=0.500s` | ingen träff | ingen dom, inget fynd ⇒ får trimmas |

**MÄTT:** på en riggad rapport skulle den naiva domaren ha trimmat **15**
rader som vår behåller.

**Åtgärd:** statusen läses ur **grammatikens egen alternativgrupp**
(`oga_kontrakt.RADER`), och domsordförrådet kommer ur kontraktet. Grupper som
`(RISE|FALL)` och `(RUN|PRIOR)` är inte domsgrupper, därför att orden inte står
i ordförrådet.

Det här är samma felklass som `M-94` (två gånger), `M-95` och `M-98` mätte.
Fjärde gången i repot, första gången **innan** den hann fälla något.

---

## 4. Turen: urvalet och tillståndsmaskinen

### 4.1 Urvalsträffen, och varför den delar sig i två tal

95 turer, 105 anrop, turens **egna** anrop som facit:

| Lager | Träff |
|---|---|
| bara alltid-med-listan som den var före mätningen | 46 av 105 |
| plus topp-N mot turens text | 59 av 105 |
| alltid-med som **regel** (läsande verktyg i scen och komposition) | **87 av 105** |

Urvalets medelstorlek: **39 av 122** verktyg. Båda talen krävs — ett urval som
träffar 100 % genom att skicka allt har inte mätt något.

**Alla 18 anrop som fortfarande missas är skrivande** (`set_transform` 6,
`measure_distance` 4, `load_component` 2, `save_layout` 2, `set_property` 1,
och tre anrop utan registerpost, som är trasiga fixturer). Varje **läsande**
anrop täcks, och det kravet hålls av ett prov.

Skälet är inte en svaghet i rangordningen utan en egenskap hos indata:
uppgifterna är **svenska** och verktygsnamnen **engelska**. Lager 3 bidrog med
13 av 105 anrop.

**Följd, och en ny regel i specen:** ett skrivande verktyg går inte att gissa
fram ur fritext. Det kommer ur **planen**, som deklarerar ett `tool` per nod.
Tills en plan finns kan turen bara läsa.

### 4.2 Tillståndsmaskinen

| Storhet | Värde |
|---|---|
| Deklarerade övergångar | 37 |
| Obyggda (kön saknar lager i loopen) | **4** |
| Strukturellt onåbara i den byggda loopen | **11** |
| Nåbara | **22** |
| Nådda av någon tur | **22 av 22** |
| Lägen nådda | **7 av 8** |
| Turer som gick en väg utanför tabellen | **0 av 108** |

Stoppkoder över de 95 bankturerna: `KLAR` 53, `TYSTNAD` 39, `TAK_FALL` 1,
`TAK_RUNDOR` 1, `UPPREPAT_ANROP` 1.

Att skilja **obyggt** från **onåbart** från **oprövat** är hela poängen: ett
täckningstal som blandar ihop *ingen har prövat* med *går inte att pröva* mäter
fel storhet. Varje övergång i de två första grupperna bär ett skrivet skäl, och
ett prov kräver skälet.

### 4.3 Budgeten över 95 riktiga turer

Fönster 32 000 tokens: **95** schemabeskärningar, **40** resultatkapningar,
**0** turer som behövde delas, **0** bokföringsfel. Att schemat beskärs i
*varje* tur är samma fynd som i avsnitt 1: postens tak är för litet för dagens
register.

---

## 5. Ögontrimningen

| Storhet | Värde |
|---|---|
| Riktiga rapporter | **9** |
| Största | **868 byte** |
| Trimmade under ett tak på 10 000 byte | **0** |
| Lång rapport (200 `EDGE`, 40 `MINDIST`) | **9 606 → 1 169 byte** |
| Noteringar, utanför blocket | 2 |
| Anmärkningar | **0** |

Noteringarna, ordagrant:

```
198 EDGE-rader utelamnade ur SECTION TIMING, alla utan fynd; 2 star kvar
    (forsta och sista raden)
27 MINDIST-rader utelamnade ur SECTION SAFETY, alla utan fynd; 13 star kvar
    (forsta, sista och raden med minsta avstandet)
```

Att **raden med minsta avståndet** står kvar är en regel som tillkom i fas 22.
En `MINDIST`-rad är ett avstånd; trimmas den minsta bort ser det som står kvar
ut som en tryggare körning än den var.

---

## 6. De trasiga fallen

13 fällda av acceptanskörningen, fyra till av enhetsproven. Var och en med sin
egen kod. Hela listan står i `tests/protocol/fas22_modellagret.md` avsnitt B.
De tre operatören namngav:

| Fall | Kod | Vad som bevisas |
|---|---|---|
| Ett kapat svar som **ser helt ut** | `K2_SER_HELT_UT` | halva listan borta, svarets egen räkning kvar, parsar felfritt |
| Tystnad märkt som klar | `T3_TYST_GODKANNANDE` | tystnad är aldrig ett godkännande (I3) |
| Ett för stort svar som tappade felet | `K4_FEL_TAPPAT` | det är precis den delen som behövs |

Och den tystaste av alla tre kapningsformerna: ett **internt konsistent men
kort** svar, där `antal` rättats och `avkortad` saknas. Det faller bara mot
råvaran.

---

## 7. Vad som INTE är mätt

* **Ingen modell, ingen brygga, ingen VC.** Se LIMITS.
* **`A4`, adapterns tokenräknare**, finns inte. Kravet "högst 5 % avvikelse"
  är oprövat; talet används i dag bara som pålägg för en uppskattad räknare.
* **Kön.** Läget `KO`, och stoppkoderna `VANTAR_GODKANNANDE`, `AVBRUTEN`,
  `BRYGGA_NERE` och `TAK_TOKEN`, har ingen kodväg som kan sätta dem.
* **Ett verktyg som ALDRIG svarar** kan inte avbrytas (M-13). Tidsvakten kan
  bara vägra lita på ett sent svar. Vad operatören ser under tiden är
  `HJARTSLAG`, inte ett stopp.
* **Att 22 av 37 övergångar är allt som går att nå** gäller den byggda loopen.
  Ändras loopen ändras talet.
* **Sammanfattaren mot banken.** Regeln "inget namn försvinner" går inte att
  mäta på banken, därför att ingen bankscen är över gränsen.
* **Systempromptens guldfil** och importgrafprovet mot adaptern är inte byggda.
* **Injektionsprovet** (två turer, identiska utom komponentnamnet) är inte kört
  i fas 22.
