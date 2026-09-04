# -*- coding: utf-8 -*-
"""L1: förloppsytan — vad användaren ser medan systemet arbetar.

Fas 17:s grind, ordagrant ur `70_faser.md`:

    Medan en körning pågår kan användaren se vad som händer, vilken grind som
    fällde och varför, och vad systemet INTE vet. Trasigt fall: ett fällt
    läge får aldrig se ut som ett arbetande.

Sista raden är den svåra, och den är hela skälet till att grinden dömer PARET
protokoll och text i stället för att bara rendera. En förloppsvisning som
snurrar vidare efter ett fall producerar tillit som inte är motiverad, och det
är samma felklass kopplaren redan skyddar mot när den ger upp efter tre raka
fel i stället för att mala vidare mot en död PLC (M-39).

Provet bär tre TRASIGA RENDERARE, en per krav på formen. Var och en ser
rimlig ut, och var och en är precis det fel någon skulle göra i god tro.
Ingen av dem får passera.
"""
import os
import re
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import guldgrind                                # noqa: E402
from vc_assist_svc.forlopp import (ARBETAR, AVBRUTET, EJ_STARTAT,  # noqa: E402
                                   FALLET, Forlopp, Forloppsfel, KLART,
                                   OBLIGATORISKA_SEKTIONER, PAGAR_MARKOR,
                                   RACKVIDDEN, REGLER, RUBRIK_VET_INTE,
                                   SAKNAS, SORTER, SPECADE_SORTER,
                                   TILLAGDA_SORTER, TYST, VANTAR, granska,
                                   granska_eller_kasta, rendera,
                                   saknade_sektioner)


class Klocka(object):
    """En klocka som står still tills provet flyttar den."""

    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += float(s)
        return self.t


OGONDOM = "\n".join([
    "EYES v1",
    "TEMPLATE plockstation",
    "RUN 2026-09-04T12:00:00 DUR 12.500s SAMPLES 250 RATE 20.0Hz",
    "SECTION MOTION",
    "GRIP FORMED t=0.950s dist=12.0mm",
    "CARRY RIGID rot=0.0deg span=3.100s",
    "PLACE IN_TARGET err=1.5mm z=0.900m",
    "SECTION HONESTY",
    "TELEPORT_TRANSFER OK",
    "BLOWUP OK",
    "UNDERGROUND OK",
    "NEVER_GRIPPED OK",
    "SECTION LIMITS",
    "NOT_SIMULATED sensor_bounce",
    "NOT_SIMULATED actuator_dynamics",
    "NOT_SIMULATED fieldbus_jitter",
    "NOT_SIMULATED degraded_modes",
    "NOT_SIMULATED real_hardware",
    "RESOLUTION sample=50.0ms read=9.9ms join=1.7ms RUN phase=2.0ms",
    "EYES VERDICT PASS allt inom tolerans",
])

# Samma rapport, men ärlighetsgrinden har aldrig kört. Den ser ut som en dom.
OGONDOM_UTAN_ARLIGHET = "\n".join([
    "EYES v1",
    "TEMPLATE plockstation",
    "RUN 2026-09-04T12:00:00 DUR 12.500s SAMPLES 250 RATE 20.0Hz",
    "SECTION MOTION",
    "GRIP FORMED t=0.950s dist=12.0mm",
    "EYES VERDICT PASS allt inom tolerans",
])

GRINDORD = "\n".join([
    "STATION ST010, deklarationsmatchning",
    "rad 12: [ODEKLARERAD/F4] taggen ST010_KLAR finns inte i signalkartan",
    "rad 18: [RIKTNING/F4] ST010_START ar deklarerad som utgang, kartan sager ingang",
    "2 anmarkningar",
])


# --------------------------------------------------------------- byggare

