# -*- coding: utf-8 -*-
"""M-122: vad de overlevande beteendemutanterna ar - ekvivalenta, osedda av
facitets kontrollpunkter, eller aldrig nadda av facitets stimulus.

Kor alla 806 skador ur mutation.skador() over de 26 referenserna genom
bank.domare.dom (samma domare som slingan). For varje mutant som OVERLEVER
(domaren GODKAND) jamfors mutantens utgangsspar med referensens pa
  (1) facitets egna sekvenser (samma stimulus som domaren anvander)
  (2) fyra perturbationer av samma stimulus: alla handelseavstand x0.25,
      x0.5, x2.0, och sekvensen spelad tva ganger i rad (latch/aterstallning)
Facit for jamforelsen ar referensen sjalv - den ar korrekt per definition i
en mutationsanalys, sa ingen ny domare uppfinns.
"""
import sys, os, json, glob, collections, multiprocessing as mp, time
ROT = '/home/anton/projects/VC_Assist'
sys.path.insert(0, ROT + '/svc'); sys.path.insert(0, ROT)
from vc_assist_svc.plc.mutation import skador
from vc_assist_svc.st import tolk as T
from vc_assist_svc.st.tolk import Tolk, Tolkfel
from bank import domare

PERT = [('facit', 1.0, 1, 1.0), ('x0.25', 0.25, 1, 1.0), ('x0.5', 0.5, 1, 1.0),
        ('x2.0', 2.0, 1, 1.0), ('upprepa2', 1.0, 2, 1.0), ('hall3', 1.0, 1, 3.0)]


def spar(st_text, post, sekv, flanker, skala=1.0, upprepa=1, hall=1.0, paus_ms=1000.0):
    typer, riktningar = domare._signalkarta(post)
    utg = sorted(n for n, r in riktningar.items() if r == 'out')
    facit = post['facit_spar']
    scan_ms = float(facit.get('scan_ms') or T.SCAN_MS)
    steg = sorted(sekv['steg'], key=lambda x: float(x['t_ms']))
    slut = max([float(s['t_ms']) for s in steg] +
               [float(f.get('till_ms', 0.0)) for f in flanker
                if f.get('sekvens') == sekv['id']])
    plan = []
    for r in range(upprepa):
        off = r * (slut * skala + paus_ms)
        for s in steg:
            if s.get('satt'):
                plan.append((off + float(s['t_ms']) * skala, s['satt']))
    slut_tot = (upprepa - 1) * (slut * skala + paus_ms) + slut * skala
    if hall != 1.0:
        # varje boolesk puls (True ... False) pa en insignal halls `hall` ganger sa lange
        ev = [(t, s, v) for t, d in plan for s, v in d.items()]
        ev.sort(key=lambda e: e[0])
        ny = []
        senast_hog = {}
        for t, s, v in ev:
            if isinstance(v, bool):
                if v:
                    senast_hog[s] = t
                elif s in senast_hog:
                    t0 = senast_hog.pop(s)
                    t = t0 + hall * (t - t0)
            ny.append((t, s, v))
        ny.sort(key=lambda e: e[0])
        plan = []
        for t, s, v in ny:
            if plan and abs(plan[-1][0] - t) < 1e-9:
                plan[-1][1][s] = v
            else:
                plan.append((t, {s: v}))
        slut_tot = max(slut_tot, max(t for t, _ in plan) + 2000.0)
    try:
        motor = Tolk(st_text, typer, riktningar, scan_ms)
    except Tolkfel as f:
        return ('TOLKFEL', str(f)[:120])
    ut = []; i = 0
    try:
        while motor.tid_ms <= slut_tot + 1e-9:
            while i < len(plan) and plan[i][0] <= motor.tid_ms + 1e-9:
                for n, v in plan[i][1].items():
                    motor.satt(n, v)
                i += 1
            motor.scan()
            ut.append(tuple(motor.las(u) for u in utg))
    except Tolkfel as f:
        return ('TOLKFEL', str(f)[:120])
    return ut


def alla_spar(st_text, post):
    facit = post['facit_spar']
    flanker = facit.get('flanker') or []
    ut = {}
    for namn, skala, upprepa, hall in PERT:
        ut[namn] = [spar(st_text, post, s, flanker, skala, upprepa, hall)
                    for s in facit.get('sekvenser') or []]
    return ut


def skiljer(a, b):
    """True om nagot spar skiljer. TOLKFEL raknas som skillnad (kod som
    kraschar dar referensen kor ar ett synligt fel)."""
    for x, y in zip(a, b):
        if x != y:
            return True
    return False


def radtyp(ref, rad):
    lines = ref.split('\n'); l = lines[rad - 1]
    i_var = None
    for k in range(rad - 1, -1, -1):
        s = lines[k].strip().upper()
        if s.startswith('END_VAR'):
            break
        if s.startswith('VAR'):
            i_var = k; break
    txt = '\n'.join(lines[:rad])
    if txt.count('(*') > txt.count('*)') or l.strip().startswith('(*') or l.strip().startswith('//'):
        return 'KOMMENTAR'
    if i_var is not None:
        return 'INITIERARE'
    return 'KOD'


