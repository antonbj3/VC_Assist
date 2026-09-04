# -*- coding: utf-8 -*-
"""L0/L1 for fas 10: installationen. Kraver varken VC eller Wine.

Grinden i docs/spec/70_faser.md ar "Ren maskin: klona, installera, kor.
Fungerar utan handpalaggning." Den gar inte att prova pa en ren maskin
harifran, men de tre delarna av den gar:

  1. hittar installationen ratt mapp, aven nar det finns flera versioner,
     ingen alls, eller en mapp som inte gar att lasa
  2. lagger den ratt filer dar, idempotent, och FALLER pa en trasig kalla
  3. tar avinstallationen bort exakt det den lade dit och ingenting annat

Hela provningen sker mot en attrappmapp i tmp_path. Windows-vagen provas
genom att injicera en Windows-miljo - det ar en provning av LOGIKEN, inte av
Windows. Windows ar oprovat, och star sa i README.md.

Kor: cd ~/projects/VC_Assist && python3 -m pytest tests/enhet/test_install.py -q
"""
import hashlib
import json
import os
import sys

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROT not in sys.path:
    sys.path.insert(0, _ROT)

from install import installera as cli          # noqa: E402
from install import paket, upptackt            # noqa: E402

FORETAG = "Visual Components"


# --------------------------------------------------------------------------
# Attrapper
# --------------------------------------------------------------------------

def bygg_vc(dokumentrot, version, nivaer=("Python 2",), foretag=FORETAG):
    """``<dokumentrot>/<foretag>/<version>/My Commands/<niva>``."""
    my_commands = os.path.join(str(dokumentrot), foretag, version, "My Commands")
    os.makedirs(my_commands, exist_ok=True)
    for niva in nivaer:
        os.makedirs(os.path.join(my_commands, niva), exist_ok=True)
    return my_commands


def bygg_prefix(hem, namn, dokument=None):
    """Ett wine-prefix. ``dokument`` gor Documents till en symlank (M-02)."""
    anvandare = os.path.join(str(hem), namn, "drive_c", "users", "anton")
    os.makedirs(anvandare, exist_ok=True)
    dokumentmapp = os.path.join(anvandare, "Documents")
    if dokument is None:
        os.makedirs(dokumentmapp, exist_ok=True)
    else:
        os.symlink(str(dokument), dokumentmapp)
    return dokumentmapp


def bygg_program(hem, prefixnamn, produkt, nivaer=("Python 2",)):
    """En VC-installation pa disk, kannetecknad av Python N/Auto Complete/api.xml."""
    rot = os.path.join(str(hem), prefixnamn, "drive_c", "Program Files",
                       FORETAG, produkt)
    for niva in nivaer:
        auto = os.path.join(rot, niva, "Auto Complete")
        os.makedirs(auto, exist_ok=True)
        with open(os.path.join(auto, "api.xml"), "w") as f:
            f.write("<api/>")
    return rot


def linuxmiljo(hem, **kw):
    return upptackt.Miljo(plattform="linux", hem=str(hem), env={}, **kw)


def windowsmiljo(hem, personal=None, env=None):
    return upptackt.Miljo(plattform="win32", hem=str(hem),
                          env=env if env is not None else {},
                          skalmapp=(lambda: str(personal)) if personal else (lambda: None))


def trad(rot):
    """Hela mappen som {relativ sokvag: sha256 eller '<mapp>'}. For fore/efter."""
    ut = {}
    for mapp, mappar, filer in os.walk(str(rot)):
        for namn in mappar:
            rel = os.path.relpath(os.path.join(mapp, namn), str(rot))
            ut[rel] = "<mapp>"
        for namn in filer:
            sokvag = os.path.join(mapp, namn)
            rel = os.path.relpath(sokvag, str(rot))
            with open(sokvag, "rb") as f:
                ut[rel] = hashlib.sha256(f.read()).hexdigest()
    return ut


