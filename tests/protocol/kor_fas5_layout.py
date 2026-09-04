# -*- coding: utf-8 -*-
"""L3: fas 5:s grind - mallayouter byggda i VC med NOLL kollisioner.

70_faser.md: "N mallayouter byggda: noll kollisioner, alla granssnitt kopplade."

Layoutmotorn loser scenerna utanfor VC och sager noll overlapp. Det ar dess EGEN
matning. Den har korningen bygger samma layouter i VC med verklig geometri och
later VC:s EGEN geometri doma, genom vcNode.measureDistance - en oberoende domare pa
samma fraga.

Matt i M-36: vcCollisionDetector duger inte. Dess NodeListA tar emot en lista och
tommer den tyst, sa detektorn svarar alltid noll. measureDistance ger daremot
exakt ratt avstand, forutsatt att node.update() och sim.update() korts mellan
flytt och matning (M-11:s efterslapning, tredje gangen den biter).

Avstand 0.0 betyder nuddar ELLER overlappar; mattet skiljer inte de tva. For en
grind som kraver noll kollisioner racker det.

Och det trasiga fallet: tva objekt flyttas medvetet in i varandra. Upptacker
detektorn inte det ar den ingen grind, och da betyder de grona svaren ingenting.

    python3 tests/protocol/kor_fas5_layout.py [--scener N]
"""
import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))

from vc_assist_svc.klient import Klient, BryggFel          # noqa: E402
from vc_assist_svc.tokenplats import tokenfil        # noqa: E402
from vc_assist_svc.layout import provscener as PS          # noqa: E402

M_PER_VC = 1000.0          # meter -> VC:s varldsenhet. MATT i M-33.


def _bygg_kod(namn_prefix, objekt):
    """Python 2.7-kod som bygger objekten som block i VC.

    Blocket vaxer fran sitt ursprung i +X, +Y, +Z (matt: ett 1200x800x144-block
    far BoundCenter [600, 400, 72]). Layoutmotorns pose ar objektets MITT, sa
    ursprunget laggs en halv utstrackning bakom.
    """
    rader = ["import json", "app = getApplication()", "byggda = []"]
    for o in objekt:
        rader += [
            "for _c in list(app.Components):",
            "    if _c.Name == %r:" % str(o["namn"]),
            "        app.deleteComponent(_c)",
            "_k = app.createComponent()",
            "_k.Name = %r" % str(o["namn"]),
            "_f = _k.RootFeature.createFeature(VC_BLOCK, str('kropp'))",
            "for _p in _f.Properties:",
            "    if _p.Name == 'Length':",
            "        _p.Value = %.3f" % o["langd_mm"],
            "    elif _p.Name == 'Width':",
            "        _p.Value = %.3f" % o["bredd_mm"],
            "    elif _p.Name == 'Height':",
            "        _p.Value = %.3f" % o["hojd_mm"],
            "_m = _k.PositionMatrix",
            "_m.setWPR(0.0, 0.0, %.3f)" % o["gir"],
            "_k.PositionMatrix = _m",
            "_m = _k.PositionMatrix",
            "_m.translateAbs(%.3f - _m.P.X, %.3f - _m.P.Y, %.3f - _m.P.Z)"
            % (o["x_mm"], o["y_mm"], o["z_mm"]),
            "_k.PositionMatrix = _m",
            "byggda.append(_k.Name)",
        ]
    rader.append("print(json.dumps({'byggda': byggda}))")
    return "\n".join(rader)


MATKOD = """import json
app = getApplication()
sim = getSimulation()
namn = %r
noder = []
for n in namn:
    c = app.findComponent(str(n))
    if c is not None:
        c.update()
        noder.append(c)
sim.update()
par = []
traffar = []
for i in range(len(noder)):
    for j in range(i + 1, len(noder)):
        etikett = noder[i].Name + '+' + noder[j].Name
        try:
            d = float(noder[i].measureDistance(noder[j])[0])
        except Exception as e:
            par.append({'par': etikett, 'fel': type(e).__name__})
            continue
        par.append({'par': etikett, 'avstand_mm': round(d, 2)})
        if d <= 0.0:
            traffar.append(etikett)
print(json.dumps({'traffar': traffar, 'par': par}))
"""


