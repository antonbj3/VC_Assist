# -*- coding: utf-8 -*-
"""Kollisionskontroll: förhand och efterhand.

Två frågor, samma matematik:

* FÖRHAND - ``provplacera(scen, namn, pose)``: får det här objektet stå där,
  innan något ändras? Svaret bär skälen, inte bara ett ja eller nej.
* EFTERHAND - ``granska(scen)``: en färdig layout granskas i sin helhet.
  Noll överlapp är fas 5:s grind, så granskningen är den som fäller.

Ett överlapp rapporteras med VILKA två objekt, HUR MYCKET de överlappar och
i VILKEN AXEL. Axeln är den med minst inträngning, alltså den kortaste vägen
ut, vilket är den upplysning som säger vad man ska göra åt saken.

Konservativ i tre punkter, alla åt det hårda hållet (fail-closed):

1. Separationskravet mellan två kroppar prövas med separerande axlar. Att
   ett par INTE separeras längs någon av de fyra kantnormalerna bevisar inte
   att de ligger närmare än kravet - vid hörn mot hörn kan avståndet vara
   större. Motorn säger då ändå nej. Den omvända riktningen är exakt: hittas
   en separerande axel med luft > kravet är avståndet bevisat större.
2. Vridna kroppar räknas mot rasterkartan (fria_ytor.py) genom sin
   omslutande axelriktade låda, alltså större än de är.
3. Fri bredd i en gång mäts på rastret och avrundas nedåt.

Källa: uppdragets punkt 4, docs/spec/50_grindar.md grind 5.
"""
from __future__ import annotations

import math

from .rum import (FRIHALLNA, LAGE_TOL_M, Kropp, Layoutfel, Scen,
                  VINKEL_TOL_GRADER, Zontyp)

__all__ = ["Overlapp", "Zonbrott", "Hojdbrott", "Passagebrott", "Utanfor",
           "Provsvar", "Granskning", "separation", "provplacera", "granska",
           "kravd_separation_m", "tillganglig_hojd_m", "radie_langs",
           "avstand_m", "fri_bredd_m"]


def _axelnamn(vektor, agare):
    """Ett läsbart namn på en riktning. Världsaxlarna får sina egna namn."""
    x, y = vektor
    if abs(y) < math.sin(math.radians(VINKEL_TOL_GRADER)):
        return "x"
    if abs(x) < math.sin(math.radians(VINKEL_TOL_GRADER)):
        return "y"
    return "lokal_%s@%s" % ("x" if abs(x) >= abs(y) else "y", agare)


class Overlapp:
    """Två kroppar som inte får plats där de står."""

    __slots__ = ("a", "b", "typ", "axel", "axel_vektor", "djup_m",
                 "kravd_marginal_m", "per_axel_m")

    #: kropparna skär varandra
    KROPP = "kropp"
    #: kropparna skär inte varandra, men underhållsutrymmet är inte fritt
    MARGINAL = "underhallsmarginal"

    def __init__(self, a, b, typ, axel, axel_vektor, djup_m,
                 kravd_marginal_m, per_axel_m):
        self.a = a
        self.b = b
        self.typ = typ
        self.axel = axel
        self.axel_vektor = axel_vektor
        self.djup_m = djup_m
        self.kravd_marginal_m = kravd_marginal_m
        self.per_axel_m = per_axel_m

    def text(self):
        if self.typ == Overlapp.KROPP:
            return ("%s och %s överlappar %.1f mm i axel %s "
                    "(världslådorna delar x %.1f mm, y %.1f mm, z %.1f mm)"
                    % (self.a, self.b, self.djup_m * 1000.0, self.axel,
                       self.per_axel_m["x"] * 1000.0,
                       self.per_axel_m["y"] * 1000.0,
                       self.per_axel_m["z"] * 1000.0))
        return ("%s och %s står %.1f mm för nära i axel %s; underhållsutrymmet "
                "kräver %.0f mm fritt"
                % (self.a, self.b, self.djup_m * 1000.0, self.axel,
                   self.kravd_marginal_m * 1000.0))

    def __repr__(self):
        return "Overlapp(%s)" % self.text()


