# -*- coding: utf-8 -*-
"""L3: FAS 15, de fem domarna och kollisionsmattet i en KORANDE VC. Mater M-88.

Fasens grind kraver domar som faller pa SEKVENS, TIMING, GREPP, KOLLISION och
GENOMFLODE, var och en med en trasig cell som MASTE fallas. M-65 matte den
matrisen pa syntetiska serier. Har byggs cellerna i VC:s riktiga scengraf och
domen tas pa det VC verkligen svarade.

VAD SOM AR RIKTIGT HAR OCH VAD SOM INTE AR DET

  poserna       riktiga. Komponenterna finns i app.Components och lases genom
                WorldPositionMatrix, samma vag en riktig cell ger.
  minsta avstandet  riktigt. vcNode.measureDistance mellan tva riktiga
                kroppar, under en KORANDE simulering - det som M-65 skrev upp
                som oprovat.
  PLC-vardena   gar genom den riktiga bryggan och den riktiga Ogonkoppling,
                med matt alder och matt hopfogningstak (M-87). Men de kommer
                fran det har skriptet och inte fran en PLC. Det star i LIMITS.
  statistiken   forsoks. Gar det inte att bygga ett vcStatistics-beteende
                sags det rent ut - inget tyst hopp over en domare.

  P15-4  measureDistance under en korande simulering: sjunker avstandet
         monotont till 0,0, och blir kontakt sant i det prov kropparna nuddar?
  P15-5  vad det kostar per prov med 1, 5 och 20 bevakade par.
  P15-8  fem trasiga celler, byggda i VC. Var och en ska fa FAIL med RATT
         domare, och exakt en domare pa FAIL.
  P15-9  LIMITS i ogats riktiga utdata, och guldgrinden mot den.

    python3 tests/protocol/kor_fas15_domarna.py --json ut.json
"""

BANKPOST = {
    "pastar":
        "De fem domarna sekvens, timing, grepp, kollision och genomflode "
        "faller var sin trasiga cell byggd i VC:s riktiga scengraf, och exakt "
        "en domare faller per cell.",
    "under_prov": (
        "ext/vc_addon/vc_assist/oga_analys.py",
        "ext/vc_addon/vc_assist/oga_provtagning.py",
        "svc/vc_assist_svc/guldgrind.py",
        "svc/vc_assist_svc/plc/ogonkoppling.py",
    ),
    "facit":
        "aldrig_gripen ska fallas av grepp, station_utan_stopp av sekvens och "
        "station_forsent av timing; avstandet mellan tva kroppar ska sjunka "
        "monotont till 0,0 och kontakt bli sant i det prov de nuddar",
    "facitkalla":
        "cellerna ar handskrivna scenarier med en felklass var och en vantad "
        "domare vardera, och det minsta avstandet domers av VC:s egen "
        "vcNode.measureDistance under korande simulering",
    "facitkalla_filer": (
        "tests/celler.py",
        "docs/spec/83_scenarier.md",
        "tests/protocol/fas15_ogat_pa_djupet.md",
        "docs/spec/50_grindar.md",
    ),
    "trasiga_fall": (
        "varje trasig cell maste fa FAIL med RATT domare, och exakt en domare "
        "pa FAIL",
        "en ogonrapport med LIMITS-sektionen bortklippt far inte bli guld",
        "gar ett vcStatistics-beteende inte att bygga sags det rent ut - "
        "inget tyst hopp over en domare",
    ),
    "kraver": ("vc",),
    "matningar": ("M-88", "M-127"),
}
import argparse
import json
import os
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "tests"))
sys.path.insert(0, os.path.join(_ROT, "tests", "protocol", "stod"))

import celler                                        # noqa: E402
import installationsgrind                            # noqa: E402
import oga_analys as A                               # noqa: E402
from vc_assist_svc.guldgrind import Guldgrind, FORGRINDAR   # noqa: E402
from vc_assist_svc.klient import Klient              # noqa: E402
from vc_assist_svc.plc.ogonkoppling import Ogonkoppling     # noqa: E402
from vc_assist_svc.tokenplats import tokenfil        # noqa: E402

