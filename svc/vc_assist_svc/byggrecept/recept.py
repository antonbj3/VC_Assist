# -*- coding: utf-8 -*-
"""Byggrecepten: Python 2.7-kod som bygger komponenter i VC.

Recepten foljer kodmall.py och scen.py: bygg() satter ihop mallen, lit() gor
strangar till _s(u"...") sa att de nar VC som bytestrangar (M-05), och
svaret ar JSON pa sista raden av stdout (31_brygga_protokoll.md).

Varje recept ar SKRIVANDE (createComponent, createBehaviour ...) och maste
domas sa av skrivgrind.granska(); det provas i tests/enhet/test_byggrecept.py.
Recepten ar inte registrerade i verktygsregistret: de ar matinstrument for
docs/spec/49_komponentmodellen.md, och ett registrerat verktyg kraver att
korsprovet i test_verktyg.py tacker det. Registreringen ar ett eget beslut
nar recepten ar matta.

Sa provar ett recept sina hypoteser: allt osakert ligger i _forsok(), som kor
ett steg, fangar undantaget och bokfor {"hypotes": id, "utfall": ...} i
listan "forsok" i svaret. SystemError ar da ett MATT utfall, inte ett haveri
som doljer resten av matningen. Id:na ar de i hypoteser.py; provordningen
kommer darifran, inte ur receptet.

Inga getattr/setattr/eval: api_index-validatorn kan inte doma dem, och vi
vill att varje VC-namn i recepten ska vara kontrollerat mot indexet.
"""
from __future__ import annotations

from ..verktyg.bas import tak
from ..verktyg.kodmall import bygg, lit, tal
from .hypoteser import provordning

# Faltnamnet ar detsamma pa bada sidor av en koppling (hypotes E3).
FALTNAMN = "Flow"

# Vilken falttyp ett recept binder. "flow" ar rang 1 (B1: Port ar en
# vcConnector). "transport" ar den typ operatoren redan matt (A1/B2).
FALTTYPER = {
    "flow": "VC_FLOWFIELD",
    "transport": "VC_TRANSPORTFIELD",
}

# MATT 2026-09-04 (B00): flodesfaltet bar Name, Container, Port, PortName;
# transportfaltet Name, Transport, Connection. Tva referenser per falt:
# BETEENDET (Container / Transport) och KONTAKTEN i det (Port / Connection).
BETEENDENAMN = ("Container", "Transport")
KONTAKTNAMN = ("Port", "Connection")
KONTAKTNAMN_TEXT = ("PortName",)

# Kontakten binds som HELTAL (B3, MATT ok; B1/B2 MATT fel). Beteendet ar
# obundet an: stegen B7-B9 ur hypoteser.py, i rangordning. B10 (PortName)
# satts alltid, utover Port.
BEHALLARSTEG = tuple(h for h in provordning("B") if h in ("B7", "B8", "B9"))
assert BEHALLARSTEG == ("B7", "B8", "B9"), BEHALLARSTEG


# ---- gemensamma hjalpare i den genererade koden ----------------------------
#
# Skrivna som rader i kroppen, inte som kodmall-hjalpare: kodmall._HJALPARE
# ar en fast tabell och bygg() kastar KeyError pa okanda namn. Den tabellen
# ar de lasande verktygens; de har raderna ar receptens egna.

_HJALP_BAS = '''
def _typnamn(o):
    return type(o).__name__


def _egen(p):
    return {"name": p.Name, "type": _enkelt(p.Type), "value": _enkelt(p.Value)}


def _egenskaper(o):
    ut = []
    for p in o.Properties:
        ut.append(_egen(p))
    return ut
'''

