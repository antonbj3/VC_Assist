# -*- coding: utf-8 -*-
"""F1: modellen skriver linan, och ogat talar tillbaka.

`M-74`:s rigg, OFORANDRAD, med **modellen som forfattare** i stallet for
fixturen. Bada matningarna som byggde linan sager sin egen grans med samma
mening: *"Alla ST-kroppar ar handskrivna, och reparationsvarven ar noll av
samma skal: ingen modell har fatt nagot fel tillbaka att laga."* Den har
korningen ar det som gor det mojligt att andra.

## Vad som ar nytt, och det ar EN sak

Fas 9:s slinga (`kor_fas9_slingan.py`) matar tillbaka GRINDARNAS ord. Den har
matar tillbaka **OGATS** ord:

    EYES VERDICT FAIL interlock: ST8A_Don/Slapp och ST8B_Don/Slapp hoga
    samtidigt i 3.90 s, 45 prov

Ogat ar ett `Grindsteg` som varje annat i `reparation.py`. Det ar inte en
bekvamlighet: `Reparationsslinga` kontrollerar redan mekaniskt att varje
fallande grinds `utdata` nar modellen TECKEN FOR TECKEN
(`kontrollera_ordagrant`). Att lagga ogat i den kedjan ar darfor det enda
sattet att fa doktrinen "observatorens egna ord" mekaniserad ocksa for grind
5, i stallet for att skriva en andra slinga som lovar samma sak i en
docstring.

Kedjan per varv:

    modellen skriver kroppen
        -> grind 1-3 (billigt, ingen VC)      fallt: grindens egna ord tillbaka
        -> OpenPLC + VC-scenen + ogat         fallt: OGATS egna ord tillbaka
        -> guldgrinden over tre celler        gront: GOLD, slingan slutar

## Tre invarianter som inte ar forhandlingsbara

**1. Forfattaren ar en PARAMETER.** Tre transporter gar att valja:
`modellklient.ClaudeCLI`, `kor_fas9_musespark.OpencodeCLI` och
`modellklient.Inspelad`. Operatoren valjer modell med en flagga, och armens
modellnamn skrivs i JSON:en (RATTELSER 2026-09-05 16:25: en arm pa en annan
modell ar en ANNAN matning).

**2. Forfattarmodellen far ALDRIG na facit.** Varje transport maste bara bada
lagren `modellklient` bygger: tom verktygslista OCH en arbetskatalog utanfor
repot, kontrollerad av `_neka_repot`. `Forfattare` avvisar en transport som
saknar dem - det ar en mekanisk kontroll, inte en uppmaning, och den finns for
att den billigaste vagen till ett gront F1 vore en modell som lasar
`kor_fas8_linan.py`.

**3. n >= 3.** A2 matte att OpenPLC-domaren inte ar deterministisk vid n = 1 -
realtidens jitter avgjorde en invariant i L-01. Ett enskilt GOLD bevisar
ingenting, och riggen vagrar korra med farre an tre korningar per uppgift.

## Grontkriteriet, mekaniserat

Bada halvorna raknas, och korningen sager VILKEN som foll:

    guld           GOLD inom fyra varv i minst 2 av 3 korningar
    komposition    minst 3 av 5 kompositionsfall lagade pa ogats egna ord

Rott ar ett lika giltigt svar. Faller F1 ar produkten banken, inte slingan,
och den slutsatsen ska skrivas i matningen.

    # torrt, utan modell och utan VC - provar RIGGEN
    python3 tests/protocol/kor_F1_modellen_skriver_linan.py --torrkorning \\
        --json /tmp/f1_torr.json

    # pa riktigt, nar operatoren valt modell
    python3 tests/protocol/kor_F1_modellen_skriver_linan.py \\
        --forfattare claude --modell sonnet \\
        --strucpp <npm-katalog> --runtime-include <include> \\
        --upprepa 3 --json docs/matningar/data/M-160_f1.json
"""

BANKPOST = {
    "pastar":
        "En sprakmodell som far ogats egna ord tillbaka skriver linans "
        "ST-kropp till GOLD inom fyra varv i minst 2 av 3 korningar, och "
        "lagar minst 3 av 5 kompositionsfel pa ogats egen felbeskrivning.",
    "under_prov": (
        "tests/protocol/kor_F1_modellen_skriver_linan.py",
        "svc/vc_assist_svc/plc/reparation.py",
        "svc/vc_assist_svc/modellklient.py",
        "svc/vc_assist_svc/claudeadapter.py",
        "svc/vc_assist_svc/guldgrind.py",
        "ext/vc_addon/vc_assist/oga_analys.py",
    ),
    "facit":
        "ogats plan for linan och for var station, deklarerad FORE "
        "losningarna i M-73/M-74 och oforandrad har; GOLD ar guldgrindens dom "
        "over de tre cellerna, och taket ar fyra varv (M-52)",
    "facitkalla":
        "linjens krav raknade ur scenens egna matt (banornas langd och fart, "
        "utmatningstiden), med klockbraketten satt av M-73; "
        "kompositionsfallen K1-K5 och deras klassning kommer ur M-74, en "
        "tidigare matning med starkare kalla. Ingen del av facit raknas fram "
        "av koden som doms har.",
    "facitkalla_filer": (
        "tests/protocol/kor_fas8_linan.py",
        "tests/protocol/fas8_linan.md",
        "docs/matningar/M-74_kompositionsfallen.md",
        "docs/matningar/M-73_linan_arbetar.md",
        "docs/matningar/M-52_reparationsslingan.md",
    ),
    "trasiga_fall": (
        "en forfattarmodell som far verktyg MASTE ge korningsfel, aldrig en "
        "dom - ett textsvar dar hade matt modellens ovilja att anvanda "
        "verktyg i stallet for dess formaga att skriva ST",
        "en transport utan `_neka_repot` avvisas: en andra vag in till "
        "modellen som saknar spärrarna gor matningen ogiltig",
        "en korning som slar i taket rapporteras som slog_i_taket, aldrig som "
        "lost eller gold",
        "ogats aterkoppling som ar tom far inte tyst bli ett varv utan "
        "innehall - korningen blir OGILTIG",
        "en klockkvot utanfor M-73:s brakett gor korningen OGILTIG, inte "
        "fallande",
        "ett kompositionsfall vars seed ogat SLAPPER igenom raknas aldrig som "
        "lagat - da var fixturen trasig, inte modellen duktig",
        "en torrkorning (inspelad modell eller inspelad scen) kan aldrig ge "
        "ett gront F1",
    ),
    "kraver": ("vc", "openplc", "strucpp", "modell"),
    "matningar": ("M-160",),
}

import argparse
import inspect
import json
import os
import re
import sys
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "svc"),
           os.path.join(_ROT, "ext", "vc_addon", "vc_assist"),
           os.path.dirname(os.path.abspath(__file__)), _ROT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import oga_kontrakt as K                                          # noqa: E402
import kor_fas8_linan as L                                        # noqa: E402
from vc_assist_svc import guldgrind, modellklient                 # noqa: E402
from vc_assist_svc.claudeadapter import ClaudeModell              # noqa: E402
from vc_assist_svc.klient import Klient                           # noqa: E402
from vc_assist_svc.api_index import bygg_validator                # noqa: E402
from vc_assist_svc.plc import reparation as R                     # noqa: E402
from vc_assist_svc.plc import stationsgrind as S                  # noqa: E402
from vc_assist_svc.plc.skelett import Skelett                     # noqa: E402


