# -*- coding: utf-8 -*-
"""C0: motorns tre rattelser, med trasig fixtur skriven FORE mekanismen.

M-122 matte att 64 av 91 overlevare var initierare i VAR-block - rader som
skrivs over innan nagon laser dem - och att `FLANK_TILL_NIVA` gjorde nagot
annat an sitt namn (den stryker anropet; Q blir aldrig sant), medan den
riktiga F15-operatorn (Q mot CLK-signalen, M-115/M-122 §3) saknades helt.

Proven har skrevs fore rattelserna och var roda da. Den roda korningen ligger
i M-131. Faller rattelsen tillbaka - initierare raknas som skador igen, namnet
aterstalls, eller niva-operatorn forsvinner - blir proven roda igen.
"""
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc.mutation import skador                    # noqa: E402


# Rad 1 PROGRAM, 2 VAR, 3-6 deklarationer, 7 END_VAR, 8-9 anrop,
# 10-12 IF trigPall.Q, 13-15 IF tonStall.Q, 16 END_PROGRAM.
KROPP = """PROGRAM Plock
VAR
    xKlar : BOOL := FALSE;
    xVilande : BOOL := TRUE;
    trigPall : R_TRIG;
    tonStall : TON;
END_VAR
    trigPall(CLK := xPallGivare);
    tonStall(IN := xStall, PT := T#500ms);
    IF trigPall.Q THEN
        xKlar := TRUE;
    END_IF;
    IF tonStall.Q THEN
        xKlar := FALSE;
    END_IF;
END_PROGRAM"""


def test_c0_initierare_i_var_undantas_fran_booleska_literaler():
    """C0.1: en rad i VAR som satter ett startvarde ar inte en skada.

    MATT (M-122 §2): 64 av 91 overlevare var initierare; 51 av 57
    FALSKT_TILL_SANT stod pa en saadan rad. Rad 3 och 4 ar initierare,
    rad 11 och 14 ar kod.
    """
    s = skador(KROPP, per_sort=3)
    boolska = [x for x in s
               if x.sort in ("FALSKT_TILL_SANT", "SANT_TILL_FALSKT")]
    traff_i_var = [(x.sort, x.rad) for x in boolska if x.rad in (3, 4)]
    assert not traff_i_var, "initierare i VAR raknades som skador: %s" % (
        traff_i_var,)
    assert [x.rad for x in boolska
            if x.sort == "FALSKT_TILL_SANT"] == [14]
    assert [x.rad for x in boolska
            if x.sort == "SANT_TILL_FALSKT"] == [11]


def test_c0_flank_struken_heter_vad_den_gor():
    """C0.2: sorten som stryker flankdetektorns anrop heter FLANK_STRUKEN.

    Det gamla namnet (FLANK_TILL_NIVA) stal platsen for den riktiga
    niva-operatorn (M-122 §3).
    """
    s = [x for x in skador(KROPP) if x.sort == "FLANK_STRUKEN"]
    assert [x for x in skador(KROPP)
            if x.sort == "FLANK_TILL_NIVA" and "flank struken" in x.kropp] == []
    assert len(s) == 1
    assert s[0].fore == "trigPall(CLK := xPallGivare);"
    assert "trigPall(CLK := xPallGivare);" not in s[0].kropp
    assert "(* flank struken *)" in s[0].kropp


def test_c0_flank_till_niva_ar_den_riktiga_f15():
    """C0.3: den riktiga operatorn (M-122 §3, M-115): `inst.Q` byts mot
    instansens CLK-signal - villkoret las pa niva i stallet for pa flank.

    tonStall har ingen CLK i kartan, sa dess .Q ska inte nivas.
    """
    s = [x for x in skador(KROPP) if x.sort == "FLANK_TILL_NIVA"
         and ".Q" in x.fore]
    assert len(s) == 1
    assert (s[0].fore, s[0].efter) == ("trigPall.Q", "xPallGivare")
    assert s[0].vantat_lager == "beteende"
    # Anropet star kvar: det ar lasningen som blir fel, inte deklarationen.
    assert "trigPall(CLK := xPallGivare);" in s[0].kropp
    assert "IF xPallGivare THEN" in s[0].kropp
    assert "tonStall.Q" in s[0].kropp
