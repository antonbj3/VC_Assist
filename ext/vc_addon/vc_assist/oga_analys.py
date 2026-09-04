# -*- coding: utf-8 -*-
"""Ogats analys: tidsserie in, dom ut.

Ror varken VC eller natverk. Kors av py3 ute i tjansten och gar att prova pa
konstruerade serier utan att VC startas - det ar avsiktligt, for en domare som
bara gar att prova genom det den ska doma ar ingen domare.

Kalla: docs/spec/40_ogat.md, docs/spec/41_ogat_kontrakt.md

TROSKELREGEL (41_ogat_kontrakt.md): varje trosket bar den matning som satte
det. Ingen trosket utan hanvisning - det kontrolleras av
tests/enhet/test_troskelharkomst.py.
"""
from __future__ import absolute_import, division, print_function

import math

import oga_kontrakt as K

# ---- trosklar ------------------------------------------------------------
# Alla ar PRELIMINARA tills M-10 (ogats kalibrering mot handbyggda celler)
# satt dem. De ar valda sa att de FALLER at det harda hallet: hellre en
# INCONCLUSIVE an ett falskt PASS.

GRIP_STABIL_MM = 2.0        # PRELIMINAR. Satts av matning M-10.
GRIP_RORELSE_MM = 5.0       # PRELIMINAR. Satts av matning M-10.
GRIP_FONSTER_S = 0.25       # PRELIMINAR. Satts av matning M-10.
TELEPORT_MAX_MM = 150.0     # PRELIMINAR. Satts av matning M-10.
CARRY_RIGID_DEG = 2.0       # PRELIMINAR. Satts av matning M-10.
CARRY_MIN_SPAN_S = 0.5      # PRELIMINAR. Satts av matning M-10.
PLACE_TOL_MM = 25.0         # PRELIMINAR. Satts av matning M-10.
BLOWUP_VMAX_MS = 25.0       # PRELIMINAR. Satts av matning M-10.
UNDERGROUND_MARGINAL_M = 0.005   # PRELIMINAR. Satts av matning M-10.
MIN_PROV = 10               # PRELIMINAR. Satts av matning M-10.


# ---- liten kvaternionmatematik ------------------------------------------

def q_konjugat(q):
    x, y, z, w = q
    return (-x, -y, -z, w)


