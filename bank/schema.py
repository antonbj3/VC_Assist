# -*- coding: utf-8 -*-
"""Schemat för en bänkuppgift, och lintern som avvisar en uppgift utan facit.

Två saker hålls isär här:

1. **Formen** — vilka fält en uppgift har (docs/spec/81_mallschema.md).
2. **Facit** — vad ögat ska säga (docs/spec/41_ogat_kontrakt.md).

Facit uttrycks i ögats *faktiska* grammatik. Vi kopierar inte grammatiken hit;
vi importerar den ur ext/vc_addon/vc_assist/oga_kontrakt.py och validerar varje
facitrad mot den. Kopierad grammatik driftar; importerad kan inte.

Felklasserna läses ur docs/spec/82_felklasser.md vid körning, av samma skäl.
En kopia av klasslistan i banken hade kunnat bli gammal utan att något märkte det.

Endast standardbiblioteket.

beskriver: bank/uppgifter/*.json, bank/katalog_index.json, bank/lasare.py
"""
from __future__ import annotations

import itertools
import os
import re
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, ".."))
_KONTRAKT_KATALOG = os.path.join(ROT, "ext", "vc_addon", "vc_assist")
if _KONTRAKT_KATALOG not in sys.path:
    sys.path.insert(0, _KONTRAKT_KATALOG)

import oga_kontrakt as K  # noqa: E402

FELKLASSFIL = os.path.join(ROT, "docs", "spec", "82_felklasser.md")
UPPGIFTSKATALOG = os.path.join(_HAR, "uppgifter")
KATALOGINDEXFIL = os.path.join(_HAR, "katalog_index.json")

# ---------------------------------------------------------------- vokabulär

GRUPPER = {
    "T": "transport",
    "P": "plock",
    "L": "palletering",
    "S": "sortering",
    "A": "montering",
    "H": "överlämning",
    "C": "cell",
}

ID_MONSTER = re.compile(r"^(T|P|L|S|A|H|C)-\d{2}$")

# Uppgifter med löpnummer >= 90 är medvetet trasiga varianter. Regel 3 i
# docs/spec/83_scenarier.md: ett scenario som ingen generator kan fälla mäter
# ingenting, så varje grind behöver en fixtur som fäller den.
VARIANTGRANS = 90

SIGNALRIKTNINGAR = ("in", "out")
SIGNALTYPER = ("bool", "int", "real")

# Grinden som ska fälla uppgiften. "OGAT" är grind 5 i docs/spec/50_grindar.md;
# G1-G4 ligger före ögat och G6-G7 efter. En uppgift vars facit ligger före ögat
# har ingen ögondom att jämföra mot, och bär i stället en förväntad grindkod.
GRINDAR = ("G1", "G2", "G3", "G4", "OGAT", "G6", "G7")

ARTEFAKTTYPER = ("st", "oga", "logg")

STAMPLAR = ("DEKLARERAD", "MATT")

# Branscherna finns för att banken ska mäta sin egen spridning. Tolv varianter
# av samma plockcell ser ut som fyrtio uppgifter men mäter en enda sak.
BRANSCHER = (
    "fordonsmontering",
    "livsmedelsforpackning",
    "lakemedel",
    "elektronik",
    "lager_orderplock",
    "plastformsprutning",
    "svetsning",
    "limning",
    "kvalitetskontroll",
    "logistik_pall",
)

# Signalnamnen följer en genomförd konvention i hela banken:
#   ST<nnn>_<DON>_<FUNKTION>     stationsbunden signal, t.ex. ST020_RB_START
#   <ANLAGGNINGSSIGNAL>          anläggningsgemensam, listad nedan
# Grind 3 (docs/spec/50_grindar.md) matchar deklarationer mot signalkartan.
# Är namnen inte disciplinerade i banken kan grinden inte prövas mot den.
ANLAGGNINGSSIGNALER = (
    "EMG_OK",            # nödstoppskretsen sluten, läses från säkerhets-PLC
    "AIR_OK",            # tryckluft över lägsta tryck
    "SAFE_DOOR_CLOSED",  # skyddsgrind stängd och låst
    "LIGHT_CURTAIN_OK",  # ljusridå obruten
    "SYS_AUTO",          # anläggningen i automatläge
    "SYS_RESET",         # återställningsknapp
    "SYS_ALARM",         # samlingslarm
)
SIGNALMONSTER = re.compile(r"^ST\d{3}_[A-Z][A-Z0-9]{0,4}_[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")

# En handskakning är fyra signaler, inte en bool: begäran, kvittens, klar,
# återställning. Grupp H finns just för att pröva dem, så där är det ett krav.
HANDSKAKNINGSANDELSER = ("_REQ", "_ACK", "_DONE", "_RST")

