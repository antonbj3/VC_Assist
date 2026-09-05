# Kö F — modellen skriver linan, ögat talar tillbaka

> **Läs `docs/uppdrag/RATTELSER.md` innan varje ny punkt.** Köerna skrevs
> innan alla mätningar var klara; ett tal som visat sig fel rättas där.

Läs `docs/uppdrag/00_GEMENSAMT.md` först. **Du startar Visual Components** —
läs VC-stycket där noga. Samordna med kö D, som också rör VC.

## Varför den här kön finns, och varför den är den enda som spelar roll just nu

Projektet har byggt två halvor och aldrig satt ihop dem.

| Kedja | Läge |
|---|---|
| ST skriven **utanför** mätslingan → OpenPLC → VC-scen → ögat | **bevisad** (M-39, M-49, M-73) |
| ST skriven **inuti** mätslingan → vår tolk → dom mot spårfacit | **bevisad** (M-96, M-110) |
| ST skriven **inuti** mätslingan → OpenPLC → **VC-scen** → ögat | **aldrig gjord** |

Mätningarna säger det själva. `M-73`: *"Alla ST-kroppar är handskrivna. Fas 8
påstår att kompositionen går att döma, inte att en språkmodell hittar den."*
`M-50`: *"Fas 7 påstår att vägen finns, inte att en språkmodell hittar den;
det är fas 9."* Och i båda: **"Reparationsvarv: noll."** Ingen modell fick
någonsin ett grindfel tillbaka att laga i en riktig scen.

Ordet "handskriven" är projektets, inte ett noggrant ord — kropparna skrevs av
en tidigare session. Skillnaden som betyder något är inte människa mot modell,
den är **utanför slingan** (full kontext, verktyg, scenen framför sig, hur många
försök som helst) mot **inuti slingan** (en prompt, inga verktyg, ett tak på
fyra varv, en grind som dömer).

`55_innovationsplanen.md` §4 fryser planeringslagret (7 906 rader) och appens
fönster med samma motivering: de betjänar en slinga som ännu bygger en
handskriven lina. **Sex andra beslut väntar på den här kön.**

---

## F1 — falsifieraren, först och minst

`M-74`:s rigg, oförändrad, med **modellen som författare** i stället för
fixturen.

Grönt: linan når **GOLD inom fyra varv i 2 av 3 körningar**, och **minst 3 av
5 kompositionsfall lagas på ögats egna ord** — alltså att ögats
felbeskrivning räcker för att modellen ska rätta rätt sak.

Rött är ett lika giltigt svar, och det ska sägas rakt ut: **faller F1 är
produkten bänken, inte slingan.** Skriv den slutsatsen i mätningen om det
händer. Ett rött F1 är den billigaste sanning projektet kan köpa.

Kör med **n ≥ 3**. A2 mätte att OpenPLC-domaren inte är deterministisk vid
n = 1 — realtidens jitter avgjorde en invariant i L-01. Ett enskilt GOLD
bevisar ingenting.

## F2 — vad ögat måste säga för att modellen ska kunna laga

`M-96` mätte att nio av sexton grinddomar var vår egen bugg och att det drev
uppgifter i taket. F1 mäter samma sak för **ögat**: när modellen får ögats
felbeskrivning tillbaka, lagar den rätt sak?

För varje fall där modellen lagade **fel** sak: var det ögats formulering,
eller uppgiften? Det svaret är produktens kärna. Ögat kan se allt och ändå
vara värdelöst om det inte kan säga vad det såg på ett sätt som går att laga.

Klassa varje misslyckat reparationsvarv i en av tre: ögat sa fel sak, ögat sa
rätt sak otydligt, eller modellen kunde inte laga trots ett tydligt besked.

## F3 — modellen bygger scenen, inte bara koden

Fas 16:s planeringslager tar en fritextbeställning och gör en körbar byggplan.
Fas 20 byggde fyra komponenttyper ur specen i riktig VC. De två har aldrig
mötts i en modelldriven körning.

Låt modellen ta en fritextbeställning hela vägen: plan → byggd scen → ST →
körning → ögats dom. Det är hela produkten i en körning.

**Trasig fixtur:** en omöjlig beställning måste avvisas med vilket villkor som
krockar, inte byggas halvt. Fas 16 har mekaniken; pröva att den håller när
modellen är författare.

---

## F4–F7 — stresstestet: större och svårare scener

Allt som byggts är **en cell till en kort lina**. Fas 8 byggde *en* lina med
två stationer. `M-133` la till fyra topologier idag. Det är inte en skala där
man vet något om skalning.

**F4. Fler stationer.** `M-73` skriver sin egen gräns: *"Fler än två
stationer. Allt här är mätt på två. Att en tredje station inte introducerar en
klass av fel som två inte har är oprövat."* Bygg 3, 5 och 8 stationer och mät
var någonting bryter — domarna, ögats provtagning, modellens kontext, eller
inget alls. Rapportera **vilken** storhet som bryter först.

**F5. Fler produkter samtidigt.** En lina med en produkt i taget döljer varje
kapplöpning. Kör med kö, med blandade produkttyper, och med en buffert som
faktiskt fylls. `T-04` (ackumulerande buffert med 12 platser) och `C-01`
(kapacitetsmål) är bankens närmaste former.

**F6. Längre körningar.** Allt är mätt i sekunder till minuter. En cell som
driver fel efter fyrtio minuter syns inte på tre. Kör minst en timme och mät
om domarna säger samma sak i slutet som i början — `M-86` mätte noll drift
över 812 objekt, men inte över tid under last.

**F7. Scenen under belastning.** `M-97` mätte att hopfogningens tak spricker
under processtopp: 7 av 300, +1,09 s. `M-130` gjorde om det under naturlig
belastning. Kör F1 med maskinen belastad och se om GOLD håller. Om domen
beror på hur upptagen datorn är, är den ingen dom.

---

## Vad som INTE hör hemma här

Bygg inte fönster, meny eller panelfält. `55_innovationsplanen.md` §4 punkt 9
fryser dem tills den här kön är grön, och skälet är gott: en yta framför en
slinga ingen modell drivit igenom är en prospekt.

Rör inte planeringslagret utöver F3. Det är fryst, inte rivet.
