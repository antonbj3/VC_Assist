# -*- coding: utf-8 -*-
"""M-67: positionerar en koppling komponenterna, eller kopplar den bara logiskt?

Fragan avgor hela kompositionslagrets design, och ingen matning svarar pa den.
Antingen raknar var layoutlosare ut varje lage sjalv, eller sa snapper VC ihop
delarna - och da ska vi LATA BLI att rakna. Tva helt olika program.

Provet ar enkelt och darfor svart att missforsta: bygg tva komponenter med
gransssnitt pa KANDA, atskilda lagen. Las varldslaget. Koppla. Las igen.

  * Rors ingenting  -> kopplingen ar logisk. Layoutlosaren ager geometrin.
  * Flyttas den ena -> VC snapper. Da ska losaren placera EN av dem och lata
                       VC gora resten, annars slass tva rakningar om samma lage.

DET TRASIGA FALLET: tva komponenter som INTE gar att koppla (tva utgangar) far
inte flyttas. En koppling som misslyckas och anda flyttar nagot ar samre an en
som bara misslyckas - da ser scenen byggd ut fast den inte ar det.

Kors mot en levande brygga:
    python3 tests/protocol/kor_m67_kopplingens_geometri.py [--json ut.json]
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "En koppling i VC flyttar inte komponenterna, sa layoutlosaren ager "
        "geometrin och maste rakna ut varje lage sjalv.",
    "under_prov": (
        "svc/vc_assist_svc/layout/losare.py",
        "svc/vc_assist_svc/layout/relationer.py",
    ),
    "facit":
        "varldslaget fore och efter connect() ska vara identiskt: noll "
        "millimeters flytt och noll vridning, bade for den lyckade och den "
        "misslyckade kopplingen",
    "facitkalla":
        "VC:s egen scengraf: WorldPositionMatrix last fore och efter "
        "connect() i en korande VC, efter sim.update(). Facit ar alltsa VC:s "
        "eget svar och inte var modell av det.",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "tva utgangar gar inte att koppla, och en misslyckad koppling far "
        "INTE flytta nagot - da ser scenen byggd ut utan att vara det",
        "utan sim.update() fore avlasningen mater provet fel storhet och "
        "skulle svara 'ingenting rorde sig' aven nar allt gjorde det",
    ),
    "kraver": ("vc",),
    "matningar": ("M-67",),
}

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.klient import BryggFel, Klient                # noqa: E402
from vc_assist_svc.tokenplats import tokenfil                    # noqa: E402

# Lagena komponenterna byggs pa. Atskilda i alla tre riktningar och vridna, sa
# att bade en flytt och en vridning syns. Talen ar godtyckliga och styr ingen
# dom - de ar provets uppstallning, inte en troskel.
A_LAGE = (0.0, 0.0, 0.0)
B_LAGE = (1500.0, 700.0, 250.0)

KOD = r'''
import json

app = getApplication()
sim = getSimulation()
ut = {"par": []}


def lage(komp):
    """Varldslaget i millimeter plus riktningsvektorn.

    WorldPositionMatrix slapar ett scenuppdateringssteg (M-11), sa den som
    laser utan update() far foregaende varv. Darfor update() forst - annars
    matter provet fel storhet och skulle svara 'ingenting rorde sig' aven nar
    allt gjorde det.
    """
    sim.update()
    m = komp.WorldPositionMatrix
    p, n = m.P, m.N
    return {"x": round(p.X, 3), "y": round(p.Y, 3), "z": round(p.Z, 3),
            "nx": round(n.X, 5), "ny": round(n.Y, 5), "nz": round(n.Z, 5)}


def skillnad(fore, efter):
    d = sum((efter[k] - fore[k]) ** 2 for k in ("x", "y", "z")) ** 0.5
    v = sum((efter[k] - fore[k]) ** 2 for k in ("nx", "ny", "nz")) ** 0.5
    return {"flytt_mm": round(d, 3), "vridning": round(v, 5)}


def bygg(namn, kontakttyp, x, y, z):
    for c in list(app.Components):
        if c.Name == namn:
            app.deleteComponent(c)
    c = app.createComponent()
    c.Name = namn
    # MATT: vcMatrix har ingen setP ("NameError: Attribute or method 'setP'
    # not found."). Laget satts som byggrecepten satter det: translateAbs ar
    # RELATIV i absoluta axlar (M-11), sa en absolut position ar skillnaden
    # mot nuvarande lage.
    m = c.PositionMatrix
    m.translateAbs(x - m.P.X, y - m.P.Y, z - m.P.Z)
    c.PositionMatrix = m
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
    return c, ifc


def prov(namn, typ_a, typ_b, vantas_ga):
    ka, ia = bygg(namn + 'A', typ_a, %(ax)f, %(ay)f, %(az)f)
    kb, ib = bygg(namn + 'B', typ_b, %(bx)f, %(by)f, %(bz)f)
    fore_a, fore_b = lage(ka), lage(kb)
    kan = bool(ia.canConnect(ib))
    kopplad = bool(ia.connect(ib)) if kan else False
    efter_a, efter_b = lage(ka), lage(kb)
    ut["par"].append({
        "namn": namn,
        "vantas_ga": vantas_ga,
        "canConnect": kan,
        "connect": kopplad,
        "IsConnected": bool(ia.IsConnected),
        "A_fore": fore_a, "A_efter": efter_a, "A": skillnad(fore_a, efter_a),
        "B_fore": fore_b, "B_efter": efter_b, "B": skillnad(fore_b, efter_b),
    })
    for k in (ka, kb):
        app.deleteComponent(k)


# 1. Ut mot in: ska ga att koppla.
prov('M67ok', VC_CONNECTOR_OUTPUT, VC_CONNECTOR_INPUT, True)
# 2. Ut mot ut: gar inte. DET TRASIGA FALLET - ingenting far flyttas.
prov('M67fel', VC_CONNECTOR_OUTPUT, VC_CONNECTOR_OUTPUT, False)

print(json.dumps(ut))
''' % {"ax": A_LAGE[0], "ay": A_LAGE[1], "az": A_LAGE[2],
       "bx": B_LAGE[0], "by": B_LAGE[1], "bz": B_LAGE[2]}


def _kor(k, kod, desc, t=90):
    post = k.anrop("exec_queue", {"code": kod, "desc": desc,
                                  "tillat_skriptbeteende": True})["result"]
    ut = k.godkann_och_vanta(post["qid"], timeout=t)
    if ut["state"] != "done":
        sv = ut.get("svar") or {}
        tb = (sv.get("error") or {}).get("traceback") or ""
        rad = (tb.strip().splitlines() or ["?"])[-1]
        raise RuntimeError("%s: %s (%s)" % (desc, ut["state"], rad[:200]))
    return ((ut.get("svar") or {}).get("result") or {}).get("result") or {}


def _dom(resultat):
    """Skriver ut och lamnar antalet fall som INTE stamde."""
    fel = 0
    print("=== M-67: flyttar en koppling nagot? ===\n")
    for p in resultat.get("par", []):
        gick = p["connect"]
        stamde = gick == p["vantas_ga"]
        print("  %-8s canConnect=%-5s connect=%-5s (vantat %s) %s"
              % (p["namn"], p["canConnect"], gick, p["vantas_ga"],
                 "OK" if stamde else "FEL"))
        print("           A flyttades %8.3f mm, vred sig %.5f"
              % (p["A"]["flytt_mm"], p["A"]["vridning"]))
        print("           B flyttades %8.3f mm, vred sig %.5f"
              % (p["B"]["flytt_mm"], p["B"]["vridning"]))
        if not stamde:
            fel += 1
        if not gick and (p["A"]["flytt_mm"] > 0.001 or p["B"]["flytt_mm"] > 0.001):
            print("           FEL: en misslyckad koppling flyttade nagot")
            fel += 1
    rorde = [p for p in resultat.get("par", [])
             if p["connect"] and (p["A"]["flytt_mm"] > 0.001
                                  or p["B"]["flytt_mm"] > 0.001)]
    print("\nSVAR: kopplingen %s komponenterna."
          % ("FLYTTAR" if rorde else "flyttar INTE"))
    if rorde:
        print("  Foljd: VC snapper. Layoutlosaren ska placera EN av dem och "
              "lata VC gora resten.")
    else:
        print("  Foljd: kopplingen ar LOGISK. Layoutlosaren ager geometrin och "
              "maste rakna ut varje lage sjalv.")
    return fel


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8901)
    p.add_argument("--token")
    p.add_argument("--json")
    a = p.parse_args(argv)

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=120.0).anslut()
    k.kor("print(1)")
    resultat = _kor(k, KOD, "M-67: kopplingens geometri")
    fel = _dom(resultat)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(resultat, f, indent=2, ensure_ascii=False)
    print("\n%s" % ("ALLA FALL STAMDE" if fel == 0 else "%d FALL STAMDE INTE" % fel))
    return 0 if fel == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
