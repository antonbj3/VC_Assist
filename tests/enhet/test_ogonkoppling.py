# -*- coding: utf-8 -*-
"""L1: kopplarens PLC-värden in på ögats tidsaxel. Ingen VC, ingen PLC, ingen docker.

Riggen är hela vägen ÄKTA utom de två ändarna:

    Kopplare -> Ogonkoppling -> Klient -> sockel -> Brygga.tick() -> Provtagare
       ^                                                                ^
    falsk OPC UA + falsk brygga för scenen                        falsk scen

Pumpen drivs av en tråd i stället för VC:s OnRun (tillåtet på Linux, samma
grepp som test_brygga.py) och matas med en STYRBAR simuleringsklocka. Det är
poängen med riggen: förhållandet mellan simuleringstid och väggklocka går att
sätta till 1, till 10, och att nolla mitt i — precis det VC gör med
`app.startSimulation()`, `sim.run()` och `sim.reset()`.

Mätningen: docs/matningar/M-42.
"""
import os
import socket
import sys
import threading
import time

import pytest

_ROT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "ext", "vc_addon", "vc_assist")))
sys.path.insert(0, os.path.normpath(os.path.join(_ROT, "svc")))

import oga_provtagning as OP                                    # noqa: E402
import pump                                                     # noqa: E402
from vc_assist_svc.klient import Klient                          # noqa: E402
from vc_assist_svc.plc import matning                            # noqa: E402
from vc_assist_svc.plc.kopplare import Kopplare, Kopplarfel      # noqa: E402
from vc_assist_svc.plc.ogonkoppling import Ogonkoppling          # noqa: E402


# ---- attrapperna i ändarna ----------------------------------------------

class FalskUa(object):
    """OPC UA-sidan. Samma lilla yta som kopplaren kräver: las/skriv."""

    def __init__(self, varden=None, kastar=False):
        self.varden = dict(varden or {})
        self.kastar = kastar
        self.n_las = 0

    def las(self, taggar):
        if self.kastar:
            raise IOError("OPC UA svarar inte")
        self.n_las += 1
        return dict((t, self.varden.get(t)) for t in taggar)

    def skriv(self, varden):
        if self.kastar:
            raise IOError("OPC UA svarar inte")
        self.varden.update(varden)


class FalskScenbrygga(object):
    """Scenens sida av kopplaren. Skild från ögats brygga med avsikt: det är
    två olika vägar in i VC, och bara den ena går genom godkännandekön."""

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


class FalskScen(OP.Scen):
    """Ögats scen. En rollpose och en signal räcker för att en rad ska ha
    både fysik och PLC på samma tidsaxel - det är det som prövas."""

    def __init__(self):
        self.saknade = []
        self.n = 0

    def uppdatera(self):
        self.n += 1

    def pose(self, spec):
        return {"p": [0.0, 0.0, float(self.n) * 0.001], "q": [0, 0, 0, 1]}

    def signal(self, spec):
        return True


class Simklocka(object):
    """Styrbar simuleringsklocka: sim = (vagg - t0) * takt + offset.

    takt=1.0  liknar app.startSimulation() - kvot 1,000 mot väggen (M-08)
    takt=10   liknar sim.run(), som kör förloppet fortare än väggklockan
    nolla()   liknar sim.reset(), som ställer simuleringstiden på noll
    steg      simuleringstiden går i SPRÅNG, inte glidande: M-08:s logg visar
              sim=1.00 på exakt 20 varv med delay(0.05), alltså ett helt
              delay-kvantum per varv. Utan sprången mäter riggen en klocka
              som är jämnare än VC:s och gör taktfönstret för lätt.
    """

    def __init__(self, takt=1.0, steg=0.0):
        self.takt = float(takt)
        self.steg = float(steg)
        self.t0 = time.time()
        self.offset = 0.0

    def vid(self, vaggtid):
        t = (float(vaggtid) - self.t0) * self.takt + self.offset
        if self.steg > 0:
            t = int(t / self.steg) * self.steg
        return t

    def __call__(self):
        return self.vid(time.time())

    def nolla(self):
        self.t0 = time.time()
        self.offset = 0.0


