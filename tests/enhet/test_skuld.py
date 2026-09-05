# -*- coding: utf-8 -*-
"""L1 for skuldregistret, och sparren som bara far ga at ett hall.

Registret genereras, aldrig fors for hand. Proven skyddar tva saker:
att skorden faktiskt hittar skulden, och att antalet matningar UTAN
arlighetsavsnitt bara kan krympa.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import skuld as S                              # noqa: E402

_MATNINGAR = os.path.join(_ROT, "docs", "matningar")

# Sa manga matningar som saknar ett arlighetsavsnitt.
#
# MATT 2026-09-04 (M-70): 1. Det talet ar resultatet av tva saker som gjordes i
# samma svep, och de far inte blandas ihop:
#
#   * 22 matningar fick ett arlighetsavsnitt skrivet at sig (M-01 till M-40).
#   * M-44 och M-47 BAR redan ett, under rubriker monstret inte sag. Monstret
#     var skrivet i ASCII och matningarna i svenska, sa atta av elva grenar
#     kunde aldrig fyra. Lagat i skuld.py, inte genom att duplicera text.
#
# Kvar: ingen. M-50 fick sitt avsnitt 2026-09-05, och taket sanktes till noll
# samma dag - talet far bara ga nedat, sa noll ar nu golvet ocksa.
#
# Talet far BARA ga nedat. Att hoja det ar att skriva en ny matning som inte
# sager vad den inte visar, och det ar precis den skuld registret finns for.
UTAN_ARLIGHETSAVSNITT = 0


def test_sparren_bara_krymper():
    utan = S.matningar_utan_arlighetsavsnitt(_MATNINGAR)
    assert len(utan) <= UTAN_ARLIGHETSAVSNITT, (
        "%d matningar saknar arlighetsavsnitt, taket ar %d. Nya:\n  %s"
        % (len(utan), UTAN_ARLIGHETSAVSNITT, "\n  ".join(utan)))


def test_sparren_ar_inte_slappare_an_verkligheten():
    """Ett tak som ligger over verkligheten mater ingenting.

    Samma regel som troskelskulden: sjunker talet ska taket sanktas, annars
    slutar sparren fanga nasta gang nagon glider.
    """
    utan = S.matningar_utan_arlighetsavsnitt(_MATNINGAR)
    assert len(utan) == UTAN_ARLIGHETSAVSNITT, (
        "verkligheten ar %d men taket sager %d - sank taket i test_skuld.py"
        % (len(utan), UTAN_ARLIGHETSAVSNITT))


# ---- skorden ur en matning -------------------------------------------------

def skriv(tmp_path, namn, text):
    p = tmp_path / namn
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_hittar_ett_arlighetsavsnitt_och_dess_punkter(tmp_path):
    f = skriv(tmp_path, "M-99_prov.md", """# M-99

## Utfall

Allt gick bra.

## Vad som INTE är mätt

* Windows.
* Fler än två signaler.

## Nasta avsnitt

