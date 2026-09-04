# -*- coding: utf-8 -*-
"""M-52: reparationsslingan, och de tre sätt den kan bli en falsk grön.

Slingan i `svc/vc_assist_svc/plc/reparation.py` är byggd runt tre doktriner ur
`docs/spec/50_grindar.md` och `61_st_generering.md`. En doktrin som bara står i
en docstring är en bön. Provet nedan gör var och en till en grind, och varje
grind har sin **trasiga fixtur**:

1. **Grindens ord går vidare ordagrant.** Trasig fixtur: en inramning som
   skriver om domen — och en som bara normaliserar radbrytningarna, vilket är
   den variant som ser oskyldig ut. Båda ska fällas.
2. **Slingan har ett tak.** Trasig fixtur: `max_varv=None`, `0`, `-1` och ett
   tal över `ABSOLUT_TAK`. Alla ska avvisas i konstruktorn, före första varvet.
3. **En låst slinga är inte ett nått tak.** Trasig fixtur: en modell som svarar
   med samma kropp två varv i rad. Utfallet ska bli `LAST`, inte `TAK`.

Modelledet är en attrapp genomgående. Attrappen har ingen kanal ut och kan
inte få en.

beskriver: svc/vc_assist_svc/plc/reparation.py, bank/reparationsbank.py
"""
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
for _p in (os.path.join(_ROT, "bank"), os.path.join(_ROT, "svc")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import reparationsbank as RB  # noqa: E402
from vc_assist_svc.harness.modell import Meddelande, Modell, Modellsvar  # noqa: E402
from vc_assist_svc.plc import reparation as R  # noqa: E402
from vc_assist_svc.plc.signalkarta import (FRAN_PLC, TILL_PLC,  # noqa: E402
                                           karta_av_rader)
from vc_assist_svc.plc.skelett import Skelett  # noqa: E402


# ------------------------------------------------------------ uppsättningen

RATT_KROPP = "DON := GIVARE;"
FEL_KROPP = "DON := NOT GIVARE;"
ANNAN_FEL_KROPP = "DON := GIVARE AND GIVARE;"

# Grindens egen utdata i provet. Formen är grindarnas gemensamma: `[kod/Fklass]`.
GRINDORD = ("EGEN GRIND EJ GODKAND\n"
            "  rad 1: [OMVANT/F5] DON drivs omvänt mot givaren\n"
            "  rad 1: [ANNAT/F8] och förreglingen saknas")


def karta():
    return karta_av_rader("PROV", [
        ("plc", "sensor", "GIVARE", "BOOL", TILL_PLC, "%IX0.0"),
        ("plc", "aktuator", "DON", "BOOL", FRAN_PLC, "%QX0.0"),
    ])


def skelett():
    return Skelett.av_karta(karta())


class Provgrind(R.Grindsteg):
    """Godkänner exakt en kropp. Allt annat får grindens egna ord."""

    namn = "provgrind"

    def __init__(self, ratt=RATT_KROPP, utdata=GRINDORD):
        self.ratt = ratt
        self.utdata = utdata
        self.sedda = []

    def doma(self, st_kalla):
        self.sedda.append(st_kalla)
        if self.ratt in st_kalla:
            return R.Grinddom(grind=self.namn, ok=True)
        return R.Grinddom(grind=self.namn, ok=False, utdata=self.utdata,
                          koder=R.koder_ur(self.utdata),
                          klasser=R.klasser_ur(self.utdata))


class Manusmodell(Modell):
    """En modell med ett manus. Ingen kanal ut, ingen url, ingen socket."""

    leverantor = "attrapp"

    def __init__(self, kroppar):
        self.kroppar = list(kroppar)
        self.i = 0
        self.sedda_historiker = []

    def svara(self, systemprompt, meddelanden, verktyg):
        self.sedda_historiker.append(tuple(meddelanden))
        if self.i >= len(self.kroppar):
            return Modellsvar(text="")
        kropp = self.kroppar[self.i]
        self.i += 1
        return Modellsvar(text=kropp)


def slinga(lage=R.LAGE_RENT, max_varv=R.MAX_VARV, grindar=None, **kw):
    return R.Reparationsslinga(skelett(), grindar or [Provgrind()],
                               lage=lage, max_varv=max_varv, **kw)


# --------------------------------------------------- 1: ordagrant, tecken för tecken

def test_grindens_ord_nar_modellen_tecken_for_tecken():
    """Strängen som når modellen jämförs med grindens `utdata`, tecken för
    tecken. Det är hela doktrinen ur 50_grindar.md, mätt i stället för bedd."""
    grind = Provgrind()
    modell = Manusmodell([FEL_KROPP, RATT_KROPP])
    protokoll = slinga(grindar=[grind]).kor(modell, "uppgiften")

    assert protokoll.utfall == R.UTFALL_LOST
    andra_varvet = modell.sedda_historiker[1]
    grindmeddelanden = [m for m in andra_varvet if m.roll == "grind"]
    assert len(grindmeddelanden) == 1
    text = grindmeddelanden[0].text
    assert GRINDORD in text, (
        "grindens utdata nådde inte modellen ordagrant; den fick %r" % text)
    # Tecken för tecken, inte "ungefär": varje rad ur grinden ska stå orörd.
    for rad in GRINDORD.splitlines():
        assert rad in text


def test_grindens_ord_ligger_orort_i_protokollet():
    grind = Provgrind()
    protokoll = slinga(grindar=[grind]).kor(
        Manusmodell([FEL_KROPP, RATT_KROPP]), "uppgiften")
    assert protokoll.varv[0].fallande[0].utdata == GRINDORD


def test_en_inramning_som_skriver_om_domen_falls():
    """TRASIG FIXTUR 1a. En omskrivning är precis det fel som underkände 2 av 4
    medan ögat visade 4 av 4."""
    def omskrivande(domar):
        return "Grinden var inte nöjd med din kod. Se över logiken."

    with pytest.raises(R.Reparationsfel) as fel:
        slinga(inramning=omskrivande).kor(
            Manusmodell([FEL_KROPP, RATT_KROPP]), "uppgiften")
    assert "ordagrant" in str(fel.value)


def test_en_inramning_som_bara_normaliserar_radbrytningar_falls_ocksa():
    """TRASIG FIXTUR 1b. Den varianten ser oskyldig ut, och är det inte:
    grinden pekar ut rader, och en hopslagen utdata pekar inte ut något."""
    def normaliserande(domar):
        return " ".join(" ".join(d.utdata.split()) for d in domar)

    with pytest.raises(R.Reparationsfel):
        slinga(inramning=normaliserande).kor(
            Manusmodell([FEL_KROPP, RATT_KROPP]), "uppgiften")


def test_kontrollera_ordagrant_slapper_igenom_en_inramning():
    """Kontrollen får inte vara så sträng att den förbjuder en inramning: den
    ska förbjuda omskrivning, inte omgivning."""
    domar = (R.Grinddom(grind="g", ok=False, utdata=GRINDORD),)
    R.kontrollera_ordagrant(R.standardinramning(domar), domar)


def test_standardinramningen_bar_bade_inledning_och_grindens_ord():
    domar = (R.Grinddom(grind="g", ok=False, utdata=GRINDORD),)
    text = R.standardinramning(domar)
    assert R.INLEDNING in text and R.AVSLUTNING in text and GRINDORD in text


# ----------------------------------------------------------------- 2: taket

@pytest.mark.parametrize("tak", [None, 0, -1, R.ABSOLUT_TAK + 1, 2.5, "fyra"])
def test_en_slinga_utan_giltigt_tak_gar_inte_att_bygga(tak):
    """TRASIG FIXTUR 2. En obegränsad slinga döljer att uppgiften är olöslig
    (61_st_generering.md), och ett tak som får vara godtyckligt stort är samma
    sak som inget tak."""
    with pytest.raises(R.Reparationsfel):
        slinga(max_varv=tak)


def test_taket_nas_och_rapporteras_som_tak():
    modell = Manusmodell([FEL_KROPP, ANNAN_FEL_KROPP, FEL_KROPP + " ",
                          ANNAN_FEL_KROPP + " "])
    protokoll = slinga(max_varv=4).kor(modell, "uppgiften")
    assert protokoll.utfall == R.UTFALL_TAK
    assert len(protokoll.varv) == 4
    assert not protokoll.lost


def test_taket_gor_en_oloslig_uppgift_synlig_i_stallet_for_evig():
    """Ingen kropp i manuset godkänns. Slingan ska sluta, inte snurra."""
    modell = Manusmodell(["A%d;" % n for n in range(50)])
    protokoll = slinga(max_varv=3).kor(modell, "uppgiften")
    assert protokoll.utfall == R.UTFALL_TAK
    assert len(protokoll.varv) == 3


def test_max_varv_har_harkomst_i_koden():
    """Konstanten får inte bli ett tycke igen."""
    kalla = open(os.path.join(_ROT, "svc", "vc_assist_svc", "plc",
                              "reparation.py"), encoding="utf-8").read()
    for rad in kalla.splitlines():
        if rad.startswith("MAX_VARV ") or rad.startswith("ABSOLUT_TAK "):
            assert "M-52" in rad, rad


# ----------------------------------------------------------- 3: låst slinga

def test_samma_kropp_tva_varv_i_rad_upptacks_som_last():
    """TRASIG FIXTUR 3. Grindarna är rena funktioner av kroppen: samma kropp
    ger samma dom, och slingan kan inte komma vidare."""
    modell = Manusmodell([FEL_KROPP, FEL_KROPP, RATT_KROPP])
    protokoll = slinga(max_varv=4).kor(modell, "uppgiften")
    assert protokoll.utfall == R.UTFALL_LAST
    assert protokoll.utfall != R.UTFALL_TAK
    assert protokoll.varv[-1].upprepar == 1
    assert not protokoll.varv[-1].domar, (
        "den upprepade kroppen dömdes en gång till; domen var redan känd")


def test_en_kropp_som_kommer_igen_efter_en_annan_ar_ocksa_last():
    """A, B, A är en cykel. Att bara jämföra med FÖREGÅENDE varv hade missat
    den, och en cykel är lika låst som en upprepning."""
    modell = Manusmodell([FEL_KROPP, ANNAN_FEL_KROPP, FEL_KROPP, RATT_KROPP])
    protokoll = slinga(max_varv=4).kor(modell, "uppgiften")
    assert protokoll.utfall == R.UTFALL_LAST
    assert protokoll.varv[-1].upprepar == 1


def test_tystnad_ar_inte_ett_godkannande():
    protokoll = slinga().kor(Manusmodell([]), "uppgiften")
    assert protokoll.utfall == R.UTFALL_TYSTNAD
    assert not protokoll.lost


# -------------------------------------------------------- lägena, och bara de

def test_rent_lage_visar_skelettet_och_senaste_domen_men_inga_forsok():
    modell = Manusmodell([FEL_KROPP, ANNAN_FEL_KROPP, RATT_KROPP])
    slinga(lage=R.LAGE_RENT, max_varv=4).kor(modell, "uppgiften")
    tredje = modell.sedda_historiker[2]
    roller = [m.roll for m in tredje]
    assert roller == ["uppgift", "grind"], roller
    assert all(m.text not in (FEL_KROPP, ANNAN_FEL_KROPP) for m in tredje)


def test_historiklage_visar_varje_tidigare_forsok_och_dess_dom():
    modell = Manusmodell([FEL_KROPP, ANNAN_FEL_KROPP, RATT_KROPP])
    slinga(lage=R.LAGE_HISTORIK, max_varv=4).kor(modell, "uppgiften")
    tredje = modell.sedda_historiker[2]
    roller = [m.roll for m in tredje]
    assert roller == ["uppgift", "modell", "grind", "modell", "grind"], roller
    assert [m.text for m in tredje if m.roll == "modell"] == [FEL_KROPP,
                                                              ANNAN_FEL_KROPP]


def test_lagena_skiljer_sig_i_precis_en_sak():
    """Första varvet är identiskt i båda lägena. Skiljer det sig mäter en
    jämförelse mellan lägena något annat än lägena."""
    ren, hist = Manusmodell([FEL_KROPP]), Manusmodell([FEL_KROPP])
    slinga(lage=R.LAGE_RENT, max_varv=1).kor(ren, "uppgiften")
    slinga(lage=R.LAGE_HISTORIK, max_varv=1).kor(hist, "uppgiften")
    assert ren.sedda_historiker[0] == hist.sedda_historiker[0]


def test_okant_lage_avvisas():
    with pytest.raises(R.Reparationsfel):
        slinga(lage="halvrent")


# ------------------------------------------------- ingen grind, ingen tystnad

def test_en_slinga_utan_grindar_gar_inte_att_bygga():
    with pytest.raises(R.Reparationsfel):
        R.Reparationsslinga(skelett(), [], max_varv=2)


def test_en_grind_som_inte_kordes_far_inte_saga_godkant():
    with pytest.raises(R.Reparationsfel):
        R.Grinddom(grind="g", ok=True, kord=False)


def test_grindsteg_utan_doma_kastar_i_stallet_for_att_slappa_igenom():
    with pytest.raises(NotImplementedError):
        R.Grindsteg().doma("PROGRAM P\nEND_PROGRAM\n")


def test_slingan_sager_aldrig_guld():
    """50_grindar.md: endast en körning i VC befordrar kandidat till guld."""
    protokoll = slinga().kor(Manusmodell([RATT_KROPP]), "uppgiften")
    assert protokoll.lost
    assert protokoll.niva == "kandidat"


# ------------------------------------------------------------- ramgrinden

def test_ett_svar_som_ror_ramen_ger_skelettets_egna_ord():
    """Skelettet är också en grind, och dess ord går vidare som varje annans."""
    modell = Manusmodell(["PROGRAM PROV\nVAR END_VAR\nEND_PROGRAM\n",
                          RATT_KROPP])
    protokoll = slinga(max_varv=3).kor(modell, "uppgiften")
    assert protokoll.utfall == R.UTFALL_LOST
    forsta = protokoll.varv[0].fallande[0]
    assert forsta.grind == "skelett"
    assert forsta.klasser == (R.KLASS_RAM,)
    grindtext = [m.text for m in modell.sedda_historiker[1]
                 if m.roll == "grind"][0]
    assert forsta.utdata in grindtext


# ------------------------------------------ stationssteget, grind 1 till 4

def test_stationssteget_slapper_en_riktig_kropp_och_faller_en_okand_tagg():
    steg = R.Stationssteg(karta())
    sk = skelett()
    assert steg.doma(sk.las_svar(RATT_KROPP)).ok
    dom = steg.doma(sk.las_svar("DONX := GIVARE;"))
    assert not dom.ok
    assert "ODEKLARERAD" in dom.koder
    assert "F4" in dom.klasser


def test_stationssteget_redovisar_de_grindar_det_hoppade_over():
    """En överhoppad grind ska synas med sitt EGET skäl. En grind som blir
    billig slutar mäta sin egen storhet."""
    steg = R.Stationssteg(karta())
    steg.doma(skelett().las_svar(RATT_KROPP))
    ej = steg.ej_korda()
    assert "kompilering" in ej and "anropsvalidering" in ej
    assert "kompilatorn" in ej["kompilering"]


def test_stationssteget_utan_grindar_gar_inte_att_bygga():
    with pytest.raises(R.Reparationsfel):
        R.Stationssteg(karta(), grindar=())


def test_stationssteget_avvisar_en_okand_grind():
    with pytest.raises(R.Reparationsfel):
        R.Stationssteg(karta(), grindar=("ogat",))


def test_klasser_lases_ur_grindens_egen_markning():
    assert R.klasser_ur("rad 1: [ODEKLARERAD/F4] x") == ("F4",)
    assert R.klasser_ur("[flank:en_puls/F15] y") == ("F15",)
    assert R.klasser_ur("[OATKOMLIG/-] z") == ()
    assert R.koder_ur("[flank:en_puls/F15] y") == ("flank:en_puls",)


# --------------------------------------------------- bänken: läckan och talen

def test_uppgiftstexten_bar_inte_referenslosningens_kropp():
    """En slinga som konvergerar för att facit läckt in i prompten mäter
    avskrift. Samma läcka som tests/enhet/test_domare.py provar, men mot den
    text slingan faktiskt skickar — prompt PLUS skelett."""
    for post in RB.uppgifter_med_sparfacit():
        upps = RB.bygg_uppsattning(post)
        lackt = RB.lackta_rader(upps["prompt"], upps["referens"])
        assert not lackt, ("%s: %d rader ur referensens kropp står i prompten, "
                           "t.ex. %r" % (post["task_id"], len(lackt), lackt[:1]))


def test_lackagekontrollen_hittar_en_planterad_lacka():
    """TRASIG FIXTUR för läckkontrollen själv. Utan den här raden vore
    provet ovan en kontroll som aldrig fällt något."""
    post = RB.uppgifter_med_sparfacit()[0]
    upps = RB.bygg_uppsattning(post)
    ren = RB._utan_kommentarer(upps["referens"])
    rad = [r.strip() for r in ren.splitlines()
           if len(r.strip()) > RB.MINSTA_LACKRAD][0]
    assert rad in RB.lackta_rader(upps["prompt"] + "\n" + rad,
                                  upps["referens"])


def test_attrappen_far_ingen_lagesflagga():
    """Attrappen ska inte kunna behandla lägena olika. Kan den det mäter
    jämförelsen attrappen och inte slingan."""
    import inspect
    kalla = inspect.getsource(RB.AttrappReparator.svara)
    for ord_ in ("rent", "historik", "lage"):
        assert ord_ not in kalla, (
            "AttrappReparator nämner %r; då vet den vilket läge den kör i" % ord_)


def test_en_korning_ger_samma_tal_tva_ganger():
    """Determinism. Utan den går två körningar inte att jämföra alls."""
    post = [p for p in RB.uppgifter_med_sparfacit()
            if p["task_id"] == "T-07"][0]
    forsta = [(k.namn, k.lage, k.utfall, k.varv)
              for k in RB.kor_uppgift(post)]
    andra = [(k.namn, k.lage, k.utfall, k.varv) for k in RB.kor_uppgift(post)]
    assert forsta == andra


def test_bada_lagena_kors_over_samma_uppgifter_och_samma_tak():
    """En jämförelse där lägena fått olika material mäter materialet."""
    post = [p for p in RB.uppgifter_med_sparfacit()
            if p["task_id"] == "T-07"][0]
    korningar = RB.kor_uppgift(post)
    rent = [k.namn for k in korningar if k.lage == R.LAGE_RENT]
    hist = [k.namn for k in korningar if k.lage == R.LAGE_HISTORIK]
    assert rent == hist and rent
    assert len(set(k.protokoll.max_varv for k in korningar)) == 1


def test_sparfacitsteget_citerar_domarens_egna_brister():
    """Steget skriver domarens kod och text, inte en sammanfattning."""
    post = [p for p in RB.uppgifter_med_sparfacit()
            if p["task_id"] == "T-07"][0]
    upps = RB.bygg_uppsattning(post)
    steg = RB.Sparfacitsteg(post)
    mb = upps["motbevis"][0][1]
    dom = steg.doma(upps["skelett"].las_svar(mb))
    assert not dom.ok
    import domare as D
    egen = D.dom(post, upps["skelett"].las_svar(mb))
    for b in egen.brister:
        assert b.kod in dom.utdata
        assert b.text.strip().splitlines()[0] in dom.utdata


def test_sparfacitsteget_slapper_referensen():
    """Ett facit ingen kan uppfylla fäller alla och ser ut som en svår bänk."""
    post = [p for p in RB.uppgifter_med_sparfacit()
            if p["task_id"] == "T-07"][0]
    upps = RB.bygg_uppsattning(post)
    assert RB.Sparfacitsteg(post).doma(
        upps["skelett"].las_svar(upps["referens"])).ok


def test_sparklassen_foljer_82_felklasser():
    assert RB.sparklass("flank:en_puls_per_detalj") == "F15"
    assert RB.sparklass("invariant:ingen_rorelse@sekv") == "F8"
    assert RB.sparklass("tolkfel:sekv") == "F1"
    assert RB.sparklass("sekv@200ms:DON") == "F5"


def test_orakeltabellen_kan_bara_bara_ett_svar_per_signatur():
    """Kollisionen är mekanismen som skiljer lägena åt, och den ska vara
    synlig i tabellen och inte gömd i en slump."""
    class Tvasteg(R.Grindsteg):
        namn = "tva"

        def doma(self, st_kalla):
            if "RATT" in st_kalla:
                return R.Grinddom(grind=self.namn, ok=True)
            return R.Grinddom(grind=self.namn, ok=False,
                              utdata="[X/F5] samma klass varje gang",
                              klasser=("F5",))

    sk = skelett()
    repertoar = ["A := GIVARE;", "B := GIVARE;", "(*RATT*)\nDON := GIVARE;"]
    tabell = RB.bygg_tabell([Tvasteg()], sk, repertoar)
    assert tabell == {("F5",): 1}, tabell