def _ledig_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Rigg(object):
    def __init__(self, tmp_path, takt=1.0, plan=None, mata_simtid=True, steg=0.0):
        self.sim = Simklocka(takt, steg)
        # Pumpen far sin simuleringstid ur skriptets scope (M-08). Utan
        # simulering finns ingen - och da ska riggen ocksa kunna vara utan.
        self.mata_simtid = bool(mata_simtid)
        self.port = _ledig_port()
        self.tokenfil = str(tmp_path / "token")
        self.brygga = pump.Brygga(port=self.port, tokenfil=self.tokenfil,
                                  loggfil=str(tmp_path / "brygga.log"))
        self.brygga.starta()
        self._stopp = threading.Event()
        self._trad = threading.Thread(target=self._pumpa)
        self._trad.daemon = True
        self._trad.start()
        self.klient = Klient(port=self.port, tokenfil=self.tokenfil).anslut()
        self.oga = Ogonkoppling(self.klient)
        self.plan = plan or {"parts": ["del"], "signals": ["C/hog"],
                             "rate_hz": 20.0, "scene": "roles"}
        self.sokvag = str(tmp_path / "eyes.json")

    def _pumpa(self):
        while not self._stopp.is_set():
            self.brygga.tick(simtid=self.sim() if self.mata_simtid else None)
            time.sleep(0.005)

    def starta_ogat(self, auto=False):
        """Startar provtagaren som _op_eyes_start gör, men med en falsk scen.

        auto=False stänger av den automatiska provtagningen så testet kan
        välja EXAKT vilka simuleringstider som provtas; prov() är samma
        anrop som pumpens tick gör."""
        p = OP.Provtagare(FalskScen(), self.plan, sokvag=self.sokvag,
                          plckalla=OP.Plckalla())
        p.starta(self.sim())
        p.aktiv = bool(auto)
        self.brygga.provtagare = p
        return p

    def vanta_pa_takt(self, tidsgrans=2.0):
        slut = time.time() + tidsgrans
        while time.time() < slut:
            if self.brygga.takt() is not None and len(self.brygga._klockpar) >= 5:
                return self.brygga.takt()
            time.sleep(0.01)
        raise AssertionError("pumpen fick aldrig en mätbar takt")

    def kopplare(self, ua=None, scen=None, oga=True):
        return Kopplare(matning.provkarta("ST010"),
                        ua or FalskUa({"matut": True}),
                        FalskScenbrygga(scen or {"matin": True}),
                        oga=self.oga if oga else None)

    def stang(self):
        self._stopp.set()
        self._trad.join(timeout=2)
        try:
            self.klient.stang()
        except Exception:
            pass
        self.brygga.stang()


@pytest.fixture
def rigg(tmp_path):
    r = Rigg(tmp_path)
    yield r
    r.stang()


# ---- 1. kopplingen finns -------------------------------------------------

def test_ett_kopplarvarv_lagger_plcvardet_i_samma_rad_som_scenen(rigg):
    """Hela poängen: en rad som bär BÅDE scenens tillstånd och PLC:ns signal.

    Utan det går frågan 'vad hände i scenen när PLC:n satte den utgången?'
    inte att svara på ur serien."""
    rigg.vanta_pa_takt()
    p = rigg.starta_ogat()
    k = rigg.kopplare()
    v = k.kor_varv()
    assert v.fel is None
    assert v.oga_fel is None, "inskottet gick inte fram: %s" % v.oga_fel
    assert v.oga["lagrat"] is True and v.oga["oga"] is True

    rad = p.prov(rigg.sim())
    assert rad["plc"] == {"matut": True}, "PLC-värdet saknas i raden"
    assert rad["sig"] == {"C/hog": True}, "scenens signal saknas i samma rad"
    assert rad["parts"]["del"]["p"], "scenens pose saknas i samma rad"
    assert "plc_gammal" not in rad
    assert 0.0 <= rad["plc_alder_s"] < OP.PLC_FARSK_S


