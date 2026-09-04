# -*- coding: utf-8 -*-
"""Placeringsspråket: de relationer en språkmodell faktiskt uttrycker.

"Bredvid", "framför", "till vänster om", "mot väggen", "i hörnet", "på",
"under", "centrerad i", "i rad med", "med X meters mellanrum".

Varje relation är ett CONSTRAINT, aldrig en färdig koordinat. Den kan två
saker, och skillnaden mellan dem är hela poängen:

* ``prova(scen)`` DÖMER ett läge som redan finns. Den svarar också
  "obestämbar" när något den lutar sig mot inte är placerat ännu, och det är
  ett tredje svar, inte ett tyst ja.
* ``forslag_for(scen, namn, raster_m)`` FÖRESLÅR lägen. Ett förslag är ett
  filter på primitiver, inte en dom om idén: relationen säger var något
  RIMLIGEN kan stå, och lösaren och kollisionskontrollen avgör om det GÅR.

Konventionen för sidorna, ur rum.py: vid vridning 0 grader pekar objektets
framsida mot +X och dess vänstra sida mot +Y. "Framför pressen" betyder
alltså framför PRESSENS framsida, inte "norr om pressen". Det är den enda
läsning som håller när pressen vrids.

Källa: uppdragets punkt 2, docs/spec/90_invarianter.md I8.
"""
from __future__ import annotations

import math
from enum import Enum

from .kollision import avstand_m, radie_langs
from .matt import Enhetsfel, Vek2, Vek3, krav, krav_vinkel
from .rum import Horn, LAGE_TOL_M, Layoutfel, Pose, Rektangel, Vagg

__all__ = ["Sida", "Riktning", "Utfall", "Relation", "FastLage", "Bredvid",
           "Framfor", "Bakom", "TillVanster", "TillHoger", "MotVagg", "IHorn",
           "Pa", "Under", "CentreradI", "IZon", "UtanforZon", "IRad",
           "Mellanrum", "MinstaAvstand", "InomRackvidd",
           "FORSLAGSRASTER_M", "MAX_FORSLAG", "BREDVID_MAX_M"]

# ANTAGET. Sätts av mätning M-20 (layoutmotorns kalibrering), som inte är körd.
# Rastret relationerna föreslår lägen på, 0,25 m. Valt mot sökrummets storlek,
# inte mot geometrin: en hall om 30 x 20 m ger 120 x 80 = 9600 lägen per
# vridning, vilket ryms i lösarens nodbudget. Ett finare raster kostar
# kvadratiskt. Det grövre rastret gör inte lägena osäkra - varje förslag prövas
# exakt av kollisionskontrollen - det gör bara att smala luckor kan missas, och
# ett missat läge är ett nej, inte ett falskt ja.
FORSLAGSRASTER_M = 0.25

# ANTAGET. Sätts av mätning M-20. Tak på antalet förslag EN relation får lämna
# för ETT objekt. 600 räcker för ett fullt väggsvep i en 30 m lång hall vid
# 0,25 m raster (120 lägen) gånger fyra vridningar_grader, med marginal. Taket finns
# för att en enda relation inte ska kunna dränka sökningen.
MAX_FORSLAG = 600

# ANTAGET. Sätts av mätning M-20. Största mellanrum två objekt får ha och ändå
# läsas som "bredvid" när talet inte är angivet. En meter är ungefär en
# gångbredd: står maskinerna längre isär än så beskriver ingen dem som
# bredvid varandra utan som på var sin sida om en gång.
BREDVID_MAX_M = 1.0


class Sida(Enum):
    """Sida räknat i REFERENSENS egen ram."""
    FRAM = "fram"
    BAK = "bak"
    VANSTER = "vanster"
    HOGER = "hoger"


class Riktning(Enum):
    """Väderstreck i hallen, för rader och rutmönster."""
    OSTER = (1.0, 0.0)
    VASTER = (-1.0, 0.0)
    NORR = (0.0, 1.0)
    SODER = (0.0, -1.0)


class Utfall:
    """Domen från en relation över en scen."""

    __slots__ = ("ok", "provbar", "avvikelse_m", "text")

    def __init__(self, ok, provbar, avvikelse_m, text):
        self.ok = bool(ok)
        self.provbar = bool(provbar)
        self.avvikelse_m = float(avvikelse_m)
        self.text = text

    @classmethod
    def uppfylld(cls, text="", avvikelse_m=0.0):
        return cls(True, True, avvikelse_m, text)

    @classmethod
    def bruten(cls, text, avvikelse_m):
        return cls(False, True, avvikelse_m, text)

    @classmethod
    def obestambar(cls, text):
        """Går inte att pröva ännu. Fail-closed: det är INTE ett ja."""
        return cls(False, False, 0.0, text)

    def __repr__(self):
        return ("Utfall(ok=%s, provbar=%s, %.4g m, %r)"
                % (self.ok, self.provbar, self.avvikelse_m, self.text))


# ---- hjälpgeometri -------------------------------------------------------

def _riktning_i_ram(kropp, sida):
    """Enhetsvektorn för en sida i referensens egen ram."""
    (ux, uy), (vx, vy) = kropp.axlar
    if sida is Sida.FRAM:
        return (ux, uy)
    if sida is Sida.BAK:
        return (-ux, -uy)
    if sida is Sida.VANSTER:
        return (vx, vy)
    if sida is Sida.HOGER:
        return (-vx, -vy)
    raise Layoutfel("okänd sida %r" % (sida,))


