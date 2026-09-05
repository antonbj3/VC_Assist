# Kö A — motorn på riktigt: OpenPLC, exporten och skanncykeln

Läs `docs/uppdrag/00_GEMENSAMT.md` först. Det gäller dig också.

## Din yta

`svc/vc_assist_svc/plc/`, `svc/vc_assist_svc/st/` (bara när A2 kräver det),
`tests/protocol/kor_A*`, `tests/enhet/test_plc_*`, `install/verktygskedjan.py`,
`docs/matningar/M-1xx` (dina egna nummer), `docs/spec/60_plc.md`,
`docs/spec/61_st_generering.md`.

## Varför den här kön finns

Kedjan ut i verkligheten är `ST → STruC++ → OpenPLC v4 → OPC UA → Visual
Components`. Vår egen ST-tolk dömer koden **innan** något av det händer. Två av
tre led är korsprövade — `M-54` och `M-99` ställde tolken mot STruC++ och la
247 permanenta fall i `tests/enhet/test_st_svep_mot_strucpp.py`.

Det tredje ledet är oprövat. `M-99` skrev det rakt ut: *"OpenPLC som tredje
motor är fortfarande oprövad."* Och `M-110` skrev en mening som är hela kön i
sammandrag: **"Domen kommer ur vår ST-tolk, inte ur OpenPLC."**

Det betyder att varje tal projektet har om tillförlitlighet är ett tal om hur
väl modellen träffar *vår tolk*. Om tolken och OpenPLC skiljer sig åt, är
talet fel — och vi vet inte åt vilket håll.

---

## Vad som redan är gjort åt dig (M-121, samma dag)

Vägen till tredje motorn är **öppnad, inte obeprövad**. `M-121` körde
**matiec — OpenPLC:s egen kompilator — via wine** och fick ett skarpt svar:
`4.0 * antal` med `antal : INT` avvisas med *"Data type mismatch for '*'"*,
med IEC 61131-3:2003 §2.5.1.4 som grund. T-04:s referens bar det felet och är
rättad.

Två slutsatser att bygga vidare på, inte ompröva:

* **STruC++ är inget typfacit.** Den accepterade samma rad — och accepterar
  också `b := 4.0 * i` med `b : BOOL`. Där de två motorerna skiljer sig i
  typfrågor har matiec rätt tills annat visas.
* **Anropsvägen till matiec fungerar under wine.** Du behöver inte bygga den.
  Läs hur `M-121` gjorde innan du skriver en egen.

## A1 — OpenPLC som tredje motor

Ta `M-99`:s 490 konstruktioner och kör dem genom OpenPLC:s runtime. Jämför
trevägs: vår tolk, STruC++, OpenPLC.

Tre utfall är intressanta, och det tredje är det dyra:

1. **Alla tre är överens.** Inget att göra.
2. **Vår tolk fäller, de andra två godkänner.** En falsk rödgrind. Den kostar
   ett reparationsvarv och lär modellen fel sak. `M-96` mätte priset: nio av
   sexton grinddomar var vår egen bugg.
3. **Alla tre godkänner texten, men OpenPLC *beter sig* annorlunda.** Det är
   hålet. Koden går hela vägen ut i en scen och felar där, långt från sin
   orsak.

Utfall 3 hittas inte av en kompileringsjämförelse. Den kräver att du **kör**
konstruktionen och läser utfallet. Bygg det.

**Trasig fixtur, före mekanismen:** en konstruktion som alla tre accepterar men
som ger olika värden vid körning. Bygg den för hand, se den fällas, bygg sedan
svepet.

**Levererar:** `docs/matningar/M-1NN_openplc_som_tredje_motor.md` med en tabell
över varje oenighet: konstruktion, vad var och en av de tre sa, och vilken av
de tre som har rätt enligt IEC 61131-3.

## A2 — en domare som dömer ur runtime, inte ur vår egen tolk

Det här är kösens tyngsta punkt.

`docs/spec/85_bankkontraktet.md` §2 räknar upp fem lagliga facitkällor, och
regeln är att **facit aldrig får komma ur koden som döms**. Idag dömer
`bank/domare.py` genom vår ST-tolk. Tolken är alltså både den som prövas och
den som dömer. Det är precis den tautologi kontraktet förbjuder.

OpenPLC är en laglig facitkälla: den ligger utanför vår kod, den är den motor
produkten faktiskt använder, och den är skriven av någon annan.

Bygg `bank/domare_openplc.py`: kompilera den genererade ST:n, kör den på
OpenPLC med bankens stimuli, läs I/O-spåret, döm mot samma `facit_spar`.
Samma domarmekanik, annan motor under.

**Trasig fixtur:** en lösning som vår tolk godkänner och som OpenPLC vägrar
kompilera måste bli rött hos den nya domaren, inte grönt och inte ett
körningsfel maskerat som ett underkännande.

## A3 — hur mycket skiljer de två domarna, i tal

Kör hela banken genom **båda** domarna. Rapportera var de är oense.

