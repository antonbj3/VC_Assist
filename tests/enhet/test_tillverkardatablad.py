# -*- coding: utf-8 -*-
"""L1 för det tredje källskiktet. Inget nät, ingen VC, inget bibliotek.

Varje grind här har en **trasig fixtur**. En grind vars fel ingen har visat går
inte att skilja från en grind som alltid säger ja, och fyra av felen nedan är de
fall `docs/spec/51_komponentdata.md` namnger:

  * en enhet som härletts ur ett värde (`MaxPayload: 180` → `180 kg`)
  * en nolla utan enhet som skrivs ut som en storhet (`MaxPayload = 0` → `0 kg`)
  * ett värde med källa jämfört med ett utan
  * en källa som inte går att nå och blir ett tyst tomt fält

Två av dem är fel som byggets EGEN kod gjorde och som grinden fällde:
`_talmonster` matchade inte `2.80 m` (efterföljande nolla), och den saknade
vänsterspärr så att `901 mm` matchade inne i `1901 mm`.
"""
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import tillverkardatablad as TD                # noqa: E402
from vc_assist_svc import komponentdatablad as KD                 # noqa: E402

SHA = "a" * 64


def _kalla(citat, url="https://example.invalid/datablad.pdf", utdrag=""):
    return TD.Kalla(url=url, hamtad="2026-09-05", sha256=SHA, citat=citat,
                    utdrag=utdrag)


class _Attrappblad:
    """Ett `komponentdatablad.Datablad` så långt berikningen bryr sig."""

    def __init__(self, namn, katalogfalt=None):
        self.namn = namn
        self.katalogfalt = dict(katalogfalt or {})


# ---------------------------------------------------------------------------
# 1. Enhetsgrinden: en enhet härleds ALDRIG ur ett värde
# ---------------------------------------------------------------------------

def test_en_enhet_som_harletts_ur_ett_varde_falls():
    """DET TRASIGA FALLET ur specens §1: `MaxPayload: 180` blir `180 kg`.

    Katalogposten skriver talet och ingenting mer. Att fästa `kg` vid det är
    troligen rätt och ändå ett påhitt — och det är just därför det överlever.
    """
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Uppgift(falt="nyttolast", varde=180, enhet="kg",
                   kalla=_kalla("MaxPayload 180"))
    assert "star inte bredvid" in str(fel.value)
    assert "180" in str(fel.value)


def test_samma_varde_med_enheten_bredvid_sig_gar_igenom():
    """Grinden får inte vara en grind som alltid säger nej."""
    u = TD.Uppgift(falt="nyttolast", varde=180, enhet="kg",
                   kalla=_kalla("660-180/3.15 180 kg 3.15 m"))
    assert u.kanoniskt() == 180.0
    assert u.lasning == TD.ORDAGRANT_PAR


def test_enheten_far_inte_lanas_fran_ett_annat_tal_i_samma_citat():
    """`3.15 m` i citatet gör inte 180 till 180 m."""
    with pytest.raises(TD.Tillverkarfel):
        TD.Uppgift(falt="rackvidd", varde=180, enhet="m",
                   kalla=_kalla("660-180/3.15 180 kg 3.15 m"))


@pytest.mark.parametrize("citat,varde,enhet,vantat", [
    # Det egna felet: `2.80 m` matchade inte 2.8 innan efterföljande nollor
    # tilläts. ABB skriver `2.80` och `3.15` i samma tabell.
    ("6700-205 2.80 m 205 kg", 2.80, "m", True),
    ("x 2.00 m", 2.0, "m", True),
    ("x 2 m", 2.0, "m", True),
    # Det andra egna felet: utan vänsterspärr matchade 901 inne i 1901.
    ("reach 1901 mm", 901, "mm", False),
    ("reach 901 mm", 901, "mm", True),
    # mm är inte m.
    ("reach 901 mm", 901, "m", False),
    # Tusentalsavskiljare: Yaskawa skriver 1,693 mm.
    ("1,693 mm vertical reach", 1693, "mm", True),
    # Ett annat tal är ett annat tal.
    ("Payload 12.5 kg", 12, "kg", False),
    ("Payload 12.5 kg", 12.5, "kg", True),
])
def test_par_i_citat_mater_narhet_och_inte_narvaro(citat, varde, enhet, vantat):
    assert TD.par_i_citat(citat, varde, enhet) is vantat


