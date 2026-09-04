# -*- coding: utf-8 -*-
"""Motsagelsegrinden: nar en bestallning inte gar att uppfylla, och VILKA
villkor som krockar.

Grinden som stanger fas 16, ordagrant ur docs/spec/70_faser.md:

    "planen AVVISAS nar den ar omojlig, i stallet for att byggas halvt.
     Trasigt fall: en bestallning som motsager sig sjalv maste fallas med
     vilket villkor som krockar."

Det sista ledet ar hela kravet. "Planen ar ogiltig" ar inget svar - operatoren
kan inte ratta nagot pa det. Svaret ska vara de tva raderna ur hans egen
bestallning som inte kan galla samtidigt, med hans egna ord.

FYRA DOMAR, OCH INGEN AV DEM HETER "MOJLIG"

    OMOJLIG        bevisat: villkoren kan inte alla galla, oavsett hur skickligt
                   nagon later ut cellen. Beviset ar en tom mangd eller ett
                   brutet NODVANDIGT villkor.
    VALET_FALLER   villkoren gar att uppfylla, men inte med den komponent som
                   valts. Skillnaden ar botemedlet: byt komponent, inte krav.
    OKANT          en STATISK storhet saknar varde - ett matt som inte star i
                   katalogen, en cellyta ingen angett. Da vet grinden inte, och
                   OKANT ar aldrig ett godkannande (I3). Kallprojektets stubbar
                   svarade `pass` nar argumentet saknades; det arvs inte.

                   En MATT storhet (scen.kollisioner, scen.min_avstand_mm) ar
                   okand av KONSTRUKTION fore bygget, och det ar inte samma sak.
                   Den blir ett krav att mata efter bygget - planens
                   verifiering - och den far darfor inte gora domen okand. Att
                   blanda ihop de tva hade gjort varenda bestallning okand och
                   grinden vardelos, vilket ar ett annat satt att sluta mata.
    INGEN_FUNNEN   ingen motsagelse hittades av de kontroller som gick att
                   kora. Det ar INTE ett bevis for att layouten gar - det ar
                   ett bevis for att just de har kontrollerna inte fallde.
                   Geometrin domes av layoutmotorn, som soker i ett raster och
                   sjalv sager att den inte pastar matematisk omojlighet.

VARFOR BADE EN SYMBOLISK OCH EN GEOMETRISK GRIND

Den symboliska (har) BEVISAR: ett tomt intervall eller en yta som inte far
plats ar omojligt, punkt. Den ar exakt, kostar ingenting och behover ingen
sokning. Den geometriska (layoutmotor.py -> layout/losare.py) LOKALISERAR:
den soker i ett raster och pekar ut en MINIMAL mangd relationer som binder.
De svarar pa olika fragor och ersatter inte varandra.

DE HARLEDDA VILLKOREN AR NODVANDIGA, ALDRIG TILLRACKLIGA

MK3 (ytan) och MK4 (passformen) ar geometriska nodvandigheter:

    MK4  en rektangel l x b far plats i en ruta B x D bara om
         (l<=B och b<=D) eller (l<=D och b<=B). Ryms den inte i nagon av de
         tva ratvinkliga lagena ryms den inte alls.
    MK3  disjunkta ytor inuti en ruta kan inte summera till mer an rutans yta.
         Med ett kravt gangstrak g mellan tva fotavtryck kan varje fotavtryck
         blasas upp med g/2 pa varje sida utan att de overlappar, och de
         uppblasta ytorna ligger da inom (B+g) x (D+g).

Bryts en av dem finns ingen layout - inte "hittade ingen". Haller de bada
sager de ingenting om huruvida en layout finns.

Endast standardbiblioteket.
"""
from __future__ import annotations

from .storheter import Faktarum, STATISK, egenskaper, lage
from .villkorssprak import BRUTET, OKANT as VILLKOR_OKANT, Typvillkor

OMOJLIG = "OMOJLIG"
VALET_FALLER = "VALET_FALLER"
OKANT = "OKANT"
INGEN_FUNNEN = "INGEN_MOTSAGELSE_FUNNEN"

