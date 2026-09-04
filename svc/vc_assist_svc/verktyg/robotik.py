# -*- coding: utf-8 -*-
"""Domanen robot: robotens konfiguration, dess program och dess korning.

Kalla for urvalet: 45_verktyg.md, avsnittet "robot". Tabellen dar namner atta
verktyg. Har byggs tjugofyra, och de atta spec-namnen ar kvar dar de gar att
halla. Tre av dem gar INTE att halla ordagrant, och skalen ar matta:

  * `create_target` som eget verktyg gar inte att bygga. Ett vcMotionTarget ar
    ett objekt i VC:s Python-scope, och bryggan kor varje anrop i sitt EGET
    scope (pump.py:_kor bygger nya exec-globaler per korning,
    31_brygga_protokoll.md). Ett mal som skapas i ett anrop finns alltsa inte
    i nasta. Det som DERSISTERAR ar styrenhetens mallista. Darfor blev
    `create_target` + `add_target` ett verktyg som bygger malet OCH lagger det
    i listan, och `move_targets` som kor hela listan i EN korning.
  * `clear_targets` som eget verktyg vore ett tredje kobesok for samma
    rorelse. `move_targets` tommer listan sjalv innan den fyller den, och
    `clear_targets` finns som lage i samma verktyg.
  * `get_joints` och `robot_limits` ar kvar med sina spec-namn.

VAD SOM AR OPROVAT, SAGT RAKT
-----------------------------
MATT 2026-09-04: den lokala komponentkatalogen innehaller NOLL komponenter.
Det finns alltsa ingen robot att prova mot, och inget verktyg har kort mot en
levande VC. Det som ar provat ar allt som gar att prova utan VC: schemat,
argumentvalideringen, routingen, korsprovet mot bryggans skrivgrind och
korsprovet mot API-indexet. Det som ar OPROVAT ar att VC svarar som kallan
sager. Det star sa i rapporten och det star sa har.

HUR ROBOTEN HITTAS, OCH VARFOR INTE PA EN KONSTANT
--------------------------------------------------
Det finns ingen typ `vcRobot` i den matta API-ytan. En robot ar en KOMPONENT
som bar ett beteende av typen vcRobotController. Beteendet kanns igen pa sin
YTA - Joints, Bases och Tools tillsammans - och inte pa konstanten
VC_ROBOTCONTROLLER. Skalet ar samma som i granssnitt.py: formaga.py provar
ATTRIBUT pa objekt, inte namn i en modul, sa en konstant gar inte att
formageprova, och en konstant som saknas ger NameError i stallet for ett
begripligt svar (36_versioner.md).

Programsidan har TVA slakter i VC, och de ar inte utbytbara:

    vcExecutor            Program ar ett vcProgram med Routines och
                          Statements. callStatement finns. Detta ar den
                          slakt verktygen har arbetar med.
    vcRslProgramExecutor  Program ar en STRANG. MainRoutine och SubRoutines
                          i stallet for vcProgram. callStatement finns inte.

Slakterna skiljs at pa ytan (Program + callStatement mot MainRoutine +
SubRoutines). RSL-slakten LASES sa langt att den namns - `robot_info` och
`program_state` svarar program_family="rsl" - men den manipuleras inte. Det
ar en uttalad grans, inte en stubbe: att skriva RSL-program kraver en egen
uppsattning verktyg mot vcRslRoutine och vcRslStatement, och den byggs den
dag det finns en RSL-robot att prova mot.

FORMAGEGRINDEN OCH DE YTOR SOM INTE GAR ATT DEKLARERA
-----------------------------------------------------
`kraver` far bara namna ytor som star i formaga.YTOR, for det ar de enda
grinden kan prova. INGEN robotyta star dar: listan slutar vid komponenten och
noden. Foljden ar att varje verktyg har deklarerar de ytor det faktiskt gar
igenom PA VAGEN till roboten - app.findComponent, comp.Behaviours, comp.Name
och slaktingarna - medan robotytorna (Joints, createTarget, Program ...)
provas PER OBJEKT i mallen med hasattr. Exakt samma losning som granssnitt.py
gor for canConnect och Sections, och av samma skal.

Det ar inte idealet. Idealet vore rader i formaga.YTOR for
robot.Joints, robot.createTarget, executor.Program och de ovriga, sa att ett
robotverktyg kan slas AV med ett skal i stallet for att falla med ett
ValueError inne i VC. Den filen ligger utanfor den har cellens skrivstaket.
Den cell som kopplar in modulen bor lagga till dem, och da kan `kraver` nedan
skarpas utan att nagon mall behover andras.

VARFOR MALLARNA SKRIVER KEDJAN RAKT UT
---------------------------------------
scen.py och granssnitt.py gar via hjalparna _komp och _nod. Det ar
lattlast, men det har en MATT kostnad: api_index.Validator foljer inte typer
genom en egendefinierad funktion, sa `_komp("R").Uri` blir OKAND for den.
Matt 2026-09-04 over de befintliga mallarna: 1 kontrollerat namn per mall.
Samma kod med kedjan utskriven - getApplication().findComponent(...) - ger
12 och uppat, och en uppfunnen medlem FALLER. Robotmallarna skriver darfor
kedjan rakt ut. Matt over den har domanens tjugofyra mallar: se
tests/enhet/test_verktyg_robotik.py, som raknar om talet vid varje korning.

SKRIVGRINDEN AVGOR VAD SOM AR LASNING
--------------------------------------
Tva verktyg som i sak bara FRAGAR - `check_reach` och `forward_kinematics` -
ar anda deklarerade write. Skalet ar mekaniskt och avsiktligt: bada maste
anropa ctrl.createTarget(), och bryggans skrivgrind domer varje create*-anrop
som skrivande (skrivgrind.MUTERANDE_PREFIX). Ett verktyg som deklarerar read
men vars kod grinden domer som skrivande skulle avvisas av bryggan med
E_NOT_APPROVED och alltsa aldrig fungera. Deklarationen foljer grinden, inte
tvartom. Bada verktygens beskrivning sager rakt ut att de gar genom kon.
"""
from __future__ import annotations

from .bas import (RET_ANTAL, RET_AVKORTAD, TIMEOUT_MS, XYZ, laggare, params,
                  returns, tak)
from .fel import Argumentfel
from .kodmall import bygg, lit, tal

DOMAN = "robot"
_lagg = laggare(DOMAN)

# Tak for en korning som far VC att RORA sig eller att kora program.
# PRELIMINART. Harkomsten ar en matning som inte gar att gora: MATT
# 2026-09-04 finns noll komponenter i den lokala katalogen, alltsa ingen
# robot vars rorelsetid gar att tidta. Talet ar satt lika med bas.
# TIMEOUT_MS_FIL (60 s), som ar samma slag av grans - en operation som tar
# sekunder snarare an millisekunder - och ska ersattas av en matning sa snart
# en robot finns i layouten (fas 5, 70_faser.md). Ett overskridande ar inte
# tyst: bryggan svarar E_TIMEOUT och markerar sig degraded.
TIMEOUT_MS_RORELSE = 60000

# ---- ytor som formagegrinden faktiskt kan prova -------------------------
#
# Robotytorna star inte i formaga.YTOR (se modulens docstring). Det som
# deklareras ar vagen FRAM till roboten, och den ar sann: varje mall slar upp
# komponenten och gar igenom dess beteendelista.
_YTOR_ROBOT = ("app.findComponent", "comp.Name", "comp.Behaviours")
_YTOR_LAYOUT = ("app.Components", "comp.Name", "comp.Behaviours")
# Mallar som ocksa laser en nod (flanslage, verktygsramens nod).
_YTOR_ROBOT_NOD = _YTOR_ROBOT + ("node.WorldPositionMatrix",)
# Mallar som ocksa slar upp en nod pa namn.
_YTOR_ROBOT_FINDNODE = _YTOR_ROBOT + ("comp.findNode", "node.WorldPositionMatrix")
# Mallar som laser komponentens egna egenskaper (nyttolast).
_YTOR_ROBOT_EGENSKAPER = _YTOR_ROBOT + ("comp.Properties",)
# Mallar som fragar om simuleringen kor - ett program utfors bara da.
_YTOR_ROBOT_SIM = _YTOR_ROBOT + ("sim.IsRunning",)


# ---- upprakningar: etikett i schemat, VC-konstant i koden ----------------
#
# Modellen ser laslig text; mallen skriver VC:s eget namn. Varje konstant
# nedan ar slagen upp i api_index (docs/referens/vc_api/constants.xml) och
# provas om vid varje testkorning, sa ett uppfunnet konstantnamn kan inte bo
# kvar har. Ordningen ar den ordning enum-listan far i schemat.

RORELSETYPER = (
    ("joint", "VC_MOTIONTARGET_MT_JOINT"),
    ("linear", "VC_MOTIONTARGET_MT_LINEAR"),
    ("circular", "VC_MOTIONTARGET_MT_CIRCLE"),
    ("spline", "VC_MOTIONTARGET_MT_SPLINE"),
)

MALLAGEN = (
    ("normal", "VC_MOTIONTARGET_TM_NORMAL"),
    ("world", "VC_MOTIONTARGET_TM_WORLDTARGET"),
    ("robot_root", "VC_MOTIONTARGET_TM_ROBOTROOT"),
    ("external_base", "VC_MOTIONTARGET_TM_EXTERNALBASE"),
    ("static_tool", "VC_MOTIONTARGET_TM_STATICTOOL"),
)

ZONMETODER = (
    ("distance", "VC_MOTIONTARGET_AM_DISTANCE"),
    ("time", "VC_MOTIONTARGET_AM_TIME"),
    ("velocity", "VC_MOTIONTARGET_AM_VELOCITY"),
)

KONFIGLAGEN = (
    ("fixed", "VC_MOTIONTARGET_CM_FIXED"),
    ("follow_frame", "VC_MOTIONTARGET_CM_FOLLOW_FRAME"),
    ("interpolate_joints", "VC_MOTIONTARGET_CM_INTERPOLATE_JOINT_VALUES"),
)

NARMNINGSAXLAR = (
    ("positive_x", "VC_APPROACH_AXIS_POSITIVE_X"),
    ("positive_y", "VC_APPROACH_AXIS_POSITIVE_Y"),
    ("positive_z", "VC_APPROACH_AXIS_POSITIVE_Z"),
    ("negative_x", "VC_APPROACH_AXIS_NEGATIVE_X"),
    ("negative_y", "VC_APPROACH_AXIS_NEGATIVE_Y"),
    ("negative_z", "VC_APPROACH_AXIS_NEGATIVE_Z"),
)

# Bitarna i getConfigWarning(). MATT ur kallans egen beskrivning:
# "The returned value indicates singularity (S), joint limits (J) and
# unreachable (U) errors using a format of SJU", 0..7. Konstanterna anvands i
# stallet for talen 1, 2 och 4 sa att inget magiskt tal star i mallen.
VARNINGSBITAR = (
    ("unreachable", "VC_MOTIONTARGET_KW_UNREACHABLE"),
    ("joint_limit", "VC_MOTIONTARGET_KW_JOINTLIMIT"),
    ("singular", "VC_MOTIONTARGET_KW_SINGULAR"),
)
VARNING_OK = "VC_MOTIONTARGET_KW_OK"

# Satstyper som add_statement far skapa, och som read_routine kan etikettera.
#
# VC_STATEMENT_SCRIPT saknas MED FLIT. En skriptsats bar godtycklig Python in
# i operatorens program; att lata modellen skapa en vore att oppna en vag
# forbi bade skrivgrinden och godkannandekon (I15:s anda: genererad kod hor
# inte hemma dar den inte kan granskas). Behovs den ska den bli ett eget
# verktyg med sin egen grind.
#
# Rorelsesatserna star med i kartan men INTE i add_statement:s enum. De skapas
# av add_motion_statement, som ocksa kan satta lage, ram och zon. Tva vagar
# till samma sats vore en vag for mycket.
SATSTYPER = (
    ("comment", "VC_STATEMENT_COMMENT"),
    ("delay", "VC_STATEMENT_DELAY"),
    ("grasp", "VC_STATEMENT_GRASP"),
    ("release", "VC_STATEMENT_RELEASE"),
    ("wait_signal", "VC_STATEMENT_WAITSIGNAL"),
    ("wait_binary_input", "VC_STATEMENT_WAITBIN"),
    ("set_binary_output", "VC_STATEMENT_SETBIN"),
    ("send_signal", "VC_STATEMENT_SENDSIGNAL"),
    ("if", "VC_STATEMENT_IF"),
    ("while", "VC_STATEMENT_WHILE"),
    ("switch_case", "VC_STATEMENT_SWITCHCASE"),
    ("break", "VC_STATEMENT_BREAK"),
    ("continue", "VC_STATEMENT_CONTINUE"),
    ("return", "VC_STATEMENT_RETURN"),
    ("call", "VC_STATEMENT_CALL"),
    ("halt", "VC_STATEMENT_HALT"),
    ("home", "VC_STATEMENT_HOME"),
    ("print", "VC_STATEMENT_PRINT"),
    ("set_property", "VC_STATEMENT_SETPROPERTY"),
    ("get_property", "VC_STATEMENT_GETPROPERTY"),
    ("path", "VC_STATEMENT_PATH"),
    ("motion_mode", "VC_STATEMENT_MOTIONMODE"),
    ("run_robot_routine", "VC_STATEMENT_RUNROBOTROUTINE"),
)

RORELSESATSER = (
    ("motion_joint", "VC_STATEMENT_PTPMOTION"),
    ("motion_linear", "VC_STATEMENT_LINMOTION"),
)

# Kartan read_routine etiketterar med. Rorelsesatserna forst sa att en
# rorelsesats far sitt egna namn och inte en efterslapande dubblett.
TYPKARTA = RORELSESATSER + SATSTYPER

