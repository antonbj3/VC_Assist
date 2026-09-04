# -*- coding: utf-8 -*-
"""L1: ögats härledningar, prövade var för sig utan att en dom fälls.

En härledning som bara går att pröva genom den dom den ska mata är inte
prövad. Därför ligger räkningarna i `oga_harledning.py` och prövas här på
konstruerade serier — samma skäl som ögat självt går att pröva utan VC.

Varje ny grind prövas i BÅDA riktningarna. En domare som fäller allt klarar
varje fällningsprov och är ändå värdelös.
"""
import math
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "tests", "enhet")))

import celler                     # noqa: E402
import oga_harledning as H        # noqa: E402
import test_troskelharkomst as L  # noqa: E402

Q0 = [0.0, 0.0, 0.0, 1.0]


def _pose(x, y, z, q=None):
    return {"p": [x, y, z], "q": list(q or Q0)}


# ---- tröskellintern, samma regel som över resten av trädet ---------------
#
# `test_troskelharkomst.py` har en parametriserad lista över de moduler vars
# skuld ska vara NOLL, och `oga_harledning.py` står inte i den. Regeln
# implementeras INTE en gång till här — den lånas, och tillämpas på den här
# modulen. En tröskel som ingen linter tittar på är precis den svaghet
# 41_ogat_kontrakt.md pekar ut hos källprojektet.

MODUL = "oga_harledning.py"


def _mina_trosklar():
    return [(rel, nr, namn, kom) for rel, nr, namn, kom in L.ALLA
            if os.path.basename(rel) == MODUL]


def test_det_finns_trosklar_att_prova_i_harledningen():
    assert len(_mina_trosklar()) > 10, "hittade för få tröskelkonstanter i %s" % MODUL


def test_varje_troskel_i_harledningen_bar_harkomst():
    """M-nummer eller specdokument — men aldrig ingenting."""
    utan = ["%s:%d %s %r" % (rel, nr, namn, kom)
            for rel, nr, namn, kom in _mina_trosklar() if not L._har_harkomst(kom)]
    assert not utan, "trösklar utan härkomst:\n  " + "\n  ".join(utan)


def test_varje_matningshanvisning_i_harledningen_gar_att_sla_upp():
    """Formen `M-\\d+` är inte härkomst. Numret måste finnas eller vara
    reserverat — annars är hänvisningen en formel."""
    finns = L.matningar_som_finns() | L.reserverade()
    doda = []
    for rel, nr, namn, kom in _mina_trosklar():
        for r in L._MNUMMER.findall(kom):
            if L._mnr(r) not in finns:
                doda.append("%s:%d %s -> %s" % (rel, nr, namn, L._mnr(r)))
    assert not doda, "\n  ".join([""] + doda)


def test_varje_specreferens_i_harledningen_pekar_pa_ett_dokument_som_finns():
    doda = []
    for rel, nr, namn, kom in _mina_trosklar():
        for d in L._SPECREF.findall(kom):
            if not L._specdok_finns(d):
                doda.append("%s:%d %s -> %s" % (rel, nr, namn, d))
    assert not doda, "\n  ".join([""] + doda)


def test_ett_reserverat_nummer_anvands_bara_som_PRELIMINART_i_harledningen():
    res = L.reserverade() - L.matningar_som_finns()
    fel = []
    for rel, nr, namn, kom in _mina_trosklar():
        for r in L._MNUMMER.findall(kom):
            if L._mnr(r) in res and "PRELIMIN" not in kom.upper():
                fel.append("%s:%d %s -> %s utan PRELIMINAR" % (rel, nr, namn, L._mnr(r)))
    assert not fel, "\n  ".join([""] + fel)


# ---- scenens delta-lagring: skrivare och läsare i samma fil -------------

def test_delta_lagringen_ger_tillbaka_exakt_det_som_skrevs():
    """Kodning och avkodning är EN mekanism. Går de isär tappas rörelse."""
    poser = [{"a": _pose(0, 0, 0), "b": _pose(1, 0, 0)},
             {"a": _pose(0, 0, 0), "b": _pose(1.5, 0, 0)},
             {"a": _pose(0, 0, 0), "b": _pose(1.5, 0, 0)},
             {"a": _pose(0.25, 0, 0), "b": _pose(2.0, 0, 0)}]
    rader, forra = [], {}
    for i, p in enumerate(poser):
        delta, forra = H.koda_scen(p, forra, i == 0)
        rad = {"t": i * 0.05, "scene": delta, "scenlast": True}
        if i == 0:
            rad["scenfull"] = True
        rader.append(rad)
    assert rader[2]["scene"] == {}, "en orörd rad ska inte lagra något alls"
    tillbaka = H.expandera(rader)
    for i, p in enumerate(poser):
        assert tillbaka[i]["scene"] == dict(
            (n, H.kvantisera(v)) for n, v in p.items())