def kor_uppgift(task_id):
    os.nice(19)
    post = json.load(open('%s/bank/uppgifter/%s.json' % (ROT, task_id)))
    ref = post['facit_spar']['referens']
    refdom = domare.dom(post, ref)
    refspar = alla_spar(ref, post)
    rader = []
    for sk in skador(ref, per_sort=3):
        d = domare.dom(post, sk.kropp)
        koder = [b.kod for b in d.brister]
        if d.godkand:
            utfall = 'OVERLEVDE'; lager = None
        elif any(k.startswith('tolkfel') for k in koder):
            utfall = 'FANGAD'; lager = 'text'
        elif any(k.startswith('forgrind') for k in koder):
            utfall = 'FANGAD'; lager = 'forgrind'
        else:
            utfall = 'FANGAD'; lager = 'beteende'
        rad = dict(uppgift=task_id, sort=sk.sort, vantat=sk.vantat_lager,
                   rad=sk.rad, fore=sk.fore[:40], efter=sk.efter[:40],
                   utfall=utfall, lager=lager, koder=koder[:6])
        if d.godkand:
            ms = alla_spar(sk.kropp, post)
            synlig = {}
            for namn, _, _, _ in PERT:
                synlig[namn] = skiljer(refspar[namn], ms[namn])
            if synlig['facit']:
                klass = 'SKILLNAD_PA_FACITSTIMULUS'
            elif any(synlig[n] for n, _, _, _ in PERT if n != 'facit'):
                klass = 'SYNLIG_BARA_UNDER_PERTURBATION'
            else:
                klass = 'OSYNLIG'
            rad['klass'] = klass
            rad['synlig'] = synlig
            rad['radtyp'] = radtyp(ref, sk.rad)
        rader.append(rad)
    return dict(uppgift=task_id, referens_godkand=refdom.godkand,
                referens_koder=[b.kod for b in refdom.brister][:5],
                n=len(rader), rader=rader)


def main():
    t0 = time.time()
    ids = sorted(os.path.basename(f)[:-5] for f in glob.glob(ROT + '/bank/uppgifter/*.json')
                 if json.load(open(f)).get('facit_spar'))
    with mp.Pool(4) as p:
        res = p.map(kor_uppgift, ids)
    ut = '/tmp/claude-1000/-home-anton/96f8ecd2-bf69-4040-be9e-53e0290900a0/scratchpad/m122_resultat.json'
    json.dump(res, open(ut, 'w'), ensure_ascii=False, indent=1)
    rader = [r for u in res for r in u['rader']]
    n = len(rader)
    fang = [r for r in rader if r['utfall'] == 'FANGAD']
    ov = [r for r in rader if r['utfall'] == 'OVERLEVDE']
    print('uppgifter %d  referens GODKAND %d/%d  (%.0fs)' % (
        len(res), sum(1 for u in res if u['referens_godkand']), len(res), time.time() - t0))
    for u in res:
        if not u['referens_godkand']:
            print('  REFERENS FALLD:', u['uppgift'], u['referens_koder'])
    print('skador %d  fangade %d  overlevde %d' % (n, len(fang), len(ov)))
    print('fangade per lager', collections.Counter(r['lager'] for r in fang))
    print('fangade per (vantat -> lager)', collections.Counter((r['vantat'], r['lager']) for r in fang))
    print()
    print('%-24s %5s %5s %5s %5s | %6s %6s %6s' % ('sort', 'n', 'text', 'bete', 'over', 'SKILL', 'PERT', 'OSYN'))
    for sort in sorted(set(r['sort'] for r in rader)):
        rs = [r for r in rader if r['sort'] == sort]
        o = [r for r in rs if r['utfall'] == 'OVERLEVDE']
        print('%-24s %5d %5d %5d %5d | %6d %6d %6d' % (
            sort, len(rs),
            sum(1 for r in rs if r['lager'] == 'text'),
            sum(1 for r in rs if r['lager'] == 'beteende'),
            len(o),
            sum(1 for r in o if r['klass'] == 'SKILLNAD_PA_FACITSTIMULUS'),
            sum(1 for r in o if r['klass'] == 'SYNLIG_BARA_UNDER_PERTURBATION'),
            sum(1 for r in o if r['klass'] == 'OSYNLIG')))
    print()
    bo = [r for r in ov if r['vantat'] == 'beteende']
    print('overlevande BETEENDEmutanter: %d' % len(bo))
    print('  klass:', collections.Counter(r['klass'] for r in bo))
    for pn, _, _, _ in PERT:
        print('  synlig under %-9s: %d' % (pn, sum(1 for r in bo if r['synlig'][pn])))
    print('  radtyp x klass:', collections.Counter((r['radtyp'], r['klass']) for r in bo))
    kod = [r for r in bo if r['radtyp'] == 'KOD']
    print('  KODRADS-overlevare: %d  klass: %s' % (len(kod), dict(collections.Counter(r['klass'] for r in kod))))
    for pn, _, _, _ in PERT:
        print('    kodrads-overlevare synliga under %-9s: %d' % (pn, sum(1 for r in kod if r['synlig'][pn])))
    print('  per uppgift (overlevande beteende / SKILLNAD / PERT / OSYN):')
    for u in res:
        b = [r for r in u['rader'] if r['utfall'] == 'OVERLEVDE' and r['vantat'] == 'beteende']
        print('    %-5s %3d %3d %3d %3d' % (
            u['uppgift'], len(b),
            sum(1 for r in b if r['klass'] == 'SKILLNAD_PA_FACITSTIMULUS'),
            sum(1 for r in b if r['klass'] == 'SYNLIG_BARA_UNDER_PERTURBATION'),
            sum(1 for r in b if r['klass'] == 'OSYNLIG')))


if __name__ == '__main__':
    main()
