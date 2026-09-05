# -*- coding: utf-8 -*-
"""L1: förloppet ut ur processen, och de två körvägar som nu för det.

`M-64` byggde förloppsytan och lämnade hålet med flit i sin §9:

    Ingenting driver ytan än. Den går att driva, och det är en annan sak än
    att den drivs ... Ska en panel i en annan process läsa den behövs en
    serialisering som inte finns.

Det här provet stänger båda halvorna, och det bär fasens egen trasiga fixtur i
en ny skepnad.

## Den nya faran, och varför den är ny

Fas 17:s grind säger: *ett fällt läge får aldrig se ut som ett arbetande.*
`granska` fäller varje RENDERARE som bryter mot det. Den kan däremot inte
fälla en LÄSARE som bryter mot det, och skillnaden är hela den här filen.

En läsare som återskapar förloppet med BILDENS EGEN skrivtid som "nu" bygger
ett protokoll som självt säger ARBETAR. Texten är då korrekt mot protokollet,
alla elva Y-regler håller, och en körning vars skrivare dog för en timme sedan
visas som levande. Det är samma odödliga körning M-64 mätte på hjärtslaget —
en annan mekanism, samma falska grön.

Därför räknar `granska_spegling` om filens ålder SJÄLV, ur den råa bilden och
läsarens klocka, precis som `granska` räknar om tystnaden själv i Y9.
"""
import io
import json
import os
import re
import sys
import time

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.forlopp import (ARBETAR, EJ_STARTAT, FALLET,  # noqa: E402
                                   FORLOPPSVERSION, FRAMTID, Forlopp,
                                   Forloppsfel, KLART, OBESTAMT, OLASBAR,
                                   RACKVIDDEN, RUBRIK_SPEGLING,
                                   RUBRIK_VET_INTE, SEKTION_SAKNAS,
                                   SPEGELREGLER, STILLASTAENDE, Spegel, TYST,
                                   granska, granska_spegling,
                                   granska_spegling_eller_kasta, las_spegling,
                                   rendera, rendera_spegling, spegla)
from vc_assist_svc.forlopp import spegel as S                     # noqa: E402
from vc_assist_svc.plan import graf as G                          # noqa: E402
from vc_assist_svc.plan.korning import (FALLEN, KORD,             # noqa: E402
                                        Korare, Post, Protokoll)
from vc_assist_svc.plan.steg import Steg                          # noqa: E402


class Klocka(object):
    """En klocka som står still tills provet flyttar den."""

    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += float(s)
        return self.t


GRINDORD = "\n".join([
    "STATION ST010, deklarationsmatchning",
    "rad 12: [ODEKLARERAD/F4] taggen ST010_KLAR finns inte i signalkartan",
    "2 anmarkningar",
])


# --------------------------------------------------------------- byggare

def arbetande(k=None, spegelfil=None):
    k = k or Klocka()
    f = Forlopp("o-17", "Bygg en plockstation.", klocka=k)
    if spegelfil is not None:
        spegla(f, spegelfil)
    f.plan(["ladda_band", "ladda_robot", "generera_st"])
    k.tick(0.2)
    f.steg_borjar("ladda_band")
    k.tick(0.3)
    f.steg_klart("ladda_band", 12.0)
    k.tick(0.2)
    f.steg_borjar("ladda_robot")
    return f, k


def fallen(k=None, spegelfil=None):
    f, k = arbetande(k, spegelfil)
    k.tick(0.4)
    f.grind("deklarationsmatchning", False, GRINDORD)
    k.tick(0.1)
    f.fall("kopplaren gav upp efter 3 raka fel; sista: IOError: OPC UA "
           "svarar inte")
    return f, k


def klar(k=None, spegelfil=None):
    f, k = arbetande(k, spegelfil)
    k.tick(0.3)
    f.steg_klart("ladda_robot", 9.0)
    k.tick(0.1)
    f.steg_borjar("generera_st")
    k.tick(0.2)
    f.steg_klart("generera_st", 5.0)
    k.tick(0.2)
    f.svar("Stationen är byggd.")
    return f, k


def skriv_bild(sokvag, f, klocka):
    """Skriver en bild för hand, med en klocka provet styr."""
    gammal, f.klocka = f.klocka, klocka
    try:
        Spegel(str(sokvag)).skriv(f)
    finally:
        f.klocka = gammal
    return str(sokvag)


