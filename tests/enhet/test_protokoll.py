# -*- coding: utf-8 -*-
"""L0: protokollet. Kors utan VC, utan natverk. Kalla: 95_testprotokoll.md."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "ext", "vc_addon", "vc_assist"))
import protokoll as P  # noqa: E402


def test_ramning_langd_i_byte_inte_tecken():
    kropp = "åäö".encode("utf-8")          # 3 tecken, 6 byte
    ram = P.rama(kropp)
    assert ram[:9] == b"00000006\n"
    assert len(ram) == 15


def test_avramare_talar_godtycklig_styckning():
    ramar = b"".join(P.rama(P.koda({"v": 1, "id": str(i), "op": "ping"}))
                     for i in range(5))
    a = P.Avramare()
    ut = []
    for i in range(len(ramar)):           # en byte i taget
        ut.extend(a.mata(ramar[i:i + 1]))
    assert len(ut) == 5
    assert [P.avkoda(k)["id"] for k in ut] == ["0", "1", "2", "3", "4"]
    assert a.obehandlat() == 0


def test_avramare_avvisar_versaler_i_prefixet():
    a = P.Avramare()
    with pytest.raises(P.Ramfel):
        a.mata(b"0000000A\n" + b"x" * 10)


def test_avramare_avvisar_saknad_radbrytning():
    a = P.Avramare()
    with pytest.raises(P.Ramfel):
        a.mata(b"00000001x" + b"y")


def test_for_stor_kropp_ger_egen_felklass():
    a = P.Avramare()
    with pytest.raises(P.ForStor):
        a.mata(b"%08x\n" % (P.MAX_KROPP + 1))
    with pytest.raises(P.ForStor):
        P.rama(b"x" * (P.MAX_KROPP + 1))


def test_felkodsregistret_ar_slutet():
    with pytest.raises(ValueError):
        P.svar_fel("a", "E_HITTEPA", "nej")


def test_sista_raden_json():
    assert P.sista_raden_json('brus\nmer brus\n{"a": 1}') == {"a": 1}
    assert P.sista_raden_json("bara brus") is None
    assert P.sista_raden_json("") is None
    assert P.sista_raden_json('{"a": 1}\n\n') == {"a": 1}   # tomma rader ignoreras


def test_version_domes_fore_token():
    """En klient med fel version ska inte tro att den har fel losen."""
    kod, _ = P.granska_begaran({"v": 99, "op": "ping", "token": "fel"}, "ratt")
    assert kod == P.E_VERSION


def test_token_kravs_nar_bryggan_har_en():
    assert P.granska_begaran({"v": 1, "op": "ping"}, "hemlis")[0] == P.E_AUTH
    assert P.granska_begaran({"v": 1, "op": "ping", "token": "hemlis"}, "hemlis")[0] is None


def test_avkoda_kraver_objekt_pa_toppnivan():
    with pytest.raises(P.Ramfel):
        P.avkoda(b"[1, 2, 3]")
    with pytest.raises(P.Ramfel):
        P.avkoda(b"inte json")


def test_pump_genererar_slumpmassig_sessionstoken(tmp_path):
    """E14: Token ar inte en fast strang utan slumpmassig per session."""
    import pump
    tfil = tmp_path / "vc_assist_token"
    b = pump.Brygga(tokenfil=str(tfil))
    b._skriv_token()
    assert len(b.token) == 48
    assert tfil.read_text().strip() == b.token
    # Kontrollera att tva anrop ger OLIKA tokens
    b2 = pump.Brygga(tokenfil=str(tmp_path / "t2"))
    b2._skriv_token()
    assert b.token != b2.token


def test_varje_felkod_i_protokollet_provas_av_minst_ett_test():
    """Kontraktstestet i 95_testprotokoll.md kräver alla elva."""
    import re
    rot = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    koder = re.findall(r"^(E_[A-Z_]+) = ", 
                       open(os.path.join(rot, "ext", "vc_addon", "vc_assist",
                                         "protokoll.py"), encoding="utf-8").read(),
                       re.M)
    assert len(koder) == 11, koder
    kat = os.path.join(rot, "tests", "enhet")
    text = "".join(open(os.path.join(kat, f), encoding="utf-8").read()
                   for f in sorted(os.listdir(kat)) if f.endswith(".py"))
    oprovade = [k for k in koder if not re.search(r"\b%s\b" % k, text)]
    assert not oprovade, ("felkoder som inget enhetstest nämner: %s"
                          % ", ".join(oprovade))

