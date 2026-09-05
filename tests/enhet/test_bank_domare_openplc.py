# -*- coding: utf-8 -*-
"""L1: OpenPLC-domaren, utan levande runtime.

`bank/domare_openplc.py` dömer bankens spårfacit genom OpenPLC Runtime v4 i
stället för genom vår egen ST-tolk — `85_bankkontraktet.md` §2 förbjuder ett
facit som kommer ur koden som döms, och `domare.py` är just den tautologin.

Den skarpa körningen kräver docker, STruC++ och en PLC i realtid och ligger i
`tests/protocol/kor_A2_domare_openplc.py`. **Det här provet får inte kräva
något av det.** En grind som bara går att köra på en maskin körs sällan, och
en grind som körs sällan mäter ingenting. REST-lagret, bygget och körningen
mockas därför, och det som provas är domarens egen mekanik:

  * kartläggningen: vilka signaler som går att mappa och vilka som fäller.
  * programbygget: kartans deklarationer först, lösningens omdeklaration fälld.
  * **gränsen mellan en DOM och ett DOMSFEL** — punkt A2:s hela poäng. Ett
    körningsfel (runtime nere, bygget hänger, kanalen faller) får aldrig bli
    ett underkännande, och en lösning OpenPLC vägrar kompilera får aldrig bli
    ett domsfel.
  * spårdomen: samma bristkoder som `domare.py` på samma spår.

TRASIG FIXTUR, och den är mätt live först (M-146 §2): en dubblerad
CASE-etikett i P-05:s referens. Vår ST-tolk säger GODKÄND, STruC++:s frontend
säger OK, och OpenPLC:s g++ säger `duplicate case value`. Här nedan spelas
runtimens **egna ord ur den körningen** upp av en attrapp, så att provet fäller
på samma sak på en maskin utan docker.

beskriver: bank/domare_openplc.py
"""
from __future__ import annotations

import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import domare as D                          # noqa: E402
import domare_openplc as DO                 # noqa: E402
from vc_assist_svc.plc import openplc as PLC  # noqa: E402
from vc_assist_svc.plc import paket as P      # noqa: E402

UPPGIFTER = os.path.join(_ROT, "bank", "uppgifter")

# OpenPLC:s EGNA ord, kopierade ur körningen 2026-09-05 mot
# ghcr.io/autonomy-logic/openplc-runtime v4.2.1 med P-05:s referens plus en
# dubblerad CASE-etikett. Attrappen spelar upp dem; texten är inte skriven
# här, den är avläst.
LOGG_DUBBLERAD_CASE = (
    "[INFO] Compiling core/generated/generated.cpp...\n"
    "[ERROR] core/generated/generated.cpp:190:13: error: duplicate case value\n"
    "[ERROR] make: *** [scripts/Makefile.strucpp:178: build/generated.o] "
    "Error 1\n"
    "[INFO] Build finished with errors\n")


def las(task_id):
    with open(os.path.join(UPPGIFTER, "%s.json" % task_id), "r",
              encoding="utf-8") as f:
        return json.load(f)


def dubblera_case(st_text):
    """Samma fixtur som protokollkörningen bygger: hela första CASE-grenen
    kopieras in före den sista etiketten. Kopian ligger EFTER originalet, så
    vår tolk når den aldrig — bara kompilatorn ser den."""
    rader = st_text.splitlines()
    etiketter = [i for i, rad in enumerate(rader)
                 if rad.strip().endswith(":")
                 and rad.strip()[:-1].strip().isdigit()]
    assert len(etiketter) >= 2, "uppgiften bär inget CASE att dubblera"
    block = rader[etiketter[0]:etiketter[1]]
    return "\n".join(rader[:etiketter[-1]] + block
                     + rader[etiketter[-1]:]) + "\n"


# ============================================================================
# ATTRAPPER — REST-lagret och körningen, aldrig domarmekaniken
# ============================================================================

class AttrappKompilering(object):
    def __init__(self, status, exit_kod=0, logg=""):
        self.status = status
        self.exit_kod = exit_kod
        self.logg = logg

    @property
    def klar(self):
        return self.status == PLC.KLAR

    @property
    def pagar(self):
        return self.status in PLC.KOMPILERAR


