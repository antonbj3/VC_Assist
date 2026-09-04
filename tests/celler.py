# -*- coding: utf-8 -*-
"""Handbyggda celler som tidsserier: en bra och en rad trasiga.

Varje trasig cell isolerar EN felklass, sa en fallning gar att harleda till sin
orsak. Serierna har samma form som eyes.json (41_ogat_kontrakt.md) och kraver
ingen VC - ogat ska ga att prova utan det system det ska doma.

Kalla: docs/spec/83_scenarier.md
"""
from __future__ import annotations

import math

RATE = 20.0
DT = 1.0 / RATE
Q0 = [0.0, 0.0, 0.0, 1.0]


def _q_z(grader):
    a = math.radians(grader) / 2.0
    return [0.0, 0.0, math.sin(a), math.cos(a)]


def _lerp(a, b, u):
    return [a[i] + (b[i] - a[i]) * u for i in range(3)]


class Bygge(object):
    """Bygger en tidsserie steg for steg."""

    def __init__(self, template, floor_z=0.0):
        self.template = template
        self.floor_z = floor_z
        self.rader = []
        self.t = 0.0

    def steg(self, del_p, verktyg_p, del_q=None, verktyg_q=None, sig=None,
             stat=None, mind=None, hit=None, scene=None, joints=None,
             joints_mal=None, plc=None):
        r = {
            "t": round(self.t, 4),
            "parts": {"del": {"p": list(del_p), "q": list(del_q or Q0)}},
            "tools": {"gripper": {"p": list(verktyg_p), "q": list(verktyg_q or Q0)}},
        }
        if sig:
            r["sig"] = dict(sig)
        if stat:
            r["stat"] = dict(stat)
        if mind:
            r["mind"] = dict(mind)
        if hit:
            r["hit"] = list(hit)
        if scene is not None:
            r["scene"] = dict(scene)
            r["scenlast"] = True
        if joints:
            r["joints"] = dict(joints)
        if joints_mal:
            r["joints_mal"] = dict(joints_mal)
        if plc:
            r["plc"] = dict(plc)
        self.rader.append(r)
        self.t += DT
        return self

    def _namn_i(self, grupp):
        ut = set()
        for r in self.rader:
            ut |= set(r.get(grupp) or {})
        return sorted(ut)

    def data(self, signaler=None):
        """Serien i eyes.json:s form.

        `tracked` HARLEDS ur raderna. En handskriven lista skulle hamna efter
        sa fort en cell far en signal till, och en signal som inte star i
        tracked provtas inte av analysen - vilket skulle se ut som att
        grinden var tyst i stallet for blind.
        """
        return {
            "v": 1,
            "template": self.template,
            "run": {"started": "2026-09-04T17:00:00", "dur_s": round(self.t, 3),
                    "samples": len(self.rader), "rate_hz": RATE},
            "tracked": {"parts": ["del"], "tools": ["gripper"],
                        "signals": list(signaler or self._namn_i("sig")
                                        or ["grip_out"]),
                        "pairs": self._namn_i("mind"),
                        "joints": self._namn_i("joints"),
                        "stations": self._namn_i("stat"),
                        "scene": self._namn_i("scene")},
            "rows": self.rader,
        }


def plan(tol_mm=25.0, mal=(1.0, 0.0, 0.75), floor_z=0.0, stationer=None,
         movers=None, forvantat_rorliga=None, ledgranser=None, ledtyper=None,
         robot_tcp=None, genomstromning=None, plc_par=None):
    """Planen ar det ogat blivit OMBETT att doma.

    Allt som inte star har domes inte alls, och det ar avsiktligt: skillnaden
    mellan "ingen fraga stalld" och "fragan stalld och obesvarad" ar hela
    skillnaden mellan tystnad och ett falskt godkannande.
    """
    p = {
        "targets": {"del": {"p": list(mal), "tol_mm": tol_mm}},
        "floor_z": floor_z,
        "movers": dict(movers or {"grip_out": "gripper"}),
        "stations": stationer or {},
    }
    if forvantat_rorliga is not None:
        p["forvantat_rorliga"] = list(forvantat_rorliga)
    if ledgranser:
        p["ledgranser"] = ledgranser
    if ledtyper:
        p["ledtyper"] = ledtyper
    if robot_tcp:
        p["robot_tcp"] = robot_tcp
    if genomstromning:
        p["genomstromning"] = genomstromning
    if plc_par:
        p["plc_par"] = plc_par
    return p


# ---- cellerna -----------------------------------------------------------

