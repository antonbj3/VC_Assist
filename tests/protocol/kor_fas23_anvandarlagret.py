# -*- coding: utf-8 -*-
"""Fas 23: vad användaren ser när något har dött, och om det kommer tillbaka.

Fas 17 stängde ytan som visar vad som händer MEDAN en körning går. Den här
körningen mäter den andra halvan, och den är den svårare: en körning som lever
kan berätta vad den gör, men ett delsystem som dog kan inte berätta någonting
alls. Tystnaden måste tolkas av någon annan än den som tystnade.

Fyra dödsfall, operatörens egna ord:

    "VC stängs under en körning. Bryggan tappar sin socket. OpenPLC svarar
     inte. Modellen tar slut mitt i en reparation."

Körs:
    python3 tests/protocol/kor_fas23_anvandarlagret.py
    python3 tests/protocol/kor_fas23_anvandarlagret.py --visa
    python3 tests/protocol/kor_fas23_anvandarlagret.py --json ut.json

Ingen VC, ingen brygga, ingen OpenPLC, ingen språkmodell. EN sak är dock inte
en attrapp: mätningen av `connect()` mot en lyssnande socket som ingen
accepterar körs mot en riktig socket i den här processen. Det är premissen bakom
regel L-1, och den skulle vara värdelös som attrapp.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Nar ett delsystem dor far den som vantar se VILKET som dog, hur det "
        "syntes och om det finns en vag tillbaka - tystnaden tolkas av nagon "
        "annan an den som tystnade, och en vag som lyckats syns i ytan.",
    "under_prov": (
        "svc/vc_assist_svc/aterhamtning/lagen.py",
        "svc/vc_assist_svc/aterhamtning/grind.py",
        "svc/vc_assist_svc/aterhamtning/yta.py",
        "svc/vc_assist_svc/aterhamtning/bild.py",
        "svc/vc_assist_svc/aterhamtning/stegen.py",
        "svc/vc_assist_svc/aterhamtning/kallor.py",
    ),
    "facit":
        "lagen, overgangarna och vagarna tillbaka som de star i "
        "28_lagen_och_aterhamtning.md, och regel L-1: laget avgors av ett "
        "ping-svar, aldrig av att en anslutning gick att oppna",
    "facitkalla":
        "docs/spec/28_lagen_och_aterhamtning.md och 27_operatorsflodet.md, "
        "skrivna fore korningen. Premissen bakom L-1 mats dessutom mot en "
        "RIKTIG socket som ingen accepterar, i den har processen - som "
        "attrapp hade den matningen varit vardelos.",
    "facitkalla_filer": (
        "docs/spec/28_lagen_och_aterhamtning.md",
        "docs/spec/27_operatorsflodet.md",
    ),
    "trasiga_fall": (
        "connect() mot en socket ingen accepterar lyckas, och far darfor "
        "ALDRIG tolkas som ett levande lage (regel L-1)",
        "en frusen klocka far inte fa ett dott delsystem att se levande ut - "
        "lasarens klocka ska ge OBESTAMT",
        "en yta som visar en lyckad aterkomst utan bevisraden ur loggen falls "
        "av atergrinden",
        "ett dolt delsystem eller en dold vag maste raknas i ytans egna "
        "'totalt, visar'-rader",
    ),
    "kraver": ("inget",),
    "matningar": ("M-103",),
}

import argparse
import json
import os
import socket
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.aterhamtning import bild as B          # noqa: E402
from vc_assist_svc.aterhamtning import grind as G         # noqa: E402
from vc_assist_svc.aterhamtning import kallor as K        # noqa: E402
from vc_assist_svc.aterhamtning import lagen as L         # noqa: E402
from vc_assist_svc.aterhamtning import stegen as S        # noqa: E402
from vc_assist_svc.aterhamtning import yta as Y           # noqa: E402

LOGGAR = {K.BOOTLOGG: ("OnAppInitialized\nloadCommand uri=vcAssistBridge\n"
                       "bridge_cmd executed\n"
                       "brygg-komponenten byggd, skriptet kompilerar\n"),
          K.BRYGGLOGG: ("startar pa 127.0.0.1:8901\n"
                        "lyssnar pa 127.0.0.1:8901\npumpen igang\n"
                        "koad q1: spara layouten\n"
                        "  varning: q1 dodar pumpen (save)\n"
                        "simuleringen stoppad\n")}

NU = 1000.0


def _levande():
    b = B.Systembild("fas23", klocka=lambda: NU)
    b.notera(B.Avlasning("bryggan", NU - 0.1, True, kor=True, keepalive=True))
    b.notera(B.Avlasning("OpenPLC", NU - 0.1, True))
    b.notera(B.Avlasning("modellen", NU - 0.1, True))
    return b


# ------------------------------------------------------ de fyra dödsfallen

def _fall_vc():
    b = _levande()
    K.vc_avslutades(b, "ConnectionResetError: [Errno 104] Connection reset "
                       "by peer")
    return b


def _fall_socket():
    b = _levande()
    K.fran_bryggfel(b, ConnectionResetError(104, "Connection reset by peer"),
                    anslutning_oppnades=True, svarade_efterat=True)
    # Det enda av de fyra dar systemet far forsoka sjalvt. Forsoket
    # registreras, och tabellen sager att det KAN lyckas.
    b.borja_forsok(L.ANSLUT_IGEN, L.SOCKET_BRUTEN)
    return b


def _fall_plc():
    b = _levande()
    for nr in (1, 2, 3):
        b.las_av("OpenPLC", False, fel="OPC UA svarade inte inom 5.0 s",
                 orsak="plc_svarar_inte")
    K.fran_kopplarfel(b, RuntimeError(
        "kopplaren gav upp efter 3 raka fel; sista: OPC UA svarade inte "
        "inom 5.0 s"))
    return b


def _fall_modell():
    b = _levande()
    K.fran_modellfel(b, RuntimeError(
        "Modellfel: inspelningen tog slut efter 3 fragor"))
    return b


DODSFALL = (
    ("VC stangs under en korning", _fall_vc),
    ("bryggan tappar sin socket", _fall_socket),
    ("OpenPLC svarar inte", _fall_plc),
    ("modellen tar slut mitt i en reparation", _fall_modell),
)


def kor_dodsfallen(visa=False):
    ut = []
    for namn, bygg in DODSFALL:
        b = bygg()
        blick = B.blicka(b, klocka=lambda: NU)
        text = Y.rendera(blick, LOGGAR)
        dom = G.granska(blick, text, LOGGAR)
        orsak = blick.orsak(
            Y.allvarligast(blick)) or L.OKAND
        mojliga, omojliga = Y.mojliga_och_omojliga(blick)
        ut.append({
            "fall": namn,
            "lage": "%s %s" % (Y.allvarligast(blick),
                               blick.lage(Y.allvarligast(blick))),
            "orsak": orsak.nyckel,
            "vagar": len(orsak.vagar),
            "nagot_forsoker": bool(mojliga),
            "tecken": len(text),
            "grind": "GODKAND" if dom.ok else dom.text(),
        })
        if visa:
            print("\n" + "=" * 72)
            print("DODSFALL: %s" % namn)
            print("=" * 72)
            print(text)
    return ut


# ----------------------------------------------- den tredje nollade klockan

def _frusen(bild, delsystem):
    sista = bild.sista(delsystem)
    return B.lage_for(bild, delsystem, sista.t)


def kor_frusen_klocka(n=60):
    """Sonden svarade en gang och dog. Vad sager de tva harledningarna?"""
    b = B.Systembild("frusen", klocka=lambda: NU)
    b.notera(B.Avlasning("bryggan", NU, True, kor=True))
    frusna = [_frusen(b, "bryggan") for _k in range(n)]
    arliga = [B.lage_for(b, "bryggan", NU + k) for k in range(1, n + 1)]
    return {
        "avlasningar": n,
        "frusen_klocka_sager_levande": sum(
            1 for x in frusna if x in L.LEVANDE),
        "lasarens_klocka_sager_levande": sum(
            1 for x in arliga if x in L.LEVANDE),
        "lasarens_klocka_sager_obestamt": arliga.count(L.OBESTAMT),
    }


def kor_connect_mot_dod_pump(n=20, timeout=0.05):
    """En RIKTIG socket som ingen accepterar. Premissen bakom regel L-1."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(128)
    port = srv.getsockname()[1]
    anslot = svarade = 0
    tider = []
    try:
        for _k in range(n):
            t0 = time.time()
            s = socket.create_connection(("127.0.0.1", port), timeout=1.0)
            tider.append((time.time() - t0) * 1000.0)
            anslot += 1
            s.settimeout(timeout)
            try:
                s.sendall(b'{"op":"ping"}\n')
                svar = s.recv(100)
            except (socket.timeout, OSError):
                svar = b""
            if svar:
                svarade += 1
            s.close()
    finally:
        srv.close()
    tider.sort()
    return {"forsok": n, "connect_lyckades": anslot, "ping_svarade": svarade,
            "connect_median_ms": round(tider[len(tider) // 2], 3)}


# ------------------------------------------------------- vad tabellen bar

def kor_aterkomsten():
    """Kommer systemet tillbaka? Ett fall i taget, och svaret ar oftast nej.

    Bara EN av de fyra har en vag systemet kan ga sjalvt. Att vagen finns
    racker inte: den ska ocksa synas i ytan nar den lyckats, annars vet den
    som vantade aldrig att vantan tog slut.
    """
    ut = []
    for namn, bygg in DODSFALL:
        b = bygg()
        blick = B.blicka(b, klocka=lambda: NU)
        d = Y.allvarligast(blick)
        orsak = blick.orsak(d)
        mojliga, _omojliga = Y.mojliga_och_omojliga(blick)
        rad = {"fall": namn, "delsystem": d,
               "automatisk_vag": orsak.automatisk.nyckel
               if orsak and orsak.automatisk else None,
               "pagaende_forsok": len(mojliga),
               "kom_tillbaka": False, "syns_i_ytan": False}
        if mojliga:
            forsok = mojliga[0][0]
            b.avsluta_forsok(forsok, True, "ping svarade: tick=41233")
            b.las_av(d, True, kor=True)
            efter = B.blicka(b, klocka=lambda: NU)
            text = Y.rendera(efter, LOGGAR)
            rad["kom_tillbaka"] = efter.lage(d) in L.LEVANDE
            rad["syns_i_ytan"] = ("lyckades" in text
                                  and "tick=41233" in text)
            rad["grind"] = ("GODKAND" if G.granska(efter, text, LOGGAR).ok
                            else "FALLD")
        ut.append(rad)
    return ut


def kor_tabellen():
    med_automatik = [o for o in L.ORSAKER if o.automatisk is not None]
    matt = [o for o in med_automatik
            if L.kan_lyckas(o, o.automatisk) == L.KAN_JA]
    lovar_sjalvstart = [o.nyckel for o in L.ORSAKER
                        if L.kan_lyckas(o, L.SJALVSTART) == L.KAN_JA]
    return {
        "orsaker": len(L.ORSAKER),
        "med_automatiskt_forsok": len(med_automatik),
        "matt_att_kunna_lyckas": len(matt),
        "kraver_operatoren": len(L.ORSAKER) - len(med_automatik),
        "orsaker_som_lovar_sjalvstart": len(lovar_sjalvstart),
        "vagar": len(L.VAGAR),
        "lagen": len(L.LAGEN),
        "regler": len(G.REGLER),
    }


def kor_ovissheten():
    """Hur stor del av ytan handlar om vad systemet INTE vet? M-60:s form."""
    ut = {}
    for namn, bygg in DODSFALL:
        blick = B.blicka(bygg(), klocka=lambda: NU)
        text = Y.rendera(blick, LOGGAR)
        i = text.find(Y.RUBRIK_VET_INTE)
        j = text.find("\nLÄST:", i)
        ovisst = len(text[i:j if j > 0 else len(text)])
        ut[namn] = {"tecken": len(text), "ovisst": ovisst,
                    "andel": round(100.0 * ovisst / len(text), 1)}
    return ut


def kor_stegen_over_fallorna():
    """De fem tysta fallorna ur 27_operatorsflodet.md §3, genom stegen."""
    fall = [
        ("fel Python N-niva", "", LOGGAR[K.BRYGGLOGG], "kroken_fyrade_inte"),
        ("syntaxfel i modulen", "OnAppInitialized\nloadCommand uri=x\n"
                                "bridge_cmd executed\n",
         LOGGAR[K.BRYGGLOGG], "skriptet_kompilerar_inte"),
        ("OnRun utan vcScript", LOGGAR[K.BOOTLOGG],
         "startar pa 127.0.0.1:8901\nlyssnar pa 127.0.0.1:8901\n",
         "operatoren_stoppade"),
        ("porten upptagen", LOGGAR[K.BOOTLOGG],
         "startar pa 127.0.0.1:8901\n", "port_upptagen"),
        ("loggen gick inte att lasa", None, None, "okand"),
    ]
    ut = []
    for namn, boot, brygg, vantad in fall:
        svaren = S.kor_stegen({S.BOOTLOGG: boot, S.BRYGGLOGG: brygg})
        orsak, steget = S.orsak_ur_stegen(svaren)
        ut.append({"falla": namn, "orsak": orsak.nyckel,
                   "ratt": orsak.nyckel == vantad,
                   "steg": steget.steg.nr if steget else None,
                   "tal": S.sammanfatta(svaren)})
    return ut


def main(argv=None):
    p = argparse.ArgumentParser(prog="kor_fas23_anvandarlagret.py")
    p.add_argument("--visa", action="store_true",
                   help="skriv ut hela ytan for varje dodsfall")
    p.add_argument("--json", metavar="FIL", default=None)
    a = p.parse_args(argv)

    resultat = {
        "dodsfall": kor_dodsfallen(visa=a.visa),
        "frusen_klocka": kor_frusen_klocka(),
        "connect_mot_dod_pump": kor_connect_mot_dod_pump(),
        "aterkomsten": kor_aterkomsten(),
        "tabellen": kor_tabellen(),
        "ovissheten": kor_ovissheten(),
        "stegen": kor_stegen_over_fallorna(),
    }

    print("\n" + "=" * 72)
    print("FAS 23 - ATERHAMTNINGEN SOM ANVANDAREN SER DEN")
    print("=" * 72)

    print("\nDE FYRA DODSFALLEN")
    print("%-40s %-22s %-9s %s" % ("fall", "lage", "forsoker", "grind"))
    for r in resultat["dodsfall"]:
        print("%-40s %-22s %-9s %s"
              % (r["fall"][:40], r["lage"], "ja" if r["nagot_forsoker"]
                 else "nej", r["grind"][:20]))

    print("\nKOMMER SYSTEMET TILLBAKA?")
    print("  %-40s %-16s %-10s %s"
          % ("fall", "automatisk vag", "kom igen", "syns i ytan"))
    for r in resultat["aterkomsten"]:
        print("  %-40s %-16s %-10s %s"
              % (r["fall"][:40], r["automatisk_vag"] or "-",
                 "ja" if r["kom_tillbaka"] else "nej",
                 "ja" if r["syns_i_ytan"] else "-"))

    f = resultat["frusen_klocka"]
    print("\nDEN TREDJE NOLLADE KLOCKAN (%d avlasningar av EN sond som dog)"
          % f["avlasningar"])
    print("  frusen klocka sager LEVANDE i   %d av %d"
          % (f["frusen_klocka_sager_levande"], f["avlasningar"]))
    print("  lasarens klocka sager LEVANDE i %d av %d"
          % (f["lasarens_klocka_sager_levande"], f["avlasningar"]))
    print("  lasarens klocka sager OBESTAMT i %d av %d"
          % (f["lasarens_klocka_sager_obestamt"], f["avlasningar"]))

    c = resultat["connect_mot_dod_pump"]
    print("\nCONNECT MOT EN SOCKET INGEN ACCEPTERAR (riktig socket)")
    print("  connect() lyckades  %d av %d, median %.3f ms"
          % (c["connect_lyckades"], c["forsok"], c["connect_median_ms"]))
    print("  ping svarade        %d av %d" % (c["ping_svarade"], c["forsok"]))

    t = resultat["tabellen"]
    print("\nVAD TABELLEN BAR")
    for nyckel in ("lagen", "orsaker", "vagar", "med_automatiskt_forsok",
                   "matt_att_kunna_lyckas", "kraver_operatoren",
                   "orsaker_som_lovar_sjalvstart", "regler"):
        print("  %-30s %d" % (nyckel, t[nyckel]))

    print("\nHUR STOR DEL AV YTAN HANDLAR OM VAD SYSTEMET INTE VET")
    for namn, v in resultat["ovissheten"].items():
        print("  %-40s %5d tecken, %4.1f %%"
              % (namn[:40], v["tecken"], v["andel"]))

    print("\nSTEGEN MOT DE FEM TYSTA FALLORNA")
    for r in resultat["stegen"]:
        print("  %-28s -> %-26s %s  (%s)"
              % (r["falla"], r["orsak"], "RATT" if r["ratt"] else "FEL",
                 r["tal"]))

    fel = [r for r in resultat["dodsfall"] if r["grind"] != "GODKAND"]
    fel += [r for r in resultat["aterkomsten"]
            if r.get("grind", "GODKAND") != "GODKAND"
            or (r["pagaende_forsok"] and not r["syns_i_ytan"])]
    fel += [r for r in resultat["stegen"] if not r["ratt"]]
    if c["ping_svarade"] != 0 or c["connect_lyckades"] != c["forsok"]:
        fel.append({"connect": c})
    print("\n%s" % ("ALLT GRONT" if not fel else "ROTT: %d punkter" % len(fel)))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(resultat, fh, ensure_ascii=False, indent=2)
        print("skrev %s" % a.json)
    return 0 if not fel else 1


if __name__ == "__main__":
    sys.exit(main())
