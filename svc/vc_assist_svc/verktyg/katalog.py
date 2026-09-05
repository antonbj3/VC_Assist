# -*- coding: utf-8 -*-
"""Domanen catalog: vad som finns att spawna (45_verktyg.md).

Alla verktyg har ar DATA. Skalet star i 45_verktyg.md: "allt som ror scenen
ar kodgenerering; allt som ror index, katalog och kunskap ar data". Ett
data-verktyg kors i tjansten och gar aldrig via bryggan, sa katalogen kan
svara aven nar VC inte ar igang.

VAD KATALOGEN AR, MATT
----------------------
45_verktyg.md forutsatter ett index som byggs i fas 4 ur eCatalog och bar
URI, namn, kategori, TILLVERKARE, VILKA GRANSSNITT komponenten bar och dess
egenskaper. Det indexet finns inte, och det gar inte att bygga har:

  * VC:s eCatalog ar en NATTJANST bakom anvandarkonto. Utan konto och
    natverk finns ingen katalog att ga igenom.
  * RATTAD 2026-09-04, se M-57. Raden sa tidigare: "MATT i testprefixet:
    NOLL .vcmx-layouter och FEM komponentfiler pa disk. Det finns alltsa
    inget lokalt katalogbibliotek att soka i heller."
    Det var fel, och felet var att jag letade i INSTALLATIONSKATALOGEN. De fem
    filerna finns - de ar ritningsmallar. Biblioteket ligger i Public Documents
    och innehaller 3201 komponenter fran 149 tillverkare, darav 1736 robotar
    och 58 transportorer. svc/vc_assist_svc/katalogindex.py bygger indexet pa
    1,8 sekunder.
    VERKTYGEN HAR ANVANDER ANNU INTE det indexet. De 65 handskrivna posterna
    star kvar tills bankens vokabular gar att bredda utan att bryta
    M4_UNKNOWN_URI. Tills dess ar begransningen VAR, inte VC:s, och det ska
    sagas sa i stallet for att skyllas pa en tom katalog.

Kallan har ar darfor bank/katalog_index.json: 65 poster med verkliga
robotmodeller, standardiserade pallmatt och lastbarare, som banken redan
binder sina uppgifter mot (lintkod M4_UNKNOWN_URI i bank/schema.py).

Foljden bars av VARJE svar, inte av en fotnot:

  * `notering` sager att katalogen ar lokal och begransad, och citerar
    indexfilens egen harkomstrad.
  * `stampel` och `stampel_betydelse` foljer med varje post, sa att en
    ANTAGEN siffra aldrig ser ut som en matt (siffrans harkomst hor till
    siffran).
  * `granssnitt` finns INTE i den har kallan. Falten ljugs inte ihop; de
    saknas, och notering_granssnitt sager att de saknas.
  * En URI som inte star i indexet ger found=false. Uppfunnen URI ar ett
    hart fel, inte en varning (I9), sa verktyget gissar aldrig fram en
    sokvag. Alternativen som foljer med ett bomskott ar VERKLIGA URI:er ur
    indexet.

bank://-URI:er ar inte laddbara VC-URI:er. Indexfilen valde schemat just for
att ingen ska forvaxla en bankpost med en matt VC-URI, och load_component
kan darfor inte ta en bank://-URI. Det star i notering.
"""
from __future__ import annotations

import collections
import json
import os
import unicodedata

from .bas import SINCE, TIMEOUT_MS, params, returns
from .fel import Schemafel
from .register import registrera
from .schema import Verktyg

DOMAN = "catalog"

_HAR = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.normpath(os.path.join(_HAR, "..", "..", ".."))
KATALOGFIL = os.path.join(ROT, "bank", "katalog_index.json")


# ---- kallan --------------------------------------------------------------

def _las_katalog(sokvag=KATALOGFIL):
    """Laser indexfilen. Kastar vid import om den inte gar att lita pa.

    Samma fil som bank/lasare.las_katalogindex laser, inte en kopia av den:
    en kopierad vokabular driftar fran bankens sa fort nagon andrar den ena.
    Dubblettkontrollen ar densamma som bankens, av samma skal - tva poster
    pa samma URI gor svaret beroende av lasordningen.
    """
    with open(sokvag, encoding="utf-8") as f:
        data = json.load(f)
    poster = collections.OrderedDict()
    for post in data["poster"]:
        if post["uri"] in poster:
            raise Schemafel("katalogindexet har tva poster pa %s (%s)"
                            % (post["uri"], sokvag))
        poster[post["uri"]] = post
    if not poster:
        raise Schemafel("katalogindexet %s ar tomt" % sokvag)
    return data, poster


DATA, POSTER = _las_katalog()

# Falt som ar postens identitet och inte ett matt varde.
_IDENTITETSFALT = ("uri", "namn", "kategori", "stampel", "not")

# Enheten star i faltnamnets suffix i indexfilen (rackvidd_mm, anslag_s,
# hastighet_mps). Tabellen skiljer namnet fran enheten sa att ett tal aldrig
# lamnar verktyget utan sin enhet. Suffixen ar de som FAKTISKT forekommer i
# bank/katalog_index.json; ett okant suffix ger enhet=null i stallet for en
# gissad enhet.
ENHET_FOR_SUFFIX = {
    "mm": "mm",
    "kg": "kg",
    "s": "s",
    "ms": "ms",
    "mmin": "m/min",
    "mps": "m/s",
}

KATEGORIER = tuple(sorted({p["kategori"] for p in POSTER.values()}))

