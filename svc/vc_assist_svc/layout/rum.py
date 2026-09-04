# -*- coding: utf-8 -*-
"""Rumsmodellen: hall, zoner, pelare, objekt och deras lägen.

Koordinatsystemet, en gång för alla:

* X åt öster, Y åt norr, Z uppåt. Högerhänt, samma hand som VC.
* Hallens golv är rektangeln (0, 0) till (bredd, djup). Väggarna heter
  VASTER (x = 0), OSTER (x = bredd), SODER (y = 0), NORR (y = djup).
* Ett objekt har en FRAMSIDA. Vid vridning 0 grader pekar framsidan mot +X
  och objektets vänstra sida mot +Y. Det är den konvention "framför",
  "bakom", "till vänster om" och "till höger om" i relationer.py mäter mot.
* Ett objekts läge anges av fotavtryckets MITT och dess UNDERKANT: pose.z_m
  är objektets golvnivå, inte dess mitt. Skälet är att stapling ("på") och
  fri höjd båda räknar från underkanten, och att en mittpunkt i Z hade gjort
  varje sådan räkning till en halveringsfälla.

Utsträckningen är axelriktad i objektets EGEN ram (AABB) plus en vridning
kring Z. Det räcker för fabrikslayout: maskiner, transportörer, pallar och
staket är rätblock, och en fri rotation kring Z täcker de vinklade banorna.
Lutning kring X eller Y finns inte i modellen, och en begäran om det ska
avvisas i stället för att approximeras.

Källa: uppdragets punkt 1, docs/spec/90_invarianter.md I8 (modellen anger
relationer, geometrin räknas), docs/spec/96_ingen_skuld.md S6.
"""
from __future__ import annotations

import math
from enum import Enum

from .matt import Enhetsfel, Langd, Vek2, Vek3, krav, krav_vinkel

__all__ = ["Layoutfel", "Vagg", "Horn", "Zontyp", "Rektangel", "Zon",
           "Pelare", "Ankare", "Objekt", "Pose", "Kropp", "Hall", "Scen",
           "LAGE_TOL_M", "VINKEL_TOL_GRADER"]


class Layoutfel(ValueError):
    """Ett fel i själva layoutbeskrivningen: okänt namn, omöjlig geometri."""


# ---- toleranser ----------------------------------------------------------
# ANTAGNA. Ingen mätning finns ännu; de sätts av mätning M-20 (layoutmotorns
# kalibrering mot en handbyggd VC-cell), som inte är körd.
#
# LAGE_TOL_M: hur nära ett läge måste ligga för att en relation ska räknas
# som uppfylld. Vald till 1 mm, alltså en tiondel av bankens hårdaste
# fixturtolerans (0,3 mm i A-01 är hårdare, men den gäller detaljens läge i
# fixturen, inte maskinens läge på golvet; golvlägen i banken anges i hela
# millimeter). En layouttolerans under 1 mm hade mätt flyttalsbrus.
LAGE_TOL_M = 0.001
# VINKEL_TOL_GRADER: ANTAGEN av samma skäl, och sätts av samma mätning M-20.
# En tiondels grad över en 3 m lång bana ger 5 mm avvikelse i änden, alltså
# samma storleksordning som lägestoleransen.
VINKEL_TOL_GRADER = 0.1


class Vagg(Enum):
    """Hallens fyra väggar."""
    VASTER = "vaster"
    OSTER = "oster"
    SODER = "soder"
    NORR = "norr"


class Horn(Enum):
    """Hallens fyra hörn, namngivna efter de två väggar de möter."""
    SYDVAST = ("soder", "vaster")
    SYDOST = ("soder", "oster")
    NORDOST = ("norr", "oster")
    NORDVAST = ("norr", "vaster")


class Zontyp(Enum):
    """Vad en zon betyder för en placering."""
    ARBETSYTA = "arbetsyta"          # här FÅR maskiner stå
    GANG = "gang"                    # hålls fri upp till zonens fria höjd
    UTRYMNINGSVAG = "utrymningsvag"  # hålls fri, och bredden mäts efteråt
    FORBJUDET = "forbjudet"          # inget får stå här, i hela hallens höjd


#: Zontyper som ingen kropp får tränga in i under zonens fria höjd.
FRIHALLNA = (Zontyp.GANG, Zontyp.UTRYMNINGSVAG, Zontyp.FORBJUDET)


