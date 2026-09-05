# Kö E — Windows, universaliteten och vad en LLM faktiskt hittar

Läs `docs/uppdrag/00_GEMENSAMT.md` först.

## Din yta

`install/`, `ext/vc_addon/vc_assist/plats.py`, `drift/`, `docs/spec/23_llm_granssnitt.md`,
`docs/spec/25_kontextbudget.md`, `docs/spec/35_plattformar.md`,
`docs/spec/46_kunskapsindex.md`, `tests/protocol/kor_m119*`,
`tests/protocol/kor_E*`, egna `M-1xx`.

## Läget, mätt

Operatörens krav är att tillägget ska fungera **med och utan Wine, på Windows
och Linux — universellt**. Allt är byggt och mätt under Wine.

`M-44` hittade nio fynd med fil och rad på Windows-vägen. Ett av dem är tyst
och totalt: **tilläggsmappen hittas inte när Dokument ligger i OneDrive**, och
hela systemet dör efter en enda lograd. Fas 13 är **inte påbörjad**.

`M-119` mätte precis kunskapstäckningen med 919 frågor. Resultatet ligger i
`docs/matningar/m119_kunskapstackning.json`, 448 kB. Det är inte analyserat.

---

## E1 — de 16 protokollpunkterna, körbara utan människa

`M-44` har **16 numrerade protokollpunkter** med var sitt förutbestämda gröna
svar. Regeln är att ingen punkt får besvaras med "borde fungera".

Skriv dem som **ett skript** som kan köras på en Windows-maskin utan att någon
tolkar något: varje punkt ger grönt eller rött med skäl, och skriptet lämnar en
JSON efter sig.

Det gör fas 13 till en körning i stället för ett projekt. Just nu väntar den på
en maskin som ingen har; efteråt väntar den på fem minuter av någons tid.

Skriptet ska bara bero på Python 3 och standardbiblioteket. Ingen `pip install`
på en maskin vi inte äger.

## E2 — OneDrive, det tysta totala felet

Det värsta felet i projektet är tyst: sökvägen hittas inte, och systemet dör
efter en lograd. Användaren ser ingenting.

Två saker, i den ordningen:

1. **Gör felet högljutt.** Innan sökvägen fungerar ska felet säga vad som är
   fel och var det letade. Ett tyst fel är dyrare än ett trasigt.
2. **Lös sökvägen.** `plats.py` ska hitta Dokument även när det ligger under
   OneDrive. `ntpath.expandvars` är rätt verktyg på Linux för `%VAR%` —
   `os.path.expandvars` expanderar inte Windows-form.

**Trasig fixtur:** en fejkad OneDrive-katalogstruktur där sökningen ska lyckas,
och en där den ska misslyckas **med ett tydligt besked**.

## E3 — M-119 är mätt. Det här är reparationerna den kräver.

`M-119` är körd och skriven: 1 025 frågor, 814 svarade, 211 kräver VC.
Resultatet är inte "50 % täckning" — det är **två skarpa halvor**. Sex
frågeslag av tretton svarar **noll**: konstanterna `VC_*`, enheter på
properties, signalkartan, standarderna, grindreglerna och komponent-i-bibliotek.
Summan döljer det, precis som `M-96` lärde en gång.

Mät inte om det. Laga det. Fem punkter, i fallande ordning av vad de kostar:

**E3a — nollan som ser ut som en mätning.** Biblioteket säger
`rackvidd_mm = 0` för ABB IRB 1200-7/0.7; tillverkaren säger 703 mm. Det
gäller **1 119 av 3 201 rader (35,0 %)** för räckvidd och **628 (19,6 %)** för
nyttolast. Formatet kan redan säga *okänd* — `None` står i 645 respektive 215
rader — så skillnaden mellan **noll** och **saknad** finns i datan och tappas i
läsningen. En nolla som läses som ett mätvärde är projektets egen doktrin om
härkomst, bruten i vår egen kod.

Laga läsningen så att saknat aldrig kan läsas som noll. **Trasig fixtur:** en
rad med `None` som blir `0` i svaret ska fällas.