_HJALP_BYGG = '''
def _forsok(logg, hypotes, funk):
    # Kor ett osakert steg och bokfor utfallet under hypotesens id. Ett
    # undantag ar ett MATT utfall och stoppar inte resten av receptet.
    try:
        r = funk()
        logg.append({"hypotes": hypotes, "utfall": "ok", "resultat": _enkelt(r)})
        return True, r
    except Exception as e:
        logg.append({"hypotes": hypotes, "utfall": "fel",
                     "fel": _typnamn(e) + ": " + str(e)})
        return False, None


def _hitta_egenskap(o, namn):
    for p in o.Properties:
        if p.Name == namn:
            return p
    return None


def _kontakt(logg, beh, typ):
    # C1 (MATT): valj kontakt pa Type, aldrig pa index -- skaparen bar
    # Output pa index 0 och Input pa index 1, banan tvartom.
    forsta = None
    for c in beh.Connectors:
        if forsta is None:
            forsta = c
        if c.Type == typ:
            return c
    for c in beh.Connectors:
        if c.Type == VC_CONNECTOR_INPUT_OUTPUT:
            return c
    logg.append({"hypotes": "C2", "utfall": "fel" if forsta is None else "ok",
                 "fel": "beteendet " + beh.Name + " har " + str(beh.ConnectorCount)
                        + " kontakter, ingen med begard typ"})
    return forsta


def _kontakter(beh):
    ut = []
    for c in beh.Connectors:
        ut.append({"name": c.Name, "index": c.Index, "type": _enkelt(c.Type),
                   "connected": c.Connection is not None})
    return ut


def _bind(logg, falt, kontakt, agare, agarindex):
    # Binder flodesfaltets tva referenser. Kontakten: Port = Index (B3,
    # MATT). Beteendet: Container enligt B7-B9 i rangordning. PortName
    # satts alltid (B10). Returnerar namnen pa egenskaperna som bands.
    bundna = []
    kontaktegenskap = None
    for namn in KONTAKTNAMN:
        kontaktegenskap = _hitta_egenskap(falt, namn)
        if kontaktegenskap is not None:
            break
    if kontaktegenskap is not None and kontakt is not None:
        def satt_port():
            kontaktegenskap.Value = kontakt.Index
            return _enkelt(kontaktegenskap.Value)
        ok, _ = _forsok(logg, "B3", satt_port)
        if ok and kontaktegenskap.Value is not None:
            bundna.append(kontaktegenskap.Name)
    for namn in KONTAKTNAMN_TEXT:
        textegenskap = _hitta_egenskap(falt, namn)
        if textegenskap is not None and kontakt is not None:
            def satt_portnamn(textegenskap=textegenskap):
                textegenskap.Value = kontakt.Name
                return _enkelt(textegenskap.Value)
            ok, _ = _forsok(logg, "B10", satt_portnamn)
            if ok:
                bundna.append(textegenskap.Name)
    beteendeegenskap = None
    for namn in BETEENDENAMN:
        beteendeegenskap = _hitta_egenskap(falt, namn)
        if beteendeegenskap is not None:
            break
    if beteendeegenskap is None:
        logg.append({"hypotes": "B00", "utfall": "fel",
                     "fel": "faltet " + falt.Name + " har ingen egenskap med nagot av namnen "
                            + repr(BETEENDENAMN),
                     "egenskaper": _egenskaper(falt)})
        return bundna
    agarnamn = None if agare is None else agare.Name
    kandidater = [("B7", agare), ("B8", agarindex), ("B9", agarnamn)]
    for hyp, varde in kandidater:
        if varde is None:
            continue
        def satt_beteende(varde=varde):
            beteendeegenskap.Value = varde
            return _enkelt(beteendeegenskap.Value)
        ok, _ = _forsok(logg, hyp, satt_beteende)
        if ok and beteendeegenskap.Value is not None:
            bundna.append(beteendeegenskap.Name)
            break
    return bundna


def _beteendeindex(k, beh):
    # Beteendets plats i komponentens lista (hypotes B8).
    i = 0
    for b in k.Behaviours:
        if b.Name == beh.Name:
            return i
        i = i + 1
    return None


def _ram(k, namn, x, y, z, vrid):
    # Hypotes F0: en Frame-feature under rotfeaturen, placerad via matrisen.
    f = k.RootFeature.createFeature(VC_FRAME, namn)
    m = f.PositionMatrix
    m.P = vcVector.new(x, y, z)
    if vrid:
        m.rotateRelZ(vrid)
    f.PositionMatrix = m
    return f


def _granssnitt(logg, k, namn, ram, falttyp, kontakt, agare, abstrakt):
    g = k.createBehaviour(VC_ONETOONEINTERFACE, namn)
    g.IsAbstract = abstrakt
    sek = g.createSection(namn)
    if sek is None:
        raise ValueError("createSection gav None for " + namn)
    if ram is not None and not abstrakt:
        sek.Frame = ram
    falt = sek.createField(falttyp, FALTNAMN)
    if falt is None:
        raise ValueError("createField gav None for " + namn)
    fore = _egenskaper(falt)
    agarindex = None if agare is None else _beteendeindex(k, agare)
    bundna = _bind(logg, falt, kontakt, agare, agarindex)
    return {"name": g.Name, "is_abstract": bool(g.IsAbstract),
            "section": sek.Name, "frame": None if ram is None else ram.Name,
            "field": falt.Name, "field_type": _enkelt(falt.Type),
            "properties_before": fore, "properties_after": _egenskaper(falt),
            "bound_properties": bundna}


def _beteenden(k):
    ut = []
    for b in k.Behaviours:
        ut.append({"name": b.Name, "type": _enkelt(b.Type), "class": _typnamn(b)})
    return ut


def _alla_kontakter(k, filter_namn):
    # Varje kontakt i varje beteende som har kontakter. Ett beteende utan
    # Connectors (granssnitt, signaler) ger AttributeError och hoppas over.
    ut = []
    for b in k.Behaviours:
        if filter_namn is not None and b.Name != filter_namn:
            continue
        try:
            kontakter = b.Connectors
        except AttributeError:
            continue
        for c in kontakter:
            ut.append((b, c))
    return ut


def _valj_kontakt(logg, k, typ, filter_namn, etikett):
    # Uppgift A: valj pa Type over ALLA beteenden, aldrig pa index eller
    # beteendenamn. En okopplad kontakt gar fore en kopplad.
    kandidater = []
    for b, c in _alla_kontakter(k, filter_namn):
        if c.Type == typ:
            kandidater.append((b, c))
    if not kandidater:
        logg.append({"hypotes": "C1", "utfall": "fel",
                     "fel": etikett + ": " + k.Name + " har ingen kontakt med typ "
                            + str(typ) + " (filter " + repr(filter_namn) + ")"})
        return None
    vald = kandidater[0]
    for b, c in kandidater:
        if c.Connection is None:
            vald = (b, c)
            break
    logg.append({"hypotes": "C1", "utfall": "ok",
                 "resultat": etikett + ": " + vald[0].Name + " / " + vald[1].Name
                             + " index " + str(vald[1].Index)
                             + " typ " + str(_enkelt(vald[1].Type))
                             + (" (redan kopplad)" if vald[1].Connection is not None else "")})
    return vald[1]
'''

