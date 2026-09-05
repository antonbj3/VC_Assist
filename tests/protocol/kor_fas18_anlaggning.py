# -*- coding: utf-8 -*-
"""Fas 18: en befintlig anlaggning in. Ett inspelat I/O-spar blir ett facit.

Operatorens fraga bakom fasen, ordagrant:

    "finns nagon mojlighet att ga omvanda riktningen -> maskinkod till
    structured text, i vart simuleringsscenario, for tror det ar ganska vanligt
    att originalkod och sant tappas bort"
    "Man lyssnar val pa kablarna typ, och lagger ihop signalerna?"

Den har korningen matter vad den vagen faktiskt racker till, och den kan gora
det darfor att vi har ett fall dar SVARET AR KANT: bankens fyra sparfacit har
bade en referenslosning och ett handskrivet facit med motbevis. Vi kan alltsa
kora det kanda programmet, spela in sparet, kasta bort kallkoden, harleda ett
facit ur inspelningen ensam - och sedan fraga hur mycket av det kanda facit som
harledningen aterfann.

TVA INSPELNINGAR, OCH SKILLNADEN AR HELA MATNINGEN
--------------------------------------------------
  PROVSPARET       alla bankens sekvenser. Nagon har ANSTRANGT sig for att
                   provoka kallstart, larm, kvittens, tidsvakt och aterstart.
                   Det ar basta mojliga fall och finns inte pa en riktig linje.
  PRODUKTIONSSPARET  ett fonster ur normaldriften, upprepat. Det ar vad en
                   anlaggning faktiskt ger: tusentals rader ur samma gren.

Vilket fonster som ar normalproduktion ar en MANNISKAS val och star i
PRODUKTIONSFONSTER nedan, med skalet. Modulen gissar det inte at nagon.

Kors:
    python3 tests/protocol/kor_fas18_anlaggning.py [--json ut.json]
    python3 tests/protocol/kor_fas18_anlaggning.py --brief <katalog>
    python3 tests/protocol/kor_fas18_anlaggning.py --svar <katalog>
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bank import anlaggning as An                               # noqa: E402
from bank import domare, lasare, reparationsbank as RB          # noqa: E402
from vc_assist_svc.plc import stationsgrind as SG               # noqa: E402
from vc_assist_svc.plc.skelett import Skelett, Skelettfel       # noqa: E402


def _fas9():
    """Fas 9:s korning, laddad som modul. Samma kontamineringsmatt, samma
    API-index. En andra implementation av samma matt mater implementationen."""
    sokvag = os.path.join(_ROT, "tests", "protocol", "kor_fas9_modellen.py")
    spec = importlib.util.spec_from_file_location("kor_fas9_modellen", sokvag)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Vilket avsnitt ur inspelningen som ar normalproduktion. Det ar ett
# MANNISKOVAL, och det ar precis vad en anlaggning ger: du far den timme nagon
# rakade spela in. Valet star har med sitt skal, i klartext, i stallet for i en
# regel som latsas harleda det ur datan.
#
#   T-07  en detalj klamms, indexeras och slapps            - stationens takt
#   H-04  en konsol lamnas over hela vagen                  - linjens takt
#   S-05  STOPPED-RESET-IDLE-START-EXECUTE-COMPLETE-STOPPED - PackML-varvet
#   L-05  ett kolli plockas och lyftbordet sanks en lagerhojd - palleteringens takt
PRODUKTIONSFONSTER = {
    "T-07": "en_detalj_hela_vagen",
    "H-04": "hel_overlamning",
    "S-05": "hel_produktionscykel",
    "L-05": "ett_lager_i_automatlage",
}

# Hur manga ganger produktionsfonstret upprepas. Talet ar INGEN troskel: hela
# poangen med korningen ar att tackningen ar densamma for 1 som for 10, och
# bada raknas och rapporteras. En anlaggning som gatt ett dygn har korts
# tusentals varv och sett exakt lika manga lagen som efter det forsta.
UPPREPNINGAR = (1, 10)          # 70_faser.md, fas 18: "ett dygns spar".


# ------------------------------------------------------------- inspelningen

def _signalkarta(post):
    sig = dict((s["name"], str(s["type"]).lower())
               for s in post["control"]["signals"])
    rikt = dict((s["name"], s["dir"]) for s in post["control"]["signals"])
    return sig, rikt


def _stimuli(post, ider=None, upprepningar=1):
    """Det OMVARLDEN gjorde: bara insignalerna, aldrig facits krav.

    Bankens sekvenser bar bade `satt` (vad givarna gjorde) och `krav` (vad en
    manniska har bestamt ska gallla). En anlaggning ger bara det forsta. Kravet
    lamnas darfor kvar har - det ar precis den kunskap fasen provar om spåret
    kan ersatta.

    AVSNITTEN AVIDENTIFIERAS, och det ar inte kosmetik. Bankens sekvens heter
    `nodstopp_utan_automatisk_omstart` darfor att en manniska skrev vad den
    provar. En inspelning fran en linje heter "08:00-08:12". Lat namnet folja
    med och briefen bar plotsligt specen i sina rubriker - och matningen mater
    hur bra en modell laser rubriker.
    """
    ut = []
    karta = []
    for s in post["facit_spar"]["sekvenser"]:
        if ider is not None and s["id"] not in ider:
            continue
        for k in range(upprepningar):
            aid = "A%02d" % (len(ut) + 1)
            karta.append((aid, s["id"]))
            ut.append((aid, "inspelat avsnitt %d" % (len(ut) + 1),
                       [(st["t_ms"], st.get("satt") or {}) for st in s["steg"]]))
    return ut, karta


def spela_in(post, ider=None, upprepningar=1, vad=""):
    sig, rikt = _signalkarta(post)
    fs = post["facit_spar"]
    stim, karta = _stimuli(post, ider, upprepningar)
    spar = An.spela_in(fs["referens"], sig, rikt, fs["scan_ms"], stim,
                       "%s, %s, inspelad genom svc/vc_assist_svc/st/tolk.py"
                       % (post["task_id"], vad))
    # Avsnittskartan foljer med korningen men ALDRIG briefen: en siffras
    # harkomst hor till siffran, och den som laser matningen ska kunna se
    # vilken bankssekvens varje inspelat avsnitt kom ur.
    spar.avsnittskarta = karta
    return spar


# --------------------------------------------------------------- matningarna

def mat_en(post):
    """Alla tal for en uppgift. Varje tal bar sin namnare."""
    tid = post["task_id"]
    fs = post["facit_spar"]
    prod_id = PRODUKTIONSFONSTER[tid]
    alla = set(s["id"] for s in fs["sekvenser"])

    prov = spela_in(post, alla, 1, "provsparet (alla bankens sekvenser)")
    h_prov = An.harled(prov)
    ut = {"task_id": tid, "produktionsfonster": prod_id,
          "provspar": {"rader": prov.antal_rader, "avsnitt": len(prov.avsnitt),
                       "avsnittskarta": prov.avsnittskarta},
          "produktion": {}}

    # 1. Ar det harledda facit uppfyllbart? Beviset ar inspelningen sjalv:
    #    programmet som spelades in maste ga igenom sitt eget spar.
    d_prov = domare.dom(post, fs["referens"], spar=h_prov.facit)
    ut["provspar"]["referensen_uppfyller"] = bool(d_prov.godkand)
    ut["provspar"]["invarianter"] = len(h_prov.facit["invarianter"])
    ut["provspar"]["flanker"] = len(h_prov.facit["flanker"])
    ut["provspar"]["ej_pastatt"] = len(h_prov.ej_pastatt)
    ut["provspar"]["tackningsbrister"] = [b.kod for b in
                                          An.granska(h_prov.facit, prov)]
    # KONTROLLEN, och utan den ar grinden trivial: samma handskrivna
    # invarianter mot PROVSPARET, dar lagen faktiskt besoktes. En grind som
    # vagrar allt ser lika bra ut som en som vagrar ratt sak.
    ut["provspar"]["otackta_handskrivna"] = sorted(set(
        b.pastaende for b in An.granska({"invarianter": fs["invarianter"]}, prov)
        if b.kod == An.T1_OTACKT_VILLKOR))

    # 2. Produktionssparet, en och tio upprepningar. Talet som ska jamforas ar
    #    inte radantalet utan TACKNINGEN.
    for n in UPPREPNINGAR:
        prod = spela_in(post, {prod_id}, n, "produktionssparet x%d" % n)
        t = An.Tackning(prod)
        h = An.harled(prod)
        # Bankens EGNA handskrivna invarianter, provade mot produktionssparet.
        # Det ar fasens huvudfraga: bar den har inspelningen upp de pastaenden
        # nagon redan vet ar sanna?
        brister = An.granska({"invarianter": fs["invarianter"]}, prod)
        otackta = sorted(set(b.pastaende for b in brister
                             if b.kod == An.T1_OTACKT_VILLKOR))
        d_prod = domare.dom(post, fs["referens"], spar=h.facit)
        post_n = {
            "rader": prod.antal_rader,
            "avsnitt": len(prod.avsnitt),
            "tysta_signaler": t.tysta(),
            "handskrivna_invarianter": len(fs["invarianter"]),
            "otackta_handskrivna": otackta,
            "harledda_invarianter": len(h.facit["invarianter"]),
            "ej_pastatt": len(h.ej_pastatt),
            "referensen_uppfyller": bool(d_prod.godkand),
            "tackningsbrister": [b.kod for b in An.granska(h.facit, prod)],
            "motbevisade_av_provsparet":
                [inv["namn"] for inv, _ in An.motbevisade(h.facit, prov)],
            "emg_ok_falskt": t.observerad("EMG_OK", False),
        }
        post_n["motbevis_fallda"] = _motbevis(post, h.facit)
        ut["produktion"]["x%d" % n] = post_n

    # 3. Diskriminerande kraft: samma motbevis, tre facit.
    ut["motbevis"] = {
        "antal": len(fs["motbevis"]),
        "handskrivet": _motbevis(post, None),
        "harlett_ur_provsparet": _motbevis(post, h_prov.facit),
        "harlett_ur_produktionssparet":
            ut["produktion"]["x%d" % UPPREPNINGAR[-1]]["motbevis_fallda"],
    }
    return ut, h_prov


def _motbevis(post, facit):
    """Hur manga av uppgiftens motbevis facit faller. `None` = det handskrivna.

    Ett motbevis ar en losning som SER riktig ut men bryter mot ett krav.
    Talet ar darfor ett matt pa facits diskriminerande kraft, och det har ett
    kant tak: det handskrivna facit faller alla (tests/enhet/test_domare.py).
    """
    n = 0
    for mb in post["facit_spar"]["motbevis"]:
        d = domare.dom(post, mb["st"], spar=facit)
        if not d.godkand:
            n += 1
    return n


# --------------------------------------------------------- modellens svar

def _las(katalog, namn):
    p = os.path.join(katalog, namn)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def kor_modellsvar(post, facit, katalog, fas9, index=None):
    """Samma mekanik som fas 9: skelett, forgrindar, domare, kontaminering.

    Den enda skillnaden ar vilket facit domaren far. Fas 9 domer mot bankens
    handskrivna sparfacit; har domer den mot ett facit HARLETT UR EN
    INSPELNING. Domaren, grindarna och kontamineringsmattet ar ordagrant
    desamma - en andra domare pa samma storhet mater domarna, inte losningarna.
    """
    tid = post["task_id"]
    station = tid.replace("-", "_")
    ut = {"task_id": tid}
    kropp = _las(katalog, "%s_kropp.st" % tid)
    arb = _las(katalog, "%s_arbetsvariabler.st" % tid) or ""
    if kropp is None:
        ut["utfall"] = "inget svar"
        return ut
    karta = RB.karta_ur_uppgift(post, station)
    sk = Skelett.av_karta(karta, arbetsvariabler=True)
    try:
        if arb.strip():
            sk.granska_arbetsvariabler(arb, karta)
        st_kalla = sk.satt_in(kropp, arb)
    except Skelettfel as fel:
        ut["utfall"] = "skelettet avvisade svaret"
        ut["skal"] = str(fel)
        return ut
    ut["kontaminering"] = fas9.kontaminering(post, kropp, arb)
    ut["kroppsrader"] = len([r for r in kropp.splitlines() if r.strip()])
    dom_sg = SG.granska_station(SG.Kandidat(station, st_kalla, None), karta,
                                index=index, stanna_vid_forsta=False)
    ut["forgrindar"] = dict((g, (True if v is True else str(v)))
                            for g, v in dom_sg.forgrindar.items())
    d = domare.dom(post, st_kalla, spar=facit)
    ut["godkand"] = bool(d.godkand)
    ut["koder"] = list(d.koder)
    ut["brister"] = [{"kod": b.kod, "text": b.text} for b in d.brister]
    ut["scan"] = d.scan_kord
    ut["utfall"] = "godkand" if d.godkand else "underkand"
    # Och samma losning mot bankens HANDSKRIVNA facit. Skillnaden mellan de tva
    # ar vad anlaggningens spar inte kunde beratta.
    dh = domare.dom(post, st_kalla)
    ut["mot_handskrivet_facit"] = {"godkand": bool(dh.godkand),
                                   "koder": list(dh.koder)}
    return ut


def _v(x):
    return "1" if x is True else ("0" if x is False else
                                  ("%g" % x if isinstance(x, float) else str(x)))


def brieftext(post, harlett, skelett):
    """Anlaggningsbriefen som en manniska skulle lasa den.

    En driftsattare som far ett inspelat spar far tva saker: I/O-listan med
    sina taggkommentarer, och tidsserien. Bada finns har. Det som INTE finns
    ar uppgiftstexten, referenslosningen, bankens handskrivna invarianter och
    sekvensnamnen - allt det ar en manniskas beskrivning av vad stationen SKA
    gora, och en anlaggning lamnar inte ifran sig den.
    """
    f = harlett.facit
    t = f["tackning"]
    ut = ["# Anlaggningsbrief %s" % post["task_id"], "",
          "Det har ar ALLT som finns. Originalkoden ar borta. Ingen",
          "specifikation, ingen kommentar i koden, ingen som minns.",
          "Det som ateratar ar en inspelning av kontaktdonen.", "",
          "## I/O-listan, med anlaggningens egna taggkommentarer", "",
          "```", skelett.rstrip(), "```", "",
          "## Vad inspelningen bestar av", "",
          "* scanperiod: %g ms" % f["scan_ms"],
          "* avlasningar: %d, i %d avsnitt" % (t["antal_rader"],
                                               t["antal_avsnitt"]),
          "* signaler som ALDRIG rorde sig: %s"
          % (", ".join(t["tysta"]) or "inga"), ""]
    for n in sorted(t["signaler"]):
        d = t["signaler"][n]
        ut.append("  %-20s varden %-18s byten %d"
                  % (n, ",".join(_v(json.loads(x)) for x in d["varden"]),
                     d["byten"]))
    ut.append("")
    ut.append("## Tidsserien, avsnitt for avsnitt")
    ut.append("")
    ut.append("`SATT` ar vad givarna gjorde. `AVLAST` ar vad utsignalerna stod")
    ut.append("pa vid den tidpunkten. Ingen rad ar en onskan - varje rad hande.")
    for sekv in f["sekvenser"]:
        ut.append("")
        ut.append("### %s" % sekv["id"])
        ut.append("")
        ut.append("```")
        ut.append("%8s  %-46s %s" % ("t_ms", "SATT", "AVLAST"))
        for st in sekv["steg"]:
            satt = " ".join("%s:=%s" % (k, _v(v))
                            for k, v in sorted((st["satt"] or {}).items()))
            krav = " ".join("%s=%s" % (k, _v(v))
                            for k, v in sorted((st["krav"] or {}).items()))
            ut.append("%8g  %-46s %s" % (st["t_ms"], satt, krav))
        ut.append("```")
    ut.append("")
    ut.append("## Flanker som raknades i inspelningen")
    ut.append("")
    ut.append("```")
    for fl in f["flanker"]:
        ut.append("%-14s %-18s %-5s %6g..%-6g  antal %d"
                  % (fl["sekvens"], fl["signal"], fl["typ"], fl["fran_ms"],
                     fl["till_ms"], fl["antal"]))
    ut.append("```")
    ut.append("")
    ut.append("## Tvasignalstillstand som ALDRIG forekom i inspelningen")
    ut.append("")
    ut.append("Varje rad ar ett forbud som spåret STODJER men inte BEVISAR.")
    ut.append("Att ett tillstand inte forekom kan bero pa en forregling eller")
    ut.append("pa en tillfallighet, och inspelningen kan inte skilja dem at.")
    ut.append("")
    ut.append("```")
    for inv in f["invarianter"]:
        ut.append("%-40s nar %-28s ska %-28s (villkoret sags %d ganger, %d episoder)"
                  % (inv["namn"],
                     ",".join("%s=%s" % (k, _v(v)) for k, v in inv["nar"].items()),
                     ",".join("%s=%s" % (k, _v(v)) for k, v in inv["kraver"].items()),
                     inv["underlag"]["villkor"]["n_rader"],
                     inv["underlag"]["villkor"]["n_episoder"]))
    ut.append("```")
    ut.append("")
    ut.append("## Vad inspelningen INTE kunde saga (%d pastaenden vagrade)"
              % len(harlett.ej_pastatt))
    ut.append("")
    ut.append("```")
    for e in harlett.ej_pastatt:
        ut.append("%-40s %s" % (e["pastaende"], e["skal"]))
    ut.append("```")
    return "\n".join(ut) + "\n"


def skriv_brief(post, harlett, katalog):
    """Det en modell far se: inspelningen och ingenting annat.

    Ingen uppgiftstext, ingen referenslosning, inga handskrivna invarianter.
    Det ar hela poangen - en anlaggning lamnar inte ifran sig sin specifikation,
    den lamnar sina kontaktdon.
    """
    tid = post["task_id"]
    fil = os.path.join(katalog, "%s_anlaggning.json" % tid)
    facit = dict(harlett.facit)
    with open(fil, "w", encoding="utf-8") as f:
        json.dump({"task_id": tid,
                   "signaler": post["control"]["signals"],
                   "facit_ur_sparet": facit,
                   "ej_pastatt": harlett.ej_pastatt}, f, indent=1,
                  ensure_ascii=False)
    karta = RB.karta_ur_uppgift(post, tid.replace("-", "_"))
    skelett = Skelett.av_karta(karta, arbetsvariabler=True).text()
    md = os.path.join(katalog, "%s_anlaggning.md" % tid)
    with open(md, "w", encoding="utf-8") as f:
        f.write(brieftext(post, harlett, skelett))
    with open(os.path.join(katalog, "%s_skelett.st" % tid), "w",
              encoding="utf-8") as f:
        f.write(skelett)
    return md


# ---------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    p.add_argument("--brief", help="skriv anlaggningsbriefen hit")
    p.add_argument("--svar", help="katalog med en modells ST att doma")
    p.add_argument("--varv", type=int, default=1,
                   help="vilket reparationsvarv svaren kommer fran")
    p.add_argument("--aterkoppling", action="store_true",
                   help="skriv grindarnas och facits EGNA ord till "
                        "<svar>/<ID>_grinddom.md")
    a = p.parse_args(argv)

    poster = [u.data for u in lasare.ladda()
              if u.data.get("facit_spar") and u.data["task_id"] in PRODUKTIONSFONSTER]
    fas9 = _fas9()
    index = fas9._apiindex() if a.svar else None

    print("=== FAS 18: en befintlig anlaggning in ===\n")
    print("  Ingen riktig anlaggning ar inspelad. Kallan ar bankens fyra")
    print("  referenslosningar, korda genom tolken och avlyssnade pa")
    print("  signalkartan - INRE TILLSTAND SPELAS ALDRIG IN. Det ar samma form")
    print("  en OPC UA-prenumeration eller en faltbussavlyssning ger, och")
    print("  skillnaden mot en riktig linje star i M-89.\n")

    alla = []
    briefer = []
    for post in poster:
        rad, h_prov = mat_en(post)
        alla.append(rad)
        if a.brief:
            briefer.append(skriv_brief(post, h_prov, a.brief))

    print("  1. INSPELNINGARNA")
    print("     %-6s %8s %8s   %-34s %8s" %
          ("", "provspar", "prod x1", "produktionsfonster", "prod x10"))
    for r in alla:
        print("     %-6s %8d %8d   %-34s %8d"
              % (r["task_id"], r["provspar"]["rader"],
                 r["produktion"]["x1"]["rader"], r["produktionsfonster"],
                 r["produktion"]["x10"]["rader"]))

    print("\n  2. TACKNING INNAN PASTAENDE")
    print("     Bankens EGNA handskrivna invarianter, provade mot")
    print("     produktionssparet. En rad per uppgift.\n")
    print("     %-6s %10s %10s   %s" % ("", "invarianter", "otackta",
                                        "som spåret aldrig visade"))
    tot_inv = tot_otackt = 0
    for r in alla:
        d = r["produktion"]["x10"]
        tot_inv += d["handskrivna_invarianter"]
        tot_otackt += len(d["otackta_handskrivna"])
        print("     %-6s %10d %10d   %s"
              % (r["task_id"], d["handskrivna_invarianter"],
                 len(d["otackta_handskrivna"]),
                 ", ".join(d["otackta_handskrivna"]) or "-"))
    print("     %-6s %10d %10d" % ("SUMMA", tot_inv, tot_otackt))
    kontroll = sum(len(r["provspar"]["otackta_handskrivna"]) for r in alla)
    print("\n     KONTROLLEN: samma %d invarianter mot PROVSPARET ger %d"
          % (tot_inv, kontroll))
    print("     otackta. Grinden vagrar alltsa inte allt - den vagrar det")
    print("     inspelningen inte bar.")

    emg = [r["task_id"] for r in alla
           if r["produktion"]["x10"]["emg_ok_falskt"] == 0]
    print("\n     EMG_OK gick ALDRIG till 0 i produktionssparet for: %s"
          % (", ".join(emg) or "ingen uppgift"))
    print("     Ett nodstopp som ingen tryckt pa sager ingenting om vad som")
    print("     hander nar nagon gor det. Fasens grind vagrar pastå det.")

    print("\n  3. MER DATA UR SAMMA GREN AR INTE MER TACKNING")
    print("     %-6s %9s %9s %9s %9s" % ("", "rader x1", "rader x10",
                                         "otackt x1", "otackt x10"))
    for r in alla:
        a1, a10 = r["produktion"]["x1"], r["produktion"]["x10"]
        print("     %-6s %9d %9d %9d %9d"
              % (r["task_id"], a1["rader"], a10["rader"],
                 len(a1["otackta_handskrivna"]), len(a10["otackta_handskrivna"])))

    print("\n  4. DISKRIMINERANDE KRAFT: samma motbevis, tre facit")
    print("     %-6s %6s %12s %12s %12s" % ("", "motbev", "handskrivet",
                                            "ur provspar", "ur produktion"))
    s = collections.Counter()
    for r in alla:
        m = r["motbevis"]
        s["antal"] += m["antal"]
        s["hand"] += m["handskrivet"]
        s["prov"] += m["harlett_ur_provsparet"]
        s["prod"] += m["harlett_ur_produktionssparet"]
        print("     %-6s %6d %12d %12d %12d"
              % (r["task_id"], m["antal"], m["handskrivet"],
                 m["harlett_ur_provsparet"], m["harlett_ur_produktionssparet"]))
    print("     %-6s %6d %12d %12d %12d"
          % ("SUMMA", s["antal"], s["hand"], s["prov"], s["prod"]))

    print("\n  5. KORRELATION AR INTE ORSAK, som ett tal")
    print("     Invarianter harledda ur PRODUKTIONSSPARET som PROVSPARET")
    print("     motbevisar. Varje sadan sag ut som en forregling i normaldrift.\n")
    print("     %-6s %12s %12s" % ("", "harledda", "motbevisade"))
    for r in alla:
        d = r["produktion"]["x10"]
        print("     %-6s %12d %12d"
              % (r["task_id"], d["harledda_invarianter"],
                 len(d["motbevisade_av_provsparet"])))

    print("\n  6. GRINDEN PA SITT EGET FACIT (ska vara tom)")
    for r in alla:
        print("     %-6s provspar %-4s produktion %-4s  referensen uppfyller "
              "%s / %s"
              % (r["task_id"],
                 r["provspar"]["tackningsbrister"] or "-",
                 r["produktion"]["x10"]["tackningsbrister"] or "-",
                 r["provspar"]["referensen_uppfyller"],
                 r["produktion"]["x10"]["referensen_uppfyller"]))

    modell = []
    if a.svar:
        print("\n  7. EN MODELLS ST MOT DET HARLEDDA FACIT")
        print("     Samma skelett, samma forgrindar, samma domare som fas 9.")
        print("     Modellen fick BARA anlaggningsbriefen: signalkartan och")
        print("     det harledda facit. Ingen uppgiftstext, ingen referens.\n")
        for post, r in zip(poster, alla):
            prov = spela_in(post, set(s["id"] for s in post["facit_spar"]["sekvenser"]),
                            1, "provsparet")
            h = An.harled(prov)
            m = kor_modellsvar(post, h.facit, a.svar, fas9, index)
            modell.append(m)
            print("     %-6s %-12s %s" % (m["task_id"], m.get("utfall"),
                                          ", ".join(sorted(set(m.get("koder") or [])))
                                          or m.get("skal", "")[:60]))
            for g, v in sorted((m.get("forgrindar") or {}).items()):
                if v is not True:
                    print("            grind %-22s %s" % (g, str(v)[:60]))
            k = m.get("kontaminering")
            if k:
                print("            kontaminering: likhet %.1f%%, langsta %d, "
                      "delade egna namn: %s"
                      % (100 * k["likhet"], k["langsta_gemensamma"],
                         ", ".join(k["delade_namn"]) or "INGA"))
        godkanda = sum(1 for m in modell if m.get("godkand"))
        if a.varv <= 1:
            print("\n     FORSTA FORSOKET mot harlett facit: %d av %d"
                  % (godkanda, len(modell)))
        else:
            print("\n     EFTER %d REPARATIONSVARV mot harlett facit: %d av %d"
                  % (a.varv - 1, godkanda, len(modell)))
        mot_hand = sum(1 for m in modell
                       if (m.get("mot_handskrivet_facit") or {}).get("godkand"))
        print("     SAMMA LOSNINGAR mot bankens handskrivna facit: %d av %d"
              % (mot_hand, len(modell)))
        print("     Skillnaden ar vad inspelningen inte kunde beratta.")
        if a.aterkoppling:
            print("\n     aterkoppling skriven (grindens och facits EGNA ord,")
            print("     ordagrant - ingen omskrivning, ingen sammanfattning):")
            for post, m in zip(poster, modell):
                print("       %s" % fas9.skriv_aterkoppling(m, post, a.svar))

    if a.brief:
        print("\n  anlaggningsbrief skriven:")
        for f in briefer:
            print("    %s" % f)

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"uppgifter": alla, "modell": modell}, f, indent=1,
                      ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