def _stodjande_par(relationer):
    """Par som FAR nudda: nagot som star PA nagot annat.

    Grinden ar noll kollisioner, men en stapel ar inte en kollision. L-02 ar
    "tva mellanlagg staplade pa EUR-pall", och dess egna relationer sager att
    lager_2 star pa lager_1. Att de nuddar ar RATT svar, och en grind som
    faller det mater fel storhet.

    Undantaget kommer ur scenens EGNA deklarerade relationer, inte ur en
    bekvamlighet: allt som inte ar deklarerat stodjande maste ha avstand > 0.
    """
    par = set()
    for r in relationer:
        if type(r).__name__ != "Pa":
            continue
        mal = getattr(r, "mal", None)
        underlag = getattr(r, "underlag", None)
        if isinstance(mal, str) and isinstance(underlag, str):
            par.add(tuple(sorted((mal, underlag))))
    return par


def _objekt_ur(scen, los):
    ut = []
    for namn, pose in sorted(los.placeringar.items()):
        o = scen.objekt(namn)
        ut.append({
            "namn": namn,
            "langd_mm": o.langd.som_mm, "bredd_mm": o.bredd.som_mm, "hojd_mm": o.hojd.som_mm,
            # motorns pose ar mitten; blocket vaxer fran ursprunget
            "x_mm": pose.x_m * M_PER_VC - o.langd.som_mm / 2.0,
            "y_mm": pose.y_m * M_PER_VC - o.bredd.som_mm / 2.0,
            "z_mm": pose.z_m * M_PER_VC,
            "gir": pose.vridning_grader,
        })
    return ut


GRANSSNITTSKOD = """import json
app = getApplication()
ut = {'byggda': [], 'kopplingar': []}

def bygg(namn, kontakttyp):
    for c in list(app.Components):
        if c.Name == namn:
            app.deleteComponent(c)
    c = app.createComponent()
    c.Name = namn
    stig = c.createBehaviour(VC_ONEWAYPATH, str('Stig'))
    ifc = c.createBehaviour(VC_ONETOONEINTERFACE, str('Flow'))
    sek = ifc.createSection(str('Sec'))
    falt = sek.createField(VC_FLOWFIELD, str('Flode'))
    kontakt = None
    for kk in stig.Connectors:
        if kk.Type == kontakttyp:
            kontakt = kk
            break
    for p in falt.Properties:
        if p.Name == 'Container':
            p.Value = stig
        elif p.Name == 'Port' and kontakt is not None:
            p.Value = kontakt.Index
        elif p.Name == 'PortName' and kontakt is not None:
            p.Value = str(kontakt.Name)
    ut['byggda'].append({'namn': namn, 'kontakt': kontakt.Name if kontakt else None})
    return ifc

kedja = %d
grans = []
for i in range(kedja):
    grans.append((bygg('Kedja%%dU' %% i, VC_CONNECTOR_OUTPUT),
                  bygg('Kedja%%dI' %% i, VC_CONNECTOR_INPUT)))
for i, (ut_if, in_if) in enumerate(grans):
    kan = bool(ut_if.canConnect(in_if))
    kopplad = bool(ut_if.connect(in_if)) if kan else False
    ut['kopplingar'].append({'par': i, 'canConnect': kan, 'connect': kopplad,
                             'IsConnected': bool(ut_if.IsConnected),
                             'till': ut_if.ConnectedComponent.Name
                                     if ut_if.ConnectedComponent else None})
print(json.dumps(ut))
"""


