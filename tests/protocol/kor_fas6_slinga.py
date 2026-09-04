# -*- coding: utf-8 -*-
"""L3: fas 6:s grind - handskriven ST styr SCENEN, tur och retur matt i ms.

70_faser.md: "Handskriven ST styr scenen genom OPC UA. Tur och retur matt i ms."

M-20 matte PLC-halvan: ST -> STruC++ -> OpenPLC -> OPC UA -> tillbaka, exakt tva
scan. M-38 matte att VC:s Python INTE nar OPC UA, men att bryggan nar scenens
signaler. Den har korningen sluter slingan genom tjansten och mater HELA vagen:

    scenens givarsignal -> kopplaren -> OPC UA -> PLC:ns logik
                        -> OPC UA -> kopplaren -> scenens donsignal

Det trasiga fallet: PLC:n stoppas mitt i. Slingan MASTE da falla, inte tyst
fortsatta med gamla varden.

    python3 tests/protocol/kor_fas6_slinga.py
"""
import argparse
import asyncio
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from asyncua.sync import Client as SyncClient        # noqa: E402
from vc_assist_svc.klient import Klient              # noqa: E402
from vc_assist_svc.plc import matning                # noqa: E402
from vc_assist_svc.plc.kopplare import Kopplare      # noqa: E402
from vc_assist_svc.plc.signalkarta import TILL_PLC   # noqa: E402


class UaKanal:
    """Den minsta yta kopplaren begar: las(taggar) och skriv(varden)."""

    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.klient = None
        self._noder = {}

    def anslut(self):
        self.klient = SyncClient(url=self.endpoint)
        self.klient.connect()
        for barn in self.klient.nodes.objects.get_children():
            namn = barn.read_browse_name().Name
            self._noder[namn] = barn
        return self

    def stang(self):
        if self.klient is not None:
            try:
                self.klient.disconnect()
            finally:
                self.klient = None

    def las(self, taggar):
        ut = {}
        for t in taggar:
            n = self._noder.get(t)
            ut[t] = None if n is None else n.read_value()
        return ut

    def skriv(self, varden):
        for t, v in varden.items():
            n = self._noder.get(t)
            if n is not None and v is not None:
                n.write_value(bool(v) if isinstance(v, bool) else v)


BYGG_SCEN = """import json
app = getApplication()
namn = %r
byggda = []
for n in namn:
    for c in list(app.Components):
        if c.Name == n[0]:
            app.deleteComponent(c)
for komp, signal in namn:
    c = None
    for x in app.Components:
        if x.Name == komp:
            c = x
            break
    if c is None:
        c = app.createComponent()
        c.Name = str(komp)
    b = c.createBehaviour(VC_BOOLEANSIGNAL, str(signal))
    byggda.append(komp + '.' + signal)
print(json.dumps({'byggda': byggda}))
"""

SATT_GIVARE = """import json
app = getApplication()
c = app.findComponent(%r)
b = c.findBehaviour(%r)
b.Value = %r
print(json.dumps({'satt': b.Value}))
"""

LAS_DON = """import json
app = getApplication()
c = app.findComponent(%r)
b = c.findBehaviour(%r)
print(json.dumps({'varde': b.Value}))
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=os.path.expanduser(
        "~/.wine-vc-test/drive_c/users/anton/vc_assist_token"))
    ap.add_argument("--endpoint", default="opc.tcp://127.0.0.1:14840/")
    ap.add_argument("--varv", type=int, default=40)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    karta = matning.provkarta("ST010")
    givare = [s for s in karta.signaler if s.riktning == TILL_PLC][0]
    don = [s for s in karta.signaler if s is not givare][0]
    print("  signalkarta: %s (%s.%s) -> PLC -> %s (%s.%s)"
          % (givare.tagg, givare.komponent, givare.scensignal,
             don.tagg, don.komponent, don.scensignal))

    k = Klient(port=a.port, tokenfil=a.token, timeout=90.0).anslut()
    k.kor("print(1)")

    par = [(givare.komponent, givare.scensignal), (don.komponent, don.scensignal)]
    post = k.anrop("exec_queue", {"code": BYGG_SCEN % (par,),
                                  "desc": "bygg scenens signaler",
                                  "tillat_skriptbeteende": True})["result"]
    ut = k.godkann_och_vanta(post["qid"], timeout=60)
    print("  scenen byggd: %s %s" % (ut["state"],
          json.dumps(((ut.get("svar") or {}).get("result") or {}).get("result"))[:70]))

    ua = UaKanal(a.endpoint).anslut()
    kopplare = Kopplare(karta, ua, k)
    utfall = {"karta": karta.station, "varv": []}
    fel = 0
    try:
        print("\n  === slingan: handskriven ST styr scenen ===")
        for vantat in (True, False, True):
            # 1. satt givaren i SCENEN
            post = k.koa(SATT_GIVARE % (str(givare.komponent), str(givare.scensignal), vantat),
                         desc="satt givaren till %s" % vantat)
            k.godkann_och_vanta(post["qid"], timeout=45)
            t0 = time.time()
            # 2. kor kopplaren tills donet i scenen foljer efter
            slog_igenom = None
            for i in range(a.varv):
                kopplare.kor_varv()
                d = k.kor(LAS_DON % (str(don.komponent), str(don.scensignal)))["result"]
                if bool(d.get("varde")) == bool(vantat):
                    slog_igenom = (time.time() - t0) * 1000.0
                    break
            if slog_igenom is None:
                fel += 1
                print("    FEL  givare=%-5s -> donet foljde ALDRIG efter (%d varv)"
                      % (vantat, a.varv))
                utfall["varv"].append({"vantat": vantat, "slog_igenom_ms": None})
            else:
                print("    OK   givare=%-5s -> donet foljde efter pa %.0f ms (%d varv)"
                      % (vantat, slog_igenom, i + 1))
                utfall["varv"].append({"vantat": vantat,
                                       "slog_igenom_ms": round(slog_igenom, 1),
                                       "varv": i + 1})
        s = kopplare.sammanfattning()
        utfall["sammanfattning"] = s
        print("\n    kopplarens varv: %d korda, %d lyckade, median %s ms, p95 %s ms"
              % (s["varv"], s["lyckade"], s["median_ms"], s["p95_ms"]))

        print("\n  === det trasiga fallet: PLC:n stoppas mitt i ===")
        ua.stang()
        try:
            for _ in range(6):
                kopplare.kor_varv()
            print("    FEL  slingan fortsatte utan att falla")
            fel += 1
            utfall["trasigt"] = "slapptes igenom"
        except Exception as e:
            print("    OK   slingan foll: %s" % str(e)[:100])
            utfall["trasigt"] = str(e)[:160]
    finally:
        ua.stang()
        k.stang()

    print("\n  %s" % ("ALLA PROV GICK IGENOM" if not fel else "%d prov foll" % fel))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(utfall, f, indent=2, ensure_ascii=False)
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
