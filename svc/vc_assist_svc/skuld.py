# -*- coding: utf-8 -*-
"""Skuldregistret: teknisk skuld fangad NAR den skrivs, inte vid en senare granskning.

Operatorens krav: "Kom ihag nu att reviewa och halla koll pa mojlig teknisk
skuld och saker som senare behover goras om" - och skarpningen: "Vi fangar det
at moment of writing foredragsvis."

VARFOR REGISTRET GENERERAS OCH INTE FORS
----------------------------------------
Ett register nagon maste komma ihag att uppdatera ar redan glomt. Den enda
skulden som hamnar i ett sadant register ar den man ando kom ihag, alltsa inte
den farliga.

Darfor for ingen det har registret. Det HARVAS ur det som redan skrivs:

  * matningarnas arlighetsavsnitt - "Vad som INTE ar matt", "Vad som inte ar
    provat", "Vad detta INTE bevisar" och deras syskon. Disciplinen finns redan
    (MATT: 30 av 43 matningar bar ett sadant avsnitt), och den skrivs samtidigt
    som matningen. Det ar precis "moment of writing".
  * markorer i koden - PRELIMINAR, "inte lagat", "oppen punkt", "kvar som",
    "oprovad". De skrivs ocksa i samma andetag som koden.

Foljden ar att skulden inte kan glida ifran verkligheten: andrar nagon en
matning andras registret nasta gang det byggs, och tar nagon bort ett
arlighetsavsnitt SYNS det som en minskning som lintern faller pa.

VAD REGISTRET INTE ER
---------------------
Det ar ingen prioriteringslista och ingen plan. Det ar en sammanstallning av
vad vi redan har skrivit att vi inte vet. Att bedoma vad som ska goras forst ar
ett annat arbete, och det ska inte smyga in har.
"""
from __future__ import annotations

import ast
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


def _avdiakritik(text):
    """Rubriken utan sina prickar: "Rackvidd" ur "Räckvidd".

    VARFOR: monstret nedan ar skrivet i ASCII, som all kod i det har repot.
    Matningarna ar skrivna i riktig svenska. MATT 2026-09-04 (M-70): av elva
    grenar i det gamla monstret fyrade TRE nagonsin i repot. De atta ovriga bar
    ett translittererat a, a eller o - "rackvidd", "oppna fragor",
    "begransningar", "forbehall", "oprovat", "rattelserna", "de har" - och kunde
    darfor aldrig matcha en verklig rubrik. Tva av dem var tillagda just for att
    fanga M-44 ("Rackvidd", "Vad rattelserna medvetet INTE gor") och M-47
    ("Vad de har matten INTE sager"), och fangade ingen av dem.

    Det ar samma felklass som M-66 sjalv rattade en gang: ett monster som ser ut
    att matcha, aldrig provat mot den text det ska lasa.
    """
    return "".join(t for t in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(t))


# Rubrikerna som markerar ett arlighetsavsnitt. Provas mot rubriken UTAN
# diakritik (se _avdiakritik), sa "Rackvidd" och "Rackvidd" ar samma sak for
# monstret. Listan ar MATT ur matningarna i repot, inte paahittad - se M-66 och
# M-70. Den ar medvetet bred: en matning som skriver "Vad som fortfarande inte
# fungerar" har gjort ratt sak, och ska inte falla pa att den valde ett annat
# ord.
#
# GRANSEN: en bar rubrik "Oppet" raknas INTE. "Oppet API" och "Oppet lage" ar
# lika rimliga rubriker, och en gren som fyrar pa dem mater fel storhet. Ett
# arlighetsavsnitt som heter "Oppet" maste namna vad som ar oppet - "Oppen
# fraga", "Oppna punkter" - eller bara heta "Vad som INTE ar matt".
_ARLIGHET = re.compile(
    r"^#{2,4}\s+"
    # Rubriken kan bara ett nummer eller en fallkod forst: "## 9. Vad som ..."
    # eller "### F9. Sadant som ...". MATT: bada formerna finns i repot, och en
    # regex som kraver att rubriken borjar med ordet missar dem tyst.
    r"(?:[0-9]+\.|[A-ZF][0-9]+\.|\d+\.\d+)?\s*"
    r"(?:"
    # "Vad ... inte ...", med upp till fyra ord emellan. Det ersatter en
    # handskriven ordlista (detta|de har|lintern|tolken|rattelserna|jag) som
    # var byggd ur de rubriker nagon rakade minnas. MATT: den missade "Vad de
    # har matten INTE sager" aven translittererad, for att ordet "matten" stod
    # mellan listan och "INTE".
    r"vad\s+(?:\S+\s+){0,4}?(?:inte|INTE)\b.*"
    r"|vad\s+som\s+ligger\s+utanfor\b.*"
    r"|fynd\s+jag\s+(?:inte|INTE)\b.*"
    r"|.*\boprovad?t?e?\b.*"
    r"|.*\bomatt[ae]?\b.*"
    r"|.*\bobevisad[et]?\b.*"
    r"|.*\bopp(?:en|et|na)\s+(?:punkt|punkter|fraga|fragor)\b.*"
    r"|.*\bkvar\s+att\s+gora\b.*"
    r"|rackvidd(?:en)?\s*$"
    r"|.*\bforbehall\b.*"
    r"|.*\bbegransningar?\b.*"
    # LIMITS star i guldgrindens OBLIGATORISKA_SEKTIONER - systemet KRAVER
    # ordet av ogats rapporter men registret kunde inte se det i en
    # matning. Tva delar av samma system var alltsa oense om vad ett
    # arlighetsavsnitt heter, och sparren fangade det pa M-84.
    r"|limits\b.*"
    r"|limitations\b.*"
    r")$",
    re.I | re.M)