def _grundcell(template, glid_deg=0.0, slut=None, teleport_m=0.0,
               bar_z=1.0, tappa=False):
    """Plocka och placera: verktyget gar ner, greppar, bar, slapper.

    Alla trasiga varianter ar samma rorelse med EN sak andrad, sa en skillnad
    i domen gar att harleda till den andringen.
    """
    b = Bygge(template)
    start = [0.0, 0.0, 0.75]
    mal = list(slut or [1.0, 0.0, 0.75])

    # 1. verktyget narmar sig uppifran, delen star still (20 steg = 1,0 s)
    for i in range(20):
        u = i / 19.0
        b.steg(start, _lerp([0.0, 0.0, 1.4], [0.0, 0.0, 0.75 + teleport_m], u),
               sig={"grip_out": False})

    # 2. lyft: delen foljer verktyget (30 steg = 1,5 s)
    for i in range(30):
        u = i / 29.0
        vp = _lerp([0.0, 0.0, 0.75 + teleport_m], [0.0, 0.0, bar_z + teleport_m], u)
        dp = [vp[0], vp[1], vp[2] - teleport_m]
        b.steg(dp, vp, del_q=_q_z(glid_deg * u), sig={"grip_out": True})

    # 3. transport i sidled (40 steg = 2,0 s)
    for i in range(40):
        u = i / 39.0
        vp = _lerp([0.0, 0.0, bar_z + teleport_m], [mal[0], mal[1], bar_z + teleport_m], u)
        dp = [vp[0], vp[1], vp[2] - teleport_m]
        if tappa and u > 0.5:
            # greppet slapper mitt i transporten och delen faller till golvet
            dp = [_lerp([0.0, 0.0, bar_z], [mal[0], mal[1], bar_z], 0.5)[0],
                  0.0, max(0.0, bar_z - 9.81 * ((u - 0.5) * 2.0) ** 2 / 2.0)]
        b.steg(dp, vp, del_q=_q_z(glid_deg), sig={"grip_out": True})

    # 4. satt ned och slapp (20 steg = 1,0 s)
    for i in range(20):
        u = i / 19.0
        vp = _lerp([mal[0], mal[1], bar_z + teleport_m], [mal[0], mal[1], mal[2] + teleport_m], u)
        dp = [vp[0], vp[1], vp[2] - teleport_m]
        if tappa:
            dp = [_lerp([0.0, 0.0, bar_z], [mal[0], mal[1], bar_z], 0.5)[0], 0.0, 0.0]
        b.steg(dp, vp, del_q=_q_z(glid_deg), sig={"grip_out": u < 0.5})

    # 5. verktyget lamnar, delen ligger kvar (20 steg = 1,0 s)
    slutlage = b.rader[-1]["parts"]["del"]["p"]
    for i in range(20):
        u = i / 19.0
        b.steg(slutlage, _lerp([mal[0], mal[1], mal[2] + teleport_m],
                               [mal[0], mal[1], 1.4], u),
               del_q=_q_z(glid_deg), sig={"grip_out": False})
    return b


def bra():
    return _grundcell("plocka_och_placera"), plan()


def teleport():
    """Greppet bildas medan verktyget ar 800 mm bort. VC:s standardgrepp ar
    icke-fysiskt, sa en MISS ser ut som en lyckad plockning utan den har grinden."""
    return _grundcell("teleport", teleport_m=0.8), plan()


def glider():
    """Delen vrider sig 15 grader i verktygets ram under barandet."""
    return _grundcell("glider", glid_deg=15.0), plan()


def tappad():
    return _grundcell("tappad", tappa=True), plan()


def fel_placerad():
    """Slutar 80 mm fran malet - inom synhall, utanfor toleransen."""
    return _grundcell("fel_placerad", slut=[1.08, 0.0, 0.75]), plan()


def aldrig_gripen():
    """Verktyget gor hela rorelsen, delen star still hela tiden."""
    b = Bygge("aldrig_gripen")
    still = [0.0, 0.0, 0.75]
    banor = [([0.0, 0.0, 1.4], [0.0, 0.0, 0.75], 20),
             ([0.0, 0.0, 0.75], [0.0, 0.0, 1.0], 30),
             ([0.0, 0.0, 1.0], [1.0, 0.0, 1.0], 40),
             ([1.0, 0.0, 1.0], [1.0, 0.0, 1.4], 20)]
    for a, c, n in banor:
        for i in range(n):
            b.steg(still, _lerp(a, c, i / float(n - 1)), sig={"grip_out": True})
    return b, plan()


def explosion():
    """Numerisk explosion: verktyg och del far orimlig fart.

    Malet ligger DAR delen hamnar. Utan det bryter cellen ocksa mot
    OFF_TARGET, och da kan BLOWUP-grinden stangas av utan att ett enda prov
    marker det - matt med mutation i tests/motbevis/test_ogat_honesty_motbevis.py.
    """
    b = Bygge("explosion")
    for i in range(40):
        x = 0.0 if i < 20 else (i - 20) * 5.0     # 5 m per 0,05 s = 100 m/s
        b.steg([x, 0.0, 0.75], [x, 0.0, 0.75], sig={"grip_out": True})
    slut = b.rader[-1]["parts"]["del"]["p"]
    return b, plan(mal=tuple(slut))


def under_golvet():
    b = _grundcell("under_golvet")
    for r in b.rader[60:80]:
        r["parts"]["del"]["p"][2] = -0.22
    return b, plan()


def kollision():
    b = _grundcell("kollision")
    b.rader[45]["hit"] = ["gripper_finger", "fixtur_vagg"]
    for i, r in enumerate(b.rader):
        d = 200.0 if i < 40 else (2.0 if i == 45 else 50.0)
        r["mind"] = {"gripper+fixtur": {"d_mm": d, "p1": [0, 0, 0], "p2": [0, 0, 0]}}
    return b, plan()


