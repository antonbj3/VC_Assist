# FAS 20 ACCEPTANS — komponentmodellen

**beskriver:** `docs/spec/49_komponentmodellen.md` (avsnitt 7–10),
`svc/vc_assist_svc/komponentmodell.py`
**kontrakt:** `docs/spec/70_faser.md` fas 20 — *"De fyra minsta uppsättningarna
byggda **ur specen**, i riktig VC: `canConnect` sant mellan rätt par, och
material som verkligen rör sig igenom. Trasigt fall: en komponent som saknar
ett av specens krävda beteenden får **inte** kunna kopplas — och felet ska säga
vilket beteende som fattas"*
**körs av:** `tests/protocol/kor_fas20_modellen.py` (mot VC),
`tests/enhet/test_komponentmodell.py` (utan VC, 199 prov)
**mätning:** `M-101`
**föregångare:** `M-40` (två tysta villkor), `M-41` (produkten flödar),
`M-67` (kopplingen flyttar ingenting)

## Status: STÄNGD — körd grön mot VC 4.10 2026-09-05. Talen i M-101

| Fråga | Utfall |
|---|---:|
| fyra minsta uppsättningar byggda ur specen, HELA enligt `granska()` | **4 av 4** |
| `canConnect` sant där specen säger ja | **7 av 7** |
| produkter genom hela kedjan på 34,8 simulerade sekunder | **13** |
| mellanrum mot `Interval` 3,0 s | **exakt 3,0000 s**, alla tolv |
| rörelse mot `Speed` 400 mm/s, 17 mätta par | **400,0000 – 400,0000 mm/s** |
| räkningen vid sista avläsningen (bana + buffert + sänka) | **2 + 1 + 10 = 13** |
| trasiga fixturer som fälls, med det saknade beteendet namngivet | **4 av 4** |
| hela tvillingar på samma plats som gick att koppla | **4 av 4** |

Tre påståenden refuterades av körningen och står i M-101: `ContentVisible`
(ur `api.xml`), spec 49 §1.1:s **MÄTT** om klassnamnen (fem av sex namn fel),
och läsningen att ett obundet flödesfält bär `Port = -1` (förvalet är `0`).

## Vad fasen mäter, och varför just det

En spec som aldrig byggts är en hypotes med tabeller. `49_komponentmodellen.md`
svarade på A–G i text — vad en ComponentProcessor är, hur ett fält binds, vad
`canConnect` kräver — men **ingenting var byggt ur den**. Fas 20 vänder på
riktningen: kravlistorna ligger som data i `komponentmodell.py`, VC-koden
**genereras ur dem**, och `tests/enhet/test_komponentmodell.py` faller om
specens tabeller och modellens data glider isär. Ändras kravet ändras bygget.

## De fyra minsta uppsättningarna

Byggda ur avsnitt 7 i specen, inte ur en handskriven mall.

| Klass | Bärande beteende | Gränssnitt | Ramar |
|---|---|---|---|
| TRANSPORTÖR | `Path` (`VC_ONEWAYPATH`) | `InInterface`, `OutInterface` | `PathIn`, `PathOut` |
| MATARE | `Creator` (`VC_COMPONENTCREATOR`) | `OutInterface` | `Out` |
| SÄNKA | `Sink` (`VC_COMPONENTCONTAINER`) | `InInterface` | `In` |
| BUFFERT | `Path` (`VC_ONEWAYPATH`) + `Accumulate`, `Capacity` | `InInterface`, `OutInterface` | `PathIn`, `PathOut` |

Varje gränssnitt bär en sektion med ett `VC_FLOWFIELD` vars `Container` binds
till det bärande beteendet och vars `Port` binds till kontaktens `Index` —
**i den ordningen** (MÄTT M-40; omvänd ordning nollställer `Port` till `-1` och
kopplingen faller tyst).

## Kedjan: alla fyra klasserna i ett flöde

```
F20_Matare  ->  F20_Bana  ->  F20_Buffert  ->  F20_Sanka
 matare          transportör    buffert         sänka
 400 mm          2000 mm        1000 mm         400 mm
 Interval 3 s    Speed 400 mm/s Speed 400 mm/s  Capacity 1e6
```

