# -*- coding: utf-8 -*-
"""M-153 (ko A, punkt A3): hela banken genom BADA domarna, n >= 3.

`bank/domare.py` domer bankens sparfacit genom var egen ST-tolk.
`bank/domare_openplc.py` domer samma facit genom OpenPLC Runtime v4. A2
(`M-146`) visade att de tva domarna gar isar - och, viktigare, att den ena
domaren kan vara oense med SIG SJALV: samma text gav tva olika kodmangder ur
OpenPLC-domaren i tva korningar, for att invariantregeln (5 scan i rad =
100 ms) ligger sa nara brottets langd att realtidens jitter avgor.

Darfor har korningen tre tal och inte ett, och de blandas latt ihop:

  (a) UTFALLSOENIGHET - domarna sager olika sak om GRON/ROD.
  (b) KODOENIGHET     - domarna sager samma sak om gron/rod men fal
                        ler pa olika bristkoder.
  (c) SJALVINSTABILITET - EN domare ger olika svar pa samma text mellan
                        korningar. Det ar M-146:s fynd, och den har ett
                        eget tal per uppgift.

Formen ar n per enhet, aldrig en korning: en enhet som ar gron i 2 av 3 ar
INTE gron. Aggregatorn far inte kunna sla ihop 2-av-3 till "gron" - det ar
korningens trasiga fixtur, och den provas mekaniskt fore varje sammanstallning.

Strukturellt undantag som maste RAKNAS och inte tigas bort: OpenPLC-domaren
kan aldrig lamna en `tolkfel:*`-kod, for den kor inte var tolk. Ett motbevis
vars `faller_pa` namner en sadan kod kan alltsa inte fallas "pa ratt brist" av
den nya domaren hur ratt den an har. M-146 raknade 1 av bankens 152 motbevis;
korningen raknar om det sjalv i stallet for att lita pa talet.

Tva lagen:

  SVEP (en arbetare, en rigg, en skiva av banken). Varje KORNING skrivs som en
  rad i en JSONL sa fort den ar klar - en avbruten korning far aldrig tappa
  det som redan ar matt:

    nice -n 19 ionice -c3 python3 tests/protocol/kor_A3_domarna_i_skala.py \\
        --skiva 1/12 --n 3 --bas https://127.0.0.1:18451 \\
        --endpoint opc.tcp://172.17.0.4:4840/openplc/opcua \\
        --jsonl /tmp/a3/w1.jsonl --byggkatalog /tmp/a3/bygg1

  SAMMANSTALLNING (ingen rigg, ingen docker, laser bara JSONL):

    python3 tests/protocol/kor_A3_domarna_i_skala.py --sammanstall /tmp/a3/*.jsonl \\
        --n 3 --json docs/matningar/radata/m153_sammanstallning.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BANKPOST = {
    "pastar": (
        "Hela bankens sparfacit gar att doma genom BADA domarna med n >= 3 "
        "per enhet, och skillnaden mellan dem gar att dela i tre tal som inte "
        "far blandas ihop: utfallsoenighet (gron/rod), kodoenighet (samma "
        "utfall, olika bristkoder) och sjalvinstabilitet (en domare oense med "
        "sig sjalv mellan korningar). En enhet som ar gron i 2 av 3 korningar "
        "ar inte gron."),
    "under_prov": ("bank/domare.py", "bank/domare_openplc.py"),
    "facit": (
        "Uppgiftens egna sparfacit (punktkrav, invarianter, flankrakning), "
        "skrivet av en manniska fore korningen. Samma facit lases av bada "
        "domarna; det som jamfors ar domarna, inte facit."),
    "facitkalla": (
        "Bankens manniskoskrivna sparfacit (laglig kalla 4) dompt genom tva "
        "oberoende motorer: var ST-tolk och OpenPLC Runtime v4.2.1 (kalla 1)"),
    "facitkalla_filer": ("bank/uppgifter",),
    "trasiga_fall": (
        "2 av 3 grona far ALDRIG bli GRON i sammanstallningen - en enhet med "
        "delade utfall ar INSTABIL, och rakans som ett eget tal",
        "en enhet med farre an n korningar i en domare far aldrig komma med "
        "bland de matta - den rakans som OMATT och faller korningen",
        "ett DOMSFEL ar aldrig ett utfall: en enhet dar en domare gav Domsfel "
        "ar ODOMD och rakans varken som ense eller som oense",
        "en kodoenighet som BARA bestar av tolkfel:*-koder ar det strukturella "
        "undantaget och maste redovisas for sig, aldrig raknas bort tyst",
        "noll matta enheter ger returkod != 0",
    ),
    "kraver": ("openplc", "strucpp"),
    "matningar": ("M-153",),
}

import domare as D                      # noqa: E402
import domare_openplc as DO             # noqa: E402


# ------------------------------------------------------------------ enheter

def las_uppgift(task_id):
    with open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % task_id),
              "r", encoding="utf-8") as f:
        return json.load(f)


def alla_uppgifter():
    """Bankens uppgifter med sparfacit, i vaxande sparlangd."""
    ut = []
    for vag in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter",
                                             "*.json"))):
        with open(vag, "r", encoding="utf-8") as f:
            post = json.load(f)
        if not (post.get("facit_spar") or {}).get("sekvenser"):
            continue
        ut.append((post["task_id"], _sparlangd(post)))
    ut.sort(key=lambda x: x[1])
    return [t for t, _ in ut]


def _sparlangd(post):
    fs = post.get("facit_spar") or {}
    s = 0
    for sekv in fs.get("sekvenser") or []:
        s += max([steg.get("t_ms", 0) for steg in (sekv.get("steg") or [])]
                 or [0])
    return s / 1000.0


def enheter_for(task_id):
    """(etikett, st_text, faller_pa) for referensen och varje motbevis."""
    post = las_uppgift(task_id)
    fs = post["facit_spar"]
    ut = [("referens", fs["referens"], [])]
    for mb in fs.get("motbevis") or []:
        ut.append(("motbevis:" + mb["namn"], mb["st"],
                   list(mb.get("faller_pa") or [])))
    return post, ut


def kostnad(task_id, etikett=None):
    """Grov kostnad i sekunder per KORNING av en enhet.

    spar + 7,1 s per sekvens (bygge + omstart), matt i M-146 pa P-05/L-01/P-07
    (29/45/60 s vid 3/5/7 sekvenser och 6,4/9,4/10,6 s spar). Anvands BARA for
    att packa skivorna jamnt; ingen dom hanger pa talet.
    """
    post = las_uppgift(task_id)
    n_seq = len(post["facit_spar"]["sekvenser"])
    return _sparlangd(post) + 7.1 * n_seq


# ------------------------------------------------------------------- svepet

def _kor_tolk(post, st_text):
    t = time.time()
    try:
        d = D.dom(post, st_text)
        return {"utfall": "GODKAND" if d.godkand else "UNDERKAND",
                "koder": sorted(d.koder), "sekunder": round(time.time() - t, 2)}
    except D.Domsfel as fel:
        return {"utfall": "DOMSFEL", "koder": [], "skal": str(fel)[:1200],
                "sekunder": round(time.time() - t, 2)}


def _kor_openplc(post, st_text, rigg, byggkatalog):
    t = time.time()
    try:
        d = DO.dom(post, st_text, rigg=rigg, byggkatalog=byggkatalog)
        rad = {"utfall": "GODKAND" if d.godkand else "UNDERKAND",
               "koder": sorted(d.koder), "sekunder": round(time.time() - t, 2)}
        off = [m["offset_scan"] for m in getattr(d, "matpunkter", [])
               if m.get("offset_scan") is not None]
        rad["matpunkter"] = {"n": len(off),
                             "fordelning": dict((str(o), off.count(o))
                                                for o in sorted(set(off)))}
        return rad
    except D.Domsfel as fel:
        return {"utfall": "DOMSFEL", "koder": [], "skal": str(fel)[:1200],
                "sekunder": round(time.time() - t, 2)}
    except Exception as fel:                       # noqa: BLE001
        # Ett ovantat undantag ur kedjan (OpenPlcFel, ett trasigt svar, en
        # bruten socket) far ALDRIG bli en dom och far inte heller tystas som
        # ett Domsfel: det ar en tredje sak och star som AVBROTT med sin klass.
        return {"utfall": "AVBROTT", "koder": [],
                "skal": "%s: %s" % (type(fel).__name__, fel), "sekunder":
                round(time.time() - t, 2)}


DOMAR = ("GODKAND", "UNDERKAND")     # allt annat ar ingen dom alls


def svep(args):
    rigg = DO.Rigg(bas=args.bas, endpoint=args.endpoint)
    rigg.kontrollera()
    os.makedirs(os.path.dirname(os.path.abspath(args.jsonl)) or ".",
                exist_ok=True)
    os.makedirs(args.byggkatalog, exist_ok=True)
    gjorda = _redan_gjorda(args.jsonl)
    ut = open(args.jsonl, "a", encoding="utf-8")

    def skriv(rad):
        ut.write(json.dumps(rad, ensure_ascii=False) + "\n")
        ut.flush()
        os.fsync(ut.fileno())

    antal = 0
    for task_id in args.uppgifter:
        post, enheter = enheter_for(task_id)
        for etikett, st_text, faller_pa in enheter:
            for varv in range(1, args.n + 1):
                for domarnamn in ("tolk", "openplc"):
                    nyckel = (task_id, etikett, domarnamn, varv)
                    if nyckel in gjorda:
                        continue
                    kat = os.path.join(
                        args.byggkatalog, task_id,
                        etikett.replace(":", "_") + "_v%d" % varv)
                    if domarnamn == "tolk":
                        rad = _kor_tolk(post, st_text)
                    else:
                        rad = _kor_openplc(post, st_text, rigg, kat)
                        shutil.rmtree(kat, ignore_errors=True)
                    rad.update({"task": task_id, "etikett": etikett,
                                "domare": domarnamn, "varv": varv,
                                "faller_pa": faller_pa, "rigg": rigg.bas,
                                "tid": time.strftime("%Y-%m-%dT%H:%M:%S")})
                    skriv(rad)
                    antal += 1
                    print("%-6s %-42s %-7s v%d %-9s %s"
                          % (task_id, etikett, domarnamn, varv, rad["utfall"],
                             ",".join(rad["koder"]) or ""))
                    sys.stdout.flush()
    ut.close()
    shutil.rmtree(args.byggkatalog, ignore_errors=True)
    return 0 if antal or gjorda else 1


def _redan_gjorda(jsonl):
    """Aterupptagning: vilka (task, etikett, domare, varv) som redan star."""
    gjorda = set()
    if not os.path.exists(jsonl):
        return gjorda
    with open(jsonl, "r", encoding="utf-8") as f:
        for rad in f:
            rad = rad.strip()
            if not rad:
                continue
            try:
                r = json.loads(rad)
            except ValueError:
                continue
            gjorda.add((r["task"], r["etikett"], r["domare"], r["varv"]))
    return gjorda


# ----------------------------------------------------------- sammanstallning

def las_rader(monster):
    rader = []
    for m in monster:
        for vag in sorted(glob.glob(m)):
            with open(vag, "r", encoding="utf-8") as f:
                for rad in f:
                    rad = rad.strip()
                    if rad:
                        rader.append(json.loads(rad))
    return rader


def _tolkfel(koder):
    return set(k for k in koder if k.startswith("tolkfel:"))


def sammanstall(rader, n_kravd):
    """Tre tal, per enhet, och aldrig ett medelvarde.

    En enhet ar (task, etikett). Per domare samlas alla varv. Reglerna:

      * en domare vars varv inte ar eniga om GRON/ROD ar UTFALLSINSTABIL;
        enheten far da inget utfall alls hos den domaren - inte majoritetens.
      * en domare vars varv ar eniga om utfall men oense om koder ar
        KODINSTABIL.
      * utfallsoenighet raknas bara nar BADA domarna har ett stabilt utfall
        och de skiljer sig. Ar nagon instabil ar det instabiliteten som ar
        fyndet, och den blandas inte in i (a).
      * kodoenighet raknas bara nar bada har stabilt SAMMA utfall.
    """
    enheter = {}
    for r in rader:
        e = enheter.setdefault((r["task"], r["etikett"]),
                               {"tolk": [], "openplc": [],
                                "faller_pa": r.get("faller_pa") or []})
        e[r["domare"]].append(r)

    ut = {"enheter": {}, "n_kravd": n_kravd}
    for (task, etikett), e in sorted(enheter.items()):
        post = {"task": task, "etikett": etikett,
                "faller_pa": e["faller_pa"], "domare": {}}
        for namn in ("tolk", "openplc"):
            varv = sorted(e[namn], key=lambda r: r["varv"])
            utfall = [r["utfall"] for r in varv]
            koder = [tuple(sorted(r["koder"])) for r in varv]
            resultat = list(zip(utfall, koder))
            post["domare"][namn] = {
                "n": len(varv),
                "utfall_per_varv": utfall,
                "koder_per_varv": [list(k) for k in koder],
                "utfall_rakning": dict((u, utfall.count(u))
                                       for u in sorted(set(utfall))),
                "stabilt_utfall": utfall[0] if utfall and len(set(utfall)) == 1
                                  else None,
                "utfallsinstabil": len(set(utfall)) > 1,
                "kodinstabil": len(set(utfall)) == 1 and len(set(koder)) > 1,
                "instabil": len(set(resultat)) > 1,
                # VAR instabiliteten sitter: koder som fanns i nagot varv men
                # inte i alla. M-146 gissade invariantregelns fem scan; det ar
                # den har listan som avgor om gissningen haller.
                "vacklande_koder": sorted(
                    set().union(*[set(k) for k in koder])
                    - set.intersection(*[set(k) for k in koder])) if koder
                    else [],
                "sekunder_median": _median([r["sekunder"] for r in varv]),
                "omatt": len(varv) < n_kravd,
                "skal": next((r["skal"] for r in varv if r.get("skal")), None),
            }
        t = post["domare"]["tolk"]
        o = post["domare"]["openplc"]
        post["omatt"] = t["omatt"] or o["omatt"]
        # Ett DOMSFEL ar ingen dom (M-146 §6). En enhet dar nagon domare inte
        # kunde falla en dom hor varken till (a) eller (b): den ar ODOMD, och
        # den star for sig med sitt skal i stallet for att bli en oenighet om
        # gron/rod som den inte ar.
        post["odomd"] = any(u not in DOMAR
                            for u in list(t["utfall_rakning"])
                            + list(o["utfall_rakning"]))
        post["utfallsoenig"] = bool(
            not post["odomd"] and t["stabilt_utfall"] and o["stabilt_utfall"]
            and t["stabilt_utfall"] != o["stabilt_utfall"])
        post["kodoenig"] = False
        post["kodoenighet_bara_tolkfel"] = False
        if (not post["odomd"]
                and t["stabilt_utfall"] and o["stabilt_utfall"]
                and t["stabilt_utfall"] == o["stabilt_utfall"]
                and not t["instabil"] and not o["instabil"]):
            tk, ok = set(t["koder_per_varv"][0]), set(o["koder_per_varv"][0])
            if tk != ok:
                post["kodoenig"] = True
                post["bara_tolk"] = sorted(tk - ok)
                post["bara_openplc"] = sorted(ok - tk)
                # Strukturellt undantag: skillnaden bestar ENBART av koder
                # OpenPLC-domaren omojligt kan lamna.
                post["kodoenighet_bara_tolkfel"] = bool(
                    (tk - ok) and (tk - ok) == _tolkfel(tk - ok)
                    and not (ok - tk))
        # Motbevisen: foll de pa sin NAMNGIVNA brist, i varje domare?
        # `faller_pa` ar bankens egen utpekning, skriven av en manniska fore
        # korningen. Ett motbevis som ar GRONT hos en domare och ROTT hos den
        # andra ar ett fynd, inte brus.
        if etikett.startswith("motbevis:"):
            fp = set(post["faller_pa"])
            post["faller_pa_bara_tolkfel"] = bool(fp) and fp == _tolkfel(fp)
            for namn in ("tolk", "openplc"):
                d = post["domare"][namn]
                d["rott_i_alla_varv"] = bool(d["utfall_per_varv"]) and all(
                    u == "UNDERKAND" for u in d["utfall_per_varv"])
                d["gront_i_alla_varv"] = bool(d["utfall_per_varv"]) and all(
                    u == "GODKAND" for u in d["utfall_per_varv"])
                d["pa_namngiven_brist"] = bool(fp) and all(
                    fp & set(k) for k in d["koder_per_varv"])
            t_, o_ = post["domare"]["tolk"], post["domare"]["openplc"]
            post["rott_bara_hos_tolken"] = bool(
                t_["rott_i_alla_varv"] and o_["gront_i_alla_varv"])
            post["rott_bara_hos_openplc"] = bool(
                o_["rott_i_alla_varv"] and t_["gront_i_alla_varv"])
            post["gront_i_bada"] = bool(
                t_["gront_i_alla_varv"] and o_["gront_i_alla_varv"])
        ut["enheter"]["%s/%s" % (task, etikett)] = post

    poster = list(ut["enheter"].values())
    matta = [p for p in poster if not p["omatt"]]
    ut["tal"] = {
        "enheter_totalt": len(poster),
        "enheter_matta": len(matta),
        "enheter_omatta": sorted(p["task"] + "/" + p["etikett"]
                                 for p in poster if p["omatt"]),
        "enheter_odomda": sorted(p["task"] + "/" + p["etikett"]
                                 for p in matta if p["odomd"]),
        "enheter_jamforbara": sum(1 for p in matta if not p["odomd"]),
        "a_utfallsoenighet": sum(1 for p in matta if p["utfallsoenig"]),
        "b_kodoenighet": sum(1 for p in matta if p["kodoenig"]),
        "b_kodoenighet_bara_tolkfel": sum(
            1 for p in matta if p["kodoenighet_bara_tolkfel"]),
        "c_sjalvinstabil_openplc": sum(
            1 for p in matta if p["domare"]["openplc"]["instabil"]),
        "c_sjalvinstabil_openplc_utfall": sum(
            1 for p in matta if p["domare"]["openplc"]["utfallsinstabil"]),
        "c_sjalvinstabil_tolk": sum(
            1 for p in matta if p["domare"]["tolk"]["instabil"]),
        "c_sjalvinstabil_tolk_utfall": sum(
            1 for p in matta if p["domare"]["tolk"]["utfallsinstabil"]),
        "domsfel_openplc": sum(
            1 for p in matta
            if any(u not in DOMAR
                   for u in p["domare"]["openplc"]["utfall_rakning"])),
        "domsfel_tolk": sum(
            1 for p in matta
            if any(u not in DOMAR
                   for u in p["domare"]["tolk"]["utfall_rakning"])),
    }
    vack = {}
    for p in matta:
        for k in p["domare"]["openplc"]["vacklande_koder"]:
            vack[k.split(":")[0]] = vack.get(k.split(":")[0], 0) + 1
    ut["tal"]["vacklande_kodslag_openplc"] = dict(sorted(vack.items()))
    vackt = {}
    for p in matta:
        for k in p["domare"]["tolk"]["vacklande_koder"]:
            vackt[k.split(":")[0]] = vackt.get(k.split(":")[0], 0) + 1
    ut["tal"]["vacklande_kodslag_tolk"] = dict(sorted(vackt.items()))
    mb = [p for p in matta if p["etikett"].startswith("motbevis:")]
    ref = [p for p in matta if p["etikett"] == "referens"]
    ut["tal"]["motbevis"] = {
        "matta": len(mb),
        "rott_i_bada_alla_varv": sum(
            1 for p in mb if p["domare"]["tolk"]["rott_i_alla_varv"]
            and p["domare"]["openplc"]["rott_i_alla_varv"]),
        "rott_bara_hos_tolken": sorted(
            p["task"] + "/" + p["etikett"] for p in mb
            if p["rott_bara_hos_tolken"]),
        "rott_bara_hos_openplc": sorted(
            p["task"] + "/" + p["etikett"] for p in mb
            if p["rott_bara_hos_openplc"]),
        "gront_i_bada": sorted(p["task"] + "/" + p["etikett"] for p in mb
                               if p["gront_i_bada"]),
        "pa_namngiven_brist_tolk": sum(
            1 for p in mb if p["domare"]["tolk"]["pa_namngiven_brist"]),
        "pa_namngiven_brist_openplc": sum(
            1 for p in mb if p["domare"]["openplc"]["pa_namngiven_brist"]),
        "faller_pa_bara_tolkfel": sorted(
            p["task"] + "/" + p["etikett"] for p in mb
            if p.get("faller_pa_bara_tolkfel")),
    }
    ut["tal"]["referenser"] = {
        "matta": len(ref),
        "gron_i_tolken_alla_varv": sum(
            1 for p in ref
            if p["domare"]["tolk"]["stabilt_utfall"] == "GODKAND"),
        "gron_i_openplc_alla_varv": sum(
            1 for p in ref
            if p["domare"]["openplc"]["stabilt_utfall"] == "GODKAND"),
        "inte_gron_i_openplc": sorted(
            p["task"] for p in ref
            if p["domare"]["openplc"]["stabilt_utfall"] != "GODKAND"),
    }
    return ut


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else round((xs[m - 1] + xs[m]) / 2.0, 2)


# ------------------------------------------------- trasiga fixturer, mekaniskt

def fixturer():
    """Fyra fall som aggregatorn MASTE falla pa. Skrivna fore mekanismen.

    Lamnar (namn, haller, vad_som_hande).
    """
    ut = []

    def rad(task, etikett, domare, varv, utfall, koder, **extra):
        r = {"task": task, "etikett": etikett, "domare": domare, "varv": varv,
             "utfall": utfall, "koder": list(koder), "sekunder": 1.0,
             "faller_pa": []}
        r.update(extra)
        return r

    # 1. 2 av 3 grona far aldrig bli GRON.
    rader = ([rad("X-01", "referens", "tolk", v, "GODKAND", []) for v in (1, 2, 3)]
             + [rad("X-01", "referens", "openplc", 1, "GODKAND", []),
                rad("X-01", "referens", "openplc", 2, "GODKAND", []),
                rad("X-01", "referens", "openplc", 3, "UNDERKAND",
                    ["invariant:x"])])
    s = sammanstall(rader, 3)["enheter"]["X-01/referens"]
    haller = (s["domare"]["openplc"]["stabilt_utfall"] is None
              and s["domare"]["openplc"]["utfallsinstabil"]
              and not s["utfallsoenig"])
    ut.append(("2_av_3_ar_inte_gron", haller,
               "stabilt_utfall=%r utfallsinstabil=%r utfallsoenig=%r"
               % (s["domare"]["openplc"]["stabilt_utfall"],
                  s["domare"]["openplc"]["utfallsinstabil"],
                  s["utfallsoenig"])))

    # 2. Farre an n korningar => OMATT, aldrig med bland de matta.
    rader = ([rad("X-02", "referens", "tolk", v, "GODKAND", []) for v in (1, 2, 3)]
             + [rad("X-02", "referens", "openplc", 1, "GODKAND", [])])
    d = sammanstall(rader, 3)
    haller = (d["enheter"]["X-02/referens"]["omatt"]
              and d["tal"]["enheter_matta"] == 0
              and "X-02/referens" in d["tal"]["enheter_omatta"])
    ut.append(("farre_an_n_ar_omatt", haller,
               "omatt=%r matta=%d" % (d["enheter"]["X-02/referens"]["omatt"],
                                      d["tal"]["enheter_matta"])))

    # 3. Ett DOMSFEL ar aldrig ett utfall - och far aldrig rakans som enighet.
    rader = ([rad("X-03", "referens", "tolk", v, "UNDERKAND", ["flank:a"])
              for v in (1, 2, 3)]
             + [rad("X-03", "referens", "openplc", v, "DOMSFEL", [],
                    skal="riggen nere") for v in (1, 2, 3)])
    d = sammanstall(rader, 3)
    p = d["enheter"]["X-03/referens"]
    haller = (p["odomd"] and not p["utfallsoenig"] and not p["kodoenig"]
              and d["tal"]["domsfel_openplc"] == 1
              and d["tal"]["enheter_jamforbara"] == 0)
    ut.append(("domsfel_ar_inget_utfall", haller,
               "odomd=%r utfallsoenig=%r kodoenig=%r domsfel=%d jamforbara=%d"
               % (p["odomd"], p["utfallsoenig"], p["kodoenig"],
                  d["tal"]["domsfel_openplc"],
                  d["tal"]["enheter_jamforbara"])))

    # 4. En kodoenighet som BARA ar tolkfel:* ar det strukturella undantaget.
    rader = ([rad("X-04", "referens", "tolk", v, "UNDERKAND",
                  ["punktkrav:a", "tolkfel:b"]) for v in (1, 2, 3)]
             + [rad("X-04", "referens", "openplc", v, "UNDERKAND",
                    ["punktkrav:a"]) for v in (1, 2, 3)])
    d = sammanstall(rader, 3)
    p = d["enheter"]["X-04/referens"]
    haller = (p["kodoenig"] and p["kodoenighet_bara_tolkfel"]
              and d["tal"]["b_kodoenighet_bara_tolkfel"] == 1)
    # ... och en kodoenighet som INTE bara ar tolkfel far inte flaggas sa.
    rader2 = ([rad("X-05", "referens", "tolk", v, "UNDERKAND",
                   ["tolkfel:b", "flank:c"]) for v in (1, 2, 3)]
              + [rad("X-05", "referens", "openplc", v, "UNDERKAND",
                     ["openplc:skriver_egen_ingang"]) for v in (1, 2, 3)])
    p2 = sammanstall(rader2, 3)["enheter"]["X-05/referens"]
    haller = haller and p2["kodoenig"] and not p2["kodoenighet_bara_tolkfel"]
    ut.append(("tolkfelundantaget_raknas_for_sig", haller,
               "bara_tolkfel=%r (kontroll: %r)"
               % (p["kodoenighet_bara_tolkfel"],
                  p2["kodoenighet_bara_tolkfel"])))
    return ut


# ---------------------------------------------------------------------- main

def _skriv_sammanstallning(args):
    fix = fixturer()
    for namn, haller, vad in fix:
        print("fixtur %-34s -> %s  (%s)"
              % (namn, "HALLER" if haller else "HALLER INTE", vad))
    rader = las_rader(args.sammanstall)
    d = sammanstall(rader, args.n)
    d["fixturer"] = [{"namn": n, "haller": h, "vad": v} for n, h, v in fix]
    d["korningar"] = len(rader)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".",
                    exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1, ensure_ascii=False)
    if args.tabell:
        tabell, _per = markdowntabell(d)
        print(tabell)
        print("")
    t = d["tal"]
    print("\n%d korningar, %d enheter (%d matta vid n=%d, %d omatta, "
          "%d odomda -> %d jamforbara)"
          % (d["korningar"], t["enheter_totalt"], t["enheter_matta"],
             args.n, len(t["enheter_omatta"]), len(t["enheter_odomda"]),
             t["enheter_jamforbara"]))
    print("(a) utfallsoenighet    : %d" % t["a_utfallsoenighet"])
    print("(b) kodoenighet        : %d  (varav bara tolkfel:*: %d)"
          % (t["b_kodoenighet"], t["b_kodoenighet_bara_tolkfel"]))
    print("(c) sjalvinstabilitet  : openplc %d (varav utfall %d), tolk %d "
          "(varav utfall %d)"
          % (t["c_sjalvinstabil_openplc"], t["c_sjalvinstabil_openplc_utfall"],
             t["c_sjalvinstabil_tolk"], t["c_sjalvinstabil_tolk_utfall"]))
    print("    vacklande kodslag (openplc): %s"
          % (t["vacklande_kodslag_openplc"] or "inga"))
    r, m = t["referenser"], t["motbevis"]
    print("referenser grona i alla varv: tolk %d/%d, openplc %d/%d %s"
          % (r["gron_i_tolken_alla_varv"], r["matta"],
             r["gron_i_openplc_alla_varv"], r["matta"],
             ("(inte gron i openplc: %s)" % ", ".join(r["inte_gron_i_openplc"]))
             if r["inte_gron_i_openplc"] else ""))
    print("motbevis: %d matta, roda i bada alla varv %d; rott BARA hos tolken "
          "%d, BARA hos openplc %d, gront i bada %d"
          % (m["matta"], m["rott_i_bada_alla_varv"],
             len(m["rott_bara_hos_tolken"]), len(m["rott_bara_hos_openplc"]),
             len(m["gront_i_bada"])))
    print("motbevis pa sin NAMNGIVNA brist: tolk %d, openplc %d "
          "(strukturellt omojliga for openplc: %d)"
          % (m["pa_namngiven_brist_tolk"], m["pa_namngiven_brist_openplc"],
             len(m["faller_pa_bara_tolkfel"])))
    fel = []
    if not t["enheter_matta"]:
        fel.append("noll matta enheter")
    for namn, haller, vad in fix:
        if not haller:
            fel.append("fixturen %s holl inte: %s" % (namn, vad))
    if fel:
        print("\nFALLER: " + "; ".join(fel))
        return 1
    return 0


def markdowntabell(d):
    """Per uppgift, i markdown. n redovisas alltid som x av n, aldrig som ett
    medelvarde: en uppgift som ar gron i 2 av 3 ar inte gron."""
    per = {}
    for nyckel, p in d["enheter"].items():
        t = per.setdefault(p["task"], {"enheter": 0, "a": 0, "b": 0,
                                       "c_op": 0, "c_tolk": 0, "odomd": 0,
                                       "omatt": 0, "namn_a": [], "namn_b": [],
                                       "namn_c": []})
        t["enheter"] += 1
        kort = p["etikett"].replace("motbevis:", "")
        if p["omatt"]:
            t["omatt"] += 1
            continue
        if p["odomd"]:
            t["odomd"] += 1
        if p["utfallsoenig"]:
            t["a"] += 1
            t["namn_a"].append(kort)
        if p["kodoenig"]:
            t["b"] += 1
            t["namn_b"].append(kort)
        if p["domare"]["openplc"]["instabil"]:
            t["c_op"] += 1
            t["namn_c"].append(kort)
        if p["domare"]["tolk"]["instabil"]:
            t["c_tolk"] += 1
    rader = ["| uppgift | enheter | (a) utfall | (b) koder | (c) openplc "
             "oense m sig sjalv | (c) tolk | odomda |",
             "|---|---|---|---|---|---|---|"]
    for task in sorted(per):
        t = per[task]
        rader.append("| %s | %d | %d | %d | %d | %d | %d |"
                     % (task, t["enheter"], t["a"], t["b"], t["c_op"],
                        t["c_tolk"], t["odomd"]))
    return "\n".join(rader), per


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uppgifter", nargs="+", default=None)
    ap.add_argument("--skiva", default=None,
                    help="i/N: packa banken i N skivor efter matt kostnad "
                         "(M-146) och kor skiva i")
    ap.add_argument("--n", type=int, default=3,
                    help="antal korningar per enhet och domare (>= 3, M-146)")
    ap.add_argument("--bas", default=None)
    ap.add_argument("--endpoint", default=None)
    ap.add_argument("--byggkatalog", default="/tmp/a3_bygg")
    ap.add_argument("--jsonl", default=None)
    ap.add_argument("--sammanstall", nargs="+", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--lista-skivor", type=int, default=None)
    ap.add_argument("--tabell", action="store_true",
                    help="skriv per-uppgift-tabellen i markdown")
    a = ap.parse_args(argv)

    if a.lista_skivor:
        for i, skiva in enumerate(packa(alla_uppgifter(), a.lista_skivor), 1):
            print("%2d: %6.0f s  %s"
                  % (i, sum(kostnad(t) * antal_enheter(t) for t in skiva),
                     " ".join(skiva)))
        return 0
    if a.sammanstall:
        return _skriv_sammanstallning(a)
    if not a.jsonl:
        ap.error("--jsonl kravs i sveplage")
    if a.n < 3:
        ap.error("n < 3: M-146 matte att OpenPLC-domaren inte ar "
                 "deterministisk vid n = 1")
    if a.skiva:
        i, N = (int(x) for x in a.skiva.split("/"))
        a.uppgifter = packa(alla_uppgifter(), N)[i - 1]
    elif not a.uppgifter:
        a.uppgifter = alla_uppgifter()
    print("skiva: %s" % " ".join(a.uppgifter))
    return svep(a)


def antal_enheter(task_id):
    post = las_uppgift(task_id)
    return 1 + len((post["facit_spar"].get("motbevis") or []))


def packa(uppgifter, n_skivor):
    """Langsta-forst i den lattaste skivan. Ingen dom hanger pa packningen."""
    skivor = [[] for _ in range(n_skivor)]
    vikt = [0.0] * n_skivor
    for task_id in sorted(uppgifter,
                          key=lambda t: -kostnad(t) * antal_enheter(t)):
        i = vikt.index(min(vikt))
        skivor[i].append(task_id)
        vikt[i] += kostnad(task_id) * antal_enheter(task_id)
    return skivor


if __name__ == "__main__":
    raise SystemExit(main())
