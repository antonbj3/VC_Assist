# -*- coding: utf-8 -*-
"""L3: FAS 15, hopfogningen mot VC:s EGEN brygga. Mater M-87.

M-42 och M-65 matte hopfogningens fel `d` mot en attrapprigg vars pump fick
sova 5 respektive 10 ms per slag. Bada mattes utan VC. M-65 skrev det rent ut
som ett hal: "Hopfogningen ar matt mot M-42:s rigg, inte mot VC:s brygga."
Den har korningen stanger det halet.

VAD SOM MATS

  1. TVA KLOCKOR. Vaggklockan (kopplarens alder mats i den) mot VC:s
     simuleringstid (ogats serie ar stamplad i den). Kvoten mats pa TVA
     oberoende satt: pumpens egen `takt()` - den som RAKNAR OM aldern - och
     en lang regression wall -> sim ur bryggans egna simtidsavlasningar.
     Skiljer de sig ar det inte en detalj: skillnaden ar direkt ett fel i
     varje omraknad alder.

  2. TUR OCH RETUR genom bryggan, matt, per anrop.

  3. d = (ogats stampel) - (den SANNA simuleringstiden i lasogonblicket).
     Den sanna tiden ar inte kand exakt; den KLAMS mellan tva
     simtidsavlasningar, en fore och en efter. Klamman ar en HARD grans, och
     dess bredd ar kartans egen osakerhet. Den redovisas, den goms inte.

  4. d SVEPS over alderns storlek. Stampeln ar
     `simtid - alder * takt`, sa ett fel i takten skalar med ALDERN. En
     kopplare med 89 ms varv (M-39) har en alder pa tiondels sekunden, inte
     pa noll. Ett tak som bara bar tur och retur bar inte den termen.

  5. UPPLOSNINGEN ur en riktig korning: prov_s, las_s, hopfogning_s och
     dess kalla (RUN eller PRIOR).

    python3 tests/protocol/kor_fas15_hopfogning.py --json ut.json
"""
import argparse
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol", "stod"))

import installationsgrind                            # noqa: E402

import oga_harledning as H                           # noqa: E402
import oga_provtagning as OP                         # noqa: E402
from vc_assist_svc.klient import Klient              # noqa: E402
from vc_assist_svc.tokenplats import tokenfil        # noqa: E402

# KOPPLAREN SJALV, inte en efterlikning av den. Att skriva om aldern och
# taket har hade matt min egen kod; det som ska matas ar den vag ett riktigt
# varde tar. Ogonkoppling lagger pa rtt_tak() bade i aldern och som
# hopfogning_s - precis den kompensation M-42 satte.
from vc_assist_svc.plc.ogonkoppling import Ogonkoppling   # noqa: E402


def p(v, andel):
    """Percentil ur en lista. Ingen numpy inne i protokollkorningarna."""
    s = sorted(v)
    return s[min(len(s) - 1, int(round(andel * (len(s) - 1))))]


class Karta(object):
    """Wall -> sim, matt ur bryggans egna simtidsavlasningar.

    Varje avlasning ger en KLAMMA, inte en punkt: simtiden lastes nagon gang
    mellan anropets borjan och dess slut. Simuleringstiden vaxer monotont, sa
    en avlasning fore ett ogonblick ar en undre grans och en efter ar en ovre.
    Det ar en hard grans, och bredden ar kartans egen osakerhet.
    """

    def __init__(self):
        self.punkter = []          # (t_fore, t_efter, simtid)

    def las(self, k):
        t0 = time.time()
        s = k.simtid()
        t1 = time.time()
        self.punkter.append((t0, t1, float(s)))
        return s

    def klamma(self, t):
        """(lag, hog) simuleringstid vid vaggtiden t, eller None."""
        lag = hog = None
        for t0, t1, s in self.punkter:
            if t1 <= t:
                lag = s if lag is None else max(lag, s)
            if t0 >= t:
                hog = s if hog is None else min(hog, s)
        if lag is None or hog is None or hog < lag:
            return None
        return (lag, hog)

    def lutning(self):
        """Minsta kvadrat over hela fonstret: simsekunder per vaggsekund."""
        if len(self.punkter) < 2:
            return None, None
        w0 = self.punkter[0][0]
        xs = [((a + b) / 2.0 - w0) for a, b, _ in self.punkter]
        ys = [s for _, _, s in self.punkter]
        n = len(xs)
        sx, sy = sum(xs), sum(ys)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, ys))
        namn = n * sxx - sx * sx
        if namn == 0:
            return None, None
        b = (n * sxy - sx * sy) / namn
        a = (sy - b * sx) / n
        res = [abs(y - (a + b * x)) * 1000.0 for x, y in zip(xs, ys)]
        return b, {"max_ms": max(res), "p95_ms": p(res, .95),
                   "median_ms": p(res, .5), "n": n}


