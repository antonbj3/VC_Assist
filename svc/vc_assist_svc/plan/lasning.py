# -*- coding: utf-8 -*-
"""Vad som gar att lasa UR operatorens text, och belagget for varje tal.

Modulen har ett enda uppdrag: gora om fri text till typade krav UTAN att hitta
pa nagot. Regeln ar mekanisk och inte en ambition:

    VARJE UTLAST VARDE BAR DEN ORDAGRANNA TEXTBIT DET LASTES UR.

Belagget ar inte en artighet. Harkomst("begaran", belagg) provas mot begaran
med en delstrangsmatchning (harkomst.py), sa ett krav som pastar sig komma ur
operatorens text men vars ord inte star dar FALLER mekaniskt. Det ar den enda
kontrollen som skiljer "operatoren bad om det" fran "vi tyckte det".

VAD SOM INTE GAR ATT LASA BLIR EN FRAGA, ALDRIG ETT VARDE

Modulen laser bara det som star. Den kompletterar aldrig, den avrundar aldrig
och den gissar aldrig en enhet. Det som inte star lamnas at forfining.py, som
har de tva enda vagarna in i en spec: anta() med motiv eller fraga().

DE SLUTNA LISTORNA

Bade komponentorden (forfining.ORDBOK) och processorden (PROCESSORD har) ar
slutna listor. En prefixmatchning hade last "pallmagasin" som "pall" och gett
en lastbarare ingen bett om; en oppen verblista hade gjort vilket ord som helst
till en process. Listorna vaxer med en matning, inte med ett infall.

Endast standardbiblioteket.
"""
from __future__ import annotations

import re

from .harkomst import normalisera

# Enheter som far sta i en begaran, och deras faktor till millimeter. VC:s
# varldsenhet ar millimeter (M-33), sa allt raknas dit direkt - en enhet som
# barsomen text tills senare ar en enhet som glomms bort.
_TILL_MM = {"mm": 1.0, "cm": 10.0, "dm": 100.0, "m": 1000.0, "meter": 1000.0,
            "metern": 1000.0}

_ENHET = r"(mm|cm|dm|meter|metern|m)\b"
_TAL = r"(\d+(?:[.,]\d+)?)"


def _tal(text):
    return float(str(text).replace(",", "."))


def _mm(tal, enhet):
    return _tal(tal) * _TILL_MM[enhet.lower()]


class Utlast(object):
    """Ett varde och den textbit det lastes ur."""

    __slots__ = ("varde", "belagg", "vad")

    def __init__(self, varde, belagg, vad=""):
        self.varde = varde
        self.belagg = belagg
        self.vad = vad

    def __repr__(self):
        return "Utlast(%s = %r ur %r)" % (self.vad, self.varde, self.belagg)


def _traff(text, monster):
    """(traff, den ordagranna textbiten) for varje traff.

    Monstret far vara bade en strang och ett kompilerat monster: de fardiga
    ligger som konstanter, ordningsformerna byggs som strangar.
    """
    if isinstance(monster, str):
        monster = re.compile(monster, re.I)
    for m in monster.finditer(text or ""):
        yield m, text[m.start():m.end()]


# --------------------------------------------------------------- cellytan

# "hogst 2x2 meter", "max 2 x 2 m", "en yta pa 4 x 3 meter", "cellen ar 2x2 m"
_YTA = re.compile(
    r"(?:h[oö]gst|max(?:imalt)?|inom|p[aå] en yta (?:p[aå]|av)|yta[nr]?\s*(?:p[aå]|av)?|"
    r"cellen (?:f[aå]r vara|ska vara|[aä]r))?\s*"
    + _TAL + r"\s*[x×]\s*" + _TAL + r"\s*" + _ENHET, re.I)

# "hogst 2 meter bred", "minst 3 m djup"
_SIDA = re.compile(
    r"(h[oö]gst|max(?:imalt)?|minst|minimum)\s*" + _TAL + r"\s*" + _ENHET
    + r"\s*(bred|bredd|djup|l[aå]ng|l[aä]ngd|h[oö]g|h[oö]jd)", re.I)

