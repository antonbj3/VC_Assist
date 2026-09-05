# -*- coding: utf-8 -*-
"""Motbevis: grindar utan en trasig fixtur som visar dem fälla.

95_testprotokoll.md: *"Trasigt fall: minst ett fall som MÅSTE falla. En grind
som aldrig fällt är oprövad"* och *"Prövar: ... alla elva felkoder ..."*.

`E_QUEUE_FULL` nämns i noll tester. Provet nedan fyller kön och kräver koden.
Går det igenom är hålet ett saknat prov, inte en trasig grind — och då hör
provet hemma i `tests/enhet/` som regressionsprov.
"""
import os
import re
import socket
import sys
import threading
import time

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "ext", "vc_addon", "vc_assist"))
sys.path.insert(0, os.path.join(_ROT, "svc"))

import protokoll as P                                  # noqa: E402
import pump                                            # noqa: E402
from vc_assist_svc.klient import Klient, BryggFel      # noqa: E402


def _ledig_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.fixture
def klient(tmp_path):
    port = _ledig_port()
    b = pump.Brygga(port=port, tokenfil=str(tmp_path / "token"),
                    loggfil=str(tmp_path / "brygga.log"))
    b.starta()
    stopp = threading.Event()

    def pumpa():
        while not stopp.is_set():
            b.tick()
            time.sleep(0.002)

    t = threading.Thread(target=pumpa)
    t.daemon = True
    t.start()
    k = Klient(port=port, tokenfil=str(tmp_path / "token"))
    k.anslut()
    yield k
    k.stang()
    stopp.set()
    t.join(timeout=2)
    b.stang()


# ---- den elfte felkoden -------------------------------------------------


def test_kon_svarar_E_QUEUE_FULL_nar_den_ar_full(klient):
    for i in range(pump.MAX_KO):
        klient.koa('c.setProperty("P", %d)' % i, desc="post %d" % i)
    with pytest.raises(BryggFel) as ei:
        klient.koa('c.setProperty("P", "en for mycket")', desc="overskott")
    assert ei.value.kod == P.E_QUEUE_FULL, (
        "kön var full men bryggan svarade %r" % (ei.value.kod,))


def test_varje_felkod_i_protokollet_provas_av_minst_ett_test():
    """Kontraktstestet i 95_testprotokoll.md kräver alla elva."""
    koder = re.findall(r"^(E_[A-Z_]+) = ", 
                       open(os.path.join(_ROT, "ext", "vc_addon", "vc_assist",
                                         "protokoll.py"), encoding="utf-8").read(),
                       re.M)
    assert len(koder) == 11, koder
    kat = os.path.join(_ROT, "tests", "enhet")
    text = "".join(open(os.path.join(kat, f), encoding="utf-8").read()
                   for f in sorted(os.listdir(kat)) if f.endswith(".py"))
    oprovade = [k for k in koder if not re.search(r"\b%s\b" % k, text)]
    assert not oprovade, ("felkoder som inget enhetstest nämner: %s"
                          % ", ".join(oprovade))
