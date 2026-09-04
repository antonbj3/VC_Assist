# -*- coding: utf-8 -*-
"""Byggplanen: den ordnade grafen, provad mot det VERKLIGA verktygsregistret.

Har mots planeringslagret och verktygslagret, och mote nummer ett ar en
granskning. Fyra krav ur uppgiften ar MEKANISKA, inte overenskomna:

1. Ett steg vars verktyg inte finns i registret avvisas VID PLANERINGEN.
2. Ett steg vars argument inte haller verktygets schema avvisas VID
   PLANERINGEN.
3. Routingen read->exec / write->exec_queue ags av utforaren. Planen kan inte
   valja: den bar inget falt for det, och lasningen avvisar nycklarna (steg.py).
4. Valideringen ar verktygsregistrets EGEN (verktyg.validera_argument). Vi
   bygger ingen andra - tva valideringar av samma sak ar tva olika
   valideringar sa fort nagon andrar den ena.

Till det kommer guldstegens regel: en plan utan verifiering ar en KANDIDAT,
aldrig en leverans (docs/spec/50_grindar.md).
"""
from __future__ import annotations

from ..guldgrind import KANDIDAT
from ..verktyg import REGISTER, Argumentfel, validera_argument
from .fel import Specfel
from .graf import Uppgiftsgraf
from .predikat import granska_vag, typ_pa_vag
from .spec import DetaljeradSpec, SPECVERSION, granska_nycklar
from .steg import FORBJUDNA_STEGNYCKLAR, KONTROLLSVAR

# Vad planen tacker. Sluten lista: "scenbygge" ar det som gar att planera med
# de verktyg som finns (scene och composition, 21 st). Styrningen och ogats
# korning har egna faser (70_faser.md) och egna verktyg som annu inte finns i
# registret - en plan far inte lata som om den byggde dem.
OMFATTNINGAR = ("scenbygge",)

LINTKODER = {
    "P1_OKANT_VERKTYG": "steget anropar ett verktyg som inte finns i registret",
    "P2_ARGUMENTFEL": "argumenten haller inte verktygets schema",
    "P3_ROUTING_I_PLANEN": "planen forsoker valja exekveringslage",
    "P4_AVSTANGT_VERKTYG": "verktyget ar avslaget av formagegrinden",
    "P5_BINDNING": "bindningen gar inte att los ur det steg den pekar pa",
    "P6_INGEN_VERIFIERING": "planen bar inget som ska bevisas",
    "P7_OBESVARAD_FRAGA": "en blockerande fraga ar obesvarad",
    "P8_TOM_PLAN": "planen har inga steg",
    "P9_PREDIKATVAG": "ett predikat laser en vag svaret aldrig bar",
    "P10_INGEN_OGONKONTROLL": "planen bar ett verifieringskrav men inget steg "
                              "som provar det",
}


