# -*- coding: utf-8 -*-
"""Verktygsloopen: turen, taken och stoppreglerna.

Loopen ar det enda stalle dar mekanismerna moter varandra, och ordningen dem
emellan ar ett beslut, inte en slump.

FORE KORNING provas varje anrop av forgranskning.Forgranskare och sedan av
turordning.Turlage. Foll det, far modellen avslaget i klartext och far forsoka
igen - avslaget ar en RUNDA, och det raknas som ett misslyckande i taken nedan.

Turordningsgrindarna domer SIST av grindarna fore korning, och skalet star i
turordning.py: de fragar om ett anrop som redan ar giltigt i sig, och de
behover den genererade koden for att kunna fraga.

EFTER MODELLENS SLUTSVAR provas svaret i den har ordningen, och ordningen ar
82_felklasser.md sorteringsregel 1 ("forsta grinden som faller bestammer
klassen") tillampad pa svaret i stallet for pa anropet:

  1 sakerhet och kodblock   forgranskning.granska_svarstext. Ovillkorlig, och
                            ett kodblock i ett svar ar det operatoren
                            klistrar in - alltsa forbi bade kon och
                            skrivgrinden.
  2 arlighet                honesty-rewrite. F12 ar overordnad i
                            felklasstabellen: en ohederlig gron ar farligare
                            an ett rott.
  3 redovisning             en klippt lista redovisad som en helhet, och ett
                            simuleringsvarv beskrivet som ett bevis. Samma
                            klass som arligheten men en storleksordning
                            mildare: underlaget ar akta och slutsatsen for
                            stor, sa den domer efter arligheten.
  4 ogat                    en dom modellen inte far falla.
  5 verifiering             verify-contract, finmaskigast och sist.

TAKEN, och varifran talen kommer:

  MAX_RUNDOR = 10           arvt (20_arv.md: "10 rundor")
  MAX_RAKA_MISSLYCKANDEN=6  arvt (20_arv.md: "stopp efter 6 raka
                            misslyckanden")
  MAX_LIKA_ANROP = 2        VART, och det ar det enda talet har som inte ar
                            arvt. Ett tredje IDENTISKT anrop (samma verktyg,
                            samma argument) efter tva som fallit kan inte ge
                            ett annat svar: forgranskningens avslag ar en ren
                            funktion av anropet, och tva korningar mot samma
                            oforandrade tillstand ger samma fel. Tva forsok
                            tillats darfor att ett verktygsfel KAN vara
                            overgaende (en kopost som hann godkannas emellan).
  MAX_OMSKRIVNINGAR = 2     VART. Efter tva omskrivningskrav pa samma tur
                            stoppar loopen och HALLER INNE svaret. Harnessen
                            skriver aldrig ett svar at modellen: den vet vad
                            som INTE stammer, aldrig vad som ar sant.

Fail-closed genomgaende: en tur som stoppar ar inte klar, och ett svar som
hallits inne levereras inte.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .. import verktyg as V
from . import arlighet as A
from . import oga as O
from . import redovisning as R
from . import turordning as T
from . import verifiering as Vf
from .fel import Modellfel
from .forgranskning import Avvisning, Forgranskare
from .instruktioner import Korpus, las_korpus
from .kanal import Anropsutfall, Verktygskanal
from .modell import Meddelande, Modell, Modellsvar, Verktygsanrop
from .sammansattning import STANDARDBUDGET, bygg_systemprompt, regelrad

MAX_RUNDOR = 10                 # arvt, 20_arv.md
MAX_RAKA_MISSLYCKANDEN = 6      # arvt, 20_arv.md
MAX_LIKA_ANROP = 2              # vart tillagg till 20_arv.md:s tak
MAX_OMSKRIVNINGAR = 2           # vart tillagg till 20_arv.md:s tak

STOPPREGLER = ("tystnad", "rundtak", "raka_misslyckanden", "upprepat_anrop",
               "omskrivning_misslyckades")

SORTER = ("AVVISAD", "VERKTYG_OK", "VERKTYG_FEL", "OMSKRIVNING", "STOPP",
          "KLAR", "VARNING")

# Handelser som avgor turens utfall. En VERKTYG_FEL gor det INTE: ett anrop
# far falla utan att turen ar forlorad, sa lange slutsvaret ar arligt om det.
_AVGORANDE = ("AVVISAD", "OMSKRIVNING", "STOPP")


@dataclass(frozen=True)
class Handelse:
    sort: str
    kod: str
    text: str
    runda: int

    def rad(self) -> str:
        return "runda %d %s %s: %s" % (self.runda, self.sort, self.kod,
                                       self.text)


@dataclass
class Turprotokoll:
    """Hela turen, som den gick. Det ar detta banken mater."""

    uppgift: str
    korpus_fingeravtryck: str = ""
    systemprompt_tecken: int = 0
    kapade_regler: Tuple[str, ...] = ()
    handelser: List[Handelse] = field(default_factory=list)
    utfallen: List[Anropsutfall] = field(default_factory=list)
    slutsvar: str = ""
    klar: bool = False
    rundor: int = 0

    def lagg(self, sort: str, kod: str, text: str, runda: int) -> Handelse:
        if sort not in SORTER:
            raise Modellfel("unknown event type %r" % (sort,))
        h = Handelse(sort=sort, kod=kod, text=text, runda=runda)
        self.handelser.append(h)
        return h

    @property
    def utfall(self) -> str:
        """Turens utfall som EN kod. Det ar den banken jamfor med facit.

        Forsta avgorande handelsen vinner. Ingen sadan och turen klar ger
        SLAPPT: harnessen har last svaret och inte haft nagot att invanda.
        """
        for h in self.handelser:
            if h.sort in _AVGORANDE:
                return "%s:%s" % (h.sort, h.kod)
        if self.klar:
            return "SLAPPT"
        return "STOPP:okant"

    @property
    def avvisningar(self) -> Tuple[Handelse, ...]:
        return tuple(h for h in self.handelser if h.sort == "AVVISAD")

    @property
    def omskrivningar(self) -> Tuple[Handelse, ...]:
        return tuple(h for h in self.handelser if h.sort == "OMSKRIVNING")

    def text(self) -> str:
        rader = ["UPPGIFT: %s" % self.uppgift,
                 "INSTRUKTIONER: %s, %d tecken%s"
                 % (self.korpus_fingeravtryck, self.systemprompt_tecken,
                    (", %d regler kapade" % len(self.kapade_regler))
                    if self.kapade_regler else "")]
        rader += [h.rad() for h in self.handelser]
        rader.append("UTFALL: %s" % self.utfall)
        return "\n".join(rader)


class Harness(object):
    """Turen, med alla tvingande mekanismer pa plats."""

    def __init__(self, modell: Modell, kanal: Verktygskanal,
                 korpus: Optional[Korpus] = None,
                 forgranskare: Optional[Forgranskare] = None,
                 register=None, urval=None, api=None,
                 budget: int = STANDARDBUDGET,
                 max_rundor: int = MAX_RUNDOR,
                 max_raka_misslyckanden: int = MAX_RAKA_MISSLYCKANDEN,
                 max_lika_anrop: int = MAX_LIKA_ANROP,
                 max_omskrivningar: int = MAX_OMSKRIVNINGAR):
        self.modell = modell
        self.kanal = kanal
        self.korpus = las_korpus() if korpus is None else korpus
        self.register = V.REGISTER if register is None else register
        self.urval = (V.urval_allt_pa(self.register) if urval is None
                      else urval)
        self.forgranskare = (Forgranskare(urval=self.urval,
                                          register=self.register)
                             if forgranskare is None else forgranskare)
        self.api = (self.forgranskare.validator.index if api is None else api)
        self.budget = budget
        self.max_rundor = max_rundor
        self.max_raka_misslyckanden = max_raka_misslyckanden
        self.max_lika_anrop = max_lika_anrop
        self.max_omskrivningar = max_omskrivningar

    # ---- turen -----------------------------------------------------------

    def kor(self, uppgift: str, ogonrapport: Optional[str] = None,
            guldbeslut: Any = None, forlopp: Any = None) -> Turprotokoll:
        """Kor en tur. `forlopp` ar valfritt och for fas 17:s yta MEDAN turen gar.

        Utan det lamnar `Turprotokoll` sin text forst nar turen ar over, och
        det ar en av de fem terminala rapportytorna M-64 raknade. Med det kan
        den som vantar lasa vilken runda som pagar, vilken grind som avvisade
        ett anrop och med vilka ord, och vad turen INTE hann prova - medan det
        hander.

        Harnessen kanner inte forloppsytan. Den anropar metoder pa ett objekt
        anroparen agt hela tiden, och `forlopp=None` ar den vag varje
        befintlig anropare redan gar.
        """
        protokoll = self._kor(uppgift, ogonrapport, guldbeslut, forlopp)
        if forlopp is not None:
            self._avsluta_forloppet(forlopp, protokoll, ogonrapport,
                                    guldbeslut)
        return protokoll

    @staticmethod
    def _stang_rundan(forlopp) -> None:
        """Stanger den runda som star som pagaende, om nagon gor det.

        Ett steg som star kvar pa PAGAR i ett stilla lage ar precis den
        snurrande symbol fasens grind forbjuder, och forloppsytans regel Y2
        faller pa den.
        """
        pagar = forlopp.pagaende_steg()
        if pagar is not None:
            forlopp.steg_klart(pagar.namn)

    def _avsluta_forloppet(self, forlopp, protokoll: Turprotokoll,
                           ogonrapport, guldbeslut) -> None:
        """Turens slut in i forloppet: ogats dom, guldet, och hur det gick.

        Ordningen ar domen fore guldet fore svaret, sa att ett guld aldrig
        star ensamt (regel A-6, och forloppsytans Y7).

        En STOPP blir ett FALL med stoppregelns EGNA ord. Ett stopp som inte
        syns ar samma tystnad som en logg ingen laser: turen holl inne svaret,
        och den som vantar far inte veta att den gjorde det.
        """
        self._stang_rundan(forlopp)
        if ogonrapport:
            forlopp.dom(ogonrapport)
        if guldbeslut is not None:
            text = getattr(guldbeslut, "text", None)
            forlopp.guld(text() if callable(text) else str(guldbeslut))
        stopp = [h for h in protokoll.handelser if h.sort == "STOPP"]
        if stopp:
            forlopp.fall("%s: %s" % (stopp[-1].kod, stopp[-1].text))
        elif protokoll.klar:
            forlopp.svar(protokoll.slutsvar)
        else:
            forlopp.fall(
                "turen slutade utan slutsvar och utan stoppkod; utfallet ar "
                "%s" % protokoll.utfall)

    def _kor(self, uppgift: str, ogonrapport: Optional[str],
             guldbeslut: Any, forlopp: Any) -> Turprotokoll:
        prompt = bygg_systemprompt(self.korpus, self.budget)
        protokoll = Turprotokoll(
            uppgift=uppgift,
            korpus_fingeravtryck=prompt.fingeravtryck,
            systemprompt_tecken=prompt.tecken,
            kapade_regler=prompt.kapade_regler)

        historik: List[Meddelande] = [Meddelande("uppgift", uppgift)]
        grund = Vf.Grund(uppgiftstext=uppgift,
                         verktygsnamn=tuple(self.urval.pa_namn()),
                         api=self.api,
                         katalogindex=self.forgranskare.katalogindex)
        if ogonrapport:
            grund.lagg_text(ogonrapport, "ogat")

        verktygslista = [self.register[n] for n in self.urval.pa_namn()]
        turlage = T.Turlage()
        raka_fel = 0
        omskrivningar = 0
        fallda_nycklar: Dict[str, int] = {}

        for runda in range(1, self.max_rundor + 1):
            protokoll.rundor = runda
            if forlopp is not None:
                self._stang_rundan(forlopp)
                forlopp.steg_borjar("runda %d" % runda,
                                    "modellen far ordet")
            svar = self.modell.svara(prompt.text, tuple(historik),
                                     verktygslista)
            if not isinstance(svar, Modellsvar):
                raise Modellfel(
                    "the adapter returned %s, not a Modellsvar"
                    % type(svar).__name__)

            if svar.tomt:
                protokoll.lagg("STOPP", "tystnad",
                               "modellen svarade varken med text eller anrop; "
                               "tystnad ar aldrig ett godkannande (I3)", runda)
                return protokoll

            if not svar.ar_slutsvar:
                historik.append(Meddelande(
                    "modell", svar.text or "(bad om %d verktygsanrop)"
                    % len(svar.anrop)))
                stoppkod, raka_fel = self._kor_anrop(
                    svar, runda, protokoll, historik, grund, uppgift,
                    fallda_nycklar, raka_fel, turlage, forlopp)
                if stoppkod is not None:
                    return protokoll
                if raka_fel >= self.max_raka_misslyckanden:
                    protokoll.lagg(
                        "STOPP", "raka_misslyckanden",
                        "%d anrop i rad foll eller avvisades; taket ar %d "
                        "(arvt, 20_arv.md)"
                        % (raka_fel, self.max_raka_misslyckanden), runda)
                    return protokoll
                continue

            # Slutsvar: ingen begaran om verktyg, alltsa det modellen vill
            # lamna ifran sig. Har, och bara har, provas grindarna pa texten.
            krav = self._granska_slutsvar(svar.text, protokoll, grund,
                                          ogonrapport, guldbeslut, runda)
            if krav is None:
                protokoll.slutsvar = svar.text
                protokoll.klar = True
                protokoll.lagg("KLAR", "slappt",
                               "slutsvaret passerade samtliga grindar", runda)
                return protokoll

            krav = self._med_regeltext(krav)
            if forlopp is not None:
                # 24_samtalsloopen.md, avsnitt 7: en omskrivning doljs inte. Kravet gar
                # ut ordagrant - det ar en grinds ord om ett svar, och det ar
                # just den sortens text som inte far mjukas upp pa vagen.
                forlopp.omskrivning(krav)
            omskrivningar += 1
            if omskrivningar > self.max_omskrivningar:
                protokoll.lagg(
                    "STOPP", "omskrivning_misslyckades",
                    "svaret kravde omskrivning %d ganger; taket ar %d. Svaret "
                    "halls inne: harnessen vet vad som inte stammer, aldrig "
                    "vad som ar sant" % (omskrivningar, self.max_omskrivningar),
                    runda)
                return protokoll
            historik.append(Meddelande("grind", krav))

        protokoll.lagg("STOPP", "rundtak",
                       "turen nadde taket pa %d rundor utan ett godkant "
                       "slutsvar (arvt, 20_arv.md)" % self.max_rundor,
                       self.max_rundor)
        return protokoll

    # ---- anropen ---------------------------------------------------------

    def _kor_anrop(self, svar: Modellsvar, runda: int,
                   protokoll: Turprotokoll, historik: List[Meddelande],
                   grund: Vf.Grund, uppgift: str,
                   fallda_nycklar: Dict[str, int], raka_fel: int,
                   turlage: "T.Turlage", forlopp: Any = None):
        """Kor rundans anrop. Returnerar (stoppkod, raka_fel).

        raka_fel raknas over HELA turen och inte per runda: en modell som
        misslyckas en gang per runda ska traffa taket lika sakert som en som
        misslyckas sex ganger i en runda.
        """
        for i, anrop in enumerate(svar.anrop):
            if not isinstance(anrop, Verktygsanrop):
                raise Modellfel("the adapter returned a call of type %s"
                                % type(anrop).__name__)
            if not anrop.id:
                anrop = Verktygsanrop(namn=anrop.namn, argument=anrop.argument,
                                      id="r%d-%d" % (runda, i + 1))
            nyckel = anrop.nyckel()
            if fallda_nycklar.get(nyckel, 0) >= self.max_lika_anrop:
                protokoll.lagg(
                    "STOPP", "upprepat_anrop",
                    "%s har redan fallit %d ganger med samma argument; ett "
                    "tredje identiskt anrop mot oforandrat tillstand ger "
                    "samma fel" % (anrop.beskrivning(), fallda_nycklar[nyckel]),
                    runda)
                return "upprepat_anrop", raka_fel

            dom = self.forgranskare.granska_anrop(anrop, uppgift)
            avvisning = dom.avvisning
            if avvisning is None:
                turdom = turlage.domer(dom.verktyg, dom.argument, dom.kod)
                if turdom.nekas:
                    avvisning = Avvisning(grind=turdom.grind,
                                          skal=turdom.skal,
                                          vad=anrop.beskrivning())
            if avvisning is not None:
                protokoll.lagg("AVVISAD", avvisning.grind, avvisning.text(),
                               runda)
                if forlopp is not None:
                    # Grindens EGNA ord, tecken for tecken. En avvisning som
                    # sammanfattas pa vagen ut ar samma omskrivning som en
                    # avvisning som sammanfattas pa vagen till modellen.
                    forlopp.grind("%s (%s)" % (avvisning.grind, anrop.namn),
                                  False, avvisning.text())
                historik.append(Meddelande(
                    "grind", self._avslagstext(avvisning), anrop.id,
                    anrop.namn))
                fallda_nycklar[nyckel] = fallda_nycklar.get(nyckel, 0) + 1
                raka_fel += 1
                if raka_fel >= self.max_raka_misslyckanden:
                    return None, raka_fel
                continue

            for varning in dom.varningar:
                protokoll.lagg("VARNING", "fore_korning", varning, runda)
                if forlopp is not None:
                    forlopp.degraderad(varning)
                historik.append(Meddelande("grind", varning, anrop.id,
                                           anrop.namn))

            if forlopp is not None:
                forlopp.lagg("VERKTYG_START", anrop.beskrivning(),
                             steg=anrop.namn)
            utfall = self.kanal.utfor(anrop.namn, dom.argument)
            turlage.lagg(anrop.namn, dom.kod, utfall.ok, utfall.resultat)
            utfall = Anropsutfall(
                verktyg=utfall.verktyg, argument=utfall.argument,
                ok=utfall.ok, resultat=utfall.resultat, fel=utfall.fel,
                koad=utfall.koad, qid=utfall.qid,
                varningar=tuple(dom.varningar),
                andrade=bool(T.andrar_scenen(dom.kod or "")))
            protokoll.utfallen.append(utfall)
            if utfall.ok:
                protokoll.lagg("VERKTYG_OK", anrop.namn, utfall.beskrivning(),
                               runda)
                if forlopp is not None:
                    forlopp.lagg("VERKTYG_KLART", utfall.beskrivning(),
                                 steg=anrop.namn)
                if utfall.andrade:
                    # Scenen andrades. Allt som mattes fore detta beskriver
                    # laget FORE andringen (ARB-004, M-11). Generationen hojs
                    # FORE resultatet laggs in, sa att anropets egna argument
                    # hor till den nya generationen.
                    grund.ny_generation()
                grund.lagg_resultat(anrop.namn, utfall.argument, utfall.resultat)
                raka_fel = 0
                fallda_nycklar.pop(nyckel, None)
            else:
                protokoll.lagg("VERKTYG_FEL", anrop.namn,
                               utfall.beskrivning(), runda)
                if forlopp is not None:
                    forlopp.lagg("VERKTYG_FEL", utfall.beskrivning(),
                                 steg=anrop.namn,
                                 ordagrant=utfall.beskrivning())
                fallda_nycklar[nyckel] = fallda_nycklar.get(nyckel, 0) + 1
                raka_fel += 1
            historik.append(Meddelande("verktyg", utfall.beskrivning(),
                                       anrop.id, anrop.namn))
            if raka_fel >= self.max_raka_misslyckanden:
                return None, raka_fel
        return None, raka_fel

    def _med_regeltext(self, krav: str) -> str:
        """Lagger till hela texten for varje regel kravet namner vid id.

        En modell som far veta att den brot ARL-001 utan att fa lasa ARL-001
        rattar gissningsvis - och den kapade prompten kan dessutom sakna
        regeln. Regeln hamtas darfor ur korpusen och skickas med.
        """
        citerade = []
        for regel_id in sorted(set(re.findall(r"\b[A-Z]{3}-\d{3}\b", krav))):
            try:
                citerade.append("  %s" % regelrad(self.korpus, regel_id))
            except KeyError:
                continue
        if not citerade:
            return krav
        return krav + "\nReglerna du bryter mot, i sin helhet:\n" + "\n".join(citerade)

    @staticmethod
    def _avslagstext(avvisning) -> str:
        return ("Anropet kordes ALDRIG. Grinden %s avvisade det:\n%s\n"
                "Ratta det och forsok igen, eller skriv att du inte kan "
                "utfora uppgiften."
                % (avvisning.grind,
                   "\n".join("  - %s" % s for s in avvisning.skal)))

    # ---- slutsvaret ------------------------------------------------------

    def _granska_slutsvar(self, text: str, protokoll: Turprotokoll,
                          grund: Vf.Grund, ogonrapport, guldbeslut,
                          runda: int) -> Optional[str]:
        """None = svaret slapps igenom. Annars omskrivningskravet."""
        dom = self.forgranskare.granska_svarstext(text)
        if not dom.slapps:
            protokoll.lagg("AVVISAD", dom.avvisning.grind,
                           dom.avvisning.text(), runda)
            return self._avslagstext(dom.avvisning)

        anmarkningar = A.granska(text, protokoll.utfallen)
        if anmarkningar:
            protokoll.lagg("OMSKRIVNING", anmarkningar[0].kod,
                           "; ".join(a.text() for a in anmarkningar), runda)
            return A.omskrivningskrav(anmarkningar)

        redovisning = R.granska(text, protokoll.utfallen)
        if redovisning:
            protokoll.lagg("OMSKRIVNING", redovisning[0].kod,
                           "; ".join(a.text() for a in redovisning), runda)
            return R.omskrivningskrav(redovisning)

        ogonanmarkningar = O.granska(text, ogonrapport, guldbeslut)
        if ogonanmarkningar:
            protokoll.lagg("OMSKRIVNING", ogonanmarkningar[0].kod,
                           "; ".join(a.text() for a in ogonanmarkningar),
                           runda)
            return O.omskrivningskrav(ogonanmarkningar, ogonrapport)

        avvikelser = Vf.granska(text, grund)
        if avvikelser:
            protokoll.lagg("OMSKRIVNING", "verify_%s" % avvikelser[0].sort,
                           "; ".join(a.text() for a in avvikelser), runda)
            return Vf.omskrivningskrav(avvikelser)
        return None
