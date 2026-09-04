# -*- coding: utf-8 -*-
"""Adaptern mellan planeringslagret och den layoutmotor som redan finns.

layoutport.py beskrev ett kontrakt - `motor.placera(begaran) -> svar` - och
sedan fanns ingen motor. MATT i M-63: den enda implementationen i hela repot
var en teststubb i tests/enhet/test_plan.py. Porten var alltsa ett hal med en
docstring framfor, och planeringslagret satte darfor ALDRIG en koordinat.

Motorn finns dock. `svc/vc_assist_svc/layout/` ar 4 359 rader med rum,
kollision, relationer och en losare som svarar med fyra domar. Den har filen
ar oversattningen, och den ar avsiktligt tunn: den raknar ingen geometri sjalv.

    delar          -> layout.rum.Objekt (matten ur specen eller databladet)
    golv_mm        -> layout.rum.Hall
    frigang_mm     -> Objekt.underhallsmarginal (kollision.kravd_separation_m)
    relationer     -> layout.relationer.* (nar -> InomRackvidd)
    losa()         -> placeringar, eller en MINIMAL mangd relationer som binder

DE FYRA DOMARNA BARS RAKT IGENOM

losarens LOST / OVERBESTAMD / RYMS_INTE / OBESTAMBART oversatts inte till
"gick" och "gick inte". Skillnaden mellan "hallen ar for liten" och "de har
tre relationerna kan inte galla samtidigt" ar precis det svar operatoren
behover for att kunna ratta sin bestallning, och losaren har redan raknat ut
det. Att slata over det hade varit att kasta bort en matning.

ANKARET AR EN SPARR, INTE EN ANTECKNING

set_transform satter komponentens ORIGO, och var origo sitter i forhallande
till lados mitt vet bara VC, genom get_bounds (layout/vc_utdata.py). Utan ett
MATT ankare ar en koordinat en gissning som flyttar komponenten fel, tyst.
Darfor: motorn raknar alltid fram DOMEN, men den lamnar ifran sig KOORDINATER
bara nar varje placerat objekts ankare ar matt. Saknas det blir det en
blockerande fraga i stallet. Fail-closed, I3.

Vad som INTE finns har: ingen optimering, ingen omplanering, ingen hallgeometri
ur en ritning. Samma avgransning som 22_planeringslagret.md §10 gor.
"""
from __future__ import annotations

from ..layout.losare import Status, losa
from ..layout.matt import Langd
from ..layout.provscener import (MARGINAL_LASTBARARE_MM, ROBOT_FRI_HOJD_MM,
                                 _robotmatt_mm)
from ..layout.relationer import Bredvid, InomRackvidd, Pa
from ..layout.rum import Ankare, Hall, Layoutfel as Rumsfel, Objekt, Scen
from ..layout.vc_utdata import till_verktygsanrop
from .layoutport import KONTRAKTSVERSION

# Hallens fria hojd nar bestallningen inte anger nagon. Talet ags av
# layout/provscener.py (HALLHOJD_M = 6.0, ANTAGET: en normal industrihall med
# travers) och laggs till som ett MARKT antagande i svaret, aldrig tyst.
from ..layout.provscener import HALLHOJD_M