# URI-gruppen ar segmentet efter bank://, alltsa bank://<grupp>/<namn>.
# Den ar INTE samma sak som kategori: gruppen transport bar bade kategorin
# transport och kategorin don, och gruppen givare bar bade givare och
# sakerhet. Darfor bars bada i svaret.
GRUPPER = tuple(sorted({u.split("/")[2] for u in POSTER}))

# Arlighetsraden. Byggd ur indexfilens EGEN harkomstrad i stallet for en
# omskrivning av den: en omskriven harkomst kan drifta fran den matning den
# beskriver, en citerad kan inte.
NOTERING = (
    "Katalogen ar LOKAL och BEGRANSAD: %d poster ur bank/katalog_index.json. "
    "VC:s eCatalog ar en nattjanst bakom anvandarkonto och ar inte genomsokt "
    "harifran. URI:erna ar bank://-poster, inte VC-URI:er, och load_component "
    "kan inte ladda dem. Valj bara URI:er ur den har trafflistan; en uppfunnen "
    "URI ar ett hart fel. Indexets egen harkomst: %s"
    % (len(POSTER), DATA["harkomst"])
)

NOTERING_GRANSSNITT = (
    "Granssnitt (vcSimInterface) saknas i den har kallan. 45_verktyg.md vantar "
    "dem ur eCatalog-indexet i fas 4; det indexet gar inte att bygga utan konto "
    "och natverk. Falten ar darfor utelamnade, inte pahittade - fraga scenen med "
    "list_interfaces nar komponenten val ar laddad."
)


def _vik(text):
    """Skiftlages- och diakritokanslig form for jamforelse.

    MATT 2026-09-04: 35 av indexets 65 poster bar icke-ASCII (Ljusrida,
    sakerhetsklassad), medan ovriga ar ASCII-translittererade (lagesgivare,
    tackplat). Utan vikningen hittar en fraga stavad pa det ena sattet inte
    posten stavad pa det andra. NFKD plus bort med kombinerande tecken gor
    det utan en handskriven teckentabell som kan aldras.
    """
    rensad = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in rensad if not unicodedata.combining(c))


def _matt(post):
    """Postens matta varden som (namn, varde, enhet), enheten ur suffixet."""
    ut = []
    for namn in sorted(post):
        if namn in _IDENTITETSFALT:
            continue
        rot, _, suffix = namn.rpartition("_")
        if rot and suffix in ENHET_FOR_SUFFIX:
            ut.append({"namn": rot, "varde": post[namn],
                       "enhet": ENHET_FOR_SUFFIX[suffix]})
        else:
            ut.append({"namn": namn, "varde": post[namn], "enhet": None})
    return ut


def _post_ut(post, rang=None):
    return {
        "uri": post["uri"],
        "namn": post["namn"],
        "kategori": post["kategori"],
        "grupp": post["uri"].split("/")[2],
        "stampel": post["stampel"],
        "stampel_betydelse": DATA["stamplar"][post["stampel"]],
        "anmarkning": post.get("not"),
        "matt": _matt(post),
        "rang": rang,
    }


def _varde(post, namn):
    """Ett matt varde ur posten, eller None om posten inte bar det faltet."""
    v = post.get(namn)
    return float(v) if isinstance(v, (int, float)) else None


# ---- registrering --------------------------------------------------------

# bas.laggare() ger mode="codegen"; den har domanen ar data, sa laggaren star
# har. effect ar INTE en parameter: alla katalogverktyg laser, och ett
# data-verktyg som skriver avvisas anda av schemat eftersom det skulle ga
# forbi godkannandekon (I12).
#
# KRAVER for ett data-verktyg. Schemat kraver minst en yta ur formaga.YTOR
# och formagegrinden slar av verktyget nar ytan saknas. Ett katalogverktyg
# ror ingen VC-yta alls - det kor i tjansten. Vi deklarerar darfor den yta
# svaret ar TILL FOR: en katalogpost finns for att laddas, och laddningen ar
# app.load (samma yta som load_component kraver). Foljden ar uttalad och
# avsiktlig: utan formagerapport fran bryggan ar ocksa katalogverktygen
# avslagna, och skalet modellen far namner ytan (I3 fail-closed).
KRAVER = ("app.load",)


def _lagg(namn, beskrivning, parameters, returns_, handlare):
    return registrera(
        Verktyg(namn=namn, beskrivning=beskrivning, mode="data", effect="read",
                parameters=parameters, returns=returns_, since=SINCE,
                kraver=KRAVER, doman=DOMAN,
                # timeout_ms ar inert pa data-vagen: utforaren skickar den
                # bara till bryggan for kodgenererande verktyg. Talet halls
                # anda pa bas.TIMEOUT_MS sa att ingen andra, tystare grans
                # uppstar i tjansten.
                timeout_ms=TIMEOUT_MS),
        handlare)


# ---- aterkommande schemabitar --------------------------------------------

_MATTPOST = {
    "type": "object",
    "description": "Ett matt varde ur posten, med sin enhet utskriven.",
    "properties": {
        "namn": {"type": "string", "description": "Storhetens namn utan enhetssuffix."},
        "varde": {"type": ["number", "integer", "string", "null"],
                  "description": "Vardet som det star i indexfilen."},
        "enhet": {"type": ["string", "null"],
                  "description": "Enheten ur faltnamnets suffix, null nar suffixet inte ar en kand enhet."},
    },
    "required": ["namn", "varde", "enhet"],
}

