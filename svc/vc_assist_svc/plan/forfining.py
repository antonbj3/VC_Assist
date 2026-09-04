# -*- coding: utf-8 -*-
"""Forfining: hur en grundbegaran blir en detaljerad spec.

DET CENTRALA KRAVET, och skalet till att modulen finns:

    Allt som INTE star i begaran men behovs ska bli ett uttalat ANTAGANDE med
    motiv, eller en FRAGA till operatoren. Aldrig ett tyst val.

Ett antagande som inte ar markt ar precis den tysta nedgraderingen hela
projektet ar byggt for att undvika. Darfor ar regeln har mekanisk och inte en
ambition: varje varde som INTE kommer ur begaran gar genom en av tva metoder,
anta() eller fraga(), och det finns ingen tredje vag in i specen.

    anta()   det finns ett forsvarbart val OCH ett skal som gar att lasa
    fraga()  valet ar operatorens; vi far inte gora det at honom

Nar valjs vilket? Regeln ar: kan valet harledas ur nagot vi HAR - katalogen,
en invariant i specen, en uppgift i banken - da ar det ett antagande med den
harledningen som motiv. Kraver det operatorens smak, hans anlaggning eller
hans pengar, da ar det en fraga. Ett uppfunnet gransnittsnamn eller en
uppfunnen URI ar alltid en fraga: I9 gor det till ett hart fel.

Tva vagar in:

    ur_bankuppgift()  en uppgift ur bank/uppgifter/ - strukturerad, med facit
    ur_fritext()      operatorens korta text - allt som inte gar att lasa ur
                      texten blir ett antagande eller en fraga
"""
from __future__ import annotations

import re

from . import lasning
from .fel import Specfel
from .harkomst import Harkomst, normalisera as _normalisera
from .kallor import bankschema
from .processer import Ordningskrav, Process, Processordning
from .spec import (Antagande, Del, DetaljeradSpec, Fraga, Grundbegaran,
                   Koppling, MIN_KORNINGAR, Omrade, Signal, Takt)
from .verifiering import Krav, Uppskjutet, Verifieringskrav
from .villkorssprak import Prosakrav, Relation, Typvillkor

# Vem som provar ett krav vi inte kan typa. Ett prosakrav utan konsument ar
# samma dodkott som det gamla Villkor.text var (M-63), sa konsumenten ar ett
# formkrav i villkorssprak.Prosakrav och inte en artighet.
KONSUMENT_FORREGLING = ("grind 3 (deklarationsmatchning) och ST-lagrets "
                        "sekvensgranskare, docs/spec/50_grindar.md")

# Sektionerna en scenbyggplan kan bevisa med en korning i VC utan att
# styrkoden finns: att bygget inte kolliderar och att inget ohederligt sker.
# TIMING, THROUGHPUT och MOTION kraver att en styrning kor sekvensen, vilket
# ar fas 7 och 8 i docs/spec/70_faser.md - inte scenbygget i fas 5.
SEKTIONER_NU = ("SAFETY", "HONESTY")
SKAL_UPPSKJUTET = ("kravet mater sekvens, tid eller genomflode och forutsatter "
                   "att styrningen kor cellen; scenbygget bevisar det inte, "
                   "fas 7 och 8 i docs/spec/70_faser.md gor det")

# Minimikravet nar begaran inte sager vad som ska bevisas. Raderna ar de ogat
# skriver aven utan styrkod, och de tacker de tva klasser ett scenbygge sjalvt
# kan orsaka: F9 geometri och F12 ohederlig (docs/spec/82_felklasser.md).
MINIMIKRAV = (("SAFETY", "COLLISION none"),
              ("HONESTY", "TELEPORT_TRANSFER OK"),
              ("HONESTY", "BLOWUP OK"),
              ("HONESTY", "UNDERGROUND OK"))

MOTIV_MINIMIKRAV = (
    "begaran sager inte vad som ska bevisas, och en plan utan verifiering ar "
    "en kandidat och aldrig en leverans (docs/spec/50_grindar.md). Kravet ar "
    "satt till de rader ogat skriver aven utan styrkod: ingen kollision och "
    "inga ohederliga rorelser")

MOTIV_KORNINGAR = (
    "begaran sager inte hur manga korningar som ska ligga bakom talen. I5 i "
    "docs/spec/90_invarianter.md kraver minst tre oberoende korningar med "
    "uppvarmning som inte raknas, sa antalet ar satt till minimum")

MOTIV_UPPVARMNING = (
    "begaran namner ingen uppvarmning och uppgiften mater inget genomflode. "
    "Uppvarmningen ar darfor satt till noll sekunder; ett kapacitetsmal skulle "
    "krava att den mats och sattes hogre")

# --------------------------------------------------------------- fritext

