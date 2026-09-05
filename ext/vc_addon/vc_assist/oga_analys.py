# -*- coding: utf-8 -*-
"""Ogats analys: tidsserie in, dom ut.

Ror varken VC eller natverk. Kors av py3 ute i tjansten och gar att prova pa
konstruerade serier utan att VC startas - det ar avsiktligt, for en domare som
bara gar att prova genom det den ska doma ar ingen domare.

Kalla: docs/spec/40_ogat.md, 41_ogat_kontrakt.md, 42_ogat_utbyggt.md

ARBETSDELNING: rakningarna bor i oga_harledning.py, POLICYN bor har. Den har
filen bestammer vilket tal som far falla en korning; den raknar sa lite som
mojligt sjalv.

DOMSGRAMMATIKEN AR LAST TILL v1 (41_ogat_kontrakt.md). De harledningar som
tillkommit sedan dess ryms inte som egna rader - okand rad i en kand sektion
ar ett kontraktsfel. De far darfor tva vagar ut: de FALLER domen med sin egen
orsak i klartext, och de ligger fullstandigt i eyes.json under "derived". Ett
forslag pa v2-grammatik med rader for dem star i docs/spec/42_ogat_utbyggt.md.

TROSKELREGEL (41_ogat_kontrakt.md): varje trosket bar den matning som satte
det. Ingen trosket utan hanvisning - det kontrolleras av
tests/enhet/test_troskelharkomst.py for den har filen och av
tests/enhet/test_oga_harledning.py for oga_harledning.py.
"""
from __future__ import absolute_import, division, print_function

import oga_harledning as H
import oga_kontrakt as K
# Farskhetsfonstret bor i provtagaren, som satter plc_gammal pa det. Har
# anvands SAMMA tal for att avgora om hopfogningens tak tacker fonstret
# (plc_otackt, M-97) - tva trosklar for en storhet hade driftat isar.
from oga_provtagning import PLC_FARSK_S

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
# Hur stor del av ett objekts serie som far vara oläst och objektet anda gar
# att uttala sig om. Over den blir scengrindarna INCONCLUSIVE i stallet for
# att lasa en utglesad serie som "stod still".
SCEN_OLAST_MAX_ANDEL = 0.25      # PRELIMINAR. Satts av matning M-10.
# Hur manga sekunder en station far svalta eller vara blockerad innan det
# faller en korning som DEKLARERAT ett genomstromningskrav. Utan deklarerat
# krav faller den inte alls - da finns inget facit att fella mot.
GENOMSTROMNING_MARGINAL_S = 0.0  # PRELIMINAR. Satts av matning M-19.

# ---- vad ogat inte ser: upplosning och rackvidd ---------------------------
#
# Hopfogningens egen osakerhet nar serien INTE bar en matt (plc_hopfogning_s
# saknas). M-65 §3 matte att kopplarens tak for tur och retur (rtt_tak) bar
# hopfogningsfelet d i 400 av 400 varv, vid bade 5 och 10 ms tur och retur.
# Priorn ar darfor det varsta taket VC:s brygga kan ge: 13,45 ms, den langsta
# tur och retur M-03 matte mot VC. En serie som bar sitt eget tak anvander
# det i stallet, och rapporten sager vilket (RUN eller PRIOR).
HOPFOGNING_PRIOR_S = 0.01345     # Satt av M-65 §3 ur M-03:s varsta tur och retur.
# PLC:ns egen skanfordrojning ligger FORE kopplarens lasning och ingar inte i
# plc_alder_s. Serien sager hur gammalt ett varde ar raknat fran lasningen,
# inte fran insignalens flank i PLC:n. M-20: exakt tva skan, 40,0 ms vid
# 20 ms skanperiod. Rapporteras som UTESLUTET, aldrig som inraknat.
PLC_SKAN_S = 0.040               # Satt av M-20.
# PLC-AXELNS GILTIGHET (M-97). En PLC-rad ar OTACKT nar alder + hopfogningstak
# overstiger farskhetsfonstret: vardets farskhet gar da inte att styrka, och
# raden ligger inte bevisat pa samma tidsaxel som fysiken. Ar andelen otackta
# rader over den har braketten ar korningens PLC-axel inget matt, och domen
# blir INCONCLUSIVE - fas 8:s OGILTIG, inte FAIL och inte PASS. Under
# braketten diskvalificeras de otackta flankerna var for sig (sekvensdom,
# fasforhallande) i stallet for att gora hela korningen obestambar (M-87 §5:
# "ogat hade blivit blint av att bli arligt").
# MATT (M-97, nio VC-korningar): friska korningar 0,0-1,0 % otackta rader
# (sex korningar), SIGSTOP-storda 3,3-5,7 % (tre korningar; 300 ms, 100 ms
# och 30 ms-jitter). De storda falldes av rad- och flanklagren (plc_gammal,
# steg inom osakerheten) innan braketten. Braketten ar darfor ett BAKSTOPP
# over allt som matts - tio ganger den friska toppen - och har i VC bara
# fallt syntetiska fixturer. Det star i M-97:s LIMITS.
PLC_AXEL_MAX_ANDEL = 0.10        # Satt av M-97.


# ---- kvaternion- och vektormatematik ------------------------------------
#
# EN implementation, i oga_harledning.py. Namnen ligger kvar har for att den
# har modulen ar ogats offentliga yta mot tjansten och mot proven; tva kopior
# av samma rakning hade kunnat drifta isar utan att nagot sag det.

q_konjugat = H.q_konjugat
q_mult = H.q_mult
q_rotera = H.q_rotera
q_vinkel_deg = H.q_vinkel_deg
i_verktygsramen = H.i_verktygsramen
_diff = H.diff
_norm = H.norm


# ---- analysen ------------------------------------------------------------

