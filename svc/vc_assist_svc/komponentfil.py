# -*- coding: utf-8 -*-
"""Vad en .vcmx-fil FAKTISKT bar, och vad den inte bar.

VARFOR DEN HAR FILEN FINNS
--------------------------
Fas 5 stangdes pa 18 layouter, 117 objektpar och noll kollisioner. Allt var
lador. Layoutlosaren har aldrig sett en riktig komponent, och en riktig
komponent bar det en lada inte har: verklig omslutande volym, monteringsramar,
granssnitt med bestamda namn och typer, robotens rackvidd.

Fragan som avgor hela designen ar inte en asikt utan en matning: GAR MATTEN ATT
FA UR FILEN, ELLER KRAVS VC? Svaret star i M-61, och det ar delat:

  LAST ur filen      namn, kategori, tillverkare, rackvidd, nyttolast, taggar,
                     granssnittens namn och typer, ramarnas namn, ledernas
                     namn och granser, robotens rackviddsprofil
  HARLEDD ur filen   varje geometriblobbs EGEN lada (blobbarna ar Autodesk 3DS)
  SAKNAS i filen     komponentens SAMMANSATTA omslutande volym

Den sista raden ar den viktiga. Det finns inget faltet i nagon del av arkivet -
inte i model.xml, inte i component.rsc, och inte heller i VC:s egen
eCatalog-databas, som bara bar Reach. Skalet ar inte slarv: den omslutande
volymen ar ingen egenskap hos FILEN. Den ar en egenskap hos den BYGGDA
komponenten vid en viss parameteruppsattning och en viss stallning. En
transportors langd ar en parameter, en robots lada beror pa ledvinklarna, och
vilken geometri som alls syns styrs av switch-features. Att rakna fram den ur
filen ar att bygga om VC:s bygge.

Darfor: den omslutande volymen hamtas fran VC med `get_bounds` vid inladdning,
och tills dess ar den `SAKNAS`. Ett falt som datan inte bar far aldrig fyllas i
med en gissning som ser komplett ut.

VAR METADATAN LIGGER, OCH VARFOR M-58 MATTE PA FEL POST
--------------------------------------------------------
M-58 matte `Category` i `component.rsc` och fann den vid MEDIAN byte 142 724,
utom rackhall for ett grunt lage. Slutsatsen - att `kategori` i grunt lage ar
KATALOGNAMNET och inte komponentens eget falt - star fast och ar viktig.

Men arkivet bar en post till, och den ar liten: `model.xml`, omkring 1,5 kB,
med komponentens EGNA uppgifter i klartext. Hela biblioteket, 3201 filer, lases
pa 0,7 s. Kategorin darifran ar komponentens egen, inte katalogens.

FORMATEN
--------
* `model.xml`      XML, egenskaper som namn/varde. Litet, alltid narvarande.
* `component.rsc`  VC:s eget textformat: nycklar, strangar och klammerblock.
                   Trad, inte lista - features NASTLAS i varandra.
* `geo-*` m.fl.    Autodesk 3DS. Samma chunk-taggar (0x4D4D huvud, 0x4110
                   hornlista), sa hornen gar att lasa utan VC.
* `envelopeprofile` 3DS med en egen chunk 0x8001: robotens rackviddsprofil som
                   en polylinje i XZ-planet, i millimeter.
"""
from __future__ import annotations

import os
import re
import struct
import zipfile
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = ["Filfel", "Harkomst", "Falt", "Sektion", "Granssnitt",
           "Ram", "Led", "Geometri",
           "Lada", "Rackviddsprofil", "Komponentfakta", "las", "las_ur_zip",
           "las_profil", "tds_profil", "text_profil", "tds_lada",
           "POSTER_UTAN_GEOMETRI"]


class Filfel(Exception):
    """Filen gar inte att lasa som en VC-komponent."""


class Harkomst(object):
    """Var ett varde kom ifran. Tre lagen, aldrig underforstadda.

    LAST     stod i filen som ett eget falt
    HARLEDD  raknat ur filens innehall, med metoden namngiven
    SAKNAS   filen bar det inte. Det ar ett fullgott svar och far aldrig
             bytas mot en gissning som ser komplett ut.
    """

    LAST = "last"
    HARLEDD = "harledd"
    SAKNAS = "saknas"


#: Poster i arkivet som inte ar geometri. Allt annat behandlas som en
#: geometriblobb och provas som 3DS.
POSTER_UTAN_GEOMETRI = ("component.rsc", "model.xml", "component.dat",
                        "materials.dat", "layout_icon.tga",
                        "component_icon_preview.tga")


# ---------------------------------------------------------------------------
# component.rsc: tokenisering och trad
# ---------------------------------------------------------------------------

# En strang far bara innehalla \" och radfortsattning (\ + nyrad). Ett bart ord
# ar allt fram till blanksteg eller klammer. Nyraden ar en egen token, for den
# skiljer en skalarrad fran ett blockhuvud.
_TOKEN = re.compile(
    r'"(?P<str>(?:\\.|[^"\\])*)"'
    r'|(?P<klammer>[{}])'
    r'|(?P<nyrad>\n)'
    r'|(?P<ord>[^\s{}"]+)', re.S)

# Radfortsattning inne i en strang: ett omvant snedstreck sist pa raden.
_FORTS = re.compile(r'\\\n')


class Post(object):
    """En post i component.rsc: en nyckel, dess argument och dess barn.

    ``argument`` ar tokenlistan efter nyckeln. Ett citerat argument bar sitt
    innehall utan citattecken; ett bart ord bar sig sjalvt. ``barn`` ar tomt
    for en skalarrad och fyllt for ett klammerblock.
    """

    __slots__ = ("nyckel", "argument", "barn")

    def __init__(self, nyckel, argument, barn=None):
        self.nyckel = nyckel
        self.argument = tuple(argument)
        self.barn = barn if barn is not None else []

    @property
    def arg1(self):
        return self.argument[0] if self.argument else ""

    def hitta(self, nyckel, arg1=None):
        """Direkta barn med den nyckeln, och valfritt det forsta argumentet."""
        for b in self.barn:
            if b.nyckel == nyckel and (arg1 is None or b.arg1 == arg1):
                yield b

    def forsta(self, nyckel, arg1=None):
        for b in self.hitta(nyckel, arg1):
            return b
        return None

    def alla(self, nyckel, arg1=None):
        """Alla efterkommande, hur djupt som helst."""
        stapel = list(self.barn)
        while stapel:
            p = stapel.pop()
            if p.nyckel == nyckel and (arg1 is None or p.arg1 == arg1):
                yield p
            stapel.extend(p.barn)

    def __repr__(self):
        return "Post(%r, %r, %d barn)" % (self.nyckel, self.argument,
                                          len(self.barn))


