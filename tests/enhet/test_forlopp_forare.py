# -*- coding: utf-8 -*-
"""L1: någon DRIVER förloppsytan — hålet som var rött till 2026-09-05.

Det här var `tests/motbevis/test_forloppet_har_ingen_forare_motbevis.py`, rött
med flit. Ytan var byggd (M-64) och oanvänd: **noll** moduler i `svc/` utanför
`forlopp/` konstruerade ett `Forlopp`. En mekanism som finns men inte anropas
är en bön med en implementation, och skillnaden mellan de två gick inte att se
i sviten — den syntes bara om man räknade förarna.

Nu flyttat hit som regressionsprov (M-93). De två som äger en körnings
tidslinje för protokollet MEDAN de kör, och ett förlopp går att läsa från en
annan process.

Provet räknar inte bara ord. Ett grep efter `forlopp` går att uppfylla med en
parameter ingen använder, så varje förare provas också genom att KÖRAS: en
riktig körning ska lämna händelser i förloppet och en läsbar yta efter sig.
"""
import os
import re
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.forlopp import (ARBETAR, FALLET, Forlopp, KLART,  # noqa: E402
                                   granska, rendera)
from vc_assist_svc.plan import graf as G                             # noqa: E402
from vc_assist_svc.plan.korning import KORD, Korare                  # noqa: E402
from vc_assist_svc.plan.steg import Steg                             # noqa: E402

# Moduler som FÅR nämna förloppet utan att räknas som förare: paketet självt.
_EGNA = os.path.join("vc_assist_svc", "forlopp")

# De två ställen som äger en KÖRNINGS TIDSLINJE och därför kan föra
# protokollet under tiden. Ett av dem måste konstruera ett `Forlopp`, annars
# ser användaren ingenting oavsett hur bra ytan är.
#
# Kopplaren och reparationsslingan står MED FLIT inte här. De är lägre lager,
# och att låta dem känna presentationslagret vore att vända beroendet fel väg.
# Deras väg in går genom `forlopp.kallor`, som ligger ovanpå båda.
FORARKANDIDATER = (
    os.path.join("svc", "vc_assist_svc", "harness", "loop.py"),
    os.path.join("svc", "vc_assist_svc", "plan", "korning.py"),
)


class Klocka(object):
    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += float(s)


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
        "är byggd och oanvänd: en körning i produktion rapporterar bara till "
        "oss.")


def test_den_som_ager_korningens_tidslinje_for_protokoll():
    """Smalare och skarpare: turen och planens körare."""
    utan = [p for p in FORARKANDIDATER if not _namner_forloppet(p)]
    assert not utan, (
        "%d av %d körvägar för inget förlopp:\n  %s\n"
        "Båda returnerade sitt protokoll först när allt var över, och det är "
        "precis de fem av sju rapportytor M-64 räknade."
        % (len(utan), len(FORARKANDIDATER), "\n  ".join(utan)))


def test_ett_forlopp_gar_att_lasa_fran_en_annan_process():
    """Panelen i 26_appen.md bor UTANFÖR körningen, på 127.0.0.1:8902.

    Utan en serialisering är "panelen" och "körningen" samma process, och ytan
    når bara den som redan kör koden.
    """
    f = Forlopp("o-1", "x")
    assert hasattr(f, "till_json"), (
        "Forlopp går inte att serialisera, så ingen annan process kan läsa "
        "det.")
    assert hasattr(Forlopp, "fran_json")
    bild = f.till_json()
    assert "skrivet" in bild, (
        "en bild utan skrivtid går inte att åldra, och en bild som inte "
        "åldras är en död körning som ser levande ut")


# ---- förarna körs, inte bara grepas --------------------------------------

class _Resultat(object):
    def __init__(self, resultat):
        self.resultat = resultat
        self.koad = False
        self.qid = None


class _Utforare(object):
    def __init__(self, klocka):
        self.klocka = klocka

    def utfor(self, namn, argument=None):
        self.klocka.tick(0.3)
        return _Resultat({"antal": 0})


def _plan_med(steg):
    from vc_assist_svc.plan.byggplan import Byggplan
    from vc_assist_svc.plan.spec import DetaljeradSpec, Grundbegaran
    from vc_assist_svc.plan.verifiering import Krav, Verifieringskrav
    begaran = Grundbegaran("prov", "en provplan", "test")
    krav = Verifieringskrav("PASS", [Krav("SAFETY", "COLLISION none")])
    spec = DetaljeradSpec("prov", begaran, verifiering=krav)
    return Byggplan("prov", spec, G.Uppgiftsgraf(steg))


def test_planens_korare_lamnar_ett_lasbart_forlopp_efter_sig():
    """Parametern räcker inte: körningen måste faktiskt fylla ytan."""
    k = Klocka()
    f = Forlopp("o-plan", "kör provplanen", klocka=k)
    steg = [Steg.verktygssteg("a", "list_components", {}, "steg a"),
            Steg.verktygssteg("b", "list_components", {}, "steg b",
                              beroenden=("a",))]
    prot = Korare(_Utforare(k)).kor(_plan_med(steg), forlopp=f)
    assert prot.rakning()[KORD] == 2
    assert len(f.handelser) >= 5          # PLAN + start/klart per steg
    assert f.lage == ARBETAR
    text = rendera(f)
    assert granska(f, text).ok
    assert "2 av 2 klara" in text


def test_harnessens_tur_lamnar_ett_lasbart_forlopp_efter_sig():
    from vc_assist_svc.harness import instruktioner as I
    from vc_assist_svc.harness import kanal as Kn
    from vc_assist_svc.harness import loop as L
    from vc_assist_svc.harness import modell as Mo

    k = Klocka()
    f = Forlopp("o-tur", "Vila.", klocka=k)
    modell = Mo.AttrappModell([Mo.sag("Ingenting att gora.")])
    protokoll = L.Harness(modell=modell, kanal=Kn.Attrappkanal(),
                          korpus=I.las_korpus()).kor("Vila.", forlopp=f)
    assert protokoll.klar
    assert f.lage == KLART, "en klar tur lämnade förloppet i %s" % f.lage
    text = rendera(f)
    assert granska(f, text).ok
    assert "Ingenting att gora." in text


def test_en_stoppad_tur_blir_ett_FALL_med_stoppregelns_egna_ord():
    """Ett stopp som inte syns är samma tystnad som en logg ingen läser."""
    from vc_assist_svc.harness import instruktioner as I
    from vc_assist_svc.harness import kanal as Kn
    from vc_assist_svc.harness import loop as L
    from vc_assist_svc.harness import modell as Mo

    k = Klocka()
    f = Forlopp("o-tur", "Gor nagot.", klocka=k)
    modell = Mo.AttrappModell([Mo.Modellsvar(text="", anrop=())])
    protokoll = L.Harness(modell=modell, kanal=Kn.Attrappkanal(),
                          korpus=I.las_korpus()).kor("Gor nagot.", forlopp=f)
    assert not protokoll.klar
    assert f.lage == FALLET
    text = rendera(f)
    assert granska(f, text).ok
    stopp = [h for h in protokoll.handelser if h.sort == "STOPP"][-1]
    assert stopp.text in text, "stoppregelns egna ord nådde inte användaren"
