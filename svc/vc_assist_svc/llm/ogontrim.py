# -*- coding: utf-8 -*-
"""Ogats rapport till modellen, och den enda trimning som ar tillaten.

DEN BARANDE REGELN
------------------
Domen ar auktoritativ. En sammanfattning far aldrig bli ett andra omdome
(I1, I11). Det modellen ser av ogat ar ogats EGEN TEXT, ordagrant: ingen
omformulering, ingen omrakning, ingen omsortering, ingen avrundning.

Darfor arbetar modulen pa ORIGINALETS RADER. Den plockar bort hela rader och
skriver aldrig om en enda. Att lasa rapporten och rendera om den vore redan
en omskrivning: `oga_kontrakt.Rapport.text()` formaterar RUN-raden med sin
egen precision, och en rapport som gatt genom en omrendering ar inte langre
ordagrant ogats.

VARFOR TRIMNINGEN INTE FRAGAR EN ORDLISTA OM RADEN AR "OK"
-----------------------------------------------------------
Den naiva vagen ar `"OK" in rad`. Den fyrar pa fel storhet i minst tre
verkliga former:

    MINDIST OK_ROBOT+STANGSEL 412.0mm t=1.20s
        "OK" ar en del av ett PARNAMN. Raden har ingen dom alls - MINDIST bar
        ett avstand, inte ett omdome.
    STEP 3 ST010_OK_SENSOR RISE MISSING win=0.0s..1.0s
        "OK" ligger i ett SIGNALNAMN, och radens dom ar MISSING. En ordlista
        pa delstrang trimmar alltsa bort ett FYND.
    PHASE A -> B dt=5.0ms tol=2.0ms res=1.0ms OUT_OF_TOL
        ordet OK finns inte, men OUT_OF_TOL innehaller inte heller nagot av
        orden - en lista pa "fel-ord" hade tystnat har.

Det ar samma felklass som M-95 matte i harnessens NEKANDE-lista: en lista som
bar tva storheter doljer felet i det vanliga fallet.

Modulen fragar darfor GRAMMATIKEN. Ogats kontrakt (`oga_kontrakt.RADER`) har
ett monster per radsort, och i de monster som bar en dom ligger domen i en
egen alternativgrupp. Statusen lases ur DEN GRUPPEN via monstrets egen
matchning. En rad utan en sadan grupp har ingen dom, och da ar svaret "vet
inte" - vilket ar fail-closed: en rad utan dom raknas aldrig som godkand.

Vilka ord som ar domsord kommer ocksa ur kontraktet (`_FYNDORD`,
`_OSAKERORD`) plus de fem godkannandeorden i 25_kontextbudget.md avsnitt 4.
Ingen ny handskriven ordlista infors har.

VAD SOM ALDRIG TAS BORT
-----------------------
    EYES v<n>-raden, TEMPLATE, RUN            rapportens identitet
    EYES VERDICT-raden                        I1
    varje rad som INTE ar OK                  atgardsunderlaget
    hela HONESTY-sektionen                    dess franvaro gar inte att
                                              skilja fran att den aldrig kordes
    hela LIMITS-sektionen                     vad ogat INTE ser; fas 17:s Y12
                                              kraver raderna i klartext, och
                                              grinden kraver sektionen (M-65 §6)
    den raden som bar sektionens ytterlage    en MINDIST-rad ar ett avstand;
                                              trimmar man bort den minsta har
                                              man tappat just den storhet raden
                                              finns for att bara
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

_EXT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..",
    "ext", "vc_addon", "vc_assist"))
if _EXT not in sys.path:
    sys.path.insert(0, _EXT)

import oga_kontrakt as K  # noqa: E402

# De fem varden som betyder "inget att atgarda pa den har raden".
# Harkomst: 25_kontextbudget.md avsnitt 4, "Vad som aldrig tas bort ur ogats
# text" - raderna som ar OK / none / IN_TARGET / RIGID / FORMED.
OK_VARDEN = ("OK", "none", "IN_TARGET", "RIGID", "FORMED")

# Hela domsordforradet, hamtat UR KONTRAKTET. Star det inte i kontraktet ar
# det inte ett domsord, och en alternativgrupp med nagot annat i (RISE|FALL,
# RUN|PRIOR, starved|blocked) ar da inte en domsgrupp.
DOMSORD = frozenset(OK_VARDEN) | frozenset(K._FYNDORD) | frozenset(K._OSAKERORD)

# Sektioner som aldrig trimmas, hur trang budgeten an ar.
ALDRIG_TRIMMADE = ("HONESTY", "LIMITS")

# Radsorter dar EN rad bar sektionens ytterlage, och vilken grupp i
# kontraktets monster som bar talet. MINDIST ar den enda i v2: raden ar ett
# avstand i millimeter, och det minsta avstandet ar hela skalet att sektionen
# finns. Harkomst: oga_kontrakt.RADER[("SAFETY", "MINDIST")].
EXTREM = {("SAFETY", "MINDIST"): (2, "min", "minsta avstandet")}

_ALTERNATIV = re.compile(r"\(([^()]*)\)")


def _grupper(monster: str) -> List[Tuple[int, str]]:
    """[(gruppnummer, innehall)] for varje FANGANDE grupp i monstret."""
    ut = []
    nr = 0
    i = 0
    while i < len(monster):
        t = monster[i]
        if t == "\\":
            i += 2
            continue
        if t == "(":
            fangar = not monster[i + 1:i + 2] == "?"
            djup = 1
            j = i + 1
            while j < len(monster) and djup:
                if monster[j] == "\\":
                    j += 2
                    continue
                if monster[j] == "(":
                    djup += 1
                elif monster[j] == ")":
                    djup -= 1
                j += 1
            if fangar:
                nr += 1
                ut.append((nr, monster[i + 1:j - 1]))
            i += 1
            continue
        i += 1
    return ut


_STATUSGRUPP: Dict[Tuple[str, str], Optional[int]] = {}


def statusgrupp(sektion: str, nyckelord: str) -> Optional[int]:
    """Vilken fangande grupp i radens monster som bar domen, eller None.

    En grupp ar en domsgrupp bara om VARJE alternativ i den ar ett domsord ur
    kontraktet. Det ar det som skiljer (OK|SHORT) fran (RISE|FALL).
    """
    nyckel = (sektion, nyckelord)
    if nyckel in _STATUSGRUPP:
        return _STATUSGRUPP[nyckel]
    monster = K.RADER.get(nyckel)
    svar = None
    if monster:
        for nr, innehall in _grupper(monster):
            delar = innehall.split("|")
            if len(delar) < 2:
                continue
            if all(d in DOMSORD for d in delar):
                svar = nr
                break
    _STATUSGRUPP[nyckel] = svar
    return svar


def status(sektion: str, rad: str) -> Optional[str]:
    """Radens dom, ur grammatikens egen grupp. None = raden bar ingen dom.

    Kastar aldrig pa en okand rad: den svarar None, och None ar fail-closed
    overallt i modulen (en rad utan kand dom raknas aldrig som godkand nar
    fragan ar "far den tas bort som OK?").
    """
    rad = rad.strip()
    if not rad:
        return None
    nyckelord = rad.split(" ", 1)[0]
    monster = K.RADER.get((sektion, nyckelord))
    if monster is None:
        return None
    m = re.match(monster, rad)
    if m is None:
        return None
    delar = rad.split()
    if len(delar) == 2 and delar[1] == "none":
        return "none"
    nr = statusgrupp(sektion, nyckelord)
    if nr is None:
        return None
    try:
        return m.group(nr)
    except IndexError:
        return None


def ar_fynd(sektion: str, rad: str) -> bool:
    """Baer raden en dom som INTE ar godkand? Da ror trimningen aldrig sektionen."""
    s = status(sektion, rad)
    return s is not None and s not in OK_VARDEN


@dataclass(frozen=True)
class Trimnotis:
    sektion: str
    nyckelord: str
    antal: int
    kvar: int
    skal: str

    def rad(self) -> str:
        return ("%d %s-rader utelamnade ur SECTION %s, alla utan fynd; %d star "
                "kvar (%s)" % (self.antal, self.nyckelord, self.sektion,
                               self.kvar, self.skal))


def _radlista(text: str):
    """[(index, sektion|None, radtext)] over originalets rader, ordagrant."""
    ut = []
    sektion = None
    for i, rad in enumerate(text.splitlines()):
        naken = rad.strip()
        if naken.startswith("SECTION "):
            sektion = naken.split(" ", 1)[1]
            ut.append((i, None, rad))
            continue
        ut.append((i, sektion, rad))
    return ut


def _extremrad(sektion, nyckelord, rader) -> Optional[int]:
    """Index i `rader` for raden som bar sektionens ytterlage, om nagon gor det."""
    spec = EXTREM.get((sektion, nyckelord))
    if not spec:
        return None
    grupp, sort, _ = spec
    monster = K.RADER.get((sektion, nyckelord))
    bast = None
    basti = None
    for i, rad in rader:
        m = re.match(monster, rad.strip())
        if not m:
            continue
        try:
            v = float(m.group(grupp))
        except (TypeError, ValueError, IndexError):
            continue
        if bast is None or (v < bast if sort == "min" else v > bast):
            bast, basti = v, i
    return basti


def trimma(text: str, tak_byte: int):
    """Kapar ogats rapport till taket. Returnerar (text, [Trimnotis]).

    Texten som kommer tillbaka ar RAPPORTEN, ordagrant, med hela rader
    borttagna. Notiserna hor UTANFOR blocket - `oga_kontrakt.las()` kastar
    Kontraktsfel pa ett okant nyckelord i en kand sektion, sa en inskjuten
    rad inne i blocket skulle gora rapporten olasbar for lasaren. En
    sammanfattning som gor domen olasbar ar varre an ingen sammanfattning.
    """
    if tak_byte < 1:
        raise ValueError("taket %r ar inget tak" % (tak_byte,))
    if len(text.encode("utf-8")) <= tak_byte:
        return text, []

    # Fail-closed: en rapport vi inte kan lasa trimmas inte alls.
    K.las(text)

    rader = _radlista(text)
    behall = set(i for i, _s, _r in rader)

    # Sektioner som over huvud taget far roras.
    per_sektion: Dict[str, List[Tuple[int, str]]] = {}
    for i, sektion, rad in rader:
        if sektion is None or not rad.strip():
            continue
        per_sektion.setdefault(sektion, []).append((i, rad))

    kandidater = []
    for sektion, sektionsrader in per_sektion.items():
        if sektion in ALDRIG_TRIMMADE:
            continue
        if any(ar_fynd(sektion, r) for _i, r in sektionsrader):
            continue
        per_nyckel: Dict[str, List[Tuple[int, str]]] = {}
        for i, r in sektionsrader:
            per_nyckel.setdefault(r.strip().split(" ", 1)[0], []).append((i, r))
        for nyckelord, gruppen in per_nyckel.items():
            if len(gruppen) < 3:
                # Forsta och sista raden star alltid kvar, sa en grupp under
                # tre rader ger ingenting att spara.
                continue
            kandidater.append((sektion, nyckelord, gruppen))

    # Storsta gruppen forst: den kostar mest och sager minst per rad.
    kandidater.sort(key=lambda k: (-len(k[2]), k[0], k[1]))

    notiser: List[Trimnotis] = []
    for sektion, nyckelord, gruppen in kandidater:
        if _storlek(text, behall) <= tak_byte:
            break
        skyddade = {gruppen[0][0], gruppen[-1][0]}
        skal = "forsta och sista raden"
        extrem = _extremrad(sektion, nyckelord, gruppen)
        if extrem is not None:
            skyddade.add(extrem)
            skal = "forsta, sista och raden med %s" % EXTREM[
                (sektion, nyckelord)][2]
        borttagna = 0
        for i, _r in gruppen:
            if _storlek(text, behall) <= tak_byte:
                break
            if i in skyddade:
                continue
            behall.discard(i)
            borttagna += 1
        if borttagna:
            notiser.append(Trimnotis(sektion=sektion, nyckelord=nyckelord,
                                     antal=borttagna,
                                     kvar=len(gruppen) - borttagna,
                                     skal=skal))
    return _bygg(text, behall), notiser


def _storlek(text: str, behall) -> int:
    return len(_bygg(text, behall).encode("utf-8"))


def _bygg(text: str, behall) -> str:
    rader = [r for i, r in enumerate(text.splitlines()) if i in behall]
    return "\n".join(rader) + ("\n" if text.endswith("\n") else "")


def block(rapport: str, notiser: List[Trimnotis]) -> str:
    """Rapporten plus noteringarna, med noteringarna UTANFOR blocket."""
    delar = [rapport.rstrip("\n")]
    for n in notiser:
        delar.append(n.rad())
    return "\n".join(delar) + "\n"


# ---------------------------------------------------------------------------
# Granskningen
# ---------------------------------------------------------------------------

O1_DOM_BORTA = "O1_DOM_BORTA"
O2_FYND_BORTA = "O2_FYND_BORTA"
O3_SKYDDAD_SEKTION = "O3_SKYDDAD_SEKTION"
O4_OMSKRIVEN_RAD = "O4_OMSKRIVEN_RAD"
O5_NOTIS_I_BLOCKET = "O5_NOTIS_I_BLOCKET"
O6_OLASBAR = "O6_OLASBAR"


def _extremkontroll(orader, skickade) -> List[str]:
    """Bar det som skickades kvar varje sektions ytterlage?

    En MINDIST-rad ar ett avstand. Trimmar man bort den MINSTA har man tappat
    just den storhet raden finns for att bara, och det som star kvar ser ut
    som en tryggare korning an den var.
    """
    ut = []
    per: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    sektion = None
    for i, rad in enumerate(orader):
        naken = rad.strip()
        if naken.startswith("SECTION "):
            sektion = naken.split(" ", 1)[1]
            continue
        if sektion is None or not naken:
            continue
        nyckel = (sektion, naken.split(" ", 1)[0])
        if nyckel in EXTREM:
            per.setdefault(nyckel, []).append((i, naken))
    for (sektion, nyckelord), gruppen in per.items():
        i = _extremrad(sektion, nyckelord, gruppen)
        if i is None:
            continue
        rad = dict(gruppen)[i]
        if rad not in skickade:
            ut.append("%s: raden %r bar %s i SECTION %s och togs bort"
                      % (O2_FYND_BORTA, rad, EXTREM[(sektion, nyckelord)][2],
                         sektion))
    return ut


def granska(original: str, skickat: str) -> List[str]:
    """Faller om det som skickades inte ar ogats egen text minus hela OK-rader.

    Detta ar byte-for-byte-provet i 25_kontextbudget.md avsnitt 4, mekaniserat.
    """
    ut = []
    orader = [r for r in original.splitlines() if r.strip()]
    srader = [r for r in skickat.splitlines() if r.strip()]
    obehall = set(r.strip() for r in orader)

    # Notiser far sta efter domsraden, aldrig inne i blocket.
    domsindex = [i for i, r in enumerate(srader)
                 if r.strip().startswith("EYES VERDICT")]
    if not domsindex:
        ut.append("%s: EYES VERDICT-raden finns inte i det som skickades"
                  % O1_DOM_BORTA)
        return ut
    slut = domsindex[0]
    blockrader = srader[:slut + 1]

    for r in blockrader:
        if r.strip() not in obehall:
            ut.append("%s: raden %r star i det som skickades men inte i ogats "
                      "egen text" % (O4_OMSKRIVEN_RAD, r.strip()))

    if orader[0].strip() != blockrader[0].strip():
        ut.append("%s: forsta raden ar %r, ogat skrev %r"
                  % (O1_DOM_BORTA, blockrader[0].strip(), orader[0].strip()))
    if orader[-1].strip() != blockrader[-1].strip():
        ut.append("%s: domsraden ar %r, ogat skrev %r"
                  % (O1_DOM_BORTA, blockrader[-1].strip(), orader[-1].strip()))

    skickade = set(r.strip() for r in blockrader)
    sektion = None
    for rad in orader:
        naken = rad.strip()
        if naken.startswith("SECTION "):
            sektion = naken.split(" ", 1)[1]
            if naken not in skickade:
                ut.append("%s: SECTION %s saknas i det som skickades"
                          % (O3_SKYDDAD_SEKTION, sektion))
            continue
        if sektion is None:
            continue
        if naken in skickade:
            continue
        if sektion in ALDRIG_TRIMMADE:
            ut.append("%s: raden %r ur SECTION %s togs bort; sektionen far "
                      "aldrig trimmas" % (O3_SKYDDAD_SEKTION, naken, sektion))
        elif ar_fynd(sektion, naken):
            ut.append("%s: raden %r bar ett fynd och togs anda bort"
                      % (O2_FYND_BORTA, naken))
    ut.extend(_extremkontroll(orader, skickade))
    try:
        K.las("\n".join(blockrader) + "\n")
    except Exception as e:      # noqa: BLE001 - kontraktets egna fel
        ut.append("%s: det som skickades gar inte langre att lasa som en "
                  "ogonrapport: %s" % (O6_OLASBAR, e))
    return ut
