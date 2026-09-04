# -*- coding: utf-8 -*-
"""Domanen simulation: tidsaxeln som allt annat mats pa.

Kalla for urvalet: docs/spec/47_verktygstackning.md avsnitt 4.3, som rangordnar
domanen som nummer ETT av tjugotre. Skalet star dar och det ar inte omfang:
ytan ar naste minst av alla (2 typer, 23 metoder, 17 egenskaper), men ogat
provtar pa sim.SimTime (40_ogat.md) och ingen grind i 50_grindar.md kan falla
nagot utan en tidsaxel. Fem av sex personaprofiler ror domanen, fyra av dem kan
inte arbeta utan den.

MATT 2026-09-04 (M-47): NOLL av domanens verktyg var byggda, och bara 5 av dess
20 namngivna API-symboler rordes av nagon byggd mall. Det ar den storsta
enskilda luckan i verktygsbiblioteket.

VAD SOM AR OPROVAT, SAGT RAKT
-----------------------------
Ingen rad har har kort mot en levande VC. Provat ar allt som gar att prova utan
VC: schemat, argumentvalideringen, routingen, korsprovet mot bryggans skrivgrind
och korsprovet mot API-indexet. Att VC svarar som kallan sager ar OPROVAT, och
tva rader ar dessutom oprovade av ett SKAL som star i kallan sjalv:

  * vcSimulation.SimulationRunTime bar noteringen "Changing the
    SimulationRunTime is only allowed in the OnRun event". Bryggan kor inte i
    OnRun. sim_warmup laser darfor tillbaka vardet och KASTAR om det inte tog -
    verktyget far inte pasta att det satt nagot det inte kan lasa tillbaka
    (I3, 41_ogat_kontrakt.md).
  * vcSimulation.setFastScheduling har INGEN motsvarande egenskap att lasa
    tillbaka. set_fast_scheduling svarar darfor verified=false och sager i
    klartext att sattningen inte gick att bekrafta. Det ar den enda arliga
    formen; ett "satt: true" hade varit en stubbe (S1).

VARFOR install_script_behaviour INTE BYGGS
-------------------------------------------
47_verktygstackning.md avsnitt 4.3 foreslar tolv verktyg. Elva byggs har.
`install_script_behaviour` byggs INTE, och det ar ingen forsummelse:
M-13 matte att ett skriptbeteende STOPPAR simuleringen och tar ned pumpen mitt
i dess eget svar, och bryggans egen skrivgrind.skapar_skriptbeteende() avvisar
varje mall som skapar ett. Ett verktyg som bara kan misslyckas ar en stubbe.
Raden hor till gransen i 47:s avsnitt 7, inte till byggordningen.

FORMAGEGRINDEN OCH DE YTOR SOM INTE GAR ATT DEKLARERA
-----------------------------------------------------
`kraver` far bara namna ytor som star i formaga.YTOR, for det ar de enda
grinden kan prova. Fem av domanens ytor star dar: sim.SimTime, sim.IsRunning,
sim.SimSpeed, sim.run, sim.reset, plus app.render. De ovriga - halt,
continueRun, update, setFastScheduling, SimWarmupTime, SimulationRunTime,
setInitialState, restoreInitialState, autoHalt, IsLooping - gor det INTE.
Samma losning som robotik.py och granssnitt.py: `kraver` deklarerar den vag
mallen faktiskt gar, och de odeklarerbara ytorna provas PER OBJEKT i mallen med
hasattr. Luckan ar mekaniskt fastlagd i
tests/enhet/test_verktyg_simmatning.py, sa den dag formaga.py far raderna
faller ett prov och `kraver` ska skarpas.
"""
from __future__ import annotations

from .bas import TIMEOUT_MS_FIL, laggare, params, returns
from .fel import Argumentfel
from .kodmall import bygg, lit, tal

DOMAN = "simulation"
_lagg = laggare(DOMAN)