def _kor(k, kod, desc, t=90):
    post = k.anrop("exec_queue", {"code": kod, "desc": desc,
                                  "tillat_skriptbeteende": True})["result"]
    ut = k.godkann_och_vanta(post["qid"], timeout=t)
    if ut["state"] != "done":
        sv = ut.get("svar") or {}
        tb = (sv.get("error") or {}).get("traceback") or ""
        rad = (tb.strip().splitlines() or ["?"])[-1]
        raise RuntimeError("%s: %s (%s)" % (desc, ut["state"], rad[:140]))
    return ((ut.get("svar") or {}).get("result") or {}).get("result") or {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    # Ingen standardsokvag. Den gamla ("~/.wine-vc-test/drive_c/users/anton/
    # vc_assist_token") bar tre antaganden som alla ar falska pa Windows: att
    # det finns ett wine-prefix, vad det heter, och vad anvandaren heter.
    ap.add_argument("--token", default=None,
                    help="tokenfilen. Utan flaggan soks den upp; se "
                         "vc_assist_svc.tokenplats")
    ap.add_argument("--scener", type=int, default=4)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=120.0).anslut()
    k.kor("print(1)")          # lamnar degraded om bryggan star dar

    losta = []
    for ps in PS.PROVSCENER:
        scen, los = ps.kor()
        _s2, relationer = ps.bygg()
        if str(los.status).endswith("LOST"):
            losta.append((ps, scen, los, _stodjande_par(relationer)))
        if len(losta) >= a.scener:
            break

    utfall = []
    fel = 0
    print("  === mallayouter byggda i VC, kollisioner matta av VC ===")
    for ps, scen, los, stod in losta:
        objekt = _objekt_ur(scen, los)
        try:
            _kor(k, _bygg_kod(ps.id, objekt), "bygg %s" % ps.id)
            d = _kor(k, MATKOD % [o["namn"] for o in objekt],
                     "mat kollisioner i %s" % ps.id)
            traffar = [t for t in (d.get("traffar") or [])
                       if tuple(sorted(t.split("+"))) not in stod]
            stodjande = [t for t in (d.get("traffar") or [])
                         if tuple(sorted(t.split("+"))) in stod]
            minsta = [p for p in (d.get("par") or []) if p.get("avstand_mm") is not None]
            minsta_v = min([p["avstand_mm"] for p in minsta]) if minsta else None
            ok = not traffar
            if not ok:
                fel += 1
            extra = (", %d deklarerat stodjande" % len(stodjande)) if stodjande else ""
            print("    %s %-11s %d objekt, %d par, %d traffar, minsta avstand %s mm%s"
                  % ("OK  " if ok else "FEL ", ps.id, len(objekt),
                     len(d.get("par") or []), len(traffar), minsta_v, extra))
            utfall.append({"scen": ps.id, "objekt": len(objekt),
                           "traffar": traffar, "stodjande": stodjande,
                           "minsta_mm": minsta_v, "ok": ok})
        except Exception as e:
            fel += 1
            print("    FEL  %-6s %s" % (ps.id, str(e)[:110]))
            utfall.append({"scen": ps.id, "fel": str(e)[:200]})

    print("\n  === granssnitt kopplade pa GRANSSNITTSNIVA (M-37) ===")
    try:
        d = _kor(k, GRANSSNITTSKOD % 3, "koppla tre granssnittspar")
        kopp = d.get("kopplingar") or []
        alla = [x for x in kopp if x.get("connect") and x.get("IsConnected")]
        print("    %s %d av %d par kopplade: %s"
              % ("OK  " if len(alla) == len(kopp) and kopp else "FEL ",
                 len(alla), len(kopp),
                 ", ".join("%s" % x.get("till") for x in alla)))
        if len(alla) != len(kopp) or not kopp:
            fel += 1
        utfall.append({"granssnittspar": len(kopp), "kopplade": len(alla)})
    except Exception as e:
        fel += 1
        print("    FEL  %s" % str(e)[:120])

    print("\n  === det trasiga fallet: tva objekt flyttas in i varandra ===")
    try:
        ps, scen, los, stod = losta[0]
        objekt = _objekt_ur(scen, los)
        objekt[1]["x_mm"] = objekt[0]["x_mm"]
        objekt[1]["y_mm"] = objekt[0]["y_mm"]
        objekt[1]["z_mm"] = objekt[0]["z_mm"]
        _kor(k, _bygg_kod("trasig", objekt), "bygg overlappande")
        d = _kor(k, MATKOD % [o["namn"] for o in objekt], "mat overlappet")
        traffar = d.get("traffar") or []
        if traffar:
            print("    OK   detektorn faller overlappet: %s" % ", ".join(traffar))
            utfall.append({"trasigt_fall": "fallt", "traffar": traffar})
        else:
            print("    FEL  detektorn sag INGET overlapp - da ar den ingen grind")
            fel += 1
            utfall.append({"trasigt_fall": "slapptes igenom", "par": d.get("par")})
    except Exception as e:
        fel += 1
        print("    FEL  %s" % str(e)[:130])

    print("\n  %d av %d prov gick igenom" % (len(utfall) - fel, len(utfall)))
    if a.json:
        with open(a.json, "w") as f:
            json.dump(utfall, f, indent=2, ensure_ascii=False)
    k.stang()
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main())