class Riggfel(Exception):
    """Riggen gar inte att stalla upp. Aldrig en dom, aldrig ett resultat."""


class Ogonfel(Exception):
    """Korningen ar OGILTIG. Skilt fran att den fallde.

    M-74:s regel, oforandrad: en korning vars klocka lag utanfor braketten
    matte kopplingen mellan klockorna i stallet for stationen, och en dom pa
    ett fonster som inte langre betyder nagot ar ingen dom. Detsamma galler en
    ogonrapport utan ord: den kan inte lagas pa, sa den far inte kosta ett
    varv av taket.
    """


# n = 1 sager ingenting. A2 matte att OpenPLC-domaren inte ar deterministisk
# vid n = 1: realtidens jitter avgjorde en invariant i L-01. Talet ar alltsa
# inte en smaksak utan en foljd av en matning.
MIN_N = 3

# Grontkriteriets tva halvor, ur KO_F §F1. Talen ar UPPDRAGETS, inte matta
# trosklar - de star har pa ETT stalle sa att bada raknas av samma kod.
GULD_AV = 2                 # GOLD i minst 2 av 3 korningar
GULD_TOTALT = 3
KOMPOSITION_AV = 3          # minst 3 av 5 kompositionsfall lagade
KOMPOSITION_TOTALT = 5

# Grindarna som gar att doma FORE ogat, alltsa utan scenkod.
#
# Grind 4 (anropsvalidering) ar INTE med, och skalet ar matt i den har riggens
# forsta uppstallning: `Stationssteg` bygger sin kandidat utan scenkod, och en
# kandidat utan scenkod ger inte `anropsvalidering: True` - den ger skalet till
# att grinden inte kunde kora. Lades den i den billiga kedjan hade VARJE
# modellsvar fallt pa grind 4 innan ogat fick se nagot, och matningen hade
# rapporterat riggens egen brist som modellens. Grind 4 kors dar scenkoden
# finns: inne i ogonsteget, genom M-74:s egen `kor_en`.
BILLIGA_GRINDAR = (S.NAMN_STATISK, S.NAMN_DEKLARATION, S.NAMN_KOMPILERING)

KONFIG = "LINJE"
OGON_CELLER = ("stationA", "stationB", "linan")
KOMPOSITIONSFALL = ("K1", "K2", "K3", "K4", "K5")

TRANSPORTER = ("claude", "opencode", "inspelad")

# De tva lagren varje transport maste bara for att fa fraga forfattarmodellen.
# Kontrollen ar mekanisk och lases ur transportens EGEN kalla: ett forbud i en
# docstring ar en bon, och den billigaste vagen till ett gront F1 vore en
# modell som lasar `kor_fas8_linan.py`.
SPARR_KATALOG = "_neka_repot"           # arbetskatalog utanfor repot
SPARR_VERKTYG = ("allowed-tools",       # ClaudeCLI: tom verktygslista
                 "verktygslarm")        # OpencodeCLI: fail-closed pa verktyg

_VERDICT = re.compile(r"^EYES VERDICT (PASS|FAIL|INCONCLUSIVE) ([^:\n]+)",
                      re.M)


# ------------------------------------------------------------- skelettet

KARTA = L.karta(KONFIG)
SKELETT = Skelett.av_karta(KARTA, L.DEKLARATIONER)


def st_kalla_av(kropp: str) -> str:
    """Modellens kropp i skelettets ram. Ramgrinden bubblar med flit."""
    return SKELETT.las_svar(kropp)


# ------------------------------------------------------------ forfattaren

class Forfattare(ClaudeModell):
    """Vilken transport som helst bakom `Modell`-ytan, MED adapterns sparrar.

    Arver `ClaudeModell` i stallet for att kopiera den, och det ar poangen:
    dess `svara` kastar `Adapterfel` sa fort den far verktyg, den skalar av ett
    kodstaket som ligger runt HELA svaret, och den summerar kostnaden. En andra
    vag in till modellen skulle vara en vag utan de sakerna.
    """

    def __init__(self, klient, namn=None):
        kontrollera_sparrarna(klient)
        ClaudeModell.__init__(self, klient=klient, namn=namn)
        self.transport = klient
        self.leverantor = "f1/%s" % getattr(klient, "namn", "okand")


def kontrollera_sparrarna(klient) -> None:
    """Transporten maste bara BADA lagren, eller sa far den inte fraga.

    `Inspelad` ror varken natverk eller katalog och ar darfor undantagen - men
    en korning pa den ar en TORRKORNING och kan aldrig ge ett gront F1
    (`grontkriteriet`).
    """
    if isinstance(klient, modellklient.Inspelad):
        return
    if not isinstance(klient, modellklient.Modellklient):
        raise Riggfel(
            "%r ar ingen modellklient.Modellklient; en transport utanfor den "
            "ytan har inga sparrar att kontrollera"
            % (type(klient).__name__,))
    try:
        kalla = inspect.getsource(type(klient))
    except (OSError, TypeError) as fel:
        raise Riggfel(
            "kan inte lasa kallan till transporten %s (%s), sa spärrarna gar "
            "inte att kontrollera. En okontrollerbar transport far inte fraga "
            "forfattarmodellen." % (type(klient).__name__, fel))
    if SPARR_KATALOG not in kalla:
        raise Riggfel(
            "transporten %s anropar aldrig %s. Modellen skulle kunna kora i "
            "repot, och bankens facit ligger dar: matningens giltighet star "
            "pa att den inte sett det." % (type(klient).__name__, SPARR_KATALOG))
    if not any(m in kalla for m in SPARR_VERKTYG):
        raise Riggfel(
            "transporten %s bar inget verktygssparr (%s). En modell med "
            "verktyg kan lasa facit, och ett textsvar darifran hade sett ut "
            "som ett arligt svar." % (type(klient).__name__,
                                      ", ".join(SPARR_VERKTYG)))


def bygg_forfattare(transport, modell=None, svar=None, tidsgrans=900):
    """Forfattaren ar en PARAMETER. Aldrig en hardkodning."""
    if transport == "inspelad":
        if not svar:
            raise Riggfel(
                "transporten `inspelad` kraver fardiga svar. En inspelning "
                "utan svar hade blivit tystnad, och tystnad ar aldrig ett "
                "godkannande (I3).")
        return Forfattare(modellklient.Inspelad(svar), namn="inspelad")
    if transport == "claude":
        return Forfattare(
            modellklient.ClaudeCLI(modell=modell or "sonnet",
                                   tidsgrans=tidsgrans),
            namn=modell or "sonnet")
    if transport == "opencode":
        import kor_fas9_musespark as MS
        return Forfattare(
            MS.OpencodeCLI(modell=modell or MS.MODELL_ID, tidsgrans=tidsgrans),
            namn=modell or MS.MODELL_ID)
    raise Riggfel("okand transport %r; transporterna ar %s"
                  % (transport, ", ".join(TRANSPORTER)))


def kontrollera_n(n) -> int:
    """n >= 3, och det ar inte en smaksak (A2)."""
    if not isinstance(n, int) or isinstance(n, bool) or n < MIN_N:
        raise Riggfel(
            "n = %r. A2 matte att OpenPLC-domaren inte ar deterministisk vid "
            "n = 1 - jitter avgjorde en invariant i L-01 - sa varje uppgift "
            "kors minst %d ganger. Ett enskilt GOLD bevisar ingenting."
            % (n, MIN_N))
    return n


# ------------------------------------------------------------------- ogat

