#!/bin/bash
# Ett commit-lås för ett repo som fem sessioner delar.
#
# Varför det finns: `git commit` tar `.git/index.lock`. Kör två sessioner
# samtidigt förlorar den ena sina indexrader, och `git commit -- <sökväg>` i en
# delad worktree har dessutom setts tappa rader som redan var stagade. Mätt,
# inte befarat. Låset gör samtidigheten ofarlig utan att någon behöver minnas
# en regel.
#
#   scripts/committa.sh "<meddelande>" <sökväg> [<sökväg> ...]
#
# Gör exakt detta, och inget annat:
#   1. tar ett exklusivt lås (väntar upp till 300 s)
#   2. `git add --` på ENBART de sökvägar du namnger — aldrig `-A`, aldrig glob
#   3. visar vad som faktiskt blev stagat
#   4. `git commit --` på samma sökvägar
#   5. kontrollerar efteråt att inga av dina rader blev kvar ostagade
set -uo pipefail
MED="${1:-}"; shift || true
[ -z "$MED" ] && { echo "fel: meddelande saknas"; exit 2; }
[ "$#" -eq 0 ] && { echo "fel: namnge minst en sökväg — aldrig -A"; exit 2; }
REPO="$(git rev-parse --show-toplevel)" || exit 2
LAS="$REPO/.git/vcassist-commit.lock"
exec 9>"$LAS" || exit 2
if ! flock -w 300 9; then echo "fel: fick inte låset inom 300 s"; exit 3; fi
# Staga bara de sökvägar som faktiskt finns. En `git mv` har redan tagit bort
# källan ur BÅDE arbetsträdet och indexet, så `git add` på den faller med
# "did not match any files" och skulle stoppa hela committen mitt i en flytt.
# Den gamla sökvägen ska ändå med i `git commit`, annars blir raderingen kvar.
# -A med uttryckliga sökvägar är ofarligt; farligt är bara -A UTAN sökvägar,
# och skriptet vägrar redan köra utan dem.
# Katalogargument vagras. En katalog stagar ALLT i den, inklusive det en
# annan session har osparat dar just nu - och det hande: en annan agents
# arbete i datablad.py foljde med i en commit vars meddelande handlade om
# nagot helt annat. Namnge filer, sa ar du ansvarig for exakt det du namner.
for v in "$@"; do
  if [ -d "$REPO/$v" ] || [ -d "$v" ]; then
    echo "fel: $v ar en katalog. Namnge filerna."
    echo "     En katalog stagar aven det andra sessioner har osparat dar."
    exit 7
  fi
done
FINNS=()
for v in "$@"; do
  if [ -e "$REPO/$v" ] || [ -e "$v" ]; then FINNS+=("$v"); fi
done
if [ "${#FINNS[@]}" -gt 0 ]; then
  git -C "$REPO" add -A -- "${FINNS[@]}" || exit 4
fi
echo "--- stagat ---"
git -C "$REPO" diff --cached --name-status -- "$@"
if [ -z "$(git -C "$REPO" diff --cached --name-only -- "$@")" ]; then
  echo "inget att committa i de sökvägarna"; exit 0
fi
git -C "$REPO" commit -m "$MED" -- "$@" || exit 5
KVAR="$(git -C "$REPO" diff --name-only -- "$@")"
if [ -n "$KVAR" ]; then
  echo "VARNING: dessa rader blev INTE med i committen:"; echo "$KVAR"; exit 6
fi
echo "klart: $(git -C "$REPO" rev-parse --short HEAD)"
