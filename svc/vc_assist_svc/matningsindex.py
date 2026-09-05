# -*- coding: utf-8 -*-
"""Mätningsindexet: genererat ur katalogen, aldrig fört för hand.

Varför modulen finns, mätt: `docs/spec/00_index.md` bar en handskriven tabell
över mätningarna som slutade vid **M-34** medan katalogen bar **108** filer.
Sjuttiofyra mätningar var alltså osynliga för den som läser indexet - och
indexet är det första en språkmodell läser. `M-119` mätte samma sak från andra
hållet: sex frågeslag av tretton svarade ingenting, och ett av skälen var att
uppslagen inte når det som ligger på disk.

En tabell någon måste komma ihåg att uppdatera är redan inaktuell. Den här
modulen läser katalogen, och ett prov fäller om filen på disk slutat stämma.

Två fel den namnger i stället för att tiga om:

* en mätningsfil vars första rad inte är `# M-NN — titel` får ingen titel, och
  en rad utan titel är värdelös i ett index. Den räknas som **titellös** och
  namnges.
* två filer som gör anspråk på samma nummer gör varje hänvisning tvetydig.
  Numret är mätningens enda identitet.
"""
from __future__ import annotations

import io
import os
import re
from typing import Dict, List, NamedTuple, Tuple

# `# M-84 — vad uppslagen gjorde med modellens ordforrad`
# Tankstrecket är ett riktigt em-streck i alla 108 filerna; en bindestreckad
# rad är alltså inte ett alternativ utan ett fel som ska synas.
# Nollan i "M-01" bars med. Repot hanvisar till M-01 pa 25 stallen och till
# M-03 pa 46; en tabell som skriver "M-1" gor varje sadant uppslag till en
# miss - precis den tysta uppslagsmissen M-119 matte.
_RUBRIK = re.compile(r"^#\s+(M-(\d+))\s+—\s+(.+?)\s*$")
_FILNAMN = re.compile(r"^M-(\d+)_.*\.md$")

BORJAN = "<!-- MATNINGSTABELL: genererad, rör inte för hand -->"
SLUT = "<!-- SLUT MATNINGSTABELL -->"


class Matning(NamedTuple):
    nummer: int          # for sortering
    etikett: str         # "M-01", exakt som filen skriver den
    fil: str
    titel: str


class Index(NamedTuple):
    matningar: Tuple[Matning, ...]
    titellosa: Tuple[str, ...]
    kollisioner: Tuple[Tuple[int, Tuple[str, ...]], ...]


def las(katalog: str) -> Index:
    """Läs alla `M-*.md` i katalogen. Ingen fil hoppas över tyst."""
    poster: List[Matning] = []
    titellosa: List[str] = []
    per_nummer: Dict[int, List[str]] = {}
    for namn in sorted(os.listdir(katalog)):
        m = _FILNAMN.match(namn)
        if not m:
            continue
        nummer = int(m.group(1))
        per_nummer.setdefault(nummer, []).append(namn)
        with io.open(os.path.join(katalog, namn), encoding="utf-8") as f:
            forsta = f.readline()
        r = _RUBRIK.match(forsta)
        if not r:
            titellosa.append(namn)
            continue
        if int(r.group(2)) != nummer:
            # Filnamnet och rubriken säger olika nummer. Det är inte ett
            # kosmetiskt fel: uppslag sker på numret, och de två skulle peka
            # åt olika håll.
            titellosa.append(namn)
            continue
        poster.append(Matning(nummer, r.group(1), namn, r.group(3)))
    kollisioner = tuple(sorted((n, tuple(sorted(fs)))
                               for n, fs in per_nummer.items() if len(fs) > 1))
    return Index(tuple(sorted(poster)), tuple(sorted(titellosa)), kollisioner)


def tabell(index: Index) -> str:
    """Tabellen som ska stå i `00_index.md`, utan omgivande markörer."""
    rader = ["| Fil | Vad den mätte |", "|---|---|"]
    for m in index.matningar:
        rader.append("| `%s` | %s — %s |" % (m.fil, m.etikett, m.titel))
    if index.titellosa:
        rader.append("")
        rader.append("**Utan läsbar rubrikrad, och därför utan titel här:** "
                     + ", ".join("`%s`" % f for f in index.titellosa))
    if index.kollisioner:
        rader.append("")
        for nummer, filer in index.kollisioner:
            rader.append("**Nummer %d görs anspråk på av fler än en fil:** %s"
                         % (nummer, ", ".join("`%s`" % f for f in filer)))
    return "\n".join(rader)


def skriv_in(indexfil: str, ny_tabell: str) -> bool:
    """Byt ut tabellen mellan markörerna. Returnerar True om filen ändrades.

    Saknas markörerna är det ett fel, inte något att laga tyst: någon har
    tagit bort dem, och att skriva tabellen någon annanstans vore att gissa.
    """
    with io.open(indexfil, encoding="utf-8") as f:
        text = f.read()
    i = text.find(BORJAN)
    j = text.find(SLUT)
    if i < 0 or j < 0 or j < i:
        raise ValueError(
            "hittar inte markörerna %r och %r i %s - utan dem vet jag inte "
            "var tabellen hör hemma" % (BORJAN, SLUT, indexfil))
    ny = text[:i] + BORJAN + "\n\n" + ny_tabell + "\n\n" + text[j:]
    if ny == text:
        return False
    with io.open(indexfil, "w", encoding="utf-8") as f:
        f.write(ny)
    return True


def aktuell(indexfil: str, katalog: str) -> Tuple[bool, str]:
    """(stämmer, skäl). Skälet är tomt när den stämmer."""
    index = las(katalog)
    onskad = tabell(index)
    with io.open(indexfil, encoding="utf-8") as f:
        text = f.read()
    i = text.find(BORJAN)
    j = text.find(SLUT)
    if i < 0 or j < 0:
        return False, "markörerna saknas i %s" % os.path.basename(indexfil)
    pa_disk = text[i + len(BORJAN):j].strip()
    if pa_disk == onskad.strip():
        return True, ""
    saknas = [m.fil for m in index.matningar if m.fil not in pa_disk]
    if saknas:
        return False, ("%d mätningar saknas i tabellen: %s"
                       % (len(saknas), ", ".join(saknas[:5])
                          + (" ..." if len(saknas) > 5 else "")))
    return False, "tabellen på disk skiljer sig från katalogen"


def _main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rot", default=".")
    p.add_argument("--kontrollera", action="store_true",
                   help="skriv ingenting; slutkod 1 om tabellen är inaktuell")
    a = p.parse_args()
    katalog = os.path.join(a.rot, "docs", "matningar")
    indexfil = os.path.join(a.rot, "docs", "spec", "00_index.md")
    if a.kontrollera:
        ok, skal = aktuell(indexfil, katalog)
        print("aktuell" if ok else "INAKTUELL: %s" % skal)
        return 0 if ok else 1
    index = las(katalog)
    andrad = skriv_in(indexfil, tabell(index))
    print("%d mätningar, %d titellösa, %d nummerkollisioner - %s"
          % (len(index.matningar), len(index.titellosa),
             len(index.kollisioner),
             "skrev om tabellen" if andrad else "oförändrad"))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
