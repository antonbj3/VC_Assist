# -*- coding: utf-8 -*-
"""Indexet over VC:s FAKTISKA komponentbibliotek, byggt ur filerna pa disk.

VARFOR DEN HAR FILEN FINNS
--------------------------
`verktyg/katalog.py` sa: "MATT 2026-09-04 i testprefixet: NOLL .vcmx-layouter
och FEM komponentfiler pa disk." Slutsatsen blev att det inte fanns nagot lokalt
bibliotek, och katalogverktygen serverade i stallet 65 handskrivna poster.

Slutsatsen var fel. Biblioteket ligger under

    <Public Documents>/Visual Components/<version>/Models/Components/

och den sokvagen ar inte gissad: VC:s EGEN eCatalog-uppdaterare skriver den i
sin logg ("Local folder: C:\\users\\Public\\Documents\\Visual Components\\4.10\\
Models"). Det ar samma felklass som M-34: ett tal som inte ror sig ar inget
bevis pa att ingenting finns - det kan vara ett bevis pa att man tittar pa fel
stalle.

SOKVAGEN ANTAS ALDRIG
---------------------
Operatorens invandning, och den ar ratt: det ska vara standard oavsett
VC-installation. Version, installationsplats, omdirigerade Dokument-mappar och
nataviserade bibliotek skiljer sig mellan maskiner, och VC:s Python-API kan inte
svara - sokning i indexets 3444 symboler efter "library" och "catalog" ger noll
akta traffar (M-55:s metod, samma vagg som M-38).

Modulen SOKER darfor, pa samma satt som install/upptackt.py gor for
tillaggsmappen, och RAPPORTERAR vad den hittade och var. En rot som inte hittas
ar ett tomt svar med skal, aldrig en gissad sokvag.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import zipfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

FORMAT = 1                      # Satt av M-58.

# Tva metadataposter inne i en .vcmx, och de bar olika saker.
#
# KATALOGPOSTEN ar den som raknas forst. MATT i M-76: den finns i 3201 av 3201
# komponenter, ar 2-3 kB stor, och hela biblioteket lases pa 0,5 SEKUNDER. Den
# bar DEKLARERADE falt - VCID, Name, Type, Manufacturer, Revision och
# IsDeprecated i 100 procent, MaxPayload i 93 och Reach i 80.
#
# MODELLEN ar 200-300 kB och bar komponentens inre: beteendena (som avgor
# familjen), granssnitten och parametrarna. Den lases bara i djupt lage, och
# kostar 12,8 s over biblioteket.
#
# Att katalogposten fanns hela tiden ar fjarde gangen i det har bygget som ett
# tal visade sig komma fran fel letstalle (M-34, M-57, M-69, och nu detta). Den
# forsta versionen av den har filen laste BARA modellen, harledde tillverkare
# och kategori ur KATALOGNAMNET, och lat databladslagret harleda rackvidden ur
# lanklangder - allt medan tre deklarerade falt lag i en fil pa tva kilobyte.
KATALOGPOST = "model.xml"
METADATA = "component.rsc"

# Ett deklarerat falt i katalogposten.
_EGENSKAP = re.compile(r'<Property name="([^"]+)">(.*?)</Property>', re.S)

# De falt vi laser ur katalogposten. Description utelamnas med flit: den ar
# hundratals ord bruksanvisning per komponent och skulle femdubbla indexet utan
# att hjalpa nagon att VALJA (M-60: informationen maste vara billig).
_KATALOGFALT = ("VCID", "Name", "Type", "Manufacturer", "MaxPayload", "Reach",
                "Tags", "Revision", "IsDeprecated", "Author")


def _katalogpost(z):
    """De deklarerade falten, eller {} om posten saknas."""
    if KATALOGPOST not in z.namelist():
        return {}
    try:
        text = z.read(KATALOGPOST).decode("utf-8", "replace")
    except (KeyError, OSError):
        return {}
    ut = {}
    for namn, varde in _EGENSKAP.findall(text):
        # Namnen forekommer i bada skiftlagen i biblioteket (imageuri mot
        # ImageUri). Vi laser skiftlagesokansligt och behaller det kanoniska.
        for kanon in _KATALOGFALT:
            if namn.lower() == kanon.lower():
                v = varde.strip()
                if v:
                    ut[kanon] = v
    return ut

_NAMN = re.compile(r'^\s*Name\s+"([^"]*)"', re.M)
_KATEGORI = re.compile(r'^\s*Category\s+"([^"]*)"', re.M)
_GRANSSNITT = re.compile(r'rSimInterface')

# Familjen lases ur STRUKTUREN, inte ur katalognamnet. Markorerna ar samma som
# datablad.FAMILJEMARKORER och star bara pa ett stalle i sak - de dubbleras har
# for att katalogindexet inte ska bero pa databladslagret. Provet som binder
# ihop dem heter tests/enhet/test_katalogindex.py::test_familjemarkorerna_ar_identiska_med_databladets
# - NAMNET star har med flit: den har kommentaren pastod i ett dygn att ett
# prov fanns, och det gjorde det inte. Ett lofte utan namn gar inte att
# kontrollera, och det ar precis darfor det overlevde (M-77).
#
# MATT (M-69): katalognamnet "Robots" har 1736 komponenter, men 466 robotar TILL
# ligger i kataloger som heter Archiv, Legacy, extra och ultra. For
# transportorer ar det varre: 45 i "Conveyors" och 182 utanfor. Ett sokskikt
# som filtrerar pa katalognamn missar alltsa var fjarde robot och fyra av fem
# transportorer.
#
# MATT (M-69) ocksa varfor detta bara finns i DJUPT lage: markoren ligger vid
# median 14 215 byte, p95 81 593 och max 1 151 329. En huvudlasning pa 4096
# byte hittar den i 2 procent av fallen.
_FAMILJEMARKORER = (
    ("robot", ("rSimRobotController", "rSimRrsRobotController")),
    ("transportor", ("rOneWayPath", "rTwoWayPath", "rSimCapacityBlock",
                     "rTransportNode")),
    ("verktyg", ("rToolContainer",)),
)


def _familj(text):
    """Familjen ur metadatans egen struktur, eller "" nar ingen markor finns.

    Tom strang och inte "ovrig": den som far tomt vet att fragan inte gick att
    besvara, medan "ovrig" later som ett svar.
    """
    for namn, markorer in _FAMILJEMARKORER:
        for m in markorer:
            if m in text:
                return namn
    return ""

# En parameter i metadatan. VC skriver dem som
#     Variable "rTVariable<rDouble>"
#     {
#       Name "ConveyorLength"
#       Value 500
# och typen i vinkelparentesen ar VC:s egen (rDouble, rInt, rBool, rString).
_PARAMETER = re.compile(
    r'Variable\s+"rTVariable<(\w+)>"\s*\{\s*Name\s+"([^"]+)"\s*\n\s*Value\s+([^\n]*)')

# Parametrar som beskriver ritning och tessellering, inte komponenten. De bar
# ingen information for den som ska VALJA en komponent, och de finns i nastan
# alla, sa de skulle dranka indexet.
#
# MATT: de sju nedan finns i 3193 av 3201 komponenter och sager darfor
# ingenting om NAGON av dem. Uri star INTE har - den bars av lika manga, men
# den ar komponentens identitet och det ar precis vad en agent behover.
_OINTRESSANTA = ("Brep", "TraceWidth", "Visible", "Name", "MaterialInherit",
                 "Layer", "CreaseAngle", "OnDemandLoad", "Pickable",
                 "ShowBackfaces", "ShowContent")


def _parametrar(text):
    """Namn -> varde ur metadatan, utan ritparametrarna.

    VARNING, matt i M-59: den har funktionen soker i HELA texten och far
    darfor med variabler som sitter inne i geometriprimitiver. `Length`,
    `Width` och `Height` finns i nastan varje komponent men ar dar en LADAS
    matt - Prorunner mk1 har namnet `Length` 24 ganger i sina 16 lador och
    noll ganger som komponentens egen egenskap. Indexets parameterlista ar
    alltsa en LISTA OVER VAD SOM NAMNS, inte over komponentens egenskaper.
    Den som vill ha komponentens egna varden ska ga via `datablad.py`, som
    laser rotnodens variabelrymd och ingenting annat.

    Schemat ar INTE enhetligt mellan tillverkare: det finns inget gemensamt
    Payload- eller Reach-falt. Varje komponentfamilj bar sina egna rattar, och
    indexet ska darfor bara VAD SOM FINNS i just den komponenten - aldrig ett
    antaget falt. Samma hallning som formagegrinden har mot API-ytor: prova vad
    som finns, anta aldrig.
    """
    ut = {}
    for m in _PARAMETER.finditer(text):
        namn = m.group(2)
        if any(o in namn for o in _OINTRESSANTA):
            continue
        varde = m.group(3).strip()
        if varde in ("", "{"):
            continue
        ut.setdefault(namn, varde[:80])
    return ut

# Sa manga byte av metadatan som lases nar bara namnet behovs.
#
# MATT i M-58 over 300 slumpade komponenter: Name ligger som mest vid byte 181.
# 4096 ger tjugo gangers marginal och kostar under tva procent av filen.
#
# VARNING som hor till samma matning: Category ligger vid MEDIAN 142 724 byte
# och nas darfor ALDRIG i grunt lage. Kategorin i ett grunt index kommer fran
# KATALOGNAMNET, inte ur metadatan. De tva sammanfaller ofta, och det ar precis
# darfor skillnaden ar farlig att glomma.
_HUVUD = 4096                   # Satt av M-58.


class Katalogfel(Exception):
    pass


@dataclass
class Post:
    namn: str
    tillverkare: str
    kategori: str
    sokvag: str
    storlek: int
    granssnitt: int = 0
    familj: str = ""
    vcid: str = ""
    rackvidd_mm: Optional[float] = None
    nyttolast_kg: Optional[float] = None
    utfasad: bool = False
    etiketter: str = ""
    revision: str = ""
    parametrar: Dict[str, str] = field(default_factory=dict)

    def till_json(self):
        d = {"namn": self.namn, "tillverkare": self.tillverkare,
             "kategori": self.kategori, "sokvag": self.sokvag,
             "storlek": self.storlek, "granssnitt": self.granssnitt}
        for nyckel, varde in (("vcid", self.vcid),
                              ("rackvidd_mm", self.rackvidd_mm),
                              ("nyttolast_kg", self.nyttolast_kg),
                              ("etiketter", self.etiketter),
                              ("revision", self.revision)):
            if varde not in (None, ""):
                d[nyckel] = varde
        if self.utfasad:
            d["utfasad"] = True
        if self.familj:
            d["familj"] = self.familj
        if self.parametrar:
            d["parametrar"] = self.parametrar
        return d


@dataclass
class Fynd:
    """En hittad biblioteksrot och HUR den hittades."""

    rot: str
    hur: str
    antal: int = 0


def kandidatrotter(hem: Optional[str] = None) -> List[Tuple[str, str]]:
    """(sokvag, hur) for de stallen ett VC-bibliotek kan ligga.

    Listan ar plattformsmedveten och ordnad efter hur troligt stallet ar. Den
    ar inte uttommande, och det ar meningen: `hitta` rapporterar vad den
    provade, sa en maskin dar biblioteket ligger nagon annanstans ger ett
    tomt svar med en lista i stallet for ett tyst fel.
    """
    hem = hem or os.path.expanduser("~")
    ut: List[Tuple[str, str]] = []
    if sys.platform.startswith("win"):
        publik = os.environ.get("PUBLIC", r"C:\Users\Public")
        ut.append((os.path.join(publik, "Documents"), "PUBLIC/Documents"))
        ut.append((os.path.join(hem, "Documents"), "anvandarens Documents"))
        ut.append((os.path.join(hem, "OneDrive", "Documents"),
                   "OneDrive-omdirigerad Documents"))
    else:
        # Under Wine ar Public Documents en riktig katalog i prefixet.
        for prefix in (os.environ.get("WINEPREFIX"),
                       os.path.join(hem, ".wine-vc-test"),
                       os.path.join(hem, ".wine")):
            if not prefix:
                continue
            ut.append((os.path.join(prefix, "drive_c", "users", "Public",
                                    "Documents"), "wine: Public/Documents"))
            ut.append((os.path.join(prefix, "drive_c", "users",
                                    os.path.basename(hem), "Documents"),
                       "wine: anvandarens Documents"))
        ut.append((os.path.join(hem, "Documents"), "hemkatalogens Documents"))
    return ut


def hitta(rotter: Optional[List[Tuple[str, str]]] = None,
          max_djup: int = 3) -> List[Fynd]:
    """Leta upp <nagonstans>/Visual Components/<version>/Models/Components.

    Versionen lases ur katalognamnet i stallet for att antas. En installation
    med tva versioner sida vid sida ger tva fynd, och det ar ratt svar - vilken
    som ska anvandas ar inte den har funktionens beslut.
    """
    ut: List[Fynd] = []
    for rot, hur in (rotter or kandidatrotter()):
        vc = os.path.join(rot, "Visual Components")
        if not os.path.isdir(vc):
            continue
        try:
            versioner = sorted(os.listdir(vc))
        except OSError:
            continue
        for v in versioner:
            komp = os.path.join(vc, v, "Models", "Components")
            if os.path.isdir(komp):
                ut.append(Fynd(komp, "%s, version %s" % (hur, v)))
    return ut


def _tal(text):
    """Ett tal ur ett deklarerat falt, eller None. Tomt och skrap ar None.

    None och inte 0.0: en robot utan angiven rackvidd har inte rackvidden noll,
    och den skillnaden ar hela poangen med falten (M-119 / E3a).
    """
    try:
        v = float(str(text).strip().replace(",", "."))
        return v if v > 0.0 else None
    except (TypeError, ValueError):
        return None


def _las(vcmx: str, djupt: bool) -> Optional[Post]:
    """En post ur en .vcmx.

    Katalogposten lases ALLTID - den ar 2-3 kB och bar de deklarerade falten.
    Modellen lases bara i djupt lage; den ar 200-300 kB och bar familjen,
    granssnitten och parametrarna.
    """
    try:
        with zipfile.ZipFile(vcmx) as z:
            namn_i_arkivet = z.namelist()
            kat = _katalogpost(z)
            text = ""
            if METADATA in namn_i_arkivet:
                if djupt:
                    text = z.read(METADATA).decode("utf-8", "replace")
                else:
                    with z.open(METADATA) as f:
                        text = f.read(_HUVUD).decode("utf-8", "replace")
            elif not kat:
                # Varken katalogpost eller modell: det har ar ingen komponent.
                return None
    except (zipfile.BadZipFile, OSError, KeyError):
        return None

    n = _NAMN.search(text) if text else None
    k = _KATEGORI.search(text) if text else None
    return Post(
        namn=(kat.get("Name") or (n.group(1) if n else
              os.path.splitext(os.path.basename(vcmx))[0])),
        # Tillverkaren ar DEKLARERAD i katalogposten (100 procent, M-76).
        # Katalognamnet anvands bara nar posten saknas.
        tillverkare=kat.get("Manufacturer", ""),
        # Likasa kategorin: Type ar deklarerad. Fore M-76 kom den ur
        # katalognamnet i grunt lage och ur modellen i djupt - tva olika
        # storheter som nastan alltid var lika (M-58).
        kategori=(kat.get("Type") or (k.group(1) if k else "")),
        sokvag=vcmx,
        storlek=os.path.getsize(vcmx),
        granssnitt=(len(_GRANSSNITT.findall(text)) if (djupt and text) else 0),
        familj=(_familj(text) if (djupt and text) else ""),
        vcid=kat.get("VCID", ""),
        rackvidd_mm=_tal(kat.get("Reach")),
        nyttolast_kg=_tal(kat.get("MaxPayload")),
        utfasad=(str(kat.get("IsDeprecated", "")).strip().lower() == "true"),
        etiketter=kat.get("Tags", ""),
        revision=kat.get("Revision", ""),
        parametrar=(_parametrar(text) if (djupt and text) else {}))


def bygg(rot: str, djupt: bool = False, skriv=None) -> Dict[str, object]:
    """Ga igenom biblioteket och lamna indexet.

    `djupt=False` laser bara metadatans huvud: namnet racker for att veta VAD
    som finns. `djupt=True` laser hela och kan da rakna granssnitt och plocka
    parametrar, till priset av att lasa narmare en gigabyte text.

    SKILLNADEN AR INTE BARA HASTIGHET (M-58). I grunt lage kommer `kategori`
    fran katalognamnet, i djupt lage ur metadatans eget Category-falt. De tva
    sammanfaller ofta men ar tva olika storheter, och den som jamfor dem
    jamfor apple med paron.
    """
    if not os.path.isdir(rot):
        raise Katalogfel("ingen biblioteksrot pa %s" % rot)
    t0 = time.time()
    poster: List[Post] = []
    olasliga: List[str] = []
    for katalog, _k, filer in os.walk(rot):
        rel = os.path.relpath(katalog, rot)
        delar = [d for d in rel.split(os.sep) if d not in (".", "")]
        tillverkare = delar[0] if delar else ""
        for f in sorted(filer):
            if not f.lower().endswith((".vcmx", ".vcm")):
                continue
            hel = os.path.join(katalog, f)
            post = _las(hel, djupt)
            if post is None:
                olasliga.append(hel)
                continue
            if not post.tillverkare:
                post.tillverkare = tillverkare
            if not post.kategori and len(delar) > 1:
                post.kategori = delar[-1]
            poster.append(post)
        if skriv and len(poster) % 500 == 0 and poster:
            skriv("  %d poster ..." % len(poster))
    return {
        "format": FORMAT,
        "rot": rot,
        "byggt": time.time(),
        "sekunder": round(time.time() - t0, 2),
        "djupt": bool(djupt),
        "antal": len(poster),
        "olasliga": olasliga,
        "tillverkare": sorted(set(p.tillverkare for p in poster if p.tillverkare)),
        "familjer": sorted(set(p.familj for p in poster if p.familj)),
        "poster": [p.till_json() for p in poster],
    }


def skriv_fil(index: Dict[str, object], sokvag: str) -> None:
    with open(sokvag, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, sort_keys=True, ensure_ascii=False)


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rot", help="biblioteksrot; annars soks den upp")
    p.add_argument("--ut", help="skriv indexet hit som JSON")
    p.add_argument("--djupt", action="store_true",
                   help="las hela metadatan och rakna granssnitt")
    a = p.parse_args(argv)

    if a.rot:
        rotter = [Fynd(a.rot, "angiven pa kommandoraden")]
    else:
        rotter = hitta()
        if not rotter:
            print("hittade inget bibliotek. Provade:")
            for rot, hur in kandidatrotter():
                print("  %-60s %s" % (rot, hur))
            return 1
    for f in rotter:
        print("bibliotek: %s\n  hittat via: %s" % (f.rot, f.hur))
    index = bygg(rotter[0].rot, djupt=a.djupt, skriv=print)
    print("%d komponenter, %d tillverkare, %d olasliga, %.1f s"
          % (index["antal"], len(index["tillverkare"]),
             len(index["olasliga"]), index["sekunder"]))
    if a.ut:
        skriv_fil(index, a.ut)
        print("skrivet: %s (%.1f MB)"
              % (a.ut, os.path.getsize(a.ut) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
