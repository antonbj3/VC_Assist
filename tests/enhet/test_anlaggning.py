# -*- coding: utf-8 -*-
"""L1 for fas 18: ett inspelat I/O-spar blir ett facit, med sin tackning.

Provsviten ar byggd kring en regel ur uppdraget: **ett tal som ser rimligt ut,
fran ett instrument ingen provat mot ett kant svar, ar projektets vanligaste
fel.** Darfor provas tackningsraknaren har inte mot en bankuppgift utan mot ett
svar JAG SJALV INJICERAR: spar dar jag skrivit varje rad for hand och alltsa vet
exakt hur manga episoder av ett villkor de innehaller.

Grinden har fyra felkoder, och var och en har bade en trasig fixtur som faller
den och ett kontrollfall som visar att den INTE faller nar tackningen bar. En
grind som avvisar allt ser lika bra ut som en som fangar ratt sak, om man bara
raknar avvisningar.

beskriver: bank/anlaggning.py, bank/domare.py
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (_ROT, os.path.join(_ROT, "svc"), os.path.join(_ROT, "bank")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import anlaggning as A                                          # noqa: E402
import domare as D                                              # noqa: E402


# ---- den injicerade stationen -------------------------------------------
#
# Ett program jag skrivit sjalv, sa att jag vet facit. Den bar tva saker:
# en VERKLIG forregling (nodstoppet slar bort bada donen) och en TILLFALLIGHET
# som ser ut som en forregling i normaldrift (klamman foljer detaljgivaren).
# Ett spar ur normalproduktion kan inte skilja dem at, och det ar hela fasen.

STATION = """
PROGRAM Prov
    IF NOT EMG_OK THEN
        BAND := FALSE;
        KLAMMA := FALSE;
    ELSE
        BAND := START;
        KLAMMA := START AND DETALJ;
    END_IF;