# ===================================================================
#  1. Ett förlopp går att läsa från en annan process
# ===================================================================

def test_ett_forlopp_gar_att_serialiseras_och_lasas_tillbaka(tmp_path):
    """Motbevisets tredje fråga, som ett prov.

    Så länge ett Forlopp bara finns i minnet hos den som kör varvet är
    "panelen" och "körningen" samma process.
    """
    f, k = fallen()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=k)
    assert not o.obestamd
    assert o.forlopp.lage == FALLET
    assert o.forlopp.order_id == f.order_id
    assert len(o.forlopp.handelser) == len(f.handelser)
    assert [s.namn for s in o.forlopp.steg] == [s.namn for s in f.steg]


def test_nagon_annans_ord_overlever_speglingen_tecken_for_tecken(tmp_path):
    """Y4 en våning ned: en omskrivning på vägen ut mäter till slut sig själv."""
    f, k = fallen()
    o = las_spegling(skriv_bild(tmp_path / "f.json", f, k), klocka=k)
    assert GRINDORD in rendera_spegling(o)
    assert GRINDORD in o.forlopp.ordagranna()


def test_speglingen_av_ett_fallet_forlopp_passerar_bada_grindarna(tmp_path):
    f, k = fallen()
    o = las_spegling(skriv_bild(tmp_path / "f.json", f, k), klocka=k)
    text = rendera_spegling(o)
    assert granska(o.forlopp, text).ok
    dom = granska_spegling(o, text)
    assert dom.ok, dom.text()


@pytest.mark.parametrize("byggare", [arbetande, fallen, klar])
def test_standardspeglingen_passerar_grinden(tmp_path, byggare):
    f, k = byggare()
    o = las_spegling(skriv_bild(tmp_path / "f.json", f, k), klocka=k)
    granska_spegling_eller_kasta(o)


@pytest.mark.parametrize("byggare", [arbetande, fallen, klar])
def test_ingen_egen_rad_ar_bredare_an_ett_terminalfonster(tmp_path, byggare):
    """Samma gräns som förloppsytans. Någon annans ord räknas inte, och inte
    heller sökvägen: båda är givna utifrån."""
    f, k = byggare()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=k)
    text = rendera_spegling(o)
    for ord_ in list(o.forlopp.ordagranna()) + [fil]:
        text = text.replace(ord_, "")
    breda = [(len(r), r) for r in text.splitlines() if len(r) > 100]
    assert not breda, "\n".join("%d tecken: %s" % b for b in breda)


# ===================================================================
#  2. Läsaren är fail-closed: en trasig bild är OBESTÄMD, aldrig tom
# ===================================================================

