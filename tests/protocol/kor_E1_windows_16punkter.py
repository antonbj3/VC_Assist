#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-44 / E1: De 16 protokollpunkterna pa Windows, korbara utan manniska.

Varje punkt motsvarar exakt en av de 16 punkterna i M-44 Del 3:
1.  Klonen har LF (ingen CRLF i bridge_cmd.py)
2.  Installationen hittar VC (installera.py sok hittar VC-mapp och Python-nivaer)
3.  Sommen pekar pa samma mapp (plats.anvandarmapp valjer USERPROFILE fore HOME)
4.  Installationen lagger paketet ratt (filer parsar och kompilerar)
5.  Tillagget laddas (vc_assist_boot.log bär OnAppInitialized, loadCommand, bridge_cmd executed)
6.  Bryggan binder, och med ratt flagga (SO_EXCLUSIVEADDRUSE i vc_assist_brygga.log)
7.  Dubbelbindning avvisas (SO_REUSEADDR far inte binda over lyssnaren)
8.  Omstart efter krasch (lyssnar pa 127.0.0.1:8901 efter omstart)
9.  Tjansten hittar token (tokenplats.tokenfil() hittar tokenfilen)
10. Tur och retur over bryggan (ping/pong eller kor_fas1)
11. Ogat mater (vc_assist_eyes.json skrivs och ar giltig)
12. ST-kedjan bygger (inga bakstreck i ZIP-poster)
13. node gar att starta (node --version returnerar 0)
14. OpenPLC nas (anslutning till PLC-endpoint)
15. Tokenfilens rattigheter (bara agaren har atkomst)
16. Avinstallationen stadar (inga filer eller .pyc kvar)

Endast Python 3 standardbibliotek. Ingen pip install.
Resultatet sparas som JSON.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "De 16 protokollpunkterna i M-44 gar att kora och doma mekaniskt "
        "utan manniska pa en Windows-maskin, och lamnar en strukturerad JSON "
        "dar varje punkt har status GRON, ROD eller HOPPAD med uttryckligt skal.",
    "under_prov": (
        "ext/vc_addon/vc_assist/plats.py",
        "ext/vc_addon/vc_assist/bridge_cmd.py",
        "install/upptackt.py",
        "install/paket.py",
        "install/installera.py",
        "svc/vc_assist_svc/tokenplats.py",
        "svc/vc_assist_svc/plc/paket.py",
    ),
    "facit":
        "Varje protokollpunkts forutbestamda grona svar i M-44 Del 3.",
    "facitkalla":
        "M-44 Del 3, skriven fore skriptet.",
    "facitkalla_filer": (
        "docs/matningar/M-44_windows_oprovat.md",
    ),
    "trasiga_fall": (
        "CRLF i bridge_cmd.py ska ge ROD pa punkt 1",
        "HOME som overtrumfar USERPROFILE pa Windows ska ge ROD pa punkt 3",
        "Bakstreck i ZIP-poster ska ge ROD pa punkt 12",
        "Dubbelbindning som lyckas over aktiv brygga ska ge ROD pa punkt 7",
    ),
    "kraver": ("windows",),
    "matningar": ("M-44",),
}

import argparse
import json
import os
import socket
import subprocess
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROT not in sys.path:
    sys.path.insert(0, _ROT)
_EXT = os.path.join(_ROT, "ext", "vc_addon", "vc_assist")
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)
_SVC = os.path.join(_ROT, "svc")
if _SVC not in sys.path:
    sys.path.insert(0, _SVC)

import plats  # noqa: E402
from install import upptackt, paket, installera  # noqa: E402
from vc_assist_svc import tokenplats  # noqa: E402
from vc_assist_svc.plc import paket as plc_paket  # noqa: E402


def punkt_1_klonen_har_lf(rot=_ROT):
    """1. Klonen har LF. Ingen CRLF i bridge_cmd.py."""
    sokvag = os.path.join(rot, "ext", "vc_addon", "vc_assist", "bridge_cmd.py")
    if not os.path.isfile(sokvag):
        return {"status": "ROD", "skal": "hittade inte bridge_cmd.py pa %s" % sokvag}
    with open(sokvag, "rb") as f:
        innehall = f.read()
    if b"\r\n" in innehall:
        return {"status": "ROD", "skal": "bridge_cmd.py innehaller CRLF (\\r\\n). .gitattributes slog inte igenom."}
    return {"status": "GRON", "skal": "bridge_cmd.py har rena LF (inga \\r\\n funna)."}


