# -*- coding: utf-8 -*-
"""M-173 (ko A, punkt A9): omstarten mitt i sparet, och RETAIN.

`RETAIN` betyder att en variabel behaller sitt varde over en VARM omstart.
Kvalificeraren fanns i vart lager pa tre stallen - lexern, modellen och
validatorn - men ingenstans i KORNINGEN: tolken hade inget omstartsbegrepp
alls, sa `VAR RETAIN` var en etikett utan verkan och en uppgift kunde inte
skilja en variabel som overlever stromavbrottet fran en som inte gor det.

Punkt A9 byggde begreppet (`tolk.varmstart()` / `tolk.kallstart()`, se
`svc/vc_assist_svc/st/tolk.py`) och den har korningen mater vad det betyder
for banken:

  1. Hur manga av bankens losningar deklarerar over huvud taget RETAIN?
  2. Hur manga uppgifter domer ANNORLUNDA med en omstart mitt i sparet?
  3. Skiljer varmstart och kallstart at nagonstans i banken?

Domarmekaniken ar INTE en egen kopia: den ar
`kor_A4_skanncykeln.dom_vid_scan`, samma funktion som M-166 anvande, med
`omstart_ms` satt. Tva domarmekaniker som ska vara lika men ar tva kodstycken
glider isar utan att nagon ser det.

## De tre trasiga fallen

1. **Sjalvkontrollen** (arvd ur M-166): utan omstart maste harnessen ge
   bit-identiskt utfall och bristkodsmangd som `bank/domare.py`.
2. **RETAIN-fixturen**, handskriven och UTANFOR banken: samma logik, samma
   spar, en enda skillnad - `VAR RETAIN` mot `VAR`. Den retentiva versionen
   MASTE overleva varmstarten (GRON) och den flyktiga MASTE falla (ROD). Ger
   de samma dom ar omstartsbegreppet en attrapp och korningen faller.
3. **Kallstartskontrollen**: samma retentiva fixtur MASTE falla vid
   KALLstart. En "varmstart" som beter sig som en kallstart, eller tvartom,
   ar inte ett omstartsbegrepp.

Kors (rent CPU-arbete, ingen rigg och ingen docker):

    nice -n 19 ionice -c3 python3 tests/protocol/kor_A9_omstarten.py \\
        --jsonl docs/matningar/radata/m173_svep.jsonl \\
        --json docs/matningar/radata/m173_sammanstallning.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
for _p in (_HAR, os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

BANKPOST = {
    "pastar": (
        "Bankens uppgifter forutsatter tyst att PLC:n aldrig startar om mitt i "
        "ett forlopp: antalet losningar som deklarerar RETAIN och antalet "
        "uppgifter vars dom andras av en varmstart mitt i sparet ar bada "
        "matta tal per uppgift, och skillnaden mellan varmstart och kallstart "
        "ar matt for sig."),
    "under_prov": ("bank/uppgifter", "svc/vc_assist_svc/st/tolk.py"),
    "facit": (
        "IEC 61131-3:s omstartsbegrepp: vid en varm start behaller variabler "
        "deklarerade RETAIN sitt varde, allt annat far sitt initialvarde; vid "
        "en kall start aterstalls ocksa de retentiva. Handskriven fixtur "
        "utanfor banken dar den enda skillnaden mellan tva losningar ar "
        "kvalificeraren RETAIN."),
    "facitkalla": (
        "handskriven RETAIN-fixtur i korningen sjalv, med facit raknat for "
        "hand fore korningen - ligger utanfor bank/uppgifter och utanfor "
        "tolken"),
    "facitkalla_filer": (),
    "trasiga_fall": (
        "RETAIN-fixturen: den retentiva versionen MASTE bli GRON och den "
        "flyktiga ROD over samma varmstart; samma dom betyder att "
        "omstartsbegreppet ar en attrapp",
        "kallstartskontrollen: den retentiva versionen MASTE falla vid "
        "KALLstart - annars ar varmstart och kallstart samma sak",
        "sjalvkontrollen ur M-166: utan omstart maste harnessen doma "
        "bit-identiskt med bank/domare.py",
        "noll matta enheter ger returkod != 0",
    ),
    "kraver": ("inget",),
    "matningar": ("M-173", "M-166"),
}

import domare as D                            # noqa: E402
import kor_A4_skanncykeln as A4               # noqa: E402
from vc_assist_svc.st import lasare as _lasare  # noqa: E402

SCAN_MS = 20.0                                 # M-20: OpenPLC v4:s scanperiod.

# Var i sekvensen omstarten laggs, som andel av sekvensens langd. "Mitt i
# sparet" ar 0,5; 0,25 och 0,75 finns for att ett noll-resultat vid EN punkt
# inte ska laesas som "banken talar omstarter".
ANDELAR = (0.25, 0.50, 0.75)


# --------------------------------------------------------- RETAIN-fixturen
#
# Samma logik, samma spar, EN skillnad: `VAR RETAIN` mot `VAR`.
#
# Stationen raknar detaljer genom en fotocell och far inte slappa ut en pall
# forran fyra har passerat. Facit begar PLT_FULL vid 900 ms, efter fyra
# pulser. Omstarten ligger vid 500 ms, mitt mellan andra och tredje pulsen.
#
# Rakningen for hand, fore korningen:
#   pulser vid 100, 300, 700, 900 ms (RISE pa PRT_PRS).
#   varmstart vid 500 ms.
#   RETAIN:  raknaren star pa 2 over omstarten, nar 4 vid 900 ms -> PLT_FULL.
#   VAR:     raknaren nollas, nar 2 vid 900 ms -> ingen PLT_FULL.
# Skillnaden ar alltsa inte en tidsmarginal utan tva olika varden.

_FIXTURKROPP = """
det(CLK := PRT_PRS);
IF det.Q THEN
    antal := antal + 1;
