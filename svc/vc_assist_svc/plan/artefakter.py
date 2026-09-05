# -*- coding: utf-8 -*-
"""De fyra artefakterna pa disk, och hashen som binder sekvensen.

22_planeringslagret.md, ordagrant:

    "Alla fyra ar JSON pa disk under bank/plans/<plan_id>/. Ingen artefakt far
     existera enbart som text i en modellprompt."

Skalet star i samma dokument, och det ar hela poangen med lagret: en plan som
bara finns i en prompt gar inte att granska, versionera eller mata mot.

    spec.json           ordersedeln, med varje krav och dess harkomst
    layout.json         var varje station star, med harkomst PER TAL (K9)
    plan.json           uppgiftsgrafen: steg, beroenden, villkor, efterkontroller
    anropssekvens.json  den topologiskt ordnade listan av verktygsanrop

HASHEN AR INTE EN ARTIGHET (K22)

Sekvensen bar `hash`, en sha256 over sin egen kanoniska JSON. Samma spec ska ge
samma sekvens byte for byte, och utan ett tal att jamfora med gar det inte att
prova. `las_sekvens` raknar om hashen och VAGRAR lamna ut en sekvens som inte
stammer - en artefakt som andrats efter att den skrevs ar inte den artefakt
planen godkandes som.

TVA TAL SOM SER LIKA UT MEN INTE AR DET

`bindningar` i sekvensen star kvar som `$bindning`-objekt, inte som varden.
Det ar avsiktligt: bindningen loses forst under korningen, ur scenens EGET
svar, och en sekvens som bar ett gissat gransnittsnamn hade sett korbar ut och
varit ett pahitt (I9).

Endast standardbiblioteket.
"""
from __future__ import annotations

import hashlib
import json
import os

from .fel import Planfel
from .kallor import ROT

# Dar artefakterna bor. Sokvagen star i specen och ar inte ett val vi gjort.
ARTEFAKTROT = os.path.join(ROT, "bank", "plans")

FILNAMN = {"spec": "spec.json", "layout": "layout.json", "plan": "plan.json",
           "sekvens": "anropssekvens.json"}

# Grinden som godkande ett tal ur layoutmotorn. K9: varje tal i LAYOUT bar
# {value, method, gate}, och ett tal utan grind ar ett lintfel. Grinden ar
# losarens EGEN oberoende efterhandsgranskning - den som gor skillnad pa "min
# sokning hittade ett lage" och "en annan kod sa att laget haller".
LAYOUTGRIND = "layout.kollision.granska"

SEKVENSVERSION = 1   # formatversion, ingen troskel: artefakternas form star i 22_planeringslagret.md


