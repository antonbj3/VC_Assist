# -*- coding: utf-8 -*-
"""M-122 del 2: den saknade F15-operatorn. Byt `inst.Q` mot instansens CLK-signal
(villkoret lases pa NIVA i stallet for pa flank) - exakt M-115:s mutation."""
import sys, os, json, glob, re, collections
sys.path.insert(0,'/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad')
from m122_mutation_skikt import ROT, alla_spar, skiljer, PERT, domare

def niva_mutanter(ref):
    inst = dict(re.findall(r"(\w+)\s*\(\s*CLK\s*:=\s*([\w\.]+)\s*\)", ref))
    ut=[]
    for i, clk in inst.items():
        m = re.compile(r"\b%s\.Q\b" % re.escape(i))
        if not m.search(ref): continue
        ny = m.sub(clk, ref)
        if ny != ref: ut.append((i, clk, ny, ref.count(i+'.Q')))
    return ut

rows=[]
for f in sorted(glob.glob(ROT+'/bank/uppgifter/*.json')):
    post=json.load(open(f))
    if not post.get('facit_spar'): continue
    ref=post['facit_spar']['referens']
    refspar=alla_spar(ref,post)
    for inst,clk,ny,n in niva_mutanter(ref):
        d=domare.dom(post,ny)
        koder=[b.kod for b in d.brister]
        rad=dict(uppgift=post['task_id'],inst=inst,clk=clk,n_byten=n,godkand=d.godkand,
                 koder=koder[:5])
        if d.godkand:
            ms=alla_spar(ny,post)
            rad['synlig']={p:skiljer(refspar[p],ms[p]) for p,_,_,_ in PERT}
        rows.append(rad)
json.dump(rows,open('/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad/m122_niva.json','w'),indent=1,ensure_ascii=False)
print('NIVA-mutanter:',len(rows),' uppgifter med flankdetektor:',len(set(r['uppgift'] for r in rows)))
f=[r for r in rows if not r['godkand']]; o=[r for r in rows if r['godkand']]
print('fangade av facit:',len(f),' overlevde:',len(o))
print('fangade via kod:',collections.Counter(k.split(':')[0].split('@')[0] for r in f for k in r['koder'][:1]))
for r in f: print('  FANGAD ',r['uppgift'],r['inst'],'->',r['clk'],r['koder'][:2])
for r in o: print('  OVERLEVDE',r['uppgift'],r['inst'],'->',r['clk'],'synlig:',{k:v for k,v in r['synlig'].items() if v})
