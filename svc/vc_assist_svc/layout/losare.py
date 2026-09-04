# -*- coding: utf-8 -*-
"""Lösaren: objekt plus constraints in, placeringar eller ett skäl ut.

Fyra svar, och det är avsiktligt fyra och inte två:

* ``LOST`` - varje objekt har ett läge, och en OBEROENDE efterhandsgranskning
  (kollision.granska) säger noll anmärkningar. Lösaren litar aldrig på sin
  egen sökning som dom över sig själv.
* ``OVERBESTAMD`` - sökningen tömde sitt lägesutrymme med alla constraints,
  men hittade en lösning när en minimal mängd av dem togs bort. Den mängden
  är svaret: DE HÄR gick inte att uppfylla samtidigt. Varje constraint i
  mängden är nödvändigt för konflikten - tas något ur den går det igen.
* ``RYMS_INTE`` - det gick inte ens utan en enda relation. Då är det inte
  constraints som står i vägen utan hallen, och svaret bär den mätta lediga
  ytan mot den begärda.
* ``OBESTAMBART`` - budgeten tog slut, eller självgranskningen sa emot
  sökningen. Motorn kan då INTE garantera att en placering är fri, och säger
  därför nej i stället för att gissa. Fail-closed, docs/spec/90_invarianter.md I3.

Vad OVERBESTAMD inte påstår: att problemet är matematiskt olösbart. Lösaren
söker i ett RASTER av lägen som relationerna föreslår, inte i det kontinuerliga
planet. Den säger "jag hittade ingen med de här, men en utan de här", vilket är
ett mätt och kontrollerbart påstående. Det motsatta felet - att påstå olösbart
och mena det - hade varit ett påstående motorn inte kan bära.

DETERMINISM: samma indata ger samma utdata, alltid. Varje ordning i sökningen
är fastlagd - objektsordningen, kandidatordningen, relationsordningen - och
ingenting hämtas ur en mängd utan sortering. Det provas mekaniskt i
tests/enhet/test_layout_placering.py.

Källa: uppdragets punkt 3.
"""
from __future__ import annotations

from enum import Enum

from .fria_ytor import RASTER_M, ledig_area_m2
from .kollision import granska, provplacera
from .matt import Langd, krav
from .relationer import FORSLAGSRASTER_M, Relation
from .rum import Layoutfel, Pose, Scen

__all__ = ["Status", "Steg", "Losning", "losa", "NODBUDGET"]

# MÄTT 2026-09-04 med bank/uppgifter genom layout/provscener.py: den dyraste
# av de nitton provscenerna använder 3 224 noder, och den dyraste
# konfliktanalysen (nitton omsökningar) 20 682 noder. Budgeten är satt till
# tio gånger den dyraste enskilda sökningen, avrundat uppåt, så att en scen
# som är dubbelt så stor som bankens största fortfarande ryms utan att
# lösaren behöver ändras. Passeras taket blir svaret OBESTAMBART, aldrig ett
# tyst sämre svar. Talet är alltså inte en gissning utan en mätning gånger en
# marginal, och mätningen går att köra om med provscener.mat().
NODBUDGET = 40000


class Status(Enum):
    LOST = "LOST"
    OVERBESTAMD = "OVERBESTAMD"
    RYMS_INTE = "RYMS_INTE"
    OBESTAMBART = "OBESTAMBART"


class Steg:
    """Ett placeringssteg i sökningen: vad som valdes och vad som förkastades."""

    __slots__ = ("namn", "pose", "kalla", "provade", "avvisade")

    def __init__(self, namn, pose, kalla, provade, avvisade):
        self.namn = namn
        self.pose = pose
        self.kalla = kalla
        self.provade = provade
        self.avvisade = avvisade

    def text(self):
        skal = ", ".join("%s x%d" % (k, v) for k, v in
                         sorted(self.avvisade.items(), key=lambda p: (-p[1], p[0])))
        return ("%s -> (%.3f, %.3f, %.3f) m vriden %.4g grader, ur %s "
                "(%d lägen prövade%s)"
                % (self.namn, self.pose.x_m, self.pose.y_m, self.pose.z_m,
                   self.pose.vridning_grader, self.kalla, self.provade,
                   ("; förkastade: " + skal) if skal else ""))

    def __repr__(self):
        return "Steg(%s)" % self.text()


