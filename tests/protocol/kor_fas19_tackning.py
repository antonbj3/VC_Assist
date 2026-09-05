# -*- coding: utf-8 -*-
"""Fas 19: personatackningen som grind.

`docs/spec/48_personaprofiler.md` beskriver sju arbetsprofiler steg for steg.
`docs/spec/47_verktygstackning.md` beskriver API-ytan de arbetar mot. Ingen av
dem hade en fas, och analysen hade aldrig korts. Den har korningen gor den till
ett tal med namnare, och till ett rott utfall nar namnaren ar riggad.

VAD KORNINGEN SVARAR PA
-----------------------
  1. Andelen tackta steg PER PROFIL, med ALLA steg i namnaren.
  2. Hur manga steg som ligger utanfor rackvidd (`UI`/`.NET`). Det talet ar
     lika viktigt som tackningen: det ar arbete anvandaren gor och som agenten
     inte kan gora at hen.
  3. Vilka byggda verktyg som INGEN profil behover. Byggd kapacitet ingen bad
     om ar ocksa ett matt.

DE TRASIGA FALLEN AR FASENS POANG
---------------------------------
En tackningssiffra ar sarskilt latt att gora meningslos - namnaren kan tyst
krympa till det vi klarar. Natten 2026-09-04/05 fangades tre grindar som matte
nagot annat an de pastod. Darfor kors fjorton riggade specer mot samma domare,
och var och en MASTE falla med sin egen kod. En grind utan trasig fixtur ar en
forhoppning som fatt ett filnamn.

    python3 tests/protocol/kor_fas19_tackning.py [--json ut.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc import personatackning as PT                     # noqa: E402
from vc_assist_svc.verktyg import REGISTER                          # noqa: E402


# ==========================================================================
# DE TRASIGA FALLEN
# ==========================================================================
# Var fixtur ar en HEL minispec. Den gronaste varianten star forst som
# kontroll: gar den inte igenom ar det domaren som ar trasig, inte fixturerna.

_GRON = """## P1 — Kontrollen

