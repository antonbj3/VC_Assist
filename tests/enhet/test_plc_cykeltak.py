# -*- coding: utf-8 -*-
"""L1: cykeltidstaket och runtimeloggen (M-178, kö A punkt A11).

Två fynd ur M-178 som båda är permanenta här, för att de annars glider tillbaka:

1. **`OpenPlcV4.logg()` läste fel nyckel och lämnade alltid en tom sträng.**
   `/api/runtime-logs` svarar `{"runtime-logs": [...]}`; metoden letade efter
   `{"logs": [...]}`. Två av projektets skarpaste fynd stod i den loggen och
   lästes aldrig: `[task MAIN] terminated by signal 8` vid nolldivision
   (M-169) och `[task MAIN] scan overrun #N: body exceeds its 20 ms period`
   när kroppen inte hinner (M-178). Felmeddelandet i `starta_och_vanta`
   ("Senaste loggrader:") har alltså alltid varit tomt.

2. **Vår ST-tolk har ingen exekveringstid.** `Tolk.scan()` gör
   `tid_ms += scan_ms` och har ingen annan tidskälla. En kropp som tar tio
   millisekunder och en som tar en mikrosekund ger exakt samma spår, alltså
   exakt samma dom. Det är inte en bugg — det är tolkens gräns — men den ska
   stå skriven och gå att fälla om någon påstår motsatsen.

Ingen rigg: provet matar klienten med runtimens uppmätta svarsform i stället
för att ringa den. Svarsformen är avskriven ur en riktig körning mot
OpenPLC v4.2.1 den 2026-09-05 (`docs/matningar/radata/m178_ut.txt`).
"""
from __future__ import annotations

import os
import sys
import time

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc.plc.openplc import OpenPlcV4      # noqa: E402
from vc_assist_svc.st import tolk as TK              # noqa: E402


# Ordagrant ur en körning mot OpenPLC Runtime v4.2.1 (M-178). Nyckeln heter
# "runtime-logs", inte "logs", och posterna är dictar med level/message.
SVAR_UR_RIKTIG_RUNTIME = {
    "runtime-logs": [
        {"id": 24990, "level": "INFO",
         "message": "PLC State: RUNNING",
         "timestamp": "2026-09-05T19:00:29+0000"},
        {"id": 24991, "level": "WARNING",
         "message": "[task MAIN] scan overrun #1: body exceeds its 20 ms "
                    "period — running at reduced rate, other tasks unaffected",
         "timestamp": "2026-09-05T19:00:29+0000"},
        {"id": 24992, "level": "ERROR",
         "message": "[task MAIN] terminated by signal 8 — other tasks keep "
                    "running",
         "timestamp": "2026-09-05T19:00:43+0000"},
    ]
}


class _Attrapp(OpenPlcV4):
    """Klienten med transporten utbytt. Allt annat är den riktiga koden."""

    def __init__(self, svar):
        OpenPlcV4.__init__(self, "https://attrapp", "u", "p",
                           tillat_osignerat=True)
        self._svar = svar
        self.senaste_param = None

    def _hamta(self, stig, parametrar=None, kraver_token=True):
        self.senaste_param = parametrar
        return self._svar


# ===================================================== 1. runtimeloggen

def test_trasig_fixtur_runtimeloggens_egen_svarsform_lases():
    """FIXTUREN: exakt den form runtimen svarar med måste ge text.

    Provet var RÖTT innan `logg()` lagades — metoden läste `data["logs"]`,
    som inte finns i svaret, och lämnade "".
    """
    klient = _Attrapp(SVAR_UR_RIKTIG_RUNTIME)
    text = klient.logg(rader=40)
    assert text, ("logg() lämnade en tom sträng på runtimens egen svarsform; "
                  "då är varje felmeddelande som citerar loggen tomt")
    assert "scan overrun #1" in text
    assert "terminated by signal 8" in text
    assert text.count("\n") == 2


def test_loggen_bar_nivan_och_ar_lasbar_for_en_manniska():
    """En logg som skrivs som JSON åt en människa är en logg ingen läser."""
    text = _Attrapp(SVAR_UR_RIKTIG_RUNTIME).logg()
    assert "[WARNING]" in text and "[ERROR]" in text
    assert '"message"' not in text, "posten skrevs som JSON i stället för text"


def test_loggen_klipps_till_begart_antal_rader():
    text = _Attrapp(SVAR_UR_RIKTIG_RUNTIME).logg(rader=1)
    assert text.count("\n") == 0
    assert "terminated by signal 8" in text, "sista raden ska vara den nyaste"