Det talet är bänkens egen felstapel. Utan det är varje "25 av 26" en siffra
utan osäkerhet.

Var noga med formen: `n` per uppgift, inte en körning. En uppgift som är grön
i tre av fem körningar är inte grön.

**Levererar:** `M-1NN`, och en rad i `docs/spec/85_bankkontraktet.md` om vilken
domare som är den auktoritativa när de skiljer sig åt — med skäl.

## A4 — skanncykeln, som ingen har mätt

Vår tolk har ingen cykeltid. Den utvärderar satser i ordning och är klar.
En riktig PLC kör en **skanncykel**: läs in, kör, skriv ut, upprepa — och allt
som beror på flanker, timers och tillståndsmaskiner beror på den cykeln.

Frågan är inte akademisk. Den avgör om bankens `facit_spar` överhuvudtaget är
välställda: ett spår med tider i millisekunder betyder olika saker vid 10 ms
och 100 ms cykel.

Mät: hur många av bankens uppgifter ändrar dom när cykeltiden ändras? Svep
minst tre cykeltider. Rapportera per uppgift.

Om svaret är "inga" har du visat att banken är cykeloberoende, och det är värt
att veta. Om svaret är "många" har du hittat en tyst antagelse under varje tal
projektet publicerat.

## A5 — exporten ut: PLCopen XML

`M-114` mätte vägen **in** — vad man kan läsa ur ett befintligt styrsystem.
Vägen ut är obyggd, och det är den användaren faktiskt behöver: koden ska
lämna vårt verktyg och landa i deras.

Bygg export till PLCopen XML. Läs sedan tillbaka den egna filen och jämför —
en export som inte överlever sin egen import är ingen export.

**Trasig fixtur:** en konstruktion som exporteras men inte kommer tillbaka
likadan måste fällas, inte tystas.

## A6 — vad som faktiskt öppnas hos en tillverkare

Det här är punkten där det är lätt att skriva ett påstående i stället för att
mäta. Gör inte det.

Ta reda på, med belägg, vilka format som går att importera i CODESYS, TIA
Portal och TwinCAT. Ett påstående räknas bara om du har en fil som öppnas —
eller en dokumenterad specifikation från tillverkaren med sidhänvisning.

Om du inte kan pröva importen (ingen licens, ingen maskin), skriv det som
**oprövat** med exakt vad som saknas för att pröva det. Ett ärligt "oprövat"
är värt mer än ett "bör fungera".

## A7 — larmet, tidsvakten och förreglingen

`M-89` hittade det skarpaste hålet i hela projektet: modellen skriver kod som
**återger inspelningen** och ändå saknar tidsvakten, larmen och förreglingarna.
Ur ett produktionsspår blev det 0 av 2.

Det är inte ett bänkproblem. Det är ett produktproblem: koden ser rätt ut,
kör rätt, och saknar allt som gör den industriell.

Bygg en grind som fäller kod utan tidsvakt på varje rörelse som kan fastna,
utan larmutgång för varje feltillstånd uppgiften nämner, och utan förregling
mellan aktuatorer som kan kollidera. Var och en med sin trasiga fixtur.

Reglerna ska matas in i systemprompten via `plc/forhandsregler.py`, som redan
gör det för de befintliga klasserna — så modellen får veta kravet innan den
skriver, inte efter.

---

## Överflöd — när de sju punkterna är slut

**A8. Vad OpenPLC gör som IEC 61131-3 inte säger.** Varje motor har sina egna
avvikelser. Hitta dem: heltalsspill, division med noll, `TIME`-aritmetik över
dygnsgränsen, strängar över sin deklarerade längd. För var och en: vad säger
standarden, vad gör matiec, vad gör vår tolk. Skillnaderna hör hemma i
`tests/enhet/test_st_svep_mot_strucpp.py`-mönstret som permanenta fall.

**A9. Retentiva variabler över omstart.** `RETAIN` betyder att värdet överlever
en varmstart. Vår tolk har inget omstartsbegrepp alls. Bygg det, och mät hur
många av bankens uppgifter som skulle döma annorlunda med en omstart mitt i
spåret.

**A10. Flanken över skanngränsen.** `R_TRIG` som utvärderas två gånger i samma
skann ger olika svar beroende på ordning. Bygg en uppgift där ordningen spelar
roll, kör den på båda motorerna, och se om de är överens. Det är den klassiskt
svåraste buggen i PLC-kod och vi har inte prövat den en enda gång.

**A11. Vad händer när ST:n är korrekt men PLC:n inte hinner.** Cykeltiden är
ett tak. Skriv kod som är riktig men för långsam för sitt eget tak, och mät om
någon del av kedjan säger till. Om ingen gör det: en användare kan få kod som
fungerar i bänken och missar sin deadline i verkligheten.

**A12. Läs `docs/spec/60_plc.md` mening för mening.** Varje mening som ingen
kod uppfyller blir en rad i en lista med filnamn och radnummer där den borde ha
uppfyllts. Listan är nästa kö, och den är värd mer än gissningar om vad som
saknas.
