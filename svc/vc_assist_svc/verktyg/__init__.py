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
    simulering.py    domanen simulation, 11 verktyg (tidsaxeln)
    matning.py       domanen measure, 7 verktyg (grindarnas ravara)
    robotik.py       domanen robot, 24 verktyg (vcExecutor-slakten)

Domanmodulerna importeras HAR, sa att registren alltid ar fulla nar nagon
rort paketet. Python kor __init__ fore varje undermodul, sa aven
"import vc_assist_svc.verktyg.register" ger ett fullt register.

Uppdelningen foljer 45_verktyg.md: allt som ror SCENEN ar kodgenerering och gar
till bryggan, allt som ror index, katalog och kunskap ar DATA och kors i
tjansten. Domanerna catalog, knowledge och eyes bar data-verktygen.
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

# Domanmodulerna importeras HAR sa registret alltid ar fullt. Ordningen ar
# alfabetisk och utan betydelse - registrera() avvisar dubbletter.
from . import granssnitt    # noqa: F401,E402
from . import katalog       # noqa: F401,E402
from . import kunskap       # noqa: F401,E402
from . import matning       # noqa: F401,E402
from . import ogonverktyg   # noqa: F401,E402
from . import robotik      # noqa: F401,E402
from . import scen          # noqa: F401,E402
from . import simulering    # noqa: F401,E402
from . import signaler      # noqa: F401,E402
from . import transport     # noqa: F401,E402

__all__ = [
    "Argumentfel", "Avstangt", "OkantVerktyg", "Schemafel", "Svarsfel",
    "Verktygsfel", "KANDA_YTOR", "Urval", "urval_allt_pa", "urval_ur_rapport",
    "MAX_POSTER", "CODE_GEN_HANDLERS", "DATA_HANDLERS", "REGISTER", "domaner",
    "registrera", "Verktyg", "validera_argument", "validera_resultat",
    "OP_FOR_EFFECT", "Resultat", "Utforare", "op_for_effect",
]
