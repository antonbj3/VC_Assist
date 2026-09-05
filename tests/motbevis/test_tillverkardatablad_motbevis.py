# -*- coding: utf-8 -*-
"""Motbevis: fem hål M-107:s gröna svit inte ser. Rött är rätt utfall.

`tests/enhet/test_tillverkardatablad.py` mäter att **det nya lagret** aldrig
härleder en enhet, aldrig skriver ut en nolla som en storhet och alltid avstår
när ena sidan saknar enhet. Alla fem proven nedan faller ändå, och de faller på
saker som ligger **utanför** det lagret eller **bredvid** dess grind:

1. Grinden mäter talet och enheten, inte att citatet handlar om **rätt
   storhet**. En diameter går att citera som en räckvidd.
2. Grinden skyddar det nya lagret. `katalogsok.Traff.rad` — som redan levereras
   — fäster `mm` och `kg` vid samma enhetslösa katalogfält, och skriver
   `0 kg` för de 628 komponenter M-85 räknade.
3. Bankens 15 robotposter bär stämpeln `PUBLICERAD_SPEC`, som säger att talen
   kommer ur tillverkarens publicerade datablad. Ingen av dem bär en URL.
4. Berikningen når 21 av 3201 komponenter. 2175 robotar står kvar som
   `enhet_saknas` för nyttolast.
5. En komponent vars katalogfält **motsäger** den citerade källan passerar
   tyst. VC skriver `MaxPayload 12` för UR10e; Universal Robots skriver
   `12,5 kg`.

Körs separat: `python3 -m pytest tests/motbevis -q`
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import tillverkardatablad as TD                # noqa: E402
from vc_assist_svc import katalogsok, katalogindex                # noqa: E402
from vc_assist_svc import komponentdatablad as KD                 # noqa: E402

SHA = "b" * 64


def _bibliotek():
    fynd = katalogindex.hitta()
    if not fynd:
        pytest.skip("inget installerat VC-bibliotek pa den har maskinen")
    return fynd[0].rot


# ---------------------------------------------------------------------------
# 1. Grinden mäter närhet, inte betydelse
# ---------------------------------------------------------------------------

def test_enhetsgrinden_ser_inte_att_citatet_handlar_om_en_annan_storhet():
    """ABB:s rad säger DIAMETER. Grinden släpper igenom den som räckvidd.

    `IRB 360-1/1130 * 1 kg 1130 mm` står under rubriken *Diameter*, inte
    *Reach* — arbetsområdets diameter är dubbla radien. Enhetsgrinden
    kontrollerar att talet och enheten står bredvid varandra, och det gör de.
    Att raden svarar på en **annan fråga** ser den inte.

    I den levererade korpusen är fältet handsatt som `ej_belagt` med just det
    skälet. Det är ett omdöme i en tabell, inte en grind — och ett omdöme som
    ingen grind bevakar är exakt det som glider bort nästa gång.
    """
    kalla = TD.Kalla(url="https://library.e.abb.com/public/x/ROB0082EN_F_HR.pdf",
                     hamtad="2026-09-05", sha256=SHA,
                     citat="IRB 360-1/1130 * 1 kg 1130 mm 3/4")
    with pytest.raises(TD.Tillverkarfel):
        TD.Uppgift(falt="rackvidd", varde=1130, enhet="mm", kalla=kalla)


# ---------------------------------------------------------------------------
# 2. Grinden i det nya lagret skyddar inte det gamla
# ---------------------------------------------------------------------------

def test_ingen_levererad_kod_faster_en_enhet_vid_ett_enhetslost_katalogfalt():
    """`katalogsok.Traff.rad` skriver `%.0f mm` och `%.0f kg`.

    Talen kommer ur `model.xml`:s `Reach` och `MaxPayload`, som filen skriver
    UTAN enhet (M-85). Sökskiktet är det modellen faktiskt läser, och det
    skriver ut en enhet ingen källa har sagt — i samma repo som just har byggt
    en grind mot precis det.

    En grind i rapportvägen skyddar inte importvägen.
    """
    traff = katalogsok.Traff(namn="Nagon robot", tillverkare="X", kategori="",
                             sokvag="/x.vcmx",
                             rackvidd_mm=901.0, nyttolast_kg=5.0)
    rad = traff.rad()
    assert "901 mm" not in rad and "5 kg" not in rad, (
        "katalogsok skriver ut en enhet som model.xml aldrig deklarerade: %s"
        % rad)


# ---------------------------------------------------------------------------
# 3. Bankens stämpel lovar en källa den inte bär
# ---------------------------------------------------------------------------

def test_varje_bankpost_med_stampeln_publicerad_spec_bar_en_kalla():
    """Stämpeln säger ordagrant: *"räckvidd, nyttolast och mått kommer ur
    tillverkarens publicerade datablad för den namngivna modellen"*.

    Ingen av bankens poster bär en URL eller ett hämtdatum. Ett datablad utan
    källa är ett påstående, och stämpeln gör påståendet svårare att se, inte
    lättare: den ser ut som en härkomst.

    Skarpast: `bank://robot/abb_irb_360_1_1130` bär `rackvidd_mm: 565` under
    stämpeln. ABB publicerar 1130 mm som DIAMETER. 565 är 1130/2 — en RÄKNING
    på ett publicerat tal, inte ett publicerat tal.
    """
    with open(os.path.join(_ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        bank = json.load(f)
    utan_kalla = [p["uri"] for p in bank["poster"]
                  if p.get("stampel") == "PUBLICERAD_SPEC"
                  and not (p.get("kalla") or p.get("kalla_url"))]
    assert not utan_kalla, (
        "%d poster stamplade PUBLICERAD_SPEC utan en URL: %s"
        % (len(utan_kalla), utan_kalla[:6]))


# ---------------------------------------------------------------------------
# 4. Täckningen
# ---------------------------------------------------------------------------

def test_varje_robot_som_banken_namner_har_en_belagd_nyttolast():
    """Bänkens celler jämför nyttolast och räckvidd. Fyra av bankens femton
    robotar har ingen källa alls.

    Tre skäl, alla uppmätta i M-107: KUKA har tagit bort sixx- och
    extra-generationerna ur sitt publika dokumentindex (två modeller), FANUC:s
    PDF för M-710iC/50 flätar samman kolumnerna vid textutdragningen så att
    varken par- eller kolumngrinden kan verifiera talet, och ABB:s
    910SC-tabell skriver ingen enhet vid *Reach*.
    """
    korpus = TD.Korpus.las()
    with open(os.path.join(_ROT, "bank", "katalog_index.json"),
              encoding="utf-8") as f:
        bank = json.load(f)
    utan = []
    for p in bank["poster"]:
        if p.get("kategori") != "robot":
            continue
        b = korpus.for_bank_uri(p["uri"])
        if b is None or b.svar("nyttolast").lage != TD.FINNS:
            utan.append(p["namn"])
    assert not utan, "%d av bankens robotar saknar en belagd nyttolast: %s" % (
        len(utan), utan)


def test_varje_robot_i_biblioteket_med_ett_maxpayload_har_ocksa_en_enhet():
    """2175 robotar bär ett MaxPayload utan enhet.

    Berikningen når 21 komponenter av 3201. Det är inte ett fel i mekanismen —
    den gör exakt vad den ska på de 28 modeller korpusen bär. Det är
    TÄCKNINGEN som saknas, och skillnaden mellan "mekanismen finns" och
    "biblioteket är berikat" är två storleksordningar.
    """
    rot = _bibliotek()
    korpus = TD.Korpus.las()
    utan, med = 0, 0
    for katalog, _k, filer in os.walk(rot):
        for f in sorted(filer):
            if not f.lower().endswith((".vcmx", ".vcm")):
                continue
            try:
                blad = KD.las(os.path.join(katalog, f))
            except KD.Databladfel:
                continue
            if blad.katalogfalt.get("maxpayload") is None:
                continue
            svar = TD.berika(blad, korpus, ("nyttolast",))["nyttolast"]
            if svar.lage == TD.FINNS:
                med += 1
            else:
                utan += 1
    assert utan == 0, ("%d komponenter bar ett MaxPayload utan enhet; %d har "
                       "en enhet med kalla" % (utan, med))


# ---------------------------------------------------------------------------
# 5. En motsägelse mellan VC och tillverkaren passerar tyst
# ---------------------------------------------------------------------------

def test_en_komponent_vars_katalogfalt_motsager_kallan_flaggas():
    """VC skriver `MaxPayload 12` för UR10e. Universal Robots skriver 12,5 kg.

    `berika()` låter tillverkarens tal vinna och säger ingenting om att VC:s
    egen fil säger något annat. Den som läser svaret ser 12,5 kg med en källa
    och har ingen anledning att misstänka att simuleringen räknar med 12.

    Samma klass, uppmätt i M-107: `IRB 1200-5/0.9` har `Reach = 0` i model.xml
    medan ABB skriver 901 mm, och `IRB 4600-20/2.50` har 2500 mot ABB:s
    2,51 m.
    """
    rot = _bibliotek()
    korpus = TD.Korpus.las()
    motsagelser = []
    for katalog, _k, filer in os.walk(rot):
        for f in sorted(filer):
            if not f.lower().endswith((".vcmx", ".vcm")):
                continue
            try:
                blad = KD.las(os.path.join(katalog, f))
            except KD.Databladfel:
                continue
            post = korpus.for_vc_namn(blad.namn)
            if post is None:
                continue
            for falt, kfalt in (("nyttolast", "maxpayload"), ("rackvidd", "reach")):
                s = post.svar(falt)
                rå = blad.katalogfalt.get(kfalt)
                if s.lage != TD.FINNS or rå is None:
                    continue
                try:
                    vc = float(str(rå).replace(",", "."))
                except ValueError:
                    continue
                if abs(vc - s.kanoniskt()) > 1e-6:
                    motsagelser.append(
                        "%s/%s: model.xml %s, %s %g %s"
                        % (blad.namn, falt, rå, s.kalla.url.split("/")[2],
                           s.varde, s.enhet))
    # Berikningen returnerar inget falt som sager att de tva kallorna
    # motsager varandra. Provet listar dem; koden gor det inte.
    assert not motsagelser, (
        "%d falt dar VC:s katalogfalt och tillverkarens datablad sager olika "
        "tal, utan att nagon grind eller nagot svarsfalt namner det: %s"
        % (len(motsagelser), motsagelser))
