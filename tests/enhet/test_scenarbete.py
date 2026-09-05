# -*- coding: utf-8 -*-
"""L0/L1 för fritextvägen till en BEFINTLIG scen. Körs utan VC och utan nätverk.

Ordningen i filen är ordningen bygget hade: **spärren först, tolken sen.**

TRE TRASIGA FIXTURER, och de står överst därför att de är skälet till att
resten finns (S2 i docs/spec/96_ingen_skuld.md). Var och en är ett
modellsvar som gör precis det som inte får hända:

  (a) en diagnosfråga som råkar ändra scenen
  (b) en tvetydig ändring som utförs ändå
  (c) en ändring utan belägg som utförs

Ingen av dem är ett konstruerat undantag. Alla tre är vad en språkmodell
gör när ingen grind står i vägen, och alla tre ska fällas MEKANISKT — inte
av att tolken är oförmögen att gissa.

VARFÖR TOLKEN INTE LÄNGRE ÄR EN ORDLISTA. `plan/forfining.py:ORDBOK` är 32
hårdkodade svenska ord. Den kan inte hitta på — men den kan inte heller läsa
"conveyor". Garantin "inget tyst val" flyttas därför från tolkens oförmåga
till grinden: modellen får läsa meningen, men varje värde den producerar
måste bära en härledning eller vara märkt som en fråga. Provet
`test_engelska_och_svenska_gar_genom_samma_grind` visar att grinden inte bär
något språk alls.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

from vc_assist_svc import verktyg as V                     # noqa: E402
from vc_assist_svc.harness import kanal as Kn              # noqa: E402
from vc_assist_svc.harness import loop as L                # noqa: E402
from vc_assist_svc.harness import modell as Mo             # noqa: E402
from vc_assist_svc.scenarbete import avsikt as Av          # noqa: E402
from vc_assist_svc.scenarbete import diagnos as Di         # noqa: E402
from vc_assist_svc.scenarbete import sparr as Sp           # noqa: E402


# ---- fixturvärld ---------------------------------------------------------

# En scen som är LÄST, inte påhittad. Tre gripdon, och det är hela poängen
# med fixtur (b): "byt det där gripdonet" har tre kandidater.
SCEN = Sp.Scenlage(
    komponenter=(("ST210_gripdon", "gripdon"),
                 ("ST220_gripdon", "gripdon"),
                 ("ST230_gripdon", "gripdon"),
                 ("station_3", "station"),
                 ("station_2", "station")),
    kalla="list_components")

# En ögonrapport med en station som svälter. Raderna följer ögats egen
# grammatik (ext/vc_addon/vc_assist/oga_kontrakt.py) och är därför läsbara
# av kontraktet självt - inte av en parser skriven här.
RAPPORT = "\n".join([
    "EYES v2",
    "TEMPLATE lina_3st",
    "RUN 2026-09-05T12:00:00 DUR 60.0s SAMPLES 600 RATE 10.0Hz",
    "SECTION MOTION",
    "GRIP FORMED t=1.000s dist=2.0mm",
    "CARRY RIGID rot=0.5deg span=3.000s",
    "PLACE IN_TARGET err=1.0mm z=0.9m",
    "SECTION TIMING",
    "EDGE start RISE t=0.100s",
    "SECTION SEQUENCE",
    "CYCLES judged=12 broken=0 late=0 truncated=0 req=12",
    "SECTION THROUGHPUT",
    "STATION station_2 in=12 out=4 avg=9.000s min=8.000s max=11.000s",
    "STATION station_3 in=4 out=4 avg=2.000s min=2.000s max=2.000s",
    "STARVED station_3 41.500s req=5.000s EXCEEDED",
    "BLOCKED station_3 0.000s req=5.000s OK",
    "BOTTLENECK station_2 blocked 68.0%",
    "SECTION SAFETY",
    "COLLISION none",
    "SECTION SCENE",
    "OBJECTS total=9 moving=4 still=5 unread=0",
    "SECTION HONESTY",
    "TELEPORT_TRANSFER OK",
    "SECTION LIMITS",
    "RESOLUTION sample=100.0ms read=unknown join=50.0ms RUN phase=unknown",
] + ["NOT_SIMULATED %s" % n for n in
     ("sensor_bounce", "actuator_dynamics", "fieldbus_jitter",
      "degraded_modes", "real_hardware")]
  + ["EYES VERDICT FAIL station_3 starved 41.500s over req 5.000s"])


# ==========================================================================
#  TRASIGA FIXTURER — skrivna före mekanismen, sedda röda före den byggdes
# ==========================================================================

def test_a_en_diagnos_som_rakar_andra_scenen_falls():
    """(a) Diagnos är läsning. Ett skrivande verktyg får inte ens finnas.

    Modellen ombeds förklara varför station_3 svälter och svarar med ett
    `set_transform`. Spärren är URVALET, inte en instruktion: verktyget är
    inte ens exponerat, och förgranskningens `avstangt`-grind fäller anropet
    innan någon kod genereras.
    """
    dom = Av.Avsiktsdom(Av.DIAGNOS, Av.Avsiktspastaende(
        avsikt=Av.DIAGNOS, belagg="varfor svalter station_3",
        mal="station_3", malbelagg="station_3"))
    urval = Sp.urval_for_avsikt(dom, V.REGISTER, V.urval_allt_pa(V.REGISTER))

    # Lager 1: skrivverktyget syns inte för modellen.
    assert "set_transform" not in urval.pa_namn()
    assert "list_components" in urval.pa_namn()

    # Lager 2: hade modellen ändå namngett det, kastar utföraren.
    with pytest.raises(V.Avstangt) as fel:
        urval.krav("set_transform")
    assert "DIAGNOS" in str(fel.value)

    # Lager 3: HELA turen. Ingen skrivning når kanalen.
    kanal = Kn.Attrappkanal({"list_components": [
        {"components": [{"name": n} for n, _ in SCEN.komponenter]}]})
    harness = L.Harness(
        modell=Mo.AttrappModell([
            Mo.anropa("set_transform",
                      {"component": "station_3", "position": [0, 0, 0]}),
            Mo.sag("Jag kan inte ändra scenen i en diagnos."),
        ]),
        kanal=kanal, urval=urval)
    protokoll = harness.kor("varfor svalter station_3")
    assert protokoll.utfall.startswith("AVVISAD:"), protokoll.text()
    assert [n for n, _a in kanal.anropade] == []


def test_b_en_tvetydig_andring_som_utfors_anda_falls():
    """(b) 'Byt det där gripdonet' med tre gripdon i scenen är en FRÅGA."""
    pastaende = Av.Avsiktspastaende(
        avsikt=Av.ANDRING, belagg="byt det dar gripdonet",
        mal="gripdon", malbelagg="gripdonet")
    dom = Av.granska(pastaende, "byt det dar gripdonet", SCEN)
    assert dom.dom == Av.FRAGA, dom.text()
    # Frågan namnger kandidaterna. En fråga utan dem är inte svarbar.
    assert dom.kandidater == ("ST210_gripdon", "ST220_gripdon", "ST230_gripdon")
    # Och den får inte utföras.
    assert Sp.far_utforas(dom) is False
    urval = Sp.urval_for_avsikt(dom, V.REGISTER, V.urval_allt_pa(V.REGISTER))
    assert urval.pa_namn() == ()


def test_c_en_andring_utan_belagg_som_utfors_falls():
    """(c) Ett värde utan härledning och utan fråga är ett tyst val."""
    # Modellen påstår en takt som inte står någonstans i operatörens mening.
    falt = (Sp.Falt("takt_s", 12.0, None),)
    brott = Sp.granska_falt(falt, begaran_text="byt gripdonet pa ST210",
                            grund=None)
    assert [k for k, _t in brott] == ["SH1_UTAN_HARKOMST"], brott

    # Och samma sak när härkomsten FINNS men orden inte står i begäran.
    falt = (Sp.Falt("takt_s", 12.0, Sp.ur_begaran("tolv sekunder per cykel")),)
    brott = Sp.granska_falt(falt, begaran_text="byt gripdonet pa ST210",
                            grund=None)
    assert [k for k, _t in brott] == ["SH2_FALSK_BEGARAN"], brott


# ==========================================================================
#  SPÄRREN
# ==========================================================================

def test_lassparren_slar_av_varje_skrivande_verktyg():
    urval = Sp.lasurval(V.REGISTER, V.urval_allt_pa(V.REGISTER))
    pa = set(urval.pa_namn())
    for namn, verktyg in V.REGISTER.items():
        if verktyg.effect == "write":
            assert namn not in pa, "%s är write och skulle exponerats" % namn
        else:
            assert namn in pa, "%s är read och slogs av utan skäl" % namn


def test_lassparren_bara_krymper():
    """En spärr som SLÄPPER PÅ ett verktyg är ingen spärr.

    Ett verktyg som redan är av av förmågeskäl ska stanna av, med SITT skäl.
    """
    grund = V.Urval({n: ("ytan saknas" if n == "list_components" else None)
                     for n in V.REGISTER})
    urval = Sp.lasurval(V.REGISTER, grund)
    assert urval.skal("list_components") == "ytan saknas"
    assert set(urval.pa_namn()) <= set(grund.pa_namn())


def test_okant_stanger_allt():
    """OKANT är aldrig ett godkännande. Ärvt ur plan/motsagelse.py."""
    dom = Av.Avsiktsdom(Av.OKANT, None, skal=("meningen sager inte vad som ska goras",))
    assert Sp.far_utforas(dom) is False
    urval = Sp.urval_for_avsikt(dom, V.REGISTER, V.urval_allt_pa(V.REGISTER))
    assert urval.pa_namn() == ()


def test_ett_uppfunnet_komponentnamn_ar_alltid_en_fraga():
    """I9: modellen får bara välja ur det som finns."""
    pastaende = Av.Avsiktspastaende(
        avsikt=Av.ANDRING, belagg="byt gripdonet pa ST999",
        mal="ST999_gripdon", malbelagg="ST999")
    dom = Av.granska(pastaende, "byt gripdonet pa ST999", SCEN)
    assert dom.dom == Av.OKANT, dom.text()
    assert "ST999_gripdon" in dom.text()


def test_ett_falt_markt_som_fraga_ar_inget_varde():
    """fraga() är den andra lagliga vägen — men den ger ingen siffra."""
    falt = (Sp.Falt("takt_s", None, Sp.som_fraga("vilken takt ska gälla?")),)
    assert Sp.granska_falt(falt, "byt gripdonet", None) == []
    assert Sp.oppna_fragor(falt) == ("vilken takt ska gälla?",)


# ==========================================================================
#  TOLKEN — och att den inte bär något språk
# ==========================================================================

@pytest.mark.parametrize("text,belagg", [
    ("varfor svalter station_3?", "varfor svalter station_3"),
    ("why is station_3 starving?", "why is station_3 starving"),
])
def test_engelska_och_svenska_gar_genom_samma_grind(text, belagg):
    """Grinden bär ingen ordlista. Den prövar citatet mot operatörens text.

    Det är hela skillnaden mot ORDBOK: den gamla vägen kan bara svenska
    därför att den ÄR svenska. Den här vägen kan varje språk modellen kan,
    därför att den bara frågar om orden står i meningen.
    """
    pastaende = Av.Avsiktspastaende(avsikt=Av.DIAGNOS, belagg=belagg,
                                    mal="station_3", malbelagg="station_3")
    dom = Av.granska(pastaende, text, SCEN)
    assert dom.dom == Av.DIAGNOS, dom.text()


def test_ordboken_ar_ett_facit_och_den_ar_matt_spraklast():
    """Facit, inte väg in. Skillnaden ska vara ett TAL och inte en åsikt.

    Mätt i M-162: fyra svenska komponentord ur ORDBOK träffar, deras fyra
    engelska motsvarigheter träffar noll.
    """
    import re
    from vc_assist_svc.plan.forfining import ORDBOK
    from vc_assist_svc.plan.harkomst import normalisera

    def traffar(text):
        tokens = set(re.findall(r"[a-z0-9]+", normalisera(text)))
        return tuple(o for o, _k, _f in ORDBOK if o in tokens)

    sv = "ett band, ett gripdon, en fotocell och ett lyftbord"
    en = "a conveyor, a gripper, a photocell and a lift table"
    assert len(traffar(sv)) == 4
    assert traffar(en) == ()


def test_ordlistan_faller_inte_stangt_over_ett_sprak_den_faller_TYST_FEL():
    """Det farligaste fyndet i M-162, och skälet spärren måste ligga i grinden.

    Ordlistans påstådda säkerhet är att den inte kan hitta på: saknas ordet
    blir det en fråga. Den egenskapen HÅLLER INTE över språk. Talet är
    språkneutralt och läses; det ord som ger talet sin MENING är svenskt och
    tappas. "at most 2x2 m" blir därför inte en fråga — det blir `eq 2000`,
    ett annat krav än det operatören skrev, utan att någon får veta det.

    En cell på 1500 mm uppfyller "at most 2x2 m" och bryter mot `eq 2000`.
    """
    from vc_assist_svc.plan import lasning as La
    svensk = La.cellmatt("cellen far vara hogst 2x2 m")
    engelsk = La.cellmatt("the cell may be at most 2x2 m")
    # Samma tal ...
    assert [mm for _f, _o, mm, _b in svensk] == [2000.0, 2000.0]
    assert [mm for _f, _o, mm, _b in engelsk] == [2000.0, 2000.0]
    # ... men inte samma krav, och ingen fråga ställdes om skillnaden.
    assert [o for _f, o, _mm, _b in svensk] == ["le", "le"]
    assert [o for _f, o, _mm, _b in engelsk] == ["eq", "eq"]


def test_ordlistan_missar_ocksa_vanlig_svenska():
    """Och den är inte ens komplett för det språk den är skriven i.

    ANDELSER i lasning.py bär inte presens-r. "en station som svetsar" läses
    som ingen process alls, medan "svetsning" läses. Mätt i M-162.
    """
    from vc_assist_svc.plan import lasning as La
    assert La.processer("en station som svetsning")[0]
    assert La.processer("en station som svetsar")[0] == []


# ==========================================================================
#  DIAGNOSEN — intention 1, hela vägen
# ==========================================================================

def test_diagnosen_svarar_ur_ogats_egna_rader():
    d = Di.ur_rapport(RAPPORT, "station_3")
    assert d.dom == Di.BELAGD, d.text()
    # Svältern är ögats ord, inte vårt.
    assert "STARVED station_3 41.500s req=5.000s EXCEEDED" in d.fynd
    # Orsaken är flaskhalsraden, och den pekar på en ANNAN station.
    assert "BOTTLENECK station_2 blocked 68.0%" in d.fynd
    assert d.orsak_station == "station_2"


def test_diagnosen_pastar_ingenting_nar_ogat_inte_matt_det():
    """Ingen STARVED-rad för stationen = OKANT, aldrig 'den svälter inte'."""
    utan = RAPPORT.replace("STARVED station_3 41.500s req=5.000s EXCEEDED\n", "")
    d = Di.ur_rapport(utan, "station_3")
    assert d.dom == Di.OKANT, d.text()
    assert "STARVED" in d.text()


def test_diagnosen_fragar_nar_stationen_ar_tvetydig():
    d = Di.ur_rapport(RAPPORT, "station")
    assert d.dom == Di.FRAGA, d.text()
    assert d.kandidater == ("station_2", "station_3")


def test_diagnosen_ror_aldrig_scenen():
    """Diagnosen namnger bara läsande verktyg. Mekaniskt, inte i text."""
    d = Di.ur_rapport(RAPPORT, "station_3")
    for namn in d.nasta_lasningar:
        assert V.REGISTER[namn].effect == "read", namn


# ==========================================================================
#  BUDGETEN — härledd, aldrig en tabell
# ==========================================================================

def test_budgeten_ar_summan_av_de_steg_grindarna_kraver():
    """Inget påhittat tal: budgeten räknas ur de anrop turen MÅSTE göra."""
    diagnos = Av.Avsiktsdom(Av.DIAGNOS, Av.Avsiktspastaende(
        avsikt=Av.DIAGNOS, belagg="varfor svalter station_3",
        mal="station_3", malbelagg="station_3"))
    andring = Av.Avsiktsdom(Av.ANDRING, Av.Avsiktspastaende(
        avsikt=Av.ANDRING, belagg="byt gripdonet pa ST210",
        mal="ST210_gripdon", malbelagg="ST210"))
    steg_d = Av.nodvandiga_steg(diagnos)
    steg_a = Av.nodvandiga_steg(andring)
    # Varje steg bär regeln som kräver det.
    for steg in steg_d + steg_a:
        assert steg.regel, steg
    # En ändring kostar mer än en diagnos, och skälet är återläsningskravet.
    assert len(steg_a) > len(steg_d)
    assert any("olast_skrivning" in s.regel for s in steg_a)
    assert Av.turbudget(andring) > Av.turbudget(diagnos)


def test_budgeten_ryms_i_harnessens_eget_rundtak():
    """En budget över taket vore en budget som inte går att köra."""
    for dom in (Av.Avsiktsdom(Av.DIAGNOS, Av.Avsiktspastaende(
                    avsikt=Av.DIAGNOS, belagg="varfor svalter station_3",
                    mal="station_3", malbelagg="station_3")),
                Av.Avsiktsdom(Av.ANDRING, Av.Avsiktspastaende(
                    avsikt=Av.ANDRING, belagg="byt gripdonet pa ST210",
                    mal="ST210_gripdon", malbelagg="ST210"))):
        assert Av.turbudget(dom) <= L.MAX_RUNDOR


# ==========================================================================
#  OPTIMERING — inte byggd, och det ska SYNAS
# ==========================================================================

def test_optimering_avvisas_med_skal_i_stallet_for_att_gissas():
    pastaende = Av.Avsiktspastaende(
        avsikt=Av.OPTIMERING, belagg="snabba upp linan",
        mal="", malbelagg="")
    dom = Av.granska(pastaende, "snabba upp linan", SCEN)
    assert dom.dom == Av.OKANT, dom.text()
    assert "OPTIMERING" in dom.text()
    assert Sp.far_utforas(dom) is False


# ==========================================================================
#  FRÅGORNA — och vem som får svara på dem
# ==========================================================================
#
# Idén är hämtad, inte uppfunnen: sibling-project
# kravformulering_v1.py delar en öppen fråga efter VEM som kan svara den.
# Dess egen motivering: "Att skicka en mätuppgift till operatören som
# 'beslut' är samma fel som att gissa talet."
#
# För den här vägen är skillnaden hela skälet att diagnosen byggs först:
# "varför svälter station 3" är en MÄTNING — ögat kan köra den — medan
# "vilket av de tre gripdonen menade du" är ett OPERATORSVAL.

def test_d_en_matbar_fraga_som_stalls_till_operatoren_falls():
    """(d) Fjärde trasiga fixturen. En diagnosväg som frågar användaren om
    något den kunde ha mätt är lika trasig som en som gissar."""
    from vc_assist_svc.scenarbete import fragor as Fr
    matbar = Fr.Fraga("varfor svalter station_3?", Fr.MATNING,
                      verktyg=("eyes_report", "layout_statistics"),
                      skal="ogat matter svalt mot ett deklarerat krav")
    brott = Fr.granska_till_operatoren((matbar,))
    assert [k for k, _t in brott] == ["FR1_MATNING_SOM_BESLUT"], brott
    # Och den ska i stället gå till ögat.
    assert Fr.till_operatoren((matbar,)) == ()
    assert Fr.till_matning((matbar,)) == (matbar,)


def test_ett_operatorsval_far_stallas_till_operatoren():
    from vc_assist_svc.scenarbete import fragor as Fr
    val = Fr.Fraga("vilket av de tre gripdonen menar du?", Fr.OPERATORSVAL,
                   kandidater=("ST210_gripdon", "ST220_gripdon"),
                   skal="ingen matning kan avgora vad du menade")
    assert Fr.granska_till_operatoren((val,)) == []
    assert Fr.till_operatoren((val,)) == (val,)


def test_en_matningsfraga_utan_verktyg_ar_ingen_matningsfraga():
    """Fail-closed: en 'mätning' ingen kan köra är en gissning med bra rykte."""
    from vc_assist_svc.scenarbete import fragor as Fr
    with pytest.raises(Fr.Fragefel):
        Fr.Fraga("varfor gar det langsamt?", Fr.MATNING, skal="x")


def test_en_matningsfraga_far_bara_namna_lasande_verktyg():
    from vc_assist_svc.scenarbete import fragor as Fr
    with pytest.raises(Fr.Fragefel):
        Fr.Fraga("byt gripdonet?", Fr.MATNING, verktyg=("set_transform",),
                 skal="x")


def test_hogst_fyra_fragor_per_runda():
    """Grupperingen är tagen ur sibling-project/lib/negotiation_protocol.py.

    Att dumpa hela listan på en gång är hur en förhandling blir ett formulär.
    """
    from vc_assist_svc.scenarbete import fragor as Fr
    manga = tuple(Fr.Fraga("fraga %d?" % i, Fr.OPERATORSVAL, skal="s")
                  for i in range(9))
    rundor = Fr.rundor(manga)
    assert [len(r) for r in rundor] == [4, 4, 1]
    assert sum(len(r) for r in rundor) == len(manga)


# ==========================================================================
#  TRE SORTERS "GÅR INTE ATT AVGÖRA" — med motsatta åtgärder
# ==========================================================================

def test_de_tre_sorterna_av_okant_har_olika_atgard():
    """Ett mått som bara skiljer den första kollapsar de andra två till
    "avgjort", och det är falsk trygghet."""
    # 1. En mätning löser det: ögat körde utan att kravet var deklarerat.
    utan_krav = RAPPORT.replace(
        "STARVED station_3 41.500s req=5.000s EXCEEDED\n", "")
    d1 = Di.ur_rapport(utan_krav, "station_3")
    assert d1.dom == Di.OKANT and d1.sort == Di.OKANT_MATBART, d1.text()

    # 2. Mer av samma mätning löser det aldrig - rapporten bär ingen topologi.
    egen = RAPPORT.replace("BOTTLENECK station_2 blocked 68.0%",
                           "BOTTLENECK station_3 starved 91.0%")
    d2 = Di.ur_rapport(egen, "station_3")
    assert d2.sort == Di.OKANT_ANNAN_SORT, d2.text()
    assert d2.nasta_lasningar, "en annan observabel ska namnges"

    # 3. Olösligt som frågan är ställd: stationen finns inte.
    d3 = Di.ur_rapport(RAPPORT, "station_9")
    assert d3.dom == Di.OKANT and d3.sort == Di.OKANT_OLOSLIGT, d3.text()


# ==========================================================================
#  BUDGETENS STATUS — härledd är inte samma sak som bevisad
# ==========================================================================

def test_budgeten_sager_sjalv_om_den_ar_bevisad():
    """Formen är lånad ur sibling-project cell_router_templates_v1.json:
    varje budgettak bär UPPNADD med namngiven bevis-cell, eller HYPOTES med
    bevis: null. En budget som inte säger vilket är en gissning i kostym."""
    dom = Av.Avsiktsdom(Av.DIAGNOS, Av.Avsiktspastaende(
        avsikt=Av.DIAGNOS, belagg="varfor svalter station_3",
        mal="station_3", malbelagg="station_3"))
    b = Av.budget(dom)
    assert b.rundor == Av.turbudget(dom)
    assert b.status in Av.BUDGETSTATUS
    # Stegen är härledda ur mätta grindar; att rundtalet RÄCKER är inte prövat.
    assert b.status == Av.HYPOTES
    assert b.bevis is None
    assert "M-162" in b.text()


# ---------------------------------------------------------------------------
# Scenlage ur ett riktigt verktygssvar
# ---------------------------------------------------------------------------

def _svar(poster, avkortad=False):
    return {"components": list(poster), "antal": len(poster),
            "avkortad": avkortad}


def test_scenlaget_tar_namn_och_kategori_ur_verktygssvaret():
    sl = Sp.scenlage_ur_svar(_svar([
        {"name": "ST210_GRP", "uri": "x", "category": "Grippers"},
        {"name": "ST210_BAND", "uri": "y", "category": "Conveyors"}]))
    assert sl.komponenter == (("ST210_GRP", "Grippers"),
                              ("ST210_BAND", "Conveyors"))
    assert sl.kalla == "list_components"
    assert sl.fullstandig() is True


def test_en_komponent_utan_kategori_far_tom_typ_aldrig_en_gissad():
    """M-69: katalognamnet gav 1736 robotar, strukturen 2202. Namn ljuger.

    En gissad typ som ser ratt ut ar varre an ingen typ, for den gar inte att
    ifragasatta.
    """
    sl = Sp.scenlage_ur_svar(_svar([
        {"name": "Gripper_2F_85", "uri": None, "category": None}]))
    assert sl.komponenter == (("Gripper_2F_85", ""),)


def test_en_avkortad_lasning_ar_inte_en_fullstandig_scen():
    """TRASIG FIXTUR. Rakningen 'scenen har tre gripdon' kan vara fel om ett
    fjarde lag i den bortklippta delen. Att tappa flaggan ar en falsk gron."""
    sl = Sp.scenlage_ur_svar(_svar(
        [{"name": "A", "category": "Grippers"}], avkortad=True))
    assert sl.avkortad is True
    assert sl.fullstandig() is False, (
        "en avkortad lasning far ALDRIG rapporteras som en hel scen")
    assert "AVKORTAD" in repr(sl)


def test_ett_scenlage_utan_lasning_ar_aldrig_fullstandigt():
    assert Sp.Scenlage().fullstandig() is False


def test_ett_svar_som_inte_ar_en_scenlasning_avvisas():
    """I9: modellen far bara valja ur det som finns, och 'det som finns' maste
    nagon ha last."""
    import pytest
    with pytest.raises(ValueError):
        Sp.scenlage_ur_svar({"antal": 0})
    with pytest.raises(TypeError):
        Sp.scenlage_ur_svar("[]")


def test_en_komponent_utan_namn_stoppar_hela_lasningen():
    """Att hoppa over den tyst vore att krympa scenen utan att saga det."""
    import pytest
    with pytest.raises(ValueError):
        Sp.scenlage_ur_svar(_svar([{"name": "", "category": "Grippers"}]))


def test_svenskt_ord_mot_engelsk_kategori_ger_INGA_kandidater():
    """MATT HAL, inte ett fel i kopplingen.

    Scenen har ett gripdon. Kategorin heter 'Grippers' och namnet 'ST210_GRP'.
    Ordet "gripdon" matchar ingetdera, sa delstrangsmatchningen ensam kan inte
    losa ut deixis over ett sprakbyte. Det ar precis darfor en modell behovs i
    ledet - och provet star har for att halet ska sluta vara osynligt.
    """
    sl = Sp.scenlage_ur_svar(_svar([
        {"name": "ST210_GRP", "category": "Grippers"}]))
    assert sl.kandidater("gripdon") == ()
    assert sl.kandidater("Grippers") == ("ST210_GRP",)


def test_svenskt_ord_mot_engelsk_scen_ar_en_fraga_inte_ett_finns_inte():
    """TRASIG FIXTUR for den matta felmoden.

    Scenen har ett gripdon, men det heter ST210_GRP och kategorin heter
    Grippers. Ordet "gripdon" matchar ingetdera. Den forsta versionen svarade
    da OKANT - "gripdon finns inte i scenen" - om en scen som HADE ett. Ett
    tyst fel, alltsa den dyraste sorten.

    Delstrangen ar ett forfilter och far aldrig vara domaren.
    """
    scen = Sp.scenlage_ur_svar(
        {"components": [{"name": "ST210_GRP", "category": "Grippers"},
                        {"name": "ST220_CNV", "category": "Conveyors"}],
         "antal": 2, "avkortad": False})
    pastaende = Av.Avsiktspastaende(
        avsikt=Av.ANDRING, belagg="byt gripdonet",
        mal="gripdonet", malbelagg="gripdonet")
    dom = Av.granska(pastaende, "byt gripdonet", scen)
    t = dom.text()
    assert dom.dom == Av.FRAGA, t
    assert "finns inte" not in t, "en oversattningsmiss far inte bli ett finns-inte"
    assert "ST210_GRP" in t and "Grippers" in t, "scenen ska raknas upp med sina sorter"
    assert set(dom.kandidater) == {"ST210_GRP", "ST220_CNV"}


def test_en_avkortad_scen_sager_det_i_fragan():
    """Ett fjarde gripdon kan ligga i den bortklippta delen."""
    scen = Sp.scenlage_ur_svar(
        {"components": [{"name": "ST210_GRP", "category": "Grippers"}],
         "antal": 1, "avkortad": True})
    dom = Av.granska(
        Av.Avsiktspastaende(avsikt=Av.ANDRING, belagg="byt gripdonet",
                            mal="gripdonet", malbelagg="gripdonet"),
        "byt gripdonet", scen)
    assert "AVKORTAD" in dom.text()


def test_ett_hopsatt_namn_ar_fortfarande_hart_fel():
    """I9 ligger FORE uppslagningen och overlever lagningen ovan.

    Operatoren sa "ST999". Modellen svarade "ST999_gripdon" - varken i scenen
    eller i meningen, alltsa hopsatt av modellen sjalv.
    """
    scen = Sp.scenlage_ur_svar(
        {"components": [{"name": "ST210_GRP", "category": "Grippers"}],
         "antal": 1, "avkortad": False})
    dom = Av.granska(
        Av.Avsiktspastaende(avsikt=Av.ANDRING, belagg="byt gripdonet pa ST999",
                            mal="ST999_gripdon", malbelagg="ST999"),
        "byt gripdonet pa ST999", scen)
    assert dom.dom == Av.OKANT and "hopsatt" in dom.text()
