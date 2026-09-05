#!/bin/bash
# VC Premium 4.10 ur TESTPREFIXET. Har far oprovad kod kora.
# Arbetsprefixet ~/.wine-vc ror vi aldrig med oprovat.
export PATH="/opt/wine-devel/bin:$PATH"
export WINEPREFIX="$HOME/.wine-vc-test"          # <-- enda skillnaden mot vc.sh
export WINEDLLOVERRIDES="mscoree=n;mshtml=d;winemenubuilder.exe=d;d3dx9_43=n;d3dcompiler_43=n;d3dx10_43=n;d3dx11_43=n"
export WINEDEBUG="${WINEDEBUG:--all}"

# SKARMEN. Skriptet arvde tidigare DISPLAY, och det var ett hal i sjalva
# skyddsracket: startades det fran en session med DISPLAY=:1 hamnade VC pa
# operatorens skarm mitt i hans arbete. Det hande 2026-09-05 09:51.
#
# Invarianten sager "satt DISPLAY explicit, arv den ALDRIG". Nu gor skriptet
# det. Vill man ha VC synlig maste man saga det med flit:
#
#     VC_TEST_DISPLAY=:1 ~/bin/vc-test.sh
#
if [ -n "$VC_TEST_DISPLAY" ]; then
  export DISPLAY="$VC_TEST_DISPLAY"
  echo "[SKARM] DISPLAY=$DISPLAY  (uttryckligt val via VC_TEST_DISPLAY)"
else
  export DISPLAY=":99"
  echo "[SKARM] DISPLAY=:99 (dold). Satt VC_TEST_DISPLAY for att se fonstret."
fi

# Den dolda skarmen maste finnas, annars startar VC inte alls och felet syns
# som nagot annat langre fram.
if [ "$DISPLAY" = ":99" ] && ! xdpyinfo -display :99 >/dev/null 2>&1; then
  echo "Ingen X-server pa :99. Starta en forst, till exempel:"
  echo "  Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp &"
  exit 1
fi

if ! ip -4 addr show ppp0 >/dev/null 2>&1; then
  echo "VPN nere, startar det forst..."
  "$HOME/bin/vpn-skolan.sh" start || { echo "VPN gick inte att starta - VC far ingen licens."; exit 1; }
fi

VCDIR="$WINEPREFIX/drive_c/Program Files/Visual Components"
EXE=$(find "$VCDIR/Visual Components Premium 4.10" -maxdepth 1 -name "VisualComponents.Engine.exe" 2>/dev/null | head -1)
[ -z "$EXE" ] && { echo "Hittar ingen VisualComponents.Engine.exe i TESTPREFIXET"; exit 1; }
echo "[TESTPREFIX] $WINEPREFIX"
cd "$(dirname "$EXE")" || exit 1
exec taskset -c 0-11 wine "$EXE" "$@"