def kort_uppehall():
    """Stationen slapper ut delen fore transportorens eftersläpning gatt ut."""
    b = _grundcell("kort_uppehall")
    for i, r in enumerate(b.rader):
        inne = 1 if 40 <= i < 48 else 0        # 8 prov = 0,4 s
        r["stat"] = {"station1": {"in": 1 if i >= 40 else 0, "out": 1 if i >= 48 else 0}}
        r["stat"]["station1"]["in"] = 1 if i >= 40 else 0
    return b, plan(stationer={"station1": {"dwell_req_s": 2.0}})


def for_fa_prov():
    b = Bygge("for_fa_prov")
    for i in range(4):
        b.steg([0.0, 0.0, 0.75], [0.0, 0.0, 1.0], sig={"grip_out": False})
    return b, plan()


# ---- scenen som helhet --------------------------------------------------
#
# Fran och med har provtas HELA scenen, inte bara rollerna. Cellerna nedan ar
# grundcellen med EN sak andrad i scenen omkring den, sa en skillnad i domen
# gar att harleda till just den andringen.

BAKGRUND = {
    "stallage": [3.0, 1.0, 0.0],
    "skyddsstaket": [-2.0, 0.0, 0.0],
    "styrskap": [0.0, 3.0, 0.0],
    "band_in": [-1.5, 0.5, 0.5],
}


def _pose(p, q=None):
    return {"p": list(p), "q": list(q or Q0)}


def _lagg_scen(b, per_rad):
    """per_rad(i) -> {namn: pose}. Raden markeras som verkligen avlast."""
    for i, r in enumerate(b.rader):
        poser = per_rad(i)
        if poser is None:
            continue
        r["scene"] = dict(poser)
        r["scenlast"] = True
        if i == 0:
            r["scenfull"] = True
    return b


def _stilla_bakgrund(_i):
    return dict((namn, _pose(p)) for namn, p in BAKGRUND.items())


def bakgrund_stilla():
    """Fyra objekt som ingen bad om nagot av, och som star still.

    Den GRONA riktningen for hela scengrinden: en scen full av oinblandade
    ting far inte gora en korning rod.
    """
    b = _lagg_scen(_grundcell("bakgrund_stilla"), _stilla_bakgrund)
    return b, plan(forvantat_rorliga=["del", "gripper"])


def scen_deltalagrad():
    """Samma scen, lagrad som delta i stallet for full varje rad.

    Kodningen ar handskriven har och inte hamtad ur ogats egen kodare: en
    fixtur som anvander koden den provar bevisar bara att koden ar sig sjalv
    lik. Domen ska bli densamma som i bakgrund_stilla.
    """
    b = _grundcell("scen_deltalagrad")
    for i, r in enumerate(b.rader):
        r["scenlast"] = True
        if i == 0:
            r["scene"] = dict((namn, _pose(p)) for namn, p in BAKGRUND.items())
            r["scenfull"] = True
        else:
            r["scene"] = {}          # ingenting andrades sedan forra raden
    return b, plan(forvantat_rorliga=["del", "gripper"])


def oombedd_rorelse():
    """Ett bakgrundsobjekt ror sig fast ingen bad om det.

    Egen felklass: nagot i scenen rorde sig som ingen bett om. Utan
    fullscenprovtagning finns den inte att se alls.
    """
    def per_rad(i):
        poser = _stilla_bakgrund(i)
        if i >= 40:
            poser["stallage"] = _pose([3.0 + (i - 40) * 0.01, 1.0, 0.0])
        return poser
    b = _lagg_scen(_grundcell("oombedd_rorelse"), per_rad)
    return b, plan(forvantat_rorliga=["del", "gripper"])


def oombedd_men_deklarerad():
    """Exakt samma rorelse, men planen sager att stallaget FAR rora sig.

    Den andra riktningen: grinden ska tiga nar rorelsen ar bestalld.
    """
    b, _p = oombedd_rorelse()
    b.template = "oombedd_men_deklarerad"
    return b, plan(forvantat_rorliga=["del", "gripper", "stallage"])


def utglesad_scen():
    """Scenen lastes bara var tionde prov. Da GAR den inte att doma.

    Fail-closed: en utglesad serie far aldrig lasas som "allt stod still".
    """
    def per_rad(i):
        return _stilla_bakgrund(i) if i % 10 == 0 else None
    b = _lagg_scen(_grundcell("utglesad_scen"), per_rad)
    return b, plan(forvantat_rorliga=["del", "gripper"])


def tva_produkter():
    """Tva detaljer med olika ledtid genom cellen. Cykeltid PER PRODUKT."""
    def per_rad(i):
        poser = _stilla_bakgrund(i)
        u = min(1.0, max(0.0, (i - 20) / 40.0))
        poser["produkt_b"] = _pose([-1.5 + u * 2.0, 0.5, 0.5])
        return poser
    b = _lagg_scen(_grundcell("tva_produkter"), per_rad)
    return b, plan(forvantat_rorliga=["del", "gripper", "produkt_b"])


# ---- signal utan verkan --------------------------------------------------