# Tak for en korning som far simuleringen att STEGA FRAM i tid.
#
# Talet ar med flit inget eget tal, utan bas.TIMEOUT_MS_FIL. Skalet ar samma
# som robotik.py anger for TIMEOUT_MS_RORELSE: harkomsten gar inte att skaffa
# har - hur lang vaggtid en simulerad sekund kostar beror pa scenen, och MATT
# 2026-09-04 finns noll komponenter i den lokala katalogen att tidta mot. Ett
# eget tal hade varit en gissning som ser ut som en matning. Storheten ar
# densamma i den enda mening som styr valet: sekunder, inte millisekunder.
# Ett overskridande ar inte tyst - bryggan svarar E_TIMEOUT och markerar sig
# degraded.
TIMEOUT_MS_KORNING = TIMEOUT_MS_FIL


# ---- domanens egna hjalpare ---------------------------------------------
#
# Ligger har och inte i kodmall.py: de ror bara den har domanen, och en delad
# hjalpare som bara en modul anvander ar skuld i den delade filen.

_EGNA = {
    "_sim": ((), [
        "def _sim():",
        "    # getSimulation() kommer ur bryggans 'from vcScript import *'.",
        "    return getSimulation()",
    ]),
    # Egenskaper som INTE star i formaga.YTOR provas per objekt. En saknad
    # egenskap ger null i svaret och aldrig en gissning (36_versioner.md:
    # okant behandlas som saknat).
    "_valfri_tal": ((), [
        "def _valfri_tal(o, namn):",
        "    # hasattr och inte getattr: getattr star i",
        "    # skrivgrind.OGENOMSKINLIGA och skulle doma en lasande mall som",
        "    # skrivande. Darfor namnges varje egenskap rakt ut av den som",
        "    # anropar, och den har hjalparen far bara vardet.",
        "    if o is None:",
        "        return None",
        "    return float(o)",
    ]),
}
_EGEN_ORDNING = ("_sim", "_valfri_tal")


def _egna(namn):
    """Raderna for hjalparna plus allt de beror av, i fast ordning."""
    behovs = set()
    kvar = list(namn)
    while kvar:
        n = kvar.pop()
        if n in behovs:
            continue
        if n not in _EGNA:
            raise KeyError("okand hjalpare %r i simuleringsmallen" % (n,))
        behovs.add(n)
        kvar.extend(_EGNA[n][0])
    rader = []
    for n in _EGEN_ORDNING:
        if n in behovs:
            rader.extend(_EGNA[n][1])
            rader.append("")
            rader.append("")
    return rader


def _mall(kodmallshjalpare, egna, rader):
    """bygg() med den har domanens egna hjalpare inskjutna forst."""
    return bygg(kodmallshjalpare, _egna(egna) + rader)


# Ytorna formagegrinden faktiskt kan prova. Se modulens docstring.
_YTOR_TILLSTAND = ("sim.SimTime", "sim.IsRunning", "sim.SimSpeed")
_YTOR_KOR = ("sim.run", "sim.IsRunning", "sim.SimTime")
_YTOR_ATERSTALL = ("sim.reset", "sim.SimTime", "sim.IsRunning")
_YTOR_LAGE = ("sim.IsRunning", "sim.SimTime")
_YTOR_STEG = ("app.render", "sim.SimTime")
_YTOR_FART = ("sim.SimSpeed",)


# Radera som varje lasande tillstandsrad delar. Den star pa ETT stalle sa att
# tva verktyg inte kan bora rapportera olika tillstand.
_TILLSTANDSRADER = [
    'lage = {"sim_time": float(sim.SimTime),',
    '        "is_running": bool(sim.IsRunning),',
    '        "sim_speed": float(sim.SimSpeed)}',
]

_RET_TILLSTAND = {
    "sim_time": {"type": "number",
                 "description": "Simuleringsklockan i SEKUNDER. Det ar den enda "
                                "storhet i VC som inte ar millimeter."},
    "is_running": {"type": "boolean",
                   "description": "Om simuleringen kor i 3D-varlden just nu."},
    "sim_speed": {"type": "number",
                  "description": "VC:s SimSpeed: stegstorlek respektive "
                                 "simuleringsfart. Kallan beskriver den som "
                                 "bada, sa vardet tolkas inte har."},
}