# Varje VC-namn den har modulen skriver in i en mall, med den typ det lases
# pa. Listan ar inte dekoration: tests/enhet/test_verktyg_robotik.py slar upp
# varje rad i api_index OCH kraver att inget VC-namn i nagon genererad mall
# saknas har. Ett uppfunnet namn kan darfor varken sta i listan eller smyga
# forbi den. Formen ar (typ, medlem); typen ar den agande typen i api.xml.
VC_MEDLEMMAR = (
    ("vcApplication", "Components"),
    ("vcApplication", "findComponent"),
    ("vcComponent", "Name"),
    ("vcComponent", "Behaviours"),
    ("vcComponent", "Properties"),
    ("vcComponent", "findNode"),
    ("vcNode", "Name"),
    ("vcNode", "WorldPositionMatrix"),
    ("vcNode", "localToWorld"),
    ("vcProperty", "Name"),
    ("vcProperty", "Value"),
    ("vcBehaviour", "Name"),
    ("vcRobotController", "Joints"),
    ("vcRobotController", "JointCount"),
    ("vcRobotController", "Bases"),
    ("vcRobotController", "Tools"),
    ("vcRobotController", "Speed"),
    ("vcRobotController", "MaxCartesianSpeed"),
    ("vcRobotController", "MaxCartesianAccel"),
    ("vcRobotController", "MaxAngularSpeed"),
    ("vcRobotController", "MaxAngularAccel"),
    ("vcRobotController", "LagTime"),
    ("vcRobotController", "SettleTime"),
    ("vcRobotController", "InitialTool"),
    ("vcRobotController", "InitialBase"),
    ("vcRobotController", "ApproachAxis"),
    ("vcRobotController", "ConfigurationMode"),
    ("vcRobotController", "TrackWorldFrameMode"),
    ("vcRobotController", "WorldTransformMatrix"),
    ("vcRobotController", "FlangeNode"),
    ("vcRobotController", "RootNode"),
    ("vcRobotController", "getJointValue"),
    ("vcRobotController", "getJointTarget"),
    ("vcRobotController", "createTarget"),
    ("vcRobotController", "addTarget"),
    ("vcRobotController", "clearTargets"),
    ("vcRobotController", "move"),
    ("vcRobotController", "moveTo"),
    ("vcRobotController", "moveImmediate"),
    ("vcRobotController", "addTool"),
    ("vcRobotController", "addBase"),
    ("vcJoint", "Name"),
    ("vcJoint", "Type"),
    ("vcJoint", "CurrentValue"),
    ("vcJoint", "InitialValue"),
    ("vcJoint", "MinValue"),
    ("vcJoint", "MaxValue"),
    ("vcJoint", "MaxSpeed"),
    ("vcJoint", "MaxAcceleration"),
    ("vcJoint", "MaxDeceleration"),
    ("vcJoint", "LagTime"),
    ("vcJoint", "SettleTime"),
    ("vcBaseFrame", "Name"),
    ("vcBaseFrame", "Node"),
    ("vcBaseFrame", "PositionMatrix"),
    ("vcBaseFrame", "PositionExpression"),
    ("vcBaseFrame", "IPOMode"),
    ("vcMotionTarget", "MotionType"),
    ("vcMotionTarget", "TargetMode"),
    ("vcMotionTarget", "Target"),
    ("vcMotionTarget", "UseJoints"),
    ("vcMotionTarget", "JointValues"),
    ("vcMotionTarget", "JointSpeedFactor"),
    ("vcMotionTarget", "CartesianSpeed"),
    ("vcMotionTarget", "CartesianAcceleration"),
    ("vcMotionTarget", "AngularSpeed"),
    ("vcMotionTarget", "AccuracyMethod"),
    ("vcMotionTarget", "AccuracyValue"),
    ("vcMotionTarget", "BaseName"),
    ("vcMotionTarget", "ToolName"),
    ("vcMotionTarget", "RobotConfig"),
    ("vcMotionTarget", "ConfigCount"),
    ("vcMotionTarget", "getConfigWarning"),
    ("vcExecutor", "Program"),
    ("vcExecutor", "CurrentStatement"),
    ("vcExecutor", "IsEnabled"),
    ("vcExecutor", "IsLooping"),
    ("vcExecutor", "UseExternalExecutor"),
    ("vcExecutor", "callRoutine"),
    ("vcExecutor", "callStatement"),
    ("vcRslProgramExecutor", "MainRoutine"),
    ("vcRslProgramExecutor", "SubRoutines"),
    ("vcProgram", "Name"),
    ("vcProgram", "MainRoutine"),
    ("vcProgram", "Routines"),
    ("vcProgram", "addRoutine"),
    ("vcProgram", "findRoutine"),
    ("vcProgram", "deleteRoutine"),
    ("vcRoutine", "Name"),
    ("vcRoutine", "Statements"),
    ("vcRoutine", "addStatement"),
    ("vcRoutine", "getStatement"),
    ("vcRoutine", "deleteStatement"),
    ("vcStatement", "Name"),
    ("vcStatement", "Type"),
    ("vcStatement", "Properties"),
    ("vcStatement", "ParentRoutine"),
    ("vcStatement", "getProperty"),
    ("vcMotionStatement", "Base"),
    ("vcMotionStatement", "Tool"),
    ("vcMotionStatement", "AccuracyMethod"),
    ("vcMotionStatement", "AccuracyValue"),
    ("vcMotionStatement", "CycleTime"),
    ("vcMotionStatement", "ExternalTCP"),
    ("vcPositionStatement", "Positions"),
    ("vcPositionStatement", "createPosition"),
    ("vcPositionFrame", "Name"),
    ("vcPositionFrame", "JointValues"),
    ("vcPositionFrame", "PositionInReference"),
    ("vcPositionFrame", "PositionInWorld"),
    ("vcPositionFrame", "setJoints"),
    ("vcIfStatement", "ThenScope"),
    ("vcIfStatement", "ElseScope"),
    ("vcIfStatement", "ElseIfScopes"),
    ("vcScopeStatement", "Scope"),
    ("vcSwitchCaseStatement", "Cases"),
    ("vcScope", "Statements"),
    ("vcMatrix", "new"),
    ("vcMatrix", "P"),
    ("vcMatrix", "getWPR"),
    ("vcMatrix", "setWPR"),
    ("vcVector", "new"),
    ("vcVector", "X"),
    ("vcVector", "Y"),
    ("vcVector", "Z"),
)

# Modulfunktioner ur vcScript. De star inte i nagon matt kalla som
# modulfunktioner (api_index sager det sjalv), men bada finns ocksa som
# metoder pa en skripttyp och gar darfor att sla upp.
VC_MODULFUNKTIONER = ("getApplication", "getSimulation")


def _konstantnamn():
    """Varje VC_-konstant den har modulen skriver in i en mall."""
    ut = [VARNING_OK]
    for grupp in (RORELSETYPER, MALLAGEN, ZONMETODER, KONFIGLAGEN,
                  NARMNINGSAXLAR, VARNINGSBITAR, TYPKARTA):
        for _etikett, konstant in grupp:
            ut.append(konstant)
    return tuple(sorted(set(ut)))


VC_KONSTANTER = _konstantnamn()


def _konstant(grupp, etikett):
    """Etikett ur schemat -> VC:s eget konstantnamn. Kastar pa okand etikett."""
    for e, konstant in grupp:
        if e == etikett:
            return konstant
    raise KeyError("%r star inte i upprakningen; schemat och kartan har "
                   "glidit isar" % (etikett,))


def _etiketter(grupp):
    return [e for e, _k in grupp]


# ---- aterkommande schemabitar -------------------------------------------

ARG_ROBOT = {
    "type": "string",
    "description": ("Robotkomponentens namn i layouten, exakt som det star i "
                    "scenen."),
}
ARG_STYRENHET = {
    "type": "string",
    "description": ("Robotstyrenhetens beteendenamn. Utelamnad tar den forsta "
                    "styrenheten i komponenten, vilket racker for en robot med "
                    "en enda arm."),
}
ARG_RUTIN = {
    "type": "string",
    "description": ("Rutinens namn i programmet. Utelamnad betyder "
                    "huvudrutinen."),
}
ARG_SATSINDEX = {
    "type": "integer",
    "description": "Satsens plats i rutinen. Den forsta satsen har index 0.",
}
ARG_RAM_BAS = {
    "type": "string",
    "description": ("Basramens namn i styrenheten. Utelamnad lamnar det som "
                    "styrenheten redan anvander."),
}
ARG_RAM_VERKTYG = {
    "type": "string",
    "description": ("Verktygsramens namn i styrenheten. Utelamnad lamnar det "
                    "som styrenheten redan anvander."),
}
ARG_EGENSKAPER = {
    "type": "object",
    "description": ("Egenskaper att satta pa satsen, som namn -> varde. "
                    "Namnen maste finnas pa satsen; las dem forst med "
                    "read_routine. Varden far vara text, tal eller "
                    "sant/falskt."),
}

RET_ROBOT = {"type": "string", "description": "Robotkomponenten som lastes."}
RET_STYRENHET = {"type": "string",
                 "description": "Robotstyrenhetens beteendenamn."}
RET_RUTIN = {"type": "string", "description": "Rutinen som rordes."}

XYZ_NULLBAR = dict(XYZ, type=["array", "null"])

_PROGRAMSLAKT = {
    "type": "string",
    "description": ("Vilken programslakt roboten bar: executor (vcExecutor "
                    "med vcProgram), rsl (vcRslProgramExecutor) eller ingen. "
                    "Programverktygen arbetar bara med executor."),
}

_EGENSKAPSPOST = {
    "type": "object",
    "description": "En egenskap med sitt varde.",
    "properties": {
        "name": {"type": "string", "description": "Egenskapens namn."},
        "value": {"type": ["string", "number", "boolean", "integer", "null"],
                  "description": ("Vardet. Varden VC inte kan ge som enkel typ "
                                  "kommer som text.")},
    },
}

_LEDPOST = {
    "type": "object",
    "description": "En led i roboten.",
    "properties": {
        "index": {"type": "integer", "description": "Ledens plats i kedjan."},
        "name": {"type": "string", "description": "Ledens namn."},
        "type": {"type": ["string", "number", "integer", "null"],
                 "description": ("VC:s upprakning for ledtypen. Slag upp den "
                                 "med lookup_api om du behover namnet.")},
        "current_value": {"type": "number",
                          "description": "Ledens varde nu, grader eller mm."},
        "target_value": {"type": "number",
                         "description": "Vardet leden ar pa vag mot."},
        "initial_value": {"type": "number",
                          "description": "Vardet leden star i vid nollstallning."},
    },
}

_GRANSPOST = {
    "type": "object",
    "description": "En leds granser och maxvarden.",
    "properties": {
        "index": {"type": "integer", "description": "Ledens plats i kedjan."},
        "name": {"type": "string", "description": "Ledens namn."},
        "min_expression": {"type": ["string", "null"],
                           "description": ("VC lagrar ledgransen som ett "
                                           "UTTRYCK, inte som ett tal. Har "
                                           "star uttrycket ordagrant.")},
        "max_expression": {"type": ["string", "null"],
                           "description": "Ovre ledgrans som uttryck."},
        "min_value": {"type": ["number", "null"],
                      "description": ("Undre gransen som tal, nar uttrycket ar "
                                      "ett rent tal. Annars null, och da "
                                      "galler uttrycket.")},
        "max_value": {"type": ["number", "null"],
                      "description": "Ovre gransen som tal, eller null."},
        "max_speed": {"type": ["number", "null"],
                      "description": "Ledens maxhastighet, grader eller mm per s."},
        "max_acceleration": {"type": ["number", "null"],
                             "description": "Ledens maxacceleration."},
        "max_deceleration": {"type": ["number", "null"],
                             "description": "Ledens maxretardation."},
        "lag_time": {"type": ["number", "null"],
                     "description": "Ledens efterslapningstid i sekunder."},
        "settle_time": {"type": ["number", "null"],
                        "description": "Ledens sattningstid i sekunder."},
    },
}

_RAMPOST = {
    "type": "object",
    "description": "En verktygs- eller basram i styrenheten.",
    "properties": {
        "name": {"type": "string", "description": "Ramens namn."},
        "kind": {"type": "string",
                 "description": "tool for verktygsram, base for basram."},
        "node": {"type": ["string", "null"],
                 "description": "Noden ramen sitter pa, null om ingen ar satt."},
        "position": XYZ,
        "wpr": XYZ,
        "world_position": XYZ_NULLBAR,
        "world_wpr": XYZ_NULLBAR,
        "position_expression": {"type": ["string", "null"],
                                "description": "Ramens lagesuttryck, om det finns."},
        "ipo_mode": {"type": ["string", "number", "integer", "null"],
                     "description": "Ramens interpolationslage."},
    },
}

_SATSPOST = {
    "type": "object",
    "description": "En sats i rutinen.",
    "properties": {
        "index": {"type": "integer", "description": "Satsens plats i rutinen."},
        "name": {"type": "string", "description": "Satsens namn."},
        "type": {"type": ["string", "number", "integer", "null"],
                 "description": "VC:s upprakning for satstypen."},
        "type_label": {"type": ["string", "null"],
                       "description": ("Lasbart namn pa satstypen, eller null "
                                       "nar typen inte star i kartan.")},
        "properties": {"type": "array", "description": "Satsens egenskaper.",
                       "items": _EGENSKAPSPOST},
        "nested_statements": {"type": "integer",
                              "description": ("Antal satser i satsens egna "
                                              "grenar. De listas INTE har.")},
    },
}