def _tokenisera(text):
    """(sort, varde) for varje token. Sort ar 'str', 'ord', '{', '}' eller nyrad."""
    for m in _TOKEN.finditer(text):
        if m.lastgroup == "str":
            yield "str", _FORTS.sub("", m.group("str")).replace('\\"', '"')
        elif m.lastgroup == "klammer":
            yield m.group("klammer"), None
        elif m.lastgroup == "nyrad":
            yield "nyrad", None
        else:
            yield "ord", m.group("ord")


def tolka_rsc(text):
    """component.rsc som ett trad av Post. Rotens barn ar filens toppniva.

    Formen ar enkel men har en fallgrop: en nyckel foljd av en NYRAD och sedan
    en klammer ar ett BLOCKHUVUD, inte en skalarrad. Utan den blicken framat
    blir varje block anonymt och tradet obrukbart.
    """
    tokens = list(_tokenisera(text))
    rot = Post("", (), [])
    stapel = [rot]
    buffert = []
    i = 0
    n = len(tokens)
    while i < n:
        sort, varde = tokens[i]
        if sort == "nyrad":
            # Blicken framat: ar nasta betydelsebarande token en klammer ar
            # bufferten ett blockhuvud och ska inte tommas som skalarrad.
            j = i + 1
            while j < n and tokens[j][0] == "nyrad":
                j += 1
            if j < n and tokens[j][0] == "{":
                i += 1
                continue
            if buffert:
                stapel[-1].barn.append(Post(buffert[0], buffert[1:]))
                buffert = []
            i += 1
            continue
        if sort == "{":
            nyckel = buffert[0] if buffert else ""
            p = Post(nyckel, buffert[1:] if buffert else (), [])
            buffert = []
            stapel[-1].barn.append(p)
            stapel.append(p)
            i += 1
            continue
        if sort == "}":
            if buffert:
                stapel[-1].barn.append(Post(buffert[0], buffert[1:]))
                buffert = []
            if len(stapel) > 1:
                stapel.pop()
            i += 1
            continue
        buffert.append(varde)
        i += 1
    if buffert:
        stapel[-1].barn.append(Post(buffert[0], buffert[1:]))
    return rot


# ---------------------------------------------------------------------------
# Autodesk 3DS: hornlistorna i geometriblobbarna
# ---------------------------------------------------------------------------

# Chunk-taggar ur 3DS-formatet. De ar formatets, inte vara, och star darfor
# som hexadecimala tal med samma namn som i formatbeskrivningen.
_TDS_HUVUD = 0x4D4D
_TDS_REDIGERING = 0x3D3D
_TDS_OBJEKT = 0x4000
_TDS_MESH = 0x4100
_TDS_HORN = 0x4110
_TDS_PROFIL = 0x8001     # VC:s egen chunk i envelopeprofile

# Chunkhuvudet ar tva byte tagg plus fyra byte storlek, och storleken RAKNAR IN
# huvudet. Talet kommer ur 3DS-formatet sjalvt; att blobbarna ar 3DS ar det
# M-61 matte.
_TDS_HUVUDSTORLEK = 6           # Satt av M-61 (3DS-formatets chunkhuvud).


def _tds_strang(d, off):
    slut = d.index(b"\0", off)
    return d[off:slut].decode("latin-1"), slut + 1


def _tds_sok(d, off, slut, sokt):
    """(offset, storlek) for varje chunk med taggen sokt, rekursivt."""
    ut = []
    while off + _TDS_HUVUDSTORLEK <= slut:
        tagg, storlek = struct.unpack_from("<HI", d, off)
        if storlek < _TDS_HUVUDSTORLEK or off + storlek > slut:
            break
        if tagg == sokt:
            ut.append((off, storlek))
        if tagg in (_TDS_HUVUD, _TDS_REDIGERING, _TDS_OBJEKT, _TDS_MESH):
            b = off + _TDS_HUVUDSTORLEK
            if tagg == _TDS_OBJEKT:
                try:
                    _namn, b = _tds_strang(d, b)
                except ValueError:
                    b = slut
            ut.extend(_tds_sok(d, b, off + storlek, sokt))
        off += storlek
    return ut


class Lada(object):
    """En axelriktad lada i millimeter, med sin harkomst."""

    __slots__ = ("min_mm", "max_mm", "harkomst", "metod")

    def __init__(self, min_mm, max_mm, harkomst, metod=""):
        self.min_mm = tuple(float(v) for v in min_mm)
        self.max_mm = tuple(float(v) for v in max_mm)
        self.harkomst = harkomst
        self.metod = metod

    @property
    def storlek_mm(self):
        return tuple(self.max_mm[i] - self.min_mm[i] for i in range(3))

    def __repr__(self):
        return ("Lada(%.1f x %.1f x %.1f mm, %s)"
                % (self.storlek_mm + (self.harkomst,)))


def tds_lada(data):
    """Lada over ALLA hornlistor i en 3DS-blobb, i blobbens EGEN ram.

    Ger None om blobben inte ar 3DS eller saknar horn. Ladan ar geometrins
    egen; var geometrin sitter i komponenten styrs av transformkedjan i
    component.rsc och ligger INTE har.
    """
    if data[:2] != b"MM":
        return None
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    horn = 0
    for off, storlek in _tds_sok(data, 0, len(data), _TDS_HORN):
        try:
            antal = struct.unpack_from("<H", data, off + _TDS_HUVUDSTORLEK)[0]
        except struct.error:
            continue
        b = off + _TDS_HUVUDSTORLEK + 2
        if b + 12 * antal > off + storlek:
            continue
        v = struct.unpack_from("<%df" % (3 * antal), data, b)
        horn += antal
        for i in range(antal):
            for k in range(3):
                x = v[3 * i + k]
                if x < lo[k]:
                    lo[k] = x
                if x > hi[k]:
                    hi[k] = x
    if horn == 0:
        return None, 0
    return Lada(lo, hi, Harkomst.HARLEDD, "3DS-hornlistor"), horn