class Byggplan(object):
    """Specen som en ordnad graf av steg."""

    __slots__ = ("id", "spec", "graf", "omfattning")

    def __init__(self, id, spec, graf, omfattning="scenbygge"):
        self.id = id
        self.spec = spec
        self.graf = graf
        self.omfattning = omfattning
        problem = []
        if not isinstance(id, str) or not id.strip():
            problem.append("planen saknar id")
        if not isinstance(spec, DetaljeradSpec):
            problem.append("planen bar ingen detaljerad spec")
        if not isinstance(graf, Uppgiftsgraf):
            problem.append("planen bar ingen uppgiftsgraf")
        if omfattning not in OMFATTNINGAR:
            problem.append("okand omfattning %r; kanda ar %s"
                           % (omfattning, ", ".join(OMFATTNINGAR)))
        if problem:
            raise Specfel("byggplanen %r" % (id,), problem)

    def __repr__(self):
        return "Byggplan(%s, %d steg, %s)" % (self.id, len(self.graf),
                                              self.omfattning)

    def __len__(self):
        return len(self.graf)

    @property
    def verifiering(self):
        """Det som ska bevisas. Ags av specen; planen bar ingen egen kopia."""
        return self.spec.verifiering

    def ordning(self):
        return self.graf.ordning()

    def ogonkontroller(self):
        return [s for s in self.graf
                if s.sort == "kontroll" and s.kontroll.sort == "oga"]

    # -- granskningen ----------------------------------------------------

    def granska(self, register=None, urval=None):
        """[(lintkod, text)]. Tom lista = planen gar att kora.

        Kastar aldrig. En granskning som kraschar pa en trasig plan sager
        ingenting om vad som var trasigt (S10 i 96_ingen_skuld.md).
        """
        register = REGISTER if register is None else register
        ut = list(self.graf.problem())
        if not len(self.graf):
            ut.append(("P8_TOM_PLAN", "planen har inga steg"))

        for steg in self.graf:
            ut += self._granska_steg(steg, register, urval)

        if self.verifiering is None or not self.verifiering.uttalad():
            ut.append(("P6_INGEN_VERIFIERING",
                       "planen sager inte vad som ska bevisas; utan det ar den "
                       "en %s, aldrig en leverans" % KANDIDAT))
        elif not self.ogonkontroller():
            ut.append(("P10_INGEN_OGONKONTROLL",
                       "planen bar %d verifieringskrav men inget kontrollsteg "
                       "som provar dem mot ogats rapport"
                       % len(self.verifiering.rader)))

        for fraga in self.spec.blockerande_fragor():
            ut.append(("P7_OBESVARAD_FRAGA",
                       "%s: %s" % (fraga.id, fraga.vad)))
        return ut

    def _granska_steg(self, steg, register, urval):
        ut = []
        smitare = sorted(set(steg.argument) & set(FORBJUDNA_STEGNYCKLAR))
        for n in smitare:
            ut.append(("P3_ROUTING_I_PLANEN",
                       "steget %s bar argumentet %r; exekveringslaget ags av "
                       "utforaren (I12)" % (steg.id, n)))
        if steg.sort == "verktyg":
            if steg.verktyg not in register:
                ut.append(("P1_OKANT_VERKTYG",
                           "steget %s anropar %r; %d verktyg finns i registret"
                           % (steg.id, steg.verktyg, len(register))))
                return ut
            verktyg = register[steg.verktyg]
            if urval is not None:
                skal = urval.skal(steg.verktyg)
                if skal is not None:
                    ut.append(("P4_AVSTANGT_VERKTYG",
                               "steget %s anropar %s, som ar avstangt: %s"
                               % (steg.id, steg.verktyg, skal)))
            try:
                # Registrets EGEN validering. Bindningar provas med sina
                # vittnesvarden: ratt typ, okant innehall.
                validera_argument(verktyg, steg.argument_med_vittnen())
            except Argumentfel as fel:
                for p in fel.problem:
                    ut.append(("P2_ARGUMENTFEL", "steget %s: %s" % (steg.id, p)))
        ut += self._granska_bindningar(steg, register)
        ut += self._granska_predikatvagar(steg, register)
        return ut

    def _svarsschema(self, steg_id, register):
        """(schema, fel). Formen pa det steget svarar med."""
        if steg_id not in self.graf:
            return None, "steget %s finns inte i planen" % steg_id
        kalla = self.graf.steg(steg_id)
        if kalla.sort == "kontroll":
            return KONTROLLSVAR[kalla.kontroll.sort], None
        if kalla.verktyg not in register:
            return None, ("steget %s anropar %r som inte finns i registret"
                          % (steg_id, kalla.verktyg))
        return register[kalla.verktyg].returns, None

    def _granska_bindningar(self, steg, register):
        ut = []
        for namn, bindning in steg.bindningar():
            if bindning.fran_steg not in self.graf:
                ut.append(("P5_BINDNING",
                           "steget %s binder %s till steget %s som inte finns"
                           % (steg.id, namn, bindning.fran_steg)))
                continue
            kalla = self.graf.steg(bindning.fran_steg)
            if bindning.sort == "namngiven":
                if (kalla.sort != "kontroll"
                        or kalla.kontroll.sort != "bindning"):
                    ut.append(("P5_BINDNING",
                               "steget %s binder %s till %s, som inte ar en "
                               "bindningskontroll" % (steg.id, namn, kalla.id)))
                    continue
                deklarerade = dict(kalla.kontroll.ger)
                if bindning.namn not in deklarerade:
                    ut.append(("P5_BINDNING",
                               "steget %s binder %s till namnet %r som %s inte "
                               "ger; den ger %s"
                               % (steg.id, namn, bindning.namn, kalla.id,
                                  ", ".join(sorted(deklarerade)) or "inget")))
                elif deklarerade[bindning.namn] != bindning.typ:
                    ut.append(("P5_BINDNING",
                               "steget %s vantar %s som %s, men %s ger den som %s"
                               % (steg.id, bindning.namn, bindning.typ,
                                  kalla.id, deklarerade[bindning.namn])))
                continue
            schema, fel = self._svarsschema(bindning.fran_steg, register)
            if fel:
                ut.append(("P5_BINDNING", "steget %s: %s" % (steg.id, fel)))
                continue
            vagfel = granska_vag(schema, bindning.vag)
            if vagfel:
                ut.append(("P5_BINDNING", "steget %s: %s" % (steg.id, vagfel)))
                continue
            typ = typ_pa_vag(schema, bindning.vag)
            if typ != bindning.typ:
                ut.append(("P5_BINDNING",
                           "steget %s laser %s.%s som %s, men svaret bar %s dar"
                           % (steg.id, bindning.fran_steg, bindning.vag,
                              bindning.typ, typ)))
        return ut

    def _granska_predikatvagar(self, steg, register):
        ut = []
        villkor = []
        if steg.forvillkor is not None:
            villkor.append(steg.forvillkor)
        if (steg.sort == "kontroll" and steg.kontroll.sort == "villkor"):
            villkor.append(steg.kontroll.villkor)
        for v in villkor:
            for p in v.predikat:
                if p.sort != "resultat":
                    continue
                schema, fel = self._svarsschema(p.steg, register)
                if fel:
                    ut.append(("P9_PREDIKATVAG", "steget %s: %s" % (steg.id, fel)))
                    continue
                vagfel = granska_vag(schema, p.vag)
                if vagfel:
                    ut.append(("P9_PREDIKATVAG",
                               "steget %s: %s" % (steg.id, vagfel)))
        return ut

    # -- domen over planen ------------------------------------------------

    def leverabel(self, register=None, urval=None):
        """(ja, skal). En plan ar leverabel nar den gar att kora OCH bar sitt
        bevis. Allt annat ar en kandidat."""
        problem = self.granska(register, urval)
        if problem:
            return False, ("%d brister, bland dem: %s"
                           % (len(problem),
                              "; ".join("%s %s" % p for p in problem[:3])))
        return True, "planen haller registret och bar %d verifieringskrav" % (
            len(self.verifiering.rader))

    def sammanfattning(self, register=None):
        """Talen en matning vill ha, i en ordbok."""
        register = REGISTER if register is None else register
        verktygssteg = [s for s in self.graf if s.sort == "verktyg"]
        skrivande = [s for s in verktygssteg
                     if s.verktyg in register
                     and register[s.verktyg].effect == "write"]
        return {
            "plan": self.id,
            "steg": len(self.graf),
            "verktygssteg": len(verktygssteg),
            "kontrollsteg": len(self.graf) - len(verktygssteg),
            "skrivande_steg": len(skrivande),
            "bredd": self.graf.bredd(),
            "antaganden": len(self.spec.antaganden),
            "fragor": len(self.spec.fragor),
            "oppna_fragor": len(self.spec.oppna_fragor()),
            "blockerande_fragor": len(self.spec.blockerande_fragor()),
            "verifieringskrav": len(self.verifiering.rader) if self.verifiering else 0,
            "uppskjutna_krav": (len(self.verifiering.uppskjutna)
                                if self.verifiering else 0),
        }

    # -- serialisering ----------------------------------------------------

    def till_json(self):
        return {"v": SPECVERSION, "niva": "byggplan", "id": self.id,
                "omfattning": self.omfattning,
                "spec": self.spec.till_json(),
                "graf": self.graf.till_json()}

    @classmethod
    def fran_json(cls, data):
        granska_nycklar(data, ("v", "niva", "id", "omfattning", "spec", "graf"),
                 "byggplan")
        if data["v"] != SPECVERSION:
            raise Specfel("byggplan", ["formatversion %r, lasaren kan %d"
                                       % (data["v"], SPECVERSION)])
        if data["niva"] != "byggplan":
            raise Specfel("byggplan", ["niva %r, forvantade byggplan"
                                       % (data["niva"],)])
        return cls(data["id"], DetaljeradSpec.fran_json(data["spec"]),
                   Uppgiftsgraf.fran_json(data["graf"]), data["omfattning"])
