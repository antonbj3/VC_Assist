# -*- coding: utf-8 -*-
"""Domaren: håller en ST-lösning mot uppgiftens spårfacit.

Varför den finns. Före M-45 bar varje uppgift i banken ett facit som bara gick
att döma efter en körning i Visual Components: en ögonrapport med rader ur ögats
grammatik. Ingen uppgift var körd, så noll uppgifter hade ett facit som gick att
avgöra mekaniskt idag. Mätningen står i `docs/matningar/M-45_bankens_tackning.md`.

Spårfacit är den andra facitformen, och den ligger **bredvid** ögondomen, aldrig
i stället för den (invariant I1: ögat fäller domen om scenen). Spårfacit dömer
en annan storhet: håller styrlogiken sitt kontrakt mot insignalerna över tid?
Det är den storhet en driftsättare provar med en simulator på skrivbordet innan
någon släpper in en robot i cellen, och den går att döma utan VC.

Tre sorters påstående, alla mekaniska:

* **punktkrav** — vid tiden t, med de här insignalerna, ska utsignalerna ha
  precis de här värdena. Tiden ligger med avsikt minst två scan från närmaste
  flank, så en implementation som råkar svara ett scan senare inte fälls för det.
* **invariant** — närhelst villkoret gäller, ska kravet gälla. Det är
  förreglingens form: "grinden får aldrig vara öppen när nödstoppet är brutet".
  Prövas i varje scan, inte i utvalda punkter.
* **flankräkning** — antalet stigande eller fallande flanker på en utgång inom
  ett fönster. Det är singuleringens och taktens form: "exakt en puls per detalj".
  Det är också den enda mekaniska domen över felklass `F15`, flank och latch.

Facit skrivs alltid i uppgiften, av en människa, före försöket. **Domaren tar
aldrig emot en assertion som modellen själv har skrivit.** Skälet är mätt av
någon annan: Koziolek m.fl. (arXiv 2405.01874) lät en modell generera testfall
till OSCAT-block och fick 0 till 50 % korrekta assertions, sämst på just
timers. En genererad assertion som blir facit mäter modellens självbild.

Varje uppgift med spårfacit bär också minst ett **motbevis**: en lösning som ser
riktig ut men bryter mot ett krav, och som domaren måste fälla på namngivna
brister. En grind utan trasig fixtur mäter ingenting (regel S2).

beskriver: bank/domare.py, bank/schema.py, svc/vc_assist_svc/st/tolk.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, ".."))
for _p in (_HAR, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.st import tolk as _tolk  # noqa: E402

Tolkfel = _tolk.Tolkfel

# Hur nära en punktavläsning får ligga en flank i spåret. Under den marginalen
# skiljer facit inte längre på "logiken svarar ett scan senare" och "logiken gör
# fel", och en bänk som fäller på ett scan mäter implementationsstil i stället
# för styrlogik. Två scan är PLC:ns egen uppmätta svarstid (M-20: exakt två scan,
# 40,0 ms vid 20 ms scanperiod), så marginalen är den tid kedjan bevisligen tar.
MARGINAL_SCAN = 2               # Mätt i M-20.


class Domsfel(Exception):
    """Spårfacit går inte att köra. Kastar hellre än dömer på en halv körning."""


class Brist(object):
    """En namngiven överträdelse. Namnet är stabilt, så ett motbevis kan peka ut
    exakt vilken brist det ska fällas på."""

    def __init__(self, kod, text):
        self.kod = kod
        self.text = text

    def __repr__(self):
        return "<Brist %s: %s>" % (self.kod, self.text)

    def __eq__(self, annat):
        return isinstance(annat, Brist) and self.kod == annat.kod

    def __hash__(self):
        return hash(self.kod)


class Dom(object):
    def __init__(self, task_id, brister, scan_kord=0):
        self.task_id = task_id
        self.brister = list(brister)
        self.scan_kord = scan_kord

    @property
    def godkand(self):
        return not self.brister

    @property
    def koder(self):
        return [b.kod for b in self.brister]

    def __repr__(self):
        return "<Dom %s %s (%d brister)>" % (
            self.task_id, "GODKAND" if self.godkand else "UNDERKAND",
            len(self.brister))

    def text(self):
        if self.godkand:
            return "%s: GODKAND, %d scan" % (self.task_id, self.scan_kord)
        rader = ["%s: UNDERKAND, %d brister" % (self.task_id, len(self.brister))]
        for b in self.brister:
            rader.append("  %s\n      %s" % (b.kod, b.text))
        return "\n".join(rader)


# ------------------------------------------------------------------ hjälp

def _signalkarta(post):
    typer, riktningar = {}, {}
    for s in (post.get("control") or {}).get("signals") or []:
        if not isinstance(s, dict) or "name" not in s:
            continue
        typer[s["name"].upper()] = s.get("type")
        riktningar[s["name"].upper()] = s.get("dir")
    return typer, riktningar


def _lika(vantat, faktiskt):
    if isinstance(vantat, bool) or isinstance(faktiskt, bool):
        return bool(vantat) == bool(faktiskt)
    if isinstance(vantat, (int, float)) and isinstance(faktiskt, (int, float)):
        return abs(float(vantat) - float(faktiskt)) <= 1e-9
    return vantat == faktiskt


def _skriv(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    return repr(v)


# ------------------------------------------------------------------ domen

def forgrindsbrist(stationsdom):
    """Den fällande förgrindens EGNA ord, ordagrant. None om alla fyra höll.

    `stationsdom` kommer ur `svc.vc_assist_svc.plc.stationsgrind.granska_station`
    och bär grind 1 till 4. Domaren bygger ingen egen grindkedja och skriver
    aldrig om en grinds svar (invariant I1): den läser Stationsdom och stannar.

    Ordningen är specens: första grinden som fäller bestämmer klassen
    (`docs/spec/82_felklasser.md`, sorteringsregel 1). Ett spår som körs på kod
    som inte klarat grind 1 till 4 mäter fel storhet — koden når aldrig en PLC.
    """
    if stationsdom is None or stationsdom.ok:
        return None
    namn = stationsdom.forsta_fallande
    utfall = stationsdom.forgrindar.get(namn, "ej kord")
    egen = (stationsdom.utdata or {}).get(namn) or ""
    text = "grinden %s fällde: %s" % (namn, utfall)
    if egen.strip():
        text += "\n" + egen.strip()
    return Brist("forgrind:%s" % namn, text)


def dom(post, st_text, spar=None, stationsdom=None):
    """Dömer `st_text` mot uppgiftens spårfacit. Lämnar en Dom.

    `stationsdom` är valfri. Ges den och har någon av grind 1 till 4 fällt,
    returneras den grindens egen dom och spåret körs inte alls.

    Kastar Domsfel om uppgiften saknar spårfacit — en tyst godkänd dom på en
    uppgift utan facit är precis den falska grönt hela banken är skriven emot.
    """
    brist = forgrindsbrist(stationsdom)
    if brist is not None:
        return Dom(post.get("task_id"), [brist], 0)
    facit = spar if spar is not None else post.get("facit_spar")
    if not isinstance(facit, dict):
        raise Domsfel("%s har inget facit_spar att döma mot"
                      % post.get("task_id"))
    typer, riktningar = _signalkarta(post)
    scan_ms = float(facit.get("scan_ms") or _tolk.SCAN_MS)
    brister = []
    scan_totalt = 0

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
            brister.append(Brist("tolkfel:%s" % sid, str(fel)))
            break

        mina_inv = [i for i in invarianter
                    if i.get("sekvens") in (None, "*", sid)]
        inv_falld = set()
        mina_flank = [f for f in flanker if f.get("sekvens") == sid]
        flankraknare = dict((f["namn"], 0) for f in mina_flank)
        forra = {}

        i = 0
        try:
            while motor.tid_ms <= slut_ms + 1e-9:
                # Insignalerna byter värde MELLAN två scan, som en givare gör.
                while i < len(steg) and float(steg[i]["t_ms"]) <= motor.tid_ms + 1e-9:
                    for namn, v in (steg[i].get("satt") or {}).items():
                        motor.satt(namn, v)
                    i += 1
                motor.scan()
                scan_totalt += 1
                nu = motor.tid_ms

                # Punktkraven läses efter den scan vars klocka står på t_ms.
                for s in steg:
                    if abs(float(s["t_ms"]) - (nu - scan_ms)) > 1e-9:
                        continue
                    for namn, vantat in (s.get("krav") or {}).items():
                        faktiskt = motor.las(namn)
                        if not _lika(vantat, faktiskt):
                            brister.append(Brist(
                                "%s@%.0fms:%s" % (sid, float(s["t_ms"]), namn),
                                "%s skulle vara %s men var %s. %s"
                                % (namn, _skriv(vantat), _skriv(faktiskt),
                                   s.get("varfor") or "")))

                for inv in mina_inv:
                    if inv["namn"] in inv_falld:
                        continue
                    if all(_lika(v, motor.las(n))
                           for n, v in inv["nar"].items()) and \
                       not all(_lika(v, motor.las(n))
                               for n, v in inv["kraver"].items()):
                        inv_falld.add(inv["namn"])
                        brister.append(Brist(
                            "invariant:%s@%s" % (inv["namn"], sid),
                            "vid t=%.0f ms gällde %s men inte %s. %s"
                            % (nu - scan_ms,
                               ", ".join("%s=%s" % (n, _skriv(v))
                                         for n, v in inv["nar"].items()),
                               ", ".join("%s=%s" % (n, _skriv(v))
                                         for n, v in inv["kraver"].items()),
                               inv.get("varfor") or "")))

                for f in mina_flank:
                    v = bool(motor.las(f["signal"]))
                    p = forra.get(f["signal"])
                    t_ledd = nu - scan_ms
                    if p is not None and float(f["fran_ms"]) <= t_ledd <= float(f["till_ms"]):
                        if f["typ"] == "RISE" and v and not p:
                            flankraknare[f["namn"]] += 1
                        elif f["typ"] == "FALL" and p and not v:
                            flankraknare[f["namn"]] += 1
                    forra[f["signal"]] = v
        except Tolkfel as fel:
            brister.append(Brist("tolkfel:%s" % sid, str(fel)))

        for f in mina_flank:
            if flankraknare[f["namn"]] != int(f["antal"]):
                brister.append(Brist(
                    "flank:%s" % f["namn"],
                    "%s skulle ha %d %s-flank(er) mellan %.0f och %.0f ms, "
                    "hade %d. %s"
                    % (f["signal"], int(f["antal"]), f["typ"],
                       float(f["fran_ms"]), float(f["till_ms"]),
                       flankraknare[f["namn"]], f.get("varfor") or "")))

    return Dom(post.get("task_id"), brister, scan_totalt)


def dom_referens(post):
    """Dömer uppgiftens egen referenslösning. Ska alltid bli godkänd: annars är
    facit inte uppfyllbart, och ett ouppfyllbart facit fäller alla."""
    facit = post.get("facit_spar") or {}
    return dom(post, facit.get("referens") or "")


def dom_motbevis(post):
    """Dömer varje motbevis. Lämnar (namn, Dom, faller_pa)."""
    facit = post.get("facit_spar") or {}
    ut = []
    for mb in facit.get("motbevis") or []:
        ut.append((mb["namn"], dom(post, mb["st"]), list(mb.get("faller_pa") or [])))
    return ut


# -------------------------------------------------------------------- CLI

def _las_uppgift(task_id):
    sokvag = os.path.join(_HAR, "uppgifter", "%s.json" % task_id)
    if not os.path.exists(sokvag):
        raise SystemExit("ingen uppgift %s" % task_id)
    with open(sokvag, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    ap = argparse.ArgumentParser(description="dom mot bankens spårfacit")
    ap.add_argument("--uppgift", required=True, help="task_id, t.ex. T-07")
    ap.add_argument("--st", help="fil med ST att döma; utan den döms referensen "
                                 "och alla motbevis")
    a = ap.parse_args(argv)
    post = _las_uppgift(a.uppgift)
    if not post.get("facit_spar"):
        print("%s har inget spårfacit" % a.uppgift)
        return 2
    if a.st:
        with open(a.st, "r", encoding="utf-8") as f:
            print(dom(post, f.read()).text())
        return 0
    d = dom_referens(post)
    print("referens  " + d.text())
    fel = 0 if d.godkand else 1
    for namn, md, faller_pa in dom_motbevis(post):
        traffar = [k for k in faller_pa if k in md.koder]
        ok = md.brister and len(traffar) == len(faller_pa)
        print("motbevis %-28s %s  (%d/%d namngivna brister)"
              % (namn, "FALLS" if ok else "FALLS INTE", len(traffar),
                 len(faller_pa)))
        if not ok:
            fel = 1
            for b in md.brister:
                print("    %s" % b.kod)
    return fel


if __name__ == "__main__":
    raise SystemExit(main())
