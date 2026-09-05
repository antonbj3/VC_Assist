# -*- coding: utf-8 -*-
"""L2: ogats dom over handbyggda celler. Ingen VC behovs.

Fas 2:s grind (70_faser.md): pa en handbyggd bra och en handbyggd trasig cell
ska ogats dom matcha facit i BADA. Den trasiga MASTE fallas.

Testerna kraver dessutom att fallningen sker pa RATT rad. En domare som faller
allt ar lika oanvandbar som en som godkanner allt, och bada ser bra ut om man
bara raknar fallningar.
"""
import ast
import os
import sys
import types

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests")))

import celler                 # noqa: E402
import oga_analys as A        # noqa: E402
import oga_kontrakt as K      # noqa: E402


def _doma(namn):
    b, plan = celler.ALLA[namn]()
    text, rapport, analys = A.doma(b.data(), plan)
    # Domen ska overleva att den skrivs ut och lases tillbaka byte for byte.
    tillbaka = K.las(text)
    assert tillbaka.text() == text
    rader = [r for _s, rr in rapport.sektioner for r in rr]
    return rapport, rader, analys


def test_den_bra_cellen_far_PASS():
    """Utan detta ar varje fallning nedan varde los - en domare som faller
    allt klarar alla ovriga prov."""
    r, rader, _ = _doma("bra")
    assert r.dom[0] == "PASS", r.dom
    assert r.godkand() is True
    assert any(x.startswith("GRIP FORMED") for x in rader)
    assert any(x.startswith("CARRY RIGID") for x in rader)
    assert any(x.startswith("PLACE IN_TARGET") for x in rader)
    assert r.overtradelser() == []


FACIT = {
    "teleport":      ("FAIL", "TELEPORT_TRANSFER VIOLATION"),
    "glider":        ("FAIL", "CARRY SLIPPING"),
    "tappad":        ("FAIL", "PLACE DROPPED"),
    "fel_placerad":  ("FAIL", "PLACE OFF_TARGET"),
    "aldrig_gripen": ("FAIL", "NEVER_GRIPPED VIOLATION"),
    "explosion":     ("FAIL", "BLOWUP VIOLATION"),
    "under_golvet":  ("FAIL", "UNDERGROUND VIOLATION"),
    "kollision":     ("FAIL", "COLLISION gripper_finger x fixtur_vagg"),
    "kollision_med_feature": ("FAIL", "COLLISION gripper_finger x fixtur_vagg"),
    "kontakt":       ("FAIL", "COLLISION gripper x fixtur t=2.200s"),
    "kort_uppehall": ("FAIL", "SHORT"),
    "for_fa_prov":   ("INCONCLUSIVE", None),
    # scenen som helhet
    "oombedd_rorelse":   ("FAIL", None),
    "utglesad_scen":     ("INCONCLUSIVE", None),
    "orort_trots_signal": ("FAIL", None),
    # robotleder
    "robot_ledgrans":    ("FAIL", None),
    "robot_singularitet": ("FAIL", None),
    "robot_foljfel":     ("FAIL", None),
    # stationer
    "station_svalt":     ("FAIL", None),
    "station_blockerad": ("FAIL", None),
    # PLC
    "plc_gammal":        ("INCONCLUSIVE", None),
    # timing: fasen mot ett krav, och mot ogats egen upplosning (M-65)
    "fas_utanfor_tolerans":      ("FAIL", None),
    "fas_inom_upplosningen":     ("INCONCLUSIVE", None),
    "fas_finare_an_upplosningen": ("INCONCLUSIVE", None),
    # rorelse
    "utslungad":         ("FAIL", None),
    "rord_men_aldrig_gripen": ("FAIL", "NEVER_GRIPPED VIOLATION"),
    # trosklarnas granser
    "utan_placeringstolerans": ("FAIL", "PLACE OFF_TARGET"),
    # stationen: en sekvens i tiden, inget grepp
    "station_utan_stopp":       ("FAIL", None),
    "station_slapper_aldrig":   ("FAIL", None),
    "station_forsent":          ("FAIL", None),
    "station_forregling_bruten": ("FAIL", None),
    "station_gor_om_arbetet":   ("FAIL", None),
    "station_bara_en_cykel":    ("INCONCLUSIVE", None),
    "station_krav_utan_prov":   ("INCONCLUSIVE", None),
    "station_utan_deklaration": ("INCONCLUSIVE", None),
}