_KATALOGPOST = {
    "type": ["object", "null"],
    "description": "En post ur det lokala katalogindexet. null nar ingen post fanns.",
    "properties": {
        "uri": {"type": "string",
                "description": "Postens URI. Anvand den exakt; hitta aldrig pa en egen."},
        "namn": {"type": "string", "description": "Komponentens namn."},
        "kategori": {"type": "string", "description": "Kategori i indexet."},
        "grupp": {"type": "string", "description": "URI-gruppen, segmentet efter bank://."},
        "stampel": {"type": "string",
                    "description": "Vardenas harkomst: PUBLICERAD_SPEC, STANDARDMATT eller ANTAGEN."},
        "stampel_betydelse": {"type": "string",
                              "description": "Vad stampeln betyder, ur indexfilens egen tabell."},
        "anmarkning": {"type": ["string", "null"],
                       "description": "Postens egen not, null nar den saknar en."},
        "matt": {"type": "array", "description": "Postens matta varden.",
                 "items": _MATTPOST},
        "rang": {"type": ["string", "null"],
                 "description": "Hur posten traffades vid sokning, null vid direkt uppslag."},
    },
    "required": ["uri", "namn", "kategori", "stampel", "stampel_betydelse", "matt"],
}

_RET_INDEX = {
    "type": "object",
    "description": "Vilket index svaret kommer ur.",
    "properties": {
        "index_id": {"type": "string", "description": "Indexets id."},
        "poster_totalt": {"type": "integer", "description": "Antal poster i hela indexet."},
        "harkomst": {"type": "string", "description": "Indexfilens egen harkomstrad."},
        "fil": {"type": "string", "description": "Filen svaret lastes ur."},
    },
    "required": ["index_id", "poster_totalt", "harkomst", "fil"],
}
_RET_NOTERING = {
    "type": "string",
    "description": "Arlighetsraden om katalogens rackvidd. Las den innan du valjer.",
}


def _index_ut():
    return {"index_id": DATA["index_id"], "poster_totalt": len(POSTER),
            "harkomst": DATA["harkomst"], "fil": "bank/katalog_index.json"}


# ---- search_catalog ------------------------------------------------------

# Ordinal rangordning, inte ett matt tal: poangen ar platsen i listan.
# Ordningen ar exakt fore prefix fore delstrang, och namn fore URI fore not,
# av samma skal som i api_index._RANGORDNING.
_RANGORDNING = ("exakt_uri", "exakt_namn", "prefix_namn", "delstrang_namn",
                "delstrang_uri", "delstrang_anmarkning")


def _rang(post, fraga, vikt):
    if post["uri"] == fraga:
        return "exakt_uri"
    namn = _vik(post["namn"])
    if namn == vikt:
        return "exakt_namn"
    if namn.startswith(vikt):
        return "prefix_namn"
    if vikt in namn:
        return "delstrang_namn"
    if vikt in _vik(post["uri"]):
        return "delstrang_uri"
    if vikt in _vik(post.get("not") or ""):
        return "delstrang_anmarkning"
    return None


def _search_catalog(argument):
    fraga = (argument.get("query") or "").strip()
    vikt = _vik(fraga)
    kategori = argument.get("category")
    min_rackvidd = argument.get("min_rackvidd_mm")
    min_nyttolast = argument.get("min_nyttolast_kg")

    traffar = []
    for post in POSTER.values():
        if kategori is not None and post["kategori"] != kategori:
            continue
        if min_rackvidd is not None:
            v = _varde(post, "rackvidd_mm")
            if v is None or v < min_rackvidd:
                continue
        if min_nyttolast is not None:
            v = _varde(post, "nyttolast_kg")
            if v is None or v < min_nyttolast:
                continue
        if fraga:
            rang = _rang(post, fraga, vikt)
            if rang is None:
                continue
        else:
            rang = None
        traffar.append((_RANGORDNING.index(rang) if rang else len(_RANGORDNING),
                        post["uri"], _post_ut(post, rang)))
    traffar.sort(key=lambda t: (t[0], t[1]))
    return {
        "traffar": [t[2] for t in traffar],
        "antal": len(traffar),
        "index": _index_ut(),
        "notering": NOTERING,
        "notering_granssnitt": NOTERING_GRANSSNITT,
    }


_lagg(
    "search_catalog",
    "Soker i det LOKALA katalogindexet (65 poster: robotar, transportorer, "
    "gripdon, givare, stationer och lastbarare). Filtren min_rackvidd_mm och "
    "min_nyttolast_kg slar bort poster som inte bar faltet alls, sa en robot "
    "utan angiven rackvidd kommer aldrig med i ett rackviddsfilter. Utan "
    "argument listas hela indexet. VC:s eCatalog ar INTE genomsokt harifran; "
    "las notering innan du valjer.",
    params({
        "query": {"type": "string",
                  "description": ("Fri text. Matchas mot namn, URI och "
                                  "anmarkning, okansligt for skiftlage och "
                                  "for a-ring och prickar.")},
        "category": {"type": "string", "enum": list(KATEGORIER),
                     "description": ("Bara poster i den har kategorin. "
                                     "Listan ar indexets verkliga kategorier.")},
        "min_rackvidd_mm": {"type": "number",
                            "description": "Minsta rackvidd i millimeter. Ror bara poster som bar rackvidd."},
        "min_nyttolast_kg": {"type": "number",
                             "description": "Minsta nyttolast i kilogram. Ror bara poster som bar nyttolast."},
    }),
    returns({
        "traffar": {"type": "array",
                    "description": "Traffarna, bast rang forst. Valj bara har ur.",
                    "items": _KATALOGPOST},
        "antal": {"type": "integer", "description": "Antal traffar."},
        "index": _RET_INDEX,
        "notering": _RET_NOTERING,
        "notering_granssnitt": {"type": "string",
                                "description": "Varfor granssnittsfalten saknas i den har kallan."},
    }, ["traffar", "antal", "index", "notering", "notering_granssnitt"]),
    _search_catalog,
)