# Sokrastret provas GROVT FORST, sedan finare. Talen ar layoutmotorns eget
# forslagsraster (250 mm) och de tva fordubblingarna over det.
#
# MATT i M-63 over 81 korningar (3 hallstorlekar x 3 rackvidder x 2-4 objekt x
# 3 raster). Tva fynd styr stegen:
#
#  * ETT GROVT RASTER KAN GE ETT FALSKT NEJ. Scenen 3x3 m med fyra objekt och
#    en robot pa 1650 mm gav RYMS_INTE vid 1000 mm, OVERBESTAMD vid 500 mm och
#    LOST vid 250 mm. Den starkaste avvisningen motorn har var alltsa fel, och
#    bara for att sokningen tog for langa steg.
#  * ETT FINT RASTER KAN GE ETT SAMRE SVAR AN ETT GROVT. Scenen 6x6 m med fyra
#    objekt och 2600 mm rackvidd gav LOST vid 1000 och 500 mm men OBESTAMBART
#    vid 250 mm: budgeten tog slut fore lagesutrymmet.
#
# Darfor stegen, och darfor i den ordningen: en LOSNING som hittas ar en
# losning oavsett raster (losaren granskar den oberoende efterat), medan ett
# NEJ alltid ska provas en gang till med finare steg innan det lamnas ut.
RASTERSTEGE_MM = (1000.0, 500.0, 250.0)   # Satt av M-63.

# Hur informativt ett nej ar, nar inget raster gav en losning. OVERBESTAMD
# pekar ut VILKA krav som binder; RYMS_INTE sager bara att hallen ar for
# liten; OBESTAMBART sager ingenting alls. Den mest informativa vinner, och
# rastret den kom ur skrivs alltid ut - annars later ett rastersvar som en
# matematisk omojlighet.
_INFORMATION = {"OVERBESTAMD": 3, "RYMS_INTE": 2, "OBESTAMBART": 1}

# Relationssorter porten kan skicka -> vad de blir i layoutmotorn. Sorter som
# inte star har oversatts inte, och det RAPPORTERAS: en relation som tyst inte
# provas ar samma tysta nedgradering som ett forval utan harkomst.
OVERSATTNING = ("nar", "beside", "on_top_of")

# Relationer som enligt K8 inte domes geometriskt utan av planens ordning och
# ogats tidsserie. De hoppas over med skal, precis som kallans static_eyes gor.
SEMANTISKA = ("feeds", "handoff", "sequence")