class Losning:
    """Svaret från lösaren. Bär alltid sitt skäl."""

    __slots__ = ("status", "placeringar", "konflikt", "spar", "granskning",
                 "noder", "skal", "scen")

    def __init__(self, status, placeringar, konflikt, spar, granskning, noder,
                 skal, scen):
        self.status = status
        self.placeringar = placeringar
        self.konflikt = tuple(konflikt)
        self.spar = tuple(spar)
        self.granskning = granskning
        self.noder = noder
        self.skal = skal
        self.scen = scen

    @property
    def ok(self):
        return self.status is Status.LOST

    def rapport(self):
        """Hela svaret som rader, i fast ordning. Det här är förklaringen."""
        rader = ["STATUS %s" % self.status.value,
                 "NODER %d" % self.noder]
        if self.skal:
            rader.append("SKAL " + self.skal)
        for steg in self.spar:
            rader.append("PLACERING " + steg.text())
        for r in self.konflikt:
            rader.append("KONFLIKT [%s] %s" % (r.kod, r.text()))
        if self.granskning is not None:
            for rad in self.granskning.rader():
                rader.append("GRANSKNING " + rad)
        return tuple(rader)

    def __repr__(self):
        return ("Losning(%s, %d placerade, %d i konflikt)"
                % (self.status.value, len(self.placeringar), len(self.konflikt)))


# ---- ordning -------------------------------------------------------------

def _beroendegraf(scen, relationer, att_placera):
    """Kanter dep -> namn, bara mellan objekt som ska placeras."""
    fore = {n: set() for n in att_placera}
    for r in relationer:
        for namn in r.positionerar():
            if namn not in fore:
                continue
            for dep in r.beroenden_for(namn):
                if dep in fore and dep != namn:
                    fore[namn].add(dep)
    return fore


def _ordning(scen, relationer, att_placera):
    """Placeringsordningen. Beroenden först, sedan hårdast bundet objekt.

    Nyckeln vid lika: flest relationer, störst fotavtryck, sedan namn. Ett
    stort och hårt bundet objekt placeras först, för det är det som har minst
    frihet och som annars tvingar fram omtag längst ner i trädet.
    """
    fore = _beroendegraf(scen, relationer, att_placera)
    antal = {n: 0 for n in att_placera}
    for r in relationer:
        for n in r.berorda():
            if n in antal:
                antal[n] += 1

    def nyckel(n):
        return (-antal[n], -scen.objekt(n).fotavtryck_area_m2, n)

    kvar = set(att_placera)
    ut = []
    while kvar:
        redo = sorted([n for n in kvar if not (fore[n] & kvar)], key=nyckel)
        if not redo:
            # Cirkulärt beroende. Bryt det på det hårdast bundna objektet och
            # gå vidare; det objektet får då söka på raster i stället för på
            # förslag, vilket är sämre men aldrig fel.
            redo = sorted(kvar, key=nyckel)[:1]
        val = redo[0]
        ut.append(val)
        kvar.discard(val)
    return tuple(ut)


# ---- kandidater ----------------------------------------------------------

def _rasterkandidater(scen, namn, raster_m):
    """Reservutrymmet: hela hallen på raster, i fast ordning."""
    o = scen.objekt(namn)
    golv = scen.hall.golv
    nx = int(golv.bredd_m / raster_m) + 1
    ny = int(golv.djup_m / raster_m) + 1
    for vridning in o.tillatna_vridningar:
        for j in range(ny):
            y = min(golv.y0_m + j * raster_m, golv.y1_m)
            for i in range(nx):
                x = min(golv.x0_m + i * raster_m, golv.x1_m)
                yield Pose.meter(x, y, 0.0, vridning), "raster"


