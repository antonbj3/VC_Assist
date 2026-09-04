# -*- coding: utf-8 -*-
"""Storheterna ett villkor far handla om, och var deras varden kommer ifran.

K6 i docs/spec/22_planeringslagret.md: villkorssspraket ar SLUTET. Vansterledet
ar en NAMNGIVEN STORHET ur en sluten lista, inte fri text. Skalet star i samma
dokument: kallprojektet skrev villkor som "If found, import the STEP geometry",
och den sortens text kan ingen kod utvardera. Ett villkor som ingen kan prova
ar en onskan, och en onskan far inte se ut som ett krav.

TRE LAGEN, OCH SKILLNADEN MELLAN DEM AR HELA POANGEN

    statisk   talet finns i specen, katalogen eller databladet. Det gar att
              prova FORE bygget, alltsa innan nagot kostat en korning.
    matt      talet finns forst nar scenen ar byggd och matt i VC
              (test_collision, min_distance). Statiskt ar det OKANT.
    dom       talet ar ogats eller ett stegs utfall. Ocksa OKANT statiskt.

OKANT AR ETT FORSTKLASSIGT SVAR (I3). En storhet utan varde far aldrig lasas
som noll och aldrig som uppfylld. Databladslagret sager samma sak med samma
ord: `null` ar inte noll (K0). Det ar just den skillnaden som gor att en
motsagelsegrind kan vara arlig: den svarar OMOJLIG nar den kan bevisa det, och
OKANT nar den inte kan - aldrig MOJLIG.

MATT SOM HOR TILL SAKEN

Delarnas matt heter langd/bredd/hojd darfor att det ar den ordning bade
spec.Del.matt_mm och layout.rum.Objekt bar dem. Cellens matt heter
bredd/djup/hojd darfor att det ar den ordning layout.rum.Hall bar dem. Namnen
ar alltsa varje kallas egna, aldrig oversatta i huvudet - en oversattning som
bara finns i en programmerares minne ar den tysta felkallan
(docs/spec/33_varldsenheten... varldsenheten ar millimeter, och varje
storhetsnamn bar sin enhet i sitt eget namn).

Endast standardbiblioteket.
"""
from __future__ import annotations

import re

STATISK = "statisk"
MATT = "matt"
DOM = "dom"

# Sluten lista. Varje rad: (monster, enhet, lage, beskrivning).
# Monstret ar helt namn eller ett namn med en rollplats i.
_ROLL = r"[A-Za-z0-9_åäöÅÄÖ-]+"

STORHETER = (
    (r"cell\.bredd_mm", "mm", STATISK, "cellens bredd"),
    (r"cell\.djup_mm", "mm", STATISK, "cellens djup"),
    (r"cell\.hojd_mm", "mm", STATISK, "fri hojd i cellen"),
    (r"cell\.yta_mm2", "mm2", STATISK, "cellens golvyta"),
    (r"cell\.gang_min_mm", "mm", STATISK, "minsta gangstrak mellan tva "
                                          "fotavtrycksvaggar"),
    (r"del\.%s\.antal" % _ROLL, "st", STATISK, "antal instanser av en roll"),
    (r"del\.%s\.langd_mm" % _ROLL, "mm", STATISK, "rollens langd"),
    (r"del\.%s\.bredd_mm" % _ROLL, "mm", STATISK, "rollens bredd"),
    (r"del\.%s\.hojd_mm" % _ROLL, "mm", STATISK, "rollens hojd"),
    (r"del\.%s\.yta_mm2" % _ROLL, "mm2", STATISK, "rollens fotavtryck"),
    (r"del\.%s\.massa_kg" % _ROLL, "kg", STATISK, "rollens massa"),
    (r"del\.%s\.rackvidd_mm" % _ROLL, "mm", STATISK, "hur langt rollen nar"),
    (r"delar\.yta_mm2", "mm2", STATISK, "summan av alla fotavtryck"),
    (r"delar\.antal", "st", STATISK, "antal komponenter i cellen"),
    (r"takt\.cykeltid_s", "s", STATISK, "begard cykeltid"),
    (r"takt\.genomflode_per_h", "1/h", STATISK, "begart genomflode"),
    (r"scen\.kollisioner", "st", MATT, "test_collision i den byggda scenen"),
    (r"scen\.min_avstand_mm", "mm", MATT, "min_distance i den byggda scenen"),
    (r"avstand\.%s\.%s_mm" % (_ROLL, _ROLL), "mm", MATT,
     "matt avstand mellan tva rollers fotavtrycksvaggar"),
    (r"steg\.%s\.ok" % _ROLL, "", DOM, "ett tidigare stegs utfall"),
    (r"oga\.[A-Z]+", "", DOM, "ogats dom for en sektion"),
)

_MONSTER = tuple((re.compile("^%s$" % m), enhet, lage, text)
                 for m, enhet, lage, text in STORHETER)