class Rektangel:
    """En axelriktad rektangel i golvplanet, i meter."""

    __slots__ = ("x0_m", "y0_m", "x1_m", "y1_m")

    def __init__(self, x0_m, y0_m, x1_m, y1_m):
        if x1_m <= x0_m or y1_m <= y0_m:
            raise Layoutfel("rektangeln har noll eller negativ utsträckning: "
                            "(%.4g, %.4g) till (%.4g, %.4g)"
                            % (x0_m, y0_m, x1_m, y1_m))
        self.x0_m, self.y0_m, self.x1_m, self.y1_m = (float(x0_m), float(y0_m),
                                                      float(x1_m), float(y1_m))

    @classmethod
    def av(cls, x0, y0, x1, y1):
        """Ur fyra Langd: två motstående hörn."""
        return cls(krav(x0, "x0").som_m, krav(y0, "y0").som_m,
                   krav(x1, "x1").som_m, krav(y1, "y1").som_m)

    @classmethod
    def vid(cls, horn, bredd, djup):
        """Ur ett hörn (Vek2) plus bredd i X och djup i Y."""
        if not isinstance(horn, Vek2):
            raise Enhetsfel("horn måste vara en Vek2")
        b = krav(bredd, "bredd").som_m
        d = krav(djup, "djup").som_m
        return cls(horn.x_m, horn.y_m, horn.x_m + b, horn.y_m + d)

    @property
    def bredd_m(self):
        return self.x1_m - self.x0_m

    @property
    def djup_m(self):
        return self.y1_m - self.y0_m

    @property
    def area_m2(self):
        return self.bredd_m * self.djup_m

    @property
    def mitt_m(self):
        return (0.5 * (self.x0_m + self.x1_m), 0.5 * (self.y0_m + self.y1_m))

    def innehaller(self, x_m, y_m, tol_m=LAGE_TOL_M):
        return (self.x0_m - tol_m <= x_m <= self.x1_m + tol_m
                and self.y0_m - tol_m <= y_m <= self.y1_m + tol_m)

    def omsluter(self, annan, tol_m=LAGE_TOL_M):
        """Ligger hela annan inuti mig?"""
        return (annan.x0_m >= self.x0_m - tol_m
                and annan.y0_m >= self.y0_m - tol_m
                and annan.x1_m <= self.x1_m + tol_m
                and annan.y1_m <= self.y1_m + tol_m)

    def snitt(self, annan):
        """Överlappet som rektangel, eller None."""
        x0 = max(self.x0_m, annan.x0_m)
        y0 = max(self.y0_m, annan.y0_m)
        x1 = min(self.x1_m, annan.x1_m)
        y1 = min(self.y1_m, annan.y1_m)
        if x1 <= x0 or y1 <= y0:
            return None
        return Rektangel(x0, y0, x1, y1)

    def __eq__(self, annan):
        return (isinstance(annan, Rektangel)
                and (self.x0_m, self.y0_m, self.x1_m, self.y1_m)
                == (annan.x0_m, annan.y0_m, annan.x1_m, annan.y1_m))

    def __hash__(self):
        return hash(("Rektangel", self.x0_m, self.y0_m, self.x1_m, self.y1_m))

    def __repr__(self):
        return ("Rektangel(%.4g, %.4g, %.4g, %.4g)"
                % (self.x0_m, self.y0_m, self.x1_m, self.y1_m))


