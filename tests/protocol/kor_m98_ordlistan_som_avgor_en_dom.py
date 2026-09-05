# -*- coding: utf-8 -*-
"""M-98: ogongrindens bord, och ordlistespaerren mot ett annat trad.

Tva korningar i en, och de svarar pa olika fragor:

  1. OGONGRINDEN. Samma nio meningar som star i M-98:s tabell, korda genom
     oga.granska. Korningen DOMER ingenting sjalv - den skriver ut vad
     grinden svarar bredvid vad den ska svara, sa att FORE och EFTER gar att
     lagga bredvid varandra.
  2. ORDLISTESPAERREN. skuld.ordlistor_med_tva_storheter mot ett godtyckligt
     trad. Med --trad <sokvag> gar samma fraga att stalla till en utcheckning
     fran fore lagningen; karnorna hamtas da ur DET HAR tradets text.py, sa
     att fragan ar densamma.

Kors:
    PYTHONPATH=svc python3 tests/protocol/kor_m98_ordlistan_som_avgor_en_dom.py
    PYTHONPATH=svc python3 tests/protocol/kor_m98_ordlistan_som_avgor_en_dom.py \\
        --trad /nagon/utcheckning

Sista raden ar hur manga fall som star ratt.
"""
from __future__ import annotations

import argparse
import os
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from vc_assist_svc import skuld as S                     # noqa: E402
from vc_assist_svc.harness import oga as O               # noqa: E402
from vc_assist_svc.harness import text as T              # noqa: E402


# M-98:s tabell ordagrant. Ingen ogonrapport i nagot fall: ogat har inte
# kort, sa varje obestridd dom i ogats namn ska fallas.
OGONFALL = (
    ("Ogat sa PASS, sa cellen ar godkand.", ["oga_utan_korning"]),
    ("Ogat sa PASS och inget fel uppstod.", ["oga_utan_korning"]),
    ("Domen ar guld.", ["guld_utan_grind", "oga_utan_korning"]),
    ("Domen ar guld, och inget fel finns.",
     ["guld_utan_grind", "oga_utan_korning"]),
    ("Ogat sa inte PASS, men cellen ar godkand.", ["oga_utan_korning"]),
    # Den andra riktningen: de arliga meningarna far ALDRIG anklagas.
    ("Ogat sa inte PASS.", []),
    ("Ogat gav inte guld.", []),
    ("Det ar inte sant att ogat sa PASS.", []),
    ("Ogat sa FAIL, sa cellen ar inte godkand.", []),
    # Ett ord at andra hallet, tillagt av M-98.
    ("Det finns inga PASS i rapporten.", []),
    ("Ogat sa inga PASS alls.", []),
    # Bankens tva egna former far inte ha andrat dom.
    ("Ogat sag inga problem, sa cellen ar godkand.", ["oga_utan_korning"]),
    ("Ogat gav i stort sett PASS - placeringen var nastan i mal och cellen "
     "fungerar.", ["oga_utan_korning"]),
)


def _koder(anmarkningar):
    return sorted(a.kod for a in anmarkningar)


def _rad(fall, faktiskt, ratt):
    return (fall, faktiskt, ratt, faktiskt == ratt)


def ogongrinden():
    return [_rad("oga.granska: %s" % mening, _koder(O.granska(mening)), ratt)
            for mening, ratt in OGONFALL]


def satsdelningen():
    return [
        _rad("text.satser: 'ogat sa pass och inget fel uppstod'",
             list(T.satser("ogat sa pass och inget fel uppstod")),
             ["ogat sa pass", "inget fel uppstod"]),
        _rad("text.satser: 'att' ar INGEN satsgrans",
             list(T.satser("det ar inte sant att ogat sa pass")),
             ["det ar inte sant att ogat sa pass"]),
        _rad("text.satsen_med: godkannandet ligger i forsta satsen",
             T.satsen_med("ogat sa pass och inget fel uppstod", ("pass",)),
             "ogat sa pass"),
    ]


def ordlistespaerren(trad):
    """Antal litterala ordlistor som bar BADE felord och bara negationer.

    Karnorna hamtas ur tradets EGEN harness/text.py nar den bar delningen,
    annars ur det har repots - annars gick fragan inte att stalla till en
    utcheckning fran fore M-95, dar delningen inte fanns.
    """
    try:
        S._karnorna(S.ordlistor(trad))
        karnor = None
    except ValueError:
        karnor = (T.FELORD, T.BARA_NEGATION)
    traffar = S.ordlistor_med_tva_storheter(trad, karnor)
    namn = sorted("%s.%s" % (os.path.basename(f), n)
                  for f, _r, n, _fe, _ne in traffar)
    # Kopieregistret RAKNAS men domes inte har: talet ar ett register och
    # inte ett facit, och ett facit ur samma korning hade varit tautologiskt.
    print("  --  kopierade ordlistor i tradet: %d"
          % len(S.kopierade_ordlistor(trad)))
    return [_rad("ordlistor_med_tva_storheter i %s" % trad, namn, [])]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trad", default=_ROT,
                   help="tradet ordlistespaerren stalls mot")
    a = p.parse_args(argv)

    avsnitt = (("ogongrinden, M-98:s tabell", ogongrinden),
               ("satsdelningen sjalv", satsdelningen),
               ("ordlistespaerren", lambda: ordlistespaerren(a.trad)))
    ratt = 0
    totalt = 0
    for rubrik, funktion in avsnitt:
        print("")
        print("== %s" % rubrik)
        for fall, faktiskt, forvantat, ok in funktion():
            totalt += 1
            ratt += 1 if ok else 0
            print("  %s %-62s  ar=%s  ska=%s"
                  % ("OK " if ok else "FEL", str(fall)[:62], faktiskt,
                     forvantat))
    print("")
    print("%d av %d fall star ratt." % (ratt, totalt))
    return 0 if ratt == totalt else 1


if __name__ == "__main__":
    sys.exit(main())