PREFIX = "F15D"
SIDA_MM = 1000.0        # Protokollets "tva kuber om 1000 mm".


def _kor(k, kod, desc, timeout=180):
    post = k.koa(kod, desc=desc)
    ut = k.godkann_och_vanta(post["qid"], timeout=timeout)
    if ut["state"] != "done":
        raise RuntimeError("%s gav %s: %r" % (desc, ut["state"], ut.get("svar")))
    return ((ut.get("svar") or {}).get("result") or {}).get("result")


def stada(k):
    kod = ("import json\n"
           "app = getApplication()\n"
           "n = 0\n"
           "for c in list(app.Components):\n"
           "    if c.Name.startswith(%r):\n"
           "        app.deleteComponent(c)\n"
           "        n += 1\n"
           "print(json.dumps({'borttagna': n}))\n") % (str(PREFIX),)
    return _kor(k, kod, "fas15: stada bort %s-komponenterna" % PREFIX)


def bygg_kroppar(k, namn_och_x, sida_mm=SIDA_MM):
    """Kuber med RIKTIG geometri. Utan geometri har measureDistance inget att
    mata pa - en tom komponent ar en punkt och svarar avstand mellan origon."""
    poster = ", ".join("(%r, %.1f)" % (str(n), x) for n, x in namn_och_x)
    kod = (
        "import json\n"
        "app = getApplication()\n"
        "for c in list(app.Components):\n"
        "    if c.Name.startswith(%r):\n"
        "        app.deleteComponent(c)\n"
        "ut = []\n"
        "for namn, x in [%s]:\n"
        "    c = app.createComponent()\n"
        "    c.Name = namn\n"
        "    f = c.RootFeature.createFeature(VC_BLOCK, 'kropp')\n"
        "    for q in f.Properties:\n"
        "        if q.Name in ('Length', 'Width', 'Height'):\n"
        "            q.Value = %.1f\n"
        "    c.RootFeature.rebuild()\n"
        "    m = c.PositionMatrix\n"
        "    m.translateAbs(x - m.P.X, -m.P.Y, -m.P.Z)\n"
        "    c.PositionMatrix = m\n"
        "    ut.append(namn)\n"
        "getSimulation().update()\n"
        "print(json.dumps({'byggda': ut}))\n"
    ) % (str(PREFIX), poster, sida_mm)
    return _kor(k, kod, "fas15: bygg %d kroppar" % len(namn_och_x))


# ---- P15-4/5: measureDistance under en korande simulering ----------------