def test_ogat_provtar_plcvardet_av_sig_sjalvt_nar_pumpen_far_ga(rigg):
    """Samma sak utan handpåläggning: pumpens egen tick provtar, och
    kopplarvarvet ligger i raderna utan att testet rör provtagaren."""
    rigg.vanta_pa_takt()
    rigg.starta_ogat(auto=True)
    k = rigg.kopplare()
    slut = time.time() + 3.0
    with_plc = []
    while time.time() < slut and len(with_plc) < 3:
        k.kor_varv()
        time.sleep(0.02)
        with_plc = [r for r in list(rigg.brygga.provtagare.rader) if "plc" in r]
    assert len(with_plc) >= 3, "ögat provtog aldrig PLC-värdet av sig självt"
    assert all(r["plc"] == {"matut": True} for r in with_plc)
    assert all(r["plc_alder_s"] < OP.PLC_FARSK_S for r in with_plc)


# ---- 2. klockvalet -------------------------------------------------------

def test_aldern_raknas_i_simuleringstid_inte_i_vaggklockstid(tmp_path):
    """Klockvalet, som ett prov.

    Simuleringen går här tio gånger fortare än väggklockan - det är inte ett
    påhitt, det är vad sim.run() gör (M-08: 20 simulerade sekunder på 0,01 s).
    En ålder på 0,2 väggsekunder är då 2,0 SIMULERADE sekunder gammal, och
    ögats serie är stämplad i simuleringstid. Räknade vi i väggklocka skulle
    värdet se färskt ut i en serie där två sekunder redan gått.
    """
    r = Rigg(tmp_path, takt=10.0)
    try:
        takt = r.vanta_pa_takt()
        assert abs(takt - 10.0) < 0.5, "pumpen mätte takten till %r" % takt
        p = r.starta_ogat()
        svar = r.oga.skjut_in({"matut": True}, t_last=time.time() - 0.2)
        assert svar["lagrat"] is True
        alder_sim = r.sim() - r.brygga.provtagare.plckalla.t
        assert 1.6 < alder_sim < 2.4, (
            "0,2 väggsekunder ska bli ~2,0 simulerade sekunder, blev %.3f"
            % alder_sim)
        rad = p.prov(r.sim())
        # Två sekunder är bortom både färskhetsgränsen och tystnadstaket:
        # serien ska visa ett hål, inte ett värde som ser samtidigt ut.
        assert "plc" not in rad, "ett två sekunder gammalt värde visades som ett värde"
        assert rad["plc_gammal"] is True
        assert "ingen ny ogonblicksbild" in rad["plc_avbrott"]
    finally:
        r.stang()


def test_utan_matt_takt_far_vardet_ingen_tidsaxel_och_raknas_som_gammalt(tmp_path):
    """Fail-closed: pumpen som aldrig fått en simuleringstid vet inte hur
    väggsekunder ska räknas om, och gissar då inte på ettan."""
    r = Rigg(tmp_path, mata_simtid=False)     # pumpen slar, men utan simtid
    try:
        time.sleep(0.1)
        p = r.starta_ogat()
        svar = r.klient.plc_in(varden={"matut": True}, alder_s=0.0)
        assert svar["takt"] is None and svar["simtid"] is None
        assert svar["lagrat"] is True and svar["pa"] is None
        assert r.oga.n_utan_axel == 0        # gick inte genom Ogonkoppling
        rad = p.prov(0.5)
        assert rad["plc_gammal"] is True, "ett värde utan tidsaxel är inte färskt"
        assert rad["plc_alder_s"] is None
    finally:
        r.stang()


# ---- 3. det trasiga fallet: PLC:n tystnar --------------------------------