# ---- catalog_item --------------------------------------------------------

def _catalog_item(argument):
    uri = argument["uri"].strip()
    post = POSTER.get(uri)
    # Alternativen ar VERKLIGA URI:er ur samma bank://<grupp>/, inte gissade
    # namn. Ingen tolerans behovs och ingen infors: gruppen ar bunden av
    # datan (storsta gruppen ar 15 poster av 65), sa listan kan inte svalla.
    alternativ = []
    if post is None:
        delar = uri.split("/")
        grupp = delar[2] if len(delar) > 2 else ""
        alternativ = [u for u in POSTER if u.split("/")[2] == grupp]
    return {
        "found": post is not None,
        "uri": uri,
        "post": _post_ut(post) if post is not None else None,
        "alternativ": alternativ,
        "index": _index_ut(),
        "notering": NOTERING,
        "notering_granssnitt": NOTERING_GRANSSNITT,
    }


_lagg(
    "catalog_item",
    "Slar upp EN katalogpost pa exakt URI och ger dess varden med enhet och "
    "harkomststampel. found=false ar ett giltigt svar och betyder att URI:n "
    "inte finns - da foljer verkliga URI:er ur samma grupp med som alternativ. "
    "Verktyget gissar aldrig fram en sokvag.",
    params({"uri": {"type": "string",
                    "description": "Postens URI, exakt som den star i trafflistan."}},
           ["uri"]),
    returns({
        "found": {"type": "boolean", "description": "Om URI:n fanns i indexet."},
        "uri": {"type": "string", "description": "URI:n som slogs upp."},
        "post": _KATALOGPOST,
        "alternativ": {"type": "array",
                       "description": ("Verkliga URI:er ur samma grupp. Fylls "
                                       "bara vid bomskott."),
                       "items": {"type": "string", "description": "En URI som finns."}},
        "index": _RET_INDEX,
        "notering": _RET_NOTERING,
        "notering_granssnitt": {"type": "string",
                                "description": "Varfor granssnittsfalten saknas i den har kallan."},
    }, ["found", "uri", "post", "alternativ", "index", "notering",
        "notering_granssnitt"]),
    _catalog_item,
)


# ---- catalog_categories --------------------------------------------------

def _catalog_categories(argument):
    kategorier = collections.Counter(p["kategori"] for p in POSTER.values())
    grupper = collections.Counter(u.split("/")[2] for u in POSTER)
    stamplar = collections.Counter(p["stampel"] for p in POSTER.values())
    return {
        "kategorier": [{"namn": k, "antal": kategorier[k]} for k in KATEGORIER],
        "grupper": [{"namn": g, "antal": grupper[g]} for g in GRUPPER],
        "stamplar": [{"namn": s, "antal": stamplar[s],
                      "betydelse": DATA["stamplar"][s]}
                     for s in sorted(DATA["stamplar"])],
        "antal_poster": len(POSTER),
        "index": _index_ut(),
        "notering": NOTERING,
    }


_lagg(
    "catalog_categories",
    "Vad det lokala katalogindexet faktiskt innehaller: kategorier, "
    "URI-grupper och hur manga poster som bar vilken harkomststampel. Las det "
    "har fore search_catalog om du inte vet vad som finns.",
    params({}),
    returns({
        "kategorier": {"type": "array",
                       "description": "Kategorierna och antal poster i var och en.",
                       "items": {"type": "object", "description": "En kategori.",
                                 "properties": {
                                     "namn": {"type": "string", "description": "Kategorins namn."},
                                     "antal": {"type": "integer", "description": "Antal poster."}},
                                 "required": ["namn", "antal"]}},
        "grupper": {"type": "array",
                    "description": "URI-grupperna, alltsa segmentet efter bank://.",
                    "items": {"type": "object", "description": "En URI-grupp.",
                              "properties": {
                                  "namn": {"type": "string", "description": "Gruppens namn."},
                                  "antal": {"type": "integer", "description": "Antal poster."}},
                              "required": ["namn", "antal"]}},
        "stamplar": {"type": "array",
                     "description": "Harkomststamplarna, med betydelse och antal.",
                     "items": {"type": "object", "description": "En stampel.",
                               "properties": {
                                   "namn": {"type": "string", "description": "Stampelns namn."},
                                   "antal": {"type": "integer", "description": "Antal poster med stampeln."},
                                   "betydelse": {"type": "string", "description": "Vad stampeln betyder."}},
                               "required": ["namn", "antal", "betydelse"]}},
        "antal_poster": {"type": "integer", "description": "Antal poster i indexet."},
        "index": _RET_INDEX,
        "notering": _RET_NOTERING,
    }, ["kategorier", "grupper", "stamplar", "antal_poster", "index", "notering"]),
    _catalog_categories,
)


