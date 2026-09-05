# -*- coding: utf-8 -*-
"""Vad som gar i stallet, nar valet faller.

`motsagelse.py` har fyra domar och ingen av dem heter "mojlig". En av dem,
`VALET_FALLER`, betyder per DEFINITION att villkoren GAR att uppfylla - bara
inte med den komponent som valts. Domen vet alltsa redan att ett alternativ
finns. Fore den har modulen sa den bara vilken SORTS atgard som behovdes:

    atgard: kravet gar att uppfylla, men inte med den har komponenten.
            Byt komponent - eller mjuka upp kravet

Den raden sager aldrig VILKEN maskin. Operatoren far en dom och hela arbetet
kvar, och han ska da soka i ett bibliotek pa 3 201 komponenter efter det som
grinden redan har talen for att hitta. Den har modulen ar den kopplingen och
ingenting mer.

FYRA REGLER, OCH DE AR FORMKRAV

  1. ALDRIG ETT NAMN UTAN SKAL. Varje forslag bar talet som avgjorde, dess
     enhet, kravet det uppfyller och varifran talet kom. "IRB 4600-60/2.05,
     rackvidd 2 050 mm, ur katalogposten" - inte "prova en IRB 4600".
  2. HOGST EN HANDFULL. En lista pa 200 robotar ar samma fel som att inte
     svara: den flyttar tillbaka hela valet till operatoren och later som ett
     svar. Taket ar `MAX_FORSLAG`, och ordningen bar ett skrivet motiv.
  3. INGET FORSLAG NAR GRINDEN INTE VET. Saknar katalogposten talet blir den
     aldrig ett forslag. Ett falt som saknas ar inte noll (K0), och `OKANT` ar
     aldrig ett godkannande (I3).
  4. `OMOJLIG` FORESLAR ALDRIG. Ar kraven motsagelsefulla i sig hjalper ingen
     maskin, och ett forslag dar hade lurat operatoren att tro att felet ligger
     i komponentvalet. Sparren ar strukturell: `foresla` gar ur pa forsta raden
     om domen inte ar `VALET_FALLER`, och soker da inte ens.

VAD ETT FORSLAG PASTAR, OCH VAD DET INTE PASTAR

Det pastar: *den har komponenten uppfyller det villkor som foll*. Det pastar
INTE att bestallningen blir byggbar med den. Passformen (MK4) och ytbeviset
(MK3) mater fotavtrycket, och en katalogpost bar inga yttermatt (M-61) - de
harleds ur rackvidden fore domen (`layoutmotor.harled_fotavtryck`). Ett storre
alternativ kan alltsa falla pa ytan i stallet. Darfor sager forslagsraden
"uppfyller kravet som foll", aldrig "loser bestallningen", och ordningen ar
minsta-som-racker just for att den sortens omkast ska bli sa osannolik som
ordningen kan gora den.

SOKSKIKTET AGS INTE HAR

Modulen kanner ingen katalog. Den tar en `sokport` - vad som helst med
katalogsok.Katalog:s publika `sok()` - och ar darmed provbar utan ett levande
bibliotek. Tva egenskaper hos den publika ytan styr koden och bada ar matta:

  * EN BRED FRAGA FAR INGA RADER. Over `katalogsok.BRED_FRAGA` traffar (40,
    satt av M-60) svarar sokskiktet med ett SAMMANDRAG per tillverkare och en
    tom radlista. Det ar ratt av sokskiktet - en lista pa 513 rader ar inget
    svar - men det betyder att den har modulen inte kan rakna upp en bred
    traffmangd. Den smalnar da av per tillverkare, precis som sokskiktets eget
    svar uppmanar till, och REDOVISAR vad som anda inte gick att rakna upp.
    MATT i M-163: kravet "rackvidd >= 2 050 mm" ger 513 traffar i det
    installerade biblioteket, varav 122 gar att rakna upp pa det sattet.
  * FAMILJEFILTRET AR EN FALLA I GRUNT LAGE. `familj` fylls bara i ett DJUPT
    index (M-69: markoren ligger vid median 14 215 byte och nas inte av den
    grunda lasningens 4 096). MATT i M-163: `sok(familj="robot")` ger 0 av
    3 201 poster i ett grunt index. Ett forslag som filtrerade pa familj hade
    darfor svarat "ingenting i biblioteket racker" om ett fullt bibliotek.
    Frageen bar alltsa BARA det numeriska kravet.

Endast standardbiblioteket.
"""
from __future__ import annotations