def _tvarsriktning(riktning):
    return (-riktning[1], riktning[0])


def _proj(kropp_a, kropp_b, axel):
    """Projektionen av vektorn a->b på axeln."""
    return ((kropp_b.mitt_x_m - kropp_a.mitt_x_m) * axel[0]
            + (kropp_b.mitt_y_m - kropp_a.mitt_y_m) * axel[1])


def _tol(tolerans):
    return LAGE_TOL_M if tolerans is None else krav(tolerans, "tolerans").som_m


def _rasterpunkter(rekt, steg_m):
    """Punkter i en rektangel, söderifrån och norrut, västerifrån och österut."""
    nx = max(1, int(math.floor(rekt.bredd_m / steg_m)) + 1)
    ny = max(1, int(math.floor(rekt.djup_m / steg_m)) + 1)
    ut = []
    for j in range(ny):
        y = rekt.y0_m + min(j * steg_m, rekt.djup_m)
        for i in range(nx):
            ut.append((rekt.x0_m + min(i * steg_m, rekt.bredd_m), y))
    return ut


class Relation:
    """Basen. En relation vet vilka objekt den rör och vad den kräver."""

    kod = "RELATION"

    def berorda(self):
        """Alla objektnamn relationen nämner."""
        raise NotImplementedError

    def positionerar(self):
        """Objekt relationen kan föreslå lägen för."""
        return ()

    def beroenden_for(self, namn):
        """Objekt som måste stå på plats innan namn kan föreslås."""
        return ()

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        """Lägen relationen föreslår, i fast ordning, eller None."""
        return None

    def prova(self, scen):
        raise NotImplementedError

    def text(self):
        raise NotImplementedError

    def _kontrollera(self, scen):
        for n in self.berorda():
            scen.objekt(n)  # kastar Layoutfel om namnet inte finns

    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, self.text())


# ---- fast läge -----------------------------------------------------------

class FastLage(Relation):
    """Objektet står där, punkt. Den enda relation som bär en koordinat."""

    kod = "FAST_LAGE"

    def __init__(self, mal, punkt, vridning_grader=0.0):
        self.mal = str(mal)
        if isinstance(punkt, Vek2):
            punkt = Vek3.m(punkt.x_m, punkt.y_m, 0.0)
        if not isinstance(punkt, Vek3):
            raise Enhetsfel("FastLage kräver en Vek2 eller Vek3")
        self.punkt = punkt
        self.vridning_grader = krav_vinkel(vridning_grader, "vridning_grader")

    def berorda(self):
        return (self.mal,)

    def positionerar(self):
        return (self.mal,)

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        return (Pose.av(self.punkt, self.vridning_grader),)

    def prova(self, scen):
        self._kontrollera(scen)
        p = scen.pose(self.mal)
        if p is None:
            return Utfall.obestambar("%s är inte placerat" % self.mal)
        d = math.hypot(p.x_m - self.punkt.x_m, p.y_m - self.punkt.y_m)
        dz = abs(p.z_m - self.punkt.z_m)
        dv = abs((p.vridning_grader - self.vridning_grader + 180.0) % 360.0 - 180.0)
        if max(d, dz) <= LAGE_TOL_M and dv <= 0.1:
            return Utfall.uppfylld(self.text(), max(d, dz))
        return Utfall.bruten("%s står %.1f mm och %.2f grader från sitt fasta "
                             "läge" % (self.mal, max(d, dz) * 1000.0, dv),
                             max(d, dz))

    def text(self):
        return ("%s står fast i (%.3f, %.3f, %.3f) m vriden %.4g grader"
                % (self.mal, self.punkt.x_m, self.punkt.y_m, self.punkt.z_m,
                   self.vridning_grader))


# ---- sidorelationer ------------------------------------------------------