def ar_arlighetsrubrik(rad):
    """Sant om raden ar en rubrik som annonserar granser."""
    return _ARLIGHET.match(_avdiakritik(rad)) is not None


# Markorer i kod och dokument som betyder "det har ar inte fardigt".
_KODMARKOR = re.compile(
    r"\b(PRELIMIN[AÄ]R|TODO|FIXME|XXX|oprovad[et]?|inte lagat|inte lagad[et]?|"
    r"oppen punkt|öppen punkt|kvar som en uttalad|inte provat|inte prövat)\b",
    re.I)

# Filer som INTE ska genomsokas efter kodmarkorer. Registret sjalvt och dess
# prov namner markorerna for att kunna kanna igen dem, och skulle annars
# rapportera sig sjalvt - en grind som far sin egen utdata som indata.
_UNDANTAG = ("skuld.py", "test_skuld.py", "SKULDREGISTER.md",
             "TROSKELSKULD.md", "M-66")


@dataclass
class Post:
    """En skuldpost: var den star, vad den sager."""

    kalla: str
    sort: str          # "matning" eller "kod"
    rubrik: str
    rader: List[str] = field(default_factory=list)

    @property
    def antal(self) -> int:
        return len(self.rader)


def _undantagen(sokvag: str) -> bool:
    return any(u in sokvag for u in _UNDANTAG)


def ur_matning(sokvag: str) -> List[Post]:
    """Arlighetsavsnitten i en matning, med sina punkter."""
    with open(sokvag, "r", encoding="utf-8") as f:
        text = f.read()
    rader = text.splitlines()
    ut: List[Post] = []
    i = 0
    while i < len(rader):
        rad = rader[i]
        if ar_arlighetsrubrik(rad):
            niva = len(rad) - len(rad.lstrip("#"))
            punkter: List[str] = []
            j = i + 1
            while j < len(rader):
                nasta = rader[j]
                if nasta.startswith("#"):
                    n2 = len(nasta) - len(nasta.lstrip("#"))
                    if n2 <= niva:
                        break
                if nasta.strip().startswith(("*", "-")):
                    punkter.append(nasta.strip().lstrip("*- ").strip())
                j += 1
            ut.append(Post(os.path.basename(sokvag), "matning",
                           rad.lstrip("# ").strip(), punkter))
            i = j
            continue
        i += 1
    return ut


def ur_kod(rot: str, andelser=(".py", ".mjs")) -> List[Post]:
    """Markorer i koden. En rad per traff, med sin egen text."""
    ut: List[Post] = []
    for katalog, kataloger, filer in os.walk(rot):
        kataloger[:] = [k for k in kataloger
                        if k not in ("__pycache__", ".git", "node_modules")]
        for f in sorted(filer):
            if not f.endswith(andelser):
                continue
            sokvag = os.path.join(katalog, f)
            if _undantagen(sokvag):
                continue
            try:
                with open(sokvag, "r", encoding="utf-8") as fh:
                    rader = fh.read().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            traffar = [("%s:%d" % (os.path.relpath(sokvag, rot), n + 1),
                        r.strip())
                       for n, r in enumerate(rader) if _KODMARKOR.search(r)]
            if traffar:
                ut.append(Post(os.path.relpath(sokvag, rot), "kod", "markorer",
                               ["%s  %s" % (var, txt) for var, txt in traffar]))
    return ut