_KONFIGPOST = {
    "type": "object",
    "description": "En robotkonfiguration och vad VC sager om den.",
    "properties": {
        "config": {"type": "integer", "description": "Konfigurationens nummer."},
        "warning": {"type": "integer",
                    "description": ("VC:s rada varningstal, 0 till 7. Bitarna "
                                    "ar singularitet, ledgrans och nabarhet.")},
        "ok": {"type": "boolean", "description": "Sant nar varningstalet ar noll."},
        "unreachable": {"type": "boolean",
                        "description": "Punkten ligger utanfor robotens rackvidd."},
        "joint_limit": {"type": "boolean",
                        "description": "En eller flera leder skulle passera sin grans."},
        "singular": {"type": "boolean",
                     "description": "Konfigurationen ar singular, till exempel i handleden."},
    },
}

# Malets egenskaper. Definieras EN gang och anvands bade platt i move_to och
# nastlat i move_targets; annars vore samma sak beskriven pa tva stallen och
# skulle glida isar.
_MALEGENSKAPER = {
    "motion": {"type": "string", "enum": _etiketter(RORELSETYPER),
               "default": "joint",
               "description": ("Rorelsens slag. joint ar punkt till punkt, "
                               "linear ar rat linje, circular ar cirkelbage, "
                               "spline ar splinekurva.")},
    "position": dict(XYZ, description=("Malets lage x, y, z i millimeter. Ange "
                                       "antingen position eller joint_values.")),
    "wpr": dict(XYZ, description=("Malets orientering, samma tre tal och samma "
                                  "ordning som get_tcp lamnar (VC:s getWPR).")),
    "joint_values": {"type": "array",
                     "description": ("Ledvarden i ledernas ordning, grader "
                                     "eller millimeter. Faerre varden an "
                                     "roboten har leder lamnar de ovriga "
                                     "ororda."),
                     "items": {"type": "number", "description": "Ett ledvarde."},
                     "minItems": 1, "maxItems": 20},
    "target_mode": {"type": "string", "enum": _etiketter(MALLAGEN),
                    "default": "normal",
                    "description": ("Vad lagesmatrisen ar relativ till. normal "
                                    "ar basramen, world ar varlden.")},
    "base": ARG_RAM_BAS,
    "tool": ARG_RAM_VERKTYG,
    "speed": {"type": "number",
              "description": "Hogsta kartesiska hastighet till malet, mm/s."},
    "acceleration": {"type": "number",
                     "description": "Hogsta kartesiska acceleration, mm/s^2."},
    "angular_speed": {"type": "number",
                      "description": "Hogsta vridhastighet till malet, grader/s."},
    "joint_speed_factor": {"type": "number",
                           "description": ("Ledhastighet som andel av maxfart, "
                                           "0 till 1. Galler ledrorelse.")},
    "zone_method": {"type": "string", "enum": _etiketter(ZONMETODER),
                    "description": ("Hur zonen kring malet mats: distance i mm, "
                                    "time i sekunder, velocity i mm/s.")},
    "zone_value": {"type": "number",
                   "description": "Zonens storlek i den enhet zone_method anger."},
    "config": {"type": "integer",
               "description": ("Robotkonfiguration att tvinga. Numren kommer ur "
                               "check_reach.")},
}

_MALSCHEMA = {
    "type": "object",
    "description": ("Ett rorelsemal. Ange antingen position eller "
                    "joint_values."),
    "properties": dict(_MALEGENSKAPER),
}


# ---- byggstenar for mallarna --------------------------------------------
#
# Varje byggsten lamnar RADER, inte en strang, sa att de gar att satta ihop.
# Kedjan skrivs rakt ut och inte via en hjalpfunktion; skalet star i modulens
# docstring och ar matt.

def _rader_komponent(namn):
    """Binder k till komponenten, eller kastar med namnet i klartext."""
    return [
        "k = getApplication().findComponent(%s)" % lit(namn),
        "if k is None:",
        '    raise ValueError("ingen komponent heter " + %s)' % lit(namn),
    ]


def _rader_styrenhet(argument):
    """Binder k och r. Roboten kanns igen pa sin yta, inte pa en konstant."""
    rader = _rader_komponent(argument["component"])
    rader += [
        "r = None",
        "for b in k.Behaviours:",
        # Joints, Bases och Tools TILLSAMMANS ar vcRobotController. Enbart
        # Joints skulle ocksa traffa en vanlig servostyrenhet utan ramar.
        '    if not (hasattr(b, "Joints") and hasattr(b, "Bases")'
        ' and hasattr(b, "Tools")):',
        "        continue",
    ]
    if "controller" in argument:
        rader += [
            "    if b.Name != %s:" % lit(argument["controller"]),
            "        continue",
        ]
    rader += ["    r = b", "    break", "if r is None:"]
    if "controller" in argument:
        rader.append('    raise ValueError(k.Name + " har ingen robotstyrenhet'
                     ' som heter " + %s)' % lit(argument["controller"]))
    else:
        rader.append('    raise ValueError(k.Name + " har ingen robotstyrenhet;'
                     ' inget av dess beteenden bar Joints, Bases och Tools")')
    return rader


def _rader_utforare():
    """Binder x till programutforaren av vcExecutor-slaget."""
    return [
        "x = None",
        "for b in k.Behaviours:",
        # Program FINNS ocksa pa vcRslProgramExecutor, men som strang.
        # callStatement finns bara pa vcExecutor och skiljer slakterna at.
        '    if not (hasattr(b, "Program") and hasattr(b, "callStatement")):',
        "        continue",
        "    x = b",
        "    break",
        "if x is None:",
        '    raise ValueError(k.Name + " har ingen programutforare av'
        ' vcExecutor-slaget; RSL-program stods inte av det har verktyget")',
    ]


def _rader_programslakt():
    """Satter familj, programnamn och antal_rutiner utan att kasta."""
    return [
        'familj = "ingen"',
        "programnamn = None",
        "antal_rutiner = None",
        "for b in k.Behaviours:",
        '    if hasattr(b, "Program") and hasattr(b, "callStatement"):',
        '        familj = "executor"',
        "        pr = b.Program",
        "        if pr is not None:",
        "            programnamn = pr.Name",
        # vcProgram.Routines rymmer alla rutiner UTOM huvudrutinen (kallans
        # egen text), sa huvudrutinen raknas till.
        "            antal_rutiner = len(pr.Routines) + 1",
        "        break",
        '    if hasattr(b, "MainRoutine") and hasattr(b, "SubRoutines"):',
        '        familj = "rsl"',
        "        programnamn = None",
        "        antal_rutiner = len(b.SubRoutines) + 1",
        "        break",
    ]


def _rader_rutin(argument):
    """Binder pr och ru. Kraver att x redan ar bunden."""
    rader = ["pr = x.Program",
             "if pr is None:",
             '    raise ValueError(k.Name + " har en utforare utan program")']
    if "routine" in argument:
        rader += [
            "ru = pr.findRoutine(%s)" % lit(argument["routine"]),
            "if ru is None:",
            "    kanda = []",
            "    for q in pr.Routines:",
            "        kanda.append(q.Name)",
            '    raise ValueError("programmet har ingen rutin som heter " + %s'
            ' + "; det har: " + ", ".join(kanda))' % lit(argument["routine"]),
        ]
    else:
        rader += [
            "ru = pr.MainRoutine",
            "if ru is None:",
            '    raise ValueError("programmet saknar huvudrutin")',
        ]
    return rader


def _rader_sats(index, variabel="sats"):
    """Binder en sats ur ru pa index, med en begriplig grans."""
    return [
        "if %d >= len(ru.Statements):" % index,
        '    raise ValueError(ru.Name + " har " + str(len(ru.Statements))'
        ' + " satser; index %d finns inte")' % index,
        "%s = ru.getStatement(%d)" % (variabel, index),
        "if %s is None:" % variabel,
        '    raise ValueError(ru.Name + " lamnade ingen sats pa index %d")'
        % index,
    ]


def _rader_matris(argument, variabel, nyckel_lage="position", nyckel_wpr="wpr"):
    """Bygger en vcMatrix ur position och wpr. Bada ar valfria."""
    rader = ["%s = vcMatrix.new()" % variabel]
    if nyckel_wpr in argument:
        a, b, c = argument[nyckel_wpr]
        # Samma tre tal och samma ordning som scen.set_transform anvander, sa
        # att lasning med get_tcp och skrivning har inte har var sin konvention.
        rader.append("%s.setWPR(%s, %s, %s)"
                     % (variabel, tal(a), tal(b), tal(c)))
    if nyckel_lage in argument:
        a, b, c = argument[nyckel_lage]
        rader.append("%s.P = vcVector.new(%s, %s, %s)"
                     % (variabel, tal(a), tal(b), tal(c)))
    return rader


def _rader_hitta_ram(namn, kalla, variabel, slag):
    """Binder en ram ur r.Bases eller r.Tools pa namn."""
    return [
        "%s = None" % variabel,
        "for f in %s:" % kalla,
        "    if f.Name == %s:" % lit(namn),
        "        %s = f" % variabel,
        "        break",
        "if %s is None:" % variabel,
        "    kanda = []",
        "    for f in %s:" % kalla,
        "        kanda.append(f.Name)",
        '    raise ValueError("styrenheten har ingen %s som heter " + %s'
        ' + "; den har: " + ", ".join(kanda))' % (slag, lit(namn)),
    ]


def _rader_typkarta():
    """En karta satstyp -> lasbart namn, byggd sa att en saknad konstant syns."""
    rader = ["typkarta = {}", "typkarta_kand = False", "try:",
             "    typkarta = {"]
    for etikett, konstant in TYPKARTA:
        rader.append('        %s: "%s",' % (konstant, etikett))
    rader += [
        "    }",
        "    typkarta_kand = True",
        "except NameError:",
        # Inte ett tyst undantag (S9): typkarta_kand foljer med i svaret, sa
        # att en oetiketterad lista syns som oetiketterad i stallet for att
        # se ut som en lista av okanda satstyper.
        "    typkarta = {}",
    ]
    return rader


def _rader_nastlade(variabel="sats"):
    """Raknar satser i satsens egna grenar utan att lista dem."""
    return [
        "nastlade = 0",
        'for gren in ("ThenScope", "ElseScope", "Scope"):',
        "    if hasattr(%s, gren):" % variabel,
        # hasattr(namn) racker inte: grenen kan finnas och vara None.
        "        s2 = getattr2(%s, gren)" % variabel,
        "        if s2 is not None:",
        "            nastlade = nastlade + len(s2.Statements)",
    ]


def _rader_ledvarden(kalla="r"):
    """Laser tillbaka ledvardena efter en rorelse."""
    return [
        "varden = []",
        "for i in range(%s.JointCount):" % kalla,
        "    varden.append(%s.getJointValue(i))" % kalla,
    ]


def _rader_mal(spec, variabel, styrenhet="r"):
    """Bygger ett vcMotionTarget ur en malspecifikation.

    spec ar redan validerad mot _MALEGENSKAPER. Att ett mal maste bara
    ANTINGEN position eller joint_values gar inte att skriva i JSON-schemat
    for en nastlad post, sa det provas har och avvisas som ett argumentfel.
    """
    rader = ["%s = %s.createTarget()" % (variabel, styrenhet)]
    rader.append("%s.MotionType = %s"
                 % (variabel, _konstant(RORELSETYPER, spec.get("motion", "joint"))))
    rader.append("%s.TargetMode = %s"
                 % (variabel,
                    _konstant(MALLAGEN, spec.get("target_mode", "normal"))))
    if "base" in spec:
        rader.append("%s.BaseName = %s" % (variabel, lit(spec["base"])))
    if "tool" in spec:
        rader.append("%s.ToolName = %s" % (variabel, lit(spec["tool"])))
    if "speed" in spec:
        rader.append("%s.CartesianSpeed = %s" % (variabel, tal(spec["speed"])))
    if "acceleration" in spec:
        rader.append("%s.CartesianAcceleration = %s"
                     % (variabel, tal(spec["acceleration"])))
    if "angular_speed" in spec:
        rader.append("%s.AngularSpeed = %s"
                     % (variabel, tal(spec["angular_speed"])))
    if "joint_speed_factor" in spec:
        rader.append("%s.JointSpeedFactor = %s"
                     % (variabel, tal(spec["joint_speed_factor"])))
    if "zone_method" in spec:
        rader.append("%s.AccuracyMethod = %s"
                     % (variabel, _konstant(ZONMETODER, spec["zone_method"])))
    if "zone_value" in spec:
        rader.append("%s.AccuracyValue = %s" % (variabel, tal(spec["zone_value"])))
    if "config" in spec:
        rader.append("%s.RobotConfig = %d" % (variabel, spec["config"]))

    if "joint_values" in spec:
        varden = spec["joint_values"]
        rader += [
            "jv = %s.JointValues" % variabel,
            "if len(jv) < %d:" % len(varden),
            '    raise ValueError("roboten har " + str(len(jv)) + " leder;'
            ' %d varden gavs")' % len(varden),
        ]
        for i, v in enumerate(varden):
            rader.append("jv[%d] = %s" % (i, tal(v)))
        # Kallan: "To read and write joint values, first get a handle for this
        # property, edit the values of that handle, and then assign that handle
        # as the value of this property." Handtaget maste alltsa skrivas
        # tillbaka; en andring pa plats racker inte.
        rader.append("%s.JointValues = jv" % variabel)
        rader.append("%s.UseJoints = True" % variabel)
    else:
        rader += _rader_matris(spec, "mm")
        rader.append("%s.Target = mm" % variabel)
    return rader


def _granska_mal(spec, var):
    """Kastar Argumentfel om malet varken bar position eller ledvarden."""
    if "joint_values" not in spec and "position" not in spec:
        raise Argumentfel(var, ["ett rorelsemal maste bara antingen position "
                                "eller joint_values; det har bar ingetdera"])
    if "joint_values" in spec and "position" in spec:
        raise Argumentfel(var, ["ett rorelsemal far inte bara bade position "
                                "och joint_values; VC skulle da tyst valja "
                                "det ena"])
    if "wpr" in spec and "position" not in spec:
        raise Argumentfel(var, ["wpr utan position beskriver inget mal; ange "
                                "position ocksa"])