def kalla_kopia(tmp_path, namn="kalla"):
    """En skrivbar kopia av det riktiga tillagget, att gora sonder."""
    import shutil
    mal = os.path.join(str(tmp_path), namn)
    shutil.copytree(paket.kallmapp(), mal,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return mal


ar_rot = hasattr(os, "geteuid") and os.geteuid() == 0
kraver_rattigheter = pytest.mark.skipif(
    os.name != "posix" or ar_rot,
    reason="rattighetsprovet kraver posix och en anvandare som inte ar root")


# --------------------------------------------------------------------------
# Versionsnummer: 4.10 ar nyare an 4.9
# --------------------------------------------------------------------------

def test_4_10_ar_nyare_an_4_9():
    """Lexikalisk sortering ger fel svar, och BADA mapparna finns pa maskinen."""
    assert upptackt.versionsnyckel("4.10") > upptackt.versionsnyckel("4.9")
    assert upptackt.versionsnyckel("5.0") > upptackt.versionsnyckel("4.10")


def test_okand_version_sorteras_sist():
    assert upptackt.versionsnyckel("Backup") < upptackt.versionsnyckel("1.0")
    assert upptackt.huvudversion("Backup") is None


def test_huvudversion_las_ur_namnet():
    assert upptackt.huvudversion("4.10") == 4
    assert upptackt.huvudversion("5.0") == 5


# --------------------------------------------------------------------------
# Sokningen
# --------------------------------------------------------------------------

def test_ingen_vc_installerad_ger_tom_lista(tmp_path):
    """Ingen VC alls: tom lista, ingen krasch, inget pahittat."""
    bygg_prefix(tmp_path, ".wine-tom")
    miljo = linuxmiljo(tmp_path)
    assert upptackt.vcmappar(miljo) == []
    assert upptackt.sok(miljo).vcmappar == []


def test_flera_versioner_rapporteras_alla_och_nyaste_forst(tmp_path):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    for version in ("4.9", "4.10", "5.0"):
        bygg_vc(dok, version)
    mappar = upptackt.vcmappar(linuxmiljo(tmp_path))
    assert [m.version for m in mappar] == ["5.0", "4.10", "4.9"]
    assert upptackt.valj_vcmapp(mappar).version == "5.0"
    assert upptackt.valj_vcmapp(mappar, "4.10").version == "4.10"
    assert upptackt.valj_vcmapp(mappar, "3.0") is None


def test_symlankade_dokumentmappar_slas_ihop(tmp_path):
    """M-02: ett kopierat prefix delar Documents med originalet via symlank.

    Den som inte loser upp lanken tror att den installerar i tva mappar och
    skriver i en. Har ska de bli EN rot med bada prefixen som kalla.
    """
    delad = os.path.join(str(tmp_path), "delade-dokument")
    os.makedirs(delad)
    bygg_vc(delad, "4.10")
    bygg_prefix(tmp_path, ".wine-vc", dokument=delad)
    bygg_prefix(tmp_path, ".wine-vc-test", dokument=delad)

    rotter = upptackt.dokumentrotter(linuxmiljo(tmp_path))
    assert len(rotter) == 1, [r.sokvag for r in rotter]
    assert len(rotter[0].kallor) == 2
    assert len(upptackt.vcmappar(linuxmiljo(tmp_path))) == 1


def test_egna_dokumentmappar_slas_inte_ihop(tmp_path):
    """Motsatsen till ovan: tva RIKTIGT skilda mappar ska forbli tva."""
    for namn in (".wine-vc", ".wine-vc-test"):
        bygg_vc(bygg_prefix(tmp_path, namn), "4.10")
    assert len(upptackt.dokumentrotter(linuxmiljo(tmp_path))) == 2
    assert len(upptackt.vcmappar(linuxmiljo(tmp_path))) == 2


def test_foretagsnamnet_ar_inte_hardkodat(tmp_path):
    """VC:s egen config har foretaget som variabel (%COMPANY%), sa vi soker."""
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, "4.10", foretag="Nagon Annan Leverantor")
    mappar = upptackt.vcmappar(linuxmiljo(tmp_path))
    assert [m.foretag for m in mappar] == ["Nagon Annan Leverantor"]


def test_wineprefix_kraver_drive_c(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), ".winealls-inte-ett-prefix"))
    bygg_prefix(tmp_path, ".wine-vc")
    prefix = [os.path.basename(p) for p, _k in upptackt.wineprefix(linuxmiljo(tmp_path))]
    assert prefix == [".wine-vc"]


def test_wineprefix_ur_miljovariabeln(tmp_path):
    bygg_vc(bygg_prefix(tmp_path, "annat-prefix"), "4.10")
    miljo = upptackt.Miljo(plattform="linux", hem=str(tmp_path),
                           env={"WINEPREFIX": os.path.join(str(tmp_path), "annat-prefix")})
    assert [m.version for m in upptackt.vcmappar(miljo)] == ["4.10"]


def test_sokningen_gar_inte_djupare_an_tva_nivaer(tmp_path):
    """En djupare sokning hittar sakerhetskopior och kostar tid pa en stor mapp."""
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(os.path.join(dok, "Sakerhetskopia"), "4.10")
    assert upptackt.vcmappar(linuxmiljo(tmp_path)) == []


@kraver_rattigheter
def test_olasbar_mapp_ger_varning_inte_krasch(tmp_path):
    """En mapp som finns men inte gar att lasa far inte falla hela sokningen.

    S9: den far inte heller forsvinna tyst - den ska sta i varningarna.
    """
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, "4.10")
    stangd = os.path.join(dok, "Stangd Mapp")
    os.makedirs(stangd)
    os.chmod(stangd, 0o000)
    try:
        res = upptackt.sok(linuxmiljo(tmp_path))
        assert [m.version for m in res.vcmappar] == ["4.10"]
        assert any("Stangd Mapp" in v for v in res.varningar), res.varningar
    finally:
        os.chmod(stangd, 0o700)