def arbetande(k=None):
    k = k or Klocka()
    f = Forlopp("o-17", "Bygg en plockstation som klarar 400 detaljer i "
                        "timmen.", klocka=k)
    f.plan(["ladda_band", "ladda_robot", "koppla_granssnitt", "generera_st"])
    k.tick(0.2)
    f.steg_borjar("ladda_band")
    k.tick(0.3)
    f.steg_klart("ladda_band", 12.0)
    k.tick(0.2)
    f.steg_borjar("ladda_robot")
    return f, k


def fallen(k=None):
    f, k = arbetande(k)
    k.tick(0.4)
    f.grind("statisk_analys", True)
    k.tick(0.1)
    f.grind("deklarationsmatchning", False, GRINDORD)
    k.tick(0.1)
    f.fall("kopplaren gav upp efter 3 raka fel; sista: IOError: OPC UA "
           "svarar inte")
    f.vet_inte("kompilering", "ej kord; deklarationsmatchning fallde forst")
    return f, k


def klar(k=None):
    f, k = arbetande(k)
    k.tick(0.3)
    f.steg_klart("ladda_robot", 9.0)
    for namn in ("koppla_granssnitt", "generera_st"):
        k.tick(0.1)
        f.steg_borjar(namn)
        k.tick(0.2)
        f.steg_klart(namn, 5.0)
    k.tick(0.2)
    f.grind("statisk_analys", True)
    f.grind("deklarationsmatchning", True)
    f.grind("anropsvalidering", True)
    f.grind("kompilering", True)
    k.tick(0.5)
    f.dom(OGONDOM)
    f.guld("GOLD gold_verified_core (1 av 1 celler gav PASS)")
    f.svar("Stationen är byggd och ögat sa PASS.")
    return f, k


# ===================================================================
#  DE TRE TRASIGA RENDERARNA
# ===================================================================

def renderare_som_snurrar_vidare(f):
    """TRASIG 1: körningen föll, men visningen påstår att den arbetar.

    Det är fasens egen trasiga fixtur. Renderaren är skriven precis som någon
    skulle skriva den i god tro: den frågar efter det pågående steget och
    skriver ut hur länge det pågått, utan att först fråga vilket läge
    körningen är i. Resultatet är en snurrande symbol över en död körning.
    """
    steg = f.pagaende_steg()
    rader = ["LÄGE: %s" % ARBETAR,
             "uppdrag %s: %s" % (f.order_id, f.uppgift),
             "tid: t+%.1f s, senaste händelsen GRIND för 0.1 s sedan"
             % (f.klocka() - f.t0)]
    if steg is not None:
        rader.append("  %s %s %.1f s"
                     % (steg.namn, PAGAR_MARKOR, f.klocka() - steg.t_start))
    rader.append("HÄNDELSER: %d totalt, visar %d"
                 % (len(f.handelser), len(f.handelser)))
    for h in f.handelser:
        rader.append("  " + h.rad(f.t0))
    rader.append("%s %d poster" % (RUBRIK_VET_INTE, len(f.ovissheter)))
    for o in f.ovissheter:
        rader.append("    %s  %s" % (o.namn, o.skal))
    return "\n".join(rader)


def renderare_som_skriver_om_grinden(f):
    """TRASIG 2: grindens dom skrivs om på vägen ut.

    Renderaren gör tre saker som var för sig ser omtänksamma ut: den kortar
    långa grindutdata, normaliserar radbrytningar och byter grindens
    fackspråk mot en vänlig mening. Tillsammans är de exakt den omskrivning
    som gjorde att en positionsdom underkände 2 av 4 medan ögat visade 4 av 4.
    """
    text = rendera(f)
    for h in f.handelser:
        if h.sort != "GRIND" or not h.ordagrant:
            continue
        forsta = h.ordagrant.splitlines()[0]
        mjukt = ("Grinden %s hittade några anmärkningar (%s ...). Se loggen "
                 "för detaljer." % (h.steg, forsta[:40]))
        text = text.replace(h.ordagrant, mjukt)
    return text


