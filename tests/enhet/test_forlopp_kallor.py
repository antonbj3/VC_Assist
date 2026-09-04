# -*- coding: utf-8 -*-
"""L1: att driva förloppsytan från ett arbete som PÅGÅR.

Mätt läge före den här filen (M-64): systemet hade **sju rapportytor**, och
**noll** av dem gav en text en människa kan läsa medan körningen pågår. Två
gick att läsa live men lämnade `dict`; fem fanns inte förrän det drivande
anropet hade returnerat. Det är hela glappet fas 17 stänger.

Provet driver förloppet från de riktiga delarna — stationsgrinden,
reparationsslingan, kopplaren, guldgrinden och planens körare — utan VC, utan
nät och utan kompilator. Två saker mäts:

1. **Ytan går att läsa MELLAN två varv**, inte bara när allt är över.
2. **Grindens ord kopieras, aldrig sammanfattas.** Varje översättning är just
   det ställe där ett ord kan bytas ut, så varje jämförelse här är tecken för
   tecken.

Trasiga fixturer: en källa som sammanfattar grindens utdata, en som räknar en
överhoppad grind som grön, och en kopplare som ger upp medan visningen
fortfarande påstår att den arbetar.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "ext", "vc_addon")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc import guldgrind as G                           # noqa: E402
from vc_assist_svc.forlopp import (ARBETAR, FALLET, Forlopp,       # noqa: E402
                                   PAGAR_MARKOR, fran_guldbeslut,
                                   fran_kopplarvarv, fran_ogonkoppling,
                                   fran_planprotokoll,
                                   fran_reparationsprotokoll,
                                   fran_stationsdom, granska,
                                   kor_kopplaren, rendera)
from vc_assist_svc.harness.modell import Modell, Modellsvar        # noqa: E402
from vc_assist_svc.plc import matning, reparation as R             # noqa: E402
from vc_assist_svc.plc import stationsgrind as S                   # noqa: E402
from vc_assist_svc.plc.kopplare import Kopplare, Kopplarfel        # noqa: E402
from vc_assist_svc.plc.signalkarta import (FRAN_PLC, TILL_PLC,     # noqa: E402
                                           karta_av_rader)
from vc_assist_svc.plc.skelett import Skelett                      # noqa: E402


class Klocka(object):
    def __init__(self, t=1000.0):
        self.t = float(t)

    def __call__(self):
        return self.t

    def tick(self, s):
        self.t += float(s)
        return self.t


def forlopp(k=None):
    return Forlopp("o-64", "Bygg en plockstation.", klocka=k or Klocka())


# ===================================================================
#  Stationsgrinden: grind 1-4 in i visningen
# ===================================================================

STATION = "Press"


def stationskarta():
    return karta_av_rader(STATION, [
        ("Givare", "Puls", "givare", "BOOL", "TILL_PLC", "%IX0.0"),
        ("Don", "Svar", "don", "BOOL", "FRAN_PLC", "%QX0.0"),
    ])


def st_kalla(kropp):
    k = stationskarta()
    return ("PROGRAM %s\n" % k.station + k.deklarationstext() + kropp
            + "END_PROGRAM\n")


def test_en_fallen_stationsgrind_ger_grindens_egna_ord_ordagrant():
    """Det ar doktrinen ur 50_grindar.md pa vagen UT till anvandaren i
    stallet for pa vagen till modellen. Samma jamforelse, samma skal."""
    dom = S.granska_station(
        S.Kandidat(STATION, st_kalla("    don := saknad_tagg;\n")),
        stationskarta(), stanna_vid_forsta=False)
    f = forlopp()
    fran_stationsdom(f, dom)

    fallna = [h for h in f.grindar() if h.text == "FÖLL"]
    assert fallna, dom.text()
    text = rendera(f)
    for h in fallna:
        assert h.ordagrant == dom.utdata[h.steg], "källan skrev om utdatan"
        assert h.ordagrant in text, "grindens ord nådde inte visningen"
    assert granska(f, text).ok


def test_en_grind_som_inte_kunde_kora_blir_en_ovisshet_aldrig_gron():
    """Kompilatorn ar inte uppsatt i provet. Det ar inte ett gront i vantan
    pa besked - det ar ett 'vet inte' med grindens eget skal (I3)."""
    dom = S.granska_station(S.Kandidat(STATION, st_kalla("    don := givare;\n")),
                            stationskarta(), stanna_vid_forsta=False)
    f = forlopp()
    fran_stationsdom(f, dom)

    grindnamn = [h.steg for h in f.grindar()]
    assert S.NAMN_KOMPILERING not in grindnamn
    ovissa = dict((o.namn, o.skal) for o in f.ovissheter)
    assert S.NAMN_KOMPILERING in ovissa
    assert ovissa[S.NAMN_KOMPILERING] == str(
        dom.forgrindar[S.NAMN_KOMPILERING])
    assert S.NAMN_KOMPILERING in rendera(f)


def test_TRASIG_en_kalla_som_sammanfattar_grinden_falls():
    """Trasig fixtur for KALLAN, inte for renderaren.

    Den har varianten ser hjalpsam ut: den kortar grindens utdata till
    forsta raden innan den lagger in den. Ingen renderare kan laga det -
    orden ar redan borta nar visningen byggs.
    """
    dom = S.granska_station(
        S.Kandidat(STATION, st_kalla("    don := saknad_tagg;\n")),
        stationskarta(), stanna_vid_forsta=False)

    def sammanfattande_kalla(f, dom):
        for namn in S.KORORDNING:
            utfall = dom.forgrindar.get(namn)
            if utfall is True:
                f.grind(namn, True)
            elif utfall is not None:
                kort = (dom.utdata.get(namn) or str(utfall)).splitlines()[0]
                f.grind(namn, False, kort)

    f = forlopp()
    sammanfattande_kalla(f, dom)
    fallna = [h for h in f.grindar() if h.text == "FÖLL"]
    assert fallna, "fixturen provar inget om ingen grind foll"
    forlorade = [h.steg for h in fallna
                 if (dom.utdata.get(h.steg) or "").strip()
                 and dom.utdata[h.steg] != h.ordagrant]
    assert forlorade, "sammanfattningen tappade ingenting; fixturen ar trasig"
    # Visningen kan inte upptacka det - och det ar hela poangen med att
    # kallan provas for sig.
    assert granska(f).ok
    for namn in forlorade:
        assert dom.utdata[namn] not in rendera(f)


# ===================================================================
#  Reparationsslingan
# ===================================================================

RATT_KROPP = "DON := GIVARE;"
FEL_KROPP = "DON := NOT GIVARE;"
GRINDORD = ("EGEN GRIND EJ GODKAND\n"
            "  rad 1: [OMVANT/F5] DON drivs omvänt mot givaren\n"
            "  rad 1: [ANNAT/F8] och förreglingen saknas")


def repkarta():
    return karta_av_rader("PROV", [
        ("plc", "sensor", "GIVARE", "BOOL", TILL_PLC, "%IX0.0"),
        ("plc", "aktuator", "DON", "BOOL", FRAN_PLC, "%QX0.0"),
    ])


class Provgrind(R.Grindsteg):
    namn = "provgrind"

    def doma(self, st_kalla):
        if RATT_KROPP in st_kalla:
            return R.Grinddom(grind=self.namn, ok=True)
        return R.Grinddom(grind=self.namn, ok=False, utdata=GRINDORD,
                          koder=R.koder_ur(GRINDORD),
                          klasser=R.klasser_ur(GRINDORD))

    def ej_korda(self):
        return {"kompilering": "kompilatorn ar inte uppsatt i provet"}


class Manusmodell(Modell):
    leverantor = "attrapp"

    def __init__(self, kroppar):
        self.kroppar = list(kroppar)
        self.i = 0

    def svara(self, systemprompt, meddelanden, verktyg):
        if self.i >= len(self.kroppar):
            return Modellsvar(text="")
        kropp = self.kroppar[self.i]
        self.i += 1
        return Modellsvar(text=kropp)


def kor_slinga(kroppar, max_varv=R.MAX_VARV):
    slinga = R.Reparationsslinga(Skelett.av_karta(repkarta()), [Provgrind()],
                                 max_varv=max_varv)
    return slinga.kor(Manusmodell(kroppar), "skriv kroppen")


def test_en_slinga_som_loste_uppgiften_ar_kandidat_aldrig_guld():
    protokoll = kor_slinga([FEL_KROPP, RATT_KROPP])
    assert protokoll.utfall == R.UTFALL_LOST
    f = forlopp()
    fran_reparationsprotokoll(f, protokoll)
    text = rendera(f)
    assert f.lage != FALLET
    assert "kandidat" in text
    assert "ögats dom" in text
    assert granska(f, text).ok


def test_slingans_grindord_gar_ordagrant_ut_till_anvandaren():
    protokoll = kor_slinga([FEL_KROPP, RATT_KROPP])
    f = forlopp()
    fran_reparationsprotokoll(f, protokoll)
    assert GRINDORD in rendera(f)


def test_en_last_slinga_ar_ett_fall_inte_ett_arbete():
    protokoll = kor_slinga([FEL_KROPP, FEL_KROPP])
    assert protokoll.utfall == R.UTFALL_LAST
    f = forlopp()
    fran_reparationsprotokoll(f, protokoll)
    assert f.lage == FALLET
    text = rendera(f)
    assert PAGAR_MARKOR not in text
    assert granska(f, text).ok


def test_slingans_ej_korda_grindar_syns_som_ovisshet():
    protokoll = kor_slinga([FEL_KROPP, RATT_KROPP])
    f = forlopp()
    fran_reparationsprotokoll(f, protokoll)
    ovissa = dict((o.namn, o.skal) for o in f.ovissheter)
    assert ovissa["kompilering"] == "kompilatorn ar inte uppsatt i provet"
    assert "kompilatorn ar inte uppsatt i provet" in rendera(f)


# ===================================================================
#  Kopplaren: ytan går att läsa MELLAN två varv
# ===================================================================

class FalskUa(object):
    def __init__(self, varden=None, kastar_fran=None):
        self.varden = dict(varden or {})
        self.kastar_fran = kastar_fran
        self.n = 0

    def _kanske_kasta(self):
        self.n += 1
        if self.kastar_fran is not None and self.n > self.kastar_fran:
            raise IOError("OPC UA svarar inte")

    def las(self, taggar):
        self._kanske_kasta()
        return dict((t, self.varden.get(t)) for t in taggar)

    def skriv(self, varden):
        self._kanske_kasta()
        self.varden.update(varden)


class FalskBrygga(object):
    def __init__(self, scen=None):
        self.scen = dict(scen or {})
        self.koade = []
        self._qid = 0

    def kor(self, kod, timeout_ms=5000):
        ut = {}
        for rad in kod.splitlines():
            if rad.startswith("ut["):
                tagg = rad.split("[", 1)[1].split("]", 1)[0].strip("'\"")
                ut[tagg] = self.scen.get(tagg)
        return {"ok": True, "result": ut}

    def koa(self, kod, desc="", timeout_ms=5000):
        self._qid += 1
        self.koade.append((kod, desc))
        return {"qid": "q%d" % self._qid, "state": "pending", "desc": desc}

    def godkann_och_vanta(self, qid, timeout=60.0, intervall=0.05):
        return {"qid": qid, "state": "done",
                "svar": {"ok": True, "result": {"result": {}}}}


def test_ytan_gar_att_lasa_mellan_tva_varv():
    """Det ar hela fasen i ett prov: forloppet finns MEDAN korningen pagar,
    inte forst nar den ar over."""
    k = Klocka()
    f = forlopp(k)
    kopplare = Kopplare(matning.provkarta("ST010"), FalskUa({"matut": True}),
                        FalskBrygga({"matin": True}))
    lasningar = []
    for _ in range(5):
        k.tick(0.05)
        v = kopplare.kor_varv()
        fran_kopplarvarv(f, v)
        text = rendera(f)
        lasningar.append(text)
        assert granska(f, text).ok
    assert len(set(lasningar)) == 5, "visningen ändrade sig inte mellan varven"
    assert f.lage == ARBETAR
    assert PAGAR_MARKOR not in lasningar[-1] or f.lage == ARBETAR


def test_en_kopplare_som_ger_upp_blir_ett_fall_med_sina_egna_ord():
    """M-39: kopplaren ger upp efter tre raka fel i stallet for att mala
    vidare och SE UT att arbeta. Visningen ska visa samma sak."""
    k = Klocka()
    f = forlopp(k)
    kopplare = Kopplare(matning.provkarta("ST010"),
                        FalskUa({"matut": True}, kastar_fran=0),
                        FalskBrygga({"matin": True}), max_raka_fel=3)
    kord = kor_kopplaren(f, kopplare, 10)
    assert kord == 2, "kopplaren skulle ge upp pa tredje varvet"
    assert f.lage == FALLET
    text = rendera(f)
    assert "gav upp" in text
    assert PAGAR_MARKOR not in text
    assert granska(f, text).ok


def test_TRASIG_en_visning_som_hanger_kvar_i_ARBETAR_efter_att_kopplaren_gav_upp():
    """Trasig fixtur: draget dar undantaget sväljs och visningen inte far
    veta nagot. Det ar precis den falska gronen M-39 finns for att undvika,
    och den ska falla har ocksa."""
    k = Klocka()
    f = forlopp(k)
    kopplare = Kopplare(matning.provkarta("ST010"),
                        FalskUa({"matut": True}, kastar_fran=0),
                        FalskBrygga({"matin": True}), max_raka_fel=3)
    f.steg_borjar("kopplarslingan")
    for _ in range(10):
        try:
            kopplare.kor_varv()
        except Kopplarfel:
            break                 # <- slukat. Forloppet far inte veta nagot.
    assert f.lage == ARBETAR, "fixturen provar inget om laget inte ar ARBETAR"
    k.tick(0.2)
    text = rendera(f)
    assert PAGAR_MARKOR in text, "visningen snurrar vidare over en dod slinga"
    # Grinden kan inte se det: protokollet ljuger, inte texten. Skyddet ar
    # att gora fallet till en handelse, och kor_kopplaren gor det.
    assert granska(f, text).ok
    f2 = forlopp(Klocka())
    kopplare2 = Kopplare(matning.provkarta("ST010"),
                         FalskUa({"matut": True}, kastar_fran=0),
                         FalskBrygga({"matin": True}), max_raka_fel=3)
    kor_kopplaren(f2, kopplare2, 10)
    assert f2.lage == FALLET
    assert PAGAR_MARKOR not in rendera(f2)


def test_ett_inskott_som_inte_nadde_ogat_syns_som_ovisshet():
    f = forlopp()
    fran_ogonkoppling(f, {"skjutna": 12, "brutna": 1, "lagrade": 9,
                          "utan_axel": 2, "oga_stangt": 1, "klockbakat": 3})
    ovissa = dict((o.namn, o.skal) for o in f.ovissheter)
    assert "PLC på ögats axel" in ovissa
    assert "PLC-värdenas tid" in ovissa
    assert "PLC-seriens hål" in ovissa
    assert "simuleringsklockan" in ovissa
    text = rendera(f)
    for namn in ("PLC på ögats axel", "PLC-värdenas tid", "PLC-seriens hål"):
        assert namn in text


def test_en_ren_ogonkoppling_lagger_ingen_ovisshet():
    f = forlopp()
    fore = len(f.ovissheter)
    fran_ogonkoppling(f, {"skjutna": 12, "brutna": 0, "lagrade": 12,
                          "utan_axel": 0, "oga_stangt": 0, "klockbakat": 0})
    assert len(f.ovissheter) == fore


# ===================================================================
#  Guldgrinden
# ===================================================================

def test_guldbeslutet_gar_ordagrant_ut():
    grind = G.Guldgrind({"plockstation"})
    beslut = grind.doma([])
    f = forlopp()
    fran_guldbeslut(f, beslut)
    assert beslut.text() in rendera(f)


def test_ett_guld_utan_ogondom_skrivs_ut_som_utan_underlag():
    """Regel A-6 i 26_appen.md: falt 6 visar aldrig guld utan falt 5."""
    grind = G.Guldgrind({"plockstation"})
    beslut = grind.doma([])
    f = forlopp()
    fran_guldbeslut(f, beslut)
    text = rendera(f)
    assert "GULDBESLUT UTAN ÖGONDOM" in text
    assert granska(f, text).ok


# ===================================================================
#  Planens körare
# ===================================================================

class Planpost(object):
    """Formen `plan.korning.Post` har. Kallan ar ANKTYPAD med flit:
    forloppsytan ar ett presentationslager och ska inte dra in
    planeringslagrets hela importkedja for fem strangar."""

    def __init__(self, steg, status, skal="", qid=None):
        self.steg = steg
        self.status = status
        self.skal = skal
        self.qid = qid


def test_kallans_planstatusar_ar_planens_egna():
    """De tva listorna ska vara samma lista. Provet laser `korning.py` som
    TEXT i stallet for att importera den, sa att ett annat lagers halva
    andring inte gor det har provet rott av fel skal."""
    import re
    with open(os.path.join(_ROT, "svc", "vc_assist_svc", "plan",
                           "korning.py"), encoding="utf-8") as fh:
        kalla = fh.read()
    planens = set(re.findall(r'^(?:KORD|HOPPAD|FALLEN|KOAD|EJ_UTFORD) = "(\w+)"',
                             kalla, re.M))
    assert planens, "hittade inga statuskonstanter i plan/korning.py"
    from vc_assist_svc.forlopp.kallor import PLANSTATUSAR
    assert planens == set(PLANSTATUSAR)


def test_en_koad_post_gor_forloppet_vantande_inte_arbetande():
    protokoll = [
        Planpost("ladda_band", "kord", "kordes direkt"),
        Planpost("flytta_robot", "koad",
                 "skrivande steg lagt i godkannandekon som q7", qid="q7"),
    ]
    f = forlopp()
    fran_planprotokoll(f, protokoll)
    from vc_assist_svc.forlopp import VANTAR
    assert f.lage == VANTAR
    text = rendera(f)
    assert "q7" in text
    assert PAGAR_MARKOR not in text
    assert granska(f, text).ok


def test_ett_ej_utfort_steg_blir_en_ovisshet():
    protokoll = [Planpost("generera_st", "ej_utford",
                          "beroendet ladda_band ar fallen")]
    f = forlopp()
    fran_planprotokoll(f, protokoll)
    ovissa = dict((o.namn, o.skal) for o in f.ovissheter)
    assert ovissa["generera_st"] == "beroendet ladda_band ar fallen"


def test_TRASIG_en_okand_planstatus_avvisas_i_stallet_for_att_bli_osynlig():
    """Trasig fixtur: en status ingen gren kanner igen. Utan kravet blir
    posten borta ur visningen utan ett ord."""
    from vc_assist_svc.forlopp import Forloppsfel
    f = forlopp()
    with pytest.raises(Forloppsfel):
        fran_planprotokoll(f, [Planpost("x", "nastan_klar", "hm")])
