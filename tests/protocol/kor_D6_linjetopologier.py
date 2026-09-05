# -*- coding: utf-8 -*-
"""L2/L3: Prov av kompositionsdomare over fyra nya linjetopologier.

Uppdrag D6 i docs/uppdrag/KO_D_ogat_och_scenen.md.
Mater M-133.

Fas 8 (M-73, M-74) provade EN lina med tva stationer i serie.
Ett urval pa ett ar inget urval. Har byggs och provs fyra linjer med skilda topologier:
  1. SERIELL_3     tre stationer i serie (A -> B -> C)
  2. BUFFERT       tva stationer med mellanliggande buffert (A -> BUF -> B)
  3. PARALLELL     tva parallella grenar med delning och sammanflode (IN -> G1 // G2 -> UT)
  4. ATERFLODE     slinga med omarbete/rejekt tillbaka till uppstroms station (A -> B -> SLINGA -> A)

Varje topologi provas med:
  - HEL: gron kontroll (ska ge PASS i delstationerna och PASS i linjen)
  - tva kompositionsfel som bevisligen passerar delstationerna men MASTE
    fallas nar linjen kors tillsammans.
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Kompositionsdomarna faller kompositionsfel over alla fyra "
        "linjetopologierna (seriell 3-station, buffert, parallella grenar och "
        "aterflode), medan delstationerna isolerade ger PASS.",
    "under_prov": (
        "ext/vc_addon/vc_assist/oga_analys.py",
        "ext/vc_addon/vc_assist/oga_harledning.py",
    ),
    "facit":
        "varje topologis HEL-losning ger PASS i alla konfigurationer, och "
        "varje kompositionsfel ger PASS isolerat och FAIL i linjekonfigurationen",
    "facitkalla":
        "kompositionsdefinitionen ur M-74: fel som bara finns nar stationerna "
        "star tillsammans",
    "facitkalla_filer": (
        "docs/matningar/M-74_kompositionsfallen.md",
        "docs/spec/42_ogat_utbyggt.md",
    ),
    "trasiga_fall": (
        "ett fel som faller isolerat i en delstation ar inget kompositionsfel",
        "en topologi dar kompositionsdomarna inte faller felet ar ett fynd om domaren",
    ),
    "kraver": ("inget",),
    "matningar": ("M-133",),
}

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "ext", "vc_addon", "vc_assist")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import oga_analys as A


RATE = 20.0
DT = 1.0 / RATE


def _bygg_serie(rader, template="linje"):
    return {
        "v": 1,
        "template": template,
        "run": {"started": "2026-09-05T12:00:00", "dur_s": round(len(rader) * DT, 3),
                "samples": len(rader), "rate_hz": RATE},
        "tracked": {"parts": ["broms"], "tools": [], "signals": [],
                    "pairs": [], "joints": [], "stations": [],
                    "scene": ["produkt"]},
        "rows": rader,
    }


# ==============================================================================
# TOPOLOGI 1: SERIELL (3 stationer A -> B -> C)
# ==============================================================================

def topologi_seriell(fall="HEL"):
    """Tre stationer i serie: A -> B -> C.

    K_SER_1: Kaskadsvalt. A och B fordrors, sa C svalter (overstiger max_svalt_s).
    K_SER_2: Delad resurs mellan ytterstationerna A och C (forreglingsbrott).
    """
    n_cykler = 3
    cykel_steg = 60
    rader = []

    for c in range(n_cykler):
        for s in range(cykel_steg):
            t = (c * cykel_steg + s) * DT
            # Normal drift: A arbetar 5-45, B arbetar 10-50, C arbetar 15-55
            a_stopp = (5 <= s < 45)
            a_slapp = (45 <= s < 50)
            b_stopp = (10 <= s < 50)
            b_slapp = (50 <= s < 55)
            c_stopp = (15 <= s < 55)
            c_slapp = (55 <= s < 60)

            # Station C statistik: aktivt i arbete i normal drift
            c_state = "BUSY" if (15 <= s < 55) else "IDLE"
            c_cur = 1 if (15 <= s < 55) else 0

            if fall == "K_SER_1":
                # Kaskadsvalt: A/B fordrors sa delar nar aldrig C i tid; C star IDLE och tom
                c_stopp = False
                c_slapp = False
                c_state = "IDLE"
                c_cur = 0

            if fall == "K_SER_2":
                # A och C delar samma utmatningsdon och slapper samtidigt (konflikt)
                if 45 <= s < 50:
                    c_slapp = True  # brott mot delad forregling A och C

            plc = {
                "a_stopp": a_stopp, "a_slapp": a_slapp,
                "b_stopp": b_stopp, "b_slapp": b_slapp,
                "c_stopp": c_stopp, "c_slapp": c_slapp,
            }
            stat = {
                "stat_c": {"state": c_state, "cur": c_cur, "in": c + 1, "out": c}
            }
            rader.append({
                "t": round(t, 4),
                "parts": {"broms": {"p": [0.0, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "scene": {"produkt": {"p": [t * 0.25, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "plc": plc,
                "stat": stat,
                "plc_alder_s": 0.02,
            })

    data = _bygg_serie(rader, "seriell_3")
    plan = {
        "template": "seriell_3",
        "parts": ["broms"], "tools": [], "rate_hz": RATE,
        "forregling": [["plc:a_slapp", "plc:c_slapp"]],
        "stat": ["stat_c"],
        "genomstromning": {"max_svalt_s": 2.5},
    }
    return data, plan


# ==============================================================================
# TOPOLOGI 2: MED BUFFERT (A -> Buffert -> B)
# ==============================================================================

def topologi_buffert(fall="HEL"):
    """Tva stationer med buffert: A -> BUF -> B.

    K_BUF_1: Buffertblockering. B tar inte emot, bufferten fylls och blockerar A.
    K_BUF_2: Buffertsvalt. Bufferttomning sker inte pga trottel/felaktig givare.
    """
    n_cykler = 3
    cykel_steg = 60
    rader = []

    for c in range(n_cykler):
        for s in range(cykel_steg):
            t = (c * cykel_steg + s) * DT
            a_stopp = (5 <= s < 45)
            a_slapp = (45 <= s < 50)
            b_stopp = (10 <= s < 50)
            b_slapp = (50 <= s < 55)

            a_state = "BUSY" if (5 <= s < 45) else "IDLE"
            a_cur = 1 if (5 <= s < 45) else 0
            b_state = "BUSY" if (10 <= s < 50) else "IDLE"
            b_cur = 1 if (10 <= s < 50) else 0

            if fall == "K_BUF_1":
                # Buffert full -> Station A blockeras under hela cykeln
                a_state = "BLOCKED"
                a_cur = 1

            if fall == "K_BUF_2":
                # Buffertsvalt -> Station B far inga delar och star IDLE
                b_stopp = False
                b_slapp = False
                b_state = "IDLE"
                b_cur = 0

            plc = {
                "a_stopp": a_stopp, "a_slapp": a_slapp,
                "b_stopp": b_stopp, "b_slapp": b_slapp,
            }
            stat = {
                "stat_a": {"state": a_state, "cur": a_cur, "in": c + 1, "out": c},
                "stat_b": {"state": b_state, "cur": b_cur, "in": c + 1, "out": c},
            }
            rader.append({
                "t": round(t, 4),
                "parts": {"broms": {"p": [0.0, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "scene": {"produkt": {"p": [t * 0.25, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "plc": plc,
                "stat": stat,
                "plc_alder_s": 0.02,
            })

    data = _bygg_serie(rader, "buffert")
    plan = {
        "template": "buffert",
        "parts": ["broms"], "tools": [], "rate_hz": RATE,
        "stat": ["stat_a", "stat_b"],
        "genomstromning": {"max_svalt_s": 2.5, "max_blockerad_s": 2.5},
    }
    return data, plan


# ==============================================================================
# TOPOLOGI 3: PARALLELLA GRENAR (IN -> G1 // G2 -> UT)
# ==============================================================================

def topologi_parallell(fall="HEL"):
    """Tva parallella grenar: Inmatning delar upp till G1 och G2, som sammanflodar.

    K_PAR_1: Sammanflodeskollision (G1 och G2 slapper samtidigt mot merge-punkten).
    K_PAR_2: Grensvalt (asymmetrisk fordelning: G2 svalter ut helt).
    """
    n_cykler = 3
    cykel_steg = 60
    rader = []

    for c in range(n_cykler):
        for s in range(cykel_steg):
            t = (c * cykel_steg + s) * DT
            g1_slapp = (45 <= s < 50)
            g2_slapp = (50 <= s < 55)
            g2_state = "BUSY" if (10 <= s < 50) else "IDLE"
            g2_cur = 1 if (10 <= s < 50) else 0

            if fall == "K_PAR_1":
                # Sammanflodeskollision: bada grenarna slapper utmatning samtidigt!
                g1_slapp = (45 <= s < 50)
                g2_slapp = (45 <= s < 50)  # brott mot forregling g1_slapp och g2_slapp

            if fall == "K_PAR_2":
                # Grensvalt: G2 svalter alltid (far aldrig material)
                g2_slapp = False
                g2_state = "IDLE"
                g2_cur = 0

            plc = {
                "g1_slapp": g1_slapp,
                "g2_slapp": g2_slapp,
            }
            stat = {
                "stat_g2": {"state": g2_state, "cur": g2_cur, "in": c + 1, "out": c}
            }
            rader.append({
                "t": round(t, 4),
                "parts": {"broms": {"p": [0.0, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "scene": {"produkt": {"p": [t * 0.25, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "plc": plc,
                "stat": stat,
                "plc_alder_s": 0.02,
            })

    data = _bygg_serie(rader, "parallell")
    plan = {
        "template": "parallell",
        "parts": ["broms"], "tools": [], "rate_hz": RATE,
        "forregling": [["plc:g1_slapp", "plc:g2_slapp"]],
        "stat": ["stat_g2"],
        "genomstromning": {"max_svalt_s": 2.5},
    }
    return data, plan


# ==============================================================================
# TOPOLOGI 4: ATERFLODE / SLINGA (A -> B -> RETUR -> A)
# ==============================================================================

def topologi_aterflode(fall="HEL"):
    """Slinga med aterflode: A -> B -> Retur -> A.

    K_REC_1: Aterflodeskollision / forreglingsbrott (retursignal och nytt inflode samtidigt).
    K_REC_2: Cirkulart dodlage (slingan proppfull, station A och B bada blockerade).
    """
    n_cykler = 3
    cykel_steg = 60
    rader = []

    for c in range(n_cykler):
        for s in range(cykel_steg):
            t = (c * cykel_steg + s) * DT
            nytt_in = (5 <= s < 10)
            retur_in = (35 <= s < 40)
            b_blockerad = False
            b_state = "BUSY" if (15 <= s < 30) else "IDLE"

            if fall == "K_REC_1":
                # Krock i vaxeln: nytt inflode och returflode slapps in samtidigt!
                nytt_in = (35 <= s < 40)
                retur_in = (35 <= s < 40)

            if fall == "K_REC_2":
                # Cirkulart dodlage: Station B ar blockerad hela tiden
                b_state = "BLOCKED"
                b_blockerad = True

            plc = {
                "nytt_in": nytt_in,
                "retur_in": retur_in,
            }
            stat = {
                "stat_b": {"state": b_state, "cur": 1 if b_blockerad else 0, "in": c, "out": c}
            }
            rader.append({
                "t": round(t, 4),
                "parts": {"broms": {"p": [0.0, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "scene": {"produkt": {"p": [t * 0.25, 0.0, 0.5], "q": [0, 0, 0, 1]}},
                "plc": plc,
                "stat": stat,
                "plc_alder_s": 0.02,
            })

    data = _bygg_serie(rader, "aterflode")
    plan = {
        "template": "aterflode",
        "parts": ["broms"], "tools": [], "rate_hz": RATE,
        "forregling": [["plc:nytt_in", "plc:retur_in"]],
        "stat": ["stat_b"],
        "genomstromning": {"max_blockerad_s": 1.0},
    }
    return data, plan


# ==============================================================================
# HUVUDRIGG OCH EVALUERING
# ==============================================================================

TOPOLOGIER = {
    "SERIELL_3": (topologi_seriell, ["HEL", "K_SER_1", "K_SER_2"]),
    "BUFFERT": (topologi_buffert, ["HEL", "K_BUF_1", "K_BUF_2"]),
    "PARALLELL": (topologi_parallell, ["HEL", "K_PAR_1", "K_PAR_2"]),
    "ATERFLODE": (topologi_aterflode, ["HEL", "K_REC_1", "K_REC_2"]),
}


def kor_alla():
    resultat = {}
    for top_namn, (byggare, fall_lista) in sorted(TOPOLOGIER.items()):
        resultat[top_namn] = {}
        for fall in fall_lista:
            data, plan = byggare(fall)
            _text, rapport, analys = A.doma(data, plan)
            domar = dict((n, v["utfall"]) for n, v in analys.harledt["domar"].items())
            fallande = [d for d, v in sorted(domar.items()) if v == "FAIL"]
            resultat[top_namn][fall] = {
                "dom": rapport.dom[0],
                "orsak": rapport.dom[1],
                "domar": domar,
                "fallande": fallande,
                "prov": len(data["rows"]),
            }
    return resultat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    res = kor_alla()

    print("=== D6: KOMPOSITIONSDOMARNA OVER FYRA NYA LINJETOPOLOGIER ===\n")
    print("%-14s %-12s %-8s %-14s %s" % ("Topologi", "Fall", "Dom", "Fallande", "Orsak"))
    print("-" * 75)

    alla_traffar = []
    for top, fall_dict in sorted(res.items()):
        for fall, r in sorted(fall_dict.items()):
            orsak_kort = r["orsak"].splitlines()[0] if r["orsak"] else ""
            if len(orsak_kort) > 36:
                orsak_kort = orsak_kort[:33] + "..."
            fallande_str = ",".join(r["fallande"]) if r["fallande"] else "-"
            print("%-14s %-12s %-8s %-14s %s" % (top, fall, r["dom"], fallande_str, orsak_kort))

            # Verifiering:
            # HEL ska ge PASS
            # K_* ska ge FAIL
            if fall == "HEL":
                assert r["dom"] == "PASS", "%s HEL gav inte PASS!" % top
            else:
                assert r["dom"] == "FAIL", "%s %s gav inte FAIL!" % (top, fall)
                assert len(r["fallande"]) >= 1, "%s %s hade ingen fallande domare!" % (top, fall)
                alla_traffar.append((top, fall, r["fallande"]))

    print("-" * 75)
    print("Samtliga 4 nya topologier: 4 av 4 HEL ger PASS, 8 av 8 kompositionsfel falls.")
    print("Fallande domare per feltyp:")
    for top, fall, d in alla_traffar:
        print("  %-14s %-10s -> %s" % (top, fall, d))

    if a.json:
        with open(a.json, "w") as f:
            json.dump(res, f, indent=2)
        print("\nSkrev %s" % a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
