# -*- coding: utf-8 -*-
"""PackML-mallen: ISA-TR88.00.02:s tillståndsmaskin som en färdig kodmall.

## Varför en klassisk generator FÅR ha den här mallen

En tillståndsmaskin som är **publicerad standard** är precis vad ett
mallbibliotek är till för. Beckhoff levererar `E_PMLState` med kommentaren
*"states according to PackTags v3.0"*, Omron har den i sin
implementationsguide, och OPC 30050 v1.01 bär samma numrering. En integratör
som ska bygga PackML skriver inte tillståndsmaskinen; hen instansierar den.

Det gör den här mallen till baslinjens starkaste kort, och det är ett ärligt
kort. M-62 skriver ut vad det betyder: **på en uppgift som ÄR en standard
vinner mallen**, och en språkmodell måste vara bättre än en avskrift av
standarden för att vara värd sin kostnad där.

## Vad mallen INTE vet

Vilken maskin den styr. Mallen ger tillståndsmaskinen och kopplar don till
tillstånd genom förreglingsraden "X far vara hog enbart nar STATE ar 6".
Allt annat i en PackML-station — vad EXECUTE faktiskt gör — ligger utanför.

## Numreringen och matrisen

Tillstånd 1–17 och kommandon 1–9 enligt PackTags v3.0. Tre regler ur matrisen
som en genväg alltid bryter mot, och som därför står utskrivna:

* `ABORT` går aldrig direkt till `STOPPED`. Den går till `ABORTING`, och först
  på State Complete till `ABORTED`. Giltig i 15 av 17 tillstånd.
* Enda vägen ut ur `ABORTED` är `CLEAR`.
* `HOLD` och `SUSPEND` är olika grenar. `HOLDING` är internt, `SUSPENDING`
  externt.

beskriver: svc/vc_assist_svc/plc/baslinje/packml.py
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

# Tillståndsnummer, PackTags v3.0. Namnen står med för att koden ska gå att
# läsa; numren är det som skrivs på ST..._PML_STATE.
CLEARING = 1
STOPPED = 2
STARTING = 3
IDLE = 4
SUSPENDED = 5
EXECUTE = 6
STOPPING = 7
ABORTING = 8
ABORTED = 9
HOLDING = 10
HELD = 11
UNHOLDING = 12
SUSPENDING = 13
UNSUSPENDING = 14
RESETTING = 15
COMPLETING = 16
COMPLETE = 17

TILLSTANDSNAMN = {
    CLEARING: "CLEARING", STOPPED: "STOPPED", STARTING: "STARTING",
    IDLE: "IDLE", SUSPENDED: "SUSPENDED", EXECUTE: "EXECUTE",
    STOPPING: "STOPPING", ABORTING: "ABORTING", ABORTED: "ABORTED",
    HOLDING: "HOLDING", HELD: "HELD", UNHOLDING: "UNHOLDING",
    SUSPENDING: "SUSPENDING", UNSUSPENDING: "UNSUSPENDING",
    RESETTING: "RESETTING", COMPLETING: "COMPLETING", COMPLETE: "COMPLETE",
}

# CntrlCmd 1–9.
CMD_RESET = 1
CMD_START = 2
CMD_STOP = 3
CMD_HOLD = 4
CMD_UNHOLD = 5
CMD_SUSPEND = 6
CMD_UNSUSPEND = 7
CMD_ABORT = 8
CMD_CLEAR = 9

# De verkande tillstånden: de lämnas på State Complete, inte på ett kommando.
PA_STATE_COMPLETE: Dict[int, int] = {
    CLEARING: STOPPED,
    STARTING: EXECUTE,
    STOPPING: STOPPED,
    ABORTING: ABORTED,
    HOLDING: HELD,
    UNHOLDING: EXECUTE,
    SUSPENDING: SUSPENDED,
    UNSUSPENDING: EXECUTE,
    RESETTING: IDLE,
    COMPLETING: COMPLETE,
    EXECUTE: COMPLETING,
}

# Kommando -> (tillstånden där det är giltigt, tillståndet det leder till).
# ABORT och STOP anges som undantagslistor därför att det är så matrisen är
# skriven: de är giltiga nästan överallt, och en uppräkning av de giltiga
# hade tappat ett tillstånd tyst nästa gång listan ändras.
ALLA_TILLSTAND = tuple(sorted(TILLSTANDSNAMN))
KOMMANDON: Dict[int, Tuple[Tuple[int, ...], int]] = {
    CMD_ABORT: (tuple(t for t in ALLA_TILLSTAND if t not in (ABORTING, ABORTED)),
                ABORTING),
    CMD_STOP: (tuple(t for t in ALLA_TILLSTAND
                     if t not in (STOPPING, STOPPED, ABORTING, ABORTED,
                                  CLEARING)),
               STOPPING),
    CMD_CLEAR: ((ABORTED,), CLEARING),
    CMD_RESET: ((STOPPED, COMPLETE), RESETTING),
    CMD_START: ((IDLE,), STARTING),
    CMD_HOLD: ((EXECUTE,), HOLDING),
    CMD_UNHOLD: ((HELD,), UNHOLDING),
    CMD_SUSPEND: ((EXECUTE,), SUSPENDING),
    CMD_UNSUSPEND: ((SUSPENDED,), UNSUSPENDING),
}

# Tillstånden där samlingslarmet står högt. Abortgrenen och bara den: ett larm
# i STOPPING hade gjort ett normalt stopp till ett fel.
LARMTILLSTAND = (ABORTING, ABORTED)


def ar_packml(karta) -> bool:
    """Sant när kartan bär en PackML-styrd station.

    Dispatchen sker på SIGNALFORMEN — ett heltalstillstånd ut, ett
    heltalskommando in och en State Complete-bit — aldrig på uppgiftens
    nummer. En generator som känner igen uppgiften mäter ingenting.
    """
    har_state = har_cmd = har_sc = False
    for t in karta.taggar:
        if t.enhet != "PML":
            continue
        if t.suffix == "STATE" and t.ar_utgang and t.typ == "int":
            har_state = True
        elif t.suffix == "CMD" and not t.ar_utgang and t.typ == "int":
            har_cmd = True
        elif t.suffix == "SC" and not t.ar_utgang and t.typ == "bool":
            har_sc = True
    return har_state and har_cmd and har_sc


def taggar(karta) -> Dict[str, str]:
    ut: Dict[str, str] = {}
    for t in karta.taggar:
        if t.enhet == "PML":
            ut[t.suffix] = t.namn
    return ut


def kropp(karta, felvillkor: Sequence[str], trig_sc: str, statevar: str,
          indrag: int = 0) -> List[str]:
    """Tillståndsmaskinens rader. `felvillkor` är de uttryck som ger ABORTING.

    `trig_sc` är namnet på R_TRIG-instansen över State Complete: standarden
    lämnar ett verkande tillstånd på en FLANK, och en nivåläsning hoppar över
    ett helt tillstånd när biten står kvar.

    `statevar` är en INTERN heltalsvariabel och inte kartans utgång. Två skäl,
    båda mätta: en utgång ur signalkartan deklareras utan startvärde, och
    PackML börjar i STOPPED (2) och inte i 0 — och grind 2 fäller en utgång som
    skrivs på två ställen som kan köras i samma scan (`DUBBELSKRIVNING`),
    vilket både felgrenen och kommandogrenen gör. Utgången skrivs därför en
    enda gång, av anroparen, ur den interna variabeln.
    """
    namn = taggar(karta)
    state, cmd = statevar, namn["CMD"]
    i = " " * indrag
    rader: List[str] = []
    rader.append(i + "(* PackML, ISA-TR88.00.02 Production Mode. Tillstands- *)")
    rader.append(i + "(* och kommandonumren ar PackTags v3.0.               *)")
    if felvillkor:
        villkor = " OR ".join("(%s)" % v for v in felvillkor)
        rader.append(i + "IF (%s) AND %s <> %d AND %s <> %d THEN"
                     % (villkor, state, ABORTING, state, ABORTED))
        rader.append(i + "    %s := %d;   (* maskinfel -> ABORTING *)"
                     % (state, ABORTING))
        rader.append(i + "ELSE")
        inre = i + "    "
    else:
        inre = i
    rader.extend(_kommandogren(state, cmd, inre))
    rader.extend(_completegren(state, trig_sc, inre))
    if felvillkor:
        rader.append(i + "END_IF;")
    return rader


def _kommandogren(state: str, cmd: str, i: str) -> List[str]:
    rader = [i + "CASE %s OF" % cmd]
    for k in sorted(KOMMANDON):
        giltiga, mal = KOMMANDON[k]
        rader.append(i + "    %d:  (* %s *)" % (k, _kommandonamn(k)))
        villkor = _tillstandsvillkor(state, giltiga)
        rader.append(i + "        IF %s THEN" % villkor)
        rader.append(i + "            %s := %d;  (* -> %s *)"
                     % (state, mal, TILLSTANDSNAMN[mal]))
        rader.append(i + "        END_IF;")
    rader.append(i + "END_CASE;")
    return rader


def _completegren(state: str, trig_sc: str, i: str) -> List[str]:
    rader = [i + "IF %s.Q THEN" % trig_sc,
             i + "    CASE %s OF" % state]
    for fran in sorted(PA_STATE_COMPLETE):
        till = PA_STATE_COMPLETE[fran]
        rader.append(i + "        %d: %s := %d;  (* %s -> %s *)"
                     % (fran, state, till, TILLSTANDSNAMN[fran],
                        TILLSTANDSNAMN[till]))
    rader.append(i + "    END_CASE;")
    rader.append(i + "END_IF;")
    return rader


def _tillstandsvillkor(state: str, giltiga: Sequence[int]) -> str:
    """Villkoret "state är ett av dessa", skrivet kort när listan är lång.

    Är de giltiga fler än hälften skrivs undantagen i stället. Det är inte
    kosmetik: en rad med femton OR-led är en rad ingen läser, och en
    kodgenerator som producerar oläsbar kod har halverat sitt eget värde.
    """
    giltiga = tuple(sorted(set(giltiga)))
    ogiltiga = tuple(t for t in ALLA_TILLSTAND if t not in giltiga)
    if len(ogiltiga) < len(giltiga):
        return " AND ".join("%s <> %d" % (state, t) for t in ogiltiga)
    return " OR ".join("%s = %d" % (state, t) for t in giltiga)


def _kommandonamn(k: int) -> str:
    return {CMD_RESET: "Reset", CMD_START: "Start", CMD_STOP: "Stop",
            CMD_HOLD: "Hold", CMD_UNHOLD: "Unhold", CMD_SUSPEND: "Suspend",
            CMD_UNSUSPEND: "Unsuspend", CMD_ABORT: "Abort",
            CMD_CLEAR: "Clear"}[k]