class Sidorelation(Relation):
    """Basen för bredvid, framför, bakom, till vänster och till höger.

    ``mellanrum`` är avståndet mellan de två YTORNA som vetter mot varandra,
    inte mellan mittpunkterna. Utelämnat betyder "intill", alltså ett
    mellanrum mellan noll och BREDVID_MAX_M.
    """

    kod = "SIDA"

    def __init__(self, mal, referens, sidor, mellanrum=None, tolerans=None):
        self.mal = str(mal)
        self.referens = str(referens)
        if self.mal == self.referens:
            raise Layoutfel("%s kan inte stå bredvid sig självt" % self.mal)
        self.sidor = tuple(sidor)
        self.mellanrum_m = (None if mellanrum is None
                            else krav(mellanrum, "mellanrum").som_m)
        if self.mellanrum_m is not None and self.mellanrum_m < 0.0:
            raise Layoutfel("ett mellanrum kan inte vara negativt")
        self.tolerans_m = _tol(tolerans)

    def berorda(self):
        return (self.mal, self.referens)

    def positionerar(self):
        return (self.mal,)

    def beroenden_for(self, namn):
        return (self.referens,) if namn == self.mal else ()

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        ref = scen.kropp(self.referens)
        if ref is None:
            return None
        o = scen.objekt(self.mal)
        z_m = scen.pose(self.referens).z_m
        if self.mellanrum_m is not None:
            luckor = (self.mellanrum_m,)
        else:
            # Intill: noll först, sedan grövre och grövre luft upp till taket.
            n = int(math.floor(BREDVID_MAX_M / raster_m))
            luckor = tuple([0.0] + [(k + 1) * raster_m for k in range(n)])
        ut = []
        for sida in self.sidor:
            axel = _riktning_i_ram(ref, sida)
            tvars = _tvarsriktning(axel)
            r_ref = radie_langs(ref, axel)
            r_ref_t = radie_langs(ref, tvars)
            for vridning in o.tillatna_vridningar_grader:
                prov = scen.kropp_for(self.mal, Pose.meter(0.0, 0.0, z_m, vridning))
                r_mal = radie_langs(prov, axel)
                r_mal_t = radie_langs(prov, tvars)
                # Sidled: mitt för varandra först, sedan symmetriskt utåt så
                # länge de fortfarande överlappar med minst halva bredden.
                grans = max(0.0, (r_ref_t + r_mal_t) * 0.5)
                steg = [0.0]
                k = 1
                while k * raster_m <= grans:
                    steg.extend([k * raster_m, -k * raster_m])
                    k += 1
                for lucka in luckor:
                    langs = r_ref + lucka + r_mal
                    for sido in steg:
                        x = ref.mitt_x_m + axel[0] * langs + tvars[0] * sido
                        y = ref.mitt_y_m + axel[1] * langs + tvars[1] * sido
                        ut.append(Pose.meter(x, y, z_m, vridning))
                        if len(ut) >= MAX_FORSLAG:
                            return tuple(ut)
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        ref = scen.kropp(self.referens)
        mal = scen.kropp(self.mal)
        if ref is None or mal is None:
            return Utfall.obestambar("%s eller %s är inte placerat"
                                     % (self.mal, self.referens))
        bast = None
        for sida in self.sidor:
            axel = _riktning_i_ram(ref, sida)
            tvars = _tvarsriktning(axel)
            langs = _proj(ref, mal, axel)
            lucka = langs - radie_langs(ref, axel) - radie_langs(mal, axel)
            sidled = abs(_proj(ref, mal, tvars))
            overlapp_t = radie_langs(ref, tvars) + radie_langs(mal, tvars) - sidled
            if overlapp_t <= self.tolerans_m:
                fel = ("%s står inte i sidled mitt för %s på sidan %s"
                       % (self.mal, self.referens, sida.value))
                avvik = -overlapp_t
            elif self.mellanrum_m is not None:
                avvik = abs(lucka - self.mellanrum_m)
                fel = ("mellanrummet mellan %s och %s är %.0f mm på sidan %s, "
                       "krävt %.0f mm"
                       % (self.mal, self.referens, lucka * 1000.0, sida.value,
                          self.mellanrum_m * 1000.0))
                if avvik <= self.tolerans_m:
                    return Utfall.uppfylld(self.text(), avvik)
            elif lucka < -self.tolerans_m:
                avvik = -lucka
                fel = ("%s tränger %.0f mm in i %s"
                       % (self.mal, -lucka * 1000.0, self.referens))
            elif lucka > BREDVID_MAX_M:
                avvik = lucka - BREDVID_MAX_M
                fel = ("%s står %.0f mm från %s, för långt för att vara "
                       "bredvid (taket är %.0f mm)"
                       % (self.mal, lucka * 1000.0, self.referens,
                          BREDVID_MAX_M * 1000.0))
            else:
                return Utfall.uppfylld(self.text(), abs(lucka))
            if bast is None or avvik < bast[0]:
                bast = (avvik, fel)
        return Utfall.bruten(bast[1], bast[0])

    def _sidtext(self):
        return " eller ".join(s.value for s in self.sidor)

    def text(self):
        if self.mellanrum_m is None:
            return "%s står %s om %s" % (self.mal, self._sidtext(), self.referens)
        return ("%s står %s om %s med %.0f mm mellanrum"
                % (self.mal, self._sidtext(), self.referens,
                   self.mellanrum_m * 1000.0))


class Bredvid(Sidorelation):
    """Bredvid: höger eller vänster om referensen, båda duger."""

    kod = "BREDVID"

    def __init__(self, mal, referens, mellanrum=None, tolerans=None):
        Sidorelation.__init__(self, mal, referens,
                              (Sida.HOGER, Sida.VANSTER), mellanrum, tolerans)


class Framfor(Sidorelation):
    """Framför referensens framsida."""

    kod = "FRAMFOR"

    def __init__(self, mal, referens, avstand=None, tolerans=None):
        Sidorelation.__init__(self, mal, referens, (Sida.FRAM,), avstand,
                              tolerans)


class Bakom(Sidorelation):
    kod = "BAKOM"

    def __init__(self, mal, referens, avstand=None, tolerans=None):
        Sidorelation.__init__(self, mal, referens, (Sida.BAK,), avstand,
                              tolerans)


class TillVanster(Sidorelation):
    kod = "TILL_VANSTER"

    def __init__(self, mal, referens, avstand=None, tolerans=None):
        Sidorelation.__init__(self, mal, referens, (Sida.VANSTER,), avstand,
                              tolerans)


class TillHoger(Sidorelation):
    kod = "TILL_HOGER"

    def __init__(self, mal, referens, avstand=None, tolerans=None):
        Sidorelation.__init__(self, mal, referens, (Sida.HOGER,), avstand,
                              tolerans)


# ---- mot väggen och i hörnet ---------------------------------------------

def _vaggavstand_m(scen, kropp, vagg):
    """Avståndet från kroppens världslåda till väggen. Negativt = utanför."""
    lada = kropp.aabb()
    axel, koord, inat = scen.hall.vaggens_lage_m(vagg)
    if axel == "x":
        return (lada.x0_m - koord) if inat > 0 else (koord - lada.x1_m)
    return (lada.y0_m - koord) if inat > 0 else (koord - lada.y1_m)


