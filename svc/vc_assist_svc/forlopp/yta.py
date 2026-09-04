# -*- coding: utf-8 -*-
"""Förloppsytan: vad användaren ser medan systemet arbetar.

`Forlopp` är protokollet som förs MEDAN körningen pågår. `rendera` gör om det
till text. De två är skilda med flit: grinden i `grind.py` dömer PARET, och
kan därför fälla vilken renderare som helst — också en som inte är skriven än.
Bygger vi en webbsida någon gång är det samma grind som vaktar den.

## Formen är katalogsökningens (M-60), och det är inte en tillfällighet

1. **Rader, inte JSON.** Ett fast antal fält per rad. Klammer bär ingen
   information för den som läser.
2. **Alltid "N totalt, visar M".** En visning som inte säger hur mycket den
   inte visade ser uttömmande ut. Trimningen är aldrig tyst.
3. **`saknas` är ett förstklassigt svar.** Ögat som inte kört står som
   `saknas`, aldrig som tomt och aldrig som noll.

Till dem kommer en fjärde, som hör just den här ytan till:

4. **Ett fällt läge ser ut som fällt.** Läget står på första raden, det är
   härlett ur händelserna, och `FALLET` är absorberande. Frasen som betyder
   att något arbetar (`PAGAR_MARKOR`) skrivs bara i läget ARBETAR.

## Grindens egna ord ramas in, aldrig om

Ett `ordagrant`-fält skrivs ut RÅTT, utan indrag och utan radprefix, mellan
två markörrader. Det är samma val som `reparation.standardinramning` gjorde,
och av samma skäl: prefixar man varje rad finns inte grindens sträng längre i
texten, och då går det inte att kontrollera att den kom fram hel.
"""
from __future__ import annotations

import re
import time
from typing import List, Optional, Sequence, Tuple

from .handelser import (ARBETAR, AVBRUTET, EJ_PROVAT, EJ_STARTAT, FALLET,
                        Forloppsfel, Handelse, KLART, MED_EGEN_SEKTION,
                        Ovisshet, PAGAR_MARKOR, RACKVIDDEN, STEG_FOLL,
                        STEG_HOPPAT, STEG_KLART, STEG_PAGAR, STEG_VANTAR,
                        Steg, TYST, UTANFOR_RACKVIDD, VANTAR)

# Hur många händelserader visningen skriver ut. MÄTT i M-64: en händelserad
# är 40-90 tecken, så tolv rader kostar under 1 100 och hela ytan mäter
# 2 321 tecken i sitt dyraste läge. Utan taket kostade en körning med 204
# händelser 8 481 tecken i stället för 1 608. Händelser som bär någon annans
# ord trimmas ALDRIG bort, oavsett tak.
MAX_HANDELSERADER = 12          # Satt av M-64.

# Hur länge det får gå mellan två VERKLIGA händelser innan läget blir TYST.
# 24_samtalsloopen.md §7: "Tystnad i två minuter ar ett gränssnittsfel", och
# talet är valt långt under operatörens gräns och långt över bryggans värsta
# uppmätta tur och retur på 13,45 ms (M-03), så ett överskridande alltid
# pekar på modellen eller på en körning och aldrig på bryggan.
TYSTNADSTAK_S = 5.0             # PRELIMINÄR. Satts av M-28.

SAKNAS = "saknas"

# Sektioner ögats rapport MÅSTE bära för att domen ska betyda något. Samma
# lista som `guldgrind.OBLIGATORISKA_SEKTIONER`, och den kopieras hit i
# stället för att importeras av samma skäl som `stationsgrind.py` kopierar
# grindnamnen: guldgrinden är py2-giltig och ska inte dras in i tjänstelagret.
# Provet `test_forlopp.py::test_sektionslistan_ar_guldgrindens` håller ihop dem.
#
# HONESTY är den bärande. `41_ogat_kontrakt.md` regel 5 säger att en
# överträdelse tvingar FAIL, men regeln är TOM om sektionen inte finns. En
# rapport utan HONESTY har alltså ingen ärlighetsgrind alls — och den såg ut
# som guld.
# LIMITS kom med v2 (M-65) och är den som hör den här fasen till: en rapport
# som inte säger vad ögat INTE ser har inte sagt allt. Samma krav som
# visningens eget avsnitt "VET INTE", en våning ned.
OBLIGATORISKA_SEKTIONER = ("MOTION", "HONESTY", "LIMITS")