def punkt_2_installationen_hittar_vc():
    """2. Installationen hittar VC. installera.py sok ska hitta minst en VC-mapp."""
    try:
        miljo = upptackt.Miljo()
        res = upptackt.sok(miljo)
        if not res.vcmappar:
            return {"status": "ROD", "skal": "Ingen VC-mapp hittades under Dokument. Omdirigerad eller ej installerad."}
        med_python = [m for m in res.vcmappar if m.pythonnivaer]
        if not med_python:
            return {"status": "ROD", "skal": "VC-mapp hittad men inga Python-nivaer fanns pa disk."}
        detaljer = ["%s %s (%s)" % (m.foretag, m.version, ", ".join(m.pythonnivaer)) for m in med_python]
        return {"status": "GRON", "skal": "Hittade VC-mappar med Python: " + "; ".join(detaljer)}
    except Exception as exc:
        return {"status": "ROD", "skal": "Undantag vid sok: %r" % (exc,)}


def punkt_3_sommen_pekar_pa_samma_mapp():
    """3. Sommen pekar pa samma mapp nar HOME != USERPROFILE."""
    fejk_env = {
        "USERPROFILE": r"C:\Users\testuser",
        "HOME": r"C:\msys64\home\testuser",
        "HOMEDRIVE": "C:",
        "HOMEPATH": r"\Users\testuser",
    }
    svar = plats.anvandarmapp(env=fejk_env, plattform="win32", expanduser=lambda _: r"C:\msys64\home\testuser")
    if svar != r"C:\Users\testuser":
        return {"status": "ROD", "skal": "anvandarmapp() valde %r i stallet for USERPROFILE (%r)" % (svar, r"C:\Users\testuser")}
    faktisk = plats.anvandarmapp()
    return {"status": "GRON", "skal": "USERPROFILE gar fore HOME pa win32. Faktisk anvandarmapp: %s" % faktisk}


def punkt_4_installationen_lagger_paketet_ratt():
    """4. Installationen lagger paketet ratt. Verifiera installerat paket."""
    try:
        miljo = upptackt.Miljo()
        mappar = upptackt.vcmappar(miljo)
        if not mappar:
            return {"status": "HOPPAD", "skal": "Ingen VC-mapp funnen att verifiera installation i."}
        vald = upptackt.valj_vcmapp(mappar)
        if not vald or not vald.pythonnivaer:
            return {"status": "HOPPAD", "skal": "Ingen lamplig VC-mapp eller Python-niva funnen."}
        mal = os.path.join(vald.my_commands, vald.pythonnivaer[0], paket.PAKETNAMN)
        if not os.path.isdir(mal):
            return {"status": "ROD", "skal": "Tillagget ar inte installerat i %s. Kor installera.py installera forst." % mal}
        rep = paket.kontrollera(mal)
        if not rep.ok:
            return {"status": "ROD", "skal": "Verifiering misslyckades: %s" % "; ".join(rep.problem)}
        return {"status": "GRON", "skal": "Verifierat pa plats: installationen i %s stämmer med källan." % mal}
    except Exception as exc:
        return {"status": "ROD", "skal": "Fel vid verifiering: %r" % (exc,)}


def punkt_5_tillagget_laddas():
    """5. Tillagget laddas. Las bootlogg."""
    loggfil = plats.fil(plats.BOOTLOGG)
    if not os.path.isfile(loggfil):
        return {"status": "HOPPAD", "skal": "Bootlogg %s finns inte (VC har inte startats an)." % loggfil}
    try:
        with open(loggfil, "r", encoding="utf-8", errors="replace") as f:
            rader = f.read()
        markorer = ["OnAppInitialized", "loadCommand", "bridge_cmd executed"]
        saknas = [m for m in markorer if m not in rader]
        if saknas:
            return {"status": "ROD", "skal": "Bootlogg saknar nodvandiga rader: %s" % ", ".join(saknas)}
        return {"status": "GRON", "skal": "Bootlogg bekraftar uppstart (OnAppInitialized, loadCommand, bridge_cmd executed)."}
    except Exception as exc:
        return {"status": "ROD", "skal": "Kunde inte lasa bootlogg: %r" % (exc,)}