def _kandidater(scen, namn, relationer, raster_m):
    """Lägen att pröva för ett objekt, i fast ordning, utan dubbletter.

    Föreslagna lägen först, i relationernas deklarationsordning. Föreslår
    ingen relation något går sökningen till rastret. Ett förslag är just ett
    förslag: det prövas av kollisionskontrollen och av de andra relationerna
    innan det står kvar.
    """
    sedda = set()
    for r in relationer:
        if namn not in r.positionerar():
            continue
        if any(not scen.ar_placerad(d) for d in r.beroenden_for(namn)):
            continue
        forslag = r.forslag_for(scen, namn, raster_m)
        if not forslag:
            continue
        for pose in forslag:
            n = pose.nyckel()
            if n in sedda:
                continue
            sedda.add(n)
            yield pose, r.kod
    if sedda:
        return
    for pose, kalla in _rasterkandidater(scen, namn, raster_m):
        n = pose.nyckel()
        if n in sedda:
            continue
        sedda.add(n)
        yield pose, kalla


def _relationer_bryts(scen, namn, relationer):
    """Första relation som FÄLLER, given det som står nu. None om ingen gör det.

    En relation vars objekt inte alla är placerade är obestämbar och prövas
    inte här; den prövas när dess sista objekt kommit på plats.
    """
    for r in relationer:
        if namn not in r.berorda():
            continue
        if any(not scen.ar_placerad(n) for n in r.berorda()):
            continue
        utfall = r.prova(scen)
        if utfall.provbar and not utfall.ok:
            return r, utfall
    return None


# ---- sökningen -----------------------------------------------------------

class _Budget(Exception):
    """Budgeten tog slut. Kastas för att avbryta sökningen på djupet."""


def _sok(scen, relationer, ordning, raster_m, budget):
    """Backtracking med konfliktstyrd bakåtjump (CBJ).

    Returnerar (placeringar, noder, spar) eller (None, noder, ()).
    Kastar _Budget när budgeten tar slut, så att den som frågar får veta att
    svaret är okänt i stället för att tro att lägesutrymmet är tömt.

    Varför bakåtjump och inte enkel backtracking: när ett objekt inte kan stå
    NÅGONSTANS av skäl som inte beror på objektet strax före, är det slöseri
    att pröva om det objektets alla rasterlägen. Mätt i provscenerna: en scen
    där en robots underhållsmarginal gör en räckviddsrelation omöjlig gick
    från över 40 000 prövade lägen (budgeten slut, svaret OBESTAMBART) till
    under 300 (svaret OVERBESTAMD med rätt två relationer utpekade). Skillnaden
    är inte hastighet utan om motorn kan svara alls.

    Varje avvisning bär vilka REDAN PLACERADE objekt som orsakade den. Är den
    mängden tom beror felet inte på något val längre upp, och då finns ingen
    lösning alls under den här grenen.
    """
    arbets = scen.kopia()
    rakning = [0]
    spar = []
    niva = {namn: k for k, namn in enumerate(ordning)}

    def skyller(namn_lista):
        """Nivåerna för de objekt som orsakade en avvisning. Låsta räknas ej."""
        return {niva[n] for n in namn_lista if n in niva}

    def rek(k):
        """True, eller (False, konfliktmängd) med nivåer strikt under k."""
        if k == len(ordning):
            return True
        namn = ordning[k]
        provade = 0
        avvisade = {}
        konflikt = set()
        for pose, kalla in _kandidater(arbets, namn, relationer, raster_m):
            rakning[0] += 1
            if rakning[0] > budget:
                raise _Budget()
            provade += 1
            svar = provplacera(arbets, namn, pose)
            if not svar.fri:
                kod = _avvisningskod(svar)
                avvisade[kod] = avvisade.get(kod, 0) + 1
                konflikt |= skyller([o.b if o.a == namn else o.a
                                     for o in svar.overlapp])
                continue
            arbets.placera(namn, pose)
            brott = _relationer_bryts(arbets, namn, relationer)
            if brott is not None:
                arbets.ta_bort_placering(namn)
                kod = brott[0].kod
                avvisade[kod] = avvisade.get(kod, 0) + 1
                konflikt |= skyller([n for n in brott[0].berorda() if n != namn])
                continue
            spar.append(Steg(namn, pose, kalla, provade, dict(avvisade)))
            svar_ner = rek(k + 1)
            if svar_ner is True:
                return True
            spar.pop()
            arbets.ta_bort_placering(namn)
            djupare = svar_ner[1]
            if k not in djupare:
                # Det här objektets val hade ingen del i felet längre ner.
                # Att pröva fler lägen här kan inte hjälpa: hoppa förbi.
                return (False, djupare)
            konflikt |= (djupare - {k})
        return (False, {n for n in konflikt if n < k})

    utfall = rek(0)
    if utfall is True:
        return arbets.placeringar(), rakning[0], tuple(spar)
    return None, rakning[0], ()


