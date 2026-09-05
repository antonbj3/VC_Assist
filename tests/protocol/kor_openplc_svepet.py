# -*- coding: utf-8 -*-
"""M-108: de 247 svepfallen genom OpenPLC som tredje motor.

Lager A (lokalt, snabbt): varje fall ur
`tests/enhet/test_st_svep_mot_strucpp.py` genom vart lager (`validera`) och
genom STruC++:s compile-API (`paket.kompilera`, samma kompilator som svepet
men den vag editorn och OpenPLC anvander, inte CLI:ts framande).

Lager B (container, langsamt): samma kalla + genererad CONFIGURATION byggs
till projekt.zip och laddas upp mot OpenPLC v4. Utfallet ar SUCCESS/FAILED
ur `/api/compilation-status`. Ingen start, ingen OPC UA - fragan har ar vad
motorn ACCEPTERAR, inte vad den gor (det ar kor_openplc_scan.py).

Klasser per fall (M-99:s definitioner):
  OVERENS            vi och OpenPLC sager samma sak
  STRANGARE_BEKRAFTAD vi faller, OpenPLC accepterar, raden finns i STRANGARE
  NY_STRANGARE       vi faller, OpenPLC accepterar, ingen rad - misstankt
                     FALSK RODGRIND, kraver IEC-dom i steg 3
  HAL_BEKRAFTAD      vi slapper, OpenPLC faller, raden finns i LATTARE
                     (kompilatorversionens begransning, aven i runtimen)
  NYTT_HAL           vi slapper, OpenPLC faller, ingen rad - ett hal
  EJ_KORD            ena sidan kordes inte - far ALDRIG rapporteras som overens

Trasiga fixturer (fail-closed):
  * OpenPLC som inte svarar -> exit != 0 med skal, aldrig tyst gront.
  * `ingen_pou` (tom kalla) maste FALLA i OpenPLC; gor den inte det ar
    sjalva verdict-mattningen trasig.
  * Ett fall dar ena sidan inte kordes rapporteras som EJ_KORD, inte OVERENS.

Kors (lager A, utan container):
    python3 tests/protocol/kor_openplc_svepet.py --no-upload --json /tmp/m108_a.json

Kors (lager B, delmangd 1 av 3 mot egen behallare):
    python3 tests/protocol/kor_openplc_svepet.py --bas https://127.0.0.1:18444 \\
        --strucpp-paket <paket> --runtime-include <include> \\
        --byggkatalog /tmp/m108_svep --del 0/3 --json /tmp/m108_b0.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.plc import paket as P  # noqa: E402
from vc_assist_svc.plc.openplc import OpenPlcV4, OpenPlcFel  # noqa: E402
from vc_assist_svc.st import validera  # noqa: E402


def _las_svep():
    """FALL/kalla/STRANGARE/LATTARE fran svepfilen, utan att kora dess prov."""
    sokvag = os.path.join(_ROT, "tests", "enhet",
                          "test_st_svep_mot_strucpp.py")
    spec = importlib.util.spec_from_file_location("svep_modul", sokvag)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.FALL, mod.kalla, mod.STRANGARE, mod.LATTARE


BANKPOST = {
    "pastar": (
        "De 247 fallen ger samma dom i vart lager som i OpenPLC, eller sa "
        "klassas avvikelsen som STRANGARE/FALSK RODGRIND/HAL."),
    # BENCH-4-not (M-108): det som DOMS ar vart ST-lager, inte kanalen.
    # openplc.py/paket.py ar harnesset facit kommer GENOM, inte källan.
    # Källan ar OpenPLC-runtimens egen kompilering - ett externt program,
    # ingen fil i repot, darfor tomt facitkalla_filer.
    "under_prov": ("svc/vc_assist_svc/st/",),
    "facit": "OpenPLC Runtime v4 (oberoende tredje motor)",
    "facitkalla": "OpenPLC Runtime v4:s egen kompilering, last over REST "
                  "(/api/compilation-status)",
    "facitkalla_filer": (),
    "trasiga_fall": (
        "OpenPLC som inte svarar far aldrig ge tyst gront",
        "saboterad C++ maste ge FAILED (--trasig-fixtur)",
        "EJ_KORD far aldrig rapporteras som OVERENS",
        "kanalens eget fel (paket/openplc) far inte klassas som "
        "motoroenighet - se icke_ascii (ascii-mur i paket.kompilera)",
    ),
    "kraver": ("openplc",),
    "matningar": ("M-108",),
}


def full_kalla(post, kalla):
    namn, _grupp, kropp, dekl, prolog = post
    if kropp is None:
        return prolog
    return kalla(kropp, dekl, prolog)


def lager_a(post, kalla, strucpp_paket, byggrot):
    """Lokal dom: vart lager + STruC++ compile-API. Inget nat."""
    namn = post[0]
    text = full_kalla(post, kalla)
    try:
        rapport = validera(text)
        var_ok = bool(rapport.ok)
        var_fel = None if var_ok else str(rapport)[:300]
    except Exception as fel:  # grinden kraschade i stallet for att doma
        return {"namn": namn, "var": None, "var_fel": "KRASCH: %r" % fel,
                "strucpp": None, "strucpp_fel": None}
    kat = os.path.join(byggrot, namn)
    try:
        P.kompilera(text, kat, strucpp_paket)
        return {"namn": namn, "var": var_ok, "var_fel": var_fel,
                "strucpp": True, "strucpp_fel": None}
    except (P.Byggfel, UnicodeEncodeError, OSError) as fel:
        return {"namn": namn, "var": var_ok, "var_fel": var_fel,
                "strucpp": False, "strucpp_fel": str(fel)[:300]}


def bygg_zip_for_openplc(post, kalla, strucpp_paket, runtime_include,
                         byggrot):
    """Full kalla + CONFIGURATION -> projekt.zip. Returnerar zipsokvag."""
    namn = post[0]
    text = full_kalla(post, kalla)
    if not text.strip():
        raise P.Byggfel("tom kalla (ingen_pou): inget att bygga")
    try:
        text.encode("ascii")
    except UnicodeEncodeError as fel:
        raise P.Byggfel("icke-ascii i kalla, paket.kompilera skriver ascii: %s"
                        % fel)
    conf = text + P.konfigurationstext("Main", intervall=P.TASKINTERVALL)
    kat = os.path.join(byggrot, namn + "_plc")
    zipvag, _ = P.bygg_projekt(conf, kat, strucpp_paket, runtime_include,
                               opcua_konfig=None)
    return zipvag


def lager_b_ett(post, kalla, klient, strucpp_paket, runtime_include,
                byggrot):
    """Ladda upp ETT fall, las tillbaka verdict. Returnerar dict."""
    namn = post[0]
    try:
        zipvag = bygg_zip_for_openplc(post, kalla, strucpp_paket,
                                      runtime_include, byggrot)
    except P.Byggfel as fel:
        return {"namn": namn, "openplc": None,
                "skal": "byggdes inte lokalt: %s" % str(fel)[:200]}
    try:
        klient.ladda_upp(zipvag)
        dom = klient.vanta_pa_kompilering(tidsgrans=120.0, paus=1.0)
        return {"namn": namn, "openplc": bool(dom.klar),
                "skal": dom.logg[-500:] if not dom.klar else ""}
    except OpenPlcFel as fel:
        return {"namn": namn, "openplc": False,
                "skal": "OpenPLC-fel: %s" % str(fel)[:500]}


def klassificera(rad, STRANGARE, LATTARE):
    """Klasser. EJ_KORD ar bara for fall dar en sida som BORDE ha korts inte
    gjorde det (krasch, uppladdningsfel). Fall dar bada motor 1+2 avvisar har
    inget att ladda upp - det ar ingen utebliven korning utan en tom fraga -
    och de far egna klasser sa att de aldrig rapporteras som OVERENS men
    inte heller som fel. Samma sak for LATTARE: frontenden avvisar fore
    backend, sa runtimens dom ar entailed, inte matt."""
    namn = rad["namn"]
    v, s, o = rad.get("var"), rad.get("strucpp"), rad.get("openplc")
    if v is None or (o is None and s is None):
        return "EJ_KORD"
    if o is None:
        if v is False and s is False:
            return "TVAFALL"
        if v is True and s is False:
            return "LATTARE_OPROVAD"
        if v is False and s is True:
            return "STRANGARE_OPROVAD"
        return "EJ_KORD"
    if v == o:
        return "OVERENS"
    if not v and o:
        return ("STRANGARE_BEKRAFTAD" if namn in STRANGARE
                else "NY_STRANGARE")
    if v and not o:
        return ("HAL_BEKRAFTAD" if namn in LATTARE else "NYTT_HAL")
    return "EJ_KORD"


def val_delmangd(fall, spec):
    """'0/3' -> var tredje fall med start 0. 'alla' -> allt."""
    if spec in (None, "", "alla"):
        return list(fall)
    i, _, n = spec.partition("/")
    return [f for k, f in enumerate(fall) if k % int(n) == int(i)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bas", default="https://127.0.0.1:18444")
    ap.add_argument("--anvandare", default="vcassist")
    ap.add_argument("--losenord", default="vcassist")
    ap.add_argument("--strucpp-paket", required=True)
    ap.add_argument("--runtime-include", default=None)
    ap.add_argument("--byggkatalog", default=None)
    ap.add_argument("--del", dest="delmangd", default="alla",
                    help="'0/3' etc, eller 'alla'")
    ap.add_argument("--grupp", default=None,
                    help="begransa till svepgrupp, t.ex. 'block'")
    ap.add_argument("--no-upload", action="store_true",
                    help="endast lager A (inget nat, ingen container)")
    ap.add_argument("--trasig-fixtur", action="store_true",
                    help="ladda upp ett saboterat arkiv och krav FAILED. "
                         "Utan den vore verdict-mattningen en grind som inte "
                         "kan falla.")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    FALL, kalla, STRANGARE, LATTARE = _las_svep()
    fall = val_delmangd(FALL, a.delmangd)
    if a.grupp:
        fall = [f for f in fall if f[1] == a.grupp]
    print("fall i denna korning: %d av %d" % (len(fall), len(FALL)))

    byggrot = a.byggkatalog or tempfile.mkdtemp(prefix="m108_svep_")
    os.makedirs(byggrot, exist_ok=True)

    # ---- lager A: lokalt, parallellt ----
    t0 = time.time()
    rader = {}
    # (ThreadPoolExecutor.map over slumpvis ordning ar ok: dict keyas pa namn)
    def _a(p):
        return lager_a(p, kalla, a.strucpp_paket, byggrot)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for rad in pool.map(_a, fall):
            rader[rad["namn"]] = rad
    print("lager A klart: %d fall pa %.0f s" % (len(rader), time.time() - t0))

    def _trasig_fixtur(klient):
        """Saboterad C++ maste ge FAILED. Annars mater vi inte kompilering."""
        import zipfile
        post = next(p for p in FALL if p[0] == "tilldelning")
        zipvag = bygg_zip_for_openplc(post, kalla, a.strucpp_paket,
                                      a.runtime_include, byggrot)
        trasig = os.path.join(byggrot, "trasig.zip")
        with zipfile.ZipFile(zipvag) as zin, \
                zipfile.ZipFile(trasig, "w",
                                compression=zipfile.ZIP_DEFLATED) as zut:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.endswith(".cpp"):
                    data += b"\nTHIS IS NOT C++;\n"
                zut.writestr(info, data)
        klient.ladda_upp(trasig)
        try:
            klient.vanta_pa_kompilering(tidsgrans=120.0, paus=1.0)
        except OpenPlcFel:
            print("trasig fixtur: saboterat arkiv foll som vantat")
            return True
        print("FEL: saboterat arkiv ACCEPTERADES - verdict-mattningen mater "
              "inte kompilering.")
        return False

    # ---- lager B: mot containern, seriellt (ett program i taget) ----
    if not a.no_upload:
        if not a.runtime_include:
            print("FEL: lager B kraver --runtime-include")
            return 2
        try:
            klient = OpenPlcV4(a.bas, a.anvandare, a.losenord,
                               tillat_osignerat=True)
            print("runtime: %s status: %s"
                  % (klient.version(), klient.status()))
        except OpenPlcFel as fel:
            print("FEL: OpenPLC svarar inte: %s" % fel)
            print("En OpenPLC som inte svarar far aldrig ge tyst gront.")
            return 1
        if a.trasig_fixtur:
            return 0 if _trasig_fixtur(klient) else 1
        post_av_namn = {p[0]: p for p in fall}
        for k, namn in enumerate(sorted(post_av_namn)):
            rad = lager_b_ett(post_av_namn[namn], kalla, klient,
                              a.strucpp_paket, a.runtime_include, byggrot)
            rader[namn].update(rad)
            if (k + 1) % 25 == 0:
                print("  ... %d/%d uppladdade" % (k + 1, len(post_av_namn)))
        # ingen_pou ar ingen trasig fixtur: kropp="" ger ett syntaktiskt
        # giltigt tomt PROGRAM Main som bada motor 1+2 godtar (svepet: OVERENS).
        # Att OpenPLC ocksa godtar det ar vantat. FAILED-vagen bevisas av
        # --trasig-fixtur (saboterad C++), som redan har fallt som vantat.

    for rad in rader.values():
        rad["klass"] = klassificera(rad, STRANGARE, LATTARE)

    klasser: dict = {}
    for rad in rader.values():
        klasser[rad["klass"]] = klasser.get(rad["klass"], 0) + 1
    print("klasser: %s" % json.dumps(klasser, sort_keys=True))
    for rad in sorted(rader.values(), key=lambda r: r["namn"]):
        if rad["klass"] not in ("OVERENS", "STRANGARE_BEKRAFTAD",
                                "HAL_BEKRAFTAD", "TVAFALL",
                                "LATTARE_OPROVAD", "STRANGARE_OPROVAD"):
            print("  %-36s %s" % (rad["namn"], rad["klass"]))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"bankpost": BANKPOST, "fall": rader,
                       "klasser": klasser}, fh, indent=2, ensure_ascii=False,
                      sort_keys=True)

    # Exit: EJ_KORD eller nya avvikelser = skarp signal, aldrig tyst gront.
    if klasser.get("EJ_KORD"):
        print("EJ_KORD finns: ena sidan kordes inte. Inte overens.")
        return 1
    if klasser.get("NY_STRANGARE") or klasser.get("NYTT_HAL"):
        print("NYA avvikelser: kraver IEC-dom i steg 3.")
        return 1
    print("INGA nya avvikelser i denna delmangd.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