# Domarnas tyngd. En hardare dom vinner over en mjukare nar bada intraffar:
# ett bevis for omojlighet upphavs inte av att nagon annan storhet var okand.
_TYNGD = {OMOJLIG: 3, VALET_FALLER: 2, OKANT: 1, INGEN_FUNNEN: 0}

KODER = {
    "MK1_INTERVALL_TOMT": "tva villkor pa samma storhet kan inte bada galla",
    "MK2_VARDE_MOT_VILLKOR": "ett kant varde bryter ett villkor",
    "MK3_YTA": "fotavtrycken far inte plats pa den begarda ytan",
    "MK4_PASSAR_EJ": "en komponent ryms inte i cellen i nagot ratvinkligt lage",
    "MK5_GEOMETRISK": "layoutmotorn hittade ingen placering som uppfyller alla "
                      "relationer",
}

# Vilka kallor som betyder "operatoren har sagt det sjalv". Ett varde ur en av
# dem som krockar med ett villkor ar en motsagelse I BESTALLNINGEN. Ett varde
# ur katalogen som krockar ar i stallet ett fallt VAL: komponenten haller inte
# kravet, och botemedlet ar en annan komponent.
_EGNA_ORD = ("begaran", "specens takt", "specens omrade")


class Krock(object):
    """Tva eller flera krav som inte kan galla samtidigt, med sina ord."""

    __slots__ = ("kod", "storhet", "skal", "villkor", "atgard")

    def __init__(self, kod, storhet, skal, villkor=(), atgard=""):
        self.kod = kod
        self.storhet = storhet
        self.skal = skal
        self.villkor = list(villkor)      # Typvillkor eller (id, rad)-par
        self.atgard = atgard

    def __repr__(self):
        return "Krock(%s, %s)" % (self.kod, self.storhet)

    def ids(self):
        return [v.id if hasattr(v, "id") else v[0] for v in self.villkor]

    def rader(self):
        """Raderna operatoren ska se: kravet, med hans egna ord och harkomst."""
        ut = []
        for v in self.villkor:
            ut.append(v.rad() if hasattr(v, "rad") else "%s: %s" % v)
        return ut

    def text(self):
        rader = ["%s: %s" % (self.kod, self.skal)]
        for r in self.rader():
            rader.append("    " + r)
        if self.atgard:
            rader.append("    atgard: %s" % self.atgard)
        return "\n".join(rader)


class Motsagelsedom(object):
    """Utfallet, med sitt skal och sina okanda storheter."""

    __slots__ = ("dom", "krockar", "okanda", "att_mata", "provade", "hoppade")

    def __init__(self, dom, krockar=(), okanda=(), provade=0, hoppade=(),
                 att_mata=()):
        self.dom = dom
        self.krockar = list(krockar)
        self.okanda = list(okanda)      # [(storhet, skal)] - STATISKA hal
        self.att_mata = list(att_mata)  # [(storhet, villkor_id)] - matta krav
        self.provade = provade
        self.hoppade = list(hoppade)    # [(kontroll, skal)]

    def __repr__(self):
        return "Motsagelsedom(%s, %d krockar, %d okanda, %d att mata)" % (
            self.dom, len(self.krockar), len(self.okanda), len(self.att_mata))

    @property
    def faller(self):
        """Sant nar planen inte far byggas. OKANT faller ocksa (fail-closed)."""
        return self.dom in (OMOJLIG, VALET_FALLER, OKANT)

    def text(self):
        rader = ["MOTSAGELSE %s" % self.dom,
                 "PROVADE %d villkorspar och harledningar" % self.provade]
        for k in self.krockar:
            rader.append(k.text())
        for storhet, skal in self.okanda:
            rader.append("OKAND %s: %s" % (storhet, skal))
        for storhet, villkor_id in self.att_mata:
            rader.append("ATT MATA EFTER BYGGET %s (villkoret %s)"
                         % (storhet, villkor_id))
        for kontroll, skal in self.hoppade:
            rader.append("EJ PROVAD %s: %s" % (kontroll, skal))
        return "\n".join(rader)


