#!/usr/bin/env python3
"""Sla upp namn i Visual Components 4.10:s API - modellens enda vag in i repot.

Finns for M-84: matningen som jamfor en modell MED uppslag mot en UTAN (M-82).
Verktyget maste darfor svara pa API-fragor och ingenting annat - en modell som
kan lasa repot ser facit, och da mater jamforelsen ingenting.

Anvands sa har:

    python3 slaupp.py namn <NAMN>        exakt uppslag, t.ex. vcApplication.load
    python3 slaupp.py sok <ORD>          fritextsokning i namn och beskrivningar
    python3 slaupp.py yta <TYP>          alla medlemmar pa en typ

Svaret kommer ur den officiella API-dokumentationen for VC 4.10: 3444 symboler
med signatur, returtyp och beskrivning.

Det har verktyget svarar BARA pa API-fragor. Det ger dig ingenting annat.
"""
import json
import subprocess
import sys

# Repots rot, harledd ur filens egen plats. Den hardkodade sokvagen som stod
# har forst hade bundit verktyget till en maskin.
import os
# TRE niva upp: filen ligger i tests/protocol/stod/. Tva niva gav tests/, och
# felet syntes forst som "No module named vc_assist_svc" i underprocessen -
# alltsa langt fran orsaken.
REPO = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", ".."))

# OBS: strangen formateras med %% REPO nedan, sa VARJE procenttecken har inne
# maste vara dubblat. Ett ensamt %%d ater upp formateringen och ger ett fel som
# syns langt fran orsaken.
KOD = '''
import sys, json
sys.path.insert(0, %r + "/svc")
import vc_assist_svc.verktyg as V
sort, arg = sys.argv[1], sys.argv[2]
if sort == "namn":
    r = V.DATA_HANDLERS["lookup_api"]({"name": arg})
elif sort == "sok":
    r = V.DATA_HANDLERS["search_api"]({"query": arg, "limit": 12})
else:
    r = V.DATA_HANDLERS["type_surface"]({"type_name": arg})
# Kapa pa ANTAL TRAFFAR, inte pa tecken. Att skiva strangen gav ogiltig JSON
# mitt i en struktur - lasbart for ett oga, oparsbart for allt annat, och det
# ar precis den sortens halvhet ett verktyg inte far ha.
for nyckel in ("symbols", "traffar", "medlemmar", "members"):
    if isinstance(r.get(nyckel), list) and len(r[nyckel]) > 12:
        r["kapat"] = "%%d av %%d visas" %% (12, len(r[nyckel]))
        r[nyckel] = r[nyckel][:12]
for post in (r.get("symbols") or []) + (r.get("traffar") or []):
    if isinstance(post, dict) and isinstance(post.get("description"), str):
        d = " ".join(post["description"].split())
        post["description"] = d[:400] + (" ..." if len(d) > 400 else "")
print(json.dumps(r, ensure_ascii=False, indent=1))
''' % REPO


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("namn", "sok", "yta"):
        print(__doc__)
        return 2
    k = subprocess.run([sys.executable, "-c", KOD, sys.argv[1], sys.argv[2]],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sys.stdout.write(k.stdout.decode("utf-8", "replace"))
    return k.returncode


if __name__ == "__main__":
    sys.exit(main())
