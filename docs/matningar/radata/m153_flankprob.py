# -*- coding: utf-8 -*-
"""M-153: var ligger flanken? Tolkens tid, OpenPLC:s tid, fonstrets slut.

Sammanstallningen i `tests/protocol/kor_A3_domarna_i_skala.py` sager ATT de tva
domarna ar oense om `flank:*`. Den sager inte VARFOR. Den har proben tar EN
signal i EN sekvens och skriver ut tre tal bredvid varandra:

  * vid vilka ms var ST-tolken ser flanken (samma slinga som `domare.py`),
  * vid vilka ms OpenPLC-domarens 20 ms-rutnat ser den,
  * facits fonster, och det bredare fonster OpenPLC-domaren faktiskt laser.

Utan de tre talen ar en oenighet en asikt. Med dem ar den en mekanism.

Kors mot en LEDIG runtime (inte en som svepet anvander):

    python3 docs/matningar/radata/m153_flankprob.py A-07 \\
        kallstart_utan_sjalvstart ST470_CLP_CLOSE \\
        https://127.0.0.1:18443 opc.tcp://172.17.0.2:4840/openplc/opcua \\
        /tmp/flankprob_bygg
"""
import json
import sys

sys.path.insert(0, "/home/anton/projects/VC_Assist/bank")
sys.path.insert(0, "/home/anton/projects/VC_Assist/svc")
import domare as D                      # noqa: E402
import domare_openplc as DO             # noqa: E402
from vc_assist_svc.st import tolk as _tolk   # noqa: E402

task, seq_id, signal = sys.argv[1], sys.argv[2], sys.argv[3]
bas, ep, kat = sys.argv[4], sys.argv[5], sys.argv[6]
post = json.load(open("/home/anton/projects/VC_Assist/bank/uppgifter/%s.json"
                      % task, encoding="utf-8"))
fs = post["facit_spar"]
st = fs["referens"]
sekv = [s for s in fs["sekvenser"] if s["id"] == seq_id][0]

# --- tolken: exakt domare.py:s slinga, sa tiderna ar domarens och inte en ny
typer, riktningar = D._signalkarta(post)
motor = _tolk.Tolk(st, typer, riktningar, float(fs.get("scan_ms") or 20))
steg = sorted(sekv["steg"], key=lambda x: float(x["t_ms"]))
slut = max([float(s["t_ms"]) for s in steg]
           + [float(f.get("till_ms", 0)) for f in (fs.get("flanker") or [])
              if f.get("sekvens") == seq_id])
i = 0
forra = None
tolk_rise, tolk_fall = [], []
scan = float(fs.get("scan_ms") or 20)
while motor.tid_ms <= slut + 1e-9:
    while i < len(steg) and float(steg[i]["t_ms"]) <= motor.tid_ms + 1e-9:
        for n, v in (steg[i].get("satt") or {}).items():
            motor.satt(n, v)
        i += 1
    motor.scan()
    v = bool(motor.las(signal))
    t_ledd = motor.tid_ms - scan
    if forra is not None:
        if v and not forra:
            tolk_rise.append(t_ledd)
        if forra and not v:
            tolk_fall.append(t_ledd)
    forra = v
print("TOLK  %s RISE vid %s" % (signal, tolk_rise[:12]))
print("TOLK  %s FALL vid %s" % (signal, tolk_fall[:12]))

# --- openplc: samma bygge, samma korning och samma rutnat som domaren
rigg = DO.Rigg(bas=bas, endpoint=ep)
rigg.kontrollera()
karta = DO._karta_for_post(post)
full, _ = DO.program_for_st(st, karta)
zipv = DO._bygg(full, karta, rigg, kat)
kl = rigg.klient()
kl.skapa_forsta_anvandare()
assert DO._ladda(kl, zipv) is None
assert DO._starta(kl) is None
spar = DO._kor_en_sekvens(rigg, karta.station, karta, sekv,
                          fs.get("flanker") or [], DO.tilldelade_namn(st))
kl.stoppa()
n_scan = int((slut / 1000.0 + DO.TAIL_S) * 1000.0 / DO.SCAN_MS) + 1
grid = DO._sampla(spar, n_scan)
tag = karta.med_tagg(signal).tagg
print("RA    forsta 6 rasamplen (t_ms, %s): %s"
      % (signal, [(round(t, 1), v.get(tag)) for t, v in spar[:6]]))
print("GRID  scan 0-4 (%s): %s"
      % (signal, [grid[k].get(tag) for k in range(min(5, len(grid)))]))
op_rise, op_fall = [], []
forra = None
for k in range(n_scan):
    v = bool(grid[k].get(tag))
    if forra is not None:
        if v and not forra:
            op_rise.append(k * DO.SCAN_MS)
        if forra and not v:
            op_fall.append(k * DO.SCAN_MS)
    forra = v
# Valfritt sjunde argument: skriv ut RASAMPLEN runt en tid (ms). Utan dem gar
# det inte att skilja "PLC:n var lag ett helt scan" fran "ett enda prov foll
# ur" - och det ar precis den skillnaden som avgor om en glitch ar motorns
# eller domarens.
if len(sys.argv) > 7:
    runt = float(sys.argv[7])
    print("RUNT  %.0f ms, rasamplen (t_ms, %s): %s"
          % (runt, signal,
             [(round(t, 1), v.get(tag)) for t, v in spar
              if runt - 120 <= t <= runt + 120]))
print("OPLC  %s RISE vid %s" % (signal, op_rise[:12]))
print("OPLC  %s FALL vid %s" % (signal, op_fall[:12]))
for f in (fs.get("flanker") or []):
    if f.get("sekvens") == seq_id and f["signal"] == signal:
        print("FACIT %s: %s antal=%s fonster [%s, %s] ms; "
              "openplc-domaren laser [%s, %s]"
              % (f["namn"], f["typ"], f["antal"], f["fran_ms"], f["till_ms"],
                 f["fran_ms"],
                 float(f["till_ms"]) + DO.TOLERANS_SCAN * DO.SCAN_MS))
