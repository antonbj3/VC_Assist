# -*- coding: utf-8 -*-
"""SPARREN: vad en modell far gora med en scen som redan finns.

Modulen ar byggd FORE tolken, och ordningen ar inte kosmetisk. Den gamla
fritextvagen (plan/forfining.py) garanterade "inget tyst val" genom att gora
tolken OFORMOGEN att gissa: ORDBOK ar 32 hardkodade svenska ord, och saknas
ordet blir det en fraga. Det ar en akta garanti - och den kostar hela
sprakformagan. "conveyor" ger None.

Garantin flyttas darfor hit. Modellen far lasa meningen; grinden avgor vad
som far goras med den. Tre las, och de ar oberoende:

  LASSPARREN        En DIAGNOS ror aldrig scenen. Spar rens ar inte en
                    instruktion i en systemprompt utan URVALET: varje verktyg
                    med effect=write slas AV, sa modellen ser dem inte
                    (Urval.openai_verktyg) och utforaren kastar Avstangt om
                    namnet anda kommer (verktyg/utforare.py: urval.krav).
                    Tredje lagret ligger redan i bryggan (skrivgrind).

  HARKOMSTGRINDEN   Varje falt modellen producerar bar en HARLEDNING eller ar
                    markt som en FRAGA. Ingen tredje vag. Det ar samma regel
                    som plan/forfining.py:s anta()/fraga(), men prova d pa
                    UTDATAN i stallet for garanterad av indatans dumhet.

  ENTYDIGHETEN      Ett mal med flera kandidater i den lasta scenen ar en
                    FRAGA tillbaka, aldrig ett val. "Byt det dar gripdonet"
                    med tre gripdon i scenen har inget ratt svar.

VARFOR KALLORNA INTE AR plan/harkomst.py:s KALLOR RAKT AV

plan/harkomst.py listar sju kallor for ett krav i en BYGGSPEC: begaran,
antagande, fraga, katalog, datablad, bank, layout. En utsaga om en scen som
redan kor har tva kallor till som inte finns dar - vad ett lasande verktyg
returnerade, och vad ogat matte - och de tva ar de viktigaste har. Listan
utvidgas darfor lokalt i stallet for att plan/harkomst.py skrivs om: fem
sessioner delar repot, och den filen ar planeringslagrets.

Delstrangskontrollen for "begaran" ar DENSAMMA funktionen
(harkomst.normalisera), sa de tva lagren kan inte drifta isar om vad ett
citat ar.

Kontrollen for "scen" och "ogat" delegeras till harness/verifiering.Grund,
som redan bar turens verktygssvar och ogats rapport och redan ar matt i fas
22. Att skriva en andra stodkontroll har hade gett tva listor som driftar.

Endast standardbiblioteket plus tjanstens egna lager.
"""
from __future__ import annotations

from ..plan.harkomst import normalisera
from ..verktyg.formagegrind import Urval

# Kallorna. Sluten lista: en kalla som inte star har finns inte, och ett falt
# med en okand kalla avvisas. Det finns ingen kalla som betyder "vi tyckte
# sa" - det ar hela poangen med listan.
#
#   begaran   operatorens egna ord, ORDAGRANT. Provas som delstrang.
#   scen      ett lasande verktygssvar i den har turen.
#   ogat      en rad ur ogats rapport, ordagrant i ogats grammatik.
#   fraga     inte ett varde alls: en oppen fraga till operatoren.
KALLOR = ("begaran", "scen", "ogat", "fraga")

# Kortaste belagg som sager nagot alls. Samma tal och samma skal som
# plan/harkomst.MIN_BELAGG_TECKEN (satt av M-63): ett belagg pa ett eller tva
# tecken matchar nastan vilken text som helst och gor kontrollen trivialt
# sann. Talet star har och inte importeras, darfor att en delad konstant over
# tva lager ar en koppling som ingen av dem beskriver - men det ar SAMMA tal,
# och test_scenarbete.py provar att de inte glidit isar.
MIN_BELAGG_TECKEN = 3       # Satt av M-63, provat mot plan/harkomst.py i M-162.

LINTKODER = {
    "SH1_UTAN_HARKOMST": "faltet bar varken harledning eller fraga",
    "SH2_FALSK_BEGARAN": "faltet sager sig komma ur begaran, men orden star "
                         "inte dar",
    "SH3_OSTODD_SCENUTSAGA": "faltet sager sig komma ur scenen eller ogat, men "
                             "ingen lasning i turen bar det",
    "SH4_OKAND_KALLA": "faltet pekar pa en kalla som inte finns",
}