class Zon:
    """Ett namngivet område på golvet med en regel knuten till sig.

    Två höjdmått, och de är AVSIKTLIGT skilda fält. Ett enda "höjd" hade
    burit två storheter och dolt felet i det vanliga fallet, där de råkar
    vara lika:

    * ``fri_hojd`` - hur högt upp zonen ska HÅLLAS FRI. Gäller bara en
      frihållen zon (gång, utrymningsväg, förbjudet område). En transportör
      som korsar över en gång på 2,6 m höjd är tillåten om gången kräver
      2,2 m fritt.
    * ``takhojd`` - hur högt det ÄR i zonen, alltså ett hinder ovanför:
      travers, mezzanin, ventilationstrumma. Gäller alla zontyper och
      begränsar hur högt ett objekt får vara där det står.
    """

    __slots__ = ("namn", "typ", "yta", "fri_hojd_m", "takhojd_m",
                 "minsta_bredd_m")

    def __init__(self, namn, typ, yta, fri_hojd=None, takhojd=None,
                 minsta_bredd=None):
        if not isinstance(typ, Zontyp):
            raise Layoutfel("zontyp måste vara ett Zontyp-värde, fick %r" % (typ,))
        if not isinstance(yta, Rektangel):
            raise Layoutfel("zonens yta måste vara en Rektangel")
        self.namn = str(namn)
        self.typ = typ
        self.yta = yta
        if fri_hojd is not None and typ is Zontyp.ARBETSYTA:
            raise Layoutfel("fri_hojd hör till en frihållen zon; %s är en "
                            "arbetsyta och begränsas av takhojd i stället"
                            % namn)
        # None betyder "hela hallens höjd" och fylls i av Hall vid inläggning.
        self.fri_hojd_m = None if fri_hojd is None else krav(
            fri_hojd, "fri_hojd").som_m
        self.takhojd_m = None if takhojd is None else krav(
            takhojd, "takhojd").som_m
        if minsta_bredd is None:
            self.minsta_bredd_m = None
        else:
            if typ not in (Zontyp.GANG, Zontyp.UTRYMNINGSVAG):
                raise Layoutfel("minsta_bredd hör bara till en gång eller en "
                                "utrymningsväg; %s är %s" % (namn, typ.value))
            self.minsta_bredd_m = krav(minsta_bredd, "minsta_bredd").som_m

    def __repr__(self):
        return "Zon(%r, %s, %r)" % (self.namn, self.typ.value, self.yta)


class Pelare:
    """En pelare. Modelleras som ett fast, låst objekt i scenen."""

    __slots__ = ("namn", "mitt", "tvarsnitt_x", "tvarsnitt_y", "hojd")

    def __init__(self, namn, mitt, tvarsnitt_x, tvarsnitt_y, hojd=None):
        if not isinstance(mitt, Vek2):
            raise Enhetsfel("pelarens mitt måste vara en Vek2")
        self.namn = str(namn)
        self.mitt = mitt
        self.tvarsnitt_x = krav(tvarsnitt_x, "tvarsnitt_x")
        self.tvarsnitt_y = krav(tvarsnitt_y, "tvarsnitt_y")
        # None betyder golv till tak: en pelare bär taket, så den går aldrig
        # att köra över. Hall fyller i hallens höjd.
        self.hojd = None if hojd is None else krav(hojd, "hojd")

    def __repr__(self):
        return "Pelare(%r, %r)" % (self.namn, self.mitt)


class Ankare:
    """Var komponentens EGET origo sitter i förhållande till dess låda.

    Detta är fällan mellan layouten och VC. Layouten vet var fotavtryckets
    mitt ska hamna; ``set_transform`` sätter komponentens origo. Är origo
    inte i fotavtryckets mitt hamnar allt fel, tyst.

    Därför bär varje objekt ett ankare med en STÄMPEL:

    * ``MATT`` - byggt ur ett verkligt svar från verktyget ``get_bounds``,
      alltså ``center`` och ``half_extent`` i nodens egen ram.
    * ``ANTAGEN`` - antagandet "origo ligger i fotavtryckets mitt, på
      underkanten". ``vc_utdata.till_verktygsanrop`` vägrar som förval att
      skriva ett anrop ur ett antaget ankare (fail-closed).
    """

    __slots__ = ("stampel", "mitt_lokal", "halv_lokal")

    MATT = "MATT"
    ANTAGEN = "ANTAGEN"

    def __init__(self, stampel, mitt_lokal, halv_lokal):
        self.stampel = stampel
        self.mitt_lokal = mitt_lokal
        self.halv_lokal = halv_lokal

    @classmethod
    def antagen_mitt_golv(cls):
        """Origo antas ligga i fotavtryckets mitt, på underkanten."""
        return cls(cls.ANTAGEN, Vek3.m(0.0, 0.0, 0.0), Vek3.m(0.0, 0.0, 0.0))

    @classmethod
    def ur_bounds(cls, center_mm, half_extent_mm):
        """Ur get_bounds svar: center och half_extent i millimeter."""
        if len(center_mm) != 3 or len(half_extent_mm) != 3:
            raise Layoutfel("get_bounds ger tre tal per fält")
        return cls(cls.MATT,
                   Vek3.mm(*[float(v) for v in center_mm]),
                   Vek3.mm(*[float(v) for v in half_extent_mm]))

    def forskjutning_lokal_m(self):
        """Vektor från origo till fotavtryckets mitt vid underkanten."""
        return (self.mitt_lokal.x_m, self.mitt_lokal.y_m,
                self.mitt_lokal.z_m - self.halv_lokal.z_m)

    def __repr__(self):
        return "Ankare(%s)" % self.stampel


