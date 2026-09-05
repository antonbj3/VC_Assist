# Uppdrag A — OpenPLC som tredje motor

Repo: `~/projects/VC_Assist`. Läs `docs/spec/00_index.md` först.

## Vad du ska bevisa, och varför det saknas

Vår ST-tolk (`svc/vc_assist_svc/st/`) dömer modellens kod innan den kompileras.
`M-54` korsprövade den mot **STruC++**, och `M-99` svepte 490 konstruktioner
genom båda — 247 permanenta fall står nu i
`tests/enhet/test_st_svep_mot_strucpp.py`.

**Men OpenPLC är motorn som faktiskt kör i produkten.** Kedjan är
`ST → STruC++ → OpenPLC v4 → OPC UA → Visual Components`. Två av tre led är
korsprövade. Det tredje är oprövat, och det är det som avgör vad som händer i
verkligheten.

`M-99` skrev det som en öppen punkt med de orden: *"OpenPLC som tredje motor är
fortfarande oprövad."*

## Varför det är dyrt att låta bli

En **falsk rödgrind** — vår grind fäller något som fungerar — kostar ett
reparationsvarv och lär modellen fel sak. `M-96` mätte det: nio av sexton
grinddomar i fas 9:s första modelldrivna körning var vår egen bugg, och tre av
fyra uppgifter slog i taket på fyra varv på grund av den.

Ett **hål** — vi släpper igenom något OpenPLC inte klarar — är värre. Då går
koden hela vägen ut i en scen och felar där, långt från sin orsak.

## Vad som redan finns

* `svc/vc_assist_svc/plc/openplc.py` (344 rader) — klienten mot runtime
* `svc/vc_assist_svc/plc/paket.py` — bygger ST till C++ via STruC++
* `tests/protocol/kor_m54_tolk_mot_strucpp.py` — mönstret för en tvåvägsjämförelse, **läs den först**
* `tests/enhet/test_st_svep_mot_strucpp.py` — 247 fall med en facitrad var
* STruC++ finns uppackad i sessionens scratchpad, annars hämtar `install/verktygskedjan.py` den med fastspikad hash
* Tre OpenPLC-avbilder finns lokalt i docker: `ghcr.io/autonomy-logic/openplc-runtime:latest` är den `verktygskedjan.py` pekar på med digest

## Uppgiften

**1. Få OpenPLC att köra ett program och svara.** Ett minimalt ST-program in,
en variabel läst tillbaka över OPC UA. Mät tur och retur i ms. Utan det steget
är resten meningslöst.

**2. Kör de 247 fallen ur svepet genom OpenPLC.** Dela utfallen i samma tre
klasser som `M-99` använde, och de definitionerna är viktiga:

* **STRÄNGARE** — vi fäller, OpenPLC accepterar, och det är rätt. Vårt lager
  finns just för att vara strängare än en kompilator (den godkänner
  `iA := rA`, index utanför fältets gränser). Sådana rader står **med skäl**,
  aldrig som fel.
* **FALSK RÖDGRIND** — vi fäller, OpenPLC kör det, och standarden ger OpenPLC
  rätt. Ett fel hos oss. Laga det.
* **HÅL** — vi släpper igenom, OpenPLC vägrar eller beter sig annorlunda. Ett
  hål i vårt lager.

**3. Där de tre motorerna är oense, säg vem som har rätt.** Två mot en är
inget bevis. Avgör mot IEC 61131-3 och **citera paragrafen**.

**4. Jämför inte bara att det kompilerar — jämför vad det GÖR.** Kör samma
program scan för scan i vår tolk och i OpenPLC med samma insignaler, och
jämför variabelvärdena. `kor_m62_baslinjen_mot_strucpp.py` gör precis det mot
STruC++ och är din mall. Timers är det intressanta: `TON` med `PT := T#4s` ska
lösa ut på samma scan i båda.

## Trasiga fall som måste falla

* En OpenPLC som inte svarar får **aldrig** ge en tyst grön. Slutkod ≠ 0 och
  utskrivet skäl.
* En jämförelse där ena sidan inte kördes får inte rapporteras som "överens".
* Ett program som kompilerar men vars variabler aldrig ändras måste fällas —
  annars mäter körningen att OpenPLC startade, inte att den körde.

## Ofrånkomliga regler

* **Ingen stub som returnerar framgång. Ingen tröskel utan mätreferens. Ingen
  grind utan trasig fixtur.**
* Committa i **små steg**, scopat per fil: `git commit -q --only -m "$MSG" -- <sökväg>`.
  Kör **ALDRIG** `git reset` eller `git stash` utan sökväg — repot är delat med
  upp till tolv skrivare.
* `pytest | tail` ger **tails** returkod, inte pytests. Skriv till fil och läs
  `$?` separat. Det felet gav fyra falska nollor på en natt.
* `tests/motbevis` **SKA vara röda** — de är motbevis. Sviten som ska vara grön
  är `python3 -m pytest tests/enhet`.
* Är arbetsträdet rött: kör `python3 tests/protocol/kor_svit_mot_head.py`. Den
  kör sviten i en ren `git worktree` av HEAD. Grönt där betyder att det röda är
  någon annans pågående arbete, inte din regression.
* Tunga körningar: `nice -n 19 ionice -c3`.

## Filer du äger

`svc/vc_assist_svc/plc/openplc.py`, nya `tests/protocol/kor_openplc_*.py`,
nya `tests/enhet/test_openplc_*.py`. **Rör inte** `svc/vc_assist_svc/st/`
utan att först köra `git log -5 --oneline -- svc/vc_assist_svc/st/` — en annan
session kan ha den. Rör inte `svc/vc_assist_svc/aterhamtning/` alls.

## Leverans

`docs/matningar/M-NN_<namn>.md` — ta ett **ledigt** nummer, kolla
`ls docs/matningar/` precis innan, och **skapa filen med en `## LIMITS`-stubb
direkt**. En tom reservationsfil fäller ärlighetsspärren för alla andra, och
det hände tre gånger en natt. Det finns en spärr mot dubbla M-nummer med
taket 0.

Varje mätning slutar med `## LIMITS` — vad som inte är mätt. En siffras
härkomst hör till siffran.

Rapportera: antal fall körda, fynd per klass, vem som hade rätt när motorerna
var oense, och vad du inte hann.