class AttrappKlient(object):
    """En OpenPlcV4 som svarar det provet ber den svara.

    Den kan bara det domaren faktiskt anropar. Att den INTE kan mer är med
    flit: en attrapp som svarar på allt döljer att domaren anropade något
    annat än den skulle.
    """

    def __init__(self, kompilering=None, statusfoljd=None, startsvar=None,
                 svarar=True, logg="", kastar=None):
        self.kompilering = kompilering or AttrappKompilering(PLC.KLAR)
        self.statusfoljd = list(statusfoljd or [PLC.KOR])
        self.startsvar = list(startsvar or ["OK"])
        self._svarar = svarar
        self._logg = logg
        self.kastar = kastar or {}
        self.anrop = []

    def _kanske_kasta(self, vad):
        self.anrop.append(vad)
        if vad in self.kastar:
            raise PLC.OpenPlcFel(self.kastar[vad])

    def svarar(self):
        self._kanske_kasta("svarar")
        return self._svarar

    def skapa_forsta_anvandare(self):
        self._kanske_kasta("skapa_forsta_anvandare")
        return False

    def ladda_upp(self, zipvag):
        self._kanske_kasta("ladda_upp")
        return {}

    def kompileringsstatus(self):
        self._kanske_kasta("kompileringsstatus")
        return self.kompilering

    def starta(self):
        self._kanske_kasta("starta")
        return self.startsvar.pop(0) if len(self.startsvar) > 1 \
            else self.startsvar[0]

    def stoppa(self):
        self._kanske_kasta("stoppa")
        return "OK"

    def status(self):
        self._kanske_kasta("status")
        return self.statusfoljd.pop(0) if len(self.statusfoljd) > 1 \
            else self.statusfoljd[0]

    def logg(self, rader=40, niva=None):
        return self._logg


def rigg_utan_kontroll(monkeypatch):
    """En Rigg vars kontroll av verktygskedjan är avstängd.

    Provet ska gå på en ren maskin. Att STruC++ saknas där är rätt, och just
    därför kontrolleras riggen i sitt eget prov längre ner i stället.
    """
    r = DO.Rigg(bas="https://attrapp", endpoint="opc.tcp://attrapp")
    monkeypatch.setattr(r, "kontrollera", lambda: None)
    return r


# ============================================================================
# TRASIG FIXTUR (mätt live först, se M-146 §2)
# ============================================================================

def test_trasig_fixtur_dubblerad_case_blir_rod_inte_gron_och_inte_domsfel(
        monkeypatch):
    """En lösning vår tolk godkänner och OpenPLC vägrar kompilera blir RÖD.

    Alla tre villkoren prövas, för att bara ett av dem är lätt att uppfylla
    av misstag:
      * vår egen tolk säger GODKÄND om texten (annars mäter fixturen inget
        nytt),
      * OpenPLC-domaren säger UNDERKÄND på `openplc:kompilerar_inte`,
      * och den gör det som en DOM, inte som ett Domsfel — ett körningsfel
        maskerat som ett underkännande är precis det punkt A2 förbjuder.
    """
    post = las("P-05")
    trasig = dubblera_case(post["facit_spar"]["referens"])

    egen = D.dom(post, trasig)
    assert egen.godkand, ("fixturen mäter fel storhet: vår egen tolk fäller "
                          "den redan på %s" % egen.koder)

    klient = AttrappKlient(kompilering=AttrappKompilering(
        PLC.FALLEN, 1, LOGG_DUBBLERAD_CASE))
    monkeypatch.setattr(DO, "_bygg", lambda *a, **k: "/attrapp/projekt.zip")
    monkeypatch.setattr(DO, "_kor_en_sekvens", _kor_aldrig)

    d = DO.dom(post, trasig, rigg=rigg_utan_kontroll(monkeypatch),
               klient=klient)
    assert not d.godkand
    assert d.koder == ["openplc:kompilerar_inte"]
    # Kompilatorns egna ord, inte vår sammanfattning (I1).
    assert "duplicate case value" in d.brister[0].text
    # Och sidan kördes aldrig.
    assert "kompileringsstatus" in klient.anrop
    assert "starta" not in klient.anrop


def _kor_aldrig(*a, **k):
    raise AssertionError("sekvensen kördes trots att bygget föll")


# ============================================================================
# KÖRNINGSFEL BLIR DOMSFEL, ALDRIG EN DOM
# ============================================================================