# ---- det INSTALLERADE biblioteket ----------------------------------------
#
# De tre verktygen ovan soker i bank/katalog_index.json: 65 handskrivna poster
# som bankens uppgifter binder mot. De tva nedan soker i det bibliotek som
# faktiskt ligger pa maskinen - 3201 komponenter fran 149 tillverkare (M-57).
#
# Tva kallor och inte en, med flit. Bankens vokabular ar ett KONTRAKT: en
# uppgift som pekar pa en URI dar maste fortsatta gora det, annars faller
# lintkoden M4_UNKNOWN_URI och femtio uppgifter blir ogiltiga. Att sla ihop dem
# hade varit att andra ett kontrakt for att slippa forklara en skillnad.
#
# Skillnaden forklaras i stallet, i bada verktygens beskrivning: banken bar det
# uppgifterna handlar om, biblioteket bar det som gar att bygga med HAR.

_BIBLIOTEK = {"katalog": None, "skal": None}


def _bibliotek():
    """Katalogen over det installerade biblioteket, byggd en gang.

    Byggs LAT och DJUPT.

    Lat, darfor att upptackten och genomgangen kostar, och det ska inte betalas
    av en tjanst som kanske aldrig fragar.

    Djupt, darfor att familjen bara finns dar. MATT (M-69): familjemarkoren
    ligger vid median 14 215 byte och p95 81 593, sa en huvudlasning pa 4096
    byte hittar den i tva procent av fallen. Utan familj filtrerar verktyget pa
    katalognamn, och da missar det var fjarde robot och fyra av fem
    transportorer - vilket ar precis felet M-59 hittade i den forsta versionen.

    Priset ar mätt: 1,8 sekunder grunt mot 12,8 djupt over 3201 komponenter,
    en gang per process. Tolv sekunder for att sluta missa 164 transportorer ar
    en bra affar.

    Misslyckas bygget lagras SKALET, inte ett tomt resultat - ett tomt
    bibliotek och ett bibliotek som inte hittades ar tva olika svar (I3).
    """
    if _BIBLIOTEK["katalog"] is not None or _BIBLIOTEK["skal"] is not None:
        return _BIBLIOTEK["katalog"], _BIBLIOTEK["skal"]
    try:
        from .. import katalogindex, katalogsok
    except ImportError as fel:
        _BIBLIOTEK["skal"] = "katalogmodulerna gar inte att importera: %s" % fel
        return None, _BIBLIOTEK["skal"]
    fynd = katalogindex.hitta()
    if not fynd:
        provade = ", ".join(sokvag for sokvag, _hur in katalogindex.kandidatrotter())
        _BIBLIOTEK["skal"] = ("inget installerat komponentbibliotek hittades. "
                              "Provade: %s" % provade)
        return None, _BIBLIOTEK["skal"]
    try:
        index = katalogindex.bygg(fynd[0].rot, djupt=True)
    except Exception as fel:
        _BIBLIOTEK["skal"] = "biblioteket gick inte att lasa: %s" % fel
        return None, _BIBLIOTEK["skal"]
    index["hittat_via"] = fynd[0].hur
    _BIBLIOTEK["katalog"] = katalogsok.Katalog.fran_index(index)
    _BIBLIOTEK["katalog"].hittat_via = fynd[0].hur
    return _BIBLIOTEK["katalog"], None


def _nollstall_bibliotek():
    """Bara for proven. Drift bygger indexet en gang och behaller det."""
    _BIBLIOTEK["katalog"] = None
    _BIBLIOTEK["skal"] = None


_BIBLIOTEKSTRAFF = {
    "type": "object",
    "description": "En komponent i det installerade biblioteket.",
    "properties": {
        "namn": {"type": "string", "description": "Komponentens namn ur dess metadata."},
        "tillverkare": {"type": "string", "description": "Tillverkaren, ur katalogtradet."},
        "familj": {"type": ["string", "null"],
                   "description": ("Vad komponenten ar, last ur dess STRUKTUR: "
                                   "robot, transportor eller verktyg. Null nar "
                                   "indexet ar grunt eller ingen markor fanns. "
                                   "Det har ar det sanna mattet - kategorin ar "
                                   "det inte (M-69).")},
        "kategori": {"type": "string",
                     "description": ("Kategorin. I ett grunt index kommer den fran "
                                     "KATALOGNAMNET och inte ur metadatans eget "
                                     "Category-falt - tva olika storheter (M-58). "
                                     "Ingendera ar samma sak som familj.")},
        "fil": {"type": "string",
                "description": "Sokvagen till .vcmx-filen. Det ar den som laddas."},
        "rackvidd_mm": {"type": ["number", "null"],
                        "description": ("Robotens rackvidd i millimeter, DEKLARERAD i "
                                        "komponentens katalogpost. Null nar faltet "
                                        "saknas - det betyder INTE noll (M-76: 2556 "
                                        "av 3201 bar det).")},
        "nyttolast_kg": {"type": ["number", "null"],
                         "description": ("Hogsta nyttolast i kilogram, deklarerad. Null "
                                         "nar faltet saknas (2986 av 3201).")},
        "utfasad": {"type": "boolean",
                    "description": ("Komponenten ar markt IsDeprecated av tillverkaren. "
                                    "73 av 3201 ar det, och de utelamnas om du inte "
                                    "ber om dem.")},
        "granssnitt": {"type": ["integer", "null"],
                       "description": ("Antal granssnittsforekomster i metadatan, eller "
                                       "null nar indexet ar grunt och inte har rakmat dem.")},
    },
    "required": ["namn", "tillverkare", "familj", "kategori", "fil",
                 "granssnitt", "rackvidd_mm", "nyttolast_kg", "utfasad"],
    "additionalProperties": False,
}