def ogonkoder(text: str):
    """Ogats EGEN domsrad, last som kod. Aldrig omraknad (I1)."""
    ut = []
    for varde, kort in _VERDICT.findall(text or ""):
        kod = "oga:%s:%s" % (varde.lower(), kort.strip().split()[0])
        if kod not in ut:
            ut.append(kod)
    return tuple(ut)


def ogats_ord(rapporter) -> str:
    """Ogats tre rapporter med en INRAMNING runt, aldrig i.

    Formen ar avsiktligt trakig, av exakt samma skal som
    `reparation.standardinramning`: en inramning som sammanfattar vad ogat
    "menar" ar just den omskrivning som gjorde att en omimplementerad
    positionsdom underkande 2 av 4 medan ogat visade 4 av 4.
    """
    delar = []
    for namn, text in rapporter:
        delar.append("--- ogat dom over %s, ordagrant ---" % namn)
        delar.append(text.rstrip("\n"))
    return "\n".join(delar)


def kontrollera_ogats_ord(utdata: str, rapporter) -> None:
    """Faller om en rapport inte nadde texten tecken for tecken."""
    for namn, text in rapporter:
        if text.rstrip("\n") not in utdata:
            raise Ogonfel(
                "ogats rapport for %s nadde inte modellen ordagrant. "
                "Inramningen skrev om domen, och en grind som tolkar om "
                "observatorens svar mater till slut sig sjalv "
                "(50_grindar.md)." % namn)


def samlad_dom(rad) -> str:
    """M-74:s `_samlad`, oforandrad: tre facit blir en dom."""
    domar = [L._dom_av(rad, namn) for namn in OGON_CELLER]
    if any(x is None for x in domar):
        raise Ogonfel("ogat domde inte alla tre facit (%s); en cell utan dom "
                      "ar aldrig ett godkannande (I3)"
                      % ", ".join("%s=%s" % (n, d)
                                  for n, d in zip(OGON_CELLER, domar)))
    if "OGILTIG" in domar:
        return "OGILTIG"
    if all(x == "PASS" for x in domar):
        return "PASS"
    if any(x == "FAIL" for x in domar):
        return "FAIL"
    return "INCONCLUSIVE"


class Ogonsteg(R.Grindsteg):
    """Grind 5 som ett steg i reparationsslingan.

    Steget kor M-74:s rigg for EN kropp: grind 1-4, kompilering, uppladdning
    till OpenPLC, omstart av runtimen, uppvarmning, matning i VC-scenen, och
    ogats tre domar. Det som kommer tillbaka in i prompten ar ogats EGNA ord.
    """

    namn = "oga"

    def __init__(self, kor_scenen, on_varv=None, guld=None):
        self.kor_scenen = kor_scenen
        self.on_varv = on_varv
        self.guld = guld or guldgrind.Guldgrind(["station", "linje"])
        self.korningar = 0
        self.senaste_rapporttexter = ()
        self.senaste_samlad = None
        self.senaste_guld = None
        self.senaste_rad = None
        self._ej_korda = {}

    # -- ett varv -------------------------------------------------------

    def doma(self, st_kalla: str) -> R.Grinddom:
        self.korningar += 1
        rad = self.kor_scenen(st_kalla)
        rad["ogonvarv"] = self.korningar
        self.senaste_rad = rad
        if self.on_varv:
            self.on_varv(rad)

        # KLOCKGRINDEN (M-74). Utanfor braketten ar korningen OGILTIG, inte
        # fallande: facits fonster ar skalade med braketten, och med kvoten
        # 0,61 syns en 2-sekunderstimer som 1,22 s pa ogats axel.
        if L._klockan_ok(rad) is False:
            raise Ogonfel(
                "klockkvoten %s ligger utanfor braketten %.2f-%.2f. Facits "
                "fonster ar skalade med den, sa korningen ar OGILTIG - inte "
                "fallande (M-74)."
                % (rad.get("klockkvot"), L.KLOCKA_LAG, L.KLOCKA_HOG))

        domar = rad.get("domar") or {}
        if not domar:
            # Grind 1-4 fallde innan ogat hann kora, eller serien kom inte
            # med. Det forsta ar en dom med grindens egna ord; det andra ar en
            # ogiltig korning.
            forst = rad.get("forsta_fallande")
            egen = (rad.get("grindarnas_egna_ord") or {}).get(forst) or ""
            if forst and egen.strip():
                return R.Grinddom(grind="grind:%s" % forst, ok=False,
                                  utdata=egen, koder=R.koder_ur(egen),
                                  klasser=R.klasser_ur(egen))
            raise Ogonfel(
                "ogat lamnade ingen dom och ingen grind fallde med egna ord "
                "(%s). En korning utan dom far inte kosta ett varv av taket."
                % (rad.get("fel") or "utan angivet skal"))

        rapporter = []
        for namn in OGON_CELLER:
            d = domar.get(namn)
            if d is None:
                raise Ogonfel("ogat domde inte %s; tre facit ar tre "
                              "pastaenden, inte ett (M-74)" % namn)
            text = d.get("text") or ""
            if not text.strip():
                # TRASIG FIXTUR (c). `kontrollera_ordagrant` hoppar over tom
                # utdata, sa ett tomt ogonsvar hade blivit ett varv utan
                # innehall: modellen far en inramning utan ord och branner ett
                # varv av fyra pa ingenting.
                raise Ogonfel(
                    "ogats dom over %s bar ingen text. En aterkoppling utan "
                    "ord gar inte att laga pa, och den far darfor inte tyst "
                    "bli ett varv." % namn)
            rapporter.append((namn, text))
        self.senaste_rapporttexter = tuple(t for _n, t in rapporter)

        utdata = ogats_ord(rapporter)
        kontrollera_ogats_ord(utdata, rapporter)
        self.senaste_samlad = samlad_dom(rad)

        beslut = guldbeslut(rad.get("celler") or {}, self.guld)
        self.senaste_guld = beslut
        if beslut.guld:
            return R.Grinddom(grind=self.namn, ok=True, utdata=utdata,
                              koder=ogonkoder(utdata))
        # Guldgrindens skal ligger EFTER ogats ord, aldrig i dem.
        text = utdata + "\n--- guldgrinden ---\n" + beslut.text()
        kontrollera_ogats_ord(text, rapporter)
        return R.Grinddom(grind=self.namn, ok=False, utdata=text,
                          koder=ogonkoder(utdata))

    def ej_korda(self):
        return dict(self._ej_korda)


def guldbeslut(celler, grind=None):
    """Guld per station, SEDAN guld for linan. Tva pastaenden, inte ett."""
    grind = grind or guldgrind.Guldgrind(["station", "linje"])
    stationer = [celler[n] for n in ("stationA", "stationB") if n in celler]
    return grind.doma(stationer, linje=celler.get("linan"))


# --------------------------------------------------------------- scenen