#: Förvalda tillåtna vridningar_grader. Fyra räta lägen räcker för nästan all
#: fabrikslayout, och en fri vinkel gör sökrummet kontinuerligt. Ett objekt
#: som ska stå snett får sina vinklar angivna uttryckligen.
VRIDNINGAR_RATA = (0.0, 90.0, 180.0, 270.0)


class Objekt:
    """Ett fysiskt objekt med axelriktad utsträckning i sin egen ram."""

    __slots__ = ("namn", "langd", "bredd", "hojd", "underhallsmarginal",
                 "kravd_fri_hojd", "tillatna_vridningar_grader", "barande",
                 "ankare", "kategori", "rackvidd", "enhet")

    def __init__(self, namn, langd, bredd, hojd,
                 underhallsmarginal=None, kravd_fri_hojd=None,
                 tillatna_vridningar_grader=VRIDNINGAR_RATA, barande=False,
                 ankare=None, kategori="", rackvidd=None, enhet=""):
        self.namn = str(namn)
        if not self.namn:
            raise Layoutfel("ett objekt måste ha ett namn")
        self.langd = krav(langd, "langd (utsträckning längs objektets X)")
        self.bredd = krav(bredd, "bredd (utsträckning längs objektets Y)")
        self.hojd = krav(hojd, "hojd")
        for m, vad in ((self.langd, "langd"), (self.bredd, "bredd"),
                       (self.hojd, "hojd")):
            if m.som_m <= 0.0:
                raise Layoutfel("%s för %s måste vara positiv" % (vad, self.namn))
        self.underhallsmarginal = (Langd.noll() if underhallsmarginal is None
                                   else krav(underhallsmarginal,
                                             "underhallsmarginal"))
        if self.underhallsmarginal.som_m < 0.0:
            raise Layoutfel("underhållsmarginalen kan inte vara negativ")
        self.kravd_fri_hojd = (Langd.noll() if kravd_fri_hojd is None
                               else krav(kravd_fri_hojd, "kravd_fri_hojd"))
        vr = tuple(krav_vinkel(v, "vridning") for v in tillatna_vridningar_grader)
        if not vr:
            raise Layoutfel("%s måste ha minst en tillåten vridning" % self.namn)
        # Sorterad och avdubblad: sökordningen ska inte bero på hur listan
        # råkade skrivas. Determinism, uppdragets krav på lösaren.
        self.tillatna_vridningar_grader = tuple(sorted(set(vr)))
        self.barande = bool(barande)
        self.ankare = ankare if ankare is not None else Ankare.antagen_mitt_golv()
        self.kategori = str(kategori)
        self.rackvidd = None if rackvidd is None else krav(rackvidd, "rackvidd")
        # Enheten är cellen objektet hör till. Två objekt i samma enhet kräver
        # inget underhållsutrymme av varandra; se kollision.kravd_separation_m.
        self.enhet = str(enhet)

    @property
    def fotavtryck_area_m2(self):
        return self.langd.som_m * self.bredd.som_m

    def __repr__(self):
        return ("Objekt(%r, %.4g x %.4g x %.4g m)"
                % (self.namn, self.langd.som_m, self.bredd.som_m,
                   self.hojd.som_m))