def _traff_ut(t, djupt):
    return {"namn": t.namn, "tillverkare": t.tillverkare or "",
            "familj": (t.familj or None) if djupt else None,
            "kategori": t.kategori or "", "fil": t.sokvag,
            "rackvidd_mm": t.rackvidd_mm, "nyttolast_kg": t.nyttolast_kg,
            "utfasad": bool(t.utfasad),
            "granssnitt": (t.granssnitt if djupt else None)}


def _search_installed_library(argument):
    katalog, skal = _bibliotek()
    if katalog is None:
        return {"traffar": [], "antal": 0, "visade": 0, "sammandrag": None,
                "kalla": "inget bibliotek", "notering": skal}
    svar = katalog.sok(fraga=argument.get("query") or "",
                       tillverkare=argument.get("manufacturer") or "",
                       kategori=argument.get("category") or "",
                       har_parameter=argument.get("has_parameter") or "",
                       familj=argument.get("family") or "",
                       min_rackvidd_mm=argument.get("min_reach_mm"),
                       min_nyttolast_kg=argument.get("min_payload_kg"),
                       med_utfasade=bool(argument.get("include_deprecated")),
                       max_rader=int(argument.get("max_rows") or 10))
    ut = {
        "traffar": [_traff_ut(t, katalog.djupt) for t in svar.traffar],
        "antal": svar.totalt,
        "visade": svar.visade,
        "sammandrag": svar.sammandrag,
        "kalla": getattr(katalog, "hittat_via", "installerat bibliotek"),
        "notering": None,
    }
    if svar.sammandrag is not None:
        ut["notering"] = ("%d traffar ar for manga for en lista. Smalna av med "
                          "manufacturer, category eller ett namnfragment; "
                          "sammandrag visar fordelningen per tillverkare."
                          % svar.totalt)
    elif svar.visade < svar.totalt:
        ut["notering"] = ("%d av %d traffar visas. Hoj max_rows eller smalna av."
                          % (svar.visade, svar.totalt))
    return ut


_lagg(
    "search_installed_library",
    "Soker i det komponentbibliotek som FAKTISKT ar installerat pa maskinen. "
    "Filtren min_reach_mm och min_payload_kg laser DEKLARERADE falt ur "
    "komponentens katalogpost, sa en fraga som 'robot med minst 3 meters "
    "rackvidd och 200 kg nyttolast' gar att stalla rakt av. "
    "(3201 komponenter, 149 tillverkare, darav 2169 robotar och 163 "
    "transportorer). Det ar det har du valjer ur nar du ska BYGGA en scen. "
    "search_catalog soker i nagot annat: bankens 65 handskrivna poster, som "
    "uppgifterna binder mot. En bred fraga ger ett sammandrag i stallet for en "
    "lista - smalna av i stallet for att be om fler rader.",
    params({
        "query": {"type": "string",
                  "description": ("Delstrang i komponentens namn, okansligt for "
                                  "skiftlage. 'IRB 6700' traffar 'IRB 6700-150/3.20'.")},
        "manufacturer": {"type": "string",
                         "description": "Exakt tillverkarnamn, t.ex. ABB eller KUKA."},
        "family": {"type": "string", "enum": ["robot", "transportor", "verktyg"],
                   "description": ("Vad komponenten AR, last ur dess struktur. "
                                   "ANVAND DEN HAR och inte category: strukturen "
                                   "ger 2202 robotar och 227 transportorer, "
                                   "katalognamnet bara 1736 och 58 (M-69). Kraver "
                                   "ett djupt index.")},
        "category": {"type": "string",
                     "description": ("Exakt kategori, t.ex. Robots eller Conveyors. "
                                     "OBS: kategorin kommer ur katalognamnet eller "
                                     "ett falt och missar var fjarde robot och fyra "
                                     "av fem transportorer. Foredra family.")},
        "has_parameter": {"type": "string",
                          "description": ("Bara komponenter vars metadata namner en "
                                          "parameter med det har i namnet - VAR SOM "
                                          "HELST i komponenten, ocksa inne i en "
                                          "geometrilada. Det ar en namnlista, inte "
                                          "komponentens egenskaper (M-59). Kraver "
                                          "ett djupt index.")},
        "min_reach_mm": {"type": "number",
                         "description": ("Bara komponenter med minst den har "
                                         "rackvidden. En komponent UTAN angiven "
                                         "rackvidd slas bort - den har inte "
                                         "rackvidden noll, den saknar faltet.")},
        "min_payload_kg": {"type": "number",
                           "description": ("Bara komponenter med minst den har "
                                           "nyttolasten. Samma regel: saknat falt "
                                           "slas bort, det tolkas inte som noll.")},
        "include_deprecated": {"type": "boolean",
                               "description": ("Ta med komponenter som tillverkaren "
                                               "markt utfasade. Standard ar att "
                                               "utelamna dem (73 av 3201).")},
        "max_rows": {"type": "integer", "minimum": 1, "maximum": 50,
                     "description": "Hogsta antal rader i listan. Standard 10."},
    }),
    returns({
        "traffar": {"type": "array", "description": "Traffarna, kortast namn forst.",
                    "items": _BIBLIOTEKSTRAFF},
        "antal": {"type": "integer", "description": "Antal traffar totalt."},
        "visade": {"type": "integer", "description": "Hur manga av dem som star i traffar."},
        "sammandrag": {"type": ["object", "null"],
                       "description": ("Antal per tillverkare nar fragan var for bred "
                                       "for en lista. Null annars.")},
        "kalla": {"type": "string", "description": "Var biblioteket hittades, eller att inget hittades."},
        "notering": {"type": ["string", "null"],
                     "description": "Varfor svaret inte ar uttommande, eller null."},
    }, ["traffar", "antal", "visade", "sammandrag", "kalla", "notering"]),
    _search_installed_library,
)


