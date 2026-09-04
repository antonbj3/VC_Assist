# -*- coding: utf-8 -*-
"""L3: fas 5:s forsta halva - kor VARJE verktyg mot en KORANDE VC.

Verktygsmallarna ar skrivna mot VC:s dokumentation men hade aldrig exekverats i
VC. Det ar precis den sortens oprovade yta dar dokumentationen och verkligheten
gar isar (se M-11: kvaternionen ar skalar-forst, tvartemot vad namnen antyder).

    python3 tests/protocol/kor_fas5.py
"""
import argparse
import json
import os
import sys
import traceback

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import verktyg as V                    # noqa: E402
from vc_assist_svc.klient import Klient, BryggFel         # noqa: E402
from vc_assist_svc.tokenplats import tokenfil        # noqa: E402

PROV = "Fas5Prov"
PROV2 = "Fas5Prov2"

# Argument per verktyg. Ordningen ar avsiktlig: det som skapar kommer fore det
# som laser, och det som raderar sist.
ORDNING = [
    ("list_components", {}),
    ("find_component", {"name": PROV}),
    ("component_info", {"name": PROV}),
    ("list_properties", {"component": PROV}),
    ("get_property", {"component": PROV, "property": "Name"}),
    ("get_transform", {"component": PROV}),
    ("get_transform", {"component": PROV, "frame": "world"}),
    ("get_bounds", {"component": PROV}),
    ("list_nodes", {"component": PROV}),
    ("find_node", {"component": PROV, "node": PROV}),
    ("list_interfaces", {"component": PROV}),
    ("list_connections", {}),
    ("list_connections", {"component": PROV}),
    ("set_transform", {"component": PROV, "position": [1.0, 2.0, 0.5]}),
    ("get_transform", {"component": PROV}),
    ("set_property", {"component": PROV, "property": "Name", "value": PROV}),
    ("clone_component", {"name": PROV, "new_name": PROV2}),
    ("delete_component", {"name": PROV2}),
    ("delete_component", {"name": PROV}),
]

# Provas SIST och for sig: MATT att app.save() stoppar simuleringen och darmed
# dodar pumpen, precis som createBehaviour(VC_SCRIPT). Allt annat maste hinna
# koras fore.
SIST = [
    ("save_layout", {"uri": "file:///C:/users/anton/fas5_prov.vcmx"}),
]

# Verktyg som kraver nagot vi INTE har och som darfor provas separat.
UTAN_FORUTSATTNING = {
    "load_component": ("ingen katalog ar synkad i testprefixet; noll .vcmx pa disk",
                       {"uri": "file:///C:/finns/inte.vcmx"}),
    "interface_info": ("kraver ett verkligt granssnitt; en tom komponent har inga",
                       {"component": PROV, "interface": "Flow"}),
    "can_connect": ("kraver tva verkliga granssnitt",
                    {"component": PROV, "interface": "Flow",
                     "other_component": PROV2, "other_interface": "Flow"}),
    "connect": ("kraver tva verkliga granssnitt",
                {"component": PROV, "interface": "Flow",
                 "other_component": PROV2, "other_interface": "Flow"}),
    "disconnect": ("kraver en verklig koppling",
                   {"component": PROV, "interface": "Flow"}),
}


def _bygg_provkomponent(k):
    post = k.koa("import json\n"
                 "app = getApplication()\n"
                 "for c in list(app.Components):\n"
                 "    if c.Name in (%r, %r):\n"
                 "        app.deleteComponent(c)\n"
                 "c = app.createComponent()\n"
                 "c.Name = %r\n"
                 "print(json.dumps({'ok': True}))\n" % (str(PROV), str(PROV2), str(PROV)),
                 desc="bygg provkomponenten")
    ut = k.godkann_och_vanta(post["qid"], timeout=30)
    if ut["state"] != "done":
        raise RuntimeError("kunde inte bygga provkomponenten: %s" % ut["state"])