def matningar_utan_arlighetsavsnitt(katalog: str) -> List[str]:
    """De matningar som inte sager nagot om vad de INTE visar.

    En matning utan ett sadant avsnitt ar inte en matning utan skuld - den ar
    en matning vars skuld ingen har skrivit ned. Samma resonemang som
    guldgrindens krav pa HONESTY: regeln ar TOM om sektionen inte finns.
    """
    ut = []
    for f in sorted(os.listdir(katalog)):
        if not (f.startswith("M-") and f.endswith(".md")):
            continue
        if not ur_matning(os.path.join(katalog, f)):
            ut.append(f)
    return ut


def moduler_utan_prov(rot: str) -> Dict[str, List[Tuple[str, int]]]:
    """Produktionsmoduler efter vilken sorts prov som namner dem.

    Tva hinkar, och skillnaden ar inte kosmetisk:

      "inget"     ingen provfil alls namner modulen. Med sakerhet oprovad.
      "bara_l3"   bara en korning under tests/protocol/ namner den. Sadana
                  kraver levande VC, OpenPLC eller kompilator och kors INTE av
                  `pytest tests/enhet`. En modul i den hinken gar alltsa inte
                  att kontrollera pa en ren maskin, och det ar en annan sorts
                  skuld an ingen tackning alls - men det ar skuld.

    Kriteriet ar med flit grovt: namns modulens filnamn i provtexten? Ett finare
    matt hade varit battre och dyrare, och det grova fangar redan det som ska
    fangas.

    MEN NAMNET MASTE STA SOM ETT EGET ORD (M-92). Forsta versionen fragade
    `stam in text`, alltsa en ren delstrang. MATT 2026-09-05: `bank/anlaggning.py`
    raknades som provad for att bokstaverna "anlaggning" fanns inne i
    `_anlaggningssignaler` i test_verktyg_signaler.py - och samtidigt matte
    coverage 0 av modulens 336 satser. Delstrangskriteriet ar alltsa en vag ut
    ur sparren som ingen behover ta medvetet: den oppnas av vilket langre ord
    som helst. Kort stam = storre hal, sa `bas.py`, `fel.py` och `text.py` var
    de mest utsatta.

    Ordgransen kan i stallet ge falskt UTSLAG: `st/lexer.py` kors till 86 % via
    tolken utan att nagon provfil skriver ordet "lexer". Det ar med flit. En
    sparre som ska hitta skuld far hellre peka pa en modul for mycket an tiga
    om en som aldrig kors - falsk gron ar den dyra riktningen.

    __init__.py raknas inte: den ar limmet och provas genom det den binder.
    """
    def namns(stam, text):
        return re.search(r"(?<![A-Za-z0-9_])" + re.escape(stam)
                         + r"(?![A-Za-z0-9_])", text) is not None

    def las(katalog):
        text = []
        for kat, kataloger, filer in os.walk(katalog):
            kataloger[:] = [k for k in kataloger if k != "__pycache__"]
            for f in filer:
                if f.endswith((".py", ".md")):
                    try:
                        with open(os.path.join(kat, f), "r",
                                  encoding="utf-8") as fh:
                            text.append(fh.read())
                    except (OSError, UnicodeDecodeError):
                        pass
        return "\n".join(text)

    enhet = las(os.path.join(rot, "tests", "enhet"))
    protokoll = las(os.path.join(rot, "tests", "protocol"))
    ovrigt = ""
    tests = os.path.join(rot, "tests")
    if os.path.isdir(tests):
        for post in sorted(os.listdir(tests)):
            hel = os.path.join(tests, post)
            if os.path.isdir(hel) and post not in ("enhet", "protocol",
                                                   "__pycache__"):
                ovrigt += las(hel)

    ut = {"inget": [], "bara_l3": []}
    for under in ("svc", "ext", "bank", "install"):
        bas = os.path.join(rot, under)
        if not os.path.isdir(bas):
            continue
        for katalog, kataloger, filer in os.walk(bas):
            kataloger[:] = [k for k in kataloger
                            if k not in ("__pycache__", "node_modules")]
            for f in sorted(filer):
                if not f.endswith(".py") or f == "__init__.py":
                    continue
                stam = os.path.splitext(f)[0]
                sokvag = os.path.relpath(os.path.join(katalog, f), rot)
                try:
                    n = sum(1 for _ in open(os.path.join(rot, sokvag),
                                            encoding="utf-8"))
                except (OSError, UnicodeDecodeError):
                    n = 0
                if namns(stam, enhet) or namns(stam, ovrigt):
                    continue
                if namns(stam, protokoll):
                    ut["bara_l3"].append((sokvag, n))
                else:
                    ut["inget"].append((sokvag, n))
    ut["inget"].sort()
    ut["bara_l3"].sort()
    return ut