def _dom_med_attrapp(monkeypatch, post, st_text, klient, kor=None):
    monkeypatch.setattr(DO, "_bygg", lambda *a, **k: "/attrapp/projekt.zip")
    monkeypatch.setattr(DO, "_kor_en_sekvens", kor or _kor_aldrig)
    return DO.dom(post, st_text, rigg=rigg_utan_kontroll(monkeypatch),
                  klient=klient)


@pytest.mark.parametrize("klient,bit", [
    (AttrappKlient(svarar=False), "svarar inte"),
    (AttrappKlient(kastar={"svarar": "nådde inte https://attrapp"}),
     "nådde inte OpenPLC"),
    (AttrappKlient(kastar={"ladda_upp": "Connection reset"}),
     "uppladdningen"),
    (AttrappKlient(kastar={"kompileringsstatus": "Connection reset"}),
     "slutade svara under kompileringen"),
])
def test_runtime_som_inte_svarar_ger_domsfel_aldrig_en_dom(monkeypatch, klient,
                                                           bit):
    """Fyra sätt riggen kan svika. Inget av dem får bli ett underkännande."""
    post = las("P-05")
    with pytest.raises(D.Domsfel) as fel:
        _dom_med_attrapp(monkeypatch, post, post["facit_spar"]["referens"],
                         klient)
    assert bit in str(fel.value)


def test_kompileringen_som_hanger_ger_domsfel_snabbt(monkeypatch):
    """Ett bygge som står kvar i COMPILING är riggens fel, inte kodens."""
    post = las("P-05")
    klient = AttrappKlient(kompilering=AttrappKompilering("COMPILING"))
    monkeypatch.setattr(DO, "_bygg", lambda *a, **k: "/attrapp/projekt.zip")
    with pytest.raises(D.Domsfel) as fel:
        DO._ladda(klient, "/attrapp/projekt.zip", tidsgrans=0.05, paus=0.01)
    assert "hängde" in str(fel.value)


def test_kanalfel_mitt_i_en_sekvens_ger_domsfel_aldrig_en_dom(monkeypatch):
    """En kanal som faller betyder att sidan inte kördes.

    Utan det här blir en trasig OPC UA-väg en lösning som "inte reagerar" —
    ett körningsfel som ser ut som en dom.
    """
    post = las("P-05")

    def faller(*a, **k):
        raise D.Domsfel("sekvensen s1: kanalfel: EMG_OK skrevs True men "
                        "lästes False; sidan kördes inte")

    with pytest.raises(D.Domsfel) as fel:
        _dom_med_attrapp(monkeypatch, post, post["facit_spar"]["referens"],
                         AttrappKlient(), kor=faller)
    assert "kanalfel" in str(fel.value)


def test_riggen_utan_strucpp_ger_domsfel_inte_en_dom(tmp_path):
    """En verktygskedja som saknas är ett domsfel med en åtgärd i klartext."""
    r = DO.Rigg(strucpp_paket=str(tmp_path / "finns-inte"),
                runtime_include=str(tmp_path))
    with pytest.raises(D.Domsfel) as fel:
        r.kontrollera()
    assert "STruC++" in str(fel.value)


def test_kompilatorfel_ar_en_dom_men_byggfel_ar_ett_domsfel(monkeypatch,
                                                            tmp_path):
    """Den bärande skillnaden, prövad på `paket`:s två undantag.

    `Kompilatorfel` = kompilatorn kördes och sa nej om koden -> en Brist.
    `Byggfel` = kompilatorn gick inte att köra -> ett Domsfel. Slås de ihop
    blir en trasig rigg en tyst underkänd lösning.
    """
    post = las("P-05")
    karta = DO._karta_for_post(post)
    rigg = DO.Rigg(bas="https://attrapp", endpoint="opc.tcp://attrapp")
    monkeypatch.setattr(rigg, "kontrollera", lambda: None)

    def kompilatorn_sa_nej(*a, **k):
        raise P.Kompilatorfel("STruC++ föll (kod 1):\nsyntax error")

    monkeypatch.setattr(DO._paket, "kompilera", kompilatorn_sa_nej)
    brist = DO._bygg("PROGRAM P\nEND_PROGRAM\n", karta, rigg, str(tmp_path))
    assert isinstance(brist, D.Brist)
    assert brist.kod == "openplc:kompilerar_inte"

    def kompilatorn_saknas(*a, **k):
        raise P.Byggfel("hittar inte STruC++-CLI:t på /ingenstans")

    monkeypatch.setattr(DO._paket, "kompilera", kompilatorn_saknas)
    with pytest.raises(D.Domsfel):
        DO._bygg("PROGRAM P\nEND_PROGRAM\n", karta, rigg, str(tmp_path))


