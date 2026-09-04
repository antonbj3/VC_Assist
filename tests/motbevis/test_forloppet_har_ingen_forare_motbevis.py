# -*- coding: utf-8 -*-
"""Motbevis: förloppsytan är byggd men ingenting DRIVER den.

`tests/enhet/test_forlopp.py` och `test_forlopp_kallor.py` visar att ytan går
att driva. Det är en annan sak än att den drivs. En yta som ingen kod
konstruerar är lika osynlig för användaren som ingen yta alls, och skillnaden
mellan de två går inte att se i sviten — den syns bara om man räknar
förarna.

Det är samma felklass som M-46 mätte på harnessen: 17 av 46 regler
mekaniserade, 29 bara bedda. En mekanism som finns men inte anropas är en bön
med en implementation.

M-64 §9 säger detta i klartext, och provet nedan gör det till ett tal.

Rött är rätt utfall här. Blir något av proven grönt är hålet lagat, och
provet flyttas till `tests/enhet/` som regressionsprov.
"""
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

# Moduler som FÅR nämna förloppet utan att räknas som förare: paketet självt.
_EGNA = os.path.join("vc_assist_svc", "forlopp")

# De två ställen som äger en KÖRNINGS TIDSLINJE och därför kan föra
# protokollet under tiden. Ett av dem måste konstruera ett `Forlopp`, annars
# ser användaren ingenting oavsett hur bra ytan är.
#
# Kopplaren och reparationsslingan står MED FLIT inte här. De är lägre lager,
# och att låta dem känna presentationslagret vore att vända beroendet fel väg.
# Deras väg in går genom `forlopp.kallor`, som ligger ovanpå båda — och den
# vägen är byggd och provad. Hålet är att ingen står högst upp och anropar
# den.
FORARKANDIDATER = (
    os.path.join("svc", "vc_assist_svc", "harness", "loop.py"),
    os.path.join("svc", "vc_assist_svc", "plan", "korning.py"),
)


def _moduler():
    for dp, _dn, fn in os.walk(os.path.join(_ROT, "svc")):
        if "__pycache__" in dp or _EGNA in dp:
            continue
        for f in sorted(fn):
            if f.endswith(".py"):
                yield os.path.relpath(os.path.join(dp, f), _ROT)


def _namner_forloppet(rel):
    with open(os.path.join(_ROT, rel), encoding="utf-8") as fh:
        return bool(re.search(r"\bforlopp\b|\bForlopp\b", fh.read()))


def test_nagon_modul_i_svc_driver_forloppet():
    """Hålet, som ett tal: hur många moduler utanför `forlopp/` känner till
    att ytan finns?"""
    forare = [rel for rel in _moduler() if _namner_forloppet(rel)]
    assert forare, (
        "noll moduler i svc/ utanför forlopp/ konstruerar ett Forlopp. Ytan "
        "är byggd och oanvänd: en körning i produktion rapporterar fortfarande "
        "bara till oss. Laga genom att låta en av %s föra förloppet, och "
        "flytta sedan provet till tests/enhet/."
        % ", ".join(os.path.basename(p) for p in FORARKANDIDATER))


def test_den_som_ager_korningens_tidslinje_for_protokoll():
    """Smalare och skarpare: turen och planens körare."""
    utan = [p for p in FORARKANDIDATER if not _namner_forloppet(p)]
    assert not utan, (
        "%d av %d körvägar för inget förlopp:\n  %s\n"
        "Båda returnerar sitt protokoll först när allt är över, och det är "
        "precis de fem av sju rapportytor M-64 räknade."
        % (len(utan), len(FORARKANDIDATER), "\n  ".join(utan)))


def test_ett_forlopp_gar_att_lasa_fran_en_annan_process():
    """Panelen i 26_appen.md bor UTANFÖR körningen, på 127.0.0.1:8902.

    Ett `Forlopp` lever i minnet hos den som kör varvet och har varken
    serialisering eller processgräns. Så länge det är sant kan panelen inte
    läsa det, och ytan når bara den som redan kör koden.
    """
    from vc_assist_svc.forlopp import Forlopp
    f = Forlopp("o-1", "x")
    assert hasattr(f, "till_json"), (
        "Forlopp går inte att serialisera, så ingen annan process kan läsa "
        "det. Innan den finns är 'panelen' och 'körningen' samma process, "
        "och 26_appen.md §2 beslut faller.")