class Bryggan(object):
    """VC-bryggan, med M-74:s omstart mellan korningar.

    Omstarten ar matt (M-49): godkannandekon vaxer med en post per varv, och
    en omstart ger dessutom varje korning SAMMA utgangslage - samma scen,
    samma simuleringstid, samma tomma ko. Det ar avgorande nar fyra varv ska
    jamforas med varandra.
    """

    def __init__(self, starta_om_mellan=True, tak_s=300.0):
        self.starta_om_mellan = starta_om_mellan
        self.tak_s = tak_s
        self._klient = None
        self.omstarter = 0

    def fram(self):
        if self._klient is not None:
            if not self.starta_om_mellan:
                return self._klient
            self._klient.stang()
            self._klient = None
            self.omstarter += 1
            L._starta_om_vc()
            if not L._vanta_pa_bryggan(self.tak_s):
                raise Riggfel("bryggan kom aldrig upp igen efter omstarten")
        elif not L._vanta_pa_bryggan(5.0):
            # Fail-closed med ett besked som gar att handla pa. En rigg som
            # kastar en AttributeError har sagt att nagot ar fel, inte VAD.
            raise Riggfel(
                "ingen brygga svarar pa port 8901. Starta VC med "
                "~/bin/vc-test.sh, eller kor med --torrkorning for att prova "
                "riggen utan VC.")
        self._klient = Klient(port=8901, tokenfil=L.TOKEN,
                              timeout=180.0).anslut()
        return self._klient

    def stang(self):
        if self._klient is not None:
            self._klient.stang()
            self._klient = None


class Scenkorare(object):
    """M-74:s `kor_en`, oforandrad, for EN kropp i LINJE-konfigurationen."""

    torr = False

    def __init__(self, argument, index, bryggan, konfig=KONFIG, namn="F1"):
        self.a = argument
        self.index = index
        self.bryggan = bryggan
        self.konfig = konfig
        self.namn = namn
        self.n = 0

    def __call__(self, st_kalla):
        self.n += 1
        brygga = self.bryggan.fram()
        etikett = "%s_%03d" % (self.namn, self.n)
        print("      --- ogat: %s / %s ---" % (etikett, self.konfig),
              flush=True)
        rad = L.kor_en(etikett, self.konfig, st_kalla, self.a, self.index,
                       brygga)
        rad["kropp"] = st_kalla
        return rad


# ---- den inspelade scenen: for att PROVA riggen, aldrig for att mata ----

def demorapport(dom, orsak, template="fas8_linan"):
    """En giltig EYES v2-rapport, skriven med OGATS EGEN skrivare.

    Finns bara for torrkorningen och proven. Att den byggs med
    `oga_kontrakt.Rapport` och inte som en strang ar avsiktligt: guldgrinden
    far da doma en RIKTIG rapport genom sin riktiga lasare, i stallet for att
    fa ett svar riggen bestamt at den. En torrkorning stamplas anda
    `torrkorning` och kan aldrig ge ett gront F1.
    """
    r = K.Rapport(template, "2026-01-01T00:00:00", 80.0, 1600, 20.0)
    r.sektion("MOTION")
    r.rad("GRIP FORMED t=1.000s dist=1.000mm")
    r.rad("CARRY RIGID rot=0.100deg span=1.000s")
    r.rad("PLACE IN_TARGET err=0.500mm z=0.500m")
    r.sektion("TIMING")
    r.rad("EDGE ST8A_Givare/Puls RISE t=8.000s")
    r.rad("RACE none")
    if dom != "PASS":
        r.sektion("SEQUENCE")
        r.rad("INTERLOCK ST8A_Don/Slapp+ST8B_Don/Slapp BROKEN overlap=3.900s")
    r.sektion("SAFETY")
    r.rad("COLLISION none")
    r.sektion("HONESTY")
    for rad in ("TELEPORT_TRANSFER OK", "BLOWUP OK", "UNDERGROUND OK",
                "NEVER_GRIPPED OK"):
        r.rad(rad)
    r.sektion("LIMITS")
    for namn in K.EJ_SIMULERAT:
        r.rad("NOT_SIMULATED %s" % namn)
    r.rad("RESOLUTION sample=50.000ms read=unknown join=0.000ms RUN "
          "phase=unknown")
    r.satt_dom(dom, orsak)
    return r.text()


class Inspelad_scen(object):
    """Inspelade ogondomar, i ordning. FOR ATT PROVA RIGGEN, aldrig for att mata.

    Fail-closed pa samma satt som `modellklient.Inspelad`: en inspelning som
    tar slut ar ett provfel, inte ett tyst varv.
    """

    torr = True

    def __init__(self, poster, konfig=KONFIG):
        self._poster = list(poster)
        self.konfig = konfig
        self.stalda = []
        self.rapporttexter = []

    def __call__(self, st_kalla):
        self.stalda.append(st_kalla)
        if not self._poster:
            raise Ogonfel(
                "inspelningen av ogat tog slut efter %d korningar. En "
                "inspelning som tar slut ar ett provfel, aldrig ett tyst varv."
                % len(self.stalda))
        p = self._poster.pop(0)
        dom = p.get("dom", "PASS" if p.get("gold") else "FAIL")
        orsak = p.get("orsak", "inspelad")
        texter = {}
        for namn in OGON_CELLER:
            texter[namn] = demorapport(dom, orsak,
                                       template="fas8_%s" % namn)
        self.rapporttexter.append([texter[n] for n in OGON_CELLER])
        forgrindar = dict((g, True) for g in S.KORORDNING)
        rad = {"fall": "inspelad", "konfig": self.konfig,
               "kropp": st_kalla, "torrkorning": True,
               "forgrindar": forgrindar, "forsta_fallande": None,
               "grindarnas_egna_ord": {},
               "klockkvot": 1.0, "klockan_ok": True,
               "domar": dict((n, {"text": texter[n], "dom": [dom, orsak],
                                  "harledt": {}}) for n in OGON_CELLER),
               "celler": dict(
                   (n, {"namn": n, "klass": "linje" if n == "linan"
                        else "station", "forgrindar": dict(forgrindar),
                        "eyes": texter[n]}) for n in OGON_CELLER)}
        return rad


# ---- torrkorningens inspelning ------------------------------------------
#
# Tre fall for guldarmen, och de ar precis de tre uppdraget kraver att
# rakningen ska klara: ett svar som ger GOLD direkt, ett som behover tva varv,
# och ett som slar i taket. Kompositionsarmen far fyra fall som lagas och ett
# som gar i taket, sa att "3 av 5" verkligen raknas och inte bara blir sant av
# att allt lyckas.
#
# Kropparna ar M-74:s EGNA - alltsa riktig ST som grind 1-4 verkligen domer.
# Bara ogats svar ar inspelade.

_FAIL_FORREGLING = {
    "gold": False, "dom": "FAIL",
    "orsak": "interlock: ST8A_Don/Slapp och ST8B_Don/Slapp hoga samtidigt "
             "i 3.90 s, 45 prov"}
_FAIL_KVAR = {"gold": False, "dom": "FAIL",
              "orsak": "interlock: overlappet star kvar, 3.20 s i 38 prov"}
_PASS = {"gold": True, "dom": "PASS", "orsak": "allt inom marginal"}


def _torra_kroppar(*fall):
    return [L.kroppar(f)["LINJE"] for f in fall]


TORRA_SVAR = {
    "gold_direkt": lambda: _torra_kroppar("HEL"),
    "tva_varv": lambda: _torra_kroppar("K3", "HEL"),
    "taket": lambda: _torra_kroppar("K1", "K2", "K3", "K4"),
    "seed_lagat": lambda: _torra_kroppar("HEL"),
    "seed_taket": lambda: _torra_kroppar("K1", "K2", "K3", "K4"),
}

TORRA_OGONDOMAR = {
    "gold_direkt": [_PASS],
    "tva_varv": [_FAIL_FORREGLING, _PASS],
    "taket": [_FAIL_FORREGLING, _FAIL_KVAR, _FAIL_KVAR, _FAIL_KVAR],
    # Kompositionsfallen bar ett ogonvarv EXTRA: seeden ar varv noll.
    "seed_lagat": [_FAIL_FORREGLING, _PASS],
    "seed_taket": [_FAIL_FORREGLING, _FAIL_KVAR, _FAIL_KVAR, _FAIL_KVAR,
                   _FAIL_KVAR],
}