def renderare_utan_arlighetsbesked(f):
    """TRASIG 3: en dom utan ärlighetsavsnitt visas som en vanlig dom.

    Renderaren skriver ut ögats text ordagrant — den ljuger inte om ETT ord.
    Den utelämnar bara beskedet att `SECTION HONESTY` aldrig fanns, och
    därmed att ärlighetsgrinden aldrig kört. Domen ser ut som en dom.
    Guldgrinden har samma regel för `HONESTY` och av samma skäl.
    """
    text = rendera(f)
    ut = []
    for rad in text.splitlines():
        if rad.startswith("SEKTIONEN ") and " SAKNAS " in rad:
            continue
        if rad.lstrip().startswith("sektion "):
            continue
        ut.append(rad)
    return "\n".join(ut)


# ===================================================================
#  1. Läget är härlett, och FALLET är absorberande
# ===================================================================

def test_ett_tomt_forlopp_ar_inte_arbetande():
    f = Forlopp("o-1", "x", klocka=Klocka())
    assert f.lage == EJ_STARTAT


def test_ett_forlopp_med_ett_steg_som_pagar_arbetar():
    f, _k = arbetande()
    assert f.lage == ARBETAR


def test_ett_fallet_forlopp_ar_fallet():
    f, _k = fallen()
    assert f.lage == FALLET


def test_ett_fall_gar_inte_att_arbeta_bort():
    """FALLET ar absorberande. Varje senare handelse kan komma in, men ingen
    av dem far gora korningen arbetande igen."""
    f, k = fallen()
    for sort in ("VERKTYG_START", "VERKTYG_KLART", "OGAT_PROVTAR", "DOM",
                 "GULD", "SVAR", "HJARTSLAG"):
        k.tick(0.1)
        f.lagg(sort, "en senare handelse")
        assert f.lage == FALLET, sort


def test_ett_svar_efter_ett_fall_gor_inte_korningen_klar():
    f, k = fallen()
    k.tick(0.1)
    f.svar("Stationen är byggd.")
    assert f.lage == FALLET


def test_ett_avbrott_ar_inte_ett_arbete():
    f, k = arbetande()
    k.tick(0.1)
    f.avbruten("operatören avbröt")
    assert f.lage == AVBRUTET


def test_en_obesvarad_kopost_ar_inte_ett_arbete():
    """En plan som star och vantar pa operatorens godkannande ARBETAR inte.
    En visning som sager att den gor det later operatoren vanta pa sig sjalv."""
    f, k = arbetande()
    k.tick(0.1)
    f.ko_vantar("q1", "load_component('band')")
    assert f.lage == VANTAR
    k.tick(0.1)
    f.ko_godkand("q1")
    assert f.lage == ARBETAR


def test_ett_levererat_svar_ar_klart():
    f, _k = klar()
    assert f.lage == KLART


def test_lagena_ar_de_deklarerade():
    from vc_assist_svc.forlopp import LAGEN
    for f, _k in (arbetande(), fallen(), klar()):
        assert f.lage in LAGEN


# ===================================================================
#  2. Ett hjärtslag är inte framsteg
# ===================================================================

def test_tystnad_over_taket_ger_laget_TYST():
    f, k = arbetande()
    k.tick(f.tystnadstak + 0.1)
    assert f.lage == TYST


def test_ett_hjartslag_nollar_inte_tystnadsklockan():
    """Trasig fixtur for hjartslaget sjalvt.

    Raknas hjartslaget som framsteg star laget kvar pa ARBETAR i all
    evighet: varje puls nollar klockan. Matt i M-64 med 600 pulser.
    """
    f, k = arbetande()
    k.tick(f.tystnadstak + 0.1)
    arbetande_avlasningar = 0
    for _ in range(600):
        f.puls()
        k.tick(1.0)
        if f.lage == ARBETAR:
            arbetande_avlasningar += 1
    assert arbetande_avlasningar == 0, (
        "%d avläsningar sa ARBETAR trots att bara hjärtslag hänt"
        % arbetande_avlasningar)
    assert f.lage == TYST