_GANG = re.compile(
    r"(?:g[aå]ng(?:str[aå]k|v[aä]g|bredd)?|passage|fri (?:bredd|yta))\D{0,12}?"
    + _TAL + r"\s*" + _ENHET, re.I)

_RACKVIDD = re.compile(
    r"(r[aä]ckvidd|arbetsradie|arbetsomr[aå]de)\D{0,8}?" + _TAL
    + r"\s*" + _ENHET, re.I)

# Ord som gor rackvidden till ett KRAV pa roboten i stallet for en uppgift om
# den. "rackvidd 1650 mm" ar robotens egenskap; "arbetsradie 1500 mm" ar vad
# uppgiften kraver av den. Blandas de ihop gar motsagelsen mellan dem forlorad.
_KRAVORD = ("arbetsradie", "arbetsomrade", "arbetsområde")

_SIDONAMN = {"bred": "bredd_mm", "bredd": "bredd_mm", "djup": "djup_mm",
             "lang": "bredd_mm", "lång": "bredd_mm", "langd": "bredd_mm",
             "längd": "bredd_mm", "hog": "hojd_mm", "hög": "hojd_mm",
             "hojd": "hojd_mm", "höjd": "hojd_mm"}

# Ord som gor en gransangivelse till ett TAK eller ett GOLV. Star inget av dem
# ar talet ett konstaterande ("cellen ar 2x2 m") och inte ett krav.
_TAK = ("hogst", "högst", "max", "maximalt", "inom")
_GOLV = ("minst", "minimum")


def cellmatt(text):
    """[(falt, operator, mm, belagg)] for cellens matt ur texten.

    `operator` ar 'le' for ett tak, 'ge' for ett golv och 'eq' for ett
    konstaterande. Skillnaden ar viktig: 'hogst 2x2 m' och 'cellen ar 2x2 m'
    ar inte samma krav, och att lasa det ena som det andra vore precis den
    tysta omskrivningen harkomstgrinden finns for att fanga.
    """
    ut = []
    for m, belagg in _traff(text, _YTA):
        inledning = normalisera(belagg)
        operator = "eq"
        if any(o in inledning for o in _TAK):
            operator = "le"
        elif any(o in inledning for o in _GOLV):
            operator = "ge"
        bredd = _mm(m.group(1), m.group(3))
        djup = _mm(m.group(2), m.group(3))
        ut.append(("bredd_mm", operator, bredd, belagg))
        ut.append(("djup_mm", operator, djup, belagg))
    for m, belagg in _traff(text, _SIDA):
        ord_ = normalisera(m.group(1))
        operator = "le" if ord_ in _TAK else "ge"
        falt = _SIDONAMN.get(normalisera(m.group(4)))
        if falt:
            ut.append((falt, operator, _mm(m.group(2), m.group(3)), belagg))
    return ut


def gangstrak(text):
    """Utlast med minsta gangstraket i mm, eller None."""
    for m, belagg in _traff(text, _GANG):
        return Utlast(_mm(m.group(1), m.group(2)), belagg, "gang_min_mm")
    return None


def rackvidd(text):
    """[Utlast] med rackvidder i mm, i textens ordning.

    Formen finns darfor att rackvidden ar svar att sla upp, och hur svar beror
    pa VAR man tittar. MATT i M-63 over hela komponentbiblioteket: 0 av 2169
    robotar bar ett reach-falt i component.rsc (det katalogindex.py laser),
    men 1434 av 2169 bar `Reach` i model.xml (det komponentfil.py laser).
    Samma fraga, tva svar, och skillnaden ar filen. Star talet i begaran ar
    det darfor ofta det snabbaste och alltid det billigaste.
    """
    ut = []
    for m, belagg in _traff(text, _RACKVIDD):
        ord_ = normalisera(m.group(1))
        ut.append(Utlast(_mm(m.group(2), m.group(3)), belagg,
                         "krav" if ord_ in _KRAVORD else "egenskap"))
    return ut


# ------------------------------------------------------------- processerna

