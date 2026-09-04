# -*- coding: utf-8 -*-
"""Provscener ur bänken, med verkliga mått, och mätningen av motorn.

Scenerna byggs ur `bank/uppgifter/*.json` och `bank/katalog_index.json`, inte
ur avskrivna tal. EUR-pallen är 1200 x 800 x 144 mm för att banken säger det,
och ABB IRB 2600 når 1650 mm för att banken bär tillverkarens publicerade
siffra. Går banken sönder går provscenerna sönder, och det är avsikten: en
kopia av måtten här hade kunnat drifta utan att någon märkte det.

Det banken INTE bär är maskinernas fotavtryck och transportörernas längd,
för uppgifterna behöver dem inte. Layouten behöver dem. De står därför här
som märkta antaganden med motiv, enligt samma regel som banken själv följer
(bank/README.md, lintkod M28_ANTAGANDE, och docs/spec/96_ingen_skuld.md S6).

Kör mätningen:

    python3 -c "import sys; sys.path.insert(0, 'svc'); \\
        from vc_assist_svc.layout import provscener; print(provscener.rapport())"
"""
from __future__ import annotations

import json
import os

from .kollision import granska
from .losare import Status, losa
from .matt import Langd, Vek2
from .relationer import (Bakom, Bredvid, CentreradI, Framfor, IHorn,
                         InomRackvidd, IRad, IZon, MinstaAvstand, MotVagg, Pa,
                         Riktning, TillHoger, TillVanster, UtanforZon)
from .rum import (Hall, Horn, Objekt, Pelare, Rektangel, Scen, Vagg, Zon,
                  Zontyp)
from .vc_utdata import till_verktygsanrop

__all__ = ["Provscen", "PROVSCENER", "mat", "rapport", "katalog", "uppgift"]

# ---- var banken ligger ---------------------------------------------------

# svc/vc_assist_svc/layout/ -> tre steg upp är projektroten.
_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
BANK = os.path.join(_ROT, "bank")


def katalog():
    """Bankens komponentindex, en post per URI."""
    with open(os.path.join(BANK, "katalog_index.json"), encoding="utf-8") as f:
        poster = json.load(f)["poster"]
    return {p["uri"]: p for p in poster}


def uppgift(task_id):
    """En bänkuppgift som dict."""
    with open(os.path.join(BANK, "uppgifter", task_id + ".json"),
              encoding="utf-8") as f:
        return json.load(f)


# ---- antaganden ----------------------------------------------------------
# Varje tal här är ETT ANTAGANDE och bär sitt motiv, precis som bankens egna.
# Ingen mätning finns; mätning M-20 (layoutmotorn mot en handbyggd VC-cell)
# är den som ska ersätta dem.

# Robotens fotplatta som andel av räckvidden. ABB IRB 2600 har ungefär 500 mm
# fotplatta vid 1650 mm räckvidd och IRB 660 ungefär 1000 mm vid 3150 mm,
# alltså kring 0,30 i båda ändar av storleksskalan. ANTAGET ur de två måtten.
ROBOTFOT_ANDEL = 0.30
ROBOTFOT_MIN_MM = 350.0    # ANTAGET: mindre än så blir ingen industrirobot
ROBOTFOT_MAX_MM = 1300.0   # ANTAGET: IRB 660:s klass är den största i banken
ROBOTHOJD_ANDEL = 0.85     # ANTAGET: robotens höjd i viloläge, andel av räckvidd
ROBOT_FRI_HOJD_MM = 500.0  # ANTAGET: fritt över roboten för armens svep uppåt

# Underhållsutrymme runt en maskin. Ingen av dem är mätt; alla är valda så att
# en människa kommer åt med verktyg utan att stå i en gång.
MARGINAL_ROBOT_MM = 800.0      # ANTAGET: åtkomst till robotfot och kablage
MARGINAL_STATION_MM = 700.0    # ANTAGET: lucköppning på en stationskåpa
MARGINAL_TRANSPORT_MM = 400.0  # ANTAGET: åtkomst längs en transportör
MARGINAL_LASTBARARE_MM = 0.0   # en pall behöver inget eget underhållsutrymme