def p15_4(k, steg=40, dt=0.05):
    """En kub kors mot en annan. Avstandet ska sjunka monotont till 0,0.

    Banan gar fran 4000 mm till 1000 mm i VC:s varldsenhet. Kuberna ar
    1000 mm breda, sa ytorna moter varandra vid 1000 mm mellan origon - det
    ar DAR kontakten ska bli sann, inte vid noll mellan origon. Skillnaden ar
    hela poangen med ett YTAVSTAND.
    """
    bygg_kroppar(k, [("%s_A" % PREFIX, 4000.0), ("%s_B" % PREFIX, 0.0)])
    a, b = "%s_A" % PREFIX, "%s_B" % PREFIX
    # Banan raknas i METER: seriens kanoniska enhet (M-33).
    punkter = [[[4.0 - i * (3.0 / (steg - 1)), 0.0, 0.0]] for i in range(steg)]
    plan = {"template": "fas15_kontakt", "parts": [a], "tools": [],
            "rate_hz": 20.0, "scen": "all",
            "mind": [{"namn": "A+B", "a": [a], "b": [b], "tolerans_mm": 100.0}]}
    k.oga_start(plan, simtid=k.simtid(),
                bana={"objekt": [a], "dt": dt, "punkter": punkter})
    time.sleep(steg * dt + 3.0)
    ut = k.oga_stopp()
    data = ut.get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret"}
    serie = []
    for r in data["rows"]:
        m = (r.get("mind") or {}).get("A+B")
        if m is None:
            continue
        serie.append({"t": r["t"], "d_mm": m.get("d_mm"),
                      "kontakt": m.get("kontakt"), "metod": m.get("metod"),
                      "x_mm": (r.get("parts") or {}).get(a, {}).get("p", [None])[0]})
    if not serie:
        return {"fel": "inga mind-rader i serien", "saknade": data.get("saknade")}
    d = [s["d_mm"] for s in serie]
    # Monotont sjunkande sa lange kuben kors mot den andra: varje steg far
    # inte oka. Ett enda tal som ligger still varje prov ar M-36:s fella -
    # geometrin svarade med ett gammalt varde.
    fallande = sum(1 for i in range(1, len(d)) if d[i] <= d[i - 1] + 1e-9)
    kontakt = [s for s in serie if s["kontakt"]]
    # DOMEN pa VC:s egen serie: det har ar cellen `kontakt` (M-65) byggd i
    # VC. Kollisionsdomaren ska falla, och ingen annan.
    _text, rapport, analys = A.doma(data, plan)
    domar = dict((n, v["utfall"]) for n, v in analys.harledt["domar"].items())
    return {
        "dom": rapport.dom[0], "orsak": rapport.dom[1], "domar": domar,
        "fallande_domare": sorted(n for n, v in domar.items() if v == "FAIL"),
        "eyes": _text,
        "prov_med_mind": len(serie),
        "metod": serie[0]["metod"],
        "d_forsta_mm": d[0], "d_minsta_mm": min(d), "d_sista_mm": d[-1],
        "distinkta_varden": len(set(round(x, 6) for x in d)),
        "andel_fallande": 100.0 * fallande / max(1, len(d) - 1),
        "kontakt_prov": len(kontakt),
        "kontakt_forsta_t": kontakt[0]["t"] if kontakt else None,
        "kontakt_forsta_x_mm": (kontakt[0]["x_mm"] * 1000.0
                                if kontakt and kontakt[0]["x_mm"] is not None else None),
        "saknade": data.get("saknade"),
        "serie": serie,
    }


def p15_5(k, antal_par, sekunder=8.0):
    """Vad kostar measureDistance per prov? Svept over antalet bevakade par."""
    namn = [("%s_%02d" % (PREFIX, i), 3000.0 * (i + 1)) for i in range(21)]
    bygg_kroppar(k, namn)
    rader = []
    for n in antal_par:
        par = [{"namn": "par%02d" % i,
                "a": ["%s_%02d" % (PREFIX, i)],
                "b": ["%s_%02d" % (PREFIX, i + 1)],
                "tolerans_mm": 10.0} for i in range(n)]
        plan = {"template": "fas15_mindkostnad", "parts": [namn[0][0]],
                "tools": [], "rate_hz": 20.0, "scen": "roles", "mind": par}
        t0 = time.time()
        svar0 = k.plc_in()
        k.oga_start(plan, simtid=k.simtid())
        time.sleep(sekunder)
        svar1 = k.plc_in()
        ut = k.oga_stopp()
        vagg = time.time() - t0
        data = ut.get("data") or {}
        dom = None
        if data.get("rows"):
            # Den grona riktningen: 3000 mm mellan origon, 1000 mm-kuber, sa
            # 2000 mm ytavstand. Kollisionsdomaren ska svara PASS har, annars
            # faller den allt och P15-4 bevisar ingenting.
            _t, rapport, analys = A.doma(data, plan)
            dom = {"dom": rapport.dom[0], "orsak": rapport.dom[1][:100],
                   "kollision": analys.harledt["domar"]["kollision"]["utfall"],
                   "mindist_mm": dict((namn, v["min_mm"]) for namn, v in
                                      analys.harledt["safety"].items()
                                      if isinstance(v, dict) and "min_mm" in v)}
        rader.append({
            "par": n, "dom": dom,
            "prov": data.get("run", {}).get("samples"),
            "rate_hz": data.get("run", {}).get("rate_hz"),
            # Pumpens egen slagtakt, ur tick-raknaren i tva plc_in-svar.
            "tick_per_s": ((svar1.get("tick", 0) - svar0.get("tick", 0)) / vagg
                           if vagg > 0 else None),
            "saknade": data.get("saknade"),
        })
    return rader