def test_en_avhuggen_fil_ar_obestamd_aldrig_ett_tomt_forlopp(tmp_path):
    """En halv fil får inte se ut som en körning som inte börjat.

    EJ STARTAT är ett lugnt besked. Ett läsfel som ser lugnt ut är den falska
    grönen i sin renaste form.
    """
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    hel = io.open(fil, encoding="utf-8").read()
    io.open(fil, "w", encoding="utf-8").write(hel[:len(hel) // 2])

    o = las_spegling(fil, klocka=k)
    assert o.obestamd
    assert o.lage == OBESTAMT
    text = rendera_spegling(o)
    assert text.splitlines()[0] == "LÄGE: %s" % OBESTAMT
    assert EJ_STARTAT not in text
    assert granska_spegling(o, text).ok


def test_en_fil_som_inte_finns_ar_obestamd_med_skalet_ordagrant(tmp_path):
    o = las_spegling(str(tmp_path / "finns_inte.json"), klocka=Klocka())
    assert o.obestamd and o.fel
    text = rendera_spegling(o)
    assert o.fel in text
    assert OLASBAR in text
    assert granska_spegling(o, text).ok


def test_en_obestamd_spegling_bar_hela_rackvidden(tmp_path):
    """`50_grindar.md` gäller varje körning, också en ingen kan läsa."""
    o = las_spegling(str(tmp_path / "borta.json"), klocka=Klocka())
    text = rendera_spegling(o)
    assert RUBRIK_VET_INTE in text
    for _nyckel, namn, _skal in RACKVIDDEN:
        assert namn in text


def test_en_bild_med_okand_version_avvisas(tmp_path):
    f, k = arbetande()
    data = f.till_json()
    data["v"] = FORLOPPSVERSION + 1
    fil = str(tmp_path / "f.json")
    io.open(fil, "w", encoding="utf-8").write(json.dumps(data))
    o = las_spegling(fil, klocka=k)
    assert o.obestamd and "version" in o.fel


def test_en_bild_med_fel_nycklar_avvisas(tmp_path):
    f, k = arbetande()
    data = f.till_json()
    del data["skrivet"]
    fil = str(tmp_path / "f.json")
    io.open(fil, "w", encoding="utf-8").write(json.dumps(data))
    o = las_spegling(fil, klocka=k)
    assert o.obestamd and "skrivet" in o.fel


def test_TRASIG_en_bild_som_tappat_rackvidden_avvisas(tmp_path):
    """Trasig fixtur: en bild där räckvidden strukits.

    Grinden Y5 kräver räckviddens poster UR PROTOKOLLET. Ett protokoll utan
    dem kräver alltså ingenting, och visningen hade blivit kortare än
    körningen var utan att någon grind märkte det. Läsaren vägrar i stället.
    """
    f, k = arbetande()
    data = f.till_json()
    data["ovissheter"] = [o for o in data["ovissheter"]
                          if o["namn"] != "sensorstuds"]
    fil = str(tmp_path / "f.json")
    io.open(fil, "w", encoding="utf-8").write(json.dumps(data))
    o = las_spegling(fil, klocka=k)
    assert o.obestamd, "en bild utan sensorstuds lästes som hel"
    assert "sensorstuds" in o.fel


def test_en_okand_stegstatus_i_bilden_avvisas(tmp_path):
    f, k = arbetande()
    data = f.till_json()
    data["steg"][0]["status"] = "nastan_klart"
    fil = str(tmp_path / "f.json")
    io.open(fil, "w", encoding="utf-8").write(json.dumps(data))
    o = las_spegling(fil, klocka=k)
    assert o.obestamd and "nastan_klart" in o.fel


def test_en_okand_handelsesort_i_bilden_avvisas(tmp_path):
    f, k = arbetande()
    data = f.till_json()
    data["handelser"][0]["sort"] = "ALLT_GICK_BRA"
    fil = str(tmp_path / "f.json")
    io.open(fil, "w", encoding="utf-8").write(json.dumps(data))
    o = las_spegling(fil, klocka=k)
    assert o.obestamd and "ALLT_GICK_BRA" in o.fel


# ===================================================================
#  3. FASENS TRASIGA FIXTUR: en läsare som fryser klockan
# ===================================================================

def lasare_som_fryser_klockan(fil):
    """TRASIG LÄSARE: återskapar förloppet med BILDENS egen skrivtid som nu.

    Det ser ut som omsorg — då mäts allt mot samma klocka och läsarens
    tidszon spelar ingen roll. Följden är att tystnaden alltid blir noll:
    varje avläsning säger ARBETAR, för alltid, oavsett hur länge sedan
    skrivaren dog.
    """
    data = json.loads(io.open(fil, encoding="utf-8").read())
    frusen = lambda: data["skrivet"]                       # noqa: E731
    f = Forlopp.fran_json(data, klocka=frusen)
    return S.Ogonblick(sokvag=fil, nu=time.time(), forlopp=f,
                       skrivet=f.skrivet)


def test_TRASIG_en_lasare_som_fryser_klockan_falls(tmp_path):
    """Fasens grind, i speglingens skepnad: ett dött läge ser arbetande ut.

    Mätt nedan: med frusen klocka säger 60 av 60 avläsningar ARBETAR, i en
    körning där skrivaren dog före den första. Det är M-64:s hjärtslag igen,
    med en annan mekanism.
    """
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)

    arbetande_avlasningar = 0
    for minut in range(1, 61):
        o = lasare_som_fryser_klockan(fil)
        # Läsaren fryser klockan, så protokollet SJÄLVT säger ARBETAR ...
        if o.forlopp.lage == ARBETAR:
            arbetande_avlasningar += 1
        # ... och den vanliga förloppsgrinden ser ingenting fel: texten är
        # korrekt mot ett protokoll som är fel.
        text = rendera(o.forlopp)
        assert granska(o.forlopp, text).ok

        # Speglingens grind räknar om åldern ur den råa bilden och fäller.
        senare = S.Ogonblick(sokvag=fil, nu=k.t + minut * 60.0,
                             forlopp=o.forlopp, skrivet=o.skrivet)
        dom = granska_spegling(senare, text + "\n\n" +
                               "\n".join(S._speglingsrader(senare)))
        assert not dom.ok, "en bild %d min gammal passerade som ARBETAR" % minut
        assert "S2" in dom.brutna

    assert arbetande_avlasningar == 60, (
        "den frusna läsaren sa ARBETAR i %d av 60 avläsningar"
        % arbetande_avlasningar)


def test_samma_bild_med_lasarens_klocka_blir_TYST(tmp_path):
    """Den ärliga vägen, mätt mot samma bild.

    Skillnaden mot provet ovan är EN sak: vilken klocka åldern räknas mot.
    """
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    senare = Klocka(k.t + 3600.0)
    o = las_spegling(fil, klocka=senare)
    assert o.forlopp.lage == TYST
    text = rendera_spegling(o)
    assert text.splitlines()[0] == "LÄGE: %s" % TYST
    assert granska_spegling(o, text).ok


class Vandande(object):
    """En klocka som vander over tystnadstaket vid det N:te anropet.

    Den finns for att flytta EN sekundgrans genom hela avlasningen, en
    position i taget. Ett enda valt N hade provat en punkt; svepet provar
    varje stalle grinden och renderaren kan hamna pa var sin sida om.
    """

    def __init__(self, fore, efter, vid):
        self.fore = float(fore)
        self.efter = float(efter)
        self.vid = int(vid)
        self.anrop = 0

    def __call__(self):
        self.anrop += 1
        return self.fore if self.anrop < self.vid else self.efter


def test_en_avlasning_ar_ett_ogonblick_var_grans_an_hamnar(tmp_path):
    """Renderaren och grinden maste se samma tillstand.

    Gar klockan MELLAN `rendera_spegling` och `granska_spegling` kan tystnaden
    passera taket dar emellan: ytan skriver ARBETAR och grinden sager TYST, och
    anvandaren far en grindanmarkning pa en yta som var korrekt nar den skrevs.
    En falsk anmarkning pa ytan ar samma sorts tillitsskada som en falsk gron.

    Provet sveper grensen over avlasningens tio forsta klockanrop. Klockan
    fryses vid LASARENS `nu`, sa alla tio ska halla; `test_bilden_aldras_anda`
    nedan haller isar det fran filens egen skrivtid, som ar en helt annan sak.
    """
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    fore = k.t + f.tystnadstak - 0.5
    efter = k.t + f.tystnadstak + 0.5
    for vid in range(1, 11):
        o = las_spegling(fil, klocka=Vandande(fore, efter, vid))
        text = rendera_spegling(o)
        dom = granska_spegling(o, text)
        assert dom.ok, "grensen vid anrop %d: %s" % (vid, dom.text())


def test_bilden_aldras_anda_mellan_tva_avlasningar(tmp_path):
    """Frysningen galler INOM en avlasning, aldrig mellan tva.

    Vore den mellan avlasningar vore den `lasare_som_fryser_klockan`.
    """
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    forst = las_spegling(fil, klocka=Klocka(k.t))
    sedan = las_spegling(fil, klocka=Klocka(k.t + 3600.0))
    assert forst.forlopp.lage == ARBETAR
    assert sedan.forlopp.lage == TYST
    assert sedan.alder > forst.alder


def test_S2_en_text_som_pastar_ARBETAR_over_en_gammal_fil_falls(tmp_path):
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t + 900.0))
    ljug = rendera_spegling(o).replace("LÄGE: %s" % TYST,
                                       "LÄGE: %s" % ARBETAR, 1)
    dom = granska_spegling(o, ljug)
    assert "S2" in dom.brutna