# Kort, laslig lista att skriva ut i ett felmeddelande. En sluten lista som
# inte gar att lasa ut ur felet ar sluten for fel person.
NAMNFORMER = tuple(m.replace("\\", "").replace(_ROLL, "<roll>")
                   for m, _e, _l, _t in STORHETER)


def granska_namn(namn):
    """None om storheten finns i spraket, annars ett felmeddelande."""
    if not isinstance(namn, str) or not namn.strip():
        return "storheten saknas; ett villkor utan vansterled ar ingen fraga"
    for monster, _enhet, _lage, _text in _MONSTER:
        if monster.match(namn):
            return None
    return ("%r ar ingen storhet i spraket. Spraket ar slutet (K6 i "
            "docs/spec/22_planeringslagret.md) och bar formerna: %s"
            % (namn, ", ".join(NAMNFORMER)))


def egenskaper(namn):
    """(enhet, lage, beskrivning) for en storhet, eller None."""
    for monster, enhet, lage, text in _MONSTER:
        if monster.match(namn):
            return enhet, lage, text
    return None


def lage(namn):
    """STATISK, MATT eller DOM. None for en okand storhet."""
    e = egenskaper(namn)
    return e[1] if e else None


def rollen_i(namn):
    """Rollen en storhet handlar om, eller None."""
    m = re.match(r"^del\.(%s)\." % _ROLL, namn or "")
    return m.group(1) if m else None


def rollparet_i(namn):
    """(a, b) for ett avstandsnamn, annars None."""
    m = re.match(r"^avstand\.(%s)\.(%s)_mm$" % (_ROLL, _ROLL), namn or "")
    return (m.group(1), m.group(2)) if m else None


# ------------------------------------------------------------------ varden

class Varde(object):
    """Ett tal med sin harkomst, eller ett arligt OKANT med sitt skal."""

    __slots__ = ("kant", "tal", "enhet", "kalla", "skal")

    def __init__(self, kant, tal=None, enhet="", kalla="", skal=""):
        self.kant = bool(kant)
        self.tal = tal
        self.enhet = enhet
        self.kalla = kalla
        self.skal = skal

    def __repr__(self):
        if self.kant:
            return "Varde(%s %s ur %s)" % (self.tal, self.enhet, self.kalla)
        return "Varde(OKANT: %s)" % self.skal

    def text(self):
        if self.kant:
            return "%g %s (%s)" % (self.tal, self.enhet, self.kalla)
        return "okant: %s" % self.skal


def okant(skal):
    return Varde(False, skal=skal)