def _granska_egenskapsvarden(varden, var):
    """Egenskapsvarden maste vara sadant lit() kan skriva som literal."""
    fel = []
    for namn in sorted(varden):
        v = varden[namn]
        if not isinstance(v, (str, bool, int, float)):
            fel.append("egenskapen %r har vardet %r av typen %s; bara text, "
                       "tal och sant/falskt gar att skriva in i VC"
                       % (namn, v, type(v).__name__))
    if fel:
        raise Argumentfel(var, fel)


def _rader_satt_egenskaper(varden, variabel="sats"):
    """Satter namngivna egenskaper pa en sats, med kanda namn i felet."""
    rader = []
    for namn in sorted(varden):
        rader += [
            "p = %s.getProperty(%s)" % (variabel, lit(namn)),
            "if p is None:",
            "    kanda = []",
            "    for pp in %s.Properties:" % variabel,
            "        kanda.append(pp.Name)",
            '    raise ValueError("satsen " + %s.Name + " har ingen egenskap'
            ' som heter " + %s + "; den har: " + ", ".join(kanda))'
            % (variabel, lit(namn)),
            "p.Value = %s" % lit(varden[namn]),
        ]
    return rader


# =========================================================================
# LASANDE VERKTYG
# =========================================================================

# ---- list_robots ---------------------------------------------------------

def _kod_list_robots(argument):
    rader = ["rader = []", "avkortad = False",
             "for komp in getApplication().Components:",
             "    if avkortad:",
             "        break"]
    if "name_contains" in argument:
        rader += ["    if %s not in komp.Name:" % lit(argument["name_contains"]),
                  "        continue"]
    rader += [
        "    styr = None",
        '    familj = "ingen"',
        "    for b in komp.Behaviours:",
        '        if hasattr(b, "Joints") and hasattr(b, "Bases")'
        ' and hasattr(b, "Tools"):',
        "            if styr is None:",
        "                styr = b",
        '        elif hasattr(b, "Program") and hasattr(b, "callStatement"):',
        '            familj = "executor"',
        '        elif hasattr(b, "MainRoutine") and hasattr(b, "SubRoutines"):',
        '            if familj == "ingen":',
        '                familj = "rsl"',
        "    if styr is None:",
        "        continue",
    ]
    rader += tak("rader", "    ")
    rader += [
        '    rader.append({"name": komp.Name, "controller": styr.Name,',
        '                  "joint_count": styr.JointCount,',
        '                  "tool_count": len(styr.Tools),',
        '                  "base_count": len(styr.Bases),',
        '                  "program_family": familj})',
        '_svara({"robots": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "list_robots",
    "Listar layoutens robotar: vilka komponenter som bar en robotstyrenhet, "
    "hur manga leder, verktygsramar och basramar de har, och vilken "
    "programslakt de anvander. Borja har.",
    "read",
    params({"name_contains": {
        "type": "string",
        "description": ("Ta bara med komponenter vars namn innehaller den har "
                        "texten.")}}),
    returns({"robots": {"type": "array", "description": "Robotarna.",
                        "items": {
                            "type": "object",
                            "description": "En robot i layouten.",
                            "properties": {
                                "name": RET_ROBOT,
                                "controller": RET_STYRENHET,
                                "joint_count": {"type": "integer",
                                                "description": "Antal leder."},
                                "tool_count": {"type": "integer",
                                               "description": "Antal verktygsramar."},
                                "base_count": {"type": "integer",
                                               "description": "Antal basramar."},
                                "program_family": _PROGRAMSLAKT}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["robots", "antal", "avkortad"]),
    _YTOR_LAYOUT,
    _kod_list_robots,
)


# ---- robot_info ----------------------------------------------------------

def _kod_robot_info(argument):
    rader = _rader_styrenhet(argument)
    rader += [
        "fl = r.FlangeNode",
        "flans = None",
        "if fl is not None:",
        "    flans = fl.Name",
        "rot = r.RootNode",
        "rotnamn = None",
        "if rot is not None:",
        "    rotnamn = rot.Name",
        "wm = r.WorldTransformMatrix",
        "ww = wm.getWPR()",
        "nyttolast = []",
        "for cp in k.Properties:",
        # Nyttolasten ar INGEN yta i VC:s robotstyrenhet. Den bor som en
        # komponentegenskap, och namnet varierar mellan tillverkarnas
        # modeller. Darfor gissas inget namn: alla egenskaper vars namn
        # innehaller payload lamnas ut, och ar listan tom sa ar den tom.
        '    if "payload" in cp.Name.lower():',
        '        nyttolast.append({"name": cp.Name, "value": _enkelt(cp.Value)})',
    ]
    rader += _rader_programslakt()
    rader += [
        '_svara({"robot": k.Name, "controller": r.Name,',
        '        "joint_count": r.JointCount,',
        '        "speed_percent": r.Speed,',
        '        "tool_count": len(r.Tools), "base_count": len(r.Bases),',
        '        "initial_tool": r.InitialTool, "initial_base": r.InitialBase,',
        '        "approach_axis": _enkelt(r.ApproachAxis),',
        '        "configuration_mode": _enkelt(r.ConfigurationMode),',
        '        "track_world_frame_mode": _enkelt(r.TrackWorldFrameMode),',
        '        "flange_node": flans, "root_node": rotnamn,',
        '        "world_frame_position": [wm.P.X, wm.P.Y, wm.P.Z],',
        '        "world_frame_wpr": [ww.X, ww.Y, ww.Z],',
        '        "program_family": familj, "program": programnamn,',
        '        "routine_count": antal_rutiner,',
        '        "payload_properties": nyttolast})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "robot_info",
    "Allt om en robot pa en gang: styrenhet, antal leder, verktygs- och "
    "basramar, robotens varldsram, flans- och rotnod, programslakt och de "
    "komponentegenskaper som handlar om nyttolast. Nyttolasten ar en "
    "komponentegenskap i VC, inte en robotyta, sa listan kan vara tom.",
    "read",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET},
           ["component"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "joint_count": {"type": "integer", "description": "Antal leder."},
             "speed_percent": {"type": "number",
                               "description": ("Ledhastighet som procent av "
                                               "maxfart, 0 till 100.")},
             "tool_count": {"type": "integer", "description": "Antal verktygsramar."},
             "base_count": {"type": "integer", "description": "Antal basramar."},
             "initial_tool": {"type": ["string", "null"],
                              "description": "Verktygsramen styrenheten startar i."},
             "initial_base": {"type": ["string", "null"],
                              "description": "Basramen styrenheten startar i."},
             "approach_axis": {"type": ["string", "number", "integer", "null"],
                               "description": "VC:s upprakning for narmningsaxeln."},
             "configuration_mode": {"type": ["string", "number", "integer", "null"],
                                    "description": "VC:s upprakning for konfigurationslaget."},
             "track_world_frame_mode": {"type": ["string", "number", "integer", "null"],
                                        "description": "Hur robotens varldsram foljer en travers."},
             "flange_node": {"type": ["string", "null"],
                             "description": "Noden verktyget monteras pa."},
             "root_node": {"type": ["string", "null"],
                           "description": "Kinematikens fasta bas."},
             "world_frame_position": XYZ,
             "world_frame_wpr": XYZ,
             "program_family": _PROGRAMSLAKT,
             "program": {"type": ["string", "null"],
                         "description": "Programmets namn, null utan program."},
             "routine_count": {"type": ["integer", "null"],
                               "description": "Antal rutiner inklusive huvudrutinen."},
             "payload_properties": {"type": "array",
                                    "description": ("Komponentegenskaper vars namn "
                                                    "namner payload. Tom lista "
                                                    "betyder att komponenten inte "
                                                    "bar nagon."),
                                    "items": _EGENSKAPSPOST}},
            ["robot", "controller", "joint_count", "speed_percent",
             "tool_count", "base_count", "world_frame_position",
             "world_frame_wpr", "program_family", "payload_properties"]),
    _YTOR_ROBOT_EGENSKAPER,
    _kod_robot_info,
)


# ---- get_joints ----------------------------------------------------------

def _kod_get_joints(argument):
    rader = _rader_styrenhet(argument)
    rader += ["rader = []", "avkortad = False", "i = 0", "for j in r.Joints:"]
    rader += tak("rader")
    rader += [
        '    rader.append({"index": i, "name": j.Name, "type": _enkelt(j.Type),',
        '                  "current_value": r.getJointValue(i),',
        '                  "target_value": r.getJointTarget(i),',
        '                  "initial_value": j.InitialValue})',
        "    i = i + 1",
        '_svara({"robot": k.Name, "controller": r.Name, "joints": rader,',
        '        "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "get_joints",
    "Lasar robotens leder: namn, typ, vardet nu, vardet leden ar pa vag mot "
    "och vardet vid nollstallning. Ordningen ar ledernas egen, och samma "
    "ordning som set_joints och rorelsemalen anvander.",
    "read",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET},
           ["component"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "joints": {"type": "array", "description": "Lederna i ordning.",
                        "items": _LEDPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["robot", "controller", "joints", "antal", "avkortad"]),
    _YTOR_ROBOT,
    _kod_get_joints,
)


# ---- robot_limits --------------------------------------------------------

def _kod_robot_limits(argument):
    rader = _rader_styrenhet(argument)
    rader += [
        "def _flyt(v):",
        # VC lagrar ledgranser som UTTRYCK (String), inte som tal. Uttrycket
        # far inte evalueras: eval ar ogenomskinligt for bade skrivgrinden och
        # for oss. Ar uttrycket ett rent tal ges det ocksa som tal, annars
        # None - och uttrycket star kvar i klartext bredvid, sa ingenting gar
        # forlorat.
        "    try:",
        "        return float(v)",
        "    except (TypeError, ValueError):",
        "        return None",
        "rader = []",
        "avkortad = False",
        "i = 0",
        "for j in r.Joints:",
    ]
    rader += tak("rader")
    rader += [
        '    rader.append({"index": i, "name": j.Name,',
        '                  "min_expression": j.MinValue,',
        '                  "max_expression": j.MaxValue,',
        '                  "min_value": _flyt(j.MinValue),',
        '                  "max_value": _flyt(j.MaxValue),',
        '                  "max_speed": _flyt(j.MaxSpeed),',
        '                  "max_acceleration": _flyt(j.MaxAcceleration),',
        '                  "max_deceleration": _flyt(j.MaxDeceleration),',
        '                  "lag_time": _flyt(j.LagTime),',
        '                  "settle_time": _flyt(j.SettleTime)})',
        "    i = i + 1",
        '_svara({"robot": k.Name, "controller": r.Name, "joints": rader,',
        '        "antal": len(rader), "avkortad": avkortad,',
        '        "speed_percent": r.Speed,',
        '        "max_cartesian_speed": r.MaxCartesianSpeed,',
        '        "max_cartesian_acceleration": r.MaxCartesianAccel,',
        '        "max_angular_speed": r.MaxAngularSpeed,',
        '        "max_angular_acceleration": r.MaxAngularAccel,',
        '        "lag_time": r.LagTime, "settle_time": r.SettleTime})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "robot_limits",
    "Robotens granser: styrenhetens max hastighet och acceleration for linjar "
    "och vridande rorelse, samt per led dess ovre och undre grans, maxfart, "
    "acceleration och retardation. VC lagrar ledgranserna som UTTRYCK; de ges "
    "bade ordagrant och som tal nar uttrycket ar ett rent tal.",
    "read",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET},
           ["component"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "joints": {"type": "array", "description": "Ledernas granser.",
                        "items": _GRANSPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD,
             "speed_percent": {"type": "number",
                               "description": "Ledhastighet i procent av maxfart."},
             "max_cartesian_speed": {"type": "number",
                                     "description": "Hogsta linjara hastighet, mm/s."},
             "max_cartesian_acceleration": {"type": "number",
                                            "description": "Hogsta linjara acceleration, mm/s^2."},
             "max_angular_speed": {"type": "number",
                                   "description": "Hogsta vridhastighet, grader/s."},
             "max_angular_acceleration": {"type": "number",
                                          "description": "Hogsta vridacceleration, grader/s^2."},
             "lag_time": {"type": "number",
                          "description": "Styrenhetens efterslapningstid i sekunder."},
             "settle_time": {"type": "number",
                             "description": "Styrenhetens sattningstid i sekunder."}},
            ["robot", "controller", "joints", "antal", "avkortad",
             "speed_percent", "max_cartesian_speed",
             "max_cartesian_acceleration", "max_angular_speed",
             "max_angular_acceleration"]),
    _YTOR_ROBOT,
    _kod_robot_limits,
)


# ---- get_tcp -------------------------------------------------------------

def _kod_get_tcp(argument):
    rader = _rader_styrenhet(argument)
    rader += [
        "fl = r.FlangeNode",
        "if fl is None:",
        '    raise ValueError(r.Name + " har ingen flansnod, sa det finns'
        ' inget verktygsfaste att mata fran")',
        "mf = fl.WorldPositionMatrix",
        "wf = mf.getWPR()",
    ]
    if "tool" in argument:
        rader.append("verktygsnamn = %s" % lit(argument["tool"]))
    else:
        rader.append("verktygsnamn = r.InitialTool")
    rader += [
        "ram = None",
        "for f in r.Tools:",
        "    if f.Name == verktygsnamn:",
        "        ram = f",
        "        break",
        "tcp = None",
        "tcpwpr = None",
        "ramnod = None",
        "hittad = False",
        "if ram is not None and ram.Node is not None:",
        # localToWorld gor sammansattningen sjalv. vcMatrix.new() runt svaret
        # ar inte kosmetika: kallan deklarerar localToWorld:s returtyp som
        # okand, och en okand typ gar inte att prova vidare mot API-indexet.
        "    mt = vcMatrix.new(ram.Node.localToWorld(ram.PositionMatrix))",
        "    wt = mt.getWPR()",
        "    tcp = [mt.P.X, mt.P.Y, mt.P.Z]",
        "    tcpwpr = [wt.X, wt.Y, wt.Z]",
        "    ramnod = ram.Node.Name",
        "    hittad = True",
        '_svara({"robot": k.Name, "controller": r.Name,',
        '        "flange_node": fl.Name,',
        '        "flange_position": [mf.P.X, mf.P.Y, mf.P.Z],',
        '        "flange_wpr": [wf.X, wf.Y, wf.Z],',
        '        "tool": verktygsnamn, "tool_node": ramnod,',
        '        "tcp_found": hittad,',
        '        "tcp_position": tcp, "tcp_wpr": tcpwpr})',
    ]
    return bygg(["_svara"], rader, ["vcMatrix"])


