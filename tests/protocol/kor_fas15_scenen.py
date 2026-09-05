# -*- coding: utf-8 -*-
"""L3: FAS 15, hela scenen i en KORANDE VC. Mater M-86.

Fasens krav ar operatorens: *"programmatiskt kunna forsta vad som pagar i en
scen"*, och tidsserier over **alla objekts positioner**. `42_ogat_utbyggt.md`
§1 sager att varje komponent i `app.Components` far sin pose i varje prov.
M-65 lagade enheten i den vagen (`poser_alla` delade inte med 1000) men matte
det i en FALSK VC. Har mats det i den riktiga.

PUNKTERNA (ur tests/protocol/fas15_ogat_pa_djupet.md)

  P15-1  hela scenen, i en enhet. En komponent pa x = 1000 mm ska ge p[0] =
         1,0 bade som roll och som bakgrund. Fel med tusen at nagot hall ar
         rott.
  P15-2  en orord komponents driv. Ingenting ror sig; varje bakgrundsobjekt
         ska fa stilla=True, vaglangd 0 och ett uppmatt brus_mm. Talet ar
         underlag till M-10:s ROR_SIG_MM.
  P15-3  VC:s EGEN kostnad for hela scenen, svept over antalet komponenter.
         Provtagarens egen kostnad ar matt utan VC (2,3 us per komponent,
         42_ogat_utbyggt.md §1); VC:s ar inte, och den ar sannolikt den
         tyngre halvan.

    python3 tests/protocol/kor_fas15_scenen.py --json ut.json
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

PREFIX = "F15"          # Allt den har korningen skapar heter sa, och bara det
                        # den skapat tas bort igen. Scenen delas med andra.


def p(v, andel):
    s = sorted(v)
    return s[min(len(s) - 1, int(round(andel * (len(s) - 1))))]


def _kor(k, kod, desc, timeout=120):
    """Scenandring genom KON, aldrig genom exec (I12)."""
    post = k.koa(kod, desc=desc)
    ut = k.godkann_och_vanta(post["qid"], timeout=timeout)
    if ut["state"] != "done":
        raise RuntimeError("%s gav %s: %r" % (desc, ut["state"], ut.get("svar")))
    return ut


def bygg(k, n, x_mm=1000.0, avstand_mm=500.0):
    """n komponenter pa kanda lagen, alla med prefixet F15.

    Lagen sats i VC:s varldsenhet - millimeter (M-33) - rakt genom
    PositionMatrix, sa provet mater ogats vag in och inte ogats vag ut.
    """
    kod = (
        "import json\n"
        "app = getApplication()\n"
        "gamla = [c for c in list(app.Components) if c.Name.startswith(%r)]\n"
        "for c in gamla:\n"
        "    app.deleteComponent(c)\n"
        "skapade = []\n"
        "for i in range(%d):\n"
        "    c = app.createComponent()\n"
        "    c.Name = '%s_%%03d' %% i\n"
        # translateAbs ar RELATIV i absoluta axlar (M-11), sa ett absolut
        # lage satts som skillnaden mot det nuvarande - samma vag som
        # VcScen.satt_pose. vcMatrix har ingen setP.
        "    m = c.PositionMatrix\n"
        "    m.translateAbs(%f + i * %f - m.P.X, -m.P.Y, -m.P.Z)\n"
        "    c.PositionMatrix = m\n"
        "    skapade.append(c.Name)\n"
        # M-11 i SAMMA tick som skrivningen: slapar varldsmatrisen ett
        # scenuppdatering? Lases det ett anrop senare hinner pumpen ticka
        # emellan och slapet ar borta - da mater provet vantetiden, inte
        # slapet.
        "d = {'skapade': len(skapade), 'forsta': skapade[:2],\n"
        "     'totalt': len(list(app.Components))}\n"
        "if skapade:\n"
        "    c = app.findComponent(skapade[0])\n"
        "    d['pos_x'] = c.PositionMatrix.P.X\n"
        "    d['varld_fore_update_x'] = c.WorldPositionMatrix.P.X\n"
        "    getSimulation().update()\n"
        "    d['varld_efter_update_x'] = c.WorldPositionMatrix.P.X\n"
        "print(json.dumps(d))\n"
    ) % (str(PREFIX), n, str(PREFIX), x_mm, avstand_mm)
    return _svar(_kor(k, kod, "fas15: bygg %d komponenter" % n))


def _svar(ut):
    """Utdata ur en koad korning.

    Koden kors med exec och har inget returvarde; bryggan tar resultatet ur
    SISTA RADEN pa stdout om den ar giltig JSON (protokoll.sista_raden_json).
    Den ligger sedan i svar.result.result.
    """
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
    return _svar(_kor(k, kod, "fas15: stada bort F15-komponenterna"))


def _las_lage(k, namn):
    """Vad VC sjalv sager att komponenten star pa, i VC:s varldsenhet.

    TRE tal, inte ett, for de ar tre olika saker:
      pos          PositionMatrix - det som sattes, direkt lasbart
      varld_fore   WorldPositionMatrix INNAN sim.update()
      varld_efter  samma efter sim.update()

    M-11: WorldPositionMatrix slapar ett scenuppdatering. Fas 8 gick pa den
    fallan och gjorde ett 1 mm-prov till falska pulser. Provtagaren gor
    sim.update() varje prov; en rak exec gor det inte, och da svarar VC med
    ett gammalt lage utan att saga nagot.
    """
    kod = ("import json\n"
           "app = getApplication()\n"
           "sim = getSimulation()\n"
           "c = app.findComponent(%r)\n"
           "pos = c.PositionMatrix.P\n"
           "fore = c.WorldPositionMatrix.P\n"
           "d = {'pos_x': pos.X, 'varld_fore_x': fore.X}\n"
           "sim.update()\n"
           "efter = c.WorldPositionMatrix.P\n"
           "d['varld_efter_x'] = efter.X\n"
           "d['y'] = efter.Y\n"
           "d['z'] = efter.Z\n"
           "print(json.dumps(d))\n") % (str(namn),)
    # sim.update() ar en SKRIVNING enligt skrivgrinden och maste ga genom kon
    # (I12). Den grinden fallde den har raden nar den forst skrevs som en rak
    # exec, och det ar ratt: update() ror scenen.
    return _svar(_kor(k, kod, "fas15: las lage for %s" % namn))


def p15_1(k, sekunder=3.0):
    """Samma komponent last som ROLL och som BAKGRUND. Samma tal, eller rott."""
    byggd = bygg(k, 2)
    namn_roll = "%s_000" % PREFIX
    namn_bakgrund = "%s_001" % PREFIX
    vc = {namn_roll: _las_lage(k, namn_roll),
          namn_bakgrund: _las_lage(k, namn_bakgrund)}
    plan = {"template": "fas15_enhet", "parts": [namn_roll], "tools": [],
            "rate_hz": 20.0, "scen": "all"}
    k.oga_start(plan, simtid=k.simtid())
    time.sleep(sekunder)
    data = k.oga_stopp().get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret"}
    rader = H.expandera(data["rows"])
    sista = rader[-1]
    roll = (sista.get("parts") or {}).get(namn_roll)
    bakgrund = (sista.get("scene") or {}).get(namn_bakgrund)
    return {
        "vc_mm": vc,
        "samma_tick": byggd,
        # SLAPET, matt i samma tick som skrivningen (M-11).
        "varldsmatrisen_slapade_samma_tick": bool(
            byggd.get("varld_fore_update_x") != byggd.get("varld_efter_update_x")),
        "roll_p": None if roll is None else roll["p"],
        "bakgrund_p": None if bakgrund is None else bakgrund["p"],
        "prov": len(rader),
        # Kravet: bada i kanonisk meter. 1000 mm i VC = 1,0 i serien.
        "roll_ok": bool(roll and abs(roll["p"][0]
                                     - vc[namn_roll]["varld_efter_x"] / 1000.0) < 1e-6),
        "bakgrund_ok": bool(bakgrund and abs(bakgrund["p"][0]
                                             - vc[namn_bakgrund]["varld_efter_x"] / 1000.0) < 1e-6),
        # M-11 en gang till, matt: slapade varldsmatrisen ett uppdatering?
        "varldsmatrisen_slapade": bool(
            vc[namn_roll]["varld_fore_x"] != vc[namn_roll]["varld_efter_x"]),
    }


def p15_2(k, n, sekunder):
    """Ingenting ror sig. Hur mycket driver en orord komponent anda?"""
    bygg(k, n)
    plan = {"template": "fas15_driv", "parts": ["%s_000" % PREFIX], "tools": [],
            "rate_hz": 20.0, "scen": "all"}
    k.oga_start(plan, simtid=k.simtid())
    time.sleep(sekunder)
    ut = k.oga_stopp()
    data = ut.get("data")
    if data is None:
        return {"fel": "serien rymdes inte i svaret", "prov": ut.get("samples")}
    rader = H.expandera(data["rows"])
    serier = H.objektserier(rader, grupper=("scene",))
    mina, andras = [], []
    for namn, serie in serier.items():
        prof = H.rorelseprofil(serie)
        post = {"objekt": namn, "stilla": prof["stilla"],
                "vaglangd_mm": prof["vaglangd_mm"],
                "brus_mm": prof["brus_mm"],
                "forflyttning_mm": prof["forflyttning_mm"],
                "maxfart_ms": prof["maxfart_ms"],
                "olast_andel": prof["olast_andel"], "prov": prof["prov"]}
        (mina if namn.startswith(PREFIX) else andras).append(post)
    mina.sort(key=lambda x: x["objekt"])
    brus = [x["brus_mm"] for x in mina]
    vag = [x["vaglangd_mm"] for x in mina]
    netto = [x["forflyttning_mm"] for x in mina]
    return {
        "sekunder": sekunder, "prov": len(rader), "objekt": len(serier),
        "mina": len(mina), "andras": len(andras),
        "alla_stilla": all(x["stilla"] is True for x in mina),
        "brus_mm": {"max": max(brus), "median": p(brus, .5), "summa": sum(brus)},
        "vaglangd_mm": {"max": max(vag), "median": p(vag, .5)},
        "forflyttning_mm": {"max": max(netto), "median": p(netto, .5)},
        # Talet M-10 ska satta ROR_SIG_MM ur: drivet per objekt och MINUT.
        "brus_mm_per_minut": (max(brus) * 60.0 / sekunder) if sekunder else None,
        "scen": data["scen"],
        "objekt_som_rorde_sig": [x for x in mina if x["stilla"] is not True][:5],
        "andras_som_rorde_sig": [x["objekt"] for x in andras
                                 if x["stilla"] is not True][:10],
    }


def p15_3(k, antal, sekunder, uppdatera=True):
    """VC:s EGEN kostnad for hela scenen, svept over antalet komponenter."""
    rader = []
    for n in antal:
        byggd = bygg(k, n)
        plan = {"template": "fas15_kostnad", "parts": ["%s_000" % PREFIX],
                "tools": [], "rate_hz": 20.0, "scen": "all"}
        k.oga_start(plan, simtid=k.simtid())
        time.sleep(sekunder)
        ut = k.oga_stopp()
        data = ut.get("data")
        scen = (data or {}).get("scen") or {}
        kostnad = scen.get("kostnad_ms") or {}
        rader.append({
            "byggda": n,
            "komponenter_i_scenen": (byggd or {}).get("totalt"),
            "objekt_i_serien": scen.get("objekt"),
            "prov": (data or {}).get("run", {}).get("samples"),
            "avlasningar": scen.get("avlasningar"),
            "median_ms": kostnad.get("median"), "max_ms": kostnad.get("max"),
            # Klockan inne i VC:s py2.7 ar grov (kvantiserad till ~1 ms, se
            # medianen som blir 0,0). Medelvardet ur SUMMAN over manga
            # avlasningar ar det enda talet som overlever den grovheten.
            "medel_ms": (round(kostnad["summa"] / kostnad["n"], 4)
                         if kostnad.get("n") else None),
            "summa_ms": kostnad.get("summa"), "n_kostnad": kostnad.get("n"),
            "gles_faktor": scen.get("gles_faktor"),
            "handelser": scen.get("handelser"),
            "budget_ms": scen.get("budget_ms"),
            "tak": any(g.get("orsak") == "TAK" for g in scen.get("handelser") or []),
        })
    return rader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8901)
    ap.add_argument("--token", default=None)
    ap.add_argument("--driv-sekunder", type=float, default=60.0)
    ap.add_argument("--kostnad-sekunder", type=float, default=8.0)
    ap.add_argument("--kostnad-antal", default="10,50,100,200,400,800")
    ap.add_argument("--driv-antal", type=int, default=50)
    ap.add_argument("--json", default=None)
    ap.add_argument("--anda", action="store_true")
    a = ap.parse_args()

    print("STEG 0 - kor VC repots kod?")
    ok_installation, _ = installationsgrind.kontrollera(skriv=print)
    if not ok_installation and not a.anda:
        return 2

    k = Klient(port=a.port, tokenfil=a.token or tokenfil(), timeout=180.0).anslut()
    ut = {"tid": time.strftime("%Y-%m-%d %H:%M:%S"),
          "installationen_ar_repots": ok_installation}
    try:
        print("\nP15-1 - hela scenen, i en enhet")
        ut["p15_1"] = p15_1(k)
        r = ut["p15_1"]
        if "fel" in r:
            print("  MISSLYCKADES: %s" % r["fel"])
        else:
            for namn, vc in sorted(r["vc_mm"].items()):
                print("  %s: PositionMatrix %.1f | World fore update %.1f | "
                      "efter %.1f  (VC:s varldsenhet)"
                      % (namn, vc["pos_x"], vc["varld_fore_x"],
                         vc["varld_efter_x"]))
            print("  i SAMMA tick som skrivningen: pos %.1f | World fore "
                  "update %.1f | efter %.1f -> slapade: %s"
                  % (r["samma_tick"].get("pos_x", -1),
                     r["samma_tick"].get("varld_fore_update_x", -1),
                     r["samma_tick"].get("varld_efter_update_x", -1),
                     r["varldsmatrisen_slapade_samma_tick"]))
            print("  ett anrop senare slapade den: %s"
                  % r["varldsmatrisen_slapade"])
            print("  som roll:      p = %r  %s"
                  % (r["roll_p"], "OK" if r["roll_ok"] else "FEL"))
            print("  som bakgrund:  p = %r  %s"
                  % (r["bakgrund_p"], "OK" if r["bakgrund_ok"] else "FEL"))

        print("\nP15-2 - en orord komponents driv (%.0f s, %d komponenter)"
              % (a.driv_sekunder, a.driv_antal))
        ut["p15_2"] = p15_2(k, a.driv_antal, a.driv_sekunder)
        r = ut["p15_2"]
        if "fel" in r:
            print("  MISSLYCKADES: %s" % r["fel"])
        else:
            print("  %d prov, %d objekt i scenen (%d mina, %d andras)"
                  % (r["prov"], r["objekt"], r["mina"], r["andras"]))
            print("  alla mina stilla: %s" % r["alla_stilla"])
            print("  brus_mm:        max %.6f  median %.6f"
                  % (r["brus_mm"]["max"], r["brus_mm"]["median"]))
            print("  vaglangd_mm:    max %.6f" % r["vaglangd_mm"]["max"])
            print("  forflyttning_mm:max %.6f" % r["forflyttning_mm"]["max"])
            print("  -> brus per objekt och MINUT: %.6f mm"
                  % r["brus_mm_per_minut"])
            if r["andras_som_rorde_sig"]:
                print("  andras objekt som rorde sig: %s"
                      % ", ".join(r["andras_som_rorde_sig"]))

        print("\nP15-3 - VC:s egen kostnad for hela scenen")
        antal = [int(x) for x in a.kostnad_antal.split(",") if x.strip()]
        ut["p15_3"] = p15_3(k, antal, a.kostnad_sekunder)
        print("  %-8s %-9s %-6s %-7s %9s %9s %9s %6s %s"
              % ("byggda", "i scenen", "prov", "avlasn", "medel_ms",
                 "median_ms", "max_ms", "gles", "TAK"))
        for r in ut["p15_3"]:
            print("  %-8d %-9s %-6s %-7s %9s %9s %9s %6d %s"
                  % (r["byggda"], r["komponenter_i_scenen"], r["prov"],
                     r["n_kostnad"], r["medel_ms"], r["median_ms"], r["max_ms"],
                     r["gles_faktor"], "JA" if r["tak"] else "nej"))
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


if __name__ == "__main__":
    sys.exit(main())