from .storheter import egenskaper, rollen_i

# Hogst sa manga namn i ett forslag.
#
# Talet sjalvt ar STALLT och inte matt, och det ska sta rent ut: uppdraget
# sager "hogst en handfull", och en handfull ar inte tio. Det som ar MATT
# (M-163, mot det installerade biblioteket) ar vad raderna KOSTAR:
# forslagsblocket bar 1 072 tecken fast rubrik, motiv, faltkalla och forbehall,
# plus 119 tecken per rad. Tre rader ar 1 429 tecken, tio ar 2 203 - och hela
# krocken med sina villkorsrader gar da fran 1 904 till 2 706. Det ar den
# skillnaden taket koper, i den post 25_kontextbudget.md kallar
# "verktygsresultat".
#
# Sokskiktets eget listtak ar 10 (katalogsok.MAX_RADER, satt av M-60), och det
# ar ett tak for att BLADDRA i en katalog. Det har ar ett tak for att VALJA en
# maskin, och de tva ar inte samma fraga.
MAX_FORSLAG = 3          # M-163: 119 tecken per rad, blocket 1 429 vid tre

# `max_rader` till sokskiktet nar vi vill ha alla rader det ar villigt att ge.
# Sokskiktet kapar sjalvt en bred fraga fore det har talet betyder nagot; det
# finns bara for att inte arva dess forval pa 10.
_ALLA_RADER = 100000     # M-163: inget tak av eget, bara ett som slar forvalet 10

# Ordningen, och dess motiv. Motivet ar ett formkrav: en sortering utan skal ar
# en godtycklig lista som ser ut som en rangordning.
ORDNINGSMOTIV = (
    "MINSTA SOM RACKER FORST: en komponent med dubbel rackvidd uppfyller "
    "samma krav men tar mer golv, och golvytan ar just det MK3 och MK4 mater. "
    "Lika tal ordnas pa namn, sa att samma bestallning alltid ger samma lista.")


class _Sokfalt(object):
    """En storhet som gar att soka pa, och hur."""

    __slots__ = ("argument", "attribut", "enhet", "vad", "kalla")

    def __init__(self, argument, attribut, enhet, vad, kalla):
        self.argument = argument      # namnet pa sokskiktets keyword-argument
        self.attribut = attribut      # faltet pa en traffrad
        self.enhet = enhet
        self.vad = vad
        self.kalla = kalla


# De storheter ett fallt VAL gar att soka ett alternativ till.
#
# Listan ar KORT med flit. Den bar bara det sokskiktet faktiskt kan filtrera
# pa OCH som betyder samma storhet pa bada sidor. Se `_EJ_SOKBARA` for de
# ovriga, dar skalet star utskrivet i stallet for att fattas.
SOKBARA = {
    "rackvidd_mm": _Sokfalt(
        "min_rackvidd_mm", "rackvidd_mm", "mm", "rackvidden",
        'sokskiktets falt rackvidd_mm, som ar katalogpostens deklarerade '
        '"Reach" (M-76 matte det i 80 % av biblioteket; de ovriga bar inget '
        'tal och far darfor aldrig foreslas)'),
}

# Varfor de andra INTE gar att soka pa. En tom lista utan skal ar ett svar som
# ser ut som ett bibliotek utan traffar.
_EJ_SOKBARA = {
    "massa_kg":
        "sokskiktet bar nyttolast (katalogpostens MaxPayload), inte "
        "komponentens EGEN massa. Att soka pa nyttolast for ett massakrav vore "
        "att lata en parameter bara tva storheter, och da doljs felet i det "
        "vanliga fallet",
    "langd_mm":
        "katalogposten deklarerar inga yttermatt (M-61), sa sokskiktet har "
        "inget mattfilter. Langden harleds ur rackvidden fore domen och ar "
        "darmed ett harlett tal, inte ett sokbart",
    "bredd_mm":
        "katalogposten deklarerar inga yttermatt (M-61), sa sokskiktet har "
        "inget mattfilter",
    "hojd_mm":
        "katalogposten deklarerar inga yttermatt (M-61), sa sokskiktet har "
        "inget mattfilter",
    "yta_mm2":
        "fotavtrycket ar harlett ur langd och bredd, och ingendera star i "
        "katalogposten (M-61)",
    "antal":
        "antalet ar operatorens val, inte en egenskap hos en komponent. Ingen "
        "maskin i biblioteket kan andra det",
}