def _band(rors, template):
    """Grundcellen plus ett transportband som styrs av signalen band_ut."""
    def per_rad(i):
        poser = _stilla_bakgrund(i)
        if rors and i >= 45:
            poser["band_in"] = _pose([-1.5 + (i - 45) * 0.02, 0.5, 0.5])
        return poser
    b = _lagg_scen(_grundcell(template), per_rad)
    for i, r in enumerate(b.rader):
        r["sig"]["band_ut"] = i >= 40
    return b


def orort_trots_signal():
    """band_ut gar hog och bandet star kvar. Ett don som inte lyder."""
    b = _band(False, "orort_trots_signal")
    return b, plan(movers={"grip_out": "gripper", "band_ut": "band_in"})


def band_ror_sig():
    """Samma signal, och bandet ror sig. Den gronna riktningen."""
    b = _band(True, "band_ror_sig")
    return b, plan(movers={"grip_out": "gripper", "band_ut": "band_in"})


# ---- robotleder ----------------------------------------------------------

ROBOT = "robot1"
LEDGRANSER = {ROBOT: [[-170.0, 170.0], [-90.0, 90.0], [-150.0, 150.0]]}
LEDTYPER = {ROBOT: ["deg", "deg", "deg"]}


def _robotcell(template, leder_vid, mal_vid=None, svans=0, svans_leder=None,
               svans_tcp=None):
    """Grundcellen med ledvarden pahangda, och en valfri svans efterat.

    Svansen ligger EFTER att detaljen ar placerad, sa den inte kan andra
    grundcellens egen dom. Skillnaden mellan tva robotceller ar da lederna.
    """
    b = _grundcell(template)
    for i, r in enumerate(b.rader):
        r["joints"] = {ROBOT: list(leder_vid(i))}
        if mal_vid is not None:
            r["joints_mal"] = {ROBOT: list(mal_vid(i))}
    if svans:
        sista = b.rader[-1]
        dp = list(sista["parts"]["del"]["p"])
        vp = list(sista["tools"]["gripper"]["p"])
        for k in range(svans):
            vq = svans_tcp(k) if svans_tcp else None
            b.steg(dp, vp, verktyg_q=vq, sig={"grip_out": False},
                   joints={ROBOT: list(svans_leder(k))})
    return b


def _robotplan(**extra):
    return plan(ledgranser=LEDGRANSER, ledtyper=LEDTYPER,
                robot_tcp={ROBOT: "gripper"}, **extra)


def robot_ren():
    """Lederna gar och stannar, langt fran sina granser. GRON riktning."""
    def leder(i):
        u = min(1.0, i / 80.0)
        return [60.0 * u, 30.0 * u, -20.0 * u]
    return _robotcell("robot_ren", leder), _robotplan()


def robot_gransnara():
    """En led gar anda fram till sin grans utan att passera den.

    GRON: att na en grans ar inte ett fel. Att ga forbi ar det.
    """
    def leder(i):
        u = min(1.0, i / 80.0)
        return [169.6 * u, 30.0 * u, -20.0 * u]
    return _robotcell("robot_gransnara", leder), _robotplan()


def robot_ledgrans():
    """Led 0 gar forbi sin ovre grans pa 170 grader."""
    def leder(i):
        u = min(1.0, i / 80.0)
        return [185.0 * u, 30.0 * u, -20.0 * u]
    return _robotcell("robot_ledgrans", leder), _robotplan()


def robot_singularitet():
    """Lederna gar fort medan verktyget star still i bade lage och vridning."""
    def leder(i):
        u = min(1.0, i / 80.0)
        return [60.0 * u, 30.0 * u, -20.0 * u]

    def svans_leder(k):
        return [60.0 + 5.0 * k, 30.0 - 5.0 * k, -20.0]
    return (_robotcell("robot_singularitet", leder, svans=12,
                       svans_leder=svans_leder),
            _robotplan())


def robot_omorientering():
    """Samma snabba leder, men verktyget VRIDER sig. Da ar det ingen urartning.

    Kravet pa verktygets vridning ar det enda som skiljer en singularitet fran
    en ren omorientering kring verktygspunkten. Utan den cellen vore
    singularitetsgrinden bara en fartgrind med ett finare namn.
    """
    def leder(i):
        u = min(1.0, i / 80.0)
        return [60.0 * u, 30.0 * u, -20.0 * u]

    def svans_leder(k):
        return [60.0 + 5.0 * k, 30.0 - 5.0 * k, -20.0]
    return (_robotcell("robot_omorientering", leder, svans=12,
                       svans_leder=svans_leder,
                       svans_tcp=lambda k: _q_z(6.0 * k)),
            _robotplan())


def robot_foljer():
    """Kommenderat och uppnatt sammanfaller. GRON riktning."""
    def leder(i):
        u = min(1.0, i / 80.0)
        return [60.0 * u, 30.0 * u, -20.0 * u]
    return (_robotcell("robot_foljer", leder, mal_vid=leder), _robotplan())


def robot_foljfel():
    """Led 1 nar aldrig sitt kommenderade varde - 12 grader kvar vid slutet."""
    def leder(i):
        u = min(1.0, i / 80.0)
        return [60.0 * u, 18.0 * u, -20.0 * u]

    def mal(i):
        u = min(1.0, i / 80.0)
        return [60.0 * u, 30.0 * u, -20.0 * u]
    return (_robotcell("robot_foljfel", leder, mal_vid=mal), _robotplan())