# Sluten lista: ord i begaran -> (process-id, vad processen ar).
# Ordningen ar en TUPEL sa att samma text alltid ger samma processer.
PROCESSORD = (
    ("mata in", "inmatning", "mata in material i cellen"),
    ("inmatning", "inmatning", "mata in material i cellen"),
    ("matas in", "inmatning", "mata in material i cellen"),
    ("plocka", "plockning", "plocka detaljen"),
    ("plockning", "plockning", "plocka detaljen"),
    ("spanna", "spanning", "spanna fixturen"),
    ("spanning", "spanning", "spanna fixturen"),
    ("svetsa", "svetsning", "svetsa detaljen"),
    ("svetsning", "svetsning", "svetsa detaljen"),
    ("mala", "malning", "mala detaljen"),
    ("malning", "malning", "mala detaljen"),
    ("lackera", "malning", "mala detaljen"),
    ("skruva", "skruvning", "skruva ihop detaljen"),
    ("skruvning", "skruvning", "skruva ihop detaljen"),
    ("limma", "limning", "limma detaljen"),
    ("limning", "limning", "limma detaljen"),
    ("pressa", "pressning", "pressa detaljen"),
    ("pressning", "pressning", "pressa detaljen"),
    ("montera", "montering", "montera ihop delarna"),
    ("montering", "montering", "montera ihop delarna"),
    ("kontrollera", "kontroll", "kontrollera resultatet"),
    ("kontroll", "kontroll", "kontrollera resultatet"),
    ("matning", "matning", "mata detaljen"),
    ("packa", "packning", "packa detaljen"),
    ("packning", "packning", "packa detaljen"),
    ("mata ut", "utmatning", "mata ut fardig detalj"),
    ("utmatning", "utmatning", "mata ut fardig detalj"),
    ("lasta ut", "utmatning", "mata ut fardig detalj"),
)

_PROCESSNAMN = dict((ord_, (pid, vad)) for ord_, pid, vad in PROCESSORD)

# Ordningsuttryck. Varje monster ger (fore, efter) i den ordning grupperna
# star. Listan ar sluten och varje rad ar en form nagon faktiskt skriver.
_ORDNINGSFORMER = (
    (r"f[oö]rst\s+(?P<a>[a-zåäö ]{3,20}?)\s*,?\s*(?:och\s+)?(?:sedan|darefter|"
     r"d[aä]refter|d[aä]rp[aå])\s+(?P<b>[a-zåäö ]{3,20}?)\b", "ab"),
    (r"(?P<a>[a-zåäö ]{3,20}?)\s+(?:ska ske\s+)?(?:f[oö]re|innan)\s+"
     r"(?P<b>[a-zåäö ]{3,20}?)\b", "ab"),
    (r"efter\s+(?P<a>[a-zåäö ]{3,20}?)\s+(?:kommer|f[oö]ljer|sker|ska)\s+"
     r"(?P<b>[a-zåäö ]{3,20}?)\b", "ab"),
    (r"(?P<b>[a-zåäö ]{3,20}?)\s+(?:sker\s+|kommer\s+)?efter\s+"
     r"(?P<a>[a-zåäö ]{3,20}?)\b", "ab"),
)


def _hela_ordet(ord_, normaliserad_text):
    """Star ordet som ett EGET ord, inte inuti ett annat?

    MATT nar jag korde operatorens egen exempeltext (M-63): en ren
    delstrangsmatchning laste 'inmatningsband' som BADE processen 'inmatning'
    OCH processen 'matning'. Bestallningen fick alltsa tva processer den aldrig
    namnde, och bada bar en 'harkomst' som pekade rakt in i operatorens text -
    belagget var akta, tolkningen var pahittad. Ordgranser ar darfor inte en
    finess utan grinden mot precis det.
    """
    monster = r"\b%s\b" % re.escape(ord_).replace(r"\ ", r"\s+")
    return re.search(monster, normaliserad_text) is not None


def _process_i(bit):
    """Process-id och beskrivning ur en textbit, eller None.

    Den LANGSTA traffen vinner: 'mata ut' ska inte lasas som 'mata'. Samma
    regel som forfiningens andelselista har, och av samma skal.
    """
    n = normalisera(bit)
    for ord_ in sorted(_PROCESSNAMN, key=len, reverse=True):
        if _hela_ordet(ord_, n):
            return (_PROCESSNAMN[ord_][0], _PROCESSNAMN[ord_][1], ord_)
    return None


