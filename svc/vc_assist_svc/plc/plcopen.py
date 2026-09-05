# -*- coding: utf-8 -*-
"""Exporten UT: en `st.Enhet` till PLCopen XML, och tillbaka igen.

`M-114` mätte vägen **in** i ett befintligt styrsystem och fann att ingen av
dem ger tillbaka källkoden. Den här modulen är vägen **ut**: koden ska lämna
vårt verktyg och landa i användarens.

## Regeln som styr hela filen

**En export som inte överlever sin egen import är ingen export.**

`exportera()` skriver dokumentet, läser tillbaka det med `las_projekt()` och
jämför modellerna. Skiljer de sig **faller den** — den skriver aldrig en fil
som ser färdig ut men kommer tillbaka stympad. Det är en fail-closed-punkt av
samma sort som `Signalkarta`: garantin bor på ett ställe och provas där.

## Varför inte bara ST-texten i `<ST>`

`M-113` la hela ST-källan som en textklump i `<ST>` och fick tillbaka den
byte-identisk. Det beviset är svagare än det ser ut: en textklump som kommer
tillbaka oförändrad visar att XML-lagret inte tappade tecken, ingenting annat.
Deklarationerna, adresserna, kvalificerarna och säkerhetsmärkningen var aldrig
med i dokumentet, och därför fanns det heller ingenting där som kunde tappas.

Här bor deklarationerna i `<interface>` som riktiga `<variable>`-element med
`address`, `constant`/`retain` och typträd, precis som ett annat verktyg
förväntar sig dem. `<ST>` bär bara satserna. Då mäter turen och retur något.

## Formatet, och vilken version det är

TC6 XML v2.01, namnrymd `http://www.plcopen.org/xml/tc6_0201`. Schemat ligger i
`plcopen_schema/` med härkomst och sha256; det är hämtat ur Beremiz, en riktig
IEC 61131-3-IDE vars egen projektfil `plc.xml` är ett dokument i just det här
formatet.

Det är **inte** IEC 61131-10:2019. PLCopen skriver själva att den nya versionen
*"is not compatible to previous versions of PLCopen XML"*. v2.01 är den version
CODESYS och TwinCAT dokumenterar import av (se `M-155`), och den enda vars
schema är fritt tillgängligt. Skulle vi skriva 61131-10 vore det ett påstående
utan ett schema att pröva det mot.

## Vad standarden inte har en plats för

`Deklaration.skyddad` — säkerhetsmärkningen som invariant I15 vilar på — har
ingen motsvarighet i PLCopen. Den skrivs i `addData` under vår egen namnrymd,
med `handleUnknown="preserve"`. Det räcker för **vår** tur och retur, men ett
främmande verktyg får enligt schemat kasta den. Se `M-154` §LIMITS: en fil som
lämnar oss bär märkningen synligt, men ingen kan lova att den kommer tillbaka.

beskriver: svc/vc_assist_svc/plc/plcopen.py
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import List, Optional, Sequence, Tuple

from ..st import las
from ..st import modell as M
from ..st import typer as T
from ..st import skrivare as W
from ..st.fel import Syntaxfel

NS_PLCOPEN = "http://www.plcopen.org/xml/tc6_0201"
NS_XHTML = "http://www.w3.org/1999/xhtml"
# Vår egen namnrymd för det standarden inte bär. Den är en URI, inte en adress:
# ingenting hämtas från den, och `handleUnknown="preserve"` är en rekommendation
# till mottagaren, inte en garanti.
NS_SAKERHET = "http://vc-assist.invalid/plcopen/sakerhet"

SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "plcopen_schema", "tc6_xml_v201.xsd")

# Tidsstämpeln i `fileHeader` är obligatorisk i schemat. Den sätts till en fast
# sträng och inte till `now()`, av samma skäl som skrivaren är deterministisk:
# utdata är ett kontrakt (docs/spec/95_testprotokoll.md, "Guldfil"), och en
# guldfil som ändrar sig av sig själv mäter ingenting. Den som vill ha en äkta
# tid skickar in den.
TIDSSTAMPEL_STANDARD = "1970-01-01T00:00:00"

FORETAG_STANDARD = "VC_Assist"
PRODUKT_STANDARD = "VC_Assist ST-lager"
PRODUKTVERSION_STANDARD = "1"

# Vår VAR-sort <-> PLCopens elementnamn i `<interface>`.
SORT_TILL_ELEMENT = {
    "VAR": "localVars",
    "VAR_TEMP": "tempVars",
    "VAR_INPUT": "inputVars",
    "VAR_OUTPUT": "outputVars",
    "VAR_IN_OUT": "inOutVars",
    "VAR_EXTERNAL": "externalVars",
    "VAR_GLOBAL": "globalVars",
}
ELEMENT_TILL_SORT = dict((v, k) for k, v in SORT_TILL_ELEMENT.items())

# Kvalificerare <-> attribut. Ordningen i tupeln är den ordning importen
# återskapar dem i; en källa som skrev dem i annan ordning kommer tillbaka
# omkastad, och det fälls av turen och retur i stället för att tystas.
KVAL_TILL_ATTRIBUT = (("CONSTANT", "constant"),
                      ("RETAIN", "retain"),
                      ("NON_RETAIN", "nonretain"))

SORT_TILL_POUTYP = {"PROGRAM": "program", "FUNCTION_BLOCK": "functionBlock",
                    "FUNCTION": "function"}
POUTYP_TILL_SORT = dict((v, k) for k, v in SORT_TILL_POUTYP.items())

# De kroppsspråk PLCopen bär. Vi skriver och läser bara ST; de andra fyra
# avvisas uttryckligen i stället för att ge en tom kropp.
KROPPSSPRAK = ("ST", "IL", "FBD", "LD", "SFC")


class ExportFel(Exception):
    """Exporten vägrade. Antingen kan konstruktionen inte avbildas, eller så
    kom den inte tillbaka likadan."""


class Importfel(Exception):
    """Dokumentet gick inte att läsa som ett PLCopen-projekt vi förstår."""


# ---- små hjälpare --------------------------------------------------------

def _q(namn: str) -> str:
    return "{%s}%s" % (NS_PLCOPEN, namn)


def _ascii(text: str, vad: str) -> str:
    """Samma krav som `st.skrivare`: allt som lämnar oss ska vara ren ASCII.

    Filen går vidare till ett verktyg vars teckenkodning vi inte äger. En
    export som släpper igenom en umlaut har inte löst problemet, den har
    flyttat det till någon annans importör.
    """
    if not isinstance(text, str):
        raise ExportFel("%s is not a string: %r" % (vad, text))
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        raise ExportFel("%s contains non-ASCII: %r. A PLCopen file that "
                        "leaves us must be pure ASCII." % (vad, text))
    return text


def _bool_attr(el: ET.Element, namn: str) -> bool:
    v = (el.get(namn) or "false").strip().lower()
    return v in ("true", "1")


def _barn(el: ET.Element, namn: str) -> Optional[ET.Element]:
    return el.find(_q(namn))


def _krav(el: Optional[ET.Element], namn: str, var: str) -> ET.Element:
    if el is None:
        raise Importfel("%s is missing entirely" % var)
    b = el.find(_q(namn))
    if b is None:
        raise Importfel("%s is missing <%s>" % (var, namn))
    return b


# ---- typerna -------------------------------------------------------------

def _skriv_typ(foralder: ET.Element, typ: T.Typ, var: str) -> None:
    # Pekare ärver Falt; den måste prövas först eller blir en REF_TO ett fält.
    if isinstance(typ, T.Pekare):
        p = ET.SubElement(foralder, _q("pointer"))
        bas = ET.SubElement(p, _q("baseType"))
        _skriv_typ(bas, typ.element, var)
        return
    if isinstance(typ, T.Elementar):
        ET.SubElement(foralder, _q(typ.namn))
        return
    if isinstance(typ, T.Strang):
        s = ET.SubElement(foralder, _q("string"))
        if typ.langd is not None:
            s.set("length", str(typ.langd))
        return
    if isinstance(typ, T.Falt):
        a = ET.SubElement(foralder, _q("array"))
        for lo, hi in typ.granser:
            d = ET.SubElement(a, _q("dimension"))
            d.set("lower", str(lo))
            d.set("upper", str(hi))
        bas = ET.SubElement(a, _q("baseType"))
        _skriv_typ(bas, typ.element, var)
        return
    if isinstance(typ, (T.Strukturtyp, T.Blocktyp)):
        # PLCopen skiljer INTE på en strukturtyp och en blockinstans: båda är
        # <derived name="..."/>. Skillnaden går att återskapa vid import, men
        # bara ur resten av dokumentet (vilka POU:er som är functionBlock) plus
        # standardbiblioteket. Det är därför `_las_typtext` inte gissar utan
        # låter ST-läsaren avgöra, precis som den gör för en handskriven fil.
        d = ET.SubElement(foralder, _q("derived"))
        d.set("name", _ascii(typ.namn, "ett typnamn"))
        return
    raise ExportFel("%s has type %s, for which PLCopen XML has no form"
                    % (var, type(typ).__name__))


def _las_typtext(el: ET.Element, var: str) -> str:
    """XML-typträd -> ST-typtext. Texten går sedan genom projektets egen
    läsare, som avgör om ett namn är en struktur eller en blockinstans."""
    tagg = el.tag.split("}")[-1]
    if tagg in T.ELEMENTARA:
        return tagg
    if tagg == "string":
        langd = el.get("length")
        return "STRING" if langd is None else "STRING[%s]" % langd
    if tagg == "array":
        matt = []
        for d in el.findall(_q("dimension")):
            lo, hi = d.get("lower"), d.get("upper")
            if lo is None or hi is None:
                raise Importfel("%s has a <dimension> without lower/upper" % var)
            matt.append("%s..%s" % (lo, hi))
        if not matt:
            raise Importfel("%s is an <array> without a single <dimension>" % var)
        bas = _krav(el, "baseType", "%s (array)" % var)
        return "ARRAY [%s] OF %s" % (", ".join(matt), _las_typtext(_ett(bas, var), var))
    if tagg == "pointer":
        bas = _krav(el, "baseType", "%s (pointer)" % var)
        return "REF_TO %s" % _las_typtext(_ett(bas, var), var)
    if tagg == "derived":
        namn = el.get("name")
        if not namn:
            raise Importfel("%s has a <derived> without name" % var)
        return namn
    raise Importfel("%s has type <%s>, which this layer cannot read"
                    % (var, tagg))


def _ett(foralder: ET.Element, var: str) -> ET.Element:
    barn = list(foralder)
    if len(barn) != 1:
        raise Importfel("%s: expected exactly one type element, got %d"
                        % (var, len(barn)))
    return barn[0]


# ---- initieringsvärden ---------------------------------------------------

def _skriv_init(foralder: ET.Element, u: M.Uttryck, var: str) -> None:
    iv = ET.SubElement(foralder, _q("initialValue"))
    if isinstance(u, M.Faltinit):
        _skriv_faltvarde(iv, u, var)
        return
    sv = ET.SubElement(iv, _q("simpleValue"))
    sv.set("value", _ascii(W.skriv_uttryck(u), "ett initieringsvärde i %s" % var))


def _skriv_faltvarde(foralder: ET.Element, f: M.Faltinit, var: str) -> None:
    av = ET.SubElement(foralder, _q("arrayValue"))
    for e in f.element:
        v = ET.SubElement(av, _q("value"))
        if e.antal is not None:
            v.set("repetitionValue", str(e.antal))
        if isinstance(e.varde, M.Faltinit):
            _skriv_faltvarde(v, e.varde, var)
        else:
            sv = ET.SubElement(v, _q("simpleValue"))
            sv.set("value", _ascii(W.skriv_uttryck(e.varde),
                                   "ett fältvärde i %s" % var))


def _las_inittext(el: ET.Element, var: str) -> str:
    sv = _barn(el, "simpleValue")
    if sv is not None:
        return sv.get("value") or ""
    av = _barn(el, "arrayValue")
    if av is not None:
        return _las_faltvardetext(av, var)
    if _barn(el, "structValue") is not None:
        raise Importfel("%s carries a <structValue>; the ST layer has no "
                        "struct initializer to read it into" % var)
    raise Importfel("%s has an <initialValue> without a value" % var)


def _las_faltvardetext(av: ET.Element, var: str) -> str:
    delar = []
    for v in av.findall(_q("value")):
        antal = v.get("repetitionValue")
        inre_av = _barn(v, "arrayValue")
        if inre_av is not None:
            text = _las_faltvardetext(inre_av, var)
        else:
            sv = _barn(v, "simpleValue")
            if sv is None:
                raise Importfel("%s has a <value> without a value" % var)
            text = sv.get("value") or ""
        if antal is not None and antal != "1":
            delar.append("%s(%s)" % (antal, text))
        else:
            delar.append(text)
    if not delar:
        raise Importfel("%s has an empty <arrayValue>" % var)
    return "[%s]" % ", ".join(delar)


# ---- deklarationer -------------------------------------------------------

def _skriv_deklaration(foralder: ET.Element, d: M.Deklaration, var: str) -> None:
    v = ET.SubElement(foralder, _q("variable"))
    v.set("name", _ascii(d.namn, "ett variabelnamn"))
    if d.adress:
        v.set("address", _ascii(d.adress, "en adress"))
    typ_el = ET.SubElement(v, _q("type"))
    _skriv_typ(typ_el, d.typ, "%s.%s" % (var, d.namn))
    if d.init is not None:
        _skriv_init(v, d.init, "%s.%s" % (var, d.namn))
    if d.skyddad:
        add = ET.SubElement(v, _q("addData"))
        data = ET.SubElement(add, _q("data"))
        data.set("name", NS_SAKERHET)
        data.set("handleUnknown", "preserve")
        m = ET.SubElement(data, "{%s}sakerhet" % NS_SAKERHET)
        m.set("skyddad", "true")
    if d.kommentar:
        _skriv_text(v, "documentation",
                    _ascii(d.kommentar, "en kommentar"))


def _skriv_text(foralder: ET.Element, elementnamn: str, text: str) -> None:
    el = ET.SubElement(foralder, _q(elementnamn))
    p = ET.SubElement(el, "{%s}p" % NS_XHTML)
    p.text = text


def _las_text(el: Optional[ET.Element]) -> str:
    if el is None:
        return ""
    p = el.find("{%s}p" % NS_XHTML)
    if p is None:
        # Ett formattedText utan xhtml-barn är inte schemagiltigt. Att svara
        # med tom sträng vore att tysta ett trasigt dokument.
        raise Importfel("a <%s> is missing its xhtml child"
                        % el.tag.split("}")[-1])
    return p.text or ""


def _deklarationsrad(v: ET.Element, var: str) -> str:
    namn = v.get("name")
    if not namn:
        raise Importfel("%s has a <variable> without name" % var)
    rad = namn
    adress = v.get("address")
    if adress:
        rad += " AT %s" % adress
    typ_el = _krav(v, "type", "%s.%s" % (var, namn))
    rad += " : %s" % _las_typtext(_ett(typ_el, "%s.%s" % (var, namn)), namn)
    iv = _barn(v, "initialValue")
    if iv is not None:
        rad += " := %s" % _las_inittext(iv, "%s.%s" % (var, namn))
    rad += ";"
    add = _barn(v, "addData")
    if add is not None:
        for data in add.findall(_q("data")):
            if data.get("name") == NS_SAKERHET:
                for m in data:
                    if m.get("skyddad") == "true":
                        rad += " {SAKERHET}"
    dok = _barn(v, "documentation")
    if dok is not None:
        rad += " (* %s *)" % _las_text(dok)
    return rad


# ---- VAR-block -----------------------------------------------------------

def _skriv_varblock(foralder: ET.Element, b: M.Varblock, var: str) -> ET.Element:
    elementnamn = SORT_TILL_ELEMENT.get(b.sort)
    if elementnamn is None:
        raise ExportFel("VAR kind %s has no place in PLCopen's <interface>"
                        % b.sort)
    el = ET.SubElement(foralder, _q(elementnamn))
    for kval, attribut in KVAL_TILL_ATTRIBUT:
        if kval in b.kvalificerare:
            el.set(attribut, "true")
    for d in b.deklarationer:
        _skriv_deklaration(el, d, var)
    return el


def _varblockrader(el: ET.Element, sort: str, var: str) -> List[str]:
    kval = [k for k, attribut in KVAL_TILL_ATTRIBUT if _bool_attr(el, attribut)]
    rader = [" ".join([sort] + kval)]
    for v in el.findall(_q("variable")):
        rader.append("    " + _deklarationsrad(v, var))
    rader.append("END_VAR")
    return rader


# ---- POU:er --------------------------------------------------------------

def _skriv_pou(foralder: ET.Element, p: M.Pou) -> None:
    poutyp = SORT_TILL_POUTYP.get(p.sort)
    if poutyp is None:
        raise ExportFel("POU kind %s does not exist in PLCopen's pouType" % p.sort)
    el = ET.SubElement(foralder, _q("pou"))
    el.set("name", _ascii(p.namn, "ett POU-namn"))
    el.set("pouType", poutyp)
    granssnitt = ET.SubElement(el, _q("interface"))
    if p.returtyp is not None:
        rt = ET.SubElement(granssnitt, _q("returnType"))
        _skriv_typ(rt, p.returtyp, "%s (returtyp)" % p.namn)
    for b in p.block:
        _skriv_varblock(granssnitt, b, p.namn)
    kropp = ET.SubElement(el, _q("body"))
    st = ET.SubElement(kropp, _q("ST"))
    q = ET.SubElement(st, "{%s}p" % NS_XHTML)
    q.text = _ascii("\n".join(W.skriv_satser(p.kropp, 1)), "en kropp i %s" % p.namn)


def _pou_rader(el: ET.Element) -> List[str]:
    namn = el.get("name")
    if not namn:
        raise Importfel("a <pou> is missing name")
    poutyp = el.get("pouType")
    sort = POUTYP_TILL_SORT.get(poutyp or "")
    if sort is None:
        raise Importfel("<pou name=%r> has pouType=%r; known are %s"
                        % (namn, poutyp, ", ".join(sorted(POUTYP_TILL_SORT))))
    huvud = "%s %s" % (sort, namn)
    rader: List[str] = []
    granssnitt = _barn(el, "interface")
    if granssnitt is not None:
        rt = _barn(granssnitt, "returnType")
        if rt is not None:
            huvud += " : %s" % _las_typtext(_ett(rt, "%s (returnType)" % namn), namn)
        for barn in granssnitt:
            taggen = barn.tag.split("}")[-1]
            if taggen in ("returnType", "addData", "documentation"):
                continue
            varsort = ELEMENT_TILL_SORT.get(taggen)
            if varsort is None:
                raise Importfel("<pou name=%r> has a <%s> in its "
                                "<interface> that this layer does not read"
                                % (namn, taggen))
            rader.extend(_varblockrader(barn, varsort, namn))
    rader.insert(0, huvud)
    kropp = _krav(el, "body", "<pou name=%r>" % namn)
    st = _barn(kropp, "ST")
    if st is None:
        andra = [b.tag.split("}")[-1] for b in kropp
                 if b.tag.split("}")[-1] in KROPPSSPRAK]
        raise Importfel("<pou name=%r> has its body written in %s, not in ST. "
                        "This layer only reads ST."
                        % (namn, andra[0] if andra else "an unknown language"))
    rader.append(_las_text(st))
    rader.append("END_%s" % sort)
    return rader


# ---- projektet -----------------------------------------------------------

def skriv_projekt(enhet: M.Enhet, *, projektnamn: str = "VC_Assist",
                  foretag: str = FORETAG_STANDARD,
                  produkt: str = PRODUKT_STANDARD,
                  produktversion: str = PRODUKTVERSION_STANDARD,
                  tidsstampel: Optional[str] = None,
                  konfigurationsnamn: str = "config") -> str:
    """`Enhet` -> PLCopen TC6 v2.01-dokument som text.

    Gör INGEN tur och retur. Den som vill ha garantin att filen kommer tillbaka
    använder `exportera()`.
    """
    if not isinstance(enhet, M.Enhet):
        raise ExportFel("skriv_projekt wants an st.Enhet, not %s"
                        % type(enhet).__name__)
    if not enhet.pouer:
        raise ExportFel("a project without a single POU is not an export; "
                        "the document would validate against the schema and still be empty")

    ET.register_namespace("", NS_PLCOPEN)
    ET.register_namespace("xhtml", NS_XHTML)

    rot = ET.Element(_q("project"))
    fh = ET.SubElement(rot, _q("fileHeader"))
    fh.set("companyName", _ascii(foretag, "företagsnamnet"))
    fh.set("productName", _ascii(produkt, "produktnamnet"))
    fh.set("productVersion", _ascii(produktversion, "produktversionen"))
    fh.set("creationDateTime", tidsstampel or TIDSSTAMPEL_STANDARD)

    ch = ET.SubElement(rot, _q("contentHeader"))
    ch.set("name", _ascii(projektnamn, "projektnamnet"))
    ci = ET.SubElement(ch, _q("coordinateInfo"))
    for grafiskt in ("fbd", "ld", "sfc"):
        g = ET.SubElement(ci, _q(grafiskt))
        s = ET.SubElement(g, _q("scaling"))
        s.set("x", "1")
        s.set("y", "1")

    typer = ET.SubElement(rot, _q("types"))
    datatyper = ET.SubElement(typer, _q("dataTypes"))
    for sd in enhet.typer:
        dt = ET.SubElement(datatyper, _q("dataType"))
        dt.set("name", _ascii(sd.namn, "ett typnamn"))
        bas = ET.SubElement(dt, _q("baseType"))
        struct = ET.SubElement(bas, _q("struct"))
        for f in sd.falt:
            _skriv_deklaration(struct, f, sd.namn)

    pous = ET.SubElement(typer, _q("pous"))
    for p in enhet.pouer:
        _skriv_pou(pous, p)

    instanser = ET.SubElement(rot, _q("instances"))
    konfigurationer = ET.SubElement(instanser, _q("configurations"))
    if enhet.globala:
        konf = ET.SubElement(konfigurationer, _q("configuration"))
        konf.set("name", _ascii(konfigurationsnamn, "konfigurationsnamnet"))
        for b in enhet.globala:
            if b.sort != "VAR_GLOBAL":
                raise ExportFel("a file-level block has kind %s; only "
                                "VAR_GLOBAL belongs in a <configuration>"
                                % b.sort)
            _skriv_varblock(konf, b, konfigurationsnamn)

    text = ET.tostring(rot, encoding="unicode")
    return '<?xml version="1.0" encoding="utf-8"?>\n' + text + "\n"


def till_st(xml: str) -> str:
    """PLCopen-dokument -> ST-källtext.

    Mellansteget är avsiktligt synligt. Det är samma väg ett riktigt verktyg
    tar (Beremiz genererar ST ur sitt `plc.xml` innan matiec får se det), och
    det gör att importen inte behöver en andra, egen tolkning av vad en
    deklaration betyder — projektets läsare avgör, som för vilken ST-fil som
    helst. Det är också det som gör att `x : TON;` blir en BLOCKINSTANS och
    `p : Punkt;` en struktur, fast PLCopen skriver båda som `<derived>`.
    """
    try:
        rot = ET.fromstring(xml)
    except ET.ParseError as fel:
        raise Importfel("the document is not well-formed XML: %s" % fel)
    if rot.tag != _q("project"):
        raise Importfel("the root element is %r; expected <project> in namespace %s"
                        % (rot.tag, NS_PLCOPEN))

    typer = _krav(rot, "types", "<project>")
    delar: List[str] = []

    datatyper = _barn(typer, "dataTypes")
    strukturer = list(datatyper.findall(_q("dataType"))) if datatyper is not None else []
    if strukturer:
        rader = ["TYPE"]
        for dt in strukturer:
            namn = dt.get("name")
            if not namn:
                raise Importfel("a <dataType> is missing name")
            bas = _krav(dt, "baseType", "<dataType name=%r>" % namn)
            struct = _barn(bas, "struct")
            if struct is None:
                raise Importfel("<dataType name=%r> has a baseType that is not "
                                "a <struct>; the ST layer only has STRUCT in "
                                "TYPE ... END_TYPE" % namn)
            rader.append("    %s : STRUCT" % namn)
            for v in struct.findall(_q("variable")):
                rader.append("        " + _deklarationsrad(v, namn))
            rader.append("    END_STRUCT;")
        rader.append("END_TYPE")
        delar.append("\n".join(rader) + "\n")

    instanser = _barn(rot, "instances")
    if instanser is not None:
        konfigurationer = _barn(instanser, "configurations")
        if konfigurationer is not None:
            for konf in konfigurationer.findall(_q("configuration")):
                for gv in konf.findall(_q("globalVars")):
                    delar.append("\n".join(
                        _varblockrader(gv, "VAR_GLOBAL",
                                       konf.get("name") or "config")) + "\n")

    pous = _barn(typer, "pous")
    if pous is not None:
        for p in pous.findall(_q("pou")):
            delar.append("\n".join(_pou_rader(p)) + "\n")

    return "\n".join(delar)


def las_projekt(xml: str) -> M.Enhet:
    """PLCopen-dokument -> `st.Enhet`."""
    kalla = till_st(xml)
    try:
        return las(kalla)
    except Syntaxfel as fel:
        raise Importfel("the ST that the document describes cannot be read: %s"
                        % fel)


def kroppstext(xml: str, pounamn: str) -> str:
    """ST-texten i en POU:s `<body><ST>`, ordagrant som den står i filen."""
    try:
        rot = ET.fromstring(xml)
    except ET.ParseError as fel:
        raise Importfel("the document is not well-formed XML: %s" % fel)
    for p in rot.iter(_q("pou")):
        if p.get("name") == pounamn:
            kropp = _krav(p, "body", "<pou name=%r>" % pounamn)
            st = _barn(kropp, "ST")
            if st is None:
                raise Importfel("<pou name=%r> has no ST body" % pounamn)
            return _las_text(st)
    raise Importfel("no <pou name=%r> in the document" % pounamn)


# ---- jämförelsen ---------------------------------------------------------

def _blockbeskrivning(b: M.Varblock) -> str:
    return "%s%s" % (b.sort, "".join(" " + k for k in b.kvalificerare))


def avvikelser(a: M.Enhet, b: M.Enhet) -> Tuple[str, ...]:
    """Var två enheter skiljer sig, i klartext.

    Finns för att `assert a == b` på två frysta dataklassträd säger *att* de
    skiljer sig men aldrig *var*. En grind som inte kan peka ut raden kostar
    ett reparationsvarv varje gång den fäller.
    """
    ut: List[str] = []

    namn_a = [t.namn for t in a.typer]
    namn_b = [t.namn for t in b.typer]
    if namn_a != namn_b:
        ut.append("typdefinitionerna skiljer sig: %r mot %r" % (namn_a, namn_b))
    else:
        for ta, tb in zip(a.typer, b.typer):
            if ta != tb:
                ut.extend("TYPE %s: %s" % (ta.namn, rad)
                          for rad in _deklarationsavvikelser(ta.falt, tb.falt))

    if len(a.globala) != len(b.globala):
        ut.append("antalet VAR_GLOBAL-block skiljer sig: %d mot %d"
                  % (len(a.globala), len(b.globala)))
    else:
        for ga, gb in zip(a.globala, b.globala):
            ut.extend(_blockavvikelser(ga, gb, "filnivå"))

    pnamn_a = [(p.sort, p.namn) for p in a.pouer]
    pnamn_b = [(p.sort, p.namn) for p in b.pouer]
    if pnamn_a != pnamn_b:
        ut.append("POU-listan skiljer sig: %r mot %r" % (pnamn_a, pnamn_b))
        return tuple(ut)

    for pa, pb in zip(a.pouer, b.pouer):
        if pa == pb:
            continue
        if pa.returtyp != pb.returtyp:
            ut.append("%s: returtypen %r mot %r"
                      % (pa.namn, pa.returtyp, pb.returtyp))
        if len(pa.block) != len(pb.block):
            ut.append("%s: %d VAR-block mot %d"
                      % (pa.namn, len(pa.block), len(pb.block)))
        else:
            for ba, bb in zip(pa.block, pb.block):
                ut.extend(_blockavvikelser(ba, bb, pa.namn))
        if pa.kropp != pb.kropp:
            ut.append("%s: kroppen kom inte tillbaka likadan (%d satser mot %d)"
                      % (pa.namn, len(pa.kropp), len(pb.kropp)))
            for i, (sa, sb) in enumerate(zip(pa.kropp, pb.kropp)):
                if sa != sb:
                    ut.append("%s: sats %d: %r mot %r" % (pa.namn, i, sa, sb))
                    break
    return tuple(ut)


def _blockavvikelser(a: M.Varblock, b: M.Varblock, var: str) -> List[str]:
    if a == b:
        return []
    ut = []
    if (a.sort, a.kvalificerare) != (b.sort, b.kvalificerare):
        ut.append("%s: blockhuvudet %r mot %r"
                  % (var, _blockbeskrivning(a), _blockbeskrivning(b)))
    ut.extend("%s: %s" % (var, rad)
              for rad in _deklarationsavvikelser(a.deklarationer, b.deklarationer))
    return ut


def _deklarationsavvikelser(a: Sequence[M.Deklaration],
                            b: Sequence[M.Deklaration]) -> List[str]:
    ut = []
    if [d.namn for d in a] != [d.namn for d in b]:
        return ["variabellistan skiljer sig: %r mot %r"
                % ([d.namn for d in a], [d.namn for d in b])]
    for da, db in zip(a, b):
        if da == db:
            continue
        for falt in ("typ", "init", "adress", "skyddad", "kommentar"):
            va, vb = getattr(da, falt), getattr(db, falt)
            if va != vb:
                ut.append("%s.%s: %r mot %r" % (da.namn, falt, va, vb))
    return ut


# ---- grinden -------------------------------------------------------------

def exportera(enhet: M.Enhet, **kw) -> str:
    """Skriv ett PLCopen-dokument som **bevisligen** kommer tillbaka.

    Skriver, läser tillbaka och jämför. Skiljer sig modellerna kastas
    `ExportFel` med varje avvikelse utskriven. Det finns ingen växel som slår
    av kontrollen: en export som får skrivas utan att ha prövats är precis den
    tysta halvfärdighet regeln finns för.
    """
    xml = skriv_projekt(enhet, **kw)
    try:
        tillbaka = las_projekt(xml)
    except Importfel as fel:
        raise ExportFel("the file could not be read back: %s" % fel)
    if tillbaka != enhet:
        rader = avvikelser(enhet, tillbaka)
        raise ExportFel("the export did not survive its own import:\n  "
                        + "\n  ".join(rader or ["(no discrepancy could be "
                                                "pinpointed, but the models "
                                                "are different)"]))
    return xml


# ---- schemat -------------------------------------------------------------

def validera_schema(xml: str, xsd: str = SCHEMA) -> Tuple[str, ...]:
    """Validera mot det officiella TC6-schemat. Tom tupel = giltigt.

    Kräver `lxml`. Saknas den kastas ImportError — en validering som tyst
    hoppar över sig själv är ett falskt grönt, och det är den dyraste sorten.
    """
    try:
        from lxml import etree
    except ImportError:
        raise ImportError("schemavalideringen kräver lxml; utan den finns "
                          "ingen validering, bara ett antagande")
    schema = etree.XMLSchema(etree.parse(xsd))
    try:
        dok = etree.fromstring(xml.encode("utf-8"))
    except etree.XMLSyntaxError as fel:
        return ("dokumentet är inte välformad XML: %s" % fel,)
    if schema.validate(dok):
        return ()
    return tuple("%s (rad %s)" % (f.message, f.line) for f in schema.error_log)