def robot_stopp_begransande():
    """Lederna stannar en efter en; den som stannar SIST bestamde tiden.

    Domen ar PASS - ett stopp ar ingen defekt. Det harledningen ska svara pa
    ar VILKEN led som orsakade det.
    """
    def leder(i):
        a = min(1.0, i / 20.0)
        b_ = min(1.0, i / 40.0)
        c = min(1.0, i / 60.0)
        return [60.0 * a, 30.0 * b_, -20.0 * c]
    return _robotcell("robot_stopp_begransande", leder), _robotplan()


# ---- kollision och minsta avstand ---------------------------------------

def mindist_nara():
    """Detektorn ser 12 mm men ingen traff. GRON: nara ar inte samma sak som i."""
    b = _grundcell("mindist_nara")
    for i, r in enumerate(b.rader):
        d = 200.0 if i < 40 else (12.0 if i == 60 else 60.0)
        r["mind"] = {"gripper+fixtur": {"d_mm": d, "p1": [0, 0, 0],
                                        "p2": [0, 0, 0], "inom_tolerans": d < 100.0}}
    return b, plan()


def kollision_med_feature():
    """Traffen bar ocksa VILKEN yta som traffade vilken (getHitFeatureA/B)."""
    b = _grundcell("kollision_med_feature")
    b.rader[45]["hit"] = ["gripper_finger", "fixtur_vagg", "Face_12", "Face_3"]
    return b, plan()


# ---- stationer: svalt och blockering ------------------------------------

def _stationscell(template, tillstand, cur=0):
    b = _grundcell(template)
    for r in b.rader:
        r["stat"] = {"station1": {"in": 1, "out": 1, "cur": cur,
                                  "state": tillstand}}
    return b


def station_svalt():
    """Stationen ar ledig och tom hela korningen, och kravet sager 1,0 s."""
    return (_stationscell("station_svalt", "IDLE"),
            plan(genomstromning={"max_svalt_s": 1.0}))


def station_svalt_utan_krav():
    """Samma serie utan deklarerat krav. Da finns inget facit att fella mot.

    Den andra riktningen, och en viktig: ett matt utan krav ar ett matt, inte
    en dom.
    """
    b = _stationscell("station_svalt_utan_krav", "IDLE")
    return b, plan()


def station_blockerad():
    """Stationen bar nagot den inte far lamna ifran sig."""
    return (_stationscell("station_blockerad", "BLOCKED", cur=1),
            plan(genomstromning={"max_blockerad_s": 1.0}))


def station_upptagen():
    """Stationen arbetar hela tiden. Varken svulten eller blockerad. GRON."""
    return (_stationscell("station_upptagen", "BUSY", cur=1),
            plan(genomstromning={"max_svalt_s": 1.0, "max_blockerad_s": 1.0}))


# ---- PLC pa samma tidsaxel ----------------------------------------------

def _plccell(template, plc_vid, gammal=False):
    b = _grundcell(template)
    for i, r in enumerate(b.rader):
        r["plc"] = {"Start": plc_vid(i)}
        r["plc_alder_s"] = 0.6 if gammal else 0.01
        if gammal:
            r["plc_gammal"] = True
    return b


def plc_i_fas():
    """PLC-taggen gar hog 100 ms fore utsignalen. Ett lasbart fasforhallande."""
    b = _plccell("plc_i_fas", lambda i: i >= 18)
    return b, plan(plc_par=[("Start", "grip_out")])


def plc_ur_fas():
    """Taggen gar hog 1,5 s FORE signalen. Domen ar anda PASS.

    Inget krav pa fasen ar deklarerat, sa ogat MATER den och domer den inte.
    Ett tal utan krav ar ett tal.
    """
    b = _plccell("plc_ur_fas", lambda i: i >= 10)
    return b, plan(plc_par=[("Start", "grip_out")])


def plc_gammal():
    """PLC-vardena ar aldre an sina egna prov. Da ar de inte samtidiga."""
    b = _plccell("plc_gammal", lambda i: i >= 18, gammal=True)
    return b, plan(plc_par=[("Start", "grip_out")])


# ---- timing: fasen DOMS mot ett krav, och mot ogats egen upplosning -------
#
# Fyra celler, samma serie som plc_i_fas/plc_ur_fas, med EN rad i planen
# andrad: max_ms. Upplosningen i de har serierna ar max(L, S+J) =
# max(50, 50 + 13,45) = 63,45 ms - provintervallet 50 ms, lasintervallet 50 ms
# (en lasning per prov) och priorn for hopfogningen. Talen ar cellernas facit.

def fas_utanfor_tolerans():
    """Taggen gar hog 510 ms fore signalen, kravet ar 100 ms. Domaren
    'timing' faller: 510 > 100 + 63. TRASIG CELL for timing-domen."""
    b = _plccell("fas_utanfor_tolerans", lambda i: i >= 10)
    return b, plan(plc_par=[{"plc": "Start", "signal": "grip_out", "max_ms": 100.0}])