def test_kvantiseringen_ligger_langt_under_varje_troskel_som_domer():
    """Kvantiseringen är den enda skillnaden mellan lagrat och läst. Den ska
    vara mätbart mindre än den minsta rörelse ögat bryr sig om."""
    halva_steget_mm = 0.5 * (10.0 ** -H.SCEN_DECIMALER) * 1000.0
    assert halva_steget_mm < H.ROR_SIG_MM / 100.0
    assert halva_steget_mm < H.STILLA_TOTAL_MM / 100.0
    p = _pose(1.0 / 3.0, 0, 0)
    assert abs(H.kvantisera(p)["p"][0] - 1.0 / 3.0) <= 0.5 * 10.0 ** -H.SCEN_DECIMALER


def test_en_olast_rad_ar_inte_samma_sak_som_en_orord():
    """Den viktigaste skillnaden i hela fullscenprovtagningen.

    En utglesad serie får aldrig läsas som "allt stod still" — då blir
    utglesningen en tyst källa till falska godkännanden.
    """
    rader = [{"t": 0.0, "scene": {"a": _pose(0, 0, 0)}, "scenlast": True,
              "scenfull": True},
             {"t": 0.05},                                     # aldrig avläst
             {"t": 0.10, "scene": {}, "scenlast": True}]      # avläst, orörd
    ut = H.expandera(rader)
    assert ut[1]["scenlast"] is False
    assert ut[2]["scenlast"] is True
    assert ut[1]["scene"] == ut[2]["scene"], "senast kända pose ska bäras vidare"
    serie = H.objektserier(ut)["a"]
    assert [x[3] for x in serie] == [True, False, True]


def test_ett_objekt_som_forsvinner_bars_inte_vidare_i_evighet():
    rader = [{"t": 0.0, "scene": {"a": _pose(0, 0, 0), "b": _pose(1, 0, 0)},
              "scenlast": True, "scenfull": True},
             {"t": 0.05, "scene": {}, "scenlast": True, "scen_borta": ["b"]}]
    ut = H.expandera(rader)
    assert "b" not in ut[1]["scene"]


# ---- rörelseprofil ------------------------------------------------------

def _serie(punkter, last=True):
    return [(i * 0.05, tuple(p), (0.0, 0.0, 0.0, 1.0), last)
            for i, p in enumerate(punkter)]


def test_ett_stillastaende_objekt_ar_stilla_och_ett_rorligt_ar_det_inte():
    stilla = H.rorelseprofil(_serie([[0, 0, 0]] * 20))
    rorligt = H.rorelseprofil(_serie([[i * 0.01, 0, 0] for i in range(20)]))
    assert stilla["stilla"] is True and stilla["vaglangd_mm"] == 0.0
    assert rorligt["stilla"] is False
    assert abs(rorligt["vaglangd_mm"] - 190.0) < 1e-6
    assert abs(rorligt["maxfart_ms"] - 0.2) < 1e-9


def test_ett_aldrig_avlast_objekt_ar_OKANT_inte_stillastaende():
    """Tre lägen, inte två. Fail-closed kräver att det tredje finns."""
    profil = H.rorelseprofil(_serie([[0, 0, 0]] * 20, last=False))
    assert profil["stilla"] is None
    assert profil["olast_andel"] == 1.0


def test_riktningsbyten_raknas():
    fram = [[i * 0.01, 0, 0] for i in range(10)]
    tillbaka = [[0.09 - i * 0.01, 0, 0] for i in range(1, 10)]
    assert H.rorelseprofil(_serie(fram + tillbaka))["riktningsbyten"] == 1