class Rackviddsprofil(object):
    """Robotens rackviddsprofil: en polylinje i XZ-planet, i millimeter.

    Den ligger i arkivposten `envelopeprofile` och ar VC:s egen chunk 0x8001 i
    en 3DS-fil. Avkodningen ar KORSPROVAD: profilens storsta |x| ar exakt lika
    med `Reach` i model.xml, och de tva falten kommer ur olika delar av
    arkivet. En avkodning som traffar ett oberoende tal ar matt, inte gissad.
    """

    __slots__ = ("segment",)

    def __init__(self, segment):
        self.segment = tuple(segment)

    @property
    def radie_mm(self):
        """Storsta avstand fran robotens egen axel. Rackvidden."""
        return max((abs(p[0]) for s in self.segment for p in s), default=0.0)

    @property
    def z_mm(self):
        v = [p[2] for s in self.segment for p in s]
        return (min(v), max(v)) if v else (0.0, 0.0)

    def __len__(self):
        return len(self.segment)

    def __repr__(self):
        return ("Rackviddsprofil(%d segment, radie %.1f mm, z %.1f..%.1f mm)"
                % ((len(self.segment), self.radie_mm) + self.z_mm))


def _profilsegment(nyttolast):
    """Segmenten ur en 0x8001-nyttolast. Tva varianter, bada EXAKT matchade.

    Biblioteket bar tva layouter under samma chunk, och kravet pa bada ar
    detsamma: den lasta strukturen ska ta slut precis dar nyttolasten tar
    slut. Det kravet ar hela skyddet mot att lasa brus som geometri.

      A  uint16 reserv, uint16 antal segment, sedan per segment uint16
         punktantal foljt av punkter som tre float64. 695 av 702 filer.
      B  uint32 0, uint32 1, uint16 punktantal, sedan EN polylinje. 7 filer.

    Ger [] nar ingen av dem passar exakt.
    """
    p = nyttolast
    if len(p) >= 4:
        antal = struct.unpack_from("<H", p, 2)[0]
        b = 4
        segment = []
        for _ in range(antal):
            if b + 2 > len(p):
                segment = []
                break
            n = struct.unpack_from("<H", p, b)[0]
            b += 2
            if n == 0 or b + 24 * n > len(p):
                segment = []
                break
            segment.append(tuple(struct.unpack_from("<3d", p, b + 24 * i)
                                 for i in range(n)))
            b += 24 * n
        if segment and b == len(p):
            return segment
    if len(p) >= 10:
        noll, ett, n = struct.unpack_from("<IIH", p, 0)
        if noll == 0 and ett == 1 and n > 1 and 10 + 24 * n == len(p):
            punkter = [struct.unpack_from("<3d", p, 10 + 24 * i)
                       for i in range(n)]
            return [(punkter[k], punkter[k + 1])
                    for k in range(len(punkter) - 1)]
    return []


def tds_profil(data):
    """Rackviddsprofilen ur en 3DS-formad `envelopeprofile`-blobb, eller None.

    Chunken hittas i forsta hand genom att ga tradet. Gar tradet sonder - och
    det gor det i 7 av 702 filer, dar objektet TRACE bar en oforklarad tvabyte
    mellan sina barn - soks chunken i stallet med en BYTESOKNING, och da ar
    det den exakta langdmatchningen i `_profilsegment` som avgor om fyndet
    duger. Ett fynd som inte gar jamnt ut kastas, for en polylinje som lases
    ur brus ser ut som en matning.
    """
    if data[:2] != b"MM":
        return None
    segment = []
    for off, storlek in _tds_sok(data, 0, len(data), _TDS_PROFIL):
        segment.extend(_profilsegment(data[off + _TDS_HUVUDSTORLEK:
                                           off + storlek]))
    if not segment:
        for off in range(0, max(len(data) - _TDS_HUVUDSTORLEK, 0)):
            if data[off] != 0x01 or data[off + 1] != 0x80:
                continue
            storlek = struct.unpack_from("<I", data, off + 2)[0]
            if storlek < 16 or off + storlek > len(data):
                continue
            segment.extend(_profilsegment(data[off + _TDS_HUVUDSTORLEK:
                                               off + storlek]))
    return Rackviddsprofil(segment) if segment else None


def text_profil(data):
    """Rackviddsprofilen ur den TEXTFORMADE varianten, eller None.

    Biblioteket bar TVA format under samma postnamn, och det ar precis den
    sortens skillnad som gor ett svep till en halv matning om man laser bara
    det ena: 498 av 702 `envelopeprofile` ar 3DS, och de ovriga 204 ar ren
    text. Textvarianten ar rader dar ett bart heltal N foljs av N rader med
    tre tal - punkterna - och senare av N rader med tva tal, kanterna.

    Punkterna lases; kanterna behovs inte for radien och lases darfor inte.
    """
    if data[:2] == b"MM":
        # 3DS-varianten. Att leta text i binart innehall kan trafa av en
        # slump, och en slumptraff ar varre an ett tomt svar.
        return None
    try:
        rader = data.decode("latin-1").split("\n")
    except (UnicodeDecodeError, AttributeError):
        return None
    punkter = []
    i = 0
    while i < len(rader):
        rad = rader[i].strip()
        i += 1
        if not rad or " " in rad or "." in rad:
            continue
        try:
            n = int(rad)
        except ValueError:
            continue
        if n <= 0 or i + n > len(rader):
            continue
        block = []
        for j in range(i, i + n):
            delar = rader[j].split()
            if len(delar) != 3:
                block = []
                break
            try:
                block.append(tuple(float(x) for x in delar))
            except ValueError:
                block = []
                break
        if block:
            punkter.extend(block)
            i += n
    if not punkter:
        return None
    # Punktlistan ar en polylinje. Segmenten byggs av foljande par, vilket
    # racker for radien och for z-omfanget; kantlistan i filen skulle ge den
    # exakta ordningen men behovs inte for de tva talen.
    return Rackviddsprofil([(punkter[k], punkter[k + 1])
                            for k in range(len(punkter) - 1)])


def las_profil(data):
    """Rackviddsprofilen, oavsett vilket av de tva formaten posten bar."""
    return tds_profil(data) or text_profil(data)


# ---------------------------------------------------------------------------
# Uppgifterna ur component.rsc
# ---------------------------------------------------------------------------