# ---------------------------------------------------------------------------
# 2. Kolumnläsningen: enheten står i rubriken, och kopplingen är positionell
# ---------------------------------------------------------------------------

_RUBRIK = "Robot variant Handling capacity (kg) Reach (m)"
_RAD = "IRB 2600-20/1.65 20 1.65"
_CITAT = _RUBRIK + " " + _RAD


def test_kolumnlasningen_gar_igenom_nar_bade_rubrik_och_rad_stammer():
    u = TD.Uppgift(falt="nyttolast", varde=20, enhet="kg",
                   kalla=_kalla(_CITAT),
                   kolumn=TD.Kolumn(_RUBRIK, _RAD, "IRB 2600-20/1.65", 0))
    assert u.kanoniskt() == 20.0
    assert u.lasning == TD.POSITIONSLAST


def test_kolumnlasningen_faller_pa_fel_kolumn():
    """TRASIG FIXTUR: kolumn 0 är kg, inte m. En förskjuten läsning ger ett
    trovärdigt tal med fel enhet, och det är precis vad som ska fällas."""
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Uppgift(falt="rackvidd", varde=20, enhet="m",
                   kalla=_kalla(_CITAT),
                   kolumn=TD.Kolumn(_RUBRIK, _RAD, "IRB 2600-20/1.65", 0))
    assert "rubriken sager enheten" in str(fel.value)


def test_kolumnlasningen_faller_nar_rubriken_inte_star_i_citatet():
    """En rubrik som inte finns i dokumentet är en gissning om en tabell."""
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Uppgift(falt="nyttolast", varde=20, enhet="kg",
                   kalla=_kalla(_RAD),
                   kolumn=TD.Kolumn(_RUBRIK, _RAD, "IRB 2600-20/1.65", 0))
    assert "star inte i kallans citat" in str(fel.value)


def test_kolumnlasningen_faller_nar_talet_inte_star_i_raden():
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Uppgift(falt="nyttolast", varde=25, enhet="kg",
                   kalla=_kalla(_CITAT),
                   kolumn=TD.Kolumn(_RUBRIK, _RAD, "IRB 2600-20/1.65", 0))
    assert "sager talet 20" in str(fel.value)


def test_raden_maste_borja_med_modellnamnet():
    """Modellnamnet bär siffror. Räknas de med blir kolumnindexet meningslöst."""
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Kolumn(_RUBRIK, _RAD, "IRB 4600-60/2.05", 0)
    assert "borjar inte med modellnamnet" in str(fel.value)


# ---------------------------------------------------------------------------
# 3. Källan: en siffras härkomst hör till siffran
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("falt,varde", [
    ("url", "inte-en-url"), ("hamtad", "5 september"), ("sha256", "abc"),
    ("citat", "   "),
])
def test_en_kalla_utan_alla_fyra_falten_ar_ingen_kalla(falt, varde):
    d = dict(url="https://example.invalid/a.pdf", hamtad="2026-09-05",
             sha256=SHA, citat="Payload 5 kg")
    d[falt] = varde
    with pytest.raises(TD.Tillverkarfel):
        TD.Kalla(**d)


def test_en_uppgift_utan_kalla_ar_ett_pastaende():
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Uppgift(falt="nyttolast", varde=5, enhet="kg", kalla=None)
    assert "pastaende" in str(fel.value)


def test_citatet_maste_sta_i_utdraget():
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Kalla(url="https://example.invalid/a.pdf", hamtad="2026-09-05",
                 sha256=SHA, citat="Payload 5 kg",
                 utdrag="ingenting om nyttolast alls")
    assert "star inte i utdraget" in str(fel.value)