class Pose:
    """Ett läge: fotavtryckets mitt i X och Y, underkanten i Z, vridning."""

    __slots__ = ("x_m", "y_m", "z_m", "vridning_grader")

    def __init__(self, x_m, y_m, z_m, vridning_grader):
        self.x_m = float(x_m)
        self.y_m = float(y_m)
        self.z_m = float(z_m)
        self.vridning_grader = krav_vinkel(vridning_grader, "vridning_grader")

    @classmethod
    def meter(cls, x_m, y_m, z_m, vridning_grader=0.0):
        """Ur råa float i METER. Enheten står i metodnamnet."""
        return cls(x_m, y_m, z_m, vridning_grader)

    @classmethod
    def av(cls, punkt, vridning_grader=0.0):
        """Ur en Vek3 plus vridning i grader."""
        if not isinstance(punkt, Vek3):
            raise Enhetsfel("pose byggs av en Vek3, fick %r" % (punkt,))
        return cls(punkt.x_m, punkt.y_m, punkt.z_m, vridning_grader)

    @property
    def punkt(self):
        return Vek3.m(self.x_m, self.y_m, self.z_m)

    def nyckel(self):
        """Avrundad nyckel för avdubbling. Sex decimaler i meter är en
        tusendels millimeter, alltså under varje tolerans modellen har."""
        return (round(self.x_m, 6), round(self.y_m, 6), round(self.z_m, 6),
                round(self.vridning_grader, 4))

    def __eq__(self, annan):
        return isinstance(annan, Pose) and self.nyckel() == annan.nyckel()

    def __hash__(self):
        return hash(("Pose",) + self.nyckel())

    def __repr__(self):
        return ("Pose.meter(%.4g, %.4g, %.4g, %.4g)"
                % (self.x_m, self.y_m, self.z_m, self.vridning_grader))


class Kropp:
    """Ett placerat objekts geometri: vriden låda i XY, intervall i Z."""

    __slots__ = ("namn", "mitt_x_m", "mitt_y_m", "halv_x_m", "halv_y_m",
                 "z0_m", "z1_m", "vridning_grader", "marginal_m", "enhet",
                 "_axlar")

    def __init__(self, namn, mitt_x_m, mitt_y_m, halv_x_m, halv_y_m,
                 z0_m, z1_m, vridning_grader, marginal_m=0.0, enhet=""):
        self.namn = namn
        self.mitt_x_m = mitt_x_m
        self.mitt_y_m = mitt_y_m
        self.halv_x_m = halv_x_m
        self.halv_y_m = halv_y_m
        self.z0_m = z0_m
        self.z1_m = z1_m
        self.vridning_grader = vridning_grader
        self.marginal_m = marginal_m
        self.enhet = enhet
        r = math.radians(vridning_grader)
        c, s = math.cos(r), math.sin(r)
        # Objektets lokala X- och Y-axel uttryckta i världen.
        self._axlar = ((c, s), (-s, c))

    @property
    def axlar(self):
        return self._axlar

    def horn(self):
        """De fyra hörnen i världen, moturs från lokal (-x, -y)."""
        (ax, ay), (bx, by) = self._axlar
        hx, hy = self.halv_x_m, self.halv_y_m
        ut = []
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            ut.append((self.mitt_x_m + sx * hx * ax + sy * hy * bx,
                       self.mitt_y_m + sx * hx * ay + sy * hy * by))
        return tuple(ut)

    def aabb(self, marginal_m=0.0):
        """Världens axelriktade omslutande rektangel. Konservativ vid vridning."""
        h = self.horn()
        xs = [p[0] for p in h]
        ys = [p[1] for p in h]
        return Rektangel(min(xs) - marginal_m, min(ys) - marginal_m,
                         max(xs) + marginal_m, max(ys) + marginal_m)

    def __repr__(self):
        return ("Kropp(%r, mitt=(%.4g, %.4g), halv=(%.4g, %.4g), z=%.4g..%.4g,"
                " v=%.4g)" % (self.namn, self.mitt_x_m, self.mitt_y_m,
                              self.halv_x_m, self.halv_y_m, self.z0_m,
                              self.z1_m, self.vridning_grader))