class Analys(object):
    def __init__(self, data, plan=None):
        self.v = data.get("v")
        self.template = data.get("template", "okand")
        self.run = data.get("run", {})
        self.tracked = data.get("tracked", {})
        self.plan = plan or {}
        # Scenen lagras delta-kodad. Den packas upp EN gang, har, sa resten av
        # analysen ser en tat serie oavsett hur den lagrats. Uppackningen bar
        # ocksa skillnaden mellan "stod still" och "lastes aldrig" vidare.
        rader = data.get("rows", [])
        self.delta_lagrad = any(("scene" in r or "scenlast" in r) for r in rader)
        self.rader = H.expandera(rader) if self.delta_lagrad else rader
        self.scen = data.get("scen") or {}
        self.ledgranser = data.get("ledgranser") or self.plan.get("ledgranser") or {}
        self.ledtyper = data.get("ledtyper") or self.plan.get("ledtyper") or {}
        self.harledt = {}
        self.skal = []          # varfor domen blev som den blev
        self._oversikt = None

    # -- hjalp --

    @staticmethod
    def _rent(namn):
        """Ett namn som far sta i domstexten.

        Grammatikens <signal>, <station> och <par> ar ett namn utan blanksteg.
        Ett namn med ett blanksteg i skulle inte matcha monstret, och
        skrivaren kastar da mitt
        i rapporten - en rapport som kraschar domaren kan dolja rott. Namnet
        stads i stallet, en gang, pa ett stalle.
        """
        return "_".join(str(namn).split()) or "namnlos"

    def oversikt(self):
        """Scenoversikten, byggd en gang och delad av alla harledningar."""
        if self._oversikt is None:
            roller = ((self.tracked.get("parts") or [])
                      + (self.tracked.get("tools") or []))
            self._oversikt = H.Scenoversikt(
                self.rader, roller, self.plan.get("forvantat_rorliga"))
        return self._oversikt

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
            if self.vantar_grepp():
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
            h["placering"]["tappad"] = True
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
                    rader.append("EDGE %s %s t=%.3fs" % (self._rent(signal), flank, t))
                    h["flanker"].append({"signal": signal, "flank": flank, "t": t})
                forra = v

        # PLC-variablerna ligger pa SAMMA tidsaxel som fysiken och far darfor
        # samma radform. Prefixet plc: skiljer dem fran VC:s egna signaler, och
        # grammatikens <signal> ar ett namn utan blanksteg, sa prefixet ryms
        # utan att kontraktet behover andras.
        plcflanker = H.plcflanker(self.rader, PLC_FARSK_S)
        for f in plcflanker:
            rader.append("EDGE %s %s t=%.3fs"
                         % (self._rent(f["signal"]), f["flank"], f["t"]))
        h["flanker"].extend(plcflanker)
        h["plc_gammal"] = [float(r.get("t", 0.0)) for r in self.rader
                           if r.get("plc_gammal")]
        if h["plc_gammal"]:
            self.skal.append(
                "%d PLC-prov var aldre an sitt eget prov" % len(h["plc_gammal"]))
        # PLC-axelns giltighet (M-97): hur stor del av PLC-raderna bar en
        # hopfogning som tacker farskhetsfonstret? Rakningen ligger alltid i
        # underlaget; policyn (braketten) tillampas i _dom.
        h["plc_axel"] = H.plc_axel(self.rader, PLC_FARSK_S)
        h["plc_axel"]["max_andel"] = PLC_AXEL_MAX_ANDEL
        h["plc_axel"]["over_braketten"] = bool(
            h["plc_axel"]["rader_med_plc"]
            and h["plc_axel"]["andel_otackt"] > PLC_AXEL_MAX_ANDEL)
        if h["plc_axel"]["over_braketten"]:
            self.skal.append(
                "%d av %d PLC-prov bar en hopfogning som tacker "
                "farskhetsfonstret %.2f s (tak max %.3f s)"
                % (h["plc_axel"]["otackta"], h["plc_axel"]["rader_med_plc"],
                   PLC_FARSK_S, h["plc_axel"]["tak_max_s"] or 0.0))
        # Upplosningen MATS ur serien: provintervall, lasintervall och
        # hopfogningens tak. En fasdom utan den vore ett tal utan storhet.
        h["upplosning"] = H.upplosning(self.rader, self.run.get("rate_hz"),
                                       HOPFOGNING_PRIOR_S)
        h["fas"] = H.fasforhallande(h["flanker"], self.plan.get("plc_par"),
                                    h["upplosning"])
        for f in h["fas"]:
            if f.get("max_ms") is None:
                continue
            if f.get("obestambar"):
                continue
            res = "unknown" if f.get("res_ms") is None else "%.1fms" % f["res_ms"]
            rader.append("PHASE plc:%s -> %s dt=%.1fms tol=%.1fms res=%s %s"
                         % (self._rent(f["plc"]), self._rent(f["signal"]),
                            f["dt_ms"], f["max_ms"], res, f["status"]))
            if f.get("status") == "OUT_OF_TOL":
                self.skal.append("fasen %s -> %s var %.0f ms, kravet ar %.0f ms "
                                 "(upplosning %.0f ms)"
                                 % (f["plc"], f["signal"], abs(f["dt_ms"]),
                                    f["max_ms"], f["res_ms"]))

        for signal, mover in (self.plan.get("movers") or {}).items():
            ms = self._latens(signal, mover)
            if ms is not None:
                rader.append("LATENCY %s -> %s %.1fms"
                             % (self._rent(signal), self._rent(mover), ms))
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
            rader.append("DWELL %s %.3fs req=%.3fs %s"
                         % (self._rent(station), faktisk, req, lage))
            h["dwell"].append({"station": station, "s": faktisk, "req_s": req, "lage": lage})

        rad = self._kapplopning(h)
        h["race"] = None if rad == "RACE none" else rad
        rader.append(rad)
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
                return "RACE %s+%s dt=%.1fms" % (self._rent(stig[i - 1]["signal"]),
                                                 self._rent(stig[i]["signal"]), dt)
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
                         % (self._rent(station), int(sista.get("in", 0)),
                            int(sista.get("out", 0)),
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
                rader.append("MINDIST %s %.1fmm t=%.3fs"
                             % (self._rent(namn), basta[0], basta[1]))
                h[namn] = {"min_mm": basta[0], "t": basta[1]}

        for r in self.rader:
            hit = r.get("hit")
            if hit:
                t = float(r.get("t", 0.0))
                rader.append("COLLISION %s x %s t=%.3fs"
                             % (self._rent(hit[0]), self._rent(hit[1]), t))
                h["kollision"] = {"a": hit[0], "b": hit[1], "t": t, "kalla": "hit"}
                if len(hit) >= 4:
                    # getHitFeatureA/B: VILKEN yta som trafffade vilken. Ryms
                    # inte i v1:s COLLISION-rad, sa den ligger i underlaget.
                    h["kollision"]["feature_a"] = hit[2]
                    h["kollision"]["feature_b"] = hit[3]
                self.skal.append("kollision mellan %s och %s vid t=%.2f s"
                                 % (hit[0], hit[1], t))
                break
        else:
            # Ingen traff ur en detektor. Da ar KONTAKTEN i minsta avstandet
            # kollisionsmattet: measureDistance ger 0,0 vid nudd OCH vid
            # overlapp (M-36, 900 mm overlapp gav 0,0), och detektorn som
            # skulle ha gett traffen tommer tyst sina nodlistor. Ett par
            # som bevakas ar ett par som inte far rora varandra.
            kontakt = self._kontakt()
            if kontakt:
                rader.append("COLLISION %s x %s t=%.3fs"
                             % (self._rent(kontakt["a"]), self._rent(kontakt["b"]),
                                kontakt["t"]))
                h["kollision"] = kontakt
                self.skal.append("kontakt mellan %s och %s vid t=%.2f s "
                                 "(minsta avstand %.1f mm)"
                                 % (kontakt["a"], kontakt["b"], kontakt["t"],
                                    kontakt["d_mm"]))
            else:
                rader.append("COLLISION none")
        return rader, h

    def _parnamn(self, namn):
        """(a, b) for ett bevakat par: ur planens nodlistor nar de finns,
        annars ur parnamnet 'a+b'. Grammatikens COLLISION-rad kraver tva namn."""
        for post in (self.tracked.get("pairs") or []):
            if isinstance(post, dict) and post.get("namn") == namn:
                a = (post.get("a") or [namn])[0]
                b = (post.get("b") or [namn])[0]
                return str(a), str(b)
        if "+" in namn:
            a, b = namn.split("+", 1)
            return a, b
        return namn, namn

    def _kontakt(self):
        """Forsta provet dar ett bevakat par har minsta avstandet 0."""
        for r in self.rader:
            for namn in sorted(r.get("mind") or {}):
                d = r["mind"][namn]
                if d is None or d.get("d_mm") is None:
                    continue
                if float(d["d_mm"]) <= 0.0:
                    a, b = self._parnamn(namn)
                    return {"a": a, "b": b, "par": namn,
                            "t": float(r.get("t", 0.0)),
                            "d_mm": float(d["d_mm"]), "kalla": "mind"}
        return None

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

        if (self.vantar_grepp() and motion_h.get("grip") is None
                and not motion_h.get("for_fa_prov")):
            rader.append("NEVER_GRIPPED VIOLATION")
            overtradelse = True
        else:
            # Utan ett deklarerat verktyg pastod korningen aldrig att den skulle
            # gripa, och da ar ett uteblivet grepp ingen overtradelse. Att anda
            # kalla det ett brott hade gjort varje stationskorning rod av fel
            # skal - men slappt tvartom hade greppgrinden kunnat forsvinna genom
            # att man utelamnade en rad ur planen. Darfor kraever _dom i stallet
            # en deklarerad SEKVENS av den som inte griper.
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

    # -- scenen som helhet -------------------------------------------------

    def scenanalys(self, th):
        """Vad som hande i HELA scenen, inte bara i rollerna.

        Ingen av de har harledningarna far ett eget nyckelord i v1:s
        grammatik. De faller domen med sin orsak i klartext och ligger
        fullstandigt i eyes.json; ett forslag pa v2-rader star i
        42_ogat_utbyggt.md.
        """
        o = self.oversikt()
        h = {"rorliga": o.rorliga(), "stilla": o.stilla(), "okanda": o.okanda(),
             "profiler": o.profiler,
             "samtidiga": o.samtidiga()[:20],
             "forandringar": o.forandringar(),
             "narhet": o.narhet(),
             "ledtider": o.ledtider(),
             "oombedd": o.oombedd_rorelse(),
             "orort": o.orort_trots_signal(th.get("flanker") or [],
                                           self.plan.get("movers")),
             "gles": self.scen}
        h["utslungad"] = {}
        for namn in (self.tracked.get("parts") or []):
            serie = o.serier.get(namn)
            if not serie:
                continue
            kast = H.utslungad(serie)
            if kast:
                h["utslungad"][namn] = kast
                self.skal.append("%s slungades ivag i %.1f m/s vid t=%.2f s"
                                 % (namn, kast["fart_ms"], kast["t"]))
        h["aldrig_tagen"] = self._aldrig_tagen(o)
        h["obestambar"] = self._scen_obestambar(o)
        if h["oombedd"]:
            for post in h["oombedd"]:
                self.skal.append("%s rörde sig %.0f mm utan att någon bad om det"
                                 % (post["objekt"], post["vaglangd_mm"]))
        for post in (h["orort"] or []):
            self.skal.append("%s fick %s men %s"
                             % (post["objekt"], post["signal"], post["varfor"]))
        return h

    def _aldrig_tagen(self, o):
        """Detaljen stod still i VARLDEN medan verktyget gjorde hela resan.

        Skild fran NEVER_GRIPPED, som bara sager att greppmangden var tom. Den
        har sager VARFOR: det fanns inget att gripa om, for delen rorde sig
        aldrig. Tva celler skiljer dem at (se tests/celler.py).
        """
        delnamn, verktygsnamn = self._del_och_verktyg()
        if delnamn is None or verktygsnamn is None:
            return None
        pd = o.profiler.get(delnamn)
        pv = o.profiler.get(verktygsnamn)
        if pd is None or pv is None or pd["stilla"] is None:
            return None
        if pd["stilla"] and pv["stilla"] is False:
            return {"del": delnamn, "verktyg": verktygsnamn,
                    "del_vaglangd_mm": round(pd["vaglangd_mm"], 3),
                    "verktyg_vaglangd_mm": round(pv["vaglangd_mm"], 3)}
        return None

    def _scen_obestambar(self, o):
        """Nar scenens grindar INTE gar att lita pa - utglesad eller oläst.

        Fail-closed: en utglesad serie far inte lasas som "allt stod still".
        """
        gles = (self.scen or {}).get("gles_faktor", 1)
        if self.plan.get("forvantat_rorliga") is None:
            return None
        if o.okanda():
            return "%d objekt lastes aldrig av" % len(o.okanda())
        varsta = 0.0
        for namn in o.profiler:
            varsta = max(varsta, o.profiler[namn]["olast_andel"])
        if varsta > SCEN_OLAST_MAX_ANDEL:
            hur = ("glesningsfaktor %d" % gles) if gles > 1 else "okand orsak"
            return ("%.0f %% av proven saknar en scenavlasning (%s)"
                    % (varsta * 100.0, hur))
        return None

    # -- robotleder ---------------------------------------------------------

    def robotanalys(self):
        o = self.oversikt()
        led = H.Ledanalys(self.rader, self.ledgranser, self.ledtyper,
                          self.plan.get("robot_tcp"), o.serier)
        h = led.analysera()
        for robot in sorted(h):
            d = h[robot]
            for g in d.get("granser_nadda", []):
                if g["over"]:
                    self.skal.append(
                        "%s led %d gick förbi sin gräns (%.2f av [%.2f, %.2f])"
                        % (robot, g["led"], g["varde"], g["gransvarden"][0],
                           g["gransvarden"][1]))
            for sing in d.get("singularitet", []):
                if not sing.get("obestambar"):
                    self.skal.append(
                        "%s stod i kinematisk urartning %.2f-%.2f s"
                        % (robot, sing["start_s"], sing["slut_s"]))
            for f in d.get("foljfel", []):
                if not f["nadde_malet"]:
                    self.skal.append(
                        "%s led %d nådde aldrig sitt kommenderade värde "
                        "(%.3f kvar)" % (robot, f["led"], f["kvarstaende_fel"]))
        return h

    # -- stationer ----------------------------------------------------------

    def stationsanalys(self):
        h = H.stationslage(self.rader)
        krav = self.plan.get("genomstromning") or {}
        h["_krav"] = dict(krav)
        h["_brott"] = []
        for station in sorted(h):
            if station.startswith("_"):
                continue
            d = h[station]
            if not isinstance(d, dict) or "svalt_s" not in d:
                continue
            for nyckel, etikett in (("svalt", "svalt"), ("blockerad", "blockerad")):
                tak = krav.get("max_%s_s" % nyckel)
                if tak is None:
                    continue
                matt = d["%s_s" % nyckel]
                if matt > float(tak) + GENOMSTROMNING_MARGINAL_S:
                    h["_brott"].append({"station": station, "vad": etikett,
                                        "matt_s": matt, "krav_s": float(tak)})
                    self.skal.append(
                        "%s var %s %.1f s, kravet är högst %.1f s"
                        % (station, etikett, matt, float(tak)))
        return h

    # -- stationens sekvens -------------------------------------------------

    def _roller(self):
        """(har_del, har_verktyg). Vad planen har DEKLARERAT, inte vad som hande."""
        return (bool(self.tracked.get("parts")), bool(self.tracked.get("tools")))

    def vantar_grepp(self):
        """Ska korningen alls gripa nagot?

        Greppgrinden ar skriven for en plockcell: en DEL och ett VERKTYG. En
        station som styrs av structured text har ingen av delarna - dess arbete
        ar en ORDNING i tiden. Att kraeva ett grepp av den vore att mata fel
        storhet, och att slappa kravet for en plockcell vore att sluta mata.
        Fragan avgors darfor av vad planen deklarerat, en gang, har.
        """
        del_, verktyg = self._roller()
        return del_ and verktyg

    def stationssekvens(self, th):
        """Den deklarerade stegordningen och forreglingen, matta.

        Ingen deklaration ger ingen dom - och det ar INTE ett godkannande.
        `_dom` skiljer "ingen fraga stalld" fran "fragan stalld och besvarad".
        """
        h = {"sekvens": None, "forregling": None}
        spec = self.plan.get("sekvens")
        flanker = th.get("flanker") or []
        t_slut = float(self.run.get("dur_s", 0.0)) or (
            max([float(r.get("t", 0.0)) for r in self.rader]) if self.rader else 0.0)
        if spec:
            d = H.sekvensdom(flanker, spec, t_slut)
            h["sekvens"] = d
            for fel in d["brott"]:
                self.skal.append(fel)
            for fel in d.get("tidsbrott") or []:
                self.skal.append(fel)
            if d["obestambar"] and not d["brott"] and not d.get("tidsbrott"):
                self.skal.append("sekvensen gick inte att doma: %s" % d["obestambar"])
        par = self.plan.get("forregling")
        if par:
            # Taket ar seriens eget provintervall. En overlapp kortare an sa
            # gar inte att skilja fran tva flanker i samma prov.
            rate = float(self.run.get("rate_hz", 0.0))
            tak = (1.0 / rate) if rate > 0 else 0.0
            d = H.forreglingsbrott(self.rader, par, tak)
            h["forregling"] = d
            for post in d:
                if post.get("brott"):
                    self.skal.append(
                        "%s och %s var hoga samtidigt i %.2f s (fran t=%.2f s)"
                        % (post["a"], post["b"], post["overlapp_s"],
                           post["t_forst"]))
        return h

    # -- scenforstaelse i ord ----------------------------------------------

    def berattelse(self):
        """Vad pagick i scenen, i ord. ALDRIG en dom.

        I1 star fast: ogats DOM ar auktoritativ, och den ar domsraden. Den har
        texten ar en redogorelse for underlaget och far inte forvaxlas med
        den - darfor innehaller den inga ord om godkant eller underkant.
        """
        h = dict(self.harledt.get("scene") or {})
        h["grepp"] = (self.harledt.get("motion") or {}).get("grip")
        h["stationer"] = self.harledt.get("stationer")
        h["robotar"] = self.harledt.get("robotar")
        h["fas"] = (self.harledt.get("timing") or {}).get("fas")
        return H.berattelse(self.oversikt(), h, self.run)

    def vad_pagar(self, t):
        """Svaret pa 'vad pagar i scenen just nu' vid en tidpunkt."""
        h = dict(self.harledt.get("scene") or {})
        h["grepp"] = (self.harledt.get("motion") or {}).get("grip")
        h["stationer"] = self.harledt.get("stationer")
        return H.vad_pagar(self.oversikt(), float(t), h)

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
        scen = self.scenanalys(th)
        robotar = self.robotanalys()
        stationer = self.stationsanalys()
        sekvens = self.stationssekvens(th)
        self.harledt = {"motion": mh, "timing": th, "throughput": gh,
                        "safety": sh, "honesty": hh, "scene": scen,
                        "robotar": robotar, "stationer": stationer,
                        "station": sekvens}
        self.harledt["berattelse"] = self.berattelse()

        gen = gen + self._genomflodesrader(stationer)
        seq = self._sekvensrader(sekvens)
        scenrader = self._scenrader(scen)
        granser = self._granser(th)
        for namn, rader in (("MOTION", motion), ("TIMING", tid),
                            ("SEQUENCE", seq), ("THROUGHPUT", gen),
                            ("SAFETY", sak), ("SCENE", scenrader),
                            ("HONESTY", hed), ("LIMITS", granser)):
            if namn in ("SEQUENCE", "SCENE") and not rader:
                # Ingen fraga stalld pa den sidan: da skrivs inte sektionen.
                # En tom sektion hade sett ut som "inget att anmarka pa".
                continue
            r.sektion(namn)
            for rad in rader:
                r.rad(rad)

        varde, orsak = self._dom(mh, th, sh, hh, scen, robotar, stationer,
                                 sekvens)
        r.satt_dom(varde, orsak)
        return r

    # -- v2-raderna ---------------------------------------------------------

    def _genomflodesrader(self, stationer):
        """STARVED/BLOCKED mot ett deklarerat krav, och flaskhalsen."""
        rader = []
        krav = stationer.get("_krav") or {}
        for station in sorted(stationer):
            if station.startswith("_"):
                continue
            d = stationer[station]
            if not isinstance(d, dict) or "svalt_s" not in d:
                continue
            for nyckel, ord_ in (("svalt", "STARVED"), ("blockerad", "BLOCKED")):
                tak = krav.get("max_%s_s" % nyckel)
                if tak is None:
                    continue
                matt = d["%s_s" % nyckel]
                over = matt > float(tak) + GENOMSTROMNING_MARGINAL_S
                rader.append("%s %s %.3fs req=%.3fs %s"
                             % (ord_, self._rent(station), matt, float(tak),
                                "EXCEEDED" if over else "OK"))
        if any(not s.startswith("_") for s in stationer):
            fh = stationer.get("_flaskhals")
            if fh:
                rader.append("BOTTLENECK %s %s %.1f%%"
                             % (self._rent(fh["station"]),
                                "starved" if fh["orsak"] == "svalt" else "blocked",
                                fh["andel"] * 100.0))
            else:
                rader.append("BOTTLENECK none")
        return rader

    def _sekvensrader(self, sekvens):
        """CYCLES, de steg som inte var OK, rakningar over taket, forreglingen."""
        rader = []
        seq = sekvens.get("sekvens")
        if seq is not None:
            rader.append("CYCLES judged=%d broken=%d late=%d truncated=%d req=%d"
                         % (seq.get("domda", 0), len(seq.get("brott") or []),
                            len(seq.get("tidsbrott") or []),
                            seq.get("avhuggna", 0),
                            int((self.plan.get("sekvens") or {}).get("min_cykler", 1))))
            for cykel in seq.get("cykler") or []:
                if cykel.get("avhuggen"):
                    continue
                for steg in cykel.get("steg") or []:
                    if steg.get("status", "OK") == "OK":
                        continue
                    if steg.get("status") == "INCONCLUSIVE":
                        # Grammatiken (EYES v2) har ingen INCONCLUSIVE-form for
                        # STEP. Osakerheten bars av domsraden och av
                        # derived.station.sekvens.osakra, inte av en STEP-rad
                        # som lasaren skulle kasta pa. Skulden star i M-97.
                        continue
                    t = "" if steg.get("dt_s") is None else " t=%.3fs" % steg["dt_s"]
                    rader.append("STEP %d %s %s %s%s win=%.2fs..%.2fs"
                                 % (cykel["nr"], self._rent(steg["signal"]),
                                    steg["flank"], steg["status"], t,
                                    steg["min_s"], steg["max_s"]))
                hogst = (self.plan.get("sekvens") or {}).get("hogst") or {}
                for signal in sorted(cykel.get("antal") or {}):
                    n = cykel["antal"][signal]
                    tak = int(hogst.get(signal, n))
                    if n > tak:
                        rader.append("COUNT %d %s n=%d max=%d EXCEEDED"
                                     % (cykel["nr"], self._rent(signal), n, tak))
        for post in (sekvens.get("forregling") or []):
            if post.get("obestambar"):
                lage = "INCONCLUSIVE"
            else:
                lage = "BROKEN" if post.get("brott") else "OK"
            rader.append("INTERLOCK %s+%s %s overlap=%.3fs"
                         % (self._rent(post["a"]), self._rent(post["b"]), lage,
                            post.get("overlapp_s", 0.0)))
        return rader

    def _scenrader(self, scen):
        """Hela scenen, i grammatik. Bara rader vars fraga har stallts."""
        rader = []
        o = self.oversikt()
        if not o.profiler:
            return rader
        rader.append("OBJECTS total=%d moving=%d still=%d unread=%d"
                     % (len(o.profiler), len(o.rorliga()), len(o.stilla()),
                        len(o.okanda())))
        gles = self.scen or {}
        if gles.get("gles_faktor") is not None:
            tak = any(h.get("orsak") == "TAK" for h in (gles.get("handelser") or []))
            median = ((gles.get("kostnad_ms") or {}).get("median") or 0.0)
            rader.append("THINNED factor=%d %s budget=%.1fms median=%.3fms"
                         % (int(gles["gles_faktor"]), "CEILING" if tak else "OK",
                            float(gles.get("budget_ms") or 0.0), float(median)))
        oombedd = scen.get("oombedd")
        if oombedd is not None:
            if oombedd:
                post = oombedd[0]
                rader.append("UNCOMMANDED %s dist=%.1fmm t=%.3fs"
                             % (self._rent(post["objekt"]), post["vaglangd_mm"],
                                post.get("t") or 0.0))
            else:
                rader.append("UNCOMMANDED none")
        if self.plan.get("movers"):
            orort = scen.get("orort") or []
            if orort:
                post = orort[0]
                rader.append("IDLE_COMMANDED %s -> %s t=%.3fs"
                             % (self._rent(post["signal"]), self._rent(post["objekt"]),
                                post["t"]))
            else:
                rader.append("IDLE_COMMANDED none")
        if self.tracked.get("parts"):
            kast = scen.get("utslungad") or {}
            if kast:
                namn = sorted(kast)[0]
                rader.append("FLUNG %s %.2fm/s t=%.3fs"
                             % (self._rent(namn), kast[namn]["fart_ms"], kast[namn]["t"]))
            else:
                rader.append("FLUNG none")
        return rader

    def _granser(self, th):
        """LIMITS: vad ogat INTE ser. Grinden kraver sektionen.

        Det ar ingen fotnot. Ett PASS ur ogat betyder att inget fel syntes i
        det som simulerades, i den upplosning serien hade. Raderna sager
        exakt vad det ar: det som inte finns i simuleringen alls, hur fint
        ogat kan skilja tva tidpunkter, och vad som ar uteslutet ur talen.
        """
        rader = ["NOT_SIMULATED %s" % namn for namn in K.EJ_SIMULERAT]
        u = th.get("upplosning") or {}
        prov = u.get("prov_s")
        if prov is None:
            rate = float(self.run.get("rate_hz") or 0.0)
            prov = (1.0 / rate) if rate > 0 else 0.0
        las = u.get("las_s")
        fas = u.get("fas_s")
        rader.append("RESOLUTION sample=%.1fms read=%s join=%.2fms %s phase=%s"
                     % (prov * 1000.0,
                        "unknown" if las is None else "%.1fms" % (las * 1000.0),
                        float(u.get("hopfogning_s", HOPFOGNING_PRIOR_S)) * 1000.0,
                        u.get("hopfogning_kalla", "PRIOR"),
                        "unknown" if fas is None else "%.1fms" % (fas * 1000.0)))
        rader.append("EXCLUDED plc_scan %.1fms" % (PLC_SKAN_S * 1000.0))
        return rader

    # -- de fem domarna -----------------------------------------------------
    #
    # Fas 15 (70_faser.md): domar som faller pa SEKVENS, TIMING, GREPP,
    # KOLLISION och GENOMFLODE - var och en med en trasig cell som maste
    # fallas, och som ar osynlig for de andra fyra. Varje domare laser bara
    # sitt eget underlag och svarar med ett utfall och sina fynd; _dom
    # rangordnar utfallen. Domarna ar metoder i DOMARE sa ett prov kan slacka
    # EN av dem och se att exakt dess celler blir grona (M-65 §4).

    DOMARE = ("sekvens", "timing", "grepp", "kollision", "genomflode")

    def _doma_sekvens(self, h):
        """Kom stegen, i ratt ordning, och holl forreglingen?"""
        sekvens = h.get("station") or {}
        seq = sekvens.get("sekvens")
        forregling = sekvens.get("forregling")
        if seq is None and forregling is None:
            return None, [], {}
        fynd = {"forregling": False, "uteblivet": False, "obestambar": None}
        skal = []
        for post in (forregling or []):
            if post.get("brott"):
                fynd["forregling"] = True
                skal.append("förreglingen bröts")
        if seq is not None:
            if seq.get("brott"):
                fynd["uteblivet"] = True
                skal.append("stationens sekvens hölls inte")
            elif seq.get("obestambar"):
                fynd["obestambar"] = seq["obestambar"]
        if fynd["forregling"] or fynd["uteblivet"]:
            return "FAIL", skal, fynd
        if fynd["obestambar"]:
            return "INCONCLUSIVE", ["sekvensen gick inte att dömas: %s"
                                    % fynd["obestambar"]], fynd
        return "PASS", [], fynd

    def _doma_timing(self, h):
        """Kom det som kom i TID: stegens fonster, PLC-fasen, uppehallet,
        och tva utgangar som inte far ga hoga inom samma fonster."""
        th = h.get("timing") or {}
        seq = (h.get("station") or {}).get("sekvens")
        fynd = {"for_sent": False, "fas_ut": False, "fas_okand": None,
                "steg_osakert": None, "uppehall": False, "kapplopning": False}
        skal = []
        fragad = False
        if seq is not None:
            fragad = True
            if seq.get("tidsbrott"):
                fynd["for_sent"] = True
                skal.append("stationens tider hölls inte")
            elif seq.get("osakra"):
                # Steget lag utanfor sitt fonster med mindre an hopfogningens
                # egen osakerhet (M-97). Varken ett fel eller ett godkannande.
                fynd["steg_osakert"] = seq["osakra"][0]
        for f in (th.get("fas") or []):
            if f.get("max_ms") is None:
                continue
            fragad = True
            if f.get("status") == "OUT_OF_TOL":
                fynd["fas_ut"] = True
                skal.append("fasen mellan PLC och scen överskrider kravet")
            elif f.get("status") == "INCONCLUSIVE" and fynd["fas_okand"] is None:
                fynd["fas_okand"] = f.get("skal") or f.get("obestambar") or "okänd orsak"
        for d in th.get("dwell", []):
            fragad = True
            if d["lage"] == "SHORT":
                fynd["uppehall"] = True
                skal.append("uppehållet för kort")
        if th.get("race"):
            fragad = True
            fynd["kapplopning"] = True
            skal.append("två utgångar gick höga inom samma fönster")
        if not fragad:
            return None, [], fynd
        if fynd["for_sent"] or fynd["fas_ut"] or fynd["uppehall"] or fynd["kapplopning"]:
            return "FAIL", skal, fynd
        if fynd["fas_okand"]:
            return "INCONCLUSIVE", ["fasen kan inte dömas: %s" % fynd["fas_okand"]], fynd
        if fynd["steg_osakert"]:
            return "INCONCLUSIVE", ["stegets tid ligger inom hopfogningens "
                                    "osäkerhet: %s" % fynd["steg_osakert"]], fynd
        return "PASS", [], fynd

    def _doma_grepp(self, h):
        """Bildades greppet, holl det, och hamnade delen ratt? Bara for en
        plan som deklarerat en del och ett verktyg."""
        if not self.vantar_grepp():
            return None, [], {}
        mh = h.get("motion") or {}
        hh = h.get("honesty") or {}
        fynd = {"aldrig": False, "teleport": False, "glid": False,
                "kort": False, "plac_okand": False, "fel": False, "tappad": False}
        skal = []
        if mh.get("for_fa_prov"):
            return "INCONCLUSIVE", ["för få prov"], fynd
        if mh.get("grip") is None:
            fynd["aldrig"] = True
            return "FAIL", ["greppet bildades aldrig"], fynd
        if hh.get("teleport"):
            fynd["teleport"] = True
            skal.append("greppet bildades på avstånd")
        carry = mh.get("carry") or {}
        plac = mh.get("placering")
        if carry.get("span_s", 0.0) < CARRY_MIN_SPAN_S:
            fynd["kort"] = True
        elif carry.get("rot_deg", 0.0) > CARRY_RIGID_DEG:
            fynd["glid"] = True
            skal.append("delen gled i greppet")
        if plac is None:
            fynd["plac_okand"] = True
        elif plac.get("tappad"):
            fynd["tappad"] = True
            skal.append("delen tappades")
        elif plac["fel_mm"] > plac["tol_mm"]:
            fynd["fel"] = True
            skal.append("delen hamnade fel")
        if fynd["teleport"] or fynd["glid"] or fynd["fel"] or fynd["tappad"]:
            return "FAIL", skal, fynd
        if fynd["kort"]:
            return "INCONCLUSIVE", ["bärsträckan för kort"], fynd
        if fynd["plac_okand"]:
            return "INCONCLUSIVE", ["placeringen kunde inte dömas"], fynd
        return "PASS", [], fynd

    def _doma_kollision(self, h):
        """Rorde tva bevakade kroppar varandra? Bara nar nagot bevakats."""
        sh = h.get("safety") or {}
        bevakat = any(("mind" in r or "hit" in r) for r in self.rader)
        if not bevakat and not sh.get("kollision"):
            return None, [], {}
        if sh.get("kollision"):
            k = sh["kollision"]
            return "FAIL", ["kollision mellan %s och %s" % (k["a"], k["b"])], \
                {"kollision": True}
        return "PASS", [], {"kollision": False}

    def _doma_genomflode(self, h):
        """Holl stationerna det deklarerade genomflodeskravet?

        Ett krav utan en enda PROVAD station ar inte uppfyllt - det ar
        obesvarat. MATT (M-74): en plan som deklarerade `genomstromning` mot en
        serie helt utan stationsprov fick PASS, alltsa ett godkannande av en
        fraga grinden aldrig stallde. Det ar samma fel som I3 forbjuder pa
        alla andra stallen, och det ar farligast just har: `stat` kraver ett
        vcStatistics-beteende i scenen, och saknas det tiger provtagningen.
        """
        stationer = h.get("stationer") or {}
        if not stationer.get("_krav"):
            return None, [], {}
        provade = [namn for namn, d in stationer.items()
                   if not namn.startswith("_") and isinstance(d, dict)
                   and "svalt_s" in d]
        if not provade:
            return "INCONCLUSIVE", ["genomströmningskravet är deklarerat, men "
                                    "ingen station provades"], \
                {"brott": [], "provade": 0}
        if stationer.get("_brott"):
            return "FAIL", ["genomströmningskravet hölls inte"], \
                {"brott": list(stationer["_brott"]), "provade": len(provade)}
        return "PASS", [], {"brott": [], "provade": len(provade)}

    def domar(self, harledt=None):
        """{domare: {"utfall": PASS|FAIL|INCONCLUSIVE|None, "skal": [...],
        "fynd": {...}}}. None = ingen fraga stalld, och det ar INTE ett PASS."""
        h = harledt if harledt is not None else self.harledt
        ut = {}
        for namn in self.DOMARE:
            utfall, skal, fynd = getattr(self, "_doma_" + namn)(h)
            ut[namn] = {"utfall": utfall, "skal": skal, "fynd": fynd}
        return ut

    def _dom(self, mh, th, sh, hh, scen=None, robotar=None, stationer=None,
             sekvens=None):
        # Ordningen ar en rangordning: en overtradelse slar allt annat, och en
        # osakerhet far ALDRIG bli ett PASS. De fem domarna svarar var for
        # sig (domar()); har bestams vem som far saga sitt forst.
        scen = scen or {}
        robotar = robotar or {}
        stationer = stationer or {}
        sekvens = sekvens or {}
        d = self.domar({"motion": mh, "timing": th, "safety": sh, "honesty": hh,
                        "stationer": stationer, "station": sekvens})
        self.harledt["domar"] = d
        if hh.get("overtradelse"):
            # Tva av de fyra hederlighetsraderna handlar om GREPPET
            # (TELEPORT_TRANSFER, NEVER_GRIPPED), och domsraden ska namna den
            # domare som ager fragan - inte bara regeln som tvingade domen.
            if hh.get("teleport") or (self.vantar_grepp() and mh.get("grip") is None
                                      and not mh.get("for_fa_prov")):
                return "FAIL", self._orsak("grasp: hederlighetsgrind fälld")
            return "FAIL", self._orsak("integrity: hederlighetsgrind fälld")
        if mh.get("for_fa_prov"):
            return "INCONCLUSIVE", self._orsak("för få prov")
        if scen.get("obestambar"):
            # En utglesad eller oläst scen far inte bli ett godkannande. Det
            # ar samma regel som for fa prov, bara pa scenens sida.
            return "INCONCLUSIVE", self._orsak("scenen går inte att döma: %s"
                                               % scen["obestambar"])
        if th.get("plc_gammal"):
            # Ett PLC-varde aldre an sitt prov ligger inte pa samma tidsaxel
            # som fysiken, och hela poangen med PLC i serien var att de gor
            # det. Da ar fasforhallandet inget matt.
            return "INCONCLUSIVE", self._orsak("PLC-värdena var inte samtidiga")
        if (th.get("plc_axel") or {}).get("over_braketten"):
            # M-97, fas 8:s OGILTIG: hopfogningens matta osakerhet tacker
            # farskhetsfonstret i for stor del av korningen. PLC-vardena ar da
            # inte bevisat pa fysikens tidsaxel, och ingen dom som vilar pa
            # dem ar ett matt - varken FAIL eller PASS.
            return "INCONCLUSIVE", self._orsak(
                "PLC-axeln går inte att lita på: hopfogningens osäkerhet täcker "
                "färskhetsfönstret i %.0f %% av PLC-proven"
                % (100.0 * th["plc_axel"]["andel_otackt"]))
        grepp, timing = d["grepp"], d["timing"]
        if grepp["fynd"].get("aldrig"):
            return "FAIL", self._orsak("grasp: greppet bildades aldrig")
        if d["kollision"]["utfall"] == "FAIL":
            return "FAIL", self._orsak("kollision: " + d["kollision"]["skal"][0])
        if scen.get("oombedd"):
            return "FAIL", self._orsak("scen: något i scenen rörde sig oombett")
        if scen.get("utslungad"):
            return "FAIL", self._orsak("scen: delen slungades iväg")
        for post in (scen.get("orort") or []):
            return "FAIL", self._orsak("scen: ett kommenderat objekt rörde sig aldrig")
        brott = self._robotbrott(robotar)
        if brott:
            return "FAIL", self._orsak("robot: " + brott)
        if d["genomflode"]["utfall"] == "FAIL":
            return "FAIL", self._orsak("throughput: genomströmningskravet hölls inte")
        if d["genomflode"]["utfall"] == "INCONCLUSIVE":
            return "INCONCLUSIVE", self._orsak(
                "throughput: " + d["genomflode"]["skal"][0])
        # Stationens egna grindar. Forreglingen forst: den ar den enda av de
        # tva som ar farlig, och den ar sann aven i en korning dar sekvensen
        # for ovrigt holl.
        if d["sekvens"]["fynd"].get("forregling"):
            return "FAIL", self._orsak("interlock: förreglingen bröts")
        if d["sekvens"]["fynd"].get("uteblivet"):
            return "FAIL", self._orsak("sequence: stationens sekvens hölls inte")
        if timing["fynd"].get("for_sent"):
            return "FAIL", self._orsak("timing: stationens tider hölls inte")
        if timing["fynd"].get("fas_ut"):
            return "FAIL", self._orsak("timing: fasen mellan PLC och scen "
                                       "överskrider kravet")
        if d["sekvens"]["utfall"] == "INCONCLUSIVE":
            return "INCONCLUSIVE", self._orsak(
                "sekvensen gick inte att döma: %s" % d["sekvens"]["fynd"]["obestambar"])
        if all(v["utfall"] is None for v in d.values()):
            # Ingen av de fem domarna fick en fraga: varken greppande roller,
            # en deklarerad sekvens, ett tidskrav, ett bevakat par eller ett
            # genomflodeskrav. Da har ingen fraga stallts, och ett PASS hade
            # varit ett godkannande av ingenting (I3).
            return "INCONCLUSIVE", self._orsak(
                "planen deklarerar varken en del och ett verktyg att gripa med "
                "eller en sekvens att följa; det finns ingenting att döma")
        if grepp["utfall"] is not None:
            # Bar- och placeringsgrindarna mater greppet. En station som inte
            # griper har ingen barstracka och inget mal, och att kraeva dem av
            # den vore att falla pa en fraga ingen stallt.
            if grepp["fynd"].get("kort"):
                return "INCONCLUSIVE", self._orsak("bärsträckan för kort")
            if grepp["fynd"].get("glid"):
                return "FAIL", self._orsak("grasp: delen gled i greppet")
            if grepp["fynd"].get("plac_okand"):
                return "INCONCLUSIVE", self._orsak("placeringen kunde inte dömas")
            if grepp["fynd"].get("tappad"):
                return "FAIL", self._orsak("grasp: delen tappades")
            if grepp["fynd"].get("fel"):
                return "FAIL", self._orsak("grasp: delen hamnade fel")
        if timing["fynd"].get("uppehall"):
            return "FAIL", self._orsak("timing: uppehållet för kort")
        if timing["fynd"].get("kapplopning"):
            return "FAIL", self._orsak("race: två utgångar gick höga inom "
                                       "samma fönster")
        if timing["fynd"].get("fas_okand"):
            return "INCONCLUSIVE", self._orsak(
                "timing: fasen kan inte dömas: %s" % timing["fynd"]["fas_okand"])
        if timing["fynd"].get("steg_osakert"):
            return "INCONCLUSIVE", self._orsak(
                "timing: stegets tid ligger inom hopfogningens osäkerhet")
        return "PASS", "allt inom marginal"

    @staticmethod
    def _robotbrott(robotar):
        """Rangordningen inom robotdelen, i den ordning en operator vill veta.

        Gransoverskridandet forst: det ar det enda av de tre som ar ett
        entydigt fel. Urartning och foljfel kan vara avsiktliga i en riggad
        cell, men de ar aldrig nagot man vill missa.
        """
        for robot in sorted(robotar):
            for g in (robotar[robot].get("granser_nadda") or []):
                if g["over"]:
                    return "led %d på %s gick förbi sin gräns" % (g["led"], robot)
        for robot in sorted(robotar):
            for sing in (robotar[robot].get("singularitet") or []):
                if not sing.get("obestambar"):
                    return "kinematisk urartning i %s" % robot
        for robot in sorted(robotar):
            for f in (robotar[robot].get("foljfel") or []):
                if not f["nadde_malet"]:
                    return "led %d på %s nådde inte sitt kommenderade värde" % (
                        f["led"], robot)
        return None

    def _orsak(self, kort):
        if not self.skal:
            return kort
        return "%s: %s" % (kort, "; ".join(self.skal[:3]))


def doma(data, plan=None):
    """Bekvamlighet: tidsserie in, (rapporttext, Rapport, Analys) ut."""
    a = Analys(data, plan)
    r = a.rapport()
    return r.text(), r, a