Komponenterna placeras så att **ramarna sammanfaller**: matarens `Out` ligger
exakt där banans `PathIn` ligger, och så vidare. `canConnect` bryr sig inte om
avståndet vid förvald tolerans (MÄTT M-67), men om produkten faktiskt går över
en koppling vars ramar ligger isär är **inte mätt** — därför byggs kedjan som
en riktig linje.

## Det trasiga fallet, parvis

Fasens poäng. För varje klass byggs tre komponenter:

| | vad | var |
|---|---|---|
| **motpart** | en hel komponent av rätt motsatt klass | uppströms eller nedströms |
| **trasig** | klassen med **ett** krävt beteende utelämnat | ett läge |
| **hel tvilling** | samma klass, ingenting utelämnat | **samma läge** |

Samma motpart provas först mot den trasiga (ska ge `canConnect False`) och
sedan mot den hela tvillingen (ska ge `True`). Eftersom tvillingarna står på
**samma plats i världen** är skillnaden mellan de två utfallen exakt det
utelämnade beteendet — inte geometrin, inte motparten, inte ordningen.

| Klass | Utelämnat | Motpart |
|---|---|---|
| TRANSPORTÖR | `Path` (`VC_ONEWAYPATH`) | en matare uppströms |
| MATARE | `Creator` (`VC_COMPONENTCREATOR`) | en transportör nedströms |
| SÄNKA | `Sink` (`VC_COMPONENTCONTAINER`) | en transportör uppströms |
| BUFFERT | `Path` (`VC_ONEWAYPATH`) | en transportör uppströms |

Grinden har **två halvor**, och båda måste hålla:

1. **VC säger nej.** `canConnect` mot den trasiga är `False`, mot den hela
   tvillingen `True`. Går den trasiga att koppla är kravet inget krav, och
   kravlistan ljuger.
2. **Vi säger varför.** `komponentmodell.granska()` namnger det utelämnade
   beteendet och dess konstant. VC självt säger ingenting alls — `canConnect`
   returnerar ett `False` utan exception, utan logg och utan spår. Ett fel som
   bara säger "gick inte" är ingen grind.

## De tre tysta villkoren

Alla mätta i M-40/M-41, alla utan felmeddelande när de bryts. Uppställningen
håller alla tre, och `kor_fas20_modellen.py` bär dem i koden:

1. **Beteendena måste finnas när simuleringen startar.** Allt byggs i ett
   startskript som `bridge_cmd` kör **före** `startSimulation()`; därför måste
   VC startas om. En matare byggd i en redan körande simulering fyrar aldrig.
2. **Ramarna måste byggas om.** `feature.rebuild()` efter `PositionMatrix`,
   annars ligger ramens verkliga läge kvar i nodens ursprung och `PathLength`
   blir `0.0`.
3. **Banbeteendet måste uppdateras efter att `Path` satts.**
   `komponent.update()` och `sim.update()` räcker inte — det är
   `vcBehaviour.update()` på banan självt.

## Vad körningen dömer

| # | Fråga | Grön när |
|---|---|---|
| 1 | byggdes de fyra uppsättningarna? | `granska()` säger HEL för alla fyra |
| 2 | kopplar rätt par? | `canConnect` sant för de tre i kedjan |
| 3 | faller de trasiga? | `canConnect` falskt för alla fyra, sant för alla fyra hela tvillingar, och granskningen namnger rätt beteende |
| 4 | **rör sig material?** | produkter skapas i takt med `Interval`, rör sig i `Speed` mm/s längs banan, och når **både** bufferten och sänkan |

Fråga 4 är den som skiljer en koppling från en fungerande kedja. En körning som
bara mätte 1–3 hade varit grön för en linje som står still.

## Ordningsregler för körningen

* **Operatörens prefix rörs aldrig.** Allt i `~/.wine-vc-test`.
* **DISPLAY ärvs aldrig** — `:99` står som konstant i körningen, och
  `_verifiera_prefix()` läser tillbaka både `DISPLAY` och `WINEPREFIX` ur
  `/proc/<pid>/environ` efter starten och avbryter om något avviker. En ärvd
  `DISPLAY` landade en gång på operatörens `:1` mitt i hans arbete.
* **VC är delad.** Körningen tar en kopia av det startskript som låg där, och
  lägger tillbaka det när mätningen är klar. Annars bygger nästa omstart —
  någon annans — våra mätkomponenter i deras scen.