def _avvisningskod(svar):
    if svar.utanfor:
        return "UTANFOR_HALLEN"
    if svar.overlapp:
        return "OVERLAPP:" + svar.overlapp[0].typ
    if svar.zonbrott:
        return "ZON:" + svar.zonbrott[0].zon
    return "HOJD"


# ---- konfliktanalys ------------------------------------------------------

def _minimal_konflikt(scen, relationer, ordning, raster_m, delbudget):
    """Minsta mängd relationer som inte går att uppfylla tillsammans.

    Strykning ett i taget, i deklarationsordning: går det ändå INTE utan
    relationen behövdes den inte för konflikten och stryks för gott. Det som
    står kvar är en minimal konfliktmängd - den är olösbar, och stryks vilken
    som helst ur den blir den lösbar. Det är den klassiska deletion-based
    MUS-algoritmen, och den kostar en omsökning per relation.

    Varje delsökning har en EGEN budget, så att en enda dyr delsökning inte
    kan äta hela analysen. Tar en delbudget slut går relationen inte att
    pröva, och då BEHÅLLS den och namnges som oprövad. Mängden är då en
    överskattning av konflikten, och att den är det står i svaret i stället
    för att döljas.

    Returnerar (konfliktmängd, oprövade).
    """
    kvar = list(relationer)
    oprovade = []
    for r in relationer:
        prov = [x for x in kvar if x is not r]
        try:
            placering, _noder, _spar = _sok(scen, prov, ordning, raster_m,
                                            delbudget)
        except _Budget:
            oprovade.append(r)
            continue
        if placering is None:
            kvar = prov
    return tuple(kvar), tuple(oprovade)


def _resten_gar(scen, relationer, konflikt, ordning, raster_m, delbudget):
    """Går resten när hela konfliktmängden stryks? Tre svar: ja, nej, okänt."""
    kvar = [r for r in relationer if r not in konflikt]
    try:
        placering, _noder, _spar = _sok(scen, kvar, ordning, raster_m, delbudget)
    except _Budget:
        return None
    return placering is not None