class Zonbrott:
    """En kropp inne i en zon som ska hållas fri."""

    __slots__ = ("objekt", "zon", "zontyp", "intrang_m2", "fri_hojd_m", "underkant_m")

    def __init__(self, objekt, zon, zontyp, intrang_m2, fri_hojd_m, underkant_m):
        self.objekt = objekt
        self.zon = zon
        self.zontyp = zontyp
        self.intrang_m2 = intrang_m2
        self.fri_hojd_m = fri_hojd_m
        self.underkant_m = underkant_m

    def text(self):
        return ("%s tränger in %.2f m2 i zonen %s (%s), som ska vara fri upp "
                "till %.2f m; objektets underkant ligger på %.2f m"
                % (self.objekt, self.zon, self.zontyp, self.intrang_m2,
                   self.fri_hojd_m, self.underkant_m))

    def __repr__(self):
        return "Zonbrott(%s)" % self.text()


class Hojdbrott:
    """En kropp som inte får plats på höjden, med sitt fria utrymme ovanför."""

    __slots__ = ("objekt", "overkant_m", "kravd_fri_hojd_m", "tillganglig_hojd_m",
                 "orsak")

    def __init__(self, objekt, overkant_m, kravd_fri_hojd_m,
                 tillganglig_hojd_m, orsak):
        self.objekt = objekt
        self.overkant_m = overkant_m
        self.kravd_fri_hojd_m = kravd_fri_hojd_m
        self.tillganglig_hojd_m = tillganglig_hojd_m
        self.orsak = orsak

    def text(self):
        return ("%s når %.2f m och kräver %.2f m fritt ovanför, alltså %.2f m; "
                "%s ger bara %.2f m"
                % (self.objekt, self.overkant_m, self.kravd_fri_hojd_m,
                   self.overkant_m + self.kravd_fri_hojd_m, self.orsak,
                   self.tillganglig_hojd_m))

    def __repr__(self):
        return "Hojdbrott(%s)" % self.text()


class Passagebrott:
    """En gång eller utrymningsväg som blivit smalare än sitt krav."""

    __slots__ = ("zon", "kravd_bredd_m", "matt_bredd_m", "vid_m", "hinder")

    def __init__(self, zon, kravd_bredd_m, matt_bredd_m, vid_m, hinder):
        self.zon = zon
        self.kravd_bredd_m = kravd_bredd_m
        self.matt_bredd_m = matt_bredd_m
        self.vid_m = vid_m
        self.hinder = hinder

    def text(self):
        return ("passagen %s är %.2f m fri där den är som smalast (%.2f m in "
                "längs gången) men kräver %.2f m; det som smalnar av är %s"
                % (self.zon, self.matt_bredd_m, self.vid_m, self.kravd_bredd_m,
                   ", ".join(self.hinder) if self.hinder else "hallens egen form"))

    def __repr__(self):
        return "Passagebrott(%s)" % self.text()


class Utanfor:
    """En kropp som sticker ut ur hallen."""

    __slots__ = ("objekt", "vagg", "overskott_m")

    def __init__(self, objekt, vagg, overskott_m):
        self.objekt = objekt
        self.vagg = vagg
        self.overskott_m = overskott_m

    def text(self):
        return ("%s sticker ut %.1f mm förbi %s"
                % (self.objekt, self.overskott_m * 1000.0, self.vagg))

    def __repr__(self):
        return "Utanfor(%s)" % self.text()


class Provsvar:
    """Svaret på förhandsfrågan: får objektet stå här?"""

    __slots__ = ("objekt", "pose", "utanfor", "overlapp", "zonbrott", "hojdbrott")

    def __init__(self, objekt, pose, utanfor, overlapp, zonbrott, hojdbrott):
        self.objekt = objekt
        self.pose = pose
        self.utanfor = tuple(utanfor)
        self.overlapp = tuple(overlapp)
        self.zonbrott = tuple(zonbrott)
        self.hojdbrott = tuple(hojdbrott)

    @property
    def fri(self):
        return not (self.utanfor or self.overlapp or self.zonbrott
                    or self.hojdbrott)

    def skal(self):
        """Alla skäl som text, i fast ordning. Tom lista betyder fri."""
        return tuple([b.text() for b in self.utanfor]
                     + [b.text() for b in self.overlapp]
                     + [b.text() for b in self.zonbrott]
                     + [b.text() for b in self.hojdbrott])

    def __repr__(self):
        return ("Provsvar(%s, fri=%s, %d skäl)"
                % (self.objekt, self.fri, len(self.skal())))