def _plan(objekt):
    """Minsta plan som ogat gar med pa. Rollen finns bara for att provtagningen
    ska starta - den har korningen mater PLC-axeln, inte greppet."""
    return {"template": "fas15_hopfogning", "parts": [objekt], "tools": [],
            "rate_hz": 20.0, "scen": "all"}


def _nagon_komponent(k):
    kod = ("import json\n"
           "app = getApplication()\n"
           "print(json.dumps([c.Name for c in list(app.Components)]))\n")
    namn = k.kor(kod)["result"]
    for n in namn:
        if n != "VcAssistBridge":
            return n
    raise RuntimeError("scenen har ingen komponent att provta")


def steg1_klockorna(k, sekunder, karta):
    """Pumpens egen takt mot den langa regressionen."""
    takter, spridningar = [], []
    slut = time.time() + sekunder
    while time.time() < slut:
        karta.las(k)
        st = k.oga_status()
        t = st.get("takt")
        if t is not None:
            takter.append(float(t))
        # Spridningen lases genom plc_in: den ar pumpens svar pa hur mycket
        # dess EGEN takt varierar over sitt fonster (M-87).
        sp = k.plc_in().get("takt_spridning")
        if sp is not None:
            spridningar.append(float(sp))
        time.sleep(0.02)
    lutning, res = karta.lutning()
    ut = {"n_takt": len(takter), "lang_kvot": lutning, "regression": res}
    # VC:s simuleringstid gar i STEG. Steget ar inte kosmetik: det ar
    # kvantiseringen som gor pumpens taktfonster oense med sig sjalvt, och
    # det ar den som term 2 i takt_spridning matter. Har mats det ur
    # kartans egna avlasningar - det minsta positiva spranget mellan tva.
    steg = sorted(set(round(karta.punkter[i][2] - karta.punkter[i - 1][2], 6)
                      for i in range(1, len(karta.punkter))))
    positiva = [x for x in steg if x > 0]
    if positiva:
        ut["simsteg"] = {"minsta_s": positiva[0], "storsta_s": positiva[-1],
                         "distinkta": len(positiva),
                         "de_fem_minsta": positiva[:5]}
    if takter:
        ut.update({"takt_median": p(takter, .5), "takt_p05": p(takter, .05),
                   "takt_p95": p(takter, .95),
                   "takt_min": min(takter), "takt_max": max(takter),
                   "takt_spann": max(takter) - min(takter)})
    if spridningar:
        ut.update({"spridning_median": p(spridningar, .5),
                   "spridning_p95": p(spridningar, .95),
                   "spridning_max": max(spridningar),
                   "n_spridning": len(spridningar)})
        # HALLER DEN? Spridningen ska tacka takten avstand till den langa
        # kvoten. Ett par dar den inte gor det ar ett par dar taket ljuger.
        if lutning is not None and takter:
            fel = [abs(t - lutning) for t in takter]
            ut["takt_fel_p95"] = p(fel, .95)
            ut["takt_fel_max"] = max(fel)
            ut["spridningen_tacker_taktfelet"] = bool(
                p(spridningar, .5) >= p(fel, .95))
    return ut