# ===================================================================
#  4. Tre lägen som bara finns när förloppet lämnat processen
# ===================================================================

def test_en_stillastaende_fil_sager_att_vi_inte_vet_om_skrivaren_lever(tmp_path):
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t + 120.0))
    text = rendera_spegling(o)
    assert STILLASTAENDE in text
    assert "skrivarens liv" in text
    assert granska_spegling(o, text).ok


def test_TRASIG_en_lasare_som_utelamnar_skrivarens_liv_falls(tmp_path):
    """TRASIG: visningen är kosmetiskt lugn — den säger TYST men inte att
    ingen vet om körningen lever."""
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t + 120.0))
    text = rendera_spegling(o)
    lugn = "\n".join(r for r in text.splitlines()
                     if STILLASTAENDE not in r)
    dom = granska_spegling(o, lugn)
    assert "S4" in dom.brutna


def test_en_avslutad_korning_star_still_utan_att_bli_ovisss(tmp_path):
    """En INSPELAD körning som gick klart är klar också i morgon.

    En fil som står still är helt i sin ordning när körningen är slut: det
    finns inget mer att skriva. Skulle läsaren kalla den ovis vore varje
    sparad körning obestämd, och då säger ordet ingenting.
    """
    f, k = klar()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t + 86400.0))
    assert o.forlopp.lage == KLART
    text = rendera_spegling(o)
    assert STILLASTAENDE not in text
    assert "24 timmar" not in text          # ingen påhittad formulering
    assert granska_spegling(o, text).ok


