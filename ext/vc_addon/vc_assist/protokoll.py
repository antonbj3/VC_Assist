# -*- coding: utf-8 -*-
"""Bryggans protokoll: ramning och kuvert.

Detta lager ror ALDRIG VC. Det ar avsiktligt: samma fil kors av bryggan inne
i VC:s Stackless Python 2.7 och av tjansten ute i Python 3, och testas pa
Linux utan att VC startas (95_testprotokoll.md, niva L0).

Kalla: docs/spec/31_brygga_protokoll.md
"""
from __future__ import absolute_import, division, print_function

import json

PROTOKOLL_VERSION = 1      # Protokollets version, 31_brygga_protokoll.md.
MAX_KROPP = 1048576        # Maxlangd kropp, 31_brygga_protokoll.md.

# Felkoder, 31_brygga_protokoll.md
E_VERSION = "E_VERSION"
E_AUTH = "E_AUTH"
E_PARSE = "E_PARSE"
E_TOO_LARGE = "E_TOO_LARGE"
E_UNKNOWN_OP = "E_UNKNOWN_OP"
E_ARGS = "E_ARGS"
E_EXEC = "E_EXEC"
E_TIMEOUT = "E_TIMEOUT"
E_QUEUE_FULL = "E_QUEUE_FULL"
E_NOT_APPROVED = "E_NOT_APPROVED"
E_BUSY = "E_BUSY"

ALLA_FELKODER = (
    E_VERSION, E_AUTH, E_PARSE, E_TOO_LARGE, E_UNKNOWN_OP, E_ARGS,
    E_EXEC, E_TIMEOUT, E_QUEUE_FULL, E_NOT_APPROVED, E_BUSY,
)


class Ramfel(Exception):
    """Trasig ramning. Anslutningen ska stangas."""

    kod = E_PARSE


class ForStor(Ramfel):
    """Kropp over MAX_KROPP."""

    kod = E_TOO_LARGE


def _bytes(x):
    if isinstance(x, bytes):
        return x
    return x.encode("utf-8")


def rama(kropp):
    """Lagg pa langdprefix. Returnerar bytes.

    Formatet ar '<8 hexsiffror, gemener><LF><kropp>'. Langden avser kroppen
    i BYTE efter UTF-8-kodning, inte tecken.
    """
    kropp = _bytes(kropp)
    if len(kropp) > MAX_KROPP:
        raise ForStor("kropp %d byte over max %d" % (len(kropp), MAX_KROPP))
    return ("%08x\n" % len(kropp)).encode("ascii") + kropp


class Avramare(object):
    """Matas med bytes, spottar ut hela kroppar.

    Tal att data kommer i godtyckliga bitar, vilket TCP garanterar att den gor.
    """

    def __init__(self, max_kropp=MAX_KROPP):
        self._buf = b""
        self._max = max_kropp

    def mata(self, data):
        if data:
            self._buf += data
        ut = []
        while True:
            if len(self._buf) < 9:
                break
            huvud = self._buf[:8]
            if self._buf[8:9] != b"\n":
                raise Ramfel("missing LF after length prefix")
            try:
                n = int(huvud, 16)
            except ValueError:
                raise Ramfel("length prefix is not a hex digit: %r" % (huvud,))
            if huvud != ("%08x" % n).encode("ascii"):
                raise Ramfel("length prefix must be eight lowercase hex digits: %r" % (huvud,))
            if n > self._max:
                raise ForStor("angiven kropp %d byte over max %d" % (n, self._max))
            if len(self._buf) < 9 + n:
                break
            ut.append(self._buf[9:9 + n])
            self._buf = self._buf[9 + n:]
        return ut

    def obehandlat(self):
        return len(self._buf)


def koda(obj):
    """dict -> bytes. ensure_ascii=False sa svenska tecken inte svaller."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")


def avkoda(kropp):
    """bytes -> dict. Kastar Ramfel vid trasig JSON eller fel toppniva."""
    try:
        obj = json.loads(kropp.decode("utf-8"))
    except Exception as e:
        raise Ramfel("broken JSON: %s" % (e,))
    if not isinstance(obj, dict):
        raise Ramfel("top level must be an object, got %s" % type(obj).__name__)
    return obj


def svar_ok(id_, result=None, stdout="", stderr="", elapsed_ms=0):
    return {
        "v": PROTOKOLL_VERSION,
        "id": id_,
        "ok": True,
        "result": result,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_ms": elapsed_ms,
    }


def svar_fel(id_, kod, meddelande, traceback_=None, stdout="", stderr="", elapsed_ms=0):
    if kod not in ALLA_FELKODER:
        raise ValueError("okand felkod %r; felkoder ar ett slutet register" % (kod,))
    fel = {"code": kod, "message": meddelande}
    if traceback_:
        fel["traceback"] = traceback_
    return {
        "v": PROTOKOLL_VERSION,
        "id": id_,
        "ok": False,
        "error": fel,
        "stdout": stdout,
        "stderr": stderr,
        "elapsed_ms": elapsed_ms,
    }


def sista_raden_json(stdout):
    """Resultatet tas ur sista raden pa stdout om den ar giltig JSON.

    Samma svarskanal som kallprojektet, av samma skal: koden kors med exec
    och har inget returvarde. Ar sista raden inte JSON blir result None och
    hela utskriften ligger kvar i stdout.
    """
    if not stdout:
        return None
    rader = [r for r in stdout.splitlines() if r.strip()]
    if not rader:
        return None
    try:
        return json.loads(rader[-1])
    except Exception:
        return None


def granska_begaran(obj, forvantad_token):
    """Returnerar (felkod, meddelande) eller (None, None).

    Ordningen ar avsiktlig: version fore token, sa en klient med fel
    protokollversion far veta det i stallet for att tro att den har fel losen.
    """
    if obj.get("v") != PROTOKOLL_VERSION:
        return E_VERSION, "protokollversion %r stods inte, bryggan talar %d" % (
            obj.get("v"), PROTOKOLL_VERSION)
    if forvantad_token is not None and obj.get("token") != forvantad_token:
        return E_AUTH, "fel eller saknad token"
    if not obj.get("op"):
        return E_ARGS, "op saknas"
    if not isinstance(obj.get("args", {}), dict):
        return E_ARGS, "args maste vara ett objekt"
    return None, None