# En senare matning som sager sig ratta en tidigare. Monstret ar skrivet med
# diakriter OCH normaliseras, av ett matt skal: M-70 fann att atta av elva
# grenar i det har filens forsta monster var doda for att de var skrivna i
# ASCII mot text pa svenska. En gren som aldrig fyrar rapporterar noll traffar,
# och noll traffar ser ut som "det finns inget att hitta".
_RATTAR = re.compile(
    r"(r\u00e4ttar|rattar|motbevisar|r\u00e4ttad av|rattad av|falsifierar|"
    r"korrigerar)\s+\[?(M-\d+)", re.I)
_NAMNER_M = re.compile(r"\bM-(\d+)\b")


def _mnr(text: str) -> str:
    """M-numret ur ett filnamn eller en hanvisning, alltid tvasiffrigt.

    Ratt regex och inte split("-"): filnamnen ar M-01_tillaggsmekanismen.md, sa
    ett enkelt split ger '01_tillaggsmekanismen.md'. Det ar ett litet fel med en
    stor foljd - funktionen kastar, och den som fangar undantaget far en tom
    lista som ser ut som "inga rattelser saknar framatpekare".
    """
    m = re.match(r"M-0*(\d+)", text.strip())
    if not m:
        raise ValueError("inget M-nummer i %r" % text)
    return "M-%02d" % int(m.group(1))


def nummerkollisioner(katalog: str) -> List[Tuple[str, List[str]]]:
    """M-nummer som mer an en matningsfil gor ansprak pa.

    VARFOR DET AR SKULD OCH INTE SLARV (M-92): numret ar den enda identiteten
    en matning har. Allt annat i systemet slar upp den PA NUMRET:

      * `test_troskelharkomst.matningar_som_finns()` bygger en MANGD, sa tva
        filer med samma nummer kollapsar till en post. En troskel som skriver
        `# Satt av M-90.` blir gron oavsett vilken av de tva den menade, och
        `svc/vc_assist_svc/forlopp/yta.py:63` var precis den raden den dagen
        det fanns tva M-90.
      * `rattelser_utan_framatpekare` nedan bygger `per_nummer[nummer] = fil`.
        Sista filen i bokstavsordning vinner, tyst, och den andra matningens
        rattelser blir osynliga for grinden.
      * en lasare som far numret hanvisat till sig hittar fel matning.

    MATT 2026-09-05: tva kollisioner samtidigt i repot (M-89 och M-90), bagge
    uppkomna av att flera agenter skrev samtidigt utan att nagot fragade om
    numret var taget. Ingen av de fyra filerna var fel skriven - det fanns bara
    ingen grind som stallde fragan i skrivogonblicket.

    Returnerar [(nummer, [filer])] for de nummer som har fler an en fil.
    """
    per_nummer: Dict[str, List[str]] = {}
    for f in sorted(os.listdir(katalog)):
        if not (f.startswith("M-") and f.endswith(".md")):
            continue
        per_nummer.setdefault(_mnr(f), []).append(f)
    return [(n, filer) for n, filer in sorted(per_nummer.items())
            if len(filer) > 1]


