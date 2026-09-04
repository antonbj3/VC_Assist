# -*- coding: utf-8 -*-
"""Enheter. En längd utan enhet går inte att bygga.

Kravet ur uppdraget är att det ska vara OMÖJLIGT att blanda ihop millimeter
och meter, och att skyddet ska ligga i typerna, inte i en kommentar. Därför:

* ``Langd`` bär meter internt och går bara att skapa genom ``Langd.m(...)``
  eller ``Langd.mm(...)``. Direktanropet ``Langd(1.2)`` kastar ``Enhetsfel``.
* Varje publik konstruktor i ``rum.py`` och ``relationer.py`` kräver ``Langd``
  och avvisar ett bart tal med ``Enhetsfel``, via ``krav()`` här.
* Motorns inre räknar i ``float`` meter. Övergången sker på ETT ställe per
  typ, i konstruktorn, och attributen som bär råa meter heter ``*_m``.
  Attribut som bär millimeter heter ``*_mm``. Ett attribut utan suffix bär
  aldrig ett tal med längdenhet.

Vinklar är grader genomgående och parametrar som bär en vinkel heter
``*_grader``. Det provas mekaniskt i tests/enhet/test_layout.py, så
disciplinen inte kan glida.

Källa: docs/spec/96_ingen_skuld.md S6 (inget tal utan härkomst) och
uppdragets punkt 1.
"""
from __future__ import annotations

import math

__all__ = ["Enhetsfel", "Langd", "Vek2", "Vek3", "krav", "krav_vinkel",
           "area_m2", "MM_PER_M"]

MM_PER_M = 1000.0  # SI-definitionen. Enda stället omräkningen står skriven.

_LOSEN = object()  # gör Langd(...) direkt omöjlig utanför modulens egna fabriker


class Enhetsfel(TypeError):
    """Ett tal utan enhet, eller fel enhetstyp, där en längd krävdes."""


class Langd:
    """En längd. Bär meter internt, byggs bara ur en namngiven enhet."""

    __slots__ = ("_m",)

    def __init__(self, meter, _losen=None):
        if _losen is not _LOSEN:
            raise Enhetsfel(
                "Langd byggs med Langd.m(x) eller Langd.mm(x), aldrig direkt. "
                "Ett bart tal bär ingen enhet och får inte bli en längd.")
        v = float(meter)
        if math.isnan(v) or math.isinf(v):
            raise Enhetsfel("en längd får inte vara NaN eller oändlig")
        self._m = v

    # ---- fabriker ------------------------------------------------------

    @classmethod
    def m(cls, varde):
        """Längd angiven i meter."""
        return cls(varde, _LOSEN)

    @classmethod
    def mm(cls, varde):
        """Längd angiven i millimeter. Bankens mått kommer i den här enheten."""
        return cls(float(varde) / MM_PER_M, _LOSEN)

    @classmethod
    def noll(cls):
        return cls(0.0, _LOSEN)

    # ---- avläsning -----------------------------------------------------

    @property
    def som_m(self):
        """Längden som float i meter. Motorns inre enhet."""
        return self._m

    @property
    def som_mm(self):
        """Längden som float i millimeter. VC:s enhet (se verktyg/scen.py)."""
        return self._m * MM_PER_M

    # ---- räkning -------------------------------------------------------

    def __add__(self, annan):
        return Langd.m(self._m + krav(annan, "term").som_m)

    def __sub__(self, annan):
        return Langd.m(self._m - krav(annan, "term").som_m)

    def __mul__(self, faktor):
        if isinstance(faktor, Langd):
            raise Enhetsfel("längd gånger längd är en yta, inte en längd; "
                            "använd area_m2()")
        return Langd.m(self._m * float(faktor))

    __rmul__ = __mul__

    def __truediv__(self, namnare):
        if isinstance(namnare, Langd):
            return self._m / namnare.som_m  # kvot mellan längder är enhetslös
        return Langd.m(self._m / float(namnare))

    def __neg__(self):
        return Langd.m(-self._m)

    def __abs__(self):
        return Langd.m(abs(self._m))

    # ---- jämförelse ----------------------------------------------------

    def __eq__(self, annan):
        return isinstance(annan, Langd) and self._m == annan._m

    def __ne__(self, annan):
        return not self.__eq__(annan)

    def __lt__(self, annan):
        return self._m < krav(annan, "jämförelse").som_m

    def __le__(self, annan):
        return self._m <= krav(annan, "jämförelse").som_m

    def __gt__(self, annan):
        return self._m > krav(annan, "jämförelse").som_m

    def __ge__(self, annan):
        return self._m >= krav(annan, "jämförelse").som_m

    def __hash__(self):
        return hash(("Langd", self._m))

    def __repr__(self):
        return "Langd.m(%.6g)  # = %.4g mm" % (self._m, self.som_mm)


