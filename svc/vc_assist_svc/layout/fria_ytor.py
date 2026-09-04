# -*- coding: utf-8 -*-
"""Fria ytor: vad som är ledigt, och var något får plats.

Det här är frågan en språkmodell ställer när den ska lägga till något i en
befintlig scen: "finns det plats för en pall till, och i så fall var?"

Rasterkartan är AVSIKTLIGT konservativ. En cell räknas som ledig bara om HELA
cellen är ledig, och ett hinder spärrar varje cell dess omslutande låda rör
vid. Den lediga ytan blir därför aldrig större än den verkliga, bara mindre.
Åt det hållet ska felet luta: ett nej som var onödigt kostar en placering, ett
ja som var fel kostar en kollision i VC.

Rasterkartan FÖRESLÅR bara. Varje läge den lämnar ifrån sig prövas exakt av
``kollision.provplacera`` innan det räknas som svar.

Passagebredder mäts INTE här. De mäts analytiskt i ``kollision.fri_bredd_m``,
där snitten läggs vid hindrens egna kanter i stället för på ett raster. Den
rastrerade varianten fanns här tidigare och är borttagen, inte etiketterad
(docs/spec/96_ingen_skuld.md S4).

Källa: uppdragets punkt 5.
"""
from __future__ import annotations

import math

from .kollision import provplacera
from .matt import krav
from .rum import (FRIHALLNA, LAGE_TOL_M, Layoutfel, Objekt, Pose, Rektangel,
                  Scen)

__all__ = ["RASTER_M", "Rasterkarta", "storsta_lediga_rektangel",
           "far_plats", "ledig_area_m2"]

# ANTAGET. Sätts av mätning M-20 (layoutmotorns kalibrering), som inte är körd.
# Valt till 50 mm, en sjättedel av det minsta objektmått banken innehåller
# (VDA KLT 4147, kortsidan 300 mm, bank/katalog_index.json). Varje objekt
# täcker då minst sex celler per axel, så den konservativa avrundningen kostar
# högst en sjättedel av det minsta objektet i varje riktning. Ett finare
# raster kostar kvadratiskt i minne och tid.
RASTER_M = 0.05

# ANTAGET. Sätts av mätning M-20. Taket på antalet celler i en rasterkarta.
# 4 000 000 celler är en hall om 50 x 50 m vid 25 mm raster, alltså mer än
# någon fabrikshall i banken behöver. Passeras taket grovnar rastret, och
# grovningen RAPPORTERAS i kartans stämpel i stället för att ske tyst.
MAX_CELLER = 4000000


