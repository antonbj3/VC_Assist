# -*- coding: utf-8 -*-
"""Porten mot layoutmotorn: det enda stalle koordinater kommer in i en plan.

Layoutmotorn byggs i svc/vc_assist_svc/layout/ och ar inte klar an. Darfor
talar planeringen inte med den direkt utan genom den har porten, och kontraktet
ar ORDBOKER, inte klasser: motorn behover inte importera nagot harifran, och
den har filen behover inte importera nagot ur motorn. Kopplingen blir en rad
kod den dag motorn finns.

KONTRAKTET

    motor.placera(begaran: dict) -> svar: dict

  begaran = {
    "v": 1,
    "plan_id":    str,
    "frigang_mm": float,             # minsta fria avstand planen kraver
    "golv_mm":    [x, y] | None,     # tillganglig yta, None = obegransad
    "delar":      [{"roll": str, "uri": str, "kategori": str|None,
                    "antal": int, "matt_mm": [l, b, h]|None,
                    "massa_kg": float|None}, ...],
    "kopplingar": [{"fran_roll": str, "till_roll": str}, ...],
  }

  svar = {
    "v": 1,
    "placeringar": [{"roll": str, "position_mm": [x, y, z],
                     "wpr_deg": [r, p, y], "motiv": str}, ...],
    "antaganden":  [{"vad": str, "varde": str, "motiv": str}, ...],
    "fragor":      [{"id": str, "vad": str, "varfor": str,
                     "blockerar": bool}, ...],
  }

TRE REGLER SOM PORTEN HALLER, OCH SOM MOTORN INTE KAN KRINGGA

1. En placering pa en roll som inte finns i specen avvisas. Motorn far inte
   uppfinna en komponent (I9).
2. En placering utan motiv avvisas. Koordinater ar det enda i hela planen som
   inte gar att lasa ur begaran, sa de maste ha ett skal (I8: modellen anger
   relationer, GEOMETRIN raknas - och den som raknade ska saga hur).
3. Ett halvt svar avvisas helt. En placering vi inte kan lita pa ar ingen
   placering (I3, fail-closed).

Roller motorn INTE placerar ar inget fel: da lamnas de at VC:s plug and play,
och planeringen skriver ut det som ett antagande.
"""
from __future__ import annotations

from .fel import Layoutfel

KONTRAKTSVERSION = 1   # formatversion, ingen troskel: forsta formen av portens kontrakt


class Placering(object):
    """En roll, ett lage, och skalet till laget.

    `instans` skiljer den andra kopian av en roll fran den forsta. Den fanns
    inte forst, och da kunde en spec som bad om tva band bara fa ett lage - en
    tyst nedgradering av precis det slag lagret finns for att undvika.
    """

    __slots__ = ("roll", "position_mm", "wpr_deg", "motiv", "instans")

    def __init__(self, roll, position_mm, wpr_deg, motiv, instans=1):
        self.roll = roll
        self.position_mm = list(position_mm)
        self.wpr_deg = list(wpr_deg)
        self.motiv = motiv
        self.instans = int(instans)

    def __repr__(self):
        if self.instans != 1:
            return "Placering(%s#%d, %s)" % (self.roll, self.instans,
                                             self.position_mm)
        return "Placering(%s, %s)" % (self.roll, self.position_mm)