def test_windows_hittar_dokument_via_registret(tmp_path):
    """Personal-nyckeln behovs: ~/Documents kan vara omdirigerad till OneDrive.

    Detta provar LOGIKEN med en injicerad miljo. Ingen rad har ar en matning
    pa Windows - det star i README.md, och det gors inget annat ansprak.
    """
    onedrive = os.path.join(str(tmp_path), "OneDrive", "Documents")
    os.makedirs(onedrive)
    bygg_vc(onedrive, "4.10")
    miljo = windowsmiljo(tmp_path, personal=onedrive,
                         env={"USERPROFILE": str(tmp_path)})
    mappar = upptackt.vcmappar(miljo)
    assert [m.version for m in mappar] == ["4.10"]
    assert onedrive in mappar[0].my_commands


def test_windows_soker_inte_i_wineprefix(tmp_path):
    """Ett wine-prefix pa en Windows-maskin ar inte VC:s tillaggsmapp."""
    bygg_vc(bygg_prefix(tmp_path, ".wine-vc"), "4.10")
    miljo = windowsmiljo(tmp_path, env={"USERPROFILE": str(tmp_path)})
    assert upptackt.wineprefix(miljo) == []
    assert upptackt.vcmappar(miljo) == []


def test_windows_registerfel_blir_varning_inte_krasch(tmp_path):
    def sprucken():
        raise OSError("nyckeln finns inte")

    docs = os.path.join(str(tmp_path), "Documents")
    bygg_vc(docs, "4.10")
    miljo = upptackt.Miljo(plattform="win32", hem=str(tmp_path), env={},
                           skalmapp=sprucken)
    assert [m.version for m in upptackt.vcmappar(miljo)] == ["4.10"]
    assert any("registret" in v for v in miljo.varningar), miljo.varningar


def test_programinstallation_hittas_via_api_xml(tmp_path):
    """36_versioner.md: installationen gar att LASA utan licens.

    Det ar sa VC 5.0:s Python-niva ska kunna matas i stallet for gissas.
    """
    bygg_program(tmp_path, ".wine-vc", "Visual Components Premium 5.0",
                 nivaer=("Python 3",))
    bygg_prefix(tmp_path, ".wine-vc")
    funna = upptackt.programinstallationer(linuxmiljo(tmp_path))
    assert len(funna) == 1
    assert funna[0].pythonnivaer == ("Python 3",)
    assert funna[0].produkt == "Visual Components Premium 5.0"


def test_programmapp_utan_api_xml_raknas_inte(tmp_path):
    rot = os.path.join(str(tmp_path), ".wine-vc", "drive_c", "Program Files",
                       "Nagot", "Program", "Python 2")
    os.makedirs(rot)
    bygg_prefix(tmp_path, ".wine-vc")
    assert upptackt.programinstallationer(linuxmiljo(tmp_path)) == []


# --------------------------------------------------------------------------
# Val av Python-niva
# --------------------------------------------------------------------------

def _vcmapp(tmp_path, version, nivaer):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, version, nivaer=nivaer)
    return upptackt.vcmappar(linuxmiljo(tmp_path))[0]


def test_enda_nivan_pa_disk_valjs(tmp_path):
    val = upptackt.valj_pythonniva(_vcmapp(tmp_path, "4.10", ("Python 2",)))
    assert (val.namn, val.kalla, val.matt) == ("Python 2", "funnen", True)


def test_flera_nivaer_valjer_den_versionen_pekar_pa(tmp_path):
    m = _vcmapp(tmp_path, "4.10", ("Python 2", "Python 3"))
    val = upptackt.valj_pythonniva(m)
    assert val.namn == "Python 2"
    assert val.kalla == "funnen-flera"
    assert "Python 3" in val.motivering


def test_ingen_niva_pa_disk_harleds_ur_versionen(tmp_path):
    """Sista utvagen, och den marks som harledd - inte som funnen."""
    val = upptackt.valj_pythonniva(_vcmapp(tmp_path, "4.10", ()))
    assert (val.namn, val.kalla, val.matt) == ("Python 2", "harledd", True)


def test_vc5_harleds_till_python3_men_ar_INTE_matt(tmp_path):
    """36_versioner.md sager "sannolikt Python 3". Sannolikt ar inte matt."""
    val = upptackt.valj_pythonniva(_vcmapp(tmp_path, "5.0", ()))
    assert val.namn == "Python 3"
    assert val.matt is False
    assert upptackt.sokvagen_ar_matt("5.0", "Python 3") is False
    assert upptackt.sokvagen_ar_matt("4.10", "Python 2") is True


def test_python3_pa_disk_valjs_for_vc5(tmp_path):
    val = upptackt.valj_pythonniva(_vcmapp(tmp_path, "5.0", ("Python 3",)))
    assert (val.namn, val.kalla) == ("Python 3", "funnen")


