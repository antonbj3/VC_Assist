# -*- coding: utf-8 -*-
"""L1: hela bryggan over en riktig sockel, utan VC.

Pumpen drivs har av en tråd i stallet for VC:s OnRun. Det ar tillatet PA
LINUX - inne i VC svalter tradar (M-07), och det ar just darfor pumpen ar
byggd som ett tick() som nagon annan anropar.
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

import protokoll as P              # noqa: E402
import pump                        # noqa: E402
from vc_assist_svc.klient import Klient, BryggFel   # noqa: E402


def _ledig_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture
def brygga(tmp_path):
    port = _ledig_port()
    b = pump.Brygga(port=port,
                    tokenfil=str(tmp_path / "token"),
                    loggfil=str(tmp_path / "brygga.log"),
                    exec_globals={"MARKOR": 4711})
    b.starta()
    stopp = threading.Event()

    def pumpa():
        while not stopp.is_set():
            b.tick()
            time.sleep(0.005)          # 200 Hz i testet, snabbare an VC:s 20

    t = threading.Thread(target=pumpa)
    t.daemon = True
    t.start()
    yield b, port, str(tmp_path / "token")
    stopp.set()
    t.join(timeout=2)
    b.stang()


@pytest.fixture
def klient(brygga):
    b, port, tokenfil = brygga
    k = Klient(port=port, tokenfil=tokenfil)
    k.anslut()
    yield k
    k.stang()


def test_ping_svarar_med_motorns_uppgifter(klient):
    r = klient.ping()
    assert r["protokoll"] == P.PROTOKOLL_VERSION
    assert r["degraded"] is False
    assert r["tick"] > 0


def test_exec_tar_resultatet_ur_sista_raden(klient):
    svar = klient.kor('print("brus")\nimport json; print(json.dumps({"summa": 2 + 2}))')
    assert svar["ok"] is True
    assert svar["result"] == {"summa": 4}
    assert "brus" in svar["stdout"]


def test_exec_ser_de_globaler_bryggan_fick(klient):
    assert klient.kor('import json; print(json.dumps({"m": MARKOR}))')["result"] == {"m": 4711}


def test_exec_utan_json_ger_result_none_men_behaller_utskriften(klient):
    svar = klient.kor('print("bara text")')
    assert svar["ok"] is True and svar["result"] is None
    assert svar["stdout"].strip() == "bara text"


def test_trasig_kod_ger_E_EXEC_med_traceback_och_bryggan_lever(klient):
    with pytest.raises(BryggFel) as ei:
        klient.kor("1/0")
    assert ei.value.kod == P.E_EXEC
    assert "ZeroDivisionError" in ei.value.traceback
    assert klient.ping()["protokoll"] == 1        # lever vidare


def test_timeout_ger_degraded_och_lasande_exec_ar_vagen_ut(klient):
    with pytest.raises(BryggFel) as ei:
        klient.kor("import time; time.sleep(0.05)", timeout_ms=1)
    assert ei.value.kod == P.E_TIMEOUT
    assert klient.ping()["degraded"] is True

    qid = klient.koa("x = 1", desc="ska sparras")["qid"]
    with pytest.raises(BryggFel) as ei2:
        klient.godkann(qid)
    assert ei2.value.kod == P.E_BUSY

    klient.kor("print(1)")                        # vagen ut
    assert klient.ping()["degraded"] is False
    assert klient.godkann_och_vanta(qid, timeout=10)["state"] == "done"


def test_kon_hela_vagen_koa_lista_godkann_kor(klient, tmp_path):
    mal = str(tmp_path / "kon_skrev_hit.txt").replace("\\", "/")
    post = klient.koa("open(%r, 'w').write('kord')\nprint('{\"ok\": 1}')" % mal,
                      desc="skriv en fil")
    assert post["state"] == "pending"
    assert not os.path.exists(mal), "en koad post far INTE kora forran den godkants"

    assert [p["qid"] for p in klient.ko()] == [post["qid"]]

    ut = klient.godkann_och_vanta(post["qid"], timeout=10)
    assert ut["state"] == "done", ut
    assert open(mal).read() == "kord"


def test_avvisad_post_kors_aldrig(klient, tmp_path):
    mal = str(tmp_path / "far_ej_finnas.txt").replace("\\", "/")
    post = klient.koa("open(%r, 'w').write('nej')" % mal, desc="ska avvisas")
    assert klient.avvisa(post["qid"])["state"] == "rejected"
    with pytest.raises(BryggFel) as ei:
        klient.godkann(post["qid"])
    assert ei.value.kod == P.E_NOT_APPROVED
    assert not os.path.exists(mal)


def test_misslyckad_koad_post_markeras_failed(klient):
    post = klient.koa("1/0", desc="trasig")
    ut = klient.godkann_och_vanta(post["qid"], timeout=10)
    assert ut["state"] == "failed"
    assert "ZeroDivisionError" in ut["svar"]["error"]["traceback"]


def test_okand_operation_namner_vad_bryggan_kan(brygga):
    b, port, tokenfil = brygga
    k = Klient(port=port, tokenfil=tokenfil)
    with pytest.raises(BryggFel) as ei:
        k.anrop("hittepa")
    assert ei.value.kod == P.E_UNKNOWN_OP
    assert "ping" in ei.value.meddelande
    k.stang()


def test_fel_token_ger_E_AUTH_och_anslutningen_stangs(brygga):
    b, port, _ = brygga
    k = Klient(port=port, token="fel losen")
    with pytest.raises(BryggFel) as ei:
        k.anrop("ping")
    assert ei.value.kod == P.E_AUTH
    with pytest.raises(Exception):
        k.anrop("ping", id_="efterat")     # anslutningen ar stangd
    k.stang()


def test_fel_protokollversion_ger_E_VERSION(brygga):
    b, port, tokenfil = brygga
    with open(tokenfil) as f:
        token = f.read().strip()
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(P.rama(P.koda({"v": 99, "id": "v", "op": "ping", "token": token})))
    a = P.Avramare()
    svar = P.avkoda(a.mata(s.recv(65536))[0])
    assert svar["error"]["code"] == P.E_VERSION
    s.close()


def test_trasig_ramning_ger_E_PARSE(brygga):
    b, port, _ = brygga
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(b"XXXXXXXX\n{}")
    a = P.Avramare()
    svar = P.avkoda(a.mata(s.recv(65536))[0])
    assert svar["error"]["code"] == P.E_PARSE
    s.close()


def test_for_stor_kropp_ger_E_TOO_LARGE(brygga):
    b, port, _ = brygga
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(b"%08x\n" % (P.MAX_KROPP + 1))
    a = P.Avramare()
    svar = P.avkoda(a.mata(s.recv(65536))[0])
    assert svar["error"]["code"] == P.E_TOO_LARGE
    s.close()


def test_flera_anrop_pa_samma_anslutning(klient):
    for i in range(50):
        assert klient.kor('import json; print(json.dumps({"i": %d}))' % i)["result"] == {"i": i}


def test_flera_samtidiga_anslutningar(brygga):
    b, port, tokenfil = brygga
    klienter = [Klient(port=port, tokenfil=tokenfil).anslut() for _ in range(5)]
    try:
        for n, k in enumerate(klienter):
            assert k.kor('import json; print(json.dumps({"n": %d}))' % n)["result"] == {"n": n}
    finally:
        for k in klienter:
            k.stang()


def test_tick_blockerar_aldrig_pa_en_tyst_anslutning(brygga):
    """En ansluten men tyst klient far inte sta pumpen i vagen."""
    b, port, tokenfil = brygga
    tyst = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        t0 = time.time()
        for _ in range(200):
            b.tick()
        gick = time.time() - t0
        assert gick < 0.5, "200 tick tog %.3f s med en tyst anslutning" % gick
    finally:
        tyst.close()


# ---- skrivgrinden i bryggan ---------------------------------------------

def test_exec_av_skrivande_kod_avvisas_och_hanvisar_till_kon(klient, tmp_path):
    mal = str(tmp_path / "far_ej_skrivas.txt").replace("\\", "/")
    with pytest.raises(BryggFel) as ei:
        klient.kor("open(%r, 'w').write('nej')" % mal)
    assert ei.value.kod == P.E_NOT_APPROVED
    assert "exec_queue" in ei.value.meddelande
    assert not os.path.exists(mal), "grinden slapp igenom skrivningen"


def test_samma_kod_gar_igenom_kon(klient, tmp_path):
    """Grinden ar en omdirigering, inte ett forbud."""
    mal = str(tmp_path / "via_kon.txt").replace("\\", "/")
    post = klient.koa("open(%r, 'w').write('kord')" % mal, desc="skriv")
    assert klient.godkann_och_vanta(post["qid"], timeout=10)["state"] == "done"
    assert open(mal).read() == "kord"


def test_otolkbar_kod_stoppas_av_grinden_fore_exec(klient):
    with pytest.raises(BryggFel) as ei:
        klient.kor("def (:")
    assert ei.value.kod == P.E_NOT_APPROVED


def test_capability_utan_rapport_sager_det_rent_ut(klient):
    with pytest.raises(BryggFel) as ei:
        klient.anrop("capability")
    assert ei.value.kod == P.E_ARGS


def test_capability_efter_skriven_rapport(brygga, klient):
    b, port, _ = brygga

    class FalskApp(object):
        Components = []

    b.skriv_formaga({"app": FalskApp()})
    r = klient.anrop("capability")["result"]
    assert r["summering"]["provade"] > 0
    assert r["port"] == port
    assert "ping" in r["operationer"]


# ---- adaptiv pump --------------------------------------------------------

def test_pumpen_slar_tatt_efter_trafik_och_glest_nar_det_ar_tyst(brygga, klient):
    b, port, _ = brygga
    klient.ping()
    assert b.nasta_paus() == pump.PAUS_AKTIV, "pumpen ska ga tatt strax efter trafik"
    b._senaste_trafik = time.time() - pump.AKTIV_FONSTER_S - 1
    assert b.nasta_paus() == pump.PAUS_TOM, "en tyst pump ska ga glest"


def test_en_ny_anslutning_racker_for_att_vacka_pumpen(brygga):
    b, port, _ = brygga
    b._senaste_trafik = 0.0
    assert b.nasta_paus() == pump.PAUS_TOM
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    try:
        for _ in range(5):
            b.tick()
            time.sleep(0.01)
        assert b.nasta_paus() == pump.PAUS_AKTIV
    finally:
        s.close()


def test_pumpen_gar_snabbt_sa_lange_ogat_provtar(brygga):
    """Ogat begar 20 Hz. Den tysta pumpen ar matt till 17,2 Hz (M-03), sa utan
    detta underprovtar ogat tyst under varje matning."""
    b, _port, _tf = brygga
    b._senaste_trafik = 0.0
    assert b.nasta_paus() == pump.PAUS_TOM

    class Provtagare(object):
        aktiv = True
    b.provtagare = Provtagare()
    assert b.nasta_paus() == pump.PAUS_AKTIV
    b.provtagare.aktiv = False
    assert b.nasta_paus() == pump.PAUS_TOM


def test_godkannandet_kvitteras_direkt_och_koden_kors_av_pumpen(brygga, klient, tmp_path):
    """Godkannandet ar en HANDLING, inte en korning. Matt skal: kod som stoppar
    simuleringen dodar pumpens tasklet mitt i exec, och ett inline-godkannande
    forsvann da tillsammans med sitt eget svar."""
    b, _port, _tf = brygga
    mal = str(tmp_path / "sent.txt").replace("\\", "/")
    post = klient.koa("open(%r, 'w').write('x')" % mal, desc="sent")
    svar = klient.godkann(post["qid"])
    assert svar["ok"] is True and svar["result"]["state"] == "approved"
    ut = klient.godkann_och_vanta.__self__.post(post["qid"])
    # posten far ett utfall inom kort, av pumpen
    for _ in range(200):
        p = klient.post(post["qid"])
        if p["state"] == "done":
            break
        time.sleep(0.01)
    assert klient.post(post["qid"])["state"] == "done"
    assert open(mal).read() == "x"


def test_en_avbruten_post_ser_varken_ut_som_pending_eller_done(brygga, klient):
    """Doden mitt i en korning far inte se ut som nagot annat an vad den var."""
    b, _port, _tf = brygga
    post = klient.koa("x = 1", desc="ska avbrytas")
    klient.godkann(post["qid"])
    for p in b.ko:
        if p.qid == post["qid"]:
            p.state = "running"          # som om pumpen dog just har
    b._markera_avbrutna()
    p = klient.post(post["qid"])
    assert p["state"] == "interrupted"
    with pytest.raises(BryggFel) as ei:
        klient.godkann(post["qid"])      # far inte kunna koras en andra gang
    assert ei.value.kod == P.E_NOT_APPROVED


# ---- omstart efter scenandring ------------------------------------------

def test_omstart_begars_hogst_en_gang_at_gangen(brygga):
    """sim.reset() utloser ett nytt OnStop innan raden efter reset() kors.
    Utan sparr blev det en omstartsstorm, matt till tusentals varv i sekunden."""
    b, _p, _t = brygga
    assert b.begar_omstart() is True
    assert b.begar_omstart() is False, "andra begaran slapptes igenom"
    b.pumpen_igang()
    assert b.begar_omstart() is False, "for tatt inpa forra omstarten"


def test_sparren_slapps_forst_nar_pumpen_bevisligen_gar(brygga):
    b, _p, _t = brygga
    b.begar_omstart()
    assert b._startar_om is True
    b.pumpen_igang()
    assert b._startar_om is False


def test_omstartstaket_stanger_av_sig_sjalvt(brygga):
    """En brygga som inte kan komma tillbaka ska sluta forsoka, inte mala."""
    b, _p, _t = brygga
    for _ in range(pump.OMSTART_TAK_PER_MINUT):
        b._startar_om = False
        b._omstartstider.append(time.time() - 2.0)
    b._startar_om = False
    assert b.begar_omstart() is False
    assert b.aterstart_simulering is False, "taket ska stanga av aterstarten"


def test_omstart_avstangd_begar_inget(brygga):
    b, _p, _t = brygga
    b.aterstart_simulering = False
    assert b.begar_omstart() is False


def test_koden_som_dodar_bryggan_avvisas_med_skalet(klient):
    """M-13: att skapa ett skriptbeteende stoppar simuleringen och dodar
    pumpen. Bryggan ska saga det, inte tystna mitt i sitt eget svar."""
    with pytest.raises(BryggFel) as ei:
        klient.koa("c.createBehaviour(VC_SCRIPT, 'x')", desc="dodande")
    assert ei.value.kod == P.E_ARGS
    assert "M-13" in ei.value.meddelande


def test_den_som_anda_vill_kan_men_far_saga_det(klient):
    post = klient.anrop("exec_queue", {"code": "c.createBehaviour(VC_SCRIPT, 'x')",
                                       "desc": "med oppna ogon",
                                       "tillat_skriptbeteende": True})
    assert post["ok"] is True


def test_ett_skriptbeteende_kan_skjutas_upp_i_stallet_for_att_forbjudas(brygga, klient, tmp_path):
    """Formagan ar inte borttagen, den ar uppskjuten till nasta VC-start."""
    b, _p, _t = brygga
    b.uppskjutetfil = str(tmp_path / "uppskjutet.json")
    r = klient.anrop("exec_queue", {"code": "c.createBehaviour(VC_SCRIPT, 'x')",
                                    "desc": "egen logik",
                                    "skjut_upp": True})["result"]
    assert r["uppskjuten"] is True and r["antal"] == 1
    poster = klient.anrop("deferred_list")["result"]["poster"]
    assert poster[0]["desc"] == "egen logik"
    assert klient.ko() == [], "en uppskjuten post ska INTE ligga i korkon"
    assert klient.anrop("deferred_clear")["result"]["borttagna"] == 1
    assert klient.anrop("deferred_list")["result"]["poster"] == []


def test_uppskjutet_avvisningsmeddelande_pekar_ut_bada_vagarna(klient):
    with pytest.raises(BryggFel) as ei:
        klient.koa("c.createBehaviour(VC_SCRIPT, 'x')", desc="x")
    assert "skjut_upp" in ei.value.meddelande
    assert "tillat_skriptbeteende" in ei.value.meddelande


def test_bryggan_varnar_INNAN_den_kor_kod_som_dodar_den(klient):
    """Efterat finns ingen pump som kan svara. Varningen maste komma fore."""
    post = klient.koa("getApplication().save('file:///x.vcmx')", desc="spara")
    svar = klient.godkann(post["qid"])
    assert svar["ok"] is True
    assert svar["result"]["dodar_pumpen"]
    assert "startas om" in svar["result"]["varning"]


def test_en_andra_brygga_skriver_inte_over_den_levandes_token(brygga, tmp_path):
    """Matt 2026-09-04: en sparad layout bar med sig brygg-komponenten. Nar den
    laddades startade en ANDRA brygga i samma process, skrev over tokenfilen och
    misslyckades sedan med att binda. Den levande bryggan blev oanbar med E_AUTH
    utan att nagot i dess egen logg sa nagot."""
    b, port, tokenfil = brygga
    with open(tokenfil) as f:
        levande = f.read().strip()

    andra = pump.Brygga(port=port, tokenfil=tokenfil,
                        loggfil=str(tmp_path / "andra.log"))
    with pytest.raises(Exception):
        andra.starta()

    with open(tokenfil) as f:
        assert f.read().strip() == levande, "tokenfilen skrevs over av en brygga som inte fick porten"
    assert andra.token is None, "en brygga utan port ska inte ha nagon token"
