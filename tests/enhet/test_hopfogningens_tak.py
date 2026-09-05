# -*- coding: utf-8 -*-
"""L1: hopfogningens TAK — de två termer M-87 mätte fram.

M-42 och M-65 mätte hopfogningsfelet `d` mot en rigg vars pump slog jämnt, och
satte taket till kopplarens tur och retur (`rtt_tak`). M-87 mätte samma sak mot
VC:s **egen** brygga och fann att taket inte räcker: felet överskred det i
30,7 % av varven vid 400 ms ålder, och värsta överskridandet var 647 ms.

Orsaken är inte vägen utan **klockan**. Stämpeln är

    t = simtid - alder * takt

och `takt` är själv en mätning över tjugo pumpslag. I VC spred den sig
0,864-1,234 (enstaka utslag 2,6) medan den verkliga kvoten låg på 1,00002.
Felet i takten skalar därför RAKT MED ÅLDERN, och tur och retur är en helt
annan storhet som inte bär den termen.

Den andra bristen ligger i vägen, inte i klockan: `rtt_tak` är max av de ÅTTA
FÖREGÅENDE turerna, alltså en backspegel. Blir just den här rundan längre än
alla åtta bär taket inte sin egen runda. M-87 mätte det med en styrd hicka:
felet gick då åt det FARLIGA hållet, +69,5 ms, i 10 % av varven. Kopplaren
lärde sig rundans längd först efteråt och rättar därför taket i efterhand.

Proven här hör ihop parvis: ett som visar att den nya termen räcker, och ett
som visar att den GAMLA inte gjorde det. Utan det andra är den nya termen
dekoration - en gräns som aldrig fällt har aldrig mätt något.
"""
import os
import sys

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "svc")))

import pump                                                     # noqa: E402


# ---- 1. spridningen mäts, den antas inte --------------------------------

class Klockpar(object):
    """Pumpens klockparsfönster, satt för hand. Mäter takt_spridning() ensam,
    utan trådar och utan tid - räkningen ska gå att pröva utan en rigg."""

    def __init__(self, par):
        self._klockpar = list(par)

    takt = pump.Brygga.takt
    takt_spridning = pump.Brygga.takt_spridning


def test_en_helt_rak_klocka_har_ingen_spridning():
    """Ligger varje punkt pa linjen ar bada termerna noll. Ett fonster som
    sager 1,000 och menar det ska inte kosta ogat nagon osakerhet."""
    par = [(i * 0.005, i * 0.005) for i in range(21)]
    b = Klockpar(par)
    assert abs(b.takt() - 1.0) < 1e-9
    assert b.takt_spridning() == pytest.approx(0.0, abs=1e-9)


def test_spridningen_tacker_taktens_verkliga_fel_i_varje_fonsterlage():
    """DET SOM SPRIDNINGEN LOVAR, provat pa en klocka vars sanning ar kand.

    Vaggen gar jamnt var 5:e ms; simuleringstiden gar i hela 20 ms-kvanta men
    i SAMMA takt, 1,000. Kvoten laser bara andpunkterna, sa dess fel beror pa
    var i trappan fonstret rakar ligga - den svanger mellan 0,8 och 1,25 utan
    att klockan andrar sig ett dugg. Kravet: spridningen ska tacka det felet
    i VARJE fonsterlage. Ett enda lage dar takten ligger langre fel an
    spridningen sager gor talet till en gissning.
    """
    trappa = [(i * 0.005, int(i * 0.005 / 0.020) * 0.020) for i in range(200)]
    varsta = 0.0
    matt = 0
    for start in range(0, len(trappa) - 21):
        b = Klockpar(trappa[start:start + 21])
        takt, sp = b.takt(), b.takt_spridning()
        if takt is None or sp is None:
            continue
        matt += 1
        varsta = max(varsta, abs(takt - 1.0))
        assert abs(takt - 1.0) <= sp + 1e-12, (
            "fonsterlage %d: takten lag %.4f fran sanningen men spridningen "
            "sade bara %.4f" % (start, abs(takt - 1.0), sp))
    assert matt > 100 and varsta > 0.1, (
        "trappan svangde inte tillrackligt for att prova nagot: varsta %.4f "
        "over %d lagen" % (varsta, matt))


