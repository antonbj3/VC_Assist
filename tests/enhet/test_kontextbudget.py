# -*- coding: utf-8 -*-
"""Kontextbudgeten: vad som far plats, vad som gar bort, och bokforingen.

FAS 22. Tre saker provas, och det tredje ar det som gor de tva forsta varda
nagot:

  1. TRIMORDNINGEN ar sluten och numrerad, och trimningen gar uppifran och ned.
  2. DET SKYDDADE ROrs ALDRIG. Racker budgeten inte till det kastas Budgetfel -
     ett fel, aldrig en tyst trimning (S1).
  3. BOKFORINGEN PROVAS AT BADA HALLEN. En trimning utan handelse faller, OCH
     en handelse utan trimning faller. En bokforing som bara provas at ena
     hallet ar oprovad, och det ar precis sa en tyst trimning overlever.

Talen i provet ar matta, inte valda: verktygsschemat vags mot registret som
det faktiskt ser ut, och verktygssvaren ar de riktiga ur repots handlare.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "tests", "protocol", "stod")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fas22_fixturer as FX                                    # noqa: E402
from vc_assist_svc import verktyg as V                         # noqa: E402
from vc_assist_svc.llm import budget as B                      # noqa: E402
from vc_assist_svc.llm import delar as D                       # noqa: E402
from vc_assist_svc.llm import kapning as K                     # noqa: E402
from vc_assist_svc.llm import matt, profil, urval as U         # noqa: E402
from vc_assist_svc.llm.fel import Budgetfel                    # noqa: E402


# ---- tabellen -----------------------------------------------------------

def test_posterna_ar_nio_och_lamnar_svarsmarginal():
    """Summan av taken ar 86 %, och de aterstaende 14 % ar svarets.

    Star summan hogre finns ingen marginal kvar, och ett svar som klipps mitt
    i en mening ar en avhuggen rapport - aldrig ett godkannande.
    """
    assert len(B.POSTER) == 9
    assert [p.nr for p in B.POSTER] == list(range(1, 10))
    assert round(B.summa_andelar(), 3) == 0.86
    assert round(1.0 - B.summa_andelar(), 3) == profil.MINSTA_SVARSMARGINAL


def test_trimstegen_ar_atta_och_slutar_med_att_turen_delas():
    assert [s.nr for s in B.TRIMSTEG] == list(range(1, 9))
    assert B.TRIMSTEG[-1].vad.endswith("delas turen")


def test_de_skyddade_posterna_ar_de_specen_namner():
    skyddade = set(p.id for p in B.POSTER if not p.far_trimmas)
    assert skyddade == {B.P_SYSTEMPROMPT, B.P_UPPGIFT, B.P_SIGNALKARTA}


# ---- en normal tur ------------------------------------------------------

def _liten_tur(prof, resultatsvar=None, schema=None):
    namn = U.valj(V.REGISTER, "koppla roboten till transportoren")
    delar = [
        D.systempromptdel("B1 uppdrag\nB2 harda regler\nB5 driftlage\n"),
        D.uppgiftsdel("Koppla roboten till transportoren."),
        D.signalkartedel("ST010_PEC_PART BOOL in\n" * 13),
        D.avstangdadel(["move_robot", "save_layout"]),
        D.schemadel(V.REGISTER, namn,
                    U.schematext(V.REGISTER, namn),
                    lambda mal: U.valj(V.REGISTER, "koppla roboten", tak=20)),
    ]
    if resultatsvar is not None:
        delar.append(D.resultatdel(resultatsvar, schema, nr=0))
    delar += D.huvudboksdelar(["list_components() -> ok, %d poster" % i
                               for i in range(9)])
    return delar


def test_en_tur_som_ryms_trimmas_inte_alls():
    """Andra riktningen. Ett lager som alltid trimmar mater ingenting."""
    prof = profil.provprofil(kontext_tokens=400000, svar_tokens_max=8000)
    delar = _liten_tur(prof)
    plan = B.Budget(prof).planera(delar)
    assert plan.handelser == []
    assert plan.delad is False
    assert B.granska(delar, plan) == []


def test_trimningen_gar_uppifran_och_ned_i_den_slutna_ordningen():
    prof = profil.provprofil(kontext_tokens=24000, svar_tokens_max=2000)
    svar, schema = FX.storsta_svaret()
    delar = _liten_tur(prof, svar, schema)
    plan = B.Budget(prof).planera(delar)
    steg = [h.steg for h in plan.handelser]
    assert steg == sorted(steg), steg
    assert steg[0] == 1, "huvudboken ska ga forst"
    assert B.granska(delar, plan) == []


def test_huvudbokens_fem_senaste_star_kvar_hur_trangt_det_an_ar():
    prof = profil.provprofil(kontext_tokens=24000, svar_tokens_max=2000)
    svar, schema = FX.storsta_svaret()
    delar = _liten_tur(prof, svar, schema)
    plan = B.Budget(prof).planera(delar)
    kvar = [d for d in plan.delar if d.post == B.P_HUVUDBOK]
    assert len(kvar) >= B.HUVUDBOK_MINST
    assert [d.id for d in kvar[-B.HUVUDBOK_MINST:]] == \
        ["huvudbok:%d" % i for i in range(4, 9)]


def test_ingen_skyddad_del_ror_sig():
    prof = profil.provprofil(kontext_tokens=24000, svar_tokens_max=2000)
    svar, schema = FX.storsta_svaret()
    delar = _liten_tur(prof, svar, schema)
    plan = B.Budget(prof).planera(delar)
    fore = dict((d.id, d.text) for d in delar if d.skyddad)
    efter = dict((d.id, d.text) for d in plan.delar)
    for id_, text in fore.items():
        assert efter.get(id_) == text, id_


# ---- fail-closed --------------------------------------------------------

def test_en_budget_som_inte_rymmer_det_skyddade_kastar():
    """TRASIG FIXTUR som SKA falla (S1).

    En budget sa liten att inte ens signalkartan far plats ger ett FEL, inte
    en tyst trimning. Tas kartan bort hittar modellen pa taggnamn, och det ar
    felklassen F3 - mekaniskt borttagen bara sa lange kartan finns i prompten.
    """
    prof = profil.provprofil(kontext_tokens=140, svar_tokens_max=19)
    delar = _liten_tur(prof)
    # Det skyddade ar 133 tokens och budgeten 121. Talen star har for att
    # provet ska falla pa RATT sak: att skyddet inte far plats, inte pa att
    # allt annat rakade vara stort.
    assert sum(d.tokens(False) for d in delar if d.skyddad) > prof.budget_tokens
    with pytest.raises(Budgetfel) as info:
        B.Budget(prof).planera(delar)
    assert "signalkarta" in str(info.value)
    assert "aldrig far trimmas" in str(info.value) or \
        "Hellre inget anrop" in str(info.value)


def test_turen_delas_hellre_an_att_nagot_skyddat_offras():
    prof = profil.provprofil(kontext_tokens=3000, svar_tokens_max=420)
    svar, schema = FX.storsta_svaret()
    delar = _liten_tur(prof, svar, schema)
    plan = B.Budget(prof).planera(delar)
    assert plan.delad is True
    assert "delas" in plan.skal_for_delning
    assert B.granska(delar, plan) == []


# ---- bokforingen at bada hallen ----------------------------------------

def test_en_tyst_trimning_falls():
    """TRASIG FIXTUR: nagot andras utan en TRIMMAD-handelse."""
    prof = profil.provprofil(kontext_tokens=400000)
    delar = _liten_tur(prof)
    plan = B.Budget(prof).planera(delar)
    plan.delar[-1] = B.Del(post=B.P_HUVUDBOK, id=plan.delar[-1].id,
                           text="nagot annat")
    koder = B.granska(delar, plan)
    assert any(B.B1_TYST_TRIMNING in k for k in koder), koder


def test_en_handelse_utan_trimning_falls():
    """TRASIG FIXTUR at andra hallet: bokforing utan verklighet.

    Utan det har provet gar det att tysta grinden genom att skriva handelser
    for trimningar som aldrig gjordes.
    """
    prof = profil.provprofil(kontext_tokens=400000)
    delar = _liten_tur(prof)
    plan = B.Budget(prof).planera(delar)
    plan.handelser.append(B.Trimmad(steg=1, post=B.P_HUVUDBOK,
                                    del_id="huvudbok:0", fore_tokens=12,
                                    efter_tokens=0, vad="pahittad"))
    koder = B.granska(delar, plan)
    assert any(B.B2_HANDELSE_UTAN_TRIMNING in k for k in koder), koder


def test_en_trimmad_skyddad_del_falls():
    prof = profil.provprofil(kontext_tokens=400000)
    delar = _liten_tur(prof)
    plan = B.Budget(prof).planera(delar)
    for i, d in enumerate(plan.delar):
        if d.post == B.P_SIGNALKARTA:
            plan.delar[i] = B.Del(post=d.post, id=d.id, text="")
            plan.handelser.append(B.Trimmad(steg=1, post=d.post, del_id=d.id,
                                            fore_tokens=d.tokens(),
                                            efter_tokens=0, vad="riggad"))
    koder = B.granska(delar, plan)
    assert any(B.B3_SKYDDAD_TRIMMAD in k for k in koder), koder


# ---- steg 7: ett svar som ensamt spranger sin post ---------------------

def test_ett_for_stort_verktygssvar_kapas_hogljutt_och_behaller_felet():
    """FAS 22:s tredje trasiga fall, i budgeten i stallet for i kapningen.

    Det stora svaret ar riktigt: %s byte ur repots egen handlare.
    """
    svar, schema = FX.storsta_svaret()
    fallet = K.Verktygssvar(verktyg=svar.verktyg, argument=dict(svar.argument),
                            ok=False, resultat=svar.resultat,
                            fel="E_EXEC: VC nekade anropet",
                            felnyckel="%s/E_EXEC" % svar.verktyg)
    prof = profil.provprofil(kontext_tokens=32000, svar_tokens_max=4000)
    delar = _liten_tur(prof, fallet, schema)
    plan = B.Budget(prof).planera(delar)
    resultatdelar = [d for d in plan.delar if d.post == B.P_RESULTAT]
    assert len(resultatdelar) == 1
    text = resultatdelar[0].text
    assert "FELNYCKEL: %s/E_EXEC" % svar.verktyg in text
    assert "E_EXEC: VC nekade anropet" in text
    assert '"avkortad": true' in text.lower()
    assert any(h.steg == 7 for h in plan.handelser), \
        [h.rad() for h in plan.handelser]
    assert B.granska(delar, plan) == []


def test_aldsta_resultatet_blir_en_huvudboksrad_innan_nagot_kapas():
    prof = profil.provprofil(kontext_tokens=32000, svar_tokens_max=4000)
    svar, schema = FX.storsta_svaret()
    delar = _liten_tur(prof)
    delar.insert(5, D.resultatdel(svar, schema, nr=0))
    delar.insert(6, D.resultatdel(svar, schema, nr=1))
    plan = B.Budget(prof).planera(delar)
    steg2 = [h for h in plan.handelser if h.steg == 2]
    assert steg2, [h.rad() for h in plan.handelser]
    kvar = [d for d in plan.delar if d.id == "resultat:0"]
    assert kvar == [] or kvar[0].post == B.P_HUVUDBOK
    huvudbok = [d.text for d in plan.delar if d.post == B.P_HUVUDBOK]
    assert any("->  ok" in t for t in huvudbok)


# ---- rapporten ----------------------------------------------------------

def test_budgetrapporten_sager_vilket_tak_som_binder():
    """Ett lager utan den rapporten gar inte att stalla in."""
    prof = profil.provprofil(kontext_tokens=24000, svar_tokens_max=2000)
    svar, schema = FX.storsta_svaret()
    delar = _liten_tur(prof, svar, schema)
    plan = B.Budget(prof).planera(delar)
    rapport = plan.rapport()
    for p in B.POSTER:
        assert p.id in rapport
    assert "TRIMMAD" in rapport
    assert "marginal for svaret" in rapport


# ---- de tva antagandena -------------------------------------------------

def test_tokentalet_bar_tva_antaganden_och_budgeten_tar_det_hogsta():
    """MATT FYND (M-102): repot bar TVA omrakningar till tokens.

    25_kontextbudget.md sager 4 byte per token; harness/sammansattning.py
    sager 3,0 TECKEN per token. De ar inte samma storhet - var text ar svensk,
    och varje a-ring ar tva byte i UTF-8. Budgeten tar det HOGSTA talet, sa
    att en underskattning aldrig blir en overskridning motparten upptacker.
    """
    m = matt.mat("Ogats dom ar auktoritativ, och forreglingen holl.")
    assert m.tokens == max(m.tokens_ur_byte, m.tokens_ur_tecken)
    assert m.spridning > 0.0
    med_prickar = matt.mat("Ögats dom är auktoritativ, och förreglingen höll.")
    assert med_prickar.byte > med_prickar.tecken


def test_en_uppskattad_raknare_far_marginal_en_exakt_far_det_inte():
    assert matt.med_marginal(1000, exakt=True) == 1000
    assert matt.med_marginal(1000, exakt=False) > 1000


# ---- verktygsschemat mot sitt tak --------------------------------------

def test_hela_registret_far_inte_plats_under_postens_tak():
    """MATT FYND (M-102), och skalet att urvalet byggs nu.

    23_llm_granssnitt.md skrev "urvalsmaskineriet byggs alltsa inte nu" vid 21
    verktyg och 11 074 byte. Registret bar i dag 122 verktyg, och schemat ar
    over 90 kB - langt over postens tak pa 10 % i varje fonster nagon
    leverantor erbjuder.
    """
    hela = U.schematext(V.REGISTER, sorted(V.REGISTER))
    tokens = matt.tokens(hela)
    assert len(V.REGISTER) > 100
    minsta_fonster = tokens * 10        # postens tak ar 10 %
    assert minsta_fonster > 200000, (
        "schemat ryms nu i ett vanligt fonster; talet i provet ar inaktuellt")
    prof = profil.provprofil()
    assert tokens > B.Budget(prof).tak_tokens(B.P_SCHEMA)


def test_urvalet_ar_deterministiskt_och_bar_alltid_med_listan():
    a = U.valj(V.REGISTER, "koppla roboten till transportoren")
    b = U.valj(V.REGISTER, "koppla roboten till transportoren")
    assert a == b
    for namn in U.alltid_med(V.REGISTER):
        assert namn in a