class MotVagg(Relation):
    """Objektet står mot en vägg, med högst ``marginal`` luft emellan."""

    kod = "MOT_VAGG"

    def __init__(self, mal, vagg, marginal=None):
        self.mal = str(mal)
        if not isinstance(vagg, Vagg):
            raise Layoutfel("vagg måste vara ett Vagg-värde, fick %r" % (vagg,))
        self.vagg = vagg
        self.marginal_m = (0.0 if marginal is None
                           else krav(marginal, "marginal").som_m)
        if self.marginal_m < 0.0:
            raise Layoutfel("marginalen mot väggen kan inte vara negativ")

    def berorda(self):
        return (self.mal,)

    def positionerar(self):
        return (self.mal,)

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        o = scen.objekt(self.mal)
        axel, koord, inat = scen.hall.vaggens_lage_m(self.vagg)
        langd_langs = (scen.hall.djup.som_m if axel == "x"
                       else scen.hall.bredd.som_m)
        ut = []
        for vridning in o.tillatna_vridningar_grader:
            prov = scen.kropp_for(self.mal, Pose.meter(0.0, 0.0, 0.0, vridning))
            lada = prov.aabb()
            halv_x, halv_y = lada.bredd_m / 2.0, lada.djup_m / 2.0
            vinkelratt = koord + inat * (self.marginal_m
                                         + (halv_x if axel == "x" else halv_y))
            halv_langs = halv_y if axel == "x" else halv_x
            steg = int(math.floor(max(0.0, langd_langs - 2.0 * halv_langs)
                                  / raster_m)) + 1
            for k in range(steg):
                langs = halv_langs + k * raster_m
                if langs + halv_langs > langd_langs + LAGE_TOL_M:
                    break
                if axel == "x":
                    ut.append(Pose.meter(vinkelratt, langs, 0.0, vridning))
                else:
                    ut.append(Pose.meter(langs, vinkelratt, 0.0, vridning))
                if len(ut) >= MAX_FORSLAG:
                    return tuple(ut)
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        kropp = scen.kropp(self.mal)
        if kropp is None:
            return Utfall.obestambar("%s är inte placerat" % self.mal)
        d = _vaggavstand_m(scen, kropp, self.vagg)
        if d <= self.marginal_m + LAGE_TOL_M:
            return Utfall.uppfylld(self.text(), max(0.0, d))
        return Utfall.bruten("%s står %.0f mm från väggen %s, tillåtet är "
                             "%.0f mm" % (self.mal, d * 1000.0,
                                          self.vagg.value,
                                          self.marginal_m * 1000.0),
                             d - self.marginal_m)

    def text(self):
        return ("%s står mot väggen %s med högst %.0f mm luft"
                % (self.mal, self.vagg.value, self.marginal_m * 1000.0))


_HORNETS_VAGGAR = {
    Horn.SYDVAST: (Vagg.SODER, Vagg.VASTER),
    Horn.SYDOST: (Vagg.SODER, Vagg.OSTER),
    Horn.NORDOST: (Vagg.NORR, Vagg.OSTER),
    Horn.NORDVAST: (Vagg.NORR, Vagg.VASTER),
}


class IHorn(Relation):
    """Objektet står i ett hörn, alltså mot båda dess väggar samtidigt."""

    kod = "I_HORN"

    def __init__(self, mal, horn, marginal=None):
        self.mal = str(mal)
        if not isinstance(horn, Horn):
            raise Layoutfel("horn måste vara ett Horn-värde, fick %r" % (horn,))
        self.horn = horn
        self.marginal_m = (0.0 if marginal is None
                           else krav(marginal, "marginal").som_m)

    def berorda(self):
        return (self.mal,)

    def positionerar(self):
        return (self.mal,)

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        o = scen.objekt(self.mal)
        ut = []
        for vridning in o.tillatna_vridningar_grader:
            prov = scen.kropp_for(self.mal, Pose.meter(0.0, 0.0, 0.0, vridning))
            lada = prov.aabb()
            x = y = None
            for vagg in _HORNETS_VAGGAR[self.horn]:
                axel, koord, inat = scen.hall.vaggens_lage_m(vagg)
                halv = (lada.bredd_m if axel == "x" else lada.djup_m) / 2.0
                v = koord + inat * (self.marginal_m + halv)
                if axel == "x":
                    x = v
                else:
                    y = v
            ut.append(Pose.meter(x, y, 0.0, vridning))
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        kropp = scen.kropp(self.mal)
        if kropp is None:
            return Utfall.obestambar("%s är inte placerat" % self.mal)
        varst = None
        for vagg in _HORNETS_VAGGAR[self.horn]:
            d = _vaggavstand_m(scen, kropp, vagg)
            if varst is None or d > varst[0]:
                varst = (d, vagg)
        if varst[0] <= self.marginal_m + LAGE_TOL_M:
            return Utfall.uppfylld(self.text(), max(0.0, varst[0]))
        return Utfall.bruten("%s står %.0f mm från väggen %s och når därför "
                             "inte hörnet %s"
                             % (self.mal, varst[0] * 1000.0, varst[1].value,
                                self.horn.name.lower()),
                             varst[0] - self.marginal_m)

    def text(self):
        return "%s står i hörnet %s" % (self.mal, self.horn.name.lower())


