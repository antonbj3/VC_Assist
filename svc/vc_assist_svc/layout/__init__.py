# -*- coding: utf-8 -*-
"""Layoutmotorn: den som BESTÄMMER var något ska stå.

Verktygslagret i ``vc_assist_svc.verktyg`` kan SÄTTA ett läge. Det som saknades
var något som bestämmer vilket läge. Det är den här motorn.

Ren Python 3, bara standardbiblioteket, och den går att prova utan att Visual
Components startas. Den anropar aldrig VC; den lämnar ifrån sig en sekvens
``set_transform``-anrop som någon annan kör.

    matt.py         enheterna. En längd utan enhet går inte att bygga.
    rum.py          hall, zoner, pelare, objekt, lägen
    kollision.py    förhandskontroll, efterhandsgranskning, passagebredder
    fria_ytor.py    vad som är ledigt, och var något får plats
    relationer.py   placeringsspråket: bredvid, framför, mot väggen, på ...
    losare.py       sökningen, konfliktkärnan och de fyra svaren
    komponent.py    bryggan från en RIKTIG komponentfil till ett Objekt
    vc_utdata.py    layouten som anrop mot det befintliga verktygsregistret
    provscener.py   24 scener ur bänken, med verkliga mått, och mätningen

Så här hänger det ihop:

    hall  ->  Scen  ->  objekt läggs till  ->  relationer skrivs
                            |
                            v
                     losa(scen, relationer)
                            |
              +-------------+--------------+
              |                            |
          LOST: placeringar          inte LOST: ett SKÄL
              |                      (vilka relationer som band,
              v                       eller att det inte ryms,
      till_verktygsanrop(scen)        eller att svaret är okänt)

Tre regler bär hela motorn:

1. En relation är ett CONSTRAINT, aldrig en färdig koordinat. Modellen anger
   relationer; geometrin räknas här och kontrolleras av kollisionskontrollen.
   Samma regel som docs/spec/90_invarianter.md I8 ställer på plug and play.
2. FAIL-CLOSED. Kan motorn inte garantera att en placering är fri säger den
   nej. Fyra svar, inte två, och tystnad är aldrig ett godkännande (I3).
3. DETERMINISM. Samma indata ger samma utdata, alltid. Varje ordning i
   sökningen är fastlagd och provas mekaniskt.

Prov: tests/enhet/test_layout*.py.
"""
from __future__ import annotations

from .fria_ytor import (RASTER_M, Rasterkarta, far_plats, ledig_area_m2,
                        storsta_lediga_rektangel)
from .komponent import (MAX_RAMRADER, Bindning, Bounds, Flode, Koppling, Matt,
                        Saknasfel, flode_ur_fakta, komponentnamn_karta,
                        kopplingsbara, objekt_ur_komponent, rackvidd_ur_fakta,
                        saknade_matt)
from .kollision import (Granskning, Hojdbrott, Overlapp, Passagebrott,
                        Provsvar, Utanfor, Zonbrott, avstand_m, fri_bredd_m,
                        granska, kravd_separation_m, provplacera, radie_langs,
                        separation, tillganglig_hojd_m)
from .losare import NODBUDGET, Losning, Status, Steg, losa
from .matt import Enhetsfel, Langd, Vek2, Vek3, area_m2, krav, krav_vinkel
from .relationer import (BREDVID_MAX_M, Bakom, Bredvid, CentreradI, FORSLAGSRASTER_M,
                         FastLage, Framfor, IHorn, IRad, IZon, InomRackvidd,
                         MAX_FORSLAG, Mellanrum, MinstaAvstand, MotVagg, Pa,
                         Relation, Riktning, Sida, TillHoger, TillVanster,
                         Under, UtanforZon, Utfall)
from .rum import (Ankare, Hall, Horn, Kropp, Layoutfel, Objekt, Pelare, Pose,
                  Rektangel, Scen, Vagg, Zon, Zontyp)
from .vc_utdata import (Ankarfel, Anrop, till_verktygsanrop,
                        validera_mot_registret)

__all__ = [
    # matt
    "Enhetsfel", "Langd", "Vek2", "Vek3", "area_m2", "krav", "krav_vinkel",
    # rum
    "Ankare", "Hall", "Horn", "Kropp", "Layoutfel", "Objekt", "Pelare",
    "Pose", "Rektangel", "Scen", "Vagg", "Zon", "Zontyp",
    # kollision
    "Granskning", "Hojdbrott", "Overlapp", "Passagebrott", "Provsvar",
    "Utanfor", "Zonbrott", "avstand_m", "fri_bredd_m", "granska",
    "kravd_separation_m", "provplacera", "radie_langs", "separation",
    "tillganglig_hojd_m",
    # fria ytor
    "RASTER_M", "Rasterkarta", "far_plats", "ledig_area_m2",
    "storsta_lediga_rektangel",
    # relationer
    "BREDVID_MAX_M", "Bakom", "Bredvid", "CentreradI", "FORSLAGSRASTER_M",
    "FastLage", "Framfor", "IHorn", "IRad", "IZon", "InomRackvidd",
    "MAX_FORSLAG", "Mellanrum", "MinstaAvstand", "MotVagg", "Pa", "Relation",
    "Riktning", "Sida", "TillHoger", "TillVanster", "Under", "UtanforZon",
    "Utfall",
    # losare
    "NODBUDGET", "Losning", "Status", "Steg", "losa",
    # riktiga komponenter
    "MAX_RAMRADER", "Bindning", "Bounds", "Flode", "Koppling", "Matt",
    "Saknasfel", "flode_ur_fakta", "komponentnamn_karta", "kopplingsbara",
    "objekt_ur_komponent", "rackvidd_ur_fakta", "saknade_matt",
    # utdata mot VC
    "Ankarfel", "Anrop", "till_verktygsanrop", "validera_mot_registret",
]