END_PROGRAM
"""

SIGNALER = {"EMG_OK": "bool", "START": "bool", "DETALJ": "bool",
            "BAND": "bool", "KLAMMA": "bool"}
RIKTNINGAR = {"EMG_OK": "in", "START": "in", "DETALJ": "in",
              "BAND": "out", "KLAMMA": "out"}
SCAN_MS = 20.0

POST = {"task_id": "X-01",
        "control": {"signals": [{"name": n, "type": t, "dir": RIKTNINGAR[n]}
                                for n, t in sorted(SIGNALER.items())]}}


def _stimuli_normaldrift(varv=3):
    """Normalproduktion: allt friskt, detaljer kommer och gar."""
    steg = [(0.0, {"EMG_OK": True, "START": True, "DETALJ": False})]
    t = 200.0
    for _ in range(varv):
        steg.append((t, {"DETALJ": True}))
        steg.append((t + 200.0, {"DETALJ": False}))
        t += 400.0
    steg.append((t, {}))
    return [("produktion", "normaldrift", steg)]


def _stimuli_med_nodstopp():
    """Samma station, men nagon trycker pa nodstoppet en gang."""
    steg = [(0.0, {"EMG_OK": True, "START": True, "DETALJ": True}),
            (200.0, {"EMG_OK": False}),
            (400.0, {"EMG_OK": True}),
            (600.0, {})]
    return [("nodstopp", "nodstoppet bryts och aterstalls", steg)]


def spar_normaldrift(varv=3):
    return A.spela_in(STATION, SIGNALER, RIKTNINGAR, SCAN_MS,
                      _stimuli_normaldrift(varv), "injicerad station, normaldrift")


def spar_med_nodstopp():
    return A.spela_in(STATION, SIGNALER, RIKTNINGAR, SCAN_MS,
                      _stimuli_normaldrift(2) + _stimuli_med_nodstopp(),
                      "injicerad station, normaldrift + nodstopp")


# ---- 1. instrumentet mot ett kant svar jag sjalv injicerar ---------------

def _handskrivet_spar(monster_per_avsnitt):
    """Ett spar dar JAG skriver varje rad. Facit ar da inte en gissning.

    `monster_per_avsnitt` ar en lista av strangar av "0" och "1": varje tecken
    ar en avlasning av EMG_OK. Antalet episoder ar antalet strak av nollor, och
    det kan raknas for hand ur strangen.
    """
    avsnitt = []
    for i, monster in enumerate(monster_per_avsnitt):
        rader = [{"t_ms": j * SCAN_MS,
                  "varden": {"EMG_OK": c == "1", "START": True,
                             "DETALJ": False, "BAND": c == "1",
                             "KLAMMA": False}}
                 for j, c in enumerate(monster)]
        avsnitt.append(A.Avsnitt("a%d" % i, "handskrivet", rader))
    return A.Spar("handskrivet", SCAN_MS, SIGNALER, RIKTNINGAR, avsnitt)


@pytest.mark.parametrize("monster,episoder,rader", [
    ("1111111111", 0, 0),
    ("1100111111", 1, 2),
    ("1001001111", 2, 4),
    ("0101010101", 5, 5),
    ("0000000000", 1, 10),
])
def test_episodraknaren_mot_ett_injicerat_kant_svar(monster, episoder, rader):
    """Raknaren provas mot ett svar som gar att rakna for hand ur monstret.

    Det har ar hela poangen med provet: ett tal ur ett instrument ingen provat
    mot ett kant svar ar projektets vanligaste fel (M-34, M-57, M-66, M-69,
    M-76, M-77). Har ar det kanda svaret injicerat, tecken for tecken.
    """
    t = A.Tackning(_handskrivet_spar([monster]))
    u = t.underlag({"EMG_OK": False})
    assert u.n_episoder == episoder
    assert u.n_rader == rader
    assert u.av_rader == len(monster)


def test_en_episod_spanner_aldrig_over_ett_avsnittsbyte():
    """Mellan tva inspelningar vet ingen vad som hande.

    Fallan ar konkret: "11110" foljt av "01111" ser ut som en enda episod om
    raknaren laser radorna i foljd. Det ar tva, for mellan avsnitten kan
    nodstoppet ha atergatt och brutits igen utan att nagon sag det.
    """
    t = A.Tackning(_handskrivet_spar(["11110", "01111"]))
    u = t.underlag({"EMG_OK": False})
    assert u.n_rader == 2
    assert u.n_episoder == 2
    assert u.n_avsnitt == 2


def test_tackningen_raknar_byten_och_tysta_signaler():
    t = A.Tackning(_handskrivet_spar(["1100110011"]))
    assert t.byten("EMG_OK") == 4
    assert t.varierar("EMG_OK")
    assert not t.varierar("START")
    assert "START" in t.tysta() and "EMG_OK" not in t.tysta()


# ---- 2. harledningen: det harledda facit haller for kallan ---------------

def test_harlett_facit_uppfylls_av_programmet_det_kom_ur():
    """Ett facit ingen kan uppfylla faller alla och ser ut som en svar bank.

    En anlaggning lamnar ingen kallkod, sa ett harlett facit har ingen
    referenslosning att bevisa uppfyllbarheten med. Beviset ar i stallet
    inspelningen sjalv: varje pastaende ar en avlasning som redan har hant.
    Det provet ar det har.
    """
    spar = spar_med_nodstopp()
    h = A.harled(spar)
    dom = D.dom(POST, STATION, spar=h.facit)
    assert dom.godkand, dom.text()
    assert dom.scan_kord == spar.antal_rader


def test_harlett_facit_faller_en_muterad_station():
    """Och ett facit som inget faller mater ingenting.

    Mutationen tar bort detaljgivaren ur klammans villkor. Den ar avsiktligt
    LITEN: den syns inte i nagon signals typ, bara i vilka tillstand som
    forekommer tillsammans.
    """
    h = A.harled(spar_med_nodstopp())
    muterad = STATION.replace("KLAMMA := START AND DETALJ;", "KLAMMA := START;")
    assert muterad != STATION
    dom = D.dom(POST, muterad, spar=h.facit)
    assert not dom.godkand
    assert dom.koder


def test_harledningen_stamplar_sitt_ursprung():
    h = A.harled(spar_normaldrift())
    assert h.facit["harledd"] is True
    assert h.facit["tackning"]["antal_rader"] == h.spar.antal_rader
    for inv in h.facit["invarianter"]:
        assert inv["underlag"]["villkor"]["n_rader"] > 0
    for f in h.facit["flanker"]:
        assert f["underlag"]["n_rader"] > 0


def test_varje_punktkrav_ligger_utanfor_marginalen():
    """Marginalregeln ar bankens, och den galler ocksa det harledda facit."""
    h = A.harled(spar_med_nodstopp())
    marginal = A.MARGINAL_SCAN * SCAN_MS
    for sekv in h.facit["sekvenser"]:
        senaste_satt = None
        for s in sekv["steg"]:
            if s["satt"]:
                senaste_satt = float(s["t_ms"])
            if s["krav"]:
                assert senaste_satt is None or \
                    float(s["t_ms"]) - senaste_satt >= marginal - 1e-9, \
                    "%s vid %s" % (sekv["id"], s["t_ms"])


# ---- 3. FASENS GRIND: tackning innan pastaende --------------------------

_NODSTOPPSINVARIANT = {
    "namn": "inget_don_med_brutet_nodstopp",
    "sekvens": "*",
    "nar": {"EMG_OK": False},
    "kraver": {"BAND": False},
    "varfor": "IEC 60204-1",
}


def test_trasig_fixtur_ett_spar_utan_nodstopp_far_inte_doma_nodstoppet():
    """FASENS VIKTIGASTE GRIND, och den maste falla har.

    Inspelningen ar en normaldriftsdag: nodstoppet stod slutet hela tiden. Ett
    facit som anda pastar vad som hander nar det bryts pastar nagot spåret
    aldrig sag, och det ar ett facit som ljuger. Grinden ska namna signalen och
    namnaren, inte bara saga nej.
    """
    spar = spar_normaldrift()
    assert A.Tackning(spar).observerad("EMG_OK", False) == 0

    facit = {"invarianter": [_NODSTOPPSINVARIANT]}
    brister = A.granska(facit, spar)
    koder = [b.kod for b in brister]
    assert A.T1_OTACKT_VILLKOR in koder
    text = [b.text for b in brister if b.kod == A.T1_OTACKT_VILLKOR][0]
    assert "EMG_OK" in text
    assert "0 av %d" % spar.antal_rader in text


def test_kontrollfall_samma_invariant_slapps_igenom_nar_sparet_bar_den():
    """Tva sidor av samma grind. Utan det har provet ar grinden trivial:
    en grind som alltid vagrar ar inte forsiktig, den ar tom."""
    spar = spar_med_nodstopp()
    assert A.Tackning(spar).observerad("EMG_OK", False) > 0
    brister = A.granska({"invarianter": [_NODSTOPPSINVARIANT]}, spar)
    assert [b.kod for b in brister] == []


def test_harledningen_sjalv_pastar_aldrig_nagot_om_ett_osett_lage():
    """Grinden ar en spärr; harledningen far inte behova den.

    Det ar skillnad pa att FANGA ett falskt pastaende och pa att inte gora det.
    Harledningen ska aldrig lamna ifran sig ett pastaende om ett lage spåret
    inte visat - och de den vagrade ska ligga kvar med sitt skal.
    """
    spar = spar_normaldrift()
    h = A.harled(spar)
    # EMG_OK stod still hela inspelningen. Da far den inte forekomma i ETT enda
    # harlett pastaende - varken som villkor eller som krav.
    for inv in h.facit["invarianter"]:
        assert "EMG_OK" not in inv["nar"], inv
        assert "EMG_OK" not in inv["kraver"], inv
    assert not A.granska(h.facit, spar)
    vagrade = [e for e in h.ej_pastatt
               if "EMG_OK" in str(e["nar"]) or "EMG_OK" in str(e["kraver"])]
    assert vagrade, "harledningen namner inte ens att EMG_OK inte gick att doma"
    for e in vagrade:
        assert e["skal"].strip(), e
    assert any("stod still" in e["skal"] or "varje" in e["skal"]
               or "aldrig" in e["skal"] for e in vagrade), \
        [e["skal"] for e in vagrade]


def test_trasig_fixtur_ett_krav_pa_en_signal_spåret_inte_har():
    facit = {"invarianter": [{"namn": "hittepa", "sekvens": "*",
                             "nar": {"EMG_OK": True},
                             "kraver": {"FINNS_INTE": True}, "varfor": "x"}]}
    koder = [b.kod for b in A.granska(facit, spar_normaldrift())]
    assert A.T2_OKAND_SIGNAL in koder


def test_trasig_fixtur_ett_harlett_facit_utan_namnare():
    """Ett harlett pastaende utan underlag gar inte att vaga."""
    h = A.harled(spar_med_nodstopp())
    assert not A.granska(h.facit, h.spar)
    for inv in h.facit["invarianter"]:
        inv.pop("underlag")
    for f in h.facit["flanker"]:
        f.pop("underlag")
    koder = [b.kod for b in A.granska(h.facit, h.spar)]
    assert A.T3_UTAN_UNDERLAG in koder


def test_trasig_fixtur_ett_harlett_facit_utan_tackningsuppgift():
    h = A.harled(spar_med_nodstopp())
    h.facit.pop("tackning")
    brister = A.granska(h.facit, h.spar)
    assert [b for b in brister
            if b.kod == A.T3_UTAN_UNDERLAG and b.pastaende == "facit"]


def test_kontrollfall_ett_handskrivet_facit_krävs_inte_pa_namnare():
    """Ett handskrivet facit har sin harkomst i en standard, inte i en matning.

    IEC 60204-1 sager att en nodstoppskrets kraver manuell aterstallning. Det
    pastaendet star upp utan en enda observation, och en grind som kraver en
    namnare av det mater fel storhet.
    """
    brister = A.granska({"invarianter": [_NODSTOPPSINVARIANT]},
                        spar_med_nodstopp())
    assert not [b for b in brister if b.kod == A.T3_UTAN_UNDERLAG]


def test_trasig_fixtur_ett_punktkrav_pa_ett_varde_som_aldrig_sags():
    """BAND stod pa 1 hela normaldriften. Ett facit som kraver 0 pastar nagot
    spåret aldrig visat, precis som nodstoppsfallet."""
    spar = spar_normaldrift()
    assert A.Tackning(spar).observerad("BAND", False) == 0
    facit = {"sekvenser": [{"id": "s", "beskrivning": "", "steg": [
        {"t_ms": 100.0, "satt": {}, "krav": {"BAND": False}, "varfor": "x"}]}]}
    koder = [b.kod for b in A.granska(facit, spar)]
    assert A.T4_OTACKT_KRAV in koder


def test_trasig_fixtur_ett_flankkrav_pa_en_flank_som_aldrig_hant():
    spar = spar_normaldrift()
    facit = {"flanker": [{"namn": "f", "sekvens": "produktion",
                          "signal": "BAND", "typ": "FALL",
                          "fran_ms": 0.0, "till_ms": 100.0, "antal": 3,
                          "varfor": "x"}]}
    koder = [b.kod for b in A.granska(facit, spar)]
    assert A.T4_OTACKT_KRAV in koder


def test_kontrollfall_ett_flankkrav_pa_noll_flanker_ar_en_observation():
    """"Den pulsade aldrig" ar nagot spåret FAKTISKT visade."""
    spar = spar_normaldrift()
    facit = {"flanker": [{"namn": "f", "sekvens": "produktion",
                          "signal": "BAND", "typ": "FALL",
                          "fran_ms": 0.0, "till_ms": 100.0, "antal": 0,
                          "varfor": "x"}]}
    assert not [b for b in A.granska(facit, spar)
                if b.kod == A.T4_OTACKT_KRAV]


# ---- 4. korrelation ar inte orsak, som ett tal --------------------------

def test_en_tillfallighet_ur_normaldrift_motbevisas_av_en_annan_inspelning():
    """Fas 18:s tredje arlighetskrav, mekaniserat.

    I normaldrift foljer klamman detaljgivaren exakt: DETALJ = 1 ger alltid
    KLAMMA = 1. Det SER ut som stationens regel, och harledningen foreslar det
    som ett forbud. Inspelningen med nodstoppet visar att det inte ar en regel:
    med brutet nodstopp ligger klamman kvar oppen med detaljen framme.

    Det ar exakt den sortens pastaende ett dygns produktionsspar ar fullt av,
    och skillnaden mellan en forregling och en tillfallighet syns bara i data
    sparet inte har.
    """
    prod = spar_normaldrift()
    h = A.harled(prod)
    kullkastade = A.motbevisade(h.facit, spar_med_nodstopp())
    assert kullkastade, "ingen harledd invariant motbevisades - provet mater inget"
    namn = set(inv["namn"] for inv, _ in kullkastade)
    assert any("KLAMMA" in n for n in namn), sorted(namn)


def test_ingen_harledd_invariant_motbevisas_av_sin_egen_inspelning():
    """Kontrollen: motbevisaren far inte fyra pa vad som helst."""
    spar = spar_med_nodstopp()
    h = A.harled(spar)
    assert A.motbevisade(h.facit, spar) == []


# ---- 5. mer data ur samma gren ar inte mer tackning ---------------------

def test_tio_ganger_sa_manga_rader_ger_inte_ett_enda_nytt_lage():
    """M-75:s slutsats som ett prov: en anlaggning kor mest normalproduktion,
    och ett dygns spar darifran ger tusentals rader ur SAMMA gren."""
    litet = A.Tackning(spar_normaldrift(1))
    stort = A.Tackning(spar_normaldrift(10))
    assert stort.antal_rader > 3 * litet.antal_rader
    assert stort.observerad("EMG_OK", False) == 0
    assert litet.observerad("EMG_OK", False) == 0
    assert stort.tysta() == litet.tysta()


# ---- 6. spåret bar inga inre tillstand ----------------------------------

def test_inspelningen_bar_bara_signalkartan():
    """Programmets eget inre syns aldrig i sparet (M-75). Provet ar mekaniskt:
    ingen rad far bara ett namn som inte star i signalkartan."""
    spar = spar_med_nodstopp()
    for r in spar.rader():
        assert set(r["varden"]) == set(SIGNALER)


def test_tathet_andringar_ar_glesare_och_slapper_igenom_mer():
    """MATT i M-89: en glesare avlasning slapper igenom verkliga fel.

    Harleder man bara vid utsignalandringar star facit tyst mellan tva
    andringar, och dar far koden gora vad den vill. Provet visar bada halvorna:
    den glesa formen ar faktiskt glesare, och den tata faller ett program som
    den glesa slapper igenom.
    """
    spar = spar_med_nodstopp()
    tat = A.harled(spar, tathet="varje_rad")
    gles = A.harled(spar, tathet="andringar")

    def krav(h):
        return sum(1 for s in h.facit["sekvenser"] for st in s["steg"] if st["krav"])
    assert krav(tat) > krav(gles)

    # En station som SLAPPER KLAMMAN FOR TIDIGT: den stiger i samma scan som
    # originalet och faller i samma scan som givaren, sa flankantalet ar
    # oforandrat och bada andringspunkterna stammer. Skillnaden ligger helt och
    # hallet MELLAN dem, och det ar precis dar ett glest facit star tyst.
    for_tidig = """