| # | Arbetssteg | Verkan | Kräver | Täckt av |
|---|---|---|---|---|
| 1 | ladda in en komponent | ändrar | `vcApplication.load` | `load_component` |
| 2 | lista komponenterna | läser | `vcApplication.Components` | `list_components` |
| 3 | koppla mot PLC | ändrar | `.NET:VisualComponents.Connectivity.Core.IServerHandler` | .NET |
| 4 | bläddra i katalogen | läser | `UI:eCatalog` | UI |
| 5 | söka i biblioteket | läser | `TJÄNST:katalogsok` | `search_catalog` |
| 6 | måttsätta | ändrar | `vcDimension.Node1` | saknas |
"""


def _byt(rad_ur, rad_in, text=_GRON):
    if rad_ur not in text:
        raise AssertionError("fixturen bygger pa en rad som inte finns: %r"
                             % rad_ur)
    return text.replace(rad_ur, rad_in)


# (namn, spectext, vantad felkod, vad fallet bevisar)
TRASIGA = [
    ("verktyget finns inte",
     _byt("| `load_component` |", "| `ladda_komponenten` |"),
     "OKANT_VERKTYG",
     "ett steg som pastas tackt av ett verktyg som inte ar registrerat"),

    ("API-namnet finns inte",
     _byt("`vcApplication.load`", "`vcApplication.loadLayoutFile`"),
     "OKANT_API",
     "ett steg som pekar pa ett API-namn indexet inte kanner"),

    ("lasande verktyg pa ett andrande steg",
     _byt("| ladda in en komponent | ändrar | `vcApplication.load` | `load_component` |",
          "| ladda in en komponent | ändrar | `vcApplication.load` | `list_components` |"),
     "FEL_VERKAN",
     "ett verktyg vars deklarerade effect inte matchar stegets verkan"),

    ("namnaren krympte",
     _GRON.replace("| 6 | måttsätta | ändrar | `vcDimension.Node1` | saknas |\n", ""),
     "NAMNAREN_KRYMPTE",
     "ett obekvamt steg som tystnat bort ur profilen"),

    ("hel profil struken",
     _GRON.replace("## P1 — Kontrollen", "## P9 — Nagon annan"),
     "PROFIL_SAKNAS",
     "en hel profil som forsvunnit ur specen"),

    ("falskt UI",
     _byt("| bläddra i katalogen | läser | `UI:eCatalog` | UI |",
          "| bläddra i katalogen | läser | `UI:findComponent` | UI |"),
     "FALSK_UTANFOR",
     "ett steg lyft ur namnaren med UI trots att namnet ar skriptbart"),

    ("falskt UI utan markerat krav",
     _byt("| bläddra i katalogen | läser | `UI:eCatalog` | UI |",
          "| bläddra i katalogen | läser | `vcApplication.findComponent` | UI |"),
     "FALSK_UTANFOR",
     "ett steg markt UI vars alla krav ligger i Python-API:t"),

    ("uppfunnet .NET-namn",
     _byt("`.NET:VisualComponents.Connectivity.Core.IServerHandler`",
          "`.NET:VisualComponents.Connectivity.Core.IPlcBridge`"),
     "OKANT_DOTNET",
     "ett .NET-namn som inte star i docs/referens/vc_dotnet/"),

    ("hal i numreringen",
     _GRON.replace("| 3 | koppla mot PLC | ändrar | `.NET:VisualComponents.Connectivity.Core.IServerHandler` | .NET |\n", ""),
     "TRASIG_NUMRERING",
     "ett steg urklippt mitt i tabellen"),

    ("bade tackt och utanfor rackvidd",
     _byt("| bläddra i katalogen | läser | `UI:eCatalog` | UI |",
          "| bläddra i katalogen | läser | `UI:eCatalog` | `list_components`, UI |"),
     "BADE_OCH",
     "ett steg som raknas bade som tackt och som utanfor rackvidd"),

    ("tjanstemodulen finns inte",
     _byt("`TJÄNST:katalogsok`", "`TJÄNST:katalogorakel`"),
     "OKAND_TJANST",
     "en tjanstekalla som inte finns under svc/vc_assist_svc/"),

    ("tjanstesteg tackt av ett VC-verktyg",
     _byt("| söka i biblioteket | läser | `TJÄNST:katalogsok` | `search_catalog` |",
          "| söka i biblioteket | läser | `TJÄNST:katalogsok` | `list_components` |"),
     "FEL_KALLA",
     "ett steg utan VC-yta som pastas tackt av ett verktyg som kraver VC"),

    ("verkan gar inte att lasa",
     _byt("| lista komponenterna | läser |", "| lista komponenterna | kanske |"),
     "OKAND_VERKAN",
     "en verkanskolumn som varken sager laser eller andrar"),

    ("profil utan steg",
     _GRON + "\n## P2 — Tomheten\n\ningen tabell alls\n",
     "TOM_PROFIL",
     "en profil vars hela tabell ar borta"),

    ("samma profil tva ganger",
     _GRON + "\n" + _GRON.replace("Kontrollen", "Kontrollen igen"),
     "DUBBEL_PROFIL",
     "en profilkod som star tva ganger; den ena tabellen doljer den andra"),
]

# Fixturerna dooms mot ett eget golv och en egen profillista - annars matte de
# repots verkliga spec i stallet for sin egen rigg.
_FIXTURGOLV = {"P1": 6}
_FIXTURPROFILER = ("P1",)

# Fall som ska falla redan i LASNINGEN, alltsa innan nagon dom hinner falla.
# En olasbar spec far aldrig ge en tackningssiffra.
OLASBARA = [
    ("tom tackningskolumn",
     _byt("| `vcDimension.Node1` | saknas |", "| `vcDimension.Node1` |  |"),
     "ett steg utan besked om det ar tackt eller inte"),
    ("tom kravkolumn",
     _byt("| måttsätta | ändrar | `vcDimension.Node1` | saknas |",
          "| måttsätta | ändrar |  | saknas |"),
     "ett steg utan krav gar inte att doma"),
    ("kolumn borttappad",
     _byt("| lista komponenterna | läser | `vcApplication.Components` | `list_components` |",
          "| lista komponenterna | `vcApplication.Components` | `list_components` |"),
     "en rad med fyra kolumner i stallet for fem"),
]


def kor_trasiga(domare):
    """Kor varje riggad spec. Returnerar [(namn, vantad, utfall, ok)]."""
    ut = []
    for namn, text, vantad, varfor in TRASIGA:
        try:
            profiler = PT.las_profiler(text)
            koder = sorted(set(f.kod for f in domare.doma(profiler)))
        except PT.Specfel as e:
            koder = ["SPECFEL: %s" % e]
        ut.append((namn, vantad, koder, vantad in koder, varfor))
    return ut


def kor_olasbara():
    ut = []
    for namn, text, varfor in OLASBARA:
        try:
            PT.las_profiler(text)
            ut.append((namn, "ingen Specfel - specen last utan invandning",
                       False, varfor))
        except PT.Specfel as e:
            ut.append((namn, str(e)[:70], True, varfor))
    return ut


# ==========================================================================
# KORNINGEN
# ==========================================================================

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    p.add_argument("--spec", default=PT.SPEC)
    a = p.parse_args(argv)

    print("=== FAS 19: PERSONATACKNINGEN ===\n")
    print("  spec:      %s" % os.path.relpath(a.spec, _ROT))
    print("  register:  %d verktyg" % len(REGISTER))

    profiler = PT.las_spec(a.spec)
    domare = PT.Domare()
    print("  index:     %d symboler" % len(domare.index.symboler))
    print("  .NET-yta:  %d namn\n" % len(domare.dotnet))

    # ---- 1. tackningen -----------------------------------------------------
    print("1. TACKNING PER PROFIL - namnaren ar ALLA steg\n")
    print("   %-4s %-38s %5s %6s %7s %8s %8s"
          % ("", "profil", "steg", "tackta", "utanfor", "obyggda", "andel"))
    tal = []
    for profil in profiler:
        t = PT.rakna(profil)
        tal.append(t)
        print("   %-4s %-38s %5d %6d %7d %8d %7.0f %%"
              % (t.kod, t.namn[:38], t.steg, t.tackta, t.utanfor, t.obyggda,
                 100 * t.andel_av_allt))
    s = PT.sammanfattning(profiler)
    print("   %-4s %-38s %5d %6d %7d %8d %7.0f %%"
          % ("", "SUMMA", s["steg"], s["tackta"], s["utanfor"], s["obyggda"],
             100.0 * s["tackta"] / max(1, s["steg"])))
    print("\n   Andelen ar tackta/steg. Talet inom rackhall (utan UI och .NET)")
    print("   star for sig, for det ar tva olika fragor:")
    for t in tal:
        print("     %-4s %2d av %2d inom rackhall = %3.0f %%  (%d steg utanfor)"
              % (t.kod, t.tackta, t.inom_rackhall,
                 100 * t.andel_inom_rackhall, t.utanfor))

    # ---- 2. utanfor rackvidd ----------------------------------------------
    print("\n2. STEG UTANFOR RACKVIDD - arbete agenten inte kan gora at nagon\n")
    utanfor = [(st, profil) for profil in profiler for st in profil.steg
               if st.utanfor_rackvidd]
    for st, _profil in utanfor:
        markor = ", ".join(t for t in st.tackt_av if t in PT.UTANFOR)
        print("   %-6s %-6s %-52s %s"
              % (st.profil, markor, st.text[:52],
                 ", ".join(st.kraver)[:60]))
    print("   %d steg av %d (%.0f %%)"
          % (len(utanfor), s["steg"], 100.0 * len(utanfor) / max(1, s["steg"])))

    # ---- 3. byggd kapacitet ingen bad om -----------------------------------
    print("\n3. VERKTYG INGEN PROFIL BEHOVER\n")
    oanvanda = PT.verktyg_ingen_profil_behover(profiler, REGISTER)
    for v in oanvanda:
        print("   %-28s %-12s %s" % (v, REGISTER[v].doman, REGISTER[v].effect))
    print("   %d av %d verktyg (%.0f %%)"
          % (len(oanvanda), len(REGISTER),
             100.0 * len(oanvanda) / max(1, len(REGISTER))))

    # ---- 3b. det gamla pastaendet om utbildaren ---------------------------
    # 48 pastod fore fas 19 att utbildaren "kraver inte en enda ytterligare
    # API-yta" an saljaren, och drog darfor slutsatsen att hon inte behovde en
    # egen profil. Pastaendet gar att prova, sa det provas.
    print("\n3b. UTBILDARENS EGNA YTOR - det gamla pastaendet provat\n")
    per_kod = {p.kod: set(PT.api_namn([p])) for p in profiler}
    egna = sorted(per_kod.get("P7", set()) - per_kod.get("P5", set()))
    print("   P7 pekar pa %d API-namn, varav %d INTE finns i P5:"
          % (len(per_kod.get("P7", ())), len(egna)))
    for namn in egna:
        print("     %s" % namn)
    print("   Pastaendet 'kraver inte en enda ytterligare API-yta' ar %s."
          % ("SANT" if not egna else "FALSKT"))

    # ---- 4. domen over den verkliga specen --------------------------------
    print("\n4. DOMEN OVER SPECEN SJALV\n")
    fel = domare.doma(profiler)
    for f in fel:
        print("   %s" % f)
    print("   %d fallningar" % len(fel))

    # ---- 5. de trasiga fallen ---------------------------------------------
    print("\n5. TRASIGA FALL - var och en MASTE falla med sin egen kod\n")
    gron_ok = not domare_pa_fixtur(_GRON)
    print("   %-3s %-34s %s" % ("", "kontrollen (ska INTE falla)",
                                "GRON" if gron_ok else "ROD"))
    utfall = kor_trasiga(PT.Domare(index=domare.index, register=REGISTER,
                                   dotnet=domare.dotnet,
                                   golv=_FIXTURGOLV, kanda=_FIXTURPROFILER))
    for namn, vantad, koder, ok, varfor in utfall:
        print("   %-3s %-34s %-18s %s"
              % ("ok" if ok else "ROD", namn, vantad,
                 ("fick %s" % ",".join(koder)) if not ok else varfor))

    print("\n   Fall som ska falla redan i lasningen:\n")
    olasbara = kor_olasbara()
    for namn, besked, ok, varfor in olasbara:
        print("   %-3s %-34s %s" % ("ok" if ok else "ROD", namn,
                                    varfor if ok else besked))

    # ---- 6. utfallet -------------------------------------------------------
    trasiga_ok = sum(1 for _n, _v, _k, ok, _w in utfall if ok)
    olasbara_ok = sum(1 for _n, _b, ok, _w in olasbara if ok)
    gront = (not fel and gron_ok
             and trasiga_ok == len(utfall) and olasbara_ok == len(olasbara))

    print("\n=== UTFALL ===")
    print("  specen sjalv:            %d fallningar" % len(fel))
    print("  kontrollen:              %s" % ("gron" if gron_ok else "ROD"))
    print("  trasiga fall fallda:     %d av %d" % (trasiga_ok, len(utfall)))
    print("  olasbara fall avvisade:  %d av %d" % (olasbara_ok, len(olasbara)))
    print("  FAS 19: %s" % ("GRON" if gront else "ROD"))

    print("\n  Vad korningen INTE visar:")
    print("    Stegen ar oviktade. Att spara en layout och att bygga ett helt")
    print("    processflode raknas som ett steg var.")
    print("    En UI-markor gar att bevisa FALSK, inte SANN: en pahittad")
    print("    UI:-token passerar. Den oppna riktningen kan bara gora")
    print("    namnaren storre, aldrig mindre.")
    print("    Ingenting har korts mot en levande VC. Domen ar spec mot index")
    print("    och register, inte mot en scen.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({
                "profiler": [{"kod": t.kod, "namn": t.namn, "steg": t.steg,
                              "tackta": t.tackta, "utanfor": t.utanfor,
                              "obyggda": t.obyggda,
                              "inom_rackhall": t.inom_rackhall}
                             for t in tal],
                "summa": {k: s[k] for k in ("profiler", "steg", "tackta",
                                            "utanfor", "obyggda")},
                "verktyg_totalt": len(REGISTER),
                "verktyg_ingen_behover": list(oanvanda),
                "fallningar": [{"kod": f.kod, "var": f.var, "text": f.text}
                               for f in fel],
                "trasiga": [{"namn": n, "vantad": v, "fick": k, "ok": ok}
                            for n, v, k, ok, _w in utfall],
                "olasbara": [{"namn": n, "ok": ok} for n, _b, ok, _w in olasbara],
                "gront": gront,
            }, f, indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0 if gront else 1


def domare_pa_fixtur(text):
    """Fallningarna en fixtur ger mot fixturgolvet. Tom lista = gron."""
    return PT.Domare(golv=_FIXTURGOLV, kanda=_FIXTURPROFILER).doma(
        PT.las_profiler(text))


if __name__ == "__main__":
    sys.exit(main())