# Den ANDRA riktningen. En domare som faller allt klarar varje fallningsprov
# och ar anda vardelos, sa varje ny grind har ocksa en cell dar den ska TIGA.
GRONA = ("bra", "bakgrund_stilla", "scen_deltalagrad", "oombedd_men_deklarerad",
         "tva_produkter", "band_ror_sig", "robot_ren", "robot_gransnara",
         "robot_omorientering", "robot_foljer", "robot_stopp_begransande",
         "mindist_nara", "station_svalt_utan_krav", "station_upptagen",
         "plc_i_fas", "plc_ur_fas", "fas_inom_tolerans", "pa_placeringsgransen",
         "pa_barstrackans_grans",
         "station_bra", "station_forregling_utan_deklaration")


@pytest.mark.parametrize("namn", sorted(FACIT))
def test_trasig_cell_falls_pa_sin_egen_orsak(namn):
    vantad_dom, vantad_rad = FACIT[namn]
    r, rader, _ = _doma(namn)
    assert r.dom[0] == vantad_dom, "%s fick %s: %s" % (namn, r.dom[0], r.dom[1])
    assert r.godkand() is False
    if vantad_rad:
        assert any(vantad_rad in x for x in rader), \
            "%s falldes, men inte pa %r. Rader: %s" % (namn, vantad_rad, rader)


def test_teleport_matter_avstandet_och_inte_bara_flaggar():
    """Talet ska bara sin egen storhet: 800 mm ar hela poangen."""
    r, rader, _ = _doma("teleport")
    rad = [x for x in rader if x.startswith("TELEPORT_TRANSFER")][0]
    assert "dist=800.0mm" in rad


def test_glidningen_matts_i_grader_i_verktygets_ram():
    r, rader, a = _doma("glider")
    rad = [x for x in rader if x.startswith("CARRY")][0]
    assert "rot=15.0deg" in rad
    assert abs(a.harledt["motion"]["carry"]["rot_deg"] - 15.0) < 0.1


def test_fel_placerad_bar_sitt_fel_i_mm():
    r, rader, _ = _doma("fel_placerad")
    assert "err=80.0mm" in [x for x in rader if x.startswith("PLACE")][0]


def test_en_overtradelse_tvingar_FAIL_aven_nar_allt_annat_ar_gront():
    """Teleportcellen har perfekt grepp, styv barning och ratt placering.
    Den ska anda falla - det ar hela skalet till att grinden finns."""
    r, rader, _ = _doma("teleport")
    assert any(x.startswith("PLACE IN_TARGET") for x in rader)
    assert any(x.startswith("CARRY RIGID") for x in rader)
    assert r.dom[0] == "FAIL"


def test_for_fa_prov_blir_inconclusive_inte_pass():
    """Fail-closed: brist pa underlag ar inte ett godkannande."""
    r, _rader, _ = _doma("for_fa_prov")
    assert r.dom[0] == "INCONCLUSIVE"
    assert r.godkand() is False


def test_ett_stillastaende_verktyg_bredvid_en_stillastaende_del_ar_inget_grepp():
    """Stillhet i verktygsramen ar trivialt sann nar bada star still. Utan
    varldsrorelsevillkoret blev det 'grepp vid t=0' och en falsk teleportdom."""
    b = celler.Bygge("stillastaende")
    for _ in range(40):
        b.steg([0.5, 0.0, 0.75], [0.0, 0.0, 1.4])
    r = A.Analys(b.data(), celler.plan()).rapport()
    rader = [x for _s, rr in r.sektioner for x in rr]
    assert any(x == "GRIP NEVER_FORMED" for x in rader)
    assert not any("TELEPORT_TRANSFER VIOLATION" in x for x in rader)