class Falt(object):
    """Ett falt i en granssnittssektion: dess typ och de tal typen bar.

    ``mount`` finns bara i ett `rSimHierarchyField` och ar riktningen: 1 
    betyder att granssnittet MONTERAS pa nagot, 0 att det tar emot. ``port``
    finns bara i ett `rSimFlowField` och ar 0 for in och 1 for ut.
    """

    __slots__ = ("sort", "namn", "func", "port", "mount", "nod", "ram")

    def __init__(self, sort, namn="", func=None, port=None, mount=None,
                 nod=None, ram=None):
        self.sort = sort
        self.namn = namn
        self.func = func
        self.port = port
        self.mount = mount
        self.nod = nod
        self.ram = ram

    def __repr__(self):
        delar = ["%s %r" % (self.sort, self.namn)]
        for etikett, v in (("func", self.func), ("port", self.port),
                           ("mount", self.mount), ("ram", self.ram)):
            if v is not None:
                delar.append("%s=%r" % (etikett, v))
        return "Falt(%s)" % ", ".join(delar)


class Sektion(object):
    """En sektion i ett granssnitt: dess namn, dess ram och dess falt."""

    __slots__ = ("namn", "ram", "falt", "mall")

    def __init__(self, namn, ram=None, falt=(), mall=False):
        self.namn = namn
        self.ram = ram
        self.falt = tuple(falt)
        self.mall = bool(mall)

    @property
    def falttyper(self):
        return tuple(sorted(set(f.sort for f in self.falt)))

    def __repr__(self):
        return ("Sektion(%r, ram=%r, %d falt)"
                % (self.namn, self.ram, len(self.falt)))


class Granssnitt(object):
    """Ett granssnitt med sitt NAMN, sina sektioner och sina falttyper.

    Det ar det en lada inte har. En generisk kontakt gar att koppla till vad
    som helst; ett `rSimFlowField` med Port 0 i sektionen `Section` pa ramen
    `Start` gar att koppla till precis det som lamnar ifran sig floden, och
    ingenting annat.
    """

    __slots__ = ("namn", "sort", "abstrakt", "sektioner", "redigeringsnamn")

    def __init__(self, namn, sort, abstrakt, sektioner, redigeringsnamn=""):
        self.namn = namn
        self.sort = sort
        self.abstrakt = bool(abstrakt)
        self.sektioner = tuple(sektioner)
        self.redigeringsnamn = redigeringsnamn

    @property
    def ramar(self):
        return tuple(sorted(set(s.ram for s in self.sektioner if s.ram)))

    @property
    def falttyper(self):
        return tuple(sorted(set(f.sort for s in self.sektioner
                                for f in s.falt)))

    @property
    def monterar(self):
        """Monteras granssnittet PA nagot? None nar datan inte sager det."""
        v = set(f.mount for s in self.sektioner for f in s.falt
                if f.mount is not None)
        if len(v) == 1:
            return bool(v.pop())
        return None

    @property
    def portar(self):
        return tuple(sorted(set(f.port for s in self.sektioner for f in s.falt
                                if f.port is not None)))

    def __repr__(self):
        return ("Granssnitt(%r, %s, ramar=%r, falt=%r)"
                % (self.namn, self.sort, self.ramar, self.falttyper))


class Ram(object):
    """En monteringsram: ett namngivet lage nagot far sitta i.

    ``lage_mm`` ar ramens lage i sin EGNA nods ram, last ur en konstant
    matris. Ar kedjan parametrisk - och det ar den ofta, for VC skriver
    transformer som uttryck over komponentens parametrar - ar lage_mm None och
    harkomsten SAKNAS. Namnet ar last i bada fallen.
    """

    __slots__ = ("namn", "lage_mm", "harkomst", "uttryck")

    def __init__(self, namn, lage_mm=None, harkomst=Harkomst.SAKNAS,
                 uttryck=None):
        self.namn = namn
        self.lage_mm = lage_mm
        self.harkomst = harkomst
        self.uttryck = uttryck

    def __repr__(self):
        if self.lage_mm is None:
            return "Ram(%r, lage %s)" % (self.namn, self.harkomst)
        return ("Ram(%r, (%.1f, %.1f, %.1f) mm)"
                % ((self.namn,) + tuple(self.lage_mm)))


class Led(object):
    """En led: namn, frihetsgrad och granser."""

    __slots__ = ("namn", "sort", "min_varde", "max_varde")

    def __init__(self, namn, sort, min_varde=None, max_varde=None):
        self.namn = namn
        self.sort = sort
        self.min_varde = min_varde
        self.max_varde = max_varde

    def __repr__(self):
        return "Led(%r, %s, %s..%s)" % (self.namn, self.sort,
                                        self.min_varde, self.max_varde)


class Geometri(object):
    """En geometripost: vilken blobb, hur den ar placerad, och blobbens lada."""

    __slots__ = ("namn", "uri", "placering", "lada", "horn")

    #: Placeringens tre lagen. Skillnaden mellan dem ar hela svaret pa fragan
    #: om den omslutande volymen gar att rakna fram ur filen.
    KONSTANT = "konstant"     # hela kedjan ar fasta matriser
    UTTRYCK = "uttryck"       # nagon transform ar ett uttryck over parametrar
    VILLKORAD = "villkorad"   # en switch-feature avgor om den alls syns

    def __init__(self, namn, uri, placering, lada=None, horn=0):
        self.namn = namn
        self.uri = uri
        self.placering = placering
        self.lada = lada
        self.horn = horn

    def __repr__(self):
        return "Geometri(%r, %s, %s)" % (self.namn, self.placering, self.lada)


#: Enhetsmatrisen, radvis. VC skriver 4x4 radvis med translationen i element
#: 12, 13 och 14 - samma form som `Location`-raden sist i varje component.rsc.
_ENHET = (1.0, 0.0, 0.0, 0.0,
          0.0, 1.0, 0.0, 0.0,
          0.0, 0.0, 1.0, 0.0,
          0.0, 0.0, 0.0, 1.0)


def _matris(post):
    """Postens egna 4x4-matris som sexton float, eller None.

    Ar det inte sexton tal ar raden inte en matris, och svaret ar None i
    stallet for en tolkning. En halvlast matris ar varre an ingen.
    """
    m = post.forsta("Matrix")
    if m is None or len(m.argument) != 16:
        return None
    try:
        return tuple(float(x) for x in m.argument)
    except ValueError:
        return None