def _tupelrad(namn, varden):
    return "%s = (%s,)" % (namn, ", ".join(lit(v) for v in varden))


_NAMNRADER = [
    _tupelrad("BETEENDENAMN", BETEENDENAMN),
    _tupelrad("KONTAKTNAMN", KONTAKTNAMN),
    _tupelrad("KONTAKTNAMN_TEXT", KONTAKTNAMN_TEXT),
    "FALTNAMN = %s" % lit(FALTNAMN),
]


# _s kommer ur bryggans exec-globaler (pump.py:_kor). Recepten ar ocksa
# matinstrument som operatoren kan klistra in i VC:s egen Python-konsol, och
# dar finns ingen brygga. Darfor en reserv som bara binds nar namnet saknas.
_S_RESERV = """
try:
    _s
except NameError:
    def _s(x):
        try:
            if isinstance(x, unicode):
                return x.encode("utf-8")
        except NameError:
            pass
        return x
"""


def _inledning():
    return (_S_RESERV.split("\n") + _NAMNRADER + _HJALP_BAS.split("\n")
            + _HJALP_BYGG.split("\n"))


def _inledning_lasande():
    """Bara det ett lasande recept behover. Bygghjalparna bar append() pa
    parametrar, och det domer skrivgrinden som skrivande."""
    return _S_RESERV.split("\n") + _HJALP_BAS.split("\n")


def _nyko(namn):
    """Rader som skapar en tom komponent med givet namn."""
    return [
        # getApplication() direkt, inte via kodmallens _app(): da ser
        # api_index-validatorn att app ar en vcApplication och kan doma
        # varje namn pa k, banan och granssnitten. Genom _app() blir allt
        # otypat och ingenting kontrolleras.
        "app = getApplication()",
        "k = app.createComponent()",
        "if k is None:",
        '    raise ValueError("createComponent gav ingen komponent")',
        "k.Name = %s" % lit(namn),
        "forsok = []",
    ]


def _block(langd, bredd, hojd):
    """Ett VC_BLOCK som kropp. Mattens egenskapsnamn ar inte i kallorna, sa
    koden laser vad blocket faktiskt bar och satter bara det som finns."""
    return [
        "kropp = k.RootFeature.createFeature(VC_BLOCK, %s)" % lit("Kropp"),
        "matt = {%s: %s, %s: %s, %s: %s}" % (
            lit("Length"), tal(langd), lit("Width"), tal(bredd),
            lit("Height"), tal(hojd)),
        "kroppens_egenskaper = []",
        "for p in kropp.Properties:",
        "    kroppens_egenskaper.append(p.Name)",
        "    if p.Name in matt:",
        "        p.Value = matt[p.Name]",
    ]