class Granskning:
    """Efterhandsdomen över en hel layout."""

    __slots__ = ("overlapp", "zonbrott", "hojdbrott", "passagebrott",
                 "utanfor", "oplacerade")

    def __init__(self, overlapp, zonbrott, hojdbrott, passagebrott, utanfor,
                 oplacerade):
        self.overlapp = tuple(overlapp)
        self.zonbrott = tuple(zonbrott)
        self.hojdbrott = tuple(hojdbrott)
        self.passagebrott = tuple(passagebrott)
        self.utanfor = tuple(utanfor)
        self.oplacerade = tuple(oplacerade)

    @property
    def ok(self):
        """Fail-closed: allt måste vara placerat OCH utan anmärkning."""
        return not (self.overlapp or self.zonbrott or self.hojdbrott
                    or self.passagebrott or self.utanfor or self.oplacerade)

    @property
    def antal_overlapp(self):
        return len(self.overlapp)

    def rader(self):
        ut = []
        for b in self.utanfor:
            ut.append("UTANFOR " + b.text())
        for b in self.overlapp:
            ut.append("OVERLAPP " + b.text())
        for b in self.zonbrott:
            ut.append("ZON " + b.text())
        for b in self.hojdbrott:
            ut.append("HOJD " + b.text())
        for b in self.passagebrott:
            ut.append("PASSAGE " + b.text())
        for n in self.oplacerade:
            ut.append("OPLACERAD %s har inget läge" % n)
        return tuple(ut)

    def __repr__(self):
        return "Granskning(ok=%s, %d anmärkningar)" % (self.ok, len(self.rader()))


# ---- geometrin -----------------------------------------------------------

def kravd_separation_m(a, b):
    """Kravet mellan två kroppar är den STÖRRE av deras underhållsmarginaler.

    Skälet: A:s underhållsutrymme ska vara fritt från B:s kropp, och B:s från
    A:s. Båda kraven gäller samtidigt, och det hårdare av dem är det som
    binder. Att summera dem hade krävt dubbelt utrymme mellan två maskiner som
    var för sig bara begär sitt eget.

    UNDANTAG: hör kropparna till samma ENHET är kravet noll. En robots
    fixtur, dess pall och dess givare står inne i robotens cell och ska stå
    tätt; underhållsutrymmet är utrymmet runt CELLEN. Utan undantaget blir en
    robot med 900 mm räckvidd och 800 mm underhållsutrymme oanvändbar: allt
    den kan nå ligger i utrymmet den kräver fritt, och varje sådan uppgift
    hade blivit falskt överbestämd.
    """
    if a.enhet and a.enhet == b.enhet:
        return 0.0
    return max(a.marginal_m, b.marginal_m)


def _skalar(v, w):
    return v[0] * w[0] + v[1] * w[1]


def radie_langs(kropp, axel):
    """Kroppens halva utsträckning projicerad på en riktning i golvplanet."""
    (ax, ay), (bx, by) = kropp.axlar
    return (kropp.halv_x_m * abs(_skalar((ax, ay), axel))
            + kropp.halv_y_m * abs(_skalar((bx, by), axel)))


def _z_intrang_m(a, b):
    return min(a.z1_m, b.z1_m) - max(a.z0_m, b.z0_m)


def _per_axel(a, b, marginal_m):
    """Världslådornas överlapp per axel. Enbart för läsbarheten i rapporten."""
    ra = a.aabb(marginal_m / 2.0)
    rb = b.aabb(marginal_m / 2.0)
    return {"x": min(ra.x1_m, rb.x1_m) - max(ra.x0_m, rb.x0_m),
            "y": min(ra.y1_m, rb.y1_m) - max(ra.y0_m, rb.y0_m),
            "z": _z_intrang_m(a, b) + marginal_m}


def avstand_m(a, b):
    """UNDRE GRÄNS för det fria avståndet mellan två kroppar i golvplanet.

    Exakt när båda är axelriktade mot varandra. För vridna kroppar är den
    största luckan längs de fyra kantnormalerna mindre än eller lika med det
    verkliga avståndet, alltså en undre gräns. Ett krav som prövas mot en
    undre gräns kan falla i onödan men aldrig släppa igenom något för nära.

    Negativt värde betyder att kropparna skär varandra i golvplanet.
    """
    d = (b.mitt_x_m - a.mitt_x_m, b.mitt_y_m - a.mitt_y_m)
    basta = None
    for kropp in (a, b):
        for axel in kropp.axlar:
            luft = (abs(_skalar(d, axel)) - radie_langs(a, axel)
                    - radie_langs(b, axel))
            if basta is None or luft > basta:
                basta = luft
    return basta