def test_en_enhet_utanfor_faltets_storhet_avvisas():
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Uppgift(falt="nyttolast", varde=5, enhet="mm",
                   kalla=_kalla("Payload 5 mm"))
    assert "hor inte till storheten Mass" in str(fel.value)


# ---------------------------------------------------------------------------
# 4. De tre lägena, och att `enhet_saknas` inte bär något tal
# ---------------------------------------------------------------------------

def test_enhet_saknas_bar_inget_talvarde():
    """Det som gör läget verkningsfullt: det finns inget tal att räkna på.

    Ett `Svar` som bar en float hade varit en märkning man kan glömma. Ett som
    inte gör det går inte att jämföra av misstag.
    """
    s = TD.enhet_saknas("nyttolast", "180", "model.xml skriver bara talet")
    assert s.varde is None
    assert s.enhet == ""
    assert s.ordagrant == "180"
    assert s.jamforbar is False
    assert s.kanoniskt() is None


def test_enhet_saknas_med_ett_talvarde_ar_en_motsagelse():
    """TRASIG FIXTUR: den som försöker smuggla in ett tal blir fälld."""
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Svar(falt="nyttolast", lage=TD.ENHET_SAKNAS, varde=180.0,
                ordagrant="180", skal="x")
    assert "far INTE bara ett talvarde" in str(fel.value)


def test_enhet_saknas_med_en_enhet_ar_en_motsagelse():
    with pytest.raises(TD.Tillverkarfel):
        TD.Svar(falt="nyttolast", lage=TD.ENHET_SAKNAS, enhet="kg",
                ordagrant="180", skal="x")


def test_saknas_maste_saga_vad_som_lettes_efter():
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Svar(falt="nyttolast", lage=TD.SAKNAS)
    assert "maste saga VAD som lettes efter" in str(fel.value)


def test_finns_kraver_varde_enhet_och_kalla():
    with pytest.raises(TD.Tillverkarfel):
        TD.Svar(falt="nyttolast", lage=TD.FINNS, varde=5.0, enhet="kg")


# ---------------------------------------------------------------------------
# 5. Nollan: 628 komponenter, och ingen av dem påstår en nyttolast
# ---------------------------------------------------------------------------

def test_en_nolla_utan_enhet_skrivs_aldrig_ut_som_en_storhet():
    """DET TRASIGA FALLET ur specens §1.

    `MaxPayload = 0` i 628 av 3201 komponenter (M-85). En nolla utan enhet är
    inte en nyttolast på noll kilo — det är ett ofyllt fält.
    """
    blad = _Attrappblad("Nagon komponent", {"maxpayload": "0"})
    svar = TD.berika(blad, korpus=None, falt=("nyttolast",))["nyttolast"]
    assert svar.lage == TD.ENHET_SAKNAS
    assert svar.varde is None
    assert svar.ordagrant == "0"
    t = svar.text()
    assert "0 kg" not in t
    assert "ofyllt falt" in t
    assert "ENHET SAKNAS" in t


def test_nollan_gar_inte_att_jamfora_ens_med_ett_annat_tal_med_enhet():
    blad = _Attrappblad("Nagon komponent", {"maxpayload": "0"})
    tak = TD.berika(blad, korpus=None, falt=("nyttolast",))["nyttolast"]
    behov = TD.Svar(falt="nyttolast", lage=TD.FINNS, varde=1.0, enhet="kg",
                    kalla=_kalla("Payload 1 kg"))
    d = TD.rymmer(behov, tak)
    assert d.avstar
    assert "INGEN enhet" in d.skal


# ---------------------------------------------------------------------------
# 6. Jämförelsen avstår hellre än gissar
# ---------------------------------------------------------------------------

def _finns(falt, varde, enhet, citat):
    return TD.finns(falt, TD.Uppgift(falt=falt, varde=varde, enhet=enhet,
                                     kalla=_kalla(citat)))


