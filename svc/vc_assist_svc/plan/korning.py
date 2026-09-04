# -*- coding: utf-8 -*-
"""Koraren: kor planens steg i ordning och for protokoll.

Tre krav ur uppgiften styr formen:

1. PROTOKOLL. Vad som kordes, vad som HOPPADES OVER och varfor, och vad som
   FOLL. Ett steg utan post i protokollet finns inte; ett hoppat steg utan
   skal ar en tyst nedgradering.
2. ATERUPPTAGNING. En avbruten plan ska kunna koras vidare utan att kora om
   det som redan lyckats. Regeln ar smal med flit: BARA steg med status
   "kord" bars over. Ett hoppat, fallet eller koat steg provas igen, for dess
   forutsattningar kan ha andrats mellan korningarna - och att bara over ett
   utfall som inte var en framgang vore att bara over en gissning.
3. TYST FEL FINNS INTE. Ett verktygsfel blir en post med skal, aldrig ett
   undantag som river korningen (S10). Bara fel som INTE ar verktygets -
   programmeringsfel har - far rasa.

KORNINGEN AR SEKVENTIELL. Planen kan deklarera parallellgrupper, men bryggan
kor en exec per bildruta och far aldrig roras fran en bakgrundstrad (I13), sa
det finns ingenting att kora samtidigt PA. Deklarationen ar ett matt pa planen
(graf.bredd()), och den dag en samtidig utforare finns ar den redan provad.

SKRIVANDE STEG GAR TILL KON. effect=write -> exec_queue ags av utforaren
(I12). Koraren valjer inte lage; den moter kon som ett faktum: en koad post ar
inte klar, och utan godkannande stannar planen dar - med ett protokoll som
sager precis vilket qid som vantar. Det ar ratt beteende, inte en brist:
godkannandet ar operatorens.
"""
from __future__ import annotations

from ..klient import BryggFel
from ..verktyg import Verktygsfel
from .fel import Korningsfel
from .predikat import Korlage
from .steg import BINDNINGSREGLER, Bindning

# Statusarna en post kan ha. Samma lista som predikat.STATUSAR, som ar den
# lista ett forvillkor far fraga om.
KORD = "kord"
HOPPAD = "hoppad"
FALLEN = "fallen"
KOAD = "koad"
EJ_UTFORD = "ej_utford"

PROTOKOLLVERSION = 1   # formatversion, ingen troskel: forsta formen av ett protokoll


def godkann_aldrig(qid, verktyg, beskrivning):
    """Standardsvaret pa en kopost: nej.

    Godkannandet ar operatorens (I12). En korare som godkande sig sjalv hade
    gjort kon till en formalitet, vilket ar precis vad den doda kon i
    kallprojektet var.
    """
    return False


class Post(object):
    """En rad i protokollet: ett steg, ett utfall och ett skal."""

    __slots__ = ("steg", "status", "skal", "resultat", "verktyg", "qid")

    def __init__(self, steg, status, skal, resultat=None, verktyg=None,
                 qid=None):
        self.steg = steg
        self.status = status
        self.skal = skal
        self.resultat = resultat
        self.verktyg = verktyg
        self.qid = qid

    def __repr__(self):
        return "Post(%s, %s)" % (self.steg, self.status)

    def till_json(self):
        return {"steg": self.steg, "status": self.status, "skal": self.skal,
                "resultat": self.resultat, "verktyg": self.verktyg,
                "qid": self.qid}

    @classmethod
    def fran_json(cls, data):
        vantade = ("steg", "status", "skal", "resultat", "verktyg", "qid")
        if not isinstance(data, dict) or set(data) != set(vantade):
            raise Korningsfel("en protokollpost ska ha precis nycklarna %s"
                              % ", ".join(sorted(vantade)))
        return cls(data["steg"], data["status"], data["skal"],
                   data["resultat"], data["verktyg"], data["qid"])


