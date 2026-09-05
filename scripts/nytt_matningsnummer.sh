#!/bin/bash
# Reservera nästa lediga mätningsnummer, atomiskt.
#
# Varför det finns, mätt 2026-09-05: två sessioner tog M-124 inom 91 sekunder
# från start. "Kolla högsta numret först" är en regel man ska minnas, och med
# fem samtidiga skrivare är den en kapplöpning per konstruktion. Numret är
# mätningens enda identitet; två filer på samma nummer gör varje hänvisning
# tvetydig.
#
#   scripts/nytt_matningsnummer.sh <kort_namn> "<titel>"
#
# Tar samma lås som scripts/committa.sh, letar upp högsta numret, skapar filen
# med rätt rubrikform och ett tomt LIMITS-avsnitt, och skriver sökvägen.
set -uo pipefail
NAMN="${1:-}"; TITEL="${2:-}"
[ -z "$NAMN" ] && { echo "fel: kort_namn saknas (t.ex. openplc_som_tredje_motor)"; exit 2; }
[ -z "$TITEL" ] && { echo "fel: titel saknas"; exit 2; }
case "$NAMN" in *[!a-z0-9_]*) echo "fel: kort_namn får bara vara a-z, 0-9 och _"; exit 2;; esac
REPO="$(git rev-parse --show-toplevel)" || exit 2
KAT="$REPO/docs/matningar"
exec 9>"$REPO/.git/vcassist-commit.lock" || exit 2
flock -w 300 9 || { echo "fel: fick inte låset inom 300 s"; exit 3; }
HOGST=$(ls "$KAT"/M-*.md 2>/dev/null | sed -E 's|.*/M-0*([0-9]+)_.*|\1|' | sort -n | tail -1)
NASTA=$(( ${HOGST:-0} + 1 ))
FIL="$KAT/M-${NASTA}_${NAMN}.md"
[ -e "$FIL" ] && { echo "fel: $FIL finns redan"; exit 4; }
# Em-streck i rubriken, inte kolon: alla 108 filerna före den här skrev så, och
# mätningsindexet läser just den formen.
cat > "$FIL" <<EOF
# M-${NASTA} — ${TITEL}

**Datum:** $(date +%F)
**Rigg:**
**Prövar:**

## Resultat

## LIMITS

* Skriv vad mätningen INTE visar. En mätning utan det här avsnittet fälls av
  \`tests/enhet/test_skuld.py\`.
EOF
echo "$FIL"
