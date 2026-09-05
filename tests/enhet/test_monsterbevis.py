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
