# -*- coding: utf-8 -*-
"""Läsaren: laddar banken, validerar varje post och svarar på frågor om den.

Frågorna som ska gå att ställa mekaniskt (fas 9 i docs/spec/70_faser.md):

  * vilka uppgifter täcker felklass X
  * hur många uppgifter per svårighetsgrad
  * vilka felklasser saknar täckning

Och den fjärde, som är hela poängen med att skriva facit i ögats grammatik:

  * håller facit mot en verklig ögondom

Endast standardbiblioteket. Körs med python3.

beskriver: bank/schema.py, bank/uppgifter/*.json, bank/katalog_index.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
if _HAR not in sys.path:
    sys.path.insert(0, _HAR)

import schema  # noqa: E402
from schema import K  # ögats kontrakt, samma modul som ögat självt använder  # noqa: E402


class Bankfel(Exception):
    """Banken går inte att lita på. Kastar hellre än returnerar en halv bank."""


class Domsjamforelse(object):
    """Utfallet av att hålla en uppgifts facit mot en verklig ögonrapport."""

    def __init__(self, task_id):
        self.task_id = task_id
        self.dom_stammer = False
        self.observerad_dom = None
        self.saknade_rader = []       # facitrader som ögat aldrig skrev
        self.forbjudna_traffar = []   # rader facit förbjöd men ögat skrev
        self.orsak_stammer = True
        self.fel = []                 # läsfel ur kontraktet, om rapporten är trasig

    @property
    def uppfyllt(self):
        return (not self.fel and self.dom_stammer and self.orsak_stammer
                and not self.saknade_rader and not self.forbjudna_traffar)

    def __repr__(self):
        return "<Domsjamforelse %s %s>" % (
            self.task_id, "uppfyllt" if self.uppfyllt else "brister")


class Uppgift(object):
    def __init__(self, data, sokvag):
        self.data = data
        self.sokvag = sokvag

    # -- bekvämligheter, så anroparen slipper gräva i råa nycklar -----------

    @property
    def id(self):
        return self.data["task_id"]

    @property
    def grupp(self):
        return self.data["grupp"]

    @property
    def bransch(self):
        return self.data["bransch"]

    @property
    def klasser(self):
        return list(self.data["targets_class"])

    @property
    def svarighet(self):
        return self.data["difficulty"]

    @property
    def ar_variant(self):
        return self.data["variant_av"] is not None

    @property
    def grind(self):
        return self.data["expect"]["gate"]

    def __repr__(self):
        return "<Uppgift %s %s>" % (self.id, self.data["title"])

    # -- facit mot verklighet ----------------------------------------------

    def jamfor(self, ogontext):
        """Håll facit mot ögats egen utdata. Ögat fäller domen (I1); vi
        implementerar aldrig om måttet, vi läser ögats slutsats."""
        res = Domsjamforelse(self.id)
        e = self.data["expect"]
        if e["gate"] != "OGAT":
            raise Bankfel(
                "%s fälls av %s, före ögat; den har ingen ögondom att jämföra mot"
                % (self.id, e["gate"]))
        try:
            rapport = K.las(ogontext)
        except K.Kontraktsfel as fel:
            res.fel.append((fel.grinddom, str(fel)))
            return res

        res.observerad_dom = rapport.dom[0]
        res.dom_stammer = rapport.dom[0] == e["verdict"]
        if e["reason_contains"]:
            res.orsak_stammer = e["reason_contains"] in rapport.dom[1]

        per_sektion = collections.defaultdict(list)
        for namn, rader in rapport.sektioner:
            per_sektion[namn].extend(rader)

        for krav in e["lines"]:
            monster = schema.mall_till_regex(krav["template"])
            if not any(monster.match(r) for r in per_sektion.get(krav["section"], [])):
                res.saknade_rader.append(krav)
        for forbud in e["forbidden_lines"]:
            monster = schema.mall_till_regex(forbud["template"])
            traff = [r for r in per_sektion.get(forbud["section"], []) if monster.match(r)]
            if traff:
                res.forbjudna_traffar.append({"krav": forbud, "rader": traff})
        return res

    def trasig_ogonrapport(self):
        """Den medvetet trasiga ögonrapporten, om varianten bär en sådan."""
        trasig = self.data.get("broken")
        if trasig and trasig["artefakt_typ"] == "oga":
            return trasig["artefakt"]
        return None


# Poängen "andel kärnutgångar vars spår stämmer" behöver en tolerans, för
# spåren jämförs på flanktider. 50 ms är valt som tio gånger det scanfönster
# vi räknar med i OpenPLC (5 ms) — talet är ett antagande tills fas 6 har mätt
# tur och retur över OPC UA, och det står som ett antagande i varje uppgift som
# lutar sig mot ett scanfönster.
SPAR_TOLERANS_S = 0.050


def _spar(rapport):
    """{signal: [(RISE|FALL, t), ...]} ur ögats EDGE-rader, i tidsordning."""
    ut = collections.defaultdict(list)
    for namn, rader in rapport.sektioner:
        if namn != "TIMING":
            continue
        for r in rader:
            if not r.startswith("EDGE "):
                continue
            _, signal, flank, tdel = r.split(" ")
            ut[signal].append((flank, float(tdel[2:-1])))
    for signal in ut:
        ut[signal].sort(key=lambda p: p[1])
    return ut


def spar_poang(referenstext, kandidattext, karnutgangar,
               tolerans_s=SPAR_TOLERANS_S):
    """Andel kärnutgångar vars flankspår stämmer med referensens.

    Facitformen som håller i praktiken är spårjämförelse per utgångsport, inte
    en enda dom. Ögondomen står kvar som den är; det här är ett mått bredvid
    den. Ett kandidatsvar som inte går att läsa som en ögonrapport ger noll —
    kompilerings-, deploy- och tidsöverdragsfel är inte delvis rätt.

    Returnerar (poang, per_utgang) där per_utgang är {signal: bool}.
    """
    if not karnutgangar:
        raise Bankfel("spårjämförelse utan namngivna kärnutgångar är odefinierad")
    try:
        ref = _spar(K.las(referenstext))
    except K.Kontraktsfel as fel:
        raise Bankfel("referensrapporten går inte att läsa: %s" % fel)
    try:
        kand = _spar(K.las(kandidattext))
    except K.Kontraktsfel:
        return 0.0, dict((s, False) for s in karnutgangar)

    per_utgang = {}
    for signal in karnutgangar:
        a, b = ref.get(signal, []), kand.get(signal, [])
        stammer = len(a) == len(b) and all(
            fa == fb and abs(ta - tb) <= tolerans_s
            for (fa, ta), (fb, tb) in zip(a, b))
        per_utgang[signal] = stammer
    poang = sum(1 for v in per_utgang.values() if v) / float(len(karnutgangar))
    return poang, per_utgang


class Bank(object):
    def __init__(self, uppgifter, katalogindex, felklasser):
        self.uppgifter = uppgifter
        self.katalogindex = katalogindex
        self.felklasser = felklasser

    def __len__(self):
        return len(self.uppgifter)

    def __iter__(self):
        return iter(self.uppgifter)

    def __getitem__(self, task_id):
        for u in self.uppgifter:
            if u.id == task_id:
                return u
        raise KeyError(task_id)

    # -- frågorna ----------------------------------------------------------

    def tacker(self, felklass):
        """Vilka uppgifter är byggda för att fånga den här klassen."""
        if felklass not in self.felklasser:
            raise Bankfel("okänd felklass %r; kända är %s"
                          % (felklass, ", ".join(sorted(self.felklasser))))
        return [u for u in self.uppgifter if felklass in u.klasser]

    def tackning(self):
        """{felklass: [task_id, ...]} för alla klasser i specen, även de tomma."""
        ut = dict((k, []) for k in self.felklasser)
        for u in self.uppgifter:
            for k in u.klasser:
                ut[k].append(u.id)
        return ut

    def otackta_klasser(self):
        return sorted((k for k, v in self.tackning().items() if not v),
                      key=lambda k: int(k[1:]))

    def klasser_utan_fallande_fixtur(self):
        """Klasser som ingen medvetet trasig variant fäller.

        Svagare än otäckt, men värt att mäta: en klass som bara har hela
        uppgifter har ingen fixtur som visar att grinden faktiskt fyrar
        (regel S2 i docs/spec/96_ingen_skuld.md).
        """
        med_fixtur = set()
        for u in self.uppgifter:
            if u.ar_variant:
                med_fixtur.update(u.klasser)
        return sorted((k for k in self.felklasser if k not in med_fixtur),
                      key=lambda k: int(k[1:]))

    def per_svarighet(self):
        r = collections.Counter(u.svarighet for u in self.uppgifter)
        return dict((n, r.get(n, 0)) for n in range(1, 6))

    def per_grupp(self):
        r = collections.Counter(u.grupp for u in self.uppgifter)
        return dict((g, r.get(g, 0)) for g in sorted(schema.GRUPPER))

    def per_bransch(self):
        r = collections.Counter(u.bransch for u in self.uppgifter)
        return dict((b, r.get(b, 0)) for b in schema.BRANSCHER)

    def per_stege(self):
        r = collections.Counter(u.data["stege"] for u in self.uppgifter)
        return dict((steg, r.get(steg, 0)) for steg, _d in schema.STEGE)

    def per_scenariotyp(self):
        r = collections.Counter(sc["typ"] for u in self.uppgifter
                                for sc in u.data["scenarios"])
        return dict((t, r.get(t, 0)) for t in schema.SCENARIOTYPER)

    def per_grind(self):
        r = collections.Counter(u.grind for u in self.uppgifter)
        return dict((g, r.get(g, 0)) for g in schema.GRINDAR)

    def varianter(self):
        return [u for u in self.uppgifter if u.ar_variant]


def las_katalogindex(sokvag=schema.KATALOGINDEXFIL):
    with open(sokvag, encoding="utf-8") as f:
        data = json.load(f)
    index = {}
    for p in data["poster"]:
        if p["uri"] in index:
            raise Bankfel("dubblerad URI i katalogindexet: %s" % p["uri"])
        index[p["uri"]] = p
    return index


def ladda(katalog=schema.UPPGIFTSKATALOG, strikt=True):
    """Läs in banken. Med strikt=True kastar en ogiltig uppgift.

    Fail-closed (I3): en bank där en post inte går att validera är inte en
    halvbra bank, den är en bank vi inte vet något om.
    """
    katalogindex = las_katalogindex()
    felklasser = schema.las_felklasser()
    uppgifter = []
    problem = []
    filer = sorted(f for f in os.listdir(katalog) if f.endswith(".json"))
    if not filer:
        raise Bankfel("noll uppgifter i %s" % katalog)
    sedda = set()
    for namn in filer:
        sokvag = os.path.join(katalog, namn)
        with open(sokvag, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except ValueError as fel:
                problem.append((namn, [("M1_MISSING_FIELD", "ogiltig JSON: %s" % fel)]))
                continue
        brister = schema.validera(data, filnamn=sokvag,
                                  katalogindex=katalogindex, felklasser=felklasser)
        if data.get("task_id") in sedda:
            brister.append(("M2_ID_MISMATCH", "dubblerat task_id"))
        sedda.add(data.get("task_id"))
        if brister:
            problem.append((namn, brister))
            continue
        uppgifter.append(Uppgift(data, sokvag))

    if problem and strikt:
        rader = []
        for namn, brister in problem:
            for kod, text in brister:
                rader.append("  %s: %s %s" % (namn, kod, text))
        raise Bankfel("banken har %d ogiltiga uppgifter:\n%s"
                      % (len(problem), "\n".join(rader)))

    bank = Bank(uppgifter, katalogindex, felklasser)
    bank.problem = problem
    return bank


def _skriv_rapport(bank, strom=sys.stdout):
    p = strom.write
    p("BANK %d uppgifter, varav %d medvetet trasiga varianter\n"
      % (len(bank), len(bank.varianter())))
    p("\nPer grupp\n")
    for g, n in bank.per_grupp().items():
        p("  %s %-16s %3d\n" % (g, schema.GRUPPER[g], n))
    p("\nPer svårighetsgrad (stämpel DEKLARERAD tills fas 9 mätt den)\n")
    for n, antal in bank.per_svarighet().items():
        p("  %d %s %d\n" % (n, "#" * antal, antal))
    p("\nPer bransch\n")
    for b, n in bank.per_bransch().items():
        p("  %-24s %3d\n" % (b, n))
    p("\nPer steg pa svarighetsstegen\n")
    for steg, n in bank.per_stege().items():
        p("  %-26s d%d  %3d\n" % (steg, schema.STEGE_SVARIGHET[steg], n))
    p("\nScenarier: %d totalt\n" % sum(bank.per_scenariotyp().values()))
    for t, n in bank.per_scenariotyp().items():
        p("  %-18s %3d\n" % (t, n))
    p("\nTäckning per felklass\n")
    tack = bank.tackning()
    utan_fixtur = set(bank.klasser_utan_fallande_fixtur())
    for k in sorted(tack, key=lambda x: int(x[1:])):
        markering = "  (ingen fällande fixtur)" if k in utan_fixtur else ""
        p("  %-4s %-14s %2d  %s%s\n"
          % (k, bank.felklasser[k]["namn"], len(tack[k]),
             ", ".join(tack[k]) or "TOM", markering))
    otackta = bank.otackta_klasser()
    p("\nOtäckta felklasser: %s\n" % (", ".join(otackta) if otackta else "inga"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Läs och fråga bänkbanken.")
    ap.add_argument("--klass", help="lista uppgifterna som täcker en felklass")
    ap.add_argument("--uppgift", help="skriv ut en uppgift som JSON")
    ap.add_argument("--slappt", action="store_true",
                    help="ladda även om poster är ogiltiga, och lista bristerna")
    args = ap.parse_args(argv)

    bank = ladda(strikt=not args.slappt)
    if args.slappt and bank.problem:
        for namn, brister in bank.problem:
            for kod, text in brister:
                print("OGILTIG %s: %s %s" % (namn, kod, text))
    if args.klass:
        for u in bank.tacker(args.klass):
            print("%s  d%d  %-22s %s" % (u.id, u.svarighet, u.bransch,
                                         u.data["title"]))
        return 0
    if args.uppgift:
        print(json.dumps(bank[args.uppgift].data, ensure_ascii=False, indent=2))
        return 0
    _skriv_rapport(bank)
    return 0


if __name__ == "__main__":
    sys.exit(main())
