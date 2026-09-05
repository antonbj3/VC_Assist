# -*- coding: utf-8 -*-
"""Befintlig anläggning in: ett inspelat I/O-spår blir ett facit, med sin täckning.

Fas 18 i `docs/spec/70_faser.md`. Operatörens fråga bakom fasen är ett verkligt
driftproblem, ordagrant:

    "finns någon möjlighet att gå omvända riktningen -> maskinkod till
    structured text, i vårt simuleringsscenario, för tror det är ganska vanligt
    att originalkod och sånt tappas bort"

och vägen dit, också ordagrant:

    "Man lyssnar väl på kablarna typ, och lägger ihop signalerna?"

Det senare är vägen. Maskinkod går INTE tillbaka till ST — STruC++ kompilerar åt
ett håll och dekompilering är inte vägen (`70_faser.md`). Det som finns att
arbeta med är uppladdningsformatet eller **spåret**. Och ett spår har redan
bänkens facitform: `(insignaler vid t) -> (utsignaler vid t + fördröjning)`.

VAD DEN HÄR MODULEN GÖR, OCH VAD DEN VÄGRAR GÖRA
------------------------------------------------
Den härleder ett spårfacit ur en inspelning, och den vägrar påstå något om ett
läge inspelningen aldrig visade. Det är fasens viktigaste grind, och skälet är
mätt i `M-75`: en nödstoppskrets *ska* ligga sluten, så `EMG_OK` bytte värde
högst två gånger i var och en av bankens fyra spårfacituppgifter. Ett spår bär
alltså n = 1 eller n = 2 observationer av precis den signal som är farligast att
gissa om — och en anläggning som gått ett dygn i normalproduktion bär noll.

Ett facit som ändå dömer det läget är ett facit som ljuger. Därför bär varje
härlett påstående sitt **underlag** — hur många avläsningar, hur många avsnitt,
hur många sammanhängande episoder det vilar på — och varje påstående som
täckningen inte bär hamnar i `ej_pastatt` med sitt skäl i stället för i facit.

INVARIANTERNA ÄR FÖRBJUDNA TILLSTÅND
------------------------------------
En invariant "när A = a ska B = b" är samma sak som "tillståndet (A = a, B = ¬b)
förekommer aldrig". Härledningen letar därför efter **tvåsignalstillstånd som
inspelningen aldrig visade** och föreslår dem som förbud. Formuleringen gör
faran uppenbar i en mening: *påståendet är att ett tillstånd ingen sett är
omöjligt.* Det är sant för en förregling och falskt för en tillfällighet, och
spåret ensamt kan inte skilja dem åt. Fas 18:s tredje ärlighetskrav —
korrelation är inte orsak — är alltså inte en varning i prosa här utan ett tal:
hur många härledda förbud som en annan inspelning motbevisar.

Domen faller med **samma mekanik som fas 9**: `bank/domare.py` tar emot det
härledda facit som sitt `spar`-argument. Ingen ny domare skrivs. En andra domare
på samma storhet mäter domarna, inte lösningarna.

beskriver: bank/anlaggning.py, bank/domare.py, svc/vc_assist_svc/st/tolk.py
"""
from __future__ import annotations