def test_okand_version_utan_niva_kastar(tmp_path):
    """Varken funnen eller harledbar. Da gissar vi inte - vi kastar (36_versioner)."""
    m = _vcmapp(tmp_path, "Experimentell", ())
    with pytest.raises(upptackt.IngenNiva) as fel:
        upptackt.valj_pythonniva(m)
    assert "--python-niva" in str(fel.value)


def test_vald_niva_slar_allt(tmp_path):
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    val = upptackt.valj_pythonniva(m, "Python 3")
    assert (val.namn, val.kalla, val.matt) == ("Python 3", "vald", False)


def test_nivanamnet_normaliseras(tmp_path):
    """Anvandaren skriver inte alltid mellanslag och versal likadant."""
    assert upptackt.pythonnivanamn("python3") == "Python 3"
    assert upptackt.pythonnivanamn("Python_2") == "Python 2"
    assert upptackt.pythonnivanamn("Python 2") == "Python 2"
    assert upptackt.pythonnivanamn("Perl 5") is None
    assert upptackt.pythonnivanamn("") is None
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    assert upptackt.valj_pythonniva(m, "python3").namn == "Python 3"


def test_nonsensniva_avvisas(tmp_path):
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    with pytest.raises(upptackt.IngenNiva):
        upptackt.valj_pythonniva(m, "Perl 5")


# --------------------------------------------------------------------------
# Kallan i repot ska ga att ladda
# --------------------------------------------------------------------------

def test_repots_egen_kalla_gar_att_ladda():
    """Samma grind som installationen kor pa operatorens maskin."""
    mapp = paket.kallmapp()
    assert paket.granska_pythonfiler(mapp, paket.kallfiler(mapp), "Python 2") == []


def test_kallfilerna_ar_alla_py_filer_och_innehaller_init():
    filer = paket.kallfiler(paket.kallmapp())
    assert "__init__.py" in filer
    assert "bridge_cmd.py" in filer
    assert all(n.endswith(".py") for n in filer)


# --------------------------------------------------------------------------
# Installationen
# --------------------------------------------------------------------------

def _installera(tmp_path, version="4.10", nivaer=("Python 2",), **kw):
    m = _vcmapp(tmp_path, version, nivaer)
    val = upptackt.valj_pythonniva(m)
    malmapp = os.path.join(m.my_commands, val.namn, paket.PAKETNAMN)
    rapport = paket.installera(malmapp, pythonniva=val.namn, vc_version=m.version,
                               nivakalla=val.kalla,
                               sokvagen_ar_matt=val.matt, **kw)
    return malmapp, rapport


def test_installationen_lagger_filerna_pa_den_matta_sokvagen(tmp_path):
    """M-01: My Commands/Python 2/<paket>/. Utan nivan fyrar kroken aldrig."""
    malmapp, rapport = _installera(tmp_path)
    assert malmapp.endswith(os.path.join("My Commands", "Python 2", "vc_assist"))
    for namn in paket.kallfiler(paket.kallmapp()):
        assert os.path.isfile(os.path.join(malmapp, namn)), namn
    assert os.path.isfile(os.path.join(malmapp, paket.MANIFESTNAMN))
    assert rapport.nya and not rapport.uppdaterade


def test_installerade_filer_ar_byte_for_byte_lika_kallan(tmp_path):
    malmapp, _ = _installera(tmp_path)
    kalla = paket.kallmapp()
    for namn in paket.kallfiler(kalla):
        assert paket.sha256(os.path.join(malmapp, namn)) == \
            paket.sha256(os.path.join(kalla, namn)), namn


def test_manifestet_bar_det_som_behovs_for_att_stada(tmp_path):
    malmapp, _ = _installera(tmp_path)
    with open(os.path.join(malmapp, paket.MANIFESTNAMN)) as f:
        manifest = json.load(f)
    assert manifest["format"] == paket.MANIFESTFORMAT
    assert set(manifest["filer"]) == set(paket.kallfiler(paket.kallmapp()))
    assert manifest["pythonniva"] == "Python 2"
    assert manifest["vc_version"] == "4.10"
    assert manifest["sokvagen_ar_matt"] is True


def test_installationen_ar_idempotent(tmp_path):
    """Andra korningen skriver ingenting - inte ens om mtime."""
    malmapp, forst = _installera(tmp_path)
    tider = {n: os.path.getmtime(os.path.join(malmapp, n))
             for n in paket.kallfiler(paket.kallmapp())}
    fore = trad(malmapp)

    igen = paket.installera(malmapp, pythonniva="Python 2", vc_version="4.10")
    assert igen.nya == [] and igen.uppdaterade == []
    assert len(igen.oforandrade) == len(forst.nya)
    for namn, tid in tider.items():
        assert os.path.getmtime(os.path.join(malmapp, namn)) == tid, namn
    efter = trad(malmapp)
    efter.pop(paket.MANIFESTNAMN)          # bar en tidsstampel, andras alltid
    fore.pop(paket.MANIFESTNAMN)
    assert fore == efter