def test_domen_pekar_ut_orsaken_i_klartext():
    for namn in ("teleport", "glider", "tappad", "kort_uppehall"):
        r, _rader, _ = _doma(namn)
        assert len(r.dom[1]) > 10, "%s: domen sager inte varfor" % namn


@pytest.mark.parametrize("namn", sorted(celler.ALLA))
def test_varje_cell_ger_en_rapport_som_lases_tillbaka(namn):
    """En rapport som kraschar domaren kan dolja rott."""
    _doma(namn)


# ---- den andra riktningen ------------------------------------------------

@pytest.mark.parametrize("namn", GRONA)
def test_en_gron_cell_far_PASS(namn):
    """För varje ny grind finns en cell där den INTE ska fälla.

    Utan de här proven mäter fällningsproven ovan ingenting: en domare som
    fäller allt klarar dem alla.
    """
    r, _rader, _a = _doma(namn)
    assert r.dom[0] == "PASS", "%s fick %s: %s" % (namn, r.dom[0], r.dom[1])
    assert r.godkand() is True


def test_varje_cell_har_ett_facit():
    """83_scenarier.md, regel 1: en cell utan facit hör inte hemma här.

    Utan det här provet kan en ny cell läggas till utan att någon säger vad
    den ska ge, och då mäter den ingenting.
    """
    utan = sorted(set(celler.ALLA) - set(FACIT) - set(GRONA))
    assert not utan, "celler utan facit: %s" % utan


# ---- scenen som helhet ---------------------------------------------------

def test_hela_scenen_finns_i_serien_inte_bara_rollerna():
    """Operatörens krav: ett objekt som ingen tänkte på ska ändå finnas där
    när man i efterhand frågar varför något gick fel."""
    r, _rader, a = _doma("bakgrund_stilla")
    scen = a.harledt["scene"]
    assert set(scen["stilla"]) >= set(celler.BAKGRUND)
    assert scen["rorliga"] == ["del", "gripper"]


def test_deltalagringen_andrar_inte_domen():
    """Lagringsformen får aldrig flytta en dom. Gör den det är den inte en
    lagringsform utan en filtrering."""
    full, rader_full, _ = _doma("bakgrund_stilla")
    delta, rader_delta, _ = _doma("scen_deltalagrad")
    assert full.dom[0] == delta.dom[0] == "PASS"
    assert rader_full == rader_delta


def test_oombedd_rorelse_faller_och_namnger_objektet():
    r, _rader, a = _doma("oombedd_rorelse")
    assert r.dom[0] == "FAIL"
    assert "stallage" in r.dom[1]
    assert a.harledt["scene"]["oombedd"][0]["objekt"] == "stallage"


def test_samma_rorelse_med_planens_valsignelse_ar_inget_fel():
    """Skillnaden mellan de två cellerna är EN rad i planen, inte i serien."""
    trasig, _r1, _a1 = _doma("oombedd_rorelse")
    hel, _r2, a2 = _doma("oombedd_men_deklarerad")
    assert trasig.dom[0] == "FAIL" and hel.dom[0] == "PASS"
    assert a2.harledt["scene"]["oombedd"] == []


def test_en_utglesad_scen_blir_inconclusive_och_aldrig_pass():
    """Fail-closed på scenens sida: en gles serie får inte läsas som stillhet."""
    r, _rader, a = _doma("utglesad_scen")
    assert r.dom[0] == "INCONCLUSIVE"
    assert r.godkand() is False
    assert "saknar en scenavlasning" in a.harledt["scene"]["obestambar"]


def test_utan_deklarerat_forvantat_rorliga_stalls_scenfragan_aldrig():
    """Tystnad om något ingen frågat om är inte ett godkännande av det."""
    _r, _rader, a = _doma("bra")
    assert a.harledt["scene"]["oombedd"] is None


def test_cykeltid_per_produkt_star_i_underlaget():
    _r, _rader, a = _doma("tva_produkter")
    ledtider = a.harledt["scene"]["ledtider"]
    assert "produkt_b" in ledtider and ledtider["produkt_b"]["ledtid_s"] > 1.0
    assert ledtider["del"]["ledtid_s"] != ledtider["produkt_b"]["ledtid_s"]