def _library_overview(argument):
    katalog, skal = _bibliotek()
    if katalog is None:
        return {"antal": 0, "familjer": {}, "tillverkare": {}, "kategorier": {},
                "kalla": "inget bibliotek", "notering": skal}
    return {
        "antal": len(katalog.poster),
        "familjer": katalog.familjer(),
        "tillverkare": katalog.tillverkare(),
        "kategorier": katalog.kategorier(),
        "kalla": getattr(katalog, "hittat_via", "installerat bibliotek"),
        "notering": (None if katalog.djupt else
                     "Indexet ar grunt: kategorin kommer fran katalognamnet och "
                     "inte ur metadatans eget Category-falt (M-58)."),
    }


_lagg(
    "library_overview",
    "Vad det installerade biblioteket innehaller i stora drag: antal per "
    "tillverkare och per kategori. Fraga detta FORST nar du inte vet vad som "
    "finns, i stallet for att soka brett och fa ett sammandrag anda.",
    params({}),
    returns({
        "antal": {"type": "integer", "description": "Antal komponenter i biblioteket."},
        "familjer": {"type": "object",
                     "description": ("Familj -> antal, last ur strukturen. Tom "
                                     "nyckel betyder att ingen markor fanns. Det "
                                     "har ar det sanna mattet (M-69)."),
                     "additionalProperties": {"type": "integer"}},
        "tillverkare": {"type": "object", "description": "Tillverkare -> antal.",
                        "additionalProperties": {"type": "integer"}},
        "kategorier": {"type": "object", "description": "Kategori -> antal.",
                       "additionalProperties": {"type": "integer"}},
        "kalla": {"type": "string", "description": "Var biblioteket hittades."},
        "notering": {"type": ["string", "null"], "description": "Forbehall, eller null."},
    }, ["antal", "familjer", "tillverkare", "kategorier", "kalla", "notering"]),
    _library_overview,
)


# ---- component_datasheet -------------------------------------------------
#
# HALET DET STANGER, ordagrant ur M-84:s sista avsnitt:
#
#     "Indexet tacker API-symboler. Det tacker inte per-komponent-data:
#      komponenternas egenskapsnamn (ConveyorSpeed, StrokeTime, MaxPayload ...),
#      bank://-URI:erna, och VILKEN boolsk signal
#      findBehavioursByType(VC_BOOLEANSIGNAL)[0] ar pa en given komponent."
#
# search_installed_library svarar pa VILKEN komponent. Det har verktyget svarar
# pa vad DEN komponenten heter invandigt: egenskaperna med namn, typ,
# standardvarde och deklarerad storhet; beteendena och signalerna VID NAMN;
# granssnitten med vad de bar; lederna med sina granser.
#
# Svaret ar TEXT och inte en struktur, av samma skal som katalogsok:
# informationen ska vara lattillganglig for en sprakmodell, och en rad per
# egenskap ar billigare att lasa an en JSON-lista med fem nycklar per post.
# Den strukturerade sammanfattningen star bredvid for det som ska raknas pa.


def _hitta_komponentfil(fraga):
    """(sokvag, tillverkare, traffar) for ett komponentnamn.

    Exakt namn vinner over delstrang, och kortast namn vinner bland
    delstrangar - samma ordning som katalogsok sorterar i, och av samma skal:
    den som sokte pa "IRB 120" menade grundmodellen och inte
    "IRB 120-3/0.6 LID".
    """
    katalog, skal = _bibliotek()
    if katalog is None:
        return None, "", skal
    exakt = katalog.med_namn(fraga)
    if exakt is not None:
        return exakt.sokvag, exakt.tillverkare, None
    svar = katalog.sok(fraga=fraga, med_utfasade=True, max_rader=8)
    if svar.totalt == 0:
        return None, "", ("ingen komponent heter %r i det installerade "
                          "biblioteket. Sok med search_installed_library "
                          "forst." % fraga)
    if svar.sammandrag is not None:
        return None, "", ("%d komponenter matchar %r - for manga for att veta "
                          "vilken du menar. Smalna av med "
                          "search_installed_library forst." % (svar.totalt, fraga))
    t = svar.traffar[0]
    return t.sokvag, t.tillverkare, None