def test_en_tyst_kopplare_ger_HAL_i_serien_inte_gamla_tal(rigg):
    """TRASIG FIXTUR. Kopplaren dör tvärt - ingen ger sig av med ett skäl.

    Serien får då inte fortsätta bära det sista värdet som om det vore
    färskt. Efter PLC_TYSTNAD_S släpps värdena och raden visar ett hål med
    skäl i stället.
    """
    rigg.vanta_pa_takt()
    p = rigg.starta_ogat()
    k = rigg.kopplare()
    k.kor_varv()
    t = rigg.sim()

    farsk = p.prov(t)
    assert farsk["plc"] == {"matut": True}

    # ingen ny ögonblicksbild - kopplaren finns inte längre
    gammal = p.prov(t + (OP.PLC_FARSK_S + OP.PLC_TYSTNAD_S) / 2.0)
    assert gammal["plc"] == {"matut": True}, "innanför taket visas värdet, flaggat"
    assert gammal["plc_gammal"] is True

    hal = p.prov(t + OP.PLC_TYSTNAD_S + 0.1)
    assert "plc" not in hal, "gamla tal följde med förbi tystnadstaket"
    assert hal["plc_gammal"] is True
    assert "ingen ny ogonblicksbild" in hal["plc_avbrott"]


def test_kopplaren_som_ger_upp_sager_det_till_serien_och_slapper_vardena(rigg):
    """TRASIG FIXTUR. PLC:n tystnar och kopplaren ger upp efter tre raka fel
    (M-39). Det sista den gör är att tala om det för ögat - tystnad går inte
    att skilja från 'inget nytt har hänt'."""
    rigg.vanta_pa_takt()
    p = rigg.starta_ogat()
    ua = FalskUa({"matut": True})
    k = rigg.kopplare(ua=ua)
    k.kor_varv()
    assert p.prov(rigg.sim())["plc"] == {"matut": True}

    ua.kastar = True
    k.kor_varv()
    # Redan FÖRSTA fallna varvet släpper värdena: det varvet har inget färskt.
    forsta = p.prov(rigg.sim())
    assert "plc" not in forsta
    assert "kopplarvarv" in forsta["plc_avbrott"] and "foll" in forsta["plc_avbrott"]

    k.kor_varv()
    with pytest.raises(Kopplarfel):
        k.kor_varv()
    sista = p.prov(rigg.sim())
    assert "plc" not in sista, "en död kopplares värden låg kvar i serien"
    assert "gav upp" in sista["plc_avbrott"]
    assert sista["plc_gammal"] is True
    assert rigg.oga.n_brutna >= 3


def test_ett_varv_som_lyckas_igen_tar_tillbaka_vardena(rigg):
    """Avbrottet är inte ett dödsbud - en återkommen kopplare ska synas som
    återkommen, annars vore hålet lika osant som de gamla talen."""
    rigg.vanta_pa_takt()
    p = rigg.starta_ogat()
    ua = FalskUa({"matut": True}, kastar=True)
    k = rigg.kopplare(ua=ua)
    k.kor_varv()
    assert "plc" not in p.prov(rigg.sim())
    ua.kastar = False
    k.kor_varv()
    rad = p.prov(rigg.sim())
    assert rad["plc"] == {"matut": True}
    assert "plc_avbrott" not in rad


# ---- 4. klockan som flyttar sig bakåt ------------------------------------

def test_en_simuleringsomstart_gor_inte_ett_gammalt_varde_farskt(rigg):
    """sim.reset() nollar simuleringstiden mitt i en körning - bryggan gör
    det själv efter varje scenändring. Ett värde stämplat före omstarten
    ligger då i FRAMTIDEN sett från den nya klockan. Det får inte klippas
    till ålder noll: det vore det färskaste värdet i hela serien."""
    rigg.vanta_pa_takt()
    time.sleep(0.3)                      # simuleringen hinner en bit fran noll
    p = rigg.starta_ogat()
    k = rigg.kopplare()
    k.kor_varv()
    stampel = rigg.brygga.provtagare.plckalla.t
    assert stampel > 0.2, "riggen hann inte få en simuleringstid att tala om"

    rigg.sim.nolla()
    rad = p.prov(rigg.sim())
    assert "plc" not in rad, "ett värde från den gamla tidsaxeln visades"
    assert "framtiden" in rad["plc_avbrott"]
    assert rad["plc_gammal"] is True