def _torrfall(etikett):
    """Vilket inspelat fall en korning ska koras med."""
    if etikett.startswith("guld#"):
        return {"1": "gold_direkt", "2": "tva_varv"}.get(
            etikett.split("#", 1)[1], "taket")
    if etikett.startswith("K5#"):
        return "seed_taket"
    return "seed_lagat"


# ------------------------------------------------------------- uppgiften

UPPGIFT = """\
Skriv kroppen till ST-programmet for en lina med TVA stationer i serie.
Bana 1 gar genom station A, bana 2 genom station B, och en produkt som lamnar
station A kommer till station B.

Signalerna ar redan deklarerade at dig:
  a_givare   fotocell vid station A            (lases)
  a_stopp    station A: bromsklacken ut, bana 1 stannar   (skrivs)
  a_slapp    station A: begar den DELADE utmataren        (skrivs)
  b_givare   fotocell vid station B            (lases)
  b_stopp    station B: bromsklacken ut, bana 2 stannar   (skrivs)
  b_slapp    station B: begar den DELADE utmataren        (skrivs)
  kor        linjens driftvaljare              (lases)
  nodstopp   nodstoppet ar utlost              (lases)

Arbetsvariabler finns deklarerade och far anvandas fritt:
  a_laget, b_laget : INT       a_flank, b_flank : R_TRIG
  a_tid, b_tid : TON           a_utid, b_utid : TON

Sa har ska VARJE station arbeta:
  1. Nar en produkt kommer till stationens fotocell ska stationen stanna
     bandet och halla produkten.
  2. Stationen processar produkten i T#2s.
  3. Darefter matar stationen ut produkten. Utmatningen tar T#1s, och under
     den tiden ska bandet ga igen.
  4. Sedan ar stationen redo for nasta produkt.

Tre krav utover stationernas egen sekvens:
  * Utmataren ar ETT don som BADA stationerna delar. Den kan inte tjana tva
    stationer samtidigt: a_slapp och b_slapp far aldrig vara hoga i samma
    scan.
  * Nar kor ar lag ELLER nodstopp ar hog ska linan sta: ingen station far da
    begara utmataren. Bromsen ska INTE roras da - en pausad lina far inte
    slappa en klamd produkt.
  * En station ska starta pa fotocellens STIGANDE FLANK, inte pa dess niva,
    och varje utgang ska skrivas pa hogst ett stalle per scan.

Svara med enbart kroppens rader."""


SEED_INLEDNING = """\

Det HAR programmet kors redan i linan, och ogat fallde det:

%s

Ogat sag korningen i scenen. Nedan star ogats EGNA domar, ordagrant och utan
omskrivning:

%s

Ratta programmet sa att ogat inte langre har nagot att anmarka pa. Svara med
enbart kroppens rader."""


def seedad_uppgiftstext(grund, kropp, ogontext):
    return grund + SEED_INLEDNING % (kropp.rstrip("\n"), ogontext.rstrip("\n"))


def seeda(ogonsteg, kropp, grunduppgift=UPPGIFT):
    """Kor ETT kompositionsfall genom ogat och bygg modellens uppgift ur domen.

    Seeden ar varv NOLL: den kostar inget av modellens fyra varv, for det ar
    inte modellen som skrev den. Det ar M-74:s egen fixtur, och det som mats
    ar om ogats felbeskrivning racker for att modellen ska ratta RATT sak.
    """
    dom = ogonsteg.doma(st_kalla_av(kropp))
    rapporttexter = list(ogonsteg.senaste_rapporttexter)
    ut = {"kropp": kropp,
          "dom": ogonsteg.senaste_samlad,
          "guld": ogonsteg.senaste_guld.niva if ogonsteg.senaste_guld else None,
          "rapporttexter": rapporttexter,
          "ogonord": dom.utdata,
          # En seed som ogat SLAPPER igenom ar en trasig fixtur, inte ett
          # gront: da matte korningen ingenting om modellens formaga att laga.
          "foll": not dom.ok}
    ut["uppgiftstext"] = seedad_uppgiftstext(grunduppgift, kropp, dom.utdata)
    for text in rapporttexter:
        if text.rstrip("\n") not in ut["uppgiftstext"]:
            raise Ogonfel("ogats ord skrevs om pa vagen in i seedens prompt")
    return ut


# ---------------------------------------------------------------- slingan

def bygg_slinga(ogonsteg, max_varv=R.MAX_VARV, lage=R.LAGE_RENT,
                systemprompt=None, karta=None, skelett=None,
                stationsgrindar=None, index=None, strucpp=None,
                byggkatalog=None):
    """Grind 1-3 billigt forst, sedan ogat (som sjalvt kor grind 1-4).

    Att de billiga grindarna star FORE ogat ar inte en optimering: en kropp som inte
    kompilerar ska aldrig kosta en VC-omstart, en uppladdning och 105 sekunder
    scenmatning, och det ar samma ordning `stationsgrind.KORORDNING` redan har
    av samma skal.
    """
    karta = karta or KARTA
    if stationsgrindar:
        grindar = tuple(stationsgrindar)
    elif strucpp:
        grindar = BILLIGA_GRINDAR
    else:
        # Utan STruC++ gar kompileringsgrinden inte att kora, och en grind som
        # inte kunde koras ar aldrig ett godkannande (I3). Den lyfts darfor ur
        # kedjan och hamnar i `ej_korda` med sitt eget skal, i stallet for att
        # falla varje modellsvar pa riggens brist.
        grindar = (S.NAMN_STATISK, S.NAMN_DEKLARATION)
    if S.NAMN_ANROP in grindar:
        raise Riggfel(
            "grind 4 (anropsvalidering) hor inte i den billiga kedjan: "
            "`Stationssteg` bygger sin kandidat utan scenkod, sa grinden kan "
            "inte kora och VARJE modellsvar hade fallt pa riggens brist. Den "
            "kors i ogonsteget, dar scenkoden finns.")
    station = R.Stationssteg(karta, grindar=grindar, index=index,
                             strucpp_paket=strucpp, byggkatalog=byggkatalog)
    return R.Reparationsslinga(
        skelett or SKELETT, [station, ogonsteg], lage=lage,
        max_varv=max_varv,
        systemprompt=systemprompt if systemprompt is not None
        else R.SYSTEMPROMPT)


def _ogonsteget(slinga):
    for steg in slinga.grindar:
        if isinstance(steg, Ogonsteg):
            return steg
    raise Riggfel("slingan har inget ogonsteg; da matar den tillbaka "
                  "grindarnas ord och inte ogats, och det ar fas 9, inte F1")