def _skar(a, b, d):
    """Skär de två kropparnas lådor varandra i XY, utan marginal?"""
    for kropp in (a, b):
        for axel in kropp.axlar:
            luft = (abs(_skalar(d, axel)) - radie_langs(a, axel)
                    - radie_langs(b, axel))
            # Beröring är inte överlapp: två lådor kant i kant delar ingen
            # volym. Utan det hade varje tätt packat pallmönster blivit en
            # kollision, och grinden hade mätt flyttalsbrus.
            if luft >= -LAGE_TOL_M:
                return False
    return True


def separation(a, b, kravd_m=None):
    """Prövar två kroppar. Returnerar None om de är fria, annars ett Overlapp.

    ``kravd_m`` är det fria avstånd som krävs mellan dem; utelämnat tas det
    ur kropparnas underhållsmarginaler.
    """
    if kravd_m is None:
        kravd_m = kravd_separation_m(a, b)

    z_djup = _z_intrang_m(a, b)
    if z_djup <= LAGE_TOL_M:
        # Skilda i höjd. Två lådor som bara nuddar (en låda PÅ en pall) delar
        # ingen volym, och underhållsutrymme i sidled gäller inte mellan
        # våningar - annars hade ingen stapel varit tillåten.
        return None

    d = (b.mitt_x_m - a.mitt_x_m, b.mitt_y_m - a.mitt_y_m)
    kandidater = []
    for agare, kropp in ((a.namn, a), (b.namn, b)):
        for axel in kropp.axlar:
            avstand = abs(_skalar(d, axel))
            luft = avstand - radie_langs(a, axel) - radie_langs(b, axel)
            if luft - kravd_m >= -LAGE_TOL_M:
                # Projektionerna är isär med minst kravet, alltså är kropparna
                # det. Ett krav som är EXAKT uppfyllt är uppfyllt: annars hade
                # ett mellanrum på 400 mm mot ett krav på 400 mm fällt, och
                # relationsspråkets egna tal hade blivit omöjliga att skriva.
                return None
            kandidater.append((kravd_m - luft, axel, agare))

    # Ingen separerande axel hittad. Antingen ligger kropparna för nära, eller
    # så är det ett hörn-mot-hörn-fall som fyra kantnormaler inte kan avgöra.
    # Båda blir nej (fail-closed).
    #
    # Z räknas med som kandidataxel: den kortaste vägen ut kan vara uppåt,
    # och för två staplade lådor är den det nästan alltid.
    kandidater.append((z_djup, (0.0, 0.0), "z"))
    djup, axel, agare = min(kandidater, key=lambda k: (round(k[0], 9), k[2]))
    if agare == "z":
        namn_axel, vektor = "z", (0.0, 0.0, 1.0)
    else:
        namn_axel = _axelnamn(axel, agare)
        vektor = (axel[0], axel[1], 0.0)

    # Skär kropparna varandra, eller är det bara underhållsutrymmet som är
    # trångt? Frågan avgörs genom att pröva om med noll krav.
    typ = (Overlapp.KROPP if _skar(a, b, d)
           else (Overlapp.MARGINAL if kravd_m > 0.0 else Overlapp.KROPP))

    return Overlapp(a.namn, b.namn, typ, namn_axel, vektor, max(djup, 0.0),
                    kravd_m, _per_axel(a, b, 0.0))


def _rektangel_som_kropp(namn, rekt, z0_m, z1_m):
    return Kropp(namn, *rekt.mitt_m, halv_x_m=rekt.bredd_m / 2.0,
                 halv_y_m=rekt.djup_m / 2.0, z0_m=z0_m, z1_m=z1_m,
                 vridning_grader=0.0)


def _utanfor_hallen(scen, kropp):
    golv = scen.hall.golv
    ut = []
    lada = kropp.aabb()
    for vagg, over in (("vaster", golv.x0_m - lada.x0_m),
                       ("oster", lada.x1_m - golv.x1_m),
                       ("soder", golv.y0_m - lada.y0_m),
                       ("norr", lada.y1_m - golv.y1_m)):
        if over > LAGE_TOL_M:
            ut.append(Utanfor(kropp.namn, vagg, over))
    return ut


