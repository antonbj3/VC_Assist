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

# Repots rot. Den hardkodade sokvagen som stod har forst hade bundit verktyget
# till en maskin. Att i stallet harleda tre niva upp ur filens plats band det
# lika hart till sin KATALOG: en kopia i en scratchpad pekade da pa
# sessionskatalogen, och felet syntes forst som "No module named vc_assist_svc"
# ur en underprocess - alltsa langt fran orsaken. Nu letas roten upp.
import os


def _leta_rot():
    """Hitta repot fran filens plats, fran cwd, eller ur miljon.

    Returnerar None om ingen av vagarna bar. Verktyget sager da vad som saknas
    i stallet for att lata underprocessen do pa en importrad.
    """
    kandidater = [os.path.dirname(os.path.abspath(__file__)), os.getcwd()]
    for start in kandidater:
        d = start
        while True:
            if os.path.isdir(os.path.join(d, "svc", "vc_assist_svc")):
                return d
            mor = os.path.dirname(d)
            if mor == d:
                break
            d = mor
    ur_miljon = os.environ.get("VC_ASSIST_REPO")
    if ur_miljon and os.path.isdir(os.path.join(ur_miljon, "svc", "vc_assist_svc")):
        return ur_miljon
    return None


REPO = _leta_rot()

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
'''


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("namn", "sok", "yta"):
        print(__doc__)
        return 2
    if REPO is None:
        sys.stderr.write(
            "slaupp.py hittar inte VC_Assist-repot. Sokte uppat fran %s och\n"
            "fran %s. Satt VC_ASSIST_REPO till repots rot.\n"
            % (os.path.dirname(os.path.abspath(__file__)), os.getcwd()))
        return 2
    k = subprocess.run([sys.executable, "-c", KOD % REPO, sys.argv[1], sys.argv[2]],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    sys.stdout.write(k.stdout.decode("utf-8", "replace"))
    return k.returncode


if __name__ == "__main__":
    sys.exit(main())