_lagg(
    "get_tcp",
    "Lasar var robotens verktygspunkt star i varlden. Flanslaget kommer "
    "alltid; TCP:n kommer nar den valda verktygsramen finns och sitter pa en "
    "nod, och tcp_found sager vilket av fallen det blev. Utan tool anvands "
    "styrenhetens egen startverktygsram.",
    "read",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "tool": dict(ARG_RAM_VERKTYG, description=(
                "Verktygsram att mata till. Utelamnad tar styrenhetens "
                "InitialTool."))},
           ["component"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "flange_node": {"type": "string", "description": "Flansnodens namn."},
             "flange_position": dict(XYZ, description="Flansens lage i varlden."),
             "flange_wpr": dict(XYZ, description="Flansens orientering i varlden."),
             "tool": {"type": ["string", "null"],
                      "description": "Verktygsramen som soktes."},
             "tool_node": {"type": ["string", "null"],
                           "description": "Noden verktygsramen sitter pa."},
             "tcp_found": {"type": "boolean",
                           "description": ("Sant nar verktygsramen fanns och TCP "
                                           "kunde raknas.")},
             "tcp_position": dict(XYZ_NULLBAR, description="TCP:ns lage i varlden."),
             "tcp_wpr": dict(XYZ_NULLBAR, description="TCP:ns orientering i varlden.")},
            ["robot", "controller", "flange_node", "flange_position",
             "flange_wpr", "tcp_found"]),
    _YTOR_ROBOT_NOD,
    _kod_get_tcp,
)


# ---- list_frames ---------------------------------------------------------

def _rader_ramslinga(kalla, slag):
    return [
        "if not avkortad:",
        "    for f in %s:" % kalla,
        "        if avkortad:",
        "            break",
    ] + tak("rader", "        ") + [
        "        mfr = f.PositionMatrix",
        "        wfr = mfr.getWPR()",
        "        vnod = None",
        "        vlage = None",
        "        vwpr = None",
        "        if f.Node is not None:",
        "            vnod = f.Node.Name",
        "            mw = vcMatrix.new(f.Node.localToWorld(f.PositionMatrix))",
        "            ww = mw.getWPR()",
        "            vlage = [mw.P.X, mw.P.Y, mw.P.Z]",
        "            vwpr = [ww.X, ww.Y, ww.Z]",
        '        rader.append({"name": f.Name, "kind": "%s", "node": vnod,' % slag,
        '                      "position": [mfr.P.X, mfr.P.Y, mfr.P.Z],',
        '                      "wpr": [wfr.X, wfr.Y, wfr.Z],',
        '                      "world_position": vlage, "world_wpr": vwpr,',
        '                      "position_expression": f.PositionExpression,',
        '                      "ipo_mode": _enkelt(f.IPOMode)})',
    ]


def _kod_list_frames(argument):
    slag = argument["kind"]
    rader = _rader_styrenhet(argument)
    rader += ["rader = []", "avkortad = False"]
    if slag in ("tool", "both"):
        rader += _rader_ramslinga("r.Tools", "tool")
    if slag in ("base", "both"):
        rader += _rader_ramslinga("r.Bases", "base")
    rader += [
        '_svara({"robot": k.Name, "controller": r.Name, "kind": %s,'
        % lit(slag),
        '        "frames": rader, "antal": len(rader), "avkortad": avkortad})',
    ]
    return bygg(["_enkelt", "_svara"], rader, ["vcMatrix"])


_lagg(
    "list_frames",
    "Listar styrenhetens verktygsramar och basramar med lage bade i sin egen "
    "nod och i varlden. Namnen harifran ar de som rorelsemal, rorelsesatser "
    "och set_robot_config vill ha.",
    "read",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "kind": {"type": "string", "enum": ["tool", "base", "both"],
                     "default": "both",
                     "description": ("tool ger verktygsramar, base ger "
                                     "basramar, both ger bada.")}},
           ["component"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "kind": {"type": "string", "description": "Slaget som listades."},
             "frames": {"type": "array", "description": "Ramarna.",
                        "items": _RAMPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["robot", "controller", "kind", "frames", "antal", "avkortad"]),
    _YTOR_ROBOT_NOD,
    _kod_list_frames,
)


# ---- list_routines -------------------------------------------------------

def _kod_list_routines(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += [
        "pr = x.Program",
        "if pr is None:",
        '    raise ValueError(k.Name + " har en utforare utan program")',
        "huvud = pr.MainRoutine",
        "huvudnamn = None",
        "huvudsatser = None",
        "if huvud is not None:",
        "    huvudnamn = huvud.Name",
        "    huvudsatser = len(huvud.Statements)",
        "rader = []",
        "avkortad = False",
        "for q in pr.Routines:",
    ]
    rader += tak("rader")
    rader += [
        '    rader.append({"name": q.Name, "statements": len(q.Statements)})',
        '_svara({"robot": k.Name, "executor": x.Name, "program": pr.Name,',
        '        "main_routine": huvudnamn, "main_statements": huvudsatser,',
        '        "routines": rader, "antal": len(rader),'
        ' "avkortad": avkortad})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "list_routines",
    "Listar robotprogrammets rutiner med antal satser i var och en. "
    "Huvudrutinen redovisas for sig; VC raknar den inte till Routines.",
    "read",
    params({"component": ARG_ROBOT}, ["component"]),
    returns({"robot": RET_ROBOT,
             "executor": {"type": "string", "description": "Programutforarens namn."},
             "program": {"type": ["string", "null"], "description": "Programmets namn."},
             "main_routine": {"type": ["string", "null"],
                              "description": "Huvudrutinens namn."},
             "main_statements": {"type": ["integer", "null"],
                                 "description": "Antal satser i huvudrutinen."},
             "routines": {"type": "array", "description": "Ovriga rutiner.",
                          "items": {"type": "object", "description": "En rutin.",
                                    "properties": {
                                        "name": {"type": "string",
                                                 "description": "Rutinens namn."},
                                        "statements": {"type": "integer",
                                                       "description": "Antal satser."}}}},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD},
            ["robot", "executor", "main_routine", "routines", "antal",
             "avkortad"]),
    _YTOR_ROBOT,
    _kod_list_routines,
)


# ---- read_routine --------------------------------------------------------

def _kod_read_routine(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    rader += _rader_typkarta()
    rader += [
        "rader = []",
        "avkortad = False",
        "index = 0",
        "for s in ru.Statements:",
    ]
    rader += tak("rader")
    rader += [
        "    etikett = None",
        "    if s.Type in typkarta:",
        "        etikett = typkarta[s.Type]",
        "    egenskaper = []",
        "    for pp in s.Properties:",
        '        egenskaper.append({"name": pp.Name, "value": _enkelt(pp.Value)})',
        "    nastlade = 0",
        '    if hasattr(s, "ThenScope") and s.ThenScope is not None:',
        "        nastlade = nastlade + len(s.ThenScope.Statements)",
        '    if hasattr(s, "ElseScope") and s.ElseScope is not None:',
        "        nastlade = nastlade + len(s.ElseScope.Statements)",
        '    if hasattr(s, "Scope") and s.Scope is not None:',
        "        nastlade = nastlade + len(s.Scope.Statements)",
        '    if hasattr(s, "ElseIfScopes") and s.ElseIfScopes is not None:',
        "        for sc in s.ElseIfScopes:",
        "            nastlade = nastlade + len(sc.Statements)",
        '    if hasattr(s, "Cases") and s.Cases is not None:',
        "        for sc in s.Cases:",
        "            nastlade = nastlade + len(sc.Statements)",
        '    rader.append({"index": index, "name": s.Name,',
        '                  "type": _enkelt(s.Type), "type_label": etikett,',
        '                  "properties": egenskaper,',
        '                  "nested_statements": nastlade})',
        "    index = index + 1",
        '_svara({"robot": k.Name, "routine": ru.Name, "statements": rader,',
        '        "antal": len(rader), "avkortad": avkortad,',
        '        "type_labels": typkarta_kand})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "read_routine",
    "Lasar satserna i en rutin med index, typ och alla egenskaper. "
    "Egenskapsnamnen harifran ar precis de namn add_statement och "
    "edit_statement vill ha. Satser inne i en gren (if, while, switch) "
    "RAKNAS men listas inte.",
    "read",
    params({"component": ARG_ROBOT, "routine": ARG_RUTIN}, ["component"]),
    returns({"robot": RET_ROBOT, "routine": RET_RUTIN,
             "statements": {"type": "array", "description": "Satserna i ordning.",
                            "items": _SATSPOST},
             "antal": RET_ANTAL, "avkortad": RET_AVKORTAD,
             "type_labels": {"type": "boolean",
                             "description": ("Sant nar VC kande alla "
                                             "satstypskonstanter, sa att "
                                             "type_label gar att lita pa.")}},
            ["robot", "routine", "statements", "antal", "avkortad",
             "type_labels"]),
    _YTOR_ROBOT,
    _kod_read_routine,
)


# ---- program_state -------------------------------------------------------

def _kod_program_state(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_programslakt()
    rader += _rader_typkarta()
    rader += [
        "aktiv = {}",
        "har_aktiv = False",
        "kor = False",
        "looping = None",
        "aktiverat = None",
        "extern = None",
        "utforare = None",
        "for b in k.Behaviours:",
        '    if not (hasattr(b, "Program") and hasattr(b, "callStatement")):',
        "        continue",
        "    utforare = b.Name",
        "    looping = bool(b.IsLooping)",
        "    aktiverat = bool(b.IsEnabled)",
        "    extern = bool(b.UseExternalExecutor)",
        "    cs = b.CurrentStatement",
        "    if cs is not None:",
        "        har_aktiv = True",
        '        aktiv["name"] = cs.Name',
        '        aktiv["type"] = _enkelt(cs.Type)',
        '        aktiv["type_label"] = None',
        "        if cs.Type in typkarta:",
        '            aktiv["type_label"] = typkarta[cs.Type]',
        '        aktiv["routine"] = None',
        "        if cs.ParentRoutine is not None:",
        '            aktiv["routine"] = cs.ParentRoutine.Name',
        "    break",
        "kor = bool(getSimulation().IsRunning)",
        '_svara({"robot": k.Name, "executor": utforare,',
        '        "program_family": familj, "program": programnamn,',
        '        "routine_count": antal_rutiner,',
        '        "is_enabled": aktiverat, "is_looping": looping,',
        '        "uses_external_executor": extern,',
        '        "simulation_running": kor,',
        '        "has_current_statement": har_aktiv,',
        '        "current_statement": aktiv,',
        '        "type_labels": typkarta_kand})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "program_state",
    "Sager var programmet star: vilken sats utforaren kor just nu, i vilken "
    "rutin, om programmet ar aktiverat och loopar, och om simuleringen kor "
    "alls. Ett robotprogram ror sig BARA medan simuleringen gar.",
    "read",
    params({"component": ARG_ROBOT}, ["component"]),
    returns({"robot": RET_ROBOT,
             "executor": {"type": ["string", "null"],
                          "description": "Programutforarens namn, null om ingen finns."},
             "program_family": _PROGRAMSLAKT,
             "program": {"type": ["string", "null"], "description": "Programmets namn."},
             "routine_count": {"type": ["integer", "null"],
                               "description": "Antal rutiner inklusive huvudrutinen."},
             "is_enabled": {"type": ["boolean", "null"],
                            "description": "Om programmet kors under simulering."},
             "is_looping": {"type": ["boolean", "null"],
                            "description": "Om utforaren borjar om fran borjan."},
             "uses_external_executor": {"type": ["boolean", "null"],
                                        "description": "Om en yttre styrning driver roboten."},
             "simulation_running": {"type": "boolean",
                                    "description": "Om simuleringen gar just nu."},
             "has_current_statement": {"type": "boolean",
                                       "description": "Om utforaren star pa en sats."},
             "current_statement": {"type": "object",
                                   "description": ("Satsen utforaren star pa. Tom "
                                                   "nar has_current_statement ar falskt."),
                                   "properties": {
                                       "name": {"type": "string", "description": "Satsens namn."},
                                       "type": {"type": ["string", "number", "integer", "null"],
                                                "description": "VC:s upprakning for satstypen."},
                                       "type_label": {"type": ["string", "null"],
                                                      "description": "Lasbart typnamn."},
                                       "routine": {"type": ["string", "null"],
                                                   "description": "Rutinen satsen hor till."}}},
             "type_labels": {"type": "boolean",
                             "description": "Sant nar satstypskonstanterna fanns."}},
            ["robot", "program_family", "simulation_running",
             "has_current_statement", "current_statement", "type_labels"]),
    _YTOR_ROBOT_SIM,
    _kod_program_state,
)


# =========================================================================
# SKRIVANDE VERKTYG
# =========================================================================

# ---- set_joints ----------------------------------------------------------

def _kod_set_joints(argument):
    rader = _rader_styrenhet(argument)
    rader += _rader_mal({"joint_values": argument["values"]}, "t")
    rader += ["r.moveImmediate(t)"]
    rader += _rader_ledvarden()
    rader += [
        '_svara({"robot": k.Name, "controller": r.Name, "set": True,',
        '        "joint_values": varden})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "set_joints",
    "Stallar roboten i givna ledvarden UTAN att simulera nagon rorelse: "
    "roboten star i posen direkt. Anvand det for att provstalla en pose. "
    "Vill du att rorelsen ska ta tid och synas, anvand move_to.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "values": {"type": "array",
                       "description": ("Ledvarden i ledernas ordning, grader "
                                       "eller millimeter. Farre varden an "
                                       "roboten har leder lamnar de ovriga "
                                       "ororda."),
                       "items": {"type": "number", "description": "Ett ledvarde."},
                       "minItems": 1, "maxItems": 20}},
           ["component", "values"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "joint_values": {"type": "array",
                              "description": "Ledvardena som lastes tillbaka efterat.",
                              "items": {"type": "number", "description": "Ett ledvarde."}}},
            ["robot", "controller", "set", "joint_values"]),
    _YTOR_ROBOT,
    _kod_set_joints,
)