# Vad visningen skriver när en obligatorisk sektion saknas. Grinden letar
# efter exakt den här inledningen i en främmande renderares text.
SEKTION_SAKNAS = "SEKTIONEN %s SAKNAS I ÖGATS RAPPORT"

# Rubriken på avsnittet om vad systemet inte vet. Det avsnittet får aldrig
# saknas och aldrig vara tomt: räckvidden i `50_grindar.md` gäller varje
# körning, också en som gick igenom.
RUBRIK_VET_INTE = "VET INTE:"

_SEKTIONSRAD = re.compile(r"^SECTION (\S+)\s*$", re.M)

_MARKOR_START = "--- %s, ordagrant ---"
_MARKOR_SLUT = "--- slut ---"

# Vad ett steg som stod på PÅGÅR säger när körningen inte längre arbetar. Ett
# steg som står kvar som "pågår" i ett stilla läge är precis den snurrande
# symbolen fasens grind förbjuder.
_STOPPAT_MITT_I = {
    FALLET: "pågick när körningen föll",
    AVBRUTET: "pågick när körningen avbröts",
    TYST: "pågick när det blev tyst",
    KLART: "stod kvar som pågående när svaret levererades",
    VANTAR: "pågår inte; kön väntar på operatören",
    EJ_STARTAT: "pågick innan körningen börjat",
}