# Transportörens höjd över golv. ANTAGET: arbetshöjd för manuell hantering.
TRANSPORTHOJD_MM = 900.0
# Fotavtryck för stationer banken namnger men inte måttsätter. Alla ANTAGNA,
# valda som en kåpa en människa arbetar framför.
STATIONSMATT_MM = {
    "bank://station/fixtur_pneumatisk_spann": (1200.0, 900.0, 1000.0),
    "bank://station/press_tvahands": (1400.0, 1200.0, 2200.0),
    "bank://station/skruvstation": (900.0, 700.0, 1600.0),
    "bank://station/limstation": (1000.0, 800.0, 1500.0),
    "bank://station/svetsstation": (1600.0, 1400.0, 2000.0),
    "bank://station/blistermaskin": (3000.0, 1500.0, 2000.0),
    "bank://station/formsprutmaskin": (5000.0, 2000.0, 2400.0),
    "bank://station/kartongresare": (1800.0, 1200.0, 1800.0),
    "bank://station/kassationslada": (800.0, 600.0, 800.0),
    "bank://station/omarbetningsplats": (1500.0, 900.0, 1200.0),
    "bank://station/buffert_ackumulerande": (3000.0, 900.0, 1000.0),
    "bank://station/agv_lastplats": (2000.0, 1400.0, 300.0),
    "bank://station/pallmagasin": (1400.0, 1000.0, 2000.0),
    "bank://station/verktygsstall": (900.0, 600.0, 1200.0),
}
# Givare och små don. ANTAGNA: en stolpe med givare tar ungefär så här mycket
# golv, och höjden är den de brukar sitta på.
SMADON_MM = (150.0, 150.0, 1000.0)

# Hallens fria höjd i provscenerna. ANTAGET: en normal industrihall med
# travers ligger kring 6 m under balk.
HALLHOJD_M = 6.0
# Gångbredd i provscenerna. ANTAGET: en truckgång som två personer kan mötas
# i. Inget standardkrav är hämtat; talet är valt och märkt.
GANGBREDD_M = 1.6
# Fri höjd i en gång. ANTAGET: en truck med förare går under.
GANG_FRI_HOJD_M = 2.4


def _robotmatt_mm(rackvidd_mm):
    sida = max(ROBOTFOT_MIN_MM, min(ROBOTFOT_MAX_MM,
                                    rackvidd_mm * ROBOTFOT_ANDEL))
    return sida, sida, rackvidd_mm * ROBOTHOJD_ANDEL


class Byggare:
    """Bygger en scen ur bankens vokabulär. Måtten kommer ur banken."""

    def __init__(self, hall, kat=None):
        self.kat = kat if kat is not None else katalog()
        self.scen = Scen(hall)
        self.relationer = []

    def _post(self, uri):
        try:
            return self.kat[uri]
        except KeyError:
            raise KeyError("bank://-posten %r finns inte i katalogindexet" % uri)

    def robot(self, namn, uri):
        p = self._post(uri)
        l, b, h = _robotmatt_mm(float(p["rackvidd_mm"]))
        return self.lagg(Objekt(
            namn, Langd.mm(l), Langd.mm(b), Langd.mm(h),
            underhallsmarginal=Langd.mm(MARGINAL_ROBOT_MM),
            kravd_fri_hojd=Langd.mm(ROBOT_FRI_HOJD_MM),
            rackvidd=Langd.mm(float(p["rackvidd_mm"])),
            kategori="robot", tillatna_vridningar=(0.0, 90.0, 180.0, 270.0)))

    def transport(self, namn, uri, langd_mm, vridningar=(0.0, 90.0, 180.0, 270.0)):
        """Transportör. BREDDEN kommer ur banken, LÄNGDEN ur uppgiften."""
        p = self._post(uri)
        return self.lagg(Objekt(
            namn, Langd.mm(float(langd_mm)), Langd.mm(float(p["bredd_mm"])),
            Langd.mm(TRANSPORTHOJD_MM),
            underhallsmarginal=Langd.mm(MARGINAL_TRANSPORT_MM),
            kategori="transport", barande=True,
            tillatna_vridningar=vridningar))

    def station(self, namn, uri, vridningar=(0.0, 90.0, 180.0, 270.0)):
        p = self._post(uri)
        l, b, h = STATIONSMATT_MM[p["uri"]]
        return self.lagg(Objekt(
            namn, Langd.mm(l), Langd.mm(b), Langd.mm(h),
            underhallsmarginal=Langd.mm(MARGINAL_STATION_MM),
            kategori="station", barande=True, tillatna_vridningar=vridningar))

    def lastbarare(self, namn, uri, vridningar=(0.0, 90.0)):
        """Pall eller låda. Alla tre måtten kommer ur banken."""
        p = self._post(uri)
        return self.lagg(Objekt(
            namn, Langd.mm(float(p["l_mm"])), Langd.mm(float(p["b_mm"])),
            Langd.mm(float(p["h_mm"])),
            underhallsmarginal=Langd.mm(MARGINAL_LASTBARARE_MM),
            kategori="lastbarare", barande=True,
            tillatna_vridningar=vridningar))

    def givare(self, namn, uri):
        self._post(uri)
        l, b, h = SMADON_MM
        return self.lagg(Objekt(namn, Langd.mm(l), Langd.mm(b), Langd.mm(h),
                                kategori="givare", tillatna_vridningar=(0.0,)))

    def lagg(self, objekt):
        self.scen.lagg_till(objekt)
        return objekt

    def kraver(self, *relationer):
        self.relationer.extend(relationer)

    def klar(self):
        return self.scen, tuple(self.relationer)


