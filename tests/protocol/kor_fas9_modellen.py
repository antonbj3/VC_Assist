# -*- coding: utf-8 -*-
"""Fas 9: en spraakmodells ST mot samma bank, samma skelett och samma domare.

Fas 11 (M-62) mätte baslinjen. Den här körningen mäter den andra sidan av
paret, och paret är hela poängen: `docs/spec/70_faser.md` säger att fas 9:s tal
**aldrig får publiceras ensamt**.

## Vad "modellen" är här, och det ska stå i varje rapport

Det finns **ingen API-nyckel och ingen byggd modellklient** i det här repot.
Modellen är därför en Claude-agent som fått **exakt** det slingan ger: uppgiftens
text, dess signaler, sekvens, förreglingar och tider, plus skelettet. Den fick
uttryckligt förbud mot att öppna repot, där facit och referenslösningar ligger.

Det är en verklig modell och en verklig mätning, men den är **inte automatiserad
och inte upprepad**. Ett tal härifrån är ett stickprov med n = 1 per uppgift.

## Vad som mäts

Samma domare som baslinjen, med samma signatur — `bank/par.py` avvisar ett par
vars sidor dömts olika. Tre tal, som kontraktet kräver:

  forsta forsoket   loste den utan reparation?
  efter k varv      inte mätt här: slingan kräver en modell som kan svara
                    automatiskt, och det finns inte
  fel per klass     ur domarens koder

Kors:
    python3 tests/protocol/kor_fas9_modellen.py --svar <katalog> [--json ut.json]
"""
from __future__ import annotations

import argparse
import collections
import difflib
import json
import os
import re
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

sys.path.insert(0, os.path.join(_ROT, "bank"))

import par as Par                                                # noqa: E402
from bank import baslinjebank as BB                              # noqa: E402
from bank import domare, lasare, reparationsbank as RB          # noqa: E402
from vc_assist_svc.plc import stationsgrind as SG               # noqa: E402
from vc_assist_svc.plc.skelett import Skelett, Skelettfel       # noqa: E402


def _las(katalog, namn):
    p = os.path.join(katalog, namn)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


# Ord som hor till spraket och inte till nagons val. Ett gemensamt `IF` sager
# ingenting; ett gemensamt `tmrIndex` sager allt.
_SPRAKORD = frozenset("""
IF THEN ELSE ELSIF END_IF CASE OF END_CASE AND OR NOT TRUE FALSE VAR END_VAR
PROGRAM END_PROGRAM TON TOF TP R_TRIG F_TRIG SR RS CTU CTD CTUD IN PT Q Q1 QU QD
ET CLK S S1 R R1 LD CV PV BOOL INT DINT SINT REAL LREAL TIME WORD BYTE T RETURN
XOR MOD AT EXIT WHILE DO END_WHILE FOR TO BY END_FOR REPEAT UNTIL END_REPEAT
""".split())

_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_KOMMENTAR = re.compile(r"\(\*.*?\*\)", re.S)


def kontaminering(post, kropp, arbetsvariabler):
    """Hur likt ar modellens svar referensen den aldrig fick se?

    Matningens giltighet star och faller med att modellen inte sag facit. Ett
    forbud i en prompt ar en bon; det har ar matningen.

    Tre matt, och det tredje ar det starkaste: VARIABELNAMN ar ett fritt val.
    Tva losningar som delar `tmrIndex` har inte kommit pa det var for sig. Tva
    som delar `IF` har ingenting gemensamt alls.

    Kommentarer raknas bort - de ar prosa pa samma sprak och skulle dranka
    matningen i ord som "att" och "bara".
    """
    ref = _KOMMENTAR.sub(" ", post["facit_spar"]["referens"])
    mod = _KOMMENTAR.sub(" ", (arbetsvariabler or "") + (kropp or ""))
    signaler = set(s["name"].upper() for s in post["control"]["signals"])

    def egna(text):
        return set(x.upper() for x in _IDENT.findall(text)) - signaler - _SPRAKORD

    a = re.sub(r"\s+", " ", ref)
    b = re.sub(r"\s+", " ", mod)
    m = difflib.SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b))
    return {
        "likhet": round(difflib.SequenceMatcher(None, ref, mod).ratio(), 4),
        "langsta_gemensamma": m.size,
        "langsta_text": a[m.a:m.a + m.size],
        "delade_namn": sorted(egna(ref) & egna(mod)),
    }


def _apiindex():
    """API-indexet for grind 4. Byggs en gang.

    Utan det svarar grinden "API-indexet saknas" - korrekt fail-closed, men fel
    besked: det ratta ar att kandidaten inte bar nagon scenkod att validera.
    Tva olika skal ska inte se likadana ut.
    """
    try:
        from vc_assist_svc.api_index import bygg_validator
        return bygg_validator()
    except Exception:
        return None