def q_mult(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def q_rotera(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    # v' = v + 2w(qv x v) + 2 qv x (qv x v)
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def q_vinkel_deg(q):
    """Vridningsvinkeln i en kvaternion, alltid 0-180 grader."""
    w = max(-1.0, min(1.0, abs(q[3])))
    return math.degrees(2.0 * math.acos(w))


def _diff(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def i_verktygsramen(p_del, q_verktyg, p_verktyg):
    """Delens lage uttryckt i verktygets ram."""
    return q_rotera(q_konjugat(q_verktyg), _diff(p_del, p_verktyg))


# ---- analysen ------------------------------------------------------------

class Analys(object):
    def __init__(self, data, plan=None):
        self.v = data.get("v")
        self.template = data.get("template", "okand")
        self.run = data.get("run", {})
        self.tracked = data.get("tracked", {})
        self.rader = data.get("rows", [])
        self.plan = plan or {}
        self.harledt = {}
        self.skal = []          # varfor domen blev som den blev

    # -- hjalp --

    def _tid(self, i):
        return float(self.rader[i].get("t", 0.0))

    def _serie(self, grupp, namn):
        """[(t, p, q)] for ett spart objekt, hoppar over rader dar det saknas."""
        ut = []
        for r in self.rader:
            d = (r.get(grupp) or {}).get(namn)
            if not d:
                continue
            ut.append((float(r.get("t", 0.0)), tuple(d["p"]), tuple(d["q"])))
        return ut

    def _del_och_verktyg(self):
        delar = self.tracked.get("parts") or []
        verktyg = self.tracked.get("tools") or []
        if not delar or not verktyg:
            return None, None
        return delar[0], verktyg[0]

    # -- rorelse --

    def rorelse(self):
        """Returnerar (rader, harledt). Rader i MOTION-sektionens grammatik."""
        rader = []
        h = {}
        delnamn, verktygsnamn = self._del_och_verktyg()
        if delnamn is None:
            self.skal.append("ingen spårad del eller verktyg")
            return rader, h

        d = self._serie("parts", delnamn)
        v = self._serie("tools", verktygsnamn)
        n = min(len(d), len(v))
        if n < MIN_PROV:
            self.skal.append("för få prov (%d, kräver %d)" % (n, MIN_PROV))
            h["for_fa_prov"] = n
            return rader, h

        rel = []
        for i in range(n):
            t = d[i][0]
            rel.append((t, i_verktygsramen(d[i][1], v[i][2], v[i][1]),
                        q_mult(q_konjugat(v[i][2]), d[i][2]),
                        _norm(_diff(d[i][1], v[i][1])) * 1000.0,
                        d[i][1]))

        grip_i = self._hitta_grepp(rel)
        h["grip_index"] = grip_i

        if grip_i is None:
            rader.append("GRIP NEVER_FORMED")
            h["grip"] = None
            self.skal.append("greppet bildades aldrig")
            # Utan grepp finns inget att bara och ingenting att placera.
            return rader, h

        t_grip, p_grip, q_grip, dist_grip, _p_varld = rel[grip_i]
        h["grip"] = {"t": t_grip, "dist_mm": dist_grip}
        rader.append("GRIP FORMED t=%.3fs dist=%.1fmm" % (t_grip, dist_grip))

        slut_i = self._hitta_slapp(rel, grip_i)
        h["slapp_index"] = slut_i
        span = rel[slut_i][0] - t_grip
        max_rot = 0.0
        for i in range(grip_i, slut_i + 1):
            vinkel = q_vinkel_deg(q_mult(q_konjugat(q_grip), rel[i][2]))
            max_rot = max(max_rot, vinkel)
        h["carry"] = {"rot_deg": max_rot, "span_s": span}
        if span < CARRY_MIN_SPAN_S:
            rader.append("CARRY INCONCLUSIVE rot=%.1fdeg span=%.3fs" % (max_rot, span))
            self.skal.append("bärsträckan för kort för att döma (%.2f s)" % span)
        elif max_rot > CARRY_RIGID_DEG:
            rader.append("CARRY SLIPPING rot=%.1fdeg span=%.3fs" % (max_rot, span))
            self.skal.append("delen gled %.1f grader i verktygets ram" % max_rot)
        else:
            rader.append("CARRY RIGID rot=%.1fdeg span=%.3fs" % (max_rot, span))

        rader.extend(self._placering(d, delnamn, h))
        return rader, h

    def _hitta_grepp(self, rel):
        """Forsta index dar delen star still i VERKTYGETS ram och samtidigt ror
        sig i VARLDEN.

        Bada villkoren behovs. Stillhet i verktygsramen ensam ar trivialt sann
        sa lange bada star stilla - en cell som borjar med ett stillastaende
        verktyg bredvid en stillastaende detalj skulle annars ge "grepp vid
        t=0" och, eftersom avstandet da ar stort, en falsk teleportdom.
        """
        n = len(rel)
        for i in range(n):
            t0 = rel[i][0]
            # Fonstret ska NA GRIP_FONSTER_S, inte stanna precis under det.
            # Med j+1 i villkoret slutade loopen ett prov for tidigt och
            # returnerade "inget grepp" redan pa forsta forsoket.
            j = i
            while j + 1 < n and rel[j][0] - t0 < GRIP_FONSTER_S - 1e-9:
                j += 1
            if rel[j][0] - t0 < GRIP_FONSTER_S - 1e-9:
                return None                      # slut pa serien, fonstret ryms inte
            stabil = True
            for k in range(i, j + 1):
                if _norm(_diff(rel[k][1], rel[i][1])) * 1000.0 > GRIP_STABIL_MM:
                    stabil = False
                    break
            if not stabil:
                continue
            varldsrorelse = 0.0
            for k in range(i, j + 1):
                varldsrorelse = max(
                    varldsrorelse, _norm(_diff(rel[k][4], rel[i][4])) * 1000.0)
            if varldsrorelse >= GRIP_RORELSE_MM:
                return i
        return None

    def _hitta_slapp(self, rel, grip_i):
        """Forsta index efter greppet dar laget i verktygsramen bryts."""
        p0 = rel[grip_i][1]
        for i in range(grip_i, len(rel)):
            if _norm(_diff(rel[i][1], p0)) * 1000.0 > GRIP_STABIL_MM * 5:
                return i - 1
        return len(rel) - 1

    def _placering(self, d, delnamn, h):
        mal = (self.plan.get("targets") or {}).get(delnamn)
        golv = float(self.plan.get("floor_z", 0.0))
        slut_p = d[-1][1]
        h["slutlage"] = list(slut_p)
        if mal is None:
            self.skal.append("inget mål angivet för %s, placeringen kan inte dömas" % delnamn)
            return []
        tol = float(mal.get("tol_mm", PLACE_TOL_MM))
        fel_mm = _norm(_diff(slut_p, tuple(mal["p"]))) * 1000.0
        h["placering"] = {"fel_mm": fel_mm, "tol_mm": tol}
        if slut_p[2] < golv + UNDERGROUND_MARGINAL_M:
            self.skal.append("delen hamnade på golvnivå, z=%.3f m" % slut_p[2])
            return ["PLACE DROPPED err=%.1fmm z=%.3fm" % (fel_mm, slut_p[2])]
        if fel_mm > tol:
            self.skal.append("delen hamnade %.1f mm fel (tål %.1f mm)" % (fel_mm, tol))
            return ["PLACE OFF_TARGET err=%.1fmm z=%.3fm" % (fel_mm, slut_p[2])]
        return ["PLACE IN_TARGET err=%.1fmm z=%.3fm" % (fel_mm, slut_p[2])]

    # -- tid --

    def tid(self):
        rader = []
        h = {"flanker": [], "dwell": []}
        for signal in (self.tracked.get("signals") or []):
            forra = None
            for r in self.rader:
                v = (r.get("sig") or {}).get(signal)
                if v is None:
                    continue
                if forra is not None and bool(v) != bool(forra):
                    flank = "RISE" if v else "FALL"
                    t = float(r.get("t", 0.0))
                    rader.append("EDGE %s %s t=%.3fs" % (signal, flank, t))
                    h["flanker"].append({"signal": signal, "flank": flank, "t": t})
                forra = v

        for signal, mover in (self.plan.get("movers") or {}).items():
            ms = self._latens(signal, mover)
            if ms is not None:
                rader.append("LATENCY %s -> %s %.1fms" % (signal, mover, ms))
                h.setdefault("latens", {})[signal] = ms

        for station, krav in (self.plan.get("stations") or {}).items():
            req = float(krav.get("dwell_req_s", 0.0))
            faktisk = self._dwell(station)
            if faktisk is None:
                continue
            lage = "OK" if faktisk >= req else "SHORT"
            if lage == "SHORT":
                self.skal.append("uppehållet vid %s var %.2f s, kravet är %.2f s"
                                 % (station, faktisk, req))
            rader.append("DWELL %s %.3fs req=%.3fs %s" % (station, faktisk, req, lage))
            h["dwell"].append({"station": station, "s": faktisk, "req_s": req, "lage": lage})

        rader.append(self._kapplopning(h))
        return rader, h

    def _latens(self, signal, mover):
        """Tid fran signalens stigande flank till att movern verkligen ror sig."""
        t_flank = None
        forra = None
        for r in self.rader:
            v = (r.get("sig") or {}).get(signal)
            if v is None:
                continue
            if forra is not None and v and not forra:
                t_flank = float(r.get("t", 0.0))
                break
            forra = v
        if t_flank is None:
            return None
        serie = self._serie("tools", mover) or self._serie("parts", mover)
        if len(serie) < 2:
            return None
        for i in range(1, len(serie)):
            if serie[i][0] < t_flank:
                continue
            if _norm(_diff(serie[i][1], serie[i - 1][1])) * 1000.0 > GRIP_STABIL_MM:
                return (serie[i][0] - t_flank) * 1000.0
        return None

    def _dwell(self, station):
        """Sammanhangande tid stationen rapporterar en del inne hos sig."""
        inne = []
        for r in self.rader:
            s = (r.get("stat") or {}).get(station)
            if s is None:
                continue
            inne.append((float(r.get("t", 0.0)), int(s.get("in", 0)) - int(s.get("out", 0))))
        if not inne:
            return None
        langst = 0.0
        start = None
        for t, n in inne:
            if n > 0 and start is None:
                start = t
            elif n <= 0 and start is not None:
                langst = max(langst, t - start)
                start = None
        if start is not None:
            langst = max(langst, inne[-1][0] - start)
        return langst

    def _kapplopning(self, h):
        fonster_ms = float(self.plan.get("race_window_ms", 0.0))
        if fonster_ms <= 0:
            return "RACE none"
        stig = [f for f in h["flanker"] if f["flank"] == "RISE"]
        stig.sort(key=lambda f: f["t"])
        for i in range(1, len(stig)):
            dt = (stig[i]["t"] - stig[i - 1]["t"]) * 1000.0
            if dt <= fonster_ms and stig[i]["signal"] != stig[i - 1]["signal"]:
                self.skal.append("två utgångar gick höga inom %.1f ms" % dt)
                return "RACE %s+%s dt=%.1fms" % (stig[i - 1]["signal"],
                                                 stig[i]["signal"], dt)
        return "RACE none"

    # -- genomstromning --

    def genomstromning(self):
        rader = []
        h = {}
        stationer = sorted(set(
            s for r in self.rader for s in (r.get("stat") or {})))
        for station in stationer:
            serie = [(float(r.get("t", 0.0)), r["stat"][station])
                     for r in self.rader if station in (r.get("stat") or {})]
            if not serie:
                continue
            sista = serie[-1][1]
            cykler = self._cykeltider(serie)
            avg = sum(cykler) / len(cykler) if cykler else 0.0
            rader.append("STATION %s in=%d out=%d avg=%.3fs min=%.3fs max=%.3fs"
                         % (station, int(sista.get("in", 0)), int(sista.get("out", 0)),
                            avg, min(cykler) if cykler else 0.0,
                            max(cykler) if cykler else 0.0))
            h[station] = {"in": int(sista.get("in", 0)), "out": int(sista.get("out", 0)),
                          "cykler_s": cykler}
        return rader, h

    @staticmethod
    def _cykeltider(serie):
        ut = []
        forra_t = None
        forra_out = None
        for t, s in serie:
            o = int(s.get("out", 0))
            if forra_out is not None and o > forra_out:
                if forra_t is not None:
                    ut.append(t - forra_t)
                forra_t = t
            elif forra_out is None:
                forra_t = t
            forra_out = o
        return ut

    # -- sakerhet --

    def sakerhet(self):
        rader = []
        h = {}
        par = sorted(set(p for r in self.rader for p in (r.get("mind") or {})))
        for namn in par:
            basta = None
            for r in self.rader:
                d = (r.get("mind") or {}).get(namn)
                if not d:
                    continue
                v = float(d.get("d_mm", 0.0))
                if basta is None or v < basta[0]:
                    basta = (v, float(r.get("t", 0.0)))
            if basta:
                rader.append("MINDIST %s %.1fmm t=%.3fs" % (namn, basta[0], basta[1]))
                h[namn] = {"min_mm": basta[0], "t": basta[1]}

        for r in self.rader:
            hit = r.get("hit")
            if hit:
                t = float(r.get("t", 0.0))
                rader.append("COLLISION %s x %s t=%.3fs" % (hit[0], hit[1], t))
                h["kollision"] = {"a": hit[0], "b": hit[1], "t": t}
                self.skal.append("kollision mellan %s och %s vid t=%.2f s"
                                 % (hit[0], hit[1], t))
                break
        else:
            rader.append("COLLISION none")
        return rader, h

    # -- hederlighet --

    def hederlighet(self, motion_h):
        rader = []
        h = {}
        overtradelse = False

        grip = motion_h.get("grip")
        if grip is None:
            rader.append("TELEPORT_TRANSFER OK")
        elif grip["dist_mm"] > TELEPORT_MAX_MM:
            # Den kritiska i VC: standardgreppet ar icke-fysiskt, sa en MISS
            # ser ut som en lyckad plockning om ingen mater avstandet.
            rader.append("TELEPORT_TRANSFER VIOLATION dist=%.1fmm t=%.3fs"
                         % (grip["dist_mm"], grip["t"]))
            h["teleport"] = grip
            overtradelse = True
            self.skal.append("greppet bildades %.0f mm från verktyget" % grip["dist_mm"])
        else:
            rader.append("TELEPORT_TRANSFER OK dist=%.1fmm t=%.3fs"
                         % (grip["dist_mm"], grip["t"]))

        vmax = self._toppfart()
        h["vmax_ms"] = vmax
        if vmax is not None and vmax > BLOWUP_VMAX_MS:
            rader.append("BLOWUP VIOLATION vmax=%.1fm/s" % vmax)
            overtradelse = True
            self.skal.append("toppfarten var %.1f m/s" % vmax)
        else:
            rader.append("BLOWUP OK" + ("" if vmax is None else " vmax=%.1fm/s" % vmax))

        zmin = self._lagsta_z()
        golv = float(self.plan.get("floor_z", 0.0))
        h["zmin_m"] = zmin
        if zmin is not None and zmin < golv - UNDERGROUND_MARGINAL_M:
            rader.append("UNDERGROUND VIOLATION zmin=%.3fm" % zmin)
            overtradelse = True
            self.skal.append("delen var %.0f mm under golvet" % ((golv - zmin) * 1000.0))
        else:
            rader.append("UNDERGROUND OK" + ("" if zmin is None else " zmin=%.3fm" % zmin))

        if motion_h.get("grip") is None and not motion_h.get("for_fa_prov"):
            rader.append("NEVER_GRIPPED VIOLATION")
            overtradelse = True
        else:
            rader.append("NEVER_GRIPPED OK")

        h["overtradelse"] = overtradelse
        return rader, h

    def _toppfart(self):
        basta = None
        for namn in (self.tracked.get("parts") or []) + (self.tracked.get("tools") or []):
            grupp = "parts" if namn in (self.tracked.get("parts") or []) else "tools"
            serie = self._serie(grupp, namn)
            for i in range(1, len(serie)):
                dt = serie[i][0] - serie[i - 1][0]
                if dt <= 0:
                    continue
                v = _norm(_diff(serie[i][1], serie[i - 1][1])) / dt
                if basta is None or v > basta:
                    basta = v
        return basta

    def _lagsta_z(self):
        lagst = None
        for namn in (self.tracked.get("parts") or []):
            for _, p, _q in self._serie("parts", namn):
                if lagst is None or p[2] < lagst:
                    lagst = p[2]
        return lagst

    # -- domen --

    def rapport(self):
        run = self.run
        r = K.Rapport(self.template, run.get("started", "okand"),
                      float(run.get("dur_s", 0.0)), int(run.get("samples", len(self.rader))),
                      float(run.get("rate_hz", 0.0)))

        motion, mh = self.rorelse()
        tid, th = self.tid()
        gen, gh = self.genomstromning()
        sak, sh = self.sakerhet()
        hed, hh = self.hederlighet(mh)
        self.harledt = {"motion": mh, "timing": th, "throughput": gh,
                        "safety": sh, "honesty": hh}

        for namn, rader in (("MOTION", motion), ("TIMING", tid),
                            ("THROUGHPUT", gen), ("SAFETY", sak), ("HONESTY", hed)):
            r.sektion(namn)
            for rad in rader:
                r.rad(rad)

        varde, orsak = self._dom(mh, th, sh, hh)
        r.satt_dom(varde, orsak)
        return r

    def _dom(self, mh, th, sh, hh):
        # Ordningen ar en rangordning: en overtradelse slar allt annat, och en
        # osakerhet far ALDRIG bli ett PASS.
        if hh.get("overtradelse"):
            return "FAIL", self._orsak("hederlighetsgrind fälld")
        if mh.get("for_fa_prov"):
            return "INCONCLUSIVE", self._orsak("för få prov")
        if mh.get("grip") is None:
            return "FAIL", self._orsak("greppet bildades aldrig")
        if sh.get("kollision"):
            return "FAIL", self._orsak("kollision")
        carry = mh.get("carry") or {}
        if carry.get("span_s", 0.0) < CARRY_MIN_SPAN_S:
            return "INCONCLUSIVE", self._orsak("bärsträckan för kort")
        if carry.get("rot_deg", 0.0) > CARRY_RIGID_DEG:
            return "FAIL", self._orsak("delen gled i greppet")
        plac = mh.get("placering")
        if plac is None:
            return "INCONCLUSIVE", self._orsak("placeringen kunde inte dömas")
        if plac["fel_mm"] > plac["tol_mm"]:
            return "FAIL", self._orsak("delen hamnade fel")
        for d in th.get("dwell", []):
            if d["lage"] == "SHORT":
                return "FAIL", self._orsak("uppehållet för kort")
        return "PASS", "allt inom marginal"

    def _orsak(self, kort):
        if not self.skal:
            return kort
        return "%s: %s" % (kort, "; ".join(self.skal[:3]))


def doma(data, plan=None):
    """Bekvamlighet: tidsserie in, (rapporttext, Rapport, Analys) ut."""
    a = Analys(data, plan)
    r = a.rapport()
    return r.text(), r, a