def test_empty_efter_start_ar_en_dom_men_utebliven_start_ar_ett_domsfel():
    """EMPTY = .so:n laddades inte, alltså lösningens egenskap (M-20).
    Att runtimen aldrig når RUNNING är riggens, alltså ett domsfel."""
    tom = AttrappKlient(statusfoljd=[PLC.TOM], logg="undefined symbol: ...")
    brist = DO._starta(tom, tidsgrans=1.0, paus=0.01)
    assert isinstance(brist, D.Brist)
    assert brist.kod == "openplc:startar_inte"
    assert "undefined symbol" in brist.text

    stoppad = AttrappKlient(statusfoljd=[PLC.STOPPAD])
    with pytest.raises(D.Domsfel):
        DO._starta(stoppad, tidsgrans=0.05, paus=0.01)


def test_busy_ar_en_omstallning_som_far_bli_klar_inte_ett_fel():
    """MÄTT 2026-09-05: `stop-plc` svarar innan omställningen är klar, och
    `start-plc` i glappet svarar BUSY. Det fällde domaren mellan sekvens 1
    och 2 innan `_stoppa` väntade ut stoppet."""
    klient = AttrappKlient(startsvar=["BUSY", "BUSY", "OK"],
                           statusfoljd=[PLC.KOR])
    assert DO._starta(klient, tidsgrans=5.0, paus=0.01) is None
    assert klient.startsvar == ["OK"]


def test_stoppet_vantas_ut_innan_nasta_sekvens():
    klient = AttrappKlient(statusfoljd=[PLC.KOR, PLC.KOR, PLC.STOPPAD])
    assert DO._stoppa(klient, tidsgrans=5.0, paus=0.01) == PLC.STOPPAD
    kvar = AttrappKlient(statusfoljd=[PLC.KOR])
    with pytest.raises(D.Domsfel):
        DO._stoppa(kvar, tidsgrans=0.05, paus=0.01)


def test_uppgift_utan_facit_eller_sekvenser_ger_domsfel():
    post = las("P-05")
    with pytest.raises(D.Domsfel):
        DO.dom({"task_id": "X-01"}, "PROGRAM P\nEND_PROGRAM\n")
    tomt = dict(post)
    tomt["facit_spar"] = dict(post["facit_spar"], sekvenser=[])
    with pytest.raises(D.Domsfel):
        DO.dom(tomt, post["facit_spar"]["referens"])


def test_annan_scanperiod_i_facit_ger_domsfel_inte_en_tyst_omtolkning():
    post = las("P-05")
    fel_rutnat = dict(post["facit_spar"], scan_ms=10.0)
    with pytest.raises(D.Domsfel) as fel:
        DO.dom(post, post["facit_spar"]["referens"], spar=fel_rutnat)
    assert "rutnät" in str(fel.value)


# ============================================================================
# KARTAN OCH PROGRAMMET
# ============================================================================

def test_alla_bankens_uppgifter_med_sparfacit_gar_att_mappa():
    """Fail-closed-listan ska inte hindra en enda uppgift vi faktiskt har.

    Går en uppgift inte att mappa är det ett Domsfel, alltså ingen dom — och
    det får inte gälla banken vi dömer i dag.
    """
    n = 0
    for namn in sorted(os.listdir(UPPGIFTER)):
        if not namn.endswith(".json"):
            continue
        post = json.load(open(os.path.join(UPPGIFTER, namn), encoding="utf-8"))
        if not post.get("facit_spar"):
            continue
        karta = DO._karta_for_post(post)
        assert len(karta.signaler) == len(post["control"]["signals"])
        n += 1
    assert n >= 33, "banken har krympt; mätt 33 uppgifter med spårfacit"


def test_signal_utan_bildtabellplats_ger_domsfel():
    """TIME, STRING och STRUCT är inga bildtabellplatser. Fail-closed."""
    for typ in ("time", "string", "struct"):
        post = {"task_id": "X-01",
                "control": {"signals": [{"name": "S", "dir": "in",
                                         "type": typ}]}}
        with pytest.raises(D.Domsfel) as fel:
            DO._karta_for_post(post)
        assert "går inte att mappa" in str(fel.value)


