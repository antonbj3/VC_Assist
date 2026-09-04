# -*- coding: utf-8 -*-
"""Fran detaljerad spec till byggplan: stegen, i ordning, med sina villkor.

Planen bygger scenen med de verktyg som FAKTISKT finns i registret (21 st,
domanerna scene och composition). Den lovar inte mer an sa: styrsignaler,
simulering och ogats korning har egna faser och egna verktyg som annu inte ar
byggda, och planen later inte som om den byggde dem.

MONSTRET PER KOPPLING ar det som ar vart att lasa. Ett gransnittsnamn star
sallan i begaran, och I9 forbjuder att hitta pa ett. I stallet:

    list_interfaces A  ->  \\
                            kontroll: valj paret enligt en sluten regel
    list_interfaces B  ->  /            |
                                        v
                             can_connect (VC:s eget svar)
                                        |
                                 kontroll: sa VC ja?
                                        |
                                     connect

Bar nagon komponent flera gransnitt kan regeln inte valja, och da FALLER
kontrollen med en text som listar kandidaterna. Det ar meningen: da ar valet
operatorens, och planen tiger inte om det.

Kompatibiliteten domes av can_connect, alltsa av VC. Vi implementerar aldrig
om nagon annans matt (I1).

KOORDINATER kommer in pa ETT stalle: layoutporten (layoutport.py). Utan
layoutmotor planeras inga set_transform-steg alls, och det skrivs ut som ett
antagande - VC:s plug and play raknar geometrin sjalv (I8).
"""
from __future__ import annotations

from .byggplan import Byggplan
from .fel import Specfel
from .graf import Uppgiftsgraf
from .layoutport import Layoutport
from .predikat import Forvillkor, Predikat
from .spec import Antagande, Fraga
from .steg import Bindning, Kontroll, Steg

# Faktumet ogonrapporten kommer in som nar planen kors. Koraren far den
# utifran; planeringslagret startar aldrig ogat sjalvt.
OGA_FAKTUM = "oga_rapport"

MOTIV_GRANSSNITTSREGEL = (
    "begaran namner inga gransnittsnamn, och en uppfunnen sadan ar ett hart "
    "fel enligt I9. Planen laser darfor komponenternas egna gransnittslistor "
    "ur scenen och kopplar bara nar bada bar exakt ett gransnitt; bar nagon "
    "flera faller kontrollen och fragan gar till operatoren")

MOTIV_INGEN_LAYOUT = (
    "ingen layoutmotor ar kopplad till planeringen, sa inga koordinater satts. "
    "Komponenterna placeras av VC:s plug and play utifran kopplingarna, vilket "
    "ar den ordning I8 foreskriver: modellen anger relationer, VC raknar "
    "geometrin")

MOTIV_KLON = (
    "en andra instans av samma komponent kan antingen klonas ur den forsta "
    "eller lasas in en gang till ur samma URI. Klonen provas forst darfor att "
    "den ar en operation i VC mot tva, men bada vagarna star i planen och den "
    "andra kors om den forsta faller")


