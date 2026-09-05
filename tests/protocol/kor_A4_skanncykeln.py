# -*- coding: utf-8 -*-
"""M-166 (ko A, punkt A4): skanncykeln under banken.

Var ST-tolk HAR en cykeltid - `st/tolk.py:SCAN_MS = 20.0`, matt i M-20 - men
ingen har nagonsin bytt den och sett efter vad som hander. Bankens spar star i
millisekunder, och ett spar med tider i millisekunder betyder olika saker vid
5 ms och 100 ms cykel. Fragan ar darfor inte akademisk: den avgor om bankens
`facit_spar` overhuvudtaget ar VALSTALLDA.

## Varfor korningen inte far vara en enkel omkorning

`bank/domare.py` laser punktkravet i EXAKT det scan vars klocka star pa `t_ms`:

    if abs(float(s["t_ms"]) - (nu - scan_ms)) > 1e-9: continue

Bankens tider ar alla multiplar av 20 ms (matt har: gcd = 20 over 348 skilda
`t_ms`). Byter man scanperiod till 40 eller 100 ms hamnar 156 av dem MELLAN tva
scan, och den raden hoppar da over kravet UTAN ETT ORD. En naiv svep hade
darfor rapporterat "inga andrade dom" - inte for att banken ar cykeloberoende
utan for att halva facit tystnade. Det ar en matning som mater sitt eget
rutnat.

Korningen anvander darfor en generaliserad lasregel som ar IDENTISK vid
scan_ms = 20 och valdefinierad vid varje annan period:

    punktkravet vid t_ms lases efter det FORSTA scan vars klocka ar >= t_ms.

Vid 20 ms ar `ceil(t/20)*20 == t` for varje t i banken, alltsa samma scan som
`domare.py` laser. Vid 100 ms ar det det forsta scan som over huvud taget har
sett stimulit - vilket ar precis vad en PLC med 100 ms cykel kan observera.

## De tva trasiga fallen

1. **Sjalvkontrollen.** Vid scan_ms = 20 maste den generaliserade domaren ge
   BIT-IDENTISKT utfall och bristkodsmangd som `bank/domare.py` for varje enhet
   i banken. Gor den inte det mater svepet harnessen och inte cykeltiden, och
   korningen faller innan den svepar.
2. **Blindhetskontrollen.** Ett handskrivet kontrollfall (`CYKELFALLET`) som
   ligger UTANFOR banken och vars dom bevisligen HANGER pa cykeltiden - en
   TON med PT = 30 ms, som lopt ut efter tva scan a 20 ms men efter ett scan
   a 40 ms - maste rapporteras som cykelberoende. Ett svep som svarar "inga"
   maste forst ha visat att det kan svara "nagra".

Utan (2) ar ett noll-resultat oskiljbart fran en trasig matare.

Kors sa har (svepet ar rent CPU-arbete, ingen rigg och ingen docker):

    nice -n 19 ionice -c3 python3 tests/protocol/kor_A4_skanncykeln.py \\
        --scan 5,10,20,40,100 \\
        --jsonl docs/matningar/radata/m166_svep.jsonl \\
        --json docs/matningar/radata/m166_sammanstallning.json
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BANKPOST = {
    "pastar": (
        "Bankens sparfacit gar att doma vid flera skanncykeltider, och antalet "
        "uppgifter vars dom andras nar cykeltiden andras ar ett matt tal per "
        "uppgift - inte ett medelvarde och inte ett antagande. Ett facit vars "
        "punkter ligger tatare an scanperioden ar inte valstallt vid den "
        "perioden, och det raknas for sig."),
    "under_prov": ("bank/uppgifter",),
    "facit": (
        "IEC 61131-3:s skanncykel (las in, kor, skriv ut, upprepa) kord vid "
        "fem perioder, plus ett handskrivet kontrollfall utanfor banken vars "
        "dom bevisligen hanger pa perioden (TON med PT = 30 ms)."),
    "facitkalla": (
        "M-20:s uppmatta scanperiod for OpenPLC Runtime v4 (20 ms, svarstid "
        "exakt tva scan) som referenspunkt, och ett handskrivet kontrollfall "
        "i korningen sjalv - bada utanfor bank/uppgifter"),
    "facitkalla_filer": ("docs/matningar/M-20_plcbandet.md",),
    "trasiga_fall": (
        "sjalvkontrollen: vid scan_ms = 20 maste den generaliserade domaren ge "
        "identiskt utfall OCH identisk bristkodsmangd som bank/domare.py for "
        "varje enhet - annars faller korningen innan den svepar",
        "blindhetskontrollen: ett handskrivet fall vars dom hanger pa "
        "cykeltiden maste rapporteras som cykelberoende; ett svep som kan "
        "svara 'inga' maste forst ha visat att det kan svara 'nagra'",
        "ett punktkrav som hamnar mellan tva scan far ALDRIG hoppas over tyst "
        "- off-grid-kraven raknas och redovisas per period",
        "noll matta enheter ger returkod != 0",
    ),
    "kraver": ("inget",),
    "matningar": ("M-166",),
}

import domare as D                      # noqa: E402
from vc_assist_svc.st import tolk as _tolk   # noqa: E402

Tolkfel = _tolk.Tolkfel


# ------------------------------------------------------------- kontrollfallet
#
# Ligger UTANFOR banken med avsikt. Facit ar rakningen for hand, skriven har:
# TON med PT = 30 ms. Vid 20 ms scan har ET vardena 0, 20, 30(mattat) - alltsa
# gar Q hogt forst i det scan vars klocka star pa 40 ms. Vid 40 ms scan har ET
# vardena 0, 30(mattat) - Q gar hogt redan i scanet vid 40 ms... men punktkravet
# star vid 20 ms, och vid 40 ms scan finns inget scan med klockan 20.
#
# Det som gor fallet skarpt ar inte rutnatet utan LOGIKEN: kravet "LARM=0 vid
# t=20 ms" ar sant vid 20 ms cykel (ET=20 < PT=30) och falskt vid 10 ms cykel?
# Nej - vid 10 ms ar ET vid klockan 20 lika med 20, ocksa < 30. Kravet som
# skiljer ar det vid t = 40 ms: vid 20 ms cykel har ET hunnit 30 (mattat) och
# Q ar hog; vid 100 ms cykel har det forsta scanet efter t=0 klockan 100 och
# ET blir 100 -> Q hog, men mellanpunkten vid 40 ms finns inte. Fallet nedan ar
# skrivet sa att bade en LOGIKskillnad och en RUTNATskillnad far falla ut, och
# vilken det var star i utfallet.
CYKELFALLET = {
    "task_id": "CYKEL-KONTROLL",
    "control": {"signals": [
        {"name": "START", "type": "bool", "dir": "in"},
        {"name": "LARM", "type": "bool", "dir": "out"},
    ]},
    "facit_spar": {
        "scan_ms": 20,
        "referens": (
            "PROGRAM Main\n"
            "VAR\n"
            "  t1 : TON;\n"
            "END_VAR\n"
            "t1(IN := START, PT := T#30ms);\n"
            "LARM := t1.Q;\n"
            "END_PROGRAM\n"),
        "sekvenser": [{
            "id": "vakten_loper_ut",
            "steg": [
                {"t_ms": 0, "satt": {"START": True}, "krav": {"LARM": False},
                 "varfor": "vakten har just startat"},
                {"t_ms": 20, "krav": {"LARM": False},
                 "varfor": "20 ms av 30 har gatt; vakten far inte ha lopt ut"},
                {"t_ms": 60, "krav": {"LARM": True},
                 "varfor": "30 ms har passerat; vakten ska ha lopt ut"},
            ],
        }],
        "flanker": [{
            "namn": "en_enda_larmflank",
            "sekvens": "vakten_loper_ut",
            "signal": "LARM", "typ": "RISE",
            "fran_ms": 0, "till_ms": 60, "antal": 1,
            "varfor": "larmet ska ga hogt exakt en gang",
        }],
        "invarianter": [],
        "motbevis": [],
    },
}


# ------------------------------------------------------------------ enheter

def las_uppgift(task_id):
    with open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % task_id),
              "r", encoding="utf-8") as f:
        return json.load(f)


def alla_uppgifter():
    ut = []
    for vag in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                             "*.json"))):
        with open(vag, "r", encoding="utf-8") as f:
            post = json.load(f)
        if not (post.get("facit_spar") or {}).get("sekvenser"):
            continue
        ut.append(post["task_id"])
    return ut


def enheter_for(post):
    fs = post["facit_spar"]
    ut = [("referens", fs["referens"])]
    for mb in fs.get("motbevis") or []:
        ut.append(("motbevis:" + mb["namn"], mb["st"]))
    return ut


# ------------------------------------------------------- domen vid en period

def _scanindex(t_ms, scan_ms):
    """Det forsta scan vars klocka ar >= t_ms.

    Vid scan_ms = 20 och bankens tider (alla multiplar av 20) ar det exakt det
    scan `domare.py` laser i. Vid grovre period ar det det forsta scan som
    over huvud taget har sett stimulit vid t_ms - det en riktig PLC med den
    perioden kan observera.
    """
    return int(math.ceil(t_ms / scan_ms - 1e-9))


def dom_vid_scan(post, st_text, scan_ms, omstart_ms=(), kall=False):
    """Samma domarmekanik som `domare.dom`, med scanperioden som parameter.

    Returnerar (Dom, matdata). `matdata` bar vad som INTE gick att lasa pa
    rutnatet, sa att ett noll-resultat gar att skilja fran en tyst matare.

    `omstart_ms` ar tider dar PLC:n startas om FORE scanet (ko A, punkt A9,
    M-168). Tom sekvens = ingen omstart, och da ar funktionen exakt den
    mekanik sjalvkontrollen jamfor mot `bank/domare.py`. `kall=True` ger en
    kallstart i stallet for en varmstart: skillnaden ar RETAIN, och att den
    skillnaden gar att se ar hela A9:s trasiga fixtur.
    """
    omstart = sorted(float(t) for t in (omstart_ms or ()))
    facit = post.get("facit_spar")
    if not isinstance(facit, dict):
        raise D.Domsfel("%s har inget facit_spar" % post.get("task_id"))
    typer, riktningar = D._signalkarta(post)
    brister = []
    scan_totalt = 0
    mat = {"punktkrav": 0, "punktkrav_offgrid": 0, "punktkrav_kollapsade": 0,
           "flankfonster": 0, "flankfonster_utan_scanpunkt": 0,
           "steg_kollapsade": 0}

    invarianter = facit.get("invarianter") or []
    flanker = facit.get("flanker") or []

    for sekv in facit.get("sekvenser") or []:
        sid = sekv["id"]
        steg = sorted(sekv["steg"], key=lambda x: float(x["t_ms"]))
        slut_ms = max([float(s["t_ms"]) for s in steg] +
                      [float(f.get("till_ms", 0.0)) for f in flanker
                       if f.get("sekvens") == sid])
        try:
            motor = _tolk.Tolk(st_text, typer, riktningar, scan_ms)
        except Tolkfel as fel:
            brister.append(D.Brist("tolkfel:%s" % sid, str(fel)))
            break

        # Kraven grupperas per LASSCAN i stallet for per t_ms. Tva krav som
        # hamnar i samma scan ar tva krav pa samma avlasning: det ar cykelns
        # verkan pa facit och rakans.
        per_scan = {}
        for s in steg:
            k = _scanindex(float(s["t_ms"]), scan_ms)
            if s.get("krav"):
                mat["punktkrav"] += len(s["krav"])
                if abs(float(s["t_ms"]) / scan_ms
                       - round(float(s["t_ms"]) / scan_ms)) > 1e-9:
                    mat["punktkrav_offgrid"] += len(s["krav"])
            per_scan.setdefault(k, []).append(s)
        for k, lista in per_scan.items():
            med_krav = [s for s in lista if s.get("krav")]
            if len(med_krav) > 1:
                mat["punktkrav_kollapsade"] += sum(len(s["krav"])
                                                   for s in med_krav[1:])
            if len(lista) > 1:
                mat["steg_kollapsade"] += len(lista) - 1

        mina_inv = [i for i in invarianter
                    if i.get("sekvens") in (None, "*", sid)]
        inv_falld = set()
        mina_flank = [f for f in flanker if f.get("sekvens") == sid]
        flankraknare = dict((f["namn"], 0) for f in mina_flank)
        forra = {}
        for f in mina_flank:
            mat["flankfonster"] += 1
            k0 = int(math.ceil(float(f["fran_ms"]) / scan_ms - 1e-9))
            if k0 * scan_ms > float(f["till_ms"]) + 1e-9:
                mat["flankfonster_utan_scanpunkt"] += 1

        # Sista scan som nagon lasning behover. Utan det taket kor en grov
        # period antingen for kort (och missar sista kravet) eller onodigt
        # langt.
        sista_k = max([_scanindex(float(s["t_ms"]), scan_ms) for s in steg] +
                      [_scanindex(float(f["till_ms"]), scan_ms)
                       for f in mina_flank] + [0])

        i = 0
        j = 0
        try:
            k = 0
            while k <= sista_k:
                while i < len(steg) and \
                        float(steg[i]["t_ms"]) <= motor.tid_ms + 1e-9:
                    for namn, v in (steg[i].get("satt") or {}).items():
                        motor.satt(namn, v)
                    i += 1
                # Omstarten ligger FORE scanet, som en stromlos period gor:
                # nasta scan ar det forsta efter uppstarten, och det laser om
                # ingangarna ur faltet (som inte andras av att PLC:n slocknar).
                while j < len(omstart) and omstart[j] <= motor.tid_ms + 1e-9:
                    if kall:
                        motor.kallstart()
                    else:
                        motor.varmstart()
                    mat["omstarter"] = mat.get("omstarter", 0) + 1
                    j += 1
                motor.scan()
                scan_totalt += 1
                nu = motor.tid_ms                 # klockan EFTER scanet

                for s in per_scan.get(k, ()):
                    for namn, vantat in (s.get("krav") or {}).items():
                        faktiskt = motor.las(namn)
                        if not D._lika(vantat, faktiskt):
                            brister.append(D.Brist(
                                "%s@%.0fms:%s" % (sid, float(s["t_ms"]), namn),
                                "%s skulle vara %s men var %s. %s"
                                % (namn, D._skriv(vantat), D._skriv(faktiskt),
                                   s.get("varfor") or "")))

                for inv in mina_inv:
                    if inv["namn"] in inv_falld:
                        continue
                    if all(D._lika(v, motor.las(n))
                           for n, v in inv["nar"].items()) and \
                       not all(D._lika(v, motor.las(n))
                               for n, v in inv["kraver"].items()):
                        inv_falld.add(inv["namn"])
                        brister.append(D.Brist(
                            "invariant:%s@%s" % (inv["namn"], sid),
                            "vid t=%.0f ms gallde %s men inte %s. %s"
                            % (nu - scan_ms,
                               ", ".join("%s=%s" % (n, D._skriv(v))
                                         for n, v in inv["nar"].items()),
                               ", ".join("%s=%s" % (n, D._skriv(v))
                                         for n, v in inv["kraver"].items()),
                               inv.get("varfor") or "")))

                nu_varden = {}
                for f in mina_flank:
                    signal = f["signal"]
                    if signal not in nu_varden:
                        nu_varden[signal] = bool(motor.las(signal))
                    v = nu_varden[signal]
                    p = forra.get(signal)
                    t_ledd = nu - scan_ms
                    if p is not None and float(f["fran_ms"]) <= t_ledd \
                            <= float(f["till_ms"]):
                        if f["typ"] == "RISE" and v and not p:
                            flankraknare[f["namn"]] += 1
                        elif f["typ"] == "FALL" and p and not v:
                            flankraknare[f["namn"]] += 1
                forra.update(nu_varden)
                k += 1
        except Tolkfel as fel:
            brister.append(D.Brist("tolkfel:%s" % sid, str(fel)))

        for f in mina_flank:
            if flankraknare[f["namn"]] != int(f["antal"]):
                brister.append(D.Brist(
                    "flank:%s" % f["namn"],
                    "%s skulle ha %d %s-flank(er) mellan %.0f och %.0f ms, "
                    "hade %d. %s"
                    % (f["signal"], int(f["antal"]), f["typ"],
                       float(f["fran_ms"]), float(f["till_ms"]),
                       flankraknare[f["namn"]], f.get("varfor") or "")))

    return D.Dom(post.get("task_id"), brister, scan_totalt), mat


# ------------------------------------------------------------ trasiga fallen

def sjalvkontroll(uppgifter=None):
    """Trasigt fall 1: vid 20 ms MASTE harnessen vara `domare.py`.

    Returnerar en lista avvikelser. Tom lista = harnessen mater cykeltiden och
    inte sig sjalv.
    """
    avvikelser = []
    for task_id in (uppgifter or alla_uppgifter()):
        post = las_uppgift(task_id)
        for etikett, st_text in enheter_for(post):
            try:
                referens = D.dom(post, st_text)
                ref = ("GODKAND" if referens.godkand else "UNDERKAND",
                       tuple(sorted(referens.koder)))
            except D.Domsfel as fel:
                ref = ("DOMSFEL", (str(fel)[:200],))
            try:
                min_dom, _ = dom_vid_scan(post, st_text, 20.0)
                min_ = ("GODKAND" if min_dom.godkand else "UNDERKAND",
                        tuple(sorted(min_dom.koder)))
            except D.Domsfel as fel:
                min_ = ("DOMSFEL", (str(fel)[:200],))
            if ref != min_:
                avvikelser.append({
                    "enhet": "%s/%s" % (task_id, etikett),
                    "domare_py": {"utfall": ref[0], "koder": list(ref[1])},
                    "harness": {"utfall": min_[0], "koder": list(min_[1])},
                })
    return avvikelser


def blindhetskontroll(perioder):
    """Trasigt fall 2: ett fall vars dom BEVISLIGEN hanger pa cykeltiden.

    Returnerar (ar_cykelberoende, {period: (utfall, koder)}).
    """
    ut = {}
    for p in perioder:
        d, _ = dom_vid_scan(CYKELFALLET, CYKELFALLET["facit_spar"]["referens"],
                            float(p))
        ut[p] = ("GODKAND" if d.godkand else "UNDERKAND", sorted(d.koder))
    utfall = set(v[0] for v in ut.values())
    return (len(utfall) > 1), ut


# ------------------------------------------------------------------- svepet

def svep(args):
    perioder = [float(x) for x in args.scan.split(",")]
    if 20.0 not in perioder:
        raise SystemExit("20 ms maste vara med: den ar baslinjen (M-20)")

    print("--- trasigt fall 2: blindhetskontrollen ---")
    beroende, tabell = blindhetskontroll(perioder)
    for p in sorted(tabell):
        print("  %6.1f ms  %s  %s" % (p, tabell[p][0], ",".join(tabell[p][1])))
    if not beroende:
        raise SystemExit(
            "BLINDHETSKONTROLLEN FOLL: kontrollfallet, vars dom hanger pa "
            "cykeltiden, gav samma utfall vid varje period. Svepet kan inte "
            "svara 'nagra' och far darfor inte svara 'inga'.")
    print("  cykelberoende UPPTACKT -> svepet kan se skillnaden\n")

    uppgifter = args.uppgifter.split(",") if args.uppgifter else alla_uppgifter()

    print("--- trasigt fall 1: sjalvkontrollen vid 20 ms ---")
    t0 = time.time()
    avvikelser = sjalvkontroll(uppgifter)
    print("  %d enheter, %d avvikelser, %.1f s"
          % (sum(len(enheter_for(las_uppgift(t))) for t in uppgifter),
             len(avvikelser), time.time() - t0))
    if avvikelser:
        for a in avvikelser[:20]:
            print("  %s: domare.py %s / harness %s"
                  % (a["enhet"], a["domare_py"], a["harness"]))
        raise SystemExit(
            "SJALVKONTROLLEN FOLL: harnessen domer inte som bank/domare.py vid "
            "20 ms. Svepet hade matt harnessen, inte cykeltiden.")
    print("  identisk med bank/domare.py\n")

    ut = open(args.jsonl, "a", encoding="utf-8") if args.jsonl else None
    rader = []
    for task_id in uppgifter:
        post = las_uppgift(task_id)
        for etikett, st_text in enheter_for(post):
            for p in perioder:
                t = time.time()
                try:
                    d, mat = dom_vid_scan(post, st_text, p)
                    rad = {"task": task_id, "etikett": etikett, "scan_ms": p,
                           "utfall": "GODKAND" if d.godkand else "UNDERKAND",
                           "koder": sorted(d.koder), "scan": d.scan_kord,
                           "mat": mat, "sekunder": round(time.time() - t, 3)}
                except D.Domsfel as fel:
                    rad = {"task": task_id, "etikett": etikett, "scan_ms": p,
                           "utfall": "DOMSFEL", "koder": [], "scan": 0,
                           "skal": str(fel)[:800], "mat": {},
                           "sekunder": round(time.time() - t, 3)}
                rader.append(rad)
                if ut:
                    ut.write(json.dumps(rad, ensure_ascii=False) + "\n")
                    ut.flush()
                    os.fsync(ut.fileno())
        print("  %-6s klar" % task_id)
    if ut:
        ut.close()
    return sammanstall(rader, perioder, args)


# ------------------------------------------------------------ sammanstallning

def sammanstall(rader, perioder, args):
    baslinje = {}
    for r in rader:
        if abs(r["scan_ms"] - 20.0) < 1e-9:
            baslinje[(r["task"], r["etikett"])] = r
    per_uppgift = {}
    for r in rader:
        p = r["scan_ms"]
        if abs(p - 20.0) < 1e-9:
            continue
        b = baslinje.get((r["task"], r["etikett"]))
        if b is None:
            continue
        post = per_uppgift.setdefault(r["task"], {})
        rad = post.setdefault(p, {"utfall_andrad": [], "koder_andrad": [],
                                  "enheter": 0})
        rad["enheter"] += 1
        if r["utfall"] != b["utfall"]:
            rad["utfall_andrad"].append(r["etikett"])
        elif sorted(r["koder"]) != sorted(b["koder"]):
            rad["koder_andrad"].append(r["etikett"])

    matsumma = {}
    for r in rader:
        m = matsumma.setdefault(r["scan_ms"], {})
        for k, v in (r.get("mat") or {}).items():
            m[k] = m.get(k, 0) + v

    resultat = {
        "perioder": perioder,
        "enheter": len(baslinje),
        "uppgifter": sorted(per_uppgift),
        "per_uppgift": per_uppgift,
        "matsumma": matsumma,
        "totalt": {},
    }
    for p in perioder:
        if abs(p - 20.0) < 1e-9:
            continue
        u = sum(len(v.get(p, {}).get("utfall_andrad", []))
                for v in per_uppgift.values())
        k = sum(len(v.get(p, {}).get("koder_andrad", []))
                for v in per_uppgift.values())
        upp = sum(1 for v in per_uppgift.values()
                  if v.get(p, {}).get("utfall_andrad"))
        resultat["totalt"][p] = {"enheter_utfall_andrat": u,
                                 "enheter_koder_andrat": k,
                                 "uppgifter_med_utfallsandring": upp}

    print("\n=== per uppgift: enheter vars UTFALL andras mot 20 ms ===")
    kolumner = [p for p in perioder if abs(p - 20.0) > 1e-9]
    print("uppgift  " + "  ".join("%7.0f" % p for p in kolumner))
    for task in sorted(per_uppgift):
        v = per_uppgift[task]
        print("%-8s " % task + "  ".join(
            "%7d" % len(v.get(p, {}).get("utfall_andrad", []))
            for p in kolumner))
    print("\n=== totalt ===")
    for p in kolumner:
        t = resultat["totalt"][p]
        print("  %6.0f ms: %d enheter byter utfall (%d uppgifter), "
              "%d enheter byter bara koder"
              % (p, t["enheter_utfall_andrat"],
                 t["uppgifter_med_utfallsandring"], t["enheter_koder_andrat"]))
    print("\n=== rutnatet: vad facit inte kan lasas pa ===")
    for p in perioder:
        m = matsumma.get(p, {})
        print("  %6.0f ms: %d punktkrav, varav %d off-grid och %d kollapsade "
              "i samma scan; %d flankfonster utan en enda scanpunkt"
              % (p, m.get("punktkrav", 0), m.get("punktkrav_offgrid", 0),
                 m.get("punktkrav_kollapsade", 0),
                 m.get("flankfonster_utan_scanpunkt", 0)))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=1, sort_keys=True)
    if not baslinje:
        print("noll matta enheter")
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-166: skanncykeln under banken")
    ap.add_argument("--scan", default="5,10,20,40,100",
                    help="cykeltider i ms, kommaseparerat; 20 maste vara med")
    ap.add_argument("--uppgifter", help="kommaseparerade task_id")
    ap.add_argument("--jsonl", help="radata, en rad per (enhet, period)")
    ap.add_argument("--json", help="sammanstallning")
    ap.add_argument("--las", help="las radata ur JSONL i stallet for att kora")
    a = ap.parse_args(argv)
    if a.las:
        rader = []
        for vag in sorted(glob.glob(a.las)):
            with open(vag, "r", encoding="utf-8") as f:
                for r in f:
                    if r.strip():
                        rader.append(json.loads(r))
        perioder = sorted(set(r["scan_ms"] for r in rader))
        return sammanstall(rader, perioder, a)
    return svep(a)


if __name__ == "__main__":
    raise SystemExit(main())