def losa(scen, relationer=(), raster_m=None, budget=NODBUDGET):
    """Placerar allt som saknar läge. Se modulens docstring för de fyra svaren.

    Objekt som redan har ett läge när lösaren anropas står kvar där de står;
    de räknas som givna. Relationer som rör dem prövas ändå.
    """
    if not isinstance(scen, Scen):
        raise Layoutfel("losa tar en Scen")
    relationer = tuple(relationer)
    for r in relationer:
        if not isinstance(r, Relation):
            raise Layoutfel("en relation måste ärva Relation, fick %r" % (r,))
        for n in r.berorda():
            scen.objekt(n)  # okänt namn är ett hårt fel, inte en varning
    steg_m = (FORSLAGSRASTER_M if raster_m is None
              else krav(raster_m, "raster_m").som_m)

    att_placera = tuple(n for n in scen.fria_namn() if not scen.ar_placerad(n))
    ordning = _ordning(scen, relationer, att_placera)

    noder = 0
    try:
        placering, noder, spar = _sok(scen, relationer, ordning, steg_m, budget)
    except _Budget:
        return Losning(Status.OBESTAMBART, {}, (), (), None, budget,
                       "budgeten om %d prövade lägen tog slut innan "
                       "lägesutrymmet var genomsökt; motorn kan inte garantera "
                       "att någon placering är fri och säger därför nej"
                       % budget, None)

    if placering is not None:
        klar = scen.kopia()
        for namn, pose in placering.items():
            if not klar.ar_placerad(namn):
                klar.placera(namn, pose)
        dom = granska(klar, raster_m=Langd.m(RASTER_M))
        if dom.ok:
            return Losning(Status.LOST, placering, (), spar, dom, noder, "", klar)
        # Sökningen och den oberoende granskningen säger emot varandra. Det
        # är inte ett godkännande, det är ett okänt läge. Fail-closed.
        return Losning(Status.OBESTAMBART, placering, (), spar, dom, noder,
                       "sökningen hittade en placering som efterhands"
                       "granskningen underkände; se GRANSKNING-raderna", klar)

    # Ingen lösning med alla relationer. Beror det på relationerna eller på
    # hallen? Frågan avgörs genom att söka helt utan dem.
    try:
        utan, noder_utan, _spar = _sok(scen, (), ordning, steg_m, budget)
    except _Budget:
        return Losning(Status.OBESTAMBART, {}, (), (), None, noder + budget,
                       "budgeten tog slut under kontrollen av om objekten alls "
                       "får plats i hallen", None)
    if utan is None:
        begard = sum(scen.objekt(n).fotavtryck_area_m2 for n in att_placera)
        ledig = ledig_area_m2(scen, max(
            [scen.objekt(n).hojd for n in att_placera] or [Langd.m(0.1)]))
        return Losning(
            Status.RYMS_INTE, {}, (), (), None, noder + noder_utan,
            "objekten får inte plats i hallen ens utan en enda relation: de "
            "kräver %.1f m2 fotavtryck och %.1f m2 är ledig, och den lediga "
            "ytan är dessutom inte sammanhängande nog"
            % (begard, ledig), None)

    # Egen budget per delsökning, så att analysen som helhet är bunden och en
    # enda dyr delsökning inte kan äta upp de andra. Golvet om 1 000 finns för
    # att en analys med många relationer annars får delbudgetar som inte
    # räcker till ens en enkel omsökning.
    delbudget = max(1000, budget // (len(relationer) + 1))
    konflikt, oprovade = _minimal_konflikt(scen, relationer, ordning, steg_m,
                                           delbudget)
    if not konflikt:
        # Varje enskild relation gick att stryka, men tillsammans går de inte.
        # Det ska inte kunna hända med strykning ett i taget, och om det ändå
        # gör det är svaret okänt och inte ett nej med adress.
        return Losning(Status.OBESTAMBART, {}, (), (), None, noder,
                       "ingen lösning hittades, och strykning ett i taget "
                       "pekade inte ut någon relation som band; konflikten är "
                       "inte lokaliserad", None)
    gar = _resten_gar(scen, relationer, konflikt, ordning, steg_m, delbudget)
    if oprovade:
        minimalitet = ("mängden är en ÖVERSKATTNING: %d relationer gick inte "
                       "att pröva inom delbudgeten (%s)"
                       % (len(oprovade),
                          ", ".join(r.kod for r in oprovade)))
    else:
        minimalitet = ("mängden är minimal: stryks vilken som helst av dem "
                       "går resten")
    if gar is True:
        rest = "stryks hela mängden går layouten"
    elif gar is False:
        rest = "även utan hela mängden återstår en konflikt, så det finns fler"
    else:
        rest = "om layouten går utan mängden hann inte prövas inom delbudgeten"
    return Losning(Status.OVERBESTAMD, {}, konflikt, (), None, noder,
                   "ingen placering uppfyller alla relationer; dessa %d binder. "
                   "%s. %s" % (len(konflikt), minimalitet, rest), None)