class Layoutsvar(object):
    """Motorns svar, sedan det provats mot kontraktet.

    `status` och `konflikt` bar motorns EGEN dom vidare i stallet for att slata
    over den. Skillnaden mellan "hallen ar for liten" och "de har tre kraven
    kan inte galla samtidigt" ar precis det svar operatoren behover for att
    kunna ratta sin bestallning, och en motor som redan raknat ut det ska inte
    tvingas kasta bort svaret pa vagen genom en port.
    """

    __slots__ = ("placeringar", "antaganden", "fragor", "status", "konflikt")

    def __init__(self, placeringar, antaganden, fragor, status="",
                 konflikt=()):
        self.placeringar = list(placeringar)
        self.antaganden = list(antaganden)   # [{vad, varde, motiv}]
        self.fragor = list(fragor)           # [{id, vad, varfor, blockerar}]
        self.status = status                 # motorns egen dom, ordagrant
        self.konflikt = list(konflikt)       # [{kod, text, roller}]

    def __repr__(self):
        return "Layoutsvar(%s, %d placeringar, %d fragor, %d i konflikt)" % (
            self.status or "utan status", len(self.placeringar),
            len(self.fragor), len(self.konflikt))

    def roller(self):
        return tuple(p.roll for p in self.placeringar)

    def rader(self):
        """Svaret som rader, i fast ordning. Det har ar forklaringen."""
        ut = []
        if self.status:
            ut.append("LAYOUT %s" % self.status)
        for p in self.placeringar:
            ut.append("PLACERING %s: %s mm, wpr %s (%s)"
                      % (p.roll, p.position_mm, p.wpr_deg, p.motiv))
        for k in self.konflikt:
            ut.append("KONFLIKT %s %s" % (k.get("kod"), k.get("text")))
        for f in self.fragor:
            ut.append("FRAGA %s: %s" % (f.get("id"), f.get("vad")))
        return ut


def begaran_ur_spec(spec, frigang_mm, golv_mm=None, datablad=None):
    """Ordboken motorn far. Bar inga koordinater - det ar just det som ska ut.

    `golv_mm` och `hojd_mm` tas ur specens omrade nar anroparen inte anger
    nagot annat: cellens matt ar ett krav i specen och inte en instalning i
    anropet. `relationer` och `datablad` ar de tva nyckeslar motorn behover
    for att kunna prova mer an ren packning - en rackvidd som inte foljer med
    gor att kravet "roboten ska na pallen" tyst inte provas.
    """
    omrade = getattr(spec, "omrade", None)
    if golv_mm is None and omrade is not None and omrade.bredd_mm and omrade.djup_mm:
        golv_mm = [omrade.bredd_mm, omrade.djup_mm]
    return {
        "v": KONTRAKTSVERSION,
        "plan_id": spec.id,
        "frigang_mm": float(frigang_mm),
        "golv_mm": list(golv_mm) if golv_mm else None,
        "hojd_mm": omrade.hojd_mm if omrade is not None else None,
        "delar": [{"roll": d.roll, "uri": d.uri, "kategori": d.kategori,
                   "antal": d.antal, "matt_mm": d.matt_mm,
                   "massa_kg": d.massa_kg} for d in spec.delar],
        "kopplingar": [{"fran_roll": k.fran_roll, "till_roll": k.till_roll}
                       for k in spec.kopplingar],
        "relationer": [{"sort": r.sort, "fran_roll": r.fran_roll,
                        "till_roll": r.till_roll, "hard": r.hard}
                       for r in getattr(spec, "relationer", ())],
        "datablad": dict(datablad or {}),
    }


def _vektor(varde, vad, roll):
    if not isinstance(varde, list) or len(varde) != 3:
        raise Layoutfel("placeringen av %s: %s ska vara tre tal, fick %r"
                        % (roll, vad, varde))
    for v in varde:
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise Layoutfel("placeringen av %s: %s bar %r som inte ar ett tal"
                            % (roll, vad, v))
        if v != v or v in (float("inf"), float("-inf")):
            raise Layoutfel("placeringen av %s: %s bar %r" % (roll, vad, v))
    return [float(v) for v in varde]