def test_en_jamforelse_med_enhet_pa_bada_sidor_domer():
    behov = _finns("nyttolast", 12.5, "kg", "Payload 12.5 kg")
    tak = _finns("nyttolast", 180, "kg", "660-180/3.15 180 kg")
    d = TD.rymmer(behov, tak)
    assert d.utfall == TD.RYMS
    assert not d.avstar
    # Takregeln skrivs ut VARJE gång, aldrig som en fotnot man kan missa.
    assert "TAK" in d.text()
    assert "verktygets" in d.text()


def test_jamforelsen_raknar_om_mellan_enheter_inom_samma_storhet():
    behov = _finns("rackvidd", 2000, "mm", "reach 2000 mm")
    tak = _finns("rackvidd", 2.65, "m", "6700-235 2.65 m 235 kg")
    assert TD.rymmer(behov, tak).utfall == TD.RYMS
    behov = _finns("rackvidd", 3000, "mm", "reach 3000 mm")
    assert TD.rymmer(behov, tak).utfall == TD.RYMS_INTE


def test_en_jamforelse_dar_ena_sidan_saknar_enhet_avstar():
    """DET TRASIGA FALLET: ett tal med källa mot ett utan.

    Utfallet får inte vara en dom. `12,0` mot `180` är två tal, inte en
    jämförelse — och en grind som ändå svarar har gett ett fel som ser ut som
    ett svar.
    """
    behov = _finns("nyttolast", 12.5, "kg", "Payload 12.5 kg")
    tak = TD.enhet_saknas("nyttolast", "180",
                          "model.xml deklarerar talet och ingenting mer")
    d = TD.rymmer(behov, tak)
    assert d.avstar
    assert d.utfall == TD.AVSTAR
    assert "fel som ser ut som ett svar" in d.skal


def test_en_jamforelse_dar_ena_sidan_saknas_avstar_och_sager_det():
    behov = _finns("nyttolast", 12.5, "kg", "Payload 12.5 kg")
    tak = TD.saknas("nyttolast", "ingen kalla bar faltet")
    d = TD.rymmer(behov, tak)
    assert d.avstar
    assert "saknas i alla kallor" in d.skal
    assert "AVSTAR" in d.text()


def test_tva_olika_storheter_gar_inte_att_jamfora():
    behov = _finns("nyttolast", 5, "kg", "Payload 5 kg")
    tak = _finns("rackvidd", 900, "mm", "Reach 900 mm")
    assert TD.rymmer(behov, tak).avstar


# ---------------------------------------------------------------------------
# 7. Korpusen: fail-closed, och ingen granne fyller någon annans fält
# ---------------------------------------------------------------------------

def test_en_saknad_korpuskatalog_kastar_i_stallet_for_att_bli_tom(tmp_path):
    """DET TRASIGA FALLET: en källa som inte går att nå blir ett tyst tomt fält.

    En tom korpus hade gjort varje fält till `saknas` utan att någon sett att
    källan var borta — berikningen hade sett ut att ha kört.
    """
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Korpus.las(str(tmp_path / "finns-inte"))
    assert "far inte bli en tom korpus" in str(fel.value)


def test_en_tom_korpuskatalog_kastar_ocksa(tmp_path):
    with pytest.raises(TD.Tillverkarfel):
        TD.Korpus.las(str(tmp_path))


def test_en_trasig_korpusfil_kastar(tmp_path):
    (tmp_path / "a.json").write_text("{ inte json", encoding="utf-8")
    with pytest.raises(TD.Tillverkarfel) as fel:
        TD.Korpus.las(str(tmp_path))
    assert "gar inte att lasa" in str(fel.value)


def _skriv_korpus(tmp_path, poster):
    (tmp_path / "a.json").write_text(
        json.dumps({"poster": poster}, ensure_ascii=False), encoding="utf-8")
    return TD.Korpus.las(str(tmp_path))


def _post(modell, vc_namn, varde=5):
    return {
        "modell": modell, "tillverkare": "Provtillverkaren",
        "vc_namn": list(vc_namn),
        "uppgifter": {"nyttolast": {
            "varde": varde, "enhet": "kg",
            "kalla": {"url": "https://example.invalid/a.pdf",
                      "hamtad": "2026-09-05", "sha256": SHA,
                      "citat": "Payload %g kg" % varde}}},
        "ej_belagda": {"rackvidd": "bladet anger ingen rackvidd"},
    }