def _hardast(domar):
    return max(domar, key=lambda d: _TYNGD[d]) if domar else INGEN_FUNNEN


# ------------------------------------------------------------ intervallen

class _Grans(object):
    __slots__ = ("varde", "strikt", "villkor")

    def __init__(self, varde, strikt, villkor):
        self.varde = varde
        self.strikt = strikt
        self.villkor = villkor


def _intervallkrockar(villkor):
    """MK1: villkor pa samma storhet som inte kan galla samtidigt.

    Rent symboliskt. Inga varden, ingen katalog, ingen geometri - bara de krav
    operatoren och detaljeringen skrivit. Det ar den billigaste och saklaste
    motsagelsen som finns, och den som en bestallning som motsager sig sjalv
    oftast faller pa.
    """
    per_storhet = {}
    for v in villkor:
        per_storhet.setdefault(v.storhet, []).append(v)
    ut = []
    provade = 0
    for storhet in sorted(per_storhet):
        krav = per_storhet[storhet]
        enhet = (egenskaper(storhet) or ("", "", ""))[0]
        nedre = None
        ovre = None
        lika = []
        olika = []
        mangder = []
        for v in krav:
            if v.operator == "ge":
                if nedre is None or v.varde > nedre.varde:
                    nedre = _Grans(v.varde, False, v)
            elif v.operator == "gt":
                if nedre is None or v.varde >= nedre.varde:
                    nedre = _Grans(v.varde, True, v)
            elif v.operator == "le":
                if ovre is None or v.varde < ovre.varde:
                    ovre = _Grans(v.varde, False, v)
            elif v.operator == "lt":
                if ovre is None or v.varde <= ovre.varde:
                    ovre = _Grans(v.varde, True, v)
            elif v.operator == "eq":
                lika.append(v)
            elif v.operator == "ne":
                olika.append(v)
            elif v.operator == "in":
                mangder.append(v)
        provade += len(krav)

        if nedre is not None and ovre is not None:
            strikt = nedre.strikt or ovre.strikt
            tomt = (nedre.varde > ovre.varde
                    or (strikt and nedre.varde == ovre.varde))
            if tomt:
                ut.append(Krock(
                    "MK1_INTERVALL_TOMT", storhet,
                    "%s maste vara bade minst %g %s och hogst %g %s; det finns "
                    "inget sadant varde"
                    % (storhet, nedre.varde, enhet, ovre.varde, enhet),
                    [nedre.villkor, ovre.villkor],
                    "ta bort eller mjuka upp ett av de tva kraven"))
        for i, a in enumerate(lika):
            for b in lika[i + 1:]:
                if a.varde != b.varde:
                    ut.append(Krock(
                        "MK1_INTERVALL_TOMT", storhet,
                        "%s ar satt till bade %r och %r"
                        % (storhet, a.varde, b.varde), [a, b],
                        "bestam vilket av de tva vardena som galler"))
        for a in lika:
            for grans, riktning in ((nedre, "minst"), (ovre, "hogst")):
                if grans is None or not isinstance(a.varde, (int, float)):
                    continue
                if riktning == "minst":
                    bryter = (a.varde < grans.varde
                              or (grans.strikt and a.varde == grans.varde))
                else:
                    bryter = (a.varde > grans.varde
                              or (grans.strikt and a.varde == grans.varde))
                if bryter:
                    ut.append(Krock(
                        "MK1_INTERVALL_TOMT", storhet,
                        "%s ar satt till %r men ska samtidigt vara %s %g %s"
                        % (storhet, a.varde, riktning, grans.varde, enhet),
                        [a, grans.villkor],
                        "det satta vardet och gransen kan inte bada sta kvar"))
            for b in olika:
                if a.varde == b.varde:
                    ut.append(Krock(
                        "MK1_INTERVALL_TOMT", storhet,
                        "%s ska vara %r och samtidigt inte vara %r"
                        % (storhet, a.varde, b.varde), [a, b],
                        "ta bort det ena av de tva kraven"))
        for m in mangder:
            kvar = list(m.varde)
            for grans, riktning in ((nedre, "minst"), (ovre, "hogst")):
                if grans is None:
                    continue
                if riktning == "minst":
                    kvar = [x for x in kvar if isinstance(x, (int, float))
                            and (x > grans.varde
                                 or (not grans.strikt and x == grans.varde))]
                else:
                    kvar = [x for x in kvar if isinstance(x, (int, float))
                            and (x < grans.varde
                                 or (not grans.strikt and x == grans.varde))]
            if (nedre is not None or ovre is not None) and not kvar:
                med = [g.villkor for g in (nedre, ovre) if g is not None]
                ut.append(Krock(
                    "MK1_INTERVALL_TOMT", storhet,
                    "%s ska vara ett av %r, och inget av dem ligger inom de "
                    "granser de andra villkoren satter" % (storhet, list(m.varde)),
                    [m] + med, "vidga listan eller mjuka upp gransen"))
    return ut, provade