def _component_datasheet(argument):
    from .. import komponentdatablad as KD

    fraga = (argument.get("name") or "").strip()
    fil = (argument.get("file") or "").strip()
    if not fraga and not fil:
        return {"funnet": False, "datablad": None, "notering":
                "ange name (komponentens namn) eller file (sokvag till .vcmx)."}
    tillverkare = ""
    if not fil:
        fil, tillverkare, skal = _hitta_komponentfil(fraga)
        if fil is None:
            return {"funnet": False, "datablad": None, "notering": skal}
    try:
        blad = KD.las(fil, tillverkare=tillverkare)
    except Exception as felet:                      # noqa: BLE001
        # Fail-closed: ett datablad som inte gick att lasa ar INTE ett tomt
        # datablad. Skalet foljer med, sa att den som fragade kan se skillnad
        # pa "komponenten bar inga egenskaper" och "filen gick inte att oppna".
        return {"funnet": False, "datablad": None,
                "notering": "%s gick inte att lasa: %s: %s"
                            % (fil, type(felet).__name__, felet)}
    text = KD.text(
        blad,
        max_egenskaper=int(argument.get("max_properties")
                           or KD.MAX_EGENSKAPER),
        max_beteenden=int(argument.get("max_behaviours") or KD.MAX_BETEENDEN))
    boolska = blad.signaler_av_typ("rSimBoolSignal")
    return {
        "funnet": True,
        "datablad": text,
        "namn": blad.namn,
        "fil": blad.sokvag,
        "antal_egenskaper": len(blad.egenskaper),
        "egenskapsnamn": [e.namn for e in blad.egenskaper],
        "signalnamn": [s.namn for s in blad.signaler()],
        "boolska_signaler": [s.namn for s in boolska],
        "granssnittsnamn": [g.namn for g in blad.granssnitt],
        "antal_leder": len(blad.leder),
        "notering": None,
    }


_lagg(
    "component_datasheet",
    "Databladet for EN komponent ur det installerade biblioteket: dess EGNA "
    "egenskaper med namn, typ, standardvarde och deklarerad storhet; dess "
    "beteenden och signaler VID NAMN; dess granssnitt och vad de bar; dess "
    "leder med granser. Fraga detta INNAN du skriver getProperty('...') eller "
    "findBehaviour('...') - det ar de namnen som avgor om raden kor. "
    "Egenskaperna lases ur komponentens STRUKTUR (rotens variabelrymd) och ar "
    "darfor komponentens egna; search_installed_library:s has_parameter soker "
    "i hela filen och far med geometrins variabler (M-59). "
    "Enheter: kallan deklarerar en STORHET (Distance, Velocity, Angle ...) for "
    "14 procent av egenskaperna och ingen enhet alls. Star det saknas ska "
    "talet INTE forses med en enhet.",
    params({
        "name": {"type": "string",
                 "description": ("Komponentens namn. Exakt namn vinner; annars "
                                 "narmaste delstrangstraff. Ger flera an atta "
                                 "traffar blir svaret ett nej med skal.")},
        "file": {"type": "string",
                 "description": ("Sokvag till en .vcmx, nar du redan har den ur "
                                 "search_installed_library. Gar fore name.")},
        "max_properties": {"type": "integer", "minimum": 1, "maximum": 400,
                           "description": ("Hogsta antal egenskapsrader. "
                                           "Standard 47 = p90 over biblioteket "
                                           "(M-85). Kapas pa ANTAL RADER, "
                                           "aldrig mitt i en post.")},
        "max_behaviours": {"type": "integer", "minimum": 1, "maximum": 200,
                           "description": ("Hogsta antal beteenderader. "
                                           "Standard 20 = p99 (M-85).")},
    }),
    returns({
        "funnet": {"type": "boolean",
                   "description": "Om ett datablad kunde lasas. False bar alltid ett skal i notering."},
        "datablad": {"type": ["string", "null"],
                     "description": ("Databladet som text, i den ordning som "
                                     "avgor om en genererad rad kor: namn, "
                                     "egenskaper, signaler, beteenden, "
                                     "granssnitt, leder. null nar funnet ar false.")},
        "namn": {"type": "string", "description": "Komponentens namn ur dess katalogpost."},
        "fil": {"type": "string", "description": "Filen databladet lastes ur."},
        "antal_egenskaper": {"type": "integer", "description": "Antal egna egenskaper."},
        "egenskapsnamn": {"type": "array",
                          "items": {"type": "string",
                                    "description": "Ett exakt egenskapsnamn."},
                          "description": ("Exakta egenskapsnamn, for "
                                          "getProperty(). Listan ar ALLTID hel, "
                                          "aven nar databladets egenskapsavsnitt "
                                          "ar kapat vid max_properties - ett namn "
                                          "kostar 25 tecken och en rad 85. Tom "
                                          "lista betyder att rotens variabelrymd "
                                          "ar tom; 126 av 3201 komponenter har "
                                          "det (M-85).")},
        "signalnamn": {"type": "array",
                       "items": {"type": "string",
                                 "description": "En signals exakta namn."},
                       "description": "Signalbeteendena vid namn, i filens ordning."},
        "boolska_signaler": {"type": "array",
                             "items": {"type": "string",
                                       "description": "En boolsk signals exakta namn."},
                             "description": ("De BOOLSKA signalerna vid namn. Ar "
                                             "listan tom kastar "
                                             "findBehavioursByType(VC_BOOLEANSIGNAL)[0] "
                                             "IndexError - det galler 88 procent av "
                                             "biblioteket (M-85). Har den ett enda "
                                             "namn ar [0] entydigt. Har den flera ar "
                                             "ordningen filens, inte API:ets: anvand "
                                             "findBehaviour(namn).")},
        "granssnittsnamn": {"type": "array",
                            "items": {"type": "string",
                                      "description": "Ett granssnitts exakta namn."},
                            "description": "Granssnitten vid namn, for connectComponents."},
        "antal_leder": {"type": "integer", "description": "Antal leder med granser."},
        "notering": {"type": ["string", "null"],
                     "description": "Varfor svaret inte bar ett datablad, eller null."},
    }, ["funnet", "datablad", "notering"]),
    _component_datasheet,
)