def test_hjartslaget_bar_vad_som_pagick_och_hur_lange():
    f, k = arbetande()
    k.tick(7.0)
    h = f.puls()
    assert h is not None
    assert "VERKTYG_START" in h.text
    assert "7.0 s" in h.text


def test_inget_hjartslag_under_taket():
    f, k = arbetande()
    k.tick(f.tystnadstak - 0.1)
    assert f.puls() is None


# ===================================================================
#  3. Formen: rader, "N totalt, visar M", och saknas
# ===================================================================

def test_laget_star_pa_forsta_raden():
    for f, _k in (arbetande(), fallen(), klar()):
        assert rendera(f).splitlines()[0] == "LÄGE: %s" % f.lage


def test_en_trimmad_handelselista_sager_hur_mycket_den_dolde():
    f, k = arbetande()
    for i in range(40):
        k.tick(0.01)
        f.lagg("OGAT_PROVTAR", "%d prov" % i)
    text = rendera(f)
    m = re.search(r"HÄNDELSER: (\d+) totalt, visar (\d+)", text)
    assert m, text
    totalt, visade = int(m.group(1)), int(m.group(2))
    assert totalt == len(f.handelser)
    assert visade < totalt
    assert "... %d till, ej visade." % (totalt - visade) in text


def test_en_handelse_med_nagon_annans_ord_trimmas_aldrig_bort():
    f, k = fallen()
    for i in range(80):
        k.tick(0.01)
        f.lagg("OGAT_PROVTAR", "%d prov" % i)
    text = rendera(f)
    assert GRINDORD in text
    assert granska(f, text).ok


def test_en_flerradig_felnyckel_nar_anvandaren_hel():
    """Trasig fixtur for RADFORMEN: ett verktygsfel med en stackspårning far
    inte klippas till sin forsta rad pa vagen ut. Radlistan kortar den till
    en rad, och da MASTE hela texten sta i ett eget block."""
    spar = ("BryggFel: E_EXEC\n"
            "  Traceback (most recent call last):\n"
            '    File "<exec>", line 3, in <module>\n'
            "  AttributeError: 'NoneType' object has no attribute 'Value'")
    f, k = arbetande()
    k.tick(0.1)
    f.steg_foll("ladda_robot", spar)
    text = rendera(f)
    assert spar in text, "felnyckeln nadde inte anvandaren hel"
    assert granska(f, text).ok
    # och radlistan bar fortfarande EN rad per handelse
    handelserader = [r for r in text.splitlines()
                     if r.startswith("  t+") and "VERKTYG_FEL" in r]
    assert len(handelserader) == 1, handelserader
    assert "\n" not in handelserader[0]
    assert handelserader[0].endswith("...")


def test_en_dom_som_saknas_sags_saknas_aldrig_tomt():
    f, _k = arbetande()
    text = rendera(f)
    assert "ÖGATS DOM (grind 5): %s" % SAKNAS in text
    assert "GULDBESLUT: %s" % SAKNAS in text


def test_en_uppgift_som_saknas_sags_saknas():
    f = Forlopp("o-1", "", klocka=Klocka())
    f.plan(["a"])
    assert "uppdrag o-1: %s" % SAKNAS in rendera(f)


# Ingen egen rad i visningen far vara bredare an sa har. MATT i M-64: 100
# tecken ryms i ett normalt terminalfonster utan radbrytning, och en visning
# som bryter rader sjalv blir olaslig i den yta som faktiskt visar den. Nagon
# ANNANS ord raknas inte: de skrivs ordagrant och far vara hur breda som helst.
MAX_RADBREDD = 100


@pytest.mark.parametrize("byggare", [arbetande, fallen, klar])
def test_ingen_egen_rad_ar_bredare_an_ett_terminalfonster(byggare):
    f, _k = byggare()
    text = rendera(f)
    for ord_ in f.ordagranna():
        text = text.replace(ord_, "")
    breda = [(len(r), r) for r in text.splitlines() if len(r) > MAX_RADBREDD]
    assert not breda, "\n".join("%d tecken: %s" % b for b in breda)