def kor_en_slinga(forfattare, slinga, uppgiftstext, uppgift="F1",
                  extra=None):
    """En hel korning: upp till fyra varv, ogats ord tillbaka mellan dem."""
    steg = _ogonsteget(slinga)
    fore = steg.korningar
    t0 = time.time()
    rad = {"uppgift": uppgift, "modell": forfattare.namn,
           "leverantor": forfattare.leverantor,
           "lage": slinga.lage, "max_varv": slinga.max_varv,
           "torrkorning": bool(getattr(steg.kor_scenen, "torr", False)
                               or isinstance(forfattare.transport,
                                             modellklient.Inspelad))}
    rad.update(extra or {})
    try:
        protokoll = slinga.kor(forfattare, uppgiftstext, uppgift=uppgift)
    except Exception as fel:                                # noqa: BLE001
        # Ett korningsfel far aldrig se ut som en dom. Talen ar da inte hela
        # armen, och det skrivs ut.
        rad.update({"utfall": "KORNINGSFEL", "fel": repr(fel), "lost": False,
                    "gold": False, "varv_korda": 0, "varv_till_gold": None,
                    "slog_i_taket": False,
                    "ogonkorningar": steg.korningar - fore,
                    "sekunder": round(time.time() - t0, 1)})
        return rad

    guld = steg.senaste_guld
    gold = bool(protokoll.lost and guld is not None and guld.guld)
    rad.update({
        "utfall": protokoll.utfall,
        "lost": bool(protokoll.lost),
        "gold": gold,
        "guld_niva": guld.niva if guld is not None else None,
        "guld_skal": guld.skal if guld is not None else None,
        "varv_korda": len(protokoll.varv),
        "varv_till_gold": protokoll.varv_till_lost if gold else None,
        "slog_i_taket": protokoll.utfall == R.UTFALL_TAK,
        "ogonkorningar": steg.korningar - fore,
        "ogats_sista_dom": steg.senaste_samlad,
        "anrop": forfattare.anrop,
        "kostnad_usd": (round(forfattare.kostnad_usd, 4)
                        if forfattare.kostnad_usd is not None else None),
        "sekunder": round(time.time() - t0, 1),
        "ej_korda": dict(protokoll.ej_korda),
        # Domen OCH koden som domdes. M-96: nar TIDLITERAL-domarna visade sig
        # vara var egen falska rodgrind fanns modellens kod inte kvar att
        # lasa, sa fyndet fick goras om fran borjan.
        "varv": [{"nummer": v.nummer, "kropp": v.kropp,
                  "upprepar": v.upprepar,
                  "domar": [{"grind": d.grind, "ok": d.ok,
                             "koder": list(d.koder),
                             "utdata": d.utdata[:4000]}
                            for d in v.domar]}
                 for v in protokoll.varv],
    })
    return rad


# ------------------------------------------------------------- skrivaren

class Skrivare(object):
    """Inkrementell JSON: flushas efter VARJE varv, inte i slutet.

    Skalet ar matt i det har projektet samma dag: en avbruten fullarm tappade
    ~10 losta uppgifter. Ett ogonvarv kostar en VC-omstart, en uppladdning och
    over hundra sekunder scenmatning - det ar den dyraste enheten i riggen och
    darfor den som ska overleva ett avbrott.
    """

    def __init__(self, sokvag, huvud=None):
        self.sokvag = sokvag
        self.data = dict(huvud or {})
        self.data.setdefault("ogonvarv", [])
        self.data.setdefault("guld_arm", [])
        self.data.setdefault("komposition", [])
        self.data.setdefault("varv", 0)
        self.skriv()

    def varv(self, rad):
        self.data["ogonvarv"].append(_kort(rad))
        self.data["varv"] = len(self.data["ogonvarv"])
        self.skriv()

    def korning(self, arm, rad):
        self.data.setdefault(arm, []).append(rad)
        self.skriv()

    def satt(self, nyckel, varde):
        self.data[nyckel] = varde
        self.skriv()

    def skriv(self):
        if not self.sokvag:
            return
        tmp = self.sokvag + ".delvis"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, ensure_ascii=False,
                      sort_keys=True)
        os.replace(tmp, self.sokvag)


def _kort(rad):
    """Ogonvarvet utan `harledt`: serien ar megabyte, domen ar rader."""
    ut = dict((k, v) for k, v in rad.items()
              if k not in ("domar", "celler", "slinga", "oga_start"))
    ut["domar"] = dict(
        (n, {"dom": (rad.get("domar") or {}).get(n, {}).get("dom"),
             "text": (rad.get("domar") or {}).get(n, {}).get("text")})
        for n in OGON_CELLER if (rad.get("domar") or {}).get(n))
    return ut