class Layoutport(object):
    """Skalet runt layoutmotorn. Provar varje svar innan det blir ett steg."""

    def __init__(self, motor):
        if not hasattr(motor, "placera"):
            raise Layoutfel("layoutmotorn saknar placera(begaran); porten "
                            "anropar den och ingenting annat")
        self.motor = motor

    def __repr__(self):
        return "Layoutport(%s)" % type(self.motor).__name__

    def placera(self, spec, frigang_mm, golv_mm=None, datablad=None):
        """Kastar Layoutfel om motorn svarar nagot som inte haller."""
        begaran = begaran_ur_spec(spec, frigang_mm, golv_mm, datablad)
        svar = self.motor.placera(begaran)
        return self.granska_svar(svar, spec)

    def granska_svar(self, svar, spec):
        if not isinstance(svar, dict):
            raise Layoutfel("layoutmotorn svarade %s, inte en ordbok"
                            % type(svar).__name__)
        okanda = sorted(set(svar) - {"v", "placeringar", "antaganden",
                                     "fragor", "status", "konflikt"})
        if okanda:
            raise Layoutfel("layoutsvaret bar okanda nycklar: %s"
                            % ", ".join(okanda))
        if svar.get("v") != KONTRAKTSVERSION:
            raise Layoutfel("layoutsvaret ar version %r, porten talar %d"
                            % (svar.get("v"), KONTRAKTSVERSION))
        roller = set(d.roll for d in spec.delar)
        placeringar = []
        sedda = set()
        for post in svar.get("placeringar") or []:
            if not isinstance(post, dict):
                raise Layoutfel("en placering ar %s, inte en ordbok"
                                % type(post).__name__)
            okanda = sorted(set(post) - {"roll", "position_mm", "wpr_deg",
                                         "motiv", "instans"})
            if okanda:
                raise Layoutfel("placeringen bar okanda nycklar: %s"
                                % ", ".join(okanda))
            roll = post.get("roll")
            if roll not in roller:
                raise Layoutfel(
                    "layoutmotorn placerade rollen %r som inte finns i specen; "
                    "kanda roller ar %s" % (roll, ", ".join(sorted(roller))))
            instans = post.get("instans", 1)
            if not isinstance(instans, int) or isinstance(instans, bool) or instans < 1:
                raise Layoutfel("placeringen av %s bar instansen %r; en instans "
                                "ar ett heltal fran och med 1" % (roll, instans))
            if (roll, instans) in sedda:
                raise Layoutfel("rollen %r instans %d placerades tva ganger"
                                % (roll, instans))
            sedda.add((roll, instans))
            motiv = post.get("motiv")
            if not isinstance(motiv, str) or not motiv.strip():
                raise Layoutfel(
                    "placeringen av %s saknar motiv; koordinater utan skal far "
                    "inte in i en plan" % (roll,))
            placeringar.append(Placering(
                roll,
                _vektor(post.get("position_mm"), "position_mm", roll),
                _vektor(post.get("wpr_deg"), "wpr_deg", roll),
                motiv, instans))

        antaganden = []
        for post in svar.get("antaganden") or []:
            if (not isinstance(post, dict)
                    or set(post) != {"vad", "varde", "motiv"}):
                raise Layoutfel("ett layoutantagande ska ha precis vad, varde "
                                "och motiv, fick %r" % (post,))
            antaganden.append(dict(post))

        fragor = []
        for post in svar.get("fragor") or []:
            if (not isinstance(post, dict)
                    or set(post) != {"id", "vad", "varfor", "blockerar"}):
                raise Layoutfel("en layoutfraga ska ha precis id, vad, varfor "
                                "och blockerar, fick %r" % (post,))
            if not isinstance(post["blockerar"], bool):
                raise Layoutfel("layoutfragan %r sager inte om den blockerar"
                                % (post.get("id"),))
            fragor.append(dict(post))

        status = svar.get("status") or ""
        if not isinstance(status, str):
            raise Layoutfel("layoutsvarets status ar %r, inte en text"
                            % (status,))
        konflikt = []
        for post in svar.get("konflikt") or []:
            if (not isinstance(post, dict)
                    or set(post) != {"kod", "text", "roller"}):
                raise Layoutfel("en konfliktpost ska ha precis kod, text och "
                                "roller, fick %r" % (post,))
            konflikt.append(dict(post))
        if konflikt and placeringar:
            raise Layoutfel(
                "layoutsvaret bar bade placeringar och en konflikt. En halv "
                "layout ar farligare an ingen: den ser korbar ut (I3)")
        return Layoutsvar(placeringar, antaganden, fragor, status, konflikt)