Text.
""")
    poster = S.ur_matning(f)
    assert len(poster) == 1
    assert poster[0].rader == ["Windows.", "Fler än två signaler."]


def test_ett_numrerat_avsnitt_raknas_ocksa(tmp_path):
    """MATT: bade '## 9. Vad som inte ar matt' och '### F9. ...' finns i repot.

    Trasig fixtur for monstret sjalvt: en regex som kraver att rubriken borjar
    med ordet missar de har tyst, och da ser en arlig matning ut som en
    slarvig.
    """
    f = skriv(tmp_path, "M-98_prov.md", "# M-98\n\n## 9. Vad som inte är mätt\n\n* En sak.\n")
    assert S.ur_matning(f)[0].rader == ["En sak."]


@pytest.mark.parametrize("rubrik,punkt", [
    # MATT 2026-09-04 (M-70): var och en av de har fanns i repot och foll.
    ("## Räckvidd", "M-44"),
    ("### Vad rättelserna medvetet INTE gör", "M-44"),
    ("### Vad de här måtten INTE säger", "M-47"),
    ("## Öppen fråga, blockerande för fas 1", "M-04"),
    ("## Trolig orsak, omätt", "M-35"),
    ("## Vad som troligen krävs, och som är OMÄTT", "M-14"),
    ("## Begränsningar", "form"),
    ("## Förbehåll", "form"),
    ("## Oprövat", "form"),
    ("## Öppna frågor", "form"),
    # LIMITS ar guldgrindens obligatoriska sektionsnamn (v2, M-65). Att
    # registret inte sag det betydde att en matning kunde skriva exakt den
    # rubrik systemet KRAVER pa annat hall och anda raknas som tyst.
    ("## LIMITS", "guldgrindens sektionsnamn"),
    ("## LIMITS", "M-84"),
    ("## Limitations", "form"),
])
def test_monstret_ser_rubriker_skrivna_i_riktig_svenska(rubrik, punkt):
    """Trasig fixtur for MONSTRET sjalvt (M-70).

    Foll for alla tio fore lagningen. Monstret var skrivet i ASCII - samma
    translitterering som all kod i repot - medan matningarna ar skrivna med
    a, a och o. Atta av elva grenar kunde darfor aldrig matcha nagonting, och
    tva av dem var tillagda just for att fanga M-44 och M-47.

    En matning som SA vad den inte visade raknades alltsa som en matning som
    inte sa nagot. Samma felklass som M-66 sjalv rattade en gang: ett monster
    som ser ut att matcha, aldrig provat mot texten det ska lasa.
    """
    assert S.ar_arlighetsrubrik(rubrik), "%s (%s)" % (rubrik, punkt)


@pytest.mark.parametrize("rubrik", [
    "## Öppet",
    "## Utfall",
    "## Vad som fungerar",
    "## Talen",
    "## Metod",
])
def test_monstret_godkanner_inte_vilken_rubrik_som_helst(rubrik):
    """Andra halvan av fixturen: en gren som fyrar pa allt mater ingenting.

    "Oppet" star med FLIT pa fel sida. Ett avsnitt som bara heter sa namner
    inte vad som ar oppet, och "Oppet API" ar en lika rimlig rubrik. Se
    gransen i skuld.py.
    """
    assert not S.ar_arlighetsrubrik(rubrik)


def test_avdiakritiken_ror_inte_rubriker_som_redan_ar_ascii(tmp_path):
    """Lagningen far inte andra det som redan fungerade."""
    f = skriv(tmp_path, "M-95_prov.md",
              "# M-95\n\n## Vad som INTE ar matt\n\n* En sak.\n")
    assert S.ur_matning(f)[0].rader == ["En sak."]


def test_en_matning_utan_arlighetsavsnitt_hittas(tmp_path):
    skriv(tmp_path, "M-97_prov.md", "# M-97\n\n## Utfall\n\nAllt gick bra.\n")
    assert S.matningar_utan_arlighetsavsnitt(str(tmp_path)) == ["M-97_prov.md"]


def test_ett_avsnitt_utan_punkter_raknas_som_avsnitt_men_ger_noll_punkter(tmp_path):
    f = skriv(tmp_path, "M-96_prov.md",
              "# M-96\n\n## Vad som INTE är mätt\n\nIngenting, allt är mätt.\n")
    poster = S.ur_matning(f)
    assert len(poster) == 1 and poster[0].antal == 0


# ---- skorden ur koden ------------------------------------------------------

def test_hittar_markorer_i_koden(tmp_path):
    (tmp_path / "m.py").write_text(
        "X = 1  # PRELIMINÄR. Sätts av M-99.\ndef f():\n    pass  # TODO laga\n",
        encoding="utf-8")
    poster = S.ur_kod(str(tmp_path))
    assert len(poster) == 1
    assert poster[0].antal == 2


def test_registret_rapporterar_inte_sig_sjalvt(tmp_path):
    """En grind som far sin egen utdata som indata mater sig sjalv."""
    (tmp_path / "skuld.py").write_text("# TODO\n", encoding="utf-8")
    (tmp_path / "test_skuld.py").write_text("# PRELIMINÄR\n", encoding="utf-8")
    assert S.ur_kod(str(tmp_path)) == []


# ---- registret som helhet --------------------------------------------------

def test_registret_gar_att_bygga_och_bar_bada_kallorna():
    reg = S.bygg(_ROT)
    assert reg["antal_punkter"] > 0
    assert reg["antal_kodmarkorer"] > 0
    t = S.text(reg)
    assert "Genererat" in t
    assert "Markörer i koden" in t
    assert str(len(reg["utan_arlighetsavsnitt"])) in t


def test_registerfilen_pa_disk_ar_aktuell():
    """En generad fil som slutat stamma ar samre an ingen fil.

    Faller det har: kor `PYTHONPATH=svc python3 -m vc_assist_svc.skuld
    --rot . --ut docs/matningar/SKULDREGISTER.md`
    """
    p = os.path.join(_MATNINGAR, "SKULDREGISTER.md")
    assert os.path.exists(p), "registret saknas pa disk"
    pa_disk = open(p, encoding="utf-8").read()
    reg = S.bygg(_ROT)
    # Bara rubrikraderna jamfors: sjalva punkterna andras med varje matning,
    # och ett prov som kraver byte-likhet hade fallit vid varje commit.
    for rad in ("## Mätningar utan ärlighetsavsnitt: %d"
                % len(reg["utan_arlighetsavsnitt"]),):
        assert rad in pa_disk, "registret pa disk ar inaktuellt: saknar %r" % rad


# ---- moduler utan prov -----------------------------------------------------

# MATT 2026-09-05. Tva hinkar, och skillnaden ar inte kosmetisk:
#   inget    ingen provfil alls namner modulen
#   bara_l3  bara en korning under tests/protocol/, som kraver levande VC eller
#            OpenPLC och INTE kors av `pytest tests/enhet` - alltsa ingenting
#            som gar att kontrollera pa en ren maskin
#
# Taken far bara ga NEDAT.
#
# Varfor det inte ocksa finns ett krav pa att taket ska ligga PA verkligheten,
# som troskelskulden har: sex agenter arbetar i repot just nu och lagger till
# moduler vars prov kommer strax efter. Ett exakthetskrav i natt hade gjort
# sviten rod for deras halvfardiga arbete i stallet for att fanga skuld. Kravet
# ska in nar natten lagt sig, och att det inte ar inne AN ar sjalv en skuld -
# den star i M-68.
MODULER_UTAN_PROV = 5
MODULER_BARA_L3 = 3


def test_moduler_utan_prov_bara_krymper():
    u = S.moduler_utan_prov(_ROT)
    assert len(u["inget"]) <= MODULER_UTAN_PROV, (
        "%d moduler har inget prov alls, taket ar %d:\n  %s"
        % (len(u["inget"]), MODULER_UTAN_PROV,
           "\n  ".join("%s (%d rader)" % (f, n) for f, n in u["inget"])))


def test_moduler_med_bara_l3_prov_bara_krymper():
    u = S.moduler_utan_prov(_ROT)
    assert len(u["bara_l3"]) <= MODULER_BARA_L3, (
        "%d moduler provas bara av en L3-korning, taket ar %d:\n  %s"
        % (len(u["bara_l3"]), MODULER_BARA_L3,
           "\n  ".join("%s (%d rader)" % (f, n) for f, n in u["bara_l3"])))


def test_de_tva_hinkarna_ar_skilda(tmp_path):
    """En modul far inte hamna i bada, och inte i fel."""
    for d in ("svc", "tests/enhet", "tests/protocol"):
        os.makedirs(os.path.join(str(tmp_path), d), exist_ok=True)
    (tmp_path / "svc" / "provad.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "svc" / "bara_kord.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "svc" / "ensam.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "enhet" / "t.py").write_text(
        "import provad\n", encoding="utf-8")
    (tmp_path / "tests" / "protocol" / "k.py").write_text(
        "import bara_kord\n", encoding="utf-8")
    u = S.moduler_utan_prov(str(tmp_path))
    assert [f for f, _n in u["inget"]] == [os.path.join("svc", "ensam.py")]
    assert [f for f, _n in u["bara_l3"]] == [os.path.join("svc", "bara_kord.py")]


def test_init_filer_raknas_inte(tmp_path):
    """__init__.py ar limmet och provas genom det den binder."""
    os.makedirs(os.path.join(str(tmp_path), "svc", "p"), exist_ok=True)
    (tmp_path / "svc" / "p" / "__init__.py").write_text("", encoding="utf-8")
    u = S.moduler_utan_prov(str(tmp_path))
    assert u["inget"] == [] and u["bara_l3"] == []


# ---- rattelser som inte syns vid pastaendet --------------------------------

def test_ingen_rattelse_saknar_sin_framatpekare():
    """En rattelse som bara star i den NYARE filen ar for den som redan vet.

    Den som slar upp den gamla matningen far det gamla svaret med full
    trovardighet. Tva mätta fall i det har repot:

      fas 6:s rubrik sa 'halva grinden ar passerad' i over ett dygn medan
      stangningen lag langst ned i samma fil.

      M-34:s tabellrad sa 'matningen fyrar inte' langt efter att M-40 och M-41
      motbevisat den; rattelsen lag i ett arlighetsavsnitt langst ned.
    """
    utan = S.rattelser_utan_framatpekare(_MATNINGAR)
    assert not utan, (
        "matningar som en senare rattar utan att sjalva peka framat:\n  %s"
        % "\n  ".join("%s rattas av %s" % (g, ", ".join(n)) for g, n in utan))


def test_kontrollen_hittar_en_rattelse_utan_pekare(tmp_path):
    """Trasig fixtur for kontrollen sjalv."""
    (tmp_path / "M-01_gammal.md").write_text(
        "# M-01\n\nEtt pastaende.\n", encoding="utf-8")
    (tmp_path / "M-02_ny.md").write_text(
        "# M-02\n\nDen har mätningen rättar M-01.\n", encoding="utf-8")
    assert S.rattelser_utan_framatpekare(str(tmp_path)) == [("M-01", ["M-02"])]


def test_en_gammal_matning_som_pekar_framat_gar_fri(tmp_path):
    (tmp_path / "M-01_gammal.md").write_text(
        "# M-01\n\nEtt pastaende. RATTAD, se M-02.\n", encoding="utf-8")
    (tmp_path / "M-02_ny.md").write_text(
        "# M-02\n\nDen har mätningen rättar M-01.\n", encoding="utf-8")
    assert S.rattelser_utan_framatpekare(str(tmp_path)) == []


def test_monstret_ar_inte_skrivet_i_ASCII_mot_svensk_text():
    """M-70: atta av elva grenar i den forsta versionen var doda.

    De var skrivna i ASCII medan texten ar pa svenska, sa 'rackvidd' kunde
    aldrig matcha 'Räckvidd'. En gren som aldrig fyrar rapporterar noll
    traffar, och noll traffar ser ut som att det inte fanns nagot att hitta.
    """
    for ord_ in ("rättar", "rättad av"):
        assert S._RATTAR.search("Den här mätningen %s M-01." % ord_), ord_
    # Och ASCII-formen ska ocksa ga igenom, for koden skrivs i ASCII.
    assert S._RATTAR.search("Den har matningen rattar M-01.")


# ---- M-numret ar matningens enda identitet ---------------------------------

# Sa manga M-nummer som mer an en matningsfil gor ansprak pa.
#
# MATT 2026-09-05 (M-94): 1. Talet var 3 under den natt det mattes - M-89, M-90
# och M-92 fick var sin andra fil av tre olika agenter inom en timme, ingen av
# dem fel skriven. Det fanns bara ingen grind som stallde fragan "ar numret
# taget?" i skrivogonblicket. Tva av de tre loste sig genom att den har
# matningen flyttade sig sjalv (M-89 -> M-92 -> M-94), och kvar star M-90.
#
# VARFOR DET INTE AR KOSMETIK: `test_troskelharkomst.matningar_som_finns()`
# bygger en MANGD, sa `svc/vc_assist_svc/forlopp/yta.py:63` (`FORLOPPSVERSION =
# 1  # M-90`) ar gron oavsett vilken av de tva M-90 den menade. Och
# `rattelser_utan_framatpekare` bygger `per_nummer[nummer] = fil`, sa den ena
# filens rattelser blir tyst osynliga for grinden.
#
# Talet far BARA ga nedat.
#
# Varfor det INTE ocksa finns ett krav pa att taket ska ligga PA verkligheten,
# som troskelskulden har: samma skal som MODULER_UTAN_PROV ovan - flera agenter
# arbetar i repot samtidigt, och ett exakthetskrav gor sviten rod for deras
# halvfardiga arbete i stallet for att fanga skuld. Att kravet inte ar inne AN
# ar sjalv en skuld, och den star i M-94.
KOLLIDERANDE_NUMMER = 1


def test_inga_nya_nummerkollisioner():
    koll = S.nummerkollisioner(_MATNINGAR)
    assert len(koll) <= KOLLIDERANDE_NUMMER, (
        "%d M-nummer bars av mer an en fil, taket ar %d:\n  %s"
        % (len(koll), KOLLIDERANDE_NUMMER,
           "\n  ".join("%s: %s" % (n, ", ".join(f)) for n, f in koll)))


def test_kontrollen_hittar_tva_filer_pa_samma_nummer(tmp_path):
    """TRASIG FIXTUR for kollisionsgrinden.

    Foll inte fore 2026-09-05, for grinden fanns inte - och just den natten
    hade repot tre sadana par samtidigt.
    """
    (tmp_path / "M-90_ett.md").write_text("# M-90\n", encoding="utf-8")
    (tmp_path / "M-90_tva.md").write_text("# M-90\n", encoding="utf-8")
    (tmp_path / "M-91_ensam.md").write_text("# M-91\n", encoding="utf-8")
    assert S.nummerkollisioner(str(tmp_path)) == [
        ("M-90", ["M-90_ett.md", "M-90_tva.md"])]


def test_nollsiffriga_varianter_av_samma_nummer_ar_samma_nummer(tmp_path):
    """M-9 och M-09 ar samma matning, och en grind som inte ser det ar blind
    for just den kollision som ar latt att skriva."""
    (tmp_path / "M-9_ett.md").write_text("# M-9\n", encoding="utf-8")
    (tmp_path / "M-09_tva.md").write_text("# M-09\n", encoding="utf-8")
    assert [n for n, _f in S.nummerkollisioner(str(tmp_path))] == ["M-09"]


def test_en_katalog_utan_kollisioner_ger_tom_lista(tmp_path):
    """Andra halvan av fixturen: en grind som fyrar pa allt mater ingenting."""
    for namn in ("M-01_a.md", "M-02_b.md", "RESERVERADE.md", "las_mig.txt"):
        (tmp_path / namn).write_text("# x\n", encoding="utf-8")
    assert S.nummerkollisioner(str(tmp_path)) == []


# ---- modulnamnet maste sta som ett eget ord --------------------------------

def test_en_modul_raknas_inte_som_provad_av_ett_langre_ord(tmp_path):
    """TRASIG FIXTUR for tackningsproxyn (M-94).

    Foll INTE fore 2026-09-05: kriteriet var `stam in text`, alltsa en ren
    delstrang, och da rackte ordet "anlaggningssignaler" i en provfil for att
    `bank/anlaggning.py` skulle raknas som provad. Coverage matte samma dag 0
    av modulens 336 satser.

    Provet visar bada halvorna: delstrangen racker inte, det egna ordet racker.
    """
    for d in ("svc", "tests/enhet", "tests/protocol"):
        os.makedirs(os.path.join(str(tmp_path), d), exist_ok=True)
    (tmp_path / "svc" / "anlaggning.py").write_text("x = 1\n", encoding="utf-8")
    prov = tmp_path / "tests" / "enhet" / "t.py"

    # Bara som delstrang i ett langre ord: modulen ar OPROVAD.
    prov.write_text("def _anlaggningssignaler():\n    pass\n", encoding="utf-8")
    u = S.moduler_utan_prov(str(tmp_path))
    assert [f for f, _n in u["inget"]] == [os.path.join("svc", "anlaggning.py")], (
        "delstrangen 'anlaggning' inne i '_anlaggningssignaler' raknades som "
        "ett prov - det ar exakt hålet den har grinden finns for")

    # Som eget ord: modulen ar provad.
    prov.write_text("import anlaggning\n", encoding="utf-8")
    assert S.moduler_utan_prov(str(tmp_path))["inget"] == []


@pytest.mark.parametrize("provtext,provad", [
    ("import bas\n", True),
    ("from x import bas\n", True),
    ("# se bas.py\n", True),
    ("basen ar bred\n", False),
    ("kompbas = 1\n", False),
    ("bas_utokad = 1\n", False),
])
def test_ordgransen_pa_en_kort_stam(tmp_path, provtext, provad):
    """Korta stammar bar hela halet: `bas`, `fel` och `text` finns inne i
    hundratals svenska ord, sa delstrangskriteriet gjorde dem provade av en
    slump. Ingen behovde ta den vagen medvetet - den var alltid oppen."""
    for d in ("svc", "tests/enhet", "tests/protocol"):
        os.makedirs(os.path.join(str(tmp_path), d), exist_ok=True)
    (tmp_path / "svc" / "bas.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "tests" / "enhet" / "t.py").write_text(provtext, encoding="utf-8")
    u = S.moduler_utan_prov(str(tmp_path))
    assert (u["inget"] == []) is provad, provtext