def test_ett_don_som_far_en_signal_men_inte_ror_sig_falls():
    trasig, _r1, a1 = _doma("orort_trots_signal")
    hel, _r2, _a2 = _doma("band_ror_sig")
    assert trasig.dom[0] == "FAIL" and hel.dom[0] == "PASS"
    assert a1.harledt["scene"]["orort"][0]["objekt"] == "band_in"


# ---- robotleder ----------------------------------------------------------

def test_ledgransen_skiljer_natt_fran_passerad():
    natt, _r1, a1 = _doma("robot_gransnara")
    forbi, _r2, a2 = _doma("robot_ledgrans")
    assert natt.dom[0] == "PASS", natt.dom
    assert forbi.dom[0] == "FAIL" and "gräns" in forbi.dom[1]
    assert a1.harledt["robotar"]["robot1"]["granser_nadda"][0]["over"] is False
    assert a2.harledt["robotar"]["robot1"]["granser_nadda"][0]["over"] is True


def test_singulariteten_skiljer_urartning_fran_omorientering():
    urartad, _r1, _a1 = _doma("robot_singularitet")
    vridande, _r2, a2 = _doma("robot_omorientering")
    assert urartad.dom[0] == "FAIL" and "urartning" in urartad.dom[1]
    assert vridande.dom[0] == "PASS", vridande.dom
    assert a2.harledt["robotar"]["robot1"]["singularitet"] == []


def test_kommenderat_mot_uppnatt_bar_sitt_kvarstaende_fel():
    r, _rader, a = _doma("robot_foljfel")
    assert r.dom[0] == "FAIL"
    fel = [f for f in a.harledt["robotar"]["robot1"]["foljfel"] if not f["nadde_malet"]]
    assert fel and abs(fel[0]["kvarstaende_fel"] - 12.0) < 0.5


def test_ogat_sager_vilken_led_som_orsakade_ett_stopp():
    """Den mest användbara av robotharledningarna: inte ATT den stannade utan
    VILKEN led som gjorde att den gjorde det."""
    r, _rader, a = _doma("robot_stopp_begransande")
    assert r.dom[0] == "PASS", "ett stopp är ingen defekt"
    stopp = a.harledt["robotar"]["robot1"]["stopp"]
    assert stopp, "inget stopp hittades"
    assert stopp[-1]["led"] is not None and stopp[-1]["bevis"]


# ---- kollision och minsta avstand ---------------------------------------

def test_minsta_avstandet_bar_sitt_tal_och_sin_tidpunkt():
    r, rader, _a = _doma("mindist_nara")
    rad = [x for x in rader if x.startswith("MINDIST")][0]
    assert "12.0mm" in rad and "t=3.000s" in rad
    assert r.dom[0] == "PASS", "nära är inte samma sak som i"


def test_traffens_ytor_foljer_med_i_underlaget():
    """getHitFeatureA/B ryms inte i v1:s COLLISION-rad. Då hör de hemma i
    eyes.json, inte i papperskorgen."""
    _r, _rader, a = _doma("kollision_med_feature")
    kol = a.harledt["safety"]["kollision"]
    assert kol["feature_a"] == "Face_12" and kol["feature_b"] == "Face_3"


# ---- stationer -----------------------------------------------------------

def test_svalt_och_blockering_faller_bara_mot_ett_deklarerat_krav():
    """Ett mått utan krav är ett mått, inte en dom."""
    med_krav, _r1, _a1 = _doma("station_svalt")
    utan_krav, _r2, a2 = _doma("station_svalt_utan_krav")
    assert med_krav.dom[0] == "FAIL" and "svalt" in med_krav.dom[1]
    assert utan_krav.dom[0] == "PASS"
    assert a2.harledt["stationer"]["station1"]["svalt_s"] > 2.0