def tillganglig_hojd_m(scen, lada):
    """Lägsta tak över en världslåda: hallen, eller en zon med lägre tak.

    Returnerar (höjd, orsak). Den lägsta bjälken vinner, för objektet står
    under den och inte bredvid.
    """
    hojd = scen.hall.hojd.som_m
    orsak = "hallens tak"
    for zon in scen.hall.zoner:
        if zon.takhojd_m is None or zon.yta.snitt(lada) is None:
            continue
        if zon.takhojd_m < hojd - LAGE_TOL_M:
            hojd = zon.takhojd_m
            orsak = "taket i zonen %s" % zon.namn
    return hojd, orsak


def _hojdbrott(scen, namn, kropp):
    """Objektets överkant plus dess krävda fria utrymme mot lägsta taket."""
    kravd = scen.objekt(namn).kravd_fri_hojd.som_m
    hojd, orsak = tillganglig_hojd_m(scen, kropp.aabb())
    if kropp.z1_m + kravd > hojd + LAGE_TOL_M:
        return [Hojdbrott(namn, kropp.z1_m, kravd, hojd, orsak)]
    return []


def _hinder_i_zon(scen, zon, extra=None, hoppa=()):
    """Kroppar som finns i zonen under dess fria höjd, som klippta lådor.

    ``hoppa`` gäller BARA kropparna i scenen. ``extra`` är den kropp som
    prövas och räknas alltid med, även om den heter samma sak som något som
    står i scenen - det är just poängen med en förhandskontroll.
    """
    ut = []
    kroppar = [k for k in scen.kroppar() if k is not None and k.namn not in hoppa]
    if extra is not None:
        kroppar.append(extra)
    for kropp in kroppar:
        if kropp.z0_m >= zon.fri_hojd_m - LAGE_TOL_M:
            continue  # passerar ovanför den höjd som ska hållas fri
        if kropp.z1_m <= LAGE_TOL_M:
            continue
        klippt = zon.yta.snitt(kropp.aabb())
        if klippt is not None:
            ut.append((kropp.namn, klippt))
    return ut


def fri_bredd_m(scen, zon, extra=None, hoppa=()):
    """Passagens smalaste fria bredd, var den är som smalast, och av vad.

    Mätt tvärs gångens LÅNGA axel. Måttet är ANALYTISKT och inte rastrerat:
    snitten läggs vid hindrens egna kanter, så måttet är exakt för
    axelriktade kroppar. En vriden kropp räknas genom sin omslutande låda,
    alltså större än den är, vilket ger en fri bredd som aldrig överskattas.

    Bara det som finns under zonens fria höjd räknas: en transportör som
    korsar över gången på 2,6 m smalnar inte av den för en truck på 2,2 m.

    ``extra`` är en kropp som inte står i scenen ännu, för förhandskontroll.
    """
    if zon.typ not in (Zontyp.GANG, Zontyp.UTRYMNINGSVAG):
        raise Layoutfel("clear width is measured in an aisle or an emergency "
                        "route, not in %s" % zon.typ.value)
    yta = zon.yta
    langs_x = yta.bredd_m >= yta.djup_m
    hinder = _hinder_i_zon(scen, zon, extra, hoppa)
    if langs_x:
        lag, hog = yta.x0_m, yta.x1_m
        tvars_lag, tvars_hog = yta.y0_m, yta.y1_m
        kant = lambda r: (r.x0_m, r.x1_m, r.y0_m, r.y1_m)
    else:
        lag, hog = yta.y0_m, yta.y1_m
        tvars_lag, tvars_hog = yta.x0_m, yta.x1_m
        kant = lambda r: (r.y0_m, r.y1_m, r.x0_m, r.x1_m)

    kanter = [kant(r) for _n, r in hinder]
    punkter = sorted({lag, hog} | {v for k in kanter for v in k[:2]})
    smalast = tvars_hog - tvars_lag
    vid = lag
    varst = ()
    for i in range(len(punkter) - 1):
        a, b = punkter[i], punkter[i + 1]
        if b - a <= LAGE_TOL_M:
            continue
        mitt = 0.5 * (a + b)
        sperrar = []
        namn = []
        for (namn_i, _r), (k0, k1, t0, t1) in zip(hinder, kanter):
            if k0 - LAGE_TOL_M <= mitt <= k1 + LAGE_TOL_M:
                sperrar.append((t0, t1))
                namn.append(namn_i)
        bredd = _storsta_lucka_m(sperrar, tvars_lag, tvars_hog)
        if bredd < smalast - LAGE_TOL_M:
            smalast = bredd
            vid = mitt - lag
            varst = tuple(sorted(set(namn)))
    return smalast, vid, varst