# ---- på och under --------------------------------------------------------

class Pa(Relation):
    """Objektet står PÅ ett annat. Underlaget måste vara bärande."""

    kod = "PA"

    def __init__(self, mal, underlag):
        self.mal = str(mal)
        self.underlag = str(underlag)
        if self.mal == self.underlag:
            raise Layoutfel("%s kan inte stå på sig självt" % self.mal)

    def berorda(self):
        return (self.mal, self.underlag)

    def positionerar(self):
        return (self.mal,)

    def beroenden_for(self, namn):
        return (self.underlag,) if namn == self.mal else ()

    def _kontrollera(self, scen):
        Relation._kontrollera(self, scen)
        if not scen.objekt(self.underlag).barande:
            raise Layoutfel("%s är inte bärande, så %s kan inte stå på det. "
                            "Sätt barande=True på underlaget om det ska gå."
                            % (self.underlag, self.mal))

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        self._kontrollera(scen)
        under = scen.kropp(self.underlag)
        if under is None:
            return None
        o = scen.objekt(self.mal)
        z_m = under.z1_m
        ut = []
        for vridning in o.tillatna_vridningar_grader:
            prov = scen.kropp_for(self.mal, Pose.meter(0.0, 0.0, z_m, vridning))
            lada = prov.aabb()
            halv_x, halv_y = lada.bredd_m / 2.0, lada.djup_m / 2.0
            yta = under.aabb()
            if (2.0 * halv_x > yta.bredd_m + LAGE_TOL_M
                    or 2.0 * halv_y > yta.djup_m + LAGE_TOL_M):
                continue  # får inte plats på underlaget vid den här vridningen
            # Mitt på först: en låda mitt på en pall är det normala fallet.
            # Sedan de fyra hörnen kant i kant med underlaget. Ett
            # palleteringsmönster börjar alltid i ett hörn, och hörnlägena
            # ligger nästan aldrig på ett raster som utgår från mitten - utan
            # dem blir varje rutmönster falskt överbestämt.
            mx, my = yta.mitt_m
            ut.append(Pose.meter(mx, my, z_m, vridning))
            for hx, hy in ((yta.x0_m + halv_x, yta.y0_m + halv_y),
                           (yta.x1_m - halv_x, yta.y0_m + halv_y),
                           (yta.x0_m + halv_x, yta.y1_m - halv_y),
                           (yta.x1_m - halv_x, yta.y1_m - halv_y)):
                ut.append(Pose.meter(hx, hy, z_m, vridning))
            inre = Rektangel(yta.x0_m + halv_x, yta.y0_m + halv_y,
                             yta.x1_m - halv_x, yta.y1_m - halv_y) \
                if (yta.bredd_m - 2.0 * halv_x > LAGE_TOL_M
                    and yta.djup_m - 2.0 * halv_y > LAGE_TOL_M) else None
            if inre is not None:
                for x, y in _rasterpunkter(inre, raster_m):
                    ut.append(Pose.meter(x, y, z_m, vridning))
                    if len(ut) >= MAX_FORSLAG:
                        return tuple(ut)
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        under = scen.kropp(self.underlag)
        mal = scen.kropp(self.mal)
        if under is None or mal is None:
            return Utfall.obestambar("%s eller %s är inte placerat"
                                     % (self.mal, self.underlag))
        dz = abs(mal.z0_m - under.z1_m)
        if dz > LAGE_TOL_M:
            return Utfall.bruten("%s har underkant på %.3f m och %s överkant "
                                 "på %.3f m; de möts inte"
                                 % (self.mal, mal.z0_m, self.underlag,
                                    under.z1_m), dz)
        yta = under.aabb()
        lada = mal.aabb()
        if not yta.omsluter(lada, tol_m=LAGE_TOL_M):
            over = max(yta.x0_m - lada.x0_m, lada.x1_m - yta.x1_m,
                       yta.y0_m - lada.y0_m, lada.y1_m - yta.y1_m)
            return Utfall.bruten("%s hänger ut %.0f mm utanför %s"
                                 % (self.mal, over * 1000.0, self.underlag),
                                 over)
        return Utfall.uppfylld(self.text(), dz)

    def text(self):
        return "%s står på %s" % (self.mal, self.underlag)


class Under(Relation):
    """Objektet står UNDER ett annat, alltså på golvet i dess skugga."""

    kod = "UNDER"

    def __init__(self, mal, over):
        self.mal = str(mal)
        self.over = str(over)
        if self.mal == self.over:
            raise Layoutfel("%s kan inte stå under sig självt" % self.mal)

    def berorda(self):
        return (self.mal, self.over)

    def positionerar(self):
        return (self.mal,)

    def beroenden_for(self, namn):
        return (self.over,) if namn == self.mal else ()

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        ovan = scen.kropp(self.over)
        if ovan is None:
            return None
        o = scen.objekt(self.mal)
        yta = ovan.aabb()
        mx, my = yta.mitt_m
        ut = []
        for vridning in o.tillatna_vridningar_grader:
            ut.append(Pose.meter(mx, my, 0.0, vridning))
            for x, y in _rasterpunkter(yta, raster_m):
                ut.append(Pose.meter(x, y, 0.0, vridning))
                if len(ut) >= MAX_FORSLAG:
                    return tuple(ut)
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        ovan = scen.kropp(self.over)
        mal = scen.kropp(self.mal)
        if ovan is None or mal is None:
            return Utfall.obestambar("%s eller %s är inte placerat"
                                     % (self.mal, self.over))
        if mal.z1_m > ovan.z0_m + LAGE_TOL_M:
            djup = mal.z1_m - ovan.z0_m
            return Utfall.bruten("%s når %.3f m och %s börjar på %.3f m; de "
                                 "krockar i höjd" % (self.mal, mal.z1_m,
                                                     self.over, ovan.z0_m), djup)
        if ovan.aabb().snitt(mal.aabb()) is None:
            return Utfall.bruten("%s står inte i skuggan av %s"
                                 % (self.mal, self.over), 0.0)
        return Utfall.uppfylld(self.text(), ovan.z0_m - mal.z1_m)

    def text(self):
        return "%s står under %s" % (self.mal, self.over)


