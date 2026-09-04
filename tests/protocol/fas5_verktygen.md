# FAS 5 ACCEPTANS — verktygen mot en körande VC

**beskriver:** `svc/vc_assist_svc/verktyg/`
**kontrakt:** `docs/spec/45_verktyg.md`
**körs av:** `tests/protocol/kor_fas5.py`

Verktygsmallarna var skrivna mot VC:s dokumentation men hade **aldrig exekverats
i VC**. Det är precis den sortens oprövade yta där dokumentationen och
verkligheten går isär — se M-11, där kvaternionen visade sig vara skalär-först
tvärtemot vad namnen antyder.

## Utfall 2026-09-04

VC Premium 4.10 under Wine 11.16, headless. Förmågerapporten: **46 av 46 ytor finns.**

**20 anrop lyckades, 0 föll. Alla 21 verktyg prövade.**

| Verktyg | Utfall mot VC |
|---|---|
| `list_components` | 2 komponenter, namn och kategori lästa |
| `find_component` | hittad, `uri: "vcid:"` |
| `component_info` | namn, kategori, 10 egenskaper |
| `list_properties` | 10 egenskaper |
| `get_property` | `Name` = `Fas5Prov`, typ `String` |
| `get_transform` | position och WPR, både lokal och världsram |
| `get_bounds` | center, halv utsträckning, min, max |
| `list_nodes` | 1 nod |
| `find_node` | hittad, världsposition läst |
| `list_interfaces` | 0 (en tom komponent har inga) |
| `list_connections` | 0, både med och utan komponentfilter |
| `set_transform` | satte `[1.0, 2.0, 0.5]` |
| `get_transform` efteråt | **läste tillbaka `[1.0, 2.0, 0.5]`** |
| `set_property` | satt |
| `clone_component` | klonad till `Fas5Prov2` |
| `delete_component` ×2 | båda raderade |
| `save_layout` | kördes; bryggan varnade i förväg om att den går ned |

Att `set_transform` följs av ett `get_transform` som läser tillbaka **samma tal**
är det egentliga provet: skrivningen tog, och läsningen ser den.

## De fem utan förutsättningar

Prövade ändå, och de föll av rätt skäl:

| Verktyg | Varför |
|---|---|
| `can_connect`, `connect`, `disconnect`, `interface_info` | kräver verkliga gränssnitt; en tom komponent har inga |
| `load_component` | ingen katalog är synkad i testprefixet — **noll `.vcmx` på disk** |

Dessa är alltså **oprövade**, inte gröna. De kräver ett riktigt komponentbibliotek.

## Ett fynd under körningen

`app.save()` **stoppar simuleringen och dödar bryggan**, precis som
`createBehaviour(VC_SCRIPT)`. Det upptäcktes genom att köra verktyget, inte genom
att läsa dokumentationen. Se M-13 för hur de två fallen nu behandlas olika.

## Vad som INTE är prövat

* **Ett riktigt komponentbibliotek.** Utan katalog är scenbygget prövat på tomma
  komponenter, inte på transportörer och robotar. Fas 5:s egentliga grind —
  *"N mållayouter byggda: noll kollisioner, alla gränssnitt kopplade"* — kräver
  det och är **inte** stängd.
* **Kollisionsräkning.** `sim.newCollisionDetector()` är aldrig anropad.
* **Windows.**