class Faktarum(object):
    """Allt en villkorsgrind far lasa varden ur, och ingenting mer.

    Tre kallor, och de har olika tyngd:

        spec       operatorens ordersedel. Talen dar bar sin egen harkomst.
        datablad   {roll: {falt: tal}} - matt i VC eller last ur katalogen.
                   Ett falt som saknas ar OKANT, aldrig noll (K0).
        matt       {storhetsnamn: tal} - det scenen faktiskt gav. Tomt fore
                   bygget, och det ar precis darfor de matta storheterna ar
                   OKANDA i en statisk dom.

    Rummet HITTAR ALDRIG PA. Saknas talet svarar det okant med skalet, och den
    som fragade far avgora vad det betyder. Det ar skillnaden mot kallprojektets
    verifier_registry, som svarade `pass` nar argumentet saknades.
    """

    def __init__(self, spec=None, datablad=None, matt=None):
        self.spec = spec
        self.datablad = dict(datablad or {})
        self.matt = dict(matt or {})

    def __repr__(self):
        return "Faktarum(%d datablad, %d matta varden)" % (
            len(self.datablad), len(self.matt))

    # -- uppslagning ------------------------------------------------------

    def _del(self, roll):
        if self.spec is None:
            return None
        for d in self.spec.delar:
            if d.roll == roll:
                return d
        return None

    def _ur_datablad(self, roll, falt):
        post = self.datablad.get(roll)
        if not isinstance(post, dict):
            return None
        varde = post.get(falt)
        return varde if isinstance(varde, (int, float)) and not isinstance(
            varde, bool) else None

    def _matt_ur_del(self, roll, index, falt):
        """langd/bredd/hojd, forst ur databladet och sedan ur specen."""
        ur_blad = self._ur_datablad(roll, falt)
        if ur_blad is not None:
            return Varde(True, float(ur_blad), "mm",
                         "databladet for %s, faltet %s" % (roll, falt))
        d = self._del(roll)
        if d is None:
            return okant("ingen roll heter %r i specen" % (roll,))
        if not d.matt_mm:
            return okant("rollen %s bar inga matt; katalogposten %s saknar "
                         "langd, bredd och hojd och inget datablad ar matt "
                         "(K0: null ar inte noll)" % (roll, d.uri))
        return Varde(True, float(d.matt_mm[index]), "mm",
                     "specens matt for %s ur katalogposten %s" % (roll, d.uri))

    def las(self, namn):
        """Storhetens varde, eller ett OKANT med skal. Kastar aldrig."""
        fel = granska_namn(namn)
        if fel:
            return okant(fel)
        if namn in self.matt:
            enhet = egenskaper(namn)[0]
            return Varde(True, float(self.matt[namn]), enhet,
                         "matt i den byggda scenen")
        if lage(namn) in (MATT, DOM):
            return okant("%s ar %s och finns forst nar scenen ar byggd och "
                         "matt; statiskt ar den okand" % (namn, lage(namn)))
        return self._las_statisk(namn)

    def _las_statisk(self, namn):
        if self.spec is None:
            return okant("ingen spec att lasa %s ur" % namn)
        if namn.startswith("cell."):
            return self._las_cell(namn)
        if namn.startswith("del."):
            return self._las_del(namn)
        if namn.startswith("delar."):
            return self._las_delar(namn)
        if namn.startswith("takt."):
            return self._las_takt(namn)
        return okant("%s gar inte att lasa statiskt" % namn)

    def _las_cell(self, namn):
        omrade = getattr(self.spec, "omrade", None)
        if omrade is None:
            return okant("specen bar inget omrade, sa %s ar okand. Cellens "
                         "matt ar ett hart slot (K2/K11): utan dem gar varken "
                         "ytan eller gangstraket att prova" % namn)
        falt = namn.split(".", 1)[1]
        if falt == "yta_mm2":
            if omrade.bredd_mm is None or omrade.djup_mm is None:
                return okant("cellens yta kraver bade bredd och djup; specen "
                             "bar %r x %r" % (omrade.bredd_mm, omrade.djup_mm))
            return Varde(True, float(omrade.bredd_mm) * float(omrade.djup_mm),
                         "mm2", "specens omrade")
        varde = getattr(omrade, falt, None)
        if varde is None:
            return okant("specens omrade bar inget %s" % falt)
        return Varde(True, float(varde), egenskaper(namn)[0], "specens omrade")

    def _las_del(self, namn):
        _prefix, roll, falt = namn.split(".", 2)
        d = self._del(roll)
        if d is None:
            return okant("ingen roll heter %r i specen; specen bar %s"
                         % (roll, ", ".join(sorted(x.roll for x in
                                                   self.spec.delar)) or "inga delar"))
        if falt == "antal":
            return Varde(True, float(d.antal), "st", "specens del %s" % roll)
        if falt == "massa_kg":
            ur_blad = self._ur_datablad(roll, "massa_kg")
            if ur_blad is not None:
                return Varde(True, float(ur_blad), "kg",
                             "databladet for %s" % roll)
            if d.massa_kg is None:
                return okant("rollen %s bar ingen massa" % roll)
            return Varde(True, float(d.massa_kg), "kg",
                         "specens del %s ur katalogposten %s" % (roll, d.uri))
        if falt == "rackvidd_mm":
            ur_blad = self._ur_datablad(roll, "rackvidd_mm")
            if ur_blad is not None:
                return Varde(True, float(ur_blad), "mm",
                             "databladet for %s" % roll)
            return okant(
                "rackvidden for %s ar okand. Den star inte i komponentens "
                "metadata: MATT i M-63 over hela biblioteket bar 0 av 2169 "
                "robotar ett reach-falt. Den maste komma ur begaran, ur "
                "bank/katalog_index.json eller ur ett matt datablad" % roll)
        if falt == "yta_mm2":
            langd = self._matt_ur_del(roll, 0, "langd_mm")
            bredd = self._matt_ur_del(roll, 1, "bredd_mm")
            if not (langd.kant and bredd.kant):
                return okant("fotavtrycket for %s kraver bade langd och "
                             "bredd; %s" % (roll, (langd if not langd.kant
                                                   else bredd).skal))
            return Varde(True, langd.tal * bredd.tal, "mm2",
                         "langd x bredd, %s" % langd.kalla)
        index = {"langd_mm": 0, "bredd_mm": 1, "hojd_mm": 2}.get(falt)
        if index is None:
            return okant("%s ar inget falt pa en del" % falt)
        return self._matt_ur_del(roll, index, falt)

    def _las_delar(self, namn):
        if namn == "delar.antal":
            return Varde(True, float(sum(d.antal for d in self.spec.delar)),
                         "st", "specens delar")
        summa = 0.0
        saknade = []
        for d in self.spec.delar:
            yta = self.las("del.%s.yta_mm2" % d.roll)
            if not yta.kant:
                saknade.append(d.roll)
                continue
            summa += yta.tal * d.antal
        if saknade:
            return okant("summan av fotavtrycken kraver matt for varje del; "
                         "dessa saknar matt: %s" % ", ".join(sorted(saknade)))
        return Varde(True, summa, "mm2", "summan av delarnas fotavtryck")

    def _las_takt(self, namn):
        takt = self.spec.takt
        if takt is None:
            return okant("specen bar ingen takt")
        falt = namn.split(".", 1)[1]
        varde = getattr(takt, falt, None)
        if varde is None:
            return okant("takten bar inget %s" % falt)
        return Varde(True, float(varde), egenskaper(namn)[0], "specens takt")