class Alternativ(object):
    """En komponent som uppfyller kravet, med talet som avgjorde."""

    __slots__ = ("namn", "tillverkare", "tal", "enhet", "vad", "krav",
                 "sokvag")

    def __init__(self, namn, tillverkare, tal, enhet, vad, krav, sokvag):
        self.namn = namn
        self.tillverkare = tillverkare
        self.tal = tal
        self.enhet = enhet
        self.vad = vad
        self.krav = krav
        self.sokvag = sokvag

    def __repr__(self):
        return "Alternativ(%s, %g %s)" % (self.namn, self.tal, self.enhet)

    @property
    def kalla(self):
        """Varifran talet kom, i sin fulla form."""
        return ("ur katalogposten %s" % self.sokvag if self.sokvag
                else "sokskiktet uppgav ingen fil")

    def rad(self, rot=""):
        """Raden operatoren far se. Namn, tal, krav och harkomst - i den
        ordningen, darfor att talet ar SKALET och skalet ska sta bredvid
        namnet.

        `rot` ar en sokvagsdel som redan star utskriven en gang i rubriken.
        Tre rader med samma 130 tecken langa katalogsokvag ar inte tre
        harkomster, det ar en harkomst och 260 tecken brus - och brus ar det
        som gor att ingen laser (M-60).
        """
        if not self.sokvag:
            kalla = "sokskiktet uppgav ingen fil"
        elif rot and self.sokvag.startswith(rot):
            kalla = "ur %s" % self.sokvag[len(rot):]
        else:
            kalla = self.kalla
        return "%s%s, %s %g %s - uppfyller %s [%s]" % (
            self.namn,
            " (%s)" % self.tillverkare if self.tillverkare else "",
            self.vad, self.tal, self.enhet, self.krav, kalla)


def _gemensam_rot(sokvagar):
    """Den katalogdel alla sokvagar delar, med avskiljaren kvar.

    Bara hela katalogled raknas - en gemensam halv katalog ar ingen sokvag och
    hade gjort resten av raden olaslig.
    """
    vagar = [v for v in sokvagar if v]
    if len(vagar) < 2:
        return ""
    avskiljare = "\\" if vagar[0].count("\\") > vagar[0].count("/") else "/"
    delar = [v.split(avskiljare) for v in vagar]
    gemensam = []
    for bitar in zip(*delar):
        if len(set(bitar)) != 1:
            break
        gemensam.append(bitar[0])
    if len(gemensam) < 2:
        return ""
    return avskiljare.join(gemensam) + avskiljare