def test_in_och_utgangar_far_skilda_indexrum():
    post = {"task_id": "X-01", "control": {"signals": [
        {"name": "A", "dir": "in", "type": "bool"},
        {"name": "B", "dir": "out", "type": "bool"},
        {"name": "C", "dir": "in", "type": "int"},
        {"name": "E", "dir": "out", "type": "real"}]}}
    karta = DO._karta_for_post(post)
    adresser = dict((s.tagg, s.adress.text()) for s in karta.signaler)
    assert adresser == {"A": "%IX0.0", "B": "%QX0.0",
                        "C": "%IW0", "E": "%QD0"}


def test_kartans_deklarationer_ligger_forst_och_ar_kartans(monkeypatch):
    """I10: modellen skriver aldrig deklarationerna."""
    post = las("P-05")
    karta = DO._karta_for_post(post)
    text, namn = DO.program_for_st(post["facit_spar"]["referens"], karta)
    assert namn == "ST140_VERKTYGSBYTE"
    assert text.index("ST140_TCH_LOCK AT %QX") < text.index("steg")
    assert "CONFIGURATION Config0" in text


def test_losning_som_deklarerar_om_en_mappad_signal_falls():
    post = las("P-05")
    karta = DO._karta_for_post(post)
    egen = post["facit_spar"]["referens"].replace(
        "    steg        : INT := 0;",
        "    steg        : INT := 0;\n    ST140_TCH_LOCK : BOOL;")
    brist = DO.program_for_st(egen, karta)
    assert isinstance(brist, D.Brist)
    assert brist.kod == "openplc:signal_omdeklarerad"
    assert "ST140_TCH_LOCK" in brist.text


def test_olasbar_st_blir_en_brist_inte_ett_undantag():
    post = las("P-05")
    karta = DO._karta_for_post(post)
    brist = DO.program_for_st("PROGRAM P\n  detta ar inte ST\n", karta)
    assert isinstance(brist, D.Brist)
    assert brist.kod == "openplc:kompilerar_inte"


def test_noll_eller_tva_program_ar_en_brist():
    post = las("P-05")
    karta = DO._karta_for_post(post)
    for kalla in ("FUNCTION F : INT\nEND_FUNCTION\n",
                  "PROGRAM A\nEND_PROGRAM\nPROGRAM B\nEND_PROGRAM\n"):
        brist = DO.program_for_st(kalla, karta)
        assert isinstance(brist, D.Brist)
        assert brist.kod == "openplc:kompilerar_inte"


# ============================================================================
# SPÅRDOMEN: samma mekanik som domare.py
# ============================================================================

def _spar_av_scan(karta, scanvarden, poll_ms=10.0):
    """Ett OPC UA-spår som om PLC:n hade kört de här scanvärdena.

    Två prov per scan, som domarens POLL_S ger vid 20 ms scanperiod.
    """
    spar = []
    for k, varden in enumerate(scanvarden):
        for j in range(2):
            spar.append((k * DO.SCAN_MS + j * poll_ms + 1.0, dict(varden)))
    return spar


def _minimal():
    post = {"task_id": "X-01", "control": {"signals": [
        {"name": "IN1", "dir": "in", "type": "bool"},
        {"name": "UT", "dir": "out", "type": "bool"}]}}
    return post, DO._karta_for_post(post)


def test_punktkrav_godkanns_inom_toleransen_och_falls_utanfor():
    """TOLERANS_SCAN = 4 (M-20:s 2 scan svarstid + M-108:s 2 scan kanalfas).

    Provet mäter gränsen från båda hållen: 4 scan sent är godkänt, 5 scan
    sent är fällt. En tolerans som aldrig fäller är ingen tolerans.
    """
    post, karta = _minimal()
    sekv = {"id": "s1", "steg": [{"t_ms": 0, "satt": {"IN1": True}, "krav": {}},
                                 {"t_ms": 100, "satt": {}, "krav": {"UT": True}}]}
    for forsening, vantat_gron in ((0, True), (4, True), (5, False)):
        scan = [{"IN1": True, "UT": False} for _ in range(40)]
        for k in range(5 + forsening, 40):
            scan[k]["UT"] = True
        brister, _n, matt = DO._dom_sekvens(
            karta, sekv, [], [], _spar_av_scan(karta, scan))
        assert bool(not brister) is vantat_gron, (forsening, brister)
        traff = [m for m in matt if m["signal"] == "UT"][0]
        assert traff["offset_scan"] == (forsening if vantat_gron else None)