def test_forandringar_sager_NAR_ett_objekt_bytte_fart_riktning_och_hojd():
    """Tre skilda storheter, tre skilda händelser. En sammanslagen "ändring"
    hade varit ett tal som bär tre saker."""
    punkter = ([[i * 0.005, 0, 1.0] for i in range(10)]          # långsamt
               + [[0.045 + i * 0.05, 0, 1.0] for i in range(1, 10)]   # tio ggr fortare
               + [[0.495 - i * 0.05, 0, 1.0] for i in range(1, 10)]   # tillbaka
               + [[0.045, 0, 1.0 - i * 0.05] for i in range(1, 10)])  # nedåt
    h = H.forandringar(_serie(punkter))
    sorter = set(x["vad"] for x in h)
    assert sorter == {"fart", "riktning", "hojd"}, sorter
    fart = [x for x in h if x["vad"] == "fart"][0]
    assert fart["till_mm_s"] > fart["fran_mm_s"] * 2


def test_ett_stillastaende_objekt_bytte_ingenting():
    """Den andra riktningen: brus kring noll är ingen förändring."""
    assert H.forandringar(_serie([[0, 0, 1.0]] * 20)) == []


def test_en_jamn_rorelse_ger_ingen_fartandring():
    """Utan det här provet skulle varje rörelse räknas som en förändring."""
    h = H.forandringar(_serie([[i * 0.02, 0, 1.0] for i in range(20)]))
    assert [x for x in h if x["vad"] == "fart"] == []


# ---- scenöversikt -------------------------------------------------------

def _scenrader(banor, n=40):
    rader = []
    for i in range(n):
        scene = dict((namn, _pose(*fn(i))) for namn, fn in banor.items())
        rader.append({"t": round(i * 0.05, 4), "scene": scene, "scenlast": True})
    return rader


def test_samtidighet_ser_vilka_objekt_som_ror_sig_i_samma_fonster():
    rader = _scenrader({
        "a": lambda i: (i * 0.02, 0, 0),                      # rör sig hela tiden
        "b": lambda i: (0.0 if i < 20 else (i - 20) * 0.02, 0, 0),
        "c": lambda i: (0, 0, 0)})                            # står still
    o = H.Scenoversikt(rader)
    assert o.rorliga() == ["a", "b"] and o.stilla() == ["c"]
    par = dict(((a, b), n) for a, b, _s, n in o.samtidiga())
    assert ("a", "b") in par, "a och b rör sig samtidigt efter t=1,0 s"
    assert par[("a", "b")] > 5


def test_sist_i_rorelse_fore_pekar_ut_ratt_objekt():
    """Frågan 'vad gjorde det?' börjar med 'vad rörde sig sist?'."""
    rader = _scenrader({
        "tidig": lambda i: (i * 0.02 if i < 10 else 0.18, 0, 0),
        "sen": lambda i: (0.0 if i < 25 else (i - 25) * 0.02, 0, 0)})
    o = H.Scenoversikt(rader)
    assert o.sist_i_rorelse_fore(0.4)[0] == "tidig"
    assert o.sist_i_rorelse_fore(1.6)[0] == "sen"


def test_narheten_kapas_hogljutt_och_aldrig_tyst(monkeypatch):
    monkeypatch.setattr(H, "NARHET_MAX_PAR", 2)
    banor = dict((namn, (lambda i, k=k: (i * 0.01 * (k + 1), 0, 0)))
                 for k, namn in enumerate("abcd"))
    n = H.Scenoversikt(_scenrader(banor)).narhet()
    assert n["kapat"] is True and n["provade_par"] == 2


def test_narheten_ar_centrumavstand_och_bar_sitt_eget_namn():
    """MINDIST i SAFETY är ytavstånd ur VC:s detektor. Det här är avstånd
    mellan origo. Två storheter, två namn — aldrig samma rad."""
    rader = _scenrader({"a": lambda i: (0, 0, 0),
                        "b": lambda i: (1.0 - i * 0.02, 0, 0)}, n=40)
    n = H.Scenoversikt(rader).narhet()
    assert n["par"][0]["a"] == "a" and n["par"][0]["b"] == "b"
    assert abs(n["par"][0]["min_mm"] - 220.0) < 1e-6


def test_oombedd_rorelse_skiljer_ingen_fraga_stalld_fran_inget_fel():
    rader = _scenrader({"okand": lambda i: (i * 0.02, 0, 0),
                        "vantad": lambda i: (0, i * 0.02, 0)})
    utan_plan = H.Scenoversikt(rader)
    assert utan_plan.oombedd_rorelse() is None, "ingen fråga ställd"
    med_plan = H.Scenoversikt(rader, forvantat_rorliga=["vantad"])
    fallda = [d["objekt"] for d in med_plan.oombedd_rorelse()]
    assert fallda == ["okand"]
    allt_tillatet = H.Scenoversikt(rader, forvantat_rorliga=["vantad", "okand"])
    assert allt_tillatet.oombedd_rorelse() == []


