# -*- coding: utf-8 -*-
"""Hela banken i en korning: varje post som gar att kora HAR, och skalet till
varje hopp.

`docs/spec/85_bankkontraktet.md`. Registret ar korningarnas EGNA deklarationer
(`BANKPOST`), lasta med AST och aldrig genom import - flera korningar satter
sys.path eller startar processer redan pa modulniva.

TRE TAL, OCH DET ANDRA AR LIKA VIKTIGT SOM DET FORSTA

    korda        posten kordes har, med sin returkod
    hoppade      posten kordes INTE, och raden sager VAD som saknades
    odeklarerade en kor_*.py utan BANKPOST - en matning ingen vet om

Ett hopp ar aldrig ett godkannande. Summan "18 av 30 korda har, 8 kraver VC,
4 saknar sina argument" ar sann; "30 av 30" hade varit en losgning.

Vad som finns HAR upptacks, det antas inte:

    vc        tokenfilen finns OCH nagot lyssnar pa bryggans port (en ren
              TCP-anslutning som stangs direkt - korningen startar aldrig VC)
    openplc   nagot lyssnar pa OPC UA-endpointens port
    strucpp   --strucpp-cli pekar pa en korbar fil
    modell    `claude` finns i PATH (vc_assist_svc.modellklient)
    windows   sys.platform ar win32

    python3 tests/protocol/kor_allt.py --torrt
    python3 tests/protocol/kor_allt.py --strucpp-cli <sokvag> --svar <katalog>
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Den aggregerade korningen kor varje bankpost vars krav ar uppfyllda "
        "har och hoppar over resten med skalet utskrivet, sa att ett hopp "
        "aldrig kan lasas som ett godkannande.",
    "under_prov": ("svc/vc_assist_svc/bankkontrakt.py",),
    "facit":
        "registrets egna poster: varje kor_*.py under tests/protocol ska ha "
        "en post, varje post ska peka pa filer som finns, och korda plus "
        "hoppade ska vara lika med antalet poster",
    "facitkalla":
        "bankkontraktet i docs/spec/85_bankkontraktet.md, skrivet fore "
        "registret, plus korningarnas egna deklarationer lasta med AST ur "
        "filerna sjalva",
    "facitkalla_filer": ("docs/spec/85_bankkontraktet.md",),
    "trasiga_fall": (
        "en korning utan BANKPOST maste synas som odeklarerad, aldrig raknas "
        "som kord",
        "en post vars krav inte ar uppfyllda maste skrivas ut med VAD som "
        "saknades",
        "en hoppad post far aldrig raknas in bland de grona",
        "en post vars under_prov eller facitkalla_filer pekar pa en fil som "
        "inte finns maste fallas",
    ),
    "kraver": ("inget",),
    "matningar": ("M-104",),
}

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
_PROTOKOLL = os.path.join(_ROT, "tests", "protocol")
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import bankkontrakt as BK                      # noqa: E402

# Argument en korning MASTE ha for att mata det den pastar. Saknas de hoppas
# posten over med det som skal - att kora den utan dem hade gett ett rott
# utfall som handlar om anropet och inte om formagan.
ARGUMENTKRAV = {
    "kor_fas7_grindar.py": ("--strucpp-cli",),
    "kor_fas7_station.py": ("--strucpp", "--runtime-include"),
    "kor_fas8_linan.py": ("--strucpp", "--runtime-include"),
    "kor_fas9_modellen.py": ("--svar",),
    "kor_m54_tolk_mot_strucpp.py": ("--strucpp-cli",),
    "kor_m62_baslinjen_mot_strucpp.py": ("--strucpp-cli",),
    "kor_m82_scenkod.py": ("--svar",),
    "kor_fas18_anlaggning.py": (),
}


def _lyssnar(port, vard="127.0.0.1", tidsgrans=0.4):
    """Sant om nagon lyssnar. Anslutningen stangs direkt - ingen trafik."""
    try:
        s = socket.create_connection((vard, port), timeout=tidsgrans)
    except (OSError, socket.timeout):
        return False
    s.close()
    return True


def tillgangligt(a):
    """Vad som gar att kora HAR, upptackt och inte antaget.

    Varje rad bar sitt skal, ocksa nar svaret ar ja: den som laser rapporten
    ska kunna se VARFOR en post hoppades over utan att kora om nagot.
    """
    ut = {}
    try:
        from vc_assist_svc.tokenplats import tokenfil
        token = tokenfil()
    except Exception as fel:                                  # noqa: BLE001
        token, skal = None, "tokenfilen gick inte att sla upp: %s" % fel
    else:
        skal = "tokenfil %s" % token
    har_token = bool(token and os.path.exists(token))
    lyssnar = _lyssnar(a.port)
    ut["vc"] = (har_token and lyssnar,
                "%s, port %d %s" % (skal if har_token else "ingen tokenfil",
                                    a.port,
                                    "lyssnar" if lyssnar else "svarar inte"))
    ut["openplc"] = (_lyssnar(a.openplc_port),
                     "OPC UA-port %d %s" % (a.openplc_port,
                                            "lyssnar" if _lyssnar(a.openplc_port)
                                            else "svarar inte"))
    cli = a.strucpp_cli
    ut["strucpp"] = (bool(cli and os.path.exists(cli) and os.access(cli, os.X_OK)),
                     "--strucpp-cli %s" % (cli or "inte angiven"))
    klient = shutil.which("claude")
    ut["modell"] = (bool(klient), "claude i PATH: %s" % (klient or "nej"))
    ut["windows"] = (sys.platform == "win32", "sys.platform=%s" % sys.platform)
    return ut


def _argument(namn, a):
    """(argv-svans, saknade flaggor) for en korning."""
    kravda = ARGUMENTKRAV.get(namn, ())
    varden = {"--strucpp-cli": a.strucpp_cli, "--strucpp": a.strucpp,
              "--runtime-include": a.runtime_include, "--svar": a.svar}
    svans, saknade = [], []
    for flagga in kravda:
        v = varden.get(flagga)
        if v:
            svans += [flagga, v]
        else:
            saknade.append(flagga)
    return svans, saknade


def _saknade_filer(post):
    """Filer posten pekar ut som inte finns. En post utan tackning."""
    return [f for f in tuple(post.under_prov) + tuple(post.facitkalla_filer)
            if not os.path.exists(os.path.join(_ROT, f))]


def kor_en(post, a):
    """Kor EN korning som underprocess och lamna dess rad."""
    sokvag = os.path.join(_PROTOKOLL, post.korning)
    svans, _saknade = _argument(post.korning, a)
    kommando = [sys.executable, sokvag] + svans
    t0 = time.time()
    try:
        k = subprocess.run(kommando, cwd=_ROT, timeout=a.tidsgrans,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        kod, utdata = k.returncode, k.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        kod, utdata = None, "TIDSGRANS efter %.0f s" % a.tidsgrans
    return {"korning": post.korning, "returkod": kod,
            "sekunder": round(time.time() - t0, 1),
            "sista_raden": [r for r in utdata.strip().splitlines() if r.strip()][-1:],
            "kommando": " ".join(kommando[1:])}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--torrt", action="store_true",
                   help="lista vad som skulle koras, kor ingenting")
    p.add_argument("--bara", help="komma-lista over korningar")
    p.add_argument("--port", type=int, default=8901, help="bryggans port")
    p.add_argument("--openplc-port", type=int, default=14840)
    p.add_argument("--strucpp-cli", help="STruC++:s korbara CLI")
    p.add_argument("--strucpp", help="STruC++:s npm-katalog")
    p.add_argument("--runtime-include", help="OpenPLC:s include-katalog")
    p.add_argument("--svar", help="katalog med modellsvar")
    p.add_argument("--tidsgrans", type=float, default=3600.0)
    p.add_argument("--json")
    a = p.parse_args(argv)

    dom = BK.granska_registret(_PROTOKOLL)

    print("=== BANKEN: %d poster, %d odeklarerade korningar ==="
          % (len(dom.poster), len(dom.odeklarerade)))
    for f in dom.odeklarerade:
        print("  ODEKLARERAD  %s - ingen BANKPOST; en matning ingen vet om" % f)
    if dom.brister:
        print("\n  BRISTER I REGISTRET (en ogiltig post ar ingen gron):")
        for b in dom.brister:
            print("    %s" % b)

    print("\n  vad som finns har:")
    finns = tillgangligt(a)
    for namn in sorted(finns):
        ja, skal = finns[namn]
        print("    %-9s %-3s %s" % (namn, "JA" if ja else "nej", skal))

    har, hoppas = BK.korbara(dom.poster, [k for k, (ja, _s) in finns.items() if ja])
    valda = set(x for x in (a.bara or "").split(",") if x.strip())

    rader, hoppade = [], []
    for post, saknas in hoppas:
        hoppade.append({"korning": post.korning, "skal": "kraver " + saknas})
    for post in har:
        if post.korning == os.path.basename(__file__):
            # Den aggregerade korningen kor inte sig sjalv. Posten star kvar i
            # registret - den ar ett pastaende som gar att falla - men en
            # rekursion hade matt sig sjalv och ingenting annat.
            hoppade.append({"korning": post.korning,
                            "skal": "den aggregerade korningen kor inte sig "
                                    "sjalv (rekursion)"})
            continue
        if valda and post.korning not in valda:
            hoppade.append({"korning": post.korning, "skal": "inte vald med --bara"})
            continue
        saknade_filer = _saknade_filer(post)
        if saknade_filer:
            hoppade.append({"korning": post.korning,
                            "skal": "posten pekar pa filer som inte finns: %s"
                                    % ", ".join(saknade_filer)})
            continue
        _svans, saknade = _argument(post.korning, a)
        if saknade:
            hoppade.append({"korning": post.korning,
                            "skal": "saknar argument: " + ", ".join(saknade)})
            continue
        if a.torrt:
            hoppade.append({"korning": post.korning, "skal": "--torrt"})
            continue
        print("\n  kor %s ..." % post.korning, flush=True)
        rad = kor_en(post, a)
        rader.append(rad)
        print("    returkod %s efter %.0f s   %s"
              % (rad["returkod"], rad["sekunder"],
                 (rad["sista_raden"] or [""])[0][:90]))

    print("\n=== SUMMA ===")
    grona = [r for r in rader if r["returkod"] == 0]
    print("  korda har:      %d, varav %d med returkod 0"
          % (len(rader), len(grona)))
    print("  hoppade over:   %d - och ett hopp ar aldrig ett godkannande"
          % len(hoppade))
    for h in sorted(hoppade, key=lambda x: x["korning"]):
        print("    %-42s %s" % (h["korning"], h["skal"]))
    print("  odeklarerade:   %d" % len(dom.odeklarerade))
    if len(rader) + len(hoppade) != len(dom.poster):
        print("  RAKNINGEN GAR INTE IHOP: %d + %d != %d poster"
              % (len(rader), len(hoppade), len(dom.poster)))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"poster": len(dom.poster),
                       "odeklarerade": dom.odeklarerade,
                       "brister": dom.brister, "korda": rader,
                       "hoppade": hoppade}, f, indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)

    # Returkoden bar tva ting och bara tva: ett rott utfall bland de korda,
    # och ett register som inte haller. Ett hopp far aldrig fara returkoden.
    if dom.brister or dom.odeklarerade:
        return 2
    return 1 if len(grona) != len(rader) else 0


if __name__ == "__main__":
    sys.exit(main())