def kor_en(post, katalog, strucpp_cli=None, byggkatalog=None, index=None):
    """Bygg, granska och döm ett svar. Varje steg kan falla, och sägar varför."""
    tid = post.get("task_id")
    station = (tid or "P").replace("-", "_")
    ut = {"task_id": tid}

    kropp = _las(katalog, "%s_kropp.st" % tid)
    arb = _las(katalog, "%s_arbetsvariabler.st" % tid) or ""
    if kropp is None:
        ut["utfall"] = "inget svar"
        return ut

    karta = RB.karta_ur_uppgift(post, station)
    sk = Skelett.av_karta(karta, arbetsvariabler=True)

    # Arbetsvariablerna granskas FORE isattningen. En variabel med adress eller
    # med en signals namn ar inte en arbetsvariabel, och den ska avvisas dar och
    # inte upptackas som ett logikfel tre grindar senare.
    try:
        if arb.strip():
            sk.granska_arbetsvariabler(arb, karta)
        st_kalla = sk.satt_in(kropp, arb)
    except Skelettfel as fel:
        ut["utfall"] = "skelettet avvisade svaret"
        ut["skal"] = str(fel)
        return ut

    ut["kontaminering"] = kontaminering(post, kropp, arb)
    ut["arbetsvariabler"] = [r.strip() for r in arb.splitlines() if r.strip()]
    ut["kroppsrader"] = len([r for r in kropp.splitlines() if r.strip()])

    dom_sg = SG.granska_station(
        SG.Kandidat(station, st_kalla, None), karta, index=index,
        strucpp_cli=strucpp_cli, byggkatalog=byggkatalog,
        stanna_vid_forsta=False)
    ut["forgrindar"] = dict((g, (True if v is True else str(v)))
                            for g, v in dom_sg.forgrindar.items())

    d = domare.dom(post, st_kalla)
    ut["godkand"] = bool(d.godkand)
    ut["brister"] = [{"kod": b.kod, "text": b.text} for b in d.brister]
    ut["koder"] = list(d.koder)
    ut["scan"] = d.scan_kord
    ut["utfall"] = "godkand" if d.godkand else "underkand"
    return ut