class Rasterkarta:
    """En binär karta över vad som är ledigt på en given höjd.

    ``hojd_m`` är höjden på det man vill ställa där, räknat från golvet. Ett
    hinder spärrar en cell bara om det finns i höjdintervallet (0, hojd_m).
    En travers på 4 m spärrar därför ingen golvyta för en 1 m hög pall, men
    zonens takhöjd spärrar den för en 5 m hög ställning.
    """

    __slots__ = ("scen", "omrade", "hojd_m", "nx", "ny", "dx_m", "dy_m",
                 "_ledig", "_prefix", "raster_m", "grovnad", "bortse_fran")

    def __init__(self, scen, hojd_m, raster_m=None, omrade=None,
                 bortse_fran=(), extra_marginal_m=0.0,
                 undvik_zontyper=FRIHALLNA):
        if not isinstance(scen, Scen):
            raise Layoutfel("Rasterkarta byggs över en Scen")
        self.scen = scen
        self.omrade = omrade if omrade is not None else scen.hall.golv
        self.hojd_m = float(hojd_m)
        self.bortse_fran = frozenset(bortse_fran)
        steg = RASTER_M if raster_m is None else krav(raster_m, "raster_m").som_m
        if steg <= 0.0:
            raise Layoutfel("rastret måste vara positivt")
        self.grovnad = 1.0
        nx = max(1, int(math.ceil(self.omrade.bredd_m / steg)))
        ny = max(1, int(math.ceil(self.omrade.djup_m / steg)))
        if nx * ny > MAX_CELLER:
            # Grovna tills kartan ryms, och behåll faktorn så att den som
            # läser kartan ser att den blivit grövre.
            faktor = math.sqrt(float(nx * ny) / MAX_CELLER)
            steg = steg * faktor
            self.grovnad = faktor
            nx = max(1, int(math.ceil(self.omrade.bredd_m / steg)))
            ny = max(1, int(math.ceil(self.omrade.djup_m / steg)))
        self.raster_m = steg
        self.nx, self.ny = nx, ny
        # Cellerna täcker området EXAKT. Ett raster som tappar en remsa vid
        # östra väggen hade gjort varje väggnära placering omöjlig att hitta.
        self.dx_m = self.omrade.bredd_m / nx
        self.dy_m = self.omrade.djup_m / ny
        self._ledig = [True] * (nx * ny)
        self._spar_hinder(bortse_fran, extra_marginal_m, undvik_zontyper)
        self._prefix = self._bygg_prefix()

    # ---- uppbyggnad ----------------------------------------------------

    def _index(self, i, j):
        return j * self.nx + i

    def _spann(self, rekt):
        """Cellindex som rektangeln rör vid. Utåtavrundat, alltså konservativt."""
        i0 = int(math.floor((rekt.x0_m - self.omrade.x0_m + LAGE_TOL_M) / self.dx_m))
        i1 = int(math.ceil((rekt.x1_m - self.omrade.x0_m - LAGE_TOL_M) / self.dx_m))
        j0 = int(math.floor((rekt.y0_m - self.omrade.y0_m + LAGE_TOL_M) / self.dy_m))
        j1 = int(math.ceil((rekt.y1_m - self.omrade.y0_m - LAGE_TOL_M) / self.dy_m))
        return (max(0, i0), min(self.nx, i1), max(0, j0), min(self.ny, j1))

    def _spar_omrade(self, rekt):
        i0, i1, j0, j1 = self._spann(rekt)
        for j in range(j0, j1):
            bas = j * self.nx
            for i in range(i0, i1):
                self._ledig[bas + i] = False

    def _spar_hinder(self, bortse_fran, extra_marginal_m, undvik_zontyper):
        hoppa = set(bortse_fran)
        for namn in self.scen.placerade_namn():
            if namn in hoppa:
                continue
            kropp = self.scen.kropp(namn)
            # Höjdfiltret: bara det som finns i intervallet (0, hojd_m) står
            # i vägen för något som ställs på golvet.
            if kropp.z0_m >= self.hojd_m - LAGE_TOL_M:
                continue
            if kropp.z1_m <= LAGE_TOL_M:
                continue
            self._spar_omrade(kropp.aabb(kropp.marginal_m + extra_marginal_m))
        for zon in self.scen.hall.zoner:
            if zon.typ in undvik_zontyper and zon.fri_hojd_m > LAGE_TOL_M:
                self._spar_omrade(zon.yta)
            if zon.takhojd_m is not None and zon.takhojd_m < self.hojd_m - LAGE_TOL_M:
                self._spar_omrade(zon.yta)
        # Utanför hallen är inget ledigt, även om området råkar sträcka sig dit.
        golv = self.scen.hall.golv
        for j in range(self.ny):
            for i in range(self.nx):
                if not self._ledig[self._index(i, j)]:
                    continue
                r = self.cell(i, j)
                if not golv.omsluter(r, tol_m=LAGE_TOL_M):
                    self._ledig[self._index(i, j)] = False

    def _bygg_prefix(self):
        """Summan av SPÄRRADE celler, så att en fönsterfråga blir O(1)."""
        nx, ny = self.nx, self.ny
        p = [0] * ((nx + 1) * (ny + 1))
        for j in range(ny):
            rad = 0
            for i in range(nx):
                rad += 0 if self._ledig[self._index(i, j)] else 1
                p[(j + 1) * (nx + 1) + (i + 1)] = p[j * (nx + 1) + (i + 1)] + rad
        return p

    # ---- avläsning -----------------------------------------------------

    def cell(self, i, j):
        return Rektangel(self.omrade.x0_m + i * self.dx_m,
                         self.omrade.y0_m + j * self.dy_m,
                         self.omrade.x0_m + (i + 1) * self.dx_m,
                         self.omrade.y0_m + (j + 1) * self.dy_m)

    def ledig(self, i, j):
        if not (0 <= i < self.nx and 0 <= j < self.ny):
            return False
        return self._ledig[self._index(i, j)]

    def antal_lediga(self):
        return sum(1 for v in self._ledig if v)

    def area_m2(self):
        return self.antal_lediga() * self.dx_m * self.dy_m

    def fonster_ledigt(self, i0, j0, bredd, hojd):
        """Är hela cellfönstret ledigt? O(1) via prefixsumman."""
        if i0 < 0 or j0 < 0 or i0 + bredd > self.nx or j0 + hojd > self.ny:
            return False
        nx1 = self.nx + 1
        p = self._prefix
        sperr = (p[(j0 + hojd) * nx1 + (i0 + bredd)]
                 - p[j0 * nx1 + (i0 + bredd)]
                 - p[(j0 + hojd) * nx1 + i0]
                 + p[j0 * nx1 + i0])
        return sperr == 0

    def storsta_rektangel(self):
        """Största lediga axelriktade rektangel, exakt över rastret.

        Klassisk histogrammetod, O(nx * ny). Vid lika stor area vinner den
        med lägst j, sedan lägst i: sökningen ska inte bero på ordningen
        celler råkar besökas i.
        """
        nx, ny = self.nx, self.ny
        hojder = [0] * nx
        bast = None  # (area_celler, j0, i0, bredd, hojd)
        for j in range(ny):
            for i in range(nx):
                hojder[i] = hojder[i] + 1 if self.ledig(i, j) else 0
            stack = []  # (startindex, hojd)
            for i in range(nx + 1):
                h = hojder[i] if i < nx else 0
                start = i
                while stack and stack[-1][1] >= h:
                    si, sh = stack.pop()
                    area = sh * (i - si)
                    if sh > 0 and area > 0:
                        kandidat = (area, j - sh + 1, si, i - si, sh)
                        if bast is None or (kandidat[0] > bast[0]
                                            or (kandidat[0] == bast[0]
                                                and kandidat[1:3] < bast[1:3])):
                            bast = kandidat
                    start = si
                stack.append((start, h))
        if bast is None:
            return None
        _area, j0, i0, b, h = bast
        return Rektangel(self.omrade.x0_m + i0 * self.dx_m,
                         self.omrade.y0_m + j0 * self.dy_m,
                         self.omrade.x0_m + (i0 + b) * self.dx_m,
                         self.omrade.y0_m + (j0 + h) * self.dy_m)

    def __repr__(self):
        return ("Rasterkarta(%d x %d celler à %.3f m, %d lediga, hojd=%.2f m)"
                % (self.nx, self.ny, self.raster_m, self.antal_lediga(),
                   self.hojd_m))