def test_andrad_fil_skrivs_om(tmp_path):
    malmapp, _ = _installera(tmp_path)
    with open(os.path.join(malmapp, "protokoll.py"), "a") as f:
        f.write("\n# nagon petade har\n")
    igen = paket.installera(malmapp, pythonniva="Python 2", vc_version="4.10")
    assert igen.uppdaterade == ["protokoll.py"]
    assert paket.sha256(os.path.join(malmapp, "protokoll.py")) == \
        paket.sha256(os.path.join(paket.kallmapp(), "protokoll.py"))


def test_foraldralos_fil_fran_en_tidigare_version_tas_bort(tmp_path):
    """S4: det som ersatts tas bort, det etiketteras inte.

    En modul som fanns i en aldre version av tillagget ska inte bli liggande
    och laddas av VC.
    """
    malmapp, _ = _installera(tmp_path)
    gammal = os.path.join(malmapp, "gammal_modul.py")
    with open(gammal, "w") as f:
        f.write("# fran en tidigare version\n")
    sokvag = os.path.join(malmapp, paket.MANIFESTNAMN)
    with open(sokvag) as f:
        manifest = json.load(f)
    manifest["filer"]["gammal_modul.py"] = paket.sha256(gammal)
    with open(sokvag, "w") as f:
        json.dump(manifest, f)

    igen = paket.installera(malmapp, pythonniva="Python 2", vc_version="4.10")
    assert igen.borttagna == ["gammal_modul.py"]
    assert not os.path.exists(gammal)


def test_installationen_skapar_saknad_pythonniva(tmp_path):
    """En harledd niva finns inte pa disk an. Den ska skapas, inte kastas om."""
    malmapp, rapport = _installera(tmp_path, nivaer=())
    assert os.path.isdir(malmapp)
    assert any(m.endswith("Python 2") for m in rapport.skapade_mappar), \
        rapport.skapade_mappar


# --------------------------------------------------------------------------
# Grinden: trasiga fall som MASTE falla (S2, 95_testprotokoll.md)
# --------------------------------------------------------------------------

def test_trasig_kalla_faller_och_ror_inte_maldisken(tmp_path):
    kalla = kalla_kopia(tmp_path)
    with open(os.path.join(kalla, "protokoll.py"), "a") as f:
        f.write("\ndef trasig(:\n")
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    malmapp = os.path.join(m.my_commands, "Python 2", paket.PAKETNAMN)

    with pytest.raises(paket.Verifieringsfel) as fel:
        paket.installera(malmapp, kalla=kalla, pythonniva="Python 2")
    assert "protokoll.py" in str(fel.value)
    assert not os.path.exists(malmapp), "maldisken rordes trots trasig kalla"


def test_trasig_skriptmall_faller_aven_om_filen_parsar(tmp_path):
    """Det EXAKTA felet i M-09: mallen ar en strang inne i en strang.

    Filen parsar. VC:s loadCommand returnerar ett objekt, execute() kastar
    inget, och modulkroppen kors aldrig - tyst. Grinden maste se det pa disk.
    """
    kalla = kalla_kopia(tmp_path)
    sokvag = os.path.join(kalla, "bridge_cmd.py")
    with open(sokvag, encoding="utf-8") as f:
        text = f.read()
    text = text.replace('SKRIPT = """from vcScript import *',
                        'SKRIPT = """from vcScript import *\ndef f(:\n')
    with open(sokvag, "w", encoding="utf-8") as f:
        f.write(text)

    import ast
    ast.parse(open(sokvag, encoding="utf-8").read())      # filen SJALV ar hel
    problem = paket.granska_pythonfiler(kalla, paket.kallfiler(kalla), "Python 2")
    assert any("SKRIPT-mallen" in p for p in problem), problem


def test_skriptmall_utan_vcScript_importen_faller(tmp_path):
    """M-06: utan raden finns varken delay() eller getSimulation(), OnRun dor tyst."""
    kalla = kalla_kopia(tmp_path)
    sokvag = os.path.join(kalla, "bridge_cmd.py")
    with open(sokvag, encoding="utf-8") as f:
        text = f.read()
    text = text.replace('SKRIPT = """from vcScript import *',
                        'SKRIPT = """import sys')
    with open(sokvag, "w", encoding="utf-8") as f:
        f.write(text)
    problem = paket.granska_pythonfiler(kalla, paket.kallfiler(kalla), "Python 2")
    assert any("vcScript" in p for p in problem), problem


def test_saknad_OnAppInitialized_faller(tmp_path):
    """Utan kroken gor VC ingenting med tillagget - och sager inget om det."""
    kalla = kalla_kopia(tmp_path)
    sokvag = os.path.join(kalla, "__init__.py")
    with open(sokvag, encoding="utf-8") as f:
        text = f.read()
    with open(sokvag, "w", encoding="utf-8") as f:
        f.write(text.replace("def OnAppInitialized(", "def NagotAnnat("))
    problem = paket.granska_pythonfiler(kalla, paket.kallfiler(kalla), "Python 2")
    assert any("OnAppInitialized" in p for p in problem), problem


