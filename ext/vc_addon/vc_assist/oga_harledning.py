# -*- coding: utf-8 -*-
"""Ogats harledningar: mekanismen, skild fran domen.

Har bor rakningarna. I oga_analys.py bor POLICYN - vilket tal som far falla en
korning. Uppdelningen ar avsiktlig och foljer samma skal som uppdelningen
provtagning/analys: en rakning som bara gar att prova genom den dom den ska
mata ar inte provad.

Modulen ror varken VC, natverk eller disk. Den kors av py2.7 inne i VC (den
delade lagringskodningen) och av py3 ute i tjansten (harledningarna), sa den
haller sig till py2-syntax.

SKRIVARE OCH LASARE I SAMMA FIL. Scenens delta-lagring kodas av provtagaren
och avkodas av analysen. Precis som med domskontraktet (41_ogat_kontrakt.md)
ligger de tva halvorna i SAMMA fil, sa de inte kan drifta isar utan att ett
prov ser det.

Kalla: docs/spec/40_ogat.md, 41_ogat_kontrakt.md, 42_ogat_utbyggt.md

TROSKELREGEL (41_ogat_kontrakt.md): varje troskel bar den matning som satte
det. tests/enhet/test_oga_harledning.py kor samma linter over den har filen
som tests/enhet/test_troskelharkomst.py kor over oga_analys.py.
"""
from __future__ import absolute_import, division, print_function

import math

# ---- trosklar ------------------------------------------------------------
#
# Tva sorters harkomst, och de blandas inte ihop:
#
#   PRELIMINAR + M-nn   ett tal som ska MATAS. Numret star i
#                       docs/matningar/RESERVERADE.md tills matningen finns.
#   42_ogat_utbyggt.md  ett tal som ar BESLUTAT, med skalet utskrivet dar.
#                       Ett tak, en kapning och en lagringsupplosning ar val,
#                       inte matningar - men de ska anda peka ut var valet gjordes.
#
# Allt preliminart ar valt sa att det faller at det harda hallet: hellre
# INCONCLUSIVE an ett falskt PASS.

# Scenens lagring. Kvantiseringen ar det enda som skiljer den lagrade serien
# fran den lasta, och den maste ligga LANGT under varje troskel som domer.
SCEN_DECIMALER = 6              # Beslut, motiverat i 42_ogat_utbyggt.md.
SCEN_FULL_VAR_N_RAD = 50        # Beslut, motiverat i 42_ogat_utbyggt.md.

# Rorelse i scenen. Ett objekt som flyttat sig mindre an sa har under HELA
# korningen har inte rort sig; det ar kvantiseringsbrus och numeriskt driv.
STILLA_TOTAL_MM = 1.0           # PRELIMINAR. Satts av matning M-10.
# Rorelse MELLAN tva prov. Under detta star objektet still i det provet.
ROR_SIG_MM = 0.5                # PRELIMINAR. Satts av matning M-10.
# Hur langt tva prov far ligga isar och anda raknas som samtidiga.
SAMTIDIG_FONSTER_S = 0.10       # PRELIMINAR. Satts av matning M-10.
# Hur mycket farten maste andras for att raknas som en fartandring, som andel
# av den storre av de tva farterna. En relativ troskel, for en absolut skulle
# bara en storhet i ett band och en annan i ett annat.
FART_ANDRING_ANDEL = 0.35       # PRELIMINAR. Satts av matning M-10.
# Farten maste dessutom vara over detta i minst en av punkterna, annars ar en
# 35-procentig andring bara brus kring noll.
FART_GOLV_MM_S = 20.0           # PRELIMINAR. Satts av matning M-10.
# Hur mycket hojden maste andras for att raknas som ett nytt hojdlage.
HOJD_ANDRING_MM = 50.0          # PRELIMINAR. Satts av matning M-10.
# Tak pa antalet par i narhetsrakningen. Over det rapporteras kapningen.
NARHET_MAX_PAR = 2000           # Beslut, motiverat i 42_ogat_utbyggt.md.
# Ett objekt som ingen bad om far rora sig sa har mycket utan att fallas.
OOMBEDD_MM = 5.0                # PRELIMINAR. Satts av matning M-10.

# Robotleder. Enheten beror pa ledtypen (grader for vridled, langdenhet for
# skjutled) - darfor tva separata tal och ingen gemensam "ledfart".
LED_STILLA_DEG_S = 0.5          # PRELIMINAR. Satts av matning M-18.
LED_STILLA_MM_S = 0.5           # PRELIMINAR. Satts av matning M-18.
LED_GRANS_MARGINAL_DEG = 0.5    # PRELIMINAR. Satts av matning M-18.
LED_FOLJFEL_DEG = 1.0           # PRELIMINAR. Satts av matning M-18.
# Singularitet mats som kinematisk urartning, inte ur en robotmodell: lederna
# gar fort medan verktyget knappt ror sig i vare sig lage eller vridning.
SING_LEDFART_DEG_S = 20.0       # PRELIMINAR. Satts av matning M-18.
SING_TCP_MM_S = 2.0             # PRELIMINAR. Satts av matning M-18.
SING_TCP_DEG_S = 2.0            # PRELIMINAR. Satts av matning M-18.
SING_MIN_S = 0.15               # PRELIMINAR. Satts av matning M-18.

# Stationer. Hur lange ett tillstand maste hallas for att raknas.
SVALT_MIN_S = 1.0               # PRELIMINAR. Satts av matning M-19.
BLOCKERAD_MIN_S = 1.0           # PRELIMINAR. Satts av matning M-19.
# Andel av korningen ett tillstand maste uppta for att kallas flaskhals.
FLASKHALS_ANDEL = 0.20          # PRELIMINAR. Satts av matning M-19.

# Utslungad detalj: VAGRAT fart over detta OCH en fallkurva som foljer
# tyngdkraften. Vagrat, inte total: en TAPPAD detalj faller ocksa fritt och
# passerar ocksa 3 m/s pa vagen ner. Det som skiljer ett kast fran ett tapp ar
# den vagrata rorelsemangden, ingenting annat - och en grind som mater den
# totala farten domer bada likadant.
UTSLUNGAD_MS = 3.0              # PRELIMINAR. Satts av matning M-10.
# Vagrat fart som fortfarande raknas som flykt, sa flygfonstret inte klipps av
# ett enda langsammare prov mitt i banan.
UTSLUNGAD_FLYG_MS = 1.5         # PRELIMINAR. Satts av matning M-10.
# Hur mycket den mata nedatriktade accelerationen far avvika fran g.
FRITT_FALL_TOL = 0.35           # PRELIMINAR. Satts av matning M-10.
# Tyngdaccelerationen. Ser ut som en naturkonstant men ar det inte i den har
# koden: VC:s scen har en EGEN tyngdacceleration, och den rakar i varldens
# langdenhet - samma omatta enhetsfraga som oga_provtagning.LANGDENHET_TILL_MM.
# Talet nedan ar SI, och det ar ett antagande tills nagon matt det i VC.
G_MS2 = 9.81                    # OMATT ANTAGANDE, se 42_ogat_utbyggt.md.


# ---- vektor- och kvaternionmatematik ------------------------------------
#
# Ligger har och inte i oga_analys.py sa att bada halvorna av ogat rakar med
# SAMMA matematik. oga_analys importerar dem harifran.

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