def _kanonisk(data):
    """JSON i EN form: sorterade nycklar, inga blanksteg, utf-8.

    Determinism byte for byte kraver att serialiseringen ar densamma varje
    gang. Utan det matter hashen hur json.dumps rakade formatera, inte vad
    sekvensen innehaller.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def hash_av(data):
    return hashlib.sha256(_kanonisk(data).encode("utf-8")).hexdigest()


def anropssekvens(plan, register=None):
    """Den topologiskt ordnade listan av verktygsanrop, med sin hash.

    K20: sekvensen harleds MEKANISKT. Modellen deltar inte. Ordningen ar
    grafens kanoniska ordning, och lage (read/write) skrivs UT ur
    verktygsregistret - planen bar det inte och far inte gora det (I12).
    """
    if register is None:
        from ..verktyg import REGISTER
        register = REGISTER
    anrop = []
    for steg_id in plan.ordning():
        steg = plan.graf.steg(steg_id)
        if steg.sort != "verktyg":
            anrop.append({"id": steg.id, "sort": "kontroll",
                          "kontroll": steg.kontroll.sort,
                          "beroenden": list(steg.beroenden)})
            continue
        verktyg = register.get(steg.verktyg)
        post = {"id": steg.id, "sort": "verktyg", "verktyg": steg.verktyg,
                "argument": _argument(steg.argument),
                "beroenden": list(steg.beroenden),
                # Lage ur REGISTRET, aldrig ur planen. Sekvenseraren satter
                # det; ett steg som forsoker satta det sjalvt ar ett fel.
                "lage": verktyg.effect if verktyg is not None else "OKANT",
                "efterkontroller": [e.till_json()
                                    for e in steg.efterkontroller]}
        anrop.append(post)
    kropp = {"v": SEKVENSVERSION, "plan_id": plan.id, "anrop": anrop}
    kropp["hash"] = hash_av(kropp)
    return kropp


def _argument(argument):
    ut = {}
    for namn, varde in argument.items():
        ut[namn] = varde.till_json() if hasattr(varde, "till_json") else varde
    return ut


def layoutartefakt(plan, layoutsvar):
    """LAYOUT-artefakten: varje tal med sin metod och sin grind (K9).

    Saknas layoutmotorn skrivs artefakten anda, med en tom stationslista och
    skalet utskrivet. En artefakt som inte finns lases som "ingen layout
    behovdes"; en tom artefakt med skal lases som det den ar.
    """
    stationer = []
    if layoutsvar is not None:
        for p in layoutsvar.placeringar:
            stationer.append({
                "roll": p.roll,
                "instans": p.instans,
                "anchor": {"value": list(p.position_mm),
                           "method": p.motiv, "gate": LAYOUTGRIND},
                "yaw_deg": {"value": p.wpr_deg[2], "method": p.motiv,
                            "gate": LAYOUTGRIND},
                # K12: arbetsutrymmet ar OKANT tills ett datablad mater det.
                # Det skrivs UT som okant och far aldrig tyst bli noll.
                "work_area": "UNKNOWN"})
    return {
        "v": SEKVENSVERSION,
        "layout_id": plan.id,
        "frame": "world",
        "unit": "mm",
        "status": layoutsvar.status if layoutsvar is not None else "EJ_KORD",
        "stations": stationer,
        "konflikt": (list(layoutsvar.konflikt) if layoutsvar is not None
                     else []),
        "skal": ("" if layoutsvar is not None else
                 "ingen layoutmotor var kopplad till planeringen, sa inga "
                 "koordinater raknades; VC:s plug and play placerar "
                 "komponenterna utifran kopplingarna (I8)"),
    }


def skriv_artefakter(besked, rot=None):
    """Skriv de fyra artefakterna. Returnerar {namn: sokvag}.

    Kastar om beskedet inte bar en plan: en artefaktkatalog med tre av fyra
    filer ser ut som en plan och ar det inte.
    """
    if besked.plan is None:
        raise Planfel("there is no plan to write; the outcome is %s. A "
                      "half artifact catalog looks runnable and is not"
                      % besked.status)
    rot = rot or ARTEFAKTROT
    katalog = os.path.join(rot, besked.plan.id)
    os.makedirs(katalog, exist_ok=True)
    innehall = {
        "spec": besked.spec.till_json(),
        "layout": layoutartefakt(besked.plan, besked.layoutsvar),
        "plan": besked.plan.till_json(),
        "sekvens": anropssekvens(besked.plan),
    }
    ut = {}
    for namn, data in sorted(innehall.items()):
        sokvag = os.path.join(katalog, FILNAMN[namn])
        with open(sokvag, "w", encoding="utf-8") as f:
            f.write(_kanonisk(data))
        ut[namn] = sokvag
    return ut


def las_sekvens(sokvag):
    """Sekvensen, med hashen omraknad. Kastar om den inte stammer.

    En artefakt som andrats efter att den skrevs ar inte den artefakt planen
    godkandes som, och att lasa den som om den vore det ar precis den tysta
    nedgraderingen lagret finns for att undvika.
    """
    with open(sokvag, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "hash" not in data:
        raise Planfel("%s has no hash and cannot be trusted" % sokvag)
    pastadd = data["hash"]
    kropp = dict(data)
    del kropp["hash"]
    verklig = hash_av(kropp)
    if verklig != pastadd:
        raise Planfel(
            "the sequence in %s carries the hash %s but the content gives %s. "
            "The artifact has been changed since it was written" % (sokvag, pastadd[:12],
                                                  verklig[:12]))
    return data


# Kortnamnet finns kvar for anropare inne i paketet; det langre namnet ar det
# som exporteras, sa att `from plan import skriv` inte later som vad som helst.
skriv = skriv_artefakter