def steg2_tur_och_retur(k, varv):
    ping, plc = [], []
    for _ in range(varv):
        t0 = time.time(); k.ping(); ping.append((time.time() - t0) * 1000.0)
    for _ in range(varv):
        t0 = time.time()
        k.plc_in({"Matvarde": True}, alder_s=0.0)
        plc.append((time.time() - t0) * 1000.0)
    return {"ping_ms": {"median": p(ping, .5), "p95": p(ping, .95), "max": max(ping)},
            "plc_in_ms": {"median": p(plc, .5), "p95": p(plc, .95), "max": max(plc)}}


def steg3_d(k, karta, alder_s, varv, kvot):
    """d = stampeln - den sanna simuleringstiden i lasogonblicket.

    Aldern simuleras genom att lasogonblicket laggs `alder_s` bakat i
    vaggklockan. Det ar exakt vad en kopplare med det varvet gor: den skickar
    ett varde den las for `alder_s` sedan.

    Vagen ut gar genom RIKTIGA Ogonkoppling, inte genom en efterlikning: det
    ar dess `rtt_tak()` som bade kompenserar aldern och blir seriens tak, och
    en efterlikning hade matt min egen aritmetik.

    TVA SKATTNINGAR av den sanna tiden, med olika svagheter, och bada
    redovisas:
      klamman     hard grans mellan tva simtidsavlasningar. Kan inte ljuga,
                  men ar aldrig smalare an tva turer och returer.
      regressionen  hela fonstrets rata linje. Mycket tatare, men forutsatter
                  att simuleringstiden gar rakt mot vaggklockan.

    UPPDELNINGEN av d. Stampeln ar `simtid_pump - alder * takt`, sa

        d ~= -(pumpens simtid ar inaktuell) + alder * (kvot - takt)

    Andra termen skalar med ALDERN och ar noll bara nar pumpens matta takt
    rakar sammanfalla med den verkliga kvoten. Den raknas ut per varv ur
    svarets egen `takt` och redovisas for sig - annars gar det inte att saga
    VILKEN av de tva som bar felet.
    """
    kopplare = Ogonkoppling(k)
    kopplare.synka()
    rader = []
    for _ in range(varv):
        karta.las(k)
        t_las = time.time() - alder_s
        t0 = time.time()
        svar = kopplare.skjut_in({"Start": True}, t_last=t_las)
        t1 = time.time()
        karta.las(k)
        stampel = svar.get("pa")
        if stampel is None:
            rader.append({"fel": "ingen stampel"})
            continue
        kl = karta.klamma(t_las)
        if kl is None:
            rader.append({"fel": "ingen klamma"})
            continue
        lag, hog = kl
        rad = {
            "alder_s": alder_s,
            # Den alder kopplaren FAKTISKT skickade: (nu - t_las) + rtt_tak.
            "alder_skickad_s": (t0 - t_las) + kopplare.rtt_tak(),
            "stampel": stampel,
            "t_las": t_las,
            # d ar ett INTERVALL: stampeln minus en klamma ar en klamma.
            "d_lag_ms": (stampel - hog) * 1000.0,
            "d_hog_ms": (stampel - lag) * 1000.0,
            "klamma_ms": (hog - lag) * 1000.0,
            # Taket som ogats KALLA till slut bar, inte det som skickades:
            # rattelsen (M-87) kommer efter svaret, och det ar kallans tal
            # som foljer med in i raden. Kopplarens sista svar bar det.
            "tak_ms": None if (kopplare.sista_svar or {}).get("hopfogning_s") is None
                      else kopplare.sista_svar["hopfogning_s"] * 1000.0,
            "takt": svar.get("takt"),
            "rtt_ms": (t1 - t0) * 1000.0,
        }
        if rad["takt"] is not None and kvot is not None:
            rad["takttermen_ms"] = (rad["alder_skickad_s"]
                                    * (kvot - rad["takt"]) * 1000.0)
        rader.append(rad)
    bra = [r for r in rader if "fel" not in r and r["tak_ms"] is not None]
    if not bra:
        return {"alder_ms": alder_s * 1000.0, "varv": len(rader),
                "fel": [r.get("fel") for r in rader][:3]}
    # Regressionen som andra skattning, rakad ur HELA fonstret.
    lutning, _res = karta.lutning()
    w0 = karta.punkter[0][0]
    ys = [s for _, _, s in karta.punkter]
    xs = [((a + b) / 2.0 - w0) for a, b, _ in karta.punkter]
    m = sum(ys) / len(ys) - lutning * (sum(xs) / len(xs))
    for r in bra:
        r["d_reg_ms"] = (r["stampel"] - (m + lutning * (r["t_las"] - w0))) * 1000.0
    # Mitten av klamman ar den andra punktskattningen; kanterna bar felet.
    mitt = [(r["d_lag_ms"] + r["d_hog_ms"]) / 2.0 for r in bra]
    reg = [r["d_reg_ms"] for r in bra]
    # SAKER overtradelse: hela intervallet ligger utanfor taket. En klamma
    # som skar taket ar inte ett bevis at nagot hall, och far inte raknas som
    # ett av dem.
    saker = [r for r in bra
             if r["d_lag_ms"] > r["tak_ms"] or r["d_hog_ms"] < -r["tak_ms"]]
    mojlig = [r for r in bra
              if max(abs(r["d_lag_ms"]), abs(r["d_hog_ms"])) > r["tak_ms"]]
    reg_over = [r for r in bra if abs(r["d_reg_ms"]) > r["tak_ms"]]
    takttermer = [r["takttermen_ms"] for r in bra if "takttermen_ms" in r]
    ut = {
        "alder_ms": alder_s * 1000.0,
        "varv": len(bra),
        "d_median_ms": p(mitt, .5), "d_p05_ms": p(mitt, .05),
        "d_p95_ms": p(mitt, .95), "d_min_ms": min(mitt), "d_max_ms": max(mitt),
        "d_reg_median_ms": p(reg, .5), "d_reg_p05_ms": p(reg, .05),
        "d_reg_p95_ms": p(reg, .95),
        "d_reg_min_ms": min(reg), "d_reg_max_ms": max(reg),
        "klamma_median_ms": p([r["klamma_ms"] for r in bra], .5),
        "klamma_max_ms": max(r["klamma_ms"] for r in bra),
        "tak_median_ms": p([r["tak_ms"] for r in bra], .5),
        "tak_max_ms": max(r["tak_ms"] for r in bra),
        "rtt_median_ms": p([r["rtt_ms"] for r in bra], .5),
        "takt_median": p([r["takt"] for r in bra if r["takt"] is not None], .5)
                       if any(r["takt"] is not None for r in bra) else None,
        "saker_over_taket": len(saker),
        "saker_over_taket_pct": 100.0 * len(saker) / len(bra),
        "mojlig_over_taket": len(mojlig),
        "mojlig_over_taket_pct": 100.0 * len(mojlig) / len(bra),
        "reg_over_taket": len(reg_over),
        "reg_over_taket_pct": 100.0 * len(reg_over) / len(bra),
        "varsta_ms": max(max(abs(r["d_lag_ms"]), abs(r["d_hog_ms"])) - r["tak_ms"]
                         for r in bra),
        "varsta_reg_ms": max(abs(r["d_reg_ms"]) - r["tak_ms"] for r in bra),
    }
    if takttermer:
        ut.update({"takttermen_median_ms": p(takttermer, .5),
                   "takttermen_p05_ms": p(takttermer, .05),
                   "takttermen_p95_ms": p(takttermer, .95),
                   "takttermen_abs_max_ms": max(abs(x) for x in takttermer)})
    return ut