class Hall:
    """Fabrikshallen: golvyta, höjd, zoner och pelare."""

    __slots__ = ("namn", "bredd", "djup", "hojd", "zoner", "pelare", "golv")

    def __init__(self, namn, bredd, djup, hojd, zoner=(), pelare=()):
        self.namn = str(namn)
        self.bredd = krav(bredd, "hallens bredd (X)")
        self.djup = krav(djup, "hallens djup (Y)")
        self.hojd = krav(hojd, "hallens fria höjd")
        if min(self.bredd.som_m, self.djup.som_m, self.hojd.som_m) <= 0.0:
            raise Layoutfel("hallens mått måste vara positiva")
        self.golv = Rektangel(0.0, 0.0, self.bredd.som_m, self.djup.som_m)
        namn_sedda = set()
        zon_lista = []
        for z in zoner:
            if not isinstance(z, Zon):
                raise Layoutfel("zoner måste vara Zon-objekt")
            if z.namn in namn_sedda:
                raise Layoutfel("två zoner heter %r" % z.namn)
            namn_sedda.add(z.namn)
            if not self.golv.omsluter(z.yta):
                raise Layoutfel("zonen %r ligger utanför hallens golv" % z.namn)
            if z.fri_hojd_m is None:
                z.fri_hojd_m = self.hojd.som_m
            if z.fri_hojd_m > self.hojd.som_m + LAGE_TOL_M:
                raise Layoutfel("zonen %r kräver högre fri höjd än hallen har"
                                % z.namn)
            if z.takhojd_m is None:
                z.takhojd_m = self.hojd.som_m
            if z.takhojd_m > self.hojd.som_m + LAGE_TOL_M:
                raise Layoutfel("zonen %r påstår högre tak än hallen har"
                                % z.namn)
            if z.minsta_bredd_m is not None:
                smalast = min(z.yta.bredd_m, z.yta.djup_m)
                if z.minsta_bredd_m > smalast + LAGE_TOL_M:
                    raise Layoutfel(
                        "zonen %r är %.3g m smal men kräver %.3g m fri bredd; "
                        "kravet går inte att uppfylla ens i en tom hall"
                        % (z.namn, smalast, z.minsta_bredd_m))
            zon_lista.append(z)
        self.zoner = tuple(zon_lista)
        pel = []
        for p in pelare:
            if not isinstance(p, Pelare):
                raise Layoutfel("pelare måste vara Pelare-objekt")
            if p.hojd is None:
                p.hojd = self.hojd
            r = Rektangel(p.mitt.x_m - p.tvarsnitt_x.som_m / 2.0,
                          p.mitt.y_m - p.tvarsnitt_y.som_m / 2.0,
                          p.mitt.x_m + p.tvarsnitt_x.som_m / 2.0,
                          p.mitt.y_m + p.tvarsnitt_y.som_m / 2.0)
            if not self.golv.omsluter(r):
                raise Layoutfel("pelaren %r står utanför hallen" % p.namn)
            pel.append(p)
        self.pelare = tuple(pel)

    def zon(self, namn):
        for z in self.zoner:
            if z.namn == namn:
                return z
        raise Layoutfel("hallen %r har ingen zon som heter %r"
                        % (self.namn, namn))

    def vaggens_lage_m(self, vagg):
        """Väggens koordinat och vilken axel den ligger vinkelrätt mot."""
        if vagg is Vagg.VASTER:
            return ("x", 0.0, +1.0)
        if vagg is Vagg.OSTER:
            return ("x", self.bredd.som_m, -1.0)
        if vagg is Vagg.SODER:
            return ("y", 0.0, +1.0)
        if vagg is Vagg.NORR:
            return ("y", self.djup.som_m, -1.0)
        raise Layoutfel("okänd vägg %r" % (vagg,))

    def __repr__(self):
        return ("Hall(%r, %.4g x %.4g x %.4g m, %d zoner, %d pelare)"
                % (self.namn, self.bredd.som_m, self.djup.som_m,
                   self.hojd.som_m, len(self.zoner), len(self.pelare)))


#: Namnprefix för de objekt hallen själv lägger in. Ett användarobjekt får
#: inte heta så, annars går pelaren att skriva över utan att någon märker det.
PELARPREFIX = "pelare:"


