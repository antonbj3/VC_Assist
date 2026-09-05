# -*- coding: utf-8 -*-
"""M-105: monster som aldrig kort mot texten de ska lasa.

Filen bar tva saker som hor ihop:

  1. TRASIGA FIXTURER for de sex matchare M-105 hittade. Var och en foll mot
     koden FORE lagningen, och var och en namnger den text som matchen aldrig
     provats mot.
  2. SPARREN: hur manga av de monster som AVGOR EN DOM som saknar bevisning.
     Taket far bara krympa, precis som i test_skuld.py.

FELKLASSEN, i ett stycke: ett monster som ser ut att matcha, aldrig provat mot
den text det ska lasa. Tre fall pa en natt hade samma form - `skuld._ARLIGHET`
skriven i ASCII mot svensk text (M-70), `st.lexer._TIDSDEL` utan `re.I` mot ett
skiftlagesokansligt sprak (M-96), och ordlistan `harness.text.NEKANDE` som
fyrade pa fel storhet (M-94). Det gemensamma ar INTE att de ar regexar.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))


# ===========================================================================
# 1. TRASIGA FIXTURER
# ===========================================================================

# ---- F1: matningskoden gick forbi M-99 -----------------------------------

def test_harkomsten_kanner_igen_ett_tresiffrigt_matningsnummer():
    """`_MATNING` var `^M-(\\d{2})$`, och repot skrev M-100 den 2026-09-04.

    Monstret skrevs nar hogsta numret var tvasiffrigt och provades aldrig mot
    ett tresiffrigt. Foljden ar inte att uppslaget tiger: det FALLER TILLBAKA
    pa filkontrollen och anmarker att "M-100" varken ar en fil eller en
    matningskod - en falsk anmarkning i den grind som granskar modellens egna
    beteenderegler.

    Provet gar over ALLA matningar som ligger pa disk, sa det aldras inte om
    med numret igen.
    """
    from vc_assist_svc.harness import instruktioner as I
    uppslag = I.Harkomstuppslag(_ROT)
    katalog = os.path.join(_ROT, "docs", "matningar")
    koder = sorted(n.split("_")[0] for n in os.listdir(katalog)
                   if n.startswith("M-") and n.endswith(".md"))
    assert koder, "hittade inga matningar att prova mot"
    dalig = [k for k in koder if uppslag.problem(k) is not None]
    assert dalig == [], (
        "de har matningarna finns pa disk men uppslaget kanner inte igen "
        "koden: %s" % ", ".join(dalig))


def test_harkomsten_avvisar_fortfarande_en_matning_som_inte_finns():
    """Andra halvan: ett monster som fyrar pa allt mater lika lite."""
    from vc_assist_svc.harness import instruktioner as I
    uppslag = I.Harkomstuppslag(_ROT)
    for post in ("M-9999", "M-7", "m-70", "M-70x"):
        assert uppslag.problem(post) is not None, (
            "%r borde inte ga att sla upp" % (post,))


# ---- F2: korsreferensen skriven i ASCII mot svensk regeltext -------------

def _regel(text):
    return {"id": "PRV-001", "version": 1, "allvar": "varning",
            "tvingas_av": None, "text": text,
            "skal": ("Ett skal som ar tillrackligt langt for granskningens "
                     "golv, och som sager varfor regeln finns i stallet for "
                     "att bara upprepa den. Det har ar en provfixtur."),
            "harkomst": ["docs/spec/90_invarianter.md"]}


def test_korsreferensen_ses_ocksa_nar_den_skrivs_med_prickar():
    """`_KORSREFERENSER` bar "som namnts" i ASCII.

    MATT: 46 av 46 regeltexter i instruktioner/ innehaller a, a eller o, och
    granskningen jamfor mot `text.lower()` UTAN att ta bort diakritiken. Grenen
    kunde alltsa aldrig fyra pa den enda stavning en riktig regel anvander.
    Samma felklass som M-70, i en annan modul.
    """
    from vc_assist_svc.harness import instruktioner as I
    uppslag = I.Harkomstuppslag(_ROT)
    problem = []
    I._las_regel(_regel("Folj regeln som nämnts ovan i systemprompten."),
                 "prov", "prov.json", uppslag, problem)
    assert any("korsreferens" in p for p in problem), (
        "korsreferensen 'som nämnts' fangades inte: %r" % (problem,))


def test_en_regel_utan_korsreferens_gar_igenom():
    from vc_assist_svc.harness import instruktioner as I
    uppslag = I.Harkomstuppslag(_ROT)
    problem = []
    I._las_regel(_regel("Anvand alltid verktyget innan du pastar nagot om scenen."),
                 "prov", "prov.json", uppslag, problem)
    assert [p for p in problem if "korsreferens" in p] == []


# ---- F3: den lokaliserade adressen ar skiftlagesokanslig ------------------

def test_adressen_lases_i_bada_skiftlagen():
    """IEC 61131-3 ar skiftlagesokansligt, och `%qx0.0` ar en giltig adress.

    `_ADRESS` var skriven `^%(?P<omrade>[IQ])(?P<storlek>[XBWDL])...` utan
    `re.I`, medan `_typ_av_text` i SAMMA fil redan gjorde `.upper()` pa typen
    och `plc.skelett._HAR_ADRESS` redan bar `re.I`. Exakt den asymmetri M-96
    matte i lexern: halva filen skiftlagesokanslig, halva inte.
    """
    from vc_assist_svc.plc import signalkarta as S
    assert S.las_adress("%qx0.0") == S.las_adress("%QX0.0")
    assert S.las_adress("%iw10") == S.las_adress("%IW10")


def test_tva_skrivningar_av_samma_adress_krockar_fortfarande():
    """Lagningen far inte gora `%qx0.0` och `%QX0.0` till TVA platser.

    Att bara satta `re.I` hade gjort det: kartan hade tagit emot bada och
    bundit tva scensignaler till samma plats i bildtabellen utan att sага
    nagot. Normaliseringen ar darfor en del av lagningen, inte en snyggning.
    """
    from vc_assist_svc.plc import signalkarta as S
    assert S.las_adress("%qx0.0").plats() == S.las_adress("%QX0.0").plats()
    assert S.las_adress("%qx0.0").text() == "%QX0.0"


def test_adressen_avvisar_fortfarande_det_som_inte_ar_en_adress():
    from vc_assist_svc.plc import signalkarta as S
    for text in ("%ZX0.0", "QX0.0", "%Q0.0", "%QX", ""):
        with pytest.raises(S.KartFel):
            S.las_adress(text)


# ---- F4: forfiningen laste enheter i ett enda skiftlage -------------------

def test_matten_lases_oavsett_skiftlage():
    """`_MM`, `_TAKT` och `_CYKEL` saknade `re.I`.

    Syskonmodulen `plan/lasning.py` laser SAMMA text - operatorens begaran -
    och bar `re.I` pa varenda monster. Att de tva laser samma text med olika
    skiftlagespolicy ar felet, inte att den ena ar strangare.
    """
    from vc_assist_svc.plan import forfining as F
    assert F.matt_mm("Bandbredd 600 MM") == [600.0]
    assert F.takt_per_h("120 enheter I TIMMEN") == 120.0
    assert F.takt_per_h("45 burkar PER MINUT") == 2700.0
    assert F.cykeltid_s("1,33 S per burk") == 1.33


def test_cykeltiden_lases_ocksa_nar_sekunden_forkortas_sek():
    """`_CYKEL` fyrade NOLL ganger i hela sviten (6452 prov).

    Den var alltsa aldrig prövad mot nagon text alls. "12 sek per cykel" ar
    den vanligaste svenska formen och gick rakt igenom som otolkad.
    """
    from vc_assist_svc.plan import forfining as F
    assert F.cykeltid_s("12 sek per cykel") == 12.0
    assert F.cykeltid_s("32,0 sekunder per enhet") == 32.0


def test_takten_far_inte_bli_fel_TAL_av_skiftlaget():
    """Lagningen far inte gora "PER MINUT" till en timtakt.

    Enheten plockades ut och jamfordes mot ("minut", "min") i gemener. Med
    `re.I` men utan `.lower()` hade "PER MINUT" fallit ur den jamforelsen och
    120 burkar i minuten blivit 120 i timmen - ett tyst fel som ar varre an
    det ursprungliga, dar talet aldrig lastes alls.
    """
    from vc_assist_svc.plan import forfining as F
    assert F.takt_per_h("120 burkar per minut") == 7200.0
    assert F.takt_per_h("120 burkar PER MINUT") == 7200.0
    assert F.takt_per_h("120 burkar per timme") == 120.0


def test_forfiningen_lasar_fortfarande_inte_in_fel_storhet():
    from vc_assist_svc.plan import forfining as F
    assert F.matt_mm("bandet ar 3 meter") == []
    assert F.takt_per_h("45 burkar i lagret") is None
    assert F.cykeltid_s("1,33 s per timme") is None


# ---- F5: trosklarna lastes i ett enda skiftlage ---------------------------

_KANDA = ("ST100_OUT", "ST100_LEN")


def test_troskeln_lases_oavsett_skiftlage():
    """`_T_UTGANG` var det ENDA monstret i sprak.py utan `re.I`.

    Alla sjutton `_M_*`, alla atta `_F_*` och de tre `_I_*` bar den. Ett
    monster som laser samma uppgiftstext som sina syskon men med en annan
    skiftlagespolicy ar samma asymmetri som M-96 matte.
    """
    from vc_assist_svc.plc.baslinje import sprak as S
    for mening in ("ST100_OUT ska vara hog nar ST100_LEN ar over 5.",
                   "ST100_OUT ska vara hog nar ST100_LEN ar Over 5.",
                   "ST100_OUT SKA VARA HOG NAR ST100_LEN AR OVER 5."):
        t = S.las_trosklar(mening, _KANDA, ["ST100_LEN"], ["ST100_OUT"])
        assert len(t) == 1, "ingen troskel last ur %r" % mening
        assert t[0].tecken == ">", (
            "tecknet blev %r i %r; ett skiftlage far inte vanda jamforelsen"
            % (t[0].tecken, mening))


def test_troskeln_vander_fortfarande_pa_under():
    from vc_assist_svc.plc.baslinje import sprak as S
    t = S.las_trosklar("ST100_OUT ska vara hog nar ST100_LEN ar UNDER 5.",
                       _KANDA, ["ST100_LEN"], ["ST100_OUT"])
    assert len(t) == 1 and t[0].tecken == "<"


def test_en_mening_utan_troskel_ger_ingen_troskel():
    from vc_assist_svc.plc.baslinje import sprak as S
    assert S.las_trosklar("ST100_OUT ska vara hog nar ST100_LEN ar hog.",
                          _KANDA, ["ST100_LEN"], ["ST100_OUT"]) == []


# ---- F6: sakerhetsordlistan hade ett hal i sina tvillingar ----------------

def test_sakerhetsgrinden_ser_ordet_med_prickar():
    """SAKERHETSORD bar tvillingpar - utom for tva ord.

    "sakerhetsplc" och "sakerhetsgrind" saknade sin a-a-o-tvilling, och
    `granska_text` jamfor mot `mening.lag` utan att ta bort diakritiken. Alltsa
    gick "vi byglar säkerhetsgrinden tillfälligt" rakt igenom en SAKERHETSgrind.
    Lagningen ar inte tva nya poster: en handskriven tvillinglista glommer
    nasta ord ocksa. Bada sidor avdiakritiseras.
    """
    from vc_assist_svc.harness import sakerhet as SK
    g = SK.Sakerhetsgrind() if hasattr(SK, "Sakerhetsgrind") else None
    assert g is not None
    for mening in ("Vi byglar säkerhetsgrinden tillfälligt.",
                   "Vi byglar sakerhetsgrinden tillfalligt.",
                   "Vi kopplar förbi säkerhets-PLC:n så länge.",
                   "Vi byglar nödstoppet under injustering."):
        dom = g.granska_text(mening)
        assert dom.skal, "slapp igenom: %r" % mening


def test_sakerhetsgrinden_slapper_fortfarande_igenom_vanlig_prosa():
    from vc_assist_svc.harness import sakerhet as SK
    g = SK.Sakerhetsgrind()
    for mening in ("Nödstoppet är kopplat till säkerhetsreläet.",
                   "Vi stänger av transportören mellan skiften.",
                   "Ljusridån larmar när någon går in."):
        assert not g.granska_text(mening).skal, "falsk traff pa %r" % mening


# ===========================================================================
# 2. BEVISNINGEN OCH SPARREN
# ===========================================================================
#
# BEVIS[nyckel] = (metod, strangar_som_MASTE_matcha, strangar_som_INTE_far)
#
# Metoden ar den koden faktiskt anvander - ett monster som anropas med
# `.search` men provas med `.match` provas inte alls.
#
# BADA halvorna kravs. Ett monster som fyrar pa allt mater lika lite som ett
# som aldrig fyrar, och det ar precis vad M-105 matte upp: av 100 monster som
# avgor en dom hade 28 bara den ena halvan och 4 ingen alls.

from vc_assist_svc import monsterbevis as MB                     # noqa: E402

BEVIS = {

    # ---- ogats domskontrakt (guldgrinden lasar hela sin dom har) ---------
    "ext/vc_addon/vc_assist/oga_kontrakt.py::_DOM": ("match",
        ("EYES VERDICT PASS allt inom tolerans",
         "EYES VERDICT FAIL gripdonet slappte",
         "EYES VERDICT INCONCLUSIVE for fa prov"),
        # "PASSED" ar INTE en dom. En grind som tar det for PASS har last en
        # dom som inte finns.
        ("EYES VERDICT PASSED allt inom tolerans",
         "eyes verdict PASS allt inom tolerans",
         "EYES VERDICT OK allt inom tolerans")),
    "ext/vc_addon/vc_assist/oga_kontrakt.py::_TEMPLATE": ("match",
        ("TEMPLATE grundmall", "TEMPLATE mall med mellanslag"),
        ("TEMPLATE", "TEMPLATE ", "template grundmall")),
    "ext/vc_addon/vc_assist/oga_kontrakt.py::_RUN": ("match",
        ("RUN kor1 DUR 12.5s SAMPLES 250 RATE 20.0Hz",
         "RUN a DUR 1s SAMPLES 2 RATE 3Hz"),
        ("RUN kor1 DUR 12.5 SAMPLES 250 RATE 20.0Hz",
         "RUN kor 1 DUR 12.5s SAMPLES 250 RATE 20.0Hz",
         "RUN kor1 DUR 12.5s SAMPLES 250 RATE 20.0hz")),
    "ext/vc_addon/vc_assist/oga_kontrakt.py::_SEKTION": ("match",
        ("SECTION MOTION", "SECTION LIMITS"),
        ("SECTION MOTION TIMING", "section MOTION", "SECTION")),
    "ext/vc_addon/vc_assist/oga_kontrakt.py::_HUVUD": ("match",
        ("EYES v1", "EYES v2"),
        ("EYES v", "eyes v1", "EYES v1 ")),

    # ---- lintern over VC-kod --------------------------------------------
    "svc/vc_assist_svc/api_index.py::_PY2PRINT": ("search",
        ("print 'hej'\n", "    print x\n", "print u'x'\n"),
        # Py3-print, tilldelning och ett namn som bara BORJAR med print.
        ("print('hej')\n", "print = 5\n", "sprint x\n", "printer 3\n")),

    # ---- grinden over forloppsytan --------------------------------------
    "svc/vc_assist_svc/forlopp/grind.py::_RAKNING": ("search",
        ("HÄNDELSER: 12 totalt, visar 5",),
        # Renderaren och grinden MASTE stava ordet likadant. Skrivs ytan om i
        # translitterering slutar grinden se raden - det ar M-70:s fälla, och
        # provet gor kopplingen synlig i stallet for tyst.
        ("HANDELSER: 12 totalt, visar 5",
         "HÄNDELSER: tolv totalt, visar fem",
         "HÄNDELSER: 12 totalt")),
    "svc/vc_assist_svc/forlopp/yta.py::_SEKTIONSRAD": ("findall",
        ("SECTION MOTION\nSECTION TIMING\n",),
        ("SECTION MOTION extra\n", "section MOTION\n", " SECTION MOTION\n")),

    # ---- granskningen av modellens beteenderegler ------------------------
    "svc/vc_assist_svc/harness/instruktioner.py::_REGEL_ID": ("match",
        ("DOM-003", "SAK-001"),
        ("dom-003", "DOM-3", "DOMA-003", "DOM-0031")),
    "svc/vc_assist_svc/harness/instruktioner.py::_FILNAMN": ("match",
        ("10_bas.json", "99_matta_fakta.json"),
        ("1_bas.json", "10_Bas.json", "10_bas.JSON", "bas.json")),
    "svc/vc_assist_svc/harness/instruktioner.py::_MATNING": ("match",
        # LAGAT 2026-09-05: repot skrev M-100 den 2026-09-04, och monstret var
        # `M-\d{2}`. Tresiffriga koder MASTE ga igenom.
        ("M-70", "M-100", "M-105"),
        ("M-7", "m-70", "M-70x", "M-", "MM-70")),
    "svc/vc_assist_svc/harness/instruktioner.py::_INVARIANT": ("match",
        ("I1", "I17"),
        ("i17", "I", "I173", "I-17")),
    "svc/vc_assist_svc/harness/instruktioner.py::_SKULD": ("match",
        ("S1", "S12"),
        ("s3", "S", "S123", "S-3")),

    # ---- fallorna i koden modellen skriver -------------------------------
    "svc/vc_assist_svc/harness/kodfallor.py::_U_STRANG": ("search",
        ("x = u'hej'", 'y = u"hej"'),
        ("x = 'hej'", "menu'", "du\"x\"")),
    "svc/vc_assist_svc/harness/kodfallor.py::_S_MED_U": ("search",
        ("_s(u'hej')", '_s( u"hej")'),
        ("_s('hej')", "s(u'hej')")),

    # ---- textlagret arlighetsgrinden domer med ---------------------------
    "svc/vc_assist_svc/harness/text.py::_VCTYP": ("search",
        # MATT: dessa fyrade NOLL ganger i hela enhetssviten (149 anrop).
        ("jag anropade vcRobot", "app.vcMatrix", "`vcComponent`"),
        ("VCRobot", "myvcRobot", "vcrobot", "vc_robot")),
    "svc/vc_assist_svc/harness/text.py::_VCKONST": ("search",
        ("satte VC_MODE_AUTO", "flaggan VC_X"),
        ("vc_mode_auto", "MYVC_MODE", "VCMODE")),
    "svc/vc_assist_svc/harness/text.py::_URI": ("search",
        ("se file:///tmp/x", "http://example.invalid/a"),
        ("se filen /tmp/x", "://tomt", "Http://Versalt")),

    # ---- personatackningens spec -> ett rapporterat tal ------------------
    "svc/vc_assist_svc/personatackning.py::_RUBRIK": ("match",
        ("## P1 - Layoutaren", "## P3 – Simuleringsingenjoren"),
        ("## Profil P3 - x", "### P3 - x", "## P3 Layoutaren", "## Utfall")),
    "svc/vc_assist_svc/personatackning.py::_ANNAN_RUBRIK": ("match",
        ("## Utfall", "##  tva blanksteg"),
        ("### djupare", "#topp", "##Utan blanksteg", "text ## mitt i")),
    "svc/vc_assist_svc/personatackning.py::_TABELLRAD": ("match",
        ("| 3 | oppna scenen |", "|12|x|"),
        ("|  | x |", "| a | x |", "text | 3 |", "|---|---|")),
    "svc/vc_assist_svc/personatackning.py::_KOD": ("findall",
        ("anvander `verktyg_x`", "`a` och `b`"),
        ("ingen kod alls", "` obalanserat", "``")),

    # ---- operatorens fria text -------------------------------------------
    "svc/vc_assist_svc/plan/forfining.py::_MM": ("findall",
        ("bandbredd 600 mm", "bandbredd 600 MM", "500,5 mm"),
        ("bandet ar 3 meter", "600 cm", "mm utan tal")),
    "svc/vc_assist_svc/plan/forfining.py::_TAKT": ("search",
        ("45 burkar per minut", "100 enheter i timmen", "120/h",
         "45 burkar PER MINUT"),
        ("45 burkar i lagret", "per minut utan tal", "45 burkar per skift")),
    "svc/vc_assist_svc/plan/forfining.py::_CYKEL": ("search",
        # MATT: fyrade NOLL ganger i hela sviten fore M-105.
        ("1,33 s per burk", "32,0 sekunder per enhet", "12 sek per cykel",
         "1,33 S per burk"),
        ("1,33 s per timme", "12 sekunder senare", "s per cykel utan tal")),
    "svc/vc_assist_svc/plan/forfining.py::_ORD": ("findall",
        ("robot 3", "band"),
        # _ORD kors ALLTID pa normaliserad text (gemener, utan diakritik).
        # Provet pinnar det: mot ren svenska ser den ingenting.
        ("ÅÄÖ", "ROBOT", "-- ")),
    "svc/vc_assist_svc/plan/lasning.py::_ORD_I_BIT": ("findall",
        ("ett band", "robot3"),
        ("ÅÄÖ", "ROBOT", "  ")),

    # ---- baslinjens lasare -----------------------------------------------
    "svc/vc_assist_svc/plc/baslinje/morfologi.py::_TAGG": ("match",
        ("ST100_CLAMP_CLOSE", "ABC12_X"),
        ("CLAMP_CLOSE", "ST_CLAMP", "S1_X", "ST100CLAMP")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_I_OMRADE": ("search",
        ("matomradet 10 till 20", "arbetsomradet -5,5 till 12"),
        ("omradet ar stort", "matomradet 10 och 20")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_M_UPPEHALL": ("match",
        ("rakna 2.5 s uppehall", "RAKNA 3 S UPPEHALL"),
        ("vanta 2.5 s", "rakna 2.5 s cykeltid", "rakna s uppehall")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_M_HALL": ("match",
        ("hall ST100_CLAMP hog nar ST100_OK ar hog",
         "hall ST100_CLAMP lag sa lange ST100_OK ar hog"),
        ("hall ST100_CLAMP hog", "satt ST100_CLAMP hog nar ST100_OK ar hog",
         "hall ST100_CLAMP mitt nar ST100_OK ar hog")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_M_HANDLING_OCH_HALL": ("match",
        ("satt ST100_CLAMP hog och hall den i minst 1.5 s",
         "pulsa ST100_TRIG och hall 2 s"),
        ("satt ST100_CLAMP hog och vanta pa ST100_OK",
         "satt ST100_CLAMP hog och hall den",
         "nollstall ST100_CLAMP och hall den i 1 s")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_M_HANDLING_PA_FLANK": ("match",
        ("satt ST100_CLAMP hog pa stigande flank pa ST100_TRIG",
         "nollstall ST100_CNT pa fallande flank pa ST100_TRIG"),
        ("satt ST100_CLAMP hog pa ST100_TRIG",
         "vanta pa stigande flank pa ST100_TRIG",
         "satt ST100_CLAMP hog nar ST100_TRIG ar hog")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_M_RAKNA": ("match",
        ("oka ST100_CNT pa stigande flank pa ST100_TRIG",
         "minska ST100_CNT pa fallande flank pa ST100_TRIG"),
        ("oka ST100_CNT nar ST100_TRIG ar hog",
         "satt ST100_CNT pa stigande flank pa ST100_TRIG",
         "oka ST100_CNT pa flank pa ST100_TRIG")),
    "svc/vc_assist_svc/plc/baslinje/sprak.py::_T_UTGANG": ("search",
        # LAGAT 2026-09-05: enda monstret i modulen utan re.I.
        ("ST1_OUT ska vara hog nar ST1_LEN ar over 5",
         "ST1_OUT ska vara hog nar ST1_LEN ar Over 5",
         "ST1_OUT SKA VARA HOG NAR ST1_LEN AR UNDER 5"),
        ("ST1_OUT ska vara hog nar ST1_LEN ar hog",
         "ST1_OUT ska vara lag nar ST1_LEN ar over 5",
         "ST1_OUT ska vara hog nar ST1_LEN ar over")),

    # ---- reparationsslingan och registret --------------------------------
    "svc/vc_assist_svc/plc/reparation.py::_MARKNING": ("findall",
        ("[DOM-003/F2]", "[deklaration/-]"),
        ("[DOM-003]", "[DOM 003/F2]", "[a/b/F2]", "DOM-003/F2")),
    "svc/vc_assist_svc/skuld.py::_NAMNER_M": ("findall",
        ("se M-70", "matt i M-100"),
        ("M70", "AM-70", "M-", "m-70")),

    # ---- kartan och ST-lagret -------------------------------------------
    "svc/vc_assist_svc/plc/signalkarta.py::_ADRESS": ("match",
        # LAGAT 2026-09-05: IEC 61131-3 ar skiftlagesokansligt.
        ("%QX0.0", "%qx0.0", "%IW10", "%iw10"),
        ("%ZX0.0", "QX0.0", "%Q0.0", "%QX", "%QX0.0.0.0.0")),
    "svc/vc_assist_svc/st/lexer.py::_ADRESS": ("match",
        ("%IX0.0", "%qw10", "%MD3"),
        ("%ZX0", "IX0.0", "%I", "%IXa")),
    "svc/vc_assist_svc/st/sekvens.py::_IDENT": ("match",
        ("Steg1", "sTeg_2"),
        ("1Steg", "steg-1", "_steg", "steg 1")),

    # ---- verktygsschemat -------------------------------------------------
    "svc/vc_assist_svc/verktyg/schema.py::_NAMN": ("match",
        ("las_signal", "a1"),
        ("LasSignal", "1x", "las-signal", "_las")),
    "svc/vc_assist_svc/verktyg/schema.py::_VERSION": ("match",
        ("1.0", "12.34"),
        ("1", "1.2.3", "v1.2", "1.")),
}


def test_bevisen_gor_det_de_lovar():
    """Trasig fixtur for BEVISTABELLEN sjalv.

    Varje strang provas mot det LEVANDE kompilerade monstret, med den metod
    koden faktiskt anvander. Ett bevis som pastar att monstret fyrar och det
    inte gor det faller har - och det ar samma prov som faller den dag nagon
    andrar monstret utan att veta vad det skulle lasa.
    """
    fel = MB.granska_bevis(BEVIS, _ROT)
    assert fel == [], "\n  ".join([""] + fel)


def test_bevistabellen_pekar_bara_pa_monster_som_avgor_en_dom():
    """Ett bevis for ett tolkande monster raknas inte in i taket."""
    fel = [n for n in BEVIS if n not in MB.DOMANDE]
    assert fel == [], (
        "de har nycklarna star i BEVIS men ar inte klassade som domande: %s"
        % ", ".join(sorted(fel)))


def test_ingen_bevispost_har_bara_en_halva():
    """Bada halvorna, alltid. En halv bevisning ar inte halvt sa bra."""
    halva = MB.halv_bevisning(BEVIS)
    assert halva == [], (
        "de har har bara den ena halvan: %s" % ", ".join(halva))


def test_klassningen_pekar_pa_monster_som_finns():
    """Ytan far krympa - men da med vett, inte tyst.

    Byter nagon namn pa ett klassat monster, eller tar bort det, faller det
    har provet i stallet for att monstret tyst slutar raknas.
    """
    saknade = MB.saknade_i_ytan(_ROT)
    assert saknade == [], (
        "klassade i M-105 men finns inte langre i kallan:\n  %s"
        % "\n  ".join(saknade))


# Sa manga av de monster som AVGOR EN DOM som saknar tvasidig bevisning.
#
# MATT 2026-09-05 (M-105). Ytan ar 116 monster pa modulniva under svc/ och
# ext/. 16 tolkar en fil Visual Components sjalvt skrivit; 100 avgor en dom.
# Av de 100 har 42 nu bade ett prov som visar att de FYRAR och ett som visar
# att de INTE fyrar. 58 har det inte.
#
# Talet ar inte satt till noll, och det ar med flit: att skriva 58 prov i
# blindo hade varit att uppfinna vad monstren SKA lasa i stallet for att ta
# reda pa det, och det ar precis den skuld sparren finns for. De 42 ar de 32
# instrumenteringen pekade ut som ensidiga eller aldrig korda, plus dem som
# lagades och deras narmaste grannar i samma fil.
#
# Talet far BARA ga nedat.
UTAN_BEVIS = 58


def test_sparren_bara_krymper():
    utan = MB.utan_bevis(BEVIS, _ROT)
    assert len(utan) <= UTAN_BEVIS, (
        "%d domande monster saknar tvasidig bevisning, taket ar %d. "
        "Nya:\n  %s" % (len(utan), UTAN_BEVIS, "\n  ".join(utan)))


def test_sparren_ar_inte_slappare_an_verkligheten():
    """Ett tak som ligger over verkligheten mater ingenting.

    Samma regel som troskelskulden och skuldregistret: sjunker talet ska taket
    sankas, annars slutar sparren fanga nasta gang nagon glider.
    """
    utan = MB.utan_bevis(BEVIS, _ROT)
    assert len(utan) == UTAN_BEVIS, (
        "verkligheten ar %d men taket sager %d - skriv ned taket i "
        "test_monsterbevis.py" % (len(utan), UTAN_BEVIS))


def test_klassningen_delar_hela_den_matta_ytan():
    """116 monster, 100 domande och 16 tolkande. Inget dubbelraknat."""
    assert len(MB.DOMANDE) == 100
    assert len(MB.TOLKANDE) == 16
    assert not (MB.DOMANDE & MB.TOLKANDE)
    assert len(MB.YTAN) == 116