def _kor(utf, namn, args):
    r = utf.utfor(namn, args)
    if r.koad:
        r = utf.godkann(r.qid)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    # Ingen standardsokvag. Den gamla ("~/.wine-vc-test/drive_c/users/anton/
    # vc_assist_token") bar tre antaganden som alla ar falska pa Windows: att
    # det finns ett wine-prefix, vad det heter, och vad anvandaren heter.
    ap.add_argument("--token", default=None,
                    help="tokenfilen. Utan flaggan soks den upp; se "
                         "vc_assist_svc.tokenplats")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=25.0).anslut()

    # Formagegrinden: urvalet kommer ur bryggans EGEN rapport, aldrig ur en
    # gissning (36_versioner.md).
    rapport = k.anrop("capability")["result"]
    urval = V.urval_ur_rapport(rapport, V.REGISTER)
    av = [n for n in V.REGISTER if not urval.pa(n)] if hasattr(urval, "pa") else []
    print("  formagerapport: %d av %d ytor finns" % (
        rapport["summering"]["finns"], rapport["summering"]["provade"]))
    if av:
        print("  avstangda verktyg: %s" % ", ".join(sorted(av)))

    utf = V.Utforare(k, urval)
    _bygg_provkomponent(k)

    utfall = []
    ok_n = fel_n = 0
    print("\n  === verktyg med forutsattningar pa plats ===")
    for namn, args in ORDNING:
        try:
            r = _kor(utf, namn, args)
            ok_n += 1
            kort = json.dumps(r.resultat, ensure_ascii=False)[:88]
            print("    OK   %-18s %s" % (namn, kort))
            utfall.append({"verktyg": namn, "args": args, "ok": True,
                           "resultat": r.resultat})
        except Exception as e:
            fel_n += 1
            print("    FEL  %-18s %s: %s" % (namn, type(e).__name__, str(e)[:100]))
            utfall.append({"verktyg": namn, "args": args, "ok": False,
                           "fel": "%s: %s" % (type(e).__name__, e)})
            if isinstance(e, BryggFel) and e.traceback:
                print("         " + (e.traceback or "").strip().splitlines()[-1][:110])

    print("\n  === verktyg utan forutsattningar (provas anda, arligt redovisat) ===")
    for namn, (varfor, args) in sorted(UTAN_FORUTSATTNING.items()):
        try:
            r = _kor(utf, namn, args)
            print("    OK   %-18s %s" % (namn, json.dumps(r.resultat)[:80]))
            utfall.append({"verktyg": namn, "ok": True, "resultat": r.resultat,
                           "anm": varfor})
        except Exception as e:
            print("    ---  %-18s %s (%s)" % (namn, str(e)[:70], varfor))
            utfall.append({"verktyg": namn, "ok": None, "varfor": varfor,
                           "fel": "%s: %s" % (type(e).__name__, e)})

    print("\n  === verktyg som doder pumpen, provas sist ===")
    for namn, args in SIST:
        try:
            r = _kor(utf, namn, args)
            ok_n += 1
            print("    OK   %-18s %s" % (namn, json.dumps(r.resultat)[:80]))
            utfall.append({"verktyg": namn, "ok": True, "resultat": r.resultat})
        except Exception as e:
            print("    DOD  %-18s %s" % (namn, str(e)[:80]))
            utfall.append({"verktyg": namn, "ok": None,
                           "varfor": "app.save() stoppar simuleringen",
                           "fel": "%s: %s" % (type(e).__name__, e)})

    provade = (set(n for n, _ in ORDNING) | set(n for n, _ in SIST)
               | set(UTAN_FORUTSATTNING))
    saknas = sorted(set(V.REGISTER) - provade)
    print("\n  %d anrop lyckades, %d foll. %d av %d verktyg provade%s"
          % (ok_n, fel_n, len(provade), len(V.REGISTER),
             (", oprovade: " + ", ".join(saknas)) if saknas else ""))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(utfall, f, indent=2, ensure_ascii=False)
    k.stang()
    return 1 if fel_n else 0


if __name__ == "__main__":
    sys.exit(main())