# ---- områden -------------------------------------------------------------

def _omradesrektangel(scen, omrade):
    if omrade is None:
        return scen.hall.golv, "hallen"
    if isinstance(omrade, Rektangel):
        return omrade, "området"
    zon = scen.hall.zon(str(omrade))
    return zon.yta, "zonen " + zon.namn


class CentreradI(Relation):
    """Objektets fotavtryck har samma mitt som hallen, en zon eller en yta."""

    kod = "CENTRERAD_I"

    def __init__(self, mal, omrade=None, tolerans=None):
        self.mal = str(mal)
        self.omrade = omrade
        self.tolerans_m = _tol(tolerans)

    def berorda(self):
        return (self.mal,)

    def positionerar(self):
        return (self.mal,)

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        rekt, _ = _omradesrektangel(scen, self.omrade)
        mx, my = rekt.mitt_m
        o = scen.objekt(self.mal)
        return tuple(Pose.meter(mx, my, 0.0, v)
                     for v in o.tillatna_vridningar_grader)

    def prova(self, scen):
        self._kontrollera(scen)
        p = scen.pose(self.mal)
        if p is None:
            return Utfall.obestambar("%s är inte placerat" % self.mal)
        rekt, vad = _omradesrektangel(scen, self.omrade)
        mx, my = rekt.mitt_m
        d = math.hypot(p.x_m - mx, p.y_m - my)
        if d <= self.tolerans_m:
            return Utfall.uppfylld(self.text(), d)
        return Utfall.bruten("%s står %.0f mm från mitten av %s"
                             % (self.mal, d * 1000.0, vad), d)

    def text(self):
        vad = "hallen" if self.omrade is None else str(self.omrade)
        return "%s är centrerad i %s" % (self.mal, vad)


class IZon(Relation):
    """Hela objektets fotavtryck ligger inne i en namngiven zon."""

    kod = "I_ZON"

    def __init__(self, mal, zon):
        self.mal = str(mal)
        self.zon = str(zon)

    def berorda(self):
        return (self.mal,)

    def positionerar(self):
        return (self.mal,)

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        yta = scen.hall.zon(self.zon).yta
        o = scen.objekt(self.mal)
        ut = []
        for vridning in o.tillatna_vridningar_grader:
            prov = scen.kropp_for(self.mal, Pose.meter(0.0, 0.0, 0.0, vridning))
            lada = prov.aabb()
            hx, hy = lada.bredd_m / 2.0, lada.djup_m / 2.0
            if 2.0 * hx > yta.bredd_m + LAGE_TOL_M or 2.0 * hy > yta.djup_m + LAGE_TOL_M:
                continue
            inre = Rektangel(yta.x0_m + hx, yta.y0_m + hy,
                             max(yta.x0_m + hx + LAGE_TOL_M, yta.x1_m - hx),
                             max(yta.y0_m + hy + LAGE_TOL_M, yta.y1_m - hy))
            for x, y in _rasterpunkter(inre, raster_m):
                ut.append(Pose.meter(x, y, 0.0, vridning))
                if len(ut) >= MAX_FORSLAG:
                    return tuple(ut)
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        kropp = scen.kropp(self.mal)
        if kropp is None:
            return Utfall.obestambar("%s är inte placerat" % self.mal)
        yta = scen.hall.zon(self.zon).yta
        lada = kropp.aabb()
        if yta.omsluter(lada, tol_m=LAGE_TOL_M):
            return Utfall.uppfylld(self.text(), 0.0)
        over = max(yta.x0_m - lada.x0_m, lada.x1_m - yta.x1_m,
                   yta.y0_m - lada.y0_m, lada.y1_m - yta.y1_m)
        return Utfall.bruten("%s sticker ut %.0f mm ur zonen %s"
                             % (self.mal, over * 1000.0, self.zon), over)

    def text(self):
        return "%s ligger helt i zonen %s" % (self.mal, self.zon)


class UtanforZon(Relation):
    """Objektet rör inte en namngiven zon alls. Rent filter, inget förslag."""

    kod = "UTANFOR_ZON"

    def __init__(self, mal, zon):
        self.mal = str(mal)
        self.zon = str(zon)

    def berorda(self):
        return (self.mal,)

    def prova(self, scen):
        self._kontrollera(scen)
        kropp = scen.kropp(self.mal)
        if kropp is None:
            return Utfall.obestambar("%s är inte placerat" % self.mal)
        yta = scen.hall.zon(self.zon).yta
        snitt = yta.snitt(kropp.aabb())
        if snitt is None:
            return Utfall.uppfylld(self.text(), 0.0)
        return Utfall.bruten("%s tränger in %.2f m2 i zonen %s"
                             % (self.mal, snitt.area_m2, self.zon),
                             snitt.area_m2)

    def text(self):
        return "%s står utanför zonen %s" % (self.mal, self.zon)