def _storsta_lucka_m(sperrar, lag, hog):
    """Största fria intervall i [lag, hog] efter att spärrarna klippts bort."""
    sorterade = sorted(sperrar)
    basta = 0.0
    kant = lag
    for t0, t1 in sorterade:
        if t0 > kant:
            basta = max(basta, min(t0, hog) - kant)
        kant = max(kant, t1)
        if kant >= hog:
            return basta
    return max(basta, hog - kant)


def _zonbrott(scen, namn, kropp):
    ut = []
    for zon in scen.hall.zoner:
        if zon.typ not in FRIHALLNA:
            continue
        if kropp.z0_m >= zon.fri_hojd_m - LAGE_TOL_M:
            continue  # passerar ovanför den höjd som ska hållas fri
        snitt = zon.yta.snitt(kropp.aabb())
        if snitt is None:
            continue
        if zon.typ is Zontyp.GANG and zon.minsta_bredd_m is not None:
            # En gång med ett breddkrav får trängas in i, så länge den bredd
            # som är kvar räcker. Det är BREDDEN som är storheten, inte
            # närvaron: en 3 m bred gång tål ett skåp, en 1,6 m bred gör det
            # inte, och en grind som bara ser närvaron mäter fel sak.
            bredd, vid, _h = fri_bredd_m(scen, zon, extra=kropp, hoppa=(namn,))
            if bredd >= zon.minsta_bredd_m - LAGE_TOL_M:
                continue
            ut.append(Zonbrott(namn, zon.namn, zon.typ.value, snitt.area_m2,
                               zon.fri_hojd_m, kropp.z0_m))
            continue
        # Utrymningsväg, förbjudet område, och en gång utan uttryckligt
        # breddkrav: hålls helt fria upp till sin fria höjd. Fail-closed - en
        # gång utan angiven minsta bredd tolkas som "rör den inte".
        zonkropp = _rektangel_som_kropp("zon:" + zon.namn, zon.yta,
                                        0.0, zon.fri_hojd_m)
        if separation(kropp, zonkropp, 0.0) is None:
            continue
        ut.append(Zonbrott(namn, zon.namn, zon.typ.value, snitt.area_m2,
                           zon.fri_hojd_m, kropp.z0_m))
    return ut


def provplacera(scen, namn, pose, bortse_fran=()):
    """FÖRHANDSKONTROLL. Får objektet stå i pose, utan att scenen ändras?

    ``bortse_fran`` är namn vars kroppar inte ska räknas, till exempel
    objektet självt när ett befintligt läge prövas om.
    """
    kropp = scen.kropp_for(namn, pose)
    hoppa = set(bortse_fran) | {namn}
    overlapp = []
    for annan in scen.placerade_namn():
        if annan in hoppa:
            continue
        traff = separation(kropp, scen.kropp(annan))
        if traff is not None:
            overlapp.append(traff)
    return Provsvar(namn, pose, _utanfor_hallen(scen, kropp), overlapp,
                    _zonbrott(scen, namn, kropp), _hojdbrott(scen, namn, kropp))


def granska(scen):
    """EFTERHANDSKONTROLL. Hela layouten, allt som kan fällas."""
    if not isinstance(scen, Scen):
        raise Layoutfel("granska takes a Scen")
    placerade = scen.placerade_namn()
    overlapp = []
    zonbrott = []
    hojdbrott = []
    utanfor = []
    for i, namn in enumerate(placerade):
        kropp = scen.kropp(namn)
        utanfor.extend(_utanfor_hallen(scen, kropp))
        zonbrott.extend(_zonbrott(scen, namn, kropp))
        hojdbrott.extend(_hojdbrott(scen, namn, kropp))
        for annan in placerade[i + 1:]:
            traff = separation(kropp, scen.kropp(annan))
            if traff is not None:
                overlapp.append(traff)

    passagebrott = []
    for zon in scen.hall.zoner:
        if zon.minsta_bredd_m is None:
            continue
        bredd_m, vid_m, hinder = fri_bredd_m(scen, zon)
        if bredd_m < zon.minsta_bredd_m - LAGE_TOL_M:
            passagebrott.append(Passagebrott(zon.namn, zon.minsta_bredd_m,
                                             bredd_m, vid_m, hinder))

    oplacerade = tuple(n for n in scen.namn() if not scen.ar_placerad(n))
    return Granskning(overlapp, zonbrott, hojdbrott, passagebrott, utanfor,
                      oplacerade)