END_IF;
PLT_FULL := antal >= 4;
END_PROGRAM
"""

FIXTUR_RETAIN = ("PROGRAM Racknaren\nVAR RETAIN\n  antal : INT := 0;\n"
                 "END_VAR\nVAR\n  det : R_TRIG;\nEND_VAR\n" + _FIXTURKROPP)
FIXTUR_FLYKTIG = ("PROGRAM Racknaren\nVAR\n  antal : INT := 0;\n"
                  "  det : R_TRIG;\nEND_VAR\n" + _FIXTURKROPP)

RETAINFALLET = {
    "task_id": "RETAIN-KONTROLL",
    "control": {"signals": [
        {"name": "PRT_PRS", "type": "bool", "dir": "in"},
        {"name": "PLT_FULL", "type": "bool", "dir": "out"},
    ]},
    "facit_spar": {
        "scan_ms": 20,
        "referens": FIXTUR_RETAIN,
        "sekvenser": [{
            "id": "fyra_detaljer_med_stromavbrott",
            "steg": [
                {"t_ms": 100, "satt": {"PRT_PRS": True}, "krav": {}},
                {"t_ms": 200, "satt": {"PRT_PRS": False}, "krav": {}},
                {"t_ms": 300, "satt": {"PRT_PRS": True}, "krav": {}},
                {"t_ms": 400, "satt": {"PRT_PRS": False},
                 "krav": {"PLT_FULL": False},
                 "varfor": "tva av fyra; pallen ar inte full"},
                {"t_ms": 700, "satt": {"PRT_PRS": True}, "krav": {}},
                {"t_ms": 800, "satt": {"PRT_PRS": False}, "krav": {}},
                {"t_ms": 900, "satt": {"PRT_PRS": True},
                 "krav": {"PLT_FULL": True},
                 "varfor": "fjarde detaljen; pallen ar full"},
            ],
        }],
        "flanker": [], "invarianter": [], "motbevis": [],
    },
}
FIXTURENS_OMSTART_MS = 500.0


def retainfixturen():
    """(retentiv_dom, flyktig_dom, retentiv_kallstart). Alla tre behovs."""
    post = RETAINFALLET
    retentiv, _ = A4.dom_vid_scan(post, FIXTUR_RETAIN, SCAN_MS,
                                  omstart_ms=(FIXTURENS_OMSTART_MS,))
    flyktig, _ = A4.dom_vid_scan(post, FIXTUR_FLYKTIG, SCAN_MS,
                                 omstart_ms=(FIXTURENS_OMSTART_MS,))
    kall, _ = A4.dom_vid_scan(post, FIXTUR_RETAIN, SCAN_MS,
                              omstart_ms=(FIXTURENS_OMSTART_MS,), kall=True)
    return retentiv, flyktig, kall


# ------------------------------------------------------------- RETAIN i banken

def retain_i_losning(st_text):
    """Namnen som star i ett `VAR RETAIN`-block, eller [] . Aldrig regex:
    ordet RETAIN kan sta i en kommentar."""
    try:
        enhet = _lasare.las(st_text)
    except Exception:
        return None                    # gar inte att lasa; raknas for sig
    namn = []
    for pou in enhet.pouer:
        for block in pou.block:
            if "RETAIN" in getattr(block, "kvalificerare", ()):
                namn.extend(d.namn for d in block.deklarationer)
    return namn


# ------------------------------------------------------------------- svepet

def omstartstider(post):
    """{sekvens-id: [tider]} - en per andel, snappad till scanrutnatet."""
    ut = {}
    for sekv in post["facit_spar"]["sekvenser"]:
        langd = max(float(s["t_ms"]) for s in sekv["steg"])
        tider = []
        for andel in ANDELAR:
            t = round(langd * andel / SCAN_MS) * SCAN_MS
            if t > 0 and t not in tider:
                tider.append(t)
        ut[sekv["id"]] = tider
    return ut


def svep(args):
    print("--- trasiga fallen ---")
    retentiv, flyktig, kall = retainfixturen()
    print("  RETAIN-fixtur, varmstart vid %.0f ms:" % FIXTURENS_OMSTART_MS)
    print("    VAR RETAIN antal -> %s %s"
          % ("GODKAND" if retentiv.godkand else "UNDERKAND",
             ",".join(sorted(retentiv.koder))))
    print("    VAR        antal -> %s %s"
          % ("GODKAND" if flyktig.godkand else "UNDERKAND",
             ",".join(sorted(flyktig.koder))))
    print("    VAR RETAIN vid KALLSTART -> %s %s"
          % ("GODKAND" if kall.godkand else "UNDERKAND",
             ",".join(sorted(kall.koder))))
    fel = 0
    if not retentiv.godkand:
        print("FIXTUREN FOLL: den retentiva versionen overlevde inte "
              "varmstarten. RETAIN har ingen verkan.")
        fel = 1
    if flyktig.godkand:
        print("FIXTUREN FOLL: den FLYKTIGA versionen overlevde ocksa. "
              "Omstarten nollstaller ingenting - begreppet ar en attrapp.")
        fel = 1
    if kall.godkand:
        print("KALLSTARTSKONTROLLEN FOLL: den retentiva versionen overlevde "
              "en KALLstart. Varmstart och kallstart ar samma sak.")
        fel = 1
    if fel:
        raise SystemExit("trasiga fallet foll; svepet kors inte")
    print("  omstartsbegreppet skiljer RETAIN fran flyktigt, och varm fran kall\n")

    uppgifter = args.uppgifter.split(",") if args.uppgifter \
        else A4.alla_uppgifter()

    print("--- sjalvkontrollen (M-166): utan omstart = bank/domare.py ---")
    avvikelser = A4.sjalvkontroll(uppgifter)
    print("  %d avvikelser" % len(avvikelser))
    if avvikelser:
        for a in avvikelser[:10]:
            print("  %s" % a["enhet"])
        raise SystemExit("SJALVKONTROLLEN FOLL; svepet hade matt harnessen")
    print()

    ut = open(args.jsonl, "a", encoding="utf-8") if args.jsonl else None
    rader = []
    retainkarta = {}
    for task_id in uppgifter:
        post = A4.las_uppgift(task_id)
        for etikett, st_text in A4.enheter_for(post):
            retainkarta["%s/%s" % (task_id, etikett)] = retain_i_losning(st_text)
            for lage in ["ingen"] + ["%.2f" % a for a in ANDELAR] + ["kall"]:
                if lage == "ingen":
                    tid = ()
                    kall_flagga = False
                else:
                    # "kall" kor EXAKT samma tider som "0.50" - annars jamfor
                    # man tva olika sparbrott och inte varm mot kall.
                    andel = 0.50 if lage == "kall" else float(lage)
                    kall_flagga = (lage == "kall")
                    tid = tuple(sorted(set(
                        round(max(float(s["t_ms"]) for s in sekv["steg"])
                              * andel / SCAN_MS) * SCAN_MS
                        for sekv in post["facit_spar"]["sekvenser"])))
                    tid = tuple(t for t in tid if t > 0)
                try:
                    d, mat = A4.dom_vid_scan(post, st_text, SCAN_MS,
                                             omstart_ms=tid, kall=kall_flagga)
                    rad = {"task": task_id, "etikett": etikett, "lage": lage,
                           "omstart_ms": list(tid),
                           "utfall": "GODKAND" if d.godkand else "UNDERKAND",
                           "koder": sorted(d.koder),
                           "omstarter": mat.get("omstarter", 0)}
                except D.Domsfel as fel:
                    rad = {"task": task_id, "etikett": etikett, "lage": lage,
                           "omstart_ms": list(tid), "utfall": "DOMSFEL",
                           "koder": [], "skal": str(fel)[:600]}
                rader.append(rad)
                if ut:
                    ut.write(json.dumps(rad, ensure_ascii=False) + "\n")
                    ut.flush()
                    os.fsync(ut.fileno())
        print("  %-6s klar" % task_id)
    if ut:
        ut.close()
    return sammanstall(rader, retainkarta, args)


# ------------------------------------------------------------ sammanstallning

def sammanstall(rader, retainkarta, args):
    bas = dict(((r["task"], r["etikett"]), r) for r in rader
               if r["lage"] == "ingen")
    per_uppgift = {}
    lagen = []
    for r in rader:
        if r["lage"] == "ingen":
            continue
        if r["lage"] not in lagen:
            lagen.append(r["lage"])
        b = bas.get((r["task"], r["etikett"]))
        if b is None:
            continue
        post = per_uppgift.setdefault(r["task"], {})
        rad = post.setdefault(r["lage"], {"utfall_andrad": [], "enheter": 0})
        rad["enheter"] += 1
        if r["utfall"] != b["utfall"]:
            rad["utfall_andrad"].append(r["etikett"])

    # Varm mot kall, enhet for enhet. Ingen RETAIN i banken => identiska.
    varm_kall_skiljer = []
    varm = dict(((r["task"], r["etikett"]), r) for r in rader
                if r["lage"] == "0.50")
    for r in rader:
        if r["lage"] != "kall":
            continue
        v = varm.get((r["task"], r["etikett"]))
        if v and (v["utfall"] != r["utfall"]
                  or sorted(v["koder"]) != sorted(r["koder"])):
            varm_kall_skiljer.append("%s/%s" % (r["task"], r["etikett"]))

    med_retain = sorted(k for k, v in retainkarta.items() if v)
    olasliga = sorted(k for k, v in retainkarta.items() if v is None)

    resultat = {
        "enheter": len(bas),
        "uppgifter": sorted(per_uppgift),
        "lagen": lagen,
        "per_uppgift": per_uppgift,
        "enheter_med_retain": med_retain,
        "enheter_som_inte_gick_att_lasa": olasliga,
        "varm_och_kall_skiljer": varm_kall_skiljer,
        "totalt": {},
    }
    for lage in lagen:
        n = sum(len(v.get(lage, {}).get("utfall_andrad", []))
                for v in per_uppgift.values())
        u = sum(1 for v in per_uppgift.values()
                if v.get(lage, {}).get("utfall_andrad"))
        resultat["totalt"][lage] = {"enheter_andrade": n, "uppgifter": u}

    print("\n=== RETAIN i banken ===")
    print("  enheter som deklarerar RETAIN: %d av %d" % (len(med_retain),
                                                         len(bas)))
    for e in med_retain[:20]:
        print("    %s: %s" % (e, ", ".join(retainkarta[e])))
    if olasliga:
        print("  enheter som inte gick att lasa: %d" % len(olasliga))

    print("\n=== enheter vars UTFALL andras av en omstart ===")
    print("uppgift  " + "  ".join("%8s" % l for l in lagen))
    for task in sorted(per_uppgift):
        v = per_uppgift[task]
        print("%-8s " % task + "  ".join(
            "%8d" % len(v.get(l, {}).get("utfall_andrad", [])) for l in lagen))
    print("\n=== totalt ===")
    for lage in lagen:
        t = resultat["totalt"][lage]
        print("  omstart vid %-5s: %d enheter byter utfall i %d uppgifter"
              % (lage, t["enheter_andrade"], t["uppgifter"]))
    print("\n  varmstart och kallstart skiljer sig i %d enheter%s"
          % (len(varm_kall_skiljer),
             " (vantat 0: ingen banklosning deklarerar RETAIN)"
             if not med_retain else ""))

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(resultat, f, ensure_ascii=False, indent=1,
                      sort_keys=True)
    if not bas:
        print("noll matta enheter")
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-173: omstarten mitt i sparet")
    ap.add_argument("--uppgifter", help="kommaseparerade task_id")
    ap.add_argument("--jsonl", help="radata")
    ap.add_argument("--json", help="sammanstallning")
    return svep(ap.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