# ---- rad, mellanrum och räckvidd ----------------------------------------

class IRad(Relation):
    """Objekten står i en rad åt ett väderstreck, med givet mellanrum.

    Det här är både "i rad med" och "med X meters mellanrum": ett rutmönster
    av pallar är en rad österut och en rad norrut, och ett mellanrum utan rad
    är en rad om två objekt.

    Mellanrummet mäts mellan de ytor som vetter mot varandra, och raden mäts
    i den ordning objekten står i listan.
    """

    kod = "I_RAD"

    def __init__(self, objekt, riktning, mellanrum, tolerans=None):
        self.objekt = tuple(str(n) for n in objekt)
        if len(self.objekt) < 2:
            raise Layoutfel("en rad behöver minst två objekt")
        if len(set(self.objekt)) != len(self.objekt):
            raise Layoutfel("samma objekt står två gånger i raden")
        if not isinstance(riktning, Riktning):
            raise Layoutfel("riktning måste vara ett Riktning-värde")
        self.riktning = riktning
        self.mellanrum_m = krav(mellanrum, "mellanrum").som_m
        if self.mellanrum_m < 0.0:
            raise Layoutfel("ett mellanrum kan inte vara negativt")
        self.tolerans_m = _tol(tolerans)

    def berorda(self):
        return self.objekt

    def positionerar(self):
        return self.objekt[1:]

    def beroenden_for(self, namn):
        if namn in self.objekt[1:]:
            return (self.objekt[self.objekt.index(namn) - 1],)
        return ()

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn not in self.objekt[1:]:
            return None
        forra = self.objekt[self.objekt.index(namn) - 1]
        ref = scen.kropp(forra)
        if ref is None:
            return None
        axel = self.riktning.value
        o = scen.objekt(namn)
        z_m = scen.pose(forra).z_m
        # Föregående objekts vridning först: en rad brukar ha samma vridning
        # hela vägen, och ordningen ska vara förutsägbar.
        vridningar_grader = [ref.vridning_grader] if any(
            abs(v - ref.vridning_grader) < 1e-9 for v in o.tillatna_vridningar_grader) else []
        vridningar_grader += [v for v in o.tillatna_vridningar_grader if v not in vridningar_grader]
        ut = []
        for vridning in vridningar_grader:
            prov = scen.kropp_for(namn, Pose.meter(0.0, 0.0, z_m, vridning))
            langs = (radie_langs(ref, axel) + self.mellanrum_m
                     + radie_langs(prov, axel))
            # Sidled ligger raden fast: mittpunkterna står på samma linje,
            # alltså ingen förskjutning tvärs riktningen.
            x = ref.mitt_x_m + axel[0] * langs
            y = ref.mitt_y_m + axel[1] * langs
            ut.append(Pose.meter(x, y, z_m, vridning))
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        kroppar = [scen.kropp(n) for n in self.objekt]
        if any(k is None for k in kroppar):
            saknas = [n for n, k in zip(self.objekt, kroppar) if k is None]
            return Utfall.obestambar("dessa står inte: " + ", ".join(saknas))
        axel = self.riktning.value
        tvars = _tvarsriktning(axel)
        varst = 0.0
        for i in range(len(kroppar) - 1):
            a, b = kroppar[i], kroppar[i + 1]
            lucka = (_proj(a, b, axel) - radie_langs(a, axel)
                     - radie_langs(b, axel))
            avvik = abs(lucka - self.mellanrum_m)
            if avvik > self.tolerans_m:
                return Utfall.bruten(
                    "mellanrummet mellan %s och %s är %.0f mm, krävt %.0f mm"
                    % (a.namn, b.namn, lucka * 1000.0,
                       self.mellanrum_m * 1000.0), avvik)
            sidled = abs(_proj(a, b, tvars))
            if sidled > self.tolerans_m:
                return Utfall.bruten(
                    "%s står %.0f mm vid sidan av raden genom %s"
                    % (b.namn, sidled * 1000.0, a.namn), sidled)
            varst = max(varst, avvik, sidled)
        return Utfall.uppfylld(self.text(), varst)

    def text(self):
        return ("%s står i rad åt %s med %.0f mm mellanrum"
                % (", ".join(self.objekt), self.riktning.name.lower(),
                   self.mellanrum_m * 1000.0))


class Mellanrum(Relation):
    """Exakt fritt avstånd mellan två objekt, oavsett i vilken riktning.

    Rent filter. Riktningen är inte given, så relationen kan inte föreslå ett
    läge - den kan bara döma ett. Vill man ha en riktning finns Framfor,
    TillHoger och IRad.
    """

    kod = "MELLANRUM"

    def __init__(self, a, b, avstand, tolerans=None):
        self.a, self.b = str(a), str(b)
        if self.a == self.b:
            raise Layoutfel("ett mellanrum går mellan två olika objekt")
        self.avstand_m = krav(avstand, "avstand").som_m
        self.tolerans_m = _tol(tolerans)

    def berorda(self):
        return (self.a, self.b)

    def prova(self, scen):
        self._kontrollera(scen)
        ka, kb = scen.kropp(self.a), scen.kropp(self.b)
        if ka is None or kb is None:
            return Utfall.obestambar("%s eller %s är inte placerat"
                                     % (self.a, self.b))
        d = avstand_m(ka, kb)
        avvik = abs(d - self.avstand_m)
        if avvik <= self.tolerans_m:
            return Utfall.uppfylld(self.text(), avvik)
        return Utfall.bruten("avståndet mellan %s och %s är %.0f mm, krävt "
                             "%.0f mm" % (self.a, self.b, d * 1000.0,
                                          self.avstand_m * 1000.0), avvik)

    def text(self):
        return ("%s och %s har %.0f mm mellanrum"
                % (self.a, self.b, self.avstand_m * 1000.0))