**E3b — grindreglerna finns men går inte att nå.** Tio av 31 grindfrågor fick
träffar i fel domän. Det rätta svaret står **komplett på disk** i
`docs/spec/41_ogat_kontrakt.md`, med enheter — och **ingen datahanterare öppnar
`docs/spec/` vid körning**. Bara `docs/referens/vc_api/` och `vc_dotnet/` läses.

Öppna `docs/spec/` för uppslagen. Det är en av de billigaste rättelserna i
projektet och den stänger ett helt frågeslag.

**E3c — `bench_task` utelämnar 9 av 23 fält.** Bland dem `control`
(signalkartan), `fysik` och `facit_spar` — och 26 uppgifter bär
klausulhänvisningar till standarder just i `facit_spar`. Det förklarar två av
de tomma frågeslagen på en gång: signalkartan svarar 0 av 94 och standarderna
0 av 23, för att fälten aldrig kommer fram.

**E3d — 709 konstanter utan en enda beskrivning.** 100 % av konstanterna, 100 %
av typerna och 100 % av händelserna saknar beskrivning; properties 0 %, metoder
6,5 %. Indexet kan bekräfta att `VC_BOOLEANSIGNAL` finns, men inte att 88,1 %
av biblioteket saknar boolean-signal — så `findBehavioursByType(...)[0]` kastar.
`M-84` visade att det är just den klassen uppslag som är mest värd: de som
svarar **SAKNAS**.

**E3e — delsträngsträffen som ljuger.** `RACE` gav `vcHelpers.Robot.traceOn`,
eftersom "race" ligger inne i "trace". `MINDIST` gav
`vcCurveData.getCurveMinDistance`. Rangen `delstrang_namn` producerar tysta
fel med hög tillförsikt. Antingen ska den rangen kräva en ordgräns, eller så
ska svaret säga att träffen är en delsträng. **Trasig fixtur:** `RACE` får
inte ge `traceOn` utan att svaret säger varför.

En sjätte, billig: 26 av 238 API-svar namnger en **annan typ** än den man
frågade om — ärvda medlemmar, `vcComponent.findBehavioursByType` svarar
`vcNode...` — samtidigt som samma svar avslutas med "använd namnet exakt som
det står". Svaret motsäger sig självt i sin egen sista mening.

## E4 — kan en LLM hitta det den behöver

Operatörens krav, ordagrant: *"Informationen måste vara lättillgänglig för
LLM"*. Kravet är inte att informationen är korrekt — det är att den går att
hitta och använda: litet ordförråd, kort form, enhet och härkomst i värdet.

Gör en pseudo-simulering i skala: ta ett femtiotal verkliga uppgifter systemet
ska klara, och för varje fråga vilken information som krävs och om den går att
nå. Räkna **täckning**, inte mängd.

Ett mätt exempel från det här projektet, värt att bära med sig: när en modell
fick API-uppslag *halverades* koden — men antalet distinkta API-namn gick från
13 till 32. Mängdmått pekade åt fel håll; ordförrådet pekade rätt. Mät bredd,
inte volym.

De uppslag som gav **SAKNAS** var de mest värdefulla.

## E5 — Python 3.7–3.9, oprövat

README säger att koden inte använder något nyare än `dataclasses` (3.7) och att
den är körd på 3.10.12 och 3.13.11. 3.7–3.9 står som **OPRÖVAT**.

Antingen prova dem — containrar räcker, ingen VC behövs — eller ta bort
påståendet. Ett "borde fungera" i en kompatibilitetstabell är ett löfte vi inte
har täckning för.

Samma sak för `ext/`-halvan: allt som körs i VC måste vara giltigt i **både**
2.7 och 3.x. Mekanisera kontrollen så att den körs vid varje installation, inte
bara när någon minns den.

## E6 — installationen på Windows

Fas 12 säger *"Windows-vägen oprövad"* om verktygskedjan: STruC++, OpenPLC och
node hämtas med fastspikad version och kontrollerad hash — på Linux.