PROGRAM Prov
VAR
    n : INT;
END_VAR
    IF NOT EMG_OK THEN
        BAND := FALSE;
        KLAMMA := FALSE;
        n := 0;
    ELSE
        BAND := START;
        IF DETALJ THEN
            n := n + 1;
        ELSE
            n := 0;
        END_IF;
        KLAMMA := START AND DETALJ AND (n <= 5);
    END_IF;
END_PROGRAM
"""
    assert not D.dom(POST, for_tidig, spar=tat.facit).godkand
    assert D.dom(POST, for_tidig, spar=gles.facit).godkand, (
        "den glesa formen fangade det - da mater provet inte skillnaden")


def test_harledningen_ar_deterministisk():
    """Samma inspelning ska ge samma facit, tecken for tecken.

    Harledningen loper over ordbocker och mangder. Ett facit vars innehall
    beror pa iterationsordning gar inte att jamfora mellan tva korningar, och
    da gar heller inget tal ur den att upprepa.
    """
    spar = spar_med_nodstopp()
    a = json.dumps(A.harled(spar).facit, sort_keys=True)
    b = json.dumps(A.harled(spar).facit, sort_keys=True)
    assert a == b


def test_ett_spar_utan_harkomst_avvisas():
    with pytest.raises(A.Anlaggningsfel):
        A.Spar("", SCAN_MS, SIGNALER, RIKTNINGAR,
               [A.Avsnitt("a", "", [{"t_ms": 0.0, "varden": {}}])])


def test_spar_gar_att_spara_och_lasa_tillbaka():
    spar = spar_med_nodstopp()
    tillbaka = A.Spar.fran_json(spar.som_json())
    assert tillbaka.antal_rader == spar.antal_rader
    assert A.Tackning(tillbaka).som_json() == A.Tackning(spar).som_json()