def test_uppslaget_pa_biblioteksnamn_ar_exakt_och_fyller_ingen_granne(tmp_path):
    """Två robotar som heter nästan likadant är två robotar."""
    k = _skriv_korpus(tmp_path, [_post("IRB 1200-5/0.9", ["IRB 1200-5/0.9"], 5)])
    assert k.for_vc_namn("IRB 1200-5/0.9") is not None
    # Gen2 är en annan komponent i biblioteket, med en annan räckvidd.
    assert k.for_vc_namn("IRB 1200-5/0.9 Gen2") is None
    assert k.for_vc_namn("IRB 1200-7/0.7") is None


def test_tva_modeller_som_gor_ansprak_pa_samma_biblioteksnamn_kastar(tmp_path):
    """TRASIG FIXTUR: ett namn som pekar på två datablad fyller den ena med
    den andras tal, och det är exakt den felklassen som ska vara omöjlig."""
    with pytest.raises(TD.Tillverkarfel) as fel:
        _skriv_korpus(tmp_path, [_post("A", ["IRB 660"], 180),
                                 _post("B", ["IRB 660"], 250)])
    assert "gor tva modeller anspraak pa" in str(fel.value)


def test_ett_falt_som_bade_ar_belagt_och_ej_belagt_kastar(tmp_path):
    p = _post("A", ["X"])
    p["ej_belagda"]["nyttolast"] = "bladet anger ingen nyttolast"
    with pytest.raises(TD.Tillverkarfel) as fel:
        _skriv_korpus(tmp_path, [p])
    assert "bade som belagd och ej belagd" in str(fel.value)


def test_ett_ej_belagt_falt_utan_skal_kastar(tmp_path):
    p = _post("A", ["X"])
    p["ej_belagda"]["rackvidd"] = ""
    with pytest.raises(TD.Tillverkarfel):
        _skriv_korpus(tmp_path, [p])


def test_ett_ej_belagt_falt_blir_saknas_med_skalet_utskrivet(tmp_path):
    k = _skriv_korpus(tmp_path, [_post("A", ["X"])])
    s = k.for_vc_namn("X").svar("rackvidd")
    assert s.lage == TD.SAKNAS
    assert "bladet anger ingen rackvidd" in s.skal


# ---------------------------------------------------------------------------
# 8. Berikningen: tre källor, och bara den tredje kan ge en enhet
# ---------------------------------------------------------------------------

def test_tillverkarens_datablad_ger_finns_katalogfaltet_ger_enhet_saknas(tmp_path):
    k = _skriv_korpus(tmp_path, [_post("A", ["X"], 5)])
    blad = _Attrappblad("X", {"maxpayload": "5", "reach": "900"})
    svar = TD.berika(blad, k, falt=("nyttolast", "rackvidd"))
    # Nyttolasten finns i korpusen -> finns, med enhet och källa.
    assert svar["nyttolast"].lage == TD.FINNS
    assert svar["nyttolast"].enhet == "kg"
    assert svar["nyttolast"].kalla.url.startswith("https://")
    # Räckvidden gör den inte -> katalogfältet, ordagrant, utan enhet.
    assert svar["rackvidd"].lage == TD.ENHET_SAKNAS
    assert svar["rackvidd"].ordagrant == "900"


def test_en_komponent_utan_datablad_och_utan_katalogfalt_star_som_saknas(tmp_path):
    k = _skriv_korpus(tmp_path, [_post("A", ["X"], 5)])
    blad = _Attrappblad("Nagon annan komponent", {})
    svar = TD.berika(blad, k, falt=("nyttolast",))["nyttolast"]
    assert svar.lage == TD.SAKNAS
    assert "korpusen saknar modellen" in svar.skal


