# -*- coding: utf-8 -*-
"""F1-riggen: modellen som författare på M-74:s lina, ögat som talar tillbaka.

Provet är skrivet FÖRE mekanismen och var rött när det skrevs. Det provar
riggen, aldrig modellen: varje körning här går på `modellklient.Inspelad` och
en inspelad scen, så ingen token och ingen VC behövs. Det som INTE går att
prova här står i M-160:s LIMITS och i riggens egen `--torrkorning`-utskrift.

De tre trasiga fallen som bär hela filen:

  (a) en författarmodell som får verktyg MÅSTE ge körningsfel, aldrig en dom.
      Ett textsvar från en modell som fått verktyg mäter modellens oförmåga
      att använda dem, och det är en falsk mätning orsakad av adaptern
      (`claudeadapter.Adapterfel`).
  (b) en körning som slår i taket får ALDRIG räknas som löst. M-52:s tak är
      fyra varv; ett tak som räknas som ett grönt döljer en olöslig uppgift.
  (c) ögats återkoppling som är tom får inte tyst bli ett varv utan innehåll.
      `reparation.kontrollera_ordagrant` hoppar över tom utdata, så hålet
      måste stängas på ögats sida - annars går ett varv förlorat i tystnad.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "tests", "protocol"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist"),
           os.path.join(_ROT, "svc"), _ROT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import kor_F1_modellen_skriver_linan as F1                        # noqa: E402
import kor_fas8_linan as L                                        # noqa: E402
from vc_assist_svc import modellklient                            # noqa: E402
from vc_assist_svc.claudeadapter import Adapterfel                # noqa: E402
from vc_assist_svc.plc import reparation as R                     # noqa: E402


# ------------------------------------------------------------ hjälpare

def _kropp(fall):
    """En av M-74:s egna ST-kroppar för LINJE-konfigurationen."""
    return L.kroppar(fall)["LINJE"]


def _fail(orsak="interlock: ST8A_Don/Slapp och ST8B_Don/Slapp hoga samtidigt"):
    return {"gold": False, "dom": "FAIL", "orsak": orsak}


def _pass():
    return {"gold": True, "dom": "PASS", "orsak": "allt inom marginal"}


def _slinga(ogonsteg, max_varv=R.MAX_VARV):
    return F1.bygg_slinga(ogonsteg, max_varv=max_varv)


def _kor(svar, ogondomar, max_varv=R.MAX_VARV, uppgiftstext=None):
    """En hel torr slinga: inspelad författare, inspelad scen."""
    forfattare = F1.bygg_forfattare("inspelad", svar=svar)
    scen = F1.Inspelad_scen(ogondomar)
    steg = F1.Ogonsteg(scen)
    rad = F1.kor_en_slinga(forfattare, _slinga(steg, max_varv),
                           uppgiftstext or F1.UPPGIFT, uppgift="prov")
    return rad, forfattare, scen


# ------------------------------------------------- (a) verktyg = körningsfel

@pytest.mark.parametrize("transport", ["inspelad", "claude", "opencode"])
def test_fixtur_forfattare_som_far_verktyg_ger_korningsfel(transport):
    """TRASIG FIXTUR (a). Ett verktyg in måste kasta, aldrig ge ett svar.

    Gäller varje transport riggen kan välja: spärren får inte hänga på vilken
    modell operatören råkar peka ut.
    """
    f = F1.bygg_forfattare(transport, modell="prov", svar=["EN_KROPP;\n"])
    with pytest.raises(Adapterfel):
        f.svara("systemprompt", (R.Meddelande("uppgift", "skriv"),),
                (object(),))


def test_fixtur_transport_utan_repospar_avvisas():
    """Ingen ANDRA väg in till modellen som saknar de två spärrarna.

    Modellen får aldrig nå repot: bankens facit ligger där. `ClaudeCLI` har
    två lager - tom verktygslista OCH en arbetskatalog utanför repot,
    kontrollerad av `_neka_repot`. En transport som saknar dem är inte
    likvärdig, och riggen ska säga nej i stället för att mäta något annat än
    den påstår.
    """
    class UtanSparr(modellklient.Modellklient):
        namn = "utan-sparr"

        def fraga(self, prompt):
            return modellklient.Svar(text="hej", modell="utan-sparr")

    with pytest.raises(F1.Riggfel):
        F1.Forfattare(UtanSparr(), namn="utan-sparr")


def test_forfattaren_ar_en_parameter_inte_en_hardkodning():
    """Minst tre transporter ska gå att välja utan att röra koden."""
    assert set(F1.TRANSPORTER) >= {"claude", "opencode", "inspelad"}
    assert isinstance(F1.bygg_forfattare("inspelad", svar=["x"]).transport,
                      modellklient.Inspelad)
    assert isinstance(F1.bygg_forfattare("claude", modell="sonnet").transport,
                      modellklient.ClaudeCLI)
    # Opencode-transporten är den ur M-110:s körning, inte en ny kopia.
    import kor_fas9_musespark as MS
    assert isinstance(F1.bygg_forfattare("opencode", modell="x").transport,
                      MS.OpencodeCLI)


def test_okand_transport_avvisas():
    with pytest.raises(F1.Riggfel):
        F1.bygg_forfattare("gissa", modell="x")


# --------------------------------------------------- (b) taket ≠ löst

def test_fixtur_korning_som_slar_i_taket_raknas_inte_som_lost():
    """TRASIG FIXTUR (b). Fyra varv, fyra FAIL: TAK, aldrig LOST."""
    rad, _f, _s = _kor([_kropp("K1"), _kropp("K2"), _kropp("K3"), _kropp("K4")],
                       [_fail(), _fail(), _fail(), _fail()])
    assert rad["utfall"] == R.UTFALL_TAK
    assert rad["lost"] is False
    assert rad["gold"] is False
    assert rad["slog_i_taket"] is True
    assert rad["varv_till_gold"] is None
    # ...och grönt-kriteriet får inte räkna den som en av två av tre.
    dom = F1.grontkriteriet([rad, rad, rad], [], n=3)
    assert dom["guld_korningar_med_gold"] == 0
    assert dom["kriterium_guld"] is False


def test_tak_over_absoluta_taket_avvisas():
    """Ett tak som får vara godtyckligt stort är samma sak som inget tak."""
    steg = F1.Ogonsteg(F1.Inspelad_scen([]))
    with pytest.raises(R.Reparationsfel):
        F1.bygg_slinga(steg, max_varv=R.ABSOLUT_TAK + 1)


# ------------------------------------------- (c) tom ögondom ≠ ett tyst varv

def test_fixtur_tom_ogonaterkoppling_blir_inte_ett_tyst_varv():
    """TRASIG FIXTUR (c). Ögat utan ord är en OGILTIG körning, inte en dom."""
    def tyst_scen(_st_kalla):
        rad = F1.Inspelad_scen([_fail()])(_st_kalla)
        for namn in F1.OGON_CELLER:
            rad["domar"][namn]["text"] = "   \n"
        return rad

    steg = F1.Ogonsteg(tyst_scen)
    with pytest.raises(F1.Ogonfel):
        steg.doma(F1.st_kalla_av(_kropp("K3")))


def test_fixtur_ogat_utan_dom_alls_ar_ogiltigt():
    """Ingen `domar`-nyckel och ingen fälld förgrind: körningen är ogiltig."""
    def stum_scen(_st_kalla):
        return {"fall": "prov", "konfig": "LINJE", "forgrindar": {},
                "klockkvot": 1.0, "klockan_ok": True}

    with pytest.raises(F1.Ogonfel):
        F1.Ogonsteg(stum_scen).doma(F1.st_kalla_av(_kropp("HEL")))


def test_fixtur_klocka_utanfor_braketten_ar_ogiltig_inte_fallande():
    """M-74:s klockgrind. Utanför braketten mäter fönstren klockorna."""
    def skev_scen(st_kalla):
        rad = F1.Inspelad_scen([_fail()])(st_kalla)
        rad["klockkvot"] = 0.6131          # M-74:s uppmätta utslag
        rad["klockan_ok"] = False
        return rad

    with pytest.raises(F1.Ogonfel):
        F1.Ogonsteg(skev_scen).doma(F1.st_kalla_av(_kropp("K3")))


# --------------------------------------- ögats ord tillbaka in i prompten

def test_ogats_egna_ord_nar_modellen_ordagrant():
    """Kärnan i F1. Fas 9 matade tillbaka GRINDARNAS ord; F1 matar ÖGATS."""
    rad, forfattare, scen = _kor([_kropp("K3"), _kropp("HEL")],
                                 [_fail(), _pass()])
    assert rad["lost"] is True and rad["gold"] is True
    assert rad["varv_till_gold"] == 2
    # Varv 2:s prompt måste bära ögats rapporter tecken för tecken.
    andra_prompten = forfattare.transport.stalda[1]
    assert "EYES VERDICT FAIL" in andra_prompten
    for text in scen.rapporttexter[0]:
        assert text in andra_prompten, "ögats ord skrevs om på vägen"


def test_ogats_ord_gar_igenom_alla_tre_facit():
    """Station A, station B och linan är tre påståenden, inte ett (M-74)."""
    _rad, forfattare, _s = _kor([_kropp("K5"), _kropp("HEL")],
                                [_fail(), _pass()])
    prompt = forfattare.transport.stalda[1]
    for namn in F1.OGON_CELLER:
        assert namn in prompt


def test_gold_direkt_ger_ett_varv():
    """Inspelat svar 1: GOLD direkt. Räkningen ska bli ett varv, inte noll."""
    rad, _f, _s = _kor([_kropp("HEL")], [_pass()])
    assert rad["utfall"] == R.UTFALL_LOST
    assert rad["lost"] is True and rad["gold"] is True
    assert rad["varv_till_gold"] == 1
    assert rad["varv_korda"] == 1
    assert rad["ogonkorningar"] == 1


def test_samma_kropp_igen_ar_last_inte_tak():
    """Grindarna är rena funktioner av kroppen: samma kropp, samma dom."""
    rad, _f, _s = _kor([_kropp("K3"), _kropp("K3")], [_fail(), _fail()])
    assert rad["utfall"] == R.UTFALL_LAST
    assert rad["lost"] is False and rad["gold"] is False
    assert rad["slog_i_taket"] is False


def test_inspelningen_som_tar_slut_ar_ett_provfel_inte_ett_tomt_varv():
    """Fail-closed: en inspelning som tar slut får aldrig se ut som tystnad."""
    rad, _f, _s = _kor([_kropp("K3")], [_fail(), _fail()])
    assert rad["utfall"] == "KORNINGSFEL"
    assert rad["lost"] is False and rad["gold"] is False


# --------------------------------------------- kompositionsfallen seedade

def test_kompositionsfallets_seed_bar_ogats_egna_ord():
    """Modellen ska laga på ögats ord, inte på vår beskrivning av dem."""
    scen = F1.Inspelad_scen([_fail(), _pass()])
    steg = F1.Ogonsteg(scen)
    seed = F1.seeda(steg, _kropp("K4"))
    assert seed["dom"] != "PASS"
    for text in seed["rapporttexter"]:
        assert text in seed["uppgiftstext"], "ögats ord skrevs om i seeden"
    assert _kropp("K4") in seed["uppgiftstext"], "modellen ser inte programmet"


def test_kompositionsfall_som_inte_faller_raknas_aldrig_som_lagat():
    """En seed som ögat SLÄPPER igenom är en trasig fixtur, inte ett grönt."""
    scen = F1.Inspelad_scen([_pass()])
    seed = F1.seeda(F1.Ogonsteg(scen), _kropp("K1"))
    assert seed["foll"] is False
    dom = F1.grontkriteriet([], [{"fall": "K1", "lagat": False,
                                  "seeden_foll": False, "upprepning": 1}], n=1)
    assert dom["kriterium_komposition"] is False


def test_grontkriteriet_raknar_bada_och_sager_vilket_som_foll():
    """Kravet är två tal, och riggen ska säga vilket av dem som föll."""
    guld = [{"gold": True, "varv_till_gold": 2, "lost": True,
             "slog_i_taket": False, "utfall": R.UTFALL_LOST},
            {"gold": True, "varv_till_gold": 1, "lost": True,
             "slog_i_taket": False, "utfall": R.UTFALL_LOST},
            {"gold": False, "varv_till_gold": None, "lost": False,
             "slog_i_taket": True, "utfall": R.UTFALL_TAK}]
    # Tre körningar per fall, så majoritetsregeln är det som räknas.
    komp = [{"fall": f, "lagat": lagat, "seeden_foll": True, "upprepning": i}
            for f, lagat in (("K1", True), ("K2", True), ("K3", False),
                             ("K4", False), ("K5", False))
            for i in (1, 2, 3)]
    dom = F1.grontkriteriet(guld, komp, n=3)
    assert dom["kriterium_guld"] is True
    assert dom["kriterium_komposition"] is False
    assert dom["gront"] is False
    assert "komposition" in dom["foll"]
    assert "guld" not in dom["foll"]


def test_ett_torrt_gront_ar_aldrig_ett_gront():
    """En inspelad körning kan aldrig vara F1:s svar. Fail-closed."""
    guld = [{"gold": True, "varv_till_gold": 1, "lost": True,
             "slog_i_taket": False, "utfall": R.UTFALL_LOST,
             "torrkorning": True}] * 3
    komp = [{"fall": f, "lagat": True, "seeden_foll": True, "upprepning": 1,
             "torrkorning": True} for f in ("K1", "K2", "K3", "K4", "K5")]
    dom = F1.grontkriteriet(guld, komp, n=3)
    assert dom["gront"] is False
    assert dom["giltigt"] is False


# ------------------------------------------------------------- n ≥ 3

def test_n_under_tre_avvisas():
    """A2 mätte att OpenPLC-domaren inte är deterministisk vid n = 1."""
    assert F1.MIN_N >= 3
    with pytest.raises(F1.Riggfel):
        F1.kontrollera_n(1)
    F1.kontrollera_n(3)


def test_grontkriteriet_rapporterar_per_korning_inte_bara_ett_medel():
    guld = [{"gold": True, "varv_till_gold": 1, "lost": True,
             "slog_i_taket": False, "utfall": R.UTFALL_LOST}] * 3
    dom = F1.grontkriteriet(guld, [], n=3)
    assert len(dom["per_guldkorning"]) == 3


# --------------------------------------------- inkrementell JSON per varv

def test_json_flushas_efter_varje_varv(tmp_path):
    """En avbruten fullarm har tappat tio lösta uppgifter i det här projektet."""
    ut = str(tmp_path / "f1.json")
    skrivare = F1.Skrivare(ut, {"modell": "inspelad"})
    sedda = []

    def on_varv(rad):
        skrivare.varv(rad)
        sedda.append(F1.las_json(ut)["varv"])

    forfattare = F1.bygg_forfattare("inspelad",
                                    svar=[_kropp("K3"), _kropp("HEL")])
    steg = F1.Ogonsteg(F1.Inspelad_scen([_fail(), _pass()]), on_varv=on_varv)
    F1.kor_en_slinga(forfattare, _slinga(steg), F1.UPPGIFT, uppgift="prov")
    assert sedda == [1, 2], "JSON flushades inte efter varje varv"
    assert F1.las_json(ut)["varv"] == 2


def test_bankposten_finns_och_kraver_modell():
    from vc_assist_svc import bankkontrakt as BK
    d = BK.las_bankpost(os.path.join(
        _ROT, "tests", "protocol", "kor_F1_modellen_skriver_linan.py"))
    assert d is not None
    post, brister = BK.granska_post("kor_F1_modellen_skriver_linan.py", d)
    assert brister == [], brister
    assert "modell" in post.kraver and "vc" in post.kraver


def test_grind_4_hor_aldrig_i_den_billiga_kedjan():
    """Mätt i riggens första uppställning: `Stationssteg` bygger sin kandidat
    utan scenkod, så anropsvalideringen kan inte köra. Låg den i den billiga
    kedjan föll VARJE modellsvar på riggens egen brist innan ögat fick se
    något - och mätningen hade rapporterat det som modellens."""
    from vc_assist_svc.plc import stationsgrind as S
    assert S.NAMN_ANROP not in F1.BILLIGA_GRINDAR
    steg = F1.Ogonsteg(F1.Inspelad_scen([]))
    with pytest.raises(F1.Riggfel):
        F1.bygg_slinga(steg, stationsgrindar=(S.NAMN_STATISK, S.NAMN_ANROP))


def test_kompileringsgrinden_lyfts_ur_kedjan_utan_strucpp():
    """En grind som inte kan köras är aldrig ett godkännande (I3) - men den
    får inte heller fälla varje svar. Den hamnar i `ej_korda` med sitt skäl."""
    from vc_assist_svc.plc import stationsgrind as S
    steg = F1.Ogonsteg(F1.Inspelad_scen([]))
    utan = F1.bygg_slinga(steg)
    med = F1.bygg_slinga(F1.Ogonsteg(F1.Inspelad_scen([])), strucpp="/nagon/vag")
    assert S.NAMN_KOMPILERING not in utan.grindar[0].grindar
    assert S.NAMN_KOMPILERING in med.grindar[0].grindar


def test_riggen_utan_brygga_faller_med_ett_besked_som_gar_att_handla_pa(
        monkeypatch):
    """En rigg som kastar AttributeError har sagt ATT något är fel, inte VAD."""
    monkeypatch.setattr(L, "_vanta_pa_bryggan", lambda _tak: False)
    with pytest.raises(F1.Riggfel) as fel:
        F1.Bryggan().fram()
    assert "vc-test.sh" in str(fel.value) and "torrkorning" in str(fel.value)


def test_bryggan_startar_om_vc_mellan_korningar(monkeypatch):
    """M-49: godkännandekön växer med en post per varv, och en omstart ger
    varje körning samma utgångsläge - samma scen, samma simuleringstid, samma
    tomma kö. Det är avgörande när fyra varv ska jämföras."""
    startade = []
    monkeypatch.setattr(L, "_vanta_pa_bryggan", lambda _tak: True)
    monkeypatch.setattr(L, "_starta_om_vc", lambda: startade.append(1))

    class Attrapp:
        def anslut(self):
            return self

        def stang(self):
            pass

    monkeypatch.setattr(F1, "Klient", lambda **_k: Attrapp())
    b = F1.Bryggan()
    b.fram()
    b.fram()
    b.fram()
    assert b.omstarter == 2 and len(startade) == 2
    b2 = F1.Bryggan(starta_om_mellan=False)
    b2.fram()
    b2.fram()
    assert b2.omstarter == 0


def test_ogiltig_korning_raknas_varken_i_taljaren_eller_namnaren():
    """M-74:s regel: en körning vars klocka låg utanför braketten är OGILTIG,
    inte fällande. Den får inte straffa fallet - och inte bära det heller."""
    komp = []
    for f in ("K1", "K2", "K3", "K4", "K5"):
        komp.append({"fall": f, "utfall": "OGILTIG", "lagat": False,
                     "seeden_foll": False, "upprepning": 1})
        komp += [{"fall": f, "lagat": True, "seeden_foll": True,
                  "upprepning": i} for i in (2, 3)]
    dom = F1.grontkriteriet([], komp, n=3)
    assert dom["kriterium_komposition"] is True
    for r in dom["per_kompositionsfall"]:
        assert r["ogiltiga_korningar"] == 1
        assert r["giltiga_korningar"] == 2
        assert r["lagat"] is True


def test_ett_fall_med_bara_en_giltig_korning_raknas_aldrig_som_lagat():
    """En enda lyckad körning kan vara jitter (A2)."""
    komp = []
    for f in ("K1", "K2", "K3", "K4", "K5"):
        komp.append({"fall": f, "utfall": "OGILTIG", "lagat": False,
                     "seeden_foll": False, "upprepning": 1})
        komp.append({"fall": f, "utfall": "OGILTIG", "lagat": False,
                     "seeden_foll": False, "upprepning": 2})
        komp.append({"fall": f, "lagat": True, "seeden_foll": True,
                     "upprepning": 3})
    dom = F1.grontkriteriet([], komp, n=3)
    assert dom["kompositionsfall_lagade"] == 0
    assert dom["kriterium_komposition"] is False


def test_fixtur_den_riktiga_vagens_byggare_tar_armens_etikett(monkeypatch):
    """Den trasiga fixturen som saknades: byggarna på den RIKTIGA vägen.

    Riggen var grön i 30 prov och kunde ändå aldrig köra. Båda armarna anropar
    sina byggare med `etikett` (`bygg_ogonsteg(etikett)`), och torrkörningens
    två byggare tar den. Den riktiga vägens två byggare tog INGA argument, så
    `guldarmen` föll på en `TypeError` i sitt första varv - efter att
    startskriptet skrivits, innan VC rörts. Provsviten gick genom
    torrkörningens byggare och såg aldrig de andra två.

    Provet ställer frågan armarna ställer: går byggarna att anropa så som de
    faktiskt anropas?
    """
    class Argument:
        forfattare = "inspelad"
        modell = None
        strucpp = None
        runtime_include = None
        byggrot = "/tmp"
        serier = None

    class Skrivarattrapp:
        def varv(self, _rad):
            pass

    monkeypatch.setattr(F1, "bygg_forfattare",
                        lambda *_a, **_k: "forfattare")
    forf, oga = F1.riktiga_byggare(Argument(), index=None, bryggan=None,
                                   skrivare=Skrivarattrapp())
    # Exakt anropsformen ur `guldarmen`/`kompositionsarmen`.
    assert forf("guld#1") == "forfattare"
    steg = oga("K3#2")
    assert isinstance(steg, F1.Ogonsteg)
    # Etiketten bär in i byggnamnet: annars skriver körning 2 över körning 1:s
    # artefakter och frågan "vilken körning föll" går inte att ställa efteråt.
    assert steg.kor_scenen.namn == "F1_K3_2"
    assert oga("guld#1").kor_scenen.namn != steg.kor_scenen.namn


def test_armarna_anropar_sina_byggare_med_etiketten():
    """Grinden ovan mäter fel storhet om armarna slutar skicka etiketten."""
    sedda = []

    class Steg(F1.Ogonsteg):
        def __init__(self):
            F1.Ogonsteg.__init__(self, lambda _k: {})

    def bygg_ogonsteg(etikett):
        sedda.append(etikett)
        raise RuntimeError("stopp efter byggaren")

    with pytest.raises(RuntimeError):
        F1.guldarmen(lambda etikett: None, bygg_ogonsteg, 3)
    assert sedda == ["guld#1"]


# --- ögats serie via filen: den mätta transportgränsen ------------------

def _rad_utan_serie(started="2026-01-01T00:00:00"):
    """Vad `L.kor_en` returnerar när serien inte rymdes i bryggans svar."""
    return {"fall": "F1_001", "konfig": "LINJE",
            "oga_start": {"startad": started, "rate_hz": 20.0, "t0": 0.0},
            "oga_stopp": {"samples": 1400, "dur_s": 70.0, "rate_hz": 20.0,
                          "saknade": []},
            "fel": "ogats serie kom inte med i svaret (684586)",
            "klockkvot": 0.99, "klockan_ok": True,
            "celler": {"stationA": {"namn": "F1_001_LINJE", "klass": "station",
                                    "forgrindar": {}},
                       "stationB": {"namn": "F1_001_LINJE", "klass": "station",
                                    "forgrindar": {}}}}


def _skriv_ogonfil(tmp_path, started, samples=1400, dur_s=70.0, rate_hz=20.0):
    import json
    sokvag = str(tmp_path / "vc_assist_eyes.json")
    with open(sokvag, "w", encoding="utf-8") as f:
        json.dump({"v": 1, "template": "fas8_linan", "rows": [],
                   "run": {"started": started, "samples": samples,
                           "dur_s": dur_s, "rate_hz": rate_hz}}, f)
    return sokvag


class _Arg:
    ogonrate = 20.0
    varvtid = 0.3
    serier = None


def test_fixtur_en_gammal_ogonfil_far_aldrig_domas_som_farsk(tmp_path,
                                                             monkeypatch):
    """Filen ligger kvar på värdens disk över en VC-omstart.

    Serien hämtas ur filen när den inte rymdes i bryggans svar (mätt: 684 586
    byte mot taket 524 288). Den enda nya felklassen den vägen bär är en
    GAMMAL fil - och en gammal serie dömd som färsk hade varit ett facit ur
    en annan körning. `run.started` måste vara exakt det ögonblick den här
    körningens `eyes_start` svarade.
    """
    monkeypatch.setattr(F1.L, "_domar", lambda *_a, **_k: {})
    gammal = _skriv_ogonfil(tmp_path, "2025-12-31T23:59:59")
    with pytest.raises(F1.Ogonfel) as fel:
        F1.serien_ur_ogonfilen(_rad_utan_serie(), _Arg(), sokvag=gammal)
    assert "aldrig domas som om den vore farsk" in str(fel.value)


@pytest.mark.parametrize("nyckel,varde", [
    ("samples", 1399), ("dur_s", 69.0), ("rate_hz", 19.0)])
def test_fixtur_ogonfil_med_annan_form_ar_ogiltig(tmp_path, monkeypatch,
                                                  nyckel, varde):
    """Rätt tidpunkt räcker inte: antal prov, längd och takt ska också stämma."""
    monkeypatch.setattr(F1.L, "_domar", lambda *_a, **_k: {})
    kwargs = {nyckel: varde}
    fil = _skriv_ogonfil(tmp_path, "2026-01-01T00:00:00", **kwargs)
    with pytest.raises(F1.Ogonfel):
        F1.serien_ur_ogonfilen(_rad_utan_serie(), _Arg(), sokvag=fil)


def test_fixtur_ingen_ogonfil_alls_ar_ogiltig_inte_tyst(tmp_path):
    """En körning utan serie är OGILTIG, aldrig ett tyst godkännande."""
    with pytest.raises(F1.Ogonfel) as fel:
        F1.serien_ur_ogonfilen(_rad_utan_serie(), _Arg(),
                               sokvag=str(tmp_path / "finns_inte.json"))
    assert "OGILTIG" in str(fel.value)


def test_serien_ur_filen_ger_samma_form_som_svarsvagen(tmp_path, monkeypatch):
    """Samma serie, samma domare - bara en annan kanal in.

    Cellerna ska bära ögats text och `linan` ska bli klassen `linje`, precis
    som `kor_en` bygger dem när serien rymdes i svaret. Annars dömer
    guldgrinden en linjecell som om den vore en station.
    """
    monkeypatch.setattr(F1.L, "_domar", lambda *_a, **_k: dict(
        (n, {"text": "EYES VERDICT PASS %s" % n, "dom": ["PASS", "ok"],
             "harledt": {}}) for n in F1.OGON_CELLER))
    fil = _skriv_ogonfil(tmp_path, "2026-01-01T00:00:00")
    rad = F1.serien_ur_ogonfilen(_rad_utan_serie(), _Arg(), sokvag=fil)
    assert "fel" not in rad
    assert rad["serien_ur_fil"]["sokvag"] == fil
    assert set(rad["celler"]) == set(F1.OGON_CELLER)
    assert rad["celler"]["linan"]["klass"] == "linje"
    assert rad["celler"]["stationA"]["klass"] == "station"
    for namn in F1.OGON_CELLER:
        assert rad["celler"][namn]["eyes"] == "EYES VERDICT PASS %s" % namn


def test_serien_ur_filen_ror_inte_en_korning_som_redan_har_domar(tmp_path):
    """Rymdes serien i svaret ska filen aldrig läsas - då vore filen facit."""
    rad = {"domar": {"linan": {"text": "x"}}, "fel": None}
    assert F1.serien_ur_ogonfilen(dict(rad), _Arg()) == rad


def test_ogats_upplosning_ar_m73s_egen_inte_fas8s_argparse_standard():
    """M-73 skriver ut vad ögat FAKTISKT såg: 80,0 s, 800 prov, 10,00 Hz.

    Fas 8:s argparse-standard är 70 s / 25 s / 20 Hz, och M-73 och M-74 kördes
    inte där - M-74:s arton körningar har "45 s uppvärmning och 80 s mätning".
    Skillnaden bär mätningen: M-73:s fjärde fynd är att ett prov vars tolerans
    är snävare än scenuppdateringens eftersläpning mäter eftersläpningen, och
    facits fönster är räknade vid 0,1 s provintervall. En rigg som säger
    "M-74:s rigg, oförändrad" och kör vid en annan upplösning dömer facit vid
    en upplösning facit aldrig kalibrerats mot.

    Talen ligger i namngivna konstanter för att de ska gå att pröva: ett tal
    som bara finns som ett `default=` i en parser inne i `main` går inte att
    fråga om utan att köra hela riggen.
    """
    assert (F1.MATNING_S, F1.UPPVARMNING_S, F1.OGONRATE_HZ) == (80.0, 45.0, 10.0)
    kalla = open(F1.__file__.replace(".pyc", ".py"), encoding="utf-8").read()
    for flagga, konstant in (("--sekunder", "MATNING_S"),
                             ("--uppvarmning", "UPPVARMNING_S"),
                             ("--ogonrate", "OGONRATE_HZ")):
        assert 'p.add_argument("%s", type=float, default=%s)' % (
            flagga, konstant) in kalla, flagga


# --- transportfelet: ett avbrott är inte ett modellsvar -----------------

class _Flakig(modellklient.Modellklient):
    """En transport som faller n gånger och sedan svarar. Bär båda spärrarna."""

    namn = "flakig"

    def __init__(self, fel, svar="a_stopp := TRUE;"):
        self._fel = list(fel)
        self._svar = svar
        self.anrop = 0
        self.verktygslarm = 0          # SPARR_VERKTYG

    def fraga(self, prompt):
        modellklient._neka_repot                    # SPARR_KATALOG
        self.anrop += 1
        if self._fel:
            raise modellklient.Modellfel(self._fel.pop(0))
        return modellklient.Svar(text=self._svar, modell="flakig",
                                 kostnad_usd=0.0)


def test_transportfel_far_ett_omforsok_och_raknas():
    """Mätt i den första riktiga F1-körningen: tre av fem anrop föll på
    transporten - `opencode gav slutkod 1` med tom stderr och `opencode gav
    ingen text tillbaka` - medan samma prompt gav fullt svar de andra två
    gångerna. Varje sådant fel kostade en VC-omstart, en uppladdning och 80 s
    scenmätning och gav ingenting att döma."""
    t = _Flakig(["opencode gav slutkod 1: ",
                 "opencode gav ingen text tillbaka"])
    f = F1.Forfattare(t, namn="flakig")
    svar = f.svara("system", [{"roll": "anvandare", "text": "skriv"}], ())
    assert svar.text.strip() == "a_stopp := TRUE;"
    assert t.anrop == 3
    assert [x["forsok"] for x in f.transportfel] == [1, 2]


def test_transportfel_som_inte_slutar_blir_korningsfel_inte_ett_tyst_varv():
    """Taket på omförsöken är också en gräns: den fjärde gången är ett fel."""
    t = _Flakig(["opencode gav slutkod 1: "] * 5)
    f = F1.Forfattare(t, namn="flakig")
    with pytest.raises(modellklient.Modellfel):
        f.svara("system", [{"roll": "anvandare", "text": "skriv"}], ())
    assert t.anrop == F1.TRANSPORT_FORSOK


def test_fixtur_verktygsdomen_far_ALDRIG_ett_omforsok():
    """Den viktigaste av de tre.

    `opencode anvande verktyg` är en fail-closed DOM om att svaret kan ha läst
    facit - inte ett avbrott. Ett omförsök där hade varit att fråga om tills
    modellen råkar svara som vi vill, och mätningens giltighet står på att
    modellen inte sett `kor_fas8_linan.py`.
    """
    t = _Flakig(["opencode anvande verktyg (tool_use) — svaret kan ha last "
                 "facit och raknas inte"])
    f = F1.Forfattare(t, namn="flakig")
    with pytest.raises(modellklient.Modellfel):
        f.svara("system", [{"roll": "anvandare", "text": "skriv"}], ())
    assert t.anrop == 1                     # ETT anrop, inget omförsök
    assert f.transportfel == []


def test_en_okand_felklass_provas_aldrig_om():
    """Listan är en vitlista: en ny felklass måste skrivas dit av en människa."""
    t = _Flakig(["opencode sa nagot ingen har sett forut"])
    f = F1.Forfattare(t, namn="flakig")
    with pytest.raises(modellklient.Modellfel):
        f.svara("system", [{"roll": "anvandare", "text": "skriv"}], ())
    assert t.anrop == 1
