# -*- coding: utf-8 -*-
"""Fas 14:s sparr: kvoten mekaniserat mot bett far bara ga UPPAT.

En regel i en promptstrang ar en bon. En regel som avvisar mekaniskt ar en
grind. Kvoten mellan de tva ar darfor harnessens enda arliga matt pa sig sjalv,
och den ska inte kunna sjunka utan att nagon markt det.

Historiken star i talen: M-46 matte 17 av 46 (37 %), och fann samtidigt att 17
var for hogt - SAK-003 var en ren etikett utan en rad kod som kunde falla den.
Det verkliga talet var 16. M-53 tog det till 37 av 46 (80 %).

VARFOR TAKET GAR AT ANDRA HALLET AN DE ANDRA SPARRARNA
------------------------------------------------------
Troskelskulden och S5 raknar SKULD, och ska krympa. Den har raknar TACKNING,
och ska vaxa. Bada har samma egenskap: talet far inte glida at fel hall utan
att ett prov faller.
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.harness import instruktioner as I               # noqa: E402

# MATT 2026-09-05 av M-53. Talen far bara ga UPPAT.
#
# Blocken raknas var for sig och inte bara i summa, av ett matt skal: M-46
# fann att `matta_fallor` lag pa 2 av 8 medan helheten lag pa 17 av 46. En
# summa kan sta still medan det block som betyder mest tappar mark.
GOLV_TOTALT = 37
GOLV_PER_BLOCK = {
    "systemroll": 2,
    "arbetsordning": 4,
    "verktygsbruk": 9,
    "arlighet": 6,
    "sakerhetsgransen": 4,
    "domankunskap_vc": 4,
    "matta_fallor": 8,
}


def korpus():
    return I.las_korpus()


def per_block(k):
    ut = {}
    for b in k.block:
        ut[b.id] = (sum(1 for r in b.regler if r.tvingad), len(b.regler))
    return ut


def test_totalen_bara_vaxer():
    k = korpus()
    tvingade = len(k.tvingade())
    assert tvingade >= GOLV_TOTALT, (
        "%d av %d regler ar mekaniserade, golvet ar %d. En regel har gatt fran "
        "grind till bon." % (tvingade, len(k.regler()), GOLV_TOTALT))


def test_golvet_ar_inte_slappare_an_verkligheten():
    """Ett golv under verkligheten slutar fanga nasta glidning."""
    k = korpus()
    assert len(k.tvingade()) == GOLV_TOTALT, (
        "verkligheten ar %d men golvet sager %d - hoj golvet i det har provet"
        % (len(k.tvingade()), GOLV_TOTALT))


@pytest.mark.parametrize("block", sorted(GOLV_PER_BLOCK))
def test_varje_block_bara_vaxer(block):
    """En summa kan sta still medan det block som betyder mest tappar mark."""
    p = per_block(korpus())
    assert block in p, "blocket %s finns inte langre i korpusen" % block
    tvingade, totalt = p[block]
    assert tvingade >= GOLV_PER_BLOCK[block], (
        "%s: %d av %d mekaniserade, golvet ar %d"
        % (block, tvingade, totalt, GOLV_PER_BLOCK[block]))


def test_inget_block_har_forsvunnit():
    p = per_block(korpus())
    saknade = sorted(set(GOLV_PER_BLOCK) - set(p))
    assert not saknade, "block borta ur korpusen: %s" % ", ".join(saknade)


def test_en_tvingad_regel_namnger_sin_mekanism():
    """Etikettfallan: M-46 fann SAK-003 markt 'block' utan en rad kod bakom.

    Det ar den farligaste posten i hela kvoten - den hojer talet utan att hoja
    hardheten, och den ser ut precis som en riktig grind.
    """
    utan = [r.id for r in korpus().tvingade() if not r.tvingas_av]
    assert not utan, (
        "regler markta 'block' utan mekanism: %s. En etikett ar ingen grind."
        % ", ".join(utan))


def test_en_bedd_regel_bar_ett_skrivet_skal():
    """En regel som arligt inte gar att mekanisera ar inte ett misslyckande.

    En regel som PASTAS mekaniserad utan att vara det ar det. Och en bedd regel
    utan skal ar en som ingen har provat att mekanisera.
    """
    k = korpus()
    bedda = [r for r in k.regler() if not r.tvingad]
    utan_skal = [r.id for r in bedda if not (r.skal or "").strip()]
    assert not utan_skal, (
        "bedda regler utan skrivet skal: %s" % ", ".join(utan_skal))


def test_kvoten_gar_att_rakna_om_ur_korpusen_sjalv():
    """Talet ska aldrig arvas. M-46 arvde 17 och det var fel."""
    k = korpus()
    assert len(k.regler()) == 46, (
        "korpusen har %d regler; golven i det har provet galler 46 och maste "
        "raknas om" % len(k.regler()))