class Forlopp(object):
    """Körningens egen berättelse, förd MEDAN den pågår.

    Ytan är avsiktligt liten och synkron: den som kör varvet för protokollet
    själv, precis som kopplaren redan gör med sina `Varv`. Ingen tråd, ingen
    kö, ingen bakgrundspumpe — bryggan får inte röras från en bakgrundstråd
    (I13), och en förloppsyta som behöver en egen klocka skulle ärva just det
    problem `26_appen.md` §1.4 avvisar panelen inne i VC för.
    """

    def __init__(self, order_id: str = "", uppgift: str = "",
                 klocka=time.time, tystnadstak: float = TYSTNADSTAK_S,
                 max_handelserader: int = MAX_HANDELSERADER):
        self.order_id = order_id or "utan id"
        self.uppgift = uppgift
        self.klocka = klocka
        self.tystnadstak = float(tystnadstak)
        self.max_handelserader = int(max_handelserader)
        self.t0 = klocka()
        self.handelser: List[Handelse] = []
        self.steg: List[Steg] = []
        self.ovissheter: List[Ovisshet] = [
            Ovisshet(namn, "%-19s %s" % (nyckel, skal), UTANFOR_RACKVIDD)
            for nyckel, namn, skal in RACKVIDDEN]

    # ---- att föra protokollet -------------------------------------------

    def lagg(self, sort: str, text: str, steg: str = "",
             ordagrant: str = "") -> Handelse:
        h = Handelse(sort=sort, text=text, t=self.klocka(), steg=steg,
                     ordagrant=ordagrant)
        self.handelser.append(h)
        return h

    def plan(self, steg: Sequence[str]) -> Handelse:
        namn = [str(s) for s in steg]
        if not namn:
            raise Forloppsfel(
                "en plan utan steg går inte att visa förloppet för; en tom "
                "plan är inte ett arbete som pågår")
        self.steg = [Steg(n) for n in namn]
        return self.lagg("PLAN", "%d steg: %s" % (len(namn), ", ".join(namn)))

    def _steg(self, namn: str) -> Steg:
        for s in self.steg:
            if s.namn == namn:
                return s
        s = Steg(namn)
        self.steg.append(s)
        return s

    def steg_borjar(self, namn: str, beskrivning: str = "") -> Handelse:
        s = self._steg(namn)
        s.satt(STEG_PAGAR)
        s.t_start = self.klocka()
        return self.lagg("VERKTYG_START", beskrivning or namn, steg=namn)

    def steg_klart(self, namn: str, ms: Optional[float] = None) -> Handelse:
        s = self._steg(namn)
        s.satt(STEG_KLART)
        s.t_slut = self.klocka()
        text = namn if ms is None else "%.1f ms" % ms
        return self.lagg("VERKTYG_KLART", text, steg=namn)

    def steg_foll(self, namn: str, felnyckel: str) -> Handelse:
        """Ett anrop som föll. Det är INTE detsamma som att körningen föll."""
        s = self._steg(namn)
        s.satt(STEG_FOLL, felnyckel)
        s.t_slut = self.klocka()
        return self.lagg("VERKTYG_FEL", felnyckel, steg=namn,
                         ordagrant=felnyckel)

    def steg_hoppat(self, namn: str, skal: str) -> Handelse:
        s = self._steg(namn)
        s.satt(STEG_HOPPAT, skal)
        self.vet_inte(namn, skal)
        return self.lagg("VERKTYG_KLART", "hoppat: %s" % skal, steg=namn)

    def grind(self, namn: str, ok: bool, ordagrant: str = "") -> Handelse:
        """En grind som KÖRDES, med grindens egna ord.

        En grind som inte kunde köras hör inte hit. Den är en ovisshet
        (`vet_inte`), aldrig ett grindutfall — tystnad är aldrig ett
        godkännande (I3).
        """
        return self.lagg("GRIND", "GODKÄND" if ok else "FÖLL", steg=namn,
                         ordagrant=ordagrant)

    def dom(self, ogontext: str) -> Handelse:
        """Ögats dom, ordagrant som ögat skrev den (I1, regel A-5)."""
        return self.lagg("DOM", "ögat har dömt", ordagrant=ogontext)

    def guld(self, beslutstext: str) -> Handelse:
        return self.lagg("GULD", beslutstext, ordagrant=beslutstext)

    def ko_vantar(self, qid: str, desc: str, dodar_pumpen: str = "") -> Handelse:
        text = desc if not dodar_pumpen else "%s — VARNING: %s" % (desc,
                                                                   dodar_pumpen)
        return self.lagg("KO_VANTAR", text, steg=qid, ordagrant=desc)

    def ko_godkand(self, qid: str) -> Handelse:
        return self.lagg("KO_GODKAND", "godkänd av operatören", steg=qid)

    def ko_avvisad(self, qid: str) -> Handelse:
        return self.lagg("KO_AVVISAD", "avvisad av operatören", steg=qid)

    def ogat_provtar(self, prov: int) -> Handelse:
        return self.lagg("OGAT_PROVTAR", "%d prov" % prov)

    def degraderad(self, skal: str) -> Handelse:
        return self.lagg("DEGRADERAD", skal, ordagrant=skal)

    def omskrivning(self, skal: str) -> Handelse:
        """24_samtalsloopen.md §7: en omskrivning döljs inte."""
        return self.lagg("OMSKRIVNING", skal, ordagrant=skal)

    def puls(self) -> Optional[Handelse]:
        """Hjärtslag, men bara när tystnaden faktiskt överskridit taket.

        Hjärtslaget räknas ALDRIG som framsteg. Gjorde det det skulle varje
        puls nolla tystnadsklockan och en död körning stå kvar på ARBETAR för
        alltid — mätt i M-64: 600 av 600 avläsningar.
        """
        tyst = self.tyst_sedan()
        if tyst <= self.tystnadstak:
            return None
        sista = self.sista_framsteg()
        vad = ("%s %s" % (sista.sort, sista.text)) if sista else "inget alls"
        return self.lagg("HJARTSLAG",
                         "%s, sedan %.1f s" % (vad, tyst))

    def fall(self, skal: str) -> Handelse:
        """Körningen föll. Absorberande: härifrån går det inte att arbeta."""
        if not (skal or "").strip():
            raise Forloppsfel(
                "ett fall utan skäl går inte att visa; 'något gick fel' är "
                "precis det besked fasens grind finns för att förbjuda")
        return self.lagg("FALLET", skal, ordagrant=skal)

    def avbruten(self, skal: str) -> Handelse:
        return self.lagg("AVBRUTEN", skal, ordagrant=skal)

    def svar(self, text: str) -> Handelse:
        return self.lagg("SVAR", text, ordagrant=text)

    def vet_inte(self, namn: str, skal: str,
                 klass: str = EJ_PROVAT) -> Ovisshet:
        o = Ovisshet(namn, skal, klass)
        self.ovissheter.append(o)
        return o

    # ---- vad som gäller just nu -----------------------------------------

    def sista_framsteg(self) -> Optional[Handelse]:
        for h in reversed(self.handelser):
            if h.framsteg:
                return h
        return None

    def tyst_sedan(self) -> float:
        sista = self.sista_framsteg()
        return self.klocka() - (sista.t if sista else self.t0)

    def obesvarade_koposter(self) -> Tuple[str, ...]:
        vantar: List[str] = []
        for h in self.handelser:
            if h.sort == "KO_VANTAR":
                vantar.append(h.steg)
            elif h.sort in ("KO_GODKAND", "KO_AVVISAD") and h.steg in vantar:
                vantar.remove(h.steg)
        return tuple(vantar)

    @property
    def lage(self) -> str:
        """Läget, HÄRLETT. Går aldrig att sätta, och FALLET är absorberande."""
        if not self.handelser:
            return EJ_STARTAT
        sorter = set(h.sort for h in self.handelser)
        if "FALLET" in sorter:
            return FALLET
        if "AVBRUTEN" in sorter:
            return AVBRUTET
        if "SVAR" in sorter:
            return KLART
        if self.obesvarade_koposter():
            return VANTAR
        if self.tyst_sedan() > self.tystnadstak:
            return TYST
        return ARBETAR

    def fallskal(self) -> Optional[str]:
        for h in self.handelser:
            if h.sort in ("FALLET", "AVBRUTEN"):
                return h.ordagrant or h.text
        return None

    def pagaende_steg(self) -> Optional[Steg]:
        for s in self.steg:
            if s.status == STEG_PAGAR:
                return s
        return None

    def grindar(self) -> Tuple[Handelse, ...]:
        return tuple(h for h in self.handelser if h.sort == "GRIND")

    def domar(self) -> Tuple[Handelse, ...]:
        return tuple(h for h in self.handelser if h.sort == "DOM")

    def guldbeslut(self) -> Optional[Handelse]:
        for h in reversed(self.handelser):
            if h.sort == "GULD":
                return h
        return None

    def ordagranna(self) -> Tuple[str, ...]:
        """Varje främmande sträng som MÅSTE nå användaren oförvanskad."""
        ut: List[str] = []
        for h in self.handelser:
            if h.ordagrant and h.ordagrant not in ut:
                ut.append(h.ordagrant)
        return tuple(ut)


