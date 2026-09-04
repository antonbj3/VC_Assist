# -*- coding: utf-8 -*-
"""Ordningen: cykler och en kanonisk topologisk ordning, pa EN plats.

Tva lager i planeringslagret behover exakt samma tva svar:

    uppgiftsgrafen (graf.py)    stegen och deras beroenden
    processordningen (processer.py)  vad som ska handa fore vad i cellen

Det ar samma matematik, och den ska darfor inte skrivas tva ganger. Tva
implementationer av samma kontroll ar tva OLIKA kontroller sa fort nagon
ratter den ena, och da kan en cykel upptackas i det ena lagret och passera i
det andra. Samma skal som byggplan.py har for att anvanda verktygsregistrets
EGEN argumentvalidering i stallet for en egen.

TVA KRAV, OCH BADA AR HARDARE AN DE LATER

1. En cykel ska UPPTACKAS OCH NAMNGES. Felet ska bara vilka noder som ingar,
   aldrig bara "ogiltig". Darfor letas starkt sammanhangande komponenter med
   Tarjans algoritm, iterativt: en djup graf far inte kunna sla i
   rekursionstaket och gora en cykelrapport till ett RecursionError.

2. ORDNINGEN AR DETERMINISTISK. Samma kanter ger samma ordning varje gang,
   oavsett i vilken ordning noderna rakade laggas in. Mekanismen: Kahns
   algoritm dar det MINSTA namnet bland de korbara alltid valjs. Det ar ett
   kanoniskt val, inte ett godtyckligt.

Modulen kanner inga steg, inga processer och inget verktygsregister. Den tar
en ordbok av kanter och lamnar listor. Endast standardbiblioteket.
"""
from __future__ import annotations


def _normalisera(kanter):
    """{nod: sorterad tupel av de noder den beror pa som ocksa finns}."""
    kanda = set(kanter)
    return dict((n, tuple(sorted(b for b in kanter[n] if b in kanda)))
                for n in kanter)


def okanda_kanter(kanter):
    """[(nod, beroende)] for varje kant som pekar pa nagot som inte finns."""
    kanda = set(kanter)
    ut = []
    for n in sorted(kanter):
        for b in sorted(kanter[n]):
            if b not in kanda:
                ut.append((n, b))
    return ut


def cykler(kanter):
    """Varje ring av noder som beror pa varandra, med sina medlemmar.

    Returnerar en sorterad lista av sorterade listor. En nod som beror pa sig
    sjalv raknas ocksa som en ring - den ar en ring av langd ett, och den ar
    lika omojlig att ordna som en langre.
    """
    kant = _normalisera(kanter)
    index = {}
    laglank = {}
    pa_stacken = set()
    stack = []
    raknare = [0]
    ut = []

    for start in sorted(kant):
        if start in index:
            continue
        arbete = [(start, 0)]
        while arbete:
            nod, i = arbete[-1]
            if i == 0:
                index[nod] = laglank[nod] = raknare[0]
                raknare[0] += 1
                stack.append(nod)
                pa_stacken.add(nod)
            grannar = kant[nod]
            if i < len(grannar):
                arbete[-1] = (nod, i + 1)
                granne = grannar[i]
                if granne not in index:
                    arbete.append((granne, 0))
                elif granne in pa_stacken:
                    laglank[nod] = min(laglank[nod], index[granne])
                continue
            arbete.pop()
            if arbete:
                forlader = arbete[-1][0]
                laglank[forlader] = min(laglank[forlader], laglank[nod])
            if laglank[nod] == index[nod]:
                komponent = []
                while True:
                    m = stack.pop()
                    pa_stacken.discard(m)
                    komponent.append(m)
                    if m == nod:
                        break
                if len(komponent) > 1 or nod in kant[nod]:
                    ut.append(sorted(komponent))
    return sorted(ut)


def kanonisk_ordning(kanter):
    """(ordning, kvarvarande). Kahn med minsta namnet forst.

    `ordning` ar de noder som gick att ordna, `kvarvarande` de som inte gjorde
    det - alltsa de som ingar i eller hanger efter en cykel. Ar `kvarvarande`
    tom ar ordningen fullstandig.

    En halv ordning lamnas ALDRIG ut som en hel: den ser korbar ut och ar det
    inte. Det ar anroparens sak att se att `kvarvarande` ar tom, och de tva
    anroparna i paketet gor det bada.
    """
    kant = _normalisera(kanter)
    kvar = dict((n, set(b)) for n, b in kant.items())
    ut = []
    while True:
        korbara = sorted(n for n, b in kvar.items() if not b)
        if not korbara:
            break
        valt = korbara[0]
        ut.append(valt)
        del kvar[valt]
        for beroenden in kvar.values():
            beroenden.discard(valt)
    return ut, sorted(kvar)


def nabar(kanter, fran, till):
    """Finns en beroendevag fran 'fran' ned till 'till'?"""
    kant = _normalisera(kanter)
    sedda = set()
    stack = [fran]
    while stack:
        nod = stack.pop()
        for b in kant.get(nod, ()):
            if b == till:
                return True
            if b not in sedda:
                sedda.add(b)
                stack.append(b)
    return False


def lager(kanter, ordning=None):
    """Noderna i lager; noder i samma lager har inga kanter mellan sig.

    Den ovre gransen for hur brett en samtidig utforare skulle kunna arbeta.
    Kraver en fullstandig ordning; anroparen har redan avvisat cykler.
    """
    kant = _normalisera(kanter)
    if ordning is None:
        ordning, kvarvarande = kanonisk_ordning(kant)
        if kvarvarande:
            raise ValueError("lager() kraver en graf utan cykler")
    niva = {}
    for n in ordning:
        beroenden = kant.get(n, ())
        niva[n] = 0 if not beroenden else 1 + max(niva[b] for b in beroenden)
    ut = []
    for n in ordning:
        while len(ut) <= niva[n]:
            ut.append([])
        ut[niva[n]].append(n)
    return [sorted(lag) for lag in ut]
