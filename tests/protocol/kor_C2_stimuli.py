# -*- coding: utf-8 -*-
"""C2: stimulusgrinden - nya stimuli for bankens domare, en i taget provade.

Kor C punkt C2 bygger stimuli ur M-134:s klassning: punktkrav dar facit ser
skillnaden men saknar punkten (klass 1-2), nya sekvenser dar stimulusen inte
nar raden (klass 3-6). Varje stimulus provas av `verifiera_stimulus` INNAN den
committas in i uppgiften:

* referensen maste vara gron MED stimulusen - faller den avvisas stimulusen.
  Ett scenario som faller bade mutanten och referensen ar ett facit i
  forkla dnad, inte en stimulus (C2:s trasiga fixtur).
* varje mutant stimulusen ar byggd for maste falla - annars ser den inget.
* en ersatt sekvens far aldrig ta bort ett gammalt steg - grinden far inte
  bli billig. Att lagga TILL sekvenser kan per konstruktion aldrig fa en
  gammal fangst att slappa: domen samlar brister over alla sekvenser.

Korning: python3 tests/protocol/kor_C2_stimuli.py [--json ut.json]
Slutkod 0 nar alla stimuli haller, 2 nar nagot faller.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)
sys.path.insert(0, os.path.dirname(__file__))

BANKPOST = {
    "pastar": "en ny stimulus for bankens domare faller de mutanter den ar "
              "byggd for och referensen forblir gron - en stimulus som faller "
              "referensen avvisas",
    "under_prov": ("bank/domare.py", "svc/vc_assist_svc/st/tolk.py",
                   "svc/vc_assist_svc/plc/mutation.py"),
    "facit": "skadan sjalv (kand textandring) och referensens eget "
             "utgangsspar: mutanten ska falla, referensen bestas",
    "facitkalla": "kand textandring i en referens som redan uppfyller sitt "
                  "handskrivna facit (85_bankkontraktet.md §2 klass 4), och "
                  "referensens utgangsspar under samma stimulus",
    "facitkalla_filer": ("bank/uppgifter",),
    "trasiga_fall": (
        "en stimulus som faller referensen avvisas med slutkod 2 - ett facit "
        "i forkla dnad, inte en stimulus",
        "en stimulus som inte faller nagon av sina mutanter avvisas med "
        "slutkod 2 - den ser inget",
        "en ersatt sekvens som tar bort ett gammalt steg avvisas - grinden "
        "far inte bli billig",
    ),
    "kraver": ("inget",),
    "matningar": ("M-135",),
}

from vc_assist_svc.plc.mutation import skador          # noqa: E402
from bank import domare                                # noqa: E402


def med_sekvens(post, ny_sekvens, ersatt_id=None, extra_invarianter=None,
                extra_flanker=None):
    """Proben: uppgiften med stimulusen inlagd. Ror aldrig `post`."""
    facit = dict(post.get("facit_spar") or {})
    gamla = list(facit.get("sekvenser") or [])
    if ersatt_id is None:
        if any(s.get("id") == ny_sekvens.get("id") for s in gamla):
            raise ValueError("sekvens %r finns redan - anvand ersatt_id"
                             % (ny_sekvens.get("id"),))
        facit["sekvenser"] = gamla + [ny_sekvens]
    else:
        if not any(s.get("id") == ersatt_id for s in gamla):
            raise ValueError("sekvens %r finns inte att ersatta" % (ersatt_id,))
        facit["sekvenser"] = [ny_sekvens if s.get("id") == ersatt_id else s
                              for s in gamla]
    if extra_invarianter:
        facit["invarianter"] = list(facit.get("invarianter") or []) \
            + list(extra_invarianter)
    if extra_flanker:
        facit["flanker"] = list(facit.get("flanker") or []) + list(extra_flanker)
    probe = dict(post)
    probe["facit_spar"] = facit
    return probe


def steg_borttagna(gamla_steg, nya_steg):
    """Gamla steg som ersattningen inte langre garanterar. Ett gammalt steg
    ar kvar om ett nytt steg har samma t_ms, samma satt och minst samma krav
    - att lagga krav till ett steg skarper, det tunnar inte ut."""
    nya = list(nya_steg or [])
    bort = []
    for g in gamla_steg or []:
        t = float(g.get("t_ms", 0.0))
        gs, gk = g.get("satt") or {}, g.get("krav") or {}
        kvar = any(float(n.get("t_ms", 0.0)) == t
                   and (n.get("satt") or {}) == gs
                   and all(k in (n.get("krav") or {}) and
                           (n.get("krav") or {})[k] == v
                           for k, v in gk.items())
                   for n in nya)
        if not kvar:
            bort.append(g)
    return bort


def verifiera_stimulus(post, ny_sekvens, mutanter, ersatt_id=None,
                       extra_invarianter=None, extra_flanker=None):
    """Provar en stimulus. Returnerar (ok, skal, detaljer).

    `mutanter` ar ST-kroppar. Tom lista ar fellagt anvand - en stimulus utan
    mutanter att falla provas inte, den pastas.
    """
    if not mutanter:
        return False, "avvisas: inga mutanter att falla", {}
    if ersatt_id is not None:
        gammal = next(s for s in (post.get("facit_spar") or {}).get("sekvenser")
                      or [] if s.get("id") == ersatt_id)
        borttagna = steg_borttagna(gammal.get("steg"), ny_sekvens.get("steg"))
        if borttagna:
            return False, ("avvisas: ersattningen tar bort %d gamla steg - "
                           "grinden far inte bli billig" % len(borttagna)), {}
    try:
        probe = med_sekvens(post, ny_sekvens, ersatt_id, extra_invarianter,
                            extra_flanker)
    except ValueError as fel:
        return False, "avvisas: %s" % (fel,), {}
    ref = (post.get("facit_spar") or {}).get("referens") or ""
    dref = domare.dom(probe, ref)
    if not dref.godkand:
        return False, ("avvisas: faller referensen (%s) - ett facit i "
                       "fork ladnad, inte en stimulus"
                       % ", ".join(dref.koder[:5])), {"referens_koder": dref.koder}
    fallda, blinda = [], []
    for m in mutanter:
        dm = domare.dom(probe, m)
        (fallda if not dm.godkand else blinda).append(dm.koder)
    if not fallda:
        return False, ("avvisas: ser ingen av %d mutanterna"
                       % len(mutanter)), {}
    return True, ("ok: referensen gron, %d av %d mutanter fallda"
                  % (len(fallda), len(mutanter))), {"fallda": fallda}


def _las_post(task_id):
    with open(os.path.join(_ROT, "bank", "uppgifter", "%s.json" % task_id),
              "r", encoding="utf-8") as h:
        return json.load(h)


def _bygg_mutanter(ref, val):
    """Valda mutanter ur motorn: {sort, rad, fore, forekomst}. Forekomst ar
    index bland kandidater med samma (sort, rad, fore) - svepets ordning."""
    ut = []
    for v in val:
        cand = [s for s in skador(ref, per_sort=3)
                if s.sort == v["sort"] and s.rad == v["rad"]
                and s.fore == v["fore"]]
        if len(cand) <= v.get("forekomst", 0):
            return None, ("hittar inte mutanten %s rad %s (%s): %d kandidater"
                          % (v["sort"], v["rad"], v["fore"], len(cand)))
        ut.append(cand[v.get("forekomst", 0)].kropp)
    return ut, ""


# En stimulus per klass ur M-134. Fylls pa klass for klass; korningen
# verifierar dem alla MOT FILEN SOM DEN LIGGER (disk truth): referensen ska
# vara gron, varje mutant falla, och mina steg ska finnas. Andrar nagon min
# sekvens utan att bevisa om den faller korningen - da syns det har.
# "lage": "ny" (ny sekvens + scenariokatalogpost) eller "ersatt" (steg
# tillagda i befintlig sekvens). "steg": de steg C2 lade till - for en ny
# sekvens hela stegen, for en ersatt sekvens bara tillaggen.
STIMULI = [
    # --- klass 1: checkpoint-gleshet (M-134) ---
    {"uppgift": "A-03", "sekvens": "en_enhet_genom_bada_stationerna",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 29600, "satt": {},
                "krav": {"ST260_ACK_RST": False},
                "varfor": "kvittensen ar en puls: efter 29200 maste den vara "
                          "nere igen (M-134 klass 1)"}],
     "mutanter": [{"sort": "TID_FORDUBBLAD", "rad": 30, "fore": "T#500ms",
                   "forekomst": 0}]},
    {"uppgift": "A-03", "sekvens": "ingen_dubbelslapp_pa_samma_klarsignal",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 30600, "satt": {},
                "krav": {"ST260_ACK_RST": False},
                "varfor": "kvittensen ar en puls: efter 30400 maste den vara "
                          "nere igen (M-134 klass 1)"}],
     "mutanter": [{"sort": "TID_FORDUBBLAD", "rad": 30, "fore": "T#500ms",
                   "forekomst": 0}]},
    {"uppgift": "S-01", "sekvens": "utskjutaren_star_kvar_ute",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 2300, "satt": {},
                "krav": {"ST190_CNV_RUN": True},
                "varfor": "hemvaktens transportband maste ga medan "
                          "utskjutaren star ute (M-134 klass 1)"}],
     "mutanter": [{"sort": "AND_TILL_OR", "rad": 34, "fore": "AND",
                   "forekomst": 0}]},
    {"uppgift": "S-07", "sekvens": "nodstopp_kraver_kvittens",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 1400, "satt": {},
                "krav": {"ST510_LBL_PRINT": False, "ST510_LBL_APPLY": False,
                         "ST510_CNV_RUN": False},
                "varfor": "ett aterstallt nodstopp far inte i sig starta "
                          "stationen (IEC 60204-1: urkopplingen mojliggor "
                          "omstart, den utfor den inte) | transportbandet "
                          "star still tills kvittens (M-134 klass 1)"}],
     "mutanter": [{"sort": "SANT_TILL_FALSKT", "rad": 24, "fore": "TRUE",
                   "forekomst": 0}]},
    {"uppgift": "T-05", "sekvens": "materialet_kommer_aldrig_fram",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 6000, "satt": {},
                "krav": {"ST050_CNV_RUN": True},
                "varfor": "narvarovakten gar: bandet maste ga har "
                          "(M-134 klass 1)"}],
     "mutanter": [{"sort": "AND_TILL_OR", "rad": 32, "fore": "AND",
                   "forekomst": 0}]},
    {"uppgift": "H-01", "sekvens": "kvittensen_uteblir",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 13520, "satt": {},
                "krav": {"ST290_HS_REQ": False},
                "varfor": "begaran maste vara nere igen (M-134 klass 1)"}],
     "mutanter": [{"sort": "FALSKT_TILL_SANT", "rad": 35, "fore": "FALSE",
                   "forekomst": 0}]},
    {"uppgift": "P-07", "sekvens": "stopptiden_for_kort",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 160, "satt": {},
                "krav": {"ST460_CNV_RUN": False},
                "varfor": "bandet star under stopptid (M-134 klass 1)"}],
     "mutanter": [{"sort": "FLANK_TILL_NIVA", "rad": 46,
                   "fore": "trigReset.Q", "forekomst": 0}]},
    # --- klass 2: nytt tunt facit (P-05, M-134) ---
    {"uppgift": "P-05", "sekvens": "locked_uteblir_ger_stopp",
     "lage": "ersatt", "scenario": None,
     "steg": [{"t_ms": 3500, "satt": {},
                "krav": {"ST140_TCH_BUSY": False},
                "varfor": "lasfelet star kvar: verktyget ar inte upptaget "
                          "(M-134 klass 2)"}],
     "mutanter": [{"sort": "TID_FORDUBBLAD", "rad": 21, "fore": "T#3s",
                   "forekomst": 0},
                  {"sort": "NOT_STRUKEN", "rad": 22, "fore": "NOT ",
                   "forekomst": 0},
                  {"sort": "SANT_TILL_FALSKT", "rad": 23, "fore": "TRUE",
                   "forekomst": 0},
                  {"sort": "AND_TILL_OR", "rad": 26, "fore": "AND",
                   "forekomst": 0},
                  {"sort": "AND_TILL_OR", "rad": 26, "fore": "AND",
                   "forekomst": 1},
                  {"sort": "FALSKT_TILL_SANT", "rad": 30, "fore": "FALSE",
                   "forekomst": 0}]},
    # normal_drift_med_byte struken: rad 38/41 ar 1 scans transienter i
    # verktygsbytet. Ingen M33-ren punkt ser dem (marginalen ar 2 scan) och
    # ingen sann invariant haller for referensen sjalv (matt i M-135) - de
    # star kvar som overlevare med skal istallet for med en billig grind.
    # --- klass 3: andra varvet (M-134) ---
    # For nya sekvenser pinar "steg" bara fangstpunkten (resten ar mekanisk
    # replay av bassekvensen): referensen-gron + mutanter-roda provas mot
    # filen som den ligger, varje korning.
    {"uppgift": "A-03", "sekvens": "tva_enheter_tatt_i_rad",
     "lage": "ny",
     "scenario": {"id": "tva_enheter_tatt_i_rad", "typ": "vandning",
                  "signal": "ST250_PRT_PRS",
                  "beskrivning": "En andra enhet kommer tatt efter den "
                                 "forsta, innan station 2 hunnit kvittera.",
                  "forvantat": "Den andra enheten halles kvar tills station "
                               "2 kvitterat foregaende enhet; grinden oppnas "
                               "inte for den."},
     "steg": [{"t_ms": 72200, "satt": {},
                "krav": {"ST250_REL_OPEN": True},
                "varfor": "andra varvet: grinden oppnar for andra enheten "
                          "(M-134 klass 3)"}],
     "mutanter": [{"sort": "AND_TILL_OR", "rad": 56, "fore": "AND",
                   "forekomst": 0},
                  {"sort": "AND_TILL_OR", "rad": 56, "fore": "AND",
                   "forekomst": 1}]},
    {"uppgift": "H-04", "sekvens": "tva_overlamningar_i_rad",
     "lage": "ny",
     "scenario": {"id": "tva_overlamningar_i_rad", "typ": "vandning",
                  "signal": "ST310_PRT_PRS",
                  "beskrivning": "Overlamningen kors tva ganger i rad utan "
                                 "aterstallning emellan.",
                  "forvantat": "Bada overlamningarna fullfoljs med kvittens "
                               "var for sig; den andra startar inte pa den "
                               "forstas kvittens."},
     "steg": [{"t_ms": 6000, "satt": {},
                "krav": {"ST310_HSK_REQ": True},
                "varfor": "andra varvet: handskakningen star kvar "
                          "(M-134 klass 3)"}],
     "mutanter": [{"sort": "OR_TILL_AND", "rad": 46, "fore": "OR",
                   "forekomst": 0}]},
    {"uppgift": "H-05", "sekvens": "tva_overlamningar_i_rad",
     "lage": "ny",
     "scenario": {"id": "tva_overlamningar_i_rad", "typ": "vandning",
                  "signal": "ST490_XFR_REQ",
                  "beskrivning": "Overlamningen kors tva ganger i rad utan "
                                 "aterstallning emellan.",
                  "forvantat": "Bada overlamningarna fullfoljs; kvittens och "
                               "aterstallning galler aven andra gangen."},
     "steg": [{"t_ms": 3700, "satt": {},
                "krav": {"SYS_ALARM": True},
                "varfor": "andra varvet: vakten star kvar (M-134 klass 3)"}],
     "mutanter": [{"sort": "SANT_TILL_FALSKT", "rad": 36, "fore": "TRUE",
                   "forekomst": 0}]},
    {"uppgift": "L-07", "sekvens": "tva_varv_i_rad",
     "lage": "ny",
     "scenario": {"id": "tva_varv_i_rad", "typ": "vandning",
                  "signal": "ST550_TBL_HOME",
                  "beskrivning": "Vagnen kor tva hela varv i rad utan stopp "
                                 "emellan.",
                  "forvantat": "Bada varven raknas och overvakas var for "
                               "sig; andra varvet startar inte pa forstas "
                               "pulsgivare."},
     "steg": [{"t_ms": 18080, "satt": {},
                "krav": {"ST550_TBL_RUN": True},
                "varfor": "andra varvet: vagnen gar (M-134 klass 3)"}],
     "mutanter": [{"sort": "SANT_TILL_FALSKT", "rad": 30, "fore": "TRUE",
                   "forekomst": 0}]},
    {"uppgift": "S-07", "sekvens": "underkanda_i_tva_omgangar",
     "lage": "ny",
     "scenario": {"id": "underkanda_i_tva_omgangar", "typ": "vandning",
                  "signal": "ST510_PEC_PART",
                  "beskrivning": "Tre underkanda etiketter kommer i tva "
                                 "omgangar i samma korning.",
                  "forvantat": "Raknaren nollstalls av godkand etikett; tre "
                               "underkanda i rad stoppar stationen i bada "
                               "omgangarna."},
     "steg": [{"t_ms": 6780, "satt": {},
                "krav": {"ST510_CNV_RUN": True},
                "varfor": "andra omgangen: bandet gar (M-134 klass 3)"}],
     "mutanter": [{"sort": "OR_TILL_AND", "rad": 44, "fore": "OR",
                   "forekomst": 0}]},
    # --- klass 4: vakten far aldrig lopa ut (P-03, M-134) ---
    # NOT forekomst 0 star kvar: den kraver upptagen-hog-med-stangt-verktyg,
    # vilket faller referensen pa invarianten griparen_rustas_bara_mot_ett_
    # oppet_verktyg. P-03:s aterstallningsvag ar oexekverbar under egna
    # invarianter (matt i M-135) - mutantskal, inte grindskal.
    {"uppgift": "P-03", "sekvens": "roboten_fastnar_i_verktyget",
     "lage": "ny",
     "scenario": {"id": "roboten_fastnar_i_verktyget", "typ": "vandning",
                  "signal": "ST120_RB_BUSY",
                  "beskrivning": "Roboten kommer inte tillbaka utan star "
                                 "kvar inne i verktyget i mer an 6 s.",
                  "forvantat": "Tidsovervakningen satter uttagsfelet; start "
                               "och stangningsklart halles tillbaka tills "
                               "upptagen faller."},
     "steg": [{"t_ms": 21000, "satt": {},
                "krav": {"ST120_RB_START": False, "ST120_RB_CLEAR": False,
                         "ST120_MLD_CLOSE_OK": False},
                "varfor": "roboten star kvar efter 6 s: uttagsfelet star och "
                          "verktyget far aldrig stangningsklart (M-134 klass 4)"},
               {"t_ms": 23500, "satt": {},
                "krav": {"ST120_RB_START": False, "ST120_RB_CLEAR": False,
                         "ST120_MLD_CLOSE_OK": False},
                "varfor": "felet star kvar utan aterstallning: uttaget star "
                          "stilla (M-134 klass 4)"}],
     "mutanter": [{"sort": "TID_FORDUBBLAD", "rad": 30, "fore": "T#6s",
                   "forekomst": 0},
                  {"sort": "SANT_TILL_FALSKT", "rad": 32, "fore": "TRUE",
                   "forekomst": 0},
                  {"sort": "NOT_STRUKEN", "rad": 34, "fore": "NOT ",
                   "forekomst": 1},
                  {"sort": "AND_TILL_OR", "rad": 34, "fore": "AND",
                   "forekomst": 0},
                  {"sort": "AND_TILL_OR", "rad": 38, "fore": "AND",
                   "forekomst": 0},
                  {"sort": "AND_TILL_OR", "rad": 38, "fore": "AND",
                   "forekomst": 1}]},
]


def kor_stimulus(defn):
    post = _las_post(defn["uppgift"])
    facit = post.get("facit_spar") or {}
    seqs = [s for s in facit.get("sekvenser") or []
            if s.get("id") == defn["sekvens"]]
    if not seqs:
        return False, ("sekvensen %r ligger inte i filen"
                       % (defn["sekvens"],)), {}
    fil_seq = seqs[0]
    saknas = steg_borttagna(defn["steg"], fil_seq.get("steg"))
    if saknas:
        return False, ("mina %d steg ligger inte i filen langre - nagon har "
                       "andrat sekvensen utan att bevisa om den"
                       % len(saknas)), {}
    if defn["lage"] == "ny":
        if defn.get("scenario") is None:
            return False, "ny sekvens saknar scenariokatalogpost", {}
        ids = [s.get("id") for s in post.get("scenarios") or []]
        if defn["scenario"].get("id") not in ids:
            return False, ("scenariot %r ligger inte i uppgiftens scenarios"
                           % (defn["scenario"].get("id"),)), {}
    ref = facit.get("referens") or ""
    dref = domare.dom(post, ref)
    if not dref.godkand:
        return False, ("referensen faller: %s"
                       % ", ".join(dref.koder[:5])), {}
    mutanter, fel = _bygg_mutanter(ref, defn["mutanter"])
    if mutanter is None:
        return False, fel, {}
    grona = 0
    for m in mutanter:
        if domare.dom(post, m).godkand:
            grona += 1
    if grona:
        return False, ("%d av %d mutanterna star - stimulusen ser dem inte"
                       % (grona, len(mutanter))), {}
    return True, ("ok: referensen gron, %d av %d mutanter fallda"
                  % (len(mutanter), len(mutanter))), {}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--json")
    a = p.parse_args(argv)
    if not STIMULI:
        print("inga stimuli definierade annu")
        return 0
    daliga = []
    for d in STIMULI:
        ok, skal, _ = kor_stimulus(d)
        print("%-8s %-40s %s" % (d["uppgift"], d["sekvens"], skal))
        if not ok:
            daliga.append("%s:%s" % (d["uppgift"], d["sekvens"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as h:
            json.dump([dict(uppgift=d["uppgift"], sekvens=d["sekvens"])
                       for d in STIMULI], h, ensure_ascii=False, indent=1)
    if daliga:
        print("UNDERKANDA: %s" % ", ".join(daliga), file=sys.stderr)
        return 2
    print("%d stimuli haller" % len(STIMULI))
    return 0


if __name__ == "__main__":
    sys.exit(main())
