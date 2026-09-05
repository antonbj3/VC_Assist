# -*- coding: utf-8 -*-
"""M-122: mutationsmotorn omkörd genom bankens domare, och vad som överlever.

## Varför körningen finns

`svc/vc_assist_svc/plc/mutation.py` gör kända skador i de referenslösningar
som uppfyller sitt eget facit. Den första körningen (2026-09-05, skript ej
kvar på disk) rapporterade 471 av 806 fångade och bara 14 fångade av
BETEENDElagret. Det talet styr ett beslut - om spårfacit alls duger som
beteendegrind - och måste därför gå att köra om.

Körningen gör tre saker, alla utan VC, OpenPLC eller nät:

1. **Skikten.** Varje skada döms av `bank.domare.dom`, exakt som
   reparationsslingan gör. `tolkfel:*` = textlagret (tolken vägrar), allt
   annat = beteendelagret (koden körde och facit fällde).
2. **Överlevarna.** En mutant domaren godkänner körs igen, bredvid
   referensen, på facitets egna sekvenser och på fem perturbationer av samma
   stimulus (alla händelseavstånd x0,25, x0,5, x2,0; sekvensen två gånger i
   rad; varje boolesk puls hålls tre gånger så länge). Facit för jämförelsen
   är referensens eget utgångsspår - referensen är korrekt per definition i
   en mutationsanalys, så ingen ny domare uppfinns. Klass:
   `SKILLNAD_PA_FACITSTIMULUS` (facit ser för få punkter),
   `SYNLIG_BARA_UNDER_PERTURBATION` (stimulus når inte raden), `OSYNLIG`.
   Dessutom radtyp: kommentar, initierare i VAR-block, eller kod.
3. **F15-operatorn i motorn.** Sedan C0/M-131 är den riktiga nivåoperatorn en
   sort i `mutation.py` (`FLANK_TILL_NIVA`): `inst.Q` byts mot instansens
   CLK-signal. Rapporten nedan grupperar den per CLK-signal.
4. **Grind 2:s fällplatser.** Vilka av validatorns fällplatser (räknade med
   AST som i `kor_fallplatstackning.py`) fyrar mutanterna, jämfört med
   M-111:s lista över platser som aldrig fyrat under enhetssviten.

    python3 tests/protocol/kor_m122_mutationsskikt.py [--json ut.json] [--m111 m111.json]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import multiprocessing as mp
import os
import re
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)
sys.path.insert(0, os.path.dirname(__file__))

BANKPOST = {
    "pastar": "en kand skada i en referens som uppfyller sitt facit fangas av "
              "bankens domare, och de som overlever ar antingen ekvivalenta, "
              "osedda av facitets kontrollpunkter eller onadda av dess stimulus",
    "under_prov": ("bank/domare.py", "svc/vc_assist_svc/st/tolk.py",
                   "svc/vc_assist_svc/plc/mutation.py",
                   "svc/vc_assist_svc/st/validator.py"),
    "facit": "skadan sjalv: fore/efter-texten ar kand, och referensens eget "
             "utgangsspar ar facit for overlevarnas jamforelse",
    "facitkalla": "en kand textandring i en referens som redan uppfyller sitt "
                  "handskrivna facit (85_bankkontraktet.md §2 klass 4), och "
                  "referensens utgangsspar under samma stimulus",
    "facitkalla_filer": ("bank/uppgifter",),
    "trasiga_fall": (
        "en referens som inte godkanns av sitt eget facit avbryter korningen "
        "med slutkod 2 - en mutationsanalys pa en rod referens mater inget",
        "noll skador ger slutkod 2",
        "fangstgrad under golvet (M-147) ger slutkod 2 - sparr som bara far ga uppat",
    ),
    "kraver": ("inget",),
    "matningar": ("M-122", "M-131", "M-135", "M-147"),
}

# MATT 2026-09-05 av M-147 (omkalibrerat nar 8 nya industriella skadesorter
# lades till i C6; M-123-principen). Golven far bara ga UPPAT.
GOLV_SKADOR = 1307              # M-147
GOLV_FANGADE = 1174             # M-147
GOLV_FANGSTGRAD = GOLV_FANGADE / GOLV_SKADOR  # M-147: 0.8982402448355011

GOLV_PER_SORT = {
    "AND_TILL_OR": (91, 98),
    "ARRAY_INDEX_UTANFOR": (0, 0),
    "DIVISION_MED_NOLL": (0, 0),
    "END_IF_STRUKEN": (99, 99),
    "FALSKT_TILL_SANT": (78, 97),
    "FLANKENS_Q_TILL_SIGNAL": (82, 82),
    "FLANK_STRUKEN": (32, 32),
    "FLANK_TAVLAR": (1, 32),
    "FLANK_TILL_NIVA": (35, 36),
    "ICKE_ASCII": (96, 96),
    "JAMFORELSE_VAND": (74, 75),
    "KVARHALLEN_UTGANG_STOPP": (45, 71),
    "LARM_KVITTERAT_UTAN_ORSAK": (0, 16),
    "NOT_STRUKEN": (95, 97),
    "OR_TILL_AND": (40, 46),
    "RETENTIV_FORLORAD": (0, 0),
    "SANT_TILL_FALSKT": (92, 97),
    "SEMIKOLON_STRUKET": (99, 99),
    "TID_FORDUBBLAD": (47, 50),
    "TID_OGILTIG": (50, 50),
    "TILLSTAND_FASTNAR": (69, 84),
    "TIMER_FORVAL_ANDRAS": (49, 50),
}


def validera_mutationsgolv(fangade: int, skador_totalt: int, per_sort=None):
    """Mekanisk grind: fangstgraden far bara ga UPPAT (M-53-monster)."""
    if skador_totalt <= 0:
        return False, "noll skador"
    kvot = fangade / skador_totalt
    if kvot < GOLV_FANGSTGRAD - 1e-9:
        return False, (
            "fangstgrad %.4f under golvet %.4f (%d av %d mot golv %d av %d, M-135)"
            % (kvot, GOLV_FANGSTGRAD, fangade, skador_totalt, GOLV_FANGADE, GOLV_SKADOR)
        )
    if per_sort:
        for sort, (g_fang, g_tot) in GOLV_PER_SORT.items():
            if sort in per_sort:
                f, tot = per_sort[sort]
                if f < g_fang:
                    return False, (
                        "sort %s: %d fangade under golvet %d (av %d, M-135)"
                        % (sort, f, g_fang, tot)
                    )
    return True, "godkand mot golvet"

from vc_assist_svc.plc.mutation import skador, var_rader  # noqa: E402
from vc_assist_svc.st import tolk as T                 # noqa: E402
from vc_assist_svc.st.tolk import Tolk, Tolkfel        # noqa: E402
from vc_assist_svc.st import validator as V            # noqa: E402
from bank import domare                                # noqa: E402

# namn, tidsskala, upprepningar, hålltid för booleska pulser
PERT = (("facit", 1.0, 1, 1.0), ("x0.25", 0.25, 1, 1.0), ("x0.5", 0.5, 1, 1.0),
        ("x2.0", 2.0, 1, 1.0), ("upprepa2", 1.0, 2, 1.0), ("hall3", 1.0, 1, 3.0))

_TYP = {"bool": "BOOL", "int": "INT", "dint": "DINT", "real": "REAL",
        "time": "TIME", "word": "WORD", "uint": "UINT", "string": "STRING"}


def _uppgifter():
    ut = []
    for f in sorted(glob.glob(os.path.join(_ROT, "bank", "uppgifter", "*.json"))):
        with open(f, "r", encoding="utf-8") as h:
            post = json.load(h)
        if post.get("facit_spar"):
            ut.append(post)
    return ut


# ------------------------------------------------------------------ spår

def spar(st_text, post, sekv, flanker, skala=1.0, upprepa=1, hall=1.0,
         paus_ms=1000.0):
    """Utgångsvärdena per scan under en (perturberad) sekvens, eller TOLKFEL."""
    typer, riktningar = domare._signalkarta(post)
    utg = sorted(n for n, r in riktningar.items() if r == "out")
    facit = post["facit_spar"]
    scan_ms = float(facit.get("scan_ms") or T.SCAN_MS)
    steg = sorted(sekv["steg"], key=lambda x: float(x["t_ms"]))
    slut = max([float(s["t_ms"]) for s in steg] +
               [float(f.get("till_ms", 0.0)) for f in flanker
                if f.get("sekvens") == sekv["id"]])
    plan = []
    for r in range(upprepa):
        off = r * (slut * skala + paus_ms)
        for s in steg:
            if s.get("satt"):
                plan.append((off + float(s["t_ms"]) * skala, dict(s["satt"])))
    slut_tot = (upprepa - 1) * (slut * skala + paus_ms) + slut * skala
    if hall != 1.0:
        ev = sorted(((t, s, v) for t, d in plan for s, v in d.items()),
                    key=lambda e: e[0])
        senast_hog, ny = {}, []
        for t, s, v in ev:
            if isinstance(v, bool):
                if v:
                    senast_hog[s] = t
                elif s in senast_hog:
                    t0 = senast_hog.pop(s)
                    t = t0 + hall * (t - t0)
            ny.append((t, s, v))
        ny.sort(key=lambda e: e[0])
        plan = []
        for t, s, v in ny:
            if plan and abs(plan[-1][0] - t) < 1e-9:
                plan[-1][1][s] = v
            else:
                plan.append((t, {s: v}))
        slut_tot = max(slut_tot, max(t for t, _ in plan) + 2000.0)
    try:
        motor = Tolk(st_text, typer, riktningar, scan_ms)
    except Tolkfel as f:
        return ("TOLKFEL", str(f)[:120])
    ut, i = [], 0
    try:
        while motor.tid_ms <= slut_tot + 1e-9:
            while i < len(plan) and plan[i][0] <= motor.tid_ms + 1e-9:
                for n, v in plan[i][1].items():
                    motor.satt(n, v)
                i += 1
            motor.scan()
            ut.append(tuple(motor.las(u) for u in utg))
    except Tolkfel as f:
        return ("TOLKFEL", str(f)[:120])
    return ut


def alla_spar(st_text, post):
    facit = post["facit_spar"]
    flanker = facit.get("flanker") or []
    return dict((namn, [spar(st_text, post, s, flanker, skala, upprepa, hall)
                        for s in facit.get("sekvenser") or []])
                for namn, skala, upprepa, hall in PERT)


def skiljer(a, b):
    return any(x != y for x, y in zip(a, b))


def radtyp(ref, rad):
    # VAR-delen ar motorns egen skanning (mutation.var_rader) - en
    # RADSKANNING, inte en parsning (M-122 LIMITS). Den star pa ett stalle.
    lines = ref.split("\n")
    l = lines[rad - 1]
    txt = "\n".join(lines[:rad])
    if txt.count("(*") > txt.count("*)") or l.strip().startswith("(*") \
            or l.strip().startswith("//"):
        return "KOMMENTAR"
    if rad in var_rader(ref):
        return "INITIERARE"
    return "KOD"


def klassa(refspar, ms):
    synlig = dict((n, skiljer(refspar[n], ms[n])) for n, _, _, _ in PERT)
    if synlig["facit"]:
        klass = "SKILLNAD_PA_FACITSTIMULUS"
    elif any(v for n, v in synlig.items() if n != "facit"):
        klass = "SYNLIG_BARA_UNDER_PERTURBATION"
    else:
        klass = "OSYNLIG"
    return klass, synlig


# ------------------------------------------------------------- del 1 och 2

def kor_uppgift(post):
    os.nice(19)
    ref = post["facit_spar"]["referens"]
    refdom = domare.dom(post, ref)
    refspar = alla_spar(ref, post)
    rader = []
    for sk in skador(ref, per_sort=3):
        d = domare.dom(post, sk.kropp)
        koder = [b.kod for b in d.brister]
        if d.godkand:
            utfall, lager = "OVERLEVDE", None
        elif any(k.startswith("tolkfel") for k in koder):
            utfall, lager = "FANGAD", "text"
        else:
            utfall, lager = "FANGAD", "beteende"
        rad = dict(uppgift=post["task_id"], sort=sk.sort, vantat=sk.vantat_lager,
                   rad=sk.rad, fore=sk.fore[:40], efter=sk.efter[:40],
                   utfall=utfall, lager=lager, koder=koder[:6])
        if d.godkand:
            klass, synlig = klassa(refspar, alla_spar(sk.kropp, post))
            rad.update(klass=klass, synlig=synlig, radtyp=radtyp(ref, sk.rad))
        rader.append(rad)
    return dict(uppgift=post["task_id"], referens_godkand=refdom.godkand,
                referens_koder=[b.kod for b in refdom.brister][:5],
                rader=rader)


# -------------------------------------------------------------------- del 4

def _med_deklarationer(ref, post):
    sig = (post.get("control") or {}).get("signals") or []
    def dek(s):
        return "    %s : %s;" % (s["name"], _TYP.get(str(s.get("type")).lower(),
                                                    str(s.get("type")).upper()))
    inn = [dek(s) for s in sig if s.get("dir") == "in"]
    ut = [dek(s) for s in sig if s.get("dir") != "in"]
    block = "VAR_INPUT\n%s\nEND_VAR\nVAR_OUTPUT\n%s\nEND_VAR\n" % (
        "\n".join(inn), "\n".join(ut))
    m = re.search(r"^PROGRAM\s+\w+\s*$", ref, re.M)
    if not m:
        return None
    return ref[:m.end()] + "\n" + block + ref[m.end():]


def fallplatser(poster):
    """Grind 2 (validera) över referenser och mutanter, med signalkartan
    deklarerad. Räknar fällplatser via samma inspelning som M-111."""
    from kor_fallplatstackning import platser_ur_kallan, _VALIDATOR
    sedda = collections.defaultdict(set)
    aktuell = [None]
    orig = V.Granskning.fel

    def insp(self, kod, rad, text):
        sedda[(kod, sys._getframe(1).f_lineno)].add(aktuell[0])
        return orig(self, kod, rad, text)

    V.Granskning.fel = insp
    ref_anm = {}
    n_mut = fangade = 0
    per_sort = collections.Counter()
    per_sort_n = collections.Counter()
    try:
        for post in poster:
            tid = post["task_id"]
            ref = _med_deklarationer(post["facit_spar"]["referens"], post)
            if ref is None:
                continue
            utg = [s["name"] for s in post["control"]["signals"] if s.get("dir") != "in"]
            aktuell[0] = ("REF", tid)
            r = V.validera(ref, utgangar=utg)
            ref_par = set((a.kod, a.text) for a in r.anmarkningar)
            ref_anm[tid] = sorted(set(a.kod for a in r.anmarkningar))
            for sk in skador(post["facit_spar"]["referens"], per_sort=3):
                n_mut += 1
                per_sort_n[sk.sort] += 1
                aktuell[0] = (tid, sk.sort)
                r2 = V.validera(_med_deklarationer(sk.kropp, post), utgangar=utg)
                nya = set((a.kod, a.text) for a in r2.anmarkningar) - ref_par
                if nya or (not r2.ok and r.ok):
                    fangade += 1
                    per_sort[sk.sort] += 1
    finally:
        V.Granskning.fel = orig
    ur_koden = platser_ur_kallan(_VALIDATOR)
    alla = set((k, rad) for k, rader in ur_koden.items() for rad in rader)
    av_mut = set(k for k, who in sedda.items() if any(w[0] != "REF" for w in who)) & alla
    av_ref = set(k for k, who in sedda.items() if any(w[0] == "REF" for w in who)) & alla
    return dict(platser=len(alla), fyrade_av_referenser=sorted(av_ref),
                fyrade_av_mutanter=sorted(av_mut), n_mutanter=n_mut,
                fangade_av_grind2=fangade,
                per_sort=dict((s, [per_sort[s], per_sort_n[s]]) for s in per_sort_n),
                referenser_med_anmarkning=dict((t, k) for t, k in ref_anm.items() if k))


# -------------------------------------------------------------------- main

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    p.add_argument("--m111", help="JSON ur kor_fallplatstackning.py --json")
    a = p.parse_args(argv)
    t0 = time.time()
    poster = _uppgifter()
    with mp.Pool(4) as pool:
        res = pool.map(kor_uppgift, poster)
    roda = [u["uppgift"] for u in res if not u["referens_godkand"]]
    rader = [r for u in res for r in u["rader"]]
    if roda:
        print("REFERENS FALLD AV SITT EGET FACIT: %s - korningen avbryts" % roda,
              file=sys.stderr)
        return 2
    if not rader:
        print("NOLL skador", file=sys.stderr)
        return 2

    print("=== M-122 MUTATIONSSKIKTEN ===  %d uppgifter, referens GODKAND %d av %d, %.0f s\n"
          % (len(res), len(res) - len(roda), len(res), time.time() - t0))
    fang = [r for r in rader if r["utfall"] == "FANGAD"]
    ov = [r for r in rader if r["utfall"] == "OVERLEVDE"]
    print("skador %d   fangade %d (%.0f %%)   overlevde %d"
          % (len(rader), len(fang), 100.0 * len(fang) / len(rader), len(ov)))
    print("fangade per lager:", dict(collections.Counter(r["lager"] for r in fang)))
    print("vantat lager -> fangande lager:",
          dict(collections.Counter((r["vantat"], r["lager"]) for r in fang)))

    per_sort_res = {}
    for sort in set(r["sort"] for r in rader):
        rs = [r for r in rader if r["sort"] == sort]
        per_sort_res[sort] = (sum(1 for r in rs if r["utfall"] == "FANGAD"), len(rs))
    ok_golv, fel_golv = validera_mutationsgolv(len(fang), len(rader), per_sort=per_sort_res)
    print("grind (M-53-golv, M-147): %s" % ("GODKAND" if ok_golv else "UNDERKAND: " + fel_golv))
    print("\n%-24s %5s %5s %5s %5s | %6s %6s %6s" % (
        "sort", "n", "text", "bete", "over", "SKILL", "PERT", "OSYN"))
    for sort in sorted(set(r["sort"] for r in rader)):
        rs = [r for r in rader if r["sort"] == sort]
        o = [r for r in rs if r["utfall"] == "OVERLEVDE"]
        print("%-24s %5d %5d %5d %5d | %6d %6d %6d" % (
            sort, len(rs),
            sum(1 for r in rs if r["lager"] == "text"),
            sum(1 for r in rs if r["lager"] == "beteende"), len(o),
            sum(1 for r in o if r["klass"] == "SKILLNAD_PA_FACITSTIMULUS"),
            sum(1 for r in o if r["klass"] == "SYNLIG_BARA_UNDER_PERTURBATION"),
            sum(1 for r in o if r["klass"] == "OSYNLIG")))
    bo = [r for r in ov if r["vantat"] == "beteende"]
    print("\noverlevande BETEENDEmutanter: %d" % len(bo))
    print("  radtyp x klass:", dict(collections.Counter((r["radtyp"], r["klass"]) for r in bo)))
    print("  radtyp ar en RADSKANNING (VAR..END_VAR via mutation.var_rader), inte en parsning - M-122 LIMITS")
    kod = [r for r in bo if r["radtyp"] == "KOD"]
    print("  kodrads-overlevare: %d  klass: %s" % (
        len(kod), dict(collections.Counter(r["klass"] for r in kod))))
    for pn, _, _, _ in PERT:
        print("    synliga under %-9s %2d av %d" % (pn, sum(1 for r in kod if r["synlig"][pn]), len(kod)))
    print("  kodrads-overlevare per uppgift:",
          dict(collections.Counter(r["uppgift"] for r in kod)))

    niva = [r for r in rader if r["sort"] == "FLANK_TILL_NIVA"]
    nf = [r for r in niva if r["utfall"] == "FANGAD"]
    no = [r for r in niva if r["utfall"] == "OVERLEVDE"]
    print("\n=== NIVA I STALLET FOR FLANK (M-115:s F15, motor-sort sedan C0) ===")
    print("nivamutanter %d i %d uppgifter   fangade %d   overlevde %d"
          % (len(niva), len(set(r["uppgift"] for r in niva)), len(nf), len(no)))
    print("  fangade:", ", ".join("%s:%s" % (r["uppgift"], r["efter"]) for r in nf))
    print("  overlevde:", ", ".join("%s:%s[%s]" % (r["uppgift"], r["efter"], r.get("klass", "-")[:5]) for r in no))

    print("\n=== GRIND 2:S FALLPLATSER ===")
    fp = fallplatser(poster)
    print("mutanter %d   fangade av grind 2 (ny anmarkning utover referensens) %d"
          % (fp["n_mutanter"], fp["fangade_av_grind2"]))
    for s, (k, n) in sorted(fp["per_sort"].items()):
        print("   %-24s %3d av %3d" % (s, k, n))
    print("fallplatser i validator.py: %d   fyrade av referenserna: %d   fyrade av mutanterna: %d %s"
          % (fp["platser"], len(fp["fyrade_av_referenser"]),
             len(fp["fyrade_av_mutanter"]), fp["fyrade_av_mutanter"]))
    print("referenser med egen grind-2-anmarkning (M-121 ager fragan):",
          fp["referenser_med_anmarkning"])
    if a.m111 and os.path.exists(a.m111):
        with open(a.m111, "r", encoding="utf-8") as h:
            m111 = json.load(h)
        aldrig = set((o["kod"], o["rad"]) for o in m111["otackta"])
        nadda = aldrig & set(tuple(x) for x in fp["fyrade_av_mutanter"])
        print("M-111: aldrig fyrade platser %d, varav mutanterna nar %d %s"
              % (len(aldrig), len(nadda), sorted(nadda)))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as h:
            json.dump(dict(uppgifter=res, fallplatser=fp), h, ensure_ascii=False, indent=1)
        print("\nskrivet:", a.json)
    if not ok_golv:
        print("KORNINGEN FALLS MOT GOLVET (M-147): %s" % fel_golv, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