# ---- P15-8: de fem cellerna i VC ----------------------------------------

class Plcdrivare(object):
    """Skjuter in cellens PLC-varden pa RATT simuleringstid, genom bryggan.

    Vagen ar den riktiga: Ogonkoppling -> plc_in -> Plckalla, med matt alder
    och matt hopfogningstak (M-87). Vad som INTE ar riktigt ar kallan: talen
    kommer harifran och inte fran en PLC. Det star i LIMITS.

    Simuleringstiden lases GRATIS ur plc_in-svaret - varje inskott bar
    pumpens simtid - sa slingan behover ingen extra tur och retur for att
    veta var i cellen den ar.
    """

    def __init__(self, klient, rader, t0):
        self.kopplare = Ogonkoppling(klient)
        self.rader = rader
        self.t0 = float(t0)
        self.n = 0
        self.sista_index = -1

    def kor(self, paus_s=0.02, extra_s=1.0):
        self.kopplare.synka()
        slut_t = self.rader[-1]["t"] + extra_s
        while True:
            t_las = time.time()
            svar = self.kopplare.sista_svar or {}
            simtid = svar.get("simtid")
            cellt = None if simtid is None else (simtid - self.t0)
            i = 0
            if cellt is not None:
                # Sista raden vars tid passerats.
                while (i + 1 < len(self.rader)
                       and self.rader[i + 1]["t"] <= cellt):
                    i += 1
            self.kopplare.skjut_in(self.rader[i].get("plc") or {}, t_last=t_las)
            self.n += 1
            self.sista_index = i
            if cellt is not None and cellt > slut_t:
                return
            time.sleep(paus_s)


def _bana_ur_cell(rader, objekt):
    """Vagpunkter for ETT objekt ur en syntetisk cells rader, i meter."""
    punkter = []
    for r in rader:
        p = None
        for grupp in ("parts", "tools", "scene"):
            if objekt in (r.get(grupp) or {}):
                p = r[grupp][objekt]["p"]
                break
        if p is None:
            p = punkter[-1][0] if punkter else [0.0, 0.0, 0.0]
        punkter.append([list(p)])
    return punkter


def kor_cell_i_vc(k, cellnamn, objekt_kartor, med_plc, extra_s=3.0):
    """Bygger cellens objekt i VC, kor den, och domer VC:s EGEN serie.

    `objekt_kartor` ar [(cellens namn, VC-namn, roll)] dar roll ar "parts",
    "tools" eller None (bakgrund).
    """
    b, plan = celler.ALLA[cellnamn]()
    rader = b.data()["rows"]
    vc_namn = [(vc, 0.0) for _cell, vc, _roll in objekt_kartor]
    bygg_kroppar(k, vc_namn)
    drivna = [vc for _cell, vc, _roll in objekt_kartor]
    punkter = []
    banor = [_bana_ur_cell(rader, cell) for cell, _vc, _roll in objekt_kartor]
    for i in range(len(rader)):
        punkter.append([banor[j][i][0] for j in range(len(banor))])
    provplan = dict(plan)
    provplan["template"] = cellnamn
    provplan["rate_hz"] = 20.0
    provplan["scen"] = "all"
    provplan["parts"] = [vc for _c, vc, roll in objekt_kartor if roll == "parts"]
    provplan["tools"] = [vc for _c, vc, roll in objekt_kartor if roll == "tools"]
    t0 = k.simtid()
    k.oga_start(provplan, simtid=t0,
                bana={"objekt": drivna, "dt": 0.05, "punkter": punkter})
    if med_plc:
        Plcdrivare(k, rader, t0).kor(extra_s=extra_s)
    else:
        time.sleep(len(rader) * 0.05 + extra_s)
    ut = k.oga_stopp()
    data = ut.get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret", "prov": ut.get("samples")}
    # Kartlagg VC:s namn tillbaka till cellens, sa planen gar att anvanda.
    for rad in data["rows"]:
        for cell, vc, roll in objekt_kartor:
            if roll and vc in (rad.get(roll) or {}):
                rad[roll][cell] = rad[roll].pop(vc)
    data["tracked"]["parts"] = [c for c, _v, roll in objekt_kartor if roll == "parts"]
    data["tracked"]["tools"] = [c for c, _v, roll in objekt_kartor if roll == "tools"]
    text, rapport, analys = A.doma(data, plan)
    domar = dict((n, v["utfall"]) for n, v in analys.harledt["domar"].items())
    ax = (analys.harledt.get("timing") or {}).get("plc_axel") or {}
    return {"dom": rapport.dom[0], "orsak": rapport.dom[1],
            "prov": len(data["rows"]), "eyes": text, "domar": domar,
            "plc_axel": {"rader_med_plc": ax.get("rader_med_plc"),
                         "otackta": ax.get("otackta"),
                         "andel_otackt": ax.get("andel_otackt"),
                         "tak_max_s": ax.get("tak_max_s"),
                         "over_braketten": ax.get("over_braketten")},
            "saknade": data.get("saknade")}