# ---- move_to -------------------------------------------------------------

def _kod_move_to(argument):
    spec = dict(argument)
    for nyckel in ("component", "controller", "mode"):
        spec.pop(nyckel, None)
    _granska_mal(spec, "move_to")
    rader = _rader_styrenhet(argument)
    rader += _rader_mal(spec, "t")
    if argument["mode"] == "immediate":
        rader.append("r.moveImmediate(t)")
    else:
        # moveTo tommer mallistan sjalv. Det ar avsiktligt: en enstaka
        # rorelse ska inte arva mal nagon annan lade dit.
        rader.append("r.moveTo(t)")
    rader += _rader_ledvarden()
    rader += [
        '_svara({"robot": k.Name, "controller": r.Name, "moved": True,',
        '        "mode": %s, "joint_values": varden})' % lit(argument["mode"]),
    ]
    return bygg(["_svara"], rader, ["vcMatrix", "vcVector"]
                if "joint_values" not in spec else [])


_lagg(
    "move_to",
    "Kor roboten till ETT mal. Ange antingen position (med wpr) eller "
    "joint_values, aldrig bada. mode=motion later rorelsen ta simuleringstid "
    "och kraver att simuleringen gar; mode=immediate stallar roboten i "
    "posen direkt. Malets hastighet, acceleration och zon satts har och "
    "galler bara den har rorelsen.",
    "write",
    params(dict(_MALEGENSKAPER,
                component=ARG_ROBOT, controller=ARG_STYRENHET,
                mode={"type": "string", "enum": ["motion", "immediate"],
                      "default": "motion",
                      "description": ("motion later rorelsen ta tid i "
                                      "simuleringen; immediate flyttar "
                                      "roboten direkt.")}),
           ["component"], minst_en_av=[("position", "joint_values")]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "moved": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "mode": {"type": "string", "description": "Laget rorelsen kordes i."},
             "joint_values": {"type": "array",
                              "description": "Ledvardena efter rorelsen.",
                              "items": {"type": "number", "description": "Ett ledvarde."}}},
            ["robot", "controller", "moved", "mode", "joint_values"]),
    _YTOR_ROBOT,
    _kod_move_to,
    timeout_ms=TIMEOUT_MS_RORELSE,
)


# ---- move_targets --------------------------------------------------------

def _kod_move_targets(argument):
    mal = argument["targets"]
    for nr, spec in enumerate(mal):
        _granska_mal(spec, "move_targets[%d]" % nr)
    rader = _rader_styrenhet(argument)
    # Listan tommes ALLTID forst. En mallista som ar kvar sedan tidigare ar
    # osynlig for modellen, och en osynlig rorelse ar den varsta sorten.
    rader.append("r.clearTargets()")
    behover_matris = False
    for nr, spec in enumerate(mal):
        rader += _rader_mal(spec, "t%d" % nr)
        rader.append("r.addTarget(t%d)" % nr)
        if "joint_values" not in spec:
            behover_matris = True
    if argument["run"]:
        rader.append("r.move()")
    rader += _rader_ledvarden()
    rader += [
        '_svara({"robot": k.Name, "controller": r.Name,',
        '        "targets": %d, "cleared": True, "ran": %s,'
        % (len(mal), "True" if argument["run"] else "False"),
        '        "joint_values": varden})',
    ]
    return bygg(["_svara"], rader,
                ["vcMatrix", "vcVector"] if behover_matris else [])


_lagg(
    "move_targets",
    "Bygger en hel bana i EN korning: tommer styrenhetens mallista, lagger "
    "dit malen i ordning och kor dem. Anvand det nar zonerna ska vara "
    "annat an noll, sa att roboten glider genom mellanpunkterna i stallet "
    "for att stanna i var och en. run=false lagger malen utan att kora dem.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "targets": {"type": "array",
                        "description": ("Malen i den ordning roboten ska ta "
                                        "dem."),
                        "items": _MALSCHEMA,
                        "minItems": 1, "maxItems": 100},
            "run": {"type": "boolean", "default": True,
                    "description": ("true kor listan direkt. false lagger bara "
                                    "dit malen, och da behovs ett nytt anrop "
                                    "med run=true for att kora dem.")}},
           ["component", "targets"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "targets": {"type": "integer", "description": "Antal mal som lades i listan."},
             "cleared": {"type": "boolean", "description": "Alltid true; listan tommes forst."},
             "ran": {"type": "boolean", "description": "Om listan ocksa kordes."},
             "joint_values": {"type": "array",
                              "description": "Ledvardena efterat.",
                              "items": {"type": "number", "description": "Ett ledvarde."}}},
            ["robot", "controller", "targets", "cleared", "ran",
             "joint_values"]),
    _YTOR_ROBOT,
    _kod_move_targets,
    timeout_ms=TIMEOUT_MS_RORELSE,
)


# ---- check_reach ---------------------------------------------------------

def _kod_check_reach(argument):
    spec = dict(argument)
    for nyckel in ("component", "controller"):
        spec.pop(nyckel, None)
    rader = _rader_styrenhet(argument)
    rader += _rader_mal(spec, "t")
    rader += [
        "konf = []",
        "nabara = []",
        "for i in range(t.ConfigCount):",
        "    w = t.getConfigWarning(i)",
        '    post = {"config": i, "warning": int(w),',
        "            \"ok\": w == %s," % VARNING_OK,
    ]
    for etikett, konstant in VARNINGSBITAR:
        rader.append('            "%s": bool(w & %s),' % (etikett, konstant))
    rader = rader[:-1] + [rader[-1].rstrip(",") + "}"]
    rader += [
        "    konf.append(post)",
        '    if post["ok"]:',
        "        nabara.append(i)",
        "varden = []",
        "vald = None",
        "if nabara:",
        "    vald = nabara[0]",
        "    t.RobotConfig = vald",
        "    for v in t.JointValues:",
        "        varden.append(v)",
        '_svara({"robot": k.Name, "controller": r.Name,',
        '        "reachable": bool(nabara), "config_count": t.ConfigCount,',
        '        "configurations": konf, "reachable_configs": nabara,',
        '        "chosen_config": vald, "joint_values": varden})',
    ]
    return bygg(["_svara"], rader,
                ["vcMatrix", "vcVector"] if "joint_values" not in spec else [])


_lagg(
    "check_reach",
    "Fragar VC om roboten nar en punkt, och i sa fall med vilka "
    "konfigurationer. Varje konfiguration domes med VC:s eget varningstal: "
    "utanfor rackvidd, ledgrans passerad eller singularitet. Ledvardena som "
    "kommer tillbaka ar VC:s losning for den forsta nabara konfigurationen. "
    "OBSERVERA: verktyget FRAGAR bara, men det maste skapa ett rorelsemal i "
    "styrenheten for att kunna fraga, och bryggans skrivgrind domer det som "
    "en andring. Darfor gar det genom godkannandekon.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "position": _MALEGENSKAPER["position"],
            "wpr": _MALEGENSKAPER["wpr"],
            "target_mode": _MALEGENSKAPER["target_mode"],
            "base": ARG_RAM_BAS, "tool": ARG_RAM_VERKTYG,
            "motion": _MALEGENSKAPER["motion"]},
           ["component", "position"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "reachable": {"type": "boolean",
                           "description": "Sant om minst en konfiguration ar felfri."},
             "config_count": {"type": "integer",
                              "description": "Antal konfigurationer kinematiken har."},
             "configurations": {"type": "array",
                                "description": "Domen per konfiguration.",
                                "items": _KONFIGPOST},
             "reachable_configs": {"type": "array",
                                   "description": "Numren pa de felfria konfigurationerna.",
                                   "items": {"type": "integer",
                                             "description": "Ett konfigurationsnummer."}},
             "chosen_config": {"type": ["integer", "null"],
                               "description": "Konfigurationen ledvardena galler, eller null."},
             "joint_values": {"type": "array",
                              "description": ("VC:s losning for den valda "
                                              "konfigurationen. Tom nar punkten "
                                              "inte gar att na."),
                              "items": {"type": "number", "description": "Ett ledvarde."}}},
            ["robot", "controller", "reachable", "config_count",
             "configurations", "reachable_configs", "joint_values"]),
    _YTOR_ROBOT,
    _kod_check_reach,
)


# ---- forward_kinematics --------------------------------------------------

def _kod_forward_kinematics(argument):
    spec = {"joint_values": argument["values"],
            "target_mode": argument["target_mode"]}
    if "base" in argument:
        spec["base"] = argument["base"]
    if "tool" in argument:
        spec["tool"] = argument["tool"]
    rader = _rader_styrenhet(argument)
    rader += _rader_mal(spec, "t")
    rader += [
        # Lagesmatrisen lases UT ur malet: med UseJoints satt raknar VC fram
        # den kartesiska motsvarigheten till ledvardena. Det ar framatkinematik
        # utan att roboten ror sig.
        "mt = t.Target",
        "wt = mt.getWPR()",
        '_svara({"robot": k.Name, "controller": r.Name,',
        '        "target_mode": %s,' % lit(argument["target_mode"]),
        '        "position": [mt.P.X, mt.P.Y, mt.P.Z],',
        '        "wpr": [wt.X, wt.Y, wt.Z],',
        '        "base": t.BaseName, "tool": t.ToolName})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "forward_kinematics",
    "Raknar ut var verktygspunkten hamnar for givna ledvarden, UTAN att "
    "flytta roboten. target_mode=world ger svaret i varldskoordinater, "
    "normal ger det relativt basramen. OBSERVERA: verktyget raknar bara, men "
    "maste skapa ett rorelsemal i styrenheten for att gora det, och bryggans "
    "skrivgrind domer det som en andring. Darfor gar det genom kon.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "values": {"type": "array",
                       "description": "Ledvarden i ledernas ordning.",
                       "items": {"type": "number", "description": "Ett ledvarde."},
                       "minItems": 1, "maxItems": 20},
            "target_mode": dict(_MALEGENSKAPER["target_mode"], default="world"),
            "base": ARG_RAM_BAS, "tool": ARG_RAM_VERKTYG},
           ["component", "values"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "target_mode": {"type": "string",
                             "description": "Vad laget ar relativt till."},
             "position": dict(XYZ, description="Verktygspunktens lage."),
             "wpr": dict(XYZ, description="Verktygspunktens orientering."),
             "base": {"type": ["string", "null"], "description": "Basramen malet raknades i."},
             "tool": {"type": ["string", "null"], "description": "Verktygsramen malet raknades i."}},
            ["robot", "controller", "target_mode", "position", "wpr"]),
    _YTOR_ROBOT,
    _kod_forward_kinematics,
)


# ---- set_robot_config ----------------------------------------------------

_KONFIGFALT = (
    ("speed_percent", "Speed", "tal"),
    ("max_cartesian_speed", "MaxCartesianSpeed", "tal"),
    ("max_cartesian_acceleration", "MaxCartesianAccel", "tal"),
    ("max_angular_speed", "MaxAngularSpeed", "tal"),
    ("max_angular_acceleration", "MaxAngularAccel", "tal"),
    ("lag_time", "LagTime", "tal"),
    ("settle_time", "SettleTime", "tal"),
    ("initial_tool", "InitialTool", "text"),
    ("initial_base", "InitialBase", "text"),
)