class Layoutmotor(object):
    """Uppfyller layoutport-kontraktet ovanpa layout/losare.losa."""

    def __init__(self, strikt_ankare=True, budget=None, raster_mm=None):
        self.strikt_ankare = bool(strikt_ankare)
        self.budget = budget
        self.raster_mm = raster_mm

    def __repr__(self):
        return "Layoutmotor(strikt_ankare=%s)" % self.strikt_ankare

    # -- kontraktet -------------------------------------------------------

    def placera(self, begaran):
        """Portens enda metod. Kastar aldrig: ett fel blir ett svar med skal."""
        antaganden = []
        fragor = []
        try:
            scen, hall_antaganden, hinder = self._scen(begaran, fragor)
        except Rumsfel as fel:
            return self._svar([], antaganden,
                              fragor + [_fraga("layout:rum",
                                               "layoutmotorn kunde inte bygga "
                                               "rummet: %s" % fel,
                                               "en scen som inte gar att bygga "
                                               "gar inte heller att lagga ut, "
                                               "och en halv layout ar farligare "
                                               "an ingen")],
                              "EJ_BYGGD", [])
        antaganden += hall_antaganden
        if hinder:
            return self._svar([], antaganden, fragor + hinder, "EJ_BYGGD", [])

        relationer, rel_antaganden, rel_fragor = self._relationer(begaran, scen)
        antaganden += rel_antaganden
        fragor += rel_fragor

        losning, raster, provade = self._stege(scen, relationer)
        antaganden.append(_antagande(
            "sokrastret", "%g mm" % raster,
            "layoutmotorn soker i ett RASTER av lagen, inte i planet. Provade "
            "steg: %s. Ett nej galler darfor det rastret och ar inget bevis "
            "for matematisk omojlighet - motorn sager det sjalv "
            "(layout/losare.py). MATT i M-63: ett grovt raster gav en gang "
            "RYMS_INTE dar ett fint gav en losning"
            % ", ".join("%g mm" % r for r in provade)))
        if losning.status is not Status.LOST:
            return self._svar([], antaganden, fragor, losning.status.value,
                              _konflikt(losning, raster))
        placeringar, ankarfragor = self._placeringar(losning, begaran)
        return self._svar(placeringar, antaganden, fragor + ankarfragor,
                          losning.status.value, [])

    def _stege(self, scen, relationer):
        """(losning, raster_mm, provade raster). Grovt forst, sedan finare.

        En LOSNING som hittas star sig oavsett raster: losaren granskar den
        med en OBEROENDE efterhandskontroll (kollision.granska) innan den
        kallas LOST. Ett NEJ daremot kan vara rastrets fel, sa det provas om
        med finare steg innan det lamnas ut.
        """
        stege = ((float(self.raster_mm),) if self.raster_mm
                 else RASTERSTEGE_MM)
        budget = self.budget if self.budget else _budget()
        basta = None
        provade = []
        for raster in stege:
            provade.append(raster)
            losning = losa(scen, relationer, raster_m=Langd.mm(raster),
                           budget=budget)
            if losning.status is Status.LOST:
                return losning, raster, provade
            vikt = _INFORMATION.get(losning.status.value, 0)
            if basta is None or vikt > basta[2]:
                basta = (losning, raster, vikt)
        return basta[0], basta[1], provade

    # -- scenen -----------------------------------------------------------

    def _scen(self, begaran, fragor):
        """(Scen, antaganden, hinder). Hinder = fragor som stoppar bygget."""
        antaganden = []
        hinder = []
        golv = begaran.get("golv_mm")
        if not golv:
            hinder.append(_fraga(
                "layout:yta",
                "hur stor yta far cellen ta? ange bredd x djup i mm",
                "layoutmotorn kraver ett golv att lagga ut pa. En yta vi valde "
                "sjalva skulle bestamma bade vad som far plats och vad som "
                "senare raknas som en for trang passage (K11)"))
            return None, antaganden, hinder

        objekt, objekt_antaganden, objekt_hinder = self._objekt(begaran)
        antaganden += objekt_antaganden
        hinder += objekt_hinder
        if hinder:
            return None, antaganden, hinder

        hojd_mm = begaran.get("hojd_mm")
        if hojd_mm is None:
            hojd_mm = HALLHOJD_M * 1000.0
            antaganden.append(_antagande(
                "cellens fria hojd", "%g mm" % hojd_mm,
                "bestallningen anger ingen fri hojd. Talet ags av "
                "layout/provscener.py (HALLHOJD_M), dar det ar markt ANTAGET: "
                "en normal industrihall med travers. Hojden paverkar bara om "
                "hoga objekt far plats, och varje objekt provas mot den"))
        hall = Hall("cell", Langd.mm(float(golv[0])), Langd.mm(float(golv[1])),
                    Langd.mm(float(hojd_mm)))
        scen = Scen(hall)
        for o in objekt:
            scen.lagg_till(o)
        return scen, antaganden, hinder

    def _objekt(self, begaran):
        """Delarna som Objekt. Ett matt som saknas blir en fraga, aldrig noll."""
        antaganden = []
        hinder = []
        ut = []
        frigang = float(begaran.get("frigang_mm") or 0.0)
        datablad = begaran.get("datablad") or {}
        for del_ in begaran.get("delar") or []:
            roll = del_["roll"]
            blad = datablad.get(roll) or {}
            matt = del_.get("matt_mm")
            rackvidd = blad.get("rackvidd_mm")
            if not matt and del_.get("kategori") == "robot" and rackvidd:
                l, b, h = _robotmatt_mm(float(rackvidd))
                matt = [l, b, h]
                antaganden.append(_antagande(
                    "fotavtryck for %s" % roll, "%g x %g x %g mm" % (l, b, h),
                    "katalogposten bar inga matt, men en rackvidd. Fotavtrycket "
                    "ar da harlett med layout/provscener.py:_robotmatt_mm, dar "
                    "andelarna star markta ANTAGNA ur tva verkliga robotar. "
                    "Talet ar alltsa harlett och inte last, och det ar skillnad"))
            if not matt or min(matt) <= 0:
                hinder.append(_fraga(
                    "layout:matt:%s" % roll,
                    "vilka matt har %s (%s)? ange langd x bredd x hojd i mm"
                    % (roll, del_.get("uri")),
                    "K0 i docs/spec/22_planeringslagret.md: en cell utan "
                    "fotavtryck ar OKAND, och en okand cell far inte placeras. "
                    "null ar inte noll, sa motorn valjer inget matt at "
                    "operatoren"))
                continue
            marginal = frigang
            if del_.get("kategori") == "lastbarare":
                marginal = MARGINAL_LASTBARARE_MM
                antaganden.append(_antagande(
                    "underhallsutrymme runt %s" % roll, "0 mm",
                    "en lastbarare ar gods och inte en maskin: den ska ga att "
                    "stalla tatt. Talet ags av layout/provscener.py "
                    "(MARGINAL_LASTBARARE_MM) dar det star markt ANTAGET"))
            ankare = _ankare(blad)
            for instans in range(1, int(del_.get("antal") or 1) + 1):
                namn = roll if instans == 1 else "%s#%d" % (roll, instans)
                ut.append(Objekt(
                    namn, Langd.mm(float(matt[0])), Langd.mm(float(matt[1])),
                    Langd.mm(float(matt[2])),
                    underhallsmarginal=Langd.mm(marginal),
                    kravd_fri_hojd=(Langd.mm(ROBOT_FRI_HOJD_MM)
                                    if del_.get("kategori") == "robot" else None),
                    rackvidd=(Langd.mm(float(rackvidd)) if rackvidd else None),
                    kategori=del_.get("kategori") or "",
                    ankare=ankare))
        return ut, antaganden, hinder

    # -- relationerna -----------------------------------------------------

    def _relationer(self, begaran, scen):
        antaganden = []
        fragor = []
        ut = []
        for r in begaran.get("relationer") or []:
            sort = r["sort"]
            fran, till = r["fran_roll"], r["till_roll"]
            if sort in SEMANTISKA:
                antaganden.append(_antagande(
                    "relationen %s %s %s" % (fran, sort, till), "hoppas over",
                    "K8: feeds, handoff och sequence ar semantiska och domes "
                    "inte av geometrin utan av planens beroendekanter och "
                    "ogats tidsserie. Samma gradering som kallans static_eyes "
                    "gor, och den ar avsiktlig"))
                continue
            if sort not in OVERSATTNING:
                fragor.append(_fraga(
                    "layout:relation:%s" % sort,
                    "hur ska relationen %s mellan %s och %s provas geometriskt?"
                    % (sort, fran, till),
                    "layoutmotorn oversatter %s och inget mer. En relation som "
                    "tyst inte provas ar en relation operatoren tror ar provad"
                    % ", ".join(OVERSATTNING), blockerar=False))
                continue
            if sort == "nar":
                try:
                    o = scen.objekt(fran)
                except Rumsfel:
                    o = None
                if o is None or o.rackvidd is None:
                    fragor.append(_fraga(
                        "layout:rackvidd:%s" % fran,
                        "vilken rackvidd har %s, i mm?" % fran,
                        "kravet ar att %s ska na %s, och utan rackvidden gar "
                        "det inte att prova. MATT i M-63: rackvidden saknas i "
                        "component.rsc for alla 2169 robotar men star i "
                        "model.xml for 1434 av dem, sa talet finns - det ligger "
                        "bara inte i det index databladet byggdes ur. Det maste "
                        "komma ur begaran, banken, komponentfilen eller ett "
                        "matt datablad. En gissad rackvidd hade avgjort om "
                        "cellen alls gar att lagga ut" % (fran, till)))
                    continue
                ut.append(InomRackvidd(till, fran, helt=True))
                antaganden.append(_antagande(
                    "rackviddens lasning for %s -> %s" % (fran, till),
                    "hela malets fotavtryck",
                    "greppunkten pa %s ar inte kand, och da ar den harda "
                    "lasningen den enda som haller: hela fotavtrycket ska ligga "
                    "inom radien. Det ar layout/relationer.py:InomRackvidd:s "
                    "egen motivering (helt=True), och den mjuka lasningen "
                    "kraver att nagon pekar ut plocklaget" % till))
            elif sort == "beside":
                ut.append(Bredvid(till, fran))
            elif sort == "on_top_of":
                ut.append(Pa(fran, till))
        return ut, antaganden, fragor

    # -- svaret -----------------------------------------------------------

    def _placeringar(self, losning, begaran):
        """Koordinater, men bara nar varje ankare ar MATT."""
        antagna = sorted(n for n in losning.scen.placerade_namn()
                         if losning.scen.objekt(n).kategori != "pelare"
                         and losning.scen.objekt(n).ankare.stampel != Ankare.MATT)
        if antagna and self.strikt_ankare:
            return [], [_fraga(
                "layout:ankare",
                "las komponentens lada med get_bounds for %s"
                % ", ".join(antagna),
                "set_transform satter komponentens ORIGO, och var origo sitter "
                "i forhallande till lados mitt vet bara VC. Ett antaget ankare "
                "flyttar komponenten fel, tyst (layout/vc_utdata.py). "
                "Layoutdomen ar raknad och star kvar; det ar KOORDINATERNA som "
                "inte far lamnas ut")]
        motiv = {}
        for steg in losning.spar:
            motiv[steg.namn] = steg.text()
        ut = []
        for anrop in till_verktygsanrop(losning.scen, strikt=False):
            namn = anrop.objekt
            roll, _sep, instans = namn.partition("#")
            ut.append({
                "roll": roll,
                "instans": int(instans) if instans else 1,
                "position_mm": [float(v) for v in anrop.argument["position"]],
                "wpr_deg": [float(v) for v in anrop.argument["wpr"]],
                "motiv": motiv.get(namn, "placerad av layoutmotorn"),
            })
        return ut, []

    @staticmethod
    def _svar(placeringar, antaganden, fragor, status, konflikt):
        return {"v": KONTRAKTSVERSION, "placeringar": list(placeringar),
                "antaganden": list(antaganden), "fragor": list(fragor),
                "status": status, "konflikt": list(konflikt)}


