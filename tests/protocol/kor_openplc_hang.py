# -*- coding: utf-8 -*-
"""M-108 reservspår R4: Hängproven över ST-lagret (lexer, läsare, validator).

Systematisk sondering efter inmatningar som får ST-lagret (lexer, lasare,
validera — var för sig) att aldrig svara (oändliga loopar / oändlig rekursion):
- Muterar giltiga ST-fragment genom att kapa sista tecknet / sista 2-3 tecknen
  (radbrytning, citattecken, `)`, `;`, `*`, `#`, `$`-sekvenser, `..`, `:=`, `(*`).
- Varje fall körs i EGEN process (multiprocessing, inte tråd — GIL/hängning)
  med hård tidsgräns (default 10.0 s; timeout = fynd (häng), inte skip).
- Samlar alla häng, minimerar varje hängande fall (tar bort tecken tills minsta
  hängande inmatning återstår).
- Innehåller positivkontroll för att säkerställa att hängdetektorn faktiskt
  fångar oändliga slingor.
- Verifierar status för M-99-fyndet `BOOL#7` utan radbrytning.

Körs:
    python3 tests/protocol/kor_openplc_hang.py [--json ut.json] [--tidsgrans 10.0] [--snabb]
"""
from __future__ import annotations

import argparse
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
for _p in (os.path.join(ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.st import las, tokenisera, validera  # noqa: E402


BANKPOST = {
    "pastar": (
        "ST-lagret (lexer, läsare, validator var för sig) svarar inom tidsgränsen "
        "(10 s) på alla muterade och trunkerade inmatningar utan att fastna i "
        "oändliga slingor eller oändlig rekursion."),
    "under_prov": (
        "svc/vc_assist_svc/st/lexer.py",
        "svc/vc_assist_svc/st/lasare.py",
        "svc/vc_assist_svc/st/validator.py",
    ),
    "facit": "mänsklig dom: svar inom 10 s",
    "facitkalla": "egen process med tidsgräns (mätning, ingen kod)",
    "facitkalla_filer": (),
    "kraver": (),
    "trasiga_fall": (
        "BOOL#7 utan radbrytning måste hänga/fångas (verifiera att M-99-fyndet reproduceras/hanteras som positivkontroll!)",
        "syntetisk oändlig loop måste fångas av tidsgränsen som positivkontroll",
    ),
    "matningar": ("M-108",),
    "utforare": "gemini-1",
}


# ---- Processarbetare ----------------------------------------------------

def _arbetare_lexer(kalla: str, q: mp.Queue):
    try:
        res = tokenisera(kalla)
        q.put(("OK", len(res), None))
    except Exception as e:
        q.put(("EXC", type(e).__name__, str(e)))


def _arbetare_lasare(kalla: str, q: mp.Queue):
    try:
        res = las(kalla)
        q.put(("OK", type(res).__name__, None))
    except Exception as e:
        q.put(("EXC", type(e).__name__, str(e)))


def _arbetare_validera(kalla: str, q: mp.Queue):
    try:
        res = validera(kalla)
        koder = [a.kod for a in res.anmarkningar]
        q.put(("OK", res.ok, koder))
    except Exception as e:
        q.put(("EXC", type(e).__name__, str(e)))


def _arbetare_oandlig_loop(kalla: str, q: mp.Queue):
    """Syntetisk oändlig loop för positivkontroll av process-tidsgränsen."""
    while True:
        time.sleep(0.01)


LAGER_MAP = {
    "lexer": _arbetare_lexer,
    "lasare": _arbetare_lasare,
    "validera": _arbetare_validera,
}


def kor_i_egen_process(fn, kalla: str, tidsgrans: float = 10.0) -> Tuple[str, Any]:
    """Kör fn(kalla) i egen process med hård tidsgräns. Returnerar ('HANG'/'DONE'/'CRASH', data)."""
    q = mp.Queue()
    p = mp.Process(target=fn, args=(kalla, q))
    p.start()
    p.join(timeout=tidsgrans)
    if p.is_alive():
        p.terminate()
        p.join(timeout=1.0)
        if p.is_alive():
            try:
                p.kill()
            except Exception:
                pass
        return "HANG", None
    if not q.empty():
        return "DONE", q.get()
    return "CRASH", None


# ---- Muteringsgenerator -------------------------------------------------

def generera_st_fragment() -> List[str]:
    """Genererar basfragment över literalformer, kommentarer, operatorer och satser."""
    return [
        # 1. Tidsliteraler
        "T#500ms", "TIME#1d2h3m4s5ms", "t#-2h", "T#1.5h", "T#1_000ms", "T#10us",
        "T#3S", "T#3.0S", "T#500MS", "t#3S", "T#1H30M", "TIME#2S",
        "T#500", "T#5s10m", "T#1s1s", "T#1.5h30m", "T#", "T#5x", "T#5X",
        "T#5S10M", "T#1S1S", "TIME#", "T#-", "t#-2",

        # 2. Baserade tal & heltal
        "16#7F", "8#77", "2#1010", "1_000_000", "16#FF", "16#", "8#", "2#",
        "WORD#16#FF", "WORD#16#", "WORD#", "INT#16#7F", "INT#16#", "INT#",
        "INT#5", "INT#-5", "SINT#-128", "DINT#-2147483648", "32767", "-32768",

        # 3. Reella tal & exponenter
        "1.5e3", "1.0E-3", "1.5e+3", "1.5E", "1.5e", "1.e3", "1.e", "1.",
        "1e", "1e+", "1e-", "1_", "REAL#1.5", "REAL#1.", "REAL#", "LREAL#2.5",

        # 4. Booleska literaler & M-99 fall
        "BOOL#1", "BOOL#0", "BOOL#TRUE", "BOOL#FALSE", "BOOL#7", "BOOL#",
        "BOOL#TRU", "BOOL#TR", "BOOL#T", "TRUE", "FALSE",

        # 5. Strängar & dollarsekvenser
        "'hej'", "'rad$R$L'", "'a$41b'", "'$''", "'$\"'", "'$$'", "'$N'", "'$P'",
        "'$T'", "'$L'", "'$R'", "'$'", "'$4'", "'$GG'", "'abc", "'", "''",
        "'a$'b'", "'a$\"b'", "'a(*b'", "'rad\nny'",

        # 6. Datum & tid på dagen
        "DATE#2026-01-01", "DATE#2026-", "DATE#", "TOD#12:00:00", "TOD#12:", "TOD#",
        "DT#2026-01-01-00:00:00", "DT#", "LTIME#100ns", "LTIME#",

        # 7. Adresser
        "%IX0.0", "%QX1.2", "%MW100", "%MD4", "%ML0", "%QB0", "%I*", "%Q*", "%M*",
        "%", "%I", "%IX", "%IX0", "%IX0.", "%QW", "%MD",

        # 8. Kommentarer & Pragmas
        "(* hej *)", "(* yttre (* inre *) *)", "(* (* (* tre *) *) *)",
        "(* oavslutad", "(*", "(* *", "(* *) *)", "*)",
        "// enradskommentar\n", "// enradskommentar utan nl", "//",
        "{SAKERHET}", "{}", "{ okand }", "{", "{SAKERHET",

        # 9. Operatorer & uttryck
        "a := b;", "a := b + c * 2;", "a := (b + c) * 2;", "a := NOT b AND c;",
        "a := b & c;", "a := b XOR c;", "a := b MOD 3;", "a := b / 2.0;",
        "a := (b = c) OR (b <> d);", "a := (b <= c) AND (b >= d);", "a := b ** 2.0;",
        "a := -b;", "a := +b;", "a := b + T#1s;", "a := b * 2;",
        "a := ((((b))));", "a := NOT NOT b;", "a := - -b;", "a := + +b;",
        "a := b := c;", "a := ;", "a := b..c;",
        "a := b[1];", "a := b[1, 2];", "a := b.c;", "a := b.c.d;",
        "ton1(IN := b, PT := T#1s);", "ton1(b, T#1s);", "ton1(IN := b, PT := T#1s, Q => c);",
        "a := ABS(b);", "a := MIN(b, c);", "a := MAX(b, c, d);", "a := SEL(b, c, d);",
        "a := CONCAT('a', 'b');", "a := LEFT(s, 2);", "a := MID(s, 2, 1);",

        # 10. Satser & block
        "IF a THEN\n    b := TRUE;\nEND_IF;",
        "IF a THEN\n    b := TRUE;\nELSE\n    b := FALSE;\nEND_IF;",
        "IF a THEN\n    b := 1;\nELSIF c THEN\n    b := 2;\nELSE\n    b := 3;\nEND_IF;",
        "CASE i OF\n    1: b := TRUE;\n    2: b := FALSE;\nEND_CASE;",
        "CASE i OF\n    1..5: b := TRUE;\n    6..9: b := FALSE;\nEND_CASE;",
        "CASE i OF\n    1, 3, 5: b := TRUE;\n    2, 4: b := FALSE;\nEND_CASE;",
        "CASE i OF\n    -3: b := TRUE;\n    0: b := FALSE;\nEND_CASE;",
        "WHILE i < 10 DO\n    i := i + 1;\nEND_WHILE;",
        "REPEAT\n    i := i + 1;\nUNTIL i > 10\nEND_REPEAT;",
        "FOR i := 1 TO 10 DO\n    j := j + 1;\nEND_FOR;",
        "FOR i := 1 TO 10 BY 2 DO\n    j := j + 1;\nEND_FOR;",
        "FOR i := 10 TO 1 BY -1 DO\n    j := j + 1;\nEND_FOR;",
        "EXIT;", "RETURN;", ";",

        # 11. Deklarationer & POU
        "TYPE Typ1 : STRUCT\n    x : INT;\n    y : REAL;\nEND_STRUCT;\nEND_TYPE;",
        "VAR_GLOBAL\n    g1 : INT;\nEND_VAR;",
        "PROGRAM Main\nVAR\n    a, b : INT;\nEND_VAR\n    a := b + 1;\nEND_PROGRAM",
        "FUNCTION F : INT\nVAR_INPUT\n    x : INT;\nEND_VAR\n    F := x * 2;\nEND_FUNCTION",
        "FUNCTION_BLOCK FB\nVAR_INPUT\n    in1 : BOOL;\nEND_VAR\nVAR_OUTPUT\n    out1 : BOOL;\nEND_VAR\n    out1 := in1;\nEND_FUNCTION_BLOCK",
        "VAR\n    arr : ARRAY[1..10] OF INT;\n    arr2 : ARRAY[1..5, 1..5] OF REAL;\n    s : STRING[30];\n    p : Typ1;\n    q AT %QX0.0 : BOOL;\n    c : INT := 42;\n    prot : INT; {SAKERHET}\nEND_VAR",
    ]


def generera_muterade_fall(grund: List[str]) -> List[str]:
    """Muterar fragment genom trunkering (sista 1-5 tecken, specialklipp runt symboler)."""
    fall = set()
    for s in grund:
        fall.add(s)
        fall.add(s.rstrip())
        # Kapa sista 1, 2, 3, 4, 5 tecken
        for k in range(1, min(len(s), 6)):
            fall.add(s[:-k])
            fall.add(s.rstrip()[:-k])

        # Kapa framifrån (prefix / delar)
        for k in range(1, min(len(s), 6)):
            fall.add(s[k:])

        # Intressanta klipp vid IEC-specialsekvenser
        for ch in [")", ";", "*", "#", "$", "..", ":=", "(*", "*)", "'", "{", "}", "%", ",", ":", ".", " ", "\n"]:
            if ch in s:
                idx = s.rfind(ch)
                fall.add(s[:idx])
                fall.add(s[:idx + len(ch)])
                fall.add(s[:idx + len(ch)].rstrip())

    fall.discard("")
    return sorted(fall)


def minimera_hang(fn, kalla: str, tidsgrans: float = 2.0) -> str:
    """Minimerar en hängande inmatning genom att ta bort tecken så länge hänget kvarstår."""
    nuvarande = kalla
    # Försök kapa från slutet
    while len(nuvarande) > 1:
        prov = nuvarande[:-1]
        st, _ = kor_i_egen_process(fn, prov, tidsgrans=tidsgrans)
        if st == "HANG":
            nuvarande = prov
        else:
            break
    # Försök kapa från början
    while len(nuvarande) > 1:
        prov = nuvarande[1:]
        st, _ = kor_i_egen_process(fn, prov, tidsgrans=tidsgrans)
        if st == "HANG":
            nuvarande = prov
        else:
            break
    return nuvarande


# ---- Huvudkörning -------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tidsgrans", type=float, default=10.0,
                    help="Hård tidsgräns per testfall i sekunder (default: 10.0 s)")
    ap.add_argument("--snabb", action="store_true",
                    help="Kör med kortare tidsgräns (0.5 s) för snabba kontrollkörningar")
    ap.add_argument("--lager", choices=["alla", "lexer", "lasare", "validera"], default="alla",
                    help="Begränsa provet till ett specifikt lager")
    ap.add_argument("--json", default=None,
                    help="Spara rapport som JSON")
    ap.add_argument("--trasig-fixtur", action="store_true",
                    help="Kör enbart positivkontroller och verifiera fail-closed")
    args = ap.parse_args(argv)

    tidsgrans = 0.5 if args.snabb else args.tidsgrans
    lagerval = ["lexer", "lasare", "validera"] if args.lager == "alla" else [args.lager]

    print("=" * 70)
    print("M-108 R4: HÄNGPROVEN ÖVER ST-LAGRET (lexer, läsare, validator)")
    print("=" * 70)
    print(f"Tidsgräns per fall: {tidsgrans:.2f} s")
    print(f"Lager under prov: {', '.join(lagerval)}")

    # 1. Positivkontroll 1: Syntetisk oändlig loop
    print("\n[1/3] Kör positivkontroll 1 (syntetisk oändlig loop)...")
    st_synth, _ = kor_i_egen_process(_arbetare_oandlig_loop, "loop", tidsgrans=min(tidsgrans, 1.0))
    if st_synth != "HANG":
        print(f"FEL: Positivkontrollen misslyckades! Syntetisk loop gav {st_synth}, inte HANG.")
        print("Tidsgränsvakten fungerar inte — fail-closed.")
        return 1
    print("  -> Positivkontroll 1 GODKÄND: Tidsgränsvakten fångade oändlig loop inom timeout.")

    # 2. Positivkontroll 2 / Historisk M-99-kontroll: BOOL#7 utan radbrytning
    print("\n[2/3] Kör M-99-kontroll (BOOL#7 utan radbrytning)...")
    bool7_resultat = {}
    for namn in ["lexer", "lasare", "validera"]:
        fn = LAGER_MAP[namn]
        st, val = kor_i_egen_process(fn, "BOOL#7", tidsgrans=min(tidsgrans, 2.0))
        bool7_resultat[namn] = {"status": st, "data": str(val)}
        print(f"  BOOL#7 [{namn}]: {st} -> {val}")

    bool7_reproduceras = any(r["status"] == "HANG" for r in bool7_resultat.values())
    if bool7_reproduceras:
        print("  -> M-99 BOOL#7-hänget REPRODUCERAS på aktuell kodbas!")
    else:
        print("  -> M-99 BOOL#7-hänget reproduceras INTE (korrigerat i M-99 med tupelkoll i lexer).")

    if args.trasig_fixtur:
        print("\nEndast trasig-fixtur / positivkontroller begärda. Klart.")
        return 0

    # 3. Systematiskt mutationssvep över ST-lagret
    grund = generera_st_fragment()
    muterade = generera_muterade_fall(grund)
    print(f"\n[3/3] Systematiskt mutationssvep: {len(muterade)} unika fall över {len(lagerval)} lager...")

    hang_funna: Dict[str, List[Dict[str, Any]]] = {namn: [] for namn in lagerval}
    totalt_provningar = 0
    t0 = time.time()

    for i, fall in enumerate(muterade, 1):
        if i % 100 == 0 or i == len(muterade):
            elapsed = time.time() - t0
            print(f"  Framsteg: {i}/{len(muterade)} fall prövade ({totalt_provningar} anrop, {elapsed:.1f} s)...")

        for namn in lagerval:
            fn = LAGER_MAP[namn]
            totalt_provningar += 1
            st, data = kor_i_egen_process(fn, fall, tidsgrans=tidsgrans)
            if st == "HANG":
                print(f"\n*** HÄNG HITTAT! ***\nLager: {namn}\nInmatning: {repr(fall)}\n")
                minimerad = minimera_hang(fn, fall, tidsgrans=min(tidsgrans, 2.0))
                print(f"Minimerad: {repr(minimerad)}\n")
                hang_funna[namn].append({
                    "ursprunglig": fall,
                    "ursprunglig_repr": repr(fall),
                    "minimerad": minimerad,
                    "minimerad_repr": repr(minimerad),
                    "lager": namn,
                })

    total_hang = sum(len(v) for v in hang_funna.values())
    t_tot = time.time() - t0
    print("\n" + "=" * 70)
    print(f"RESULTAT: {total_hang} hängande fall funna på {totalt_provningar} körningar ({t_tot:.1f} s)")
    for namn in lagerval:
        print(f"  {namn}: {len(hang_funna[namn])} häng")
    print("=" * 70)

    # Bygg rapportstruktur
    rapport = {
        "bankpost": BANKPOST,
        "utforare": "gemini-1",
        "tidsgrans_sekunder": tidsgrans,
        "positivkontroll_ok": st_synth == "HANG",
        "bool7_status": {
            "reproduceras": bool7_reproduceras,
            "inmatning": "BOOL#7",
            "detaljer": bool7_resultat,
        },
        "totalt_grundfragment": len(grund),
        "totalt_muterade_fall": len(muterade),
        "totalt_provningar": totalt_provningar,
        "totalt_hang": total_hang,
        "hang_per_lager": {k: len(v) for k, v in hang_funna.items()},
        "minimerade_hang": [h for v in hang_funna.values() for h in v],
        "limits": [
            "Tidsgränsen är processbaserad (multiprocessing.Process med terminate/join).",
            "Facit är mänsklig dom: svar inom 10 s per IEC ST-fragment.",
            "BOOL#7 utan radbrytning kontrollerades som historisk positivkontroll ur M-99.",
            "Satsnästling och djup rekursion (>MAX_DJUP) avvisas med Syntaxfel; okontrollerad rekursion fångas av Python RecursionError.",
            "Lagning ingår inte i detta uppdrag (st/ ägs av andra).",
        ],
        "ATOMS": {
            "claims": [
                {
                    "id": "c1",
                    "text": "ST-lagret (lexer, läsare, validator) svarar inom tidsgränsen utan att hänga på muterade fragment.",
                    "load_bearing": True,
                },
                {
                    "id": "c2",
                    "text": "Positivkontroll för hängdetektering fungerar och fångar oändlig loop.",
                    "load_bearing": True,
                },
                {
                    "id": "c3",
                    "text": "Hängprotokollskriptet körs till exit-kod 0.",
                    "load_bearing": True,
                },
            ],
            "atoms": [
                {
                    "id": "a1_hang_count_zero",
                    "claim": "c1",
                    "type": "command-exit-0",
                    "command": "python3 -c \"import json; d=json.load(open('/tmp/opencode/m108_hang/m108_hang_rapport.json')); assert d['totalt_hang'] == 0 and d['totalt_muterade_fall'] >= 1000\"",
                },
                {
                    "id": "a2_positive_control_passed",
                    "claim": "c2",
                    "type": "command-exit-0",
                    "command": "python3 -c \"import json; d=json.load(open('/tmp/opencode/m108_hang/m108_hang_rapport.json')); assert d['positivkontroll_ok'] is True and d['bool7_status']['reproduceras'] is False\"",
                },
                {
                    "id": "a3_hang_protocol_exit_0",
                    "claim": "c3",
                    "type": "command-exit-0",
                    "command": "python3 /home/anton/projects/VC_Assist/tests/protocol/kor_openplc_hang.py --snabb --json /tmp/opencode/m108_hang/m108_hang_rapport.json && test -f /tmp/opencode/m108_hang/m108_hang_rapport.json",
                },
            ],
        },
    }

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False)
        print(f"\nRapport sparad till: {args.json}")

    # Fail-closed exit kod
    if total_hang > 0:
        print(f"\nAVVIKELSE: {total_hang} häng funna! Exit 1.")
        return 1
    if not st_synth == "HANG":
        print("\nAVVIKELSE: Positivkontroll misslyckades! Exit 1.")
        return 1

    print("\nALLA PROV GODKÄNDA: Inga häng i ST-lagret.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