def _kod_set_robot_config(argument):
    rader = _rader_styrenhet(argument)
    for nyckel, attribut, slag in _KONFIGFALT:
        if nyckel not in argument:
            continue
        varde = tal(argument[nyckel]) if slag == "tal" else lit(argument[nyckel])
        rader.append("r.%s = %s" % (attribut, varde))
    if "approach_axis" in argument:
        rader.append("r.ApproachAxis = %s"
                     % _konstant(NARMNINGSAXLAR, argument["approach_axis"]))
    if "configuration_mode" in argument:
        rader.append("r.ConfigurationMode = %s"
                     % _konstant(KONFIGLAGEN, argument["configuration_mode"]))
    rader += [
        '_svara({"robot": k.Name, "controller": r.Name, "set": True,',
        '        "speed_percent": r.Speed,',
        '        "max_cartesian_speed": r.MaxCartesianSpeed,',
        '        "max_cartesian_acceleration": r.MaxCartesianAccel,',
        '        "max_angular_speed": r.MaxAngularSpeed,',
        '        "max_angular_acceleration": r.MaxAngularAccel,',
        '        "lag_time": r.LagTime, "settle_time": r.SettleTime,',
        '        "initial_tool": r.InitialTool, "initial_base": r.InitialBase,',
        '        "approach_axis": _enkelt(r.ApproachAxis),',
        '        "configuration_mode": _enkelt(r.ConfigurationMode)})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "set_robot_config",
    "Andrar styrenhetens instalningar: hastigheter, accelerationer, "
    "efterslapning och sattning, narmningsaxel, konfigurationslage och vilka "
    "ramar roboten startar i. Allt utom component ar valfritt, och det som "
    "utelamnas lamnas orort. Ramnamnen maste finnas; hamta dem med "
    "list_frames.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "speed_percent": {"type": "number",
                              "description": ("Ledhastighet som procent av "
                                              "maxfart, 0 till 100.")},
            "max_cartesian_speed": {"type": "number",
                                    "description": "Hogsta linjara hastighet, mm/s."},
            "max_cartesian_acceleration": {"type": "number",
                                           "description": "Hogsta linjara acceleration, mm/s^2."},
            "max_angular_speed": {"type": "number",
                                  "description": "Hogsta vridhastighet, grader/s."},
            "max_angular_acceleration": {"type": "number",
                                         "description": "Hogsta vridacceleration, grader/s^2."},
            "lag_time": {"type": "number",
                         "description": "Efterslapningstid i sekunder."},
            "settle_time": {"type": "number",
                            "description": "Sattningstid i sekunder."},
            "initial_tool": {"type": "string",
                             "description": "Verktygsram att starta i."},
            "initial_base": {"type": "string",
                             "description": "Basram att starta i."},
            "approach_axis": {"type": "string",
                              "enum": _etiketter(NARMNINGSAXLAR),
                              "description": ("Vilken av verktygsramens axlar "
                                              "som pekar mot arbetsstycket.")},
            "configuration_mode": {"type": "string",
                                   "enum": _etiketter(KONFIGLAGEN),
                                   "description": ("Hur konfigurationen halls "
                                                   "under linjar rorelse.")}},
           ["component"],
           minst_en_av=[("speed_percent", "max_cartesian_speed",
                         "max_cartesian_acceleration", "max_angular_speed",
                         "max_angular_acceleration", "lag_time", "settle_time",
                         "initial_tool", "initial_base", "approach_axis",
                         "configuration_mode")]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "set": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "speed_percent": {"type": "number", "description": "Vardet efterat."},
             "max_cartesian_speed": {"type": "number", "description": "Vardet efterat."},
             "max_cartesian_acceleration": {"type": "number", "description": "Vardet efterat."},
             "max_angular_speed": {"type": "number", "description": "Vardet efterat."},
             "max_angular_acceleration": {"type": "number", "description": "Vardet efterat."},
             "lag_time": {"type": "number", "description": "Vardet efterat."},
             "settle_time": {"type": "number", "description": "Vardet efterat."},
             "initial_tool": {"type": ["string", "null"], "description": "Vardet efterat."},
             "initial_base": {"type": ["string", "null"], "description": "Vardet efterat."},
             "approach_axis": {"type": ["string", "number", "integer", "null"],
                               "description": "Vardet efterat, som VC:s upprakning."},
             "configuration_mode": {"type": ["string", "number", "integer", "null"],
                                    "description": "Vardet efterat, som VC:s upprakning."}},
            ["robot", "controller", "set", "speed_percent",
             "max_cartesian_speed", "max_angular_speed"]),
    _YTOR_ROBOT,
    _kod_set_robot_config,
)


# ---- add_frame -----------------------------------------------------------

def _kod_add_frame(argument):
    slag = argument["kind"]
    rader = _rader_styrenhet(argument)
    rader.append("f = r.addTool()" if slag == "tool" else "f = r.addBase()")
    rader += [
        "if f is None:",
        '    raise ValueError("VC lamnade ingen ram tillbaka")',
        "f.Name = %s" % lit(argument["name"]),
    ]
    if "node" in argument:
        rader += [
            "nd = k.findNode(%s)" % lit(argument["node"]),
            "if nd is None:",
            '    raise ValueError(k.Name + " har ingen nod som heter " + %s)'
            % lit(argument["node"]),
            "f.Node = nd",
        ]
    if "position_expression" in argument:
        rader.append("f.PositionExpression = %s"
                     % lit(argument["position_expression"]))
    behover_matris = "position" in argument or "wpr" in argument
    if behover_matris:
        rader += _rader_matris(argument, "mm")
        rader.append("f.PositionMatrix = mm")
    rader += [
        "mfr = f.PositionMatrix",
        "wfr = mfr.getWPR()",
        "vnod = None",
        "if f.Node is not None:",
        "    vnod = f.Node.Name",
        '_svara({"robot": k.Name, "controller": r.Name, "added": True,',
        '        "kind": %s, "name": f.Name, "node": vnod,' % lit(slag),
        '        "position": [mfr.P.X, mfr.P.Y, mfr.P.Z],',
        '        "wpr": [wfr.X, wfr.Y, wfr.Z]})',
    ]
    return bygg(["_svara"], rader,
                ["vcMatrix", "vcVector"] if behover_matris else [])


_lagg(
    "add_frame",
    "Definierar en ny verktygsram eller basram i styrenheten. Namnet ar "
    "obligatoriskt: utan det numrerar VC sjalv och du vet inte vad ramen "
    "heter nasta gang. Laget kan anges som tal eller som VC-uttryck, och "
    "noden ar den nod ramen sitter fast i.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "kind": {"type": "string", "enum": ["tool", "base"],
                     "description": "tool for verktygsram, base for basram."},
            "name": {"type": "string", "description": "Namn att ge ramen."},
            "node": {"type": "string",
                     "description": ("Nod i robotkomponenten som ramen sitter "
                                     "pa. Utelamnad lamnar VC:s eget val.")},
            "position": dict(XYZ, description="Ramens lage i nodens koordinater, mm."),
            "wpr": dict(XYZ, description="Ramens orientering, samma tre tal som get_tcp lamnar."),
            "position_expression": {"type": "string",
                                    "description": ("VC-uttryck for ramens lage, "
                                                    "i stallet for fasta tal.")}},
           ["component", "kind", "name"]),
    returns({"robot": RET_ROBOT, "controller": RET_STYRENHET,
             "added": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "kind": {"type": "string", "description": "Slaget som skapades."},
             "name": {"type": "string", "description": "Ramens namn."},
             "node": {"type": ["string", "null"], "description": "Noden ramen sitter pa."},
             "position": XYZ, "wpr": XYZ},
            ["robot", "controller", "added", "kind", "name", "position", "wpr"]),
    _YTOR_ROBOT_FINDNODE,
    _kod_add_frame,
)


# ---- create_routine ------------------------------------------------------

def _kod_create_routine(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += [
        "pr = x.Program",
        "if pr is None:",
        '    raise ValueError(k.Name + " har en utforare utan program")',
        "ru = pr.addRoutine(%s)" % lit(argument["name"]),
        "if ru is None:",
        '    raise ValueError("VC skapade ingen rutin som heter " + %s)'
        % lit(argument["name"]),
        '_svara({"robot": k.Name, "program": pr.Name, "created": True,',
        '        "routine": ru.Name, "statements": len(ru.Statements)})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "create_routine",
    "Skapar en ny, tom rutin i robotprogrammet. Rutinen kors inte av sig "
    "sjalv; den anropas fran huvudrutinen med en call-sats eller direkt med "
    "run_routine.",
    "write",
    params({"component": ARG_ROBOT,
            "name": {"type": "string", "description": "Namn att ge rutinen."}},
           ["component", "name"]),
    returns({"robot": RET_ROBOT,
             "program": {"type": ["string", "null"], "description": "Programmets namn."},
             "created": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "routine": RET_RUTIN,
             "statements": {"type": "integer", "description": "Antal satser, noll i en ny rutin."}},
            ["robot", "created", "routine", "statements"]),
    _YTOR_ROBOT,
    _kod_create_routine,
)


# ---- delete_routine ------------------------------------------------------

def _kod_delete_routine(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += _rader_rutin({"routine": argument["routine"]})
    rader += [
        "antal = len(ru.Statements)",
        "pr.deleteRoutine(ru)",
        '_svara({"robot": k.Name, "deleted": True, "routine": %s,'
        % lit(argument["routine"]),
        '        "statements_deleted": antal,',
        '        "routines_left": len(pr.Routines)})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "delete_routine",
    "Tar bort en rutin ur programmet med alla dess satser. Huvudrutinen gar "
    "inte att ta bort; ange den vid namn och VC nekar.",
    "write",
    params({"component": ARG_ROBOT,
            "routine": {"type": "string",
                        "description": "Rutinens namn. Obligatoriskt har."}},
           ["component", "routine"]),
    returns({"robot": RET_ROBOT,
             "deleted": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "routine": RET_RUTIN,
             "statements_deleted": {"type": "integer",
                                    "description": "Antal satser som forsvann med rutinen."},
             "routines_left": {"type": "integer",
                               "description": "Antal rutiner kvar utover huvudrutinen."}},
            ["robot", "deleted", "routine", "statements_deleted",
             "routines_left"]),
    _YTOR_ROBOT,
    _kod_delete_routine,
)


# ---- add_motion_statement ------------------------------------------------

def _kod_add_motion_statement(argument):
    if "properties" in argument:
        _granska_egenskapsvarden(argument["properties"], "add_motion_statement")
    if "joint_values" not in argument and "position" not in argument:
        raise Argumentfel("add_motion_statement",
                          ["en rorelsesats maste veta VART den ska: ange "
                           "position eller joint_values"])
    behover_r = "base" in argument or "tool" in argument
    rader = (_rader_styrenhet(argument) if behover_r
             else _rader_komponent(argument["component"]))
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    konstant = _konstant(RORELSESATSER,
                         "motion_linear" if argument["motion"] == "linear"
                         else "motion_joint")
    if "index" in argument:
        rader.append("sats = ru.addStatement(%s, %d)"
                     % (konstant, argument["index"]))
    else:
        rader.append("sats = ru.addStatement(%s)" % konstant)
    rader += [
        "if sats is None:",
        '    raise ValueError("VC skapade ingen rorelsesats")',
    ]
    if "name" in argument:
        rader.append("sats.Name = %s" % lit(argument["name"]))
    if "base" in argument:
        rader += _rader_hitta_ram(argument["base"], "r.Bases", "rambas", "basram")
        rader.append("sats.Base = rambas")
    if "tool" in argument:
        rader += _rader_hitta_ram(argument["tool"], "r.Tools", "ramverktyg",
                                  "verktygsram")
        rader.append("sats.Tool = ramverktyg")
    if "zone_method" in argument:
        rader.append("sats.AccuracyMethod = %s"
                     % _konstant(ZONMETODER, argument["zone_method"]))
    if "zone_value" in argument:
        rader.append("sats.AccuracyValue = %s" % tal(argument["zone_value"]))
    if "cycle_time" in argument:
        rader.append("sats.CycleTime = %s" % tal(argument["cycle_time"]))
    if "external_tcp" in argument:
        rader.append("sats.ExternalTCP = %r" % bool(argument["external_tcp"]))
    rader += _rader_position(argument)
    if "properties" in argument:
        rader += _rader_satt_egenskaper(argument["properties"])
    rader += [
        '_svara({"robot": k.Name, "routine": ru.Name, "added": True,',
        '        "statement": sats.Name, "index": len(ru.Statements) - 1,',
        '        "motion": %s, "positions": len(sats.Positions)})'
        % lit(argument["motion"]),
    ]
    behover_matris = "position" in argument or "wpr" in argument
    return bygg(["_svara"], rader,
                ["vcMatrix", "vcVector"] if behover_matris else [])


def _rader_position(argument):
    """Satter rorelsesatsens position, som ledvarden eller som matris."""
    rader = [
        # En ny rorelsesats far normalt en position av VC sjalv. Ar listan
        # anda tom skapas en, sa att satsen aldrig blir en rorelse utan mal.
        "if len(sats.Positions) > 0:",
        "    pos = sats.Positions[0]",
        "else:",
        "    pos = sats.createPosition(%s)" % lit("P1"),
        "if pos is None:",
        '    raise ValueError("rorelsesatsen fick ingen position")',
    ]
    if "joint_values" in argument:
        varden = ", ".join(tal(v) for v in argument["joint_values"])
        rader.append("pos.setJoints([%s])" % varden)
    else:
        rader += _rader_matris(argument, "mm")
        rader.append("pos.PositionInReference = mm")
    return rader


_lagg(
    "add_motion_statement",
    "Lagger en rorelsesats i en rutin: led (punkt till punkt) eller linjar. "
    "Ange vart roboten ska med position eller med joint_values. Zon, "
    "cykeltid, basram och verktygsram satts har och galler den satsen. "
    "Hastighet ar INTE en deklarerad yta pa rorelsesatsen i VC; den satts "
    "med properties, och namnen laser du ut med read_routine.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "routine": ARG_RUTIN,
            "motion": {"type": "string", "enum": ["joint", "linear"],
                       "default": "joint",
                       "description": ("joint ar punkt till punkt, linear ar "
                                       "rat linje.")},
            "position": dict(XYZ, description=(
                "Malets lage i basramens koordinater, mm. Ange position eller "
                "joint_values.")),
            "wpr": dict(XYZ, description="Malets orientering, samma tre tal som get_tcp lamnar."),
            "joint_values": {"type": "array",
                             "description": "Malet som ledvarden i ledernas ordning.",
                             "items": {"type": "number", "description": "Ett ledvarde."},
                             "minItems": 1, "maxItems": 20},
            "index": {"type": "integer",
                      "description": ("Plats i rutinen. Utelamnad lagger satsen "
                                      "sist.")},
            "name": {"type": "string", "description": "Namn att ge satsen."},
            "base": ARG_RAM_BAS, "tool": ARG_RAM_VERKTYG,
            "zone_method": _MALEGENSKAPER["zone_method"],
            "zone_value": _MALEGENSKAPER["zone_value"],
            "cycle_time": {"type": "number",
                           "description": ("Tid satsen ska ta i sekunder. Skalar "
                                           "hastighet och acceleration.")},
            "external_tcp": {"type": "boolean",
                             "description": ("Sant nar verktyget star still och "
                                             "arbetsstycket bars av roboten.")},
            "properties": ARG_EGENSKAPER},
           ["component"], minst_en_av=[("position", "joint_values")]),
    returns({"robot": RET_ROBOT, "routine": RET_RUTIN,
             "added": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "statement": {"type": "string", "description": "Satsens namn."},
             "index": {"type": "integer", "description": "Satsens plats i rutinen."},
             "motion": {"type": "string", "description": "Rorelsens slag."},
             "positions": {"type": "integer",
                           "description": "Antal positioner satsen bar."}},
            ["robot", "routine", "added", "statement", "motion", "positions"]),
    _YTOR_ROBOT,
    _kod_add_motion_statement,
)


