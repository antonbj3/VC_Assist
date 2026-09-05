# -*- coding: utf-8 -*-
"""M-122 del 3: vilka av grind 2:s fallplatser fyrar de 808 mutanterna?
Jamfors med M-111:s lista over platser som aldrig fyrat under tests/enhet."""
import sys, os, json, glob, re, collections
ROT='/home/anton/projects/VC_Assist'
sys.path.insert(0, ROT+'/svc'); sys.path.insert(0, ROT)
from vc_assist_svc.plc.mutation import skador
from vc_assist_svc.st import validator as V
from vc_assist_svc.st.validator import validera
sys.path.insert(0, ROT+'/tests/protocol')
from kor_fallplatstackning import platser_ur_kallan, _VALIDATOR

TYP = {'bool':'BOOL','int':'INT','dint':'DINT','real':'REAL','time':'TIME','word':'WORD','uint':'UINT','string':'STRING'}

def med_deklarationer(ref, post):
    sig = (post.get('control') or {}).get('signals') or []
    inn = ['    %s : %s;' % (s['name'], TYP.get(str(s.get('type')).lower(), str(s.get('type')).upper())) for s in sig if s.get('dir')=='in']
    ut  = ['    %s : %s;' % (s['name'], TYP.get(str(s.get('type')).lower(), str(s.get('type')).upper())) for s in sig if s.get('dir')!='in']
    block = 'VAR_INPUT\n%s\nEND_VAR\nVAR_OUTPUT\n%s\nEND_VAR\n' % ('\n'.join(inn), '\n'.join(ut))
    m = re.search(r'^PROGRAM\s+\w+\s*$', ref, re.M)
    if not m: return None
    return ref[:m.end()] + '\n' + block + ref[m.end():]

sedda = collections.defaultdict(set)   # (kod, rad) -> set of (uppgift, sort)
aktuell = [None]
orig = V.Granskning.fel
def insp(self, kod, rad, text):
    sedda[(kod, sys._getframe(1).f_lineno)].add(aktuell[0])
    return orig(self, kod, rad, text)
V.Granskning.fel = insp

bas_koder = collections.Counter(); ref_anm = {}
n_mut = 0; mut_anm_ny = 0; mut_fangade_av_grind2 = 0
per_sort = collections.Counter(); per_sort_n = collections.Counter()
for f in sorted(glob.glob(ROT+'/bank/uppgifter/*.json')):
    post = json.load(open(f))
    if not post.get('facit_spar'): continue
    tid = post['task_id']
    ref = med_deklarationer(post['facit_spar']['referens'], post)
    if ref is None: print('ingen PROGRAM-rad', tid); continue
    utg = [s['name'] for s in post['control']['signals'] if s.get('dir')!='in']
    aktuell[0] = ('REF', tid)
    r = validera(ref, utgangar=utg)
    ref_koder = set((a.kod, a.rad, a.text) for a in r.anmarkningar)
    ref_anm[tid] = sorted(set(a.kod for a in r.anmarkningar))
    for a in r.anmarkningar: bas_koder[a.kod] += 1
    for sk in skador(post['facit_spar']['referens'], per_sort=3):
        n_mut += 1; per_sort_n[sk.sort] += 1
        kropp = med_deklarationer(sk.kropp, post)
        aktuell[0] = (tid, sk.sort)
        r2 = validera(kropp, utgangar=utg)
        nya = set((a.kod, a.text) for a in r2.anmarkningar) - set((k, t) for k, _, t in ref_koder)
        if nya or (not r2.ok and r.ok):
            mut_fangade_av_grind2 += 1; per_sort[sk.sort] += 1
V.Granskning.fel = orig

ur_koden = platser_ur_kallan(_VALIDATOR)
alla = set((k, rad) for k, rader in ur_koden.items() for rad in rader)
m111 = json.load(open('/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad/m111_nu.json'))
aldrig = set((o['kod'], o['rad']) for o in m111['otackta'])
fyrade_av_mut = set(k for k, who in sedda.items() if any(w[0] != 'REF' for w in who))
fyrade_av_ref = set(k for k, who in sedda.items() if any(w[0] == 'REF' for w in who))
print('referensernas egna grind-2-anmarkningar (med signalkartan deklarerad):', dict(bas_koder))
print('  referenser med anmarkning:', {t: k for t, k in ref_anm.items() if k})
print('mutanter:', n_mut, ' fangade av grind 2 (ny anmarkning utover referensens):', mut_fangade_av_grind2)
for s in sorted(per_sort_n): print('   %-24s %3d av %3d' % (s, per_sort[s], per_sort_n[s]))
print('fallplatser i validator.py:', len(alla))
print('fyrade av REFERENSERNA sjalva:', len(fyrade_av_ref & alla), sorted(fyrade_av_ref & alla))
print('fyrade av MUTANTERNA (distinkta):', len(fyrade_av_mut & alla), sorted(fyrade_av_mut & alla))
print('M-111 aldrig-fyrade platser nu:', len(aldrig), ' varav mutanterna nar:', len(aldrig & fyrade_av_mut), sorted(aldrig & fyrade_av_mut))
print('fyrade av mutanter utanfor AST-inventeringen (Syntaxfel-vagar etc):', len(fyrade_av_mut - alla))