def steg5_upplosning(k, objekt, sekunder, las_intervall_s):
    """Upplosningen ur en RIKTIG korning: prov_s, las_s, hopfogning_s, fas_s.

    Kopplarvarvet efterliknas med `las_intervall_s`; M-39 matte 89 ms mot
    OpenPLC. Har finns ingen OpenPLC, och det STAR i mattningens LIMITS.
    """
    t0 = k.simtid()
    k.oga_start(_plan(objekt), simtid=t0)
    kopplare = Ogonkoppling(k)
    kopplare.synka()
    slut = time.time() + sekunder
    n = 0
    varannan = True
    try:
        while time.time() < slut:
            t_las = time.time()
            kopplare.skjut_in({"Start": varannan}, t_last=t_las)
            varannan = not varannan
            n += 1
            time.sleep(max(0.0, las_intervall_s - (time.time() - t_las)))
    finally:
        ut = k.oga_stopp()
    data = ut.get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret", "prov": ut.get("samples")}
    rader = data["rows"]
    u = H.upplosning(rader, data["run"].get("rate_hz"), 0.01345)
    med_plc = [r for r in rader if r.get("plc") is not None]
    gamla = [r for r in med_plc if r.get("plc_gammal")]
    med_tak = [r for r in med_plc if r.get("plc_hopfogning_s") is not None]
    aldrar = [r["plc_alder_s"] for r in med_plc if r.get("plc_alder_s") is not None]
    return {
        "prov": len(rader), "inskott": n,
        "kopplare_lagrade": kopplare.n_lagrade,
        "kopplare_utan_axel": kopplare.n_utan_axel,
        "kopplare_rtt_tak_ms": kopplare.rtt_tak() * 1000.0,
        "rader_med_plc": len(med_plc), "rader_gamla": len(gamla),
        "rader_med_tak": len(med_tak),
        "alder_median_ms": p(aldrar, .5) * 1000.0 if aldrar else None,
        "alder_max_ms": max(aldrar) * 1000.0 if aldrar else None,
        "upplosning": {"prov_ms": None if u["prov_s"] is None else u["prov_s"] * 1000.0,
                       "las_ms": None if u["las_s"] is None else u["las_s"] * 1000.0,
                       "hopfogning_ms": u["hopfogning_s"] * 1000.0,
                       "hopfogning_kalla": u["hopfogning_kalla"],
                       "fas_ms": None if u["fas_s"] is None else u["fas_s"] * 1000.0},
        "PLC_FARSK_S": OP.PLC_FARSK_S, "PLC_TYSTNAD_S": OP.PLC_TYSTNAD_S,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=None)
    ap.add_argument("--varv", type=int, default=120)
    ap.add_argument("--klocksekunder", type=float, default=20.0)
    ap.add_argument("--upplosningssekunder", type=float, default=20.0)
    ap.add_argument("--lasvarv-ms", type=float, default=89.0,
                    help="kopplarens varvtid; M-39 matte 89 ms mot OpenPLC")
    ap.add_argument("--json", default=None)
    ap.add_argument("--anda", action="store_true",
                    help="kor aven om VC inte har repots kod (utdatan marks)")
    a = ap.parse_args()

    # STEG 0. Kor VC den kod som ligger i repot? Se installationsgrind.py:
    # en L3-matning mot en gammal installation ger tal for kod som inte
    # langre finns, och ingenting kraschar pa vagen.
    print("STEG 0 - kor VC repots kod?")
    installationen_ok, _rader = installationsgrind.kontrollera(skriv=print)
    if not installationen_ok and not a.anda:
        return 2

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=60.0).anslut()
    objekt = _nagon_komponent(k)
    ut = {"objekt": objekt, "tid": time.strftime("%Y-%m-%d %H:%M:%S"),
          "installationen_ar_repots": installationen_ok}

    karta = Karta()
    print("STEG 1 - de tva klockorna (%.0f s)" % a.klocksekunder)
    ut["klockorna"] = steg1_klockorna(k, a.klocksekunder, karta)
    kl = ut["klockorna"]
    print("  pumpens takt():   median %.4f  p05 %.4f  p95 %.4f  min %.4f  max %.4f"
          % (kl["takt_median"], kl["takt_p05"], kl["takt_p95"],
             kl["takt_min"], kl["takt_max"]))
    print("  lang regression:  %.5f simsekunder per vaggsekund  (%d punkter)"
          % (kl["lang_kvot"], kl["regression"]["n"]))
    if "spridning_median" in kl:
        print("  pumpens takt_spridning: median %.4f  p95 %.4f  max %.4f"
              % (kl["spridning_median"], kl["spridning_p95"], kl["spridning_max"]))
        print("  taktens avstand till den langa kvoten: p95 %.4f  max %.4f"
              % (kl["takt_fel_p95"], kl["takt_fel_max"]))
    if "simsteg" in kl:
        print("  VC:s simuleringssteg: minsta %.4f s, %d distinkta sprang, "
              "de fem minsta %s"
              % (kl["simsteg"]["minsta_s"], kl["simsteg"]["distinkta"],
                 kl["simsteg"]["de_fem_minsta"]))
    print("  regressionens residual: median %.2f  p95 %.2f  max %.2f ms"
          % (kl["regression"]["median_ms"], kl["regression"]["p95_ms"],
             kl["regression"]["max_ms"]))

    # Ogat maste PROVTA for att ett inskott ska fa en stampel: utan
    # provtagare svarar bryggan "ogat provtar inte" och lagrar ingenting. Det
    # ar avsiktligt (ingen falsk framgang), och det galler ocksa matningen.
    k.oga_start(_plan(objekt), simtid=k.simtid())
    print("\nSTEG 2 - tur och retur genom bryggan (%d varv)" % a.varv)
    ut["tur_och_retur"] = steg2_tur_och_retur(k, a.varv)
    for namn, d in sorted(ut["tur_och_retur"].items()):
        print("  %-12s median %.2f  p95 %.2f  max %.2f ms"
              % (namn, d["median"], d["p95"], d["max"]))

    print("\nSTEG 3 - d mot VC:s egen brygga, svept over alderns storlek")
    print("  %-6s %-5s %8s %8s %8s %8s %7s %8s %7s %8s"
          % ("alder", "varv", "d_med", "d_reg", "reg_p05", "reg_p95",
             "klamma", "tak", "over%", "takttrm"))
    ut["d"] = []
    kvot = ut["klockorna"]["lang_kvot"]
    for alder in (0.0, 0.025, 0.050, 0.100, 0.200, 0.400):
        r = steg3_d(k, karta, alder, a.varv, kvot)
        ut["d"].append(r)
        if "fel" in r:
            print("  %-8.0f MISSLYCKADES: %r" % (alder * 1000.0, r["fel"]))
            continue
        print("  %-6.0f %-5d %+8.2f %+8.2f %+8.2f %+8.2f %7.2f %8.2f %6.1f%% %+8.2f"
              % (r["alder_ms"], r["varv"], r["d_median_ms"],
                 r["d_reg_median_ms"], r["d_reg_p05_ms"], r["d_reg_p95_ms"],
                 r["klamma_median_ms"], r["tak_median_ms"],
                 r["reg_over_taket_pct"], r.get("takttermen_p95_ms", 0.0)))

    k.oga_stopp()

    print("\nSTEG 5 - upplosningen ur en riktig korning (%.0f s, kopplarvarv %.0f ms)"
          % (a.upplosningssekunder, a.lasvarv_ms))
    ut["upplosning"] = steg5_upplosning(k, objekt, a.upplosningssekunder,
                                        a.lasvarv_ms / 1000.0)
    r = ut["upplosning"]
    if "fel" in r:
        print("  MISSLYCKADES: %s" % r["fel"])
    else:
        u = r["upplosning"]
        print("  prov %d, inskott %d, rader med plc %d (varav %d gamla, %d med tak)"
              % (r["prov"], r["inskott"], r["rader_med_plc"], r["rader_gamla"],
                 r["rader_med_tak"]))
        print("  alder i serien: median %.1f ms  max %.1f ms"
              % (r["alder_median_ms"], r["alder_max_ms"]))
        print("  prov_s %.1f ms | las_s %s | hopfogning %.2f ms (%s) | fas_s %s"
              % (u["prov_ms"],
                 "okand" if u["las_ms"] is None else "%.1f ms" % u["las_ms"],
                 u["hopfogning_ms"], u["hopfogning_kalla"],
                 "okand" if u["fas_ms"] is None else "%.1f ms" % u["fas_ms"]))

    if a.json:
        with open(a.json, "w") as f:
            json.dump(ut, f, indent=2)
        print("\n  skrev %s" % a.json)
    k.stang()
    return 0


if __name__ == "__main__":
    sys.exit(main())