def test_genomflodeskrav_utan_provad_station_ar_obesvarat_inte_uppfyllt():
    """Nollpunkten för genomflödesgrinden.

    Grinden såg ett krav, hittade inga brott — för det fanns inga stationer
    att hitta brott hos — och svarade PASS. Ett godkännande av en fråga den
    aldrig ställde (M-74).
    """
    r, _rader, a = _doma("station_krav_utan_prov")
    assert r.dom[0] == "INCONCLUSIVE", r.dom
    assert "ingen station provades" in r.dom[1]
    assert a.domar()["genomflode"]["fynd"]["provade"] == 0


def test_blockerad_och_upptagen_ar_inte_samma_sak():
    blockerad, _r1, a1 = _doma("station_blockerad")
    upptagen, _r2, a2 = _doma("station_upptagen")
    assert blockerad.dom[0] == "FAIL" and upptagen.dom[0] == "PASS"
    assert a1.harledt["stationer"]["_flaskhals"]["orsak"] == "blockerad"
    assert a2.harledt["stationer"]["_flaskhals"] is None


# ---- PLC pa samma tidsaxel ----------------------------------------------

def test_plctaggar_ligger_pa_samma_tidsaxel_som_fysiken():
    """Hela poängen: när en PLC-variabel och en fysisk rörelse ligger på samma
    tidsaxel blir ett tidsfel ett läsbart fasförhållande."""
    r, rader, a = _doma("plc_i_fas")
    assert any(x.startswith("EDGE plc:Start RISE") for x in rader), rader
    fas = a.harledt["timing"]["fas"]
    assert fas[0]["forst"] == "plc"
    # 110, inte 100: taggen sags hog i provet vid t=0,90 med aldern 0,01 s,
    # alltsa lastes den hog vid 0,89. Flanken hor till lasningen, inte till
    # provet (M-65 §3). Fore det stod har 100,0 - provet laste in att en
    # PLC-flank lag pa provets tid, vilket ar upp till PLC_FARSK_S for sent.
    assert abs(fas[0]["dt_ms"] - 110.0) < 1e-6
    assert r.dom[0] == "PASS"


def test_ett_stort_fasfel_mats_men_domes_inte_utan_krav():
    _r, _rader, a = _doma("plc_ur_fas")
    assert abs(a.harledt["timing"]["fas"][0]["dt_ms"] - 510.0) < 1e-6


def test_gamla_plcvarden_blir_inconclusive_inte_pass():
    """Ett värde äldre än sitt eget prov ligger inte på samma tidsaxel, och då
    är fasförhållandet inget mått."""
    r, _rader, _a = _doma("plc_gammal")
    assert r.dom[0] == "INCONCLUSIVE" and r.godkand() is False


# ---- utslungad mot tappad ------------------------------------------------

def test_kast_och_tapp_ar_tva_felklasser_och_blandas_inte_ihop():
    """Båda är fritt fall och båda passerar 3 m/s. Det som skiljer dem är den
    vågräta farten — en grind som mäter total fart dömer dem likadant."""
    kast, _r1, a1 = _doma("utslungad")
    tapp, _r2, a2 = _doma("tappad")
    assert "slungades" in kast.dom[1]
    assert "slungades" not in tapp.dom[1], tapp.dom
    assert a1.harledt["scene"]["utslungad"]
    assert a2.harledt["scene"]["utslungad"] == {}


def test_aldrig_tagen_skiljs_fran_aldrig_gripen():
    """NEVER_GRIPPED säger att greppmängden var tom. `aldrig_tagen` säger
    VARFÖR: det fanns inget att gripa om. En cell där detaljen RÖR sig och
    ändå aldrig grips skiljer de två grindarna åt."""
    still, _r1, a1 = _doma("aldrig_gripen")
    rord, _r2, a2 = _doma("rord_men_aldrig_gripen")
    assert a1.harledt["scene"]["aldrig_tagen"] is not None
    assert a2.harledt["scene"]["aldrig_tagen"] is None
    assert still.dom[0] == rord.dom[0] == "FAIL"


# ---- scenforstaelse i ord -----------------------------------------------

def test_ogat_kan_svara_pa_vad_som_pagar_i_scenen():
    """Operatörens fråga, ordagrant. Svaret är text — aldrig en dom."""
    _r, _rader, a = _doma("bakgrund_stilla")
    text = " ".join(a.berattelse())
    assert "gripper" in text and "stallage" in text
    assert "rorde sig" in text or "Rorde sig" in text
    for forbjudet in ("PASS", "FAIL", "godkand", "godkänd"):
        assert forbjudet not in text