def test_f_strang_faller_pa_python2_men_inte_pa_python3(tmp_path):
    """f-strangar finns inte i VC 4.x:s Python 2.7. I 5.0 gor de det."""
    kalla = kalla_kopia(tmp_path)
    with open(os.path.join(kalla, "protokoll.py"), "a") as f:
        f.write('\ndef nyhet(x):\n    return f"{x}"\n')
    filer = paket.kallfiler(kalla)
    assert any("f-strang" in p for p in paket.granska_pythonfiler(kalla, filer, "Python 2"))
    assert paket.granska_pythonfiler(kalla, filer, "Python 3") == []


def test_okand_niva_provas_som_python2(tmp_path):
    """36_versioner.md: okant behandlas som saknat, aldrig som en gissning."""
    kalla = kalla_kopia(tmp_path)
    with open(os.path.join(kalla, "protokoll.py"), "a") as f:
        f.write('\ndef nyhet(x):\n    return f"{x}"\n')
    assert paket.granska_pythonfiler(kalla, paket.kallfiler(kalla), None) != []


def test_kalla_utan_init_avvisas(tmp_path):
    kalla = kalla_kopia(tmp_path)
    os.remove(os.path.join(kalla, "__init__.py"))
    with pytest.raises(paket.InstallationsFel) as fel:
        paket.kallfiler(kalla)
    assert "__init__.py" in str(fel.value)


def test_misslyckad_malverifiering_stadar_undan_sig_sjalv(tmp_path, monkeypatch):
    """Ett halvt tillagg i VC ar varre an inget: VC sager inget om det.

    Grinden ska alltsa inte bara kasta, den ska ta bort det den skrev.
    """
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    malmapp = os.path.join(m.my_commands, "Python 2", paket.PAKETNAMN)
    monkeypatch.setattr(paket, "granska_malet",
                        lambda *a, **kw: ["pahittat fel for provets skull"])
    with pytest.raises(paket.Verifieringsfel) as fel:
        paket.installera(malmapp, pythonniva="Python 2", vc_version="4.10")
    assert "togs bort igen" in str(fel.value)
    assert not os.path.exists(malmapp)


@kraver_rattigheter
def test_skrivskyddad_malmapp_ger_lasbart_fel(tmp_path):
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    niva = os.path.join(m.my_commands, "Python 2")
    malmapp = os.path.join(niva, paket.PAKETNAMN)
    os.chmod(niva, 0o500)
    try:
        with pytest.raises(paket.InstallationsFel) as fel:
            paket.installera(malmapp, pythonniva="Python 2", vc_version="4.10")
        text = str(fel.value)
        assert malmapp in text
        assert "--mal" in text, "felet ska saga vad man gor at det"
    finally:
        os.chmod(niva, 0o700)


@kraver_rattigheter
def test_skrivskyddad_mapp_stoppar_inte_sokningen(tmp_path):
    """Skrivskydd ar inte lasskydd: en skrivskyddad mapp ska anda HITTAS."""
    dok = bygg_prefix(tmp_path, ".wine-vc")
    my_commands = bygg_vc(dok, "4.10")
    niva = os.path.join(my_commands, "Python 2")
    os.chmod(niva, 0o500)
    try:
        mappar = upptackt.vcmappar(linuxmiljo(tmp_path))
        assert [m.pythonnivaer for m in mappar] == [("Python 2",)]
    finally:
        os.chmod(niva, 0o700)


# --------------------------------------------------------------------------
# Kontroll av en befintlig installation
# --------------------------------------------------------------------------

def test_kontroll_av_hel_installation_ar_ren(tmp_path):
    malmapp, _ = _installera(tmp_path)
    rapport = paket.kontrollera(malmapp)
    assert rapport.installerad and rapport.aktuell and rapport.ok
    assert rapport.problem == []


def test_kontroll_faller_pa_andrad_fil(tmp_path):
    malmapp, _ = _installera(tmp_path)
    with open(os.path.join(malmapp, "pump.py"), "a") as f:
        f.write("\n# petad efter installationen\n")
    rapport = paket.kontrollera(malmapp)
    assert not rapport.ok
    assert any("pump.py" in p for p in rapport.problem)


def test_kontroll_utan_installation_ar_inte_ok(tmp_path):
    rapport = paket.kontrollera(os.path.join(str(tmp_path), "finns-inte"))
    assert not rapport.installerad and not rapport.ok


# --------------------------------------------------------------------------
# Avinstallationen
# --------------------------------------------------------------------------

def test_installera_avinstallera_lamnar_tradet_precis_som_det_var(tmp_path):
    """Det starkaste provet: hela mappen fore och efter, byte for byte."""
    m = _vcmapp(tmp_path, "4.10", ("Python 2",))
    rot = os.path.dirname(os.path.dirname(m.my_commands))
    fore = trad(rot)

    malmapp = os.path.join(m.my_commands, "Python 2", paket.PAKETNAMN)
    paket.installera(malmapp, pythonniva="Python 2", vc_version="4.10")
    assert trad(rot) != fore
    paket.avinstallera(malmapp)
    assert trad(rot) == fore