def test_ett_fallet_forlopp_ur_en_gammal_fil_ar_fortfarande_fallet(tmp_path):
    f, k = fallen()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t + 86400.0))
    text = rendera_spegling(o)
    assert text.splitlines()[0] == "LÄGE: %s" % FALLET
    assert granska_spegling(o, text).ok


def test_en_fil_skriven_i_framtiden_ar_obestamd_aldrig_arbetande(tmp_path):
    """En klocka som gått bakåt gör annars varje död körning evig."""
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t - 3600.0))
    assert o.forlopp.lage == OBESTAMT
    text = rendera_spegling(o)
    assert text.splitlines()[0] == "LÄGE: %s" % OBESTAMT
    assert FRAMTID in text
    assert granska_spegling(o, text).ok


def test_TRASIG_en_lasare_som_klipper_negativ_alder_till_noll_falls(tmp_path):
    """TRASIG: `alder = max(0, nu - skrivet)`.

    Den ser ut som en rimlig sanering av ett omöjligt tal. Följden är att en
    fil från framtiden ser ut som en fil skriven just nu, alltså som en helt
    färsk och arbetande körning.
    """
    f, k = arbetande()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=Klocka(k.t - 3600.0))
    klippt = rendera_spegling(o)
    klippt = klippt.replace("LÄGE: %s" % OBESTAMT, "LÄGE: %s" % ARBETAR, 1)
    klippt = "\n".join(r for r in klippt.splitlines() if FRAMTID not in r)
    dom = granska_spegling(o, klippt)
    assert "S5" in dom.brutna


def test_S3_en_visning_utan_speglingsblock_falls(tmp_path):
    """En inspelad körning som inte säger när den spelades in ser ut som nuet."""
    f, k = klar()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=k)
    utan = rendera(o.forlopp)
    dom = granska_spegling(o, utan)
    assert "S3" in dom.brutna


def test_S1_ett_lasfel_som_visas_som_ej_startat_falls(tmp_path):
    """TRASIG: en läsare som ger ett tomt förlopp när filen är borta."""
    o = las_spegling(str(tmp_path / "borta.json"), klocka=Klocka())
    tomt = rendera(Forlopp("o-1", "x", klocka=Klocka())) + \
        "\n\n" + "\n".join(S._speglingsrader(o))
    dom = granska_spegling(o, tomt)
    assert "S1" in dom.brutna


def test_TRASIG_en_kosmetiskt_lugn_visning_av_ett_fall_falls(tmp_path):
    """TRASIG: fallets skäl mjukas upp till en vänlig mening.

    Ingen enskild rad är osann. Det som försvinner är beskedet om VAD som
    hände, och det är hela skillnaden mellan en visning och en lugnande
    signal.
    """
    f, k = fallen()
    fil = skriv_bild(tmp_path / "f.json", f, k)
    o = las_spegling(fil, klocka=k)
    lugn = rendera_spegling(o)
    lugn = lugn.replace(f.fallskal(), "Ett problem uppstod. Vi försöker igen.")
    dom = granska_spegling(o, lugn)
    assert not dom.ok
    assert "Y3" in dom.brutna or "Y4" in dom.brutna