# --------------------------------------------------------- varden mot krav

def _vardekrockar(villkor, faktarum):
    """MK2 plus de tva sorternas okanda: statiska hal och matta krav.

    Ett villkor pa en MATT storhet ar okant fore bygget av konstruktion. Det
    ar inget hal i datan - det ar planens verifiering, och den hor hemma i en
    egen lista.
    """
    krockar = []
    okanda = []
    att_mata = []
    provade = 0
    for v in villkor:
        dom, skal = v.prova(faktarum)
        provade += 1
        if dom == VILLKOR_OKANT:
            if lage(v.storhet) == STATISK:
                okanda.append((v.storhet, skal))
            else:
                att_mata.append((v.storhet, v.id))
            continue
        if dom != BRUTET:
            continue
        varde = faktarum.las(v.storhet)
        egna = any(ord_ in varde.kalla for ord_ in _EGNA_ORD)
        if egna:
            atgard = ("bestallningen sager bade det ena och det andra; ett av "
                      "de tva maste andras")
        else:
            atgard = ("kravet gar att uppfylla, men inte med den har "
                      "komponenten. Byt komponent - eller mjuka upp kravet")
        krockar.append(Krock(
            "MK2_VARDE_MOT_VILLKOR", v.storhet, skal, [v,
                ("varde:%s" % v.storhet, "%s = %s" % (v.storhet, varde.text()))],
            atgard))
    return krockar, okanda, att_mata, provade


# ------------------------------------------------------------- geometrin

def _cellmatt(faktarum):
    """(bredd, djup, gang) i mm, eller (None, skal)."""
    bredd = faktarum.las("cell.bredd_mm")
    djup = faktarum.las("cell.djup_mm")
    if not bredd.kant or not djup.kant:
        return None, (bredd if not bredd.kant else djup).skal
    gang = faktarum.las("cell.gang_min_mm")
    return (bredd.tal, djup.tal, gang.tal if gang.kant else 0.0,
            gang.kant), None


def _passform(faktarum, spec, cellvillkor):
    """MK4: en komponent som inte ryms i cellen i nagot ratvinkligt lage."""
    matt, skal = _cellmatt(faktarum)
    if matt is None:
        return [], [("MK4_PASSAR_EJ", skal)]
    bredd, djup, gang, _hade_gang = matt
    ut = []
    for d in spec.delar:
        langd = faktarum.las("del.%s.langd_mm" % d.roll)
        bred = faktarum.las("del.%s.bredd_mm" % d.roll)
        if not langd.kant or not bred.kant:
            continue
        l, b = langd.tal, bred.tal
        ryms = ((l <= bredd and b <= djup) or (l <= djup and b <= bredd))
        if not ryms:
            ut.append(Krock(
                "MK4_PASSAR_EJ", "del.%s" % d.roll,
                "%s ar %g x %g mm och cellen %g x %g mm; komponenten ryms inte "
                "i nagot av de tva ratvinkliga lagena. Det ar en geometrisk "
                "nodvandighet, inte en misslyckad sokning"
                % (d.roll, l, b, bredd, djup),
                list(cellvillkor) + [("matt:%s" % d.roll,
                                      "%s = %g x %g mm (%s)"
                                      % (d.roll, l, b, langd.kalla))],
                "gor cellen storre eller valj en mindre komponent"))
    return ut, []


