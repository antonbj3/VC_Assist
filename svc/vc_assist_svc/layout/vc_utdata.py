# -*- coding: utf-8 -*-
"""Från layout till en sekvens anrop mot de BEFINTLIGA verktygen.

Motorn räknar i meter och beskriver ett objekt genom sitt fotavtrycks mitt vid
underkanten. ``set_transform`` i svc/vc_assist_svc/verktyg/scen.py tar
millimeter och sätter KOMPONENTENS ORIGO, inte lådans mitt. Mellan de två
ligger tre fällor, och alla tre hanteras här i stället för i en kommentar:

1. ENHETEN. Layouten är meter, VC är millimeter. Omräkningen sker på ett
   ställe, genom ``Vek3.som_mm_lista``, och ingenstans annars.
2. ORIGO. Var komponentens origo sitter i förhållande till dess låda vet bara
   VC, genom verktyget ``get_bounds``. Objektets ``ankare`` bär det svaret och
   en stämpel: MATT eller ANTAGEN. Som förval VÄGRAR den här modulen skriva
   ett anrop ur ett antaget ankare - ett antagande som körs mot en riktig scen
   flyttar komponenten fel, tyst. Fail-closed, docs/spec/90_invarianter.md I3.
3. ORIENTERINGEN. ``set_transform`` vill ha wpr i grader, i den ordning
   ``getWPR`` lämnar den: W kring X, P kring Y, R kring Z. Vridningen kring Z
   hör alltså hemma i det TREDJE talet. Ett halvt varv fel här hade blivit en
   tyst vridning kring fel axel.

Modulen anropar aldrig VC. Den bygger anropen, och den kan låta det RIKTIGA
verktygsregistret validera dem, så att formen aldrig kan drifta från schemat.

Källa: uppdragets punkt 6, docs/spec/45_verktyg.md.
"""
from __future__ import annotations

import math

from .matt import MM_PER_M
from .rum import Ankare, Layoutfel, Scen

__all__ = ["Ankarfel", "Anrop", "till_verktygsanrop", "validera_mot_registret"]

VERKTYG = "set_transform"


class Ankarfel(Layoutfel):
    """Ett anrop begärdes ur ett ankare som inte är mätt."""


class Anrop:
    """Ett verktygsanrop, i den form utforaren och schemat vill ha det."""

    __slots__ = ("verktyg", "argument", "objekt")

    def __init__(self, verktyg, argument, objekt):
        self.verktyg = verktyg
        self.argument = argument
        self.objekt = objekt

    def som_dict(self):
        return {"verktyg": self.verktyg, "argument": dict(self.argument)}

    def __eq__(self, annan):
        return (isinstance(annan, Anrop) and self.verktyg == annan.verktyg
                and self.argument == annan.argument)

    def __hash__(self):
        return hash((self.verktyg, tuple(sorted(self.argument))))

    def __repr__(self):
        return "Anrop(%s, %r)" % (self.verktyg, self.argument)


def _origo_mm(objekt, pose):
    """Komponentens origo i världen, i millimeter.

    Lådans fotavtrycksmitt vid underkanten ska hamna i pose. Ankaret säger
    var den punkten ligger i komponentens EGEN ram, alltså vektorn origo ->
    punkt. Origo hamnar därför i pose minus den vektorn, vriden till världen.
    """
    fx, fy, fz = objekt.ankare.forskjutning_lokal_m()
    r = math.radians(pose.vridning_grader)
    c, s = math.cos(r), math.sin(r)
    x = pose.x_m - (c * fx - s * fy)
    y = pose.y_m - (s * fx + c * fy)
    z = pose.z_m - fz
    return [x * MM_PER_M, y * MM_PER_M, z * MM_PER_M]


def till_verktygsanrop(scen, strikt=True, komponentnamn=None):
    """Layouten som en sekvens ``set_transform``-anrop, i placeringsordning.

    ``strikt=True`` kräver att varje objekts ankare är MATT, alltså hämtat ur
    ett verkligt ``get_bounds``-svar. ``strikt=False`` släpper igenom antagna
    ankare och är till för prov utan VC; den skriver aldrig något som körs mot
    en riktig scen utan att den som anropar valt det.

    ``komponentnamn`` mappar layoutnamn till komponentnamn i VC. Saknas ett
    namn i mappen används layoutnamnet. Hallens egna pelare hoppas över: de är
    byggnaden, inte komponenter i layouten.
    """
    if not isinstance(scen, Scen):
        raise Layoutfel("till_verktygsanrop takes a Scen")
    karta = dict(komponentnamn or {})
    ut = []
    antagna = []
    for namn, pose in scen.placeringar().items():
        objekt = scen.objekt(namn)
        if objekt.kategori == "pelare":
            continue
        if objekt.ankare.stampel != Ankare.MATT:
            antagna.append(namn)
            if strikt:
                continue
        argument = {
            "component": karta.get(namn, namn),
            # Millimeter. Enheten byts på exakt ett ställe, här.
            "position": _origo_mm(objekt, pose),
            # W kring X, P kring Y, R kring Z: vridningen hör i tredje talet.
            "wpr": [0.0, 0.0, pose.vridning_grader],
        }
        ut.append(Anrop(VERKTYG, argument, namn))
    if strikt and antagna:
        raise Ankarfel(
            "these objects have an ASSUMED ankare and therefore cannot be "
            "written as a tool call: %s. Read the component's box with "
            "get_bounds and build the ankare with Ankare.ur_bounds, or call "
            "with strikt=False if the calls are only to be read, not run."
            % ", ".join(sorted(antagna)))
    return tuple(ut)


def validera_mot_registret(anrop):
    """Låter det RIKTIGA verktygsregistret pröva anropen.

    Importen ligger i funktionen: layoutmotorn ska gå att prova helt utan
    verktygslagret, och verktygslagret ska inte dras in i varje import av
    layout. Att formen prövas mot registret och inte mot en kopia av schemat
    är hela poängen - en kopia hade kunnat drifta utan att något märkte det.

    Returnerar argumenten kompletterade med schemats förval, ett per anrop.
    Kastar verktygslagrets egna fel om något inte håller.
    """
    from ..verktyg import REGISTER, validera_argument

    ut = []
    for a in anrop:
        if a.verktyg not in REGISTER:
            raise Layoutfel("the tool %r is not in the register" % a.verktyg)
        ut.append(validera_argument(REGISTER[a.verktyg], a.argument))
    return tuple(ut)