def test_visningen_ar_rader_inte_json():
    text = rendera(fallen()[0])
    assert "{" not in text and "}" not in text


class Raknande(Forlopp):
    """Ett forlopp som raknar hur ofta nagon fragar efter dess lage."""

    def __init__(self, *a, **kw):
        Forlopp.__init__(self, *a, **kw)
        self.lasningar = 0

    @property
    def lage(self):
        self.lasningar += 1
        return Forlopp.lage.fget(self)


def test_visningen_raknar_sitt_lage_exakt_en_gang():
    """En visning som raknar sitt eget tillstand tva ganger kan motsaga sig
    sjalv: klockan hinner ga mellan avlasningarna, och huvudet sager ARBETAR
    medan kroppen sager TYST. Laget lases en gang och skickas ned."""
    k = Klocka()
    f = Raknande("o-1", "x", klocka=k)
    f.plan(["a", "b"])
    k.tick(0.2)
    f.steg_borjar("a")
    f.lasningar = 0
    rendera(f)
    assert f.lasningar == 1, "rendera() lasta laget %d ganger" % f.lasningar


def test_grinden_raknar_sitt_lage_exakt_en_gang():
    k = Klocka()
    f = Raknande("o-1", "x", klocka=k)
    f.plan(["a", "b"])
    k.tick(0.2)
    f.steg_borjar("a")
    text = rendera(f)
    f.lasningar = 0
    granska(f, text)
    assert f.lasningar == 1, "granska() lasta laget %d ganger" % f.lasningar


# ===================================================================
#  4. Vad systemet INTE vet
# ===================================================================

def test_rackvidden_star_i_varje_visning_ocksa_en_som_gick_igenom():
    """50_grindar.md: ogat ar felfinnande, aldrig bevis. En korning som inte
    provat sensorstuds ska saga det, inte tiga."""
    for f, _k in (arbetande(), fallen(), klar()):
        text = rendera(f)
        for _nyckel, namn, _skal in RACKVIDDEN:
            assert namn in text, "%s saknas i läget %s" % (namn, f.lage)


def test_rackvidden_ar_ogats_egen_lista():
    """Ogats kontrakt kraver sedan v2 en NOT_SIMULATED-rad per post i
    EJ_SIMULERAT, och det ar samma fem saker ur samma stycke i
    50_grindar.md. Tva listor som ska vara samma lista gar isar tyst."""
    sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
    import oga_kontrakt as K
    assert tuple(n for n, _namn, _skal in RACKVIDDEN) == K.EJ_SIMULERAT


def test_rackviddens_skal_namner_ogats_eget_ord():
    """Den som laser ogats rapport bredvid visningen ska se att
    NOT_SIMULATED sensor_bounce och raden 'sensorstuds' ar samma sak."""
    f, _k = arbetande()
    text = rendera(f)
    for nyckel, _namn, _skal in RACKVIDDEN:
        assert nyckel in text, "%s namns inte i visningen" % nyckel


def test_avsnittet_om_ovisshet_ar_aldrig_tomt():
    f = Forlopp("o-1", "x", klocka=Klocka())
    f.plan(["a"])
    text = rendera(f)
    assert RUBRIK_VET_INTE in text
    assert "(inget utöver räckvidden)" in text
    assert "sensorstuds" in text


def test_en_ovisshet_utan_skal_gar_inte_att_skapa():
    f = Forlopp("o-1", "x", klocka=Klocka())
    with pytest.raises(Forloppsfel):
        f.vet_inte("kompilering", "")


def test_en_grind_som_inte_kordes_star_som_ovisshet_inte_som_gron():
    f, _k = fallen()
    text = rendera(f)
    assert "kompilering" in text
    assert "ej kord; deklarationsmatchning fallde forst" in text


# ===================================================================
#  5. Sektionslistan får inte glida från guldgrindens
# ===================================================================

