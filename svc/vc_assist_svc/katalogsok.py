# -*- coding: utf-8 -*-
"""Sokskiktet over komponentindexet, format for en sprakmodell.

Operatorens krav, ordagrant: "Informationen maste vara lattillganglig for LLM."
Det ar ett krav pa FORMEN, och det ar skarpare an det later.

Indexet (`katalogindex.py`) bar 3201 komponenter och 4,3 MB. Ett korrekt index
som kostar 4,3 MB att lasa ar oanvandbart for en agent - den laser det inte, och
gissar i stallet, vilket ar precis vad indexet skulle hindra. Korrekt racker
alltsa inte. Det maste ocksa vara BILLIGT.

TRE REGLER SOM FORMEN FOLJER
----------------------------
1. En trafflista ar RADER, inte JSON. En rad per komponent, ett fast antal falt,
   och alltid "N traffar, visar M". Ett svar som inte sager hur mycket det inte
   visade ar ett svar som ser uttommande ut.

2. En bred fraga far ett SAMMANDRAG, inte en lista. "robotar" traffar 1736
   stycken; att radda upp dem ar att branna kontexten pa det agenten inte
   fragade efter. Svaret blir da fordelningen per tillverkare och en uppmaning
   att smalna av. Det ar samma doktrin som 25_kontextbudget.md:s trimning:
   ingen bortprioritering ar tyst.

3. Ett falt som datan inte bar sags SAKNAS. Aldrig noll, aldrig tomt, aldrig
   utelamnat. Ett utelamnat falt lases som "noll" av bade manniskor och
   modeller, och da har indexet ljugit tyst.

VAD DEN INTE GOR
----------------
Den tolkar inte parameternamn. Biblioteket bar 1806 unika namn utan gemensamt
schema (M-57), och en avbildning fran storhet till parameternamn hor till
databladslagret, inte hit. Det som star har ar sokningen och FORMEN pa svaret.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

# Sa manga traffar en lista visar innan svaret blir ett sammandrag i stallet.
# MATT i M-60: en rad ar 40-70 tecken, sa tio rader ar under 700 tecken - i
# storleksordningen ett par hundra tokens, vilket far plats i posten
# "verktygsresultat" (25_kontextbudget.md, post 8) utan att tranga ut nagot.
MAX_RADER = 10                  # Satt av M-60.

# Over sa manga traffar ar en lista meningslos oavsett tak: agenten har fragat
# for brett, och det ar den upplysningen den behover.
BRED_FRAGA = 40                 # Satt av M-60.

SAKNAS = "MISSING"

# Sa manga tecken maste sta kvar av BETECKNINGEN sedan ett ledande
# tillverkarnamn strukits, for att ledet ska fa strykas alls.
#
# MATT i M-161 over hela det installerade biblioteket: 3201 fragor pa formen
# "<FEL TILLVERKARE> <riktigt komponentnamn>" ska alla ge noll traffar. Utan
# sparren gav tre av dem traffar, och alla tre var komponenter vars NAMN ar en
# enda siffra - biblioteket bar atta sadana ("0" .. "7"). Med sparren ar det
# 3201 av 3201. Priset ar ocksa matt och det ar de atta: de gar inte att na med
# ett tillverkarled framfor sig. De gar att na pa sitt namn.
MIN_BETECKNING = 2              # Satt av M-161.


def normalisera(text: str) -> str:
    """Namnet utan skiljetecken och skiftlage. 'IRB 1200-5/0.9' -> irb1200509.

    MATT i M-161, bada hallen. NYTTAN: en beteckning skrivs pa manga satt, och
    3201 biblioteksnamn omstavade med `_`, med `-` och helt utan avskiljare
    hittas av den RAKA delstrangen i 612, 1403 respektive 508 fall - av den
    normaliserade i 3201 av 3201, utan att den riktiga komponenten en enda gang
    saknades bland traffarna (7 080 fragor). RISKEN: samma matning at andra
    hallet visar att 74 av 3201 sjalvfragor (2,31 %) far FLER traffar av
    normaliseringen - "C4" hittar da "EC-400". Darfor ar stegen en STEGE och
    inte en union: den normaliserade nivan kors bara nar den raka gav noll, och
    da ar breddningen per konstruktion noll.
    """
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


class Sokfel(Exception):
    pass


def _text(x) -> str:
    return "" if x is None else str(x)


def _positivt_tal(x) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
        return v if v > 0.0 else None
    except (TypeError, ValueError):
        return None


@dataclass
class Traff:
    namn: str
    tillverkare: str
    kategori: str
    sokvag: str
    granssnitt: int = 0
    familj: str = ""
    rackvidd_mm: Optional[float] = None
    nyttolast_kg: Optional[float] = None
    utfasad: bool = False
    parametrar: Dict[str, str] = field(default_factory=dict)

    def rad(self) -> str:
        """En rad, fasta falt, ingen JSON.

        Familjen star FORE kategorin, for den ar den sanna: kategorin kommer
        ur katalognamnet eller ur ett falt, familjen ur komponentens struktur.
        """
        return "%s | %s | %s | rackvidd %s | nyttolast %s%s" % (
            self.tillverkare or SAKNAS, self.namn,
            self.familj or self.kategori or SAKNAS,
            ("%.0f mm" % self.rackvidd_mm) if (self.rackvidd_mm is not None and self.rackvidd_mm > 0.0)
            else SAKNAS,
            ("%.0f kg" % self.nyttolast_kg) if (self.nyttolast_kg is not None and self.nyttolast_kg > 0.0)
            else SAKNAS,
            "  [UTFASAD]" if self.utfasad else "")

    def fullt(self, max_parametrar: int = 25) -> str:
        rader = ["namn: %s" % self.namn,
                 "tillverkare: %s" % (self.tillverkare or SAKNAS),
                 "kategori: %s" % (self.kategori or SAKNAS),
                 "granssnitt: %s" % (self.granssnitt if self.granssnitt else SAKNAS),
                 "fil: %s" % self.sokvag]
        if not self.parametrar:
            rader.append("parametrar: %s (indexet byggdes i grunt lage)" % SAKNAS)
            return "\n".join(rader)
        nycklar = sorted(self.parametrar)
        rader.append("parametrar (%d st):" % len(nycklar))
        for k in nycklar[:max_parametrar]:
            rader.append("  %s = %s" % (k, self.parametrar[k]))
        if len(nycklar) > max_parametrar:
            rader.append("  ... %d till, ej visade"
                         % (len(nycklar) - max_parametrar))
        return "\n".join(rader)


@dataclass
class Svar:
    """Ett sokresultat, med sin egen arlighet inbyggd."""

    totalt: int
    traffar: List[Traff]
    sammandrag: Optional[Dict[str, int]] = None
    fraga: str = ""
    # HUR namnet lastes, nar det inte lastes rakt av. None betyder att fragan
    # traffade som den skrevs. Ingen bortprioritering ar tyst
    # (25_kontextbudget.md), och det galler ocksa en del av fragan som
    # verktyget sjalvt valde att slappa.
    lasning: Optional[str] = None

    @property
    def visade(self) -> int:
        return len(self.traffar)

    def text(self) -> str:
        if self.totalt == 0:
            return "0 traffar for %s." % (self.fraga or "fragan")
        if self.sammandrag is not None:
            rader = ["%d traffar for %s - for manga for en lista."
                     % (self.totalt, self.fraga or "fragan"),
                     "Fordelning per tillverkare:"]
            for namn, n in sorted(self.sammandrag.items(),
                                  key=lambda p: (-p[1], p[0]))[:15]:
                rader.append("  %-24s %4d" % (namn or SAKNAS, n))
            ovriga = len(self.sammandrag) - 15
            if ovriga > 0:
                rader.append("  ... %d tillverkare till" % ovriga)
            rader.append("Smalna av med tillverkare, kategori eller ett "
                         "namnfragment.")
            return "\n".join(rader)
        rader = ["%d traffar, visar %d." % (self.totalt, self.visade)]
        if self.lasning:
            rader.append("last som: %s" % self.lasning)
        rader.extend(t.rad() for t in self.traffar)
        if self.visade < self.totalt:
            rader.append("... %d till, ej visade." % (self.totalt - self.visade))
        return "\n".join(rader)

    def tecken(self) -> int:
        return len(self.text())


class Katalog(object):
    """Indexet i minnet, med sokning.

    3201 poster ar litet. En linjar genomsokning tar millisekunder, och en
    databas skulle inte gora nagot billigare - den skulle bara flytta samma
    paase parametrar till en annan lagringsform. Skalet att INTE bygga en
    grafdatabas ar alltsa matt och inte principiellt.
    """

    def __init__(self, poster: Sequence[Traff], rot: str = "", djupt: bool = False):
        self.poster = list(poster)
        self.rot = rot
        self.djupt = bool(djupt)
        self._tillverkarnamn: Optional[List[str]] = None

    # ---- lasning -------------------------------------------------------

    @staticmethod
    def fran_index(index: Dict[str, object]) -> "Katalog":
        if not isinstance(index, dict) or "poster" not in index:
            raise Sokfel("this is not a catalog index")
        poster = [Traff(namn=_text(p.get("namn")),
                        tillverkare=_text(p.get("tillverkare")),
                        kategori=_text(p.get("kategori")),
                        sokvag=_text(p.get("sokvag")),
                        granssnitt=int(p.get("granssnitt") or 0),
                        familj=_text(p.get("familj")),
                        rackvidd_mm=_positivt_tal(p.get("rackvidd_mm")),
                        nyttolast_kg=_positivt_tal(p.get("nyttolast_kg")),
                        utfasad=bool(p.get("utfasad")),
                        parametrar=dict(p.get("parametrar") or {}))
                   for p in index["poster"]]
        return Katalog(poster, _text(index.get("rot")),
                       bool(index.get("djupt")))

    @staticmethod
    def las_fil(sokvag: str) -> "Katalog":
        if not os.path.exists(sokvag):
            raise Sokfel("no index at %s" % sokvag)
        with open(sokvag, "r", encoding="utf-8") as f:
            return Katalog.fran_index(json.load(f))

    # ---- sokningen -----------------------------------------------------

    def sok(self, fraga: str = "", tillverkare: str = "", kategori: str = "",
            har_parameter: str = "", familj: str = "",
            min_rackvidd_mm: Optional[float] = None,
            min_nyttolast_kg: Optional[float] = None,
            med_utfasade: bool = False,
            max_rader: int = MAX_RADER) -> Svar:
        """Filtrera och lamna ett svar som bar sin egen arlighet.

        `fraga` matchas mot namnet i en STEGE av lasningar, fran strangast
        till losast, och en losare niva kors bara nar den strangare gav NOLL
        traffar. Steg ett ar dagens beteende oforandrat: skiftlagesokanslig
        delstrang - en modell skriver "IRB 6700" nar filen heter
        "IRB 6700-150/3.20". Se `_namnstegen` for varfor det finns fler steg
        och vad var och en kostar.
        """
        beskrivning = self._beskriv_fraga(fraga, tillverkare, kategori,
                                          har_parameter, familj,
                                          min_rackvidd_mm, min_nyttolast_kg)
        traffar: List[Traff] = []
        lasning: Optional[str] = None
        for namnprov, tv_ur_fragan, hur in self._namnstegen(fraga):
            traffar = self._filtrera(namnprov, tillverkare or tv_ur_fragan,
                                     kategori, har_parameter, familj,
                                     min_rackvidd_mm, min_nyttolast_kg,
                                     med_utfasade)
            if traffar:
                lasning = hur
                break
        if len(traffar) > BRED_FRAGA:
            fordelning: Dict[str, int] = {}
            for t in traffar:
                fordelning[t.tillverkare] = fordelning.get(t.tillverkare, 0) + 1
            return Svar(len(traffar), [], fordelning, beskrivning, lasning)
        return Svar(len(traffar), traffar[:max(int(max_rader), 1)],
                    None, beskrivning, lasning)

    # ---- namnstegen ----------------------------------------------------

    def _tillverkarnamnen(self) -> List[str]:
        """Tillverkarnamnen ur INDEXET, langst forst.

        Langst forst darfor att "Bosch Rexroth" ska kanna igen sig fore
        "Bosch" om bada finns. Listan ar indexets egen och aldrig en
        handskriven - ett handskrivet register over tillverkarnamn hade varit
        ett pastaende utan facitkalla.
        """
        if self._tillverkarnamn is None:
            self._tillverkarnamn = sorted(
                {t.tillverkare.lower() for t in self.poster if t.tillverkare},
                key=len, reverse=True)
        return self._tillverkarnamn

    def _dela_tillverkarled(self, fraga: str) -> Tuple[str, str]:
        """(tillverkare, resten) nar fragan INLEDS med ett tillverkarnamn."""
        f = (fraga or "").strip()
        for t in self._tillverkarnamnen():
            if f.lower().startswith(t + " "):
                # Fragans EGEN stavning tillbaka, inte indexets. Svaret ska
                # eka det anroparen skrev ("FANUC"), medan filtret jamfor
                # skiftlagesokansligt mot indexets ("Fanuc").
                return f[:len(t)], f[len(t) + 1:].strip()
        return "", f

    def _namnstegen(self, fraga: str):
        """Lasningarna av `fraga`, fran strangast till losast.

        Varje steg ar (namnprov, tillverkare_ur_fragan, hur_det_lastes).

        VARFOR STEGEN FINNS, matt i M-119 och delad i M-161: banken fragar
        efter "ABB IRB 1200-5/0.9", biblioteket bar "IRB 1200-5/0.9", och en
        rak delstrangssokning traffade darfor NOLL av 75 biblioteksfragor.
        Femton av de 75 ar riktiga modellbeteckningar; de ovriga 60 ar bankens
        egna svenska funktionsbeskrivningar, och dem loser inget namnsteg -
        se M-161 avsnitt 6, som mater varfor: de tva vokabularen beskriver
        inte ens samma storheter.

        VARFOR DET AR EN STEGE OCH INTE EN UNION: samma matning visar att en
        skiljeteckenslos matchning breddar 2,31 % av alla sjalvfragor ("C4"
        hittar "EC-400"). Kors den bara nar den raka gav noll ar breddningen
        per konstruktion noll, och nyttan - 3201 av 3201 omstavade beteckningar
        - ar kvar.

        VAD STEGEN INTE GOR: de gissar aldrig. Alla fyra proven i
        tests/enhet/test_katalogsok_normalisering.py som ska ge SAKNAS ger det
        efterat ocksa. `ABB IRB 660-180/3.15` far inte bli `IRB 660`, och
        `ABB IRB 360-1/1130 FlexPicker` far inte bli `IRB 360-3/1130`.
        """
        f = (fraga or "").strip()
        if not f:
            return [(None, "", None)]

        # 1. Rak delstrang. Dagens beteende, oforandrat.
        steg = [(lambda namn, x=f.lower(): x in namn.lower(), "", None)]

        # 2. Samma sak utan skiljetecken, mellanslag och skiftlage.
        fn = normalisera(f)
        if fn:
            steg.append((lambda namn, x=fn: x in normalisera(namn), "",
                         "skiljetecken och mellanslag utelamnade"))

        tv, kvar = self._dela_tillverkarled(f)
        if not tv or len(normalisera(kvar)) < MIN_BETECKNING:
            return steg

        # 3. Tillverkarledet last som TILLVERKARE och inte som en del av
        #    namnet. Det ar ett filter och inte ett bortstruket ord - en
        #    beteckning som bars av en ANNAN tillverkare traffar inte.
        #
        #    Tva rungor och inte en, av samma skal som steg 1 kommer fore
        #    steg 2: den RAKA delstrangen inom tillverkaren provas fore den
        #    skiljeteckenslosa. MATT i M-161 att det behovs: "FANUC C4" har
        #    ingen rak traff bland Fanuc, men "c4" ligger inne i
        #    normaliserade "m710ic45m". Ordningen gor att den losare rungan
        #    bara nas av det den strangare inte kunde ta.
        steg.append((lambda namn, x=kvar.lower(): x in namn.lower(), tv,
                     "\"%s\" last som tillverkare, \"%s\" som namn"
                     % (tv, kvar)))
        kn = normalisera(kvar)
        steg.append((lambda namn, x=kn: x in normalisera(namn), tv,
                     "\"%s\" last som tillverkare, \"%s\" som namn "
                     "(skiljetecken utelamnade)" % (tv, kvar)))

        # 4. Efterstallda RENA BOKSTAVSORD slappta, ett i taget, sa lange
        #    minst ett sifferbarande ord star kvar. Banken skriver
        #    "ABB IRB 910SC-3/0.55 SCARA"; biblioteket skriver ingen SCARA.
        #    Kravet pa ett sifferbarande ord kvar ar det som gor att
        #    "ABB IRB 360-1/1130 FlexPicker" stannar pa "IRB 360-1/1130" och
        #    darmed pa NOLL traffar i stallet for att glida till en granne.
        #
        #    TVA LATTNADER FAR INTE STAPLAS. Rungan matchar RAKT och aldrig
        #    normaliserat: att kasta en del av fragan ar redan en lattnad, och
        #    att samtidigt strunta i skiljetecknen gor stubben till nagot annat
        #    an en beteckning. MATT: den skalade fixturen fallde precis det.
        #    "INOVANCE TS 5 - Rotate Unit" tappade bada orden, stubben blev
        #    "ts5", och den ligger inne i normaliserade "IR-TS5-55Z15S-INT" -
        #    en traff pa en komponent som inte har med fragan att gora. Rakt
        #    matchar "ts 5 -" ingenting, och "IRB 910SC-3/0.55" matchar sig
        #    sjalv, sa den enda vinsten star kvar.
        delar = kvar.split()
        while len(delar) > 1 and delar[-1].isalpha():
            delar = delar[:-1]
            if not any(any(c.isdigit() for c in d) for d in delar):
                break
            stubbe = " ".join(delar)
            if len(normalisera(stubbe)) < MIN_BETECKNING:
                break
            slappt = " ".join(kvar.split()[len(delar):])
            steg.append((lambda namn, x=stubbe.lower(): x in namn.lower(), tv,
                         "\"%s\" last som tillverkare; \"%s\" slapptes ur "
                         "namnet" % (tv, slappt)))
        return steg

    def _filtrera(self, namnprov, tillverkare, kategori, har_parameter,
                  familj="", min_rackvidd=None, min_nyttolast=None,
                  med_utfasade=False) -> List[Traff]:
        """`namnprov` ar ett predikat pa NAMNET, eller None nar fragan var tom.

        Att det ar ett predikat och inte en strang ar hela skalet till att
        stegen i `_namnstegen` kan aterbruka samma filtrering: de ovriga
        filtren ska galla identiskt pa varje niva.
        """
        tv = (tillverkare or "").strip().lower()
        kt = (kategori or "").strip().lower()
        hp = (har_parameter or "").strip().lower()
        fm = (familj or "").strip().lower()
        ut = []
        for t in self.poster:
            if fm and fm != t.familj.lower():
                continue
            # En komponent utan angiven rackvidd har inte rackvidden noll. Den
            # slas darfor bort ur ett rackviddsfilter i stallet for att
            # jamforas mot None - samma regel som bankens katalogverktyg.
            if min_rackvidd is not None:
                if t.rackvidd_mm is None or t.rackvidd_mm < min_rackvidd:
                    continue
            if min_nyttolast is not None:
                if t.nyttolast_kg is None or t.nyttolast_kg < min_nyttolast:
                    continue
            if t.utfasad and not med_utfasade:
                continue
            if namnprov is not None and not namnprov(t.namn):
                continue
            if tv and tv != t.tillverkare.lower():
                continue
            if kt and kt != t.kategori.lower():
                continue
            if hp and not any(hp in k.lower() for k in t.parametrar):
                continue
            ut.append(t)
        # Kortast namn forst: "IRB 120" fore "IRB 120-3/0.6 LID". En modell som
        # sokte pa ett kort namn menade oftast grundmodellen.
        ut.sort(key=lambda t: (len(t.namn), t.tillverkare, t.namn))
        return ut

    @staticmethod
    def _beskriv_fraga(fraga, tillverkare, kategori, har_parameter,
                       familj="", min_rackvidd=None, min_nyttolast=None) -> str:
        delar = []
        if min_rackvidd is not None:
            delar.append("rackvidd >= %.0f mm" % min_rackvidd)
        if min_nyttolast is not None:
            delar.append("nyttolast >= %.0f kg" % min_nyttolast)
        if familj:
            delar.append("familj = %s" % familj)
        if fraga:
            delar.append('namn ~ "%s"' % fraga)
        if tillverkare:
            delar.append("tillverkare = %s" % tillverkare)
        if kategori:
            delar.append("kategori = %s" % kategori)
        if har_parameter:
            delar.append('bar parameter ~ "%s"' % har_parameter)
        return " och ".join(delar) if delar else "hela katalogen"

    # ---- oversikter ----------------------------------------------------

    def tillverkare(self) -> Dict[str, int]:
        ut: Dict[str, int] = {}
        for t in self.poster:
            ut[t.tillverkare] = ut.get(t.tillverkare, 0) + 1
        return ut

    def familjer(self) -> Dict[str, int]:
        """Antal per familj, ur strukturen. Tom nyckel = ingen markor fanns."""
        ut: Dict[str, int] = {}
        for t in self.poster:
            ut[t.familj] = ut.get(t.familj, 0) + 1
        return ut

    def kategorier(self) -> Dict[str, int]:
        ut: Dict[str, int] = {}
        for t in self.poster:
            ut[t.kategori] = ut.get(t.kategori, 0) + 1
        return ut

    def oversikt(self, max_rader: int = 12) -> str:
        """Det forsta en agent bor se: vad finns det HAR, i stora drag."""
        k = self.kategorier()
        tv = self.tillverkare()
        fm = self.familjer()
        rader = ["%d komponenter, %d tillverkare, %d kategorier."
                 % (len(self.poster), len(tv), len(k)),
                 "Indexet ar %s." % ("djupt (parametrar och familj ingar)"
                                     if self.djupt
                                     else "grunt (kategori kommer fran "
                                          "katalognamnet och familjen saknas "
                                          "helt, se M-58 och M-69)")]
        if self.djupt:
            rader.append("Familj ur STRUKTUREN (det sanna mattet, M-69):")
            for namn, n in sorted(fm.items(), key=lambda p: (-p[1], p[0])):
                rader.append("  %-32s %5d" % (namn or "(ingen markor)", n))
        rader.append("Storsta kategorierna (ur katalognamn eller falt - INTE "
                     "samma sak som familj):")
        for namn, n in sorted(k.items(), key=lambda p: (-p[1], p[0]))[:max_rader]:
            rader.append("  %-32s %5d" % (namn or SAKNAS, n))
        return "\n".join(rader)

    def med_namn(self, namn: str) -> Optional[Traff]:
        n = (namn or "").strip().lower()
        for t in self.poster:
            if t.namn.lower() == n:
                return t
        return None