class Forslag(object):
    """Svaret pa "vad ska jag byta till?" - eller skalet att det inte finns."""

    __slots__ = ("storhet", "roll", "krav", "alternativ", "totalt",
                 "uppraknade", "ej_uppraknade", "skal", "ordningsmotiv",
                 "faltkalla", "rot")

    def __init__(self, storhet, roll, krav, alternativ=(), totalt=0,
                 uppraknade=0, ej_uppraknade=0, skal="", faltkalla=""):
        self.storhet = storhet
        self.roll = roll
        self.krav = krav
        self.alternativ = list(alternativ)
        self.totalt = totalt
        self.uppraknade = uppraknade
        self.ej_uppraknade = ej_uppraknade
        self.skal = skal
        self.faltkalla = faltkalla
        self.ordningsmotiv = ORDNINGSMOTIV
        self.rot = _gemensam_rot([a.sokvag for a in self.alternativ])

    def __repr__(self):
        return "Forslag(%s, %d alternativ)" % (self.storhet,
                                               len(self.alternativ))

    def rader(self):
        ut = ["FORSLAG for %s (rollen %s), kravet ar %s"
              % (self.storhet, self.roll, self.krav)]
        if self.alternativ:
            ut.append(self.ordningsmotiv)
            for i, a in enumerate(self.alternativ, 1):
                ut.append("%d. %s" % (i, a.rad(self.rot)))
            if self.rot:
                ut.append("Sokvagarna ovan star under %s" % self.rot)
            ut.append("Talet kommer ur %s." % self.faltkalla)
            ut.append("Forslaget uppfyller det villkor som foll. Det ar inte "
                      "ett lofte om att bestallningen blir byggbar - ytan och "
                      "passformen provas mot fotavtrycket, som harleds ur "
                      "rackvidden. Kor om bestallningen med komponenten.")
        if self.skal:
            ut.append(self.skal)
        if self.totalt or self.uppraknade or self.ej_uppraknade:
            ut.append("Sokskiktet: %d traffar pa kravet, %d uppraknade, %d "
                      "kunde inte raknas upp."
                      % (self.totalt, self.uppraknade, self.ej_uppraknade))
        return ut

    def text(self):
        return "\n".join(self.rader())


# ------------------------------------------------------------------ kravet

class _Krav(object):
    """De granser pa EN storhet som ett alternativ maste halla."""

    __slots__ = ("nedre", "nedre_strikt", "ovre", "ovre_strikt", "enhet",
                 "text")

    def __init__(self, nedre, nedre_strikt, ovre, ovre_strikt, enhet, text):
        self.nedre = nedre
        self.nedre_strikt = nedre_strikt
        self.ovre = ovre
        self.ovre_strikt = ovre_strikt
        self.enhet = enhet
        self.text = text

    def haller(self, tal):
        if self.nedre is not None:
            if tal < self.nedre or (self.nedre_strikt and tal == self.nedre):
                return False
        if self.ovre is not None:
            if tal > self.ovre or (self.ovre_strikt and tal == self.ovre):
                return False
        return True