class Provscen:
    """En provscen: hur den byggs, och vilket svar som är facit."""

    __slots__ = ("id", "uppgift_id", "beskrivning", "_bygg", "vantat")

    def __init__(self, id_, uppgift_id, beskrivning, bygg, vantat):
        self.id = id_
        self.uppgift_id = uppgift_id
        self.beskrivning = beskrivning
        self._bygg = bygg
        self.vantat = vantat

    def bygg(self, kat=None):
        return self._bygg(kat)

    def kor(self, kat=None):
        scen, relationer = self.bygg(kat)
        return scen, losa(scen, relationer)

    def __repr__(self):
        return "Provscen(%s, %s, vantat=%s)" % (self.id, self.uppgift_id,
                                                self.vantat.value)


# ---- hallar --------------------------------------------------------------

def _hall(namn, bredd_m, djup_m, zoner=(), pelare=()):
    return Hall(namn, Langd.m(bredd_m), Langd.m(djup_m), Langd.m(HALLHOJD_M),
                zoner=zoner, pelare=pelare)


def _gang(namn, x0, y0, x1, y1):
    return Zon(namn, Zontyp.GANG, Rektangel.av(*[Langd.m(v)
                                                 for v in (x0, y0, x1, y1)]),
               fri_hojd=Langd.m(GANG_FRI_HOJD_M),
               minsta_bredd=Langd.m(GANGBREDD_M))


# ---- scenerna ------------------------------------------------------------

def _t01(kat):
    """T-01: band med stoppgrind, en givare och ett don, längs södra väggen."""
    u = uppgift("T-01")
    assert u["grupp"] == "T"
    b = Byggare(_hall("T-01", 14.0, 9.0, zoner=[_gang("gang", 0.0, 6.0, 14.0, 9.0)]), kat)
    b.transport("band", "bank://transport/band_600", 6000.0,
                vridningar=(0.0,))
    b.givare("fotocell", "bank://givare/fotocell_genomgaende")
    b.station("kassation", "bank://station/kassationslada", vridningar=(0.0,))
    b.kraver(MotVagg("band", Vagg.SODER, marginal=Langd.mm(500.0)),
             Bredvid("fotocell", "band", mellanrum=Langd.mm(100.0)),
             Framfor("kassation", "band", avstand=Langd.m(1.0)),
             UtanforZon("band", "gang"))
    return b.klar()


def _t02(kat):
    """T-02: indexerad matning som matar en fixtur."""
    b = Byggare(_hall("T-02", 12.0, 8.0), kat)
    b.transport("matare", "bank://transport/band_400", 3000.0, vridningar=(0.0,))
    b.station("fixtur", "bank://station/fixtur_pneumatisk_spann",
              vridningar=(0.0,))
    b.givare("lagesgivare", "bank://givare/lagesgivare_encoder")
    b.kraver(MotVagg("matare", Vagg.VASTER, marginal=Langd.m(1.0)),
             Framfor("fixtur", "matare", avstand=Langd.mm(600.0)),
             Bredvid("lagesgivare", "matare", mellanrum=Langd.mm(150.0)))
    return b.klar()


def _t03(kat):
    """T-03: två banor som flyter samman i en tredje."""
    b = Byggare(_hall("T-03", 16.0, 12.0), kat)
    b.transport("bana_a", "bank://transport/band_600", 5000.0, vridningar=(0.0,))
    b.transport("bana_b", "bank://transport/band_600", 5000.0, vridningar=(0.0,))
    b.transport("samlingsbana", "bank://transport/band_600", 4000.0,
                vridningar=(0.0,))
    b.kraver(MotVagg("bana_a", Vagg.SODER, marginal=Langd.m(1.5)),
             IRad(("bana_a", "bana_b"), Riktning.NORR, Langd.m(2.0)),
             Framfor("samlingsbana", "bana_a", avstand=Langd.m(1.0)))
    return b.klar()