def rattelser_utan_framatpekare(katalog: str) -> List[Tuple[str, List[str]]]:
    """Matningar som en SENARE sager sig ratta, utan att sjalva peka framat.

    En rattelse som bara star i den nyare filen ar en rattelse for den som redan
    vet. Den som slar upp den gamla matningen far det gamla svaret med full
    trovardighet - samma fel som fas 6:s rubrik gjorde i ett dygn, och som
    M-34:s tabellrad gjorde tills den flyttades upp till pastaendet.
    """
    filer = sorted(f for f in os.listdir(katalog)
                   if f.startswith("M-") and f.endswith(".md"))
    text = {}
    for f in filer:
        try:
            with open(os.path.join(katalog, f), "r", encoding="utf-8") as fh:
                text[f] = fh.read()
        except (OSError, UnicodeDecodeError):
            text[f] = ""
    per_nummer = {}
    for f in filer:
        per_nummer[_mnr(f)] = f

    rattade: Dict[str, List[str]] = {}
    for f, t in text.items():
        for m in _RATTAR.finditer(t):
            rattade.setdefault(_mnr(m.group(2)), []).append(_mnr(f))

    ut: List[Tuple[str, List[str]]] = []
    for gammal, nyare in sorted(rattade.items()):
        fil = per_nummer.get(gammal)
        if fil is None:
            continue
        namnda = set("M-%02d" % int(x) for x in _NAMNER_M.findall(text[fil]))
        saknade = sorted(set(nyare) - namnda)
        if saknade:
            ut.append((gammal, saknade))
    return ut


# ---- ordlistor som avgor en dom ------------------------------------------

# Katalogerna som soks efter ordlistor. Samma som kodmarkorsvepet, minus
# tests/: en ordlista i ett prov ar provets egen fixtur och ingen dom.
_ORDLISTEKATALOGER = ("svc", "ext", "bank", "install")

# En lista under tre ord ar ingen ordlista utan tre namn. MATT M-98: av 163
# moduldeklarerade stranglistor i svc/ext/bank/install ligger 23 av de 35
# helt-inneslutna paren pa exakt 3 gemensamma ord, alltsa pa golvet - det ar
# sammantraffanden, inte kopior.
_MINSTA_ORDLISTA = 3

# Nar tva listor i olika filer raknas som KOPIOR. Talet ar matt och inte valt:
# fordelningen av parvis overlapp over de 163 listorna gar 19 par vid >=4, 7
# vid >=5, 6 vid >=6 och 4 vid >=7. Knacken ligger mellan 4 och 5, och
# gransen star pa 6 sa att ett femordigt sammantraffande inte blir ett fynd.
# Listor med SAMMA namn raknas som kopior oavsett storlek - ett delat namn ar
# ingen slump.
KOPIEGRANS = 6

# `__all__` ar Pythons exportlista och ingen ordlista som domer nagot. Den
# star for sig darfor att den annars ensam star for 43 av de identiska paren.
_ICKE_ORDLISTOR = ("__all__",)


@dataclass(frozen=True)
class Ordlista:
    """En moduldeklarerad lista av strangar, dar den star."""

    fil: str
    namn: str
    rad: int
    ord: frozenset
    sammansatt: bool


def _strangarna(nod) -> Optional[List[str]]:
    """Strangarna i en tupel/lista/mangd av BARA strangliteraler, annars None."""
    if not isinstance(nod, (ast.Tuple, ast.List, ast.Set)):
        return None
    ut: List[str] = []
    for e in nod.elts:
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            ut.append(e.value)
        else:
            return None
    return ut


def ordlistor(rot: str) -> List[Ordlista]:
    """Alla moduldeklarerade stranglistor under _ORDLISTEKATALOGER.

    En lista byggd ur ANDRA listor (`NEKANDE = FELORD + BARA_NEGATION`) far
    sammansatt=True och tomma ord. Skillnaden ar hela poangen med
    ordlistor_med_tva_storheter nedan: en sammansatt lista BAR sina delar
    oppet, och da gar var storhet att fraga om for sig.
    """
    ut: List[Ordlista] = []
    for under in _ORDLISTEKATALOGER:
        katalog = os.path.join(rot, under)
        if not os.path.isdir(katalog):
            continue
        for dp, dn, fn in os.walk(katalog):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for namn_ in sorted(fn):
                if not namn_.endswith(".py"):
                    continue
                stig = os.path.join(dp, namn_)
                try:
                    with open(stig, "r", encoding="utf-8") as f:
                        trad = ast.parse(f.read())
                except (OSError, SyntaxError, UnicodeDecodeError):
                    continue
                rel = os.path.relpath(stig, rot)
                for nod in trad.body:
                    if not isinstance(nod, ast.Assign) or len(nod.targets) != 1:
                        continue
                    mal = nod.targets[0]
                    if not isinstance(mal, ast.Name):
                        continue
                    if mal.id in _ICKE_ORDLISTOR:
                        continue
                    ord_ = _strangarna(nod.value)
                    if ord_ is not None:
                        if len(ord_) < _MINSTA_ORDLISTA:
                            continue
                        ut.append(Ordlista(rel, mal.id, nod.lineno,
                                           frozenset(o.strip().lower()
                                                     for o in ord_),
                                           False))
                    elif isinstance(nod.value, ast.BinOp):
                        ut.append(Ordlista(rel, mal.id, nod.lineno,
                                           frozenset(), True))
    return ut