def test_alla_speglingsregler_har_minst_en_trasig_fixtur():
    """Samma prov som förloppsytans: en regel utan en trasig fixtur är oprövad.

    Provet läser sin EGEN källa. En regel som ingen fixtur nämner har aldrig
    fällt något, och en grind som aldrig fällt är en bön (S2 i
    `docs/spec/96_ingen_skuld.md`).
    """
    kalla = io.open(__file__, encoding="utf-8").read()
    utan = []
    for regel in SPEGELREGLER:
        # Formen är EXAKT. En lösare sökning hade räknat en regel som nämns i
        # ett funktionsnamn, och då mäter provet sina egna rubriker.
        if '"%s" in dom.brutna' % regel not in kalla:
            utan.append(regel)
    assert not utan, ("dessa regler har ingen trasig fixtur: %s"
                      % ", ".join(utan))


# ===================================================================
#  5. Skrivningen: efter varje händelse, aldrig bara på slutet
# ===================================================================

def test_spegeln_skriver_efter_varje_handelse(tmp_path):
    fil = str(tmp_path / "f.json")
    f, _k = arbetande(spegelfil=fil)
    # en skrivning vid kopplingen plus en per händelse
    assert f.spegel.skrivningar == 1 + len(f.handelser)


def test_speglingen_gar_att_lasa_MELLAN_tva_steg(tmp_path):
    """Fasens grönt: ytan går att läsa medan körningen pågår.

    Läsningen sker bara mot FILEN — inget objekt delas — så det är samma väg
    en panel i en annan process skulle gå.
    """
    fil = str(tmp_path / "f.json")
    k = Klocka()
    f = Forlopp("o-1", "prov", klocka=k)
    spegla(f, fil)
    f.plan(["a", "b", "c"])

    sedda = []
    for namn in ("a", "b", "c"):
        k.tick(0.5)
        f.steg_borjar(namn)
        o = las_spegling(fil, klocka=k)
        text = rendera_spegling(o)
        granska_spegling_eller_kasta(o, text)
        sedda.append(text)
        k.tick(0.5)
        f.steg_klart(namn)

    assert len(set(sedda)) == 3, "de tre avläsningarna var inte olika"
    assert "b" in sedda[1] and "pågår sedan" in sedda[1]
    assert "1 av 3 klara" in sedda[1]


def test_TRASIG_en_spegel_som_bara_skriver_pa_slutet(tmp_path):
    """TRASIG SKRIVARE: skriver först när körningen är avslutad.

    Det är precis de fem terminala rapportytorna M-64 räknade, byggda en gång
    till. Mätt: filen visar aldrig ARBETAR under körningen.
    """
    class Slutspegel(Spegel):
        def skriv(self, f):
            if f.lage in S.AVSLUTADE:
                Spegel.skriv(self, f)

    fil = str(tmp_path / "f.json")
    k = Klocka()
    f = Forlopp("o-1", "prov", klocka=k)
    f.spegla(Slutspegel(fil))
    f.plan(["a", "b"])

    arbetande_avlasningar = 0
    for namn in ("a", "b"):
        k.tick(0.5)
        f.steg_borjar(namn)
        if las_spegling(fil, klocka=k).lage == ARBETAR:
            arbetande_avlasningar += 1
        k.tick(0.5)
        f.steg_klart(namn)
    assert arbetande_avlasningar == 0, (
        "slutspegeln råkade visa ARBETAR; fixturen mäter inte det den ska")

    # och det som gick att läsa under tiden var ett obestämt läge, inte ett
    # lugnt EJ STARTAT.
    o = las_spegling(fil, klocka=k)
    assert o.obestamd

    f.svar("klart")
    assert las_spegling(fil, klocka=k).lage == KLART


def test_skrivningen_ar_atomisk_ingen_halv_fil_blir_kvar(tmp_path):
    """En läsare ser den gamla bilden eller den nya, aldrig en halv."""
    fil = str(tmp_path / "f.json")
    f, k = arbetande(spegelfil=fil)
    kvar = [n for n in os.listdir(str(tmp_path)) if n != "f.json"]
    assert not kvar, "temporärfiler blev kvar: %s" % kvar
    assert not las_spegling(fil, klocka=k).obestamd


# ===================================================================
#  6. FÖRARNA: de två som äger en körnings tidslinje
# ===================================================================