def _mult(a, b):
    """a * b, radvis 4x4. En punkt ar en RADVEKTOR: p' = p * M."""
    ut = []
    for rad in range(4):
        for kol in range(4):
            ut.append(sum(a[rad * 4 + k] * b[k * 4 + kol] for k in range(4)))
    return tuple(ut)


def _lage(m):
    return (m[12], m[13], m[14])


def _struktur_ur(rot):
    """Rakna tradets delar. Talen bar M-61:s slutsats om den omslutande volymen.

    En rTransformFeature bar antingen en fast Matrix, ett Expression, eller
    bada. Bara den forsta sorten gar att lasa; de andra tva kraver att VC:s
    uttrycksprak vardefas mot komponentens parametrar.
    """
    r = {"transform_totalt": 0, "transform_med_matris": 0,
         "transform_med_uttryck": 0, "switchar": 0, "noder": 0,
         "nodoffset_uttryck": 0}
    for p in rot.alla("Feature", "rTransformFeature"):
        r["transform_totalt"] += 1
        if p.forsta("Matrix") is not None:
            r["transform_med_matris"] += 1
        if _uttryckstext(p):
            r["transform_med_uttryck"] += 1
    for _ in rot.alla("Feature", "rSwitchFeature"):
        r["switchar"] += 1
    for p in rot.alla("Node"):
        if not p.barn:
            continue
        r["noder"] += 1
        if _uttryckstext(p, "Offset"):
            r["nodoffset_uttryck"] += 1
    return r


def _heltal(post, nyckel):
    p = post.forsta(nyckel)
    if p is None or not p.argument:
        return None
    try:
        return int(p.arg1)
    except ValueError:
        return None


def _strang(post, nyckel):
    p = post.forsta(nyckel)
    return p.arg1 if p is not None and p.argument else None


def _falt_ur(sektion):
    ut = []
    stapel = list(sektion.barn)
    while stapel:
        q = stapel.pop()
        if q.nyckel.startswith("rSim") and q.nyckel.endswith("Field"):
            ut.append(Falt(q.nyckel, _strang(q, "Name") or "",
                           func=_strang(q, "Func"),
                           port=_heltal(q, "Port"),
                           mount=_heltal(q, "Mount"),
                           nod=_strang(q, "Node"),
                           ram=_strang(q, "Frame")))
        stapel.extend(q.barn)
    return sorted(ut, key=lambda f: (f.sort, f.namn))


def _granssnitt_ur(rot):
    ut = []
    for sort in ("rSimInterface", "rSimDynamicInterface"):
        for p in rot.alla("Functionality", sort):
            sektioner = []
            for mall, nyckel in ((False, "Section"), (True, "TemplateSection")):
                for s in p.hitta(nyckel):
                    sektioner.append(Sektion(_strang(s, "Name") or "",
                                             _strang(s, "Frame"),
                                             _falt_ur(s), mall))
            abstrakt = any(a.arg1 == "1" for a in p.hitta("Abstract"))
            ut.append(Granssnitt(_strang(p, "Name") or "", sort, abstrakt,
                                 sektioner,
                                 _strang(p, "ConnectionEditName") or ""))
    return tuple(ut)


class _Kedja(object):
    """Laget i tradet: transformerna ovanfor, och om nagot av dem ar okant.

    Tre saker gor ett lage OLASBART ur filen, och alla tre ar vanliga:

      uttryck    en transform eller en nodoffset ar ett uttryck over
                 komponentens parametrar
      led        en nod bar en rorlig led, sa laget beror pa stallningen
      okand_nod  en nod utan Offset. Att den skulle vara enhetsmatrisen ar
                 en GISSNING, och en gissning som nastan alltid stammer ar
                 precis den sortens fel M-58 handlade om

    Bara den tomma kedjan - inget av de tre, och inga transformer alls - ger
    ett last lage, och det laget ar komponentens eget origo.
    """

    __slots__ = ("matriser", "uttryck", "led", "okand_nod", "villkorad")

    def __init__(self, matriser=(), uttryck=None, led=False, okand_nod=False,
                 villkorad=False):
        self.matriser = matriser
        self.uttryck = uttryck
        self.led = led
        self.okand_nod = okand_nod
        self.villkorad = villkorad

    @property
    def okand(self):
        return bool(self.uttryck) or self.led or self.okand_nod

    def med(self, **kw):
        d = {"matriser": self.matriser, "uttryck": self.uttryck,
             "led": self.led, "okand_nod": self.okand_nod,
             "villkorad": self.villkorad}
        d.update(kw)
        return _Kedja(**d)

    def skal(self):
        if self.uttryck:
            return self.uttryck
        if self.led:
            return "en rorlig led i kedjan; laget beror pa stallningen"
        if self.okand_nod:
            return "en nod utan Offset; dess eget lage star inte i filen"
        return None

    def lage(self):
        m = _ENHET
        for x in self.matriser:
            m = _mult(x, m)
        return _lage(m)


def _uttryckstext(post, nyckel="Transform"):
    """Uttryckets text, eller "" nar det inte finns eller ar tomt.

    VC skriver `Expression ""` i 6950 av bibliotekets 39 171 transformer. En
    TOM strang ar inget uttryck - den betyder att transformen inte har nagon
    parametrisk del - och att rakna den som ett uttryck hade blast upp
    matningen med sjutton procent. Det ar samma sorts fel som att lasa
    `Extention` som `Extent`.
    """
    b = post.forsta(nyckel)
    e = b.forsta("Expression") if b is not None else None
    return e.arg1.strip() if e is not None and e.argument else ""


def _nodkedja(nod, kedja):
    """Kedjan efter att ha gatt in i en nod."""
    d = nod.forsta("Dof")
    if d is not None and d.argument and d.arg1 != "Fixed":
        kedja = kedja.med(led=True)
    o = nod.forsta("Offset")
    if o is None:
        return kedja.med(okand_nod=True)
    txt = _uttryckstext(nod, "Offset")
    if txt:
        return kedja.med(uttryck=kedja.uttryck or txt)
    m = _matris(o)
    if m is None:
        return kedja.med(okand_nod=True)
    return kedja.med(matriser=kedja.matriser + (m,))


