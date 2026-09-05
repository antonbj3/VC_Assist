#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-161: komponentsokets nolla var TVA hal, och bara det ena gick att laga.

M-119 matte att fragan "vilken komponent i det installerade biblioteket
motsvarar bankens X?" besvarades i 0 av 75 fall pa forsta forsoket och 7 av 72
vid omtag. Det talet ar en summa over tva olika fel, och en nolla som bestar av
tva orsaker gar inte att laga forran den delas.

DELNINGEN ar mekanisk och kommer ur bankens EGET falt `stampel`, som skrevs
innan sokverktyget fanns och som inte beror pa nagot sokresultat:

  * `ANTAGEN` (60 av 75) - namnet ar bankforfattarens egen svenska
    funktionsbeskrivning ("Induktiv narvarogivare"). Det finns ingen
    modellbeteckning att normalisera. VOKABULARGLAPP.
  * `PUBLICERAD_SPEC` (10) och `STANDARDMATT` (5) - namnet ar en beteckning ur
    en tillverkares datablad eller en standard ("ABB IRB 2600-20/1.65",
    "VDA KLT 4147"). FORMATGLAPP, om komponenten finns.

Korningen gor tre saker:

 1. Delar M-119:s 75 fragor i de tva klasserna och skriver ut delningen.
 2. Kor HELA M-119:s fragekorpus en gang till, genom samma verktygsvag och
    samma domare, och lagger talen bredvid M-119:s lagrade.
 3. Kor de TVA SKALADE TRASIGA FIXTURERNA mot hela biblioteket: 2 935 omojliga
    beteckningar och 3 201 riktiga namn med FEL tillverkarled. Bada maste ge
    noll traffar. Det ar den verkliga risken med lagningen - ett sok som gors
    mer tillatande far inte borja hitta pa - och den provas i skala, inte pa
    ett handplacerat fall.

    nice -n 19 ionice -c3 python3 tests/protocol/kor_m161_komponentsoket.py
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "komponentsokets nolla i M-119 var tva hal och inte ett: 60 av de 75 "
        "fragorna bar bankens egna svenska funktionsbeskrivningar, som inget "
        "namnsteg kan losa, och 15 bar riktiga beteckningar, av vilka 8 finns "
        "i biblioteket under en annan skrivning. En namnstege som laser ett "
        "ledande tillverkarnamn som TILLVERKARE hamtar hem de 8 pa FORSTA "
        "forsoket, utan att en enda fraga som ska ge SAKNAS borjar ge traff.",
    "under_prov": (
        "svc/vc_assist_svc/katalogsok.py",
        "svc/vc_assist_svc/verktyg/katalog.py",
        "svc/vc_assist_svc/katalogindex.py",
        "tests/protocol/stod/slaupp.py",
    ),
    "facit":
        "for varje fraga: klassen SVAR, HALVT, SAKNAS eller TYST FEL enligt "
        "M-119:s egna namngivna regler, samma domare och samma korpus; och for "
        "de tva skalade fixturerna: NOLL traffar, undantagslost",
    "facitkalla":
        "Fragorna och domsreglerna ar M-119:s och lases ur dess lagrade "
        "korning (docs/matningar/m119_kunskapstackning.json) - en tidigare "
        "matning med M-nummer, 85_bankkontraktet.md:s femte facitkalla. "
        "Klassdelningen kommer ur bank/katalog_index.json:s falt `stampel`, "
        "en manniskas facit skrivet fore verktyget (fjarde kallan). Bada "
        "ligger utanfor under_prov.",
    "facitkalla_filer": (
        "bank/katalog_index.json",
        "docs/matningar/M-119_kunskapstackningen_over_frageslag.md",
        "docs/matningar/m119_kunskapstackning.json",
        "tests/protocol/kor_kunskapstackning.py",
    ),
    "trasiga_fall": (
        "2 935 beteckningar dar varje sifferblock bytts mot 9997 maste ge "
        "NOLL traffar - formen pa en beteckning far aldrig racka for en traff",
        "3 201 riktiga komponentnamn med FEL tillverkarled framfor sig maste "
        "ge NOLL traffar - tillverkarledet ar ett filter, inte ett ord som "
        "far strykas och glommas",
        "en fraga vars beteckning inte finns i biblioteket far aldrig glida "
        "till en granne: `ABB IRB 660-180/3.15` far inte bli `IRB 660` och "
        "`ABB IRB 360-1/1130 FlexPicker` far inte bli `IRB 360-3/1130`",
        "andelen SVAR i nagot av M-119:s ovriga frageslag far inte sjunka",
    ),
    "kraver": ("vc",),
    "matningar": ("M-161",),
}