def _t04(kat):
    """T-04: ackumulerande buffert mellan inflöde och utflöde."""
    b = Byggare(_hall("T-04", 18.0, 10.0), kat)
    b.transport("inflode", "bank://transport/rullbana_ackumulerande_500",
                4000.0, vridningar=(0.0,))
    b.station("buffert", "bank://station/buffert_ackumulerande",
              vridningar=(0.0,))
    b.transport("utflode", "bank://transport/rullbana_ackumulerande_500",
                4000.0, vridningar=(0.0,))
    b.kraver(MotVagg("inflode", Vagg.VASTER, marginal=Langd.m(1.0)),
             Framfor("buffert", "inflode", avstand=Langd.mm(800.0)),
             Framfor("utflode", "buffert", avstand=Langd.mm(800.0)))
    return b.klar()


def _p01(kat):
    """P-01: robot plockar ur en stillastående fixtur och lägger i en KLT."""
    u = uppgift("P-01")
    assert u["grupp"] == "P"
    b = Byggare(_hall("P-01", 12.0, 10.0), kat)
    b.robot("robot", "bank://robot/abb_irb_1200_5_0900")
    b.station("fixtur", "bank://station/fixtur_pneumatisk_spann")
    b.lastbarare("klt", "bank://last/klt_4147")
    b.kraver(CentreradI("robot"),
             InomRackvidd("fixtur", "robot", helt=False),
             InomRackvidd("klt", "robot"))
    return b.klar()


def _p02(kat):
    """P-02: robot plockar från ett rörligt band, med låda bredvid."""
    b = Byggare(_hall("P-02", 14.0, 10.0), kat)
    b.robot("robot", "bank://robot/fanuc_m10id_12")
    b.transport("band", "bank://transport/band_600", 5000.0, vridningar=(0.0,))
    b.lastbarare("klt", "bank://last/klt_6147")
    b.kraver(MotVagg("band", Vagg.SODER, marginal=Langd.m(2.0)),
             Framfor("robot", "band", avstand=Langd.m(1.0)),
             InomRackvidd("band", "robot", helt=False),
             InomRackvidd("klt", "robot"))
    return b.klar()


def _p04(kat):
    """P-04: plock ur ostrukturerad hög i gitterbox, med 3D-kamera."""
    b = Byggare(_hall("P-04", 12.0, 10.0), kat)
    b.robot("robot", "bank://robot/abb_irb_2600_20_1650")
    b.lastbarare("gitterbox", "bank://last/gitterbox")
    b.lastbarare("utpall", "bank://last/eur_pall")
    b.givare("kamera", "bank://givare/kamera_3d_bin")
    b.kraver(CentreradI("robot"),
             InomRackvidd("gitterbox", "robot", helt=False),
             InomRackvidd("utpall", "robot", helt=False),
             MinstaAvstand("gitterbox", "utpall", Langd.m(0.5)),
             Bredvid("kamera", "gitterbox", mellanrum=Langd.mm(200.0)))
    return b.klar()


def _l01(kat):
    """L-01: palletering, ett lager i rutmönster på EUR-pall."""
    u = uppgift("L-01")
    assert u["fysik"]["arbetsradie_mm"] > 0
    b = Byggare(_hall("L-01", 14.0, 12.0), kat)
    b.robot("robot", "bank://robot/abb_irb_660_180_3150")
    b.lastbarare("pall", "bank://last/eur_pall", vridningar=(0.0,))
    b.transport("inbana", "bank://transport/band_600", 4000.0, vridningar=(0.0,))
    for i in range(4):
        b.lastbarare("kolli_%d" % i, "bank://last/klt_4147", vridningar=(0.0,))
    b.kraver(CentreradI("robot"),
             InomRackvidd("pall", "robot"),
             InomRackvidd("inbana", "robot", helt=False),
             Pa("kolli_0", "pall"),
             IRad(("kolli_0", "kolli_1"), Riktning.OSTER, Langd.mm(0.0)),
             IRad(("kolli_2", "kolli_3"), Riktning.OSTER, Langd.mm(0.0)),
             Pa("kolli_2", "pall"),
             IRad(("kolli_0", "kolli_2"), Riktning.NORR, Langd.mm(0.0)))
    return b.klar()


def _l02(kat):
    """L-02: två lager med mellanlägg, alltså stapling i höjd."""
    b = Byggare(_hall("L-02", 12.0, 12.0), kat)
    b.robot("robot", "bank://robot/abb_irb_660_180_3150")
    b.lastbarare("pall", "bank://last/eur_pall", vridningar=(0.0,))
    b.lastbarare("lager_1", "bank://last/mellanlagg_papp", vridningar=(0.0,))
    b.lastbarare("lager_2", "bank://last/mellanlagg_papp", vridningar=(0.0,))
    b.kraver(CentreradI("robot"),
             InomRackvidd("pall", "robot"),
             Pa("lager_1", "pall"),
             Pa("lager_2", "lager_1"))
    return b.klar()


