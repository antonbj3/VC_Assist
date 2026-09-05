# -*- coding: utf-8 -*-
"""Bankkontraktet: en gemensam form for allt som benchas (85_bankkontraktet.md).

Repot har 26 korningar under `tests/protocol/`. Var och en mater nagot riktigt.
Ingen svarar i samma form, ingen vet om de andra finns, och ingen kan saga vad
som INTE ar benchat.

Modulen laser varje kornings EGNA deklaration - en modulniva-dict som heter
`BANKPOST` - och domer den. Deklarationen lases med AST, aldrig genom import:
en korning som importeras kor sin modulniva-kod, och flera av dem satter
sys.path eller oppnar filer.

## Regeln som bar allt

`facitkalla` far aldrig peka pa nagot i `under_prov`. BENCH-4 stod gron i
manader mot ett facit som raknades fram av samma algoritm som domdes. Talet var
perfekt och matte ingenting.

Det ar den enda kontroll som gar att mekanisera - vi kan inte se att ett facit
ar FEL, bara att det kommer nagon annanstans ifran an koden som prova.
"""
from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

# Vad en korning kan behova for att alls ga att kora. Ett hopp ar aldrig ett
# godkannande, sa den som kor maste kunna saga VAD som saknades.
KRAV = ("inget", "strucpp", "vc", "openplc", "modell", "windows")

# Falten en post maste bara. Saknas ett ar posten ogiltig, och en ogiltig post
# far inte raknas som en gron.
OBLIGATORISKA = ("pastar", "under_prov", "facit", "facitkalla", "trasiga_fall")


@dataclass
class Bankpost:
    """Ett pastaende med ett facit och ett satt att falla."""

    korning: str
    pastar: str = ""
    under_prov: Tuple[str, ...] = ()
    facit: str = ""
    facitkalla: str = ""
    facitkalla_filer: Tuple[str, ...] = ()
    trasiga_fall: Tuple[str, ...] = ()
    kraver: Tuple[str, ...] = ("inget",)
    matningar: Tuple[str, ...] = ()


@dataclass
class Registerdom:
    brister: List[str] = field(default_factory=list)
    poster: List[Bankpost] = field(default_factory=list)
    odeklarerade: List[str] = field(default_factory=list)

    @property
    def godkand(self) -> bool:
        return not self.brister


def _konstant(nod):
    """Ett literalt varde ur AST, eller None. Aldrig eval."""
    try:
        return ast.literal_eval(nod)
    except (ValueError, SyntaxError):
        return None


def las_bankpost(sokvag: str):
    """`BANKPOST`-dicten ur en korning, eller None. Laser, kor aldrig."""
    with open(sokvag, "r", encoding="utf-8") as f:
        trad = ast.parse(f.read(), filename=sokvag)
    for sats in trad.body:
        if not isinstance(sats, ast.Assign):
            continue
        for mal in sats.targets:
            if isinstance(mal, ast.Name) and mal.id == "BANKPOST":
                d = _konstant(sats.value)
                return d if isinstance(d, dict) else None
    return None


def _strang(d, nyckel):
    v = d.get(nyckel)
    return v if isinstance(v, str) else ""


def _lista(d, nyckel):
    v = d.get(nyckel)
    if isinstance(v, str):
        return (v,)
    if isinstance(v, (list, tuple)):
        return tuple(str(x) for x in v)
    return ()


def granska_post(namn: str, d: Dict) -> Tuple[Bankpost, List[str]]:
    """Domer EN post. Returnerar posten och dess brister."""
    brister = []
    for falt in OBLIGATORISKA:
        if not d.get(falt):
            brister.append("%s: %s saknas" % (namn, falt))

    post = Bankpost(
        korning=namn,
        pastar=_strang(d, "pastar"),
        under_prov=_lista(d, "under_prov"),
        facit=_strang(d, "facit"),
        facitkalla=_strang(d, "facitkalla"),
        facitkalla_filer=_lista(d, "facitkalla_filer"),
        trasiga_fall=_lista(d, "trasiga_fall"),
        kraver=_lista(d, "kraver") or ("inget",),
        matningar=_lista(d, "matningar"),
    )

    # DEN BARANDE KONTROLLEN. Ett facit ur samma kod som doms mater ingenting.
    delade = set(post.facitkalla_filer) & set(post.under_prov)
    if delade:
        brister.append(
            "%s: facitkallan ligger i koden som provas (%s). Ett facit ur samma "
            "algoritm som doms ar tautologiskt - BENCH-4 stod gron i manader pa "
            "just det." % (namn, ", ".join(sorted(delade))))

    for k in post.kraver:
        if k not in KRAV:
            brister.append("%s: okant krav %r; kraven ar %s"
                           % (namn, k, ", ".join(KRAV)))

    # Ett pastaende ska ga att motbevisa. En etikett gor det inte.
    if post.pastar and len(post.pastar.split()) < 4:
        brister.append("%s: pastar ar en etikett, inte ett pastaende: %r"
                       % (namn, post.pastar))
    return post, brister


def granska_registret(protokollkatalog: str) -> Registerdom:
    """Varje korning under katalogen, med sin deklaration eller utan.

    Tva kontroller gor registret komplett AV KONSTRUKTION: ingen forraldralos
    korning, och ingen post som pekar pa en fil som inte finns. Utan dem ar
    registret en lista nagon minns att uppdatera - och ett verktyg man maste
    minnas ar redan glomt.
    """
    dom = Registerdom()
    filer = sorted(f for f in os.listdir(protokollkatalog)
                   if f.startswith("kor_") and f.endswith(".py"))
    for f in filer:
        sokvag = os.path.join(protokollkatalog, f)
        d = las_bankpost(sokvag)
        if d is None:
            dom.odeklarerade.append(f)
            continue
        post, brister = granska_post(f, d)
        dom.poster.append(post)
        dom.brister.extend(brister)
    return dom


def korbara(poster: Sequence[Bankpost], tillgangligt: Sequence[str]) -> Tuple:
    """Delar posterna i de som gar att kora har och de som inte gor det.

    Ett hopp ar aldrig ett godkannande, sa den andra listan bar SKALET.
    """
    har, hoppas = [], []
    finns = set(tillgangligt) | {"inget"}
    for p in poster:
        saknas = [k for k in p.kraver if k not in finns]
        (hoppas if saknas else har).append(
            (p, ", ".join(saknas)) if saknas else p)
    return har, hoppas