def test_avinstallationen_ror_inte_frammande_filer(tmp_path):
    """Mappen kan lika garna innehalla operatorens egna kommandon."""
    malmapp, _ = _installera(tmp_path)
    frammande = os.path.join(malmapp, "mina_egna_anteckningar.txt")
    with open(frammande, "w") as f:
        f.write("min fil\n")

    rapport = paket.avinstallera(malmapp)
    assert os.path.isfile(frammande)
    assert rapport.kvar == ["mina_egna_anteckningar.txt"]
    assert os.path.isdir(malmapp), "mappen ska sta kvar for den frammande filens skull"
    assert not os.path.exists(os.path.join(malmapp, "pump.py"))


def test_avinstallationen_ror_inte_grannmappen(tmp_path):
    malmapp, _ = _installera(tmp_path)
    granne = os.path.join(os.path.dirname(malmapp), "NagonAnnansTillagg")
    os.makedirs(granne)
    with open(os.path.join(granne, "__init__.py"), "w") as f:
        f.write("# nagon annans\n")
    fore = trad(granne)
    paket.avinstallera(malmapp)
    assert trad(granne) == fore


def test_avinstallationen_tar_bort_bytekod(tmp_path):
    """VC:s Python lagger .pyc bredvid var .py. Det ar vart avfall, inte anvandarens."""
    malmapp, _ = _installera(tmp_path)
    py2 = os.path.join(malmapp, "pump.pyc")
    with open(py2, "wb") as f:
        f.write(b"\x03\xf3\r\n")
    cache = os.path.join(malmapp, "__pycache__")
    os.makedirs(cache)
    py3 = os.path.join(cache, "pump.cpython-311.pyc")
    with open(py3, "wb") as f:
        f.write(b"\x03\xf3\r\n")

    rapport = paket.avinstallera(malmapp)
    assert not os.path.exists(py2)
    assert not os.path.exists(py3)
    assert len(rapport.bytekod) == 2
    assert not os.path.exists(malmapp)


def test_avinstallationen_tar_bort_mappar_den_sjalv_skapade(tmp_path):
    malmapp, rapport = _installera(tmp_path, nivaer=())
    niva = os.path.dirname(malmapp)
    av = paket.avinstallera(malmapp)
    assert not os.path.exists(malmapp)
    assert not os.path.exists(niva), "den harledda Python-nivan skapades av oss"
    assert os.path.isdir(os.path.dirname(niva)), "My Commands ar inte var"
    assert niva in av.mappar_borttagna


def test_avinstallation_utan_manifest_vagrar_gissa(tmp_path):
    """Utan manifest vet vi inte vilka filer som ar vara. Da rors ingenting."""
    malmapp, _ = _installera(tmp_path)
    os.remove(os.path.join(malmapp, paket.MANIFESTNAMN))
    fore = trad(malmapp)
    with pytest.raises(paket.InstallationsFel) as fel:
        paket.avinstallera(malmapp)
    assert "gissar inte" in str(fel.value)
    assert trad(malmapp) == fore


def test_avinstallationen_rapporterar_andrade_filer(tmp_path):
    malmapp, _ = _installera(tmp_path)
    with open(os.path.join(malmapp, "pump.py"), "a") as f:
        f.write("\n# handredigerad\n")
    rapport = paket.avinstallera(malmapp)
    assert rapport.andrade == ["pump.py"]
    assert "pump.py" in rapport.borttagna


def test_avinstallationen_rapporterar_saknade_filer(tmp_path):
    malmapp, _ = _installera(tmp_path)
    os.remove(os.path.join(malmapp, "pump.py"))
    rapport = paket.avinstallera(malmapp)
    assert rapport.saknades == ["pump.py"]
    assert not os.path.exists(malmapp)


# --------------------------------------------------------------------------
# Kommandoraden
# --------------------------------------------------------------------------

def kor(argv, miljo):
    rader = []
    kod = cli.main(argv, skriv=rader.append, miljo=miljo)
    return kod, "\n".join(rader)


def test_cli_utan_vc_ger_slutkod_2(tmp_path):
    bygg_prefix(tmp_path, ".wine-tom")
    kod, ut = kor(["sok"], linuxmiljo(tmp_path))
    assert kod == cli.INGEN_VC
    assert "--mal" in ut, "utan traff ska den saga hur man pekar ut mappen sjalv"

    kod, _ = kor(["installera"], linuxmiljo(tmp_path))
    assert kod == cli.INGEN_VC