def test_en_klocka_som_byter_regim_mitt_i_fonstret_far_spridning():
    """Första halvan går 1,0, andra halvan 2,0. Fönstrets kvot blir 1,5 och
    säger ingenting om vilken av de två som gäller nu. Delfönstren gör det:
    de två första säger 1,0, de två sista 2,0, och den största avvikelsen
    från helhetens 1,5 är 0,5."""
    par = [(i * 0.005, i * 0.005) for i in range(11)]
    v0, s0 = par[-1]
    par += [(v0 + i * 0.005, s0 + i * 0.010) for i in range(1, 11)]
    b = Klockpar(par)
    assert b.takt() == pytest.approx(1.5, abs=1e-6)
    assert b.takt_spridning() == pytest.approx(0.5, abs=1e-6)


def test_ett_for_kort_fonster_ger_okand_spridning_inte_noll():
    """En okänd osäkerhet får aldrig räknas som noll. Sju par räcker inte
    till fyra delfönster med två par vardera, och då är svaret None - inte
    0,0."""
    par = [(i * 0.005, i * 0.005) for i in range(7)]
    assert Klockpar(par).takt_spridning() is None
    assert Klockpar(par + [(0.035, 0.035)]).takt_spridning() is not None


# ---- 2. taket mot en klocka som hoppar, i riggen -------------------------

def _rigg(tmp_path, steg):
    """Riggen ur test_ogonkoppling, med en simuleringsklocka som går i SPRÅNG.

    Sprången är inte kosmetik: M-08 mätte att VC:s simuleringstid går i hela
    delay-kvanta, och det är just kvantiseringen som gör pumpens taktfönster
    oense med sig självt. En jämn klocka hade gjort provet grönt av fel skäl.
    """
    import test_ogonkoppling as TO
    return TO.Rigg(tmp_path, steg=steg)


def _varv(rigg, alder_s, n=60):
    """n inskott med en påhittad ålder. Returnerar (d, tak, vagen) per varv.

    d = stämpeln minus den SANNA simuleringstiden i läsögonblicket. Riggens
    simuleringsklocka är känd, så sanningen behöver inte klämmas fram som i
    M-87:s VC-körning - den går att läsa rakt av.

    `tak` läses ur ÖGATS KÄLLA efter varvet, inte ur svaret: rättelsen (§3)
    kommer efter svaret, och det är källans tal som följer med in i raden.
    Ett prov som läste svarets tal hade mätt ett tak ögat aldrig bär.
    """
    import test_ogonkoppling as TO
    ut = []
    kopplare = rigg.oga
    kopplare.synka()
    for _ in range(n):
        t_las = TO.time.time() - alder_s
        svar = kopplare.skjut_in({"Start": True}, t_last=t_las)
        if svar.get("pa") is None or svar.get("hopfogning_s") is None:
            continue
        d = (svar["pa"] - rigg.sim.vid(t_las))
        delar = svar.get("hopfogning_delar") or {}
        buret = rigg.brygga.provtagare.plckalla.hopfogning_s
        ut.append((d, buret, delar.get("vagen_s")))
        TO.time.sleep(0.005)
    return ut