def _falttyp(argument):
    nyckel = argument.get("falttyp", "flow")
    if nyckel not in FALTTYPER:
        raise ValueError("okand falttyp %r, valj bland %s"
                         % (nyckel, sorted(FALTTYPER)))
    return FALTTYPER[nyckel]


# ---- sondera_falt ------------------------------------------------------------

FALTKONSTANTER = (
    "VC_FLOWFIELD", "VC_TRANSPORTFIELD", "VC_SIGNALFIELD", "VC_HIERARCHYFIELD",
    "VC_PROCESSORFIELD", "VC_ATTACHMENTFIELD", "VC_ACTIONFIELD",
    "VC_INTEGERCOMPATIBILITYFIELD", "VC_RSLFIELD", "VC_BASEEXPORTFIELD",
    "VC_JOINTEXPORTFIELD", "VC_TOOLEXPORTFIELD",
)

BETEENDEKONSTANTER = (
    "VC_ONEWAYPATH", "VC_COMPONENTCONTAINER", "VC_COMPONENTCREATOR",
    "VC_CONTAINERFILLER", "VC_COMPONENTFLOWPROXY", "VC_TRANSPORT",
    "VC_ONEDIRECTIONALPATH", "VC_CONTAINER", "VC_CONVEYORTRANSPORTCONTROLLER",
)


def sondera_falt(argument):
    """Matinstrumentet: ett falt av varje typ och ett beteende av varje
    flodestyp i en skrapkomponent; dumpar egenskaper och kontakter, tar bort
    komponenten. Svarar pa B0, C1/C2, D0 och A1 i EN korning."""
    namn = argument.get("name", "VCA_Sond")
    rader = _inledning() + _nyko(namn) + [
        "g = k.createBehaviour(VC_ONETOONEINTERFACE, %s)" % lit("Sond"),
        "sek = g.createSection(%s)" % lit("Sond"),
        "falt = []",
    ]
    for konst in FALTKONSTANTER:
        rader += [
            "def skapa_%s():" % konst.lower(),
            "    f = sek.createField(%s, %s)" % (konst, lit(konst)),
            "    if f is None:",
            '        raise ValueError("createField gav None")',
            '    return {"constant": %s, "name": f.Name, "type": _enkelt(f.Type),'
            ' "properties": _egenskaper(f)}' % lit(konst),
            "ok, r = _forsok(forsok, %s, skapa_%s)" % (lit("B0"), konst.lower()),
            "if ok:",
            "    falt.append(r)",
        ]
    rader += ["beteenden = []"]
    for konst in BETEENDEKONSTANTER:
        rader += [
            "def skapa_%s():" % konst.lower(),
            "    b = k.createBehaviour(%s, %s)" % (konst, lit(konst)),
            "    if b is None:",
            '        raise ValueError("createBehaviour gav None")',
            '    return {"constant": %s, "name": b.Name, "class": _typnamn(b),'
            ' "type": _enkelt(b.Type)}' % lit(konst),
            "ok, r = _forsok(forsok, %s, skapa_%s)" % (lit("D0"), konst.lower()),
            "if ok:",
            # Kontakterna for sig (hypotes C1): ett beteende utan Connectors
            # ar ett matt utfall, inte ett bortfall av hela posten.
            "    def kontakter_%s():" % konst.lower(),
            "        return _kontakter(k.findBehaviour(%s))" % lit(konst),
            "    ok2, r2 = _forsok(forsok, %s, kontakter_%s)" % (lit("C1"), konst.lower()),
            '    r["connectors"] = r2 if ok2 else None',
            "    beteenden.append(r)",
        ]
    behall = bool(argument.get("behall", False))
    rader += [
        "kvar = %r" % behall,
        "if not kvar:",
        "    app.deleteComponent(k)",
        '_svara({"probe": %s, "kept": kvar, "fields": falt,' % lit(namn),
        '        "behaviours": beteenden, "forsok": forsok})',
    ]
    return bygg(["_enkelt", "_svara"], rader, ["vcVector"])


# ---- transportor ---------------------------------------------------------------