def diff(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def norm(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def i_verktygsramen(p_del, q_verktyg, p_verktyg):
    """Delens lage uttryckt i verktygets ram."""
    return q_rotera(q_konjugat(q_verktyg), diff(p_del, p_verktyg))


# ---- scenens delta-lagring: kodare OCH avkodare -------------------------

def kvantisera(pose):
    """En pose avrundad till den upplosning serien lagras i.

    Kvantiseringen ar EXPLICIT och matbar: den lasta serien skiljer sig fran
    den provtagna med hogst en halv enhet i sista decimalen, och det talet
    ligger fem tiopotenser under varje troskel som domer. En delta-lagring
    som far ga med "ungefar lika" doljer i stallet rorelse.
    """
    return {"p": [round(float(x), SCEN_DECIMALER) for x in pose["p"]],
            "q": [round(float(x), SCEN_DECIMALER) for x in pose["q"]]}


def _lika(a, b):
    return a["p"] == b["p"] and a["q"] == b["q"]


def koda_scen(poser, forra, tvinga_full):
    """(delta, ny_forra). `forra` ar senast SKRIVNA kvantiserade poser.

    Returnerar bara det som andrats, utom pa fulla rader dar allt skrivs.
    Skalet till fulla rader star i 41_ogat_kontrakt.md: en avbruten fil ska
    anda ga att lasa.
    """
    kvant = {}
    for namn in poser:
        kvant[namn] = kvantisera(poser[namn])
    if tvinga_full:
        return dict(kvant), dict(kvant)
    delta = {}
    for namn in kvant:
        gammal = forra.get(namn)
        if gammal is None or not _lika(gammal, kvant[namn]):
            delta[namn] = kvant[namn]
    ny = dict(forra)
    ny.update(kvant)
    # Ett objekt som forsvunnit ur scenen ska inte baras vidare i evighet.
    for namn in list(ny):
        if namn not in kvant:
            del ny[namn]
    return delta, ny


def expandera(rader):
    """Delta-lagrad serie -> tat serie. Motsatsen till koda_scen().

    Varje rad far en full `scene` med senast kanda pose per objekt, och en
    flagga `scenlast` som sager om scenen VERKLIGEN lastes i det provet.
    Skillnaden ar avgorande: ett objekt som saknas i deltat pa en last rad
    STOD STILL, medan samma objekt pa en oläst rad ar OKANT. Utan den
    skillnaden blir en utglesad provtagning till "allt stod still", vilket ar
    precis den falska framgang ogat finns for att fanga.
    """
    ut = []
    barare = {}
    for rad in rader:
        ny = dict(rad)
        last = bool(rad.get("scenlast"))
        if rad.get("scenfull"):
            barare = dict(rad.get("scene") or {})
        elif last:
            for namn, pose in (rad.get("scene") or {}).items():
                barare[namn] = pose
            for namn in (rad.get("scen_borta") or []):
                if namn in barare:
                    del barare[namn]
        ny["scene"] = dict(barare)
        ny["scenlast"] = last
        ut.append(ny)
    return ut


# ---- serier per objekt ---------------------------------------------------

def objektserier(rader, grupper=("parts", "tools", "scene")):
    """{namn: [(t, p, q, last)]} over alla grupper.

    `last` sager om provet ar en riktig avlasning. For parts och tools ar det
    alltid sant; for scene beror det pa om scenen lastes i just det provet.
    Ett objekt som finns i flera grupper hor till den forsta det namns i, sa
    en roll aldrig dubblerar sin egen serie.
    """
    ut = {}
    sedd_i = {}
    for rad in rader:
        t = float(rad.get("t", 0.0))
        for grupp in grupper:
            d = rad.get(grupp) or {}
            last = True if grupp != "scene" else bool(rad.get("scenlast"))
            for namn in d:
                if sedd_i.setdefault(namn, grupp) != grupp:
                    continue
                pose = d[namn]
                ut.setdefault(namn, []).append(
                    (t, tuple(pose["p"]), tuple(pose["q"]), last))
    return ut


def rorelseprofil(serie):
    """Vad ett objekt gjorde: vaglangd, fart, och NAR det rorde sig.

    Bara prov som verkligen lastes rakas. En lucka i avlasningen ger en lucka
    i profilen, inte en nolla - `oläst_andel` bar den luckan vidare.
    """
    lasta = [(t, p, q) for (t, p, q, last) in serie if last]
    n_olasta = len(serie) - len(lasta)
    profil = {"prov": len(serie), "olasta": n_olasta,
              "olast_andel": (n_olasta / len(serie)) if serie else 1.0,
              "vaglangd_mm": 0.0, "brus_mm": 0.0, "forflyttning_mm": 0.0,
              "maxfart_ms": 0.0, "maxvrid_deg_s": 0.0,
              "intervall": [], "t_forsta": None, "t_sista": None,
              "z_min": None, "z_max": None, "riktningsbyten": 0}
    if not lasta:
        profil["stilla"] = None          # OKANT, inte "stod still"
        return profil
    for _t, p, _q in lasta:
        profil["z_min"] = p[2] if profil["z_min"] is None else min(profil["z_min"], p[2])
        profil["z_max"] = p[2] if profil["z_max"] is None else max(profil["z_max"], p[2])
    # Nettoforflyttningen: forsta till sista laget. Brus integrerar till noll,
    # rorelse gor det inte - det ar det som skiljer en langsam verklig drift
    # (varje steg under golvet, men nettot vaxer) fran numeriskt jitter.
    profil["forflyttning_mm"] = norm(diff(lasta[-1][1], lasta[0][1])) * 1000.0
    start = None
    forra_riktning = None
    for i in range(1, len(lasta)):
        dt = lasta[i][0] - lasta[i - 1][0]
        steg = diff(lasta[i][1], lasta[i - 1][1])
        d_mm = norm(steg) * 1000.0
        if dt > 0:
            profil["maxfart_ms"] = max(profil["maxfart_ms"], d_mm / 1000.0 / dt)
            vrid = q_vinkel_deg(q_mult(q_konjugat(lasta[i - 1][2]), lasta[i][2]))
            profil["maxvrid_deg_s"] = max(profil["maxvrid_deg_s"], vrid / dt)
        if d_mm > ROR_SIG_MM:
            # Bara steg OVER golvet ar vag. Fore M-65 summerades varje steg,
            # och ett objekt som jittrade en halv millimeter fram och
            # tillbaka fick 19,5 mm vag pa 40 prov - alltsa 'rorligt' och
            # 'oombett' - utan att nagonsin ha flyttat sig. Matt i M-65 §2.
            profil["vaglangd_mm"] += d_mm
            if start is None:
                start = lasta[i - 1][0]
            if profil["t_forsta"] is None:
                profil["t_forsta"] = lasta[i - 1][0]
            profil["t_sista"] = lasta[i][0]
            riktning = tuple(1 if x > 0 else (-1 if x < 0 else 0) for x in steg)
            if forra_riktning is not None and riktning != forra_riktning:
                profil["riktningsbyten"] += 1
            forra_riktning = riktning
        else:
            profil["brus_mm"] += d_mm
            if start is not None:
                profil["intervall"].append((start, lasta[i - 1][0]))
                start = None
    if start is not None:
        profil["intervall"].append((start, lasta[-1][0]))
    # Stilla ar BADA: ingen vag over golvet, och inget netto. Ett objekt som
    # kryper 0,1 mm per prov i en riktning har ingen vag over golvet men
    # 20 mm netto pa 200 prov, och det ar en rorelse.
    profil["stilla"] = (profil["vaglangd_mm"] <= STILLA_TOTAL_MM
                        and profil["forflyttning_mm"] <= STILLA_TOTAL_MM)
    if not profil["stilla"] and profil["t_forsta"] is None:
        # Rorelse som bara syns i nettot: hela serien ar dess intervall.
        profil["t_forsta"] = lasta[0][0]
        profil["t_sista"] = lasta[-1][0]
        profil["intervall"].append((lasta[0][0], lasta[-1][0]))
    return profil


def forandringar(serie):
    """NAR ett objekt bytte fart, riktning eller hojd - inte bara ATT det gjorde.

    Tre skilda storheter, tre skilda handelser. En sammanslagen "andring" hade
    varit ett tal som bar tre saker, och da gar det inte att svara pa vilken
    av dem som intraffade.
    """
    lasta = [(t, p) for (t, p, _q, last) in serie if last]
    ut = []
    if len(lasta) < 3:
        return ut
    farter, riktningar = [None], [None]
    for i in range(1, len(lasta)):
        dt = lasta[i][0] - lasta[i - 1][0]
        steg = diff(lasta[i][1], lasta[i - 1][1])
        farter.append((norm(steg) * 1000.0 / dt) if dt > 0 else 0.0)
        riktningar.append(tuple(1 if x > 1e-9 else (-1 if x < -1e-9 else 0)
                                for x in steg) if farter[-1] > FART_GOLV_MM_S
                          else None)
    for i in range(2, len(lasta)):
        storst = max(farter[i], farter[i - 1])
        if (storst > FART_GOLV_MM_S
                and abs(farter[i] - farter[i - 1]) > FART_ANDRING_ANDEL * storst):
            ut.append({"t": lasta[i][0], "vad": "fart",
                       "fran_mm_s": round(farter[i - 1], 2),
                       "till_mm_s": round(farter[i], 2)})
        if (riktningar[i] is not None and riktningar[i - 1] is not None
                and riktningar[i] != riktningar[i - 1]):
            ut.append({"t": lasta[i][0], "vad": "riktning",
                       "fran": list(riktningar[i - 1]), "till": list(riktningar[i])})
    niva = lasta[0][1][2]
    for t, p in lasta[1:]:
        if abs(p[2] - niva) * 1000.0 > HOJD_ANDRING_MM:
            ut.append({"t": t, "vad": "hojd",
                       "fran_m": round(niva, 4), "till_m": round(p[2], 4)})
            niva = p[2]
    ut.sort(key=lambda h: (h["t"], h["vad"]))
    return ut


def rorde_sig_vid(serie):
    """{t: True} for de prov dar objektet rorde sig sedan forra provet."""
    ut = {}
    lasta = [(t, p) for (t, p, _q, last) in serie if last]
    for i in range(1, len(lasta)):
        if norm(diff(lasta[i][1], lasta[i - 1][1])) * 1000.0 > ROR_SIG_MM:
            ut[lasta[i][0]] = True
    return ut


# ---- scenoversikt --------------------------------------------------------

class Scenoversikt(object):
    """Vad hande i scenen som helhet - alla objekt, inte bara rollerna.

    Motivet ar operatorens: ett objekt som ingen tankte pa ska anda finnas i
    serien nar man i efterhand fragar varfor nagot gick fel.
    """

    def __init__(self, rader, roller=None, forvantat_rorliga=None):
        self.rader = rader
        self.roller = list(roller or [])
        self.forvantat = (None if forvantat_rorliga is None
                          else set(forvantat_rorliga) | set(self.roller))
        self.serier = objektserier(rader)
        self.profiler = {}
        for namn in self.serier:
            self.profiler[namn] = rorelseprofil(self.serier[namn])
        self._rorde = {}
        for namn in self.serier:
            self._rorde[namn] = rorde_sig_vid(self.serier[namn])

    # -- vad rorde sig, vad stod still --

    def rorliga(self):
        return sorted(n for n in self.profiler if self.profiler[n]["stilla"] is False)

    def stilla(self):
        return sorted(n for n in self.profiler if self.profiler[n]["stilla"] is True)

    def okanda(self):
        """Objekt vars rorelse INTE gar att uttala sig om: aldrig avlasta."""
        return sorted(n for n in self.profiler if self.profiler[n]["stilla"] is None)

    def forandringar(self):
        """{objekt: [handelse]} - nar varje objekt bytte fart, riktning, hojd."""
        ut = {}
        for namn in self.serier:
            h = forandringar(self.serier[namn])
            if h:
                ut[namn] = h
        return ut

    # -- samtidighet --

    def samtidiga(self):
        """[(a, b, sekunder, prov)] - vilka objekt rorde sig samtidigt.

        Ravaran till kapplopningsanalys: tva ting som ror sig i samma fonster
        ar det som kan kollidera, kapplopa eller stjala samma resurs.
        """
        namn = self.rorliga()
        rutor = {}
        for n in namn:
            for t in self._rorde[n]:
                rutor.setdefault(self._ruta(t), set()).add(n)
        par = {}
        for ruta in rutor:
            lista = sorted(rutor[ruta])
            for i in range(len(lista)):
                for j in range(i + 1, len(lista)):
                    par[(lista[i], lista[j])] = par.get((lista[i], lista[j]), 0) + 1
        ut = [(a, b, round(k * SAMTIDIG_FONSTER_S, 3), k)
              for (a, b), k in par.items()]
        ut.sort(key=lambda x: (-x[3], x[0], x[1]))
        return ut

    @staticmethod
    def _ruta(t):
        return int(math.floor(t / SAMTIDIG_FONSTER_S + 1e-9))

    def sist_i_rorelse_fore(self, t):
        """Vilket objekt rorde sig sist innan t. Svaret pa 'vad gjorde det'."""
        basta = None
        for namn in self._rorde:
            for tid in self._rorde[namn]:
                if tid < t and (basta is None or tid > basta[1]):
                    basta = (namn, tid)
        return basta

    # -- narhet --

    def narhet(self):
        """Minsta CENTRUMAVSTAND per par over tid, och nar.

        OBS: det ar en ANNAN storhet an SAFETY-sektionens MINDIST. MINDIST ar
        ytavstand ur VC:s kollisionsdetektor. Det har ar avstand mellan tva
        objekts origo och sager ingenting om deras form. De far darfor inte
        skrivas pa samma rad, och de bar olika namn har.
        """
        namn = sorted(self.serier)
        par = []
        for i in range(len(namn)):
            for j in range(i + 1, len(namn)):
                if (self.profiler[namn[i]]["stilla"] is True
                        and self.profiler[namn[j]]["stilla"] is True):
                    continue          # tva stillastaende har konstant avstand
                par.append((namn[i], namn[j]))
        kapat = len(par) > NARHET_MAX_PAR
        par = par[:NARHET_MAX_PAR]
        lagen = {}
        for rad in self.rader:
            t = float(rad.get("t", 0.0))
            grupp = {}
            for g in ("parts", "tools", "scene"):
                for n, pose in (rad.get(g) or {}).items():
                    if g == "scene" and not rad.get("scenlast"):
                        continue
                    grupp[n] = pose["p"]
            lagen[t] = grupp
        ut = []
        for a, b in par:
            basta = None
            for t in sorted(lagen):
                if a in lagen[t] and b in lagen[t]:
                    d = norm(diff(lagen[t][a], lagen[t][b])) * 1000.0
                    if basta is None or d < basta[0]:
                        basta = (d, t)
            if basta is not None:
                ut.append({"a": a, "b": b, "min_mm": round(basta[0], 3),
                           "t": basta[1]})
        ut.sort(key=lambda d: d["min_mm"])
        return {"par": ut, "kapat": kapat, "provade_par": len(par)}

    # -- rorelse ingen bad om --

    def oombedd_rorelse(self):
        """Objekt som rorde sig fast planen inte forvantade sig det.

        Returnerar None nar planen INTE sagt vad som far rora sig. Det ar
        skillnaden mellan "inget fel" och "ingen fraga stalld", och de tva far
        aldrig se likadana ut.
        """
        if self.forvantat is None:
            return None
        ut = []
        for namn in self.rorliga():
            if namn in self.forvantat:
                continue
            p = self.profiler[namn]
            # Vagen over golvet ELLER nettot: en langsam drift har ingen vag
            # men ett netto, och den ar lika oombedd.
            storst = max(p["vaglangd_mm"], p["forflyttning_mm"])
            if storst > OOMBEDD_MM:
                ut.append({"objekt": namn, "vaglangd_mm": round(storst, 2),
                           "t": p["t_forsta"]})
        ut.sort(key=lambda d: -d["vaglangd_mm"])
        return ut

    def orort_trots_signal(self, flanker, karta):
        """Objekt som fick en stigande signal men aldrig rorde sig efterat.

        `karta` ar planens {signal: objekt}. Utan den finns ingen koppling
        mellan en signal och ett ting, och da gors ingen bedomning alls.
        """
        ut = []
        for signal in sorted(karta or {}):
            objekt = karta[signal]
            stig = [f["t"] for f in flanker
                    if f["signal"] == signal and f["flank"] == "RISE"]
            if not stig:
                continue
            serie = self.serier.get(objekt)
            if serie is None:
                ut.append({"signal": signal, "objekt": objekt,
                           "t": stig[0], "varfor": "objektet finns inte i serien"})
                continue
            rorde = self._rorde.get(objekt) or {}
            efterat = [t for t in rorde if t >= stig[0]]
            if not efterat:
                ut.append({"signal": signal, "objekt": objekt, "t": stig[0],
                           "varfor": "ingen rorelse efter flanken"})
        return ut

    # -- ledtid per produkt --

    def ledtider(self):
        """Per objekt: fran forsta till sista rorelse. Cykeltid PER PRODUKT.

        Stationens cykeltid (THROUGHPUT) mater stationen. Det har mater
        PRODUKTEN, och de tva ar olika tal aven i en cell som gar perfekt.
        """
        ut = {}
        for namn in self.rorliga():
            p = self.profiler[namn]
            if p["t_forsta"] is None:
                continue
            ut[namn] = {"start_s": p["t_forsta"], "slut_s": p["t_sista"],
                        "ledtid_s": round(p["t_sista"] - p["t_forsta"], 3),
                        "vaglangd_mm": round(p["vaglangd_mm"], 2)}
        return ut


# ---- robotleder ----------------------------------------------------------

def _ledenhet(typ):
    """'deg' for en vridled, 'mm' for en skjutled, None nar typen ar okand.

    En ledfart som inte vet sin enhet ar ett tal som bar tva storheter. Da
    domer vi inte pa den - vi rapporterar den namnlos och sager varfor.
    """
    if typ in ("R", "rot", "rotational", 0):
        return "deg"
    if typ in ("T", "trans", "translational", 1):
        return "mm"
    return None


class Ledanalys(object):
    """vcServoController.Joints over tid, per robot.

    Rader: {"joints": {robot: [varde, ...]}} och valfritt
    {"joints_mal": {robot: [mal, ...]}} for kommenderat mot uppnatt.
    """

    def __init__(self, rader, granser=None, typer=None, tcp=None, serier=None):
        self.rader = rader
        self.granser = granser or {}
        self.typer = typer or {}
        self.tcp = tcp or {}
        self.serier = serier or {}
        self.robotar = sorted(set(
            r for rad in rader for r in (rad.get("joints") or {})))

    def _serie(self, robot, nyckel="joints"):
        ut = []
        for rad in self.rader:
            v = (rad.get(nyckel) or {}).get(robot)
            if v is None:
                continue
            ut.append((float(rad.get("t", 0.0)), [float(x) for x in v]))
        return ut

    def analysera(self):
        ut = {}
        for robot in self.robotar:
            ut[robot] = self._robot(robot)
        return ut

    def _robot(self, robot):
        serie = self._serie(robot)
        n_leder = max(len(v) for _t, v in serie) if serie else 0
        typer = list(self.typer.get(robot) or [])
        granser = list(self.granser.get(robot) or [])
        h = {"prov": len(serie), "leder": n_leder, "led": [],
             "granser_nadda": [], "stopp": [], "singularitet": [],
             "foljfel": [], "enhetslosa_leder": []}
        if len(serie) < 2:
            h["obestambar"] = "for fa ledprov (%d)" % len(serie)
            return h
        farter = []
        for i in range(n_leder):
            typ = typer[i] if i < len(typer) else None
            enhet = _ledenhet(typ)
            if enhet is None:
                h["enhetslosa_leder"].append(i)
            varden = [(t, v[i]) for t, v in serie if i < len(v)]
            fart = []
            for k in range(1, len(varden)):
                dt = varden[k][0] - varden[k - 1][0]
                fart.append((varden[k][0],
                             (varden[k][1] - varden[k - 1][1]) / dt if dt > 0 else 0.0))
            acc = []
            for k in range(1, len(fart)):
                dt = fart[k][0] - fart[k - 1][0]
                acc.append((fart[k][0],
                            (fart[k][1] - fart[k - 1][1]) / dt if dt > 0 else 0.0))
            farter.append(fart)
            post = {"index": i, "enhet": enhet,
                    "min": min(v for _t, v in varden),
                    "max": max(v for _t, v in varden),
                    "rorelse": round(sum(abs(varden[k][1] - varden[k - 1][1])
                                         for k in range(1, len(varden))), 6),
                    "maxfart": round(max([abs(v) for _t, v in fart] or [0.0]), 6),
                    "maxacc": round(max([abs(v) for _t, v in acc] or [0.0]), 6)}
            if i < len(granser) and granser[i] is not None:
                lag, hog = granser[i]
                post["gransvarden"] = [lag, hog]
                for t, v in varden:
                    if v <= lag + LED_GRANS_MARGINAL_DEG or v >= hog - LED_GRANS_MARGINAL_DEG:
                        h["granser_nadda"].append(
                            {"led": i, "t": t, "varde": v, "gransvarden": [lag, hog],
                             "over": v < lag or v > hog})
                        break
            h["led"].append(post)
        h["stopp"] = self._stopp(robot, serie, farter, h)
        h["singularitet"] = self._singularitet(robot, serie, farter)
        h["foljfel"] = self._foljfel(robot)
        return h

    def _stopp(self, _robot, serie, farter, h):
        """Vilken led orsakade ett stopp - den nyttigaste av alla.

        Tva olika orsaker, och de blandas aldrig ihop:
          GRANS        en led sto pa sin grans nar roreisen upphorde
          BEGRANSANDE  ingen led stod pa grans; den led som slutade SIST ar
                       den som bestamde rorelsetiden
        """
        rorlig = []
        for k in range(len(serie) - 1):
            t = serie[k + 1][0]
            rors = False
            for i in range(len(farter)):
                for tid, v in farter[i]:
                    if abs(tid - t) < 1e-9 and abs(v) > self._stillatroskel(h, i):
                        rors = True
                        break
                if rors:
                    break
            rorlig.append((t, rors))
        ut = []
        for k in range(1, len(rorlig)):
            if rorlig[k - 1][1] and not rorlig[k][1]:
                t = rorlig[k][0]
                ut.append(self._stopporsak(t, farter, h))
        return ut

    @staticmethod
    def _stillatroskel(h, i):
        for post in h["led"]:
            if post["index"] == i:
                return LED_STILLA_MM_S if post["enhet"] == "mm" else LED_STILLA_DEG_S
        return LED_STILLA_DEG_S

    def _stopporsak(self, t, farter, h):
        pa_grans = [g for g in h["granser_nadda"] if g["t"] <= t]
        if pa_grans:
            sista = pa_grans[-1]
            return {"t": t, "led": sista["led"], "orsak": "GRANS",
                    "bevis": "led %d stod pa %.3f av [%.3f, %.3f] vid t=%.3f"
                             % (sista["led"], sista["varde"],
                                sista["gransvarden"][0], sista["gransvarden"][1],
                                sista["t"])}
        sist = None
        for i in range(len(farter)):
            troskel = self._stillatroskel(h, i)
            for tid, v in farter[i]:
                if tid < t and abs(v) > troskel:
                    if sist is None or tid > sist[1]:
                        sist = (i, tid, abs(v))
        if sist is None:
            return {"t": t, "led": None, "orsak": "OKAND",
                    "bevis": "ingen led rorde sig fore stoppet"}
        return {"t": t, "led": sist[0], "orsak": "BEGRANSANDE",
                "bevis": "led %d rorde sig sist, %.3f enheter/s vid t=%.3f"
                         % (sist[0], sist[2], sist[1])}

    def _singularitet(self, robot, serie, farter):
        """Kinematisk urartning matt ur DATA, inte ur en antagen robotmodell.

        Villkoret: lederna gar fort medan verktyget knappt ror sig - varken i
        lage eller i vridning. Kravet pa vridningen ar det som skiljer en
        singularitet fran en ren omorientering kring verktygspunkten.

        Utan en utpekad verktygspunkt gors ingen bedomning alls; en
        singularitetsdom utan verktygets rorelse vore en gissning.
        """
        tcp = self.tcp.get(robot)
        serie_tcp = self.serier.get(tcp) if tcp else None
        if not serie_tcp:
            return [{"obestambar": "ingen verktygspunkt utpekad for %s" % robot}]
        tcp_lage = {}
        for t, p, q, last in serie_tcp:
            if last:
                tcp_lage[round(t, 6)] = (p, q)
        tider = sorted(tcp_lage)
        ut = []
        start = None
        forra = None
        for k in range(1, len(tider)):
            t = tider[k]
            dt = t - tider[k - 1]
            if dt <= 0:
                continue
            p0, q0 = tcp_lage[tider[k - 1]]
            p1, q1 = tcp_lage[t]
            tcp_fart = norm(diff(p1, p0)) * 1000.0 / dt
            tcp_vrid = q_vinkel_deg(q_mult(q_konjugat(q0), q1)) / dt
            ledfart = 0.0
            for i in range(len(farter)):
                for tid, v in farter[i]:
                    if abs(tid - t) < 1e-9:
                        ledfart = max(ledfart, abs(v))
            urartad = (ledfart > SING_LEDFART_DEG_S
                       and tcp_fart < SING_TCP_MM_S and tcp_vrid < SING_TCP_DEG_S)
            if urartad and start is None:
                start = (t, ledfart, tcp_fart, tcp_vrid)
            elif not urartad and start is not None:
                if forra is not None and forra - start[0] >= SING_MIN_S:
                    ut.append({"start_s": start[0], "slut_s": forra,
                               "ledfart": round(start[1], 3),
                               "tcp_mm_s": round(start[2], 3),
                               "tcp_deg_s": round(start[3], 3)})
                start = None
            forra = t
        if start is not None and forra is not None and forra - start[0] >= SING_MIN_S:
            ut.append({"start_s": start[0], "slut_s": forra,
                       "ledfart": round(start[1], 3),
                       "tcp_mm_s": round(start[2], 3),
                       "tcp_deg_s": round(start[3], 3)})
        return ut

    def _foljfel(self, robot):
        """Kommenderat mot uppnatt, per led. Kraver joints_mal i serien."""
        varden = dict((t, v) for t, v in self._serie(robot))
        mal = dict((t, v) for t, v in self._serie(robot, "joints_mal"))
        gemensamma = sorted(set(varden) & set(mal))
        if not gemensamma:
            return []
        ut = []
        n = min(min(len(varden[t]) for t in gemensamma),
                min(len(mal[t]) for t in gemensamma))
        for i in range(n):
            varst = 0.0
            varst_t = None
            for t in gemensamma:
                fel = abs(mal[t][i] - varden[t][i])
                if fel > varst:
                    varst, varst_t = fel, t
            sista = gemensamma[-1]
            kvar = abs(mal[sista][i] - varden[sista][i])
            ut.append({"led": i, "max_fel": round(varst, 6), "t": varst_t,
                       "kvarstaende_fel": round(kvar, 6),
                       "nadde_malet": kvar <= LED_FOLJFEL_DEG})
        return ut


# ---- stationer: svalt och blockering ------------------------------------

def stationslage(rader):
    """Per station: svalt- och blockeringsintervall, och flaskhalsen.

    Svalt och blockering ar de tva vanligaste orsakerna till dalig
    genomstromning, och de ser likadana ut i ett medelvarde: stationen
    producerar inte. Skillnaden ar VARFOR, och den ligger i tillstandet.

    En station raknas som svulten nar den ar ledig OCH tom - den vantar pa
    arbete. Blockerad nar den bar nagot den inte far lamna ifran sig.
    """
    stationer = sorted(set(s for r in rader for s in (r.get("stat") or {})))
    ut = {}
    for station in stationer:
        serie = [(float(r.get("t", 0.0)), r["stat"][station])
                 for r in rader if station in (r.get("stat") or {})]
        if len(serie) < 2:
            ut[station] = {"obestambar": "for fa stationsprov (%d)" % len(serie)}
            continue
        span = serie[-1][0] - serie[0][0]
        h = {"svalt": _intervall(serie, _ar_svulten, SVALT_MIN_S),
             "blockerad": _intervall(serie, _ar_blockerad, BLOCKERAD_MIN_S),
             "span_s": round(span, 3)}
        h["svalt_s"] = round(sum(b - a for a, b in h["svalt"]), 3)
        h["blockerad_s"] = round(sum(b - a for a, b in h["blockerad"]), 3)
        h["svalt_andel"] = (h["svalt_s"] / span) if span > 0 else 0.0
        h["blockerad_andel"] = (h["blockerad_s"] / span) if span > 0 else 0.0
        sista = serie[-1][1]
        h["in"] = int(sista.get("in", 0))
        h["out"] = int(sista.get("out", 0))
        h["tillstand"] = sorted(set(str(s.get("state")) for _t, s in serie
                                    if s.get("state") is not None))
        ut[station] = h
    ut["_flaskhals"] = _flaskhals(ut)
    return ut


def _ar_svulten(s):
    """Ledig och tom. Ett tillstandsnamn ur VC vager tyngre an rakningen."""
    tillstand = s.get("state")
    if tillstand is not None:
        return str(tillstand).upper() in ("IDLE", "LEDIG") and _inne(s) <= 0
    if s.get("idle_pct") is not None:
        return float(s["idle_pct"]) > 0 and _inne(s) <= 0
    return _inne(s) <= 0


def _ar_blockerad(s):
    tillstand = s.get("state")
    if tillstand is not None:
        return str(tillstand).upper() in ("BLOCKED", "BLOCKERAD")
    return False


def _inne(s):
    if s.get("cur") is not None:
        return int(s["cur"])
    return int(s.get("in", 0)) - int(s.get("out", 0))


def _intervall(serie, predikat, minsta_s):
    ut = []
    start = None
    for t, s in serie:
        if predikat(s):
            if start is None:
                start = t
        elif start is not None:
            if t - start >= minsta_s:
                ut.append((start, t))
            start = None
    if start is not None and serie[-1][0] - start >= minsta_s:
        ut.append((start, serie[-1][0]))
    return ut


def _flaskhals(stationer):
    """Den station som star mest i vagen, och VILKEN av de tva orsakerna."""
    basta = None
    for station in stationer:
        h = stationer[station]
        if not isinstance(h, dict) or "svalt_andel" not in h:
            continue
        for orsak in ("blockerad", "svalt"):
            andel = h["%s_andel" % orsak]
            if andel >= FLASKHALS_ANDEL and (basta is None or andel > basta["andel"]):
                basta = {"station": station, "orsak": orsak,
                         "andel": round(andel, 4),
                         "sekunder": h["%s_s" % orsak]}
    return basta


# ---- PLC pa samma tidsaxel ----------------------------------------------

PLC_PREFIX = "plc:"


def _lastid(rad):
    """Simuleringstiden da PLC-vardet i raden LASTES: t - plc_alder_s.

    Raden bar vardet vid provets tid t, men vardet ar alder_s gammalt da.
    Flanken hor till lasningen, inte till provet. Fore M-65 lades varje
    PLC-flank pa provets tid, alltsa upp till PLC_FARSK_S (250 ms) for sent,
    och fasen mot en VC-signal lutade systematiskt at ett hall. Matt i
    M-65 §3. Utan alder (None) star provets tid kvar - och raden ar da
    redan markt plc_gammal, sa analysen domer INCONCLUSIVE.
    """
    t = float(rad.get("t", 0.0))
    alder = rad.get("plc_alder_s")
    if alder is None:
        return t, None
    return t - float(alder), float(alder)


def plcflanker(rader):
    """Flanker i PLC-variablerna, i samma form som signalflankerna.

    Namnen bar prefixet plc: sa en PLC-tagg och en VC-signal aldrig kan
    forvaxlas i domstexten. Domskontraktets <signal> ar ett namn utan
    blanksteg, sa prefixet ryms i grammatiken utan att den behover andras.

    Flankens tid ar LASNINGENS tid (se _lastid), och flanken bar ocksa
    provets tid och aldern, sa underlaget visar bada.
    """
    ut = []
    taggar = sorted(set(t for r in rader for t in (r.get("plc") or {})))
    for tagg in taggar:
        forra = None
        for rad in rader:
            v = (rad.get("plc") or {}).get(tagg)
            if v is None:
                continue
            if forra is not None and bool(v) != bool(forra):
                t_las, alder = _lastid(rad)
                ut.append({"signal": PLC_PREFIX + tagg,
                           "flank": "RISE" if v else "FALL",
                           "t": round(t_las, 6),
                           "t_prov": float(rad.get("t", 0.0)),
                           "alder_s": alder})
            forra = v
    ut.sort(key=lambda f: (f["t"], f["signal"]))
    return ut


def plc_lastider(rader):
    """De DISTINKTA tidpunkter PLC-varden lastes vid, ur serien sjalv."""
    tider = set()
    for rad in rader:
        if rad.get("plc") is None or rad.get("plc_alder_s") is None:
            continue
        tider.add(round(_lastid(rad)[0], 4))
    return sorted(tider)


def plc_lasintervall(rader):
    """Medianavstandet mellan tva lasningar, MATT ur serien. None = okant.

    En PLC-flank kan ha intraffat nar som helst mellan tva lasningar. Det
    intervallet ar darfor halva osakerheten i varje PLC-flank, och det antas
    inte: det raknas ur de lastider serien sjalv bar. Ser ogat bara en
    lasning per prov ar intervallet provintervallet - konservativt, for den
    verkliga kopplaren kan ha last oftare an ogat provtog.
    """
    tider = plc_lastider(rader)
    if len(tider) < 2:
        return None
    gap = sorted(tider[i] - tider[i - 1] for i in range(1, len(tider)))
    return gap[len(gap) // 2]


def upplosning(rader, rate_hz, hopfogning_prior_s):
    """Hur fint ogat kan skilja tva tidpunkter at, i sekunder. MATT per serie.

    Tre delar, och de ar tre skilda storheter:
      prov_s        provintervallet: en VC-signals flank ses forst i nasta prov
      las_s         lasintervallet: en PLC-flank kan ligga var som helst
                    mellan tva lasningar (plc_lasintervall)
      hopfogning_s  hopfogningens egen osakerhet: RUN nar serien bar den
                    (plc_hopfogning_s, kopplarens matta tur-och-retur-tak),
                    annars PRIOR ur M-42
    fas_s ar den ovre gransen for felet i en fasskillnad PLC-flank mot
    VC-flank. Felet ar e_prov - e_las + j med e_prov i [0, prov_s),
    e_las i [0, las_s) och j i [0, hopfogning_s], alltsa inom
    (-las_s, prov_s + hopfogning_s), och gransen ar

        fas_s = max(las_s, prov_s + hopfogning_s)

    INTE summan av de tre: summan ar ocksa en grans men en los, och en los
    grans gor varje fasdom mer INCONCLUSIVE an den behover vara. Matt i
    M-65 §3 med Monte Carlo over 20 000 slumpade flanker: felet overskred
    aldrig max(L, S+J) och nadde 95 % av den. Gransen galler ett par
    PLC-tagg mot VC-signal; tva PLC-taggar ur samma lasning skiljer sig
    hogst las_s.
    """
    prov_s = None
    if rate_hz and float(rate_hz) > 0:
        prov_s = 1.0 / float(rate_hz)
    else:
        tider = sorted(set(float(r.get("t", 0.0)) for r in rader))
        if len(tider) >= 2:
            gap = sorted(tider[i] - tider[i - 1] for i in range(1, len(tider)))
            prov_s = gap[len(gap) // 2]
    las_s = plc_lasintervall(rader)
    hop = [float(r["plc_hopfogning_s"]) for r in rader
           if r.get("plc_hopfogning_s") is not None]
    if hop:
        hopfogning_s, kalla = max(hop), "RUN"
    else:
        hopfogning_s, kalla = float(hopfogning_prior_s), "PRIOR"
    fas_s = None
    if prov_s is not None and las_s is not None:
        fas_s = max(las_s, prov_s + hopfogning_s)
    return {"prov_s": prov_s, "las_s": las_s, "hopfogning_s": hopfogning_s,
            "hopfogning_kalla": kalla, "fas_s": fas_s}


def _parpost(post):
    """(tagg, signal, max_ms) ur planens plc_par, i bada formerna."""
    if isinstance(post, dict):
        return post.get("plc"), post.get("signal"), post.get("max_ms")
    return post[0], post[1], None


def fasforhallande(flanker, par, upplosning=None):
    """dt mellan en PLC-tagg och en VC-signal. Ett tidsfel blir lasbart.

    `par` ar [(plc_tagg, vc_signal)] eller [{"plc":..., "signal":...,
    "max_ms":...}]. For varje stigande PLC-flank tas den narmaste stigande
    VC-flanken; tecknet sager vem som kom forst.

    Med `max_ms` DOMS fasen, och da mot upplosningen:
      |dt| <= max                     OK
      max < |dt| <= max + fas_s       INCONCLUSIVE - inom ogats egen osakerhet
      |dt| > max + fas_s              OUT_OF_TOL
      max < fas_s                     INCONCLUSIVE - kravet ar finare an ogat
    En fasdom utan upplosning vore ett tal utan storhet: ett fasfel pa 60 ms
    i en serie som provtar var 50:e ms ar inte ett fel, det ar ett prov.
    """
    ut = []
    fas_s = (upplosning or {}).get("fas_s")
    for post in (par or []):
        tagg, signal, max_ms = _parpost(post)
        a = [f["t"] for f in flanker
             if f["signal"] == PLC_PREFIX + tagg and f["flank"] == "RISE"]
        b = [f["t"] for f in flanker
             if f["signal"] == signal and f["flank"] == "RISE"]
        if not a or not b:
            d = {"plc": tagg, "signal": signal, "obestambar":
                 "saknar stigande flank pa %s"
                 % ("PLC-taggen" if not a else "signalen")}
            if max_ms is not None:
                d["max_ms"] = float(max_ms)
                d["status"] = "INCONCLUSIVE"
            ut.append(d)
            continue
        for t in a:
            narmast = min(b, key=lambda x: abs(x - t))
            d = {"plc": tagg, "signal": signal, "t_plc": t,
                 "t_signal": narmast,
                 "dt_ms": round((narmast - t) * 1000.0, 3),
                 "forst": "plc" if t <= narmast else "signal"}
            if max_ms is not None:
                d["max_ms"] = float(max_ms)
                d["res_ms"] = None if fas_s is None else round(fas_s * 1000.0, 3)
                d["status"], d["skal"] = _fasdom(abs(d["dt_ms"]), float(max_ms),
                                                 d["res_ms"])
            ut.append(d)
    return ut


def _fasdom(dt_ms, max_ms, res_ms):
    if res_ms is None:
        return "INCONCLUSIVE", "upplosningen ar okand: for fa PLC-lasningar"
    if max_ms < res_ms:
        return "INCONCLUSIVE", ("kravet %.0f ms ar finare an ogats upplosning "
                                "%.0f ms i den har takten" % (max_ms, res_ms))
    if dt_ms <= max_ms:
        return "OK", ""
    if dt_ms <= max_ms + res_ms:
        return "INCONCLUSIVE", ("fasen %.0f ms ligger over kravet %.0f ms men "
                                "inom upplosningen %.0f ms" % (dt_ms, max_ms, res_ms))
    return "OUT_OF_TOL", ("fasen %.0f ms overskrider kravet %.0f ms med mer an "
                          "upplosningen %.0f ms" % (dt_ms, max_ms, res_ms))


# ---- stationens sekvens --------------------------------------------------
#
# En station som styrs av structured text gor sitt arbete som en ORDNING av
# flanker i tiden, inte som ett grepp. Rakningarna nedan mater den ordningen;
# policyn - vilket brott som faller en korning - bor i oga_analys.py.
#
# Storheterna ar tva, och de blandas aldrig ihop:
#   sekvensdom()      hande de deklarerade stegen, i ratt ordning, i tid?
#   forreglingsbrott() var tva utgangar hoga SAMTIDIGT?
# En sekvens kan halla medan forreglingen brister, och tvartom.


def _flank_vid(flanker, signal, flank, fran, till):
    """Forsta flanken av ratt sort i [fran, till]. None nar den uteblev."""
    basta = None
    for f in flanker:
        if f["signal"] != signal or f["flank"] != flank:
            continue
        t = float(f["t"])
        if t < fran - 1e-9 or t > till + 1e-9:
            continue
        if basta is None or t < basta:
            basta = t
    return basta


def sekvensdom(flanker, spec, t_slut):
    """Domer en deklarerad stegordning mot de MATTA flankerna.

    `spec` ar planens `sekvens`:

        {"start": {"signal": "plc:givare", "flank": "RISE"},
         "steg": [{"signal": "plc:stopp", "flank": "RISE",
                   "min_s": 0.0, "max_s": 0.5}, ...],
         "min_cykler": 2}

    Varje steg raknas fran CYKELNS start, inte fran foregaende steg. Skalet ar
    att ett fel i ett tidigt steg annars skulle flytta hela facit med sig och
    dolja sig sjalvt: mater man varje steg mot sin foregangare kan en for sen
    stoppflank se ratt ut sa lange slappet ar lika sent.

    En cykel doms bara om HELA dess fonster ryms i serien (`t_slut`). En
    avhuggen sista cykel ar inte ett brott - den ar oprovad, och de tva far
    aldrig se likadana ut.

    Returnerar {"cykler": [...], "domda": n, "brott": [...], "obestambar": ...}
    """
    ut = {"cykler": [], "domda": 0, "brott": [], "obestambar": None,
          "avhuggna": 0}
    if not spec:
        ut["obestambar"] = "ingen sekvens deklarerad"
        return ut
    start = spec.get("start") or {}
    steg = list(spec.get("steg") or [])
    if not start.get("signal") or not steg:
        ut["obestambar"] = "sekvensen saknar start eller steg"
        return ut
    fonster = max(float(s.get("max_s", 0.0)) for s in steg)
    starter = sorted(float(f["t"]) for f in flanker
                     if f["signal"] == start["signal"]
                     and f["flank"] == start.get("flank", "RISE"))
    if not starter:
        ut["obestambar"] = ("ingen %s-flank pa %s: ingen cykel borjade ens"
                            % (start.get("flank", "RISE"), start["signal"]))
        return ut
    for i, t0 in enumerate(starter):
        # Cykeln slutar dar nasta borjar. En flank som hor till nasta produkt
        # far inte laga den har cykelns hal.
        nasta = starter[i + 1] if i + 1 < len(starter) else None
        slut = t0 + fonster if nasta is None else min(t0 + fonster, nasta)
        rad = {"nr": i, "t0": round(t0, 4), "steg": []}
        if t0 + fonster > float(t_slut) + 1e-9:
            rad["avhuggen"] = True
            ut["avhuggna"] += 1
            ut["cykler"].append(rad)
            continue
        golv = t0
        felet = None
        for s in steg:
            fran = max(golv, t0 + float(s.get("min_s", 0.0)))
            till = min(slut, t0 + float(s.get("max_s", 0.0)))
            t = None if till < fran - 1e-9 else _flank_vid(
                flanker, s["signal"], s["flank"], fran, till)
            post = {"signal": s["signal"], "flank": s["flank"],
                    "min_s": float(s.get("min_s", 0.0)),
                    "max_s": float(s.get("max_s", 0.0)),
                    "t": None if t is None else round(t, 4),
                    "dt_s": None if t is None else round(t - t0, 4)}
            rad["steg"].append(post)
            if t is None:
                felet = ("cykel %d: %s %s uteblev i fonstret %.2f-%.2f s efter "
                         "starten" % (i, s["signal"], s["flank"],
                                      float(s.get("min_s", 0.0)),
                                      float(s.get("max_s", 0.0))))
                break
            golv = t
        rad["ok"] = felet is None
        if felet:
            rad["fel"] = felet
            ut["brott"].append(felet)
        ut["domda"] += 1
        ut["cykler"].append(rad)
    krav = int(spec.get("min_cykler", 1))
    if ut["domda"] < krav:
        ut["obestambar"] = ("bara %d hel cykel gick att doma, kravet ar %d"
                            % (ut["domda"], krav))
    return ut


def _varden_over_tid(rader, signal):
    """[(t, bool)] for en signal, ur plc: eller ur sig. Hoppar over hal."""
    ut = []
    for r in rader:
        if signal.startswith(PLC_PREFIX):
            d = r.get("plc") or {}
            nyckel = signal[len(PLC_PREFIX):]
        else:
            d = r.get("sig") or {}
            nyckel = signal
        if nyckel not in d or d[nyckel] is None:
            continue
        ut.append((float(r.get("t", 0.0)), bool(d[nyckel])))
    return ut


def forreglingsbrott(rader, par, tak_s):
    """Hur lange tva signaler var hoga SAMTIDIGT, per deklarerat par.

    `tak_s` ar seriens EGET provintervall och skickas in av anroparen - en
    fast konstant hade beskrivit en annan takt an den som mattes.

    Regeln: ett overlapp raknas som VERKLIGT nar det syns i minst tva prov i
    rad, alltsa nar den matta varaktigheten nar ett helt provintervall. ETT
    prov med bada hoga kan vara tva flanker som foll i samma prov, och det ar
    ett provtagningsutslag, inte ett brott. Tva prov i rad kan det inte vara.

    Overlappet summeras over prov, inte over flanker: en flankbaserad rakning
    hade missat ett overlapp som redan pagick fore forsta provet.
    """
    ut = []
    for a, b in (par or []):
        sa = dict(_varden_over_tid(rader, a))
        sb = dict(_varden_over_tid(rader, b))
        gemensamma = sorted(t for t in sa if t in sb)
        post = {"a": a, "b": b, "overlapp_s": 0.0, "prov": 0, "t_forst": None,
                "tak_s": round(float(tak_s), 4)}
        if not gemensamma:
            post["obestambar"] = "ingen tidpunkt bar bada signalerna"
            ut.append(post)
            continue
        forra = None
        for t in gemensamma:
            bada = sa[t] and sb[t]
            if bada:
                post["prov"] += 1
                if post["t_forst"] is None:
                    post["t_forst"] = round(t, 4)
                # Bara mellanrummet mellan TVA prov som bada bar overlappet
                # rakas. Mellanrummet fore det forsta hor till tiden innan, och
                # att rakna det hade gjort ett enda prov till ett helt
                # provintervall - alltsa till ett brott.
                if forra is not None:
                    post["overlapp_s"] += t - forra
            forra = t if bada else None
        post["overlapp_s"] = round(post["overlapp_s"], 4)
        post["brott"] = post["overlapp_s"] >= float(tak_s) - 1e-9
        ut.append(post)
    return ut


# ---- utslungad detalj ----------------------------------------------------

def utslungad(serie):
    """Fart over trosket OCH en fallkurva som foljer tyngdkraften.

    Skild fran BLOWUP: en numerisk explosion har ingen fysik i sig och ligger
    en tiopotens hogre i fart. En utslungad detalj gar fort OCH faller ratt.
    Bada raknas, sa de aldrig kan doljas av varandra.

    Skild ocksa fran ett TAPP. Ett tapp ar ocksa fritt fall och passerar ocksa
    3 m/s pa vagen ner - matt pa cellen `tappad`, dar en tidigare version av
    den har grinden fallde med orsaken "delen slungades ivag". Det som skiljer
    dem ar den VAGRATA farten, och det ar den som mats.

    Fallkurvan mats over FLYGFONSTRET - fran det prov farten forst overskrider
    trosket till det prov den sjunker under flygfarten. En tidigare version tog
    den globala toppfarten som startpunkt, och eftersom en kastparabel gar
    FORTAST precis innan den tar mark hamnade fonstret efter kastet, dar
    accelerationen ar noll. Den missade varje riktigt kast.
    """
    lasta = [(t, p) for (t, p, _q, last) in serie if last]
    if len(lasta) < 4:
        return None
    farter = [None]
    vagrat = [None]
    for i in range(1, len(lasta)):
        dt = lasta[i][0] - lasta[i - 1][0]
        steg = diff(lasta[i][1], lasta[i - 1][1])
        farter.append(norm(steg) / dt if dt > 0 else 0.0)
        vagrat.append(math.sqrt(steg[0] ** 2 + steg[1] ** 2) / dt if dt > 0 else 0.0)
    start = None
    for i in range(1, len(lasta)):
        if vagrat[i] > UTSLUNGAD_MS:
            start = i
            break
    if start is None:
        return None
    slut = start
    while slut + 1 < len(lasta) and vagrat[slut + 1] > UTSLUNGAD_FLYG_MS:
        slut += 1
    z = [(t, p[2]) for t, p in lasta[start - 1:slut + 1]]
    if len(z) < 3:
        return None
    accar = []
    for i in range(2, len(z)):
        dt1 = z[i - 1][0] - z[i - 2][0]
        dt2 = z[i][0] - z[i - 1][0]
        if dt1 <= 0 or dt2 <= 0:
            continue
        v1 = (z[i - 1][1] - z[i - 2][1]) / dt1
        v2 = (z[i][1] - z[i - 1][1]) / dt2
        accar.append((v2 - v1) / ((dt1 + dt2) / 2.0))
    if not accar:
        return None
    medel = sum(accar) / len(accar)
    if abs(medel + G_MS2) > FRITT_FALL_TOL * G_MS2:
        return None
    return {"t": lasta[start][0], "fart_ms": round(farter[start], 3),
            "vagrat_ms": round(vagrat[start], 3), "z_acc_ms2": round(medel, 3),
            "flygfonster_s": round(lasta[slut][0] - lasta[start][0], 3)}


# ---- handelser och berattelse -------------------------------------------

def handelser(oversikt, extra=None):
    """En tidsordnad lista over vad som hande. Ravaran till berattelsen."""
    ut = []
    for namn in oversikt.rorliga():
        p = oversikt.profiler[namn]
        for a, b in p["intervall"]:
            ut.append({"t": a, "vad": "rorelse_start", "objekt": namn,
                       "text": "%s borjade rora sig" % namn})
            ut.append({"t": b, "vad": "rorelse_slut", "objekt": namn,
                       "text": "%s stannade" % namn})
    for namn, poster in oversikt.forandringar().items():
        for h in poster:
            ut.append({"t": h["t"], "vad": "byte_" + h["vad"], "objekt": namn,
                       "text": "%s bytte %s" % (namn, h["vad"])})
    for post in (extra or []):
        ut.append(post)
    ut.sort(key=lambda h: (h["t"], h.get("vad", ""), h.get("objekt", "")))
    return ut


def _lista(namn, tak=6):
    namn = list(namn)
    if len(namn) <= tak:
        return ", ".join(namn)
    return "%s och %d till" % (", ".join(namn[:tak]), len(namn) - tak)


def berattelse(oversikt, h=None, run=None):
    """Vad pagick i scenen, i ord. ALDRIG en dom - domen ar auktoritativ (I1).

    Den har texten svarar pa operatorens fraga "vad pagar i scenen", och den
    far darfor saga saker domen inte tar stallning till. Den far daremot
    aldrig saga att nagot ar bra eller godkant; det ordet hor domen till.
    """
    h = h or {}
    rader = []
    if run:
        rader.append(
            "Korningen varade %.2f s och gav %d prov i %.1f Hz."
            % (float(run.get("dur_s", 0.0)), int(run.get("samples", 0)),
               float(run.get("rate_hz", 0.0))))
    rorliga = oversikt.rorliga()
    stilla = oversikt.stilla()
    okanda = oversikt.okanda()
    rader.append("Scenen innehaller %d objekt: %d rorde sig, %d stod still."
                 % (len(oversikt.profiler), len(rorliga), len(stilla)))
    if rorliga:
        rader.append("Rorde sig: %s." % _lista(rorliga))
    if stilla:
        rader.append("Stod still hela korningen: %s." % _lista(stilla))
    if okanda:
        rader.append(
            "Gar inte att uttala sig om: %s - de lastes aldrig av."
            % _lista(okanda))
    for namn in rorliga[:5]:
        p = oversikt.profiler[namn]
        rader.append(
            "%s: %.0f mm vag, toppfart %.2f m/s, i rorelse %.2f-%.2f s, "
            "%d riktningsbyten."
            % (namn, p["vaglangd_mm"], p["maxfart_ms"],
               p["t_forsta"] or 0.0, p["t_sista"] or 0.0, p["riktningsbyten"]))
    for namn in rorliga[:5]:
        byten = oversikt.forandringar().get(namn) or []
        if byten:
            rader.append(
                "%s bytte %s."
                % (namn, ", ".join("%s vid %.2f s" % (h["vad"], h["t"])
                                   for h in byten[:4])))
    samtidiga = oversikt.samtidiga()
    if samtidiga:
        a, b, sek, _n = samtidiga[0]
        rader.append("Mest samtidig rorelse: %s och %s, %.2f s tillsammans."
                     % (a, b, sek))
    narhet = h.get("narhet") or {}
    if narhet.get("par"):
        n = narhet["par"][0]
        rader.append("Narmast varandra kom %s och %s: %.1f mm mellan origo "
                     "vid t=%.2f s (centrumavstand, inte ytavstand)."
                     % (n["a"], n["b"], n["min_mm"], n["t"]))
    if narhet.get("kapat"):
        rader.append("Narhetsrakningen kapades vid %d par; fler par fanns."
                     % narhet.get("provade_par", 0))
    grepp = h.get("grepp")
    if grepp:
        rader.append("Greppet bildades vid t=%.2f s pa %.0f mm avstand."
                     % (grepp["t"], grepp["dist_mm"]))
    for post in (h.get("stationer") or {}).items():
        station, d = post
        if station.startswith("_") or not isinstance(d, dict):
            continue
        if "svalt_s" not in d:
            continue
        rader.append("Station %s: %d in, %d ut, svalt %.1f s, blockerad %.1f s."
                     % (station, d["in"], d["out"], d["svalt_s"], d["blockerad_s"]))
    flaskhals = (h.get("stationer") or {}).get("_flaskhals")
    if flaskhals:
        rader.append(
            "Flaskhalsen ar %s: %s %.0f %% av korningen (%.1f s)."
            % (flaskhals["station"],
               "blockerad" if flaskhals["orsak"] == "blockerad" else "svulten",
               flaskhals["andel"] * 100.0, flaskhals["sekunder"]))
    for robot, d in sorted((h.get("robotar") or {}).items()):
        if d.get("obestambar"):
            rader.append("Roboten %s: %s." % (robot, d["obestambar"]))
            continue
        rader.append("Roboten %s: %d leder, %d prov." % (robot, d["leder"], d["prov"]))
        for stopp in d.get("stopp", [])[:3]:
            if stopp["led"] is None:
                continue
            rader.append("  Stoppet vid t=%.2f s orsakades av led %d (%s): %s."
                         % (stopp["t"], stopp["led"], stopp["orsak"].lower(),
                            stopp["bevis"]))
        for g in d.get("granser_nadda", [])[:3]:
            rader.append("  Led %d nadde sin %s vid t=%.2f s (%.2f av [%.2f, %.2f])."
                         % (g["led"], "grans" if not g["over"] else "GRANS OCH GICK FORBI",
                            g["t"], g["varde"], g["gransvarden"][0], g["gransvarden"][1]))
        for s in d.get("singularitet", []):
            if s.get("obestambar"):
                rader.append("  Singularitet gick inte att bedoma: %s." % s["obestambar"])
            else:
                rader.append(
                    "  Kinematisk urartning %.2f-%.2f s: lederna gick %.1f "
                    "enheter/s medan verktyget stod nastan still."
                    % (s["start_s"], s["slut_s"], s["ledfart"]))
    for f in (h.get("fas") or []):
        if f.get("obestambar"):
            rader.append("PLC-taggen %s mot %s: %s."
                         % (f["plc"], f["signal"], f["obestambar"]))
        else:
            rader.append(
                "PLC-taggen %s gick hog %.0f ms %s signalen %s."
                % (f["plc"], abs(f["dt_ms"]),
                   "fore" if f["forst"] == "plc" else "efter", f["signal"]))
    oombedd = h.get("oombedd")
    if oombedd is None:
        rader.append("Planen sager inte vad som far rora sig, sa oombedd "
                     "rorelse bedoms inte.")
    elif oombedd:
        for post in oombedd[:3]:
            rader.append("%s rorde sig %.0f mm fran t=%.2f s utan att nagon "
                         "bad om det." % (post["objekt"], post["vaglangd_mm"],
                                          post["t"] or 0.0))
    for post in (h.get("orort") or []):
        rader.append("%s fick signalen %s vid t=%.2f s men %s."
                     % (post["objekt"], post["signal"], post["t"], post["varfor"]))
    gles = h.get("gles")
    if gles and gles.get("faktor", 1) > 1:
        rader.append(
            "Ogat glesade ut scenprovtagningen till var %d:e prov (rollerna "
            "provtogs i full takt). %d andringar, senast vid t=%.2f s."
            % (gles["faktor"], len(gles.get("handelser") or []),
               (gles.get("handelser") or [{}])[-1].get("t", 0.0)))
    return rader


def vad_pagar(oversikt, t, h=None):
    """Svaret pa 'vad pagar i scenen just nu', for en tidpunkt.

    Det ar den fraga operatoren staller. Den far ett svar i ord - och svaret
    ar inte en dom.
    """
    h = h or {}
    rader = ["Vid t=%.2f s:" % t]
    rors, star = [], []
    for namn in sorted(oversikt.serier):
        rorde = oversikt._rorde.get(namn) or {}
        nara = [tid for tid in rorde if abs(tid - t) <= SAMTIDIG_FONSTER_S]
        (rors if nara else star).append(namn)
    if rors:
        rader.append("  i rorelse: %s" % _lista(rors))
    if star:
        rader.append("  star still: %s" % _lista(star))
    grepp = h.get("grepp")
    if grepp and grepp["t"] <= t:
        rader.append("  greppet har hallit sedan t=%.2f s" % grepp["t"])
    for station, d in sorted((h.get("stationer") or {}).items()):
        if station.startswith("_") or not isinstance(d, dict) or "svalt" not in d:
            continue
        for a, b in d["svalt"]:
            if a <= t <= b:
                rader.append("  %s svalter (sedan t=%.2f s)" % (station, a))
        for a, b in d["blockerad"]:
            if a <= t <= b:
                rader.append("  %s ar blockerad (sedan t=%.2f s)" % (station, a))
    sist = oversikt.sist_i_rorelse_fore(t)
    if sist:
        rader.append("  sist i rorelse fore nu: %s vid t=%.2f s" % (sist[0], sist[1]))
    return rader