def _krav_positiv(namn, varde, verktyg):
    """Schemat provar TYP, inte intervall. Kontrollen ligger dar den biter."""
    if varde <= 0.0:
        raise Argumentfel(verktyg, [
            "%s ar %r; en tid maste vara storre an noll. VC:s egen "
            "standard ar tio DYGN, och den skulle ta ned bryggan pa "
            "E_TIMEOUT i stallet for att svara" % (namn, varde)])


# ==========================================================================
# LASANDE
# ==========================================================================

# ---- sim_state -----------------------------------------------------------

def _kod_sim_state(argument):
    rader = ["sim = _sim()"] + list(_TILLSTANDSRADER) + [
        # De fyra egenskaperna nedan star INTE i formaga.YTOR och kan darfor
        # inte formageprovas. De provas per objekt i stallet, och en saknad
        # egenskap blir null - aldrig ett gissat varde.
        'lage["is_looping"] = bool(sim.IsLooping) if hasattr(sim, "IsLooping") else None',
        'lage["warmup_time"] = _valfri_tal(sim.SimWarmupTime if hasattr(sim, "SimWarmupTime") else None, "SimWarmupTime")',
        'lage["run_time"] = _valfri_tal(sim.SimulationRunTime if hasattr(sim, "SimulationRunTime") else None, "SimulationRunTime")',
        'lage["notering"] = %s' % lit(
            "null i ett falt betyder att den VC som svarade saknar "
            "egenskapen, inte att vardet ar noll (36_versioner.md)."),
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim", "_valfri_tal"], rader)


_lagg(
    "sim_state",
    "Lasar simuleringens tillstand: klocka, om den kor, fart, looping, "
    "uppvarmningstid och inprogrammerad korlangd. Detta ar tidsaxeln varje "
    "matning och varje grind provtar mot - las den FORE och EFTER varje "
    "annat anrop du vill kunna tidsatta.",
    "read",
    params({}),
    returns(dict(_RET_TILLSTAND, **{
        "is_looping": {"type": ["boolean", "null"],
                       "description": "Om VC startar om simuleringen nar den ar "
                                      "klar. null om denna VC saknar egenskapen."},
        "warmup_time": {"type": ["number", "null"],
                        "description": "Uppvarmningstid i sekunder innan "
                                       "statistiken borjar raknas. null om "
                                       "egenskapen saknas."},
        "run_time": {"type": ["number", "null"],
                     "description": "Den simuleringstid VC stannar vid. null om "
                                    "egenskapen saknas."},
        "notering": {"type": "string",
                     "description": "Vad ett null-falt betyder."}}),
            ["sim_time", "is_running", "sim_speed", "is_looping",
             "warmup_time", "run_time", "notering"]),
    _YTOR_TILLSTAND,
    _kod_sim_state,
)


# ==========================================================================
# SKRIVANDE
# ==========================================================================

# ---- sim_run -------------------------------------------------------------

def _kod_sim_run(argument):
    _krav_positiv("seconds", argument["seconds"], "sim_run")
    rader = ["sim = _sim()", "fore = float(sim.SimTime)",
             "sim.run(%s)" % tal(argument["seconds"]),
             "efter = float(sim.SimTime)"] + list(_TILLSTANDSRADER) + [
        'lage["started_at"] = fore',
        'lage["advanced"] = efter - fore',
        'lage["requested"] = %s' % tal(argument["seconds"]),
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_run",
    "Kor simuleringen framat ett angivet antal SEKUNDER simuleringstid. "
    "Antalet ar obligatoriskt: VC:s egen standard ar tio dygn, och den skulle "
    "ta ned bryggan pa timeout i stallet for att svara. Svaret bar hur langt "
    "klockan faktiskt gick, vilket inte behover vara det du bad om.",
    "write",
    params({"seconds": {"type": "number",
                        "description": "Simuleringstid i sekunder att kora. "
                                       "Maste vara storre an noll."}},
           ["seconds"]),
    returns(dict(_RET_TILLSTAND, **{
        "started_at": {"type": "number", "description": "Klockan fore korningen."},
        "advanced": {"type": "number",
                     "description": "Hur manga sekunder klockan faktiskt gick. "
                                    "Skiljer den sig fran requested stannade "
                                    "simuleringen i fortid."},
        "requested": {"type": "number", "description": "Antalet sekunder som begardes."}}),
            ["sim_time", "is_running", "sim_speed", "started_at", "advanced",
             "requested"]),
    _YTOR_KOR,
    _kod_sim_run,
    timeout_ms=TIMEOUT_MS_KORNING,
)


# ---- sim_continue --------------------------------------------------------

def _kod_sim_continue(argument):
    _krav_positiv("seconds", argument["seconds"], "sim_continue")
    rader = ["sim = _sim()", "fore = float(sim.SimTime)",
             "sim.continueRun(%s)" % tal(argument["seconds"]),
             "efter = float(sim.SimTime)"] + list(_TILLSTANDSRADER) + [
        'lage["started_at"] = fore',
        'lage["advanced"] = efter - fore',
        'lage["requested"] = %s' % tal(argument["seconds"]),
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_continue",
    "Fortsatter en stoppad simulering ett angivet antal sekunder utan att "
    "nollstalla klockan. Skillnaden mot sim_run ar att klockan och scenens "
    "tillstand behalls; sim_run efter en halt startar om fran samma punkt men "
    "raknas av VC som en ny korning.",
    "write",
    params({"seconds": {"type": "number",
                        "description": "Ytterligare simuleringstid i sekunder. "
                                       "Maste vara storre an noll."}},
           ["seconds"]),
    returns(dict(_RET_TILLSTAND, **{
        "started_at": {"type": "number", "description": "Klockan fore korningen."},
        "advanced": {"type": "number", "description": "Hur manga sekunder klockan gick."},
        "requested": {"type": "number", "description": "Antalet sekunder som begardes."}}),
            ["sim_time", "is_running", "sim_speed", "started_at", "advanced",
             "requested"]),
    _YTOR_LAGE,
    _kod_sim_continue,
    timeout_ms=TIMEOUT_MS_KORNING,
)


# ---- sim_halt ------------------------------------------------------------

def _kod_sim_halt(argument):
    rader = ["sim = _sim()", "fore = bool(sim.IsRunning)",
             "sim.halt()"] + list(_TILLSTANDSRADER) + [
        'lage["was_running"] = fore',
        'lage["halted"] = fore and not lage["is_running"]',
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_halt",
    "Stoppar simuleringen omedelbart. Klockan star kvar dar den ar - anvand "
    "sim_reset for att nolla den. Svaret sager om simuleringen faktiskt gick "
    "innan, sa ett stopp av nagot som redan stod syns som halted=false.",
    "write",
    params({}),
    returns(dict(_RET_TILLSTAND, **{
        "was_running": {"type": "boolean", "description": "Om simuleringen gick fore anropet."},
        "halted": {"type": "boolean",
                   "description": "True bara om anropet faktiskt stoppade nagot "
                                  "som gick. False betyder att den redan stod."}}),
            ["sim_time", "is_running", "sim_speed", "was_running", "halted"]),
    _YTOR_LAGE,
    _kod_sim_halt,
)


# ---- sim_reset -----------------------------------------------------------

def _kod_sim_reset(argument):
    rader = ["sim = _sim()", "fore = float(sim.SimTime)",
             "sim.reset()"] + list(_TILLSTANDSRADER) + [
        'lage["time_before"] = fore',
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_reset",
    "Aterstaller simuleringen och de statiska komponenterna till utgangslaget "
    "och nollar simuleringsklockan. Detta ar det enda satt en bank kan koras "
    "om under samma forutsattningar - las 83_scenarier.md innan du hoppar "
    "over det mellan tva korningar.",
    "write",
    params({}),
    returns(dict(_RET_TILLSTAND, **{
        "time_before": {"type": "number",
                        "description": "Klockan fore nollstallningen, sa att "
                                       "korningens langd inte gar forlorad."}}),
            ["sim_time", "is_running", "sim_speed", "time_before"]),
    _YTOR_ATERSTALL,
    _kod_sim_reset,
)


# ---- sim_step ------------------------------------------------------------

def _kod_sim_step(argument):
    rader = ["sim = _sim()", "fore = float(sim.SimTime)", "sim.update()"]
    if argument["render"]:
        # app.render() ritar om 3D-vyn. Den behovs nar nasta steg ar en
        # bildfangst; den kostar tid nar det inte ar det, darfor ett val.
        rader.append("_app().render()")
    rader += list(_TILLSTANDSRADER) + [
        'lage["time_before"] = fore',
        'lage["rendered"] = %s' % ("True" if argument["render"] else "False"),
        'lage["notering"] = %s' % lit(
            "M-11 och M-36: VC utvarderar inte geometri och varldsmatriser "
            "om inom samma korning. Utan detta steg svarar en efterfoljande "
            "matning konsekvent och trovardigt med ett gammalt tal."),
        "_svara(lage)",
    ]
    return _mall(["_app", "_svara"], ["_sim"], rader)


_lagg(
    "sim_step",
    "Uppdaterar simuleringen och 3D-varlden sa att scenen speglar "
    "komponenternas nuvarande tillstand, utan att kora tiden framat. MATT "
    "(M-11, M-36): utan detta svarar bade varldsmatriser och avstandsmatningar "
    "med ett GAMMALT tal, konsekvent och trovardigt. Kor detta efter varje "
    "flytt och fore varje matning.",
    "write",
    params({"render": {"type": "boolean", "default": False,
                       "description": "Rita ocksa om 3D-vyn. Behovs fore en "
                                      "bildfangst, kostar tid annars."}}),
    returns(dict(_RET_TILLSTAND, **{
        "time_before": {"type": "number", "description": "Klockan fore uppdateringen."},
        "rendered": {"type": "boolean", "description": "Om 3D-vyn ocksa ritades om."},
        "notering": {"type": "string", "description": "Varfor steget behovs."}}),
            ["sim_time", "is_running", "sim_speed", "time_before", "rendered",
             "notering"]),
    _YTOR_STEG,
    _kod_sim_step,
)


# ---- sim_speed -----------------------------------------------------------

def _kod_sim_speed(argument):
    if "speed" not in argument and "loop" not in argument:
        raise Argumentfel("sim_speed", ["ange speed, loop eller bada"])
    if "speed" in argument and argument["speed"] <= 0.0:
        raise Argumentfel("sim_speed",
                          ["speed ar %r; SimSpeed maste vara storre an noll"
                           % (argument["speed"],)])
    rader = ["sim = _sim()"]
    if "speed" in argument:
        rader.append("sim.SimSpeed = %s" % tal(argument["speed"]))
    if "loop" in argument:
        rader += [
            # Fail-closed: verktyget far inte pasta att det satt looping i en
            # VC som inte har egenskapen (I3).
            'if not hasattr(sim, "IsLooping"):',
            '    raise ValueError("denna VC har ingen IsLooping att satta")',
            "sim.IsLooping = %s" % ("True" if argument["loop"] else "False"),
        ]
    rader += list(_TILLSTANDSRADER) + [
        'lage["is_looping"] = bool(sim.IsLooping) if hasattr(sim, "IsLooping") else None',
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_speed",
    "Satter simuleringens fart och om den ska loopa. Svaret bar de varden VC "
    "faktiskt har efterat, inte de du bad om - VC klipper egna granser tyst. "
    "Ber du om loop i en VC som saknar egenskapen kastar verktyget i stallet "
    "for att pasta att det gick.",
    "write",
    params({"speed": {"type": "number",
                      "description": "Ny SimSpeed. Maste vara storre an noll."},
            "loop": {"type": "boolean",
                     "description": "Om VC ska starta om simuleringen nar den "
                                    "ar klar."}},
           [], minst_en_av=[("speed", "loop")]),
    returns(dict(_RET_TILLSTAND, **{
        "is_looping": {"type": ["boolean", "null"],
                       "description": "Loopinstallningen efterat, null om "
                                      "egenskapen saknas i denna VC."}}),
            ["sim_time", "is_running", "sim_speed", "is_looping"]),
    _YTOR_FART,
    _kod_sim_speed,
)


# ---- sim_warmup ----------------------------------------------------------

def _kod_sim_warmup(argument):
    for namn in ("warmup_seconds", "run_time_seconds"):
        if namn in argument and argument[namn] < 0.0:
            raise Argumentfel("sim_warmup",
                              ["%s ar %r; en tid kan inte vara negativ"
                               % (namn, argument[namn])])
    rader = ["sim = _sim()", "satta = []", "vagrade = []"]
    if "warmup_seconds" in argument:
        v = tal(argument["warmup_seconds"])
        rader += [
            'if not hasattr(sim, "SimWarmupTime"):',
            '    raise ValueError("denna VC har ingen SimWarmupTime")',
            "sim.SimWarmupTime = %s" % v,
            # Lasningen tillbaka ar hela poangen: kallan sager att den ena av
            # de tva egenskaperna bara far skrivas i OnRun-handelsen.
            "if abs(float(sim.SimWarmupTime) - %s) < 1e-9:" % v,
            '    satta.append("warmup_seconds")',
            "else:",
            '    vagrade.append("warmup_seconds")',
        ]
    if "run_time_seconds" in argument:
        v = tal(argument["run_time_seconds"])
        rader += [
            'if not hasattr(sim, "SimulationRunTime"):',
            '    raise ValueError("denna VC har ingen SimulationRunTime")',
            "sim.SimulationRunTime = %s" % v,
            "if abs(float(sim.SimulationRunTime) - %s) < 1e-9:" % v,
            '    satta.append("run_time_seconds")',
            "else:",
            '    vagrade.append("run_time_seconds")',
        ]
    rader += [
        "if vagrade:",
        '    raise ValueError("VC behallde sitt gamla varde for " + ",".join(vagrade)'
        ' + "; kallan sager att SimulationRunTime bara far andras i OnRun")',
        'lage = {"warmup_time": float(sim.SimWarmupTime) if hasattr(sim, "SimWarmupTime") else None,',
        '        "run_time": float(sim.SimulationRunTime) if hasattr(sim, "SimulationRunTime") else None,',
        '        "applied": satta,',
        '        "sim_time": float(sim.SimTime)}',
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_warmup",
    "Satter uppvarmningstid och inprogrammerad korlangd i sekunder. "
    "Uppvarmningen ar den tid statistiken INTE raknar, sa att en flaskhalsdom "
    "inte mater uppstarten. VARNING ur kallan: SimulationRunTime far enligt "
    "VC bara andras i OnRun-handelsen; verktyget laser tillbaka och KASTAR om "
    "vardet inte tog, i stallet for att pasta att det gick.",
    "write",
    params({"warmup_seconds": {"type": "number",
                               "description": "Uppvarmningstid i sekunder. Noll "
                                              "eller storre."},
            "run_time_seconds": {"type": "number",
                                 "description": "Simuleringstid dar VC ska "
                                                "stanna. Noll eller storre."}},
           [], minst_en_av=[("warmup_seconds", "run_time_seconds")]),
    returns({"warmup_time": {"type": ["number", "null"],
                             "description": "Uppvarmningstiden VC har efterat."},
             "run_time": {"type": ["number", "null"],
                          "description": "Korlangden VC har efterat."},
             "applied": {"type": "array",
                         "description": "Vilka av de begarda faltena som "
                                        "verkligen lastes tillbaka med ratt varde.",
                         "items": {"type": "string",
                                   "description": "Argumentnamnet som tog."}},
             "sim_time": _RET_TILLSTAND["sim_time"]},
            ["warmup_time", "run_time", "applied", "sim_time"]),
    _YTOR_LAGE,
    _kod_sim_warmup,
)


# ---- set_fast_scheduling -------------------------------------------------

def _kod_set_fast_scheduling(argument):
    rader = [
        "sim = _sim()",
        # Snabbschemalaggning byter ut transportornas tidsmodell. Att andra
        # den medan simuleringen gar ger en scen dar forsta och andra halvan
        # av korningen inte ar samma modell.
        "if bool(sim.IsRunning):",
        '    raise ValueError("simuleringen kor; stoppa den med sim_halt '
        'innan schemalaggningen byts, annars mater halva korningen en annan '
        'tidsmodell an den andra")',
        "sim.setFastScheduling(%s)" % ("True" if argument["enabled"] else "False"),
        '_svara({"requested": %s,' % ("True" if argument["enabled"] else "False"),
        '        "verified": False,',
        '        "sim_time": float(sim.SimTime),',
        '        "notering": %s})' % lit(
            "VC exponerar ingen egenskap som speglar setFastScheduling, sa "
            "sattningen gar INTE att lasa tillbaka. verified=false betyder "
            "just det och inte att den misslyckades (41_ogat_kontrakt.md)."),
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "set_fast_scheduling",
    "Slar pa eller av snabbschemalaggning for alla transportorer som stodjer "
    "den. Anvands nar en lang produktionskorning ska ga fort. VIKTIGT: VC har "
    "ingen egenskap som speglar installningen, sa verktyget kan INTE bekrafta "
    "att den tog - svaret sager verified=false och det ar arligt, inte ett fel.",
    "write",
    params({"enabled": {"type": "boolean",
                        "description": "True slar pa snabbschemalaggning."}},
           ["enabled"]),
    returns({"requested": {"type": "boolean", "description": "Vardet som begardes."},
             "verified": {"type": "boolean",
                          "description": "Alltid false: VC har ingen yta att "
                                         "lasa tillbaka installningen pa."},
             "sim_time": _RET_TILLSTAND["sim_time"],
             "notering": {"type": "string", "description": "Varfor verified ar false."}},
            ["requested", "verified", "sim_time", "notering"]),
    _YTOR_LAGE,
    _kod_set_fast_scheduling,
)


# ---- sim_initial_state ---------------------------------------------------

def _kod_sim_initial_state(argument):
    handling = argument["action"]
    rader = ["sim = _sim()", "fore = float(sim.SimTime)"]
    if handling == "save":
        rader.append("sim.setInitialState()")
    else:
        rader.append("sim.restoreInitialState()")
    rader += list(_TILLSTANDSRADER) + [
        'lage["action"] = %s' % lit(handling),
        'lage["time_before"] = fore',
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_initial_state",
    "Sparar scenens nuvarande tillstand som utgangslage (save) eller "
    "aterstaller till det tidigare sparade (restore). Detta ar det som gor "
    "att tva korningar av samma bankuppgift blir jamforbara: spara EN gang "
    "efter att layouten ar byggd, aterstall mellan varje forsok.",
    "write",
    params({"action": {"type": "string", "enum": ["save", "restore"],
                       "description": "save skriver over det sparade "
                                      "utgangslaget; restore laser tillbaka det."}},
           ["action"]),
    returns(dict(_RET_TILLSTAND, **{
        "action": {"type": "string", "description": "Handlingen som utfordes."},
        "time_before": {"type": "number", "description": "Klockan fore anropet."}}),
            ["sim_time", "is_running", "sim_speed", "action", "time_before"]),
    _YTOR_LAGE,
    _kod_sim_initial_state,
)


# ---- sim_autohalt --------------------------------------------------------

def _kod_sim_autohalt(argument):
    rader = ["sim = _sim()", "fore = bool(sim.IsRunning)",
             "stoppade = bool(sim.autoHalt())"] + list(_TILLSTANDSRADER) + [
        'lage["was_running"] = fore',
        'lage["halted"] = stoppade',
        'lage["notering"] = %s' % lit(
            "autoHalt stoppar bara om INGEN komponent kor ett skript som "
            "genererar simuleringshandelser. halted=false betyder alltsa att "
            "scenen fortfarande har nagot att gora, inte att anropet gick fel."),
        "_svara(lage)",
    ]
    return _mall(["_svara"], ["_sim"], rader)


_lagg(
    "sim_autohalt",
    "Stoppar simuleringen OM ingen komponent langre kor ett skript som "
    "genererar handelser, och sager om den gjorde det. Detta ar satt att "
    "svara pa 'ar cellen klar' utan att gissa en korlangd.",
    "write",
    params({}),
    returns(dict(_RET_TILLSTAND, **{
        "was_running": {"type": "boolean", "description": "Om simuleringen gick fore anropet."},
        "halted": {"type": "boolean",
                   "description": "True om VC stoppade simuleringen for att "
                                  "scenen var klar."},
        "notering": {"type": "string", "description": "Vad halted=false betyder."}}),
            ["sim_time", "is_running", "sim_speed", "was_running", "halted",
             "notering"]),
    _YTOR_LAGE,
    _kod_sim_autohalt,
)