def _karnorna(listor: Sequence[Ordlista]) -> Tuple[frozenset, frozenset]:
    """De tva storheterna, hamtade ur den modul som AGER delningen.

    Karnorna star INTE som literaler har. Grinden mot kopierade ordlistor far
    inte sjalv bara en kopia av den lista den domer om - da hade den matt sin
    egen avskrift i stallet for repots. De lases ur
    `svc/vc_assist_svc/harness/text.py`, dar M-95 gjorde delningen:

      FELORD         ord som sager att nagot GICK FEL
      BARA_NEGATION  ord som bara negerar det de star bredvid

    Saknas nagon av dem KASTAR grinden. En grind vars indata forsvunnit ska
    saga det, aldrig svara "inga fynd" (S10).
    """
    hittade: Dict[str, frozenset] = {}
    for lista in listor:
        if lista.fil.replace("\\", "/").endswith("harness/text.py"):
            if lista.namn in ("FELORD", "BARA_NEGATION"):
                hittade[lista.namn] = lista.ord
    saknade = sorted({"FELORD", "BARA_NEGATION"} - set(hittade))
    if saknade:
        raise ValueError(
            "ordlistegrinden hittar inte %s i harness/text.py; karnorna maste "
            "lasas ur den modul som ager delningen (M-95, M-98)"
            % ", ".join(saknade))
    return hittade["FELORD"], hittade["BARA_NEGATION"]


def ordlistor_med_tva_storheter(
        rot: str,
        karnor: Optional[Tuple[Sequence[str], Sequence[str]]] = None
) -> List[Tuple[str, int, str, List[str], List[str]]]:
    """Litterala ordlistor som bar BADE felord och bara negationer.

    FELKLASSEN, matt tre ganger: M-94 fynd 1 och 4 (`text.NEKANDE`) och M-98
    (`oga.NEKANDE_OGONORD`). En lista som bar tva storheter svarar pa fragan
    "bar texten nagot av de har orden?" - och den fragan ar inte den grinden
    stallde sig. Foljden var bada gangerna en falsk gron: ett orelaterat
    "inte" nagon annanstans i svaret tystade grinden.

    Kriteriet ar STRUKTURELLT och har ingen undantagslista: en lista som bar
    bada storheterna maste vara SAMMANSATT ur de listor som bar var sin
    (`NEKANDE = FELORD + BARA_NEGATION + FORBEHALL`). Da gar var storhet att
    fraga om for sig, och unionen finns kvar for den som verkligen vill ha
    bredden.

    MATT 2026-09-05, samma grind mot tre trad:
      fore M-95   2 traffar (text.NEKANDE, oga.NEKANDE_OGONORD)
      fore M-98   1 traff  (oga.NEKANDE_OGONORD)
      efter M-98  0

    karnor ar (felord, negationer) och finns bara for att kunna stalla samma
    fraga till ett ANNAT trad an det som bar delningen. Utelamnas den lases
    karnorna ur harness/text.py, och det ar den enda vag registret gar.

    Returnerar [(fil, rad, namn, felorden, negationerna)].
    """
    listor = ordlistor(rot)
    if karnor is None:
        felord, negationer = _karnorna(listor)
    else:
        # Bara for att kunna stalla SAMMA fraga till ett annat trad, t.ex. en
        # utcheckning fran fore delningen (M-98:s tabell). Registret gar
        # aldrig den vagen: bygg() lamnar karnor=None.
        felord = frozenset(o.strip().lower() for o in karnor[0])
        negationer = frozenset(o.strip().lower() for o in karnor[1])
    ut = []
    for lista in listor:
        if lista.sammansatt:
            continue
        f = sorted(lista.ord & felord)
        n = sorted(lista.ord & negationer)
        if f and n:
            ut.append((lista.fil, lista.rad, lista.namn, f, n))
    return sorted(ut)