class Scen:
    """Hallen plus objekten plus var de står. Håller ingen dom själv."""

    __slots__ = ("hall", "_objekt", "_placering", "_lasta")

    def __init__(self, hall):
        if not isinstance(hall, Hall):
            raise Layoutfel("en scen byggs kring en Hall")
        self.hall = hall
        self._objekt = {}
        self._placering = {}
        self._lasta = set()
        for p in hall.pelare:
            o = Objekt(PELARPREFIX + p.namn, p.tvarsnitt_x, p.tvarsnitt_y,
                       p.hojd, tillatna_vridningar_grader=(0.0,), kategori="pelare")
            self._objekt[o.namn] = o
            self._placering[o.namn] = Pose.meter(p.mitt.x_m, p.mitt.y_m, 0.0, 0.0)
            self._lasta.add(o.namn)

    # ---- innehåll ------------------------------------------------------

    def lagg_till(self, objekt):
        if not isinstance(objekt, Objekt):
            raise Layoutfel("bara Objekt går att lägga i en scen")
        if objekt.namn.startswith(PELARPREFIX):
            raise Layoutfel("namnet %r är reserverat för hallens pelare"
                            % objekt.namn)
        if objekt.namn in self._objekt:
            raise Layoutfel("scenen har redan ett objekt som heter %r"
                            % objekt.namn)
        if objekt.hojd.som_m > self.hall.hojd.som_m:
            raise Layoutfel("%s är %.3g m högt och hallen %.3g m"
                            % (objekt.namn, objekt.hojd.som_m,
                               self.hall.hojd.som_m))
        self._objekt[objekt.namn] = objekt
        return objekt

    def objekt(self, namn):
        try:
            return self._objekt[namn]
        except KeyError:
            raise Layoutfel("scenen har inget objekt som heter %r" % namn)

    def namn(self):
        """Alla objektnamn i inläggningsordning."""
        return tuple(self._objekt)

    def fria_namn(self):
        """Objekt som lösaren får flytta, i inläggningsordning."""
        return tuple(n for n in self._objekt if n not in self._lasta)

    # ---- placering -----------------------------------------------------

    def placera(self, namn, pose, last=False):
        o = self.objekt(namn)
        if not isinstance(pose, Pose):
            raise Layoutfel("placera kräver en Pose")
        if namn in self._lasta:
            raise Layoutfel("%s är låst och går inte att flytta" % namn)
        v = round(pose.vridning_grader, 4)
        if v not in tuple(round(x, 4) for x in o.tillatna_vridningar_grader):
            raise Layoutfel("%s får inte stå vriden %.4g grader; tillåtna är %s"
                            % (namn, pose.vridning_grader,
                               ", ".join("%g" % x for x in o.tillatna_vridningar_grader)))
        self._placering[namn] = pose

    def las(self, namn):
        """Låser ett redan placerat objekt, som en pelare."""
        if namn not in self._placering:
            raise Layoutfel("%s är inte placerat och går inte att låsa" % namn)
        self._lasta.add(namn)

    def ta_bort_placering(self, namn):
        if namn in self._lasta:
            raise Layoutfel("%s är låst" % namn)
        self._placering.pop(namn, None)

    def pose(self, namn):
        return self._placering.get(namn)

    def ar_placerad(self, namn):
        return namn in self._placering

    def placeringar(self):
        """Namn -> Pose i inläggningsordning. Determinism för utdata."""
        return {n: self._placering[n] for n in self._objekt
                if n in self._placering}

    def placerade_namn(self):
        return tuple(n for n in self._objekt if n in self._placering)

    # ---- geometri ------------------------------------------------------

    def kropp(self, namn):
        """Objektets kropp där det står, eller None om det inte är placerat."""
        p = self._placering.get(namn)
        if p is None:
            return None
        return self.kropp_for(namn, p)

    def kropp_for(self, namn, pose):
        """Objektets kropp om det ställdes i pose. Rör inte scenen."""
        o = self.objekt(namn)
        return Kropp(namn, pose.x_m, pose.y_m,
                     o.langd.som_m / 2.0, o.bredd.som_m / 2.0,
                     pose.z_m, pose.z_m + o.hojd.som_m,
                     pose.vridning_grader, o.underhallsmarginal.som_m,
                     o.enhet)

    def kroppar(self):
        return tuple(self.kropp(n) for n in self.placerade_namn())

    # ---- kopiering -----------------------------------------------------

    def kopia(self):
        """Grund kopia: samma Objekt-instanser, egna placeringar.

        Objekten är oföränderliga i praktiken - inget i motorn skriver i
        dem efter konstruktionen - så de delas medvetet. Det gör en
        sökgren billig att förgrena.
        """
        ny = Scen.__new__(Scen)
        ny.hall = self.hall
        ny._objekt = dict(self._objekt)
        ny._placering = dict(self._placering)
        ny._lasta = set(self._lasta)
        return ny

    def __repr__(self):
        return ("Scen(%r, %d objekt, %d placerade)"
                % (self.hall.namn, len(self._objekt), len(self._placering)))