def kor_svalt_i_vc(k, sekunder=6.0, max_svalt_s=1.0, satt_idle=False):
    """Cellen `station_svalt` i VC: en station med ett RIKTIGT vcStatistics-
    beteende som ingen produkt nagonsin nar. Kravet sager hogst `max_svalt_s`
    svalt; korningen ar langre. Genomflodesdomaren ska falla - och med kravet
    satt till 100 s (den grona riktningen) ska den svara PASS pa SAMMA serie.

    Beteendet skapas med VC_STATISTICS (M-15: skapbart, ger vcStatistics).
    Skrivgrinden slapper det - det ar inget skriptbeteende (M-13).

    TRE VARIANTER:
      satt_idle=False  INERT. Ingen process har satt beteendets tillstand:
                       VC svarar state '' och 0,0 i alla procent, korningen
                       igenom. Ogat far INTE saga PASS pa det (falskt gront
                       i forsta korningen) - det ar obestambart.
      satt_idle=True   Station med verklig process (katalogens Index Conveyor
                       Process med ProcessExecutor och Statistics), satt till
                       State='Idle'. Da MATER statistiken, stationen ar ledig
                       och tom, och genomflodesdomaren ska falla mot kravet.
      satt_idle='Busy' GRON KONTROLL: samma station med matning / arbete
                       (State='Busy'). Stationen svalter inte (0 s svalt)
                       och ska fa PASS aven med kravet 1.0 s.
    """
    station = "%s_station" % PREFIX
    kropp = "%s_kropp" % PREFIX
    bygg_kroppar(k, [(kropp, 0.0)])
    if satt_idle is True or satt_idle == "Busy":
        st_val = "Busy" if satt_idle == "Busy" else "Idle"
        kod = (
            "import json\n"
            "app = getApplication()\n"
            "uri = 'C:/users/Public/Documents/Visual Components/4.10/Models/Components/Visual Components/Advanced Motion/Index Conveyor Process.vcmx'\n"
            "c = app.load(uri)\n"
            "c.Name = %r\n"
            "b = c.findBehaviour('Statistics')\n"
            "b.Name = 'stat'\n"
            "b.State = %r\n"
            "d = {'beteende': type(b).__name__,\n"
            "     'har_arrived': hasattr(b, 'ComponentsArrived'),\n"
            "     'state_satt': str(b.State),\n"
            "     'process': 'Index Conveyor Process'}\n"
            "d = dict((k, str(v)) for k, v in d.items())\n"
            "print(json.dumps(d))\n"
        ) % (str(station), st_val)
        desc = "fas15: station med process (State %s)" % st_val
    else:
        kod = (
            "import json\n"
            "app = getApplication()\n"
            "c = app.createComponent()\n"
            "c.Name = %r\n"
            "b = c.createBehaviour(VC_STATISTICS, 'stat')\n"
            "d = {'beteende': None if b is None else type(b).__name__,\n"
            "     'har_arrived': hasattr(b, 'ComponentsArrived'),\n"
            "     'state_fore': '%%s' %% (b.State,)}\n"
            "d = dict((k, '%%s' %% (v,)) for k, v in d.items())\n"
            "print(json.dumps(d))\n"
        ) % (str(station),)
        desc = "fas15: station med vcStatistics (inert)"
    skapat = _kor(k, kod, desc)
    plan = {"template": "station_svalt", "parts": [kropp], "tools": [],
            "rate_hz": 20.0, "scen": "roles", "stat": ["%s/stat" % station],
            "genomstromning": {"max_svalt_s": max_svalt_s}}
    k.oga_start(plan, simtid=k.simtid())
    time.sleep(sekunder)
    ut = k.oga_stopp()
    data = ut.get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret", "skapat": skapat}
    stat = [r["stat"]["%s/stat" % station] for r in data["rows"]
            if (r.get("stat") or {}).get("%s/stat" % station)]
    _text, rapport, analys = A.doma(data, plan)
    domar = dict((n, v["utfall"]) for n, v in analys.harledt["domar"].items())
    # Den grona riktningen pa SAMMA serie: ett krav stationen haller.
    gron_plan = dict(plan, genomstromning={"max_svalt_s": 100.0})
    _t2, rapport2, analys2 = A.doma(data, gron_plan)
    return {"dom": rapport.dom[0], "orsak": rapport.dom[1], "domar": domar,
            "eyes": _text, "prov": len(data["rows"]), "saknade": data.get("saknade"),
            "skapat": skapat, "stationsprov": len(stat),
            "forsta_stat": stat[0] if stat else None,
            "sista_stat": stat[-1] if stat else None,
            "svalt_s": (analys.harledt["stationer"].get("%s/stat" % station) or {}).get("svalt_s"),
            "gron_dom": rapport2.dom[0],
            "gron_genomflode": analys2.harledt["domar"]["genomflode"]["utfall"]}