def test_berikningen_utan_korpus_ger_aldrig_finns():
    """VC:s två filer kan inte ge en enhet, hur fyllda de än är."""
    blad = _Attrappblad("X", {"maxpayload": "180", "reach": "3150"})
    svar = TD.berika(blad, korpus=None)
    assert {s.lage for s in svar.values()} <= {TD.ENHET_SAKNAS, TD.SAKNAS}
    assert TD.FINNS not in {s.lage for s in svar.values()}


def test_databladets_katalogfalt_bar_de_ordagranna_strangarna(tmp_path):
    """`nyttolast_kg` bär en enhet i sitt eget namn som filen aldrig sa.

    `katalogfalt` är samma tal utan den påhängda enheten och utan
    float-omvandlingen — och det är det `enhet_saknas` visar.
    """
    import zipfile
    vcmx = tmp_path / "a.vcmx"
    with zipfile.ZipFile(vcmx, "w") as z:
        z.writestr("model.xml",
                   '<Properties><Property name="Name">Provet</Property>'
                   '<Property name="MaxPayload">0</Property></Properties>')
        z.writestr("component.rsc", 'Node "rSimResource"\n{\nName "Provet"\n}\n')
    blad = KD.las(str(vcmx))
    assert blad.katalogfalt["maxpayload"] == "0"
    # Den gamla vägen ger en float vars NAMN påstår kilo.
    assert blad.nyttolast_kg == 0.0
    svar = TD.berika(blad, korpus=None, falt=("nyttolast",))["nyttolast"]
    assert svar.lage == TD.ENHET_SAKNAS and svar.ordagrant == "0"


# ---------------------------------------------------------------------------
# 9. Den levererade korpusen på disk
# ---------------------------------------------------------------------------

def test_den_levererade_korpusen_gar_att_lasa_och_bar_sina_grindar():
    """Korpusen läses genom samma konstruktorer som byggde den.

    Att den går att läsa BETYDER att varje uppgift klarar enhetsgrinden på
    nytt: `Uppgift.fran_json` kör `__post_init__`.
    """
    k = TD.Korpus.las()
    assert len(k) >= 20
    belagda = sum(len(b.uppgifter) for b in k.blad)
    assert belagda >= 40
    for b in k.blad:
        for falt, u in b.uppgifter.items():
            assert u.kalla.url.startswith("https://")
            assert u.kalla.citat.strip()
            assert TD.normalisera(u.kalla.citat) in TD.normalisera(u.kalla.utdrag)


def test_varje_falt_i_korpusen_ar_antingen_belagt_eller_har_ett_skal():
    """Ingen tystnad. Ett fält som varken är belagt eller förklarat är en
    lucka som ser ut som ett svar."""
    k = TD.Korpus.las()
    tysta = []
    for b in k.blad:
        for falt in TD.FALT:
            if falt not in b.uppgifter and falt not in b.ej_belagda:
                tysta.append("%s/%s" % (b.modell, falt))
    assert not tysta, "fält utan svar och utan skäl: %s" % tysta


def test_korpusens_citat_star_i_utdragen_utan_natet_och_utan_cachen():
    """De två första grindlagren kör utan nät. Det tredje kräver cachen och
    körs i `tests/protocol/kor_m107_bygg_korpus.py`."""
    k = TD.Korpus.las()
    assert TD.verifiera(k, kraev_cache=False) == []


def test_ingen_korpuspost_binder_ett_biblioteksnamn_som_inte_finns():
    """En bindning till ett namn biblioteket inte bär är en bindning till
    ingenting, och den syns aldrig som ett fel om ingen slår upp den."""
    ix = os.path.join(_ROT, "bank", "katalog_index.json")
    assert os.path.exists(ix)          # bara för att visa att banken finns
    k = TD.Korpus.las()
    # Varje vc_namn ska vara unikt och icke-tomt; att det FINNS på disk mäts i
    # tests/protocol/kor_m107_berikningen.py, som har biblioteket.
    sedda = set()
    for b in k.blad:
        for n in b.vc_namn:
            assert n.strip(), "%s bar ett tomt vc_namn" % b.modell
            assert n.lower() not in sedda
            sedda.add(n.lower())