def _l03(kat):
    """L-03: avpalletering, pall in på kedjetransportör, kolli ut på band."""
    b = Byggare(_hall("L-03", 16.0, 12.0), kat)
    b.robot("robot", "bank://robot/abb_irb_4600_60_2050")
    b.transport("pallbana", "bank://transport/kedjetransportor_pall", 3000.0,
                vridningar=(0.0,))
    b.transport("utbana", "bank://transport/band_600", 4000.0, vridningar=(0.0,))
    b.lastbarare("pall", "bank://last/eur_pall", vridningar=(0.0,))
    b.kraver(MotVagg("pallbana", Vagg.SODER, marginal=Langd.m(2.0)),
             Pa("pall", "pallbana"),
             Framfor("robot", "pallbana", avstand=Langd.m(1.2)),
             InomRackvidd("pall", "robot", helt=False),
             TillHoger("utbana", "robot", avstand=Langd.m(1.0)))
    return b.klar()


def _s01(kat):
    """S-01: två utgångar, en givare, utskjutare i korsningen."""
    b = Byggare(_hall("S-01", 16.0, 12.0), kat)
    b.transport("inbana", "bank://transport/band_600", 5000.0, vridningar=(0.0,))
    b.transport("utbana_ok", "bank://transport/band_400", 3000.0,
                vridningar=(0.0,))
    b.transport("utbana_nok", "bank://transport/band_400", 3000.0,
                vridningar=(90.0,))
    b.givare("fotocell", "bank://givare/reflex_fotocell")
    b.kraver(MotVagg("inbana", Vagg.SODER, marginal=Langd.m(2.0)),
             Framfor("utbana_ok", "inbana", avstand=Langd.mm(300.0)),
             TillVanster("utbana_nok", "inbana", avstand=Langd.mm(400.0)),
             Bredvid("fotocell", "inbana", mellanrum=Langd.mm(150.0)))
    return b.klar()


def _s02(kat):
    """S-02: tre utgångar i rad, alla nås från samma inbana."""
    b = Byggare(_hall("S-02", 18.0, 14.0), kat)
    b.transport("inbana", "bank://transport/band_600", 4000.0, vridningar=(0.0,))
    for i in range(3):
        b.transport("ut_%d" % i, "bank://transport/band_400", 2500.0,
                    vridningar=(0.0,))
    b.kraver(MotVagg("inbana", Vagg.VASTER, marginal=Langd.m(1.0)),
             Framfor("ut_0", "inbana", avstand=Langd.mm(400.0)),
             IRad(("ut_0", "ut_1", "ut_2"), Riktning.NORR, Langd.m(1.2)))
    return b.klar()


def _a01(kat):
    """A-01: fixtur med två matarbanor och robot, ur uppgiftens egen scen."""
    u = uppgift("A-01")
    roller = {k["role"]: k["uri"] for k in u["scene"]["components"]}
    b = Byggare(_hall("A-01", 14.0, 12.0), kat)
    b.robot("robot", roller["robot"])
    b.station("fixtur", roller["fixtur"])
    b.transport("matarbana_a", roller["matarbana_a"], 3000.0, vridningar=(0.0,))
    b.transport("matarbana_b", roller["matarbana_b"], 3000.0, vridningar=(0.0,))
    b.givare("lagesgivare_a", roller["lagesgivare_a"])
    b.kraver(CentreradI("robot"),
             InomRackvidd("fixtur", "robot", helt=False),
             InomRackvidd("matarbana_a", "robot", helt=False),
             InomRackvidd("matarbana_b", "robot", helt=False),
             MinstaAvstand("matarbana_a", "matarbana_b", Langd.m(0.6)),
             Bredvid("lagesgivare_a", "fixtur", mellanrum=Langd.mm(150.0)))
    return b.klar()


def _a03(kat):
    """A-03: två stationer i följd, förbundna av en ackumulerande rullbana."""
    b = Byggare(_hall("A-03", 20.0, 12.0,
                      zoner=[_gang("gang", 0.0, 9.0, 20.0, 12.0)]), kat)
    b.station("st250", "bank://station/fixtur_pneumatisk_spann",
              vridningar=(0.0,))
    b.station("st260", "bank://station/fixtur_pneumatisk_spann",
              vridningar=(0.0,))
    b.transport("rullbana", "bank://transport/rullbana_ackumulerande_500",
                4000.0, vridningar=(0.0,))
    b.kraver(MotVagg("st250", Vagg.SODER, marginal=Langd.m(1.0)),
             IRad(("st250", "st260"), Riktning.OSTER, Langd.m(5.0)),
             Bakom("rullbana", "st250", avstand=Langd.mm(600.0)),
             UtanforZon("st250", "gang"), UtanforZon("st260", "gang"),
             UtanforZon("rullbana", "gang"))
    return b.klar()


