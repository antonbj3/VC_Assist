# -*- coding: utf-8 -*-
"""Routingregeln och vagen ut till bryggan.

45_verktyg.md och I12 i 90_invarianter.md:

    effect = read   ->  bryggans "exec"
    effect = write  ->  bryggans "exec_queue", alltsa godkannandekon

    "Regeln ar mekanisk. Ingen enskild handlare far valja sjalv."

Sa har ar den omojlig att kringga, och inte bara forbjuden:

1. Tabellen ar det ENDA stallet i tjansten dar operationsnamnen "exec" och
   "exec_queue" star. Den ar en MappingProxyType och gar inte att skriva i.
2. Handlarna far aldrig se klienten. register.registrera() avvisar varje
   handlare vars signatur tar mer an (argument), sa det finns inget satt for
   en handlare att sanda nagot sjalv.
3. Kodgeneratorer returnerar en STRANG. Utforaren laser aldrig nagot ur den
   strangen for att bestamma lage; op slas upp pa verktygets effect innan
   handlaren ens anropas.
4. Verktygsdefinitionen ar oforanderlig (Verktyg.__setattr__ kastar), sa
   effect kan inte andras efter registrering.

Andra forsvarslinjen ligger inne i bryggan: pump.py:_op_exec kor
skrivgrind.granska() pa koden och avvisar skrivande kod med E_NOT_APPROVED
aven om tjansten skulle rada fel. De tva linjerna ar oberoende.
"""
from __future__ import annotations

import time
from types import MappingProxyType

from .fel import OkantVerktyg, Svarsfel
from .register import CODE_GEN_HANDLERS, DATA_HANDLERS, REGISTER
from .schema import validera_argument, validera_resultat

OP_FOR_EFFECT = MappingProxyType({"read": "exec", "write": "exec_queue"})

# Hur ofta kon fragas om en godkand posts utfall, och hur lange.
KO_POLL_S = 0.05            # PRELIMINAR. Satts av matning M-14.
KO_TIMEOUT_S = 60.0         # PRELIMINAR. Satts av matning M-14.


def op_for_effect(effect):
    """Enda stallet dar ett exekveringslage valjs."""
    try:
        return OP_FOR_EFFECT[effect]
    except KeyError:
        raise ValueError(
            "okand effect %r; tabellen ar sluten och rymmer bara %s (I12)"
            % (effect, ", ".join(sorted(OP_FOR_EFFECT))))


class Resultat(object):
    """Vad ett verktygsanrop lamnade efter sig."""

    __slots__ = ("verktyg", "effect", "mode", "op", "kod", "koad", "qid",
                 "resultat", "stdout", "svar")

    def __init__(self, verktyg, effect, mode, op=None, kod=None, koad=False,
                 qid=None, resultat=None, stdout="", svar=None):
        self.verktyg = verktyg
        self.effect = effect
        self.mode = mode
        self.op = op
        self.kod = kod
        self.koad = koad
        self.qid = qid
        self.resultat = resultat
        self.stdout = stdout
        self.svar = svar

    def __repr__(self):
        if self.koad:
            return "Resultat(%s, koad som %s)" % (self.verktyg, self.qid)
        return "Resultat(%s, %r)" % (self.verktyg, self.resultat)


