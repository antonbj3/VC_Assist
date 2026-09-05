# Kö D — ögat, scenen och den femte domaren

Läs `docs/uppdrag/00_GEMENSAMT.md` först. **Du är den enda kön som startar
Visual Components** — läs VC-stycket där noga.

## Din yta

`ext/vc_addon/vc_assist/oga_*.py`, `svc/vc_assist_svc/oga*`, `bank/anlaggning.py`,
`tests/protocol/kor_fas15_*`, `tests/protocol/kor_D*`, `docs/spec/40_ogat.md`,
`docs/spec/41_ogat_kontrakt.md`, `docs/spec/42_ogat_utbyggt.md`, egna `M-1xx`.

## Läget, mätt

Ögat är det mest prövade i projektet, och gränsen är känd med namn.

* `M-86`: hela scenen i serie, **812 objekt**, meter åt båda håll, **noll
  drift**, 4,3 µs per komponent och prov.
* `M-87`: hopfogningens tak mätt mot VC:s brygga. `RUN` i **604 av 604**.
* `M-88`: **4 av 5** domare fäller VC-byggda celler ensamma — grepp, sekvens,
  timing, kollision — med `station_bra` som grön kontroll.
* `M-97`: under processtopp håller taket **inte**: 7 av 300, +1,09 s.

Fyra öppna punkter står kvar, och de är dina.

---

## D1 — den femte domaren, fälld av en riktig cell

Genomflödesdomaren sa **PASS på en utsvulten station**. Orsaken var inte
domarens logik utan att `vcStatistics` låg inert och `state` var tom sträng.
Den är lagad till INCONCLUSIVE med VC-raden som fixtur — men **ingen
VC-byggd cell fäller den**, för `State` går inte att sätta utan en riktig
process bakom komponenten.

Det betyder att fyra domare är prövade mot verkligheten och den femte bara mot
en syntetisk rad. Så länge det står så är genomflöde en domare vi *tror* på.

Bygg en cell i riktig VC med en process som faktiskt svälter: en matare som
inte matar, en transportör som står, en sänka som inte tar emot. Kör den. Se
domaren fälla den av **rätt skäl** — inte INCONCLUSIVE för att data saknas,
utan FAIL för att genomflödet är för lågt.

**Trasig fixtur, före mekanismen:** samma cell med tillräcklig matning måste
vara grön. En domare som fäller allt är lika värdelös som en som släpper allt.

## D2 — P15-7

Protokollpunkten är skriven och inte körd. Kör den. Om den visar sig vara fel
ställd fråga, skriv om den och säg varför.

## D3 — braketten på körningsnivå

Osäkerhetsbraketten på körningsnivå har bara fällt **fixturer**, aldrig något
verkligt. En grind som bara sett sina egna provfall vet inte om den fäller
rätt saker i verkligheten.

Kör den mot riktiga körningar ur VC tills den fällt minst ett verkligt fall
— eller tills du kan visa, med tal, att inget verkligt fall ligger utanför
braketten. Båda är resultat. Att inte veta är det som inte duger.

## D4 — taket under processtopp

`M-97` mätte att hopfogningens tak spricker under processtopp: 7 av 300
avläsningar, +1,09 s. Störningen var en känd SIGSTOP.

Två frågor, och den andra är den viktiga:

1. Håller taket om störningen är en riktig belastning i stället för SIGSTOP?
   Fem sessioner kör på maskinen just nu — du har naturlig belastning gratis.
2. **Vad gör ögat när taket spricker?** Om svaret är "rapporterar ett värde
   ändå", är varje tidsdom under belastning opålitlig utan att någon märker
   det. Det ska synas i utdatan, inte tigas ihjäl.

## D5 — en riktig anläggning, eller en ärlig gräns

`M-89` mätte fas 18 med bankens **egna referenslösningar** som källa. Talen:
28 av 28 förreglingar återfinns ur ett provspår, **3 av 28** ur ett
produktionsspår. `EMG_OK` gick aldrig till 0 i något av fyra produktionsspår.

Specen säger rakt ut: *"ingen riktig anläggning är inspelad"*.

Två vägar, välj den som går:

* Spela in ett riktigt I/O-spår. Även en liten rigg räknas — en enda
  transportör med två givare är en riktig anläggning.
* Om ingen finns att nå: skriv gränsen som en mätning. Vad exakt skiljer ett
  produktionsspår från ett provspår, och vilka av bänkens påståenden slutar
  gälla när källan byts? Talet 3 av 28 är en varningsklocka som ingen ännu
  har följt till botten.

## D6 — en lina, en gång

Fas 8 byggde **en** lina med två stationer och fällde fem kompositionsfel som
båda enstationskörningarna släppte igenom. Det är ett starkt resultat ur ett
enda försök.

Ett urval på ett är inget urval. Bygg minst fyra linor till, med olika
topologi: seriell, med buffert, med parallella grenar, med återflöde. Mät
kompositionsdomarnas träff per topologi.

Om en topologi inte fäller något är det ett fynd om domaren, inte om linan.

## D7 — motsägelsen i README

`README.md` säger att fas 10 är **stängd** via `M-112`. Men avsnittet
*"Fas 10 i detalj"* längre ner säger att fasens **öppna punkt** är att VC
startar med det installationen lade dit.

Ett av de två är fel. Ta reda på vilket genom att köra det: installera i
testprefixet, starta VC med `~/bin/vc-test.sh`, läs `vc_assist_boot.log`.
Rätta sedan den av de två texterna som ljuger.

Det här är precis den sorten teknisk skuld projektet är strängast mot: något
som **felaktigt tros vara gjort**.

## Om du blir klar

`docs/spec/42_ogat_utbyggt.md` är enligt fasplanen *"ospecificerat i faser"*.
Skriv fasplanen för resten av den: varje mening i specen ska ha en fas, en
grind och en trasig fixtur, eller strykas som något vi inte tänker bygga.