def skriv_aterkoppling(resultat, post, katalog):
    """Grindens och domarens EGNA ord tillbaka till modellen, ordagrant.

    Ingen omskrivning, ingen sammanfattning, ingen tolkning. Doktrinen star i
    `50_grindar.md` och ar motiverad av en matt incident: en omimplementerad
    positionsdom underkande 2 av 4 medan ogat visade 4 av 4. En grind som
    tolkar om observatorens svar mater till slut sig sjalv.

    Detsamma galler vagen ut. En atermatning som ar omformulerad ar inte
    grindens dom - den ar var asikt om den.
    """
    tid = resultat["task_id"]
    rader = ["# Grindernas dom over din losning for %s" % tid, ""]
    if resultat.get("utfall") == "godkand":
        rader.append("**GODKAND.** Ingen andring behovs.")
    else:
        rader.append("**UNDERKAND.** Nedan star grindarnas egna ord, ordagrant.")
    rader.append("")

    rader.append("## Forgrindarna")
    rader.append("")
    for namn in ("statisk_analys", "deklarationsmatchning", "anropsvalidering",
                 "kompilering"):
        v = (resultat.get("forgrindar") or {}).get(namn)
        if v is True:
            rader.append("* `%s` — GODKAND" % namn)
        elif v is None:
            rader.append("* `%s` — ej kord" % namn)
        else:
            rader.append("* `%s` — **%s**" % (namn, v))
    rader.append("")

    egna = resultat.get("grindens_egna_ord") or {}
    for namn, text in sorted(egna.items()):
        if not text or not text.strip():
            continue
        rader.append("### %s, ordagrant" % namn)
        rader.append("")
        rader.append("```")
        rader.append(text.rstrip())
        rader.append("```")
        rader.append("")

    brister = resultat.get("brister") or []
    if brister:
        rader.append("## Facit: vad koden gjorde mot vad den skulle gora")
        rader.append("")
        rader.append("Facit ar ett SPAR: insignaler satts vid en tidpunkt och "
                     "utsignalerna lases. Varje rad nedan ar en avlasning som "
                     "inte stamde.")
        rader.append("")
        for b in brister:
            rader.append("* `%s`" % b["kod"])
            for r in str(b.get("text") or "").splitlines():
                if r.strip():
                    rader.append("  %s" % r.strip())
        rader.append("")
        rader.append("En rad som borjar med `invariant:` ar ett villkor som "
                     "ska galla HELA tiden, inte bara vid en tidpunkt.")
        rader.append("")

    rader.append("## Vad du ska gora")
    rader.append("")
    rader.append("Skriv om `%s_kropp.st` och vid behov `%s_arbetsvariabler.st`."
                 % (tid, tid))
    rader.append("Andra ingenting annat. Du far fortfarande inte oppna repot.")

    sokvag = os.path.join(katalog, "%s_grinddom.md" % tid)
    with open(sokvag, "w", encoding="utf-8") as f:
        f.write("\n".join(rader) + "\n")
    return sokvag


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--svar", required=True, help="katalogen med modellens svar")
    p.add_argument("--strucpp-cli", help="STruC++ CLI for grind 1")
    p.add_argument("--byggkatalog")
    p.add_argument("--json")
    p.add_argument("--varv", type=int, default=1,
                   help="vilket reparationsvarv svaren kommer fran")
    p.add_argument("--aterkoppling", action="store_true",
                   help="skriv grindernas egna ord till <svar>/<ID>_grinddom.md")
    a = p.parse_args(argv)

    poster = [u.data for u in lasare.ladda() if u.data.get("facit_spar")]
    index = _apiindex()
    resultat = [kor_en(post, a.svar, a.strucpp_cli, a.byggkatalog, index)
                for post in poster]

    print("=== FAS 9: en modells ST mot bankens spårfacit ===\n")
    print("  MODELLEN ar en Claude-agent, inte ett API-anrop. Ingen nyckel och")
    print("  ingen modellklient finns i repot. Stickprov n = 1 per uppgift.\n")
    godkanda = 0
    klasser = collections.Counter()
    for r in resultat:
        if r.get("godkand"):
            godkanda += 1
        print("  %-6s %-12s %s" % (r["task_id"], r["utfall"],
                                   "" if r.get("godkand") else
                                   ", ".join(sorted(set(r.get("koder") or []))) or
                                   r.get("skal", "")[:70]))
        for g, v in sorted((r.get("forgrindar") or {}).items()):
            if v is not True:
                print("           grind %-22s %s" % (g, str(v)[:60]))
        klasser.update(r.get("koder") or [])

    if a.varv <= 1:
        print("\n  FORSTA FORSOKET: %d av %d" % (godkanda, len(resultat)))
    else:
        print("\n  EFTER %d REPARATIONSVARV: %d av %d"
              % (a.varv - 1, godkanda, len(resultat)))

    # Paret, och det ar hela poangen: specen sager att fas 9:s tal aldrig far
    # publiceras ensamt. Par.para KASTAR om sidorna domts av olika domare - en
    # jamforelse mellan tva domare mater domaren, inte de tva sidorna.
    grindar = ("spar",)
    modellsidan = Par.Sida(
        "modell (Claude-agent, n=1)",
        Par.signatur(poster, grindar),
        dict((r["task_id"], bool(r.get("godkand"))) for r in resultat),
        dict(klasser))
    try:
        bas = BB.kor_niva(poster, "spec")
        baslinjesidan = BB._sida("baslinjen (M-62, niva spec)", bas, poster,
                                 grindar)
        rapport = Par.para(baslinjesidan, modellsidan)
        print("\n  PARET (samma domare, kontrollerad signatur %s):"
              % baslinjesidan.signatur.kort())
        print("    %-32s %d av %d" % (baslinjesidan.namn,
                                      baslinjesidan.klarade, baslinjesidan.antal))
        print("    %-32s %d av %d" % (modellsidan.namn,
                                      modellsidan.klarade, modellsidan.antal))
        if modellsidan.klarade == baslinjesidan.klarade:
            print("    => OAVGJORT mot en mallkompilator. Det ska sagas med "
                  "de orden.")
        elif modellsidan.klarade < baslinjesidan.klarade:
            print("    => Baslinjen ar BATTRE. En regelmotor slog modellen.")
        else:
            print("    => Modellen ar battre pa %d uppgifter."
                  % (modellsidan.klarade - baslinjesidan.klarade))
    except Par.Parfel as fel:
        print("\n  PARET GAR INTE ATT BILDA:\n    %s" % fel)
    except Exception as fel:
        print("\n  baslinjesidan gick inte att kora: %s: %s"
              % (type(fel).__name__, fel))
    print("\n  KONTAMINERING - liknar svaret referensen modellen aldrig sag?")
    print("    %-6s %8s %9s  %s" % ("", "likhet", "langsta", "delade egna namn"))
    varning = 0
    for r in resultat:
        k = r.get("kontaminering")
        if not k:
            continue
        print("    %-6s %7.1f%% %9d  %s"
              % (r["task_id"], 100 * k["likhet"], k["langsta_gemensamma"],
                 ", ".join(k["delade_namn"]) or "INGA"))
        if k["delade_namn"] or k["likhet"] > 0.35:
            varning += 1
    if varning:
        print("    VARNING: %d svar liknar referensen. Talen ovan ar inte att "
              "lita pa." % varning)
    else:
        print("    Noll delade variabelnamn. Variabelnamn ar ett fritt val, och")
        print("    tva losningar som inte delar ett enda har inte kopierat.")

    print("\n  fel per klass:")
    for kod, n in klasser.most_common():
        print("    %-24s %d" % (kod, n))
    if a.varv <= 1:
        print("\n  Efter k varv: kor om med --varv 2 nar modellen svarat pa")
        print("  aterkopplingen. Slingan drivs for hand: bryggan mellan grind")
        print("  och modell ar ett meddelande, inte ett API-anrop.")

    if a.aterkoppling:
        print("\n  aterkoppling skriven:")
        for post, r in zip(poster, resultat):
            print("    %s" % skriv_aterkoppling(r, post, a.svar))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"resultat": resultat, "godkanda": godkanda,
                       "av": len(resultat)}, f, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