def krav(varde, vad):
    """Kräver en Langd. Ett bart tal är ett fel, inte en tolkning."""
    if isinstance(varde, Langd):
        return varde
    raise Enhetsfel(
        "%s måste vara en Langd, fick %r av typen %s. "
        "Skriv Langd.mm(1200) eller Langd.m(1.2) - talet ensamt säger inte "
        "vilken enhet det bär." % (vad, varde, type(varde).__name__))


def krav_vinkel(varde, vad):
    """Kräver en vinkel i GRADER som float. Normaliserar till [0, 360)."""
    if isinstance(varde, Langd):
        raise Enhetsfel("%s är en vinkel i grader, inte en längd" % vad)
    try:
        v = float(varde)
    except (TypeError, ValueError):
        raise Enhetsfel("%s måste vara ett tal i grader, fick %r" % (vad, varde))
    if math.isnan(v) or math.isinf(v):
        raise Enhetsfel("%s får inte vara NaN eller oändlig" % vad)
    return v % 360.0


def area_m2(a, b):
    """Ytan av två längder, i kvadratmeter. Namnet bär enheten."""
    return krav(a, "sida a").som_m * krav(b, "sida b").som_m


class Vek2:
    """En punkt eller vektor i golvplanet."""

    __slots__ = ("x_m", "y_m")

    def __init__(self, x, y):
        self.x_m = krav(x, "x").som_m
        self.y_m = krav(y, "y").som_m

    @classmethod
    def mm(cls, x, y):
        return cls(Langd.mm(x), Langd.mm(y))

    @classmethod
    def m(cls, x, y):
        return cls(Langd.m(x), Langd.m(y))

    @property
    def x(self):
        return Langd.m(self.x_m)

    @property
    def y(self):
        return Langd.m(self.y_m)

    def __eq__(self, annan):
        return (isinstance(annan, Vek2)
                and self.x_m == annan.x_m and self.y_m == annan.y_m)

    def __hash__(self):
        return hash(("Vek2", self.x_m, self.y_m))

    def __repr__(self):
        return "Vek2.m(%.6g, %.6g)" % (self.x_m, self.y_m)


class Vek3:
    """En punkt eller vektor i rummet. Z är uppåt."""

    __slots__ = ("x_m", "y_m", "z_m")

    def __init__(self, x, y, z):
        self.x_m = krav(x, "x").som_m
        self.y_m = krav(y, "y").som_m
        self.z_m = krav(z, "z").som_m

    @classmethod
    def mm(cls, x, y, z):
        return cls(Langd.mm(x), Langd.mm(y), Langd.mm(z))

    @classmethod
    def m(cls, x, y, z):
        return cls(Langd.m(x), Langd.m(y), Langd.m(z))

    @property
    def x(self):
        return Langd.m(self.x_m)

    @property
    def y(self):
        return Langd.m(self.y_m)

    @property
    def z(self):
        return Langd.m(self.z_m)

    def som_mm_lista(self):
        """[x, y, z] i millimeter, formen verktyget set_transform vill ha."""
        return [self.x_m * MM_PER_M, self.y_m * MM_PER_M, self.z_m * MM_PER_M]

    def __eq__(self, annan):
        return (isinstance(annan, Vek3) and self.x_m == annan.x_m
                and self.y_m == annan.y_m and self.z_m == annan.z_m)

    def __hash__(self):
        return hash(("Vek3", self.x_m, self.y_m, self.z_m))

    def __repr__(self):
        return "Vek3.m(%.6g, %.6g, %.6g)" % (self.x_m, self.y_m, self.z_m)
