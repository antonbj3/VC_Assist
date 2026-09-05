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

## E3 — M-119: vad hittade den, och vad är den tysta klassen

919 frågor är mätta och osammanfattade. Analysera dem.

Frågan som räknas är inte "hur många procent svarade rätt". Den är: **finns det
en klass frågor där systemet svarar med tillförsikt och har fel?** Ett tyst fel
— ett svar som ser bra ut och är fel — är den dyraste sorten, eftersom ingen
kontrollerar det.

Rapportera per frågeslag, inte som ett totaltal. Ett totaltal döljer exakt den
klass du letar efter.

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

## Om du blir klar

`docs/spec/25_kontextbudget.md` beskriver hur mycket som får plats i en modells
sammanhang. Mät det mot verkligheten: hur stor blir systemprompten med alla
regler från `forhandsregler.py`, och vad ryker först när den inte får plats?
