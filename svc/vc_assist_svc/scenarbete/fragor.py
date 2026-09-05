# -*- coding: utf-8 -*-
"""FRAGORNA: vad systemet inte vet, och VEM som kan svara.

Uppdelningen ar inte uppfunnen har. Den ar hamtad ur operatorens eget
forarbete i sibling-project som delar
en oppen fraga efter vem som kan besvara den, med den egna motiveringen:

    "Att skicka en matuppgift till operatoren som 'beslut' ar samma fel som
     att gissa talet."

For fritextvagen till en befintlig scen ar det skillnaden som gor att
DIAGNOSEN gar att bygga forst:

    MATNING        "varfor svalter station 3?" Ogat kan kora den. Fragan far
                   ALDRIG ga till operatoren - han skulle behova gissa om
                   nagot vi kan mata. Den routas till ett LASANDE verktyg.
    OPERATORSVAL   "vilket av de tre gripdonen menade du?" Ingen matning i
                   varlden avgor vad han menade. Bara han kan svara.

En vag som fragar anvandaren om nagot den kunde ha matt ar lika trasig som en
som gissar. Bada har slutat anvanda det den har.

FAIL-CLOSED PA BADA HALLEN

En MATNING utan namngivet verktyg ar ingen matning - det ar en gissning med
bra rykte, och konstruktionen kastar (Fragefel). Ett verktyg som SKRIVER far
aldrig sta i en matningsfraga: da vore "matningen" en scenandring, och hela
lassparren gick forlorad genom en fraga.

GRUPPERINGEN

sibling-project/lib/negotiation_protocol.py grupperar hogst fyra fragor per
runda i stallet for att lamna hela listan pa en gang. Skalet ar praktiskt och
vart att arva: en forhandling som dumpar tolv fragor har blivit ett formular,
och ett formular far ett formulars svar. Talet ar ADOPTERAT ur det repot och
INTE matt har - se M-162:s LIMITS.

Endast standardbiblioteket plus tjanstens egna lager.
"""
from __future__ import annotations

MATNING = "MATNING"
OPERATORSVAL = "OPERATORSVAL"
VEM = (MATNING, OPERATORSVAL)

# Hogst sa manga fragor i en runda. ADOPTERAT ur
# sibling-project/lib/negotiation_protocol.py och inte matt i det har repot; se
# M-162 LIMITS. Talet ar en STANDARD och inte en grans - den som vet sin
# operators talamod skickar sitt eget.
MAX_FRAGOR_PER_RUNDA = 4    # M-162: adopterat, ej matt har.

LINTKODER = {
    "FR1_MATNING_SOM_BESLUT": "en fraga som en matning kan svara pa stalldes "
                              "till operatoren",
}


class Fragefel(Exception):
    """Fragan haller inte sin egen form. Fyrar vid konstruktion, aldrig i drift."""


class Fraga(object):
    """En oppen fraga, med vem som kan svara och varfor den ar oppen.

    Falten foljer formen i sibling-project
    morgonrapport_gen_v1.py:_beslutsraderna(): fragan i en mening, vad som ar
    kant, vad som hander vid varje svar, och skalet. Inget tal skrivs for hand
    in i texten - kandidaterna och verktygen ar egna falt, sa att den som
    laser kan sla upp dem.
    """

    __slots__ = ("text_", "vem", "verktyg", "kandidater", "skal")

    def __init__(self, text, vem, verktyg=(), kandidater=(), skal=""):
        if vem not in VEM:
            raise Fragefel("unknown responder %r; the two are %s"
                           % (vem, ", ".join(VEM)))
        if not (text or "").strip():
            raise Fragefel("a question without text is not a question")
        if not (skal or "").strip():
            raise Fragefel(
                "fragan %r bar inget skal. En fraga utan skal gar inte att "
                "vaga mot att lata bli att stalla den" % (text,))
        verktyg = tuple(verktyg)
        if vem == MATNING:
            if not verktyg:
                raise Fragefel(
                    "fragan %r ar markt MATNING men namner inget verktyg som "
                    "kan kora den. En matning ingen kan utfora ar en gissning "
                    "med bra rykte" % (text,))
            _krav_lasande(text, verktyg)
        self.text_ = text
        self.vem = vem
        self.verktyg = verktyg
        self.kandidater = tuple(kandidater)
        self.skal = skal

    def __repr__(self):
        return "Fraga(%s, %r)" % (self.vem, self.text_)

    def rad(self):
        """Raden operatoren far se. Bara OPERATORSVAL hamnar nagonsin har."""
        delar = [self.text_, "    varfor: %s" % self.skal]
        if self.kandidater:
            delar.append("    alternativ: %s" % ", ".join(self.kandidater))
        return "\n".join(delar)


def _krav_lasande(text, verktyg):
    """Ett skrivande verktyg far aldrig sta i en matningsfraga.

    Kontrollen stalls till verktygets deklarerade effect - samma falt som
    lassparren och utforarens routingtabell laser (I12). Utan den vore en
    fraga en vag runt lassparren: "vi behover mata det har" med ett
    set_transform i svansen.
    """
    from ..verktyg.register import REGISTER
    fel = []
    for namn in verktyg:
        v = REGISTER.get(namn)
        if v is None:
            fel.append("%s finns inte bland de %d registrerade verktygen"
                       % (namn, len(REGISTER)))
        elif v.effect != "read":
            fel.append("%s har effect=%s; en matningsfraga far bara namna "
                       "lasande verktyg, annars ar 'matningen' en scenandring"
                       % (namn, v.effect))
    if fel:
        raise Fragefel("the question %r: %s" % (text, "; ".join(fel)))


def till_operatoren(fragor):
    """De fragor som faktiskt ska stallas till en manniska."""
    return tuple(f for f in fragor if f.vem == OPERATORSVAL)


def till_matning(fragor):
    """De fragor systemet ska svara pa sjalvt, genom att lasa."""
    return tuple(f for f in fragor if f.vem == MATNING)


def granska_till_operatoren(fragor):
    """[(lintkod, text)] om nagon matbar fraga skulle gatt till operatoren.

    Grinden provar en LISTA som nagon tankt lamna over. Den fyrar pa exakt
    det fel kravformulering_v1.py namner: en matuppgift skickad som ett
    beslut.
    """
    ut = []
    for f in fragor:
        if f.vem != MATNING:
            continue
        ut.append(("FR1_MATNING_SOM_BESLUT",
                   "%r ar markt MATNING och kan koras med %s. Att stalla den "
                   "till operatoren ar att be honom gissa om nagot vi kan mata"
                   % (f.text_, ", ".join(f.verktyg))))
    return ut


def rundor(fragor, tak=MAX_FRAGOR_PER_RUNDA):
    """Fragorna grupperade i rundor om hogst `tak` stycken."""
    if tak < 1:
        raise Fragefel("a cap of %r questions per round closes the question path completely"
                       % (tak,))
    fragor = tuple(fragor)
    return tuple(fragor[i:i + tak] for i in range(0, len(fragor), tak))