class Protokoll(object):
    """Korningens egen berattelse. Serialiserbar, sa den kan aterupptas."""

    __slots__ = ("plan_id", "poster")

    def __init__(self, plan_id, poster=()):
        self.plan_id = plan_id
        self.poster = list(poster)

    def __len__(self):
        return len(self.poster)

    def __iter__(self):
        return iter(self.poster)

    def __repr__(self):
        r = self.rakning()
        return "Protokoll(%s, %s)" % (
            self.plan_id, ", ".join("%s=%d" % (k, v) for k, v in sorted(r.items())
                                    if v))

    def post(self, steg_id):
        for p in self.poster:
            if p.steg == steg_id:
                return p
        return None

    def status(self, steg_id):
        p = self.post(steg_id)
        return p.status if p else None

    def rakning(self):
        ut = {KORD: 0, HOPPAD: 0, FALLEN: 0, KOAD: 0, EJ_UTFORD: 0}
        for p in self.poster:
            ut[p.status] += 1
        return ut

    def fallna(self):
        return [p for p in self.poster if p.status == FALLEN]

    def hoppade(self):
        return [p for p in self.poster if p.status == HOPPAD]

    def koade(self):
        return [p for p in self.poster if p.status == KOAD]

    def verifieringspost(self, plan):
        for steg in plan.ogonkontroller():
            p = self.post(steg.id)
            if p is not None:
                return p
        return None

    def klar(self, plan):
        """Ar planen fardigkord? Fail-closed: allt utom idel 'kord' ar nej."""
        for steg in plan.graf:
            p = self.post(steg.id)
            if p is None:
                return False, "steget %s har ingen post" % steg.id
            if p.status == HOPPAD:
                continue
            if p.status != KORD:
                return False, "steget %s: %s (%s)" % (steg.id, p.status, p.skal)
        return True, "%d steg kordes, %d hoppades over" % (
            self.rakning()[KORD], self.rakning()[HOPPAD])

    def till_json(self):
        return {"v": PROTOKOLLVERSION, "plan_id": self.plan_id,
                "poster": [p.till_json() for p in self.poster]}

    @classmethod
    def fran_json(cls, data):
        if not isinstance(data, dict) or set(data) != {"v", "plan_id", "poster"}:
            raise Korningsfel("ett protokoll ska ha precis v, plan_id och poster")
        if data["v"] != PROTOKOLLVERSION:
            raise Korningsfel("protokollet ar version %r, lasaren kan %d"
                              % (data["v"], PROTOKOLLVERSION))
        return cls(data["plan_id"], [Post.fran_json(p) for p in data["poster"]])