def _h01(kat):
    """H-01: robot lämnar över till band, med verktygsställ bredvid."""
    b = Byggare(_hall("H-01", 14.0, 12.0), kat)
    b.robot("robot", "bank://robot/kuka_kr10_r1100")
    b.transport("band", "bank://transport/band_400", 4000.0, vridningar=(0.0,))
    b.station("verktygsstall", "bank://station/verktygsstall")
    b.kraver(CentreradI("robot"),
             InomRackvidd("band", "robot", helt=False),
             InomRackvidd("verktygsstall", "robot", helt=False),
             MinstaAvstand("band", "verktygsstall", Langd.m(0.8)))
    return b.klar()


def _c01(kat):
    """C-01: komplett cell med två stationer, buffert, pelare och gång."""
    hall = _hall("C-01", 24.0, 16.0,
                 zoner=[_gang("gang", 0.0, 12.5, 24.0, 16.0),
                        Zon("utrymning", Zontyp.UTRYMNINGSVAG,
                            Rektangel.av(Langd.m(22.0), Langd.m(0.0),
                                         Langd.m(24.0), Langd.m(12.5)),
                            fri_hojd=Langd.m(2.2),
                            minsta_bredd=Langd.m(1.2))],
                 pelare=[Pelare("p1", Vek2.m(8.0, 6.0), Langd.mm(400.0),
                                Langd.mm(400.0)),
                         Pelare("p2", Vek2.m(16.0, 6.0), Langd.mm(400.0),
                                Langd.mm(400.0))])
    b = Byggare(hall, kat)
    b.transport("inbana", "bank://transport/band_600", 5000.0, vridningar=(0.0,))
    b.station("station_1", "bank://station/press_tvahands", vridningar=(0.0,))
    b.station("buffert", "bank://station/buffert_ackumulerande",
              vridningar=(0.0,))
    b.station("station_2", "bank://station/skruvstation", vridningar=(0.0,))
    b.robot("robot", "bank://robot/abb_irb_2600_20_1650")
    b.lastbarare("utpall", "bank://last/eur_pall", vridningar=(0.0,))
    b.kraver(MotVagg("inbana", Vagg.SODER, marginal=Langd.m(1.0)),
             Framfor("station_1", "inbana", avstand=Langd.m(1.0)),
             TillHoger("buffert", "station_1", avstand=Langd.m(1.0)),
             TillHoger("station_2", "buffert", avstand=Langd.m(1.0)),
             CentreradI("robot"),
             InomRackvidd("utpall", "robot", helt=False),
             UtanforZon("utpall", "gang"),
             UtanforZon("robot", "gang"))
    return b.klar()


def _t01_pelarhall(kat):
    """T-01 igen, men i en hall med pelare mitt i vägen. Samma facit."""
    hall = _hall("T-01-pelare", 14.0, 9.0,
                 pelare=[Pelare("mitt", Vek2.m(7.0, 2.0), Langd.mm(500.0),
                                Langd.mm(500.0))])
    b = Byggare(hall, kat)
    b.transport("band", "bank://transport/band_600", 6000.0, vridningar=(0.0,))
    b.givare("fotocell", "bank://givare/fotocell_genomgaende")
    b.kraver(MotVagg("band", Vagg.NORR, marginal=Langd.m(1.0)),
             Bredvid("fotocell", "band", mellanrum=Langd.mm(100.0)))
    return b.klar()


def _under_travers(kat):
    """En travers över halva hallen: pressen måste stå där taket räcker."""
    hall = _hall("travers", 14.0, 10.0,
                 zoner=[Zon("under_travers", Zontyp.ARBETSYTA,
                            Rektangel.av(Langd.m(0.0), Langd.m(0.0),
                                         Langd.m(7.0), Langd.m(10.0)),
                            takhojd=Langd.m(2.0))])
    b = Byggare(hall, kat)
    b.station("press", "bank://station/press_tvahands", vridningar=(0.0,))
    b.transport("band", "bank://transport/band_600", 4000.0, vridningar=(0.0,))
    b.kraver(Framfor("band", "press", avstand=Langd.m(1.0)))
    return b.klar()


# ---- överbestämda och omöjliga ------------------------------------------

def _ob_horn_och_mitt(kat):
    """Överbestämd: pallen ska stå både i hörnet och mitt i hallen."""
    b = Byggare(_hall("OB-horn-mitt", 10.0, 8.0), kat)
    b.lastbarare("pall", "bank://last/eur_pall", vridningar=(0.0,))
    b.kraver(IHorn("pall", Horn.SYDVAST), CentreradI("pall"))
    return b.klar()