def _transportor_rader(argument, ackumulera, kapacitet):
    namn = argument["name"]
    langd = float(argument.get("langd", 1000.0))
    bredd = float(argument.get("bredd", 400.0))
    hojd = float(argument.get("hojd", 700.0))
    hastighet = float(argument.get("hastighet", 200.0))
    abstrakt = bool(argument.get("abstrakt", False))
    vrid_ut = float(argument.get("vrid_ut", 180.0))     # hypotes F1; 0 = F2
    falttyp = _falttyp(argument)
    rader = _inledning() + _nyko(namn)
    if argument.get("geometri", True):
        rader += _block(langd, bredd, hojd)
    else:
        rader += ["kroppens_egenskaper = []"]
    rader += [
        # Ramar: banans borjan och slut, pa banans ovansida (hypotes F0).
        "ram_in = _ram(k, %s, 0.0, 0.0, %s, 0.0)" % (lit("PathIn"), tal(hojd)),
        "ram_ut = _ram(k, %s, %s, 0.0, %s, %s)" % (lit("PathOut"), tal(langd),
                                                    tal(hojd), tal(vrid_ut)),
        # Banan (hypotes C0/C3).
        "bana = k.createBehaviour(VC_ONEWAYPATH, %s)" % lit("Path"),
        "if bana is None:",
        '    raise ValueError("createBehaviour(VC_ONEWAYPATH) gav None")',
        "bana.Path = [ram_in, ram_ut]",
        "bana.Speed = %s" % tal(hastighet),
        "bana.Accumulate = %r" % bool(ackumulera),
    ]
    if kapacitet is not None:
        rader.append("bana.Capacity = %d" % int(kapacitet))
    rader += [
        "kontakt_in = _kontakt(forsok, bana, VC_CONNECTOR_INPUT)",
        "kontakt_ut = _kontakt(forsok, bana, VC_CONNECTOR_OUTPUT)",
        "granssnitt = []",
        "def bygg_in():",
        "    return _granssnitt(forsok, k, %s, ram_in, %s, kontakt_in, bana, %r)"
        % (lit("InInterface"), falttyp, abstrakt),
        "def bygg_ut():",
        "    return _granssnitt(forsok, k, %s, ram_ut, %s, kontakt_ut, bana, %r)"
        % (lit("OutInterface"), falttyp, abstrakt),
        "ok, r = _forsok(forsok, %s, bygg_in)" % lit("C3"),
        "if ok:",
        "    granssnitt.append(r)",
        "ok, r = _forsok(forsok, %s, bygg_ut)" % lit("C3"),
        "if ok:",
        "    granssnitt.append(r)",
        '_svara({"built": True, "component": k.Name, "kind": %s,'
        % lit("buffert" if kapacitet is not None else "transportor"),
        '        "path_length": bana.PathLength, "capacity": bana.Capacity,',
        '        "accumulate": bool(bana.Accumulate),',
        '        "body_properties": kroppens_egenskaper,',
        '        "connectors": _kontakter(bana), "behaviours": _beteenden(k),',
        '        "interfaces": granssnitt, "forsok": forsok})',
    ]
    return rader


def transportor(argument):
    """En bana som tar emot i ena anden och lamnar i den andra (fraga C)."""
    return bygg(["_enkelt", "_svara"],
                _transportor_rader(argument, False, None), ["vcVector"])


def buffert(argument):
    """Ett buffertmagasin: ackumulerande bana med N platser (hypotes D4)."""
    kapacitet = int(argument.get("kapacitet", 10))
    if kapacitet < 1:
        raise ValueError("kapacitet maste vara minst 1")
    return bygg(["_enkelt", "_svara"],
                _transportor_rader(argument, True, kapacitet), ["vcVector"])


# ---- matare -----------------------------------------------------------------------

