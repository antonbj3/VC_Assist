# -*- coding: utf-8 -*-
"""C12: Kalibrering mot verkliga buggar och 82_felklasser.md."""
import json
import os
import sys

_ROT = "/home/anton/projects/VC_Assist"
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "bank"))

from vc_assist_svc.plc.mutation import _SKADOR, skador

# Mappning mellan 82_felklasser.md och mutationsmotorns sorter
FELKLASS_MAPP = {
    "F1 (Syntax)": [
        ("SEMIKOLON_STRUKET", "saknat semikolon i slutet av sats"),
        ("END_IF_STRUKEN", "obalanserade block"),
        ("ICKE_ASCII", "icke-ASCII-tecken"),
    ],
    "F2 (Okänt namn / symbol)": [
        ("FLANKENS_Q_TILL_SIGNAL", "funktionsblocksinstans använd som variabelnamn"),
    ],
    "F4 (Deklaration / Typ)": [
        ("TID_OGILTIG", "ogiltig tidsliteral utan enhet (fälls av validatorn)"),
        ("JAMFORELSE_VAND", "ogiltig operatorkombination (<> till >>)"),
    ],
    "F5 (Sekvens)": [
        ("TILLSTAND_FASTNAR", "steg := N struket; sekvensen avancerar aldrig"),
    ],
    "F6 (Timing)": [
        ("TID_FORDUBBLAD", "timerpreset fördubblat; kliver utanför tidsfönster"),
        ("TIMER_FORVAL_ANDRAS", "timerpreset ändrat under drift till 10 ms (förtida timeout)"),
    ],
    "F7 (Kapplöpning)": [
        ("FLANK_TAVLAR", "R_TRIG evaluerad sist i scan; .Q läses från föregående scan"),
    ],
    "F8 (Förregling)": [
        ("AND_TILL_OR", "förreglingsvillkor uppluckrat (bara ett led krävs)"),
        ("OR_TILL_AND", "förreglingsvillkor skärpt (båda leden krävs)"),
        ("NOT_STRUKEN", "förregling inverterad (villkor gäller tvärtom)"),
        ("SANT_TILL_FALSKT", "aktiveringsvillkor fallerar"),
        ("FALSKT_TILL_SANT", "avstängningsvillkor fallerar"),
        ("KVARHALLEN_UTGANG_STOPP", "utgång inte nollställd vid nödstopp/fel (kvarhållen spänning)"),
        ("LARM_KVITTERAT_UTAN_ORSAK", "förregling mot kvittering vid aktivt fel saknas"),
    ],
    "F15 (Flank och latch)": [
        ("FLANK_TILL_NIVA", "trig.Q bytt mot CLK-signalen; villkor läst på nivå (M-115/M-122)"),
        ("FLANK_STRUKEN", "flankanrop struket; Q förblir falsk för evigt"),
        ("RETENTIV_FORLORAD", "RETAIN struket; tillstånd förlorat över omstart"),
    ],
}

ICKE_KOD_KLASSER = {
    "F3 (Fel tagg)": "Tillhör signalkartans koppling mot I/O-moduler (grind 3), inte algoritmisk kod.",
    "F9 (Geometri)": "Kollisioner och räckvidd i VC-scenen (ögat, SAFETY).",
    "F10 (Grepp)": "Fysiskt grepp, glidning och vakuumfysik i simuleringen (ögat, MOTION).",
    "F11 (Genomflöde)": "Kapacitetsmål och cykeltider över en simulerad timme (ögat, THROUGHPUT).",
    "F12 (Ohederlig)": "Teleportering och fysikfusk i VC (ögat, HONESTY).",
    "F13 (Verktygsfel)": "LLM-agentens verktygsanrop i samtalsloopen.",
    "F14 (Annat)": "Slaskklass; ska enligt spec hållas nära noll.",
}

HISTORISKA_BUGGAR = [
    ("M-106", "Tolkfel i dubbelflank på samma signal", "FLANKENS_Q_TILL_SIGNAL / FLANK_TAVLAR"),
    ("M-115", "Flank läses på nivå; spår blint vid enskottssekvens", "FLANK_TILL_NIVA"),
    ("M-121", "DUBBELSKRIVNING och TYP i referenser", "FALSKT_TILL_SANT / TID_OGILTIG"),
    ("M-40", "Matning fyrade aldrig p.g.a. tyst förregling", "AND_TILL_OR / NOT_STRUKEN"),
    ("M-54", "Kod som kompilatorn avvisar godkändes av tolk", "TID_OGILTIG / SEMIKOLON_STRUKET"),
    ("M-79", "Dubbelskrivning i referensens logik", "KVARHALLEN_UTGANG_STOPP"),
]

print("=== C12: KALIBRERING MOT VERKLIGA BUGGAR ===")
print("Alla kodapplicerbara felklasser i 82_felklasser.md:")
for fk, sorter in sorted(FELKLASS_MAPP.items()):
    print("\n%s:" % fk)
    for sort, besk in sorter:
        print("  - %-26s: %s" % (sort, besk))

print("\n" + "=" * 60)
print("Icke-kodapplicerbara felklasser (fysik/scen/agent):")
for fk, orsak in sorted(ICKE_KOD_KLASSER.items()):
    print("  %-20s: %s" % (fk, orsak))

print("\n" + "=" * 60)
print("Repots historiska buggar och motsvarande mutationssort:")
for m_nr, bugg, sort in HISTORISKA_BUGGAR:
    print("  %-8s %-50s -> %s" % (m_nr, bugg, sort))