def _ob_rackvidd(kat):
    """Överbestämd: fixturen ska stå mot östra väggen och nås av en robot
    som står mot den västra, i en hall bredare än räckvidden."""
    b = Byggare(_hall("OB-rackvidd", 20.0, 10.0), kat)
    b.robot("robot", "bank://robot/abb_irb_1200_5_0900")
    b.station("fixtur", "bank://station/fixtur_pneumatisk_spann",
              vridningar=(0.0,))
    b.kraver(MotVagg("robot", Vagg.VASTER, marginal=Langd.mm(500.0)),
             MotVagg("fixtur", Vagg.OSTER, marginal=Langd.mm(500.0)),
             InomRackvidd("fixtur", "robot", helt=False))
    return b.klar()


def _ob_tva_vaggar(kat):
    """Överbestämd: bandet ska stå mot både södra och norra väggen."""
    b = Byggare(_hall("OB-tva-vaggar", 12.0, 9.0), kat)
    b.transport("band", "bank://transport/band_600", 6000.0, vridningar=(0.0,))
    b.kraver(MotVagg("band", Vagg.SODER, marginal=Langd.mm(200.0)),
             MotVagg("band", Vagg.NORR, marginal=Langd.mm(200.0)))
    return b.klar()


def _ob_pa_for_liten(kat):
    """Överbestämd: en EUR-pall ska stå på en KLT-låda."""
    b = Byggare(_hall("OB-pa", 10.0, 8.0), kat)
    b.lastbarare("klt", "bank://last/klt_4147", vridningar=(0.0,))
    b.lastbarare("pall", "bank://last/eur_pall", vridningar=(0.0,))
    b.kraver(CentreradI("klt"), Pa("pall", "klt"))
    return b.klar()


def _ob_gangen(kat):
    """Överbestämd: pressen ska stå i gången, som ska hållas fri."""
    b = Byggare(_hall("OB-gang", 12.0, 10.0,
                      zoner=[_gang("gang", 0.0, 4.0, 12.0, 6.0)]), kat)
    b.station("press", "bank://station/press_tvahands", vridningar=(0.0,))
    b.kraver(IZon("press", "gang"))
    return b.klar()


def _ryms_inte(kat):
    """Ryms inte: åtta EUR-pallar i en hall om 3 x 3 m."""
    b = Byggare(_hall("RYMS-INTE", 3.0, 3.0), kat)
    for i in range(8):
        b.lastbarare("pall_%d" % i, "bank://last/eur_pall")
    return b.klar()


PROVSCENER = (
    Provscen("T-01", "T-01", "band mot vägg, givare och kassation", _t01,
             Status.LOST),
    Provscen("T-02", "T-02", "indexerad matare mot fixtur", _t02, Status.LOST),
    Provscen("T-03", "T-03", "två banor som flyter samman", _t03, Status.LOST),
    Provscen("T-04", "T-04", "buffert mellan in- och utflöde", _t04,
             Status.LOST),
    Provscen("P-01", "P-01", "robot, fixtur och KLT inom räckvidd", _p01,
             Status.LOST),
    Provscen("P-02", "P-02", "robot vid rörligt band", _p02, Status.LOST),
    Provscen("P-04", "P-04", "plock ur gitterbox med 3D-kamera", _p04,
             Status.LOST),
    Provscen("L-01", "L-01", "palleteringscell med fyra kolli på EUR-pall",
             _l01, Status.LOST),
    Provscen("L-02", "L-02", "två mellanlägg staplade på EUR-pall", _l02,
             Status.LOST),
    Provscen("L-03", "L-03", "avpalletering från kedjetransportör", _l03,
             Status.LOST),
    Provscen("S-01", "S-01", "två utgångar med utskjutare", _s01, Status.LOST),
    Provscen("S-02", "S-02", "tre utgångar i rad", _s02, Status.LOST),
    Provscen("A-01", "A-01", "fixtur med två matarbanor, ur uppgiftens scen",
             _a01, Status.LOST),
    Provscen("A-03", "A-03", "två stationer i rad med gång bakom", _a03,
             Status.LOST),
    Provscen("H-01", "H-01", "överlämning robot till band", _h01, Status.LOST),
    Provscen("C-01", "C-01", "komplett cell med pelare, gång och utrymningsväg",
             _c01, Status.LOST),
    Provscen("T-01-pelare", "T-01", "samma cell i en hall med pelare",
             _t01_pelarhall, Status.LOST),
    Provscen("TRAVERS", "T-02", "press under en travers med 2 m fri höjd",
             _under_travers, Status.LOST),
    Provscen("OB-horn-mitt", "L-01", "pall både i hörnet och centrerad",
             _ob_horn_och_mitt, Status.OVERBESTAMD),
    Provscen("OB-rackvidd", "P-01", "fixtur utanför robotens räckvidd",
             _ob_rackvidd, Status.OVERBESTAMD),
    Provscen("OB-tva-vaggar", "T-01", "band mot två motstående väggar",
             _ob_tva_vaggar, Status.OVERBESTAMD),
    Provscen("OB-pa", "L-01", "EUR-pall på en KLT-låda", _ob_pa_for_liten,
             Status.OVERBESTAMD),
    Provscen("OB-gang", "A-03", "press mitt i gången", _ob_gangen,
             Status.OVERBESTAMD),
    Provscen("RYMS-INTE", "L-01", "åtta EUR-pallar i en hall om 3 x 3 m",
             _ryms_inte, Status.RYMS_INTE),
)


