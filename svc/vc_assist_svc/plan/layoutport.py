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
    """En roll, ett lage, och skalet till laget."""

    __slots__ = ("roll", "position_mm", "wpr_deg", "motiv")

    def __init__(self, roll, position_mm, wpr_deg, motiv):
        self.roll = roll
        self.position_mm = list(position_mm)
        self.wpr_deg = list(wpr_deg)
        self.motiv = motiv

    def __repr__(self):
        return "Placering(%s, %s)" % (self.roll, self.position_mm)


class Layoutsvar(object):
    """Motorns svar, sedan det provats mot kontraktet."""

    __slots__ = ("placeringar", "antaganden", "fragor")

    def __init__(self, placeringar, antaganden, fragor):
        self.placeringar = list(placeringar)
        self.antaganden = list(antaganden)   # [{vad, varde, motiv}]
        self.fragor = list(fragor)           # [{id, vad, varfor, blockerar}]

    def __repr__(self):
        return "Layoutsvar(%d placeringar, %d fragor)" % (
            len(self.placeringar), len(self.fragor))

    def roller(self):
        return tuple(p.roll for p in self.placeringar)


def begaran_ur_spec(spec, frigang_mm, golv_mm=None):
    """Ordboken motorn far. Bar inga koordinater - det ar just det som ska ut."""
    return {
        "v": KONTRAKTSVERSION,
        "plan_id": spec.id,
        "frigang_mm": float(frigang_mm),
        "golv_mm": list(golv_mm) if golv_mm else None,
        "delar": [{"roll": d.roll, "uri": d.uri, "kategori": d.kategori,
                   "antal": d.antal, "matt_mm": d.matt_mm,
                   "massa_kg": d.massa_kg} for d in spec.delar],
        "kopplingar": [{"fran_roll": k.fran_roll, "till_roll": k.till_roll}
                       for k in spec.kopplingar],
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

    def placera(self, spec, frigang_mm, golv_mm=None):
        """Kastar Layoutfel om motorn svarar nagot som inte haller."""
        begaran = begaran_ur_spec(spec, frigang_mm, golv_mm)
        svar = self.motor.placera(begaran)
        return self.granska_svar(svar, spec)

    def granska_svar(self, svar, spec):
        if not isinstance(svar, dict):
            raise Layoutfel("layoutmotorn svarade %s, inte en ordbok"
                            % type(svar).__name__)
        okanda = sorted(set(svar) - {"v", "placeringar", "antaganden", "fragor"})
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
                                         "motiv"})
            if okanda:
                raise Layoutfel("placeringen bar okanda nycklar: %s"
                                % ", ".join(okanda))
            roll = post.get("roll")
            if roll not in roller:
                raise Layoutfel(
                    "layoutmotorn placerade rollen %r som inte finns i specen; "
                    "kanda roller ar %s" % (roll, ", ".join(sorted(roller))))
            if roll in sedda:
                raise Layoutfel("rollen %r placerades tva ganger" % (roll,))
            sedda.add(roll)
            motiv = post.get("motiv")
            if not isinstance(motiv, str) or not motiv.strip():
                raise Layoutfel(
                    "placeringen av %s saknar motiv; koordinater utan skal far "
                    "inte in i en plan" % (roll,))
            placeringar.append(Placering(
                roll,
                _vektor(post.get("position_mm"), "position_mm", roll),
                _vektor(post.get("wpr_deg"), "wpr_deg", roll),
                motiv))

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

        return Layoutsvar(placeringar, antaganden, fragor)
