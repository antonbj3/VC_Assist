# Rådata som räddats ur `/tmp`

Filerna här är utdata och körkod från mätningar som gjordes i en sessions
scratchpad under `/tmp` och **aldrig hann in i repot**. Disken var på 96 % samma
morgon; en mätning som bara finns i `/tmp` finns inte.

* `m122_*` — mutationssvepet 2026-09-05: 808 skador ur 26 referenser, 717
  fångade, **91 överlevde**, varav 67 osynliga även under störning.
  `m122_resultat.json` är hela utfallet per skada. `m122.json` är körningens
  fulla utdata (uppgifter + fällplatser), `m122_repo.txt` den korta
  sammanfattningen — båda låg kvar i `/tmp` och är räddade hit av kö C (C7).
* `mut.txt`, `mut.json` — den tidigare, mindre körningen.

Mätningsdokumentet är skrivet (`M-122_mutationsskikten_omkorda.md`) och körkoden
ligger i `tests/protocol/kor_m122_mutationsskikt.py`. Filerna här är svepets
rådata — läs dem som sådana.