class Scenharkomst(object):
    """Var ett falt kom ifran, i en form som gar att sla upp igen."""

    __slots__ = ("kalla", "belagg")

    def __init__(self, kalla, belagg):
        self.kalla = kalla
        self.belagg = belagg

    def __repr__(self):
        return "Scenharkomst(%s: %s)" % (self.kalla, self.belagg)

    def text(self):
        if self.kalla == "begaran":
            return 'ur din mening: "%s"' % self.belagg
        if self.kalla == "fraga":
            return "vantar pa ditt svar: %s" % self.belagg
        return "ur %s: %s" % (self.kalla, self.belagg)

    def granska(self, vad, begaran_text, grund):
        """[(lintkod, text)]. Tom lista = harkomsten gar att folja.

        Kastar aldrig (S10): en granskning som kraschar pa ett trasigt falt
        sager ingenting om vad som var trasigt.
        """
        if self.kalla not in KALLOR:
            return [("SH4_OKAND_KALLA",
                     "%s pekar pa kallan %r, som inte finns; kanda ar %s"
                     % (vad, self.kalla, ", ".join(KALLOR)))]
        if (not isinstance(self.belagg, str)
                or len(self.belagg.strip()) < MIN_BELAGG_TECKEN):
            return [("SH1_UTAN_HARKOMST",
                     "%s bar ett belagg pa under %d tecken (%r); ett sa kort "
                     "belagg matchar nastan vilken text som helst och bevisar "
                     "ingenting" % (vad, MIN_BELAGG_TECKEN, self.belagg))]
        if self.kalla == "fraga":
            return []
        if self.kalla == "begaran":
            if normalisera(self.belagg) not in normalisera(begaran_text):
                return [("SH2_FALSK_BEGARAN",
                         "%s sager sig komma ur din mening med orden %r, men "
                         "de orden star inte dar. En modell som skriver om "
                         "operatorens ord har slutat citera honom"
                         % (vad, self.belagg))]
            return []
        # scen och ogat: turens egna lasningar ar facit.
        if grund is None:
            return [("SH3_OSTODD_SCENUTSAGA",
                     "%s sager sig komma ur %s, men turen har ingen grund att "
                     "prova det mot; en utsaga om scenen utan lasning ar en "
                     "gissning" % (vad, self.kalla))]
        skal = _stods_av_grunden(self.belagg, grund)
        if skal is not None:
            return [("SH3_OSTODD_SCENUTSAGA",
                     "%s sager sig komma ur %s med orden %r: %s"
                     % (vad, self.kalla, self.belagg, skal))]
        return []


def ur_begaran(belagg):
    """Kortform: operatorens egna ord."""
    return Scenharkomst("begaran", belagg)


def ur_scenen(belagg):
    """Kortform: ett lasande verktygssvar i turen."""
    return Scenharkomst("scen", belagg)


def ur_ogat(belagg):
    """Kortform: en rad ur ogats rapport."""
    return Scenharkomst("ogat", belagg)


def som_fraga(text):
    """Den andra lagliga vagen. Ger inget varde - den ber om ett."""
    return Scenharkomst("fraga", text)


def _stods_av_grunden(belagg, grund):
    """None om grunden bar belagget, annars skalet den inte gor det.

    Delegerar till harness/verifiering.Grund, som redan ar turens facit for
    vad verktygen returnerade och vad ogat skrev. Namnen provas ett i taget
    sa att felet kan namna DET ord som saknades.
    """
    from ..harness.text import Namnpastaende
    for ord_ in str(belagg).split():
        rent = ord_.strip(".,;:()[]\"'")
        if len(rent) < MIN_BELAGG_TECKEN or rent.replace(".", "").isdigit():
            continue
        skal = grund.stodjer_namn(Namnpastaende(namn=rent, mening=str(belagg)))
        if skal is not None:
            return skal
    return None


class Falt(object):
    """Ett varde modellen producerat, och varifran det kom.

    harkomst=None ar INTE ett tomt falt - det ar ett varde utan harledning,
    och det ar precis vad grinden finns for att fanga.
    """

    __slots__ = ("namn", "varde", "harkomst")

    def __init__(self, namn, varde, harkomst):
        self.namn = namn
        self.varde = varde
        self.harkomst = harkomst

    def __repr__(self):
        return "Falt(%s=%r, %r)" % (self.namn, self.varde, self.harkomst)

    @property
    def ar_fraga(self):
        return (self.harkomst is not None
                and self.harkomst.kalla == "fraga")


def granska_falt(falt, begaran_text, grund):
    """[(lintkod, text)] over manga falt. Tom lista = alla bar sin harkomst.

    Det ar HELA sparren mot ett tyst val: ett falt som varken gar att harleda
    eller ar markt som fraga kommer inte igenom har.
    """
    ut = []
    for f in falt:
        if f.harkomst is None:
            ut.append(("SH1_UTAN_HARKOMST",
                       "%s bar varken en harledning eller en fraga. Ett varde "
                       "utan harkomst ar ett tyst val, och det finns ingen "
                       "tredje vag in i en spec (plan/forfining.py)" % (f.namn,)))
            continue
        ut += f.harkomst.granska(f.namn, begaran_text, grund)
    return ut