def fas_inom_tolerans():
    """110 ms fas, kravet 300 ms. GRON."""
    b = _plccell("fas_inom_tolerans", lambda i: i >= 18)
    return b, plan(plc_par=[{"plc": "Start", "signal": "grip_out", "max_ms": 300.0}])


def fas_inom_upplosningen():
    """110 ms fas, kravet 100 ms: over kravet men inom ogats upplosning
    (63 ms). Da vet ogat inte - INCONCLUSIVE, aldrig PASS, aldrig FAIL."""
    b = _plccell("fas_inom_upplosningen", lambda i: i >= 18)
    return b, plan(plc_par=[{"plc": "Start", "signal": "grip_out", "max_ms": 100.0}])


def fas_finare_an_upplosningen():
    """Kravet ar 20 ms i en serie som bara kan skilja 63 ms. Fasen ar 0 - och
    anda INCONCLUSIVE: ogat kan inte se ett 20 ms-fel i den har takten, och
    ett PASS hade varit ett pastaende om nagot ogat inte kan se."""
    b = _plccell("fas_finare_an_upplosningen", lambda i: i >= 20)
    return b, plan(plc_par=[{"plc": "Start", "signal": "grip_out", "max_ms": 20.0}])


# ---- utslungad och aldrig tagen -----------------------------------------

def utslungad():
    """Detaljen slungas ivag i drygt 5 m/s och foljer sedan tyngdkraften.

    Skild fran explosionscellen: den har farten ar fysiskt mojlig och kurvan
    ar en riktig kastparabel. En grind som bara mater fart kan inte skilja
    dem at, och da faller bada eller ingen.
    """
    b = Bygge("utslungad")
    start = [0.0, 0.0, 0.75]
    for i in range(20):
        u = i / 19.0
        b.steg(start, _lerp([0.0, 0.0, 1.4], [0.0, 0.0, 0.75], u),
               sig={"grip_out": False})
    for i in range(30):
        u = i / 29.0
        vp = _lerp([0.0, 0.0, 0.75], [0.0, 0.0, 1.0], u)
        b.steg(vp, vp, sig={"grip_out": True})
    # kastet: 5 m/s i x, 2 m/s uppat, sedan bara tyngdkraft
    z0, vx, vz = 1.0, 5.0, 2.0
    sista = None
    for k in range(1, 11):
        tk = k * DT
        sista = [vx * tk, 0.0, z0 + vz * tk - 0.5 * 9.81 * tk * tk]
        b.steg(sista, [0.0, 0.0, 1.0], sig={"grip_out": False})
    for _ in range(20):
        b.steg(sista, [0.0, 0.0, 1.4], sig={"grip_out": False})
    return b, plan(mal=tuple(sista))


def rord_men_aldrig_gripen():
    """Detaljen ror sig - men aldrig i verktygets ram. Den greps aldrig.

    Skiljer NEVER_GRIPPED fran "aldrig tagen": har finns rorelse, sa det gar
    inte att skylla pa en stillastaende detalj. Utan den har cellen kan de tva
    grindarna tacka for varandra, och en av dem kan vara dod utan att nagot
    marker det.
    """
    b = Bygge("rord_men_aldrig_gripen")
    for i in range(110):
        dp = [-1.0 + i * 0.02, 0.0, 0.75]         # detaljen glider pa ett band
        vp = [2.0, 0.0, 1.0 + 0.2 * math.sin(i / 8.0)]   # verktyget arbetar bredvid
        b.steg(dp, vp, sig={"grip_out": i >= 40})
    return b, plan(mal=(1.18, 0.0, 0.75))


# ---- celler som ligger PA en troskels grans -----------------------------
#
# En troskel vars grans ingen cell ror ar obestamd: `>` och `>=` ger samma dom
# i hela banken, och da har gransen inget facit. Matt med mutation i
# tests/motbevis/test_ogat_honesty_motbevis.py.

def pa_placeringsgransen():
    """Slutlaget ligger EXAKT pa toleransen.

    Toleransen raknas ur seriens eget slutlage med samma rakning som analysen
    anvander, sa likheten ar exakt och inte "nastan". En grans som provas med
    ett avrundat tal provar inte gransen.
    """
    mal = (1.0, 0.0, 0.75)
    b = _grundcell("pa_placeringsgransen", slut=[1.025, 0.0, 0.75])
    slut = b.rader[-1]["parts"]["del"]["p"]
    fel_mm = math.sqrt(sum((slut[i] - mal[i]) ** 2 for i in range(3))) * 1000.0
    return b, plan(mal=mal, tol_mm=fel_mm)


def pa_barstrackans_grans():
    """Barstrackan ar exakt CARRY_MIN_SPAN_S lang: greppet vid t=0, slappet
    vid t=0,50. Bada tiderna ar exakta i flyttal, sa skillnaden ar det ocksa."""
    b = Bygge("pa_barstrackans_grans")
    mal = [1.0, 0.0, 0.75]
    for i in range(11):                       # t = 0,00 ... 0,50
        u = i / 10.0
        p = _lerp([0.0, 0.0, 0.75], mal, u)
        b.steg(p, p, sig={"grip_out": True})
    for i in range(20):                       # verktyget lamnar OMEDELBART
        # u borjar pa forsta steget, inte pa noll: ett forsta varv dar
        # verktyget star kvar skjuter slappet ett prov framat och gor
        # barstrackan 0,55 s i stallet for de 0,50 gransen ligger pa.
        u = (i + 1) / 20.0
        b.steg(mal, _lerp(mal, [mal[0], 0.0, 1.4], u), sig={"grip_out": False})
    return b, plan(mal=tuple(mal))


