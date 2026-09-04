# M-14 — gränssnitt går att skapa, men inte att koppla ihop

**Datum:** 2026-09-04 · VC Premium 4.10 · Wine 11.16 · headless
**Status:** delvis löst. `connect` är **oprövat** mot VC.

## Bakgrund

Fyra av kompositionsdomänens sex verktyg var oprövade i fas 5, eftersom en tom
komponent inte har några gränssnitt och den lokala katalogen är **tom** — noll
komponenter, mätt i båda wine-prefixen.

Gränssnitt är beteenden, och beteenden som inte är skript dödar inte bryggan
(M-13). Alltså går de att bygga själv.

## Vad som fungerar

`createBehaviour(VC_ONETOONEINTERFACE, "Flow")` skapar ett `vcSimInterface`.
Därmed kunde tre av de fyra verktygen bevisas mot VC:

| Verktyg | Utfall |
|---|---|
| `list_interfaces` | 1 gränssnitt, med `connected`, `is_abstract` |
| `interface_info` | `angle_tolerance=360.0`, `distance_tolerance=1e9`, sektioner |
| `disconnect` | svarar korrekt på ett gränssnitt utan koppling |

`createSection(name)` och `section.createField(typ, namn)` fungerar också.
Signaturerna kom **ur API-indexet**, inte ur gissningar: mitt första försök
anropade `createSection()` utan argument, och py2-bindningen returnerade `None`
i stället för att klaga.

## Vad som INTE gick: `connect`

`canConnect` returnerar **False** i varje uppställning jag prövat:

| Uppställning | `canConnect` |
|---|---|
| abstrakt, sektion med flödesfält + signalfält | False |
| abstrakt, sektion med bara signalfält | False |
| abstrakt, sektion med bara flödesfält | False |
| fysiskt (`IsAbstract=False`), sektion med flödesfält | False |
| abstrakt, sektion med transportfält | False |
| abstrakt, sektion med hierarkifält | False |
| abstrakt, **inga sektioner alls** | False *(se nedan)* |

## Ett fynd som inte höll — och varför det står här

Sista raden gav först **True**, och `connect` returnerade True med
`IsConnected=True`. Jag höll på att skriva ned det som ett fynd: *"ett
gränssnitt utan sektioner kopplar"*.

Det gjorde det inte. En omkörning på ett **färskt** par gav False, och en
omläsning av samma komponenter gav också False.

Träffen kom ur tillstånd som lämnats kvar av tidigare varv i samma loop —
sex uppställningar hade byggts och rivits i följd i samma scen.

**En enstaka positiv observation i en scen som bär kvarvarande tillstånd är
ingen mätning.** Ett prov som ändrar scenen måste börja från ett känt läge, och
ett positivt utfall måste reproduceras isolerat innan det får kallas ett fynd.

## Vad som troligen krävs, och som är OMÄTT

Dokumentationen säger att fältens **ordning** utvärderas när en koppling
upprättas, och att `Section.Frame` hör till ett *fysiskt* gränssnitt. Rimlig
hypotes: fälten måste vara **komplementära**, inte identiska, och bundna till
verkliga beteenden — en sida ger, den andra tar. Två tomma komponenter har
ingenting att binda till.

Det är en **hypotes**, inte en mätning. Att pröva den kräver komponenter som
faktiskt modellerar ett flöde, alltså en katalog.

## Följd

`connect` är **oprövat** mot VC och får inte redovisas som grönt. Fas 5:s
egentliga grind — *"N mållayouter byggda: noll kollisioner, alla gränssnitt
kopplade"* — är blockerad på samma sak som allt annat: **det finns ingen
komponentkatalog lokalt.**