def test_pumpen_kastar_taktfonstret_nar_klockan_gar_bakat(rigg):
    """Ett taktfönster som spänner över hoppet ger en takt som är ren dikt."""
    rigg.vanta_pa_takt()
    fore = rigg.brygga.n_klockbakat
    rigg.sim.nolla()
    slut = time.time() + 2.0
    while time.time() < slut and rigg.brygga.n_klockbakat == fore:
        time.sleep(0.01)
    assert rigg.brygga.n_klockbakat == fore + 1
    # takten mäts om från den nya axeln, och landar på samma ~1,0
    time.sleep(0.2)
    assert abs(rigg.brygga.takt() - 1.0) < 0.2


# ---- 5. ingen falsk framgång --------------------------------------------

def test_ett_inskott_till_ett_oga_som_inte_provtar_kvitteras_inte_som_lagrat(rigg):
    rigg.vanta_pa_takt()
    rigg.brygga.provtagare = None
    svar = rigg.oga.skjut_in({"matut": True}, t_last=time.time())
    assert svar["oga"] is False and svar["lagrat"] is False
    assert svar["skal"] == "ogat provtar inte"
    assert rigg.oga.n_oga_stangt == 1 and rigg.oga.n_lagrade == 0


def test_ett_inskott_som_inte_gar_fram_faller_inte_varvet_men_tigs_inte_ihjal(rigg):
    """Ögat får aldrig fälla kopplarens varv. Men ett inskott som försvinner
    lämnar serien åt sitt eget tystnadstak, och DET ska synas."""
    class TrasigtOga(object):
        def skjut_in(self, varden, t_last=None):
            raise IOError("bryggan svarar inte")

        def bryt(self, skal):
            raise IOError("bryggan svarar inte")

        def sammanfattning(self):
            return {}

    k = rigg.kopplare()
    k.oga = TrasigtOga()
    v = k.kor_varv()
    assert v.fel is None, "ögat fällde kopplarens varv"
    assert v.oga_fel and "OSError" in v.oga_fel or "IOError" in v.oga_fel
    assert k.n_ogafel == 1
    assert k.sammanfattning()["ogafel"] == 1


def test_inskottet_gar_inte_genom_godkannandekon(rigg):
    """I12 gäller det som ändrar SCENEN. Ett PLC-värde rör bara ögats egen
    buffert, och ska därför inte kräva ett godkännande per varv - annars
    vore slingan omöjlig att köra."""
    rigg.vanta_pa_takt()
    rigg.starta_ogat()
    k = rigg.kopplare()
    k.kor_varv()
    assert rigg.brygga.ko == [], "inskottet lade en post i godkännandekön"


def test_ogat_utan_kopplare_ljuger_inte_om_att_ha_plcvarden(rigg):
    """En provtagare med en tom källa skriver ingenting alls om PLC - varken
    värden eller hål. Ingen har lovat några."""
    p = rigg.starta_ogat()
    rad = p.prov(rigg.sim())
    assert "plc" not in rad and "plc_avbrott" not in rad
    assert "plc_alder_s" not in rad


# ---- 6. mätningen: fördröjningen d --------------------------------------