def matare(argument):
    """Skapar produkter och lamnar dem genom ett ut-granssnitt (hypotes D1).

    Mallen ar antingen en komponent som redan star i scenen (mall) eller en
    URI (del_uri). Katalogen ar matt tom, sa mall ar den vanliga vagen: bygg
    en produkt (t.ex. med transportor-receptets block) och namnge den."""
    namn = argument["name"]
    intervall = float(argument.get("intervall", 5.0))
    # D5: Limit satts ALLTID. En skapare byggd utan Limit skapade noll
    # produkter pa 6 s simtid (MATT 2026-09-04).
    grans = int(argument.get("grans", 1000000))
    abstrakt = bool(argument.get("abstrakt", False))
    falttyp = _falttyp(argument)
    hojd = float(argument.get("hojd", 700.0))
    rader = _inledning() + _nyko(namn) + _block(
        float(argument.get("langd", 400.0)),
        float(argument.get("bredd", 400.0)), hojd)
    rader += [
        "ram_ut = _ram(k, %s, %s, 0.0, %s, %s)" % (
            lit("Out"), tal(float(argument.get("langd", 400.0))), tal(hojd),
            tal(float(argument.get("vrid_ut", 180.0)))),
        "skapare = k.createBehaviour(VC_COMPONENTCREATOR, %s)" % lit("Creator"),
        "if skapare is None:",
        '    raise ValueError("createBehaviour(VC_COMPONENTCREATOR) gav None")',
        "skapare.Enabled = True",
        "skapare.Interval = %s" % tal(intervall),
        "skapare.Limit = %d" % grans,
        "mallnamn = None",
    ]
    if "mall" in argument:
        rader += [
            "mall = _komp(%s)" % lit(argument["mall"]),
            "if mall.Name == k.Name:",
            '    raise ValueError("mallen kan inte vara mataren sjalv")',
            "skapare.TemplateComponent = mall",
            "if skapare.TemplateComponent is not None:",
            "    mallnamn = skapare.TemplateComponent.Name",
        ]
    elif "del_uri" in argument:
        rader.append("skapare.Part = %s" % lit(argument["del_uri"]))
    rader += [
        # Las tillbaka ALLT som sattes (uppgift B): vardet i svaret ar det
        # VC har, inte det vi skickade.
        'aterlast = {"interval": skapare.Interval, "limit": skapare.Limit,',
        '            "part": skapare.Part, "template": mallnamn,',
        '            "enabled": bool(skapare.Enabled),',
        '            "interval_tog": skapare.Interval == %s,' % tal(intervall),
        '            "limit_tog": skapare.Limit == %d,' % grans,
        '            "template_tog": mallnamn is not None or bool(skapare.Part)}',
        "kontakt_ut = _kontakt(forsok, skapare, VC_CONNECTOR_OUTPUT)",
        "granssnitt = []",
        "def bygg_ut():",
        "    return _granssnitt(forsok, k, %s, ram_ut, %s, kontakt_ut, skapare, %r)"
        % (lit("OutInterface"), falttyp, abstrakt),
        "ok, r = _forsok(forsok, %s, bygg_ut)" % lit("D1"),
        "if ok:",
        "    granssnitt.append(r)",
        '_svara({"built": True, "component": k.Name, "kind": %s,' % lit("matare"),
        '        "creator": aterlast,',
        '        "creator_properties": _egenskaper(skapare),',
        '        "body_properties": kroppens_egenskaper,',
        '        "connectors": _kontakter(skapare), "behaviours": _beteenden(k),',
        '        "interfaces": granssnitt, "forsok": forsok})',
    ]
    hjalpare = ["_enkelt", "_svara"]
    if "mall" in argument:
        hjalpare.append("_komp")
    return bygg(hjalpare, rader, ["vcVector"])


# ---- sanka ----------------------------------------------------------------------------

def sanka(argument):
    """Tar emot produkter i en osynlig behallare (hypotes D2). Tar INTE bort
    dem: det kraver ett skriptbeteende, och det stoppar bryggan (M-13)."""
    namn = argument["name"]
    kapacitet = int(argument.get("kapacitet", 1000000))
    abstrakt = bool(argument.get("abstrakt", False))
    falttyp = _falttyp(argument)
    hojd = float(argument.get("hojd", 700.0))
    rader = _inledning() + _nyko(namn) + _block(
        float(argument.get("langd", 400.0)),
        float(argument.get("bredd", 400.0)), hojd)
    rader += [
        "ram_in = _ram(k, %s, 0.0, 0.0, %s, 0.0)" % (lit("In"), tal(hojd)),
        "behallare = k.createBehaviour(VC_COMPONENTCONTAINER, %s)" % lit("Sink"),
        "if behallare is None:",
        '    raise ValueError("createBehaviour(VC_COMPONENTCONTAINER) gav None")',
        "behallare.Capacity = %d" % kapacitet,
        "behallare.ContentVisible = %r" % bool(argument.get("synlig", False)),
        "kontakt_in = _kontakt(forsok, behallare, VC_CONNECTOR_INPUT)",
        "granssnitt = []",
        "def bygg_in():",
        "    return _granssnitt(forsok, k, %s, ram_in, %s, kontakt_in, behallare, %r)"
        % (lit("InInterface"), falttyp, abstrakt),
        "ok, r = _forsok(forsok, %s, bygg_in)" % lit("D2"),
        "if ok:",
        "    granssnitt.append(r)",
        '_svara({"built": True, "component": k.Name, "kind": %s,' % lit("sanka"),
        '        "capacity": behallare.Capacity,',
        '        "body_properties": kroppens_egenskaper,',
        '        "connectors": _kontakter(behallare), "behaviours": _beteenden(k),',
        '        "interfaces": granssnitt, "forsok": forsok})',
    ]
    return bygg(["_enkelt", "_svara"], rader, ["vcVector"])