# Normaliseringen bor i harkomst.py: samma funktion maste avgora bade om ett
# ord finns i katalogen och om ett belagg finns i begaran. Tva normaliseringar
# hade gjort en harkomst falsk pa ett a-ring.


_ORD = re.compile(r"[a-z0-9]+")

# Svenska bestamda och pluralandelser. "bandet" och "roboten" ska hitta samma
# katalogpost som "band" och "robot"; utan listan hittar de ingen alls. Listan
# ar sluten och kort med flit: prefixmatchning hade last "pallmagasin" som
# "pall" och gett en lastbarare som ingen bett om.
ANDELSER = ("", "en", "et", "n", "t", "ar", "arna", "erna", "or", "orna", "er")


def _tokens(text):
    return _ORD.findall(_normalisera(text))


def _namner(tokens, ord_):
    """Star ordet i texten, som eget ord eller som EFTERLED i ett sammansatt?

    Suffixet, inte prefixet. MATT i M-63 pa operatorens egen exempeltext:
    "ett inmatningsband" gav ingen komponent alls, eftersom 'band' inte var
    ett eget token - och planen blev BYGGBAR med en tredjedel av det han bad
    om. Ett sammansatt ord bestams av sitt EFTERLED: ett inmatningsband ar ett
    band.

    Prefixmatchning vore fel at andra hallet, och det star redan i ORDBOKs
    kommentar: den hade last "pallmagasin" som "pall" och gett en lastbarare
    ingen bett om.
    """
    for andelse in ANDELSER:
        form = ord_ + andelse
        if form in tokens:
            return True
        if any(t != form and t.endswith(form) for t in tokens):
            return True
    return False


# ord i begaran -> (kategori i katalogindexet, fragment i uri eller namn)
# Fragmentet None betyder att ordet bara pekar ut kategorin. Listan ar en
# TUPEL och inte en ordbok darfor att ordningen ska vara densamma varje gang:
# samma begaran ska ge samma spec.
ORDBOK = (
    ("band", "transport", "band"),
    ("bandtransportor", "transport", "band"),
    ("rullbana", "transport", "rullbana"),
    ("kedjetransportor", "transport", "kedje"),
    ("matare", "transport", "matare"),
    ("transportor", "transport", None),
    ("stoppgrind", "don", "stoppgrind"),
    ("utskjutare", "don", "utskjutare"),
    ("lyftbord", "don", "lyftbord"),
    ("vandare", "don", "vandare"),
    ("robot", "robot", None),
    ("vakuumgripdon", "gripdon", "vakuum"),
    ("skruvdragare", "gripdon", "skruvdragare"),
    ("svetspistol", "gripdon", "svetspistol"),
    ("gripdon", "gripdon", None),
    ("gripare", "gripdon", None),
    ("fotocell", "givare", "fotocell"),
    ("induktiv", "givare", "induktiv"),
    ("kamera", "givare", "kamera"),
    ("vagcell", "givare", "vagcell"),
    ("givare", "givare", None),
    ("fixtur", "station", "fixtur"),
    ("buffert", "station", "buffert"),
    ("press", "station", "press"),
    ("skruvstation", "station", "skruvstation"),
    ("kassationslada", "station", "kassation"),
    ("pallmagasin", "station", "pallmagasin"),
    ("gitterbox", "lastbarare", "gitterbox"),
    ("klt", "lastbarare", "klt"),
    ("pall", "lastbarare", "pall"),
    ("ljusrida", "sakerhet", "ljusrid"),
    ("nodstopp", "sakerhet", "nodstopp"),
)

# Matt i millimeter ur texten, till exempel "bandbredd 600 mm".
_MM = re.compile(r"(\d+(?:[.,]\d+)?)\s*mm")
# Takt: "45 burkar per minut", "100 enheter i timmen", "120/h".
_TAKT = re.compile(r"(\d+(?:[.,]\d+)?)\s*[a-zA-Z]*\s*(?:per|/|i)\s*"
                   r"(minut|min|timme|timmen|h)\b")
# Cykeltid: "1,33 s per burk", "32,0 sekunder per enhet".
_CYKEL = re.compile(r"(\d+(?:[.,]\d+)?)\s*s(?:ekunder)?\s*(?:per|/)\s*"
                    r"(?:cykel|enhet|detalj|burk|styck|del)")


def _tal(text):
    return float(text.replace(",", "."))


def matt_mm(text):
    return [_tal(m) for m in _MM.findall(text)]


def takt_per_h(text):
    m = _TAKT.search(text)
    if not m:
        return None
    varde = _tal(m.group(1))
    return varde * 60.0 if m.group(2) in ("minut", "min") else varde


def cykeltid_s(text):
    m = _CYKEL.search(text)
    return _tal(m.group(1)) if m else None