def las_json(sokvag):
    with open(sokvag, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------- grontkriteriet

def _majoritet(n):
    """Fler an halften. For n = 3 ar det 2, alltsa uppdragets "2 av 3"."""
    return n // 2 + 1


def grontkriteriet(guld_rader, komp_rader, n):
    """Bada halvorna raknade, och ett besked om VILKEN som foll."""
    per_guld = [{"korning": i + 1, "gold": bool(r.get("gold")),
                 "varv_till_gold": r.get("varv_till_gold"),
                 "utfall": r.get("utfall"),
                 "slog_i_taket": bool(r.get("slog_i_taket"))}
                for i, r in enumerate(guld_rader)]
    med_gold = sum(1 for r in guld_rader if r.get("gold"))
    # En majoritet av korningarna, och aldrig farre an uppdragets 2 av 3.
    # Skalet ar A2:s: en enda lyckad korning kan vara jitter.
    kravda = max(GULD_AV, _majoritet(n))
    kriterium_guld = bool(guld_rader) and med_gold >= kravda

    per_fall = {}
    for r in komp_rader:
        per_fall.setdefault(r["fall"], []).append(r)
    fallrader = []
    lagade = 0
    for fall in sorted(per_fall):
        mina = per_fall[fall]
        # Tre sorters korningar, och skillnaden bar rakningen:
        #   OGILTIG   seeden gick inte att doma (klockan utanfor braketten,
        #             ogat utan ord). M-74:s regel: en sadan korning ar inte
        #             fallande, den ar ogiltig - den raknas darfor varken i
        #             taljaren eller i namnaren.
        #   SLAPPTE   ogat slapp igenom M-74:s egen K-kropp. Da ar FIXTUREN
        #             trasig, och fallet far aldrig raknas som lagat.
        #   giltig    seeden foll, modellen fick ogats ord och sitt tak.
        ogiltiga = [r for r in mina if r.get("utfall") == "OGILTIG"]
        slappte = [r for r in mina
                   if r.get("utfall") != "OGILTIG" and not r.get("seeden_foll")]
        giltiga = [r for r in mina if r not in ogiltiga and r not in slappte]
        k = sum(1 for r in giltiga if r.get("lagat"))
        # Majoritet av de GILTIGA korningarna, och minst tva av dem. En enda
        # lyckad korning kan vara jitter (A2), och ett fall vars fixtur inte
        # fallde mater ingenting om modellens formaga att laga.
        ok = (not slappte) and len(giltiga) >= 2 and k >= _majoritet(len(giltiga))
        lagade += 1 if ok else 0
        fallrader.append({"fall": fall, "lagade_korningar": k,
                          "korningar": len(mina),
                          "giltiga_korningar": len(giltiga),
                          "ogiltiga_korningar": len(ogiltiga),
                          "seeden_slappte_igenom_i": len(slappte),
                          "seeden_foll_i": len(giltiga), "lagat": ok})
    kriterium_komposition = lagade >= KOMPOSITION_AV

    torra = [r for r in list(guld_rader) + list(komp_rader)
             if r.get("torrkorning")]
    giltigt = (not torra
               and len(guld_rader) >= n
               and len(per_fall) >= KOMPOSITION_TOTALT)
    skal = []
    if torra:
        skal.append("%d av korningarna ar torrkorningar (inspelad modell "
                    "eller inspelad scen); en inspelning kan aldrig ge ett "
                    "gront F1" % len(torra))
    if len(guld_rader) < n:
        skal.append("bara %d guldkorningar av n = %d" % (len(guld_rader), n))
    if len(per_fall) < KOMPOSITION_TOTALT:
        skal.append("bara %d av %d kompositionsfall korda"
                    % (len(per_fall), KOMPOSITION_TOTALT))

    foll = []
    if not giltigt:
        foll.append("giltighet")
    if not kriterium_guld:
        foll.append("guld")
    if not kriterium_komposition:
        foll.append("komposition")
    return {
        "n": n,
        "giltigt": giltigt,
        "ogiltighetsskal": skal,
        "kriterium_guld": kriterium_guld,
        "guld_korningar_med_gold": med_gold,
        "guld_korningar": len(guld_rader),
        "guld_kravda": kravda,
        "per_guldkorning": per_guld,
        "kriterium_komposition": kriterium_komposition,
        "kompositionsfall_lagade": lagade,
        "kompositionsfall_kravda": KOMPOSITION_AV,
        "per_kompositionsfall": fallrader,
        "gront": bool(giltigt and kriterium_guld and kriterium_komposition),
        "foll": foll,
    }


# ------------------------------------------------------------------ armarna

def guldarmen(bygg_forfattaren, bygg_ogonsteg, n, max_varv=R.MAX_VARV,
              lage=R.LAGE_RENT, systemprompt=None, slingargument=None,
              skrivare=None):
    """Fri forfattning: modellen skriver linans kropp fran uppgiften."""
    ut = []
    for i in range(1, n + 1):
        etikett = "guld#%d" % i
        print("\n  === guldarmen, korning %d av %d ===" % (i, n), flush=True)
        steg = bygg_ogonsteg(etikett)
        slinga = bygg_slinga(steg, max_varv=max_varv, lage=lage,
                             systemprompt=systemprompt,
                             **(slingargument or {}))
        rad = kor_en_slinga(bygg_forfattaren(etikett), slinga, UPPGIFT,
                            uppgift="linan", extra={"upprepning": i})
        _skriv_korning(rad)
        ut.append(rad)
        if skrivare:
            skrivare.korning("guld_arm", rad)
    return ut


def kompositionsarmen(bygg_forfattaren, bygg_ogonsteg, n, fall=None,
                      max_varv=R.MAX_VARV, lage=R.LAGE_RENT,
                      systemprompt=None, slingargument=None, skrivare=None):
    """M-74:s fem kompositionsfall, lagade pa ogats egna ord."""
    ut = []
    for namn in (fall or KOMPOSITIONSFALL):
        kropp = L.kroppar(namn)["LINJE"]
        for i in range(1, n + 1):
            print("\n  === %s, korning %d av %d (%s) ==="
                  % (namn, i, n, dict((f, v) for f, _x, v, _p in L.FALL)[namn]),
                  flush=True)
            etikett = "%s#%d" % (namn, i)
            steg = bygg_ogonsteg(etikett)
            rad = {"fall": namn, "upprepning": i}
            try:
                seed = seeda(steg, kropp)
            except Ogonfel as fel:
                rad.update({"utfall": "OGILTIG", "fel": repr(fel),
                            "lagat": False, "seeden_foll": False,
                            "torrkorning": bool(getattr(steg.kor_scenen,
                                                        "torr", False))})
                print("      seeden blev OGILTIG: %r" % fel)
                ut.append(rad)
                if skrivare:
                    skrivare.korning("komposition", rad)
                continue
            rad["seeden_foll"] = seed["foll"]
            rad["seedens_dom"] = seed["dom"]
            # Seedens ogonord sparas: F2 ska kunna klassa varje misslyckat
            # reparationsvarv i "ogat sa fel sak", "ogat sa ratt sak otydligt"
            # eller "modellen kunde inte laga trots ett tydligt besked", och
            # den fragan gar inte att stalla i efterhand utan orden.
            rad["seedens_ogonord"] = seed["ogonord"][:8000]
            if not seed["foll"]:
                # M-74 fallde alla fem i LINJE. Slapper ogat igenom fixturen
                # har ar det fixturen som ar trasig, och da mater korningen
                # ingenting om modellens formaga att laga.
                rad.update({"utfall": "SEEDEN_FOLL_INTE", "lagat": False,
                            "torrkorning": bool(getattr(steg.kor_scenen,
                                                        "torr", False))})
                print("      seeden SLAPPTE IGENOM - fixturen ar trasig, "
                      "inte modellen duktig")
                ut.append(rad)
                if skrivare:
                    skrivare.korning("komposition", rad)
                continue
            slinga = bygg_slinga(steg, max_varv=max_varv, lage=lage,
                                 systemprompt=systemprompt,
                                 **(slingargument or {}))
            svar = kor_en_slinga(bygg_forfattaren(etikett), slinga,
                                 seed["uppgiftstext"], uppgift=namn,
                                 extra=rad)
            svar["lagat"] = bool(svar.get("gold"))
            # Seeden ar ett ogonvarv den ocksa: den kostar en VC-omstart, en
            # uppladdning och en matning. Ett tak som inte namner sin kostnad
            # ar ett pastaende.
            svar["ogonkorningar_med_seed"] = svar.get("ogonkorningar", 0) + 1
            _skriv_korning(svar)
            ut.append(svar)
            if skrivare:
                skrivare.korning("komposition", svar)
    return ut


def _skriv_korning(rad):
    print("      %-8s %-14s varv %s/%s  ogonvarv %s  %s"
          % (rad.get("uppgift") or rad.get("fall"), rad.get("utfall"),
             rad.get("varv_till_gold") or rad.get("varv_korda"),
             rad.get("max_varv"), rad.get("ogonkorningar"),
             "GOLD" if rad.get("gold") else (rad.get("guld_niva") or "")),
          flush=True)
    if rad.get("fel"):
        print("      FEL: %s" % rad["fel"])


# --------------------------------------------------------------- utskriften

def skriv_domen(dom):
    print("\n=== F1: grontkriteriet ===\n")
    print("  guld:         GOLD i %d av %d korningar (kravs %d)  -> %s"
          % (dom["guld_korningar_med_gold"], dom["guld_korningar"],
             dom["guld_kravda"], "JA" if dom["kriterium_guld"] else "NEJ"))
    for r in dom["per_guldkorning"]:
        print("      korning %d: %-14s varv till GOLD %s"
              % (r["korning"], r["utfall"], r["varv_till_gold"]))
    print("\n  komposition:  %d av %d fall lagade (kravs %d)  -> %s"
          % (dom["kompositionsfall_lagade"], KOMPOSITION_TOTALT,
             dom["kompositionsfall_kravda"],
             "JA" if dom["kriterium_komposition"] else "NEJ"))
    for r in dom["per_kompositionsfall"]:
        print("      %-4s lagat i %d av %d giltiga korningar (%d ogiltiga, "
              "%d dar seeden slapp igenom)  %s"
              % (r["fall"], r["lagade_korningar"], r["giltiga_korningar"],
                 r["ogiltiga_korningar"], r["seeden_slappte_igenom_i"],
                 "LAGAT" if r["lagat"] else "-"))
    if not dom["giltigt"]:
        print("\n  OGILTIG MATNING:")
        for s in dom["ogiltighetsskal"]:
            print("      %s" % s)
    print("\n  %s" % ("F1 AR GRONT" if dom["gront"]
                      else "F1 AR ROTT - foll pa: %s" % ", ".join(dom["foll"])))
    if not dom["gront"] and dom["giltigt"]:
        print("\n  Ett rott F1 ar ett giltigt svar och den billigaste sanning")
        print("  projektet kan kopa: da ar produkten banken, inte slingan.")
        print("  Skriv den slutsatsen i matningen (KO_F §F1).")


# ---------------------------------------------------------------- huvudet

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--forfattare", default="claude", choices=list(TRANSPORTER),
                   help="transport for forfattarmodellen. ALDRIG hardkodad.")
    p.add_argument("--modell", default=None,
                   help="modellnamn inom transporten. Skrivs i JSON:en: en "
                        "arm pa en annan modell ar en ANNAN matning")
    p.add_argument("--upprepa", type=int, default=MIN_N,
                   help="n per uppgift. Minst %d (A2)" % MIN_N)
    p.add_argument("--max-varv", type=int, default=R.MAX_VARV)
    p.add_argument("--lage", default=R.LAGE_RENT, choices=list(R.LAGEN))
    p.add_argument("--utan-forhandsregler", action="store_true",
                   help="ge modellen bara uppdraget, inte grindarnas regler")
    p.add_argument("--arm", default="bada",
                   choices=("bada", "guld", "komposition"))
    p.add_argument("--fall", default=None,
                   help="komma-lista over kompositionsfall, t.ex. K3,K5")
    p.add_argument("--torrkorning", action="store_true",
                   help="kor hela slingan med INSPELAD modell och INSPELAD "
                        "scen. Provar riggen, mater ingenting.")
    p.add_argument("--json", default=None)
    # M-74:s egna riggparametrar, oforandrade.
    p.add_argument("--strucpp", default=None)
    p.add_argument("--runtime-include", default=None)
    p.add_argument("--byggrot", default=None)
    p.add_argument("--bas", default="https://127.0.0.1:18443")
    p.add_argument("--anvandare", default="vcassist")
    p.add_argument("--losenord", default="vcassist")
    p.add_argument("--endpoint", default="opc.tcp://127.0.0.1:14840/")
    p.add_argument("--runtime-omstart",
                   default="docker restart vcassist-openplc-v4")
    p.add_argument("--endpoint-server",
                   default="opc.tcp://172.17.0.2:4840/openplc/opcua")
    p.add_argument("--sekunder", type=float, default=70.0)
    p.add_argument("--uppvarmning", type=float, default=25.0)
    p.add_argument("--ogonrate", type=float, default=20.0)
    p.add_argument("--varvtid", type=float, default=0.3)
    p.add_argument("--ingen-omstart-per-korning", action="store_true")
    p.add_argument("--serier", default=None)
    a = p.parse_args(argv)

    try:
        kontrollera_n(a.upprepa)
    except Riggfel as fel:
        print("FEL: %s" % fel, file=sys.stderr)
        return 2

    fall = [f.strip() for f in a.fall.split(",")] if a.fall else \
        list(KOMPOSITIONSFALL)
    okanda = [f for f in fall if f not in KOMPOSITIONSFALL]
    if okanda:
        print("FEL: okant kompositionsfall %s; fallen ar %s"
              % (", ".join(okanda), ", ".join(KOMPOSITIONSFALL)),
              file=sys.stderr)
        return 2

    systemprompt = R._GRUNDPROMPT if a.utan_forhandsregler else R.SYSTEMPROMPT
    huvud = {"modell": a.modell or a.forfattare, "transport": a.forfattare,
             "lage": a.lage, "max_varv": a.max_varv, "n": a.upprepa,
             "torrkorning": bool(a.torrkorning),
             "forhandsregler": not a.utan_forhandsregler,
             "konfig": KONFIG, "fall": fall}
    skrivare = Skrivare(a.json, huvud) if a.json else Skrivare(None, huvud)

    bryggan = None
    if a.torrkorning:
        print("=== F1 TORRKORNING ===\n")
        print("  INGEN modell och INGEN VC. Inspelade svar och inspelade")
        print("  ogondomar. Talen ar inspelningens, inte en modells, och")
        print("  grontkriteriet ar ogiltigt av konstruktion.\n")

        def bygg_forfattaren(etikett):
            return bygg_forfattare("inspelad",
                                   svar=TORRA_SVAR[_torrfall(etikett)]())

        def bygg_ogonsteg(etikett):
            return Ogonsteg(
                Inspelad_scen(TORRA_OGONDOMAR[_torrfall(etikett)]),
                on_varv=skrivare.varv)
    else:
        if not a.strucpp or not a.runtime_include:
            print("FEL: --strucpp och --runtime-include kravs for en riktig "
                  "korning. Kor --torrkorning for att prova riggen utan VC.",
                  file=sys.stderr)
            return 2
        if a.byggrot is None:
            a.byggrot = os.path.join(os.path.expanduser("~"), ".cache",
                                     "vcassist_f1")
        os.makedirs(a.byggrot, exist_ok=True)
        if a.serier:
            os.makedirs(a.serier, exist_ok=True)
        forf = bygg_forfattare(a.forfattare, modell=a.modell)
        if isinstance(forf.transport, (modellklient.ClaudeCLI,)) and \
                not forf.transport.tillganglig():
            # Fail-closed. En korning som tyst faller tillbaka pa en attrapp
            # skulle rapportera attrappens tal som en modells.
            print("INGEN MODELLKLIENT. Transporten %s hittar ingen korbar.\n"
                  "Korningen far inte falla tillbaka pa en attrapp."
                  % a.forfattare, file=sys.stderr)
            return 2

        kalla = L._startskript()
        with open(L.STARTSKRIPT, "w") as f:
            f.write(kalla)
        print("  startskript skrivet: %s (%d tecken)"
              % (L.STARTSKRIPT, len(kalla)))
        bryggan = Bryggan(starta_om_mellan=not a.ingen_omstart_per_korning)
        index = bygg_validator()

        def bygg_forfattaren():
            return bygg_forfattare(a.forfattare, modell=a.modell)

        def bygg_ogonsteg():
            return Ogonsteg(Scenkorare(a, index, bryggan),
                            on_varv=skrivare.varv)

    slingargument = {}
    if not a.torrkorning:
        slingargument = {"strucpp": a.strucpp,
                         "byggkatalog": os.path.join(a.byggrot, "slinga"),
                         "stationsgrindar": BILLIGA_GRINDAR}

    guld, komp = [], []
    try:
        if a.arm in ("bada", "guld"):
            guld = guldarmen(bygg_forfattaren, bygg_ogonsteg, a.upprepa,
                             max_varv=a.max_varv, lage=a.lage,
                             systemprompt=systemprompt,
                             slingargument=slingargument, skrivare=skrivare)
        if a.arm in ("bada", "komposition"):
            komp = kompositionsarmen(bygg_forfattaren, bygg_ogonsteg,
                                     a.upprepa, fall=fall,
                                     max_varv=a.max_varv, lage=a.lage,
                                     systemprompt=systemprompt,
                                     slingargument=slingargument,
                                     skrivare=skrivare)
    finally:
        if bryggan is not None:
            bryggan.stang()

    dom = grontkriteriet(guld, komp, a.upprepa)
    skrivare.satt("grontkriteriet", dom)
    skriv_domen(dom)
    if a.json:
        print("\n  skrivet: %s" % a.json)

    fel = [r for r in guld + komp if r.get("utfall") == "KORNINGSFEL"]
    if fel:
        print("\n  korningsfel: %d - talen ovan ar INTE hela armen"
              % len(fel))
        return 1
    return 0 if dom["gront"] else 1


if __name__ == "__main__":
    sys.exit(main())