# Svarighetsstegen. Ordningen är den beprövade undervisningsprogressionen, och
# svårighetsgraden härleds ur steget i stället för att gissas per uppgift. Då
# blir stegen faktiskt stigande och två uppgifter på samma steg får samma tal.
STEGE = (
    ("start_stopp_transportor", 1),
    ("set_reset", 1),
    ("nivareglering", 2),
    ("sortering_hojd_enkel", 2),
    ("sortering_hojd_avancerad", 3),
    ("separeringsstation", 3),
    ("palletering", 4),
    ("plock_placera_tre_axlar", 4),
    ("produktionslinje", 5),
    ("hiss", 5),
)
STEGE_SVARIGHET = dict(STEGE)

# Gränsscenarier. Mätt skäl (SemaPLC, arXiv 2608.18565): felfrekvensen är
# 17,3 % vid gränsöverskridande scenarier mot 7,1 % vid normaldrift. Ett facit
# som bara kör normalfallet mäter alltså nästan ingenting. Därför är det ett
# fält och inte en fotnot.
SCENARIOTYPER = ("normaldrift", "gransvarde_lag", "gransvarde_hog", "vandning")
ANALOGA_TYPER = ("int", "real")
MIN_FORVANTAT_TECKEN = 40

# Kedjan uppgifterna ska vara sanna i. VC har ingen inbyggd ST-motor; VC Premium
# är en OPC UA-KLIENT som mappar simuleringsvariabler mot en server. En uppgift
# som låter som om VC kör logiken själv är fel formulerad, så prompten måste
# nämna OPC UA.
KEDJENYCKEL = "OPC UA"

# Vilken sorts artefakt en trasig variant måste bära för att dess facit ska gå
# att pröva mekaniskt. En variant vars facit ligger på ögat måste bära en
# ögonrapport; annars är facit ett påstående och inte en mätning.
ARTEFAKT_FOR_GRIND = {
    "G1": ("st",), "G2": ("st",), "G3": ("st",), "G4": ("st", "logg"),
    "OGAT": ("oga",), "G6": ("oga",), "G7": ("st", "logg", "oga"),
}

# ---------------------------------------------------------------- felklasser