import json
import os
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, ".."))
for _p in (_HAR, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from vc_assist_svc.st import tolk as _tolk  # noqa: E402

Tolkfel = _tolk.Tolkfel

# Hur nära en punktavläsning får ligga en insignaländring. Två scan är PLC:ns
# egen uppmätta svarstid, och samma marginal som bankens domare använder: under
# den skiljer ett facit inte längre på "logiken svarar ett scan senare" och
# "logiken gör fel".
MARGINAL_SCAN = 2               # Mätt i M-20.

# Så många skilda värden en signal måste ha antagit i inspelningen för att ett
# krav på den ska säga något alls. Talet är inte en tröskel utan definitionen av
# "rörde sig": en signal som stod still hela inspelningen säger ingenting om vad
# den styr, och ett krav på dess enda värde är sant oavsett vad logiken gör.
MINSTA_ANTAL_VARDEN = 2         # Mätt i M-75: tysta signaler, 0-2 av 20 per uppgift.


class Anlaggningsfel(Exception):
    """Inspelningen går inte att läsa. Kastar hellre än härleder ur en halv fil."""


# ------------------------------------------------------------------ hjälp

def _lika(a, b):
    """Samma likhetsbegrepp som domaren använder, och av samma skäl."""
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= 1e-9
    return a == b


def _nyckel(v):
    """Ett värde som ordboksnyckel, utan att True och 1 blir samma sak."""
    return json.dumps(v, sort_keys=True)


def _skriv(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    return repr(v)


def _villkorstext(villkor):
    return ", ".join("%s=%s" % (n, _skriv(v)) for n, v in sorted(villkor.items()))


# ------------------------------------------------------------------ spåret

class Avsnitt(object):
    """En sammanhängande inspelning: från spänningspåslag till avbrott.

    En anläggning som spelas in ger inte en enda oändlig rad. Den ger avsnitt:
    ett skift, en timme, tiden mellan två omstarter. Episodräkningen får aldrig
    spänna över ett avsnitt, för mellan två avsnitt vet ingen vad som hände.
    """

    def __init__(self, id, beskrivning, rader):
        self.id = id
        self.beskrivning = beskrivning
        self.rader = list(rader)

    def __len__(self):
        return len(self.rader)

    def __repr__(self):
        return "<Avsnitt %s, %d rader>" % (self.id, len(self.rader))


class Spar(object):
    """Ett inspelat I/O-spår. Kontaktdonen och ingenting annat.

    `signaler` är namn -> typ och `riktningar` namn -> "in"/"out", precis den
    signalkarta bankens uppgifter bär. Programmets inre — stegvariabeln,
    timrarnas ackumulatorer, de 16 till 66 villkorsgrenarna M-75 räknade — finns
    inte här, och kan inte finnas här. Det är hela poängen med fasen.
    """

    def __init__(self, harkomst, scan_ms, signaler, riktningar, avsnitt):
        if not str(harkomst or "").strip():
            raise Anlaggningsfel("ett spår utan härkomst är ingen inspelning")
        if not avsnitt:
            raise Anlaggningsfel("spåret har inga avsnitt")
        self.harkomst = harkomst
        self.scan_ms = float(scan_ms)
        self.signaler = dict(signaler)
        self.riktningar = dict(riktningar)
        self.avsnitt = list(avsnitt)

    # -- vad spåret består av ---------------------------------------------

    def rader(self):
        for a in self.avsnitt:
            for r in a.rader:
                yield r

    @property
    def antal_rader(self):
        return sum(len(a) for a in self.avsnitt)

    def ingangar(self):
        return sorted(n for n in self.signaler
                      if self.riktningar.get(n) == "in")

    def utgangar(self):
        return sorted(n for n in self.signaler
                      if self.riktningar.get(n) == "out")

    def boolsignaler(self):
        return sorted(n for n, t in self.signaler.items()
                      if str(t).lower() == "bool")

    def valj(self, ider):
        """Ett fönster ur inspelningen: bara de namngivna avsnitten.

        Vilket fönster som är normalproduktion är en MÄNNISKAS val, och det är
        precis vad en anläggning ger: du får den timme någon råkade spela in.
        Modulen gissar det inte åt någon; den som väljer får skriva ned varför.
        """
        vald = [a for a in self.avsnitt if a.id in set(ider)]
        saknas = set(ider) - set(a.id for a in vald)
        if saknas:
            raise Anlaggningsfel("spåret har inga avsnitt %s"
                                 % ", ".join(sorted(saknas)))
        return Spar(self.harkomst + " (fönster: %s)" % ", ".join(ider),
                    self.scan_ms, self.signaler, self.riktningar, vald)

    # -- serialisering ----------------------------------------------------

    def som_json(self):
        return {
            "harkomst": self.harkomst,
            "scan_ms": self.scan_ms,
            "signaler": self.signaler,
            "riktningar": self.riktningar,
            "avsnitt": [{"id": a.id, "beskrivning": a.beskrivning,
                         "rader": a.rader} for a in self.avsnitt],
        }

    @classmethod
    def fran_json(cls, d):
        return cls(d["harkomst"], d["scan_ms"], d["signaler"], d["riktningar"],
                   [Avsnitt(a["id"], a.get("beskrivning") or "", a["rader"])
                    for a in d["avsnitt"]])


def spela_in(st_text, signaler, riktningar, scan_ms, stimuli, harkomst):
    """Spela in ett spår ur en körande station.

    `stimuli` är (avsnitts-id, beskrivning, [(t_ms, {insignal: värde})]) — det
    omvärlden gjorde, inte det logiken svarade. Inspelningen läser BARA
    signalkartan; inget inre tillstånd följer med, för det gör det inte i en
    riktig anläggning heller.

    Ordningen speglar domarens egen loop scan för scan, så en punktavläsning i
    ett härlett facit hamnar på exakt den avläsning inspelningen gjorde. Skulle
    de två gå isär vore facit inte längre en observation utan en översättning.
    """
    avsnitt = []
    for aid, beskrivning, steg in stimuli:
        steg = sorted(steg, key=lambda x: float(x[0]))
        if not steg:
            raise Anlaggningsfel("avsnittet %s har inga stimuli" % aid)
        slut_ms = max(float(t) for t, _ in steg)
        motor = _tolk.Tolk(st_text, signaler, riktningar, float(scan_ms))
        rader = []
        i = 0
        while motor.tid_ms <= slut_ms + 1e-9:
            while i < len(steg) and float(steg[i][0]) <= motor.tid_ms + 1e-9:
                for namn, v in (steg[i][1] or {}).items():
                    motor.satt(namn, v)
                i += 1
            motor.scan()
            rader.append({"t_ms": round(motor.tid_ms - float(scan_ms), 6),
                          "varden": dict((n, motor.las(n)) for n in signaler)})
        avsnitt.append(Avsnitt(aid, beskrivning, rader))
    return Spar(harkomst, scan_ms, signaler, riktningar, avsnitt)


# --------------------------------------------------------------- täckningen

class Underlag(object):
    """Nämnaren bakom ett påstående. Ett tal utan nämnare är ingen mätning.

    `n_rader` är hur många avläsningar villkoret gällde i, `n_avsnitt` i hur
    många skilda inspelningar, och `n_episoder` hur många sammanhängande stråk.
    Episoden är den nämnare som betyder något för en tid: en timer som löst ut
    en gång är ett stickprov med n = 1 hur många scan den än stod utlöst.
    """

    def __init__(self, n_rader, n_avsnitt, n_episoder, av_rader):
        self.n_rader = n_rader
        self.n_avsnitt = n_avsnitt
        self.n_episoder = n_episoder
        self.av_rader = av_rader

    @property
    def sedd(self):
        return self.n_rader > 0

    @property
    def alltid(self):
        return self.n_rader == self.av_rader

    def som_json(self):
        return {"n_rader": self.n_rader, "n_avsnitt": self.n_avsnitt,
                "n_episoder": self.n_episoder, "av_rader": self.av_rader}

    def __repr__(self):
        return "<Underlag %d rader / %d episoder / %d avsnitt av %d rader>" % (
            self.n_rader, self.n_episoder, self.n_avsnitt, self.av_rader)


class Tackning(object):
    """Vad inspelningen faktiskt visade, per signal och per villkor."""

    def __init__(self, spar):
        self.spar = spar
        self.per_signal = {}
        for namn in spar.signaler:
            self.per_signal[namn] = {"varden": {}, "byten": 0}
        for a in spar.avsnitt:
            forra = None
            for r in a.rader:
                for namn in spar.signaler:
                    v = r["varden"].get(namn)
                    d = self.per_signal[namn]
                    d["varden"][_nyckel(v)] = d["varden"].get(_nyckel(v), 0) + 1
                    if forra is not None and not _lika(forra["varden"].get(namn), v):
                        d["byten"] += 1
                forra = r
        self.antal_rader = spar.antal_rader

    # -- per signal -------------------------------------------------------

    def varden(self, namn):
        return sorted(self.per_signal[namn]["varden"], key=str)

    def antal_varden(self, namn):
        return len(self.per_signal[namn]["varden"])

    def byten(self, namn):
        return self.per_signal[namn]["byten"]

    def observerad(self, namn, varde):
        """Hur många avläsningar signalen hade det värdet. Noll = aldrig sett."""
        if namn not in self.per_signal:
            return None
        return self.per_signal[namn]["varden"].get(_nyckel(varde), 0)

    def varierar(self, namn):
        return self.antal_varden(namn) >= MINSTA_ANTAL_VARDEN

    def tysta(self):
        """Signaler som aldrig rörde sig. M-75 mätte 0 till 2 per uppgift."""
        return sorted(n for n in self.per_signal if not self.varierar(n))

    # -- per villkor ------------------------------------------------------

    def underlag(self, villkor):
        """Nämnaren för ett sammansatt villkor {signal: värde}."""
        n_rader = 0
        n_avsnitt = 0
        n_episoder = 0
        for a in self.spar.avsnitt:
            sett_i_avsnittet = False
            forra = False
            for r in a.rader:
                nu = all(_lika(v, r["varden"].get(n)) for n, v in villkor.items())
                if nu:
                    n_rader += 1
                    sett_i_avsnittet = True
                    if not forra:
                        n_episoder += 1
                forra = nu
            if sett_i_avsnittet:
                n_avsnitt += 1
        return Underlag(n_rader, n_avsnitt, n_episoder, self.antal_rader)

    def som_json(self):
        return {
            "harkomst": self.spar.harkomst,
            "antal_rader": self.antal_rader,
            "antal_avsnitt": len(self.spar.avsnitt),
            "signaler": dict(
                (n, {"varden": self.varden(n), "byten": self.byten(n)})
                for n in sorted(self.per_signal)),
            "tysta": self.tysta(),
        }


# --------------------------------------------------------------- härledningen

def _forbjudna_par(spar, tackning):
    """Alla tvåsignalstillstånd inspelningen ALDRIG visade.

    Ett förbjudet par (A = a, B = b) är samma påstående som invarianten
    "när A = a ska B = ¬b" och som dess kontraposition "när B = b ska A = ¬a".
    Att leta efter förbjudna tillstånd i stället för efter implikationer gör tre
    saker på en gång: kontrapositionerna slutar räknas två gånger, påståendet
    blir läsbart som det det är — *ett tillstånd ingen sett antas omöjligt* — och
    täckningsfrågan blir en fråga med ett tal: hur ofta sågs var sida?
    """
    boolar = spar.boolsignaler()
    rader = list(spar.rader())
    par = []
    for i, A in enumerate(boolar):
        for B in boolar[i + 1:]:
            if spar.riktningar.get(A) != "out" and spar.riktningar.get(B) != "out":
                # Ingen styrlogik kan bryta ett förbud mellan två insignaler:
                # dem sätter omvärlden. Ett sådant påstående dömer anläggningens
                # omgivning, inte dess program.
                continue
            sedda = set((bool(r["varden"].get(A)), bool(r["varden"].get(B)))
                        for r in rader)
            for a in (True, False):
                for b in (True, False):
                    if (a, b) not in sedda:
                        par.append((A, a, B, b))
    return par


def _invariant_ur_par(spar, tackning, A, a, B, b):
    """Formulera förbudet (A=a, B=b) som en invariant domaren kan pröva.

    Riktningen väljs efter underlaget: den sida som setts flest gånger blir
    villkoret. Skälet är att en invariant bara prövas när villkoret gäller — en
    riktning med noll observationer prövas aldrig och mäter därför ingenting.
    Båda nämnarna följer med i `underlag`, så valet går att granska.
    """
    ua = tackning.underlag({A: a})
    ub = tackning.underlag({B: b})
    if ua.n_rader >= ub.n_rader:
        nar, narv, krav, kravv, u_nar, u_krav = A, a, B, not b, ua, ub
    else:
        nar, narv, krav, kravv, u_nar, u_krav = B, b, A, not a, ub, ua
    namn = "aldrig_%s%d_med_%s%d" % (A, int(a), B, int(b))
    return {
        "namn": namn,
        "sekvens": "*",
        "nar": {nar: narv},
        "kraver": {krav: kravv},
        "varfor": ("härlett ur spåret: tillståndet %s=%s och %s=%s förekom "
                   "aldrig i %d avläsningar"
                   % (A, _skriv(a), B, _skriv(b), tackning.antal_rader)),
        "underlag": {"villkor": u_nar.som_json(), "krav": u_krav.som_json(),
                     "forbjudet_tillstand": {A: a, B: b}},
    }


# Hur tätt ett härlett facit läser av utsignalerna.
#
#   "varje_rad"   varje avläsning marginalregeln tillåter blir ett punktkrav.
#   "andringar"   bara de avläsningar där utsignalvektorn ändrade sig.
#
# MÄTT i M-89, och det var inte en detalj: med "andringar" gick L-05:s
# modellösning igenom det härledda facit och föll på bankens handskrivna, på
# `nodstopp_kraver_kvittens@1800ms` — en robot som startade om efter nödstopp
# utan kvittens. Mellan två ändringar i inspelningen stod facit tyst, och där
# fick koden göra vad den ville. En inspelning ÄR varje rad, så tätheten
# "varje_rad" är den trogna, och den glesa finns kvar bara för att brieftexten
# ska gå att läsa.
TATHETER = ("varje_rad", "andringar")


def _sekvens_ur_avsnitt(spar, avsnitt, tathet="varje_rad"):
    """Ett avsnitt blir en sekvens: insignaländringarna och de utsignaler som
    faktiskt lästes av, aldrig något annat.

    Punktkraven läggs bara där marginalregeln tillåter det. Ligger en
    utsignaländring närmare än två scan efter en insignaländring skjuts
    avläsningen fram till första tillåtna rad — och det som skrivs ned är
    värdet DÄR, inte det man hade velat se. Ett facit som flyttar ett värde
    bakåt i tiden är inte längre en inspelning.
    """
    if tathet not in TATHETER:
        raise Anlaggningsfel("okänd täthet %r" % (tathet,))
    ingangar = [n for n in spar.ingangar()]
    utgangar = [n for n in spar.utgangar()]
    steg = []
    forra = None
    senaste_satt = None
    senast_pastadd = None
    marginal = MARGINAL_SCAN * spar.scan_ms
    for r in avsnitt.rader:
        t = float(r["t_ms"])
        satt = {}
        if forra is None:
            satt = dict((n, r["varden"][n]) for n in ingangar)
        else:
            for n in ingangar:
                if not _lika(forra["varden"].get(n), r["varden"].get(n)):
                    satt[n] = r["varden"][n]
        if satt:
            senaste_satt = t
        ut = dict((n, r["varden"][n]) for n in utgangar)
        krav = {}
        marginal_ok = senaste_satt is None or (t - senaste_satt) >= marginal - 1e-9
        andrat = (senast_pastadd is None or
                  any(not _lika(senast_pastadd.get(n), ut[n]) for n in utgangar))
        if marginal_ok and (tathet == "varje_rad" or andrat):
            krav = ut
            senast_pastadd = dict(ut)
        if satt or krav:
            steg.append({
                "t_ms": t,
                "satt": satt,
                "krav": krav,
                "varfor": ("avläst ur inspelningen %s vid t=%.0f ms"
                           % (avsnitt.id, t)) if krav else "",
            })
        forra = r
    if not any(s["krav"] for s in steg):
        raise Anlaggningsfel(
            "avsnittet %s gav inget punktkrav; utsignalerna ändrades aldrig "
            "utanför marginalen" % avsnitt.id)
    return {"id": avsnitt.id, "beskrivning": avsnitt.beskrivning, "steg": steg}


def _flanker_ur_avsnitt(spar, avsnitt):
    """Räkna flankerna precis som domaren räknar dem, i samma fönster."""
    ut = []
    utgangar = [n for n in spar.utgangar()
                if str(spar.signaler[n]).lower() == "bool"]
    if not avsnitt.rader:
        return ut
    fran = float(avsnitt.rader[0]["t_ms"])
    till = float(avsnitt.rader[-1]["t_ms"])
    for namn in utgangar:
        antal = 0
        forra = None
        for r in avsnitt.rader:
            v = bool(r["varden"].get(namn))
            if forra is not None and v and not forra:
                antal += 1
            forra = v
        ut.append({
            "namn": "%s_rise_%s" % (namn, avsnitt.id),
            "sekvens": avsnitt.id,
            "signal": namn,
            "typ": "RISE",
            "fran_ms": fran,
            "till_ms": till,
            "antal": antal,
            "varfor": ("räknat ur inspelningen %s: %d stigande flank(er) på "
                       "%d avläsningar" % (avsnitt.id, antal, len(avsnitt.rader))),
            "underlag": {"n_rader": len(avsnitt.rader), "n_avsnitt": 1,
                         "n_episoder": antal, "av_rader": spar.antal_rader},
        })
    return ut


class Harlett(object):
    """Ett facit härlett ur ett spår, plus allt spåret inte bar."""

    def __init__(self, spar, facit, tackning, ej_pastatt):
        self.spar = spar
        self.facit = facit
        self.tackning = tackning
        self.ej_pastatt = ej_pastatt

    def som_json(self):
        return {"facit": self.facit, "ej_pastatt": self.ej_pastatt}

    def __repr__(self):
        return ("<Harlett %d sekvenser, %d invarianter, %d flanker, "
                "%d ej påstådda>" % (len(self.facit["sekvenser"]),
                                     len(self.facit["invarianter"]),
                                     len(self.facit["flanker"]),
                                     len(self.ej_pastatt)))


def harled(spar, standard=None, tathet="varje_rad"):
    """Härled ett spårfacit ur inspelningen. Formen är den domaren äter.

    Facit får därutöver två fält bankens schema inte känner: `tackning` och
    `ej_pastatt`. Det är avsiktligt. Ett härlett facit är INTE en bankuppgift —
    en bankuppgift bär en referenslösning som bevisar att facit går att
    uppfylla, och en anläggning har ingen källkod att lämna ifrån sig. Det som
    bär uppfyllbarheten här är i stället inspelningen själv: varje påstående är
    en avläsning som redan har hänt.
    """
    tackning = Tackning(spar)
    sekvenser = [_sekvens_ur_avsnitt(spar, a, tathet) for a in spar.avsnitt]
    flanker = []
    for a in spar.avsnitt:
        flanker.extend(_flanker_ur_avsnitt(spar, a))

    invarianter = []
    ej_pastatt = []
    for A, a, B, b in _forbjudna_par(spar, tackning):
        inv = _invariant_ur_par(spar, tackning, A, a, B, b)
        villkor = inv["nar"]
        kravsignal = list(inv["kraver"])[0]
        u = tackning.underlag(villkor)
        if not u.sedd:
            ej_pastatt.append({
                "pastaende": inv["namn"],
                "nar": villkor, "kraver": inv["kraver"],
                "skal": "villkoret %s sågs aldrig i inspelningen"
                        % _villkorstext(villkor),
                "underlag": u.som_json()})
            continue
        if u.alltid:
            ej_pastatt.append({
                "pastaende": inv["namn"],
                "nar": villkor, "kraver": inv["kraver"],
                "skal": ("villkoret %s gällde i varje avläsning; invarianten "
                         "säger då ingenting om villkoret"
                         % _villkorstext(villkor)),
                "underlag": u.som_json()})
            continue
        if not tackning.varierar(kravsignal):
            ej_pastatt.append({
                "pastaende": inv["namn"],
                "nar": villkor, "kraver": inv["kraver"],
                "skal": ("kravsignalen %s stod still hela inspelningen (%d "
                         "värde); ett krav på dess enda värde är sant oavsett "
                         "vad logiken gör"
                         % (kravsignal, tackning.antal_varden(kravsignal))),
                "underlag": tackning.underlag({kravsignal:
                                               inv["kraver"][kravsignal]}).som_json()})
            continue
        invarianter.append(inv)

    facit = {
        "harledd": True,
        "tathet": tathet,
        "harkomst": spar.harkomst,
        "standard": standard or ("inspelat I/O-spår; ingen publicerad "
                                 "tillståndsmodell åberopas"),
        "scan_ms": spar.scan_ms,
        "sekvenser": sekvenser,
        "invarianter": invarianter,
        "flanker": flanker,
        "tackning": tackning.som_json(),
    }
    return Harlett(spar, facit, tackning, ej_pastatt)


# ------------------------------------------------------------------- grinden

# Grindens felkoder. Varje kod har en trasig fixtur i
# tests/enhet/test_anlaggning.py som fäller den, och ett kontrollfall som visar
# att ett täckt facit släpps igenom. En grind som avvisar allt ser lika bra ut
# som en som fångar rätt sak, om man bara räknar avvisningar.
T1_OTACKT_VILLKOR = "T1_OTACKT_VILLKOR"
T2_OKAND_SIGNAL = "T2_OKAND_SIGNAL"
T3_UTAN_UNDERLAG = "T3_UTAN_UNDERLAG"
T4_OTACKT_KRAV = "T4_OTACKT_KRAV"


class Tackningsbrist(object):
    """En namngiven täckningsöverträdelse. Namnet är stabilt, så en trasig
    fixtur kan peka ut exakt vilken brist den ska fällas på."""

    def __init__(self, kod, pastaende, text):
        self.kod = kod
        self.pastaende = pastaende
        self.text = text

    def __repr__(self):
        return "<Tackningsbrist %s på %s>" % (self.kod, self.pastaende)


def granska(facit, spar_eller_tackning, kraver_underlag=None):
    """Fäller varje påstående inspelningen inte bär. Lämnar en lista brister.

    Detta är fas 18:s grind, och den formuleras i en mening: **täckning innan
    påstående.** Ett stillastående nödstopp som aldrig aktiverats under
    inspelningen säger ingenting om vad som händer när det aktiveras, och ett
    facit som ändå dömer det läget är ett facit som ljuger.

    Grinden dömer vilket spårfacit som helst mot vilken inspelning som helst —
    också ett handskrivet bankfacit. Det är avsiktligt: talet "hur många av
    bankens egna påståenden bär den här inspelningen upp?" är fasens mått på
    vad en anläggning räcker till.

    `kraver_underlag` skiljer två sorters facit, och skillnaden är inte
    formalia. Ett HANDSKRIVET facit har sin härkomst i en publicerad standard —
    `IEC 60204-1` säger att en nödstoppskrets kräver manuell återställning, och
    det påståendet står upp utan en enda observation. Ett HÄRLETT facit har sin
    härkomst i en inspelning, och då är nämnaren allt det har. Kravet på
    `underlag` gäller därför bara det härledda, och `harled` stämplar det den
    lämnar ifrån sig. Utan skillnaden hade grinden fällt bankens egna
    invarianter för att de saknar ett tal de aldrig påstod sig ha.
    """
    tackning = (spar_eller_tackning if isinstance(spar_eller_tackning, Tackning)
                else Tackning(spar_eller_tackning))
    kanda = set(tackning.per_signal)
    brister = []
    if kraver_underlag is None:
        kraver_underlag = bool(facit.get("harledd"))

    if kraver_underlag and not facit.get("tackning"):
        brister.append(Tackningsbrist(
            T3_UTAN_UNDERLAG, "facit",
            "facit är härlett ur ett spår men bär ingen täckningsuppgift; ett "
            "facit som inte säger vilka lägen spåret visade är inte ett facit"))

    def _signalfinns(pastaende, namn):
        if namn not in kanda:
            brister.append(Tackningsbrist(
                T2_OKAND_SIGNAL, pastaende,
                "påståendet läser %s, som inte finns i inspelningen" % namn))
            return False
        return True

    for inv in facit.get("invarianter") or []:
        namn = inv.get("namn") or "?"
        ok = True
        for n in list(inv.get("nar") or {}) + list(inv.get("kraver") or {}):
            ok = _signalfinns(namn, n) and ok
        if not ok:
            continue
        if kraver_underlag and not inv.get("underlag"):
            brister.append(Tackningsbrist(
                T3_UTAN_UNDERLAG, namn,
                "invarianten bär ingen nämnare; ett härlett påstående utan "
                "underlag går inte att väga"))
        u = tackning.underlag(inv.get("nar") or {})
        if not u.sedd:
            brister.append(Tackningsbrist(
                T1_OTACKT_VILLKOR, namn,
                "villkoret %s förekom i 0 av %d avläsningar; spåret har aldrig "
                "visat det läget och kan därför inte säga vad som gäller där"
                % (_villkorstext(inv.get("nar") or {}), tackning.antal_rader)))
        for n, v in (inv.get("kraver") or {}).items():
            if tackning.observerad(n, v) == 0:
                brister.append(Tackningsbrist(
                    T4_OTACKT_KRAV, namn,
                    "kravet vill att %s ska vara %s, ett värde signalen aldrig "
                    "antog i inspelningen" % (n, _skriv(v))))

    for sekv in facit.get("sekvenser") or []:
        sid = sekv.get("id") or "?"
        for s in sekv.get("steg") or []:
            for n, v in (s.get("krav") or {}).items():
                pastaende = "%s@%sms:%s" % (sid, s.get("t_ms"), n)
                if not _signalfinns(pastaende, n):
                    continue
                if tackning.observerad(n, v) == 0:
                    brister.append(Tackningsbrist(
                        T4_OTACKT_KRAV, pastaende,
                        "punktkravet vill att %s ska vara %s, ett värde "
                        "signalen aldrig antog i inspelningen"
                        % (n, _skriv(v))))
            for n in (s.get("satt") or {}):
                _signalfinns("%s@%sms" % (sid, s.get("t_ms")), n)

    for f in facit.get("flanker") or []:
        namn = f.get("namn") or "?"
        if not _signalfinns(namn, f.get("signal")):
            continue
        if kraver_underlag and not f.get("underlag"):
            brister.append(Tackningsbrist(
                T3_UTAN_UNDERLAG, namn,
                "flankkravet bär ingen nämnare"))
        if int(f.get("antal") or 0) > 0:
            vantat = True if f.get("typ") == "RISE" else False
            if tackning.observerad(f.get("signal"), vantat) == 0:
                brister.append(Tackningsbrist(
                    T4_OTACKT_KRAV, namn,
                    "flankkravet räknar %d %s-flank(er) på %s, men signalen "
                    "antog aldrig värdet %s i inspelningen"
                    % (int(f["antal"]), f.get("typ"), f.get("signal"),
                       _skriv(vantat))))
    return brister


def motbevisade(facit, spar):
    """Vilka av facits invarianter som en ANNAN inspelning motbevisar.

    Det här är fas 18:s tredje ärlighetskrav som ett tal. Ett förbud härlett ur
    normalproduktion är ett påstående om att ett tillstånd ingen sett är
    omöjligt. Kör man samma påstående mot en inspelning som innehåller
    nödstoppet, tryckluftsbortfallet och tidsvakten faller de som bara var
    tillfälligheter — och de som står kvar var förreglingar.

    Lämnar (invariant, första motbevisande raden).
    """
    ut = []
    for inv in facit.get("invarianter") or []:
        for a in spar.avsnitt:
            traff = None
            for r in a.rader:
                if all(_lika(v, r["varden"].get(n))
                       for n, v in (inv.get("nar") or {}).items()) and \
                   not all(_lika(v, r["varden"].get(n))
                           for n, v in (inv.get("kraver") or {}).items()):
                    traff = (a.id, r["t_ms"])
                    break
            if traff:
                ut.append((inv, traff))
                break
    return ut