class _Resultat(object):
    def __init__(self, resultat):
        self.resultat = resultat
        self.koad = False
        self.qid = None


class Lasandeutforare(object):
    """En utförare som läser förloppsFILEN inifrån ett verktygsanrop.

    Det är den skarpaste formen av fasens fråga: kan någon som INTE äger
    objektet se vad som pågår, medan det pågår? Utföraren delar ingenting med
    föraren utom en sökväg.
    """

    def __init__(self, fil, klocka):
        self.fil = fil
        self.klocka = klocka
        self.sett = []

    def utfor(self, namn, argument=None):
        self.klocka.tick(0.4)
        o = las_spegling(self.fil, klocka=self.klocka)
        text = rendera_spegling(o)
        granska_spegling_eller_kasta(o, text)
        self.sett.append(text)
        return _Resultat({"components": [], "antal": 0, "avkortad": False})


def _plan_med(steg):
    from vc_assist_svc.plan.byggplan import Byggplan
    from vc_assist_svc.plan.spec import DetaljeradSpec, Grundbegaran
    from vc_assist_svc.plan.verifiering import Krav, Verifieringskrav
    begaran = Grundbegaran("prov", "en provplan", "test")
    krav = Verifieringskrav("PASS", [Krav("SAFETY", "COLLISION none")])
    spec = DetaljeradSpec("prov", begaran, verifiering=krav)
    return Byggplan("prov", spec, G.Uppgiftsgraf(steg))


def _v(id, beroenden=()):
    return Steg.verktygssteg(id, "list_components", {}, "provsteg %s" % id,
                             beroenden=beroenden)


def test_planens_korare_for_forloppet_MEDAN_planen_kor(tmp_path):
    """Motbevisets andra fråga: den som äger körningens tidslinje för protokoll.

    Läsningarna sker inne i verktygsanropen, alltså före `kor()` returnerat.
    """
    fil = str(tmp_path / "f.json")
    k = Klocka()
    f = Forlopp("o-plan", "kör provplanen", klocka=k)
    spegla(f, fil)
    utf = Lasandeutforare(fil, k)

    prot = Korare(utf).kor(_plan_med([_v("a"), _v("b", ("a",)),
                                      _v("c", ("b",))]), forlopp=f)
    assert prot.rakning()[KORD] == 3
    assert len(utf.sett) == 3

    # Vid det andra anropet ska steg a redan stå som klart och b som pågående.
    assert "1 av 3 klara" in utf.sett[1]
    assert "a" in utf.sett[1] and "pågår sedan" in utf.sett[1]
    # och vid det tredje har två steg fått sitt utfall.
    assert "2 av 3 klara" in utf.sett[2]


def test_ett_fallet_plansteg_nar_anvandaren_med_sina_egna_ord(tmp_path):
    """Vilken grind som fällde, och varför — ordagrant."""
    class Fallande(object):
        def utfor(self, namn, argument=None):
            from vc_assist_svc.verktyg import Verktygsfel
            raise Verktygsfel("E_EXEC: VC nekade anropet")

    k = Klocka()
    f = Forlopp("o-plan", "kör provplanen", klocka=k)
    prot = Korare(Fallande()).kor(_plan_med([_v("a"), _v("b", ("a",))]),
                                  forlopp=f)
    assert prot.status("a") == FALLEN
    text = rendera(f)
    assert "E_EXEC: VC nekade anropet" in text
    assert granska(f, text).ok


def test_ett_aterupptaget_steg_star_som_ej_kort_i_den_har_korningen(tmp_path):
    """Ett steg som bars över är klart, men det kördes inte HÄR.

    Räknas det bara som klart ser körningen ut att ha prövat något den inte
    prövat, och det är samma tysta nedgradering som ett hoppat steg utan skäl.
    """
    plan = _plan_med([_v("a"), _v("b", ("a",))])
    tidigare = Protokoll(plan.id, [Post("a", KORD, "kordes direkt",
                                        {"antal": 0})])
    k = Klocka()
    f = Forlopp("o-plan", "kör igen", klocka=k)
    Korare(Lasandeutforare_utan_fil(k)).kor(plan, tidigare=tidigare,
                                            forlopp=f)
    text = rendera(f)
    assert "aterupptagen ur ett tidigare protokoll" in text
    assert granska(f, text).ok