def test_sektionslistan_ar_guldgrindens():
    """Listorna ar kopierade, inte importerade (samma val som
    stationsgrind.py). Da maste ett prov halla ihop dem."""
    assert OBLIGATORISKA_SEKTIONER == guldgrind.OBLIGATORISKA_SEKTIONER


def test_en_dom_utan_honesty_upptacks():
    assert saknade_sektioner(OGONDOM) == ()
    assert saknade_sektioner(OGONDOM_UTAN_ARLIGHET) == ("HONESTY", "LIMITS")


# ===================================================================
#  6. Standardytan passerar sin egen grind i varje läge
# ===================================================================

@pytest.mark.parametrize("byggare", [arbetande, fallen, klar])
def test_standardytan_passerar_grinden(byggare):
    f, _k = byggare()
    dom = granska(f)
    assert dom.ok, dom.text()


def test_standardytan_passerar_grinden_ocksa_nar_ogat_saknar_honesty():
    f, k = arbetande()
    k.tick(0.3)
    f.dom(OGONDOM_UTAN_ARLIGHET)
    dom = granska(f)
    assert dom.ok, dom.text()
    text = rendera(f)
    assert "SEKTIONEN HONESTY SAKNAS I ÖGATS RAPPORT" in text


def test_standardytan_passerar_grinden_i_ett_tyst_lage():
    f, k = arbetande()
    k.tick(30.0)
    f.puls()
    dom = granska(f)
    assert dom.ok, dom.text()
    assert "LÄGE: %s" % TYST in rendera(f)


def test_granska_eller_kasta_slapper_igenom_en_ren_yta():
    f, _k = klar()
    assert granska_eller_kasta(f) == rendera(f)


# ===================================================================
#  7. DE TRE TRASIGA FIXTURERNA — de måste falla
# ===================================================================

def test_TRASIG_en_fallen_korning_som_ser_ut_att_arbeta_falls():
    """Fasens egen trasiga fixtur, ordagrant ur 70_faser.md:
    'ett fällt läge får aldrig se ut som ett arbetande'."""
    f, _k = fallen()
    text = renderare_som_snurrar_vidare(f)
    dom = granska(f, text)
    assert not dom.ok, "en snurrande visning över en död körning passerade"
    assert "Y1" in dom.brutna, dom.text()
    assert "Y2" in dom.brutna, dom.text()
    assert PAGAR_MARKOR in text          # felet finns verkligen i texten
    assert f.lage == FALLET              # och protokollet vet bättre


def test_TRASIG_en_omskriven_grinddom_falls_tecken_for_tecken():
    """En omskrivning pa vagen till anvandaren ar samma fel som en
    omskrivning pa vagen till modellen (50_grindar.md)."""
    f, _k = fallen()
    text = renderare_som_skriver_om_grinden(f)
    dom = granska(f, text)
    assert not dom.ok, "en omskriven grinddom nådde användaren"
    assert "Y4" in dom.brutna, dom.text()
    assert GRINDORD not in text
    # Omskrivningen ser vanlig ut: den bar till och med grindens forsta rad.
    assert "deklarationsmatchning" in text


def test_TRASIG_en_korning_utan_arlighetsavsnitt_falls():
    """Samma regel guldgrinden redan har for HONESTY: en rapport utan den
    sektionen har ingen arlighetsgrind alls, och den sag ut som guld."""
    f, k = arbetande()
    k.tick(0.3)
    f.dom(OGONDOM_UTAN_ARLIGHET)
    text = renderare_utan_arlighetsbesked(f)
    dom = granska(f, text)
    assert not dom.ok, "en dom utan ärlighetsgrind visades som en dom"
    assert "Y6" in dom.brutna, dom.text()
    assert any("HONESTY" in b.vad for b in dom.brott), dom.text()
    # Ogats egna ord ar OFORANDRADE i den har renderaren. Felet ar inte en
    # omskrivning utan en utelamning, och den maste falla for sig.
    assert OGONDOM_UTAN_ARLIGHET in text
    assert "Y4" not in dom.brutna