def test_orort_trots_signal_kraver_en_karta_mellan_signal_och_ting():
    rader = _scenrader({"don": lambda i: (0, 0, 0)})
    o = H.Scenoversikt(rader)
    flanker = [{"signal": "start", "flank": "RISE", "t": 0.5}]
    assert o.orort_trots_signal(flanker, None) == []
    ut = o.orort_trots_signal(flanker, {"start": "don"})
    assert ut and ut[0]["objekt"] == "don"


def test_ledtid_per_produkt_mater_produkten_inte_stationen():
    rader = _scenrader({"p1": lambda i: (i * 0.02 if i < 20 else 0.38, 0, 0),
                        "p2": lambda i: (0.0 if i < 10 else (i - 10) * 0.02, 0, 0)})
    ledtider = H.Scenoversikt(rader).ledtider()
    assert abs(ledtider["p1"]["ledtid_s"] - 0.95) < 1e-6
    assert ledtider["p2"]["ledtid_s"] > ledtider["p1"]["ledtid_s"]


# ---- robotleder ---------------------------------------------------------

def _ledrader(varden, mal=None, robot="r"):
    rader = []
    for i, v in enumerate(varden):
        rad = {"t": round(i * 0.05, 4), "joints": {robot: list(v)}}
        if mal is not None:
            rad["joints_mal"] = {robot: list(mal[i])}
        rader.append(rad)
    return rader


def test_ledgrans_skiljer_natt_fran_passerad():
    """Att nå en gräns är inte ett fel. Att gå förbi den är det."""
    natt = H.Ledanalys(_ledrader([[i * 8.5] for i in range(21)]),
                       granser={"r": [[-170.0, 170.0]]},
                       typer={"r": ["deg"]}).analysera()["r"]
    passerad = H.Ledanalys(_ledrader([[i * 9.5] for i in range(21)]),
                           granser={"r": [[-170.0, 170.0]]},
                           typer={"r": ["deg"]}).analysera()["r"]
    assert natt["granser_nadda"] and natt["granser_nadda"][0]["over"] is False
    assert passerad["granser_nadda"][0]["over"] is True


def test_en_led_utan_kand_typ_far_ingen_enhet_och_domes_inte_pa_grader():
    """En ledfart som inte vet sin enhet bär två storheter i ett tal."""
    h = H.Ledanalys(_ledrader([[i * 2.0] for i in range(10)])).analysera()["r"]
    assert h["enhetslosa_leder"] == [0]
    assert h["led"][0]["enhet"] is None


def test_stopporsaken_ar_GRANS_nar_en_led_star_pa_sin_grans():
    varden = [[min(200.0, i * 20.0)] for i in range(10)] + [[200.0]] * 10
    h = H.Ledanalys(_ledrader(varden), granser={"r": [[-170.0, 170.0]]},
                    typer={"r": ["deg"]}).analysera()["r"]
    assert h["stopp"], "ett stopp ska hittas"
    assert h["stopp"][0]["orsak"] == "GRANS" and h["stopp"][0]["led"] == 0
    assert "170" in h["stopp"][0]["bevis"]


def test_stopporsaken_ar_den_led_som_slutade_sist_nar_ingen_star_pa_grans():
    """Den leden bestämde rörelsetiden. Det är det svar en operatör vill ha."""
    varden = []
    for i in range(20):
        varden.append([min(20.0, i * 4.0), min(60.0, i * 4.0)])
    varden += [[20.0, 60.0]] * 5
    h = H.Ledanalys(_ledrader(varden), granser={"r": [[-170.0, 170.0]] * 2},
                    typer={"r": ["deg", "deg"]}).analysera()["r"]
    assert h["stopp"][0]["orsak"] == "BEGRANSANDE"
    assert h["stopp"][0]["led"] == 1, "led 1 rörde sig längst"


def test_singularitet_domes_inte_utan_en_utpekad_verktygspunkt():
    h = H.Ledanalys(_ledrader([[i * 5.0] for i in range(20)])).analysera()["r"]
    assert h["singularitet"][0]["obestambar"]