def _trad_ur(rot):
    """Gar hela tradet EN gang och lamnar (ramar, geometri).

    Kedjan gas UPPIFRAN: en ram och en geometripost arver varje transform,
    varje nod och varje switch de ligger under. Det ar precis det som gor den
    sammansatta ladan till nagot annat an en summa av blobbar.
    """
    ramar = []
    geometri = []

    def ga(post, kedja, rotniva):
        for b in post.barn:
            k, rn = kedja, rotniva
            if b.nyckel == "Node" and b.barn:
                # Bara ett block ar en nod. `Node "mountplate"` inne i ett
                # granssnittsfalt ar en HANVISNING till en nod, inte en nod.
                if not rotniva:
                    k = _nodkedja(b, kedja)
                rn = False
            elif b.nyckel == "Feature" and b.arg1 == "rTransformFeature":
                txt = _uttryckstext(b)
                if txt:
                    k = kedja.med(uttryck=kedja.uttryck or txt)
                m = _matris(b)
                if m is not None:
                    k = k.med(matriser=k.matriser + (m,))
                elif not txt:
                    # Varken uttryck eller matris. Att den da ar
                    # enhetsmatrisen ar troligt och OPROVAT, sa kedjan blir
                    # okand i stallet for antagen.
                    k = k.med(okand_nod=True)
            elif b.nyckel == "Feature" and b.arg1 == "rSwitchFeature":
                k = kedja.med(villkorad=True)
            elif b.nyckel == "Feature" and b.arg1 == "rFrameFeature":
                namn = b.forsta("Name")
                namn = namn.arg1 if namn is not None else ""
                egen = _matris(b)
                txt = _uttryckstext(b)
                if txt:
                    ramar.append(Ram(namn, None, Harkomst.SAKNAS, txt))
                elif kedja.okand:
                    ramar.append(Ram(namn, None, Harkomst.SAKNAS,
                                     kedja.skal()))
                elif egen is not None:
                    hel = kedja.med(matriser=kedja.matriser + (egen,))
                    ramar.append(Ram(namn, hel.lage(),
                                     Harkomst.LAST if not kedja.matriser
                                     else Harkomst.HARLEDD))
                elif kedja.matriser:
                    ramar.append(Ram(namn, kedja.lage(), Harkomst.HARLEDD))
                else:
                    # Ingen transform, ingen nod och inget uttryck ovanfor:
                    # ramen ligger i komponentens EGET origo.
                    ramar.append(Ram(namn, (0.0, 0.0, 0.0), Harkomst.LAST))
            elif b.nyckel == "Feature" and b.arg1 == "rGeoFeature":
                namn = b.forsta("Name")
                uri = None
                for var in b.alla("Variable"):
                    n = var.forsta("Name")
                    if n is not None and n.arg1 == "Uri":
                        w = var.forsta("Value")
                        if w is not None and w.argument:
                            uri = w.arg1
                placering = (Geometri.VILLKORAD if kedja.villkorad
                             else Geometri.UTTRYCK if kedja.okand
                             else Geometri.KONSTANT)
                geometri.append(Geometri(namn.arg1 if namn else "", uri,
                                         placering))
            ga(b, k, rn)

    ga(rot, _Kedja(), True)
    return tuple(ramar), geometri


def _leder_ur(rot):
    ut = []
    for p in rot.alla("Dof"):
        if not p.argument or p.arg1 == "Fixed":
            continue
        namn = p.forsta("Name")
        mn = p.forsta("MinLimit")
        mx = p.forsta("MaxLimit")

        def _tal(post):
            if post is None:
                return None
            e = post.forsta("Expression")
            if e is not None:
                try:
                    return float(e.arg1)
                except ValueError:
                    return None
            if post.argument:
                try:
                    return float(post.arg1)
                except ValueError:
                    return None
            return None
        ut.append(Led(namn.arg1 if namn else "", p.arg1, _tal(mn), _tal(mx)))
    return tuple(ut)


# ---------------------------------------------------------------------------
# Fakta om en komponent
# ---------------------------------------------------------------------------

_EGENSKAP = re.compile(r'<Property name="([^"]+)">(.*?)</Property>', re.S)


class Komponentfakta(object):
    """Allt filen bar om en komponent, med harkomst pa varje falt."""

    __slots__ = ("sokvag", "namn", "kategori", "tillverkare", "rackvidd_mm",
                 "nyttolast_kg", "taggar", "utfasad", "beskrivning",
                 "granssnitt", "ramar", "leder", "geometri", "profil",
                 "lada", "lada_skal", "djupt", "egenskaper", "struktur")

    def __init__(self, sokvag, namn, kategori, tillverkare, rackvidd_mm=None,
                 nyttolast_kg=None, taggar=(), utfasad=False, beskrivning="",
                 granssnitt=(), ramar=(), leder=(), geometri=(), profil=None,
                 lada=None, lada_skal="", djupt=False, egenskaper=None,
                 struktur=None):
        self.sokvag = sokvag
        self.namn = namn
        self.kategori = kategori
        self.tillverkare = tillverkare
        self.rackvidd_mm = rackvidd_mm
        self.nyttolast_kg = nyttolast_kg
        self.taggar = tuple(taggar)
        self.utfasad = bool(utfasad)
        self.beskrivning = beskrivning
        self.granssnitt = tuple(granssnitt)
        self.ramar = tuple(ramar)
        self.leder = tuple(leder)
        self.geometri = tuple(geometri)
        self.profil = profil
        self.lada = lada
        self.lada_skal = lada_skal
        self.djupt = bool(djupt)
        self.egenskaper = dict(egenskaper or {})
        # Rakningen av tradets egna delar. Den bar svaret pa varfor den
        # sammansatta ladan inte gar att rakna fram: en transform som bara
        # bar ett UTTRYCK kraver att uttrycket vardefas, och det ar VC:s
        # arbete, inte filens innehall.
        self.struktur = dict(struktur or {})

    @property
    def lada_harkomst(self):
        return self.lada.harkomst if self.lada is not None else Harkomst.SAKNAS

    def granssnittsnamn(self):
        return tuple(g.namn for g in self.granssnitt if g.namn)

    def ramnamn(self):
        return tuple(r.namn for r in self.ramar if r.namn)

    def __repr__(self):
        return ("Komponentfakta(%r, %s, %s, lada=%s)"
                % (self.namn, self.tillverkare, self.kategori,
                   self.lada_harkomst))


def _egenskaper(xml):
    ut = {}
    for m in _EGENSKAP.finditer(xml):
        ut[m.group(1)] = m.group(2).strip()
    return ut


def _tal(text):
    if text is None:
        return None
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return v