# ===================================================================
#  8. En trasig fixtur per regel — ingen grind utan en
# ===================================================================

def test_Y1_ett_annat_lage_i_texten_an_i_protokollet_falls():
    f, _k = fallen()
    text = rendera(f).replace("LÄGE: %s" % FALLET, "LÄGE: %s" % ARBETAR, 1)
    assert "Y1" in granska(f, text).brutna


def test_Y2_en_pagaendemarkor_i_ett_stilla_lage_falls():
    f, _k = klar()
    text = rendera(f) + "\n  generera_st %s 2.1 s" % PAGAR_MARKOR
    assert "Y2" in granska(f, text).brutna


def test_Y2_falls_inte_av_nagon_annans_ord():
    """En kompilatorrad som rakar innehalla frasen ar inte visningens
    pastaende. Grinden maste ta bort frammande ord innan den letar."""
    f, k = arbetande()
    k.tick(0.1)
    f.grind("statisk_analys", False,
            "varning: timern %s 2.1 s utan att loysa ut" % PAGAR_MARKOR)
    k.tick(0.1)
    f.fall("grind 2 fällde")
    dom = granska(f)
    assert dom.ok, dom.text()


def test_Y3_ett_fall_utan_skal_gar_inte_att_foras():
    f, _k = arbetande()
    with pytest.raises(Forloppsfel):
        f.fall("   ")


def test_Y3_ett_bortskrivet_fallskal_falls():
    f, _k = fallen()
    text = rendera(f).replace(f.fallskal(), "något gick fel")
    brutna = granska(f, text).brutna
    assert "Y3" in brutna and "Y4" in brutna


def test_Y5_en_visning_utan_avsnittet_om_ovisshet_falls():
    f, _k = klar()
    text = "\n".join(r for r in rendera(f).splitlines()
                     if not r.startswith(RUBRIK_VET_INTE))
    assert "Y5" in granska(f, text).brutna


def test_Y5_en_visning_som_tappar_en_rackviddspost_falls():
    f, _k = klar()
    text = "\n".join(r for r in rendera(f).splitlines()
                     if "sensorstuds" not in r)
    assert "Y5" in granska(f, text).brutna


def test_Y7_guld_utan_ogondom_falls():
    f, k = arbetande()
    k.tick(0.2)
    f.guld("GOLD gold_verified_core (1 av 1 celler gav PASS)")
    text = rendera(f).replace("GULDBESLUT UTAN ÖGONDOM, saknar underlag:",
                              "GULDBESLUT:")
    assert "Y7" in granska(f, text).brutna


def test_Y7_standardytan_skriver_ut_att_guldet_saknar_underlag():
    f, k = arbetande()
    k.tick(0.2)
    f.guld("GOLD gold_verified_core (1 av 1 celler gav PASS)")
    dom = granska(f)
    assert dom.ok, dom.text()
    assert "GULDBESLUT UTAN ÖGONDOM" in rendera(f)


def test_Y8_en_tyst_trimning_falls():
    f, k = arbetande()
    for i in range(40):
        k.tick(0.01)
        f.lagg("OGAT_PROVTAR", "%d prov" % i)
    text = rendera(f)
    text = re.sub(r"HÄNDELSER: \d+ totalt, visar (\d+)",
                  lambda m: "HÄNDELSER: %s totalt, visar %s"
                            % (m.group(1), m.group(1)), text)
    text = re.sub(r"\n *\.\.\. \d+ till, ej visade\.", "", text)
    assert "Y8" in granska(f, text).brutna


def test_Y9_ett_hjartslag_som_raknas_som_framsteg_falls():
    """Trasig fixtur: ett forlopp dar HJARTSLAG smugits in i listan over
    handelser som raknas som framsteg. Da star laget kvar pa ARBETAR."""
    import vc_assist_svc.forlopp.handelser as H
    gammal = H.EJ_FRAMSTEG
    try:
        H.EJ_FRAMSTEG = ()
        f, k = arbetande()
        # Hjartslag varje sekund, i tio minuter. Ingenting verkligt hander.
        for _ in range(600):
            k.tick(1.0)
            f.lagg("HJARTSLAG", "lever")
        assert f.lage == ARBETAR, (
            "fixturen provar inget: laget blev inte ARBETAR")
        assert "Y9" in granska(f).brutna
    finally:
        H.EJ_FRAMSTEG = gammal