def test_singularitet_skiljer_urartning_fran_ren_omorientering():
    """Kravet på verktygets VRIDNING är det enda som skiljer dem åt. Utan det
    är singularitetsgrinden bara en fartgrind med ett finare namn."""
    n = 20
    varden = [[i * 5.0, -i * 5.0] for i in range(n)]

    def kor(q_fn):
        serie = [(round(i * 0.05, 4), (0.0, 0.0, 1.0), q_fn(i), True)
                 for i in range(n)]
        return H.Ledanalys(_ledrader(varden), typer={"r": ["deg", "deg"]},
                           tcp={"r": "tcp"}, serier={"tcp": serie}).analysera()["r"]

    still = kor(lambda i: (0.0, 0.0, 0.0, 1.0))
    vrider = kor(lambda i: (0.0, 0.0, math.sin(math.radians(20.0 * i) / 2),
                            math.cos(math.radians(20.0 * i) / 2)))
    assert still["singularitet"] and not still["singularitet"][0].get("obestambar")
    assert vrider["singularitet"] == [], "en omorientering är ingen urartning"


def test_kommenderat_mot_uppnatt_ser_bade_att_det_gick_och_att_det_inte_gick():
    varden = [[i * 1.0] for i in range(20)]
    natt = H.Ledanalys(_ledrader(varden, mal=varden),
                       typer={"r": ["deg"]}).analysera()["r"]
    missat = H.Ledanalys(_ledrader(varden, mal=[[v[0] + 12.0] for v in varden]),
                         typer={"r": ["deg"]}).analysera()["r"]
    assert natt["foljfel"][0]["nadde_malet"] is True
    assert missat["foljfel"][0]["nadde_malet"] is False
    assert abs(missat["foljfel"][0]["kvarstaende_fel"] - 12.0) < 1e-9


def test_for_fa_ledprov_ar_obestambart_inte_gront():
    h = H.Ledanalys(_ledrader([[0.0]])).analysera()["r"]
    assert h["obestambar"]


# ---- stationer ----------------------------------------------------------

def _statrader(tillstand, cur, n=60, station="s1"):
    return [{"t": round(i * 0.05, 4),
             "stat": {station: {"in": 1, "out": 1, "cur": cur,
                                "state": tillstand}}}
            for i in range(n)]


def test_svalt_och_blockering_skiljs_at_och_ar_inte_samma_stillestand():
    """Båda ser likadana ut i ett medelvärde: stationen producerar inte.
    Skillnaden är VARFÖR, och den är hela poängen med att mäta tillståndet."""
    svulten = H.stationslage(_statrader("IDLE", 0))["s1"]
    blockerad = H.stationslage(_statrader("BLOCKED", 1))["s1"]
    upptagen = H.stationslage(_statrader("BUSY", 1))["s1"]
    assert svulten["svalt_s"] > 2.0 and svulten["blockerad_s"] == 0.0
    assert blockerad["blockerad_s"] > 2.0 and blockerad["svalt_s"] == 0.0
    assert upptagen["svalt_s"] == 0.0 and upptagen["blockerad_s"] == 0.0


def test_flaskhalsen_pekas_ut_med_sin_orsak():
    rader = []
    for i in range(60):
        rader.append({"t": round(i * 0.05, 4),
                      "stat": {"snabb": {"in": 1, "out": 1, "cur": 1, "state": "BUSY"},
                               "trog": {"in": 1, "out": 0, "cur": 1,
                                        "state": "BLOCKED"}}})
    h = H.stationslage(rader)
    assert h["_flaskhals"]["station"] == "trog"
    assert h["_flaskhals"]["orsak"] == "blockerad"


def test_en_station_utan_flaskhals_pekas_inte_ut():
    assert H.stationslage(_statrader("BUSY", 1))["_flaskhals"] is None


def test_for_fa_stationsprov_ar_obestambart():
    assert H.stationslage(_statrader("IDLE", 0, n=1))["s1"]["obestambar"]


# ---- PLC på samma tidsaxel ----------------------------------------------

def _plcrader(plc_hog_vid, sig_hog_vid, n=40):
    return [{"t": round(i * 0.05, 4),
             "plc": {"Start": i >= plc_hog_vid},
             "sig": {"do_start": i >= sig_hog_vid}} for i in range(n)]


def test_plctaggar_bar_ett_prefix_sa_de_aldrig_forvaxlas_med_vc_signaler():
    flanker = H.plcflanker(_plcrader(10, 14))
    assert flanker[0]["signal"] == "plc:Start"
    assert " " not in flanker[0]["signal"], "måste rymmas i grammatikens <signal>"


