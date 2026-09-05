# Kö B — bänken i skala: de 37 svaren, spridningen och enskottet

Läs `docs/uppdrag/00_GEMENSAMT.md` först.

## Din yta

`bank/uppgifter/*.json`, `bank/domare.py` (bara efter samråd med kö A, som
bygger en andra domare), `tests/protocol/kor_fas9_*`, `tests/protocol/kor_B*`,
`docs/spec/80_bank.md`, `docs/spec/85_bankkontraktet.md`, egna `M-1xx`.

## Läget, mätt

Banken bär **63** uppgifter. **26** har `facit_spar`. De 37 som saknar det är
**inte** halvbyggda — de bär prompt, scen, signalkarta, fysik, `expect`,
`scenarios`, `failure_modes`, `antaganden`, `targets_class`, `stege` och
`orsak`, allihop. De saknar **exakt ett fält**.

Måttet på återstående arbete är alltså **37 svar**, inte 37 uppgifter.

`M-110` körde flerskott över de 26: **25 av 26 lösta**, median 2 varv, på
Muse Spark 1.3. Enskott är inte kört över skalan — `M-96`:s "0 av 20" vilade
på **fyra** celler, och hela enskottseffekten satt i **en** av dem (S-05, 0 av
5 → 5 av 5). Ett annat urval av fyra hade gett ett annat tal med samma regler.

---

## B1 — de 37 svaren

Skriv `facit_spar` och en referenslösning för de 37.

Kontraktet gäller: `docs/spec/85_bankkontraktet.md` §2 räknar upp fem lagliga
facitkällor, och ett spårfacit **härlett ur uppgiftens egna `scenarios` och
`expect`** är lagligt enligt klass 4 — de skrevs före all kod.

Det som är förbjudet är ett facit ur samma tolk som dömer det. Om du märker att
du kör lösningen genom vår ST-tolk för att få fram spåret, har du brutit
kontraktet. Skriv spåret ur uppgiftens text.

**Trasig fixtur:** ett facit som producerats genom att köra referenslösningen
måste avvisas av en mekanism, inte av god vilja.

Committa i småsteg: några uppgifter per commit. En avbruten körning har
tappat tio lösta uppgifter i det här projektet redan.

## B2 — enskott över hela banken, med och utan regler

Det här är operatörens fråga, ordagrant: *"100 % reliable structured text,
preferably oneshotted"*.

Kör enskott över hela banken, i två armar: med grindreglerna i systemprompten
och utan. `plc/forhandsregler.py` bygger reglerna.

Kravet som gör körningen värd något: **n ≥ 3 per uppgift och arm**, så
spridningen går att rapportera. Ett `n = 1` säger ingenting om
tillförlitlighet, och tillförlitlighet är hela frågan.

Rapportera per uppgift: hur många av n som löstes, inte bara ett medelvärde.
En uppgift som är grön 1 av 3 gånger är inte grön.

## B3 — flerskottets varvfördelning

`M-110` gav median 2 varv men rapporterade inte fördelningen. Kör om med
`n ≥ 3` och rapportera hela fördelningen: hur ofta 1, 2, 3, 4+ varv.

Det är den siffran som säger om taket på fyra varv (`M-52`) är rätt satt.
Ligger massan på 1–2 är taket generöst. Ligger den mot 4 är taket det som
skapar "olöst".

## B4 — H-01, och transporten som flagnar

`M-110` fann att `H-01` krävde åtta försök med tomma svar och timeouter, och
att en direktsond med samma fråga gav korrekt ST. Slutsatsen var *"flagnande
transport, inte uppgiften"*.

Den slutsatsen är rimlig och omätt. Mät den: kör samma fråga n gånger och
räkna hur ofta transporten faller. Om felfrekvensen är verklig ska
modellklienten ha en omförsökspolicy — och den policyn ska ha ett tak och
synas i utdatan, aldrig tyst dölja hur många försök som gick åt.

Ett omförsök som inte syns i talen är en dold rabatt på tillförlitligheten.

## B5 — kostnaden som aldrig mättes

`tests/protocol/kor_fas9_musespark.py` skriver `kostnad_usd=0.0`.

Repots invariant är att `None` betyder **okänd** och `0.0` betyder **mätt till
noll**. Modellen är gratis, så noll är sannolikt sant — men koden har aldrig
läst ett kostnadsfält, den har antagit. Summerar någon senare Sonnet-armens
0,294 USD med den här armens 0,0 får de ett tal som ser mätt ut.

Ta reda på om `opencode`:s JSON rapporterar kostnad. Om ja, läs den. Om nej,
skriv `None` och låt gratisnivån stå som en mening i mätningen i stället för
som en nolla i koden.

## B6 — baslinjen parad med varje tal

`M-62` byggde en regelbaserad generator utan språkmodell över samma bank och
samma domare. Fas 11:s regel är att fas 9:s tal **alltid rapporteras som par**:
vårt mot baslinjens. Ett tal utan baslinje publiceras inte.

Banken har vuxit sedan dess. Kör om baslinjen över hela den växta banken, så
att B2 och B3 kan rapporteras parat. Utan det är de nya talen inte
publicerbara enligt projektets egen regel.

## B7 — kontraktsrevision

Gå igenom alla 63 uppgifters `facit_spar` mot `85_bankkontraktet.md` §2 och
klassa varje facit i en av de fem lagliga källorna. Varje facit som inte går
att klassa är ett facit vi inte vet varifrån det kommer.

Mekanisera klassningen som ett fält i uppgiften, och gör det obligatoriskt.
`docs/spec/85_bankkontraktet.md` säger redan att facitkällan aldrig får ligga
i `under_prov` — det är en regel utan mekanism idag.

## Om du blir klar

Ta `docs/spec/83_scenarier.md` och mät täckningen: hur många av de scenarier
specen beskriver har någon uppgift i banken? Varje scenario utan uppgift är en
sorts fel vi säger oss pröva utan att pröva den.