def test_Y11_ett_levererat_svar_over_en_halvkord_plan_falls():
    """Trasig fixtur: ett svar levereras medan tva steg aldrig kordes, och
    visningen namner dem inte. Varje rad ar sann, helheten ar falsk."""
    f, k = arbetande()
    k.tick(0.3)
    f.steg_klart("ladda_robot", 9.0)
    k.tick(0.2)
    f.svar("Stationen är byggd.")
    okorda = [s.namn for s in f.steg if s.status == "väntar"]
    assert okorda, "fixturen provar inget om varje steg kordes"
    text = "\n".join(r for r in rendera(f).splitlines()
                      if not r.lstrip().startswith("steg "))
    text = re.sub(r"STEG: (\d+) av (\d+) klara, \d+ kördes aldrig",
                  r"STEG: \1 av \2 klara", text)
    brutna = granska(f, text).brutna
    assert "Y11" in brutna, granska(f, text).text()


def test_Y11_standardytan_raknar_de_okorda_stegen():
    f, k = arbetande()
    k.tick(0.3)
    f.steg_klart("ladda_robot", 9.0)
    k.tick(0.2)
    f.svar("Stationen är byggd.")
    dom = granska(f)
    assert dom.ok, dom.text()
    text = rendera(f)
    assert "kördes aldrig" in text
    assert "steg koppla_granssnitt" in text


def test_Y10_ett_arbetande_lage_utan_besked_om_vad_som_pagar_falls():
    f, _k = arbetande()
    text = "\n".join(r for r in rendera(f).splitlines()
                     if not r.startswith("tid: "))
    assert "Y10" in granska(f, text).brutna


def test_alla_regler_har_minst_en_trasig_fixtur():
    """En grind utan en trasig fixtur ar en forhoppning som fatt ett namn.

    Provet letar upp reglerna i den har filens egna prov och kraver att var
    och en av dem namns i minst ett prov som kraver att den BRYTS.
    """
    with open(__file__, encoding="utf-8") as fh:
        kalla = fh.read()
    utan = [r for r in REGLER
            if ('"%s" in dom.brutna' % r) not in kalla
            and ('"%s" in granska' % r) not in kalla
            and ("assert %r in brutna" % r) not in kalla
            and ('%s" in brutna' % r) not in kalla]
    assert not utan, "regler utan en trasig fixtur: %s" % ", ".join(utan)


# ===================================================================
#  9. Den slutna händelselistan
# ===================================================================

def test_handelselistan_ar_sluten():
    f = Forlopp("o-1", "x", klocka=Klocka())
    with pytest.raises(Forloppsfel):
        f.lagg("KLART_ANTAR_JAG", "en sort som inte finns")


def test_tilläggen_till_den_specade_listan_syns():
    """24_samtalsloopen.md §7 kallar listan sluten. Tva sorter ar tillagda,
    och de star for sig sa att tillagget syns i stallet for att glida in."""
    assert set(SORTER) == set(SPECADE_SORTER) | set(TILLAGDA_SORTER)
    assert TILLAGDA_SORTER == ("FALLET", "GRIND")
    assert len(SPECADE_SORTER) == 17
    for sort in TILLAGDA_SORTER:
        assert sort not in SPECADE_SORTER


def test_en_plan_utan_steg_gar_inte_att_visa():
    f = Forlopp("o-1", "x", klocka=Klocka())
    with pytest.raises(Forloppsfel):
        f.plan([])


def test_en_renderare_som_inte_lamnar_text_avvisas():
    f, _k = klar()
    with pytest.raises(Forloppsfel):
        granska(f, {"lage": "ARBETAR"})