def kopierade_ordlistor(rot: str) -> List[Tuple[str, str, str, str, int]]:
    """Ordlistor som star i tva filer, och alltsa kan glida isar.

    `harness/text.py`:s egen docstring sager varfor: "de ligger PA ETT STALLE
    just for att en kopierad ordlista blir tva ordlistor sa fort nagon ratter
    den ena". Registret sag inte att den regeln brots - `oga.py` bar en egen
    kopia, och M-98 lagade den ena utan att den andra rorde sig.

    ATT DET INTE AR TEORETISKT, matt 2026-09-05: `guldgrind.DALIGA_ORD` och
    `oga_kontrakt._FYNDORD` delar 12 ord, och den forsta bar dessutom
    "CEILING" - som den andra med FLIT lagt i `_OSAKERORD`. Kopian HAR redan
    glidit isar, och de tva grindarna laser samma ogonrapport.

    Kriteriet: samma normaliserade namn och minst ett gemensamt ord, eller
    minst KOPIEGRANS gemensamma ord. Returnerar
    [(fil_a, namn_a, fil_b, namn_b, antal_gemensamma)].
    """
    listor = [l for l in ordlistor(rot) if not l.sammansatt]
    ut = []
    for i, a in enumerate(listor):
        for b in listor[i + 1:]:
            if a.fil == b.fil:
                continue
            gem = a.ord & b.ord
            if not gem:
                continue
            samma_namn = a.namn.strip("_").lower() == b.namn.strip("_").lower()
            if len(gem) >= KOPIEGRANS or samma_namn:
                ut.append((a.fil, a.namn, b.fil, b.namn, len(gem)))
    return sorted(ut, key=lambda r: (-r[4], r[0], r[1]))


def bygg(rot: str) -> Dict[str, object]:
    matningar = os.path.join(rot, "docs", "matningar")
    poster: List[Post] = []
    for f in sorted(os.listdir(matningar)):
        if f.startswith("M-") and f.endswith(".md") and not _undantagen(f):
            poster.extend(ur_matning(os.path.join(matningar, f)))
    kodposter: List[Post] = []
    for under in ("svc", "ext", "install", "bank", "tests"):
        katalog = os.path.join(rot, under)
        if os.path.isdir(katalog):
            kodposter.extend(ur_kod(katalog))
    return {
        "matningsposter": poster,
        "kodposter": kodposter,
        "utan_arlighetsavsnitt": matningar_utan_arlighetsavsnitt(matningar),
        "nummerkollisioner": nummerkollisioner(matningar),
        "moduler_utan_prov": moduler_utan_prov(rot),
        "rattelser_utan_framatpekare": rattelser_utan_framatpekare(matningar),
        "ordlistor_med_tva_storheter": ordlistor_med_tva_storheter(rot),
        "kopierade_ordlistor": kopierade_ordlistor(rot),
        "antal_punkter": sum(p.antal for p in poster),
        "antal_kodmarkorer": sum(p.antal for p in kodposter),
    }


