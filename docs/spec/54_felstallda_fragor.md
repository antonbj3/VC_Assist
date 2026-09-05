# 54 — Fem frågor vi svarat skickligt på utan att pröva om de var rätt frågor

`53_utvagen.md` visade en: *"kan vi exportera scenen?"* var fel fråga, för en
cell är nio lager och det som måste flytta är receptet, inte renderingen.

Det här dokumentet samlar de övriga jag hittat, och planen för var och en. Formen
är densamma varje gång: **ett tal vi mäter noggrant, och ett tal ingen mätt.**

---

## §1 "Är den genererade koden korrekt?"

**Vad vi mäter:** att koden passerar fem grindar och stämmer med bänkens facit.

**Vad vi inte mäter:** om facit är rätt sak att vilja. Bankens 63 uppgifter är
**skrivna av oss**. En bänk man skriver själv mäter sin egen fantasi — samma
felklass som ett facit ur koden som döms (`85_bankkontraktet.md` §2), en nivå
upp.

`M-89` är undantaget och pekar ut vägen: ett **inspelat I/O-spår från en
verklig anläggning** är ett facit ingen av oss hittat på.

**Plan.** Varje ny bänkuppgift ska ha en facitkälla ur `85`:s två starkaste
klasser — en standardparagraf eller en mätning av verkligheten. En uppgift vars
facit bara är *"en människas facit skrivet före"* räknas som svagare och märks
så i uppgiftsfilen.

---

## §2 "Hur tillförlitlig är modellen?"

**Vad vi mäter:** andelen lösta. Enskott 6 av 20, flerskott 3 av 4.

**Vad vi inte mäter:** vad det kostar att **granska** ett svar. För ett verktyg
är den avgörande storheten inte träffsäkerhet utan **sparad tid**. Ett verktyg
som har rätt 30 % av gångerna och där kontrollen tar tio sekunder är bättre än
ett med 90 % där kontrollen tar en timme — och vi vet inte vilket vi byggt.

Vi har inte heller mätt **latensen till ett konvergerat svar**, bara till ett
första.

**Plan.** Mät två tal per bänkkörning: tid till ett svar som passerar alla
grindar (inte till första svaret), och storleken på det en människa måste läsa
för att lita på det. Det andra går att uppskatta mekaniskt — rader kod plus
rader domstext.

---

## §3 "Fångar grinden fel?"

**Vad vi mäter:** att grindar fyrar. `M-111`: 37 av 68 fällplatser fyrar, 31
aldrig.

**Vad vi inte mäter:** om grinden fångar fel **en ingenjör inte hade sett**. En
grind som bara fäller det en erfaren människa upptäcker på fem sekunder tillför
ingenting utom fördröjning. Vårt starkaste resultat är just av den motsatta
sorten — fas 8:s kompositionsfel som **båda stationerna passerade** — men vi har
aldrig mätt hur stor andel av alla domar som är av den sorten.

**Plan.** Klassa varje felklass efter om den är **lokal** (syns i en fil) eller
**icke-lokal** (kräver att man ser flera delar samtidigt, eller en körning).
Rapportera andelen icke-lokala domar. Det är grindkedjans egentliga
existensberättigande, och talet finns inte.

---

## §4 "Ögat säger PASS"

**Vad vi mäter:** att cellen gör rätt sak i simuleringen.

**Vad vi inte mäter:** hur långt det räcker. `50_grindar.md` skriver själv ut
räckvidden — *"sensorstuds, ställdonsdynamik, fältbussjitter och verklig
hårdvara"* saknas — men ingen har mätt **hur stor** skillnaden är. Ett grönt öga
betyder i dag *logiskt riktigt i en värld utan brus*, och det påståendet är
svagare än det låter.

**Plan.** Injicera bruset i simuleringen i stället för att beskriva det:
sensorstuds som en signal som studsar, jitter som en fördröjning med spridning,
en ställdonsfördröjning. Mät hur många celler som är gröna med brus och röda
utan. Faller inga är antingen bänken för lätt eller bruset för litet, och båda
är fynd.

---

## §5 "Enskott eller flerskott?"

**Vad vi mäter:** andelen lösta på första försöket.

**Vad vi kanske optimerar fel:** en slinga som **konvergerar pålitligt på tre
varv** kan vara strikt bättre än ett enskott som träffar 30 %. Grindarnas ord
tillbaka är produktens kärna, inte dess reservutgång — det var hela poängen med
kompositionsfasen. Enskott är billigare, inte bättre.

**Plan.** Rapportera alltid tre tal tillsammans, aldrig ett: andel på första
försöket, andel inom taket, och **varv till konvergens**. Ett enskottstal utan
de andra två inbjuder till fel slutsats.

---

## §6 Vad teknisk skuld faktiskt visade sig vara

Vi har behandlat skuld som *det som är omärkt färdigt* — `TODO`, stubbar,
oprövade moduler. Mätningarna hittade något annat om och om igen:

| | |
|---|---|
| en grind som bar **motsatsen till sitt eget fältnamn** | `_sekvens`, fel åt båda hållen |
| en regel om tecken som **inte kunde skriva tecknen** | translittererad ASCII-text om `å ä ö` |
| en räkning på 584 **utan medlemmar** | gick inte att revidera |
| en ordlista på **25 % recall** som såg fullständig ut | säkerhetsorden |
| en tidsliteral som avvisade **giltig** ST | halva regexen skiftlägesokänslig |
| ett täckningstal där **31 av 68** platser aldrig fyrat | såg ut som täckning |

Ingen av dem var omärkt. Alla såg **färdiga** ut.

> **Skuld är inte det som är ogjort. Det är det som felaktigt tros vara gjort.**

**Plan, och den är den enda som gäller allt annat:** varje påstående som styr ett
beslut ska ha ett prov som visar att det kan vara **falskt**. Det räcker inte att
en grind fyrar; det ska finnas ett fall där den låter bli. Det räcker inte att en
siffra finns; den ska gå att räkna om ur sina delar. Det gäller redan för
ordlistor (`M-105`), fällplatser (`M-111`) och facitkällor (`85`) — och det ska
gälla resten.

---

## §7 Ordningen

1. **§6 först**, som en genomgång: vilka påståenden i repot saknar ett fall där
   de kan vara falska. Det är en mätning, inte en åsikt.
2. **§3**, andelen icke-lokala domar. Billigast av de fyra och svarar på om
   grindkedjan är värd sin fördröjning.
3. **§4**, bruset. Kräver arbete i ögat men är det som skiljer *logiskt riktigt*
   från *driftsäkert*.
4. **§1**, facitkällornas styrka. Löpande, per ny uppgift.
5. **§2 och §5**, talen som ska rapporteras tillsammans. Billiga, och de
   hindrar fel slutsats av rätt mätning.

Ingenting här är byggt. Det är en lista över frågor vi ställt fel, och den är
skriven för att den som läser den ska kunna motbevisa någon av dem.