def test_invariant_faller_forst_bortom_toleransen():
    """Ett scan där kravet brister är kanalfas. Fem i rad är logik."""
    post, karta = _minimal()
    sekv = {"id": "s1", "steg": [{"t_ms": 0, "satt": {"IN1": True},
                                  "krav": {}}]}
    inv = [{"namn": "aldrig_ut_utan_in", "sekvens": "s1",
            "nar": {"IN1": True}, "kraver": {"UT": False}, "varfor": ""}]
    for brott, ska_falla in ((4, False), (5, True)):
        scan = [{"IN1": True, "UT": False} for _ in range(20)]
        for k in range(3, 3 + brott):
            scan[k]["UT"] = True
        brister, _n, _m = DO._dom_sekvens(
            karta, sekv, inv, [], _spar_av_scan(karta, scan))
        assert bool(brister) is ska_falla, (brott, brister)


def test_flankfonstret_forlangs_bara_bakat():
    """Kanalen kan bara försena. En flank före sitt fönster räknas inte."""
    post, karta = _minimal()
    sekv = {"id": "s1", "steg": [{"t_ms": 0, "satt": {"IN1": True},
                                  "krav": {}}]}
    flank = [{"namn": "en_puls", "sekvens": "s1", "signal": "UT",
              "typ": "RISE", "antal": 1, "fran_ms": 100.0, "till_ms": 200.0,
              "varfor": ""}]
    # Flanken kommer 3 scan efter fönstrets slut: inom kanalfasen, godkänd.
    scan = [{"IN1": True, "UT": False} for _ in range(30)]
    for k in range(13, 30):
        scan[k]["UT"] = True
    brister, _n, _m = DO._dom_sekvens(karta, sekv, [], flank,
                                      _spar_av_scan(karta, scan))
    assert not brister, brister
    # Samma flank FÖRE fönstret räknas inte, och kravet blir 0 av 1.
    tidig = [{"IN1": True, "UT": False} for _ in range(30)]
    for k in range(2, 30):
        tidig[k]["UT"] = True
    brister, _n, _m = DO._dom_sekvens(karta, sekv, [], flank,
                                      _spar_av_scan(karta, tidig))
    assert [b.kod for b in brister] == ["flank:en_puls"]


def test_tva_flankkrav_pa_samma_signal_kan_bada_fallas():
    """M-106:s rättelse, samma i båda domarna: föregående scans värden får
    skrivas först när ALLA flankkrav lästs. Skrevs de inne i slingan fick
    det andra kravet redan det uppdaterade värdet som sitt föregående och
    kunde aldrig fällas."""
    post, karta = _minimal()
    sekv = {"id": "s1", "steg": [{"t_ms": 0, "satt": {"IN1": True},
                                  "krav": {}}]}
    flank = [{"namn": "f1", "sekvens": "s1", "signal": "UT", "typ": "RISE",
              "antal": 1, "fran_ms": 0.0, "till_ms": 400.0, "varfor": ""},
             {"namn": "f2", "sekvens": "s1", "signal": "UT", "typ": "RISE",
              "antal": 2, "fran_ms": 0.0, "till_ms": 400.0, "varfor": ""}]
    scan = [{"IN1": True, "UT": False} for _ in range(30)]
    for k in range(5, 30):
        scan[k]["UT"] = True
    brister, _n, _m = DO._dom_sekvens(karta, sekv, [], flank,
                                      _spar_av_scan(karta, scan))
    assert [b.kod for b in brister] == ["flank:f2"]