def las_felklasser(sokvag: str = FELKLASSFIL) -> dict:
    """F-koderna ur specens egen tabell. Ingen kopia i banken."""
    ut = {}
    rad_re = re.compile(r"^\|\s*`(F\d+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
    with open(sokvag, encoding="utf-8") as f:
        for rad in f:
            m = rad_re.match(rad)
            if m:
                ut[m.group(1)] = {"namn": m.group(2), "definition": m.group(3)}
    if not ut:
        raise RuntimeError(
            "hittade noll felklasser i %s; tabellformen har ändrats" % sokvag)
    return ut


# ------------------------------------------------------- facitrader och ögat

# En facitrad är en rad ur ögats grammatik där varje tal får bytas mot '*'.
# '*' betyder "vilket tal som helst" — vi låser ordningen och orden, inte de
# mätvärden vi ännu inte mätt. Ett facit som låste talen hade varit ett påhitt.
JOKER = "*"
_TALKANDIDATER = ("1.5", "2")      # flyttal och heltal; ögat har båda sorterna
_TALMONSTER = r"(?:-?\d+(?:\.\d+)?)"
MAX_JOKRAR = 8


def vittnen(mall: str):
    """Konkreta rader som mallen tillåter. Används för att bevisa att mallen
    över huvud taget kan uppstå ur ögats grammatik."""
    delar = mall.split(JOKER)
    n = len(delar) - 1
    if n == 0:
        return [mall]
    if n > MAX_JOKRAR:
        raise ValueError("för många jokrar i %r" % (mall,))
    ut = []
    for komb in itertools.product(_TALKANDIDATER, repeat=n):
        s = delar[0]
        for i, v in enumerate(komb):
            s += v + delar[i + 1]
        ut.append(s)
    return ut


def mall_till_regex(mall: str):
    """Mallen som ett mönster att matcha en verklig ögonrad mot."""
    delar = [re.escape(d) for d in mall.split(JOKER)]
    return re.compile("^" + _TALMONSTER.join(delar) + "$")


def granska_facitrad(sektion: str, mall: str):
    """None om raden finns i ögats grammatik, annars ett felmeddelande."""
    if sektion not in K.SEKTIONER:
        return "okänd sektion %r; kända är %s" % (sektion, ", ".join(K.SEKTIONER))
    nyckel = mall.split(" ", 1)[0]
    monster = K.RADER.get((sektion, nyckel))
    if monster is None:
        return "okänt nyckelord %r i sektionen %s" % (nyckel, sektion)
    try:
        kandidater = vittnen(mall)
    except ValueError as fel:
        return str(fel)
    for v in kandidater:
        if re.match(monster, v):
            return None
    return ("mallen %r kan inte uppstå ur ögats mönster för %s/%s"
            % (mall, sektion, nyckel))


# ------------------------------------------------------------------ lintkoder

# M1-M12 ägs av docs/spec/81_mallschema.md. M13 och uppåt är bankens egna
# tillägg och är dokumenterade i bank/README.md.
LINTKODER = {
    "M1_MISSING_FIELD": "obligatoriskt fält saknas",
    "M2_ID_MISMATCH": "task_id matchar inte filnamnet",
    "M3_ID_PATTERN": "task_id bryter mönstret",
    "M4_UNKNOWN_URI": "komponent-URI finns inte i katalogindexet",
    "M5_COORDS_IN_CONNECTION": "koordinater i scene.connections",
    "M6_NO_FACIT": "expect saknar mätbart krav",
    "M7_RUNS_TOO_FEW": "expect.runs under 3",
    "M8_UNKNOWN_CLASS": "targets_class innehåller okänd felklass",
    "M9_SIGNAL_DIR": "signal utan dir eller med okänd riktning",
    "M10_TIMING_NO_TOLERANCE": "tidskrav utan tolerans",
    "M11_EMPTY_SEQUENCE": "control.sequence tom",
    "M12_STATUS_WITHOUT_RUN": "verified_status över unverified utan last_run",
    "M13_LINE_NOT_IN_GRAMMAR": "facitrad finns inte i ögats grammatik",
    "M14_PASS_WITH_VIOLATION": "facit säger PASS men kräver en HONESTY-överträdelse",
    "M15_GATE_FACIT": "facit stämmer inte med den grind som ska fälla",
    "M16_VARIANT_WITHOUT_ARTIFACT": "trasig variant utan artefakt att fälla",
    "M17_DIFFICULTY": "svårighetsgrad utanför 1-5 eller utan stämpel",
    "M18_PROMPT": "uppgiftstexten saknas eller är för kort för att vara konkret",
    "M19_UNKNOWN_ROLE": "koppling pekar på en roll som inte finns i scenen",
    "M20_GROUP_MISMATCH": "grupp stämmer inte med prefixet i task_id",
    "M21_VARIANT_TARGET": "variant_av pekar på fel sorts uppgift",
    "M22_SIGNAL_NAME": "signalnamnet följer inte bankens namnkonvention",
    "M23_ROBOT_KAPACITET": "roboten räcker inte till uppgiftens last eller radie",
    "M24_LAYOUT_URI": "uppgiften lutar sig mot en förbyggd layout som inte finns",
    "M25_HANDSKAKNING": "överlämning utan fullständig handskakning",
    "M26_BRANSCH": "okänd eller saknad bransch",
    "M27_ORSAK": "uppgiften säger inte vilken verklig driftsättningsmiss den speglar",
    "M28_ANTAGANDE": "ett tal utan härkomst och utan märkt antagande",
    "M29_KEDJA": "uppgiftstexten nämner inte kedjan över OPC UA",
    "M30_SCENARIER": "gränsscenarierna är ofullständiga",
    "M31_KARNUTGANGAR": "kärnutgångarna för spårjämförelse saknas eller är inte utgångar",
    "M32_STEGE": "svårighetsgraden stämmer inte med steget på svårighetsstegen",
}

# Uppgiftstexten är det enda modellen får se. En text på under så här många
# tecken kan inte bära mått i mm, tider i s och signalnamn samtidigt, och blir
# då en genrebeskrivning i stället för en uppgift.
MIN_PROMPT_TECKEN = 200

KARNFALT = ("task_id", "title", "goal", "grupp", "bransch", "orsak", "prompt",
            "targets_class", "stege", "difficulty", "difficulty_stamp",
            "failure_modes", "antaganden", "fysik", "scenarios", "core_outputs",
            "variant_av", "scene", "control", "expect", "verified_status",
            "last_run")

# En orsak under så här många tecken hinner inte namnge en verklig miss. Talet
# är satt genom att skriva ut den kortaste orsak jag ville släppa igenom
# ("uppehållet är kortare än transportörens eftersläpning, så nästa detalj
# skjuts in innan den förra lämnat givaren") och räkna tecknen: 104.
MIN_ORSAK_TECKEN = 100
MIN_MOTIV_TECKEN = 40


def _fel(kod, text):
    return (kod, text)


def _ar_tal(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validera(post, filnamn=None, katalogindex=None, felklasser=None):
    """Lista av (lintkod, förklaring). Tom lista = uppgiften duger.

    Kastar aldrig på en trasig uppgift; en linter som kraschar döljer rött
    (regel S10 i docs/spec/96_ingen_skuld.md).
    """
    felklasser = felklasser if felklasser is not None else las_felklasser()
    katalogindex = katalogindex if katalogindex is not None else set()
    fel = []

    if not isinstance(post, dict):
        return [_fel("M1_MISSING_FIELD", "uppgiften är inte ett objekt")]

    for f in KARNFALT:
        if f not in post:
            fel.append(_fel("M1_MISSING_FIELD", "fältet %r saknas" % f))
    if fel:
        return fel

    tid = post["task_id"]
    if not isinstance(tid, str) or not ID_MONSTER.match(tid):
        fel.append(_fel("M3_ID_PATTERN", "task_id %r bryter mönstret" % (tid,)))
        return fel
    if filnamn is not None:
        stam = os.path.splitext(os.path.basename(filnamn))[0]
        if stam != tid:
            fel.append(_fel("M2_ID_MISMATCH",
                            "task_id %s mot filnamn %s" % (tid, stam)))

    prefix, nummer = tid.split("-")
    nummer = int(nummer)
    ar_variant = nummer >= VARIANTGRANS

    if post["grupp"] != prefix:
        fel.append(_fel("M20_GROUP_MISMATCH",
                        "grupp %r mot prefix %r" % (post["grupp"], prefix)))

    if not isinstance(post["prompt"], str) or len(post["prompt"]) < MIN_PROMPT_TECKEN:
        fel.append(_fel("M18_PROMPT",
                        "uppgiftstexten är %d tecken, kravet är %d"
                        % (len(post.get("prompt") or ""), MIN_PROMPT_TECKEN)))
    elif KEDJENYCKEL not in post["prompt"]:
        fel.append(_fel("M29_KEDJA",
                        "uppgiftstexten nämner inte %s; kedjan är ST -> OpenPLC "
                        "Runtime v4 -> OPC UA -> VC-scenen, och VC kör ingen ST själv"
                        % KEDJENYCKEL))

    if not isinstance(post["targets_class"], list) or not post["targets_class"]:
        fel.append(_fel("M8_UNKNOWN_CLASS", "targets_class är tom"))
    else:
        for k in post["targets_class"]:
            if k not in felklasser:
                fel.append(_fel("M8_UNKNOWN_CLASS", "okänd felklass %r" % (k,)))

    d = post["difficulty"]
    if not isinstance(d, int) or isinstance(d, bool) or not 1 <= d <= 5:
        fel.append(_fel("M17_DIFFICULTY", "svårighetsgrad %r" % (d,)))
    if post["stege"] not in STEGE_SVARIGHET:
        fel.append(_fel("M32_STEGE", "okänt steg %r" % (post["stege"],)))
    elif STEGE_SVARIGHET[post["stege"]] != d:
        fel.append(_fel("M32_STEGE",
                        "steget %s ger svårighetsgrad %d, uppgiften säger %r"
                        % (post["stege"], STEGE_SVARIGHET[post["stege"]], d)))
    if post["difficulty_stamp"] not in STAMPLAR:
        fel.append(_fel("M17_DIFFICULTY",
                        "okänd stämpel %r" % (post["difficulty_stamp"],)))
    elif post["difficulty_stamp"] == "MATT" and not post["last_run"]:
        fel.append(_fel("M17_DIFFICULTY",
                        "svårighetsgraden är stämplad MATT utan last_run"))

    if not isinstance(post["failure_modes"], list) or not post["failure_modes"]:
        fel.append(_fel("M1_MISSING_FIELD", "failure_modes är tom"))

    if post["bransch"] not in BRANSCHER:
        fel.append(_fel("M26_BRANSCH", "okänd bransch %r" % (post["bransch"],)))

    orsak = post["orsak"]
    if not isinstance(orsak, str) or len(orsak) < MIN_ORSAK_TECKEN:
        fel.append(_fel("M27_ORSAK",
                        "orsaken är %d tecken, kravet är %d"
                        % (len(orsak or ""), MIN_ORSAK_TECKEN)))

    fel += _validera_antaganden(post)
    fel += _validera_fysik(post)
    fel += _validera_scen(post, katalogindex)
    fel += _validera_styrning(post)
    fel += _validera_kapacitet(post, katalogindex)
    fel += _validera_scenarier(post)
    fel += _validera_karnutgangar(post)
    fel += _validera_facit(post)
    fel += _validera_variant(post, ar_variant)

    if post["verified_status"] not in ("unverified", "L1", "L2"):
        fel.append(_fel("M1_MISSING_FIELD",
                        "okänt verified_status %r" % (post["verified_status"],)))
    elif post["verified_status"] != "unverified" and not post["last_run"]:
        fel.append(_fel("M12_STATUS_WITHOUT_RUN",
                        "status %s utan last_run" % post["verified_status"]))
    return fel


def _signaler(post):
    styr = post.get("control")
    if not isinstance(styr, dict):
        return []
    return [s for s in (styr.get("signals") or []) if isinstance(s, dict)]


def _validera_scenarier(post):
    """Normaldrift räcker inte. Varje analog insignal ska överskridas åt båda
    håll, och minst ett booleskt vändningsfall ska finnas."""
    fel = []
    lista = post["scenarios"]
    if not isinstance(lista, list) or not lista:
        return [_fel("M30_SCENARIER", "uppgiften har inga scenarier alls")]

    signaler = dict((s["name"], s) for s in _signaler(post) if "name" in s)
    sedda = {}
    for sc in lista:
        if not isinstance(sc, dict) or set(sc) != {"id", "typ", "signal",
                                                   "beskrivning", "forvantat"}:
            fel.append(_fel("M30_SCENARIER",
                            "scenariot ska ha exakt id, typ, signal, beskrivning, "
                            "forvantat: %r" % (sc,)))
            continue
        if sc["typ"] not in SCENARIOTYPER:
            fel.append(_fel("M30_SCENARIER", "okänd scenariotyp %r" % (sc["typ"],)))
            continue
        if len(str(sc["forvantat"])) < MIN_FORVANTAT_TECKEN:
            fel.append(_fel("M30_SCENARIER",
                            "scenariot %r säger inte vad styrningen ska göra"
                            % (sc["id"],)))
        if not str(sc["beskrivning"]).strip():
            fel.append(_fel("M30_SCENARIER", "scenariot %r saknar beskrivning"
                            % (sc["id"],)))
        if sc["typ"] == "normaldrift":
            if sc["signal"] is not None:
                fel.append(_fel("M30_SCENARIER",
                                "normaldrift pekar inte ut en enskild signal"))
        else:
            namn = sc["signal"]
            if namn not in signaler:
                fel.append(_fel("M30_SCENARIER",
                                "scenariot %r pekar på okänd signal %r"
                                % (sc["id"], namn)))
                continue
            if sc["typ"] in ("gransvarde_lag", "gransvarde_hog"):
                if signaler[namn].get("type") not in ANALOGA_TYPER:
                    fel.append(_fel("M30_SCENARIER",
                                    "gränsvärdesscenariot %r pekar på %s som inte "
                                    "är analog" % (sc["id"], namn)))
                if signaler[namn].get("dir") != "in":
                    fel.append(_fel("M30_SCENARIER",
                                    "gränsvärdet ska överskridas på en insignal, "
                                    "%s är en utsignal" % (namn,)))
            sedda.setdefault((sc["typ"], namn), 0)
            sedda[(sc["typ"], namn)] += 1

    typer = [sc.get("typ") for sc in lista if isinstance(sc, dict)]
    if "normaldrift" not in typer:
        fel.append(_fel("M30_SCENARIER", "inget normaldriftsfall"))
    if "vandning" not in typer:
        fel.append(_fel("M30_SCENARIER",
                        "inget vändningsfall; en boolesk signal som uteblir eller "
                        "kommer i fel ordning är den billigaste verkliga fällan"))
    for namn, s in signaler.items():
        if s.get("dir") == "in" and s.get("type") in ANALOGA_TYPER:
            for typ in ("gransvarde_lag", "gransvarde_hog"):
                if sedda.get((typ, namn), 0) != 1:
                    fel.append(_fel("M30_SCENARIER",
                                    "den analoga insignalen %s saknar exakt ett "
                                    "%s-scenario" % (namn, typ)))
    return fel


def _validera_karnutgangar(post):
    """Facitformen som håller i praktiken är spårjämförelse per utgångsport.
    Uppgiften måste därför namnge vilka utgångar som ska jämföras; utan det är
    poängen 'andel portar vars spår stämmer' inte definierad."""
    fel = []
    karn = post["core_outputs"]
    if not isinstance(karn, list) or not karn:
        return [_fel("M31_KARNUTGANGAR", "uppgiften namnger inga kärnutgångar")]
    utgangar = set(s["name"] for s in _signaler(post)
                   if s.get("dir") == "out" and "name" in s)
    for namn in karn:
        if namn not in utgangar:
            fel.append(_fel("M31_KARNUTGANGAR",
                            "%r är ingen utsignal i signalkartan" % (namn,)))
    if len(set(karn)) != len(karn):
        fel.append(_fel("M31_KARNUTGANGAR", "dubblerad kärnutgång"))
    return fel


def _validera_antaganden(post):
    """Varje tal jag inte kan grunda i publicerad praxis ska stå märkt.

    Ett märkt antagande är hederligt. Ett omärkt påhittat tal ser ut som en
    mätning, och det är just den sortens falska precision hela specen är
    skriven emot (docs/spec/01_kalldisciplin.md)."""
    fel = []
    lista = post["antaganden"]
    if not isinstance(lista, list) or not lista:
        return [_fel("M28_ANTAGANDE",
                     "uppgiften påstår sig inte anta något; ingen uppgift är helt grundad")]
    for a in lista:
        if not isinstance(a, dict) or set(a) != {"vad", "varde", "motiv"}:
            fel.append(_fel("M28_ANTAGANDE",
                            "antagandet ska ha exakt vad, varde, motiv: %r" % (a,)))
            continue
        if not str(a["vad"]).strip():
            fel.append(_fel("M28_ANTAGANDE", "antagandet namnger inte vad det gäller"))
        if len(str(a["motiv"])) < MIN_MOTIV_TECKEN:
            fel.append(_fel("M28_ANTAGANDE",
                            "motivet för %r är för kort för att vara ett skäl"
                            % (a["vad"],)))
    return fel


def _validera_fysik(post):
    fel = []
    f = post["fysik"]
    if not isinstance(f, dict) or set(f) != {"detalj", "arbetsradie_mm"}:
        return [_fel("M1_MISSING_FIELD",
                     "fysik ska ha exakt detalj och arbetsradie_mm")]
    d = f["detalj"]
    if not isinstance(d, dict) or set(d) != {"namn", "l_mm", "b_mm", "h_mm", "massa_kg"}:
        fel.append(_fel("M1_MISSING_FIELD",
                        "fysik.detalj ska ha exakt namn, l_mm, b_mm, h_mm, massa_kg"))
        return fel
    for nyckel in ("l_mm", "b_mm", "h_mm", "massa_kg"):
        if not _ar_tal(d[nyckel]) or d[nyckel] <= 0:
            fel.append(_fel("M1_MISSING_FIELD",
                            "fysik.detalj.%s = %r" % (nyckel, d[nyckel])))
    if not _ar_tal(f["arbetsradie_mm"]) or f["arbetsradie_mm"] <= 0:
        fel.append(_fel("M1_MISSING_FIELD",
                        "fysik.arbetsradie_mm = %r" % (f["arbetsradie_mm"],)))
    return fel


def _validera_kapacitet(post, katalogindex):
    """Roboten måste orka lasten och nå radien.

    Det här är den mekaniska kontrollen mot slarvet "5 kg last och 3 m
    räckvidd i samma uppgift". Talen kommer ur katalogindexets publicerade
    modelldata, inte ur uppgiftstexten, så en uppgift kan inte skriva sig fri.
    """
    fel = []
    if not isinstance(katalogindex, dict):
        return fel
    fysik = post.get("fysik")
    if not isinstance(fysik, dict) or not isinstance(fysik.get("detalj"), dict):
        return fel
    detalj = fysik["detalj"].get("massa_kg")
    radie = fysik.get("arbetsradie_mm")
    if not (_ar_tal(detalj) and _ar_tal(radie)):
        return fel

    komponenter = (post.get("scene") or {}).get("components") or []
    verktygsmassa = 0.0
    for k in komponenter:
        post_i_index = katalogindex.get(k.get("uri")) if isinstance(k, dict) else None
        if post_i_index and post_i_index.get("kategori") == "gripdon":
            verktygsmassa = max(verktygsmassa, float(post_i_index.get("massa_kg") or 0.0))
    for k in komponenter:
        post_i_index = katalogindex.get(k.get("uri")) if isinstance(k, dict) else None
        if not post_i_index or post_i_index.get("kategori") != "robot":
            continue
        behov = detalj + verktygsmassa
        if behov > post_i_index["nyttolast_kg"]:
            fel.append(_fel("M23_ROBOT_KAPACITET",
                            "%s bär %.1f kg men uppgiften kräver %.1f kg "
                            "(detalj %.1f + verktyg %.1f)"
                            % (post_i_index["namn"], post_i_index["nyttolast_kg"],
                               behov, detalj, verktygsmassa)))
        if radie > post_i_index["rackvidd_mm"]:
            fel.append(_fel("M23_ROBOT_KAPACITET",
                            "%s når %d mm men uppgiften kräver %d mm"
                            % (post_i_index["namn"], post_i_index["rackvidd_mm"], radie)))
    return fel


def _validera_scen(post, katalogindex):
    fel = []
    scen = post["scene"]
    if not isinstance(scen, dict):
        return [_fel("M1_MISSING_FIELD", "scene är inte ett objekt")]
    komponenter = scen.get("components")
    if not isinstance(komponenter, list) or not komponenter:
        return [_fel("M1_MISSING_FIELD", "scene.components är tom")]

    roller = set()
    for k in komponenter:
        if not isinstance(k, dict) or set(k) != {"role", "uri", "count"}:
            fel.append(_fel("M1_MISSING_FIELD",
                            "komponenten ska ha exakt role, uri, count: %r" % (k,)))
            continue
        roller.add(k["role"])
        if katalogindex and k["uri"] not in katalogindex:
            fel.append(_fel("M4_UNKNOWN_URI", "okänd URI %r" % (k["uri"],)))
        if not isinstance(k["count"], int) or k["count"] < 1:
            fel.append(_fel("M1_MISSING_FIELD",
                            "count ska vara ett positivt heltal: %r" % (k["count"],)))

    for c in scen.get("connections") or []:
        if not isinstance(c, dict):
            fel.append(_fel("M5_COORDS_IN_CONNECTION", "kopplingen är inte ett objekt"))
            continue
        if set(c) != {"from_role", "to_role"}:
            # I8: modellen anger relationer, VC räknar geometrin. Allt utöver
            # de två rollerna är på väg mot koordinater.
            fel.append(_fel("M5_COORDS_IN_CONNECTION",
                            "kopplingen bär andra fält än rollerna: %r" % (sorted(c),)))
            continue
        if any(_ar_tal(v) for v in c.values()):
            fel.append(_fel("M5_COORDS_IN_CONNECTION", "tal i koppling %r" % (c,)))
        for nyckel in ("from_role", "to_role"):
            if c[nyckel] not in roller:
                fel.append(_fel("M19_UNKNOWN_ROLE",
                                "kopplingen pekar på okänd roll %r" % (c[nyckel],)))
    if "layout_uri" not in scen:
        fel.append(_fel("M1_MISSING_FIELD", "scene.layout_uri saknas"))
    elif scen["layout_uri"] is not None:
        # MÄTT 2026-09-04: noll .vcmx-layouter på disk i VC-installationen.
        # En uppgift som pekar på en förbyggd layout är därför inte körbar,
        # och en obekräftad sökväg i banken är en tyst framtida fällning.
        fel.append(_fel("M24_LAYOUT_URI",
                        "layout_uri %r; det finns inget layoutarkiv att peka på"
                        % (scen["layout_uri"],)))
    return fel


def _validera_styrning(post):
    fel = []
    styr = post["control"]
    if not isinstance(styr, dict):
        return [_fel("M1_MISSING_FIELD", "control är inte ett objekt")]

    signaler = styr.get("signals")
    if not isinstance(signaler, list) or not signaler:
        fel.append(_fel("M9_SIGNAL_DIR", "control.signals är tom"))
    else:
        for s in signaler:
            if not isinstance(s, dict) or "name" not in s:
                fel.append(_fel("M9_SIGNAL_DIR", "signal utan namn: %r" % (s,)))
                continue
            if s.get("dir") not in SIGNALRIKTNINGAR:
                fel.append(_fel("M9_SIGNAL_DIR",
                                "signalen %s har riktning %r" % (s["name"], s.get("dir"))))
            if s.get("type") not in SIGNALTYPER:
                fel.append(_fel("M9_SIGNAL_DIR",
                                "signalen %s har typ %r" % (s["name"], s.get("type"))))
            if not s.get("comment"):
                fel.append(_fel("M1_MISSING_FIELD",
                                "signalen %s saknar kommentar" % s["name"]))
            namn = s["name"]
            if namn not in ANLAGGNINGSSIGNALER and not SIGNALMONSTER.match(namn):
                fel.append(_fel("M22_SIGNAL_NAME",
                                "signalnamnet %r följer varken ST<nnn>_<DON>_<FUNKTION> "
                                "eller listan över anläggningssignaler" % (namn,)))

    if not styr.get("sequence"):
        fel.append(_fel("M11_EMPTY_SEQUENCE", "control.sequence är tom"))

    timing = styr.get("timing")
    if not isinstance(timing, dict):
        fel.append(_fel("M10_TIMING_NO_TOLERANCE", "control.timing saknas"))
    else:
        har_krav = bool(timing.get("dwell_s")) or _ar_tal(timing.get("cycle_s"))
        tol = timing.get("tolerance_s")
        if har_krav and not (_ar_tal(tol) and tol > 0):
            fel.append(_fel("M10_TIMING_NO_TOLERANCE",
                            "tidskrav utan positiv tolerans: %r" % (tol,)))
        if not har_krav:
            fel.append(_fel("M10_TIMING_NO_TOLERANCE",
                            "control.timing bär varken uppehåll eller cykeltid"))
    if "interlocks" not in styr or not isinstance(styr["interlocks"], list):
        fel.append(_fel("M1_MISSING_FIELD", "control.interlocks saknas"))

    if post["grupp"] == "H" and isinstance(signaler, list):
        namn = [s.get("name", "") for s in signaler if isinstance(s, dict)]
        saknas = [a for a in HANDSKAKNINGSANDELSER
                  if not any(n.endswith(a) for n in namn)]
        if saknas:
            fel.append(_fel("M25_HANDSKAKNING",
                            "överlämningen saknar %s; en handskakning är fyra "
                            "signaler, inte en bool" % ", ".join(saknas)))
    return fel


def _validera_facit(post):
    fel = []
    e = post["expect"]
    if not isinstance(e, dict):
        return [_fel("M6_NO_FACIT", "expect är inte ett objekt")]

    for f in ("runs", "warmup_s", "must_pass", "max_collisions",
              "min_clearance_mm", "gate", "verdict", "reason_contains",
              "lines", "forbidden_lines", "gate_code", "throughput_per_h"):
        if f not in e:
            fel.append(_fel("M6_NO_FACIT", "expect.%s saknas" % f))
    if fel:
        return fel

    if not isinstance(e["runs"], int) or e["runs"] < 3:
        fel.append(_fel("M7_RUNS_TOO_FEW", "expect.runs = %r" % (e["runs"],)))
    if not _ar_tal(e["warmup_s"]) or e["warmup_s"] < 0:
        fel.append(_fel("M6_NO_FACIT", "expect.warmup_s = %r" % (e["warmup_s"],)))
    if not isinstance(e["max_collisions"], int) or e["max_collisions"] < 0:
        fel.append(_fel("M6_NO_FACIT",
                        "expect.max_collisions = %r" % (e["max_collisions"],)))
    if not _ar_tal(e["min_clearance_mm"]) or e["min_clearance_mm"] <= 0:
        fel.append(_fel("M6_NO_FACIT",
                        "expect.min_clearance_mm = %r" % (e["min_clearance_mm"],)))
    for s in e["must_pass"]:
        if s not in K.SEKTIONER:
            fel.append(_fel("M6_NO_FACIT", "must_pass nämner okänd sektion %r" % (s,)))

    if e["gate"] not in GRINDAR:
        fel.append(_fel("M15_GATE_FACIT", "okänd grind %r" % (e["gate"],)))
        return fel

    rader = e["lines"]
    forbjudna = e["forbidden_lines"]
    for namn, lista in (("lines", rader), ("forbidden_lines", forbjudna)):
        if not isinstance(lista, list):
            fel.append(_fel("M6_NO_FACIT", "expect.%s är inte en lista" % namn))
            continue
        for r in lista:
            if not isinstance(r, dict) or set(r) != {"section", "template"}:
                fel.append(_fel("M13_LINE_NOT_IN_GRAMMAR",
                                "raden ska ha exakt section och template: %r" % (r,)))
                continue
            brist = granska_facitrad(r["section"], r["template"])
            if brist:
                fel.append(_fel("M13_LINE_NOT_IN_GRAMMAR", brist))

    if e["gate"] == "OGAT":
        # M6 är den bärande regeln: facit skrivs före försöket. En ögonuppgift
        # utan dom och utan en enda krävd rad har inget facit.
        if e["verdict"] not in K.DOMAR:
            fel.append(_fel("M6_NO_FACIT", "okänd ögondom %r" % (e["verdict"],)))
        if not rader:
            fel.append(_fel("M6_NO_FACIT", "ögonuppgift utan en enda krävd rad"))
        if e["gate_code"] is not None:
            fel.append(_fel("M15_GATE_FACIT",
                            "gate_code hör till grindarna före ögat"))
        if e["verdict"] == "PASS":
            if e["reason_contains"] is not None:
                fel.append(_fel("M15_GATE_FACIT",
                                "ett PASS motiveras inte av en orsakssträng"))
            for r in rader:
                if isinstance(r, dict) and " VIOLATION" in str(r.get("template")):
                    # Kontraktets regel 5: en överträdelse tvingar FAIL. Ett
                    # facit som kräver båda kan aldrig uppfyllas.
                    fel.append(_fel("M14_PASS_WITH_VIOLATION",
                                    "facit kräver %r under ett PASS" % (r["template"],)))
        elif not e["reason_contains"]:
            fel.append(_fel("M6_NO_FACIT",
                            "en fällning ska namnge vad domen ska handla om"))
    else:
        if e["verdict"] is not None:
            fel.append(_fel("M15_GATE_FACIT",
                            "grinden %s fäller före ögat; verdict ska vara null"
                            % e["gate"]))
        if not e["gate_code"]:
            fel.append(_fel("M6_NO_FACIT",
                            "grinden %s fäller, men facit namnger ingen kod"
                            % e["gate"]))
        if rader:
            fel.append(_fel("M15_GATE_FACIT",
                            "ögonrader i ett facit som fälls före ögat"))
    return fel


def _validera_variant(post, ar_variant):
    fel = []
    trasig = post.get("broken")
    if not ar_variant:
        if post["variant_av"] is not None:
            fel.append(_fel("M21_VARIANT_TARGET",
                            "en hel uppgift får inte peka ut ett original"))
        if trasig is not None:
            fel.append(_fel("M21_VARIANT_TARGET",
                            "en hel uppgift får inte bära en trasig artefakt"))
        return fel

    original = post["variant_av"]
    if not isinstance(original, str) or not ID_MONSTER.match(original or ""):
        fel.append(_fel("M21_VARIANT_TARGET",
                        "variant_av %r är inte ett uppgifts-id" % (original,)))
    elif int(original.split("-")[1]) >= VARIANTGRANS:
        fel.append(_fel("M21_VARIANT_TARGET",
                        "en variant får inte peka på en annan variant"))

    if not isinstance(trasig, dict):
        fel.append(_fel("M16_VARIANT_WITHOUT_ARTIFACT", "broken saknas"))
        return fel
    if set(trasig) != {"artefakt_typ", "artefakt", "vad_som_ar_fel"}:
        fel.append(_fel("M16_VARIANT_WITHOUT_ARTIFACT",
                        "broken ska ha exakt artefakt_typ, artefakt, vad_som_ar_fel"))
        return fel
    if trasig["artefakt_typ"] not in ARTEFAKTTYPER:
        fel.append(_fel("M16_VARIANT_WITHOUT_ARTIFACT",
                        "okänd artefakttyp %r" % (trasig["artefakt_typ"],)))
    elif trasig["artefakt_typ"] not in ARTEFAKT_FOR_GRIND.get(post["expect"]["gate"], ()):
        fel.append(_fel("M15_GATE_FACIT",
                        "grinden %s fäller inte en artefakt av typen %s"
                        % (post["expect"]["gate"], trasig["artefakt_typ"])))
    if not trasig["artefakt"] or not str(trasig["artefakt"]).strip():
        fel.append(_fel("M16_VARIANT_WITHOUT_ARTIFACT", "artefakten är tom"))
    if not trasig["vad_som_ar_fel"]:
        fel.append(_fel("M16_VARIANT_WITHOUT_ARTIFACT",
                        "varianten säger inte vad som är fel"))
    return fel