# ------------------------------------------------------------- renderingen

def saknade_sektioner(ogontext: str) -> Tuple[str, ...]:
    """Obligatoriska sektioner ögats rapport INTE bär.

    Att läsa sektionsnamnen ur ögats egen text är inte att räkna om ett mått.
    Grinden mäter ingenting; den upptäcker att en grind aldrig kört. Det är
    exakt vad `guldgrind.doma_cell` redan gör, och det görs om här därför att
    visningen kan komma att stå UTAN en guldgrind — och en dom som visas som
    en dom när ärlighetsgrinden aldrig kört är ett falskt grönt hos
    användaren i stället för hos oss.
    """
    funna = set(_SEKTIONSRAD.findall(ogontext or ""))
    return tuple(n for n in OBLIGATORISKA_SEKTIONER if n not in funna)


def _saknade_i_domarna(f: "Forlopp") -> List[Tuple[str, str]]:
    ut: List[Tuple[str, str]] = []
    for h in f.domar():
        for namn in saknade_sektioner(h.ordagrant):
            ut.append((namn, SEKTION_SAKNAS % namn))
    return ut


def _block(vem: str, text: str) -> List[str]:
    """Någon annans ord, rått, mellan två markörrader."""
    return [_MARKOR_START % vem, text, _MARKOR_SLUT]