def test_redogorelsen_ligger_i_underlaget_och_ar_aldrig_domen():
    """I1 står fast: grinden läser domsraden, inte redogörelsen."""
    r, _rader, a = _doma("bra")
    assert isinstance(a.harledt["berattelse"], list)
    assert r.dom[1] not in a.harledt["berattelse"]


def test_vad_pagar_svarar_for_en_utpekad_tidpunkt():
    _r, _rader, a = _doma("bra")
    svar = " ".join(a.vad_pagar(2.0))
    assert "t=2.00" in svar
    assert "gripper" in svar


def test_berattelsen_pekar_ut_flaskhalsen():
    _r, _rader, a = _doma("station_blockerad")
    text = " ".join(a.berattelse())
    assert "Flaskhalsen ar station1" in text and "blockerad" in text


# ---- bakåtkompatibilitet mot fas 2 --------------------------------------

FAS2 = {"bra": "PASS", "teleport": "FAIL", "glider": "FAIL",
        "fel_placerad": "FAIL", "tappad": "FAIL"}


@pytest.mark.parametrize("namn", sorted(FAS2))
def test_fas2_cellerna_far_samma_dom_genom_VC_vagen(namn):
    """De fem cellerna i tests/protocol/kor_fas2.py döms i dag rätt mot en
    riktig VC. Ändrar utbyggnaden deras dom är det en regression.

    Provet går VC-vägen utan VC: banan kvantiseras till [x, y, z, gir] precis
    som kor_fas2._punkt() gör, spelas tillbaka under VC:s objektnamn och döps
    om på vägen in i analysen — samma kedja, utan bryggan.
    """
    import math
    b, plan = celler.ALLA[namn]()

    def punkt(pose):
        p, q = pose["p"], pose["q"]
        return [round(p[0], 5), round(p[1], 5), round(p[2], 5),
                round(math.degrees(2.0 * math.atan2(q[2], q[3])), 4)]

    def pose(pt):
        a = math.radians(pt[3]) / 2.0
        return {"p": pt[:3], "q": [0, 0, math.sin(a), math.cos(a)]}

    rader = []
    for i, r in enumerate(b.data()["rows"]):
        rader.append({"t": round(i * 0.05, 4),
                      "parts": {"del": pose(punkt(r["parts"]["del"]))},
                      "tools": {"gripper": pose(punkt(r["tools"]["gripper"]))}})
    data = {"v": 1, "template": namn,
            "run": {"started": "2026-09-04T17:00:00", "dur_s": len(rader) * 0.05,
                    "samples": len(rader), "rate_hz": 20.0},
            "tracked": {"parts": ["del"], "tools": ["gripper"],
                        "signals": [], "pairs": []},
            "rows": rader}
    _text, rapport, _a = A.doma(data, plan)
    assert rapport.dom[0] == FAS2[namn], "%s: %s" % (namn, rapport.dom)


def test_ogat_svarar_pa_nar_nagot_bytte_fart_riktning_eller_hojd():
    """Coordinatorns fråga, ordagrant: vilket objekt bytte hastighet, riktning
    eller höjd — och när."""
    _r, _rader, a = _doma("bra")
    byten = a.harledt["scene"]["forandringar"]
    assert "gripper" in byten and "del" in byten
    sorter = set(h["vad"] for poster in byten.values() for h in poster)
    assert {"fart", "hojd"} <= sorter
    assert all(isinstance(h["t"], float) for poster in byten.values()
               for h in poster)


def test_bakgrundsobjekt_som_star_still_bytte_ingenting():
    """Den andra riktningen: en scen full av stillastående ting ska inte
    fylla förändringslistan med brus."""
    _r, _rader, a = _doma("bakgrund_stilla")
    byten = a.harledt["scene"]["forandringar"]
    assert not (set(byten) & set(celler.BAKGRUND))


# ---- stationen: sekvensen ar arbetet, greppet finns inte -----------------

