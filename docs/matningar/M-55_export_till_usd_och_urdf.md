# M-55 — VC kan inte exportera till USD eller URDF, men bär halva datan

**Datum:** 2026-09-04 · API-indexet ur `vc_python_api.json`, VC Premium 4.10
**Fråga:** går det att komma från Visual Components till USD/Isaac Sim, och hur
ser VC:s egna robottillgångar ut jämfört med URDF?

## Det som inte finns

Sökning i indexets **3444 symboler**:

| Format | Träffar |
|---|---|
| USD | **0** |
| URDF | **0** |
| glTF / GLB | **0** |
| OBJ | **0** |
| COLLADA / DAE | **0** |
| STL | **0** |
| IGES | **0** |
| JT | **0** |
| 3DXML | **0** |

`app.save` finns och skriver VC:s eget format. `VC_EXPORT_*`-konstanterna
handlar om vilken **omfattning** en egenskap exporteras med, inte om filformat.

Detta är samma vägg som `M-38` fann för OPC UA: VC:s importörer och exportörer
bor i .NET, och VC:s Python når inte .NET (`M-07`). Att GUI:t kan spara ett
format säger alltså ingenting om vad vi kan göra från kod.

## Det som finns

All data en exportör behöver är läsbar från Python:

| Vad | Var |
|---|---|
| ledträdet | `vcNode.Children`, `.Dof`, `.JointType`, `.JointExpression` |
| ledens gränser | `vcJoint.MinValue`, `.MaxValue`, `.MaxSpeed`, `.MaxAcceleration`, `.LagTime`, `.SettleTime` |
| ledtyp och axel | `VC_DOF_ROTATIONAL`, `_TRANSLATIONAL`, `_FIXED`; `VC_JOINTAXIS_PLUS_X` … |
| kinematikklass | `VC_ARTICULATEDKINEMATICS`, `VC_DELTAKINEMATICS`, `VC_CARTESIANKINEMATICS`, `VC_GENERICKINEMATICS` |
| geometrin | `vcTriangleSet`: `PointCount`, `PolygonCount`, `PolygonTable` |
| lägen | `PositionMatrix`, `NodePositionMatrix`, `WorldPositionMatrix` |

Det är i sak innehållet i en URDF. Vägen finns alltså — men den måste **byggas
av oss**, inte hittas.

## Det som avgör hur långt en export räcker

| Sökord | Träffar |
|---|---|
| `mass` | **0** |
| `inertia` | **0** |
| `friction` | **0** |
| `density` | **0** (enda träffen är `vcMaterial.LineStippling`, ett falskt napp) |
| `rigidbody` | **0** |
| `gravity` | **0** |
| `physics` | 22, men **bara kollisionsformen**: `VC_PHYSICSCOLLIDER_BOX`, `_BOXES`, `_PRECISE`, `_NONE`, `_UNSPECIFIED`, och `vcFeature.PhysicsCollider` |

VC vet vilken **form** en kollisionskropp har. Den vet inte vad den **väger**.

> **FÖRDJUPAD av M-59, och slutsatsen håller åt båda hållen.** Den här mätningen
> gäller Python-**API:t**. Filformatet bär faktiskt fälten `Mass`,
> `CenterOfGravity` och `Inertia` — men de sitter på **verktygsramar**, inte på
> komponenten, och de är i praktiken tomma: 392 av 3201 har ett värde skilt från
> noll, och **351 av de 392 har värdet −1000**, en sentinel för "ingen last
> satt". Den som läser raden rakt av får en robot med minus ett kilos
> verktygslast. Efter rensning: **46 av 2202 robotar**.
>
> Det finns alltså ingen massa att hämta, varken genom API:t eller ur filen.

Följden är exakt avgränsad: en export från VC skulle bli geometriskt och
kinematiskt trogen men **inte dynamikfärdig**. URDF kräver `<inertial>` med
massa och tröghetstensor; Isaac behöver massa och friktion för att simulera
kontakt. De talen finns inte i källan.

De skulle gå att **gissa** ur densitet × volym. Det får i så fall aldrig
presenteras som ett mätvärde. En härledd massa är en modellparameter, och den
ska bära sin härledning hela vägen fram — annars är det precis den tysta
uppgraderingen från gissning till fakta som resten av det här projektet är
byggt för att hindra.

## Vad detta säger om VC:s tillgångar

VC:s komponenter är inte URDF och liknar det inte. De bär **beteenden,
signaler och gränssnitt** — processlogiken — där en URDF bär massa och tröghet.
Rikare på ett sätt, fattigare på ett annat, och skillnaden är inte ett
formatbekymmer utan en skillnad i vad de två verktygen är byggda för. VC
simulerar flöde och logik. Isaac simulerar fysik.

## Vad som INTE är mätt

* **Om GUI:t kan exportera** något av formaten via en insticksmodul. Sannolikt,
  men irrelevant för vad vi kan göra från kod — och det ska inte antas åt något
  håll utan att prövas.
* **Hur väl en egen exportör faktiskt skulle fungera.** Ovanstående säger att
  datan finns, inte att en exportör är byggd eller provad.
* **Vad `PolygonTable` innehåller i praktiken.** Symbolen finns; formen på
  datan är inte avläst.
* **Om VC 5.0 ändrar något.** Hela mätningen gäller 4.10.
