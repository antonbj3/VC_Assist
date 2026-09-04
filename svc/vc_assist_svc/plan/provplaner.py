# -*- coding: utf-8 -*-
"""Provplaner ur banken, och matningen av dem.

Uppgiften: bygg minst tio provplaner ur bank/uppgifter/ och MAT hur manga som
gar att planera fullt ut, hur manga antaganden som behovde markas och hur
manga fragor som uppstod. Har byggs de ur HELA banken, inte tio utvalda: ett
urval man valt sjalv mater urvalet.

Tva korningar, och skillnaden mellan dem ar hela poangen:

  utan karta   bank://-vokabularen ar inte VC-URI:er, sa varje komponent blir
               en blockerande fraga. Talet visar hur mycket EN obesvarad fraga
               blockerar.
  med karta    en demonstrationskarta oversatter dem, sa att resten av planen
               gar att mata. Kartan ar INTE verkliga VC-URI:er och far aldrig
               anvandas till en korning - den finns for att svara pa fragan
               "vad ar kvar nar URI-fragan ar besvarad".

    python3 -m vc_assist_svc.plan.provplaner
    python3 -m vc_assist_svc.plan.provplaner --plan T-01

beskriver: svc/vc_assist_svc/plan/*.py, bank/uppgifter/*.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sys

from .fel import Planfel
from .forfining import Forfinare
from .kallor import UPPGIFTSKATALOG  # lagger ocksa bank/ i sokvagen
from .planering import planera

import lasare  # noqa: E402  - bank/lasare.py, nadd genom kallor.py


def demonstrationskarta(bank):
    """bank:// -> en URI som ser ut som en fil, for MATNING och inget annat.

    Ingen av de har URI:erna finns. De existerar for att kunna mata hur mycket
    av en plan som ar fardig nar URI-fragan val ar besvarad, och far aldrig
    laggas i en plan som ska koras: en uppfunnen URI ar ett hart fel (I9).
    """
    return dict((uri, "file:///demonstration/%s.vcm" % uri.split("/")[-1])
                for uri in sorted(bank.katalogindex))


def bygg(uppgift, katalogindex, urikarta=None):
    """(plan, fel). Kastar inte: en uppgift som inte gar att planera ar ett
    matvarde, inte ett avbrott."""
    try:
        spec = Forfinare(katalogindex, urikarta).ur_bankuppgift(uppgift.data)
        return planera(spec), None
    except Planfel as fel:
        return None, "%s: %s" % (type(fel).__name__, fel)


def bygg_alla(bank, urikarta=None):
    ut = []
    for uppgift in bank:
        plan, fel = bygg(uppgift, bank.katalogindex, urikarta)
        ut.append((uppgift.id, plan, fel))
    return ut


def mat(byggen):
    """Talen. En ordbok, sa att bade rapporten och testerna laser samma sak."""
    rakning = collections.Counter()
    lintkoder = collections.Counter()
    kallor = collections.Counter()
    per_plan = []
    ej_byggda = []
    ej_leverabla = []
    for task_id, plan, fel in byggen:
        if plan is None:
            ej_byggda.append((task_id, fel))
            continue
        problem = plan.granska()
        s = plan.sammanfattning()
        s["lintproblem"] = len(problem)
        s["leverabel"] = not problem
        per_plan.append(s)
        for kod, _text in problem:
            lintkoder[kod] += 1
        if problem:
            ej_leverabla.append((task_id, problem))
        for kalla, antal in plan.spec.antaganden_per_kalla().items():
            kallor[kalla] += antal
        rakning["planer"] += 1
        rakning["leverabla"] += 1 if not problem else 0
        for nyckel in ("steg", "verktygssteg", "kontrollsteg", "skrivande_steg",
                       "antaganden", "fragor", "blockerande_fragor",
                       "verifieringskrav", "uppskjutna_krav"):
            rakning[nyckel] += s[nyckel]
        rakning["bredd_max"] = max(rakning["bredd_max"], s["bredd"])
    return {"rakning": dict(rakning), "lintkoder": dict(lintkoder),
            "antagandekallor": dict(kallor), "per_plan": per_plan,
            "ej_byggda": ej_byggda, "ej_leverabla": ej_leverabla}


def _snitt(summa, antal):
    return (summa / float(antal)) if antal else 0.0


def skriv_rapport(bank, strom=sys.stdout):
    p = strom.write
    utan = mat(bygg_alla(bank))
    med = mat(bygg_alla(bank, demonstrationskarta(bank)))
    p("PROVPLANER ur %d bankuppgifter\n" % len(bank))
    for namn, m in (("utan urikarta", utan),
                    ("med demonstrationskarta", med)):
        r = m["rakning"]
        n = r.get("planer", 0)
        p("\n%s\n" % namn.upper())
        p("  planer byggda            %d av %d\n" % (n, len(bank)))
        p("  leverabla (noll brister) %d\n" % r.get("leverabla", 0))
        p("  steg totalt              %d (snitt %.1f per plan)\n"
          % (r.get("steg", 0), _snitt(r.get("steg", 0), n)))
        p("  varav skrivande steg     %d\n" % r.get("skrivande_steg", 0))
        p("  antaganden               %d (snitt %.1f)\n"
          % (r.get("antaganden", 0), _snitt(r.get("antaganden", 0), n)))
        p("  fragor                   %d (varav blockerande %d)\n"
          % (r.get("fragor", 0), r.get("blockerande_fragor", 0)))
        p("  verifieringskrav         %d, uppskjutna %d\n"
          % (r.get("verifieringskrav", 0), r.get("uppskjutna_krav", 0)))
        p("  bredaste lager           %d\n" % r.get("bredd_max", 0))
        p("  antaganden per kalla     %s\n"
          % ", ".join("%s=%d" % kv for kv in sorted(m["antagandekallor"].items())
                      if kv[1]))
        if m["lintkoder"]:
            p("  brister per kod          %s\n"
              % ", ".join("%s=%d" % kv for kv in sorted(m["lintkoder"].items())))
        for task_id, fel in m["ej_byggda"]:
            p("  GICK INTE ATT PLANERA    %s: %s\n" % (task_id, fel))
    p("\nDemonstrationskartan ar INTE verkliga VC-URI:er. Den finns for att\n"
      "mata vad som aterstar nar URI-fragan ar besvarad (I9).\n")
    return utan, med


def main(argv=None):
    a = argparse.ArgumentParser(description="Provplaner ur banken.")
    a.add_argument("--plan", help="skriv en enda plan som JSON")
    a.add_argument("--karta", help="JSON-fil med bank://-URI -> VC-URI")
    args = a.parse_args(argv)

    bank = lasare.ladda(UPPGIFTSKATALOG, strikt=False)
    if getattr(bank, "problem", None):
        sys.stderr.write("VARNING: %d bankuppgifter ar ogiltiga och hoppas over\n"
                         % len(bank.problem))
    urikarta = None
    if args.karta:
        with open(args.karta, encoding="utf-8") as f:
            urikarta = json.load(f)

    if args.plan:
        uppgift = bank[args.plan]
        plan, fel = bygg(uppgift, bank.katalogindex,
                         urikarta or demonstrationskarta(bank))
        if plan is None:
            sys.stderr.write("%s gick inte att planera: %s\n" % (args.plan, fel))
            return 1
        json.dump(plan.till_json(), sys.stdout, ensure_ascii=False, indent=1,
                  sort_keys=True)
        sys.stdout.write("\n")
        return 0

    if urikarta is not None:
        mat_ = mat(bygg_alla(bank, urikarta))
        json.dump(mat_["rakning"], sys.stdout, ensure_ascii=False, indent=1,
                  sort_keys=True)
        sys.stdout.write("\n")
        return 0

    skriv_rapport(bank)
    return 0


if __name__ == "__main__":
    sys.exit(main())