# ---- koppla -------------------------------------------------------------------------------

def koppla(argument):
    """Kopplar tva byggda komponenter: ut-granssnittet i a mot in-granssnittet
    i b. Provar stegen i ordning och bokfor varje utfall:

      E0  canConnect + connect pa granssnitten (den riktiga vagen)
      G0  app.connectComponents(a, b)          (VC matchar sjalv)
      B5  kontakt mot kontakt, utanfor granssnitten (MATT: fungerar)

    Kontakterna valjs over ALLA beteenden i komponenten pa Type (uppgift A):
    Output i a, Input i b; okopplad fore kopplad; aldrig pa index eller
    beteendenamn. beteende_a/beteende_b ar valfria FILTER, inte uppslag.
    Stannar vid forsta steg som ger en verklig koppling."""
    a = lit(argument["a"])
    b = lit(argument["b"])
    g_a = lit(argument.get("granssnitt_a", "OutInterface"))
    g_b = lit(argument.get("granssnitt_b", "InInterface"))
    filter_a = lit(argument["beteende_a"]) if "beteende_a" in argument else "None"
    filter_b = lit(argument["beteende_b"]) if "beteende_b" in argument else "None"
    rader = _inledning() + [
        "app = getApplication()",
        "forsok = []",
        "ka = _komp(%s)" % a,
        "kb = _komp(%s)" % b,
        "ga = ka.findBehaviour(%s)" % g_a,
        "gb = kb.findBehaviour(%s)" % g_b,
        "vag = None",
        "if ga is not None and gb is not None:",
        "    def via_granssnitt():",
        "        kan = bool(ga.canConnect(gb))",
        "        if not kan:",
        '            raise ValueError("canConnect ar False")',
        "        if not ga.connect(gb):",
        '            raise ValueError("connect gav False fast canConnect var True")',
        "        return _anslutna(ga)",
        "    ok, r = _forsok(forsok, %s, via_granssnitt)" % lit("E0"),
        "    if ok:",
        "        vag = %s" % lit("E0"),
        "else:",
        '    forsok.append({"hypotes": %s, "utfall": "fel",' % lit("E0"),
        '                   "fel": "granssnittet saknas: " + repr(ga is None) + " / " + repr(gb is None)})',
        "if vag is None:",
        "    def via_app():",
        "        if not app.connectComponents(ka, kb):",
        '            raise ValueError("connectComponents gav False")',
        "        return True",
        "    ok, r = _forsok(forsok, %s, via_app)" % lit("G0"),
        "    if ok:",
        "        vag = %s" % lit("G0"),
        "ut = None",
        "inn = None",
        "if vag is None:",
        "    ut = _valj_kontakt(forsok, ka, VC_CONNECTOR_OUTPUT, %s, %s)" % (filter_a, lit("ut")),
        "    inn = _valj_kontakt(forsok, kb, VC_CONNECTOR_INPUT, %s, %s)" % (filter_b, lit("in")),
        "    if ut is None or inn is None:",
        '        raise ValueError("ingen kontakt att koppla: ut=" + repr(ut is None) + " in=" + repr(inn is None))',
        "    def via_kontakt():",
        "        ut.connect(inn)",
        "        if ut.Connection is None:",
        '            raise ValueError("connect gav ingen Connection")',
        "        return ut.Connection.Name",
        "    ok, r = _forsok(forsok, %s, via_kontakt)" % lit("B5"),
        "    if ok:",
        "        vag = %s" % lit("B5"),
        "    else:",
        "        def via_egenskap():",
        "            ut.Connection = inn",
        "            if ut.Connection is None:",
        '                raise ValueError("Connection forblev None")',
        "            return ut.Connection.Name",
        "        ok, r = _forsok(forsok, %s, via_egenskap)" % lit("B5"),
        "        if ok:",
        "            vag = %s" % lit("B5"),
        "kontaktpar = None",
        "if ut is not None and inn is not None:",
        '    kontaktpar = {"ut": ut.Name, "ut_index": ut.Index,',
        '                  "ut_connected": ut.Connection is not None,',
        '                  "in": inn.Name, "in_index": inn.Index,',
        '                  "in_connected": inn.Connection is not None}',
        '_svara({"connected": vag is not None, "via": vag,',
        '        "a": ka.Name, "b": kb.Name, "connectors": kontaktpar,',
        '        "a_connected_to": _anslutna(ga) if ga is not None else None,',
        '        "b_connected_to": _anslutna(gb) if gb is not None else None,',
        '        "a_is_connected": bool(ga.IsConnected) if ga is not None else None,',
        '        "b_is_connected": bool(gb.IsConnected) if gb is not None else None,',
        '        "forsok": forsok})',
    ]
    return bygg(["_komp", "_anslutna", "_enkelt", "_svara"], rader, ["vcVector"])