def las_ur_zip(z, sokvag="", djupt=False, geometri=False):
    """Fakta ur ett oppnat .vcmx-arkiv.

    ``djupt=False`` laser bara model.xml. Det racker for namn, kategori,
    tillverkare, rackvidd och nyttolast, och kostar omkring 1,5 kB per
    komponent.

    ``djupt=True`` laser aven component.rsc och far da granssnitten, ramarna,
    lederna och geometriposternas placering.

    ``geometri=True`` laser dessutom geometriblobbarna och rackviddsprofilen.
    Det ar dyrt: blobbarna ar arkivets storsta del.
    """
    poster = set(z.namelist())
    if "model.xml" not in poster:
        raise Filfel("%s saknar model.xml och ar ingen VC-komponent" % sokvag)
    egen = _egenskaper(z.read("model.xml").decode("utf-8-sig", "replace"))
    taggar = tuple(t for t in (egen.get("Tags") or "").split(";") if t)
    fakta = Komponentfakta(
        sokvag=sokvag,
        namn=egen.get("Name") or "",
        kategori=egen.get("Type") or "",
        tillverkare=egen.get("Manufacturer") or "",
        rackvidd_mm=_tal(egen.get("Reach")),
        nyttolast_kg=_tal(egen.get("MaxPayload")),
        taggar=taggar,
        utfasad=(egen.get("IsDeprecated") == "True"),
        beskrivning=egen.get("Description") or "",
        djupt=djupt,
        egenskaper=egen,
    )
    # Den omslutande volymen star inte i nagon del av arkivet. Se modulens
    # inledning: den ar en egenskap hos den byggda komponenten, inte hos
    # filen. Skalet skrivs ut sa att den som lyfter faltet ser varfor.
    fakta.lada = None
    fakta.lada_skal = (
        "ingen omslutande volym i arkivet; hamtas fran VC med get_bounds")
    if not djupt:
        return fakta
    if "component.rsc" not in poster:
        raise Filfel("%s saknar component.rsc" % sokvag)
    rot = tolka_rsc(z.read("component.rsc").decode("utf-8", "replace"))
    fakta.struktur = _struktur_ur(rot)
    fakta.granssnitt = _granssnitt_ur(rot)
    fakta.ramar, geo = _trad_ur(rot)
    fakta.leder = _leder_ur(rot)
    if geometri:
        cache = {}
        for g in geo:
            if not g.uri or g.uri not in poster:
                continue
            if g.uri not in cache:
                svar = tds_lada(z.read(g.uri))
                cache[g.uri] = svar if svar else (None, 0)
            g.lada, g.horn = cache[g.uri]
        if "envelopeprofile" in poster:
            fakta.profil = las_profil(z.read("envelopeprofile"))
    fakta.geometri = tuple(geo)
    return fakta


def las(sokvag, djupt=False, geometri=False):
    """Fakta ur en .vcmx-fil pa disk."""
    if not os.path.isfile(sokvag):
        raise Filfel("ingen fil pa %s" % sokvag)
    try:
        with zipfile.ZipFile(sokvag) as z:
            return las_ur_zip(z, sokvag, djupt=djupt, geometri=geometri)
    except zipfile.BadZipFile as e:
        raise Filfel("%s ar inget zip-arkiv: %s" % (sokvag, e))


# ---------------------------------------------------------------------------
# Svepet: talen i M-61
# ---------------------------------------------------------------------------

def svep(filer, geometri=True, skriv=None):
    """Rakna over ett helt bibliotek vad filerna bar. Talen i M-61.

    Namnaren ar alltid antalet filer som gicks igenom, och den skrivs ut. Ett
    svep som bara redovisar tallaren sager ingenting.
    """
    r = {
        "namnare": len(filer),
        "lasta": 0,
        "olasliga": [],
        "lada_last": 0,
        "lada_harledd": 0,
        "lada_saknas": 0,
        "geometri_blobbar": 0,
        "geometri_med_horn": 0,
        "geometri_konstant": 0,
        "geometri_uttryck": 0,
        "geometri_villkorad": 0,
        "alla_geo_konstanta": 0,
        "utan_geometri": 0,
        "ram_namn": 0,
        "ram_lage_last": 0,
        "ramar_totalt": 0,
        "ramlagen_lasta": 0,
        "granssnitt_namn": 0,
        "granssnitt_totalt": 0,
        "granssnitt_utan_namn": 0,
        "rackvidd_last": 0,
        "rackvidd_noll": 0,
        "rackvidd_saknas": 0,
        "profil_last": 0,
        "profil_stammer_med_rackvidd": 0,
        "profil_avviker": [],
        "leder": 0,
        "transform_med_matris": 0,
        "transform_med_uttryck": 0,
        "transform_totalt": 0,
        "profil_utan_rackviddsfalt": 0,
        "profil_fyller_halet": 0,
        "ramlage_harledd": 0,
        "profil_mot_rackvidd_mm": [],
        "kategori_last": 0,
        "per_kategori": {},
    }
    for i, f in enumerate(filer):
        try:
            fakta = las(f, djupt=True, geometri=geometri)
        except (Filfel, OSError, KeyError, struct.error) as e:
            r["olasliga"].append((f, str(e)))
            continue
        r["lasta"] += 1
        k = r["per_kategori"].setdefault(
            fakta.kategori or "(tom)",
            {"antal": 0, "rackvidd": 0, "profil": 0, "granssnitt": 0,
             "ramar": 0, "alla_geo_konstanta": 0})
        k["antal"] += 1
        if fakta.kategori:
            r["kategori_last"] += 1
        if fakta.lada is None:
            r["lada_saknas"] += 1
        elif fakta.lada.harkomst == Harkomst.LAST:
            r["lada_last"] += 1
        else:
            r["lada_harledd"] += 1
        if fakta.rackvidd_mm is None:
            r["rackvidd_saknas"] += 1
        elif fakta.rackvidd_mm > 0.0:
            r["rackvidd_last"] += 1
            k["rackvidd"] += 1
        else:
            r["rackvidd_noll"] += 1
        if fakta.profil is not None:
            r["profil_last"] += 1
            k["profil"] += 1
            if not fakta.rackvidd_mm:
                r["profil_utan_rackviddsfalt"] += 1
                if fakta.profil.radie_mm > 0.0:
                    r["profil_fyller_halet"] += 1
            else:
                d = fakta.profil.radie_mm - fakta.rackvidd_mm
                r["profil_mot_rackvidd_mm"].append(round(d, 3))
                # En millimeter ar avlasningens egen upplosning: profilen ar
                # float64 i millimeter och Reach ar ett heltal i millimeter.
                if abs(d) <= 1.0:
                    r["profil_stammer_med_rackvidd"] += 1
                else:
                    r["profil_avviker"].append(
                        (os.path.basename(f), fakta.profil.radie_mm,
                         fakta.rackvidd_mm))
        if fakta.granssnitt:
            r["granssnitt_namn"] += 1
            k["granssnitt"] += 1
        r["granssnitt_totalt"] += len(fakta.granssnitt)
        r["granssnitt_utan_namn"] += sum(1 for g in fakta.granssnitt
                                         if not g.namn)
        if fakta.ramar:
            r["ram_namn"] += 1
            k["ramar"] += 1
        r["ramar_totalt"] += len(fakta.ramar)
        r["ramlage_harledd"] += sum(1 for x in fakta.ramar
                                    if x.harkomst == Harkomst.HARLEDD)
        lasta_lagen = sum(1 for x in fakta.ramar
                          if x.harkomst == Harkomst.LAST)
        r["ramlagen_lasta"] += lasta_lagen
        if lasta_lagen:
            r["ram_lage_last"] += 1
        r["leder"] += len(fakta.leder)
        for nyckel in ("transform_totalt", "transform_med_matris",
                       "transform_med_uttryck"):
            r[nyckel] += fakta.struktur.get(nyckel, 0)
        if not fakta.geometri:
            r["utan_geometri"] += 1
        else:
            alla_konst = True
            for g in fakta.geometri:
                r["geometri_blobbar"] += 1
                if g.horn:
                    r["geometri_med_horn"] += 1
                if g.placering == Geometri.KONSTANT:
                    r["geometri_konstant"] += 1
                elif g.placering == Geometri.UTTRYCK:
                    r["geometri_uttryck"] += 1
                    alla_konst = False
                else:
                    r["geometri_villkorad"] += 1
                    alla_konst = False
            if alla_konst:
                r["alla_geo_konstanta"] += 1
                k["alla_geo_konstanta"] += 1
        if skriv and i and i % 250 == 0:
            skriv("  %d/%d" % (i, len(filer)))
    return r