def text(register: Dict[str, object]) -> str:
    rader = ["# Skuldregistret",
             "",
             "**Genererat**, aldrig fört för hand. Ett register någon måste "
             "komma ihåg att uppdatera är redan glömt, och den enda skuld som "
             "hamnar där är den man ändå kom ihåg.",
             "",
             "Byggs med `python3 -m vc_assist_svc.skuld` ur två källor som "
             "båda skrivs samtidigt som arbetet: mätningarnas ärlighetsavsnitt "
             "och markörer i koden.",
             ""]
    utan = register["utan_arlighetsavsnitt"]
    rader.append("## Mätningar utan ärlighetsavsnitt: %d" % len(utan))
    rader.append("")
    if utan:
        rader.append("En mätning utan ett sådant avsnitt är inte en mätning "
                     "utan skuld — det är en mätning vars skuld ingen har "
                     "skrivit ned.")
        rader.append("")
        for f in utan:
            rader.append("* `%s`" % f)
        rader.append("")
    kollisioner = register.get("nummerkollisioner") or []
    rader.append("## Mätningsnummer som fler än en fil gör anspråk på: %d"
                 % len(kollisioner))
    rader.append("")
    if kollisioner:
        rader.append("Numret är mätningens enda identitet. Två filer på samma "
                     "nummer gör varje hänvisning tvetydig, och både "
                     "tröskellintern och rättelsegrinden slår upp på numret.")
        rader.append("")
        for nummer, filer in kollisioner:
            rader.append("* **%s** — %s" % (nummer, ", ".join("`%s`" % f
                                                              for f in filer)))
        rader.append("")
    blandade = register.get("ordlistor_med_tva_storheter") or []
    rader.append("## Ordlistor som bär två storheter: %d" % len(blandade))
    rader.append("")
    rader.append("En lista som bär både felord och bara negationer svarar på "
                 "frågan *bär texten något av de här orden?* — och det är "
                 "inte den fråga någon grind ställer sig. Mätt tre gånger: "
                 "M-94 fynd 1 och 4, M-98. Taket är noll, och kriteriet har "
                 "ingen undantagslista: en lista som bär båda storheterna "
                 "ska vara **sammansatt** ur de listor som bär var sin.")
    rader.append("")
    for fil, rad, namn, felord, negationer in blandade:
        rader.append("* `%s:%d` **%s** — felord %s, negationer %s"
                     % (fil, rad, namn, ", ".join(felord),
                        ", ".join(negationer)))
    if blandade:
        rader.append("")
    kopior = register.get("kopierade_ordlistor") or []
    rader.append("## Ordlistor som står i två filer: %d" % len(kopior))
    rader.append("")
    rader.append("`harness/text.py` säger det själv: *\"de ligger PA ETT "
                 "STALLE just for att en kopierad ordlista blir tva ordlistor "
                 "sa fort nagon ratter den ena\"*. Registret såg inte att "
                 "regeln bröts. Listan nedan är ett **register**, inte en "
                 "anklagelse: en delad ordlista kan vara rätt, men den måste "
                 "vara sedd.")
    rader.append("")
    for fil_a, namn_a, fil_b, namn_b, antal in kopior:
        rader.append("* %d gemensamma — `%s`.**%s** ↔ `%s`.**%s**"
                     % (antal, fil_a, namn_a, fil_b, namn_b))
    if kopior:
        rader.append("")
    rader.append("## Vad mätningarna säger att de inte vet: %d punkter"
                 % register["antal_punkter"])
    rader.append("")
    for p in register["matningsposter"]:
        if not p.rader:
            continue
        rader.append("### %s — %s" % (p.kalla, p.rubrik))
        rader.append("")
        for r in p.rader:
            rader.append("* %s" % r)
        rader.append("")
    utan_prov = register.get("moduler_utan_prov") or {"inget": [], "bara_l3": []}
    for nyckel, rubrik in (
            ("inget", "Produktionsmoduler som ingen provfil nämner"),
            ("bara_l3", "Produktionsmoduler som bara nämns av en L3-körning "
                        "(kräver VC/OpenPLC, körs inte av `pytest tests/enhet`)")):
        lista = utan_prov.get(nyckel) or []
        rader.append("## %s: %d (%d rader)"
                     % (rubrik, len(lista), sum(n for _f, n in lista)))
        rader.append("")
        for f, n in lista:
            rader.append("* `%s` — %d rader" % (f, n))
        rader.append("")
    rader.append("## Markörer i koden: %d" % register["antal_kodmarkorer"])
    rader.append("")
    for p in register["kodposter"]:
        rader.append("### %s" % p.kalla)
        rader.append("")
        for r in p.rader:
            rader.append("* %s" % r)
        rader.append("")
    return "\n".join(rader) + "\n"


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description="Bygg skuldregistret.")
    p.add_argument("--rot", default=os.path.normpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
    p.add_argument("--ut", default=None)
    a = p.parse_args(argv)
    reg = bygg(a.rot)
    print("%d punkter ur %d matningsavsnitt, %d kodmarkorer i %d filer, "
          "%d matningar utan arlighetsavsnitt"
          % (reg["antal_punkter"], len(reg["matningsposter"]),
             reg["antal_kodmarkorer"], len(reg["kodposter"]),
             len(reg["utan_arlighetsavsnitt"])))
    if a.ut:
        with open(a.ut, "w", encoding="utf-8") as f:
            f.write(text(reg))
        print("skrivet: %s" % a.ut)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