# ---- mätningen -----------------------------------------------------------

def mat():
    """Kör alla provscener och MÄTER motorn. Inga påståenden, bara tal."""
    kat = katalog()
    per_scen = []
    for prov in PROVSCENER:
        scen, losning = prov.kor(kat)
        dom = losning.granskning
        if losning.status is Status.LOST and dom is None:
            dom = granska(losning.scen)
        anrop = ()
        if losning.status is Status.LOST:
            anrop = till_verktygsanrop(losning.scen, strikt=False)
        per_scen.append({
            "id": prov.id,
            "uppgift": prov.uppgift_id,
            "vantat": prov.vantat.value,
            "fick": losning.status.value,
            "enligt_facit": losning.status is prov.vantat,
            "noder": losning.noder,
            "objekt": len(scen.namn()),
            "overlapp": 0 if dom is None else dom.antal_overlapp,
            "granskning_ok": None if dom is None else dom.ok,
            "anrop": len(anrop),
            "konflikt": tuple(r.kod for r in losning.konflikt),
            "skal": losning.skal,
        })
    losta = [r for r in per_scen if r["fick"] == Status.LOST.value]
    vantade_losta = [r for r in per_scen if r["vantat"] == Status.LOST.value]
    vantade_ob = [r for r in per_scen if r["vantat"] == Status.OVERBESTAMD.value]
    return {
        "antal_scener": len(per_scen),
        "losta": len(losta),
        "vantade_losta": len(vantade_losta),
        "losta_av_vantade": sum(1 for r in vantade_losta if r["enligt_facit"]),
        "overbestamda_vantade": len(vantade_ob),
        "overbestamda_upptackta": sum(1 for r in vantade_ob if r["enligt_facit"]),
        # Falskt löst: motorn sa LOST men den oberoende granskningen hittade
        # något. Det här talet MÅSTE vara noll; det är fas 5:s grind.
        "falska_losta": sum(1 for r in losta if not r["granskning_ok"]),
        "overlapp_totalt": sum(r["overlapp"] for r in losta),
        "enligt_facit": sum(1 for r in per_scen if r["enligt_facit"]),
        "dyraste_sokning_noder": max(r["noder"] for r in per_scen),
        "anrop_totalt": sum(r["anrop"] for r in per_scen),
        "per_scen": tuple(per_scen),
    }


def rapport():
    """Mätningen som text, en rad per scen plus en summering."""
    m = mat()
    rader = ["PROVSCENER ur bank/uppgifter, mätt %d scener" % m["antal_scener"]]
    for r in m["per_scen"]:
        rader.append("  %-14s %-6s vantat=%-13s fick=%-13s %s objekt=%d "
                     "noder=%d overlapp=%d anrop=%d"
                     % (r["id"], r["uppgift"], r["vantat"], r["fick"],
                        "OK " if r["enligt_facit"] else "FEL",
                        r["objekt"], r["noder"], r["overlapp"], r["anrop"]))
        if r["konflikt"]:
            rader.append("        konflikt: " + ", ".join(r["konflikt"]))
    rader += [
        "SUMMA losta %d av %d vantade" % (m["losta_av_vantade"],
                                          m["vantade_losta"]),
        "SUMMA overbestamda upptackta %d av %d" % (m["overbestamda_upptackta"],
                                                   m["overbestamda_vantade"]),
        "SUMMA falska losta %d (grind: maste vara 0)" % m["falska_losta"],
        "SUMMA overlapp i losta layouter %d (grind: maste vara 0)"
        % m["overlapp_totalt"],
        "SUMMA enligt facit %d av %d" % (m["enligt_facit"], m["antal_scener"]),
        "SUMMA dyraste sokning %d noder" % m["dyraste_sokning_noder"],
        "SUMMA set_transform-anrop %d" % m["anrop_totalt"],
    ]
    return "\n".join(rader)