class MinstaAvstand(Relation):
    """Minst så här långt mellan två objekt. Rent filter."""

    kod = "MINSTA_AVSTAND"

    def __init__(self, a, b, avstand):
        self.a, self.b = str(a), str(b)
        if self.a == self.b:
            raise Layoutfel("ett avstånd går mellan två olika objekt")
        self.avstand_m = krav(avstand, "avstand").som_m

    def berorda(self):
        return (self.a, self.b)

    def prova(self, scen):
        self._kontrollera(scen)
        ka, kb = scen.kropp(self.a), scen.kropp(self.b)
        if ka is None or kb is None:
            return Utfall.obestambar("%s eller %s är inte placerat"
                                     % (self.a, self.b))
        d = avstand_m(ka, kb)
        if d >= self.avstand_m - LAGE_TOL_M:
            return Utfall.uppfylld(self.text(), d - self.avstand_m)
        return Utfall.bruten("%s och %s står %.0f mm isär, minst %.0f mm krävs"
                             % (self.a, self.b, d * 1000.0,
                                self.avstand_m * 1000.0),
                             self.avstand_m - d)

    def text(self):
        return ("%s och %s står minst %.0f mm isär"
                % (self.a, self.b, self.avstand_m * 1000.0))


class InomRackvidd(Relation):
    """Objektet ligger inom robotens arbetsradie.

    ``helt=True`` (förvalt) kräver att HELA fotavtrycket ligger inne, alltså
    att robotens hand når varje punkt på det. Det är den hårda läsningen och
    den enda som håller när greppunkten inte är känd. ``helt=False`` kräver
    bara att någon del når in, vilket är rätt för ett långt band där bara
    plockläget behöver nås.

    Radien tas ur robotens ``rackvidd`` om den inte anges. Banken bär den för
    varje robot, ur tillverkarens publicerade datablad.
    """

    kod = "INOM_RACKVIDD"

    def __init__(self, mal, robot, radie=None, helt=True):
        self.mal = str(mal)
        self.robot = str(robot)
        if self.mal == self.robot:
            raise Layoutfel("roboten når trivialt sig själv")
        self.radie_m = None if radie is None else krav(radie, "radie").som_m
        self.helt = bool(helt)

    def berorda(self):
        return (self.mal, self.robot)

    def positionerar(self):
        return (self.mal,)

    def beroenden_for(self, namn):
        return (self.robot,) if namn == self.mal else ()

    def _radie(self, scen):
        if self.radie_m is not None:
            return self.radie_m
        o = scen.objekt(self.robot)
        if o.rackvidd is None:
            raise Layoutfel("%s bär ingen räckvidd och InomRackvidd fick "
                            "ingen radie; gissa aldrig en räckvidd" % self.robot)
        return o.rackvidd.som_m

    def _matt_m(self, scen, kropp, mitt):
        """Avståndet som ska prövas: längst bort, eller närmast."""
        horn = kropp.horn()
        avstand = [math.hypot(x - mitt[0], y - mitt[1]) for x, y in horn]
        return max(avstand) if self.helt else min(avstand)

    def forslag_for(self, scen, namn, raster_m=FORSLAGSRASTER_M):
        if namn != self.mal:
            return None
        robot = scen.kropp(self.robot)
        if robot is None:
            return None
        r = self._radie(scen)
        mitt = (robot.mitt_x_m, robot.mitt_y_m)
        ruta = Rektangel(mitt[0] - r, mitt[1] - r, mitt[0] + r, mitt[1] + r)
        o = scen.objekt(self.mal)
        ut = []
        for vridning in o.tillatna_vridningar_grader:
            for x, y in _rasterpunkter(ruta, raster_m):
                pose = Pose.meter(x, y, 0.0, vridning)
                if self._matt_m(scen, scen.kropp_for(self.mal, pose), mitt) <= r:
                    ut.append(pose)
                    if len(ut) >= MAX_FORSLAG:
                        return tuple(ut)
        return tuple(ut)

    def prova(self, scen):
        self._kontrollera(scen)
        robot = scen.kropp(self.robot)
        mal = scen.kropp(self.mal)
        if robot is None or mal is None:
            return Utfall.obestambar("%s eller %s är inte placerat"
                                     % (self.mal, self.robot))
        r = self._radie(scen)
        d = self._matt_m(scen, mal, (robot.mitt_x_m, robot.mitt_y_m))
        if d <= r + LAGE_TOL_M:
            return Utfall.uppfylld(self.text(), r - d)
        return Utfall.bruten("%s ligger %.0f mm från %s, som når %.0f mm"
                             % (self.mal, d * 1000.0, self.robot, r * 1000.0),
                             d - r)

    def text(self):
        vad = "helt" if self.helt else "delvis"
        radie = ("robotens räckvidd" if self.radie_m is None
                 else "%.0f mm" % (self.radie_m * 1000.0))
        return ("%s ligger %s inom %s från %s"
                % (self.mal, vad, radie, self.robot))