def processer(text):
    """([(pid, vad, belagg)], [(fore, efter, belagg)]).

    Processerna kommer bara ur de ord som star i den slutna listan, och varje
    ordningskrav bar den mening det lastes ur.
    """
    hittade = {}
    ordningar = []
    for monster, _form in _ORDNINGSFORMER:
        for m, belagg in _traff(text, monster):
            a = _process_i(m.group("a"))
            b = _process_i(m.group("b"))
            if not a or not b or a[0] == b[0]:
                continue
            hittade.setdefault(a[0], (a[1], belagg))
            hittade.setdefault(b[0], (b[1], belagg))
            if (a[0], b[0]) not in [(f, e) for f, e, _b in ordningar]:
                ordningar.append((a[0], b[0], belagg))
    # Processer som namns utan ordning ska ocksa med: de ska utforas, aven om
    # ingen sagt nar. Att tiga om dem hade tappat halva bestallningen.
    normaliserad = normalisera(text)
    for ord_ in sorted(_PROCESSNAMN, key=len, reverse=True):
        if not _hela_ordet(ord_, normaliserad):
            continue
        pid, vad = _PROCESSNAMN[ord_]
        if pid in hittade:
            continue
        belagg = _belagg_for(text, ord_)
        if belagg:
            hittade[pid] = (vad, belagg)
    ut = [(pid, hittade[pid][0], hittade[pid][1]) for pid in sorted(hittade)]
    return ut, ordningar


def _belagg_for(text, ord_):
    """Den ordagranna biten i den ursprungliga texten som gav ordet.

    Normaliseringen kan ha bytt a-ring mot a, sa traffen soks i den
    normaliserade texten och samma teckenintervall plockas ur originalet.
    Det haller belagget ordagrant, vilket ar hela poangen med det.
    """
    n = normalisera(text)
    i = n.find(ord_)
    if i < 0:
        return ""
    # Normaliseringen kan ha kortat text (flera blanksteg -> ett), sa
    # intervallet ar en uppskattning. Bekraftas belagget inte av
    # harkomstkontrollen ar det inget belagg, och da anvands ordet sjalvt.
    bit = text[i:i + len(ord_)]
    return bit if normalisera(bit) == ord_ else ord_


# --------------------------------------------------- komponentupprakningen

# Artiklar och rakneord som star framfor en komponent i en upprakning. Listan
# ar sluten: den ska ta bort "ett" och "tva", inte gissa vad som ar ett
# substantiv.
_ARTIKLAR = ("en", "ett", "den", "det", "tva", "tre", "fyra", "fem", "sex",
             "sju", "atta", "nio", "tio", "flera", "nagra", "ytterligare")

# Upprakningen efter "med": "med ett inmatningsband, en robot och en
# utlastningslada". Den stannar vid meningsslut.
_MED = re.compile(r"\bmed\s+([^.;\n]{3,200})", re.I)
_DELARE = re.compile(r"\s*(?:,|\boch\b|\bsamt\b)\s*", re.I)


def komponentupprakning(text):
    """[(ordagrann bit, orden i den)] for varje post i en 'med'-upprakning.

    MATT i M-63 pa operatorens EGEN exempeltext ur 27_operatorsflodet:
    "med ett inmatningsband, en robot och en utlastningslada" gav EN
    komponent - roboten - och planen blev BYGGBAR med en tredjedel av det
    operatoren bad om. Ett tyst bortfall som sag ut som ett ja.

    Funktionen laser upprakningen sjalv, sa att forfining.py kan FRAGA om de
    ord den inte kanner igen i stallet for att tiga om dem. Den avgor inte vad
    orden betyder; den sager bara att de stod dar.
    """
    ut = []
    for m, _belagg in _traff(text, _MED):
        for bit in _DELARE.split(m.group(1)):
            bit = bit.strip()
            if not bit:
                continue
            ord_ = [o for o in _ORD_I_BIT.findall(normalisera(bit))
                    if o not in _ARTIKLAR]
            if ord_:
                ut.append((bit, ord_))
    return ut