def oppna_fragor(falt):
    """De falt som ar markta som fragor. De bar inget varde an."""
    return tuple(f.harkomst.belagg for f in falt if f.ar_fraga)


class Scenlage(object):
    """Vad en LASNING av scenen faktiskt gav. Inget hittas pa har.

    komponenter ar (namn, typ)-par ur ett lasande verktygssvar, och `kalla`
    namner verktyget som gav dem. Ett Scenlage utan kalla gar inte att
    granska mot, och det ar med flit: I9 sager att modellen bara far valja ur
    det som finns, och "det som finns" maste da vara nagot nagon last.
    """

    __slots__ = ("komponenter", "kalla")

    def __init__(self, komponenter=(), kalla=""):
        self.komponenter = tuple((str(n), str(t)) for n, t in komponenter)
        self.kalla = kalla

    def __repr__(self):
        return "Scenlage(%d komponenter ur %s)" % (len(self.komponenter),
                                                   self.kalla or "ingen lasning")

    def namn(self):
        return tuple(n for n, _t in self.komponenter)

    def kandidater(self, ord_):
        """Komponenterna ett ord kan syfta pa, i scenens egen ordning.

        Matchningen ar en delstrang pa normaliserad text at BADA hallen:
        "gripdon" traffar ST210_gripdon (ordet i namnet) och "ST210_gripdon"
        traffar sig sjalv. Den ar avsiktligt grov - grovheten ar ofarlig
        darfor att flera traffar blir en FRAGA och inte ett val.
        """
        n = normalisera(ord_)
        if not n:
            return ()
        ut = []
        for namn, typ in self.komponenter:
            if n in normalisera(namn) or n == normalisera(typ):
                ut.append(namn)
        return tuple(ut)


# ---- lassparren ----------------------------------------------------------

# Skalet som gar tillbaka till modellen och till operatoren nar ett skrivande
# verktyg slas av. Det ska ga att lasa utan att kanna till specen.
SKAL_DIAGNOS = ("avsikten ar DIAGNOS, och en diagnos ar LASNING: verktyget "
                "har effect=write och far inte roras. Vill du andra scenen, "
                "sag det - da blir det en annan avsikt med en annan grind")

SKAL_INGEN_AVSIKT = ("avsikten ar OKANT eller vantar pa ett svar; OKANT ar "
                     "aldrig ett godkannande (I3, arvt ur plan/motsagelse.py)")


def _krymp(grundurval, av_namn, skal):
    """Ett nytt urval dar av_namn ar av. Redan avslagna behaller SITT skal.

    Spar ren far bara krympa. Ett urval som slog PA nagot vore ingen spar r -
    det vore en vag runt formagegrinden (36_versioner.md).
    """
    domar = {}
    for namn in grundurval.pa_namn():
        domar[namn] = skal if namn in av_namn else None
    for namn, gammalt in grundurval.av_namn().items():
        domar[namn] = gammalt
    return Urval(domar, getattr(grundurval, "rapport", None))


def lasurval(register, grundurval):
    """Urvalet for en DIAGNOS: varje skrivande verktyg ar av.

    Fragan stalls till verktygets DEKLARERADE effect och inte till dess namn
    eller beskrivning. Det ar samma falt som utforarens routingtabell laser
    (I12) och det ar oforanderligt efter registrering (Verktyg.__setattr__),
    sa de tva kan inte saga olika saker om samma verktyg.
    """
    skriver = {n for n, v in register.items() if v.effect == "write"}
    return _krymp(grundurval, skriver, SKAL_DIAGNOS)


def stangt_urval(grundurval):
    """Allt av. For en avsikt som inte ar avgjord."""
    return _krymp(grundurval, set(grundurval.pa_namn()), SKAL_INGEN_AVSIKT)


def urval_for_avsikt(dom, register, grundurval):
    """Urvalet en avsiktsdom ger ratt till.

    Importen av avsikt.py ligger inne i funktionen med flit: sparren ska ga
    att lasa och prova UTAN tolken, eftersom den byggdes fore den.
    """
    from . import avsikt as A
    if dom.dom == A.DIAGNOS:
        return lasurval(register, grundurval)
    if dom.dom in (A.ANDRING, A.OPTIMERING):
        return grundurval
    return stangt_urval(grundurval)


def far_utforas(dom):
    """Far den har domen andra nagot alls?

    Fyra domar, och tva av dem sager nej pa olika satt: FRAGA vantar pa ett
    svar, OKANT vet inte. Ingen av dem ar ett godkannande.
    """
    from . import avsikt as A
    return dom.dom in (A.ANDRING, A.OPTIMERING)