def _ytbevis(faktarum, spec, cellvillkor):
    """MK3: summan av fotavtrycken mot den begarda ytan."""
    matt, skal = _cellmatt(faktarum)
    if matt is None:
        return [], [("MK3_YTA", skal)]
    bredd, djup, gang, _hade_gang = matt
    summa = 0.0
    saknade = []
    delar = []
    for d in spec.delar:
        langd = faktarum.las("del.%s.langd_mm" % d.roll)
        bred = faktarum.las("del.%s.bredd_mm" % d.roll)
        if not langd.kant or not bred.kant:
            saknade.append(d.roll)
            continue
        summa += (langd.tal + gang) * (bred.tal + gang) * d.antal
        delar.append("%s %gx%g mm x%d" % (d.roll, langd.tal, bred.tal, d.antal))
    if saknade:
        return [], [("MK3_YTA",
                     "ytbeviset kraver matt for varje del; dessa saknar matt: %s"
                     % ", ".join(sorted(saknade)))]
    tak = (bredd + gang) * (djup + gang)
    if summa > tak:
        return [Krock(
            "MK3_YTA", "cell.yta_mm2",
            "fotavtrycken kraver %.3f m2 (med %g mm gang runt varje) och "
            "cellen ger hogst %.3f m2. Disjunkta ytor kan inte summera till "
            "mer an rutans yta, sa ingen layout finns. Delarna: %s"
            % (summa / 1e6, gang, tak / 1e6, "; ".join(delar)),
            list(cellvillkor),
            "gor cellen storre, ta bort en komponent eller minska gangkravet")], []
    return [], []


# ------------------------------------------------------------------ domen

def granska(villkor, faktarum, spec=None, geometri=True):
    """Motsagelsedom over en mangd Typvillkor. Kastar aldrig.

    `geometri=False` stanger av de harledda ytkontrollerna. Det finns for att
    kunna prova den symboliska delen for sig; det ar aldrig ett satt att fa ett
    gronare svar, eftersom en avstangd kontroll rapporteras som EJ PROVAD.
    """
    villkor = [v for v in villkor if isinstance(v, Typvillkor)]
    if not isinstance(faktarum, Faktarum):
        faktarum = Faktarum()
    krockar, provade = _intervallkrockar(villkor)
    varde_krockar, okanda, att_mata, n = _vardekrockar(villkor, faktarum)
    # En storhet vars villkor redan visats vara omojliga sinsemellan behover
    # inte ocksa rapporteras mot det varde vi harledde ur samma villkor. Ett
    # problem som rapporteras tva ganger later som tva problem, och operatoren
    # letar da efter ett fel som inte finns.
    redan = set(k.storhet for k in krockar)
    krockar += [k for k in varde_krockar if k.storhet not in redan]
    provade += n
    hoppade = []

    if spec is not None and geometri:
        cellvillkor = [v for v in villkor
                       if v.storhet in ("cell.bredd_mm", "cell.djup_mm",
                                        "cell.yta_mm2")]
        for kontroll in (_passform, _ytbevis):
            fynd, ej = kontroll(faktarum, spec, cellvillkor)
            krockar += fynd
            hoppade += ej
            provade += 1
    elif spec is not None:
        hoppade.append(("MK3_YTA och MK4_PASSAR_EJ",
                        "de harledda ytkontrollerna var avstangda i anropet"))

    domar = []
    for k in krockar:
        if k.kod == "MK2_VARDE_MOT_VILLKOR" and "Byt komponent" in k.atgard:
            domar.append(VALET_FALLER)
        else:
            domar.append(OMOJLIG)
    if not domar and (okanda or hoppade):
        domar.append(OKANT)
    return Motsagelsedom(_hardast(domar), krockar, okanda, provade, hoppade,
                         att_mata)
