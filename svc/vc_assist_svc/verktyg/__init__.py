# -*- coding: utf-8 -*-
"""Verktygsregistret: det sprakmodellen faktiskt anropar (fas 4-5).

Kalla: docs/spec/45_verktyg.md. Formen ar arvd ur Isaac Assist (20_arv.md):
en ren datalista i OpenAI:s function-calling-form, delad i tva register.

    schema.py        verktygsdefinitionen och valideringen av argument och svar
    register.py      DATA_HANDLERS och CODE_GEN_HANDLERS, och enda vagen in
    utforare.py      routingregeln effect -> exec / exec_queue (I12)
    formagegrind.py  vilka verktyg som far exponeras alls (36_versioner.md)
    kodmall.py       byggstenarna for den Python 2.7-kod som gar till bryggan
    bas.py           delade schemabitar och trosklar
    scen.py          domanen scene, 15 verktyg
    granssnitt.py    domanen composition, 6 verktyg

Domanmodulerna importeras HAR, sa att registren alltid ar fulla nar nagon
rort paketet. Python kor __init__ fore varje undermodul, sa aven
"import vc_assist_svc.verktyg.register" ger ett fullt register.

DATA_HANDLERS ar tomt an sa lange, och det ar ingen lucka utan foljden av
45_verktyg.md: "allt som ror scenen ar kodgenerering; allt som ror index,
katalog och kunskap ar data". Domanerna catalog, knowledge, plc och eyes
bar data-verktygen, och de byggs i egna celler. Vagen for dem ar fardig och
provad har (utforare.utfor grenar pa mode), sa den cell som bygger dem
behover bara anropa registrera().
"""
from __future__ import annotations

from .fel import (Argumentfel, Avstangt, OkantVerktyg, Schemafel, Svarsfel,
                  Verktygsfel)
from .formagegrind import KANDA_YTOR, Urval, urval_allt_pa, urval_ur_rapport
from .kodmall import MAX_POSTER
from .register import (CODE_GEN_HANDLERS, DATA_HANDLERS, REGISTER, domaner,
                       registrera)
from .schema import Verktyg, validera_argument, validera_resultat
from .utforare import OP_FOR_EFFECT, Resultat, Utforare, op_for_effect

from . import granssnitt  # noqa: F401,E402  - fyller registret vid import
from . import scen        # noqa: F401,E402  - fyller registret vid import

__all__ = [
    "Argumentfel", "Avstangt", "OkantVerktyg", "Schemafel", "Svarsfel",
    "Verktygsfel", "KANDA_YTOR", "Urval", "urval_allt_pa", "urval_ur_rapport",
    "MAX_POSTER", "CODE_GEN_HANDLERS", "DATA_HANDLERS", "REGISTER", "domaner",
    "registrera", "Verktyg", "validera_argument", "validera_resultat",
    "OP_FOR_EFFECT", "Resultat", "Utforare", "op_for_effect",
]
