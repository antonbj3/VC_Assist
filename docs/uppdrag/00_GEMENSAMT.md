# Gemensamt för uppdrag A–E

Fem sessioner arbetar samtidigt i **ett** repo, `~/projects/VC_Assist`, i tio
timmar. Det här dokumentet är det som gäller alla fem. Din egen brief säger vad
just du ska göra.

Läs `docs/spec/00_index.md` först. Läs sedan `docs/spec/96_ingen_skuld.md` —
den är operatörens krav, inte en stilguide.

## Att fem delar ett repo

**Committa aldrig med `git commit` direkt.** Använd:

```
scripts/committa.sh "<meddelande>" <sökväg> [<sökväg> ...]
```

Den tar ett exklusivt lås, stagar **bara** de sökvägar du namnger, visar vad
som blev stagat, committar samma sökvägar och kontrollerar efteråt att inget
av ditt blev kvar ostagat. Skälet är mätt, inte befarat: `git commit -- <väg>`
i en delad worktree har tappat rader som redan var stagade, och två samtidiga
`git commit` river varandras `index.lock`.

**Aldrig `git add -A`, `git add .` eller en glob.** En glob i ett delat repo
stagar någon annans halvfärdiga arbete. Namnge filer.

**Aldrig `git stash`, aldrig `git reset` utan `-- <sökväg>`, aldrig `git gc`.**
Stash i ett delat repo river de andra fyras arbete. `git gc` behöver lika
mycket ledigt utrymme som packen är stor och fyllde disken senast den kördes.

**Committa i små steg.** Ett serverfel mitt i ett långt pass har nollat en hel
sessions minne förut. Committa varje färdig sak för sig.

**Innan du raderar en fil**, kontrollera att den inte är spårad:
`git cat-file -e HEAD:<sökväg>`.

**Låset skyddar indexet, inte innehållet.** Det hände på riktigt medan de här
köerna skrevs: två skrivare la var sin `BANKPOST` överst i samma fil inom några
minuter, båda committade utan konflikt, och filen fick två poster där läsaren
bara läser den första. Låset kan inte hindra det — bara ytindelningen kan.
Läs filen precis innan du ändrar den, och håll dig till din yta.

## Sökvägar som är dina

Varje brief har ett stycke **"Din yta"**. Rör inte filer utanför den utan att
säga till. Om du måste, säg det i committmeddelandet.

## Disciplinerna

Det här är projektets, och de gäller varje rad du skriver.

* **Ingen stub som returnerar framgång.** En funktion som inte gör sitt jobb
  ska falla, inte svara `True`.
* **Ingen tröskel utan mätreferens.** Skriver du `if x > 0.8`, ska det finnas
  en mätning som säger varifrån 0,8 kommer. Annars är talet en gissning som
  ser ut som kunskap.
* **Ingen grind utan trasig fixtur.** En grind som aldrig fällt något är en
  grind som inte är prövad. Skriv fixturen **före** mekanismen, se den vara
  röd, bygg sedan mekanismen.
* **Varje mätning blir `docs/matningar/M-NN_<namn>.md`.** Reservera numret med
  `scripts/nytt_matningsnummer.sh <kort_namn> "<titel>"` — den tar samma lås
  som committa.sh och skapar filen med rätt rubrikform. Gör det **inte** för
  hand: två sessioner tog M-124 inom 91 sekunder från start idag, båda enligt
  den gamla regeln "kolla högsta numret först". Läs-sedan-skriv är en
  kapplöpning när fem skriver. En siffra utan härkomst är ingen siffra.
* **Kör aldrig prov genom ett rör.** `pytest ... | tail` ger dig `tail`:s
  slutkod, och ett rött prov ser grönt ut. Skriv till fil och läs filen:
  `cmd > ut.txt 2>&1; echo "rc=$?"; tail -20 ut.txt`. Det här har kostat
  projektet fyra falska nollor på en natt.
* **`tests/motbevis` ska vara röda.** De är motbevis. Den gröna sviten är
  `tests/enhet`.
* **Ett facit får aldrig komma ur koden som döms.** `docs/spec/85_bankkontraktet.md`
  räknar upp fem lagliga facitkällor. Ett facit härlett ur samma tolk som
  dömer det ska avvisas.
* **All kod som körs inne i Visual Components måste vara giltig i både
  Python 2.7 och 3.x.** VC bär Stackless Python 2.7.1 utan `clr`, `System`
  eller .NET.
* **Sök aldrig efter en process på hela kommandoraden.** Din egen sökning
  matchar sig själv. Det har hänt tre gånger här. Använd
  `svc/vc_assist_svc/processer.py`.

## Visual Components

* Operatörens prefix är `~/.wine-vc`. **Rör det aldrig.**
* Allt oprövat körs i `~/.wine-vc-test`, som har egen Documents i
  `~/vc-test-documents`.
* Starta VC med `~/bin/vc-test.sh`. Den sätter `DISPLAY=:99`.
* VPN till licensservern: `~/bin/vpn-skolan.sh start`.
* Tilläggets sökväg är `My Commands/Python 2/<paket>/` — mätt i M-01.
* VC:s världsenhet är **millimeter**. Kvaternionen är skalär först:
  `(x,y,z,w) = (q.Y,q.Z,q.W,q.X)` (M-72).
* `WorldPositionMatrix` släpar en scenuppdatering. Bara `sim.update()` fräschar
  upp den.

## Maskinen

Tunga steg körs alltid `nice -n 19 ionice -c3` och med trådtak. Fem sessioner
plus operatörens skrivbord delar en maskin; ett jobb som tar alla kärnor får
skärmen att hacka. Disken var på 96 % i morse — kolla `df -h /` innan du
skriver något stort, och lägg stora mellanfiler i din scratchpad, inte i repot.

## När du är klar med en punkt

Skriv mätningen, committa den med `scripts/committa.sh`, och gå vidare. Rapportera
inte i chatten vad som står i en fil — operatören läser inte rapporter, han
läser resultat.

**Om en punkt visar sig vara fel ställd fråga:** säg det, mät det som var rätt
fråga i stället, och skriv ner varför den första var fel. Det är ett fullgott
resultat. Det som inte är fullgott är att svara på den fel ställda frågan.