# ---- las_flode (uppgift C) -------------------------------------------------------

def las_flode(argument):
    """LASANDE. Svarar pa den enda fraga som raknas: rorde sig nagot?

    Per komponent: lage i varlden, vilken behallare den ligger i, avstand pa
    banan, skapelsetid (>0 = skapad under simuleringen). Per beteende som
    lagrar: antal och namn. Plus simtid och totalt antal komponenter. Kor
    fore och efter en simulering och jamfor."""
    rader = _inledning_lasande() + [
        "app = getApplication()",
        "sim = app.getSimulation()",
        "komponenter = []",
        "innehall = []",
        "avkortad = False",
        "for k in app.Components:",
    ] + tak("komponenter") + [
        "    m = k.WorldPositionMatrix",
        "    behallare = k.Container",
        "    avstand = None",
        "    if behallare is not None:",
        "        try:",
        "            avstand = k.getPathDistance()",
        "        except Exception:",
        "            avstand = None",
        '    komponenter.append({"name": k.Name,',
        '                        "position": [m.P.X, m.P.Y, m.P.Z],',
        '                        "creation_time": k.CreationTime,',
        '                        "container": None if behallare is None else behallare.Name,',
        '                        "container_of": None if behallare is None else behallare.Component.Name,',
        '                        "path_distance": avstand})',
        "    for b in k.Behaviours:",
        "        try:",
        "            lagrade = b.Components",
        "            antal = b.ComponentCount",
        "        except AttributeError:",
        "            continue",
        "        namn = []",
        "        for c in lagrade:",
        "            namn.append(c.Name)",
        '        innehall.append({"component": k.Name, "behaviour": b.Name,',
        '                         "class": _typnamn(b), "count": antal, "contents": namn})',
        '_svara({"sim_time": sim.SimTime, "running": bool(sim.IsRunning),',
        '        "component_count": len(app.Components), "components": komponenter,',
        '        "containers": innehall, "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


# ---- registret ---------------------------------------------------------------------------------

RECEPT = {
    "sondera_falt": sondera_falt,
    "transportor": transportor,
    "buffert": buffert,
    "matare": matare,
    "sanka": sanka,
    "koppla": koppla,
    "las_flode": las_flode,
}

# Vilka recept som SKRIVER. Skrivgrinden maste doma dem sa, och las_flode
# maste slippa igenom som lasande (test_byggrecept.py).
EFFEKT = {namn: "write" for namn in RECEPT}
EFFEKT["las_flode"] = "read"

# Ett minsta och ett storsta anrop per recept. Testerna kor ALLA, sa ett
# recept utan exempel far inte finnas.
EXEMPEL = {
    "sondera_falt": [{}, {"name": "Sond", "behall": True}],
    "transportor": [{"name": "Bana1"},
                    {"name": "Bana2", "langd": 2000, "bredd": 500, "hojd": 800,
                     "hastighet": 300, "abstrakt": True, "vrid_ut": 0,
                     "falttyp": "transport", "geometri": False}],
    "buffert": [{"name": "Buffert1"}, {"name": "Buffert2", "kapacitet": 5}],
    "matare": [{"name": "Matare1"},
               {"name": "Matare2", "mall": "Produkt", "intervall": 2.5,
                "grans": 100, "abstrakt": True},
               {"name": "Matare3", "del_uri": "file:///c/produkt.vcm"}],
    "sanka": [{"name": "Sanka1"}, {"name": "Sanka2", "kapacitet": 50, "synlig": True}],
    "koppla": [{"a": "Bana1", "b": "Bana2"},
               {"a": "Matare1", "b": "Bana1", "granssnitt_a": "OutInterface",
                "granssnitt_b": "InInterface", "beteende_a": "Creator",
                "beteende_b": "Path"}],
    "las_flode": [{}],
}


def generera(namn, argument=None):
    """Koden for ett recept. Okant recept ar ett fel, aldrig en gissning."""
    if namn not in RECEPT:
        raise KeyError("okant recept %r, valj bland %s" % (namn, sorted(RECEPT)))
    return RECEPT[namn](dict(argument or {}))