def ledig_area_m2(scen, hojd, raster_m=None, omrade=None):
    """Hur mycket golv som är ledigt för något så här högt. Konservativt."""
    h = krav(hojd, "hojd").som_m
    return Rasterkarta(scen, h, raster_m=raster_m, omrade=omrade).area_m2()


def storsta_lediga_rektangel(scen, hojd, raster_m=None, omrade=None,
                             bortse_fran=()):
    """Största lediga rektangel för något som är ``hojd`` högt, eller None."""
    h = krav(hojd, "hojd").som_m
    karta = Rasterkarta(scen, h, raster_m=raster_m, omrade=omrade,
                        bortse_fran=bortse_fran)
    return karta.storsta_rektangel()


def far_plats(scen, objekt, raster_m=None, omrade=None, vridningar=None,
              z=None):
    """Får objektet plats någonstans, och i så fall var?

    Returnerar en ``Pose`` som är EXAKT prövad av ``kollision.provplacera``,
    eller None. Sökordningen är fast: söderifrån och norrut, västerifrån och
    österut, och vridningarna i objektets egen stigande ordning. Samma scen
    ger därför alltid samma svar.

    Objektet måste redan finnas i scenen (utan läge). Skälet är att kroppen,
    marginalen och de tillåtna vridningarna hör till objektet, inte till
    frågan, och en kopia av dem här hade kunnat drifta.
    """
    if isinstance(objekt, Objekt):
        namn = objekt.namn
    else:
        namn = str(objekt)
    o = scen.objekt(namn)
    if scen.ar_placerad(namn):
        raise Layoutfel("%s står redan någonstans; ta bort läget först" % namn)
    z0_m = 0.0 if z is None else krav(z, "z").som_m
    hojd_m = z0_m + o.hojd.som_m + o.kravd_fri_hojd.som_m
    vr = (o.tillatna_vridningar if vridningar is None
          else tuple(sorted(set(float(v) % 360.0 for v in vridningar))))

    karta = Rasterkarta(scen, hojd_m, raster_m=raster_m, omrade=omrade,
                        bortse_fran=(namn,),
                        extra_marginal_m=o.underhallsmarginal.som_m)
    for vridning in vr:
        # Fotavtryckets omslutande låda vid den här vridningen.
        r = math.radians(vridning)
        c, s = abs(math.cos(r)), abs(math.sin(r))
        bx = o.langd.som_m * c + o.bredd.som_m * s
        by = o.langd.som_m * s + o.bredd.som_m * c
        celler_x = max(1, int(math.ceil(bx / karta.dx_m - LAGE_TOL_M)))
        celler_y = max(1, int(math.ceil(by / karta.dy_m - LAGE_TOL_M)))
        for j in range(karta.ny - celler_y + 1):
            for i in range(karta.nx - celler_x + 1):
                if not karta.fonster_ledigt(i, j, celler_x, celler_y):
                    continue
                mitt_x = karta.omrade.x0_m + (i + celler_x / 2.0) * karta.dx_m
                mitt_y = karta.omrade.y0_m + (j + celler_y / 2.0) * karta.dy_m
                pose = Pose.meter(mitt_x, mitt_y, z0_m, vridning)
                if provplacera(scen, namn, pose).fri:
                    return pose
    return None