import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(HAR, "..", ".."))
sys.path.insert(0, HAR)
sys.path.insert(0, os.path.join(ROT, "svc"))

import kor_kunskapstackning as M119                               # noqa: E402
from vc_assist_svc import katalogindex, katalogsok                # noqa: E402

MATNINGAR = os.path.join(ROT, "docs", "matningar")
FORE = os.path.join(MATNINGAR, "m119_kunskapstackning.json")
UT = os.path.join(MATNINGAR, "m161_komponentsoket.json")

_URI = re.compile(r"\((bank://[^)]+)\)")


# ============================================================ 1. delningen

def dela_de_75():
    """De 75 biblioteksfragorna, delade pa bankens egen stampel.

    Regeln avgors av fragan och aldrig av svaret: `stampel` star i
    bank/katalog_index.json och skrevs innan sokverktyget fanns.
    """
    bank = {p["uri"]: p for p in M119._bankkatalog()["poster"]}
    fore = json.load(open(FORE, encoding="utf-8"))
    ut = []
    for f in fore["alla"]:
        if f["sort"] != "S5_bibliotek":
            continue
        m = _URI.search(f["fraga"])
        p = bank[m.group(1)]
        ut.append({
            "id": f["id"], "uri": m.group(1), "namn": p["namn"],
            "kategori": p["kategori"], "stampel": p["stampel"],
            "klass": 1 if p["stampel"] == "ANTAGEN" else 2,
            "arg": f["arg"], "klass_fore": f["klass"],
        })
    return ut


# ==================================================== 2. de skalade fixturerna

def skalade_fixturer():
    """Bada maste ge noll. De kors mot HELA det installerade biblioteket."""
    fynd = katalogindex.hitta()
    if not fynd:
        return {"kord": False, "skal": "inget installerat bibliotek hittades"}
    index = katalogindex.bygg(fynd[0].rot, djupt=True)
    kat = katalogsok.Katalog.fran_index(index)
    poster = [(t.namn, (t.tillverkare or "")) for t in kat.poster]
    tillverkare = sorted({t.lower() for _n, t in poster if t})

    siffra = re.compile(r"\d+")
    f1 = {"fragor": 0, "traffar": 0, "exempel": []}
    for namn, _t in poster:
        if not siffra.search(namn):
            continue
        fejk = siffra.sub("9997", namn)
        if fejk == namn:
            continue
        f1["fragor"] += 1
        svar = kat.sok(fraga=fejk, max_rader=3)
        if svar.totalt:
            f1["traffar"] += 1
            if len(f1["exempel"]) < 8:
                f1["exempel"].append(
                    {"namn": namn, "fraga": fejk, "antal": svar.totalt,
                     "traffar": [t.namn for t in svar.traffar]})

    f2 = {"fragor": 0, "traffar": 0, "exempel": []}
    for namn, t in poster:
        if not t:
            continue
        fel = [x for x in tillverkare if x != t.lower()]
        if not fel:
            continue
        ft = fel[hash(namn) % len(fel)]
        f2["fragor"] += 1
        svar = kat.sok(fraga="%s %s" % (ft.upper(), namn), max_rader=3)
        if svar.totalt:
            f2["traffar"] += 1
            if len(f2["exempel"]) < 8:
                f2["exempel"].append(
                    {"fraga": "%s %s" % (ft.upper(), namn),
                     "antal": svar.totalt,
                     "traffar": [x.namn for x in svar.traffar],
                     "lasning": svar.lasning})

    # Motprovet: RATT tillverkarled maste hitta komponenten igen.
    f3 = {"fragor": 0, "hittade_sig": 0, "ensam_traff": 0}
    for namn, t in poster:
        if not t:
            continue
        f3["fragor"] += 1
        svar = kat.sok(fraga="%s %s" % (t.upper(), namn), max_rader=50)
        if svar.sammandrag is not None:
            f3["hittade_sig"] += 1          # for bred for en lista, inte ett miss
            continue
        if namn in [x.namn for x in svar.traffar]:
            f3["hittade_sig"] += 1
            if svar.totalt == 1:
                f3["ensam_traff"] += 1

    return {"kord": True, "antal_komponenter": len(poster),
            "omojlig_beteckning": f1, "fel_tillverkarled": f2,
            "ratt_tillverkarled": f3}


# =========================================================== 3. omkorningen