@pytest.mark.parametrize("alder_s", [0.100, 0.400])
def test_taket_bar_felet_nar_klocktermen_ar_med(tmp_path, alder_s):
    """M-87:s krav: taket i serien ska rymma hopfogningsfelet, åt båda hållen.

    Provet mäter mot riggens KÄNDA simuleringsklocka, inte mot en klämma, så
    det finns ingen kartosäkerhet att skylla på.
    """
    rigg = _rigg(tmp_path, steg=0.02)
    try:
        rigg.vanta_pa_takt()
        rigg.starta_ogat()
        varv = _varv(rigg, alder_s)
        assert len(varv) >= 30, "för få varv gick fram: %d" % len(varv)
        over = [(d, tak) for d, tak, _v in varv if abs(d) > tak]
        varsta = max(abs(d) - tak for d, tak, _v in varv)
        print("\nM-87 klocktermen, alder %.0f ms, %d varv: varsta %+.2f ms, "
              "over taket %d" % (alder_s * 1000.0, len(varv),
                                 varsta * 1000.0, len(over)))
        assert not over, ("%d av %d varv lag utanfor taket, varst %.1f ms"
                          % (len(over), len(varv), varsta * 1000.0))
    finally:
        rigg.stang()


def test_utan_klocktermen_racker_taket_INTE_vid_stor_alder(tmp_path):
    """DEN TRASIGA FIXTUREN. Samma varv, men taket räknat som det gjordes
    FÖRE M-87: bara vägen (kopplarens tur och retur), utan klocktermen.

    Faller det här provet betyder det att den gamla räkningen plötsligt
    räcker - och då är den nya termen dekoration och ska bort. Provet finns
    för att den skillnaden ska gå att mäta, inte tros.

    Åldern är 400 ms, samma punkt där M-87 mätte 30,7 % överskridanden mot
    VC:s egen brygga.
    """
    rigg = _rigg(tmp_path, steg=0.02)
    try:
        rigg.vanta_pa_takt()
        rigg.starta_ogat()
        varv = _varv(rigg, 0.400)
        assert len(varv) >= 30, "för få varv gick fram: %d" % len(varv)
        gamla = [(d, v) for d, _tak, v in varv if v is not None]
        assert gamla, "svaret bar inga hopfogningsdelar att räkna om"
        over = [(d, v) for d, v in gamla if abs(d) > v]
        print("\nM-87 utan klocktermen, 400 ms alder, %d varv: over det GAMLA "
              "taket %d (%.0f %%)"
              % (len(gamla), len(over), 100.0 * len(over) / len(gamla)))
        assert over, ("det gamla taket rackte i alla %d varv - da mater den "
                      "nya termen ingenting" % len(gamla))
    finally:
        rigg.stang()


# ---- 3. backspegeln: en runda langre an de atta foregaende ---------------

class Hickrigg(object):
    """Riggen med en pump som sover LANGT vart n:te slag.

    Hickan ar inte pahittad for att gora provet svart: den ar den enda vag
    som gor rundans egen tur och retur langre an max av de atta foregaende,
    och det ar exakt det fall backspegeln inte kan se. Utan en styrd hicka
    matte M-65 samma sak som en sallsynt slumpfallning ("orsaken ar okand") -
    tre varv av 2400 i en korning, noll i nasta.
    """

    def __init__(self, tmp_path, hicka_var=10, hicka_s=0.08):
        import test_ogonkoppling as TO
        self.TO = TO

        class R(TO.Rigg):
            def _pumpa(sjalv):
                n = 0
                while not sjalv._stopp.is_set():
                    n += 1
                    sjalv.brygga.tick(simtid=sjalv.sim())
                    TO.time.sleep(hicka_s if (n % hicka_var == 0) else 0.005)

        self.rigg = R(tmp_path)

    def varv(self, n=120):
        """(d, skickat tak, rundans egen tur och retur) per varv."""
        r = self.rigg
        r.vanta_pa_takt()
        r.starta_ogat()
        r.oga.synka()
        k = r.kopplare()
        takt = r.brygga.takt()
        ut = []
        for _ in range(n):
            tak = r.oga.rtt_tak()
            n0 = len(r.oga.rtt_s)
            v = k.kor_varv()
            if v.fel or v.oga_fel:
                continue
            egen = max(r.oga.rtt_s[n0:]) if len(r.oga.rtt_s) > n0 else 0.0
            d = r.brygga.provtagare.plckalla.t - r.sim.vid(v.t_fran_plc)
            ut.append((d, tak * takt, egen * takt))
        return ut

    def stang(self):
        self.rigg.stang()


