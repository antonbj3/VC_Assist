#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-119: kan en sprakmodell hitta det den behover - matt BRETT, per frageslag.

Tre matningar har provat uppslagen i var sitt horn. M-84 matte att API-uppslag
bytte modellens ordforrad fran 13 till 32 namn och namngav fyra hal. M-85 matte
komponentdatabladet: 14 % av 82 383 egenskaper deklarerar en storhet. M-96
matte enskott och fann att hela effekten satt i EN uppgift.

Ingen har fragat brett: FINNS SVARET PA PLATS, FOR VARJE SORTS FRAGA modellen
faktiskt staller?

Den har korningen bygger en fragekorpus UR REPOTS EGNA KALLOR - aldrig ur
fantasin - staller varje fraga mot de levererade uppslagsverktygen langs exakt
den vag en modell gar (underprocess mot tests/protocol/stod/slaupp.py), och
klassar varje svar i fyra klasser:

    SVAR       fragan besvaras, med varde OCH harkomst
    HALVT      nagot kommer tillbaka, men utan enhet, utan kalla, eller tvetydigt
    SAKNAS     verktyget sager arligt att det inte vet
    TYST FEL   verktyget svarar nagot som SER UT som ett svar men inte ar det

Den sista klassen ar hela poangen. Ett `MaxPayload = 0` utan enhet ar ett tyst
fel; ett arligt SAKNAS ar det inte. M-84 matte samma asymmetri fran andra
hallet: uppslagen som svarade SAKNAS andrade koden mest.

TACKNINGEN RAPPORTERAS PER FRAGESORT, aldrig som en summa. Det ar M-96:s
lardom: summan 6 av 20 dolde att alla sex satt i en enda uppgift.

Startar INTE Visual Components. Fragor som kraver ett korande VC klassas
KRAVER_VC och rors inte.

    nice -n 19 ionice -c3 python3 tests/protocol/kor_kunskapstackning.py
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "de levererade uppslagsverktygen svarar pa en matt andel av de fragor "
        "en modell faktiskt staller nar den bygger en cell, och andelen ar "
        "OLIKA STOR per frageslag - namn och URI:er besvaras nastan alltid, "
        "medan enheter, signalkartor och standarder inte besvaras alls.",
    "under_prov": (
        "tests/protocol/stod/slaupp.py",
        "svc/vc_assist_svc/api_index.py",
        "svc/vc_assist_svc/katalogsok.py",
        "svc/vc_assist_svc/katalogindex.py",
        "svc/vc_assist_svc/komponentdatablad.py",
        "svc/vc_assist_svc/verktyg/kunskap.py",
    ),
    "facit":
        "for varje fraga: vilken av klasserna SVAR, HALVT, SAKNAS och TYST FEL "
        "svaret hor till, och for de fragor som har ett oberoende varde "
        "(bankens katalogindex, stamplat PUBLICERAD_SPEC ur tillverkarens "
        "datablad) dessutom om verktygets varde motsager det",
    "facitkalla":
        "Fragorna harleds mekaniskt ur tre kallor som ligger UTANFOR "
        "under_prov och skrevs fore verktygen: bankens 63 uppgifter "
        "(prompt, scene.components, control.signals, fysik, expect.lines, "
        "failure_modes, scenarios), personaspecens 228 arbetssteg med sin "
        "Kraver-kolumn, och de oppna punkter M-84 och M-85 skrivit ut. "
        "De oberoende VARDENA kommer ur bank/katalog_index.json, vars poster "
        "bar stampeln PUBLICERAD_SPEC = tillverkarens publicerade datablad.",
    "facitkalla_filer": (
        "bank/uppgifter",
        "bank/katalog_index.json",
        "docs/spec/48_personaprofiler.md",
        "docs/matningar/M-84_uppslagen_bytte_ordforrad_inte_radantal.md",
        "docs/matningar/M-85_komponentdatabladet.md",
    ),
    "trasiga_fall": (
        "ett svar som namnger en ANNAN symbol an den som fragades far aldrig "
        "raknas som SVAR - det ar HALVT, for verktyget sager samtidigt "
        "'anvand namnet exakt som det star'",
        "ett tal utan deklarerad enhet far aldrig raknas som SVAR",
        "ett biblioteksvarde som MOTSAGER bankens PUBLICERAD_SPEC (rackvidd "
        "0 mm for en robot vars datablad sager 901 mm) maste klassas TYST FEL, "
        "aldrig SVAR och aldrig SAKNAS",
        "en fritextsokning som ger traffar dar ingen traff bar sokordet maste "
        "klassas TYST FEL, inte SVAR",
        "en fraga som kraver ett korande VC far inte raknas i tackningens "
        "namnare - den redovisas i egen kolumn",
    ),
    "kraver": ("vc",),
    "matningar": ("M-119",),
}

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, OrderedDict

HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(HAR, "..", ".."))
SLAUPP = os.path.join(ROT, "tests", "protocol", "stod", "slaupp.py")
UTKATALOG = os.path.join(ROT, "docs", "matningar")

SVAR, HALVT, SAKNAS, TYST = "SVAR", "HALVT", "SAKNAS", "TYST_FEL"
KLASSER = (SVAR, HALVT, SAKNAS, TYST)


# ===================================================================== fragan

