# Uppdrag B — tillförlitligheten i skala, och vart varven tar vägen

Repo: `~/projects/VC_Assist`. Läs `docs/spec/00_index.md` först.

> Ersätter det tidigare B-uppdraget om universalitet. Skälet står i §0.

## §0 Varför just det här, och varför nu

Operatörens krav, ordagrant: *"100% reliable structured text, preferably
oneshotted, multi shot som fastnar på grindar och görs om/korrigeras är
fallback."*

Vad som är mätt i dag (`M-96`):

| | utfall |
|---|---|
| enskott, utan grindreglerna | **0 av 20** (n = 5 per uppgift, **4 uppgifter**) |
| flerskott, tak fyra varv | **3 av 4** inom taket, varv 3/1/2 |

**Fyra uppgifter.** Hela tillförlitlighetspåståendet vilar på fyra celler.

Under natten gick banken från 4 till **18 uppgifter med spårfacit** (av 61).
Mätningen har alltså aldrig körts i den skala som nu finns. Det är den enskilt
billigaste förbättringen av projektets svagaste tal — ingen ny kod krävs, bara
körningar och en ärlig läsning av dem.

## §1 Kör bänken i sin nya skala

```bash
python3 tests/protocol/kor_fas9_slingan.py --lage historik --json <ut>.json
python3 tests/protocol/kor_fas9_slingan.py --max-varv 1 --upprepa 5 --json <ut>.json
python3 tests/protocol/kor_fas9_slingan.py --max-varv 1 --upprepa 5 \
        --utan-forhandsregler --json <ut>.json
```

Körningen tar alla uppgifter med `facit_spar` automatiskt. `--uppgift` väljer
en enskild.

Rapportera **andelen per uppgift**, inte bara summan. En uppgift som klaras tre
gånger av fem är något helt annat än en som klaras en gång av fem, och båda ser
ut som "1 av 4" i en enda körning. Det felet är redan gjort en gång: tre armar
gav alla 1 av 4 — på olika uppgift varje gång.

**Committa efter varje arm.** Faller sessionen mitt i är halva mätningen värd
mycket mer än noll.

## §2 Läs varje takslag, en och en

Det här är uppdragets tyngsta del och den som ger mest.

Körningen sparar `domar_per_varv` **och** `kroppar_per_varv` i JSON. För varje
uppgift som slog i taket: läs domarna varv för varv och avgör vart varven tog
vägen. Klassificera varje förlorat varv:

* **format** — kodstaket, icke-ASCII, ramen ändrad. Kostar ett varv och har
  ingenting med uppgiften att göra.
* **falsk rödgrind** — grinden fällde något som fungerar. Det dyraste, för
  modellen lär sig fel sak. `M-99` fann sju, `M-96` en till.
* **verklig brist** — modellen förstod inte uppgiften eller cellen.
* **oscillation** — modellen lagar A och orsakar B, lagar B och orsakar A.

Mallen finns: `M-96` gjorde exakt det för T-07 och fann att **två av fyra varv
gick till ett enda `ä` i en kommentar** — i varv 1 och igen i varv 4 — medan
uppgiften var på väg att lösas (fyra brister i varv 2, **en** i varv 3).

Det talet — **hur stor andel av alla förlorade varv som är format eller falsk
rödgrind** — är uppdragets viktigaste resultat. Är det stort är vägen till
enskott kort och känd.

## §3 Ett tak som aldrig prövats är ett påstående

`M-52` satte taket till fyra varv. `M-96` prövade det mot en riktig modell för
första gången: det räckte i tre fall av fyra.

Med arton uppgifter går frågan att besvara: **hur många varv behövs
egentligen?** Kör de uppgifter som slog i taket om med `--max-varv 8` och se om
de löses på fem, sex eller aldrig. En uppgift som löses på varv sex säger något
annat än en som står still från varv tre.

`ABSOLUT_TAK` är 20 och finns i `svc/vc_assist_svc/plc/reparation.py`. Höj inte
det.

## §4 Vad du INTE ska göra

* **Ändra inte grindarna för att talen ska bli bättre.** Hittar du en falsk
  rödgrind: skriv upp den, mät vad den kostade i varv, och laga den **bara**
  om du kan visa mot STruC++ att kompilatorn accepterar det vi fäller. Att en
  grind är strängare än kompilatorn är ofta rätt och hela skälet att den finns.
* **Ändra inte prompten mitt i en mätning.** Två armar med olika prompt är två
  olika mätningar.
* **Rapportera inte en förbättring du inte kan skilja från brus.** n = 1 per
  uppgift räcker inte. Det är hela poängen med `--upprepa`.

## §5 Om du blir klar

* **Enskott med reglerna, i skala.** `M-96`:s LIMITS säger att armen inte är
  färdigmätt. Arton uppgifter × fem försök ger ett tal som tål att läsas.
* **Kostnaden per löst uppgift.** Flerskott kostade 1,32 USD för fyra celler.
  Vad kostar arton? Det talet behöver den som ska driva bänken.
* **Vilka felklasser som återstår när format och falska rödgrindar är borta.**
  Det är listan över vad som faktiskt är svårt.

## Ofrånkomliga regler

* **Ingen stub som returnerar framgång. Ingen tröskel utan mätreferens. Ingen
  grind utan trasig fixtur.**
* Committa i **små steg**, scopat per fil: `git commit -q --only -m "$MSG" -- <sökväg>`.
  Kör **ALDRIG** `git reset` eller `git stash` utan sökväg — repot delas av
  många skrivare.
* `pytest | tail` ger **tails** returkod, inte pytests. Skriv till fil, läs
  `$?` separat.
* `tests/motbevis` **SKA vara röda**. Grön svit: `python3 -m pytest tests/enhet`.
* Är arbetsträdet rött: `python3 tests/protocol/kor_svit_mot_head.py` kör
  sviten i en ren `git worktree` av HEAD. Grönt där = det röda är någon annans
  pågående arbete.
* Starta **inte** Visual Components. Rör **ALDRIG** `~/.wine-vc`.
* Körningarna kostar pengar och kvot. Kör inte samma arm två gånger av misstag
  — skriv alltid till en namngiven `--json`.

## Filer du äger

`docs/matningar/M-96_slingan_kor_sig_sjalv.md` (fyll i den, ta inte bort det
som står), nya `docs/matningar/M-NN_*.md`, nya `tests/protocol/kor_fas9_*.py`.
**Rör inte** `svc/vc_assist_svc/plc/forhandsregler.py` — den är under granskning
av en annan session.

## Leverans

`docs/matningar/M-NN_<namn>.md` — ta ett **ledigt** nummer från M-109 och uppåt
(M-108 är taget av en annan session), kolla `ls docs/matningar/` precis innan,
och **skapa filen med en `## LIMITS`-stubb direkt**. Spärr mot dubbla nummer,
tak 0.

Rapportera: andelen per uppgift i varje arm, vart de förlorade varven tog vägen
i procent per klass, hur många varv som egentligen behövs, och kostnaden per
löst uppgift.