def test_nivafiltret_skickas_vidare():
    klient = _Attrapp(SVAR_UR_RIKTIG_RUNTIME)
    klient.logg(niva="WARNING")
    assert klient.senaste_param == {"level": "WARNING"}


@pytest.mark.parametrize("svar", [
    {"logs": [{"level": "INFO", "message": "gammal form"}]},
    [{"level": "INFO", "message": "ren lista"}],
    {"runtime_logs": [{"level": "INFO", "message": "understreck"}]},
])
def test_alla_tre_svarsformerna_lases(svar):
    """Formen har hetat olika saker. Ingen av dem får ge tomt."""
    assert _Attrapp(svar).logg().strip()


def test_okand_form_ger_tomt_men_kraschar_inte():
    """En form vi inte känner igen ska ge tomt, inte ett undantag: loggen är
    en upplysning i ett felmeddelande, och den får aldrig dölja felet den
    skulle förklara."""
    assert _Attrapp({"nagot_annat": 17}).logg() == ""


# =============================================== 2. tolken har ingen tid

TUNG = """PROGRAM Tung
VAR
    i   : DINT;
    j   : DINT;
    acc : REAL := 0.0;
END_VAR
acc := 0.0;
FOR i := 1 TO %d DO
    FOR j := 1 TO %d DO
        acc := acc + 1.0;
    END_FOR;
END_FOR;
UT_ACC := acc;
END_PROGRAM
"""


def _ett_scan(yttre, inre):
    t = TK.Tolk(TUNG % (yttre, inre), {"UT_ACC": "real"}, {"UT_ACC": "out"},
                TK.SCAN_MS)
    t0 = time.perf_counter()
    t.scan()
    return (time.perf_counter() - t0) * 1000.0, t.tid_ms, t.las("UT_ACC")


def test_tolkens_klocka_ar_oberoende_av_arbetet():
    """M-178: modellklockan flyttas med scanperioden, oavsett arbetsmängd.

    Det är tolkens gräns och den bär hela punkt A11:s svar för vår egen motor:
    en kod som är för långsam för sitt tak går inte att skilja från en som är
    snabb, för tolken har ingen exekveringstid att jämföra taket med.
    """
    latt_vagg, latt_klocka, latt_acc = _ett_scan(1, 1)
    tung_vagg, tung_klocka, tung_acc = _ett_scan(120, 120)

    assert latt_acc == 1.0 and tung_acc == 14400.0, "arbetet utfördes inte"
    assert tung_vagg > latt_vagg * 5, (
        "väggtiden växte inte med arbetet (%.3f ms mot %.3f ms); då mäter "
        "provet inte det det påstår" % (tung_vagg, latt_vagg))
    assert latt_klocka == TK.SCAN_MS
    assert tung_klocka == TK.SCAN_MS, (
        "modellklockan rörde sig av arbetet (%.3f ms). Har tolken fått en "
        "exekveringstid ska M-178 mätas om och det här provet skrivas om."
        % tung_klocka)


def test_ingen_grind_i_kedjan_mater_exekveringstid():
    """M-178: taket finns i PLC-uppgiften, men ingen av våra grindar läser det.

    Textsökning, alltså en UNDRE gräns — men noll är noll. Provet är ett tak
    som bara får krympa: bygger någon en cykeltidsgrind ska raden nedan tas
    bort, inte höjas.
    """
    import re
    ord_ = re.compile(r"cycle_time|cykeltid|exekveringstid|scan_time|overrun|"
                      r"budget_ms|wcet", re.I)
    kedjan = ("svc/vc_assist_svc/st/validator.py",
              "svc/vc_assist_svc/plc/deklarationsgrind.py",
              "svc/vc_assist_svc/plc/industrigrind.py",
              "svc/vc_assist_svc/plc/stationsgrind.py",
              "svc/vc_assist_svc/plc/forhandsregler.py")
    traffar = {}
    for rel in kedjan:
        vag = os.path.join(_ROT, rel)
        if not os.path.exists(vag):
            continue
        with open(vag, "r", encoding="utf-8") as f:
            n = sum(1 for rad in f if ord_.search(rad))
        if n:
            traffar[rel] = n
    assert traffar == {}, (
        "en grind nämner numera exekveringstid (%s). Om den MÄTER den är det "
        "goda nyheter — ta bort det här provet och skriv en mätning som säger "
        "vad den fäller på." % traffar)
