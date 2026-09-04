# -*- coding: utf-8 -*-
"""Var tjansten hittar bryggans tokenfil. Windows och Wine, samma anrop.

Fore den har modulen bar fyra provskript samma rad:

    ~/.wine-vc-test/drive_c/users/anton/vc_assist_token

Tre antaganden i en strang: att det finns ett wine-prefix, att det heter
``.wine-vc-test``, och att anvandaren heter ``anton``. Pa Windows ar alla tre
falska, och felet blir ``FileNotFoundError`` pa en sokvag som inte ens ser ut
som en Windows-sokvag.

Harledningen har ar densamma at bada hallen: bryggan skriver filen i
``plats.anvandarmapp()``, och det ar samma mapp tjansten laser i - direkt pa
Windows, och genom wine-prefixets ``drive_c/users/<du>`` pa Linux.

Ingenting gissas. Kan filen inte hittas raknas alla stallen som provades upp.
"""
from __future__ import annotations

import os
import sys

_HAR = os.path.dirname(os.path.abspath(__file__))
_ROT = os.path.normpath(os.path.join(_HAR, "..", ".."))
_EXT = os.path.join(_ROT, "ext", "vc_addon", "vc_assist")
for _p in (_EXT, _ROT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import plats  # noqa: E402
from install import upptackt  # noqa: E402

TOKENVARIABEL = "VC_ASSIST_TOKEN"


class TokenSaknas(Exception):
    """Ingen tokenfil hittad. Bararen av detaljerna ar ``provade``."""

    def __init__(self, meddelande, provade):
        Exception.__init__(self, "%s\n  - %s"
                           % (meddelande, "\n  - ".join(provade)))
        self.provade = list(provade)


def _windowskandidater(miljo):
    hem = plats.anvandarmapp(env=miljo.env, plattform=miljo.plattform,
                             expanduser=lambda _t: miljo.hem)
    return [(os.path.join(hem, plats.TOKEN), "anvandarmappen %s" % hem)]


def _winekandidater(miljo):
    ut = []
    for prefix, kalla in upptackt.wineprefix(miljo):
        anvandarrot = os.path.join(prefix, "drive_c", "users")
        try:
            namn = sorted(os.listdir(anvandarrot))
        except OSError as fel:
            miljo.varna("kunde inte lasa %s: %s" % (anvandarrot, fel))
            continue
        for n in namn:
            if n.lower() == "public":
                continue
            ut.append((os.path.join(anvandarrot, n, plats.TOKEN),
                       "%s, anvandaren %s" % (kalla, n)))
    return ut


def kandidater(miljo=None):
    """Alla stallen tokenfilen kan ligga pa, i ordning, som (sokvag, kalla).

    ``VC_ASSIST_TOKEN`` ligger forst pa bada plattformarna: den som har en udda
    uppsattning ska kunna peka ut filen i stallet for att overtala sokningen.
    """
    if miljo is None:
        miljo = upptackt.Miljo()
    ut = []
    uttryckligt = miljo.env.get(TOKENVARIABEL)
    if uttryckligt:
        ut.append((uttryckligt, TOKENVARIABEL))
    ut.extend(_windowskandidater(miljo) if miljo.ar_windows
              else _winekandidater(miljo))
    sedda = set()
    kvar = []
    for sokvag, kalla in ut:
        if sokvag in sedda:
            continue
        sedda.add(sokvag)
        kvar.append((sokvag, kalla))
    return kvar


def tokenfil(miljo=None, mtime=None):
    """Den tokenfil som FINNS, senast skriven forst.

    Senast skriven, inte forst i listan: pa den har maskinen finns tva
    wine-prefix med var sin brygga, och den som kordes sist ar den som lyssnar.
    Ordningen i ``kandidater`` avgor bara vid lika tid.

    ``VC_ASSIST_TOKEN`` ar undantaget: det ar ett val, inte en kandidat, och
    det tavlar darfor inte pa tidsstampel.
    """
    if miljo is None:
        miljo = upptackt.Miljo()
    if mtime is None:
        mtime = os.path.getmtime
    # Ett uttryckligt val konkurrerar inte. Star VC_ASSIST_TOKEN satt och
    # filen inte finns ar det ETT fel att rapportera, inte en anledning att
    # leta vidare och tyst anvanda nagon annans token.
    uttryckligt = miljo.env.get(TOKENVARIABEL)
    if uttryckligt:
        if os.path.isfile(uttryckligt):
            return uttryckligt
        raise TokenSaknas(
            "%s pekar pa en fil som inte finns" % TOKENVARIABEL,
            ["%s  (%s)" % (uttryckligt, TOKENVARIABEL)])
    alla = kandidater(miljo)
    funna = []
    for i, (sokvag, kalla) in enumerate(alla):
        if not os.path.isfile(sokvag):
            continue
        try:
            t = mtime(sokvag)
        except OSError:
            t = 0.0
        funna.append((-t, i, sokvag, kalla))
    if not funna:
        raise TokenSaknas(
            "hittade ingen tokenfil (%s). Bryggan skriver den forst nar den "
            "bundit porten - star det inget i bootloggen har tillagget inte "
            "laddats (M-01, M-09). Peka ut filen med %s om den ligger nagon "
            "annanstans." % (plats.TOKEN, TOKENVARIABEL),
            ["%s  (%s)" % (s, k) for s, k in alla] or ["inga kandidater alls"])
    funna.sort()
    return funna[0][2]
