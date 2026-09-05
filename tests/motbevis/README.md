# tests/motbevis — prov som SKA vara röda

Varje test här är ett motbevis: det fäller på ett hål som sviten i
`tests/enhet/` inte ser. Röd är rätt utfall. Blir ett test här grönt är hålet
lagat, och testet flyttas till `tests/enhet/` som regressionsprov.

Körs separat, så den vanliga sviten står kvar grön:

    python3 -m pytest tests/motbevis -q

Full genomgång av de nio första: `docs/motbevis_2026_09_04.md`.

Senare tillskott bär sin genomgång i den mätning som byggde dem:

* `test_tillverkardatablad_motbevis.py` — 7 röda, se `docs/matningar/M-107_tillverkarens_datablad.md`.