def test_bristkoderna_har_samma_form_som_i_domare_py():
    """Samma domarmekanik betyder samma namn. Ett motbevis pekar ut en
    bristkod, och två domare som stavar den olika kan inte jämföras."""
    post, karta = _minimal()
    sekv = {"id": "s1", "steg": [{"t_ms": 0, "satt": {"IN1": True}, "krav": {}},
                                 {"t_ms": 100, "satt": {},
                                  "krav": {"UT": True}}]}
    scan = [{"IN1": True, "UT": False} for _ in range(30)]
    brister, _n, _m = DO._dom_sekvens(karta, sekv, [], [],
                                      _spar_av_scan(karta, scan))
    assert [b.kod for b in brister] == ["s1@100ms:UT"]

    egen = D.dom({"task_id": "X-01", "control": post["control"]},
                 "PROGRAM P\nVAR\n IN1 : BOOL;\n UT : BOOL;\nEND_VAR\n"
                 " UT := FALSE;\nEND_PROGRAM\n",
                 spar={"scan_ms": 20.0, "sekvenser": [sekv]})
    assert egen.koder == ["s1@100ms:UT"]


def test_omsamplingen_haller_sista_vardet_fore_scangransen():
    """Nollte ordningens hållning: scan k bär det sista provet före
    (k+1)*20 ms — samma kant som domare.py läser efter."""
    # Prov vid 0, 25 och 55 ms; scangranserna ligger vid 20, 40, 60 och 80 ms.
    # Scan 2 bar provet fran 55 ms, scan 3 har inget nytt och haller kvar det.
    grid = DO._sampla([(0.0, {"A": 1}), (25.0, {"A": 2}), (55.0, {"A": 3})], 4)
    assert [g.get("A") for g in grid] == [1, 2, 3, 3]


def test_en_signal_som_aldrig_lastes_ar_inte_ett_tyst_godkant():
    """Ett tomt spår ger None, och None är aldrig lika med ett väntat värde."""
    post, karta = _minimal()
    sekv = {"id": "s1", "steg": [{"t_ms": 0, "satt": {}, "krav": {"UT": False}}]}
    brister, _n, matt = DO._dom_sekvens(karta, sekv, [], [], [])
    assert [b.kod for b in brister] == ["s1@0ms:UT"]
    assert matt[0]["offset_scan"] is None


# ============================================================================
# FÖRGRINDEN OCH RIGGENS UPPSLAG
# ============================================================================

class Stationsdom(object):
    def __init__(self):
        self.ok = False
        self.forsta_fallande = "grind2"
        self.forgrindar = {"grind2": "FALLDE"}
        self.utdata = {"grind2": "dubbelskrivning på ST140_TCH_LOCK"}


def test_forgrinden_avgor_utan_att_nagot_kors(monkeypatch):
    """I1: en lösning som inte klarat grind 1-4 når aldrig en PLC, så spåret
    mäter fel storhet. Domaren bygger ingen egen grindkedja."""
    post = las("P-05")
    monkeypatch.setattr(DO, "_bygg", _kor_aldrig)
    d = DO.dom(post, post["facit_spar"]["referens"],
               stationsdom=Stationsdom())
    assert d.koder == ["forgrind:grind2"]
    assert "dubbelskrivning" in d.brister[0].text


def test_riggen_lases_ur_miljon_inte_ur_en_konstant(monkeypatch):
    """Två OpenPLC-runtimes kör på den här maskinen och hör till olika
    mätningar. En hårdkodad port hade dömt genom någon annans PLC."""
    monkeypatch.setenv("VC_ASSIST_OPENPLC_BAS", "https://127.0.0.1:19999")
    monkeypatch.setenv("VC_ASSIST_OPENPLC_ENDPOINT", "opc.tcp://annan:4840/x")
    monkeypatch.setenv("VC_ASSIST_STRUCPP_PAKET", "/en/annan/vag")
    r = DO.Rigg()
    assert r.bas == "https://127.0.0.1:19999"
    assert r.endpoint == "opc.tcp://annan:4840/x"
    assert r.strucpp_paket == "/en/annan/vag"


def test_felraderna_ur_byggloggen_inte_de_sista_raderna():
    """MÄTT 2026-09-05: OpenPLC:s logg slutar med länkkommandon, medan g++:s
    `error:` ligger mitt i. En dom som citerar slutet säger att bygget föll
    och inte varför."""
    text = DO._fel_ur_logg(LOGG_DUBBLERAD_CASE)
    assert "duplicate case value" in text
    assert "Build finished" not in text
    # Utan felrader faller den tillbaka på slutet, i stället för på tystnad.
    assert "rad tre" in DO._fel_ur_logg("rad ett\nrad två\nrad tre\n")
