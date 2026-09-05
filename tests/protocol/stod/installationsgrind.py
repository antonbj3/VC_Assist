# -*- coding: utf-8 -*-
"""Grinden fore varje L3-korning: kor VC den kod som ligger i repot?

VARFOR DEN FINNS. Under fas 15 matte jag hopfogningen mot en korande VC och
fick tillbaka en serie helt utan `plc_hopfogning_s`. Talet fanns i repots
`pump.py` sedan M-65. Det var installationen i VC:s anvandarmapp som lag kvar
fran en tidigare timme: fem av elva filer var aldre an repot.

Det ar den farligaste sortens fel. Ingenting kraschade, ingen rad saknades i
protokollet, och matningen hade fatt ett tal - talet for den gamla koden. En
L3-korning som inte forst provar VAD den mater kan alltsa rapportera grona
siffror om kod som inte langre finns.

`install/installera.py verifiera` kan redan svara pa fragan; den var bara
aldrig stalld fore en matning. Har ar den stalld.
"""
import os
import subprocess
import sys

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def kontrollera(mal=None, skriv=None):
    """(ok, rader). ok=False betyder att VC INTE kor repots kod.

    Kastar inte: den som anropar avgor om korningen ska stoppas eller bara
    marka sin utdata. Men svaret ar aldrig 'vet inte' - en installation som
    inte gar att verifiera ar inte samma sak som en som stammer.

    Utan `mal` letar `installera verifiera` sjalv upp installationen, samma
    upptackt som installationen gick genom.
    """
    skriv = skriv or (lambda rad: None)
    argv = [sys.executable, "-m", "install.installera", "verifiera"]
    if mal:
        argv += ["--mal", mal]
    ut = subprocess.Popen(
        argv, cwd=_ROT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=dict(os.environ, PYTHONPATH=_ROT))
    text = ut.communicate()[0].decode("utf-8", "replace")
    rader = [r.strip() for r in text.splitlines() if r.strip()]
    for r in rader:
        skriv("  %s" % r)
    ok = any(r.startswith("samma som repots kalla: ja") for r in rader)
    if not rader:
        skriv("  INGEN INSTALLATION HITTAD - korningen mater okand kod")
    if not ok:
        skriv("  KORNINGEN MATER INTE REPOTS KOD. Kor:")
        skriv("    PYTHONPATH=. python3 -m install.installera installera")
        skriv("    ~/bin/vc-stoppa.sh && ~/bin/vc-test-headless.sh &")
    return ok, rader