def _ar_tal(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _krav_pa(storhet, villkor):
    """Granserna pa `storhet` ur ALLA villkor, eller None om ingen finns.

    Bara ordningsoperatorerna raknas. `eq` utelamnas med flit: ett
    likhetsvillkor pa en katalogstorhet ar i praktiken ett PASTAENDE om den
    valda komponenten ("roboten har rackvidden 1650 mm", lasning.py), inte ett
    krav pa dess ersattare. Toges det med hade forslagsmangden alltid varit
    tom, och tomheten hade sett ut som ett fattigt bibliotek. Krockar ett `eq`
    med en grans ar det redan en MK1 och domen ar da OMOJLIG, som inte
    foreslar nagot.
    """
    enhet = (egenskaper(storhet) or ("", "", ""))[0]
    nedre = ovre = None
    nedre_strikt = ovre_strikt = False
    for v in villkor:
        if v.storhet != storhet or not _ar_tal(v.varde):
            continue
        if v.operator in ("ge", "gt"):
            strikt = v.operator == "gt"
            if nedre is None or v.varde > nedre or (v.varde == nedre and strikt):
                nedre, nedre_strikt = v.varde, strikt
        elif v.operator in ("le", "lt"):
            strikt = v.operator == "lt"
            if ovre is None or v.varde < ovre or (v.varde == ovre and strikt):
                ovre, ovre_strikt = v.varde, strikt
    if nedre is None and ovre is None:
        return None
    delar = []
    if nedre is not None:
        delar.append("%s %g %s" % ("gt" if nedre_strikt else "ge", nedre, enhet))
    if ovre is not None:
        delar.append("%s %g %s" % ("lt" if ovre_strikt else "le", ovre, enhet))
    return _Krav(nedre, nedre_strikt, ovre, ovre_strikt, enhet,
                 " och ".join(delar))


# ------------------------------------------------------------- uppraakningen

def _svara(sokport, **kv):
    """Ett anrop till sokskiktets publika yta. Kastar vidare."""
    return sokport.sok(max_rader=_ALLA_RADER, **kv)


def _rader(sokport, argument, undre):
    """(rader, totalt, ej_uppraknade) ur sokskiktet.

    Sokskiktet vagrar lista en bred fraga och lamnar ett sammandrag per
    tillverkare i stallet (M-60). Vi foljer da dess egen uppmaning och fragar
    om per tillverkare. Det som anda inte gar att rakna upp RAKNAS, sa att
    forslaget kan saga hur mycket det inte sag.
    """
    svar = _svara(sokport, **{argument: undre})
    totalt = int(getattr(svar, "totalt", 0) or 0)
    if getattr(svar, "sammandrag", None) is None:
        return list(getattr(svar, "traffar", ()) or ()), totalt, 0
    rader = []
    ej = 0
    fordelning = svar.sammandrag or {}
    for tillverkare in sorted(fordelning, key=lambda t: (-fordelning[t], t)):
        if not tillverkare:
            # Poster UTAN tillverkare gar inte att smalna av pa. Ett tomt
            # tillverkarfilter ar inget filter alls i sokskiktet, sa fragan
            # hade kommit tillbaka lika bred - och deras antal hade da raknats
            # en gang till. De raknas i stallet ur sammandraget, dar de star
            # med sitt eget tal.
            ej += int(fordelning[tillverkare] or 0)
            continue
        dela = _svara(sokport, tillverkare=tillverkare, **{argument: undre})
        if getattr(dela, "sammandrag", None) is not None:
            ej += int(getattr(dela, "totalt", 0) or 0)
            continue
        rader += list(getattr(dela, "traffar", ()) or ())
    return rader, totalt, ej


def _population(sokport, argument):
    """(alla poster, de som bar faltet alls) - talen bakom ett tomt svar.

    "Ingenting racker" ar bara ett svar om det sager hur manga som provades och
    hur manga som over huvud taget bar talet. Noll av noll ar ett trasigt
    index; noll av 1 437 ar ett besked.
    """
    try:
        alla = int(getattr(_svara(sokport), "totalt", 0) or 0)
        # 0.0 slapper igenom alla poster som deklarerar ett POSITIVT tal och
        # sallar bort dem som inte bar faltet alls - sokskiktets egen regel:
        # en komponent utan angivet varde har inte vardet noll.
        med = int(getattr(_svara(sokport, **{argument: 0.0}), "totalt", 0) or 0)
        return alla, med
    except Exception:
        return None, None


# --------------------------------------------------------------- forslaget

def _falt(storhet):
    """Faltnamnet i en delstorhet, t.ex. 'rackvidd_mm'. None for ovriga."""
    if not storhet.startswith("del."):
        return None
    bitar = storhet.split(".", 2)
    return bitar[2] if len(bitar) == 3 else None


def for_krock(krock, villkor, sokport):
    """Ett `Forslag` for en krock som ar ett fallt VAL. KASTAR ALDRIG.

    Grinden ar en grind. Att ett sokskikt gar sonder - ett trasigt index, en
    rad med skrap i, en port som inte alls ar en port - far gora forslaget
    tomt och sitt skal utskrivet, aldrig fella hela domen. En dom som
    forsvinner i ett undantag ar ett sant nej som blev till ingenting.
    """
    try:
        return _bygg(krock, villkor, sokport)
    except Exception as fel:                      # noqa: BLE001 - se ovan
        return Forslag(krock.storhet, rollen_i(krock.storhet) or "?",
                       "(kunde inte laesas)",
                       skal="Forslagssokningen gick sonder: %s (%s). Domen "
                            "star kvar; det ar bara namnen som saknas."
                            % (fel, type(fel).__name__))


def _bygg(krock, villkor, sokport):
    roll = rollen_i(krock.storhet) or "?"
    falt = _falt(krock.storhet)
    krav = _krav_pa(krock.storhet, villkor)
    if krav is None:
        return Forslag(krock.storhet, roll, "(inget sokbart krav)",
                       skal="Kravet ar inte en storleksgrans, sa det finns "
                            "inget tal att soka pa. Ett forslag hade da varit "
                            "en gissning.")
    sokfalt = SOKBARA.get(falt)
    if sokfalt is None:
        return Forslag(krock.storhet, roll, krav.text,
                       skal="Sokskiktet kan inte soka pa %s: %s."
                            % (krock.storhet,
                               _EJ_SOKBARA.get(falt,
                                               "storheten star inte bland de "
                                               "sokbara falten")))
    if krav.nedre is None:
        return Forslag(krock.storhet, roll, krav.text,
                       skal="Kravet ar bara ett tak (%s). Sokskiktet filtrerar "
                            "pa MINSTA varde, inte pa storsta, sa den mangd "
                            "som uppfyller taket gar inte att fraga fram. "
                            "Talen finns i katalogen; filtret gor det inte."
                            % krav.text)

    try:
        rader, totalt, ej = _rader(sokport, sokfalt.argument, krav.nedre)
    except Exception as fel:
        return Forslag(krock.storhet, roll, krav.text,
                       skal="Sokskiktet svarade inte: %s (%s). Grinden gissar "
                            "inte at den." % (fel, type(fel).__name__))

    alternativ = []
    utan_tal = 0
    for t in rader:
        tal = getattr(t, sokfalt.attribut, None)
        if not _ar_tal(tal):
            # Ett namn utan tal ar en gissning. Regel 1.
            utan_tal += 1
            continue
        if not krav.haller(float(tal)):
            continue
        namn = getattr(t, "namn", "") or ""
        if not namn:
            utan_tal += 1
            continue
        sokvag = getattr(t, "sokvag", "") or ""
        alternativ.append(Alternativ(
            namn, getattr(t, "tillverkare", "") or "", float(tal),
            sokfalt.enhet, sokfalt.vad, krav.text, sokvag))
    alternativ.sort(key=lambda a: (a.tal, a.namn))
    uppraknade = len(rader)

    skal = ""
    if not alternativ:
        if ej:
            skal = ("Ingen kandidat gick att namna: %d av %d traffar lamnade "
                    "sokskiktet som ett sammandrag (en bred fraga far inga "
                    "rader, M-60) och gar darfor inte att rakna upp harifran. "
                    "Smalna av bestallningen - tillverkare eller ett "
                    "namnfragment - sa gar de att namna." % (ej, totalt))
        elif totalt == 0:
            alla, med = _population(sokport, sokfalt.argument)
            if alla is None:
                skal = ("0 av biblioteket uppfyller %s, och sokskiktet svarade "
                        "inte pa hur stort biblioteket ar." % krav.text)
            else:
                skal = ("0 av %d poster som sokskiktet visar (utfasade "
                        "raknas inte) uppfyller %s. %d av dem deklarerar %s "
                        "alls; resten bar inget tal och far darfor aldrig "
                        "foreslas. Kravet star kvar som uppfyllbart - "
                        "biblioteket ar inte varlden, och en komponent som "
                        "klarar det kan finnas utanfor den har installationen."
                        % (alla, krav.text, med, sokfalt.vad))
        else:
            skal = ("%d traffar holl den undre gransen, men ingen av de %d som "
                    "gick att rakna upp holl hela kravet %s."
                    % (totalt, uppraknade, krav.text))
    elif ej:
        skal = ("%d av %d traffar gick inte att rakna upp (sokskiktet lamnar "
                "inga rader for en bred fraga, M-60), sa listan ar de minsta "
                "bland de %d som gick - inte bevisat de minsta i hela "
                "biblioteket." % (ej, totalt, uppraknade))
        if (krav.nedre is not None and not krav.nedre_strikt
                and alternativ[0].tal == krav.nedre):
            # ... med ETT undantag som gar att bevisa aven med halv
            # uppraakning: traffar kravet med noll marginal kan ingen
            # ouppraknad post ligga lagre och anda halla det.
            skal += (" Den forsta ar dock ett bevisat minimum: den traffar "
                     "gransen exakt, och lagre an gransen haller ingen.")
    if utan_tal:
        skal = (skal + " " if skal else "") + (
            "%d traffar saknade talet och utelamnades: ett falt som saknas ar "
            "inte noll." % utan_tal)

    return Forslag(krock.storhet, roll, krav.text, alternativ[:MAX_FORSLAG],
                   totalt, uppraknade, ej, skal, sokfalt.kalla)