class Fraga(object):
    """En fraga, dess harkomst, och det anrop en modell skulle gora."""

    __slots__ = ("id", "sort", "text", "kalla", "verktyg", "arg", "facit",
                 "kraver_vc", "svar", "klass", "regel", "notering", "sekunder")

    def __init__(self, fid, sort, text, kalla, verktyg=None, arg=None,
                 facit=None, kraver_vc=False):
        self.id = fid
        self.sort = sort
        self.text = text
        self.kalla = kalla
        self.verktyg = verktyg
        self.arg = arg
        self.facit = facit or {}
        self.kraver_vc = kraver_vc
        self.svar = None
        self.klass = None
        self.regel = None
        self.notering = None
        self.sekunder = None

    def som_dict(self):
        return {
            "id": self.id, "sort": self.sort, "fraga": self.text,
            "kalla": self.kalla, "verktyg": self.verktyg, "arg": self.arg,
            "kraver_vc": self.kraver_vc, "klass": self.klass,
            "regel": self.regel, "notering": self.notering,
            "sekunder": self.sekunder,
        }


SORTER = OrderedDict([
    ("S1_api_namn",      "API-namn och signatur"),
    ("S2_typyta",        "Typens hela yta"),
    ("S3_konstant",      "Konstantnamn (VC_*)"),
    ("S4_bank_uri",      "bank://-URI:er"),
    ("S5_bibliotek",     "Finns komponenten i biblioteket"),
    ("S5b_omtag",        "Samma, andra forsoket utan tillverkarprefix"),
    ("S6_egenskap",      "Komponentens egenskaper och enheter"),
    ("S7_signalkarta",   "Signalkartans namn och riktning"),
    ("S8_geometri",      "Geometri och matt"),
    ("S8b_omtag",        "Samma, andra forsoket utan tillverkarprefix"),
    ("S9_standard",      "Standardhanvisningar"),
    ("S10_grindregel",   "Grindarnas regler"),
    ("S11_vc_dok",       "VC:s beteende, dokumenterat"),
    ("S12_vc_kor",       "VC:s beteende, kraver korande VC"),
])


# ================================================================ harledning
#
# Varje fraga ska ga att spara till en rad i en fil som skrevs fore verktyget.
# Ingen fraga hittas pa.

# Bankens matt bar sin enhet i FALTNAMNET. Det ar bankens egen disciplin och
# den ar oberoende av uppslagsverktygen; darfor duger den som facit for fragan
# "bar svaret en enhet". Nyckelordet ar det ENGELSKA ord ett biblioteksdatablad
# skulle anvanda for samma storhet.
ENHETSFALT = OrderedDict([
    ("rackvidd_mm", ("reach", "mm")),
    ("nyttolast_kg", ("payload", "kg")),
    ("hastighet_mps", ("speed", "m/s")),
    ("hastighet_mmin", ("speed", "m/min")),
    ("bredd_mm", ("width", "mm")),
    ("massa_kg", ("mass", "kg")),
    ("anslag_s", ("stroke", "s")),
    ("slag_s", ("stroke", "s")),
    ("svarstid_ms", ("response", "ms")),
    ("lyfthojd_mm", ("lift", "mm")),
    ("l_mm", ("length", "mm")),
    ("b_mm", ("width", "mm")),
    ("h_mm", ("height", "mm")),
])


def _bankuppgifter():
    kat = os.path.join(ROT, "bank", "uppgifter")
    ut = []
    for namn in sorted(os.listdir(kat)):
        if namn.endswith(".json"):
            with open(os.path.join(kat, namn), encoding="utf-8") as f:
                ut.append((namn, json.load(f)))
    return ut