# ---- add_statement -------------------------------------------------------

def _kod_add_statement(argument):
    if "properties" in argument:
        _granska_egenskapsvarden(argument["properties"], "add_statement")
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    konstant = _konstant(SATSTYPER, argument["type"])
    if "index" in argument:
        rader.append("sats = ru.addStatement(%s, %d)"
                     % (konstant, argument["index"]))
    else:
        rader.append("sats = ru.addStatement(%s)" % konstant)
    rader += [
        "if sats is None:",
        '    raise ValueError("VC skapade ingen sats av typen %s")'
        % argument["type"],
    ]
    if "name" in argument:
        rader.append("sats.Name = %s" % lit(argument["name"]))
    if "properties" in argument:
        rader += _rader_satt_egenskaper(argument["properties"])
    rader += [
        "egenskaper = []",
        "for pp in sats.Properties:",
        '    egenskaper.append({"name": pp.Name, "value": _enkelt(pp.Value)})',
        '_svara({"robot": k.Name, "routine": ru.Name, "added": True,',
        '        "statement": sats.Name, "type": %s,' % lit(argument["type"]),
        '        "index": len(ru.Statements) - 1,',
        '        "properties": egenskaper})',
    ]
    return bygg(["_enkelt", "_svara"], rader)


_lagg(
    "add_statement",
    "Lagger en sats i en rutin: grepp, slapp, vantan pa signal, satt signal, "
    "fordrojning, villkor, loop, anrop av rutin, kommentar och de ovriga i "
    "listan. Rorelsesatser skapas INTE har utan med add_motion_statement. "
    "Satsens egna falt satts med properties; svaret listar alla falt satsen "
    "fick, sa att du ser vad den heter om ett namn var fel.",
    "write",
    params({"component": ARG_ROBOT, "routine": ARG_RUTIN,
            "type": {"type": "string", "enum": _etiketter(SATSTYPER),
                     "description": "Satsens slag."},
            "index": {"type": "integer",
                      "description": ("Plats i rutinen. Utelamnad lagger satsen "
                                      "sist.")},
            "name": {"type": "string", "description": "Namn att ge satsen."},
            "properties": ARG_EGENSKAPER},
           ["component", "type"]),
    returns({"robot": RET_ROBOT, "routine": RET_RUTIN,
             "added": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "statement": {"type": "string", "description": "Satsens namn."},
             "type": {"type": "string", "description": "Slaget som skapades."},
             "index": {"type": "integer", "description": "Satsens plats i rutinen."},
             "properties": {"type": "array",
                            "description": "Alla falt satsen bar efterat.",
                            "items": _EGENSKAPSPOST}},
            ["robot", "routine", "added", "statement", "type", "properties"]),
    _YTOR_ROBOT,
    _kod_add_statement,
)


# ---- edit_statement ------------------------------------------------------

def _kod_edit_statement(argument):
    if "properties" in argument:
        _granska_egenskapsvarden(argument["properties"], "edit_statement")
    behover_r = "base" in argument or "tool" in argument
    rader = (_rader_styrenhet(argument) if behover_r
             else _rader_komponent(argument["component"]))
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    rader += _rader_sats(argument["index"])
    if "name" in argument:
        rader.append("sats.Name = %s" % lit(argument["name"]))
    for nyckel, attribut, slag in (("zone_value", "AccuracyValue", "tal"),
                                   ("cycle_time", "CycleTime", "tal")):
        if nyckel not in argument:
            continue
        rader += [
            'if not hasattr(sats, "%s"):' % attribut,
            '    raise ValueError("satsen " + sats.Name + " har inget %s;'
            ' det faltet finns bara pa rorelsesatser")' % attribut,
            "sats.%s = %s" % (attribut, tal(argument[nyckel])),
        ]
    if "zone_method" in argument:
        rader += [
            'if not hasattr(sats, "AccuracyMethod"):',
            '    raise ValueError("satsen " + sats.Name + " har ingen'
            ' AccuracyMethod; det faltet finns bara pa rorelsesatser")',
            "sats.AccuracyMethod = %s"
            % _konstant(ZONMETODER, argument["zone_method"]),
        ]
    if "external_tcp" in argument:
        rader += [
            'if not hasattr(sats, "ExternalTCP"):',
            '    raise ValueError("satsen " + sats.Name + " har ingen'
            ' ExternalTCP; det faltet finns bara pa rorelsesatser")',
            "sats.ExternalTCP = %r" % bool(argument["external_tcp"]),
        ]
    if "base" in argument:
        rader += _rader_hitta_ram(argument["base"], "r.Bases", "rambas", "basram")
        rader += [
            'if not hasattr(sats, "Base"):',
            '    raise ValueError("satsen " + sats.Name + " har ingen basram")',
            "sats.Base = rambas",
        ]
    if "tool" in argument:
        rader += _rader_hitta_ram(argument["tool"], "r.Tools", "ramverktyg",
                                  "verktygsram")
        rader += [
            'if not hasattr(sats, "Tool"):',
            '    raise ValueError("satsen " + sats.Name + " har ingen'
            ' verktygsram")',
            "sats.Tool = ramverktyg",
        ]
    behover_matris = "position" in argument or "wpr" in argument
    if behover_matris or "joint_values" in argument:
        rader += [
            'if not hasattr(sats, "Positions"):',
            '    raise ValueError("satsen " + sats.Name + " bar ingen position;'
            ' bara rorelsesatser gor det")',
        ]
        rader += _rader_position(argument)
    if "properties" in argument:
        rader += _rader_satt_egenskaper(argument["properties"])
    rader += [
        "egenskaper = []",
        "for pp in sats.Properties:",
        '    egenskaper.append({"name": pp.Name, "value": _enkelt(pp.Value)})',
        '_svara({"robot": k.Name, "routine": ru.Name, "edited": True,',
        '        "statement": sats.Name, "index": %d,' % argument["index"],
        '        "properties": egenskaper})',
    ]
    return bygg(["_enkelt", "_svara"], rader,
                ["vcMatrix", "vcVector"] if behover_matris else [])


_lagg(
    "edit_statement",
    "Andrar en sats som redan finns, utpekad med sitt index i rutinen. "
    "Satsens egna falt andras med properties; rorelsesatsens deklarerade falt "
    "- basram, verktygsram, zon, cykeltid och positionen - har egna argument. "
    "Ett rorelsefalt pa en sats som inte ar en rorelsesats avvisas med "
    "satsens namn i felet.",
    "write",
    params({"component": ARG_ROBOT, "controller": ARG_STYRENHET,
            "routine": ARG_RUTIN, "index": ARG_SATSINDEX,
            "name": {"type": "string", "description": "Nytt namn pa satsen."},
            "position": dict(XYZ, description="Nytt lage for en rorelsesats, mm."),
            "wpr": dict(XYZ, description="Ny orientering for en rorelsesats."),
            "joint_values": {"type": "array",
                             "description": "Nya ledvarden for en rorelsesats.",
                             "items": {"type": "number", "description": "Ett ledvarde."},
                             "minItems": 1, "maxItems": 20},
            "base": ARG_RAM_BAS, "tool": ARG_RAM_VERKTYG,
            "zone_method": _MALEGENSKAPER["zone_method"],
            "zone_value": _MALEGENSKAPER["zone_value"],
            "cycle_time": {"type": "number", "description": "Ny cykeltid i sekunder."},
            "external_tcp": {"type": "boolean",
                             "description": "Nytt varde for extern verktygspunkt."},
            "properties": ARG_EGENSKAPER},
           ["component", "index"],
           minst_en_av=[("name", "position", "wpr", "joint_values", "base",
                         "tool", "zone_method", "zone_value", "cycle_time",
                         "external_tcp", "properties")]),
    returns({"robot": RET_ROBOT, "routine": RET_RUTIN,
             "edited": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "statement": {"type": "string", "description": "Satsens namn."},
             "index": {"type": "integer", "description": "Satsens plats i rutinen."},
             "properties": {"type": "array",
                            "description": "Alla falt satsen bar efterat.",
                            "items": _EGENSKAPSPOST}},
            ["robot", "routine", "edited", "statement", "index", "properties"]),
    _YTOR_ROBOT,
    _kod_edit_statement,
)


# ---- delete_statement ----------------------------------------------------

def _kod_delete_statement(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    rader += _rader_sats(argument["index"])
    rader += [
        "namn = sats.Name",
        "ru.deleteStatement(sats)",
        '_svara({"robot": k.Name, "routine": ru.Name, "deleted": True,',
        '        "statement": namn, "index": %d,' % argument["index"],
        '        "statements_left": len(ru.Statements)})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "delete_statement",
    "Tar bort en sats ur en rutin, utpekad med sitt index. Indexen for de "
    "satser som ligger efter flyttas ned ett steg, sa las om rutinen med "
    "read_routine innan du tar bort nasta.",
    "write",
    params({"component": ARG_ROBOT, "routine": ARG_RUTIN,
            "index": ARG_SATSINDEX},
           ["component", "index"]),
    returns({"robot": RET_ROBOT, "routine": RET_RUTIN,
             "deleted": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "statement": {"type": "string", "description": "Namnet pa satsen som togs bort."},
             "index": {"type": "integer", "description": "Platsen den lag pa."},
             "statements_left": {"type": "integer",
                                 "description": "Antal satser kvar i rutinen."}},
            ["robot", "routine", "deleted", "statement", "index",
             "statements_left"]),
    _YTOR_ROBOT,
    _kod_delete_statement,
)


# ---- run_routine ---------------------------------------------------------

def _kod_run_routine(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    # suspendScript=False later bryggan svara direkt. True skulle halla
    # exec-korningen kvar tills rutinen ar klar, och en rutin som vantar pa
    # en signal blir da en tyst timeout i stallet for ett svar.
    rader += [
        "kor = bool(getSimulation().IsRunning)",
        "x.callRoutine(ru, %r)" % bool(argument["wait"]),
        '_svara({"robot": k.Name, "executor": x.Name, "started": True,',
        '        "routine": ru.Name, "waited": %r,' % bool(argument["wait"]),
        '        "simulation_running": kor})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "run_routine",
    "Kor en rutin i roboten. En rutin utfors BARA medan simuleringen gar; "
    "svaret sager om den gjorde det, sa att en tyst icke-korning inte ser ut "
    "som en lyckad. wait=false later anropet svara direkt, vilket ar ratt nar "
    "rutinen vantar pa signaler.",
    "write",
    params({"component": ARG_ROBOT, "routine": ARG_RUTIN,
            "wait": {"type": "boolean", "default": False,
                     "description": ("true haller korningen kvar tills rutinen "
                                     "ar klar. Anvand bara for korta rutiner: "
                                     "en rutin som vantar pa en signal ger "
                                     "annars en timeout i stallet for ett "
                                     "svar.")}},
           ["component"]),
    returns({"robot": RET_ROBOT,
             "executor": {"type": "string", "description": "Programutforarens namn."},
             "started": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "routine": RET_RUTIN,
             "waited": {"type": "boolean", "description": "Om anropet vantade in rutinen."},
             "simulation_running": {"type": "boolean",
                                    "description": ("Om simuleringen gick. Var den "
                                                    "stilla hander ingenting.")}},
            ["robot", "executor", "started", "routine", "waited",
             "simulation_running"]),
    _YTOR_ROBOT_SIM,
    _kod_run_routine,
    timeout_ms=TIMEOUT_MS_RORELSE,
)


# ---- step_statement ------------------------------------------------------

def _kod_step_statement(argument):
    rader = _rader_komponent(argument["component"])
    rader += _rader_utforare()
    rader += _rader_rutin(argument)
    rader += _rader_sats(argument["index"])
    rader += [
        "kor = bool(getSimulation().IsRunning)",
        "x.callStatement(sats, %r)" % bool(argument["wait"]),
        '_svara({"robot": k.Name, "executor": x.Name, "stepped": True,',
        '        "routine": ru.Name, "statement": sats.Name,',
        '        "index": %d, "waited": %r,' % (argument["index"],
                                                bool(argument["wait"])),
        '        "simulation_running": kor})',
    ]
    return bygg(["_svara"], rader)


_lagg(
    "step_statement",
    "Kor EN sats ur en rutin, utan att kora resten. Det ar stegningen: las "
    "rutinen med read_routine, kor sats for sats och las var roboten star "
    "med get_tcp emellan. Precis som run_routine hander ingenting nar "
    "simuleringen star stilla, och svaret sager om den gjorde det.",
    "write",
    params({"component": ARG_ROBOT, "routine": ARG_RUTIN,
            "index": ARG_SATSINDEX,
            "wait": {"type": "boolean", "default": True,
                     "description": ("true vantar in satsen innan svaret ges, "
                                     "vilket ar det normala for stegning. "
                                     "false svarar direkt.")}},
           ["component", "index"]),
    returns({"robot": RET_ROBOT,
             "executor": {"type": "string", "description": "Programutforarens namn."},
             "stepped": {"type": "boolean", "description": "Alltid true; ett misslyckande kastar."},
             "routine": RET_RUTIN,
             "statement": {"type": "string", "description": "Satsen som kordes."},
             "index": {"type": "integer", "description": "Satsens plats i rutinen."},
             "waited": {"type": "boolean", "description": "Om anropet vantade in satsen."},
             "simulation_running": {"type": "boolean",
                                    "description": "Om simuleringen gick."}},
            ["robot", "executor", "stepped", "routine", "statement", "index",
             "waited", "simulation_running"]),
    _YTOR_ROBOT_SIM,
    _kod_step_statement,
    timeout_ms=TIMEOUT_MS_RORELSE,
)