def utan_placeringstolerans():
    """Malet saknar tol_mm, sa PLACE_TOL_MM anvands.

    Utan den har cellen skickar varje plan med sin egen tolerans och
    PLACE_TOL_MM kan sattas till 2,5 meter utan att en enda dom rors - talet
    vore da ett pastaende, inte en troskel.
    """
    b = _grundcell("utan_placeringstolerans", slut=[1.08, 0.0, 0.75])
    p = plan(mal=(1.0, 0.0, 0.75))
    del p["targets"]["del"]["tol_mm"]
    return b, p


# ---- stationen: en sekvens i tiden, inget grepp --------------------------
#
# En station som styrs av structured text har varken en DEL eller ett VERKTYG.
# Dess arbete ar en ORDNING av flanker. Cellerna nedan provar den grinden, och
# varje trasig cell bryter EN sak - annars gar en fallning inte att harleda.

STATION_TEMPLATE = "station_sekvens"
# Facit for cellerna: givaren stiger, stoppet gar hogt inom ett halvsekund,
# slapper efter processtiden, och slappsignalen kommer efter stoppet.
STATIONSSEKVENS = {
    "start": {"signal": "plc:givare", "flank": "RISE"},
    "steg": [{"signal": "plc:stopp", "flank": "RISE", "min_s": 0.0, "max_s": 0.5},
             {"signal": "plc:stopp", "flank": "FALL", "min_s": 1.5, "max_s": 2.5},
             {"signal": "plc:slapp", "flank": "RISE", "min_s": 1.5, "max_s": 2.8},
             {"signal": "plc:slapp", "flank": "FALL", "min_s": 2.0, "max_s": 3.3}],
    "min_cykler": 2,
}


def stationsplan(sekvens=True, forregling=True):
    """Planen for en station: ingen del, inget verktyg, en deklarerad sekvens."""
    p = {"floor_z": 0.0, "movers": {}, "stations": {}}
    if sekvens:
        p["sekvens"] = dict(STATIONSSEKVENS)
    if forregling:
        p["forregling"] = [["plc:stopp", "plc:slapp"]]
    return p


class Stationsbygge(object):
    """En serie UTAN roller: bara scenen och PLC-varden pa samma tidsaxel.

    Skild fran `Bygge`, som alltid lagger en del och ett verktyg i varje rad.
    Att lana den och nolla rollerna hade gett en cell som pastar sig gripa och
    inte gor det - alltsa en annan felklass an den som ska provas har.
    """

    def __init__(self, template=STATION_TEMPLATE):
        self.template = template
        self.rader = []
        self.t = 0.0

    def steg(self, plc, x_mm=0.0):
        self.rader.append({
            "t": round(self.t, 4),
            "parts": {"broms": {"p": [0.0, 0.0, 0.5], "q": list(Q0)}},
            "scene": {"produkt": {"p": [x_mm / 1000.0, 0.0, 0.5], "q": list(Q0)}},
            "scenlast": True,
            "plc": dict(plc),
            "plc_alder_s": 0.05,
        })
        self.t += DT
        return self

    def data(self):
        return {
            "v": 1,
            "template": self.template,
            "run": {"started": "2026-09-04T21:00:00", "dur_s": round(self.t, 3),
                    "samples": len(self.rader), "rate_hz": RATE},
            "tracked": {"parts": ["broms"], "tools": [], "signals": [],
                        "pairs": [], "joints": [], "stations": [],
                        "scene": ["produkt"]},
            "rows": self.rader,
        }


# Varje cykel inleds med ett tomt fonster sa att givaren har en STIGANDE
# flank. Utan det borjar serien med givaren redan hog, och da finns ingen
# cykelstart att raekna fran - vilket ar en annan felklass an de som provas.
STATION_TOMT_S = 0.4


def _stationscykel(b, t_stopp_s=2.0, slapp_s=0.5, givare_s=3.6,
                   stopp_fordrojning_s=0.1, stopp_igen=False,
                   stoppa_aldrig=False, slapp_aldrig=False, x0=0.0):
    """En cykel: produkten kommer, stoppet gar pa, processtiden gar, den slapps.

    Talen ar cellens egna och namnges - de ar facit, inte trosklar.

    `stopp_igen` lagger en ANDRA stoppuls mitt i slappet. Den bryter
    forreglingen utan att rubba ett enda av sekvensens steg, och det ar
    avsikten: annars gar det inte att visa att forreglingsgrinden mater nagot
    som sekvensgrinden inte redan mater.
    """
    n = int(round((STATION_TOMT_S + givare_s) * RATE))
    for i in range(n):
        t = i * DT - STATION_TOMT_S
        givare = 0.0 <= t < givare_s - 0.4
        stopp = (not stoppa_aldrig) and stopp_fordrojning_s <= t < t_stopp_s
        if stopp_igen and t_stopp_s + 0.15 <= t < t_stopp_s + 0.45:
            stopp = True
        slapp = (not slapp_aldrig) and t_stopp_s <= t < t_stopp_s + slapp_s
        x = x0 if stopp else x0 + (max(t, 0.0) * 250.0)
        b.steg({"givare": givare, "stopp": stopp, "slapp": slapp}, x_mm=x)
    return b