def _bankkatalog():
    with open(os.path.join(ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        return json.load(f)


_RAD = re.compile(r"^\|\s*(\d+)\s*\|")
_BAKTICK = re.compile(r"`([^`]+)`")


def _personarader():
    """(profil, nr, arbetssteg, verkan, kraver-token-lista, tackt-av)."""
    sok = os.path.join(ROT, "docs", "spec", "48_personaprofiler.md")
    profil = None
    ut = []
    with open(sok, encoding="utf-8") as f:
        for radnr, ln in enumerate(f, 1):
            m = re.match(r"## (P\d) ", ln)
            if m:
                profil = m.group(1)
            if _RAD.match(ln):
                c = [x.strip() for x in ln.strip().strip("|").split("|")]
                if len(c) >= 5:
                    ut.append((profil, c[0], c[1], c[2],
                               _BAKTICK.findall(c[3]), c[4], radnr))
    return ut


def harled():
    """Hela korpusen. Returnerar en lista av Fraga i deklarerad ordning."""
    fragor = []
    rader = _personarader()
    uppg = _bankuppgifter()
    katalog = _bankkatalog()
    poster = {p["uri"]: p for p in katalog["poster"]}

    # ---- S1, S2, S3: personaspecens Kraver-kolumn -------------------------
    # 228 arbetssteg, skrivna av en manniska som namnger vad steget VILAR PA.
    # Tre former i kolumnen ger tre frageslag; UI:, .NET: och TJANST: hor inte
    # till VC:s Python-yta och ar darfor inte fragor till uppslagsverktyget.
    sedda_api, sedda_typ, sedda_konst = OrderedDict(), OrderedDict(), OrderedDict()
    for profil, nr, steg, verkan, tokens, tackt, radnr in rader:
        for tok in tokens:
            kalla = "48_personaprofiler.md:%d (%s steg %s: %s)" % (
                radnr, profil, nr, steg)
            if tok.startswith((".NET:", "UI:", "TJANST:", "TJÄNST:")):
                continue
            if re.fullmatch(r"VC_[A-Z_0-9]+", tok):
                sedda_konst.setdefault(tok, kalla)
            elif "." in tok:
                sedda_api.setdefault(tok, kalla)
                # vcHelpers ar en MODUL med undermoduler: ytan heter
                # vcHelpers.Robot, inte vcHelpers. Att dela pa forsta punkten
                # hade gett `yta vcHelpers` = SAKNAS, och det hade varit
                # harledningens fel och inte verktygets.
                delar = tok.split(".")
                sedda_typ.setdefault(
                    ".".join(delar[:2]) if delar[0] == "vcHelpers" else delar[0],
                    kalla)
            else:
                sedda_typ.setdefault(tok, kalla)

    for i, (namn, kalla) in enumerate(sedda_api.items(), 1):
        fragor.append(Fraga(
            "S1-%03d" % i, "S1_api_namn",
            "Finns %s, och vilken signatur och returtyp har den?" % namn,
            kalla, "namn", namn, {"vantat_namn": namn}))

    for i, (typ, kalla) in enumerate(sedda_typ.items(), 1):
        fragor.append(Fraga(
            "S2-%03d" % i, "S2_typyta",
            "Vilka medlemmar bar typen %s?" % typ,
            kalla, "yta", typ, {"vantat_namn": typ}))

    for i, (k, kalla) in enumerate(sedda_konst.items(), 1):
        fragor.append(Fraga(
            "S3-%03d" % i, "S3_konstant",
            "Finns konstanten %s, och vad betyder den?" % k,
            kalla, "namn", k, {"vantat_namn": k}))

    # ---- S4: bank://-URI:erna ur scenerna ---------------------------------
    # Varje uri som nagon av de 63 uppgifterna faktiskt bygger sin scen av.
    urier = OrderedDict()
    for fil, d in uppg:
        for c in d["scene"]["components"]:
            urier.setdefault(c["uri"], "%s (%s roll=%s)" % (fil, d["task_id"],
                                                            c["role"]))
    for i, (uri, kalla) in enumerate(urier.items(), 1):
        p = poster.get(uri)
        fragor.append(Fraga(
            "S4-%03d" % i, "S4_bank_uri",
            "Vad ar %s, och vilka matt bar posten?" % uri,
            "bank/uppgifter/" + kalla, "bank", uri,
            {"vantad_uri": uri, "bankpost": p}))

    # ---- S5: finns bankens komponent i det installerade biblioteket -------
    # Fragan modellen staller nar den ska LADDA komponenten. M-85 matte att
    # banken och biblioteket inte delar vokabular; har fragas varje post.
    for i, (uri, kalla) in enumerate(urier.items(), 1):
        p = poster.get(uri)
        if not p:
            continue
        fragor.append(Fraga(
            "S5-%03d" % i, "S5_bibliotek",
            "Vilken komponent i det installerade biblioteket motsvarar "
            "'%s' (%s)?" % (p["namn"], uri),
            "bank/katalog_index.json (%s)" % uri, "komponentsok", p["namn"],
            {"bankpost": p, "uri": uri}))

    # ---- S8: bankens matt genom verktyget ---------------------------------
    # S6 (egenskapernas ENHETER) byggs i ett ANDRA steg, ur S5:s svar: en
    # modell far databladet genom att FORST soka i biblioteket, precis som
    # verktygets egen notering sager ("Sok med search_installed_library
    # forst"). Att fraga databladet med BANKENS namn hade matt
    # vokabularglappet en gang till (M-85 gjorde det) i stallet for enheterna.
    # S8: bankens matt mot verktygets. Samma falt, men fragan ar VARDET och
    # facit ar bankens PUBLICERAD_SPEC.
    n8 = 0
    for uri, kalla in urier.items():
        p = poster.get(uri)
        if not p or p.get("stampel") != "PUBLICERAD_SPEC":
            continue
        for falt in ("rackvidd_mm", "nyttolast_kg"):
            if falt not in p:
                continue
            n8 += 1
            fragor.append(Fraga(
                "S8-%03d" % n8, "S8_geometri",
                "Hur stor ar %s for %s?" % (falt, p["namn"]),
                "bank/katalog_index.json (%s.%s = %s, stampel "
                "PUBLICERAD_SPEC)" % (uri, falt, p[falt]),
                "komponentsok", p["namn"],
                {"bankfalt": falt, "banksvar": p[falt], "uri": uri,
                 "bankpost": p}))

    # Bankens EGNA matt, fragade genom bank-URI:n. Facit ar samma rad, men
    # fragan ar en annan: bar SVARET en enhet?
    n8b = n8
    for uri, kalla in list(urier.items()):
        p = poster.get(uri)
        if not p:
            continue
        for falt in ENHETSFALT:
            if falt in p:
                n8b += 1
                fragor.append(Fraga(
                    "S8-%03d" % n8b, "S8_geometri",
                    "Vilket varde OCH vilken enhet ger banken for %s pa %s?"
                    % (falt, p["namn"]),
                    "bank/katalog_index.json (%s.%s)" % (uri, falt),
                    "bank", uri,
                    {"bankfalt": falt, "banksvar": p[falt],
                     "bankenhet": ENHETSFALT[falt][1], "kravd_enhet": True}))
                break          # ett matt per post racker for enhetsfragan

    # ---- S7: signalkartan --------------------------------------------------
    # Bankens control.signals ar OPC UA-variabelnamn. Fragan modellen staller
    # ar VILKEN komponent i scenen som bar signalen och vilken VC-typ den far.
    n7 = 0
    sedda_sig = set()
    for fil, d in uppg:
        sigs = d["control"]["signals"]
        val = []
        for s in sigs:
            if s["dir"] == "in" and not val:
                val.append(s)
        for s in sigs:
            if s["type"] != "bool":
                val.append(s)
                break
        for s in val:
            if s["name"] in sedda_sig:
                continue
            sedda_sig.add(s["name"])
            n7 += 1
            fragor.append(Fraga(
                "S7-%03d" % n7, "S7_signalkarta",
                "Vilken komponent i scenen bar signalen %s (%s, %s), och "
                "vilken VC-signaltyp far den?"
                % (s["name"], s["dir"], s["type"]),
                "bank/uppgifter/%s (control.signals)" % fil,
                "bank", s["name"],
                {"signal": s["name"], "dir": s["dir"], "typ": s["type"]}))

    # ---- S9: standardhanvisningar -----------------------------------------
    STD = re.compile(r"\b(?:ISO|IEC|EN|DIN|ANSI|VDI|VDA|RIA)\s?\d{3,5}"
                     r"(?:-\d+)?(?::\d{4})?")
    std = OrderedDict()
    for fil, d in uppg:
        txt = json.dumps(d, ensure_ascii=False)
        for m in STD.findall(txt):
            std.setdefault(m.strip(), "bank/uppgifter/%s (%s)"
                           % (fil, d["task_id"]))
    for i, (s, kalla) in enumerate(std.items(), 1):
        fragor.append(Fraga(
            "S9-%03d" % i, "S9_standard",
            "Vad kraver %s av cellen, och var star kravet?" % s,
            kalla, "sok", s.split(":")[0], {"standard": s}))

    # ---- S10: grindarnas regler --------------------------------------------
    # expect.lines ar de rader ogat MASTE skriva. Fragan modellen staller ar
    # vad raden betyder och vilken grind som skriver den.
    mallar = OrderedDict()
    for fil, d in uppg:
        for L in (d["expect"].get("lines") or []):
            nyckel = (L["section"], L["template"].split()[0])
            mallar.setdefault(nyckel, ("bank/uppgifter/%s (expect.lines: %s)"
                                       % (fil, L["template"])))
        for L in (d["expect"].get("forbidden_lines") or []):
            nyckel = (L["section"], L["template"].split()[0])
            mallar.setdefault(nyckel, ("bank/uppgifter/%s (forbidden_lines: "
                                       "%s)" % (fil, L["template"])))
    for i, ((sektion, ord0), kalla) in enumerate(mallar.items(), 1):
        fragor.append(Fraga(
            "S10-%03d" % i, "S10_grindregel",
            "Vad betyder raden %s i sektionen %s, och vilken grind skriver "
            "den?" % (ord0, sektion),
            kalla, "sok", ord0, {"sektion": sektion, "nyckelord": ord0}))
    # Grindnamnen ur expect.gate och must_pass.
    grindar = OrderedDict()
    for fil, d in uppg:
        g = d["expect"].get("gate")
        if g:
            grindar.setdefault(g, "bank/uppgifter/%s (expect.gate)" % fil)
        for mp in (d["expect"].get("must_pass") or []):
            grindar.setdefault(mp, "bank/uppgifter/%s (expect.must_pass)" % fil)
    for j, (g, kalla) in enumerate(grindar.items(), i + 1):
        fragor.append(Fraga(
            "S10-%03d" % j, "S10_grindregel",
            "Vad ar grinden/sektionen %s och vilken regel domer den?" % g,
            kalla, "sok", g, {"grind": g}))

    # ---- S11: VC:s beteende sa som DOKUMENTATIONEN sager det ---------------
    # Harleds ur de symboler personaspecen sager att ett steg VILAR PA, plus
    # de namn M-84 skrev ut som osakra. Fragan ar: sager beskrivningen vad som
    # hander i grensfallet, eller bara vad metoden heter?
    KANTFALL = OrderedDict([
        ("vcNode.findBehavioursByType",
         "vad returneras om komponenten inte bar nagon behaviour av typen?"),
        ("vcComponent.getProperty",
         "vad returneras om egenskapen inte finns?"),
        ("vcApplication.load",
         "vad returneras om URI:n inte gar att ladda?"),
        ("vcApplication.findComponent",
         "vad returneras om namnet inte finns i layouten?"),
        ("vcSimInterface.canConnect",
         "vad svarar den om granssnitten ar av olika sort?"),
        ("vcSimInterface.connect",
         "vad hander om granssnittet redan ar kopplat?"),
        ("vcApplication.connectComponents",
         "vad hander om ingen matchande granssnittspar finns?"),
        ("vcSignal.connect",
         "vad hander om signalen redan ar kopplad till en annan?"),
        ("vcRobotController.moveImmediate",
         "vad hander om ledvardet ligger utanfor ledens granser?"),
        ("vcMotionTarget.getConfigWarnings",
         "vad betyder en tom lista - att punkten gar att na?"),
        ("vcSimulation.run",
         "vad hander om den anropas medan simuleringen redan gar?"),
        ("vcSimulation.reset",
         "aterstalls signalvarden, eller bara komponentlagen?"),
        ("vcCollisionDetector.testAllCollisions",
         "vad returneras nar ingen krock finns?"),
        ("vcNode.measureDistance",
         "vad returneras om kropparna overlappar?"),
        ("vcComponent.saveState",
         "vad ingar i tillstandet - egenskaper, lage, signaler?"),
        ("vcBooleanSignalMap.trySetDirection",
         "vad returneras om riktningen inte gar att satta?"),
        ("vcTransportSystem.findSolution",
         "vad returneras om ingen vag finns?"),
        ("vcStatistics.Utilization",
         "vilken tidsbas raknas utnyttjandet over?"),
        ("vcProductTypeManager.createProductType",
         "vad hander om typnamnet redan finns?"),
        ("vcExecutor.callRoutine",
         "blockerar anropet tills rutinen ar klar?"),
    ])
    for i, (namn, fragan) in enumerate(KANTFALL.items(), 1):
        kalla = sedda_api.get(namn) or ("M-84/M-85 oppen punkt: %s" % namn)
        fragor.append(Fraga(
            "S11-%03d" % i, "S11_vc_dok",
            "%s - %s" % (namn, fragan),
            kalla, "namn", namn,
            {"vantat_namn": namn, "kantfall": fragan}))

    # ---- S12: fragor som KRAVER ett korande VC ----------------------------
    # Ur bankens scenarier som inte ar normaldrift, och ur failure_modes.
    # De ror vad som HANDER i en korande scen; ingen filläsning avgor dem.
    n12 = 0
    for fil, d in uppg:
        for sc in d.get("scenarios") or []:
            if sc.get("typ") == "normaldrift":
                continue
            n12 += 1
            fragor.append(Fraga(
                "S12-%03d" % n12, "S12_vc_kor",
                "Vad gor scenen om %s?" % sc["beskrivning"],
                "bank/uppgifter/%s (scenarios.%s)" % (fil, sc["id"]),
                None, None, {"scenario": sc["id"]}, kraver_vc=True))
    return fragor


# =================================================================== korning

# Ett och samma (verktyg, argument) ger samma svar varje gang - verktyget ar
# rent och laser bara filer pa disk. 794 fragor blir 662 distinkta anrop, och
# de 123 tunga (biblioteket) blir 123 i stallet for 182. Cachen andrar inte ett
# enda svar; den betalar inte for samma svar tva ganger.
def harled_omtag(fragor):
    """Andra forsoket: samma soktrang utan tillverkarprefixet.

    En modell som far noll traffar soker om med en kortare strang. Det ar inte
    en tillatelse att fuska - det ar vad M-85 matte att skillnaden BESTAR I:
    banken skriver "ABB IRB 1200-5/0.9", biblioteket "IRB 1200-5/0.9". Passet
    mater darfor tva saker: att forsta forsoket faller, och hur mycket det
    andra hamtar hem.
    """
    ut = []
    n = 0
    for f in fragor:
        if f.verktyg != "komponentsok" or f.klass != SAKNAS:
            continue
        delar = f.arg.split(" ", 1)
        if len(delar) < 2 or len(delar[1]) < 4:
            continue
        n += 1
        sort = "S5b_omtag" if f.sort == "S5_bibliotek" else "S8b_omtag"
        ny_f = Fraga(
            f.id + "b", sort,
            f.text + "  [andra forsoket, utan '%s']" % delar[0],
            f.kalla + " (omtag efter %s)" % f.id,
            "komponentsok", delar[1], dict(f.facit))
        ut.append(ny_f)
    return ut


def harled_steg2(fragor):
    """S6: egenskaperna och deras enheter, fragade om DEN komponent S5 fann."""
    poster = {p["uri"]: p for p in _bankkatalog()["poster"]}
    ut = []
    n6 = 0
    sedda = set()
    for f in fragor:
        if f.sort not in ("S5_bibliotek", "S5b_omtag"):
            continue
        if f.klass != SVAR or not f.svar:
            continue
        if f.facit["uri"] in sedda:
            continue
        p = poster[f.facit["uri"]]
        platt = _plattnamn(p["namn"])
        traff = [t for t in (f.svar.get("traffar") or [])
                 if _samma_komponent(platt, t.get("namn"))]
        if not traff:
            continue
        biblioteksnamn = traff[0]["namn"]
        sedda.add(f.facit["uri"])
        for falt, (nyckelord, enhet) in ENHETSFALT.items():
            if falt not in p:
                continue
            n6 += 1
            ut.append(Fraga(
                "S6-%03d" % n6, "S6_egenskap",
                "Vilken egenskap pa '%s' bar %s, och vilken storhet "
                "deklarerar den?" % (biblioteksnamn, falt),
                "bank/katalog_index.json (%s.%s), via biblioteksstraffen i %s"
                % (f.facit["uri"], falt, f.id),
                "komponent", biblioteksnamn,
                {"nyckelord": nyckelord, "banksvar": p[falt],
                 "bankenhet": enhet, "bankfalt": falt, "uri": f.facit["uri"]}))
    return ut


_CACHE = {}


def kor_ett(f):
    """Ett anrop langs samma vag en modell gar: underprocess mot slaupp.py."""
    nyckel = (f.verktyg, f.arg)
    if nyckel in _CACHE:
        svar, rc, parsfel, sek = _CACHE[nyckel]
        f.sekunder = sek
        return svar, rc, parsfel
    t0 = time.time()
    k = subprocess.run(
        [sys.executable, SLAUPP, f.verktyg, f.arg],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=ROT, timeout=900)
    f.sekunder = round(time.time() - t0, 3)
    ut = k.stdout.decode("utf-8", "replace")
    try:
        svar, parsfel = json.loads(ut), None
    except Exception as fel:                                   # noqa: BLE001
        svar = None
        parsfel = "%s: %s" % (type(fel).__name__, str(fel)[:200])
    _CACHE[nyckel] = (svar, k.returncode, parsfel, f.sekunder)
    return svar, k.returncode, parsfel


# ================================================================= domandet
#
# Reglerna star med namn sa att varje klassning gar att sla upp och bestrida.

_ORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[a-z]+|[0-9]+")


def _segment(text):
    """Namnets ord, delat pa punkt, camelCase, siffror och skiljetecken.

    `vcHelpers.Robot.traceOff` -> {vc, helpers, robot, trace, off}. Ordet
    "race" ar alltsa INTE ett segment i det namnet, aven om det ar en
    delstrang i det.
    """
    return {m.group(0).lower() for m in _ORD.finditer(text or "")}


def _plattnamn(text):
    """Namnet utan skiljetecken och skiftlage. 'ABB IRB 1200-5/0.9' -> abbirb120050 9."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _samma_komponent(banknamn_platt, biblioteksnamn):
    """Ar biblioteksposten den bankposten menar?

    M-85 matte att skillnaden ar tillverkarprefixet: banken skriver
    "ABB IRB 1200-5/0.9", biblioteket "IRB 1200-5/0.9". Den ena strangen ar
    alltsa en delstrang av den andra. Kravet att den kortare ska vara minst
    sex tecken haller "AGV" fran att matcha allt.
    """
    b = _plattnamn(biblioteksnamn)
    if not b or not banknamn_platt:
        return False
    if b == banknamn_platt:
        return True
    kort, lang = sorted((b, banknamn_platt), key=len)
    return len(kort) >= 6 and kort in lang


def _harkomst_finns(sym):
    return bool(sym.get("harkomst"))


def dom(f, svar, rc, parsfel):
    """(klass, regel, notering). Ingen regel far vara en asikt utan namn."""
    if parsfel is not None:
        if rc == 0:
            return TYST, "R0_OPARSBART_MED_NOLLA",\
                "verktyget gav returkod 0 men utdata ar inte JSON: %s" % parsfel
        return SAKNAS, "R0_FEL_MED_KOD", "returkod %d, %s" % (rc, parsfel)

    v = f.verktyg

    # ---- namn ------------------------------------------------------------
    if v == "namn":
        if not svar.get("found"):
            return SAKNAS, "R1_NAMN_SAKNAS", "forslag: %s" % ", ".join(
                x["name"] for x in (svar.get("forslag") or [])[:3])
        symbols = svar.get("symbols") or []
        if not symbols:
            return TYST, "R2_FOUND_UTAN_SYMBOL", "found=true men symbols=[]"
        s = symbols[0]
        namngiven = s.get("full_name") or ""
        if namngiven.lower() != f.arg.lower():
            return HALVT, "R3_ANNAT_NAMN_AN_FRAGAT",\
                "fragade %s, svaret namnger %s (arvd medlem; svaret sager " \
                "inte att den ar arvd, och instruktionen sager 'anvand " \
                "namnet exakt som det star')" % (f.arg, namngiven)
        if not _harkomst_finns(s):
            return HALVT, "R4_UTAN_HARKOMST", "symbolen bar ingen harkomst"
        besk = (s.get("description") or "").strip()
        if not besk:
            return HALVT, "R5_UTAN_BESKRIVNING",\
                "namnet finns men ingenting sager vad det gor"
        if s.get("sort") == "metod" and not s.get("signature"):
            return HALVT, "R6_METOD_UTAN_SIGNATUR", "signature=null"
        # Kantfallsfragorna (S11) stalls om ett GRENSFALL. En beskrivning som
        # inte bar en villkorssats svarar inte pa den fragan.
        if f.sort == "S11_vc_dok":
            villkor = re.search(
                r"\b(if|otherwise|when|unless|returns None|empty list|"
                r"does not|cannot|fails|invalid)\b", besk, re.I)
            if not villkor:
                return HALVT, "R7_INGEN_VILLKORSSATS",\
                    "beskrivningen sager vad metoden gor, inte vad som hander " \
                    "i grensfallet"
        return SVAR, "R8_EXAKT_MED_HARKOMST", None

    # ---- yta -------------------------------------------------------------
    if v == "yta":
        if not svar.get("found"):
            return SAKNAS, "R10_TYP_SAKNAS", None
        if not (svar.get("medlemmar") or []):
            return TYST, "R11_TYP_UTAN_MEDLEMMAR", "found=true, antal=0"
        return SVAR, "R12_YTA_MED_MEDLEMMAR", "%d medlemmar" % len(
            svar.get("medlemmar") or [])

    # ---- bank ------------------------------------------------------------
    if v == "bank":
        if f.arg.startswith("bank://"):
            if not svar.get("found"):
                return SAKNAS, "R20_URI_SAKNAS", "%d alternativ gavs" % len(
                    svar.get("alternativ") or [])
            post = svar.get("post") or {}
            if post.get("uri") != f.arg:
                return TYST, "R21_ANNAN_URI", "fragade %s, fick %s" % (
                    f.arg, post.get("uri"))
            if f.facit.get("kravd_enhet"):
                matt = post.get("matt") or []
                utan = [m["namn"] for m in matt if m.get("enhet") in (None, "")]
                if not matt:
                    return SAKNAS, "R22_INGA_MATT", None
                if utan:
                    return HALVT, "R23_MATT_UTAN_ENHET",\
                        "utan enhet: %s" % ", ".join(utan)
            return SVAR, "R24_URI_MED_POST", None
        # fritext (S7 signalnamn)
        traffar = svar.get("traffar")
        if traffar is None:
            return TYST, "R25_INGEN_TRAFFLISTA", "svaret bar inget traffalt"
        if not traffar:
            return SAKNAS, "R26_FRITEXT_TOM", None
        ord_ = f.arg.lower()
        bar = [t for t in traffar
               if ord_ in (t.get("namn", "") + " " + t.get("uri", "")).lower()]
        if not bar:
            return TYST, "R27_TRAFFAR_UTAN_SOKORDET",\
                "%d traffar, ingen bar '%s'" % (len(traffar), f.arg)
        return SVAR, "R28_FRITEXT_TRAFF", "%d traffar" % len(traffar)

    # ---- sok -------------------------------------------------------------
    #
    # Verktyget deklarerar SJALVT var traffen kom ifran (`rang`: prefix,
    # delstrang_namn, delstrang_typ, delstrang_beskrivning). Domen anvander den
    # deklarationen i stallet for att gissa:
    #
    #   * ordet ar ett HELT SEGMENT i namnet  -> namnet bar verkligen ordet
    #   * bara en delstrang i namnet          -> "RACE" traffar `traceOn`, och
    #                                            det ser ut som en namntraff
    #   * bara i beskrivningen                -> verktyget sager det sjalvt
    if v == "sok":
        traffar = svar.get("traffar")
        if not traffar:
            return SAKNAS, "R30_SOK_TOM", None
        ord_ = _segment(f.arg)
        segmenttraff = [t for t in traffar
                        if ord_ and ord_ <= _segment(t.get("full_name") or "")]
        namnrang = [t for t in traffar
                    if t.get("rang") in ("exakt", "prefix", "delstrang_namn")]
        namn3 = ", ".join((t.get("full_name") or "") for t in traffar[:3])
        if segmenttraff:
            if f.sort in ("S9_standard", "S10_grindregel"):
                return HALVT, "R34_NAMNTRAFF_FEL_DOMAN",\
                    "%d traffar i VC:s API-index, men fragan galler %s: %s" % (
                        len(traffar),
                        "en standard" if f.sort == "S9_standard"
                        else "ogats rapportrad", namn3)
            return SVAR, "R32_SOKTRAFF", "%d traffar" % len(traffar)
        if namnrang:
            return TYST, "R31_DELSTRANG_I_NAMN",\
                "%d traffar med rang delstrang_namn, men '%s' ar ingen del av " \
                "namnet: %s" % (len(namnrang), f.arg, namn3)
        return HALVT, "R35_ENDAST_BESKRIVNINGSTRAFF",\
            "%d traffar, alla ur beskrivningstext: %s" % (len(traffar), namn3)

    # ---- komponentsok ----------------------------------------------------
    #
    # Bankens namn bar tillverkarprefixet ("ABB IRB 1200-5/0.9"), bibliotekets
    # gor det inte ("IRB 1200-5/0.9"). Det ar M-85:s matning, inte en gissning,
    # och darfor matchas namnen som delstrangar av varandra INNAN nagot varde
    # las. Ett varde last ur fel traff hade varit ett tyst fel i DOMAREN.
    if v == "komponentsok":
        traffar = svar.get("traffar")
        if traffar is None:
            return TYST, "R40_INGEN_TRAFFLISTA", None
        if not traffar:
            return SAKNAS, "R41_BIBLIOTEK_TOMT",\
                "banken och biblioteket delar inte vokabular (M-85)"
        namn = _plattnamn(f.arg)
        kandidat = [t for t in traffar if _samma_komponent(namn, t.get("namn"))]
        namn3 = ", ".join((t.get("namn") or "") for t in traffar[:3])
        if not kandidat:
            return TYST, "R45_TRAFFAR_UTAN_NAMNET",\
                "%d traffar for '%s', ingen ar komponenten: %s" % (
                    len(traffar), f.arg, namn3)
        falt = f.facit.get("bankfalt")
        if falt in ("rackvidd_mm", "nyttolast_kg"):
            vantat = f.facit.get("banksvar")
            # None ar inte noll. Ett falt som saknas ar ett arligt SAKNAS;
            # en NOLLA ar det som ser ut som ett matt varde.
            varden = [t.get(falt) for t in kandidat if t.get(falt) is not None]
            if not varden:
                return SAKNAS, "R43_FALTET_SAKNAS",\
                    "%s ar None eller saknas i biblioteksposten; bankens "\
                    "PUBLICERAD_SPEC sager %s" % (falt, vantat)
            x = varden[0]
            if x in (0, 0.0):
                return TYST, "R42_NOLLA_MOT_PUBLICERAD_SPEC",\
                    "%s = 0 i biblioteket, men bankens PUBLICERAD_SPEC "\
                    "(tillverkarens datablad) sager %s" % (falt, vantat)
            if float(x) != float(vantat):
                return HALVT, "R47_AVVIKER_FRAN_SPEC",\
                    "%s: biblioteket %s, banken %s" % (falt, x, vantat)
            return SVAR, "R44_VARDE_MOT_SPEC", "%s = %s" % (falt, x)
        return SVAR, "R46_BIBLIOTEKSTRAFF", "%d traffar, %d ar komponenten" % (
            len(traffar), len(kandidat))

    # ---- komponent -------------------------------------------------------
    #
    # Regeln som bar sorten: ETT TAL UTAN DEKLARERAD ENHET AR INGET SVAR.
    # Databladet skriver sjalvt ut "storhet saknas" och "ENHET EJ DEKLARERAD",
    # och det ar arligt - men for den som fragar efter en STORHET ar raden
    # halv, inte hel. En NOLLA utan enhet ar varre an halv: den ser ut som ett
    # matt varde (M-107: MaxPayload = 0 i 628 komponenter).
    if v == "komponent":
        if not svar.get("funnet"):
            return SAKNAS, "R50_KOMPONENT_SAKNAS", (svar.get("notering") or "")[:120]
        namn = svar.get("namn") or ""
        blad = svar.get("datablad") or []
        nyckel = (f.facit.get("nyckelord") or "").lower()
        rader = [r for r in blad if nyckel and nyckel in r.lower()]
        if not rader:
            return SAKNAS, "R51_EGENSKAP_SAKNAS",\
                "ingen rad i databladet for '%s' namner '%s'" % (namn, nyckel)
        nakna = [r for r in rader if re.search(r":\s*0(?:[.,]0+)?\s*$", r)
                 and ("ENHET EJ DEKLARERAD" in r or "storhet saknas" in r)]
        if nakna:
            return TYST, "R52_NOLLA_UTAN_ENHET", nakna[0].strip()[:170]
        utan = [r for r in rader
                if "storhet saknas" in r.lower() or "ENHET EJ DEKLARERAD" in r]
        if len(utan) == len(rader):
            return HALVT, "R53_UTAN_STORHET",\
                "%d rad(er) bar '%s', ingen deklarerar storhet: %s" % (
                    len(rader), nyckel, utan[0].strip()[:120])
        return SVAR, "R54_EGENSKAP_MED_STORHET", "%d av %d rad(er) med storhet" % (
            len(rader) - len(utan), len(rader))

    raise AssertionError("odomd verktygssort: %r" % v)


# ================================================================= rapporten

def rapportera(fragor, sekunder):
    per = OrderedDict()
    for nyckel, etikett in SORTER.items():
        rader = [f for f in fragor if f.sort == nyckel]
        c = Counter(f.klass for f in rader if not f.kraver_vc)
        per[nyckel] = {
            "etikett": etikett,
            "antal": len(rader),
            "kraver_vc": sum(1 for f in rader if f.kraver_vc),
            "kord": sum(1 for f in rader if not f.kraver_vc),
            SVAR: c[SVAR], HALVT: c[HALVT], SAKNAS: c[SAKNAS], TYST: c[TYST],
        }
        korda = per[nyckel]["kord"]
        per[nyckel]["andel_svar"] = round(100.0 * c[SVAR] / korda, 1) if korda else None
        per[nyckel]["andel_tyst"] = round(100.0 * c[TYST] / korda, 1) if korda else None
    tysta = [f.som_dict() for f in fragor if f.klass == TYST]
    return {
        "korning": "kor_kunskapstackning.py",
        "matning": "M-119",
        "fragor_totalt": len(fragor),
        "korda": sum(1 for f in fragor if not f.kraver_vc),
        "kraver_vc": sum(1 for f in fragor if f.kraver_vc),
        "sekunder": round(sekunder, 1),
        "per_sort": per,
        "regelrakning": dict(Counter(f.regel for f in fragor if f.regel)),
        "tysta_fel": tysta,
        "alla": [f.som_dict() for f in fragor],
    }


def main():
    t0 = time.time()
    fragor = harled()
    sys.stderr.write("harledde %d fragor ur bank, spec och matningar\n"
                     % len(fragor))
    for i, f in enumerate(fragor, 1):
        if f.kraver_vc:
            f.klass, f.regel = None, "KRAVER_VC"
            continue
        svar, rc, parsfel = kor_ett(f)
        f.svar = svar
        f.klass, f.regel, f.notering = dom(f, svar, rc, parsfel)
        if i % 25 == 0:
            sys.stderr.write("  %d/%d  (%.0f s)\n"
                             % (i, len(fragor), time.time() - t0))
    omtag = harled_omtag(fragor)
    sys.stderr.write("omtag: %d andra forsok utan tillverkarprefix\n"
                     % len(omtag))
    for j, f in enumerate(omtag, 1):
        svar, rc, parsfel = kor_ett(f)
        f.svar = svar
        f.klass, f.regel, f.notering = dom(f, svar, rc, parsfel)
    fragor = fragor + omtag
    steg2 = harled_steg2(fragor)
    sys.stderr.write("steg 2: %d egenskapsfragor ur biblioteksstraffarna\n"
                     % len(steg2))
    for j, f in enumerate(steg2, 1):
        svar, rc, parsfel = kor_ett(f)
        f.svar = svar
        f.klass, f.regel, f.notering = dom(f, svar, rc, parsfel)
        if j % 25 == 0:
            sys.stderr.write("  steg2 %d/%d  (%.0f s)\n"
                             % (j, len(steg2), time.time() - t0))
    fragor = fragor + steg2
    rap = rapportera(fragor, time.time() - t0)
    ut = os.path.join(UTKATALOG, "m119_kunskapstackning.json")
    with open(ut, "w", encoding="utf-8") as f:
        json.dump(rap, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in rap.items()
                      if k not in ("alla", "tysta_fel")},
                     ensure_ascii=False, indent=1))
    print("\nTYSTA FEL: %d" % len(rap["tysta_fel"]))
    for t in rap["tysta_fel"][:40]:
        print("  %-9s %-16s %s\n            %s"
              % (t["id"], t["regel"], t["fraga"][:90], (t["notering"] or "")[:120]))
    print("\nskrev %s" % ut)
    return 0


if __name__ == "__main__":
    sys.exit(main())
