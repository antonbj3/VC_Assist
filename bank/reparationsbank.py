# -*- coding: utf-8 -*-
"""M-52: reparationsslingan över banken, i två lägen, med attrappmodell.

`docs/spec/61_st_generering.md` lämnar frågan öppen: ska slingan få se tidigare
försök eller starta rent varje varv? "Båda har kända nackdelar och valet ska
mätas, inte tyckas." Den här filen är mätningen. Talen står i
`docs/matningar/M-52_reparationsslingan.md`.

## Modelledet är ATTRAPPERAT, och det sägs rakt ut

Ingen språkmodell körs här. Slingans mekanik är det som mäts, och den mäts med
en deterministisk attrapp — `AttrappReparator` nedan. Attrappen är **minneslös
per konstruktion**: den ser bara det slingans läge visar den, och den vet inte
vilket läge den kör i. Skillnaden mellan lägena kommer alltså ur vad slingan
visar, inte ur att attrappen behandlar lägena olika.

## Materialet är bankens eget, inte påhittat

Repertoaren i varje körning är:

    1. en deklarationsmiss   referensen med EN utsignal felstavad
    2. ett motbevis          människoskrivet, med namngivna brister
    3. ett andra motbevis    likaså
    4. referensen            som domaren redan godkänt

Motbevisen kommer ur `bank/uppgifter/*.json` och är skrivna före försöket, av
en människa. Modellen skriver aldrig sitt eget facit (Koziolek m.fl., arXiv
2405.01874: 0–50 % korrekta genererade assertions, sämst på timers; se
`docs/research/R-01`).

## Orakeltabellen, och varför den gör mätningen strängare och inte snällare

Attrappen får en tabell från felklassignatur till nästa försök. Den är byggd
genom att köra repertoaren en gång i förväg. Det gör attrappen till en
**maximalt kompetent minneslös reparatör**: för varje fel den kan få se har den
exakt rätt nästa försök. En riktig modell har ingen sådan tabell. Talen för
`rent` är alltså en ÖVRE gräns för vad ett minneslöst läge kan klara, inte en
förutsägelse om en riktig modell.

Tabellen har en egenskap som är hela poängen: den kan bara bära ETT svar per
signatur. Bär två försök samma signatur går det andra inte att nå minneslöst.

Körs som `python3 bank/reparationsbank.py`.

beskriver: svc/vc_assist_svc/plc/reparation.py, bank/domare.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, ".."))
for _p in (_HAR, os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare  # noqa: E402
from vc_assist_svc.harness.modell import Modell, Modellsvar  # noqa: E402
from vc_assist_svc.plc import reparation as R  # noqa: E402
from vc_assist_svc.plc.signalkarta import (FRAN_PLC, TILL_PLC,  # noqa: E402
                                           Signalkarta, karta_av_rader)
from vc_assist_svc.plc.skelett import Skelett  # noqa: E402

# ---------------------------------------------------------------- kartan

# Bankens typord -> ST-typ. Banken skriver signaltypen i `control.signals`, och
# den ska inte gissas om på vägen.
BANKTYP = {"bool": "BOOL", "real": "REAL", "int": "INT"}

# ST-typ -> adressens storleksbokstav. Samma tabell som signalkartans
# TYP_STORLEK, begränsad till de tre typer banken använder.
STORLEK = {"BOOL": "X", "REAL": "D", "INT": "W"}

# Bitar per byte i OpenPLC:s bool-tabell (bool_input[BUFFER_SIZE][8]).
BITAR_PER_BYTE = 8              # Mätt i M-20.


def karta_ur_uppgift(post: dict, station: str) -> Signalkarta:
    """Signalkartan ur uppgiftens `control.signals`.

    Adresserna delas ut löpande per riktning och storleksklass. De är inte
    mätta mot någon verklig scen — de finns för att skelettet ska gå att
    generera, och för att grind 3 ska ha något att jämföra mot. En bänkkarta
    är inte en driftkarta.
    """
    nasta: Dict[Tuple[str, str], List[int]] = {}
    rader = []
    for s in (post.get("control") or {}).get("signals") or []:
        typ = BANKTYP[s["type"]]
        till_plc = s["dir"] == "in"
        riktning = TILL_PLC if till_plc else FRAN_PLC
        omrade = "I" if till_plc else "Q"
        stor = STORLEK[typ]
        rakn = nasta.setdefault((omrade, stor), [0, 0])
        if stor == "X":
            adress = "%%%s%s%d.%d" % (omrade, stor, rakn[0], rakn[1])
            rakn[1] += 1
            if rakn[1] >= BITAR_PER_BYTE:
                rakn[1] = 0
                rakn[0] += 1
        else:
            adress = "%%%s%s%d" % (omrade, stor, rakn[0])
            rakn[0] += 1
        rader.append(("plc", s["name"], s["name"], typ, riktning, adress,
                      False, s.get("comment")))
    return karta_av_rader(station, rader)


_PROGRAMRAD = re.compile(r"^\s*PROGRAM\s+(\w+)", re.I)


def dela_referens(referens: str) -> Tuple[str, str, str]:
    """(station, extra_deklarationer, kropp) ur en hel referens-POU.

    Deklarationerna hör till ramen och inte till modellen — skelettet tar emot
    dem som `extra_deklarationer`, precis som `61_st_generering.md` säger om
    arbetsvariabler. Att de i banken är HÄMTADE ur referenslösningen är en
    verklig kanal från facit till prompten, och den står i M-52.
    """
    rader = referens.splitlines()
    m = _PROGRAMRAD.match(rader[0])
    if not m:
        raise ValueError("referensen börjar inte med PROGRAM: %r" % rader[0])
    station = m.group(1)
    i_var = next(i for i, r in enumerate(rader) if r.strip().upper() == "VAR")
    i_slut = next(i for i, r in enumerate(rader)
                  if r.strip().upper() == "END_VAR")
    i_endp = next(i for i, r in enumerate(rader)
                  if r.strip().upper() == "END_PROGRAM")
    extra = "\n".join(rader[i_var:i_slut + 1])
    kropp = "\n".join(rader[i_slut + 1:i_endp]).strip("\n")
    return station, extra, kropp


# ------------------------------------------------------------- spårfacit

# Spårfacits tre påståendeformer -> felklass ur `docs/spec/82_felklasser.md`.
#
#   flank      F15 står ordagrant i tabellen: "spårfacit, flankräkning".
#   invariant  F8 "saknad eller felaktig förregling". domare.py kallar
#              invarianten "förreglingens form", och det är den storhet den
#              mäter.
#   punktkrav  F5 "stegen sker i fel ordning".
#   tolkfel    F1 "koden kompilerar inte" — här: går inte att köra alls.
#
# F6 och F7 används INTE: sorteringsregel 5 säger att de aldrig får fällas av
# en statisk grind, och spårfacit ligger inte i ögat. F5 och F8 är vår läsning
# och föreslås som en egen rad i 82_felklasser.md; förslaget står i M-52.
SPARKLASS = (("tolkfel:", "F1"), ("flank:", "F15"), ("invariant:", "F8"))
SPARKLASS_OVRIGT = "F5"


def sparklass(kod: str) -> str:
    for prefix, klass in SPARKLASS:
        if kod.startswith(prefix):
            return klass
    return SPARKLASS_OVRIGT


class Sparfacitsteg(R.Grindsteg):
    """Bankens spårfacit som ett steg i reparationsslingan.

    Steget dömer inte om något: det anropar `domare.dom` och skriver ut
    domarens EGNA brister, kod och text, i grindarnas gemensamma märkform
    `[kod/Fklass]`. Att låta domaren tala i samma grammatik som grind 2 och 3
    är inte en omskrivning — det är att ge samma sorts svar samma form.
    """

    namn = "sparfacit"

    def __init__(self, post: dict):
        self.post = post

    def doma(self, st_kalla: str) -> R.Grinddom:
        dom = domare.dom(self.post, st_kalla)
        if dom.godkand:
            return R.Grinddom(grind=self.namn, ok=True)
        rader = ["SPARFACIT EJ GODKAND, %d brister, %d scan"
                 % (len(dom.brister), dom.scan_kord)]
        koder: List[str] = []
        klasser: List[str] = []
        for b in dom.brister:
            klass = sparklass(b.kod)
            rader.append("  [%s/%s] %s" % (b.kod, klass, b.text.strip()))
            if b.kod not in koder:
                koder.append(b.kod)
            if klass not in klasser:
                klasser.append(klass)
        return R.Grinddom(grind=self.namn, ok=False, utdata="\n".join(rader),
                          koder=tuple(koder), klasser=tuple(klasser))


# ------------------------------------------------------------- attrappen

class AttrappReparator(Modell):
    """En minneslös reparatör med en orakeltabell. ENDAST för mätning.

    Den har ingen kanal ut och kan inte få en: den har en lista kroppar och en
    tabell. Regeln är densamma i båda lägena, och attrappen vet inte vilket
    läge den kör i:

      1. Ser den ingen grinddom: skriv repertoarens första kropp.
      2. Ser den en grinddom: slå upp den senaste domens felklassignatur i
         tabellen och skriv den kropp tabellen pekar ut. Är signaturen okänd,
         börja om från början — en minneslös reparatör har inget annat att
         falla tillbaka på.
      3. Syns tidigare försök i historiken: hoppa förbi varje kropp som redan
         står där. Det är HELA det extra som historikläget ger.

    Punkt 3 är verkningslös i `rent`, därför att inga tidigare försök visas
    där. Attrappen behöver alltså ingen lägesflagga, och kan inte fuska med en.
    """

    leverantor = "attrapp"
    namn = "attrapp-reparator"

    def __init__(self, repertoar: Sequence[str],
                 tabell: Dict[Tuple[str, ...], int]):
        if len(repertoar) < 2:
            raise ValueError("en repertoar under två kroppar mäter ingen "
                             "reparation alls")
        self.repertoar = list(repertoar)
        self.tabell = dict(tabell)
        self.sedda_meddelanden: List[Tuple] = []

    def svara(self, systemprompt, meddelanden, verktyg) -> Modellsvar:
        self.sedda_meddelanden.append(tuple(meddelanden))
        forsok = [m.text for m in meddelanden if m.roll == "modell"]
        domar = [m.text for m in meddelanden if m.roll == "grind"]
        if not domar:
            i = 0
        else:
            i = self.tabell.get(signatur_ur_text(domar[-1]), 0)
        while i < len(self.repertoar) and self.repertoar[i] in forsok:
            i += 1
        if i >= len(self.repertoar):
            i = len(self.repertoar) - 1
        return Modellsvar(text=self.repertoar[i], leverantor=self.leverantor)


def signatur_ur_text(domtext: str) -> Tuple[str, ...]:
    """Felklassignaturen ur en grinds egen utdata, sorterad."""
    return tuple(sorted(set(R.klasser_ur(domtext))))


# ------------------------------------------------------------- körningen

def signatur_av(grindar: Sequence[R.Grindsteg], skelett: Skelett,
                kropp: str) -> Tuple[str, ...]:
    """Felklassignaturen en kropp ger, genom samma grindkedja som slingan."""
    try:
        st_kalla = skelett.las_svar(kropp)
    except Exception:
        return (R.KLASS_RAM,)
    for steg in grindar:
        dom = steg.doma(st_kalla)
        if not dom.ok:
            return tuple(sorted(set(dom.klasser)))
    return ()


def bygg_tabell(grindar: Sequence[R.Grindsteg], skelett: Skelett,
                repertoar: Sequence[str]) -> Dict[Tuple[str, ...], int]:
    """Orakeltabellen: signatur -> index på nästa försök. Först skriven vinner.

    Att den första vinner är inte en förenkling utan själva mekanismen: en
    minneslös reparatör har EN reaktion per fel den ser. Bär två försök samma
    signatur går det andra inte att nå utan minne.
    """
    tabell: Dict[Tuple[str, ...], int] = {}
    for k in range(len(repertoar) - 1):
        sig = signatur_av(grindar, skelett, repertoar[k])
        if sig and sig not in tabell:
            tabell[sig] = k + 1
    return tabell


def felstava_utsignal(kropp: str, tagg: str) -> str:
    """Kroppen med `tagg` felstavad. En deklarationsmiss, inte ett logikfel.

    Det är den felklass `61_st_generering.md` säger att skelettet finns för att
    ta bort, och den som en modell utan skelett gör oftast.
    \b runt taggen: ST050_CNV_RUN får inte träffa inuti ett längre namn.
    """
    return re.sub(r"\b%s\b" % re.escape(tagg), tagg + "X", kropp)


def uppgiftstext(post: dict, skelett: Skelett) -> str:
    """Det modellen får: uppgiftens egen text och skelettet med tomt fack."""
    return "%s\n\nSkelettet. Skriv bara kroppen, mellan markorerna:\n\n%s" % (
        post["prompt"], skelett.text())


def _utan_kommentarer(st_text: str) -> str:
    ut, djup, i = [], 0, 0
    while i < len(st_text):
        if st_text[i:i + 2] == "(*":
            djup += 1
            i += 2
        elif st_text[i:i + 2] == "*)" and djup:
            djup -= 1
            i += 2
        else:
            if not djup:
                ut.append(st_text[i])
            i += 1
    return "".join(ut)


# En rad ur referensen räknas som läckt bara om den bär något. Tröskeln är
# `tests/enhet/test_domare.py`:s egen: den provar samma läcka mot uppgiftens
# prompt och räknar rader över 25 tecken.
MINSTA_LACKRAD = 25             # Satt av M-52.


def lackta_rader(prompt: str, referenskropp: str) -> List[str]:
    """Rader ur referensens KROPP som står i prompten.

    Ramen räknas inte: deklarationerna hör till skelettet och står där med
    avsikt. Kroppen är det modellen ska skriva, och en enda av dess rader i
    prompten gör bänken till en avskrivningsövning.
    """
    ren = _utan_kommentarer(referenskropp)
    ut = []
    for rad in ren.splitlines():
        rad = rad.strip()
        if len(rad) > MINSTA_LACKRAD and rad in prompt:
            ut.append(rad)
    return ut


class Korning(object):
    """En slinga körd i ett läge, med sitt utfall."""

    def __init__(self, uppgift, namn, lage, protokoll, repertoar_langd,
                 tecken=0):
        self.uppgift = uppgift
        self.namn = namn
        self.lage = lage
        self.protokoll = protokoll
        self.repertoar_langd = repertoar_langd
        # Tecken som gick UT till modellen över hela slingan. Historikläget
        # betalar sin vinst i kontext, och kostnaden ska stå bredvid vinsten.
        self.tecken = tecken

    @property
    def utfall(self):
        return self.protokoll.utfall

    @property
    def varv(self):
        return len(self.protokoll.varv)


def bygg_uppsattning(post: dict) -> dict:
    """Allt en uppgift behöver för att köras: karta, skelett, grindar, kroppar."""
    facit = post["facit_spar"]
    station, extra, referenskropp = dela_referens(facit["referens"])
    karta = karta_ur_uppgift(post, station)
    skelett = Skelett.av_karta(karta, extra)
    grindar = [R.Stationssteg(karta), Sparfacitsteg(post)]
    utsignaler = karta.utgangar()
    felstavad = felstava_utsignal(referenskropp, utsignaler[0])
    motbevis = []
    for mb in facit.get("motbevis") or []:
        _st, _extra, kropp = dela_referens(mb["st"])
        motbevis.append((mb["namn"], kropp))
    return {"station": station, "karta": karta, "skelett": skelett,
            "grindar": grindar, "referens": referenskropp,
            "felstavad": felstavad, "motbevis": motbevis,
            "prompt": uppgiftstext(post, skelett)}


def kor_uppgift(post: dict, lagen=R.LAGEN, max_varv: int = R.MAX_VARV,
                upps: Optional[dict] = None) -> List[Korning]:
    """Alla körningar för en uppgift, i varje läge.

    Repertoarerna är uppgiftens egna motbevis: varje enskilt motbevis, och
    varje ORDNAT par av två olika motbevis. Paren finns därför att det är där
    två fel kan bära samma felklassignatur, och det är just den kollisionen som
    skiljer lägena åt.
    """
    upps = upps or bygg_uppsattning(post)
    tid = post["task_id"]
    ut: List[Korning] = []
    repertoarer: List[Tuple[str, List[str]]] = []
    for namn, kropp in upps["motbevis"]:
        repertoarer.append((namn, [upps["felstavad"], kropp, upps["referens"]]))
    for namn_a, kropp_a in upps["motbevis"]:
        for namn_b, kropp_b in upps["motbevis"]:
            if namn_a == namn_b:
                continue
            repertoarer.append(("%s+%s" % (namn_a, namn_b),
                                [upps["felstavad"], kropp_a, kropp_b,
                                 upps["referens"]]))
    for namn, repertoar in repertoarer:
        tabell = bygg_tabell(upps["grindar"], upps["skelett"], repertoar)
        for lage in lagen:
            slinga = R.Reparationsslinga(upps["skelett"], upps["grindar"],
                                         lage=lage, max_varv=max_varv)
            modell = AttrappReparator(repertoar, tabell)
            protokoll = slinga.kor(modell, upps["prompt"], uppgift=tid)
            tecken = sum(len(m.text) for h in modell.sedda_meddelanden
                         for m in h)
            ut.append(Korning(tid, namn, lage, protokoll, len(repertoar),
                              tecken))
    return ut


def uppgifter_med_sparfacit() -> List[dict]:
    ut = []
    katalog = os.path.join(_HAR, "uppgifter")
    for f in sorted(os.listdir(katalog)):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(katalog, f), "r", encoding="utf-8") as fh:
            post = json.load(fh)
        if post.get("facit_spar"):
            ut.append(post)
    return ut


# ---------------------------------------------------------------- rapport

def rapport(korningar: Sequence[Korning], lagen=R.LAGEN) -> str:
    rader = []
    per_lage: Dict[str, List[Korning]] = dict((l, []) for l in lagen)
    for k in korningar:
        per_lage[k.lage].append(k)
    n = len(per_lage[lagen[0]])
    rader.append("SLINGOR: %d per lage, %d lagen, %d totalt"
                 % (n, len(lagen), len(korningar)))
    rader.append("")
    rader.append("%-10s %-12s %-12s %-12s %s"
                 % ("lage", "lost", "last", "tak", "varv till lost"))
    for lage in lagen:
        ks = per_lage[lage]
        lost = [k for k in ks if k.utfall == R.UTFALL_LOST]
        last = [k for k in ks if k.utfall == R.UTFALL_LAST]
        tak = [k for k in ks if k.utfall == R.UTFALL_TAK]
        varv = {}
        for k in lost:
            varv[k.varv] = varv.get(k.varv, 0) + 1
        rader.append("%-10s %-12s %-12s %-12s %s"
                     % (lage, "%d av %d" % (len(lost), len(ks)),
                        "%d av %d" % (len(last), len(ks)),
                        "%d av %d" % (len(tak), len(ks)),
                        ", ".join("varv %d: %d" % (v, varv[v])
                                  for v in sorted(varv))))
    rader.append("")
    rader.append("FEL PER KLASS (antal varv som fallde pa klassen)")
    klasser = set()
    per_lage_klass: Dict[str, Dict[str, int]] = {}
    for lage in lagen:
        rakn: Dict[str, int] = {}
        varv_totalt = 0
        for k in per_lage[lage]:
            varv_totalt += len(k.protokoll.varv)
            for klass, antal in k.protokoll.klassrakning().items():
                rakn[klass] = rakn.get(klass, 0) + antal
        rakn["_varv"] = varv_totalt
        per_lage_klass[lage] = rakn
        klasser |= set(x for x in rakn if not x.startswith("_"))
    rader.append("%-10s %s" % ("lage", "  ".join("%-10s" % c
                                                 for c in sorted(klasser))))
    for lage in lagen:
        rakn = per_lage_klass[lage]
        rader.append("%-10s %s   (av %d domda varv)"
                     % (lage,
                        "  ".join("%-10s" % ("%d" % rakn.get(c, 0))
                                  for c in sorted(klasser)),
                        rakn["_varv"]))
    rader.append("")
    rader.append("TECKEN TILL MODELLEN (summa over alla slingor, samma manus)")
    for lage in lagen:
        ks = per_lage[lage]
        rader.append("%-10s %d tecken over %d slingor, %d per slinga i snitt"
                     % (lage, sum(k.tecken for k in ks), len(ks),
                        sum(k.tecken for k in ks) // max(1, len(ks))))
    rader.append("")
    rader.append("PER UPPGIFT")
    rader.append("%-8s %-10s %-12s %-12s %-12s"
                 % ("uppgift", "lage", "lost", "last", "tak"))
    for tid in sorted(set(k.uppgift for k in korningar)):
        for lage in lagen:
            ks = [k for k in korningar
                  if k.uppgift == tid and k.lage == lage]
            rader.append(
                "%-8s %-10s %-12s %-12s %-12s"
                % (tid, lage,
                   "%d av %d" % (len([k for k in ks
                                      if k.utfall == R.UTFALL_LOST]), len(ks)),
                   "%d av %d" % (len([k for k in ks
                                      if k.utfall == R.UTFALL_LAST]), len(ks)),
                   "%d av %d" % (len([k for k in ks
                                      if k.utfall == R.UTFALL_TAK]), len(ks))))
    rader.append("")
    rader.append("SISTA VARVET SOM LOSTE NAGOT: %s"
                 % (max([k.varv for k in korningar
                         if k.utfall == R.UTFALL_LOST] or [0])))
    rader.append("")
    rader.append("EJ KORDA GRINDAR (aldrig ett godkannande)")
    ej: Dict[str, str] = {}
    for k in korningar:
        ej.update(k.protokoll.ej_korda)
    for namn in sorted(ej):
        rader.append("  %-22s %s" % (namn, ej[namn]))
    return "\n".join(rader)


def main(argv=None):
    ap = argparse.ArgumentParser(description="M-52: reparationsslingan i tva lagen")
    ap.add_argument("--tak", type=int, default=R.MAX_VARV,
                    help="max varv per slinga (standard: MAX_VARV)")
    ap.add_argument("--uppgift", help="bara en uppgift, t.ex. T-07")
    a = ap.parse_args(argv)

    poster = uppgifter_med_sparfacit()
    if a.uppgift:
        poster = [p for p in poster if p["task_id"] == a.uppgift]
        if not poster:
            raise SystemExit("ingen uppgift %s med sparfacit" % a.uppgift)

    korningar: List[Korning] = []
    for post in poster:
        upps = bygg_uppsattning(post)
        lackt = lackta_rader(upps["prompt"], upps["referens"])
        if lackt:
            raise SystemExit(
                "%s: referensens kropp lacker in i prompten (%d rader), t.ex. "
                "%r. En slinga som konvergerar pa en lackt losning mater "
                "avskrift." % (post["task_id"], len(lackt), lackt[0]))
        korningar.extend(kor_uppgift(post, max_varv=a.tak, upps=upps))

    print("UPPGIFTER: %d med sparfacit, %d motbevis totalt"
          % (len(poster),
             sum(len(p["facit_spar"].get("motbevis") or []) for p in poster)))
    print("MODELLEDET AR ATTRAPPERAT. Ingen sprakmodell kordes.")
    print("TAK: %d varv" % a.tak)
    print("")
    print(rapport(korningar))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
