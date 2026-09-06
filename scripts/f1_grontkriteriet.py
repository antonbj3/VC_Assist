# Grontkriteriet raknat av RIGGENS EGEN kod over de tva armarnas JSON.
# Armarna kordes i tva anrop (guld forst, sedan komposition), sa varje anrop
# sag bara sin egen halva. Rakningen far inte goras for hand.
import json, os, sys
ROT="/home/anton/projects/VC_Assist"
for p in (os.path.join(ROT,"tests","protocol"), os.path.join(ROT,"svc"),
          os.path.join(ROT,"ext","vc_addon","vc_assist"), ROT):
    sys.path.insert(0,p)
import kor_F1_modellen_skriver_linan as F1
g = json.load(open(sys.argv[1]))
k = json.load(open(sys.argv[2]))
assert g["modell"] == k["modell"], "olika modeller: %s vs %s" % (g["modell"], k["modell"])
assert g["n"] == k["n"]
dom = F1.grontkriteriet(g["guld_arm"], k["komposition"], g["n"])
print("modell: %s   n: %d\n" % (g["modell"], g["n"]))
F1.skriv_domen(dom)
json.dump(dom, open(sys.argv[3], "w"), indent=1, ensure_ascii=False, sort_keys=True)