def _budget():
    from ..layout.losare import NODBUDGET
    return NODBUDGET


def _ankare(blad):
    """Ett MATT ankare nar databladet bar VC:s lada, annars ett antaget."""
    lada = blad.get("bounds")
    if isinstance(lada, dict) and lada.get("center_mm") and lada.get("half_extent_mm"):
        return Ankare.ur_bounds(lada["center_mm"], lada["half_extent_mm"])
    return None


def _antagande(vad, varde, motiv):
    return {"vad": vad, "varde": varde, "motiv": motiv}


def _fraga(id, vad, varfor, blockerar=True):
    return {"id": id, "vad": vad, "varfor": varfor, "blockerar": blockerar}


def _konflikt(losning, raster_mm):
    """Losarens skal, i maskinlasbar form.

    OVERBESTAMD bar en MINIMAL mangd relationer: tas nagon ur den gar resten.
    Det ar exakt det svar fas 16:s grind kraver - inte "planen ar ogiltig",
    utan VILKA krav som inte kan galla samtidigt.
    """
    ut = [{"kod": "SKAL",
           "text": "%s (sokraster %g mm)" % (losning.skal, raster_mm),
           "roller": []}]
    for r in losning.konflikt:
        ut.append({"kod": r.kod, "text": r.text(),
                   "roller": [n.partition("#")[0] for n in r.berorda()]})
    return ut
