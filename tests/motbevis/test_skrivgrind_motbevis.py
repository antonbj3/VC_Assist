# -*- coding: utf-8 -*-
"""Motbevis: skrivgrinden dömer NAMNETS FORM, inte operationen.

Två hål, båda fail-open, båda i den grind som är bryggans andra försvarslinje.

1. `granska()` släpper igenom varje mutation som skrivs som ett dunder-anrop.
   `c.Name = "x"` fastnar (och har ett eget prov), men `c.__setattr__("Name",
   "x")` — exakt samma operation — döms som LÄSANDE och körs direkt i `exec`,
   utan kö och utan godkännande. Orsaken är `_ar_muterande_namn`: den strippar
   inledande understreck men inte avslutande, så resten efter "set" blir
   "attr__" och ordgränsprovet säger nej.

2. `skapar_skriptbeteende()` känner bara igen `createBehaviour` när typargumentet
   står som ett bart namn i anropet. Varje annan form — en variabel, ett
   attribut, uppackning — ger tom lista, och `pump._op_exec_queue` köar då koden
   utan invändning. M-13: det är den ENDA operation som stoppar simuleringen och
   dödar bryggan mitt i sitt eget svar.

I3 i 90_invarianter.md är fail-closed. Båda dessa är fail-open.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
import skrivgrind as S  # noqa: E402


# ---- 1. dunder-mutationer döms som läsande ------------------------------

DUNDERSKRIVNINGAR = [
    ("import shutil; shutil.rmtree('/tmp/x')", "raderar ett helt träd"),
    ("import os; os.truncate('/tmp/x', 0)", "tömmer en fil"),
]


@pytest.mark.parametrize("kod,skal", DUNDERSKRIVNINGAR,
                         ids=[k for k, _ in DUNDERSKRIVNINGAR])
def test_en_skrivning_skriven_som_dunderanrop_maste_ocksa_fastna(kod, skal):
    dom = S.granska(kod)
    assert dom.skriver is True, (
        "%r dömdes som LÄSANDE och skulle köras direkt i exec, utan kö (%s)"
        % (kod, skal))


# ---- 2. skriptbeteendegrinden är fail-open ------------------------------

SKRIPTBETEENDEN = [
    ("c.createBehaviour(vcConst.VC_SCRIPT, 'x')", "typen via ett attribut"),
    ("c.createBehaviour(*[VC_SCRIPT, 'x'])", "uppackade argument"),
    ("c.createBehaviour(**{'type': VC_SCRIPT, 'name': 'x'})", "nyckelordsargument"),
    ("setattr(b, 'Script', kod)", "tilldelning till .Script via setattr"),
]


@pytest.mark.parametrize("kod,skal", SKRIPTBETEENDEN,
                         ids=[s for _, s in SKRIPTBETEENDEN])
def test_skriptbeteende_maste_upptackas_oavsett_hur_typen_skrivs(kod, skal):
    skal_lista = S.skapar_skriptbeteende(kod)
    assert skal_lista, (
        "%r (%s) gav tom lista: pump._op_exec_queue köar den utan invändning, "
        "och vid godkännande dör bryggan utan väg tillbaka (M-13)" % (kod, skal))


def test_grinden_ar_fail_closed_nar_typargumentet_inte_gar_att_avgora():
    """I3: okänt är inte ett godkännande.

    Ett `createBehaviour` vars typ inte går att läsa syntaktiskt ska räknas
    som ett skriptbeteende, precis som `granska()` räknar ogenomskinliga
    anrop som skrivande. I dag räknas det som ofarligt.
    """
    assert S.skapar_skriptbeteende("c.createBehaviour(typen, namnet)"), (
        "typargumentet gick inte att avgöra och grinden svarade 'ofarligt'")