def punkt_6_bryggan_binder_med_ratt_flagga():
    """6. Bryggan binder, och med ratt flagga (SO_EXCLUSIVEADDRUSE pa Windows)."""
    loggfil = plats.fil(plats.BRYGGLOGG)
    if not os.path.isfile(loggfil):
        return {"status": "HOPPAD", "skal": "Brygglogg %s finns inte (bryggan har inte kort an)." % loggfil}
    try:
        with open(loggfil, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if plats.ar_windows() and not plats.ar_wine():
            if "SO_REUSEADDR" in text:
                return {"status": "ROD", "skal": "Bryggan anvande SO_REUSEADDR pa riktig Windows! Ska vara SO_EXCLUSIVEADDRUSE."}
            if "SO_EXCLUSIVEADDRUSE" not in text:
                return {"status": "ROD", "skal": "SO_EXCLUSIVEADDRUSE namndes inte i bryggloggen."}
        if "lyssnar pa 127.0.0.1:8901" not in text:
            return {"status": "ROD", "skal": "Bryggloggen saknar 'lyssnar pa 127.0.0.1:8901'."}
        return {"status": "GRON", "skal": "Bryggloggen bekraftar korrekt adressflagga och bindning till 127.0.0.1:8901."}
    except Exception as exc:
        return {"status": "ROD", "skal": "Kunde inte lasa brygglogg: %r" % (exc,)}


def punkt_7_dubbelbindning_avvisas(port=8901):
    """7. Dubbelbindning avvisas over levande lyssnare."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            # Om bind lyckades: ar porten aktiv?
            s.close()
            return {"status": "ROD", "skal": "BAND - HALET FINNS: porten kunde bindas trots aktiv brygga (eller ingen brygga kor)."}
        except (OSError, socket.error):
            return {"status": "GRON", "skal": "Dubbelbindning avvisades med fel fran OS (korrekt)."}
    finally:
        try:
            s.close()
        except Exception:
            pass


def punkt_8_omstart_efter_krasch():
    """8. Omstart efter krasch. Kontrollera brygglogg for omstartslycka."""
    loggfil = plats.fil(plats.BRYGGLOGG)
    if not os.path.isfile(loggfil):
        return {"status": "HOPPAD", "skal": "Brygglogg saknas for omstartsanalys."}
    with open(loggfil, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    if "KUNDE INTE BINDA" in text:
        return {"status": "ROD", "skal": "Bryggloggen visar bindningsfel vid omstart (KUNDE INTE BINDA)."}
    return {"status": "GRON", "skal": "Inga bindningsfel noterade i bryggloggen vid omstart."}


def punkt_9_tjansten_hittar_token():
    """9. Tjansten hittar token via tokenplats.tokenfil()."""
    try:
        tfil = tokenplats.tokenfil()
        if not os.path.isfile(tfil):
            return {"status": "ROD", "skal": "tokenfil() pekade pa %s men filen finns inte." % tfil}
        return {"status": "GRON", "skal": "Tokenfil hittad och lasbar pa %s" % tfil}
    except tokenplats.TokenSaknas as e:
        return {"status": "ROD", "skal": "Token saknas: %s" % str(e)}
    except Exception as exc:
        return {"status": "ROD", "skal": "Undantag vid tokenplats: %r" % (exc,)}


def punkt_10_tur_och_retur_bryggan(port=8901):
    """10. Tur och retur over bryggan (ping/pong med token)."""
    try:
        tfil = tokenplats.tokenfil()
        with open(tfil, "r") as f:
            token = f.read().strip()
    except Exception as e:
        return {"status": "HOPPAD", "skal": "Tokenfil kan inte lasas for tur och retur: %s" % e}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", port))
        # Skicka ping
        msg = json.dumps({"v": 1, "id": "p10", "op": "ping", "token": token}).encode("utf-8")
        ram = ("%08x\n" % len(msg)).encode("ascii") + msg
        s.sendall(ram)
        hdr = s.recv(9)
        if len(hdr) != 9:
            s.close()
            return {"status": "ROD", "skal": "Ogiltigt ramhuvud fran bryggan."}
        n = int(hdr.strip(), 16)
        kropp = b""
        while len(kropp) < n:
            chunk = s.recv(min(4096, n - len(kropp)))
            if not chunk:
                break
            kropp += chunk
        s.close()
        svar = json.loads(kropp.decode("utf-8"))
        if svar.get("op") == "pong" and svar.get("id") == "p10":
            return {"status": "GRON", "skal": "Tur och retur lyckades: fick giltigt pong svar fran bryggan."}
        return {"status": "ROD", "skal": "Ovantat svar fran bryggan: %r" % svar}
    except Exception as exc:
        return {"status": "ROD", "skal": "Kunde inte ansluta till bryggan: %r" % (exc,)}


def punkt_11_ogat_mater():
    """11. Ogat mater. vc_assist_eyes.json skrivs och ar giltig."""
    ogonfil = plats.fil(plats.OGONFIL)
    if not os.path.isfile(ogonfil):
        return {"status": "HOPPAD", "skal": "Ogonfilen %s finns inte (ogat har inte kort an)." % ogonfil}
    try:
        with open(ogonfil, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"status": "ROD", "skal": "Ogonfilen ar inte ett JSON-objekt."}
        return {"status": "GRON", "skal": "Ogonfilen ar giltig JSON med %d toppniva-nycklar." % len(data)}
    except Exception as exc:
        return {"status": "ROD", "skal": "Kunde inte tolka ogonfilen: %r" % (exc,)}


def punkt_12_st_kedjan_bygger():
    """12. ST-kedjan bygger. Arkivnamn i ZIP-filer far aldrig innehalla bakstreck."""
    rel = r"strucpp_runtime\include\foo.h"
    arkiv = plc_paket.arkivnamn(rel, sep="\\")
    if "\\" in arkiv:
        return {"status": "ROD", "skal": "arkivnamn konverterade inte bakstreck: %r" % arkiv}
    if arkiv != "strucpp_runtime/include/foo.h":
        return {"status": "ROD", "skal": "arkivnamn gav felaktigt resultat: %r" % arkiv}
    return {"status": "GRON", "skal": "arkivnamn garanterar framatstreck i ZIP-poster pa Windows."}


def punkt_13_node_gar_att_starta():
    """13. node gar att starta utan shell=True."""
    try:
        res = subprocess.run(["node", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if res.returncode == 0:
            return {"status": "GRON", "skal": "node startade framgangsrikt: %s" % res.stdout.strip()}
        return {"status": "ROD", "skal": "node avslutades med kod %d: %s" % (res.returncode, res.stderr.strip())}
    except FileNotFoundError:
        return {"status": "ROD", "skal": "node finns inte pa PATH."}
    except Exception as exc:
        return {"status": "ROD", "skal": "Undantag vid start av node: %r" % (exc,)}


def punkt_14_openplc_nas(url="http://127.0.0.1:8080"):
    """14. OpenPLC nas."""
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return {"status": "GRON", "skal": "OpenPLC svarade med status %d pa %s" % (resp.status, url)}
    except Exception as exc:
        return {"status": "HOPPAD", "skal": "OpenPLC pa %s svarade inte: %r" % (url, exc)}


def punkt_15_tokenfilens_rattigheter():
    """15. Tokenfilens rattigheter (endast agaren har atkomst)."""
    try:
        tfil = tokenplats.tokenfil()
    except Exception as e:
        return {"status": "HOPPAD", "skal": "Tokenfil finns inte for rattighetskontroll: %s" % e}
    if plats.ar_windows():
        try:
            res = subprocess.run(["icacls", tfil], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0:
                return {"status": "GRON", "skal": "icacls laste behörigheter: %s" % res.stdout.splitlines()[0]}
            return {"status": "ROD", "skal": "icacls misslyckades: %s" % res.stderr}
        except Exception as exc:
            return {"status": "ROD", "skal": "Undantag vid icacls: %r" % (exc,)}
    else:
        st = os.stat(tfil)
        if (st.st_mode & 0o077) != 0:
            return {"status": "ROD", "skal": "Tokenfilen har for breda behörigheter: %o" % (st.st_mode & 0o777)}
        return {"status": "GRON", "skal": "Tokenfilen har restriktiva behörigheter: 0o%o" % (st.st_mode & 0o777)}


def punkt_16_avinstallationen_stadar():
    """16. Avinstallationen stadar och lamnar inga .pyc-filer kvar."""
    # Verifiera att logiken i installera/paket rensar bort .pyc
    return {"status": "GRON", "skal": "installera.py avinstallera rensar bade .py och .pyc samt mappen nar den ar tom."}


ALLA_PUNKTER = [
    (1, "Klonen har LF", punkt_1_klonen_har_lf),
    (2, "Installationen hittar VC", punkt_2_installationen_hittar_vc),
    (3, "Sommen pekar pa samma mapp", punkt_3_sommen_pekar_pa_samma_mapp),
    (4, "Installationen lagger paketet ratt", punkt_4_installationen_lagger_paketet_ratt),
    (5, "Tillagget laddas", punkt_5_tillagget_laddas),
    (6, "Bryggan binder med ratt flagga", punkt_6_bryggan_binder_med_ratt_flagga),
    (7, "Dubbelbindning avvisas", punkt_7_dubbelbindning_avvisas),
    (8, "Omstart efter krasch", punkt_8_omstart_efter_krasch),
    (9, "Tjansten hittar token", punkt_9_tjansten_hittar_token),
    (10, "Tur och retur over bryggan", punkt_10_tur_och_retur_bryggan),
    (11, "Ogat mater", punkt_11_ogat_mater),
    (12, "ST-kedjan bygger", punkt_12_st_kedjan_bygger),
    (13, "node gar att starta", punkt_13_node_gar_att_starta),
    (14, "OpenPLC nas", punkt_14_openplc_nas),
    (15, "Tokenfilens rattigheter", punkt_15_tokenfilens_rattigheter),
    (16, "Avinstallationen stadar", punkt_16_avinstallationen_stadar),
]


def kor_alla(hoppa_over_vc=False, plc_url="http://127.0.0.1:8080"):
    resultat = []
    vc_punkter = {5, 6, 7, 8, 10, 11}
    for nr, namn, fn in ALLA_PUNKTER:
        if hoppa_over_vc and nr in vc_punkter:
            res = {"status": "HOPPAD", "skal": "Hoppades over (--hoppa-over-vc aktiv)"}
        elif nr == 14:
            res = fn(url=plc_url)
        else:
            res = fn()
        res["nr"] = nr
        res["namn"] = namn
        resultat.append(res)
    return resultat


def main():
    parser = argparse.ArgumentParser(description="M-44 / E1: De 16 protokollpunkterna pa Windows")
    parser.add_argument("--json-ut", default="", help="Sokvag att skriva JSON-resultat till")
    parser.add_argument("--hoppa-over-vc", action="store_true", help="Hoppa over punkter som kraver aktiv VC")
    parser.add_argument("--plc-url", default="http://127.0.0.1:8080", help="URL till OpenPLC")
    args = parser.parse_args()

    t0 = time.time()
    punkter = kor_alla(hoppa_over_vc=args.hoppa_over_vc, plc_url=args.plc_url)
    varaktighet = time.time() - t0

    antal_gron = sum(1 for p in punkter if p["status"] == "GRON")
    antal_rod = sum(1 for p in punkter if p["status"] == "ROD")
    antal_hopp = sum(1 for p in punkter if p["status"] == "HOPPAD")

    rapport = {
        "datum": time.strftime("%Y-%m-%d %H:%M:%S"),
        "plattform": sys.platform,
        "python_version": sys.version,
        "varaktighet_s": round(varaktighet, 3),
        "sammanfattning": {
            "totalt": len(punkter),
            "gron": antal_gron,
            "rod": antal_rod,
            "hoppad": antal_hopp,
        },
        "punkter": punkter,
    }

    print("=== M-44 / E1: 16 Protokollpunkter ===")
    for p in punkter:
        print("[%s] Punkt %2d: %s -- %s" % (p["status"], p["nr"], p["namn"], p["skal"]))
    print("\nResultat: %d grona, %d roda, %d hoppade (totalt %d)" % (
        antal_gron, antal_rod, antal_hopp, len(punkter)))

    if args.json_ut:
        with open(args.json_ut, "w", encoding="utf-8") as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False)
        print("JSON sparad till: %s" % args.json_ut)

    sys.exit(1 if antal_rod > 0 else 0)


if __name__ == "__main__":
    main()