def test_backspegeln_ensam_racker_INTE_nar_en_runda_hickar(tmp_path):
    """DEN TRASIGA FIXTUREN for rattelsen. Taket som SKICKADES med vardet ar
    max av de atta foregaende turerna; halls det mot felet spricker det.

    Faller provet har racker backspegeln plotsligt, och da mater rattelsen
    ingenting och ska bort.
    """
    h = Hickrigg(tmp_path)
    try:
        varv = h.varv()
        assert len(varv) >= 60, "for fa varv gick fram: %d" % len(varv)
        over = [(d, tak) for d, tak, _e in varv if abs(d) > tak]
        varsta = max(abs(d) - tak for d, tak, _e in varv)
        print("\nM-87 backspegeln, %d varv: over det SKICKADE taket %d "
              "(%.0f %%), varst %+.1f ms"
              % (len(varv), len(over), 100.0 * len(over) / len(varv),
                 varsta * 1000.0))
        assert over, ("backspegeln rackte i alla %d varv - da mater "
                      "rattelsen ingenting" % len(varv))
        # Riktningen ar halva poangen: de overskridanden som kommer av en
        # hicka ligger at det FARLIGA hallet - ogat tror att vardet ar
        # farskare an det ar.
        assert max(d for d, _t in over) > 0.0
    finally:
        h.stang()


def test_rundans_egen_tur_och_retur_bar_felet(tmp_path):
    """Och rattelsens tal racker: max(skickat tak, rundans egen tur och
    retur) rymmer felet i varje varv. Det ar precis det kopplaren skickar
    efterat nar den upptackt att rundan blev langre an taket."""
    h = Hickrigg(tmp_path)
    try:
        varv = h.varv()
        assert len(varv) >= 60, "for fa varv gick fram: %d" % len(varv)
        over = [(d, tak, e) for d, tak, e in varv if abs(d) > max(tak, e)]
        varsta = max(abs(d) - max(tak, e) for d, tak, e in varv)
        print("\nM-87 med rundans egen: over %d, varst %+.1f ms"
              % (len(over), varsta * 1000.0))
        assert not over, ("%d av %d varv lag utanfor aven med rundans egen "
                          "tur och retur, varst %.1f ms"
                          % (len(over), len(varv), varsta * 1000.0))
    finally:
        h.stang()


def test_rattelsen_hojer_taket_i_ogats_kalla_och_sanker_det_aldrig(tmp_path):
    """Rattelsen gar hela vagen fram: kopplaren skickar den, bryggan tar emot
    den, och Plckalla bar det HOGRE talet. Ett lagre tal far aldrig vinna -
    en osakerhet som gar att tvatta bort ar ingen osakerhet."""
    import oga_provtagning as OP
    kalla = OP.Plckalla()
    kalla.skjut_in({"Start": True}, t=1.0, hopfogning_s=0.005)
    assert kalla.hoj_hopfogning(0.030) is True
    assert kalla.hopfogning_s == 0.030 and kalla.n_hojda == 1
    assert kalla.hoj_hopfogning(0.001) is False
    assert kalla.hopfogning_s == 0.030 and kalla.n_hojda == 1
    assert kalla.hoj_hopfogning(None) is False


def test_kopplaren_rattar_taket_nar_rundan_blev_langre_an_backspegeln(tmp_path):
    """Kopplaren ska RAKNA sina rattelser, och de ska verkligen bli av under
    en hicka. Noll rattelser i en hickande rigg betyder att mekanismen inte
    utloses, och da bar den ingenting."""
    h = Hickrigg(tmp_path)
    try:
        h.varv(n=80)
        print("\nM-87 rattelser: %d av %d inskott"
              % (h.rigg.oga.n_rattade, h.rigg.oga.n_skjutna))
        assert h.rigg.oga.n_rattade > 0, "ingen rattelse utlostes under hickan"
        assert h.rigg.oga.sammanfattning()["rattade_tak"] == h.rigg.oga.n_rattade
    finally:
        h.stang()