class Utforare(object):
    """Kor ett verktyg. Enda stallet som bade kanner klienten och registret."""

    def __init__(self, klient, urval, register=None, data_handlers=None,
                 code_gen_handlers=None):
        self.klient = klient
        self.urval = urval
        self.register = REGISTER if register is None else register
        self._data = DATA_HANDLERS if data_handlers is None else data_handlers
        self._kodgen = (CODE_GEN_HANDLERS if code_gen_handlers is None
                        else code_gen_handlers)
        self.koade = {}          # qid -> verktygsnamn, sa svaret kan provas
        self.ko_timeout_s = KO_TIMEOUT_S

    def _verktyg(self, namn):
        if namn not in self.register:
            raise OkantVerktyg(
                "%r finns inte; %d verktyg ar registrerade" % (namn, len(self.register)))
        return self.register[namn]

    def utfor(self, namn, argument=None):
        verktyg = self._verktyg(namn)
        # Formagegrinden fore allt annat: ett verktyg vars yta saknas ska
        # aldrig hinna generera kod (36_versioner.md).
        self.urval.krav(namn)
        args = validera_argument(verktyg, argument)

        if verktyg.mode == "data":
            resultat = self._data[namn](args)
            validera_resultat(verktyg, resultat)
            return Resultat(namn, verktyg.effect, verktyg.mode,
                            resultat=resultat)

        kod = self._kodgen[namn](args)
        if not isinstance(kod, str):
            raise Svarsfel("%s: the code generator returned %s, not a string"
                           % (namn, type(kod).__name__))

        # HAR, och ingen annanstans, valjs laget.
        op = op_for_effect(verktyg.effect)
        svar = self.klient.anrop(op, {
            "code": kod,
            "desc": verktyg.beskriv_anrop(args),
            "timeout_ms": verktyg.timeout_ms,
        })
        resultat = svar.get("result")

        if op == "exec_queue":
            qid = (resultat or {}).get("qid")
            if not qid:
                raise Svarsfel("%s: the bridge queued without returning a qid"
                               % namn)
            self.koade[qid] = namn
            return Resultat(namn, verktyg.effect, verktyg.mode, op=op, kod=kod,
                            koad=True, qid=qid, resultat=resultat,
                            stdout=svar.get("stdout", ""), svar=svar)

        if resultat is None:
            # Sista raden pa stdout var inte JSON. Da har mallen inte svarat,
            # och tystnad ar aldrig ett godkannande (I3).
            raise Svarsfel(
                "%s: sista raden pa stdout var ingen JSON; bryggans svarskanal "
                "ar tom. stdout: %r" % (namn, svar.get("stdout", "")))
        validera_resultat(verktyg, resultat)
        return Resultat(namn, verktyg.effect, verktyg.mode, op=op, kod=kod,
                        resultat=resultat, stdout=svar.get("stdout", ""),
                        svar=svar)

    def godkann(self, qid):
        """Tommer en kopost. Kon ska ha en tommare fran dag ett (30_arkitektur).

        Bryggan kor koden vid godkannandet och lagger dess svar i
        result.result (pump.py:_op_queue_approve). Forst DAR finns ett svar
        att prova mot verktygets returns-schema.
        """
        if qid not in self.koade:
            raise OkantVerktyg(
                "%r koades inte av den har utforaren; den vet inte vilket "
                "schema svaret ska provas mot" % (qid,))
        namn = self.koade[qid]
        verktyg = self._verktyg(namn)
        kvitto = (self.klient.anrop("queue_approve", {"qid": qid})
                  .get("result") or {})
        if kvitto.get("dodar_pumpen"):
            # Bryggan har sagt i forvag att den gar ned. Att polla efter ett
            # utfall vore att vanta pa ett svar som inte kan skickas.
            return Resultat(namn, verktyg.effect, verktyg.mode,
                            op="queue_approve", koad=False, qid=qid,
                            resultat=None, stdout="", svar=kvitto)
        post = self._vanta_pa_utfall(qid, namn)
        if post["state"] != "done":
            raise Svarsfel("%s: queue item %s ended as %r, not done"
                           % (namn, qid, post["state"]))
        svar = post.get("svar") or {}
        resultat = svar.get("result")
        if isinstance(resultat, dict) and "result" in resultat:
            resultat = resultat["result"]
        if resultat is None:
            raise Svarsfel(
                "%s: koposten kordes men sista raden pa stdout var ingen JSON. "
                "stdout: %r" % (namn, svar.get("stdout", "")))
        validera_resultat(verktyg, resultat)
        return Resultat(namn, verktyg.effect, verktyg.mode, op="queue_approve",
                        koad=False, qid=qid, resultat=resultat,
                        stdout=svar.get("stdout", ""), svar=svar)

    def _vanta_pa_utfall(self, qid, namn, timeout=None):
        """Godkannandet KVITTERAS bara; pumpen kor koden.

        Bryggan andrades av ett matt skal: kod som stoppar simuleringen dodar
        pumpens tasklet mitt i exec, och ett inline-godkannande forsvann da
        tillsammans med sitt eget svar (M-13). Utfallet lases darfor ur kon.
        """
        slut = time.time() + (timeout or self.ko_timeout_s)
        sist = None
        while time.time() < slut:
            for post in (self.klient.anrop("queue_list", {"with_result": True})
                         ["result"]["queue"]):
                if post["qid"] == qid:
                    sist = post
                    if post["state"] in ("done", "failed", "interrupted",
                                         "rejected"):
                        return post
            time.sleep(KO_POLL_S)
        raise Svarsfel("%s: queue item %s got no outcome within %.0f s (last: %r)"
                       % (namn, qid, timeout or self.ko_timeout_s,
                          (sist or {}).get("state")))