def test_hopfogningens_fordrojning_ar_matt_och_pekar_at_ratt_hall(rigg):
    """MÄTNINGEN i M-42, som ett prov som går att köra om.

    d = felet i hopfogningen: skillnaden mellan den simuleringstid ögat
    stämplar värdet med, och den simuleringstid värdet FAKTISKT lästes vid.

        d < 0  ögat tror värdet är äldre än det är   (konservativt)
        d > 0  ögat tror värdet är färskare än det är (farligt hållet)

    Riggens simuleringsklocka är en känd funktion av väggklockan, så den
    sanna tidpunkten är känd - det är därför felet går att mäta alls.

    Provet mäter BÅDA: med kompensationen ur `rtt_tak()`, och vad samma varv
    hade gett utan den. Det andra talet är härkomsten till att kompensationen
    finns.
    """
    rigg.vanta_pa_takt()
    rigg.starta_ogat()
    rigg.oga.synka()
    k = rigg.kopplare()
    d_ms, d_utan_ms, rtt_ms = [], [], []
    takt = rigg.brygga.takt()
    for _ in range(200):
        komp = rigg.oga.rtt_tak()
        t0 = time.time()
        v = k.kor_varv()
        assert v.fel is None and v.oga_fel is None
        rtt_ms.append((time.time() - t0) * 1000.0)
        d = (rigg.brygga.provtagare.plckalla.t
             - rigg.sim.vid(v.t_fran_plc)) * 1000.0
        d_ms.append(d)
        d_utan_ms.append(d + komp * 1000.0 * takt)

    def p(v, andel):
        s = sorted(v)
        return s[min(len(s) - 1, int(round(andel * (len(s) - 1))))]

    print("\nM-42 hopfogningen, %d varv, takt %.4f" % (len(d_ms), takt))
    print("  d MED kompensation (ms):  median %+.2f  p05 %+.2f  p95 %+.2f  "
          "min %+.2f  max %+.2f"
          % (p(d_ms, .5), p(d_ms, .05), p(d_ms, .95), min(d_ms), max(d_ms)))
    print("  d UTAN kompensation (ms): median %+.2f  p95 %+.2f  max %+.2f"
          % (p(d_utan_ms, .5), p(d_utan_ms, .95), max(d_utan_ms)))
    print("  varv (ms): median %.2f  p95 %.2f  max %.2f"
          % (p(rtt_ms, .5), p(rtt_ms, .95), max(rtt_ms)))
    print("  ogonkopplingen: %r" % (rigg.oga.sammanfattning(),))
    andel_over = 100.0 * len([x for x in d_ms if x > 0]) / len(d_ms)
    print("  andel varv med d > 0 (farliga hallet): %.1f %%" % andel_over)

    # 1. Utan kompensation lutar hopfogningen åt det FARLIGA hållet. Det är
    #    skälet till att kompensationen finns, mätt och inte påstått.
    assert p(d_utan_ms, .5) > 0.0
    # 2. Med den lutar den åt det konservativa hållet i stället. Inte VARJE
    #    varv - jitteret i turen och returen är kvar, och det påstås inte
    #    bort - men systematiken har bytt tecken.
    assert p(d_ms, .5) < 0.0, "hopfogningen lutar systematiskt åt det farliga hållet"
    # 3. Ingen magisk gräns uppåt heller: felet mäts mot riggens egna mätta
    #    storheter. Ögat kan aldrig tro att ett värde är färskare än ett helt
    #    varv tillåter - då hade tiden gått åt fel håll.
    assert max(d_ms) <= max(rtt_ms) * takt + 1.0
    # 4. Osäkerheten måste vara liten mot det fönster den matar. Är den det
    #    inte är plc_gammal-flaggan brus och inte ett mått.
    assert max(abs(x) for x in d_ms) < OP.PLC_FARSK_S * 1000.0 / 5.0
    assert rigg.oga.n_utan_axel == 0 and rigg.oga.n_oga_stangt == 0
    assert rigg.oga.n_lagrade == 200


def test_synkningen_lagrar_ingenting_men_mater_vagen(rigg):
    """En tur och retur utan värden. Bryggan säger rent ut att inget lagrades
    - en synkning får inte se ut som ett inskott."""
    rigg.vanta_pa_takt()
    rigg.starta_ogat()
    svar = rigg.oga.synka(3)
    assert svar["oga"] is True and svar["lagrat"] is False
    assert svar["skal"] == "inga varden i begaran"
    assert rigg.oga.n_lagrade == 0 and rigg.oga.rtt_tak() > 0.0
    assert rigg.brygga.provtagare.plckalla.n_inskott == 0