class Planerare(object):
    """Bygger stegen. Bar ingen kannedom om bryggan eller korningen."""

    def __init__(self, spec, layout=None, frigang_mm=None, golv_mm=None,
                 datablad=None):
        self.spec = spec
        self.layout = layout
        self.frigang_mm = frigang_mm
        self.golv_mm = golv_mm
        self.datablad = dict(datablad or {})
        # Layoutmotorns EGNA svar, sparat rakt av. Utan det kan den som
        # planerade se att inga koordinater kom, men inte VARFOR - och
        # skillnaden mellan "hallen ar for liten" och "de har tre kraven kan
        # inte galla samtidigt" ar hela svaret till operatoren.
        self.layoutsvar = None
        self.steg = []
        if layout is not None and not isinstance(layout, Layoutport):
            raise Specfel("planeringen",
                          ["layout maste vara en Layoutport; porten ar det "
                           "som provar motorns svar innan det blir steg"])

    # -- bokforing --------------------------------------------------------

    def _anta(self, vad, varde, motiv, kalla="standard"):
        self.spec.antaganden.append(Antagande(vad, varde, motiv, kalla))

    def _fraga(self, id, vad, varfor, blockerar=True):
        if any(f.id == id for f in self.spec.fragor):
            return
        self.spec.fragor.append(Fraga(id, vad, varfor, blockerar))

    def _lagg(self, steg):
        self.steg.append(steg)
        return steg

    # -- planen -----------------------------------------------------------

    def planera(self):
        placeringar = self._placeringar()
        klara = {}          # roll -> id pa det steg som gor rollen anvandbar
        self._laddsteg(placeringar, klara)
        self._kopplingssteg(klara)
        self._verifieringssteg()
        graf = Uppgiftsgraf(self.steg)
        return Byggplan(self.spec.id, self.spec, graf, "scenbygge")

    # -- delarna ----------------------------------------------------------

    def _laddsteg(self, placeringar, klara):
        laddade = []
        for del_ in self.spec.delar:
            roll = del_.roll
            ladda = self._lagg(Steg.verktygssteg(
                "ladda_%s" % roll, "load_component",
                {"uri": del_.uri, "name": roll},
                "laser in %s ur katalogen och ger den rollens namn" % roll))
            laddade.append(ladda.id)
            namnkontroll = self._lagg(Steg.kontrollsteg(
                "namn_%s" % roll,
                Kontroll("villkor", villkor=Forvillkor([Predikat(
                    "resultat", steg=ladda.id, vag="name", operator="==",
                    varde=roll)])),
                "VC byter namn pa en komponent vars namn redan finns i "
                "layouten; far %s ett annat namn pekar varje foljande steg "
                "pa fel komponent" % roll,
                beroenden=(ladda.id,)))
            sist = namnkontroll.id
            if (roll, 1) in placeringar:
                p = placeringar[(roll, 1)]
                sist = self._lagg(Steg.verktygssteg(
                    "placera_%s" % roll, "set_transform",
                    {"component": roll, "position": p.position_mm,
                     "wpr": p.wpr_deg},
                    "layoutmotorn: %s" % p.motiv,
                    beroenden=(namnkontroll.id,))).id
            sist = self._instanser(del_, ladda.id, sist, placeringar)
            klara[roll] = sist
        if len(laddade) > 1:
            # En deklaration, inte en korform: inlasningarna har inga
            # beroenden mellan sig och FAR koras samtidigt av en utforare som
            # kan det. Koraren i korning.py kor sekventiellt (I13).
            for steg_id in laddade:
                self._satt_parallell(steg_id, "inlasning")

    def _instanser(self, del_, ladda_id, sist_id, placeringar=None):
        """Instans 2..n av en del: klona ur den forsta, eller las in igen.

        Ett alternativ i planens mening: antingen A eller B, och exakt en av
        dem kors. Att bara ignorera antal > 1 hade varit en tyst nedgradering
        - specen sager tva, scenen hade fatt en.
        """
        for i in range(2, del_.antal + 1):
            namn = "%s_%d" % (del_.roll, i)
            grupp = "instans_%s" % namn
            forvillkor = Forvillkor([Predikat("status", steg=ladda_id,
                                              status="kord")])
            self._lagg(Steg.verktygssteg(
                "inst_%s_a_klon" % namn, "clone_component",
                {"name": del_.roll, "new_name": namn},
                MOTIV_KLON, beroenden=(sist_id, ladda_id),
                forvillkor=forvillkor, alternativ_grupp=grupp))
            self._lagg(Steg.verktygssteg(
                "inst_%s_b_ladd" % namn, "load_component",
                {"uri": del_.uri, "name": namn},
                "andra vagen till instans %d av %s: samma URI en gang till"
                % (i, del_.roll),
                beroenden=(sist_id, ladda_id), forvillkor=forvillkor,
                alternativ_grupp=grupp))
            # Instansen far sitt EGNA lage. Att lata kopia nummer tva sta kvar
            # dar VC:s klon lagger den vore en tyst nedgradering: layouten har
            # raknat ett lage for den, och specen bad om tva.
            p = (placeringar or {}).get((del_.roll, i))
            if p is not None:
                self._lagg(Steg.verktygssteg(
                    "placera_%s" % namn, "set_transform",
                    {"component": namn, "position": p.position_mm,
                     "wpr": p.wpr_deg},
                    "layoutmotorn, instans %d: %s" % (i, p.motiv),
                    beroenden=("inst_%s_a_klon" % namn,
                               "inst_%s_b_ladd" % namn)))
        return sist_id

    def _placeringar(self):
        """{roll: Placering} ur layoutmotorn, eller inget alls."""
        if self.layout is None:
            self._anta("placering", "VC:s plug and play", MOTIV_INGEN_LAYOUT)
            return {}
        if self.frigang_mm is None:
            self._fraga(
                "frigang",
                "vilken minsta frigang ska layoutmotorn rakna med?",
                "layoutmotorn kraver ett avstand att halla, och ett avstand vi "
                "valde sjalva skulle bestamma bade cellens yta och vad som "
                "senare raknas som en for trang passage")
            return {}
        svar = self.layout.placera(self.spec, self.frigang_mm, self.golv_mm,
                                   self.datablad)
        self.layoutsvar = svar
        for a in svar.antaganden:
            self.spec.antaganden.append(
                Antagande(a["vad"], a["varde"], a["motiv"], "layout"))
        for f in svar.fragor:
            self._fraga(f["id"], f["vad"], f["varfor"], f["blockerar"])
        placerade = set(svar.roller())
        utan = [d.roll for d in self.spec.delar if d.roll not in placerade]
        if utan:
            self._anta("placering av %s" % ", ".join(utan),
                       "VC:s plug and play",
                       "layoutmotorn lamnade %d roller utan koordinater. De "
                       "far sina lagen ur kopplingarna i stallet, vilket ar "
                       "den ordning I8 foreskriver" % len(utan))
        return dict(((p.roll, p.instans), p) for p in svar.placeringar)

    # -- kopplingarna -----------------------------------------------------

    def _kopplingssteg(self, klara):
        if self.spec.kopplingar:
            self._anta("gransnittsval", "enda_gemensamma_par",
                       MOTIV_GRANSSNITTSREGEL)
        for n, koppling in enumerate(self.spec.kopplingar, 1):
            a, b = koppling.fran_roll, koppling.till_roll
            for roll in (a, b):
                if roll not in klara:
                    raise Specfel("planeringen",
                                  ["kopplingen %d pekar pa rollen %r som "
                                   "ingen del bar" % (n, roll)])
            lista_a = self._lagg(Steg.verktygssteg(
                "gr%d_a" % n, "list_interfaces", {"component": a},
                "hamtar %s egna gransnitt ur scenen i stallet for att hitta "
                "pa ett namn" % a, beroenden=(klara[a],),
                parallell_grupp="granssnitt_%d" % n))
            lista_b = self._lagg(Steg.verktygssteg(
                "gr%d_b" % n, "list_interfaces", {"component": b},
                "hamtar %s egna gransnitt ur scenen" % b,
                beroenden=(klara[b],), parallell_grupp="granssnitt_%d" % n))
            par = self._lagg(Steg.kontrollsteg(
                "par%d" % n,
                Kontroll("bindning", regel="enda_gemensamma_par",
                         kallor=(lista_a.id, lista_b.id),
                         ger=(("if%d_a" % n, "string"), ("if%d_b" % n, "string"))),
                "valjer gransnittsparet nar det inte finns nagot val att gora; "
                "bar nagon komponent flera gransnitt faller steget och fragan "
                "gar till operatoren",
                beroenden=(lista_a.id, lista_b.id)))
            kan = self._lagg(Steg.verktygssteg(
                "kan%d" % n, "can_connect",
                {"component": a,
                 "interface": Bindning("namngiven", par.id, namn="if%d_a" % n),
                 "other_component": b,
                 "other_interface": Bindning("namngiven", par.id,
                                             namn="if%d_b" % n)},
                "fragar VC om paret gar att koppla; kompatibiliteten ar VC:s "
                "matt och raknas aldrig om har (I1)",
                beroenden=(par.id,)))
            svarade_ja = self._lagg(Steg.kontrollsteg(
                "kanok%d" % n,
                Kontroll("villkor", villkor=Forvillkor([Predikat(
                    "resultat", steg=kan.id, vag="can_connect", operator="==",
                    varde=True)])),
                "en koppling VC sagt nej till far inte forsokas anda",
                beroenden=(kan.id,)))
            self._lagg(Steg.verktygssteg(
                "koppla%d" % n, "connect",
                {"component": a,
                 "interface": Bindning("namngiven", par.id, namn="if%d_a" % n),
                 "other_component": b,
                 "other_interface": Bindning("namngiven", par.id,
                                             namn="if%d_b" % n)},
                "kopplingen ar relationen sjalv; inga koordinater foljer med "
                "(I8)", beroenden=(svarade_ja.id, par.id)))

    def _satt_parallell(self, steg_id, grupp):
        for i, s in enumerate(self.steg):
            if s.id == steg_id:
                d = s.till_json()
                d["parallell_grupp"] = grupp
                self.steg[i] = Steg.fran_json(d)
                return
        raise Specfel("planeringen", ["inget steg heter %r" % (steg_id,)])

    # -- beviset ----------------------------------------------------------

    def _verifieringssteg(self):
        """Sista steget ar alltid det som provar att planen bevisade nagot."""
        beroende_pa = set()
        for s in self.steg:
            beroende_pa.update(s.beroenden)
        slut = tuple(sorted(s.id for s in self.steg if s.id not in beroende_pa))
        self._lagg(Steg.kontrollsteg(
            "verifiera", Kontroll("oga", fakta_nyckel=OGA_FAKTUM),
            "haller planens verifieringskrav mot ogats EGEN rapport. Utan den "
            "har kontrollen ar planen en kandidat, aldrig en leverans",
            beroenden=slut))


def planera(spec, layout=None, frigang_mm=None, golv_mm=None, datablad=None):
    """Detaljerad spec -> byggplan.

    Lagger till i specens antaganden och fragor: valen planeringen sjalv gor
    hor hemma dar, bredvid de val forfiningen gjorde, sa att operatoren har en
    lista och inte tva.
    """
    return Planerare(spec, layout, frigang_mm, golv_mm, datablad).planera()
