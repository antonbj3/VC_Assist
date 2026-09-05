# -*- coding: utf-8 -*-
"""M-146 (ko A, punkt A2): domaren som domer ur OpenPLC-runtime.

`docs/spec/85_bankkontraktet.md` §2: ett facit far aldrig komma ur koden som
doms. `bank/domare.py` domer bankens sparfacit genom var EGEN ST-tolk, alltsa
ar tolken bade den som provas och den som domer. `bank/domare_openplc.py`
domer samma sparfacit genom OpenPLC Runtime v4 - en motor utanfor var kod,
den produkten faktiskt anvander.

Korningen provar fyra saker, och den andra ar den som bar punkten:

  1. REFERENSEN AR GRON I BADA DOMARNA. Uppgiftens egen referenslosning ar
     gron hos `domare.py`. Ar den inte gron ocksa hos OpenPLC-domaren ar
     antingen domaren trasig eller sa ar det en verklig oenighet mellan
     motorerna - och da ska bristkoderna sta i rapporten, inte tigas ihjal.
  2. TRASIG FIXTUR (skriven och sedd rod FORE mekanismen, se M-146 §2):
     en dubblerad CASE-etikett i uppgiftens referens. Var tolk sager GRON,
     STruC++:s frontend sager OK, och OpenPLC:s g++ sager
     `duplicate case value`. Den MASTE bli UNDERKAND med
     `openplc:kompilerar_inte` - inte gron, och inte ett korningsfel
     maskerat som ett underkannande.
  3. ETT KORNINGSFEL AR ALDRIG EN DOM. Samma losning domd mot en runtime som
     inte finns ska ge Domsfel i klartext, aldrig en Dom. En rigg som ar nere
     far inte kunna se ut som en losning som ar fel.
  4. TOLERANSEN MOT SIN EGEN MATNING. Domaren lamnar per punktkrav hur manga
     scan efter `t_ms` det vantade vardet forst sags. TOLERANS_SCAN = 4 ar
     harledd ur M-20 (2 scan svarstid) + M-108 (2 scan kanalfas); den har
     korningen skriver ut den uppmatta fordelningen sa att talet gar att
     prova mot verkligheten i stallet for att tros pa.

Med `--motbevis` doms ocksa varje uppgifts motbevis i bada domarna. Det ar
matningen ko A3 behover: var de tva domarna ar oense, per uppgift.

Kors (tung: realtid, ~20-40 s per uppgift och losning):

    nice -n 19 ionice -c3 python3 tests/protocol/kor_A2_domare_openplc.py \\
        --byggkatalog /tmp/a2_bygg --json /tmp/a2.json

Riggen: OpenPLC Runtime v4 pa VC_ASSIST_OPENPLC_BAS (standard
https://127.0.0.1:18443, containern vcassist-openplc-v4) med OPC UA pa
VC_ASSIST_OPENPLC_ENDPOINT. STruC++ ur VC_ASSIST_STRUCPP_PAKET.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare as D                      # noqa: E402
import domare_openplc as DO             # noqa: E402

BANKPOST = {
    "pastar": (
        "Bankens sparfacit gar att doma genom OpenPLC Runtime v4 i stallet "
        "for genom var egen ST-tolk, med samma domarmekanik: referensen ar "
        "gron i bada domarna, en losning OpenPLC vagrar kompilera blir rod, "
        "och ett korningsfel blir ett Domsfel och aldrig en dom."),
    "under_prov": ("bank/domare_openplc.py",),
    "facit": (
        "Uppgiftens egna sparfacit (punktkrav, invarianter, flankrakning), "
        "skrivet av en manniska fore korningen, last mot OpenPLC:s korning"),
    "facitkalla": (
        "OpenPLC Runtime v4.2.1 (oberoende tredje motor) + bankens "
        "manniskoskrivna sparfacit"),
    "facitkalla_filer": ("bank/uppgifter",),
    "trasiga_fall": (
        "dubblerad CASE-etikett: var tolk gron, OpenPLC:s g++ "
        "'duplicate case value' - MASTE bli openplc:kompilerar_inte",
        "samma losning mot en runtime som inte finns MASTE ge Domsfel, "
        "aldrig en Dom",
        "en referens som inte blir gron rapporteras med bristkoder, "
        "aldrig som en lyckad korning",
        "noll domda uppgifter ger returkod != 0",
    ),
    "kraver": ("openplc", "strucpp"),
    "matningar": ("M-146",),
}

# Uppgifterna som doms som standard. Valda pa kortast realtid i sparfacit
# (P-05 6,5 s, L-01 9,4 s, P-07 10,8 s), inte pa utfall: domaren ska provas
# dar den kostar minst, och alla tre ar GRONA hos domare.py fore korningen.
STANDARDUPPGIFTER = ("P-05", "L-01", "P-07")

# En port dar ingenting lyssnar. Anvands for utfall 3: en rigg som ar nere.
DOD_BAS = "https://127.0.0.1:18299"


def las_uppgift(task_id):
    with open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % task_id),
              "r", encoding="utf-8") as f:
        return json.load(f)


def dubblerad_case(st_text):
    """Trasig fixtur: en CASE-etikett som redan finns.

    Var ST-tolk tar forsta traffen och bryr sig inte; STruC++:s frontend
    skriver ut bada; g++ faller pa `duplicate case value`. Lamnar None nar
    uppgiftens referens inte har ett CASE att dubblera - da ar den uppgiften
    inte en barare av fixturen, och det sags rakt ut i stallet for att
    fixturen tyst hoppas over.
    """
    rader = st_text.splitlines()
    etiketter = [i for i, rad in enumerate(rader)
                 if rad.strip().endswith(":")
                 and rad.strip()[:-1].strip().isdigit()]
    if len(etiketter) < 2:
        return None
    # HELA den forsta grenen kopieras in strax fore den sista etiketten.
    #
    # Tva enklare varianter provades och forkastades 2026-09-05, bada for att
    # de andrade BETEENDET och inte bara kompilerbarheten - da hade fixturen
    # matt fel storhet:
    #   * bara etikettraden, med tom kropp: var tolk tar forsta traffen, och
    #     en tom gren fore den riktiga slukade den (P-05, L-01, P-07, T-01
    #     blev roda pa punktkrav).
    #   * etikettraden plus en enda rad ur nasta gren: kapade ett IF mitt i
    #     och gav tolkfel.
    # En hel gren ar en komplett satslista, och eftersom kopian ligger EFTER
    # originalet nar den aldrig var tolks utvardering. Matt gron i var tolk pa
    # atta uppgifter (P-05, L-01, P-07, T-01, A-05, T-05, L-06, L-07).
    block = rader[etiketter[0]:etiketter[1]]
    sista = etiketter[-1]
    return "\n".join(rader[:sista] + block + rader[sista:]) + "\n"


def _sammanfatta_matpunkter(dom):
    off = [m["offset_scan"] for m in getattr(dom, "matpunkter", [])
           if m["offset_scan"] is not None]
    if not off:
        return {"n": 0}
    return {"n": len(off), "min": min(off), "max": max(off),
            "median": statistics.median(off),
            "fordelning": dict((str(o), off.count(o)) for o in sorted(set(off)))}


def _dom_par(post, st_text, rigg, byggkatalog, etikett):
    """Domer samma text i bada domarna. Lamnar en rad, aldrig ett undantag."""
    rad = {"etikett": etikett}
    try:
        vd = D.dom(post, st_text)
        rad["tolk"] = "GODKAND" if vd.godkand else "UNDERKAND"
        rad["tolk_koder"] = sorted(vd.koder)
    except D.Domsfel as fel:
        rad["tolk"] = "DOMSFEL"
        rad["tolk_skal"] = str(fel)
        rad["tolk_koder"] = []
    t = time.time()
    try:
        od = DO.dom(post, st_text, rigg=rigg, byggkatalog=byggkatalog)
        rad["openplc"] = "GODKAND" if od.godkand else "UNDERKAND"
        rad["openplc_koder"] = sorted(od.koder)
        rad["openplc_text"] = od.text()[:4000]
        rad["matpunkter"] = _sammanfatta_matpunkter(od)
    except D.Domsfel as fel:
        rad["openplc"] = "DOMSFEL"
        rad["openplc_skal"] = str(fel)[:2000]
        rad["openplc_koder"] = []
    rad["sekunder"] = round(time.time() - t, 1)
    rad["oense"] = rad["tolk"] != rad["openplc"] or (
        sorted(rad.get("tolk_koder") or []) != sorted(rad.get("openplc_koder") or []))
    return rad


def kor(args):
    rigg = DO.Rigg(bas=args.bas, endpoint=args.endpoint)
    rigg.kontrollera()
    ut = {"rigg": {"bas": rigg.bas, "endpoint": rigg.endpoint,
                   "strucpp_paket": rigg.strucpp_paket,
                   "runtime_include": rigg.runtime_include,
                   "tolerans_scan": DO.TOLERANS_SCAN,
                   "scan_ms": DO.SCAN_MS},
          "uppgifter": {}, "fixturer": {}}
    os.makedirs(args.byggkatalog, exist_ok=True)

    for task_id in args.uppgifter:
        post = las_uppgift(task_id)
        if not post.get("facit_spar"):
            raise SystemExit("%s har inget sparfacit" % task_id)
        rader = [_dom_par(post, post["facit_spar"]["referens"], rigg,
                          os.path.join(args.byggkatalog, task_id, "referens"),
                          "referens")]
        print("%-6s referens  tolk=%s openplc=%s (%.1f s) %s"
              % (task_id, rader[0]["tolk"], rader[0]["openplc"],
                 rader[0]["sekunder"], rader[0].get("openplc_koder") or ""))
        sys.stdout.flush()
        if args.motbevis:
            for mb in post["facit_spar"].get("motbevis") or []:
                r = _dom_par(post, mb["st"], rigg,
                             os.path.join(args.byggkatalog, task_id,
                                          "mb_" + mb["namn"]),
                             "motbevis:" + mb["namn"])
                r["faller_pa"] = list(mb.get("faller_pa") or [])
                rader.append(r)
                print("%-6s %-28s tolk=%s openplc=%s (%.1f s)"
                      % (task_id, mb["namn"], r["tolk"], r["openplc"],
                         r["sekunder"]))
                sys.stdout.flush()
        ut["uppgifter"][task_id] = rader

    # --- trasig fixtur: OpenPLC vagrar kompilera, var tolk gor det inte ---
    fixturuppgift = args.uppgifter[0]
    post = las_uppgift(fixturuppgift)
    trasig = dubblerad_case(post["facit_spar"]["referens"])
    if trasig is None:
        raise SystemExit("%s:s referens har inget CASE att dubblera; valj en "
                         "uppgift som bar fixturen" % fixturuppgift)
    fix = _dom_par(post, trasig, rigg,
                   os.path.join(args.byggkatalog, "fixtur_dubblerad_case"),
                   "fixtur:dubblerad_case")
    fix["kravs"] = "tolk GODKAND, openplc UNDERKAND med openplc:kompilerar_inte"
    fix["haller"] = (fix["tolk"] == "GODKAND"
                     and fix["openplc"] == "UNDERKAND"
                     and "openplc:kompilerar_inte" in fix["openplc_koder"])
    ut["fixturer"]["dubblerad_case"] = fix
    print("fixtur dubblerad_case: tolk=%s openplc=%s %s -> %s"
          % (fix["tolk"], fix["openplc"], fix["openplc_koder"],
             "HALLER" if fix["haller"] else "HALLER INTE"))
    sys.stdout.flush()

    # --- korningsfel ar aldrig en dom ---
    dod = DO.Rigg(bas=args.dod_bas, endpoint=rigg.endpoint)
    riggfel = {"kravs": "Domsfel, aldrig en Dom"}
    try:
        d = DO.dom(post, post["facit_spar"]["referens"], rigg=dod,
                   byggkatalog=os.path.join(args.byggkatalog, "riggen_nere"))
        riggfel["utfall"] = "DOM(%s)" % ("GODKAND" if d.godkand
                                         else ",".join(d.koder))
        riggfel["haller"] = False
    except D.Domsfel as fel:
        riggfel["utfall"] = "DOMSFEL"
        riggfel["skal"] = str(fel)[:600]
        riggfel["haller"] = True
    ut["fixturer"]["riggen_nere"] = riggfel
    print("fixtur riggen_nere: %s -> %s"
          % (riggfel["utfall"], "HALLER" if riggfel["haller"] else "HALLER INTE"))
    sys.stdout.flush()

    # --- sammanfattning ---
    alla = [r for rader in ut["uppgifter"].values() for r in rader]
    referenser = [r for r in alla if r["etikett"] == "referens"]
    ut["sammanfattning"] = {
        "domda_texter": len(alla),
        "referenser_gron_i_tolken": sum(1 for r in referenser
                                        if r["tolk"] == "GODKAND"),
        "referenser_gron_i_openplc": sum(1 for r in referenser
                                         if r["openplc"] == "GODKAND"),
        "oense": sorted(r["etikett"] + "@" + t
                        for t, rader in ut["uppgifter"].items()
                        for r in rader if r["oense"]),
        "matpunkter": _slagen_ihop([r.get("matpunkter") for r in alla]),
    }
    return ut


def _slagen_ihop(sammanfattningar):
    tot = {}
    n = 0
    for s in sammanfattningar:
        if not s or not s.get("n"):
            continue
        n += s["n"]
        for k, v in (s.get("fordelning") or {}).items():
            tot[k] = tot.get(k, 0) + v
    if not n:
        return {"n": 0}
    return {"n": n, "fordelning": dict(sorted(tot.items(), key=lambda x: int(x[0]))),
            "max": max(int(k) for k in tot)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--uppgifter", nargs="+", default=list(STANDARDUPPGIFTER))
    ap.add_argument("--bas", default=None,
                    help="OpenPLC REST-bas (standard: VC_ASSIST_OPENPLC_BAS)")
    ap.add_argument("--endpoint", default=None,
                    help="OPC UA-endpoint (standard: VC_ASSIST_OPENPLC_ENDPOINT)")
    ap.add_argument("--dod-bas", default=DOD_BAS,
                    help="bas dar ingenting lyssnar, for riggen-nere-fixturen")
    ap.add_argument("--byggkatalog", default="/tmp/a2_bygg")
    ap.add_argument("--motbevis", action="store_true",
                    help="dom ocksa varje uppgifts motbevis i bada domarna")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    ut = kor(a)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(ut, f, indent=1, ensure_ascii=False)
    s = ut["sammanfattning"]
    print("\n%d texter domda i bada domarna; %d/%d referenser grona i tolken, "
          "%d/%d i OpenPLC" % (s["domda_texter"],
                               s["referenser_gron_i_tolken"], len(ut["uppgifter"]),
                               s["referenser_gron_i_openplc"], len(ut["uppgifter"])))
    print("oense: %s" % (", ".join(s["oense"]) or "inga"))
    print("punktkravens uppmatta offset (scan): %s" % (s["matpunkter"],))

    # Fail-closed: noll domda texter, en fixtur som inte haller, eller en
    # referens som inte ar gron i BADA domarna ar ett rott utfall. En korning
    # som inte kan falla mater ingenting.
    fel = []
    if not s["domda_texter"]:
        fel.append("noll domda texter")
    for namn, f in ut["fixturer"].items():
        if not f.get("haller"):
            fel.append("fixturen %s holl inte: %s"
                       % (namn, f.get("utfall") or f.get("openplc_koder")))
    if s["referenser_gron_i_openplc"] != len(ut["uppgifter"]):
        fel.append("%d av %d referenser ar inte grona i OpenPLC-domaren"
                   % (len(ut["uppgifter"]) - s["referenser_gron_i_openplc"],
                      len(ut["uppgifter"])))
    if fel:
        print("\nFALLER: " + "; ".join(fel))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