def okorda_steg(f: "Forlopp", lage: Optional[str] = None) -> Tuple[Steg, ...]:
    """Steg utan utfall, i en körning som är slut.

    Ett levererat svar över en halvkörd plan är den klassiska falska grönen:
    allt som står i visningen är sant, och det som avgör saknas. Stegen
    härleds i stället för att föras in, så att den som driver förloppet inte
    kan glömma bort dem.

    Ett steg som stod på PÅGÅR skiljs från ett som aldrig startade, och det
    är inte kosmetik: ett påbörjat steg kan ha hunnit ha verkan innan
    körningen dog, och en omkörning skulle kunna ladda in en komponent två
    gånger (`24_samtalsloopen.md` §5). De två får inte se likadana ut.
    """
    if (f.lage if lage is None else lage) not in (KLART, FALLET, AVBRUTET):
        return ()
    return tuple(s for s in f.steg if s.status in (STEG_VANTAR, STEG_PAGAR))


def _okort_skal(lage: str, steg: Steg) -> str:
    if steg.status == STEG_PAGAR:
        return ("påbörjat, utan utfall; kan ha hunnit ha verkan "
                "(24_samtalsloopen.md §5)")
    return "steget kördes aldrig; körningen slutade som %s" % lage


def _stegrader(f: Forlopp, lage: str, nu: float) -> List[str]:
    klara = sum(1 for s in f.steg if s.status == STEG_KLART)
    okorda = okorda_steg(f, lage)
    aldrig = [s for s in okorda if s.status != STEG_PAGAR]
    avbrutna = [s for s in okorda if s.status == STEG_PAGAR]
    extra = []
    if aldrig:
        extra.append("%d kördes aldrig" % len(aldrig))
    if avbrutna:
        extra.append("%d utan utfall" % len(avbrutna))
    rader = ["STEG: %d av %d klara%s"
             % (klara, len(f.steg),
                (", " + ", ".join(extra)) if extra else "")]
    for i, s in enumerate(f.steg, 1):
        if s.status == STEG_PAGAR and lage == ARBETAR:
            sedan = nu - (s.t_start if s.t_start is not None else f.t0)
            status = "%s %.1f s" % (PAGAR_MARKOR, sedan)
        elif s.status == STEG_PAGAR:
            status = _STOPPAT_MITT_I[lage]
        elif s.skal:
            status = "%s: %s" % (s.status, s.skal)
        else:
            status = s.status
        rader.append("  %2d %-26s %s" % (i, s.namn, status))
    return rader


def _grindrader(f: Forlopp) -> List[str]:
    grindar = f.grindar()
    if not grindar:
        return ["GRINDAR: %s — ingen grind har kört" % SAKNAS]
    fallna = [h for h in grindar if h.text != "GODKÄND"]
    rader = ["GRINDAR: %d körda, %d föll" % (len(grindar), len(fallna))]
    for h in grindar:
        rader.append("  %-26s %s" % (h.steg, h.text))
        if h.ordagrant:
            rader.extend(_block("%s, grindens egna ord" % h.steg,
                                h.ordagrant))
    return rader


def _domrader(f: Forlopp) -> List[str]:
    domar = f.domar()
    if not domar:
        rader = ["ÖGATS DOM (grind 5): %s — ögat har inte kört." % SAKNAS,
                 "  En körning utan ögondom är kandidat, aldrig guld."]
    else:
        rader = ["ÖGATS DOM (grind 5), som ögat skrev den:"]
        for h in domar:
            rader.extend(_block("ögats egen utdata", h.ordagrant))
        for _namn, rad in _saknade_i_domarna(f):
            rader.append("%s: den grinden har aldrig kört, så domen är inte "
                         "ett godkännande." % rad)
    guld = f.guldbeslut()
    if guld is None:
        rader.append("GULDBESLUT: %s — guldgrinden har inte dömt" % SAKNAS)
    elif not domar:
        # Regel A-6: fält 6 visar aldrig guld utan fält 5. Visningen döljer
        # inte beslutet - den skriver ut att det står utan underlag.
        rader.append("GULDBESLUT UTAN ÖGONDOM, saknar underlag: %s"
                     % guld.ordagrant)
    else:
        rader.append("GULDBESLUT: %s" % guld.ordagrant)
    return rader


