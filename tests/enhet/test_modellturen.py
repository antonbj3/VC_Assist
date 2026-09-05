# -*- coding: utf-8 -*-
"""Turen: modellprofilen, tillstandsmaskinen och de fyra tysta felen.

FAS 22. Maskinen deklareras i `llm/tur.py` och provas mot den BYGGDA loopens
protokoll - inte mot en andra loop skriven for provet. Skalet ar att tva
loopar med samma namn blir tva storheter: den ena provas medan den andra kors.

DE FYRA SATTEN EN TUR KAN TYSTNA PA, och vad var och en ska bli:

    modellen svarar ingenting        STOPP/TYSTNAD, aldrig KLAR (I3)
    svaret gar inte att tolka        SVARSFEL efter ETT omforsok
    verktyget finns inte             AVVISAD fore korning, aldrig ett anrop ut
    verktyget svarar aldrig i tid    FALL med TAK_TID, aldrig ett ok

Den fjarde ar den enda som inte gar att avbryta, och det ar matt: exec kors
synkront pa VC:s trad (`pump._op_cancel`, M-13). Tidsvakten kan darfor bara
vagra lita pa svaret - vilket ar precis vad den gor.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "tests", "protocol", "stod")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.harness import fallor as F                  # noqa: E402
from vc_assist_svc.harness import kanal as Kn                  # noqa: E402
from vc_assist_svc.harness import loop as L                    # noqa: E402
from vc_assist_svc.harness import modell as Mo                 # noqa: E402
from vc_assist_svc.harness.fel import Modellfel                # noqa: E402
from vc_assist_svc.llm import kapning as K                     # noqa: E402
from vc_assist_svc.llm import profil, scenvy, tur              # noqa: E402
from vc_assist_svc.llm.fel import Profilfel, Turfel            # noqa: E402

UPPGIFT = "Koppla roboten till transportoren och rapportera avstandet."


def _kor(modell, manus=None, uppgift=UPPGIFT, **kw):
    return L.Harness(modell=modell, kanal=Kn.Attrappkanal(manus or {}),
                     **kw).kor(uppgift)


# ---- modellprofilen -----------------------------------------------------

def test_provprofilen_ar_hel():
    p = profil.provprofil()
    assert p.budget_tokens + p.svarsmarginal_tokens == p.kontext_tokens
    assert set(profil.FALTNAMN) == set(f.namn for f in profil.FALT)


@pytest.mark.parametrize("falt", [f.namn for f in profil.FALT])
def test_varje_saknat_falt_kastar_och_namner_vad_det_anvands_till(falt):
    """Tre svarsformer, aldrig fler: saknad formaga kastar med sitt NAMN.

    Ett falt som far ett standardvarde i tysthet ar den nedgradering
    36_versioner.md forbjuder - och for `kontext_tokens` betyder den att hela
    budgeten raknas pa nagon annans fonster.
    """
    d = dict((f.namn, getattr(profil.provprofil(), f.namn))
             for f in profil.FALT)
    del d[falt]
    with pytest.raises(Profilfel) as info:
        profil.las(d)
    assert falt in str(info.value)
    assert profil._FALT[falt].anvands_till.split()[0] in str(info.value)


def test_ett_okant_varde_raknas_som_saknat():
    d = dict((f.namn, getattr(profil.provprofil(), f.namn))
             for f in profil.FALT)
    d["tokenraknare"] = "okand"
    with pytest.raises(Profilfel):
        profil.las(d)


def test_en_modell_utan_verktygsanrop_stoppar_tjansten_med_formagans_namn():
    with pytest.raises(Profilfel) as info:
        profil.provprofil(verktygsanrop=False)
    assert "VERKTYGSANROP" in str(info.value)
    assert "tolkar" in str(info.value) and "fritext" in str(info.value)


def test_ett_svarstak_over_marginalen_ar_en_marginal_som_redan_ar_uppaten():
    with pytest.raises(Profilfel) as info:
        profil.provprofil(svar_tokens_max=100000)
    assert "marginalen" in str(info.value)


def test_icke_repeterbar_profil_markeras_men_stoppar_inte():
    p = profil.provprofil(seed=False, temperatur_noll=False)
    assert any("icke-repeterbara" in a for a in p.anmarkningar)


# ---- tillstandsmaskinen mot de riktiga turerna --------------------------

@pytest.fixture(scope="module")
def bankturer():
    ut = []
    for f in F.ALLA:
        p = L.Harness(modell=Mo.AttrappModell(f.svar),
                      kanal=Kn.Attrappkanal(f.manus or {})).kor(
            f.uppgift, ogonrapport=f.ogonrapport, guldbeslut=f.guld)
        ut.append((f, p))
    return ut


def test_alla_bankens_turer_gar_en_deklarerad_vag(bankturer):
    assert len(bankturer) >= 90, len(bankturer)
    for f, p in bankturer:
        assert tur.granska(p) == [], f.id


def test_varje_tur_slutar_i_ett_uttalat_slutlage(bankturer):
    for f, p in bankturer:
        lage = tur.slutlage(tur.spar_ur_protokoll(p))
        assert lage in tur.TERMINALA, (f.id, lage)


def test_tackningen_rapporteras_som_par(bankturer):
    """En maskin ingen tur besoker ar en beskrivning, inte en grind."""
    t = tur.Tackning()
    for _f, p in bankturer:
        t.lagg(tur.spar_ur_protokoll(p))
    assert len(t.lagen) >= 6
    assert len(t.overgangar) >= 10
    assert "av %d overgangar" % len(tur.OVERGANGAR) in t.rad()


def test_en_vag_utanfor_tabellen_kastar():
    """TRASIG FIXTUR for maskinen sjalv."""
    with pytest.raises(Turfel) as info:
        tur._nasta(tur.KLAR, "VERKTYG_OK")
    assert "ingen deklarerad overgang" in str(info.value)


def test_stoppkoderna_i_koden_och_i_specen_ar_samma_lista():
    """En sluten lista som inte provas mot koden har redan glidit."""
    assert tur.okanda_stoppkoder() == ()
    assert tur.overflodiga_stoppkoder() == ()


# ---- de fyra tysta felen ------------------------------------------------

def test_tystnad_blir_aldrig_ett_godkant_slutsvar():
    """FAS 22:s andra trasiga fall (I3)."""
    p = _kor(Mo.AttrappModell([]))
    assert p.klar is False
    assert p.slutsvar == ""
    assert p.utfall == "STOPP:tystnad"
    assert tur.stoppkod(p) == "TYSTNAD"
    assert tur.slutlage(tur.spar_ur_protokoll(p)) == tur.STOPPAD
    assert tur.granska(p) == []


def test_ett_protokoll_som_pastar_klart_med_tomt_svar_falls():
    """TRASIG FIXTUR: samma tystnad, men markt som klar."""
    p = _kor(Mo.AttrappModell([]))
    p.klar = True
    koder = tur.granska(p)
    assert any(tur.T3_TYST_GODKANNANDE in k for k in koder), koder


def test_ett_otolkbart_svar_ger_ett_omforsok_och_sedan_svarsfel():
    class Trasig(Mo.Modell):
        leverantor = "attrapp"

        def __init__(self):
            self.forsok = 0

        def svara(self, systemprompt, meddelanden, verktyg):
            self.forsok += 1
            raise Modellfel("argumenten gar inte att avkoda som JSON")

    inre = Trasig()
    vakt = tur.Tolkvakt(inre)
    p = _kor(vakt)
    assert inre.forsok == tur.OMFORSOK_MAX + 1
    assert p.klar is False
    assert tur.stoppkod(p, vakt) == tur.SVARSFEL
    assert tur.stoppkod(p) == "TYSTNAD", (
        "utan vakten gar orsaken forlorad - det ar just det vakten finns for")


def test_ett_verktyg_som_inte_finns_avvisas_fore_korning():
    kanal = Kn.Attrappkanal({})
    h = L.Harness(modell=Mo.AttrappModell([Mo.anropa("hitta_pa", {"x": 1})]),
                  kanal=kanal)
    p = h.kor(UPPGIFT)
    assert kanal.anropade == [], "anropet gick ut trots att verktyget saknas"
    assert p.utfall.startswith("AVVISAD:")
    assert tur.granska(p) == []


def test_ett_verktyg_som_svarar_for_sent_blir_ett_fall_aldrig_ett_ok():
    """Klockan ar injicerad. Ett prov som mater en tidsgrans genom att sova
    mater schemalaggaren."""
    tider = iter([0.0, 500.0, 500.0, 500.1])
    kanal = tur.Tidsvaktkanal(
        Kn.Attrappkanal({"list_components": [{"components": [], "antal": 0,
                                              "avkortad": False},
                                             {"components": [], "antal": 0,
                                              "avkortad": False}]}),
        tak_s=60.0, klocka=lambda: next(tider))
    sen = kanal.utfor("list_components", {})
    assert sen.ok is False
    assert "TAK_TID" in sen.fel
    assert "INTE att avbryta" in sen.fel
    i_tid = kanal.utfor("list_components", {})
    assert i_tid.ok is True


# ---- scenvyn ------------------------------------------------------------

def _scen(antal, plannamn):
    poster = [{"name": "KOMP%03d" % i, "uri": "bank://transport/rullbana",
               "category": "transport"} for i in range(antal)]
    for i, namn in enumerate(plannamn):
        poster[i]["name"] = namn
    return K.Verktygssvar(
        verktyg="list_components", argument={},
        resultat={"components": poster, "antal": len(poster),
                  "avkortad": False})


def test_en_stor_scen_behaller_planens_komponenter_och_deras_kopplade():
    plannamn = ["ST010", "CNV1", "IRB1200"]
    svar = _scen(200, plannamn)
    kopplingar = [("CNV1", "KOMP150")]
    vy = scenvy.sammanfatta(svar, plannamn, kopplingar)
    visade = set(p["name"] for p in vy.resultat["components"])
    assert set(plannamn) | {"KOMP150"} <= visade
    assert sum(vy.resultat["kategorier"].values()) == 200
    assert "200 komponenter" in vy.resultat["kaprad"]
    assert scenvy.granska(svar, vy, plannamn + ["KOMP150"]) == []


def test_en_liten_scen_gar_fram_hel_och_ordagrant():
    svar = _scen(9, ["ST010"])
    vy = scenvy.sammanfatta(svar, ["ST010"], [])
    assert vy is svar


def test_ett_namn_turen_behover_far_inte_sammanfattas_bort():
    """TRASIG FIXTUR. En miss andrar regel 1; den ar ingen ratt att skruva pa."""
    svar = _scen(200, ["ST010"])
    vy = scenvy.sammanfatta(svar, ["ST010"], [])
    koder = [a.kod for a in scenvy.granska(svar, vy, ["ST010", "KOMP177"])]
    assert scenvy.S1_NAMN_BORTA in koder, koder


def test_avkortad_far_inte_svaljas_i_sammanfattningen():
    """TRASIG FIXTUR. Att svalja avkortad ar att gora fail-closed till
    fail-open."""
    svar = _scen(200, ["ST010"])
    svar.resultat["avkortad"] = True
    vy = scenvy.sammanfatta(svar, ["ST010"], [])
    assert vy.resultat["avkortad"] is True
    riggad = K.Verktygssvar(verktyg=vy.verktyg, argument=dict(vy.argument),
                            resultat=dict(vy.resultat, avkortad=False),
                            id=vy.id, ur_kalla=vy.ur_kalla,
                            sammanfattning=True)
    koder = [a.kod for a in scenvy.granska(svar, riggad, ["ST010"])]
    assert scenvy.S2_AVKORTAD_SVALD in koder, koder


def test_en_sammanfattning_av_en_sammanfattning_ar_ett_linterfel():
    svar = _scen(200, ["ST010"])
    vy = scenvy.sammanfatta(svar, ["ST010"], [])
    with pytest.raises(ValueError) as info:
        scenvy.sammanfatta(vy, ["ST010"], [])
    assert "redan en sammanfattning" in str(info.value)
