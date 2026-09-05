# -*- coding: utf-8 -*-
"""L1 for det arbetade exemplet i fas 9:s prompt.

Ett exempel ar den starkaste hjalpen mot formfel - modellen ser hur en godkand
kropp SER UT i stallet for att harleda formen ur en regellista.

Och det ar precis darfor det ar farligt: visas uppgiftens EGEN referens mater
korningen hur bra modellen kopierar facit, inte om den kan skriva ST. Proven
haller fast gransen.
"""
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol"))

import kor_fas9_slingan as K                                        # noqa: E402
from bank import reparationsbank as RB                              # noqa: E402


def _poster():
    return RB.uppgifter_med_sparfacit()


def test_exemplet_ar_aldrig_uppgiftens_eget_facit():
    """TRASIG FIXTUR for lackaget.

    Skulle valjaren nagonsin returnera uppgiftens egen referens vore hela
    matningen vardelos - och felet skulle synas som ett PLOTSLIGT bra tal, den
    sortens fynd som ar latt att tro pa.
    """
    poster = _poster()
    assert len(poster) >= 2, "med en enda uppgift gar granskningen inte att gora"
    for post in poster:
        tid, kropp = K.exempel_fran_annan_uppgift(post, poster)
        assert tid is not None
        assert tid != post["task_id"]
        egen = RB.bygg_uppsattning(post)["referens"]
        assert kropp != egen


def test_en_ensam_uppgift_ger_INGET_exempel_i_stallet_for_sitt_eget():
    """Fail-closed. Finns ingen granne ska valjaren svara None, inte falla
    tillbaka pa uppgiftens egen referens - det vore den tysta formen av
    lackaget."""
    post = _poster()[0]
    tid, kropp = K.exempel_fran_annan_uppgift(post, [post])
    assert tid is None and kropp is None


def test_exemplet_ar_en_kropp_och_inte_ett_helt_program():
    """Skelettet ager PROGRAM-raden och VAR-blocken. Ett exempel som bar dem
    hade lart modellen att skriva just det den aldrig far skriva."""
    poster = _poster()
    _tid, kropp = K.exempel_fran_annan_uppgift(poster[0], poster)
    for forbjudet in ("PROGRAM ", "END_PROGRAM", "VAR_INPUT", "END_VAR"):
        assert forbjudet not in kropp, "exemplet bar %r" % forbjudet