def _handelserader(f: Forlopp) -> List[str]:
    alla = f.handelser
    # Händelser som bär någon annans ord trimmas aldrig bort.
    maste = [h for h in alla if h.ordagrant]
    ovriga = [h for h in alla if not h.ordagrant]
    plats = max(0, f.max_handelserader - len(maste))
    visade = set(id(h) for h in maste) | set(id(h) for h in ovriga[-plats:])
    valda = [h for h in alla if id(h) in visade]
    rader = ["HÄNDELSER: %d totalt, visar %d" % (len(alla), len(valda))]
    for h in valda:
        rad = h.rad(f.t0)
        rader.append("  " + rad)
        # En flerradig felnyckel ryms inte i en rad. Den som inte har ett eget
        # avsnitt får sitt block här, så att den når användaren HEL.
        if (h.ordagrant and h.sort not in MED_EGEN_SEKTION
                and h.ordagrant not in rad):
            rader.extend(_block("%s, källans egna ord" % h.sort,
                                h.ordagrant))
    dolda = len(alla) - len(valda)
    if dolda:
        rader.append("  ... %d till, ej visade." % dolda)
    return rader


def _ovissrader(f: Forlopp, lage: str) -> List[str]:
    rackvidd = [o for o in f.ovissheter if o.klass == UTANFOR_RACKVIDD]
    korning = [o for o in f.ovissheter if o.klass == EJ_PROVAT]
    # En saknad sektion i ögats rapport är en grind som aldrig kört. Den
    # härleds ur domen i stället för att föras in i protokollet, så att den
    # inte kan glömmas bort av den som driver förloppet.
    harledda = [("sektion " + namn,
                 "ögats rapport bär ingen SECTION %s; den grinden har aldrig "
                 "kört" % namn)
                for namn, _rad in _saknade_i_domarna(f)]
    harledda += [("steg " + s.namn, _okort_skal(lage, s))
                 for s in okorda_steg(f, lage)]
    rader = ["%s %d poster" % (RUBRIK_VET_INTE,
                               len(f.ovissheter) + len(harledda)),
             "  utanför räckvidd (50_grindar.md). Ögats eget namn i mitten:"]
    for o in rackvidd:
        rader.append("    %-18s %s" % (o.namn, o.skal))
    rader.append("  ej prövat i den här körningen:")
    if not korning and not harledda:
        rader.append("    (inget utöver räckvidden)")
    for o in korning:
        rader.append("    %-24s %s" % (o.namn, o.skal))
    for namn, skal in harledda:
        rader.append("    %-24s %s" % (namn, skal))
    return rader


def rendera(f: Forlopp) -> str:
    """Förloppet som text. Läget står först, och det är härlett."""
    nu = f.klocka()
    lage = f.lage
    sista = f.sista_framsteg()
    rader = ["LÄGE: %s" % lage,
             "uppdrag %s: %s" % (f.order_id, f.uppgift or SAKNAS)]
    if sista is None:
        rader.append("tid: t+%.1f s, ingen händelse ännu" % (nu - f.t0))
    else:
        rader.append("tid: t+%.1f s, senaste händelsen %s för %.1f s sedan"
                     % (nu - f.t0, sista.sort, nu - sista.t))
    skal = f.fallskal()
    if skal is not None:
        rader.append("skäl, ordagrant:")
        rader.append(skal)
    if lage == TYST:
        rader.append("ingenting har hänt på %.1f s. Systemet vet inte om "
                     "något arbetar."
                     % (nu - (sista.t if sista else f.t0)))
    rader.append("")
    rader.extend(_stegrader(f, lage, nu))
    rader.append("")
    rader.extend(_grindrader(f))
    rader.append("")
    rader.extend(_domrader(f))
    rader.append("")
    rader.extend(_handelserader(f))
    rader.append("")
    rader.extend(_ovissrader(f, lage))
    return "\n".join(rader)