class Lasandeutforare_utan_fil(object):
    def __init__(self, klocka):
        self.klocka = klocka

    def utfor(self, namn, argument=None):
        self.klocka.tick(0.2)
        return _Resultat({"antal": 0})


def test_en_okand_planstatus_avvisas_ocksa_i_forararvagen():
    """En post som föll igenom alla grenar hade blivit osynlig i visningen."""
    from vc_assist_svc.forlopp.kallor import fran_planpost
    f = Forlopp("o-1", "x", klocka=Klocka())
    with pytest.raises(Forloppsfel):
        fran_planpost(f, Post("a", "nastan", "inget skäl"))


# ===================================================================
#  7. RIKTIG INSPELAD DATA: bankens egna ögonrapporter
# ===================================================================

def _inspelade_ogonrapporter():
    """Varje EYES-rapport som ligger sparad i bank/uppgifter/."""
    import glob
    ut = []
    for stig in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                              "*.json"))):
        data = json.loads(io.open(stig, encoding="utf-8").read())

        def gar(o):
            if isinstance(o, dict):
                for v in o.values():
                    gar(v)
            elif isinstance(o, list):
                for v in o:
                    gar(v)
            elif isinstance(o, str) and o.startswith("EYES v"):
                ut.append((os.path.basename(stig), o))
        gar(data)
    return ut


def test_bankens_inspelade_ogonrapporter_finns():
    assert len(_inspelade_ogonrapporter()) >= 9


def test_varje_inspelad_ogonrapport_utan_LIMITS_sags_sakna_den():
    """LIMITS ska vara lika synligt som utfallet.

    MÄTT 2026-09-05: 9 av 9 inspelade ögonrapporter i banken är v1 och bär
    ingen `SECTION LIMITS`. Guldgrinden kräver sektionen sedan M-65, alltså
    är ingen av dem guld — och visningen måste säga varför, inte tiga om det
    och visa domen som en dom.
    """
    utan_besked = []
    for namn, rapport in _inspelade_ogonrapporter():
        if "SECTION LIMITS" in rapport:
            continue
        f = Forlopp("o-bank", namn, klocka=Klocka())
        f.plan(["kor cellen"])
        f.steg_klart("kor cellen")
        f.dom(rapport)
        text = rendera(f)
        if SEKTION_SAKNAS % "LIMITS" not in text:
            utan_besked.append(namn)
        assert rapport in text, "%s: ögats ord skrevs om" % namn
        assert granska(f, text).ok
    assert not utan_besked, (
        "dessa inspelade domar visades som domar trots att LIMITS aldrig "
        "kört: %s" % ", ".join(utan_besked))


def test_en_inspelad_fallen_ogondom_ur_banken_hela_vagen_genom_speglingen(
        tmp_path):
    """En riktig, inspelad FAIL ur banken, hela vägen ut till användaren.

    `L-90` är en verklig körning från 2026-09-04 med en verklig kollision.
    Ingenting i den här filen räknar om ögats mått; rapporten går ordagrant
    ut, och det enda visningen lägger till är att LIMITS aldrig kört.
    """
    stig = os.path.join(_ROT, "bank", "uppgifter", "L-90.json")
    data = json.loads(io.open(stig, encoding="utf-8").read())
    rapport = data["broken"]["artefakt"]
    assert rapport.startswith("EYES v")

    fil = str(tmp_path / "f.json")
    k = Klocka()
    f = Forlopp("L-90", "avlaggshojd fran pallens overkant", klocka=k)
    spegla(f, fil)
    f.plan(["bygg cellen", "kor ogat"])
    k.tick(1.0)
    f.steg_klart("bygg cellen")
    k.tick(1.0)
    f.steg_klart("kor ogat")
    k.tick(0.5)
    f.dom(rapport)
    k.tick(0.1)
    f.fall("ogat sa FAIL; cellen ar inte guld")

    o = las_spegling(fil, klocka=k)
    text = rendera_spegling(o)
    granska_spegling_eller_kasta(o, text)
    assert text.splitlines()[0] == "LÄGE: %s" % FALLET
    assert "COLLISION kolli_7 x pallkarm t=5.240s" in text
    assert SEKTION_SAKNAS % "LIMITS" in text
    assert RUBRIK_SPEGLING in text
