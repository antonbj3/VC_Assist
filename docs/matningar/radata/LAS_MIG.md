# Rådata som räddats ur `/tmp`

Filerna här är utdata och körkod från mätningar som gjordes i en sessions
scratchpad under `/tmp` och **aldrig hann in i repot**. Disken var på 96 % samma
morgon; en mätning som bara finns i `/tmp` finns inte.

* `m122_*` — mutationssvepet 2026-09-05: 808 skador ur 26 referenser, 717
  fångade, **91 överlevde**, varav 67 osynliga även under störning.
  `m122_resultat.json` är hela utfallet per skada.
* `mut.txt`, `mut.json` — den tidigare, mindre körningen.

**Mätningsdokumenten är inte skrivna.** Kö C (`docs/uppdrag/KO_C_de_91_overlevande.md`)
skriver dem, och flyttar då körkoden till `tests/protocol/` där den hör hemma.
Tills dess är de här filerna rådata utan tolkning — läs dem som sådana.