def signalnamn(text):
    """Signalnamn som foljer bankens konvention. Namnen kommer UR begaran."""
    ut = []
    for ord_ in re.findall(r"[A-Z][A-Z0-9_]+", text or ""):
        if (bankschema.SIGNALMONSTER.match(ord_)
                or ord_ in bankschema.ANLAGGNINGSSIGNALER):
            if ord_ not in ut:
                ut.append(ord_)
    return ut


# --------------------------------------------------------------- forfinaren

class Forfinare(object):
    """Bygger en detaljerad spec, och bokfor varje val den gor pa vagen."""

    def __init__(self, katalogindex=None, urikarta=None, svar=None,
                 fragerunda=0):
        self.katalogindex = dict(katalogindex or {})
        self.urikarta = dict(urikarta or {})
        # Operatorens svar pa tidigare fragor, {fraga_id: text}. En besvarad
        # fraga blockerar inte, och svarets ORD blir en del av begaran - det
        # ar operatorens text lika mycket som den forsta meningen, och
        # harkomstgrinden ska kunna hitta dem dar.
        self.svar = dict(svar or {})
        self.fragerunda = int(fragerunda)
        self.antaganden = []
        self.fragor = []
        # Den femte artefakten i 22_planeringslagret.md: celldatabladet, per
        # ROLL. Bara falt katalogen faktiskt bar hamnar har. Ett falt som
        # saknas skrivs inte som noll - det skrivs inte alls, och lases da som
        # OKANT (K0: null ar inte noll).
        self.datablad = {}

    # -- de tva enda vagarna in ------------------------------------------

    def anta(self, vad, varde, motiv, kalla="standard"):
        self.antaganden.append(Antagande(vad, varde, motiv, kalla))
        return varde

    def fraga(self, id, vad, varfor, blockerar=True):
        """Fragan, och den star ALLTID som obesvarad nar den stalls igen.

        Regeln ar viktigare an den later: en fraga som stalls om ar en fraga
        som inte blev besvarad. Loste operatorens svar den, sa stalls den inte
        alls - svaret lades till i begaran, och samma monster som laser den
        forsta meningen plockade upp det. Kommer fragan tillbaka betyder det
        att svaret inte gick att lasa, och att da marka den som besvarad hade
        gjort ett obrukbart svar till ett tyst ja.
        """
        if id in self.svar:
            varfor = ("%s. Du svarade %r pa den har fragan, och det svaret "
                      "gick inte att lasa ut nagot ur - fragan star darfor "
                      "kvar" % (varfor, self.svar[id]))
        self.fragor.append(Fraga(id, vad, varfor, blockerar))
        return None

    def _blad(self, roll, post):
        """For in de storheter katalogposten faktiskt bar i databladet."""
        for falt in ("rackvidd_mm", "nyttolast_kg", "massa_kg", "l_mm",
                     "b_mm", "h_mm"):
            if post.get(falt) is None:
                continue
            namn = {"l_mm": "langd_mm", "b_mm": "bredd_mm",
                    "h_mm": "hojd_mm"}.get(falt, falt)
            self.datablad.setdefault(roll, {})[namn] = post[falt]

    def _robotroll(self, delar):
        """Den enda rollen med kategorin robot, eller None om det inte ar en."""
        robotar = [d.roll for d in delar if d.kategori == "robot"]
        return robotar[0] if len(robotar) == 1 else None

    # -- katalogen --------------------------------------------------------

    def kandidater(self, kategori, fragment, matt):
        """Posterna i katalogen ett ord kan syfta pa, i katalogens ordning."""
        ut = []
        for uri in sorted(self.katalogindex):
            post = self.katalogindex[uri]
            if post.get("kategori") != kategori:
                continue
            if fragment and fragment not in _normalisera(
                    uri + " " + str(post.get("namn", ""))):
                continue
            ut.append(post)
        if len(ut) > 1 and matt:
            # Matt ur begaran far SMALNA av traffen, aldrig utoka den. Star
            # 600 mm i texten och exakt en post ar 600 mm bred ar valet
            # harlett ur begaran och inte en gissning.
            smalare = [p for p in ut if p.get("bredd_mm") in matt]
            if len(smalare) == 1:
                return smalare
        return ut

    def los_uri(self, uri):
        """bank://-vokabularen -> den URI VC faktiskt kan ladda.

        Katalogindexet sager sjalvt att bank:// ar bankens vokabular och binds
        till eCatalog i fas 5. Utan en karta far planen INTE hitta pa en
        VC-URI: I9 gor en uppfunnen URI till ett hart fel, inte en varning.
        Den olosta URI:n lamnas orord och blir en fraga i fraga_om_urier();
        EN fraga per URI, aven nar flera roller delar den.
        """
        return self.urikarta.get(uri, uri)

    def fraga_om_urier(self, uri_roller):
        """En fraga per olost URI, med alla roller som vantar pa svaret."""
        for uri in sorted(uri_roller):
            if uri in self.urikarta or not uri.startswith("bank://"):
                continue
            roller = ", ".join(sorted(uri_roller[uri]))
            self.fraga(
                "uri:%s" % uri,
                "vilken komponent i VC:s eCatalog motsvarar %s (rollen %s)?"
                % (uri, roller),
                "bank:// ar bankens egen vokabular och pekar inte pa nagon fil "
                "VC kan ladda. En uppfunnen URI ar ett hart fel enligt I9, sa "
                "planen far inte valja en at operatoren")

    # -- vag 1: en uppgift ur banken --------------------------------------

    def ur_bankuppgift(self, data):
        """En bankuppgift -> detaljerad spec.

        Uppgiften ar redan detaljerad; forfiningen handlar darfor mest om att
        BEHALLA de antaganden banken redan markt (de foljer med som kalla
        "bank") och att marka det som banken inte kunde veta: URI:er som inte
        gar att ladda, och krav som den har planen inte bevisar.
        """
        tid = data["task_id"]
        begaran = Grundbegaran(tid, data["goal"], "bank:%s" % tid)

        for a in data.get("antaganden") or []:
            self.antaganden.append(
                Antagande(a["vad"], a["varde"], a["motiv"], "bank"))

        delar = []
        anvand_karta = False
        uri_roller = {}
        for komponent in data["scene"]["components"]:
            uri_roller.setdefault(komponent["uri"], set()).add(komponent["role"])
        self.fraga_om_urier(uri_roller)
        for komponent in data["scene"]["components"]:
            roll = komponent["role"]
            uri = self.los_uri(komponent["uri"])
            anvand_karta = anvand_karta or uri != komponent["uri"]
            post = self.katalogindex.get(komponent["uri"], {})
            matt = None
            if all(post.get(n) for n in ("l_mm", "b_mm", "h_mm")):
                matt = [post["l_mm"], post["b_mm"], post["h_mm"]]
            self._blad(roll, post)
            delar.append(Del(roll, uri, komponent.get("count", 1),
                             post.get("kategori"), matt, post.get("massa_kg")))
        if anvand_karta:
            self.anta(
                "komponent-URI",
                "%d URI:er ur urikartan" % len(self.urikarta),
                "uppgiften pekar pa bankens bank://-vokabular, som enligt "
                "bank/katalog_index.json binds till eCatalog forst i fas 5. "
                "Kartan operatoren gav oversatter dem; utan karta blir varje "
                "URI en fraga i stallet", "katalog")

        kopplingar = [Koppling(k["from_role"], k["to_role"],
                               Harkomst("bank", "%s#scene.connections[%d]"
                                        % (tid, n)))
                      for n, k in enumerate(data["scene"]["connections"])]

        signaler = [Signal(s["name"], s["dir"], s["type"], s.get("comment", ""))
                    for s in data["control"]["signals"]]

        takt = self._takt_ur_bank(data)
        villkor, prosakrav = self._villkor_ur_bank(data, delar)
        verifiering = self._verifiering_ur_bank(data)

        return DetaljeradSpec(tid, begaran, delar, kopplingar, signaler, takt,
                              villkor, self.antaganden, self.fragor,
                              verifiering, prosakrav=prosakrav)

    def _takt_ur_bank(self, data):
        timing = data["control"].get("timing") or {}
        expect = data["expect"]
        return Takt(timing.get("cycle_s"), timing.get("tolerance_s"),
                    expect.get("throughput_per_h"),
                    max(expect.get("runs") or MIN_KORNINGAR, MIN_KORNINGAR),
                    expect.get("warmup_s") or 0.0)

    def _villkor_ur_bank(self, data, delar):
        """(typade villkor, prosakrav). Uppgiftens krav, var och en typad.

        Fore M-63 blev alla fyra sorterna prosa i ett Villkor.text som ingen
        rad kod laste. Nu blir de tal som gar att jamfora - och forreglingarna,
        som spraket i K6 INTE kan uttrycka (de ar villkorade forbud, inte
        jamforelser), blir prosakrav med en utskriven konsument i stallet for
        att tyst forsvinna.
        """
        tid = data["task_id"]
        villkor = []
        prosa = []

        def bank(falt):
            return Harkomst("bank", "%s#%s" % (tid, falt))

        for n, text in enumerate(data["control"].get("interlocks") or [], 1):
            prosa.append(Prosakrav(
                "forregling_%d" % n, "forregling", text,
                KONSUMENT_FORREGLING, bank("control.interlocks[%d]" % (n - 1))))
        expect = data["expect"]
        if expect.get("max_collisions") is not None:
            villkor.append(Typvillkor(
                "kollisioner", "geometri", "scen.kollisioner", "le",
                float(expect["max_collisions"]), bank("expect.max_collisions"),
                "hogst %d kollisioner i cellen" % expect["max_collisions"]))
        if expect.get("min_clearance_mm") is not None:
            villkor.append(Typvillkor(
                "frigang", "geometri", "scen.min_avstand_mm", "ge",
                float(expect["min_clearance_mm"]), bank("expect.min_clearance_mm"),
                "minsta fria avstand %.1f mm" % expect["min_clearance_mm"]))
        if expect.get("throughput_per_h"):
            villkor.append(Typvillkor(
                "kapacitet", "kapacitet", "takt.genomflode_per_h", "ge",
                float(expect["throughput_per_h"]), bank("expect.throughput_per_h"),
                "minst %.1f enheter i timmen vid stationar drift"
                % expect["throughput_per_h"]))
        radie = (data.get("fysik") or {}).get("arbetsradie_mm")
        if radie is not None:
            roll = self._robotroll(delar)
            if roll is None:
                self.fraga(
                    "arbetsradie",
                    "vilken robot ska na %g mm? uppgiften anger en arbetsradie "
                    "men scenen bar %d robotar" % (radie,
                        len([d for d in delar if d.kategori == "robot"])),
                    "arbetsradien ar ett krav pa EN robots rackvidd. Med flera "
                    "robotar gar kravet inte att binda utan att valja at "
                    "operatoren, och den rackvidd som inte racker upptacks da "
                    "forst i scenen", blockerar=False)
            else:
                villkor.append(Typvillkor(
                    "rackvidd", "geometri", "del.%s.rackvidd_mm" % roll, "ge",
                    float(radie), bank("fysik.arbetsradie_mm"),
                    "roboten maste na %g mm" % radie))
        return villkor, prosa

    def _verifiering_ur_bank(self, data):
        """Uppgiftens facit, delat i det planen bevisar och det den skjuter upp.

        Ingenting far tappas bort: varje rad i uppgiftens facit hamnar i EN av
        de tva listorna. Ett bortglomt krav ar osynligt, ett uppskjutet ar
        markt med skal.
        """
        expect = data["expect"]
        rader, uppskjutna, forbjudna = [], [], []
        for krav in expect.get("lines") or []:
            if krav["section"] in SEKTIONER_NU:
                rader.append(Krav(krav["section"], krav["template"]))
            else:
                uppskjutna.append(Uppskjutet(krav["section"], krav["template"],
                                             SKAL_UPPSKJUTET))
        for krav in expect.get("forbidden_lines") or []:
            if krav["section"] in SEKTIONER_NU:
                forbjudna.append(Krav(krav["section"], krav["template"]))
            else:
                uppskjutna.append(Uppskjutet(krav["section"], krav["template"],
                                             SKAL_UPPSKJUTET))
        if not rader:
            self.fraga(
                "verifiering",
                "vad ska scenbygget av %s bevisa? uppgiften falls av grind %s "
                "och bar ingen rad i %s"
                % (data["task_id"], expect.get("gate"),
                   " eller ".join(SEKTIONER_NU)),
                "uppgifter som falls fore ogat (grind 1-4 i "
                "docs/spec/50_grindar.md) bar ingen ogondom att stalla planen "
                "mot. En plan utan verifiering ar en kandidat och aldrig en "
                "leverans, och vi far inte hitta pa ett facit at operatoren")
        return Verifieringskrav(expect.get("verdict") or "PASS", rader,
                                forbjudna, uppskjutna)

    # -- vag 2: operatorens korta text ------------------------------------

    def ur_fritext(self, begaran):
        """Fri text -> detaljerad spec, med varje lucka markt.

        Textens innehall lases; textens TYSTNAD blir antaganden och fragor.
        """
        if not isinstance(begaran, Grundbegaran):
            raise Specfel("forfiningen", ["ur_fritext kraver en Grundbegaran"])
        begaran = self._med_svaren(begaran)
        text = begaran.text
        delar = self._delar_ur_fritext(text)
        kopplingar = self._kopplingar_ur_fritext(delar, text)
        signaler = self._signaler_ur_fritext(text)
        takt = self._takt_ur_fritext(text)
        omrade, villkor = self._omrade_ur_fritext(text)
        villkor += self._rackvidd_ur_fritext(text, delar)
        relationer = self._relationer_ur_fritext(text, delar)
        processordning = self._processer_ur_fritext(text)
        verifiering = self._verifiering_ur_fritext()
        return DetaljeradSpec(begaran.id, begaran, delar, kopplingar, signaler,
                              takt, villkor, self.antaganden, self.fragor,
                              verifiering, omrade, relationer, processordning,
                              fragerunda=self.fragerunda)

    def _med_svaren(self, begaran):
        """Begaran med operatorens svar tillagda, ordagrant.

        Svaren ar hans ord och hor darfor till begaran. Det ar ocksa det enda
        som gor dem lasbara: mattet, kopplingen eller processordningen i ett
        svar plockas upp av samma monster som laser den forsta meningen, och
        harkomsten pekar pa text som faktiskt star dar.
        """
        if not self.svar:
            return begaran
        rader = ["%s: %s" % (id_, self.svar[id_]) for id_ in sorted(self.svar)]
        return Grundbegaran(begaran.id,
                            begaran.text + "\nSvar:\n" + "\n".join(rader),
                            begaran.kalla)

    # -- de fyra formerna som gor texten till KRAV ------------------------

    def _omrade_ur_fritext(self, text):
        """(Omrade eller None, [Typvillkor]) for cellens matt och gangstrak.

        Varje tal blir BADE ett villkor och, nar det ar ett tak eller ett
        konstaterande, ett matt pa den yta layouten far anvanda. Skillnaden
        mellan 'hogst 2x2 m' och 'minst 3 m bred' bevaras: den forsta bygger
        cellen, den andra kan gora den omojlig.
        """
        villkor = []
        matt = lasning.cellmatt(text)
        tak = {}
        belagg_for_tak = {}
        for n, (falt, operator, mm, belagg) in enumerate(matt, 1):
            villkor.append(Typvillkor(
                "cell_%s_%d" % (falt.split("_")[0], n), "geometri",
                "cell.%s" % falt, operator, mm,
                Harkomst("begaran", belagg),
                "cellens %s %s %g mm" % (falt, operator, mm)))
            if operator in ("le", "eq") and falt not in tak:
                tak[falt] = mm
                belagg_for_tak[falt] = belagg
        gang = lasning.gangstrak(text)
        if gang is not None:
            villkor.append(Typvillkor(
                "gangstrak", "geometri", "cell.gang_min_mm", "ge", gang.varde,
                Harkomst("begaran", gang.belagg),
                "minsta gangstrak %g mm" % gang.varde))
        if not tak:
            if matt or gang is not None:
                self.fraga(
                    "cellyta",
                    "hur stor yta far cellen ta? ange bredd x djup",
                    "begaran satter en undre grans eller ett gangstrak men "
                    "ingen yta. Utan en yta gar varken passformen eller "
                    "ytkravet att prova, och en yta vi valde sjalva skulle "
                    "bestamma hela layouten", blockerar=False)
            return None, villkor
        if gang is None:
            self.fraga(
                "gangstrak",
                "vilket minsta gangstrak ska galla mellan tva komponenter?",
                "K11 i docs/spec/22_planeringslagret.md ger gangstraket INGET "
                "forval: ett gangstrak vi valde sjalva skulle bestamma bade "
                "cellens yta och vad som senare raknas som en for trang "
                "passage", blockerar=False)
        belagg = belagg_for_tak.get("bredd_mm") or list(belagg_for_tak.values())[0]
        omrade = Omrade(tak.get("bredd_mm"), tak.get("djup_mm"),
                        tak.get("hojd_mm"),
                        gang.varde if gang is not None else None,
                        Harkomst("begaran", belagg))
        return omrade, villkor

    def _rackvidd_ur_fritext(self, text, delar):
        """Rackvidder ur texten, bundna till robotrollen."""
        utlasta = lasning.rackvidd(text)
        if not utlasta:
            return []
        roll = self._robotroll(delar)
        if roll is None:
            self.fraga(
                "rackvidd",
                "vilken komponent galler rackvidden %s?"
                % ", ".join("%g mm" % u.varde for u in utlasta),
                "begaran namner en rackvidd men scenen bar ingen entydig "
                "robot att binda den till. Att binda den at operatoren vore "
                "ett tyst val som avgor om cellen alls gar att lagga ut",
                blockerar=False)
            return []
        ut = []
        for n, u in enumerate(utlasta, 1):
            if u.vad == "krav":
                ut.append(Typvillkor(
                    "rackviddskrav_%d" % n, "geometri",
                    "del.%s.rackvidd_mm" % roll, "ge", u.varde,
                    Harkomst("begaran", u.belagg),
                    "%s maste na %g mm" % (roll, u.varde)))
            else:
                # Operatoren uppger robotens rackvidd. Det ar ett pastaende om
                # komponenten, och det skrivs bade som ett villkor (sa att en
                # motsagelse mot ett krav gar att hitta) och in i databladet
                # (sa att andra kontroller kan lasa talet).
                self.datablad.setdefault(roll, {})["rackvidd_mm"] = u.varde
                ut.append(Typvillkor(
                    "rackvidd_%d" % n, "geometri",
                    "del.%s.rackvidd_mm" % roll, "eq", u.varde,
                    Harkomst("begaran", u.belagg),
                    "%s har rackvidden %g mm" % (roll, u.varde)))
        return ut

    def _relationer_ur_fritext(self, text, delar):
        """'X ska na Y' blir en typad relation, aldrig en gissad koppling."""
        roller = [d.roll for d in delar]
        ut = []
        for fran, till, belagg in lasning.nakrav(text, roller):
            ut.append(Relation("nar", fran, till,
                               Harkomst("begaran", belagg)))
        return ut

    def _processer_ur_fritext(self, text):
        """Processerna och deras ordning, var och en med sin mening som belagg.

        En cykel avvisas INTE har. Specen ska kunna bara det operatoren
        faktiskt bad om, ocksa nar det ar omojligt - annars gar det inte att
        visa honom vad som krockade. Domen faller i bestallning.py.
        """
        funna, ordningar = lasning.processer(text)
        processer = [Process(pid, vad, None, Harkomst("begaran", belagg))
                     for pid, vad, belagg in funna]
        krav = [Ordningskrav(fore, efter, Harkomst("begaran", belagg))
                for fore, efter, belagg in ordningar]
        if len(processer) > 1 and not krav:
            self.fraga(
                "processordning",
                "i vilken ordning ska %s utforas?"
                % ", ".join(p.id for p in processer),
                "begaran namner flera processer men ingen ordning mellan dem. "
                "Ordningen orden rakade sta i texten ar inget belagg for vad "
                "som ska ske forst, och en gissad ordning styr hela "
                "styrkoden", blockerar=False)
        return Processordning(processer, krav)

    def _delar_ur_fritext(self, text):
        tokens = set(_tokens(text))
        matt = matt_mm(text)
        delar = []
        sedda = set()
        for ord_, kategori, fragment in ORDBOK:
            if not _namner(tokens, ord_) or (kategori, fragment) in sedda:
                continue
            sedda.add((kategori, fragment))
            traffar = self.kandidater(kategori, fragment, matt)
            if len(traffar) == 1:
                post = traffar[0]
                self.fraga_om_urier({post["uri"]: {ord_}})
                uri = self.los_uri(post["uri"])
                self.anta(
                    "komponent for %r" % ord_, post["uri"],
                    "ordet %r i begaran pekar pa kategorin %s i "
                    "katalogindexet, och exakt en post dar matchar: %s. Valet "
                    "ar darfor harlett ur begaran och katalogen, inte gjort"
                    % (ord_, kategori, post["namn"]), "katalog")
                dim = None
                if all(post.get(n) for n in ("l_mm", "b_mm", "h_mm")):
                    dim = [post["l_mm"], post["b_mm"], post["h_mm"]]
                self._blad(ord_, post)
                delar.append(Del(ord_, uri, 1, kategori, dim,
                                 post.get("massa_kg")))
            elif traffar:
                self.fraga(
                    "val:%s" % ord_,
                    "vilken %s menas med %r? katalogen har %d: %s"
                    % (kategori, ord_, len(traffar),
                       ", ".join(p["uri"] for p in traffar)),
                    "flera poster i katalogen matchar ordet, och att valja en "
                    "av dem at operatoren vore ett tyst val som styr bade "
                    "geometri och kapacitet")
            else:
                self.fraga(
                    "saknas:%s" % ord_,
                    "begaran namner %r men katalogen har ingen post i "
                    "kategorin %s som matchar" % (ord_, kategori),
                    "modellen far bara valja ur indexet (I9), sa en komponent "
                    "som inte finns i katalogen maste operatoren peka ut")
        self._fraga_om_okanda_ord(text)
        if not delar and not self.fragor:
            self.fraga(
                "delar",
                "vilka komponenter ska scenen bestå av?",
                "begaran namner inget som gar att kanna igen i katalogen, och "
                "en scen utan delar gar inte att bygga")
        return delar

    def _fraga_om_okanda_ord(self, text):
        """Ord i komponentupprakningen som ingen rad i ORDBOK kanner igen.

        Det har ar grinden mot det tysta bortfallet. Utan den blev
        bestallningen "med ett inmatningsband, en robot och en utlastningslada"
        en plan med EN komponent, och beskedet blev BYGGBAR - en tredjedel av
        det operatoren bad om, levererat som ett ja (MATT i M-63).

        Fragan blockerar. Att bygga tva tredjedelar av en cell ar inte att
        bygga den halvt; det ar att bygga en annan cell.
        """
        kanda = set(o for o, _k, _f in ORDBOK)
        for bit, ord_ in lasning.komponentupprakning(text):
            if any(_namner(set(ord_), k) for k in kanda):
                continue
            id_ = "okant_ord:%s" % "_".join(ord_)
            if id_ in self.svar:
                # Operatoren har sagt vad ordet ar. Svaret lades till i
                # begaran av _med_svaren, sa komponenten plockas upp av samma
                # ordlista som allt annat - och om svaret INTE namner nagot
                # kant star fragan kvar, obesvarad i sak.
                if any(_namner(set(_tokens(self.svar[id_])), k)
                       for k in kanda):
                    self.fragor.append(Fraga(
                        id_, "vilken komponent i katalogen ar %r?" % bit,
                        "operatoren har svarat %r, och det ordet finns i "
                        "ordlistan" % self.svar[id_], False, self.svar[id_]))
                    continue
            self.fraga(
                id_,
                "vilken komponent i katalogen ar %r?" % bit,
                "begaran raknar upp %r bland komponenterna, och inget ord i "
                "den slutna ordlistan matchar det. Att hoppa over det vore "
                "ett tyst bortfall: planen skulle byggas utan en komponent "
                "operatoren bad om, och beskedet skulle anda sta som "
                "byggbart" % bit)

    def _kopplingar_ur_fritext(self, delar, text):
        """Kopplingar som STAR i texten. Resten blir en fraga.

        Topologin gissas aldrig. En kedja i den ordning orden rakade sta i
        texten hade sett rimlig ut och varit ett pahitt. Star det daremot
        "bandet matar roboten" ar det operatorens ord, och da ar kopplingen
        last och inte gissad - belagget bevisar skillnaden.
        """
        if len(delar) < 2:
            return []
        roller = [d.roll for d in delar]
        ut = [Koppling(fran, till, Harkomst("begaran", belagg))
              for fran, till, belagg in lasning.kopplingar(text, roller)]
        kopplade = set()
        for k in ut:
            kopplade.add(k.fran_roll)
            kopplade.add(k.till_roll)
        utan = [r for r in roller if r not in kopplade]
        if utan:
            self.fraga(
                "kopplingar",
                "hur ska %s kopplas ihop med resten? ange par av roller"
                % ", ".join(utan),
                "kopplingen ar relationen sjalv (I8), och en gissad topologi "
                "styr hela geometrin. Ordningen orden rakade sta i texten ar "
                "inget belagg for vad som ska sitta ihop")
        return ut

    def _signaler_ur_fritext(self, text):
        namn = signalnamn(text)
        if not namn:
            return []
        self.fraga(
            "signalriktning",
            "vilken riktning och typ har signalerna %s?" % ", ".join(namn),
            "begaran namner signalerna men inte om de ar in- eller utgangar. "
            "En gissad riktning kan gora en ingang till en utgang, och grind 3 "
            "matchar deklarationer mot signalkartan",
            blockerar=False)
        return []

    def _takt_ur_fritext(self, text):
        per_h = takt_per_h(text)
        cykel = cykeltid_s(text)
        if per_h is None and cykel is None:
            self.fraga(
                "takt",
                "vilken takt ska cellen halla? ange cykeltid eller kapacitet",
                "utan takt gar det inte att saga om cellen racker till, och "
                "ett tal vi hittade pa skulle bli det mal bygget senare mats "
                "mot", blockerar=False)
            return None
        if cykel is not None:
            # Ett tidskrav utan tolerans gar inte att prova (samma regel som
            # bankens M10). Tiden bars darfor inte in i takten forran
            # operatoren svarat - att valja en tolerans sjalva hade bestamt
            # vad som raknas som godkant.
            self.fraga(
                "tolerans",
                "vilken tolerans galler for cykeltiden %.2f s?" % cykel,
                "ett tidskrav utan tolerans gar inte att prova, och en "
                "tolerans vi valde sjalva hade bestamt vad som raknas som "
                "godkant", blockerar=False)
        if per_h is None:
            return None
        korningar = self.anta("antal korningar", MIN_KORNINGAR,
                              MOTIV_KORNINGAR)
        uppvarmning = self.anta("uppvarmning", 0.0, MOTIV_UPPVARMNING)
        return Takt(None, None, per_h, korningar, uppvarmning)

    def _verifiering_ur_fritext(self):
        self.anta("verifieringskrav",
                  ", ".join("%s %s" % (s, m) for s, m in MINIMIKRAV),
                  MOTIV_MINIMIKRAV)
        return Verifieringskrav("PASS", [Krav(s, m) for s, m in MINIMIKRAV])


# ------------------------------------------------------------------- utat

def ur_bankuppgift(data, katalogindex=None, urikarta=None):
    return Forfinare(katalogindex, urikarta).ur_bankuppgift(data)


def ur_fritext(begaran, katalogindex=None, urikarta=None, svar=None,
               fragerunda=0):
    return Forfinare(katalogindex, urikarta, svar, fragerunda).ur_fritext(begaran)
