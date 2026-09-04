# -*- coding: utf-8 -*-
"""Tjanstens sida av bryggan. Python 3, utanfor VC.

Skriven mot docs/spec/31_brygga_protokoll.md, inte mot pump.py. Ramningen
delas genom att samma protokoll.py anvands av bada sidor.
"""
from __future__ import annotations

import os
import socket
import sys
import time
import uuid

_HAR = os.path.dirname(os.path.abspath(__file__))
_EXT = os.path.join(_HAR, "..", "..", "ext", "vc_addon", "vc_assist")
if _EXT not in sys.path:
    sys.path.insert(0, os.path.normpath(_EXT))

import protokoll as P  # noqa: E402


class BryggFel(Exception):
    """Bryggan svarade med ok=false."""

    def __init__(self, kod, meddelande, traceback_=None, svar=None):
        Exception.__init__(self, "%s: %s" % (kod, meddelande))
        self.kod = kod
        self.meddelande = meddelande
        self.traceback = traceback_
        self.svar = svar


class Klient(object):
    def __init__(self, host="127.0.0.1", port=8901, token=None,
                 tokenfil=None, timeout=30.0):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self.token = token if token is not None else self._las_token(tokenfil)
        self.sock = None
        self._avramare = P.Avramare()

    @staticmethod
    def _las_token(tokenfil):
        if tokenfil is None:
            return None
        with open(tokenfil, "r") as f:
            return f.read().strip()

    def anslut(self):
        s = socket.create_connection((self.host, self.port), timeout=self.timeout)
        s.settimeout(self.timeout)
        self.sock = s
        self._avramare = P.Avramare()
        return self

    def stang(self):
        if self.sock is not None:
            try:
                self.sock.close()
            finally:
                self.sock = None

    def __enter__(self):
        return self.anslut()

    def __exit__(self, *a):
        self.stang()

    def anrop(self, op, args=None, id_=None, rasa=True):
        if self.sock is None:
            self.anslut()
        id_ = id_ or uuid.uuid4().hex[:12]
        begaran = {"v": P.PROTOKOLL_VERSION, "id": id_, "op": op, "args": args or {}}
        if self.token is not None:
            begaran["token"] = self.token
        self.sock.sendall(P.rama(P.koda(begaran)))
        svar = self._las_ett()
        if svar.get("id") != id_ and svar.get("id") is not None:
            raise BryggFel("E_PARSE", "svarets id %r matchar inte fragan %r"
                           % (svar.get("id"), id_), svar=svar)
        if rasa and not svar.get("ok"):
            fel = svar.get("error") or {}
            raise BryggFel(fel.get("code", "E_PARSE"), fel.get("message", ""),
                           fel.get("traceback"), svar)
        return svar

    def _las_ett(self):
        slut = time.time() + self.timeout
        while True:
            kroppar = self._avramare.mata(b"")
            if kroppar:
                return P.avkoda(kroppar[0])
            if time.time() > slut:
                raise BryggFel("E_TIMEOUT", "inget svar inom %.1f s" % self.timeout)
            data = self.sock.recv(65536)
            if not data:
                raise BryggFel("E_PARSE", "bryggan stangde anslutningen")
            kroppar = self._avramare.mata(data)
            if kroppar:
                return P.avkoda(kroppar[0])

    # ---- bekvamligheter --------------------------------------------------

    def ping(self):
        return self.anrop("ping")["result"]

    def kor(self, kod, timeout_ms=5000):
        return self.anrop("exec", {"code": kod, "timeout_ms": timeout_ms})

    def koa(self, kod, desc="", timeout_ms=5000):
        return self.anrop("exec_queue", {"code": kod, "desc": desc,
                                         "timeout_ms": timeout_ms})["result"]

    def ko(self, med_kod=False):
        return self.anrop("queue_list", {"with_code": med_kod})["result"]["queue"]

    def godkann(self, qid):
        return self.anrop("queue_approve", {"qid": qid})

    def avvisa(self, qid):
        return self.anrop("queue_reject", {"qid": qid})["result"]