def test_fasforhallandet_sager_vem_som_kom_forst_och_hur_langt_fore():
    """Ett tidsfel blir läsbart först när de två ligger på samma tidsaxel."""
    rader = _plcrader(10, 14)
    flanker = H.plcflanker(rader) + [{"signal": "do_start", "flank": "RISE",
                                      "t": 0.70}]
    fas = H.fasforhallande(flanker, [("Start", "do_start")])
    assert fas[0]["forst"] == "plc"
    assert abs(fas[0]["dt_ms"] - 200.0) < 1e-6


def test_fasforhallandet_gissar_inte_nar_en_flank_saknas():
    fas = H.fasforhallande(H.plcflanker(_plcrader(10, 99)),
                           [("Start", "do_start")])
    assert fas[0]["obestambar"]


# ---- utslungad ----------------------------------------------------------

def _kast(vx, vz, z0=1.0, n=10):
    punkter = []
    for k in range(n):
        t = k * 0.05
        punkter.append([vx * t, 0.0, z0 + vz * t - 0.5 * 9.81 * t * t])
    return _serie(punkter)


def test_ett_kast_fangas_och_ett_tapp_gor_det_inte():
    """Ett tapp är också fritt fall och passerar också 3 m/s på vägen ner.
    Det som skiljer dem är den VÅGRÄTA farten — mätt på cellen `tappad`, som
    en tidigare version av grinden fällde med fel orsak."""
    kast = H.utslungad(_kast(5.0, 2.0))
    tapp = H.utslungad(_kast(0.0, 0.0))
    assert kast and abs(kast["vagrat_ms"] - 5.0) < 1e-6
    assert abs(kast["z_acc_ms2"] + 9.81) < 0.01
    assert tapp is None


def test_en_vagrat_snabb_men_ofysisk_rorelse_ar_inget_kast():
    """Utan fallkurvan är det inte ett kast utan bara fart — och farten har
    redan en egen grind i BLOWUP."""
    punkter = [[k * 0.3, 0.0, 1.0] for k in range(10)]
    assert H.utslungad(_serie(punkter)) is None


# ---- berättelsen --------------------------------------------------------

def test_berattelsen_svarar_pa_vad_som_pagar_utan_att_falla_en_dom():
    """I1: domen är auktoritativ. Redogörelsen får aldrig låta som en dom."""
    rader = _scenrader({"robot": lambda i: (i * 0.02, 0, 0),
                        "bord": lambda i: (2, 0, 0)})
    text = " ".join(H.berattelse(H.Scenoversikt(rader),
                                 {"narhet": {"par": []}},
                                 {"dur_s": 2.0, "samples": 40, "rate_hz": 20.0}))
    assert "robot" in text and "bord" in text
    for forbjudet in ("PASS", "FAIL", "godkand", "godkänd", "underkänd"):
        assert forbjudet not in text, "berättelsen får inte fälla en dom"


def test_berattelsen_sager_ut_att_nagot_aldrig_lastes_av():
    rader = _scenrader({"a": lambda i: (0, 0, 0)})
    for r in rader:
        r["scenlast"] = False
    text = " ".join(H.berattelse(H.Scenoversikt(rader)))
    assert "uttala sig om" in text


def test_vad_pagar_svarar_for_en_tidpunkt():
    rader = _scenrader({"a": lambda i: (i * 0.02 if i < 20 else 0.38, 0, 0),
                        "b": lambda i: (3, 0, 0)})
    o = H.Scenoversikt(rader)
    tidigt = " ".join(H.vad_pagar(o, 0.5))
    sent = " ".join(H.vad_pagar(o, 1.8))
    assert "i rorelse: a" in tidigt
    assert "star still" in sent and "a" in sent


def test_glesningen_star_i_berattelsen_och_doljs_aldrig():
    rader = _scenrader({"a": lambda i: (0, 0, 0)})
    text = " ".join(H.berattelse(
        H.Scenoversikt(rader),
        {"gles": {"faktor": 8, "handelser": [{"t": 1.5}]}}))
    assert "glesade ut" in text and "var 8:e" in text


@pytest.mark.parametrize("namn", sorted(celler.ALLA))
def test_varje_cell_gar_att_bygga_en_scenoversikt_av(namn):
    """En härledning som kraschar på en cell kan dölja rött."""
    b, _plan = celler.ALLA[namn]()
    o = H.Scenoversikt(H.expandera(b.data()["rows"]), ["del", "gripper"])
    o.samtidiga()
    o.narhet()
    o.ledtider()
    assert isinstance(H.berattelse(o), list)