def _filer_under(rot):
    ut = []
    for katalog, _d, filer in os.walk(rot):
        for n in filer:
            if n.lower().endswith((".vcmx", ".vcm")):
                ut.append(os.path.join(katalog, n))
    return sorted(ut)


def main(argv=None):
    import argparse
    import json
    p = argparse.ArgumentParser(description="Las en .vcmx, eller svep ett bibliotek.")
    p.add_argument("--fil", help="las EN komponent och skriv ut vad den bar")
    p.add_argument("--svep", nargs="?", const="", metavar="ROT",
                   help="svep ett bibliotek; utan ROT soks det upp")
    p.add_argument("--utan-geometri", action="store_true",
                   help="hoppa over geometriblobbarna i svepet")
    p.add_argument("--ut", help="skriv svepets tal hit som JSON")
    a = p.parse_args(argv)

    if a.fil:
        f = las(a.fil, djupt=True, geometri=True)
        print("namn:        %s" % f.namn)
        print("tillverkare: %s" % f.tillverkare)
        print("kategori:    %s" % f.kategori)
        print("rackvidd:    %s" % ("%.0f mm" % f.rackvidd_mm
                                   if f.rackvidd_mm else Harkomst.SAKNAS))
        print("nyttolast:   %s" % ("%.3g kg" % f.nyttolast_kg
                                   if f.nyttolast_kg else Harkomst.SAKNAS))
        print("lada:        %s (%s)" % (f.lada_harkomst, f.lada_skal))
        print("granssnitt:  %s" % (", ".join(f.granssnittsnamn())
                                   or Harkomst.SAKNAS))
        print("ramar:       %s" % (", ".join(f.ramnamn()) or Harkomst.SAKNAS))
        print("leder:       %d" % len(f.leder))
        print("profil:      %s" % (f.profil or Harkomst.SAKNAS))
        print("geometri:    %d poster" % len(f.geometri))
        return 0

    if a.svep is None:
        p.print_help()
        return 2
    rot = a.svep
    if not rot:
        from .katalogindex import hitta
        fynd = hitta()
        if not fynd:
            print("hittade inget bibliotek")
            return 1
        rot = fynd[0].rot
        print("bibliotek: %s\n  hittat via: %s" % (fynd[0].rot, fynd[0].hur))
    filer = _filer_under(rot)
    r = svep(filer, geometri=not a.utan_geometri, skriv=print)
    n = r["namnare"]
    print("\nNAMNARE: %d filer" % n)
    for nyckel in ("lasta", "lada_last", "lada_harledd", "lada_saknas",
                   "kategori_last", "rackvidd_last", "rackvidd_noll",
                   "rackvidd_saknas", "profil_last",
                   "profil_stammer_med_rackvidd", "granssnitt_namn",
                   "ram_namn", "ram_lage_last", "profil_fyller_halet",
                   "alla_geo_konstanta", "utan_geometri"):
        print("  %-30s %6d  (%5.1f %%)" % (nyckel, r[nyckel],
                                           100.0 * r[nyckel] / max(n, 1)))
    print("  %-30s %6d" % ("granssnitt_totalt", r["granssnitt_totalt"]))
    print("  %-30s %6d" % ("ramar_totalt", r["ramar_totalt"]))
    print("  %-30s %6d" % ("ramlagen_lasta", r["ramlagen_lasta"]))
    print("  %-30s %6d" % ("ramlage_harledd", r["ramlage_harledd"]))
    print("  %-30s %6d" % ("profil_utan_rackviddsfalt",
                           r["profil_utan_rackviddsfalt"]))
    print("  %-30s %6d" % ("leder", r["leder"]))
    print("  %-30s %6d" % ("geometri_blobbar", r["geometri_blobbar"]))
    print("  %-30s %6d" % ("geometri_konstant", r["geometri_konstant"]))
    print("  %-30s %6d" % ("geometri_uttryck", r["geometri_uttryck"]))
    print("  %-30s %6d" % ("geometri_villkorad", r["geometri_villkorad"]))
    print("  %-30s %6d" % ("olasliga", len(r["olasliga"])))
    if a.ut:
        with open(a.ut, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=1, sort_keys=True, ensure_ascii=False)
        print("skrivet: %s" % a.ut)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