def test_stationen_utan_roller_kan_fa_PASS_men_bara_med_en_deklarerad_sekvens():
    """Bada halvorna i ett prov, for de bar varandra.

    Slapptes greppkravet utan att nagot annat kravdes i stallet hade vagen ut
    ur greppgrinden varit att utelamna `tools` ur planen.
    """
    r, _rader, _ = _doma("station_bra")
    assert r.dom[0] == "PASS", r.dom
    r2, _r2, _ = _doma("station_utan_deklaration")
    assert r2.dom[0] == "INCONCLUSIVE", r2.dom
    assert "sekvens" in r2.dom[1]


def test_stationen_far_inte_NEVER_GRIPPED_nar_inget_verktyg_deklarerats():
    """Ett uteblivet grepp ar en overtradelse bara nar korningen pastod att
    den skulle gripa."""
    r, rader, _ = _doma("station_bra")
    assert "NEVER_GRIPPED OK" in rader
    assert r.overtradelser() == []
    # ... och plockcellen far det fortfarande.
    r2, rader2, _ = _doma("aldrig_gripen")
    assert "NEVER_GRIPPED VIOLATION" in rader2


def test_forreglingsbrottet_bar_sin_matta_overlapp_i_sekunder():
    """Ett tal, inte en flagga.

    Den andra stoppulsen ar 0,30 s lang och overlappar slappet i sex prov;
    fem mellanrum a 0,05 s ger 0,25 s per cykel, tre cykler ger 0,75 s. Det
    ar den matta varaktigheten, inte den palagda - de skiljer sig med ett
    provintervall och det ar precis vad provtagningen kostar.
    """
    r, _rader, a = _doma("station_forregling_bruten")
    post = a.harledt["station"]["forregling"][0]
    assert post["brott"] is True
    assert abs(post["overlapp_s"] - 0.75) < 1e-6, post
    assert r.dom[1].startswith("interlock:"), r.dom


def test_forreglingen_domer_inte_nar_planen_inte_bett_om_den():
    """Samma serie, samma overlapp - men ingen fraga stalld."""
    r, _rader, a = _doma("station_forregling_utan_deklaration")
    assert r.dom[0] == "PASS", r.dom
    assert a.harledt["station"]["forregling"] is None


def test_sekvensbrottet_namner_vilket_steg_och_vilket_fonster():
    r, _rader, a = _doma("station_slapper_aldrig")
    d = a.harledt["station"]["sekvens"]
    # Tva storheter (M-65 §4): stoppet SLAPPTE, men vid 3,4 s mot fonstret
    # 1,5-2,5 - ett tidsbrott. Slappsignalen kom ALDRIG - ett sekvensbrott.
    assert d["tidsbrott"], d
    assert "plc:stopp FALL" in d["tidsbrott"][0]
    assert "1.50-2.50" in d["tidsbrott"][0]
    assert d["brott"], d
    assert "plc:slapp RISE" in d["brott"][0]
    assert "1.50-2.80" in d["brott"][0]


def test_en_avhuggen_sista_cykel_ar_oprovad_och_inte_ett_brott():
    """Serien slutar mitt i en cykel. Det far inte bli ett fel - men det far
    heller inte rakas som en godkand cykel."""
    b = celler.Stationsbygge()
    for _ in range(2):
        celler._stationscykel(b)
    # halv cykel till: givaren stiger, sedan tar serien slut
    for i in range(10):
        b.steg({"givare": True, "stopp": i >= 2, "slapp": False})
    text, r, a = A.doma(b.data(), celler.stationsplan())
    d = a.harledt["station"]["sekvens"]
    assert d["avhuggna"] == 1, d
    assert d["domda"] == 2, d
    assert r.dom[0] == "PASS", r.dom