def test_taktfonstret_ar_matt_och_inte_gissat(tmp_path):
    """Hur många tick-par takten behöver för att bli ett tal och inte brus.

    Takten går in MULTIPLIKATIVT i varje ålder (alder_sim = alder_vagg * takt),
    så ett taktfel på 10 % är ett åldersfel på 10 %. Fönstret ska vara långt
    nog att jitteret medelvärdesbildas bort och kort nog att inte släpa efter
    när takten byter regim - och det är två storheter, alltså mäts båda.
    """
    rigg = Rigg(tmp_path, steg=0.005)     # simuleringstiden gar i sprang
    rigg.vanta_pa_takt()
    par = []
    slut = time.time() + 1.5
    sist = None
    while time.time() < slut:
        p = (rigg.brygga.simtid_vagg, rigg.brygga.simtid)
        if p != sist and p[0] is not None:
            par.append(p)
            sist = p
        time.sleep(0.002)
    assert len(par) > 60, "riggen gav bara %d tick-par" % len(par)

    def takt_over(n):
        fel = []
        for i in range(len(par) - n + 1):
            a, b = par[i], par[i + n - 1]
            if b[0] - a[0] <= 0:
                continue
            fel.append(abs((b[1] - a[1]) / (b[0] - a[0]) - rigg.sim.takt))
        return max(fel), sum(fel) / len(fel)

    print("\nM-42 taktfonstret (%d par, sann takt %.1f):" % (len(par), rigg.sim.takt))
    matt = {}
    for n in (2, 5, 10, 20, 40):
        matt[n] = takt_over(n)
        print("  n=%-3d  varsta fel %.4f  medelfel %.4f  slap %.0f ms"
              % (n, matt[n][0], matt[n][1], (n - 1) * 5.0))
    # Ett par är jitter, inte takt. Fönstret ska mäta bort det.
    assert matt[2][0] > matt[pump.TAKTFONSTER][0] * 2
    # Och vid det valda fönstret ska felet vara litet mot det det styr: en
    # ålder på 0,25 s (PLC_FARSK_S) får inte flyttas mer än en tiondel av
    # färskhetsfönstret av taktfelet allena.
    assert matt[pump.TAKTFONSTER][0] * OP.PLC_FARSK_S < OP.PLC_FARSK_S / 10.0
    rigg.stang()


def test_tystnadstaket_slar_till_nar_det_ska_och_inte_forr(rigg):
    """Tystnadstaket mätt i sin egen storhet: hur långt efter det sista
    inskottet serien går från flaggat värde till hål. M-39 mätte kopplarens
    varv till median 89 ms och p95 105 ms; tre raka fel (MAX_RAKA_FEL) tar
    alltså högst ~315 ms innan kopplaren säger ifrån själv. Taket ska ligga
    över det, annars slår det på en kopplare som lever."""
    rigg.vanta_pa_takt()
    p = rigg.starta_ogat()
    k = rigg.kopplare()
    k.kor_varv()
    t = rigg.sim()
    steg = 0.01
    hal_vid, sista_farsk, alder = None, None, None
    for i in range(1, 200):
        rad = p.prov(t + i * steg)
        if "plc" in rad:
            sista_farsk = rad["plc_alder_s"]
            continue
        hal_vid, alder = i * steg, rad["plc_alder_s"]
        break
    print("\nM-42 tystnadstaket: sista visade vardet %.3f s gammalt, "
          "forsta halet vid %.3f s (alder %.3f s, PLC_TYSTNAD_S=%.2f)"
          % (sista_farsk, hal_vid, alder, OP.PLC_TYSTNAD_S))
    assert hal_vid is not None
    # Halet ska ligga PA taket, inte nagon annanstans: sista visade vardet
    # under det, forsta halet over, och inget provsteg daremellan.
    assert sista_farsk <= OP.PLC_TYSTNAD_S < alder <= OP.PLC_TYSTNAD_S + steg
    assert hal_vid > 3 * 0.105, "taket slår före kopplaren hinner ge upp (M-39)"