Kör samma sak på Windows-vägen, eller visa exakt var den bryts. Hashkontrollen
måste hålla: en manipulerad nedladdning ska avvisas.

## E7 — universaliteten som en mätning, inte ett påstående

Till sist: skriv `docs/matningar/M-1NN_universaliteten.md` som en tabell över
varje kombination av operativsystem, Python-version, VC-version och
Wine/inte-Wine, med tre möjliga celler: **mätt**, **oprövat**, **går inte**.

Ingen cell får säga "borde fungera". Tabellen blir README:s
kompatibilitetsavsnitt, och den blir ärlig.

---

## Överflöd — när de sju punkterna är slut

**E8. En ren maskin, hela vägen.** `M-90` körde installationen på en ren
Linux-maskin. Gör om det för hela kedjan: klona repot i en tom container, följ
README steg för steg utan att veta något, och skriv ner varje ställe där en
instruktion inte räcker. En instruktion som kräver att man redan kan systemet
är ingen instruktion.

**E9. Felmeddelandena som användaren möter.** Gå igenom varje felväg i
`install/` och `ext/` och läs meddelandet som en användare som inte byggt
systemet. Säger det vad som är fel, var, och vad man gör åt det? Ett fel som
bara namnger ett undantag är ett fel som skickar användaren till oss.

**E10. Vad tillägget gör när VC är en annan version.** VC 4.10 är mätt. Vad
händer i 4.9 eller 5.0 — dör tillägget tyst, eller säger det ifrån? Bygg
versionskontrollen så att en oprövad version säger *oprövad*, inte kraschar och
inte låtsas fungera.

**E11. Kontextbudgeten mot verkligheten.** Mät hur stor systemprompten blir med
alla regler från `forhandsregler.py`, och vad som ryker först när den inte får
plats. Om reglerna trängs ut av uppgiftstexten faller grindarna tyst — och det
är precis den sortens tysta fel `M-119` letade efter.

**E12. Skriv README:s installationsavsnitt om, mätt.** Varje steg ska ha körts
av dig, i den ordningen, på en maskin utan förkunskap. Varje påstående som du
inte kört stryks eller märks **oprövat**.

**E13. Leverantörsdokumentationen får inte följa med ut — och ska inte det
heller.** `docs/referens/vc_api/` och `docs/referens/vc_dotnet/` är **4,6 MB
av Visual Components egen dokumentation**, tio filer, tagna ur en installation.
`Create3D.Shared.xml` är deras .NET-dokumentation rakt av. Ett publikt repo som
bär dem sprider leverantörens material.

Det är dessutom fel konstruktion oavsett juridiken: vi skeppar **4.10:s**
API-yta till en användare som kanske kör 4.9 eller 5.0, och indexet blir tyst
fel för dem — samma klass av fel som `M-119` just mätte.

Bygg en **extraktor** som läser API-ytan ur användarens egen VC-installation och
bygger indexet lokalt vid installationen. Fas 4 mätte 3 444 symboler ur
`api.xml` med 0 falskt positiva och 0 falskt negativa; extraktorn ska klara
samma prov mot en lokal installation.

Sedan: ta bort leverantörsfilerna ur det som publiceras, och lägg in en
kontroll i utgivningen som fäller om de kommer tillbaka. **Trasig fixtur:** en
`docs/referens/`-fil i utgivningsträdet ska stoppa utgivningen.

**E14. Bryggans token är en fast sträng.** `ext/vc_addon/vc_assist/plats.py`
har `TOKEN = "vc_assist_token"`. Bryggan lyssnar på `127.0.0.1:8901`, och vilken
lokal process som helst kan alltså tala med den och köra kod i VC genom kön.

För en brygga som bara lyssnar på loopback är det försvarbart. Men det ska vara
ett **beslut med skäl i `docs/spec/31_brygga_protokoll.md`**, inte något som
råkade bli så. Skriv beslutet — eller generera token per session och lägg den
där bara ägaren kan läsa den. Välj, och skriv varför.