CELLER = {
    # cell -> (objektkartor, PLC-driven, vantad domare). Vantad None = den
    # GRONA kontrollen: utan en cell som ska fa PASS bevisar fallningarna
    # ingenting - en domare som faller allt klarar alla ovriga prov.
    "aldrig_gripen": ([("del", "%s_del" % PREFIX, "parts"),
                       ("gripper", "%s_gripper" % PREFIX, "tools")], False, "grepp"),
    # Stationscellerna bar bromsen som roll: pumpen kraver minst ett spart
    # objekt i parts eller tools, och Stationsbygge har just `broms` dar.
    "station_bra": ([("produkt", "%s_produkt" % PREFIX, None),
                     ("broms", "%s_broms" % PREFIX, "parts")], True, None),
    "station_utan_stopp": ([("produkt", "%s_produkt" % PREFIX, None),
                            ("broms", "%s_broms" % PREFIX, "parts")], True, "sekvens"),
    "station_forsent": ([("produkt", "%s_produkt" % PREFIX, None),
                         ("broms", "%s_broms" % PREFIX, "parts")], True, "timing"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--anda", action="store_true")
    ap.add_argument("--hoppa", default="", help="punkter att hoppa over, t.ex. p15_5")
    ap.add_argument("--bara", default="",
                    help="bara dessa celler i P15-8 (kommaseparerat), t.ex. station_svalt")
    a = ap.parse_args()

    print("STEG 0 - kor VC repots kod?")
    ok_installation, _ = installationsgrind.kontrollera(skriv=print)
    if not ok_installation and not a.anda:
        return 2
    hoppa = set(x for x in a.hoppa.split(",") if x.strip())
    bara = set(x for x in a.bara.split(",") if x.strip())

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=180.0).anslut()
    ut = {"tid": time.strftime("%Y-%m-%d %H:%M:%S"),
          "installationen_ar_repots": ok_installation}
    try:
        if "p15_4" not in hoppa:
            print("\nP15-4 - measureDistance under en KORANDE simulering")
            ut["p15_4"] = p15_4(k)
            r = ut["p15_4"]
            if "fel" in r:
                print("  MISSLYCKADES: %s  saknade=%r" % (r["fel"], r.get("saknade")))
            else:
                print("  metod: %s | %d prov med mind | %d distinkta avstandsvarden"
                      % (r["metod"], r["prov_med_mind"], r["distinkta_varden"]))
                print("  d: forsta %.1f mm -> minsta %.1f mm -> sista %.1f mm"
                      % (r["d_forsta_mm"], r["d_minsta_mm"], r["d_sista_mm"]))
                print("  andel prov dar avstandet inte okade: %.1f %%"
                      % r["andel_fallande"])
                print("  kontakt i %d prov, forst vid t=%s med origoavstand %s mm"
                      % (r["kontakt_prov"], r["kontakt_forsta_t"],
                         r["kontakt_forsta_x_mm"]))
                print("  DOM: %s  fallande domare=%s  (vantad: kollision ensam)"
                      % (r["dom"], r["fallande_domare"]))
                print("      orsak: %s" % r["orsak"][:110])

        if "p15_5" not in hoppa:
            print("\nP15-5 - vad measureDistance kostar per prov")
            ut["p15_5"] = p15_5(k, [1, 5, 20])
            print("  %-6s %-6s %-9s %-10s %-8s %s" % ("par", "prov", "rate_hz",
                                                      "tick/s", "saknade", "dom"))
            for r in ut["p15_5"]:
                print("  %-6d %-6s %-9s %-10s %-8s %s / kollision=%s"
                      % (r["par"], r["prov"], r["rate_hz"],
                         None if r["tick_per_s"] is None else round(r["tick_per_s"], 1),
                         len(r["saknade"] or []),
                         (r["dom"] or {}).get("dom"), (r["dom"] or {}).get("kollision")))

        if "p15_8" not in hoppa:
            print("\nP15-8 - trasiga celler byggda i VC")
            ut["p15_8"] = {}
            for namn, (kartor, med_plc, vantad) in sorted(CELLER.items()):
                if bara and namn not in bara:
                    continue
                try:
                    r = kor_cell_i_vc(k, namn, kartor, med_plc)
                except Exception as e:
                    r = {"fel": "%s: %s" % (type(e).__name__, e)}
                r["vantad_domare"] = vantad
                if "domar" in r and r["domar"]:
                    fallande = [d for d, v in sorted(r["domar"].items())
                                if v == "FAIL"]
                    r["fallande_domare"] = fallande
                    r["ratt_domare"] = ((fallande == [vantad]) if vantad
                                        else (fallande == [] and r.get("dom") == "PASS"))
                ut["p15_8"][namn] = r
                print("  %-22s dom=%-13s vantad domare=%-11s fallande=%s%s"
                      % (namn, r.get("dom", r.get("fel")), vantad or "(PASS)",
                         r.get("fallande_domare"),
                         "" if r.get("ratt_domare") else "   <- INTE SOM VANTAT"))
                if r.get("orsak"):
                    print("      orsak: %s" % r["orsak"][:110])
                if r.get("plc_axel", {}).get("rader_med_plc"):
                    ax = r["plc_axel"]
                    print("      PLC-axeln: %d av %d otackta (%.1f %%), tak max %.3f s%s"
                          % (ax["otackta"], ax["rader_med_plc"],
                             100.0 * ax["andel_otackt"], ax["tak_max_s"] or 0.0,
                             "  <- OVER BRAKETTEN" if ax["over_braketten"] else ""))
            # Genomflodet: en station med ett riktigt vcStatistics-beteende,
            # i tva varianter. Den inerta ar den TRASIGA FIXTUREN for
            # fail-closed (M-88 §5: forsta korningen gav PASS pa den).
            for namn, satt_idle, vantat in (("station_svalt_inert", False, "INCONCLUSIVE"),
                                            ("station_svalt", True, "FAIL"),
                                            ("station_svalt_matad", "Busy", "PASS")):
                if bara and namn not in bara:
                    continue
                try:
                    r = kor_svalt_i_vc(k, satt_idle=satt_idle)
                except Exception as e:
                    r = {"fel": "%s: %s" % (type(e).__name__, e)}
                r["vantad_domare"] = "genomflode"
                r["vantad_dom"] = vantat
                if r.get("domar"):
                    fallande = [d for d, v in sorted(r["domar"].items()) if v == "FAIL"]
                    r["fallande_domare"] = fallande
                    if vantat == "FAIL":
                        r["ratt_domare"] = (fallande == ["genomflode"]
                                            and r.get("gron_genomflode") == "PASS")
                    else:
                        r["ratt_domare"] = (r.get("dom") == vantat and not fallande)
                ut["p15_8"][namn] = r
                print("  %-22s dom=%-13s vantad=%-16s fallande=%s%s"
                      % (namn, r.get("dom", r.get("fel")),
                         "genomflode" if vantat == "FAIL" else vantat,
                         r.get("fallande_domare"),
                         "" if r.get("ratt_domare") else "   <- INTE SOM VANTAT"))
                if r.get("orsak"):
                    print("      orsak: %s" % r["orsak"][:110])
                if "skapat" in r:
                    print("      vcStatistics: %r | stationsprov %s | sista %s | svalt %s s | "
                          "med krav 100 s: %s (genomflode %s)"
                          % (r["skapat"], r.get("stationsprov"), r.get("sista_stat"),
                             r.get("svalt_s"), r.get("gron_dom"), r.get("gron_genomflode")))

        # P15-9: LIMITS i ogats RIKTIGA utdata, och guldgrinden mot den.
        texter = [(n, r["eyes"]) for n, r in (ut.get("p15_8") or {}).items()
                  if r.get("eyes")]
        if texter:
            print("\nP15-9 - LIMITS i ogats riktiga utdata")
            grind = Guldgrind({"cell"})
            ut["p15_9"] = {}
            for namn, text in texter:
                cell = {"namn": namn, "klass": "cell", "eyes": text,
                        "forgrindar": dict((g, True) for g in FORGRINDAR)}
                utan = {"namn": namn + "_utan_limits", "klass": "cell",
                        "eyes": _utan_sektion(text, "LIMITS"),
                        "forgrindar": dict((g, True) for g in FORGRINDAR)}
                b1 = grind.doma([cell])
                b2 = grind.doma([utan])
                rader = [r.strip() for r in text.splitlines() if r.strip()]
                limits = [r for r in rader if r.startswith(("NOT_SIMULATED",
                                                            "RESOLUTION",
                                                            "EXCLUDED"))]
                ut["p15_9"][namn] = {
                    "limitsrader": limits,
                    "med_limits_guld": b1.guld, "med_limits_skal": b1.text(),
                    "utan_limits_guld": b2.guld, "utan_limits_skal": b2.text()}
                print("  %-22s LIMITS-rader %d | med: %s | UTAN: %s"
                      % (namn, len(limits), b1.text()[:34], b2.text()[:46]))
    finally:
        try:
            print("\n  stadar: %r" % (stada(k),))
        except Exception as e:
            print("\n  STADNINGEN MISSLYCKADES: %s: %s" % (type(e).__name__, e))
        if a.json:
            with open(a.json, "w") as f:
                json.dump(ut, f, indent=2)
            print("  skrev %s" % a.json)
        k.stang()
    return 0


def _utan_sektion(text, sektion):
    """Samma rapport med en hel sektion bortklippt. Den TRASIGA fixturen for
    guldgrindens LIMITS-krav: en grind som aldrig fallt har inte matt nagot."""
    ut, i = [], 0
    rader = text.splitlines()
    while i < len(rader):
        if rader[i].strip() == "SECTION %s" % sektion:
            i += 1
            while i < len(rader) and not rader[i].startswith(("SECTION ", "EYES ")):
                i += 1
            continue
        ut.append(rader[i])
        i += 1
    return "\n".join(ut) + "\n"


if __name__ == "__main__":
    sys.exit(main())