_ORD_I_BIT = re.compile(r"[a-z0-9]+")


# ------------------------------------------------------------ kopplingarna

# Hur en koppling skrivs i fri text. Listan ar sluten: en oppen lista hade
# gjort vilket ord som helst mellan tva roller till en koppling, och topologin
# ar det som styr hela geometrin.
_KOPPLINGSORD = (r"->", r"=>", r"→", r"till", r"kopplas till", r"kopplad till",
                 r"matar in i", r"matar", r"vidare till")

_ANDELSER = ("", "en", "et", "n", "t", "ar", "arna", "erna", "or", "orna", "er")


def kopplingar(text, roller):
    """[(fran_roll, till_roll, belagg)] ur uttryck som 'bandet -> roboten'.

    Bara par dar BADA orden ar kanda roller blir en koppling. Ett ord vi inte
    har en roll for ger ingen koppling alls - och forfining.py gor da en fraga
    av det, i stallet for att koppla ihop nagot pa mafa. Topologin gissas
    aldrig: ordningen orden rakade sta i texten ar inget belagg for vad som
    ska sitta ihop.
    """
    n = normalisera(text)
    ut = []
    for a in roller:
        for b in roller:
            if a == b:
                continue
            for ord_ in _KOPPLINGSORD:
                monster = (r"%s\s*%s\s*%s"
                           % (_rollmonster(a), ord_, _rollmonster(b)))
                m = re.search(monster, n)
                if not m:
                    continue
                if (a, b) not in [(x, y) for x, y, _b in ut]:
                    ut.append((a, b, _ur_original(text, n, m)))
                break
    return ut


def _rollmonster(roll):
    return "%s(?:%s)?" % (re.escape(normalisera(roll)),
                          "|".join(a for a in _ANDELSER if a))


def _ur_original(text, normaliserad, m):
    """Den ordagranna biten ur ursprungstexten som traffen svarar mot.

    Normaliseringen kan ha kortat text (flera blanksteg -> ett), sa
    intervallet ar en uppskattning. Bekraftas den inte av normaliseringen
    anvands den normaliserade biten - den star kvar som belagg, och
    harkomstgrinden jamfor anda normaliserat mot normaliserat.
    """
    bit = text[m.start():m.end()]
    return bit if normalisera(bit) == m.group(0) else m.group(0)


# ---------------------------------------------------------- rackviddskravet

_NA = re.compile(r"ska\s+(?:kunna\s+)?n[aå]\s+(?P<mal>[^.;\n]{3,80})", re.I)


def nakrav(text, roller):
    """[(fran_roll, till_roll, belagg)] ur meningar av formen 'X ska na Y'.

    Rollnamnen kommer ur specen, inte ur en gissning: bara ord som ar en
    KAND roll blir en relation. En mening som namner nagot vi inte har en roll
    for ger ingen relation alls - och forfining.py gor da en fraga av det, i
    stallet for att koppla ihop nagot pa mafa.
    """
    ut = []
    kanda = list(roller)
    for m, belagg in _traff(text, _NA):
        fore = text[:m.start()]
        fran = _sista_rollen(fore, kanda)
        if fran is None:
            continue
        for roll in kanda:
            if roll == fran:
                continue
            if _namner(m.group("mal"), roll):
                if (fran, roll) not in [(a, b) for a, b, _ in ut]:
                    ut.append((fran, roll, belagg))
    return ut


def _namner(bit, roll):
    n = normalisera(bit)
    r = normalisera(roll)
    return any(r + andelse in n for andelse in ("", "en", "et", "n", "t",
                                                "ar", "arna", "erna", "or",
                                                "orna", "er"))


def _sista_rollen(text, roller):
    """Den roll som namns SENAST fore uttrycket - meningens subjekt."""
    n = normalisera(text)
    bast = None
    for roll in roller:
        i = n.rfind(normalisera(roll))
        if i >= 0 and (bast is None or i > bast[0]):
            bast = (i, roll)
    return bast[1] if bast else None