def kor_korpusen():
    """M-119:s hela korpus en gang till, samma vag och samma domare."""
    t0 = time.time()
    fragor = M119.harled()
    sys.stderr.write("harledde %d fragor (M-119:s korpus)\n" % len(fragor))
    for i, f in enumerate(fragor, 1):
        if f.kraver_vc:
            f.klass, f.regel = None, "KRAVER_VC"
            continue
        svar, rc, parsfel = M119.kor_ett(f)
        f.svar = svar
        f.klass, f.regel, f.notering = M119.dom(f, svar, rc, parsfel)
        if i % 50 == 0:
            sys.stderr.write("  %d/%d  (%.0f s)\n" % (i, len(fragor),
                                                      time.time() - t0))
    omtag = M119.harled_omtag(fragor)
    sys.stderr.write("omtag: %d\n" % len(omtag))
    for f in omtag:
        svar, rc, parsfel = M119.kor_ett(f)
        f.svar = svar
        f.klass, f.regel, f.notering = M119.dom(f, svar, rc, parsfel)
    fragor = fragor + omtag
    steg2 = M119.harled_steg2(fragor)
    sys.stderr.write("steg 2: %d\n" % len(steg2))
    for f in steg2:
        svar, rc, parsfel = M119.kor_ett(f)
        f.svar = svar
        f.klass, f.regel, f.notering = M119.dom(f, svar, rc, parsfel)
    return fragor + steg2, time.time() - t0


def per_sort(fragor):
    per = OrderedDict()
    for nyckel, etikett in M119.SORTER.items():
        rader = [f for f in fragor if f.sort == nyckel]
        c = Counter(f.klass for f in rader if not f.kraver_vc)
        kord = sum(1 for f in rader if not f.kraver_vc)
        per[nyckel] = {
            "etikett": etikett, "antal": len(rader), "kord": kord,
            M119.SVAR: c[M119.SVAR], M119.HALVT: c[M119.HALVT],
            M119.SAKNAS: c[M119.SAKNAS], M119.TYST: c[M119.TYST],
            "andel_svar": round(100.0 * c[M119.SVAR] / kord, 1) if kord else None,
        }
    return per


def main():
    delning = dela_de_75()
    n1 = sum(1 for d in delning if d["klass"] == 1)
    n2 = sum(1 for d in delning if d["klass"] == 2)
    print("DELNINGEN AV DE 75 (bankens egen stampel, skriven fore verktyget)")
    print("  klass 1  VOKABULARGLAPP  (stampel ANTAGEN)          %d" % n1)
    print("  klass 2  FORMATGLAPP     (PUBLICERAD_SPEC/STANDARDMATT) %d" % n2)
    for d in delning:
        if d["klass"] == 2:
            print("     %-8s %-16s %s" % (d["id"], d["stampel"], d["namn"]))

    print("\nDE SKALADE TRASIGA FIXTURERNA")
    fix = skalade_fixturer()
    if not fix["kord"]:
        print("  KORDES INTE: %s" % fix["skal"])
    else:
        print("  bibliotek: %d komponenter" % fix["antal_komponenter"])
        for nyckel, text in (("omojlig_beteckning", "omojligt sifferblock"),
                             ("fel_tillverkarled", "fel tillverkarled")):
            d = fix[nyckel]
            print("  %-22s %5d fragor -> %d traffar%s"
                  % (text, d["fragor"], d["traffar"],
                     "   FIXTUREN FALLER" if d["traffar"] else "   (ratt: noll)"))
            for e in d["exempel"]:
                print("      %s" % json.dumps(e, ensure_ascii=False))
        d = fix["ratt_tillverkarled"]
        print("  %-22s %5d fragor -> %d hittade sig sjalva, %d som ensam traff"
              % ("ratt tillverkarled", d["fragor"], d["hittade_sig"],
                 d["ensam_traff"]))

    fragor, sekunder = kor_korpusen()
    efter = per_sort(fragor)
    fore = json.load(open(FORE, encoding="utf-8"))["per_sort"]

    print("\nFORE (M-119) MOT EFTER, per frageslag")
    print("  %-18s %6s   %-22s %-22s" % ("sort", "kord", "SVAR fore", "SVAR efter"))
    for nyckel, e in efter.items():
        f = fore.get(nyckel, {})
        if not e["kord"]:
            continue
        print("  %-18s %6d   %6d (%5s %%)        %6d (%5s %%)"
              % (nyckel, e["kord"], f.get("SVAR", 0), f.get("andel_svar"),
                 e["SVAR"], e["andel_svar"]))

    rap = {
        "korning": "kor_m161_komponentsoket.py",
        "matning": "M-161",
        "fore_matning": "M-119",
        "sekunder": round(sekunder, 1),
        "delning": delning,
        "klass_1": n1, "klass_2": n2,
        "skalade_fixturer": fix,
        "per_sort_efter": efter,
        "per_sort_fore": fore,
        "alla": [f.som_dict() for f in fragor],
    }
    with open(UT, "w", encoding="utf-8") as f:
        json.dump(rap, f, ensure_ascii=False, indent=1)
    print("\nskrev %s" % UT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