def test_cli_hela_varvet(tmp_path):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, "4.10")
    bygg_vc(dok, "4.9")

    kod, ut = kor(["sok"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert "4.10" in ut and "4.9" in ut

    kod, ut = kor(["installera"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert "Python 2" in ut
    assert "MATT" in ut, "den matta sokvagen ska sagas vara matt"
    assert "4.9" in ut, "de ovriga funna mapparna ska rapporteras"

    malmapp = os.path.join(dok, FORETAG, "4.10", "My Commands", "Python 2",
                           paket.PAKETNAMN)
    assert os.path.isfile(os.path.join(malmapp, "pump.py"))
    assert not os.path.exists(os.path.join(dok, FORETAG, "4.9", "My Commands",
                                           "Python 2", paket.PAKETNAMN))

    kod, ut = kor(["verifiera"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert "samma som repots kalla: ja" in ut

    kod, ut = kor(["avinstallera"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert not os.path.exists(malmapp)


def test_cli_valjer_version_pa_begaran(tmp_path):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, "4.10")
    bygg_vc(dok, "4.9")
    kod, _ = kor(["installera", "--vc-version", "4.9"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert os.path.isdir(os.path.join(dok, FORETAG, "4.9", "My Commands",
                                      "Python 2", paket.PAKETNAMN))
    assert not os.path.exists(os.path.join(dok, FORETAG, "4.10", "My Commands",
                                           "Python 2", paket.PAKETNAMN))


def test_cli_okand_version_ger_fel_och_listar_de_funna(tmp_path):
    bygg_vc(bygg_prefix(tmp_path, ".wine-vc"), "4.10")
    kod, ut = kor(["installera", "--vc-version", "9.9"], linuxmiljo(tmp_path))
    assert kod == cli.FEL
    assert "4.10" in ut


def test_cli_alla_installerar_i_alla(tmp_path):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    for version in ("4.10", "4.9"):
        bygg_vc(dok, version)
    kod, _ = kor(["installera", "--alla"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    for version in ("4.10", "4.9"):
        assert os.path.isfile(os.path.join(dok, FORETAG, version, "My Commands",
                                           "Python 2", paket.PAKETNAMN, "pump.py"))
    kod, _ = kor(["avinstallera", "--alla"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    for version in ("4.10", "4.9"):
        assert not os.path.exists(os.path.join(dok, FORETAG, version, "My Commands",
                                               "Python 2", paket.PAKETNAMN))


def test_cli_mal_pekar_ut_mappen_direkt(tmp_path):
    """Utvagen nar sokningen inte hittar nagot: peka ut mappen sjalv."""
    malmapp = os.path.join(str(tmp_path), "nagonstans", "Visual Components",
                           "5.0", "My Commands", "Python 3", paket.PAKETNAMN)
    kod, ut = kor(["installera", "--mal", malmapp], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert os.path.isfile(os.path.join(malmapp, "pump.py"))
    assert "OPROVAD SOKVAG" in ut, "5.0 + Python 3 ar inte kort av oss"
    assert "Python 3" in ut and "5.0" in ut


def test_cli_verifiera_faller_pa_andrad_fil(tmp_path):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, "4.10")
    kor(["installera"], linuxmiljo(tmp_path))
    malmapp = os.path.join(dok, FORETAG, "4.10", "My Commands", "Python 2",
                           paket.PAKETNAMN)
    with open(os.path.join(malmapp, "formaga.py"), "a") as f:
        f.write("\ndef trasig(:\n")
    kod, ut = kor(["verifiera"], linuxmiljo(tmp_path))
    assert kod == cli.FEL
    assert "PROBLEM" in ut and "formaga.py" in ut


def test_cli_avinstallera_utan_installation_ger_fel(tmp_path):
    bygg_vc(bygg_prefix(tmp_path, ".wine-vc"), "4.10")
    kod, ut = kor(["avinstallera"], linuxmiljo(tmp_path))
    assert kod == cli.FEL
    assert "ingen installation" in ut


def test_cli_json_ar_giltig_json(tmp_path):
    bygg_vc(bygg_prefix(tmp_path, ".wine-vc"), "4.10")
    kod, ut = kor(["sok", "--json"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    data = json.loads(ut)
    assert data["vcmappar"][0]["version"] == "4.10"
    assert data["vcmappar"][0]["pythonnivaer"] == ["Python 2"]


def test_cli_utan_kommando_ger_hjalp(tmp_path):
    kod, _ = kor([], linuxmiljo(tmp_path))
    assert kod == cli.FEL


def test_cli_upprepad_installation_ar_idempotent(tmp_path):
    dok = bygg_prefix(tmp_path, ".wine-vc")
    bygg_vc(dok, "4.10")
    kor(["installera"], linuxmiljo(tmp_path))
    malmapp = os.path.join(dok, FORETAG, "4.10", "My Commands", "Python 2",
                           paket.PAKETNAMN)
    fore = trad(malmapp)
    kod, ut = kor(["installera"], linuxmiljo(tmp_path))
    assert kod == cli.KLART
    assert "nya: 0" in ut and "uppdaterade: 0" in ut
    efter = trad(malmapp)
    efter.pop(paket.MANIFESTNAMN)
    fore.pop(paket.MANIFESTNAMN)
    assert fore == efter
