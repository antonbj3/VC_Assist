# -*- coding: utf-8 -*-
"""L1: kopplaren mellan PLC och scen. Ingen docker, inget nat, ingen VC.

Bada sidor ar attrapper, och det ar hela poangen med kopplarens lilla yta:
`ua` behover bara las/skriv, `brygga` bara bryggans klientyta.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc import matning                          # noqa: E402
from vc_assist_svc.plc.kopplare import Kopplare, Kopplarfel    # noqa: E402
from vc_assist_svc.plc.signalkarta import (FRAN_PLC, TILL_PLC,  # noqa: E402
                                           karta_av_rader)


class FalskUa:
    def __init__(self, varden=None, kastar=False):
        self.varden = dict(varden or {})
        self.kastar = kastar
        self.skrivna = []

    def las(self, taggar):
        if self.kastar:
            raise IOError("OPC UA svarar inte")
        return dict((t, self.varden.get(t)) for t in taggar)

    def skriv(self, varden):
        if self.kastar:
            raise IOError("OPC UA svarar inte")
        self.skrivna.append(dict(varden))
        self.varden.update(varden)


class FalskBrygga:
    """Talar bryggans klientyta: kor, koa, godkann_och_vanta."""

    def __init__(self, scen=None):
        self.scen = dict(scen or {})
        self.korda = []
        self.koade = []
        self._qid = 0

    def kor(self, kod, timeout_ms=5000):
        self.korda.append(kod)
        # Attrappen laser ut vilka taggar koden fragar efter.
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
        kod = self.koade[-1][0]
        satt = {}
        vantande = None
        for rad in kod.splitlines():
            r = rad.strip()
            if r.startswith("b.Value = "):
                vantande = eval(r.split("=", 1)[1].strip())
            elif r.startswith("satt[") and vantande is not None:
                tagg = r.split("[", 1)[1].split("]", 1)[0].strip("'\"")
                satt[tagg] = vantande
                vantande = None
        self.scen.update(satt)
        return {"qid": qid, "state": "done",
                "svar": {"ok": True, "result": {"result": satt}}}


def karta():
    return matning.provkarta("ST010")


def test_riktningen_kommer_ur_kartan_inte_ur_en_gissning():
    k = Kopplare(karta(), FalskUa(), FalskBrygga())
    assert [s.tagg for s in k.till_plc] == ["matin"]
    assert [s.tagg for s in k.fran_plc] == ["matut"]


def test_kartan_slapper_aldrig_igenom_en_signal_utan_scensignal():
    """Kopplaren har ingen gren for det fallet, och ska inte ha nagon:
    Signalkarta avvisar signalen redan vid bygget. Grinden bor ett lager upp,
    och provas dar - inte genom en oatkomlig gren i kopplaren."""
    from vc_assist_svc.plc.signalkarta import KartFel
    with pytest.raises(KartFel):
        karta_av_rader("ST", [("", "", "b", "BOOL", FRAN_PLC, "%QX0.0")])
    with pytest.raises(KartFel):
        karta_av_rader("ST", [("K", "", "b", "BOOL", FRAN_PLC, "%QX0.0")])
    with pytest.raises(KartFel):
        karta_av_rader("ST", [("K", "S", "b", "BOOL", "AT_SIDAN", "%QX0.0")])


def test_ett_varv_flyttar_varden_at_ratt_hall():
    ua = FalskUa({"matut": True})
    brygga = FalskBrygga({"matin": True})
    k = Kopplare(karta(), ua, brygga)
    v = k.kor_varv()
    assert v.fel is None
    assert ua.skrivna == [{"matin": True}], "scenens givare ska ut till PLC"
    assert v.fran_plc == {"matut": True}
    assert brygga.scen["matut"] is True, "PLC:ns utgang ska in i scenen"
    for t in (v.las_vc_ms, v.skriv_plc_ms, v.las_plc_ms, v.skriv_vc_ms, v.totalt_ms):
        assert t is not None and t >= 0.0


def test_varje_led_tidtas_separat():
    k = Kopplare(karta(), FalskUa({"matut": False}), FalskBrygga({"matin": False}))
    v = k.kor_varv()
    d = v.till_json()
    for n in ("las_vc_ms", "skriv_plc_ms", "las_plc_ms", "skriv_vc_ms", "totalt_ms"):
        assert d[n] is not None, "%s tidtogs inte" % n


def test_en_dod_plc_faller_slingan_i_stallet_for_att_mala_vidare():
    """Den trasiga fixturen. En kopplare som fortsatter mot en dod PLC ser ut
    att arbeta, och scenen far da gamla varden som om de vore farska."""
    k = Kopplare(karta(), FalskUa(kastar=True), FalskBrygga({"matin": True}),
                 max_raka_fel=3)
    k.kor_varv()
    k.kor_varv()
    with pytest.raises(Kopplarfel) as e:
        k.kor_varv()
    assert "gav upp" in str(e.value)
    assert all(v.fel for v in k.varv)


def test_ett_lyckat_varv_nollstaller_felrakningen():
    ua = FalskUa({"matut": True}, kastar=True)
    k = Kopplare(karta(), ua, FalskBrygga({"matin": True}), max_raka_fel=3)
    k.kor_varv(); k.kor_varv()
    ua.kastar = False
    k.kor_varv()                      # lyckas -> raknaren nollas
    ua.kastar = True
    k.kor_varv(); k.kor_varv()        # tva nya fel racker inte
    assert len(k.varv) == 5


def test_sammanfattningen_skiljer_lyckade_fran_fallna():
    ua = FalskUa({"matut": True})
    k = Kopplare(karta(), ua, FalskBrygga({"matin": True}), max_raka_fel=99)
    k.kor_varv()
    ua.kastar = True
    k.kor_varv()
    s = k.sammanfattning()
    assert s["varv"] == 2 and s["lyckade"] == 1 and s["fallna"] == 1
    assert s["median_ms"] is not None
    assert s["till_plc"] == ["matin"] and s["fran_plc"] == ["matut"]


def test_kopplaren_tar_en_signalkarta_inte_vad_som_helst():
    with pytest.raises(Kopplarfel):
        Kopplare({"station": "ST010"}, FalskUa(), FalskBrygga())


def test_scenskrivningen_gar_genom_KON_aldrig_direkt():
    """I12: allt som andrar scenen gar genom godkannandekon."""
    brygga = FalskBrygga({"matin": True})
    k = Kopplare(karta(), FalskUa({"matut": True}), brygga)
    k.kor_varv()
    assert brygga.koade, "skrivningen koades inte"
    # Lasning anvander ocksa b.Value; det ar TILLDELNINGEN som aldrig far ga
    # genom exec.
    assert not any("b.Value = " in kod for kod in brygga.korda), \
        "en skrivning gick genom exec i stallet for kon"