def test_en_station_som_gor_om_sitt_arbete_falls_av_RAKNINGEN_inte_ordningen():
    """Ordningen haller varje varv - det ar antalet varv som ar felet.

    MATT (M-50): en nivalasning dar en flank kravs stoppade samma produkt tre
    till fyra ganger och passerade ordningsdomen pa fem cykler av sex. Utan
    rakningen ar den felklassen osynlig for ogat.
    """
    r, _rader, a = _doma("station_gor_om_arbetet")
    assert r.dom[0] == "FAIL", r.dom
    d = a.harledt["station"]["sekvens"]
    assert d["brott"], d
    assert "gick hog 2 ganger" in d["brott"][0]
    # ... och ordningen holl: inget steg saknades.
    for cykel in d["cykler"]:
        for steg in cykel.get("steg", []):
            assert steg["status"] != "MISSING", steg


def test_rakningen_domer_inte_nar_planen_inte_bett_om_den():
    r, _rader, _ = _doma("station_forregling_utan_deklaration")
    assert r.dom[0] == "PASS", r.dom


def _rapport_mb(data, plan, modul=A):
    _text, rapport, _analys = modul.doma(data, plan)
    return rapport


ISOLERING_MB = [
    ("explosion", "BLOWUP VIOLATION",
     ("OFF_TARGET", "DROPPED", "SLIPPING", "NEVER_FORMED", "NEVER_GRIPPED VIOLATION")),
    ("aldrig_gripen", "NEVER_GRIPPED VIOLATION",
     ("OFF_TARGET", "DROPPED", "SLIPPING", "BLOWUP VIOLATION",
      "UNDERGROUND VIOLATION")),
]


@pytest.mark.parametrize("namn,egen,frammande", ISOLERING_MB,
                         ids=[x[0] for x in ISOLERING_MB])
def test_en_trasig_cell_bryter_mot_exakt_en_felklass(namn, egen, frammande):
    b, plan = celler.ALLA[namn]()
    r = _rapport_mb(b.data(), plan)
    rader = [x for _s, rr in r.sektioner for x in rr]
    assert any(egen in x for x in rader), "%s bröt inte mot sin egen klass" % namn
    smitta = [x for x in rader if any(f in x for f in frammande)]
    assert not smitta, (
        "%s bryter mot fler klasser än sin egen: %s. Då täcker grindarna för "
        "varandra: mutationsprovet visar att %s-grinden kan stängas av utan "
        "att sviten fälls." % (namn, smitta, egen.split()[0]))


def _modul_med_bytt_operator(gammal, ny):
    """Laddar oga_analys på nytt med EN operator utbytt. Mätning, inte fix.

    Raden slås upp på sitt INNEHÅLL, inte på ett radnummer: modulen växer, och
    ett prov som bygger på ett radnummer mäter fel sak efter nästa commit.
    """
    stig = os.path.join(_ROT, "ext", "vc_addon", "vc_assist", "oga_analys.py")
    rader = open(stig, encoding="utf-8").read().split("\n")
    traff = [i for i, r in enumerate(rader) if gammal in r]
    assert len(traff) == 1, ("hittade %d rader med %r; provet måste peka ut "
                             "exakt en" % (len(traff), gammal))
    i = traff[0]
    rader[i] = rader[i].replace(gammal, ny, 1)
    kalla = "\n".join(rader)
    ast.parse(kalla)
    m = types.ModuleType("_oga_analys_mut")
    m.__file__ = stig
    exec(compile(kalla, stig, "exec"), m.__dict__)
    return m


def test_placeringsgransen_ar_bestamd_av_minst_en_cell():
    """`if plac["fel_mm"] > plac["tol_mm"]` . Byts `>` mot `>=`
    ändras ingen dom i någon av bankens elva celler: gränsen är obestämd.
    """
    mut = _modul_med_bytt_operator(
        'plac["fel_mm"] > plac["tol_mm"]', 'plac["fel_mm"] >= plac["tol_mm"]')
    fore, efter = {}, {}
    for namn, bygg in sorted(celler.ALLA.items()):
        b, plan = bygg()
        fore[namn] = _rapport_mb(b.data(), plan).dom
        b, plan = bygg()
        efter[namn] = _rapport_mb(b.data(), plan, modul=mut).dom
    assert fore != efter, (
        "`>` och `>=` ger identiska domar för alla elva celler: ingen cell "
        "ligger på toleransgränsen, så gränsen har inget facit")


