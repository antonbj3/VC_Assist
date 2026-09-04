# -*- coding: utf-8 -*-
"""Baslinjen: en regelbaserad ST-generator utan språkmodell, och dess yta.

Fas 11 i `docs/spec/70_faser.md`. Skälet står i `R-01`: ingen har publicerat
vår loop, ingen leverantör publicerar ett korrekthetstal, och varje akademiskt
tal är kompileringsgrad på en annan uppgiftsmängd. Fas 9:s tal får därför
aldrig publiceras ensamt — det rapporteras som par, vårt mot baslinjens, över
samma bank och med **samma domare**.

`BaslinjeModell` här nere är den yta som gör paret möjligt: den talar
`harness.modell.Modell`, precis som en språkmodellsadapter, så att
`plc.reparation.Reparationsslinga` kan köra båda sidor genom exakt samma
slinga och exakt samma grindar. Slingan vet aldrig vilken sida den kör.

## Reparationen är också klassisk

Baslinjen är deterministisk: samma spec ger samma kropp. En deterministisk
generator kan inte reparera genom att försöka igen — andra varvet ger samma
kropp och slingan låser (`UTFALL_LAST`). Den enda ärliga klassiska reparationen
är att **läsa grindens egen kodmärkning och ändra generatorns inställning**,
precis som en lintdriven fixare gör. Tabellen `ATGARDER` är den mekanismen, och
den är kort med flit: den kan bara det den bevisligen kan.

Koder som ingen regel täcker samlas i `BaslinjeModell.utan_regel`. Det är den
mest användbara listan i hela fas 11: den säger var en klassisk metod slutar,
och alltså var en språkmodell måste vara bättre för att vara värd sin kostnad.

beskriver: svc/vc_assist_svc/plc/baslinje/__init__.py
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from ..reparation import klasser_ur, koder_ur
from ...harness.modell import Meddelande, Modell, Modellsvar
from .generator import (Baslinje, Baslinjefel, NIVAER, NIVA_MAGER, NIVA_PROSA,
                        NIVA_SPEC, Rapport, Resultat, Spec)
from . import morfologi, packml, sprak

__all__ = [
    "Baslinje", "Baslinjefel", "BaslinjeModell", "NIVAER", "NIVA_MAGER",
    "NIVA_PROSA", "NIVA_SPEC", "Rapport", "Resultat", "Spec",
    "ATGARDER", "morfologi", "packml", "sprak",
]


# Grindkod -> den inställning på generatorn som åtgärdar den.
#
# Varje post är en regel någon kan följa utan att förstå uppgiften, och det är
# hela definitionen av en klassisk reparation. Att posterna är just två är
# ingen förenkling utan mätningen: grind 2 och 3 fäller på FORM, och form går
# att laga med en regel. Spårfacit fäller på BETEENDE I TIDEN, och en dom som
# säger "ST050_CNV_RUN var 1 vid 1800 ms" pekar inte ut någon rad att ändra.
ATGARDER: Dict[str, str] = {
    "ORORD_SIGNAL": "las_obundna",
    "ODRIVEN_UTGANG": "driv_obundna",
}


class BaslinjeModell(Modell):
    """Baslinjen med språkmodellens yta mot reparationsslingan.

    Den har ingen kanal ut och kan inte få en: den bär en `Spec` och en
    generator. `uppgiftstext` från slingan används inte som indata — baslinjen
    fick sin uppgift som strukturerad spec när den skapades, och det är en
    fördel mot modellen som står utskriven i M-62.
    """

    leverantor = "baslinje"

    def __init__(self, spec: Spec, niva: str = NIVA_SPEC,
                 driv_obundna: bool = False, las_obundna: bool = False):
        self.namn = "baslinje-%s" % niva
        self.spec = spec
        self.niva = niva
        self._val = {"driv_obundna": driv_obundna, "las_obundna": las_obundna}
        self.utan_regel: List[str] = []
        self.atgardade: List[str] = []
        self.rapporter: List[Rapport] = []
        self.varv = 0

    def generator(self) -> Baslinje:
        return Baslinje(niva=self.niva, **self._val)

    def generera(self) -> Resultat:
        resultat = self.generator().generera(self.spec)
        self.rapporter.append(resultat.rapport)
        return resultat

    def svara(self, systemprompt: str, meddelanden: Sequence[Meddelande],
              verktyg: Sequence[Any]) -> Modellsvar:
        self.varv += 1
        domar = [m.text for m in meddelanden if m.roll == "grind"]
        if domar:
            self._atgarda(domar[-1])
        return Modellsvar(text=self.generera().kropp,
                          leverantor=self.leverantor)

    # -- reparationen ----------------------------------------------------

    def _atgarda(self, domtext: str) -> None:
        """Slå upp grindens EGNA koder i åtgärdstabellen. Ingen omtolkning.

        Koderna läses med `reparation.koder_ur`, alltså med samma läsare som
        slingan själv använder på samma text. Att härleda felet ur koden på
        nytt vore att implementera om måttet (I1).
        """
        for kod in koder_ur(domtext):
            grund = kod.split(":", 1)[0]
            installning = ATGARDER.get(grund)
            if installning is None:
                if kod not in self.utan_regel:
                    self.utan_regel.append(kod)
                continue
            if not self._val[installning]:
                self._val[installning] = True
                self.atgardade.append(kod)

    @property
    def kan_mer(self) -> bool:
        """Sant så länge någon åtgärd återstår att prova."""
        return not all(self._val.values())