def station_bra():
    """Tva hela cykler i ratt ordning. Utan den ar varje fallning nedan
    vardelos - en domare som faller allt klarar alla ovriga prov."""
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b)
    return b, stationsplan()


def station_utan_stopp():
    """Stoppet gar aldrig hogt: stationen gjorde ingenting."""
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b, stoppa_aldrig=True)
    return b, stationsplan()


def station_slapper_aldrig():
    """Stoppet gar pa och stannar dar. Produkten kommer aldrig vidare."""
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b, t_stopp_s=3.4, slapp_aldrig=True)
    return b, stationsplan()


def station_forsent():
    """Ratt ordning, men processtiden ar dubbelt sa lang som facit tillater."""
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b, t_stopp_s=3.0, givare_s=4.6)
    return b, stationsplan()


def station_forregling_bruten():
    """Stoppet och slappet hoga SAMTIDIGT - tva rorelser pa en gang.

    Sekvensens fyra steg haller alla; det ENDA som brister ar forreglingen.
    """
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b, stopp_igen=True)
    return b, stationsplan()


def station_forregling_utan_deklaration():
    """Samma overlapp, men planen har inte bett om nagon forregling.

    Den andra riktningen: en grind som faller aven nar ingen fraga stallts
    mater sin egen asikt, inte korningen.
    """
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b, stopp_igen=True)
    return b, stationsplan(forregling=False)


def station_bara_en_cykel():
    """En enda cykel, men facit kraver tva. Oprovat, inte godkant."""
    b = Stationsbygge()
    _stationscykel(b)
    return b, stationsplan()


def station_utan_deklaration():
    """Ingen sekvens, ingen forregling, inga greppande roller.

    Ingen fraga stalld. Det far ALDRIG bli ett PASS - da vore vagen ut ur
    greppgrinden att utelamna en rad ur planen.
    """
    b = Stationsbygge()
    for _ in range(3):
        _stationscykel(b)
    return b, stationsplan(sekvens=False, forregling=False)


ALLA = {
    "bra": bra,
    "teleport": teleport,
    "glider": glider,
    "tappad": tappad,
    "fel_placerad": fel_placerad,
    "aldrig_gripen": aldrig_gripen,
    "explosion": explosion,
    "under_golvet": under_golvet,
    "kollision": kollision,
    "kort_uppehall": kort_uppehall,
    "for_fa_prov": for_fa_prov,
    # scenen som helhet
    "bakgrund_stilla": bakgrund_stilla,
    "scen_deltalagrad": scen_deltalagrad,
    "oombedd_rorelse": oombedd_rorelse,
    "oombedd_men_deklarerad": oombedd_men_deklarerad,
    "utglesad_scen": utglesad_scen,
    "tva_produkter": tva_produkter,
    "orort_trots_signal": orort_trots_signal,
    "band_ror_sig": band_ror_sig,
    # robotleder
    "robot_ren": robot_ren,
    "robot_gransnara": robot_gransnara,
    "robot_ledgrans": robot_ledgrans,
    "robot_singularitet": robot_singularitet,
    "robot_omorientering": robot_omorientering,
    "robot_foljer": robot_foljer,
    "robot_foljfel": robot_foljfel,
    "robot_stopp_begransande": robot_stopp_begransande,
    # kollision och minsta avstand
    "mindist_nara": mindist_nara,
    "kollision_med_feature": kollision_med_feature,
    # stationer
    "station_svalt": station_svalt,
    "station_svalt_utan_krav": station_svalt_utan_krav,
    "station_blockerad": station_blockerad,
    "station_upptagen": station_upptagen,
    # PLC
    "plc_i_fas": plc_i_fas,
    "plc_ur_fas": plc_ur_fas,
    "plc_gammal": plc_gammal,
    "fas_utanfor_tolerans": fas_utanfor_tolerans,
    "fas_inom_tolerans": fas_inom_tolerans,
    "fas_inom_upplosningen": fas_inom_upplosningen,
    "fas_finare_an_upplosningen": fas_finare_an_upplosningen,
    # rorelse
    "utslungad": utslungad,
    "rord_men_aldrig_gripen": rord_men_aldrig_gripen,
    # trosklarnas granser
    "pa_placeringsgransen": pa_placeringsgransen,
    "pa_barstrackans_grans": pa_barstrackans_grans,
    "utan_placeringstolerans": utan_placeringstolerans,
    # stationen
    "station_bra": station_bra,
    "station_utan_stopp": station_utan_stopp,
    "station_slapper_aldrig": station_slapper_aldrig,
    "station_forsent": station_forsent,
    "station_forregling_bruten": station_forregling_bruten,
    "station_forregling_utan_deklaration": station_forregling_utan_deklaration,
    "station_bara_en_cykel": station_bara_en_cykel,
    "station_utan_deklaration": station_utan_deklaration,
}