class Korare(object):
    """Kor en plan. Kanner utforaren, aldrig bryggan direkt."""

    def __init__(self, utforare, godkannare=None):
        self.utforare = utforare
        self.godkannare = godkannare or godkann_aldrig

    def __repr__(self):
        return "Korare(%s)" % type(self.utforare).__name__

    # -- korningen --------------------------------------------------------

    def kor(self, plan, fakta=None, tidigare=None):
        """Kor planen och lamnar protokollet. Kastar aldrig pa ett stegfel."""
        lage = Korlage(fakta=fakta)
        poster = []
        klara = self._aterupptagna(plan, tidigare, lage, poster)

        for steg_id in plan.ordning():
            if steg_id in klara:
                continue
            steg = plan.graf.steg(steg_id)
            post = self._kor_steg(plan, steg, lage)
            poster.append(post)
            lage.statusar[steg.id] = post.status
            if post.resultat is not None:
                lage.resultat[steg.id] = post.resultat
        return Protokoll(plan.id, poster)

    def _aterupptagna(self, plan, tidigare, lage, poster):
        if tidigare is None:
            return set()
        if tidigare.plan_id != plan.id:
            raise Korningsfel(
                "protokollet horde till planen %r, inte %r; ett protokoll fran "
                "en annan plan sager ingenting om den har"
                % (tidigare.plan_id, plan.id))
        klara = set()
        for steg_id in plan.ordning():
            gammal = tidigare.post(steg_id)
            if gammal is None or gammal.status != KORD:
                # Bara en lyckad post bars over. Ett hoppat eller fallet steg
                # provas igen: dess forutsattningar kan ha andrats.
                continue
            klara.add(steg_id)
            lage.statusar[steg_id] = KORD
            if gammal.resultat is not None:
                lage.resultat[steg_id] = gammal.resultat
                bindningar = gammal.resultat.get("bindningar") \
                    if isinstance(gammal.resultat, dict) else None
                if isinstance(bindningar, dict):
                    lage.bindningar.update(bindningar)
            poster.append(Post(steg_id, KORD,
                               "aterupptagen: %s" % gammal.skal,
                               gammal.resultat, gammal.verktyg, gammal.qid))
        return klara

    def _kor_steg(self, plan, steg, lage):
        blockerad = self._blockerad(plan, steg, lage)
        if blockerad:
            return Post(steg.id, EJ_UTFORD, blockerad, verktyg=steg.verktyg)

        if steg.alternativ_grupp:
            for annan in plan.graf:
                if (annan.id != steg.id
                        and annan.alternativ_grupp == steg.alternativ_grupp
                        and lage.statusar.get(annan.id) == KORD):
                    return Post(steg.id, HOPPAD,
                                "alternativet %s lyckades redan" % annan.id,
                                verktyg=steg.verktyg)

        if steg.forvillkor is not None:
            holl, skal = steg.forvillkor.prova(lage)
            if not holl:
                return Post(steg.id, HOPPAD, "forvillkoret holl inte: %s" % skal,
                            verktyg=steg.verktyg)

        if steg.sort == "kontroll":
            return self._kor_kontroll(plan, steg, lage)
        return self._kor_verktyg(steg, lage)

    def _blockerad(self, plan, steg, lage):
        """Skalet steget inte gar att kora, eller None.

        Ett vanligt beroende maste vara KORD. Aven ett HOPPAT beroende
        blockerar: dess svar finns inte, och ett steg som laser ett svar som
        inte finns far inte koras.

        Beror steget pa flera steg i SAMMA alternativgrupp racker det att ETT
        av dem lyckades - det ar just vad ett alternativ betyder. Utan den
        regeln gick det inte att bero pa ett alternativ alls, eftersom det
        forlorande alternativet alltid ar hoppat.
        """
        grupper = {}
        for beroende in steg.beroenden:
            grupp = None
            if beroende in plan.graf:
                grupp = plan.graf.steg(beroende).alternativ_grupp
            if grupp and grupp != steg.alternativ_grupp:
                grupper.setdefault(grupp, []).append(beroende)
                continue
            status = lage.statusar.get(beroende)
            if status is None:
                return "beroendet %s har inget utfall" % beroende
            if status != KORD:
                return "beroendet %s ar %s" % (beroende, status)
        for grupp, medlemmar in sorted(grupper.items()):
            if not any(lage.statusar.get(m) == KORD for m in medlemmar):
                return ("inget alternativ i gruppen %s lyckades (%s)"
                        % (grupp, ", ".join(
                            "%s=%s" % (m, lage.statusar.get(m, "utan utfall"))
                            for m in sorted(medlemmar))))
        return None

    # -- kontrollstegen ---------------------------------------------------

    def _kor_kontroll(self, plan, steg, lage):
        kontroll = steg.kontroll
        if kontroll.sort == "villkor":
            holl, skal = kontroll.villkor.prova(lage)
            return Post(steg.id, KORD if holl else FALLEN, skal,
                        {"holl": holl, "skal": skal})
        if kontroll.sort == "bindning":
            regel = BINDNINGSREGLER[kontroll.regel]
            kallsvar = [lage.resultat.get(k) for k in kontroll.kallor]
            bindningar, skal = regel(kallsvar, kontroll.ger)
            if bindningar is None:
                return Post(steg.id, FALLEN,
                            "regeln %s kunde inte valja: %s"
                            % (kontroll.regel, skal),
                            {"bindningar": {}, "skal": skal})
            lage.bindningar.update(bindningar)
            return Post(steg.id, KORD, skal,
                        {"bindningar": dict(bindningar), "skal": skal})

        krav = plan.verifiering
        if krav is None or not krav.uttalad():
            skal = ("planen bar inget verifieringskrav; en plan utan bevis ar "
                    "en kandidat")
            return Post(steg.id, FALLEN, skal,
                        {"uppfyllt": False, "dom": None, "skal": skal})
        text = lage.fakta.get(kontroll.fakta_nyckel)
        dom = krav.doma(text)
        return Post(steg.id, KORD if dom.uppfyllt else FALLEN, dom.text(),
                    {"uppfyllt": dom.uppfyllt, "dom": dom.observerad_dom,
                     "skal": dom.text()})

    # -- verktygsstegen ---------------------------------------------------

    def _kor_verktyg(self, steg, lage):
        argument = {}
        for namn, varde in steg.argument.items():
            if isinstance(varde, Bindning):
                finns, last = varde.los(lage)
                if not finns:
                    return Post(steg.id, FALLEN,
                                "bindningen %s gick inte att losa ur %s"
                                % (namn, varde.fran_steg), verktyg=steg.verktyg)
                argument[namn] = last
            else:
                argument[namn] = varde
        try:
            resultat = self.utforare.utfor(steg.verktyg, argument)
        except (Verktygsfel, BryggFel, OSError) as fel:
            # Verktygslagrets och bryggans egna fel ar UTFALL, inte krascher:
            # de hor hemma i protokollet dar de gar att lasa. Allt annat far
            # rasa - ett fel i planeringslagret sjalvt ska synas som ett fel.
            return Post(steg.id, FALLEN, "%s: %s" % (type(fel).__name__, fel),
                        verktyg=steg.verktyg)

        if resultat.koad:
            if not self.godkannare(resultat.qid, steg.verktyg,
                                   "%s(%s)" % (steg.verktyg, argument)):
                return Post(steg.id, KOAD,
                            "skrivande steg lagt i godkannandekon som %s; "
                            "godkannandet ar operatorens (I12)" % resultat.qid,
                            verktyg=steg.verktyg, qid=resultat.qid)
            try:
                resultat = self.utforare.godkann(resultat.qid)
            except (Verktygsfel, BryggFel, OSError) as fel:
                return Post(steg.id, FALLEN,
                            "godkand men foll i kon: %s: %s"
                            % (type(fel).__name__, fel),
                            verktyg=steg.verktyg, qid=resultat.qid)
            return Post(steg.id, KORD, "kordes ur kon efter godkannande",
                        resultat.resultat, steg.verktyg, resultat.qid)
        return Post(steg.id, KORD, "kordes direkt", resultat.resultat,
                    steg.verktyg)
