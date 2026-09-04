# -*- coding: utf-8 -*-
"""Det kontrollerade språket: bankens sekvens- och förreglingsrader till IR.

Baslinjens andra steg. Morfologin säger vilka don som finns; den här modulen
läser den **strukturerade uppgiftsspecen** — `control.sequence` och
`control.interlocks` — och gör om raderna till en liten mellanform som
generatorn kan gjuta kod ur.

## Varför det här är en klassisk metod och inte en språkmodell i förklädnad

Raderna är skrivna i en kontrollerad svenska med en liten och sluten
verbrepertoar: *satt X hog*, *nollstall X*, *vanta pa X*, *vid X:*, *starta
vakten T s pa X*, *lat X folja Y*. Ett mönsterläsande över en kontrollerad
grammatik är precis vad ett kravtabellsverktyg gör, och det har funnits i
branschen längre än språkmodellerna. Ingen statistik, ingen inlärning, inget
sampling: samma rad ger alltid samma IR.

## Regeln som gör mätningen ärlig

**Varje rad som inte går att läsa räknas.** `Lasning.olasta` bär dem, och
generatorn skriver ut dem i sin rapport. En parser som tyst hoppar över det den
inte förstår ser ut att förstå allt, och då mäter bänken parserns tystnad i
stället för dess räckvidd. Talet står i `docs/matningar/M-62_baslinjen.md`.

## Vad IR:en INTE bär

Ingen ordning mellan olika stationer, ingen fysik, inga enheter utöver sekunder
och millimeter, och ingen mening som bara finns i prosan runt omkring. En rad
som säger "for skiftregistret framat med ST190_ENC_POS, inte med tiden" läses
inte: den beskriver en datastruktur, inte en sekvens, och baslinjen har ingen
regel som bygger datastrukturer. Den raden hamnar i `olasta`.

beskriver: svc/vc_assist_svc/plc/baslinje/sprak.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# ---- villkorens mellanform ----------------------------------------------

FLANK_UPP = "RISE"
FLANK_NED = "FALL"


@dataclass(frozen=True)
class Term:
    """En enda prövning i ett villkor."""

    signal: str
    sant: bool = True
    flank: str = ""            # "", FLANK_UPP eller FLANK_NED
    jamforelse: str = ""       # "", "<", ">", "<=", ">=", "=", "<>"
    varde: float = 0.0

    def __str__(self):
        if self.flank:
            return "%s(%s)" % (self.flank, self.signal)
        if self.jamforelse:
            return "%s %s %g" % (self.signal, self.jamforelse, self.varde)
        return self.signal if self.sant else "NOT " + self.signal


@dataclass(frozen=True)
class Villkor:
    """En konjunktion eller disjunktion av termer. Tom = alltid sant."""

    termer: Tuple[Term, ...] = ()
    op: str = "AND"

    @property
    def tomt(self) -> bool:
        return not self.termer

    def signaler(self) -> Tuple[str, ...]:
        return tuple(t.signal for t in self.termer)

    def __str__(self):
        return (" %s " % self.op).join(str(t) for t in self.termer) or "TRUE"


# ---- handlingarnas mellanform -------------------------------------------

SATT = "satt"          # signal := TRUE/FALSE
OKA = "oka"            # signal := signal + 1
MINSKA = "minska"      # signal := signal - 1
NOLLA = "nolla"        # signal := 0
FOLJ = "folj"          # signal := kalla


@dataclass(frozen=True)
class Handling:
    sort: str
    signal: str
    varde: bool = True
    kalla: str = ""

    def __str__(self):
        if self.sort == SATT:
            return "%s := %s" % (self.signal, "TRUE" if self.varde else "FALSE")
        if self.sort == FOLJ:
            return "%s := %s" % (self.signal, self.kalla)
        return "%s(%s)" % (self.sort, self.signal)


# ---- direktiven ---------------------------------------------------------

D_STEG = "steg"                # ett steg i kedjan: villkor -> handlingar
D_DRIFTUT = "driftut"          # utgång som ska följa driftsvillkoret
D_VAKT = "vakt"                # tidsövervakning
D_UPPEHALL = "uppehall"        # fast väntetid i kedjan
D_KVITTENSKRAV = "kvittenskrav"  # kall start kräver kvittens
D_ATERSTALL = "aterstall"      # larm och kvittens nollställs på flank
D_LARMLATCH = "larmlatch"      # larmet latchas
D_FOLJ = "folj"                # utgång följer en ingång scan för scan
D_RAKNA = "rakna"              # räknare upp/ner på flank
D_BORJA_OM = "borja_om"        # kedjan går tillbaka till noll
D_HALL = "hall"                # utgång hålls hög/låg medan villkoret gäller


@dataclass
class Direktiv:
    sort: str
    rad: str = ""
    villkor: Villkor = field(default_factory=Villkor)
    handlingar: Tuple[Handling, ...] = ()
    signal: str = ""
    kalla: str = ""
    tid_s: float = 0.0
    lage: str = ""             # "auto", "hand" eller "" för båda
    tak: str = ""              # övre ändläge för D_FOLJ
    stam: str = ""             # vaktens egen ordstam, när den inte namnger en tagg

    def __str__(self):
        return "%s(%s -> %s)" % (self.sort, self.villkor,
                                 ", ".join(str(h) for h in self.handlingar))


# ---- förreglingarnas mellanform -----------------------------------------

F_OMSESIDIG = "omsesidig"       # a och b aldrig höga samtidigt
F_FORVILLKOR = "forvillkor"     # a får inte gå hög innan b
F_HALLVILLKOR = "hallvillkor"   # a får inte stå hög när b är låg
F_PERMISSIV = "permissiv"       # ingenting kommenderas när b är låg
F_ENBART = "enbart"             # a hög enbart när b = n
F_CYKELSPARR = "cykelsparr"     # ingen ny cykel när a >= n
F_HANDSPARR = "handsparr"       # handkörning spärrad i automatläge


@dataclass(frozen=True)
class Forregling:
    sort: str
    rad: str = ""
    a: str = ""
    b: str = ""
    varde: float = 0.0


# ---- läsningen ----------------------------------------------------------

@dataclass
class Lasning:
    """Allt som gick att läsa, och allt som inte gjorde det.

    `olasta` är den viktigaste listan i hela modulen. Den är baslinjens egen
    redovisning av var den slutar förstå, och den räknas i M-62.
    """

    direktiv: List[Direktiv] = field(default_factory=list)
    forreglingar: List[Forregling] = field(default_factory=list)
    olasta: List[str] = field(default_factory=list)
    olasta_forreglingar: List[str] = field(default_factory=list)
    # Rader som INTE blir egen kod, men som standardramen redan garanterar.
    # De räknas för sig: att räkna dem som lästa hade överdrivit läsarens
    # räckvidd, och att räkna dem som olästa hade överdrivit generatorns hål.
    ramtackta: List[Tuple[str, str]] = field(default_factory=list)

    @property
    def antal_rader(self) -> int:
        return len(self.direktiv) + len(self.olasta)


_SIGNAL = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b")
_TAL = re.compile(r"(\d+(?:[.,]\d+)?)")

# Orden som gör en term falsk. `utan` och `inte` bär samma negation som `lag`.
_LAGA = ("ar lag", "ar laga", "gatt lag", "gar lag", "blir lag", "ar noll",
         "ar tom", "ar fri")
_HOGA = ("ar hog", "ar hoga", "ar hogt", "gatt hog", "gar hog", "kommer",
         "ar sluten", "bekraftar")


def _tal(text: str, standard: float = 0.0) -> float:
    m = _TAL.search(text or "")
    if not m:
        return standard
    return float(m.group(1).replace(",", "."))


def _signaler_i(text: str, kanda) -> List[str]:
    """Signalnamnen i en textbit, i den ordning de står.

    `kanda` är kartan; ett namn som inte står i kartan är inte en signal utan
    ett ord med versaler, och det ska inte bli en term. Fail-closed: hellre en
    oläst rad än en term mot en tagg som inte finns (den hade fällts av grind 3
    och sett ut som ett logikfel).
    """
    ut = []
    for m in _SIGNAL.finditer((text or "").upper()):
        namn = m.group(1)
        if namn in kanda and namn not in ut:
            ut.append(namn)
    return ut


def _polaritet(bit: str) -> Optional[bool]:
    """True, False eller None (ingen polaritet uttalad i biten)."""
    liten = bit.lower()
    for ord_ in _LAGA:
        if ord_ in liten:
            return False
    if "utan " in liten or "inte " in liten or "inget " in liten:
        return False
    for ord_ in _HOGA:
        if ord_ in liten:
            return True
    return None


# Jämförelseorden i det kontrollerade språket. Ordningen spelar roll: "eller
# mer" måste prövas före "ar over", annars blir "5 eller mer" ett ">".
_JAMFORELSER = (
    (re.compile(r"\beller mer\b|\beller fler\b|\bnar\b"), ">="),
    (re.compile(r"\beller mindre\b|\beller farre\b"), "<="),
    (re.compile(r"\bar under\b|\bunderstiger\b|\bar lagre an\b"), "<"),
    (re.compile(r"\bar over\b|\boverstiger\b|\bar hogre an\b"), ">"),
    (re.compile(r"\bar lika med\b|\bar\s+\d"), "="),
)


def _jamforelse(bit_utan_namn: str) -> Tuple[str, float]:
    """(tecken, värde) om biten bär en jämförelse, annars ("", 0.0).

    Biten kommer in UTAN sina taggnamn. Skälet är mätt i den här modulens egen
    utveckling: `ST260_LAY_CNT ar under 5` gav jämförelsen `< 260`, därför att
    talet 260 satt i stationsprefixet. Ett tal som plockas ur ett namn är inte
    ett gränsvärde, och en generator som förreglar på stationsnumret ser ut att
    fungera tills stationen byter nummer.
    """
    if not _TAL.search(bit_utan_namn or ""):
        return "", 0.0
    for regex, tecken in _JAMFORELSER:
        if regex.search(" " + (bit_utan_namn or "").lower() + " "):
            return tecken, _tal(bit_utan_namn)
    return "", 0.0


def _utan_namn(bit: str, namn: Sequence[str]) -> str:
    ut = bit or ""
    for n in namn:
        ut = re.sub(re.escape(n), " ", ut, flags=re.I)
    return ut


def las_villkor(text: str, kanda) -> Villkor:
    """Ett villkor ur en textbit i det kontrollerade språket.

    Formen som bär hela banken är en uppräkning med ett efterföljande predikat:
    *"nar EMG_OK, AIR_OK och SYS_AUTO ar hoga"*. Predikatet står sist och
    gäller alla. Bitarna läses därför var för sig, och en bit utan eget
    predikat ärver det från den SENASTE bit som både bär en signal och uttalar
    en polaritet. Att i stället ärva från hela radens text gav fel: raden
    *"... ar hoga och inget larm star"* har ordet `inget` sist, och varje term
    blev negerad.
    """
    if not text:
        return Villkor()
    liten = " " + text.strip().lower() + " "
    termer: List[Term] = []

    # Flankerna först: de är egna termer och ska inte också bli nivåtermer.
    flankade = set()
    for flankord, sort in (("stigande flank", FLANK_UPP),
                           ("fallande flank", FLANK_NED)):
        for m in re.finditer(flankord + r"\s+pa\s+([a-z0-9_]+)", liten):
            namn = m.group(1).upper()
            if namn in kanda:
                termer.append(Term(namn, flank=sort))
                flankade.add(namn)

    bitar = re.split(r"\boch\b|,|\bsamt\b", text)
    # (signaler, polaritet, jämförelse) per bit, i textens ordning.
    lasta: List[Tuple[List[str], Optional[bool], Tuple[str, float]]] = []
    for bit in bitar:
        namn = [n for n in _signaler_i(bit, kanda) if n not in flankade]
        if not namn:
            continue
        lasta.append((namn, _polaritet(bit), _jamforelse(_utan_namn(bit, namn))))

    arvd = None
    for _namn, pol, _jam in lasta:
        if pol is not None:
            arvd = pol
    for namn, pol, (tecken, varde) in lasta:
        if pol is None:
            pol = arvd if arvd is not None else True
        for n in namn:
            if tecken:
                termer.append(Term(n, jamforelse=tecken, varde=varde))
            else:
                termer.append(Term(n, sant=pol))
    op = "OR" if re.search(r"\beller\b", text.lower()) and \
        not re.search(r"eller mer|eller fler|eller mindre|eller farre",
                      text.lower()) else "AND"
    return Villkor(tuple(termer), op)


# Verben i det kontrollerade språket, och den polaritet de betyder utan ett
# eget nivåord. Listan är sluten med flit: ett verb som inte står här läses
# inte, och raden hamnar i `olasta` i stället för att tolkas på en gissning.
_VERB = (("satt", None), ("satter", None), ("nollstall", False),
         ("nollstaller", False), ("oka", None), ("minska", None),
         ("hall", None), ("haller", None))
_VERBORD = re.compile(r"\b(satter|satt|nollstaller|nollstall|okar|oka|"
                      r"minskar|minska|haller|hall)\b", re.I)
# Ord som avslutar ett verbs räckvidd inne i samma mening. `aldrig samtidigt
# med ST310_RB_START` är ett FÖRBUD mot en signal, inte en order till den, och
# utan brytorden hade båda robotarna startats i samma steg.
_BRYT = re.compile(r"\b(aldrig|utan att|utan|i stallet|dock|men|sa att|"
                   r"i samma scan som)\b", re.I)
_NIVA = re.compile(r"\b(hog|hogt|hoga|lag|lagt|laga)\b", re.I)


def las_handlingar(text: str, kanda) -> Tuple[Handling, ...]:
    """Handlingarna i en textbit, i textens ordning.

    Läses som verb med räckvidd: varje verb äger texten fram till nästa verb
    eller till ett brytord. Formen är den branschen skriver kravrader i, och
    den är sluten nog att gå att läsa utan att gissa.
    """
    ut: List[Handling] = []
    tagna = set()
    traffar = list(_VERBORD.finditer(text or ""))
    for i, m in enumerate(traffar):
        verb = m.group(1).lower()
        slut = traffar[i + 1].start() if i + 1 < len(traffar) else len(text)
        rest = text[m.end():slut]
        brott = _BRYT.search(rest)
        if brott:
            rest = rest[:brott.start()]
        namn = [n for n in _signaler_i(rest, kanda) if n not in tagna]
        if not namn:
            continue
        if verb.startswith("nollstall"):
            for n in namn:
                ut.append(Handling(SATT, n, False))
                tagna.add(n)
            continue
        if verb.startswith("oka"):
            for n in namn:
                ut.append(Handling(OKA, n))
                tagna.add(n)
            continue
        if verb.startswith("minska"):
            for n in namn:
                ut.append(Handling(MINSKA, n))
                tagna.add(n)
            continue
        niva = _NIVA.search(rest)
        hog = True if niva is None else niva.group(1).lower().startswith("hog")
        for n in namn:
            ut.append(Handling(SATT, n, hog))
            tagna.add(n)
    return tuple(ut)


# ---- radmönstren --------------------------------------------------------
#
# Ordningen är viktig: det mest specifika mönstret först. Ett generellt mönster
# som står före ett specifikt äter upp det, och då blir en tidsövervakning ett
# vanligt steg utan att någon märker det.

_M_VAKT = re.compile(
    r"^starta\s+(?P<namn>[a-z]*vakt(?:en|ningen)?|tidsovervakningen)\s+"
    r"(?P<tid>[\d.,]+)\s*s\s+(?:pa|sa fort)\s+(?P<rest>.+)$", re.I)
_M_UPPEHALL = re.compile(r"^rakna\s+(?P<tid>[\d.,]+)\s*s\s+uppehall", re.I)
_M_ATERSTALL = re.compile(
    r"^nollstall\s+larm.*\bflank\b\s+pa\s+(?P<sig>[A-Za-z0-9_]+)", re.I)
_M_KVITTENS = re.compile(r"^efter\s+spanningspaslag", re.I)
# "vid X: gor Y" och "nar X: gor Y" är samma sats i det kontrollerade språket.
# Uppgiftsprosan skriver "Nar ...", de strukturerade specfälten "vid ...", och
# en grammatik som bara känner den ena formen mäter vilket fält texten stod i.
_M_VID = re.compile(r"^(?:forst\s+)?(?:vid|nar)\s+(?P<villkor>[^:]+?)\s*[:]\s*"
                    r"(?P<handling>.+)$", re.I)
_M_VANTA_OCH = re.compile(
    r"^vanta\s+pa\s+(?P<villkor>.+?)\s+och\s+(?P<handling>"
    r"(?:satt|nollstall|oka|minska).+)$", re.I)
_M_VANTA = re.compile(r"^vanta\s+pa\s+(?P<villkor>.+)$", re.I)
_M_SATT_NAR = re.compile(
    r"^(?P<handling>satt\s+.+?)\s+(?:nar|sa lange|om)\s+(?P<villkor>.+)$", re.I)
_M_NOLLSTALL_NAR = re.compile(
    r"^(?P<handling>nollstall\s+.+?)\s+(?:nar|sa lange|i samma scan som)\s+"
    r"(?P<villkor>.+)$", re.I)
_M_HALL = re.compile(
    r"^hall\s+(?P<sig>[A-Za-z0-9_]+)\s+(?P<niva>hog|lag)\s+"
    r"(?:nar|sa lange)\s+(?P<villkor>.+)$", re.I)
_M_FOLJ = re.compile(
    r"^lat\s+(?P<sig>[A-Za-z0-9_]+)\s+folja\s+(?P<kalla>[A-Za-z0-9_]+)"
    r".*?(?:upp till\s+(?P<tak>[A-Za-z0-9_]+))?$", re.I)
_M_RAKNA = re.compile(
    r"^(?P<verb>oka|minska)\s+(?P<sig>[A-Za-z0-9_]+)\s+pa\s+"
    r"(?P<flank>stigande|fallande)\s+flank\s+pa\s+(?P<kalla>[A-Za-z0-9_]+)",
    re.I)
_M_LAGE = re.compile(r"^i\s+(?P<lage>automatlage|handlage)\s*[:,]\s*"
                     r"(?P<rest>.+)$", re.I)
_M_LARM = re.compile(r"\blatcha\s+SYS_ALARM\b|\blatchat?\s+larm\b", re.I)

_LAGEORD = {"automatlage": "auto", "handlage": "hand"}

# Ändelserna som skiljer vaktens namn från donets. Svensk bestämd form och
# sammansättningsfog, inget mer: "lyftvakten" -> "lyft".
_VAKTANDELSER = ("overvakningen", "vakningen", "vakten", "vakt")


def _vaktstam(namn: str) -> str:
    ord_ = (namn or "").lower()
    for andelse in _VAKTANDELSER:
        if ord_.endswith(andelse):
            ord_ = ord_[:-len(andelse)]
            break
    # En stam under tre tecken matchar för mycket i en kommentartext.
    return ord_ if len(ord_) >= 3 else ""


def _las_rad(rad: str, kanda) -> List[Direktiv]:
    text = rad.strip().rstrip(".")
    lage = ""
    m = _M_LAGE.match(text)
    if m:
        lage = _LAGEORD[m.group("lage").lower()]
        text = m.group("rest").strip()

    def klar(d: Direktiv) -> List[Direktiv]:
        d.lage = lage
        d.rad = rad
        return [d]

    m = _M_VAKT.match(text)
    if m:
        rest = m.group("rest")
        delar = re.split(r"\butan\b", rest)
        sigs = _signaler_i(delar[0], kanda)
        if sigs:
            termer = [Term(sigs[0])]
            if len(delar) > 1:
                for namn in _signaler_i(delar[1], kanda):
                    termer.append(Term(namn, sant=False))
            return klar(Direktiv(D_VAKT, tid_s=_tal(m.group("tid")),
                                 signal=sigs[0],
                                 villkor=Villkor(tuple(termer))))
        # "sa fort nagon av lyftriktningarna ar hog": ingen tagg namnges.
        # Vaktens EGET namn bär då donet ("lyftvakten" -> "lyft"), och
        # generatorn slår upp stammen i signalernas kommentarer. Det är en
        # lexikal uppslagning i kartans egen text, inte en gissning: hittar
        # den ingen signal blir vakten inte till, och det räknas.
        return klar(Direktiv(D_VAKT, tid_s=_tal(m.group("tid")), signal="",
                             stam=_vaktstam(m.group("namn"))))

    m = _M_UPPEHALL.match(text)
    if m:
        return klar(Direktiv(D_UPPEHALL, tid_s=_tal(m.group("tid"))))

    m = _M_ATERSTALL.match(text)
    if m and m.group("sig").upper() in kanda:
        return klar(Direktiv(D_ATERSTALL, signal=m.group("sig").upper()))

    if _M_KVITTENS.match(text):
        sigs = _signaler_i(text, kanda)
        return klar(Direktiv(D_KVITTENSKRAV,
                             signal=sigs[0] if sigs else ""))

    m = _M_RAKNA.match(text)
    if m and m.group("sig").upper() in kanda and \
            m.group("kalla").upper() in kanda:
        flank = FLANK_UPP if m.group("flank").lower() == "stigande" else FLANK_NED
        sort = OKA if m.group("verb").lower() == "oka" else MINSKA
        return klar(Direktiv(D_RAKNA, signal=m.group("sig").upper(),
                             kalla=m.group("kalla").upper(),
                             villkor=Villkor((Term(m.group("kalla").upper(),
                                                   flank=flank),)),
                             handlingar=(Handling(sort,
                                                  m.group("sig").upper()),)))

    m = _M_FOLJ.match(text)
    if m and m.group("sig").upper() in kanda and \
            m.group("kalla").upper() in kanda:
        tak = (m.group("tak") or "").upper()
        return klar(Direktiv(D_FOLJ, signal=m.group("sig").upper(),
                             kalla=m.group("kalla").upper(),
                             tak=tak if tak in kanda else ""))

    m = _M_HALL.match(text)
    if m and m.group("sig").upper() in kanda:
        return klar(Direktiv(D_HALL, signal=m.group("sig").upper(),
                             villkor=las_villkor(m.group("villkor"), kanda),
                             handlingar=(Handling(
                                 SATT, m.group("sig").upper(),
                                 m.group("niva").lower() == "hog"),)))

    for regex in (_M_VID, _M_VANTA_OCH):
        m = regex.match(text)
        if m:
            villkor = las_villkor(m.group("villkor"), kanda)
            handlingar = las_handlingar(m.group("handling"), kanda)
            if villkor.tomt and not handlingar:
                break
            return klar(Direktiv(D_STEG, villkor=villkor,
                                 handlingar=handlingar))

    for regex in (_M_SATT_NAR, _M_NOLLSTALL_NAR):
        m = regex.match(text)
        if m:
            villkor = las_villkor(m.group("villkor"), kanda)
            handlingar = las_handlingar(m.group("handling"), kanda)
            if handlingar:
                sort = D_DRIFTUT if _bara_system(villkor, kanda) else D_STEG
                return klar(Direktiv(sort, villkor=villkor,
                                     handlingar=handlingar))

    m = _M_VANTA.match(text)
    if m:
        villkor = las_villkor(m.group("villkor"), kanda)
        if not villkor.tomt:
            return klar(Direktiv(D_STEG, villkor=villkor))

    if _M_LARM.search(text):
        return klar(Direktiv(D_LARMLATCH))

    # "... och borja om" i slutet av en rad som i övrigt inte gick att läsa.
    if re.search(r"\bborja om\b", text, re.I):
        return klar(Direktiv(D_BORJA_OM))
    return []


def _bara_system(villkor: Villkor, kanda) -> bool:
    """Sant om varje term i villkoret är en systemsignal eller ett larm.

    Ett villkor som bara är EMG_OK, AIR_OK och SYS_AUTO är driftsvillkoret, och
    en utgång som styrs av det ska följa driften och inte ligga i stegkedjan.
    """
    from . import morfologi as Mo
    if villkor.tomt:
        return False
    for t in villkor.termer:
        if t.signal not in Mo.SYSTEMSIGNALER:
            return False
    return True


_F_OMSESIDIG = re.compile(
    r"^(?P<a>[A-Za-z0-9_]+)\s+och\s+(?P<b>[A-Za-z0-9_]+)\s+far\s+aldrig\s+"
    r"(?:sta|vara)\s+hoga\s+samtidigt", re.I)
_F_FORVILLKOR = re.compile(
    r"^(?P<a>[A-Za-z0-9_]+)\s+far\s+(?:aldrig|inte)\s+ga\s+hog\s+innan\s+"
    r"(?P<b>[A-Za-z0-9_]+)\s+ar\s+hog", re.I)
_F_HALL = re.compile(
    r"^(?P<a>[A-Za-z0-9_]+)\s+far\s+aldrig\s+(?:sta|ga)\s+hog\s+"
    r"(?:nar|utan att)\s+(?P<b>[A-Za-z0-9_]+)\s+ar\s+(?P<niva>lag|hog)", re.I)
_F_ENBART = re.compile(
    r"^(?P<a>[A-Za-z0-9_]+)\s+far\s+vara\s+hog\s+enbart\s+nar\s+"
    r"(?P<b>[A-Za-z0-9_]+)\s+ar\s+(?P<varde>\d+)", re.I)
_F_PERMISSIV = re.compile(
    r"^(?:inget|ingen|inga)\b.*\bnar\s+(?P<b>[A-Za-z0-9_]+)\s+ar\s+lag", re.I)
_F_CYKEL = re.compile(
    r"^ingen\s+ny\s+cykel\s+nar\s+(?P<a>[A-Za-z0-9_]+)\s+ar\s+"
    r"(?P<varde>\d+)\s+eller\s+mer", re.I)
_F_HANDSPARR = re.compile(
    r"^(?:handkorningen|handlaget)\s+far\s+aldrig\s+vara\s+aktiv\s+nar\s+"
    r"(?P<b>[A-Za-z0-9_]+)\s+ar\s+hog", re.I)
# Rader vars krav standardramen redan uppfyller, med den ramregel som gör det.
# Listan är kort med flit: en rad får bara stå här om ramen BEVISLIGEN
# garanterar den, inte om den ser ut att göra det.
_F_RAMTACKT = (
    (re.compile(r"^ett aterstallt nodstopp far aldrig", re.I),
     "ramen: kvittenskravet latchas av NOT EMG_OK och slapper bara pa "
     "stigande flank pa SYS_RESET"),
    (re.compile(r"^SYS_ALARM\s+hog", re.I),
     "ramen: SYS_ALARM ingar i driftsvillkoret, och driftsgrenen nollstaller "
     "varje utgang i samma scan"),
)

_F_AUTOSPARR = re.compile(
    r"^automatiken\s+far\s+aldrig\s+kommendera\s+.*\bnar\s+"
    r"(?P<b>[A-Za-z0-9_]+)\s+ar\s+lag", re.I)


def _las_forregling(rad: str, kanda) -> Optional[Forregling]:
    text = rad.strip().rstrip(".")

    def sig(m, grupp):
        return (m.group(grupp) or "").upper()

    m = _F_OMSESIDIG.match(text)
    if m and sig(m, "a") in kanda and sig(m, "b") in kanda:
        return Forregling(F_OMSESIDIG, rad, sig(m, "a"), sig(m, "b"))
    m = _F_FORVILLKOR.match(text)
    if m and sig(m, "a") in kanda and sig(m, "b") in kanda:
        return Forregling(F_FORVILLKOR, rad, sig(m, "a"), sig(m, "b"))
    m = _F_HALL.match(text)
    if m and sig(m, "a") in kanda and sig(m, "b") in kanda:
        if m.group("niva").lower() == "lag":
            return Forregling(F_HALLVILLKOR, rad, sig(m, "a"), sig(m, "b"))
        return Forregling(F_OMSESIDIG, rad, sig(m, "a"), sig(m, "b"))
    m = _F_ENBART.match(text)
    if m and sig(m, "a") in kanda and sig(m, "b") in kanda:
        return Forregling(F_ENBART, rad, sig(m, "a"), sig(m, "b"),
                          float(m.group("varde")))
    m = _F_CYKEL.match(text)
    if m and sig(m, "a") in kanda:
        return Forregling(F_CYKELSPARR, rad, sig(m, "a"), "",
                          float(m.group("varde")))
    m = _F_HANDSPARR.match(text)
    if m and sig(m, "b") in kanda:
        return Forregling(F_HANDSPARR, rad, "", sig(m, "b"))
    m = _F_AUTOSPARR.match(text)
    if m and sig(m, "b") in kanda:
        return Forregling(F_PERMISSIV, rad, "", sig(m, "b"))
    m = _F_PERMISSIV.match(text)
    if m and sig(m, "b") in kanda:
        return Forregling(F_PERMISSIV, rad, "", sig(m, "b"))
    return None


def las(sekvens: Sequence[str], forreglingar: Sequence[str],
        kanda) -> Lasning:
    """Hela specen till IR. `kanda` är taggnamnen som finns i kartan."""
    ut = Lasning()
    kanda = set(str(k).upper() for k in kanda)
    for rad in sekvens or ():
        direktiv = _las_rad(rad, kanda)
        if direktiv:
            ut.direktiv.extend(direktiv)
        else:
            ut.olasta.append(rad)
    for rad in forreglingar or ():
        f = _las_forregling(rad, kanda)
        if f is not None:
            ut.forreglingar.append(f)
            continue
        tackt = [skal for regex, skal in _F_RAMTACKT if regex.match(rad.strip())]
        if tackt:
            ut.ramtackta.append((rad, tackt[0]))
        else:
            ut.olasta_forreglingar.append(rad)
    return ut


# ---- gränsvärden ur uppgiftstexten --------------------------------------
#
# Ett arbetsområde är en storhet som INTE går att läsa ur en I/O-lista. En
# encoder heter `..._POS` vad än slaglängden är. Talen står i uppgiftstexten,
# i en handfull former, och att läsa dem är samma sorts mönsterläsning som
# resten av modulen. Utbytet över hela banken räknas i M-62: en extraktion som
# bara fungerar på de uppgifter man provade den mot är inte en metod.

@dataclass(frozen=True)
class Intervall:
    """Ett tillåtet område för en mätsignal, med det villkor som gör det
    tillämpligt (tom sträng = alltid)."""

    signal: str
    lag: float
    hog: float
    nar: str = ""
    rad: str = ""


@dataclass(frozen=True)
class Troskel:
    """En boolesk utgång som ska följa en mätsignal över eller under ett tal."""

    utgang: str
    matning: str
    tecken: str
    varde: float
    rad: str = ""


_I_MELLAN = re.compile(r"\bmellan\s+(?P<lag>-?[\d.,]+)\s+och\s+(?P<hog>-?[\d.,]+)", re.I)
_I_OMRADE = re.compile(r"\b\w*omradet\s+(?P<lag>-?[\d.,]+)\s+till\s+"
                       r"(?P<hog>-?[\d.,]+)", re.I)
_I_NAR = re.compile(r"\bnar\s+(?P<sig>[A-Za-z0-9_]+)\s+ar\s+hog", re.I)
_T_UTGANG = re.compile(
    r"(?P<sig>[A-Za-z0-9_]+)\s+(?:ska\s+)?vara\s+hog\s+(?:for|nar)\b"
    r"[^.]*?\b(?P<tecken>over|under|storre an|mindre an)\s+(?P<varde>[\d.,]+)")


def _meningar(text: str):
    for stycke in re.split(r"(?<=[.])\s+|\n", text or ""):
        rensad = stycke.replace("\n", " ").strip()
        if rensad:
            yield rensad


def las_intervall(prompt: str, kanda, matsignaler) -> List[Intervall]:
    """Arbetsområden ur uppgiftstexten, ett per mening som bär ett.

    Bara mätsignaler får ett intervall. En boolesk givare har inget område, och
    ett tal i samma mening som en bit är något annat — en takt, ett antal, en
    massa — och ska inte bli en larmgräns.
    """
    matsignaler = set(str(s).upper() for s in matsignaler)
    ut: List[Intervall] = []
    tagna = set()
    for mening in _meningar(prompt):
        namn = [n for n in _signaler_i(mening, kanda) if n in matsignaler]
        if not namn or namn[0] in tagna:
            continue
        m = _I_MELLAN.search(mening) or _I_OMRADE.search(mening)
        if not m:
            continue
        villkor = ""
        v = _I_NAR.search(mening)
        if v and v.group("sig").upper() in kanda:
            villkor = v.group("sig").upper()
        ut.append(Intervall(namn[0], _tal(m.group("lag")), _tal(m.group("hog")),
                            villkor, mening))
        tagna.add(namn[0])
    return ut


def las_trosklar(prompt: str, kanda, matsignaler, utgangar) -> List[Troskel]:
    """Booleska utgångar som ska följa en mätsignal över eller under ett tal."""
    matsignaler = [str(s).upper() for s in matsignaler]
    utgangar = set(str(s).upper() for s in utgangar)
    ut: List[Troskel] = []
    for mening in _meningar(prompt):
        m = _T_UTGANG.search(mening)
        if not m or m.group("sig").upper() not in utgangar:
            continue
        namn = [n for n in _signaler_i(mening, kanda) if n in matsignaler]
        if not namn:
            # Ingen mätsignal i meningen. Bär kartan exakt EN mätsignal är den
            # den enda kandidaten; bär den flera går tröskeln inte att binda,
            # och då blir det ingen tröskel. Antagandet står i generatorns
            # rapport, så att det syns att det ÄR ett antagande.
            if len(matsignaler) != 1:
                continue
            namn = [matsignaler[0]]
        tecken = ">" if m.group("tecken") in ("over", "storre an") else "<"
        ut.append(Troskel(m.group("sig").upper(), namn[0], tecken,
                          _tal(m.group("varde")), mening))
    return ut


# ---- uppgiftsprosan som sekvens -----------------------------------------
#
# Nivån `prosa` finns för EN fråga, och den frågan bär hela M-62:s slutsats:
# är den strukturerade specen (`control.sequence`) mer maskinläsbar än den
# prosa modellen får? Uppgiftstexten i banken skriver sin sekvens som en
# numrerad lista och sina krav som punkter. Att plocka ut dem är
# dokumentstruktur, inte språkförståelse.

_P_NUMMER = re.compile(r"^\s*(\d+)\.\s+(.*)$")
_P_PUNKT = re.compile(r"^\s*[*-]\s+(.*)$")
_P_FORTSATT = re.compile(r"^\s{2,}(\S.*)$")


def steg_ur_prompt(prompt: str) -> Tuple[List[str], List[str]]:
    """(numrerade steg, punktkrav) ur uppgiftstexten, med radbrytningar hopfogade.

    Returnerar bara listornas rader. Löptexten runt omkring läses inte: den
    bär bakgrund, scen och kedja, och en generator som drar sekvens ur löptext
    gissar.
    """
    numrerade: List[str] = []
    punkter: List[str] = []
    aktuell: Optional[List[str]] = None
    for rad in (prompt or "").splitlines():
        m = _P_NUMMER.match(rad)
        if m:
            numrerade.append(m.group(2).strip())
            aktuell = numrerade
            continue
        m = _P_PUNKT.match(rad)
        if m:
            punkter.append(m.group(1).strip())
            aktuell = punkter
            continue
        m = _P_FORTSATT.match(rad)
        if m and aktuell:
            aktuell[-1] = (aktuell[-1] + " " + m.group(1).strip()).strip()
            continue
        aktuell = None
    return numrerade, punkter


def dela_meningar(rader: Sequence[str]) -> List[str]:
    """Punktkraven som enskilda meningar.

    Ett punktkrav är ofta tre meningar: rubrik, regel och motivering. Reglerna
    läses en mening i taget, därför att grammatiken är en SATS-grammatik.
    """
    ut: List[str] = []
    for rad in rader:
        for mening in _meningar(rad):
            rensad = mening.strip().rstrip(".")
            if rensad:
                ut.append(rensad)
    return ut
