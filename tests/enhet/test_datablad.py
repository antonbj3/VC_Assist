# -*- coding: utf-8 -*-
"""L1 for databladslagret. Ingen VC, inget riktigt bibliotek.

Komponenterna attrapperas som riktiga .vcmx: zip-arkiv med en component.rsc i
VC:s eget textformat, med de block matningen M-59 fann - Dof med MinLimit och
MaxLimit, en rSimRobotController med JointMap, ett kinematikblock med
lanklangder, rotens egen variabelrymd och rSimInterface.

TRE TRASIGA FIXTURER bar provet:
  * en komponent UTAN ledblock ska ge "saknas", inte noll axlar
  * ett falt som FINNS men ar tomt ska ge "saknas", inte noll
  * en storhet som inte hor till familjen ska falla, inte svara "saknas"

Den tredje ar den viktigaste. "Storheten finns inte i datan" och "storheten
finns inte i fragan" ar tva olika svar, och ett datablad som ger samma svar pa
bada ar precis det som ser komplett ut och ljuger.
"""
import json
import os
import sys
import zipfile

import pytest

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))

from vc_assist_svc import datablad as D                          # noqa: E402


# ---------------------------------------------------------------------------
# Attrapperna
# ---------------------------------------------------------------------------

def _dof(namn, typ="Rotational", minv="-170", maxv="170",
         fart="100", acc="400", quantity="Angular velocity"):
    """Ett Dof-block som VC skriver det.

    Notera att SoftMinLimit ar 0.0 medan den VERKLIGA gransen star i
    MinLimit/MaxLimit langre ned - sa ser filerna ut, och en lasare som tar
    Soft-falten far noll grader i bada andar.
    """
    return '''Dof  "%s"
{
  Name "%s"
  Properties
  {
    Variable "rTExpressionVariable<rDouble>"
    {
      Name "SoftMinLimit"
      Value
      {
        Expression "0.0"
      }
    }
    Variable "rTVariable<rDouble>"
    {
      Name "MaxSpeed"
      Value %s
      Quantity "%s"
      Magnitude 1
    }
    Variable "rTVariable<rDouble>"
    {
      Name "MaxAcceleration"
      Value %s
      Quantity "Angular acceleration"
      Magnitude 1
    }
  }
  JointValue 0
  MinLimit
  {
    Expression "%s"
  }
  MaxLimit
  {
    Expression "%s"
  }
  AxisType 2
}''' % (typ, namn, fart, quantity, acc, minv, maxv)


def _rotvar(poster):
    """Rotens egen variabelrymd. (namn, typ, varde, quantity)."""
    ut = []
    for namn, typ, varde, q in poster:
        ut.append('''  Variable "rTVariable<%s>"
  {
    Name "%s"
    Value %s
    Group 1%s
  }''' % (typ, namn, varde, ('\n    Quantity "%s"' % q) if q else ""))
    return "VariableSpace \"\"\n{\n%s\n}" % "\n".join(ut)


def _geometrilada(langd=1234, bredd=99, hojd=42):
    """En geometriprimitiv med LADANS matt. Den ska ALDRIG na databladet.

    Ladan bar bade de generiska namnen (Length, Width, Height) och de namn
    databladet faktiskt letar efter (ConveyorLength och syskonen). Det andra
    ar avsiktligt och det ar matt: `Item/Robot Pedestals/Robot enclosure with
    conveyor belt` traffar "ConveyorLength" i ratexten och har INGEN sadan
    rotvariabel (M-59). En lasare som soker i hela texten far ladans 1234 mm
    och svaret ser likadant ut som ett riktigt.
    """
    return '''Feature "rPrimitiveBoxFeature"
{
Name "Box"
VariableSpace
{
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "Length"
    Value %(l)d
  }
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "Width"
    Value %(b)d
  }
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "Height"
    Value %(h)d
  }
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "ConveyorLength"
    Value %(l)d
  }
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "ConveyorWidth"
    Value %(b)d
  }
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "ConveyorHeight"
    Value %(h)d
  }
  Variable "rTExpressionVariable<rDouble>"
  {
    Name "MaxLoad"
    Value 999000
  }
}
}''' % {"l": langd, "b": bredd, "h": hojd}


def robot_rsc(namn="IRB 6700", leder=6, kinematik=True, styrenhet=True,
              maxload=None, rotvar=(), verktygsmassa=None, dof_typ="Rotational"):
    ledblock = "\n".join(_dof("Axis%d" % (i + 1), dof_typ)
                         for i in range(leder))
    jointmap = "\n".join('Joint %d "Axis%d"' % (i, i + 1) for i in range(leder))
    ctl = ('''Functionality "rSimRobotController"
{
Id 2
Name "IRC5"
RootNode "%s"
FlangeNode "mountplate"
JointMap
{
%s
}
Bases ""
{
}
Tools ""
{
%s
}
}''' % (namn, jointmap,
        "\n".join('''BaseFrame "rSimBaseFrame"
{
Frame "tool1"
Node "mountplate"
Mass  %s
Inertia  0 0 0 1
}''' % m for m in ([verktygsmassa] if verktygsmassa is not None else []))))
    kin = '''Functionality "rKinArticulated2"
{
Id 1
Name "Kinematics"
L01Z 830
L12X 350
L12Y 0
L23X 0
L23Z 1145
L34X -200
L34Z 1212.5
L45X 0
L45Z 0
L56X 0
L56Z 220
}'''
    poster = list(rotvar)
    if maxload is not None:
        poster.append(("MaxLoad", "rDouble", maxload, "Mass"))
    return '''VCMD0028041000000000COMPONENT
Node "rSimResource"
{
Name "%s"
Category  "Robots"
%s
%s
%s
%s
Functionality "rSimInterface"
{
Id 6
Name "Tool"
Section
{
Name "Mount"
Fields
{
rSimHierarchyField
{
Name "Hierarchy"
Mount 1
Node "mountplate"
}
}
}
}
%s
}
''' % (namn, _rotvar(poster), _geometrilada(),
       ctl if styrenhet else "", kin if kinematik else "", ledblock)


def transportor_rsc(namn="Band 1", langd="2000", bredd="500", hojd="700",
                    fart="300", kapacitet="10"):
    poster = []
    for n, v, q in (("ConveyorLength", langd, "Distance"),
                    ("ConveyorWidth", bredd, "Distance"),
                    ("ConveyorHeight", hojd, "Distance"),
                    ("ConveyorSpeed", fart, ""),
                    ("Advanced::ConveyorCapacity", kapacitet, "")):
        if v is not None:
            poster.append((n, "rDouble", v, q))
    return '''VCMD0028041000000000COMPONENT
Node "rSimResource"
{
Name "%s"
Category  "Conveyors"
%s
%s
Functionality "rOneWayPath"
{
Id 3
Name "Path"
}
Functionality "rSimInterface"
{
Id 4
Name "SideA_ioPort0"
Section
{
Name "flowIN"
Fields
{
rSimFlowField
{
Name "flowfield"
Port 0
}
}
}
}
}
''' % (namn, _rotvar(poster), _geometrilada())


def skriv_vcmx(sokvag, rsc):
    os.makedirs(os.path.dirname(sokvag), exist_ok=True)
    with zipfile.ZipFile(sokvag, "w") as z:
        z.writestr("component.rsc", rsc)
        z.writestr("geo-1", b"\x00\x01")
    return sokvag


# ---------------------------------------------------------------------------
# Vardet och dess harkomst
# ---------------------------------------------------------------------------

def test_ett_varde_utan_kalla_far_inte_finnas():
    with pytest.raises(D.Databladsfel):
        D.Varde("rackvidd", 1500, "mm", D.LAST, "")


def test_saknas_med_ett_varde_ar_en_motsagelse():
    with pytest.raises(D.Databladsfel):
        D.Varde("rackvidd", 1500, "mm", D.SAKNAS, "skal")


def test_ett_varde_utan_harkomst_far_inte_finnas():
    with pytest.raises(D.Databladsfel):
        D.Varde("rackvidd", 1500, "mm", "kanske", "skal")


def test_harkomsten_ar_ett_FALT_inte_en_formulering():
    """En harledd siffra maste ga att skilja fran en avlast MEKANISKT."""
    a = D.last("rackvidd", 1500, "stod i filen")
    b = D.harledd("rackvidd", 1500, "summan av lanklangderna")
    assert a.varde == b.varde
    assert a.harkomst != b.harkomst
    assert a.till_json()["harkomst"] == "last"
    assert b.till_json()["harkomst"] == "harledd"


def test_den_korta_json_formen_behaller_harkomsten_men_inte_kallan():
    v = D.harledd("rackvidd", 1500, "en lang formel som kostar tecken")
    assert v.till_json(kort=True) == {"harkomst": "harledd", "varde": 1500,
                                      "enhet": "mm"}
    assert "kalla" in v.till_json()


def test_texten_bar_enhet_och_harledning():
    t = D.harledd("rackvidd", 2723.9, "summan av lanklangderna").text()
    assert "2723.9" in t and "mm" in t and "harledd" in t


# ---------------------------------------------------------------------------
# Roboten
# ---------------------------------------------------------------------------

def test_robot_lases_med_axlar_granser_och_hastigheter(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    assert b.familj == "robot"
    assert b["frihetsgrader"].varde == 6
    assert b["frihetsgrader"].harkomst == D.LAST
    assert b["ledtyper"].varde == ["vridande"] * 6
    assert b["ledgranser"].varde[0]["min"] == -170.0
    assert b["ledgranser"].varde[0]["enhet"] == "grad"
    assert b["maxhastighet"].varde[0]["varde"] == 100.0
    assert b["maxhastighet"].varde[0]["enhet"] == "grad/s"
    assert b["monteringsram"].varde == "mountplate"
    assert b["styrenhet"].varde == "IRC5"


def test_frihetsgraderna_kommer_ur_JOINTMAP_inte_ur_antalet_dof(tmp_path):
    """En IRB 6700 har atta Dof-block och sex styrda axlar (M-59)."""
    rsc = robot_rsc(leder=6)
    rsc = rsc.replace('Dof  "Rotational"',
                      _dof("Extra1", "Fixed") + "\n" +
                      _dof("Extra2", "RotationalFollower") + "\n" +
                      'Dof  "Rotational"', 1)
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), rsc), "ABB")
    assert b["frihetsgrader"].varde == 6
    assert "JointMap" in b["frihetsgrader"].kalla


def test_rackvidden_ar_HARLEDD_och_kallan_bar_formeln(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    v = b["rackvidd"]
    assert v.harkomst == D.HARLEDD
    # L12X 350 + |0,1145| + |-200,1212.5| + |0,0| = 2723.9. Flanslanken L56
    # ar INTE med: tillverkaren matter till handledscentrum (M-59).
    assert abs(v.varde - 2723.9) < 0.2
    assert "L56" in v.kalla and "M-59" in v.kalla
    assert v.enhet == "mm"


def test_en_ledgrans_som_ar_ett_uttryck_star_kvar_som_uttryck(tmp_path):
    """718 komponenter har en grans som beror av en annan led (M-59).

    Att rakna om den till ett tal vore ett pastaende om ett arbetsomrade
    ingen matt.
    """
    rsc = robot_rsc().replace('Expression "-170"',
                              'Expression "Axis2<-55.0?-9.0*Axis2-605.0:-170.0"')
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), rsc), "ABB")
    g = b["ledgranser"].varde[0]
    assert "min" not in g
    assert g["min_uttryck"].startswith("Axis2<")


def test_nyttolasten_lases_och_rakas_om_till_kilo(tmp_path):
    """Filens massenhet ar gram: MaxLoad 20000 i en 20 kg-robot (M-59)."""
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"),
                         robot_rsc(maxload="20000")), "KUKA")
    assert b["nyttolast"].varde == 20.0
    assert b["nyttolast"].enhet == "kg"
    assert b["nyttolast"].harkomst == D.LAST


def test_verktygsmassan_minus_1000_ar_INGEN_massa(tmp_path):
    """VC skriver -1000 nar ingen last ar satt. 351 komponenter bar det."""
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"),
                         robot_rsc(verktygsmassa="-1000")), "KUKA")
    assert b["verktygslast"].harkomst == D.SAKNAS


def test_verktygsmassan_noll_ar_ingen_massa_heller(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"),
                         robot_rsc(verktygsmassa="0")), "KUKA")
    assert b["verktygslast"].harkomst == D.SAKNAS


def test_verktygsmassan_lases_nar_den_finns(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"),
                         robot_rsc(verktygsmassa="6000")), "Igus")
    assert b["verktygslast"].varde == 6.0


def test_egenvikten_saknas_alltid_och_sager_varfor(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    assert b["egenvikt"].harkomst == D.SAKNAS
    assert "3201" in b["egenvikt"].kalla


def test_ett_MaxLoad_inne_i_en_geometrilada_ar_inte_robotens_nyttolast(tmp_path):
    """Ladan i attrappen bar MaxLoad 999000. Roten bar ingen.

    En lasare som soker i hela texten far en robot som lyfter 999 kilo.
    """
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    assert b["nyttolast"].harkomst == D.SAKNAS


def test_monteringsgranssnitt_skiljer_vard_fran_gast(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    assert b["granssnitt"].varde == ["Tool"]


# ---------------------------------------------------------------------------
# Familjen lases ur STRUKTUREN
# ---------------------------------------------------------------------------

def test_familjen_kommer_ur_funktionsblocken_inte_ur_katalognamnet(tmp_path):
    """466 robotar ligger utanfor katalogen Robots (M-59)."""
    sokvag = str(tmp_path / "Legacy" / "gammal.vcmx")
    b = D.las(skriv_vcmx(sokvag, robot_rsc(namn="KR 210")), "KUKA")
    assert b.familj == "robot"


def test_transportor_lases_med_matt_och_hastighet(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), transportor_rsc()), "Item")
    assert b.familj == "transportor"
    assert b["langd"].varde == 2000.0 and b["langd"].enhet == "mm"
    assert b["hastighet"].varde == 300.0 and b["hastighet"].enhet == "mm/s"
    assert b["kapacitet"].varde == 10.0


def test_hastighetens_enhet_sager_att_den_inte_star_i_filen(tmp_path):
    """ConveyorSpeed saknar Quantity i 99 av 115 (M-59). Da sags det."""
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), transportor_rsc()), "Item")
    assert "ingen Quantity" in b["hastighet"].kalla
    assert "M-33" in b["hastighet"].kalla


def test_LADANS_matt_hamnar_ALDRIG_i_databladet(tmp_path):
    """Length/Width/Height sitter i geometriprimitiver (M-59).

    Attrappens lada ar 1234 x 99 x 42 och bandet 2000 x 500 x 700. En
    oscopead lasare tar ladan och svaret ser likadant ut.
    """
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), transportor_rsc()), "Item")
    assert b["langd"].varde == 2000.0
    assert b["bredd"].varde == 500.0
    assert b["hojd"].varde == 700.0
    # Och ladan far inte fylla ett falt som saknas i roten heller.
    tom = D.las(skriv_vcmx(str(tmp_path / "c.vcmx"),
                           transportor_rsc(langd=None)), "Item")
    assert tom["langd"].harkomst == D.SAKNAS


# ---------------------------------------------------------------------------
# TRASIG FIXTUR 1: ingen ledinformation alls
# ---------------------------------------------------------------------------

def test_TRASIG_utan_ledblock_ger_SAKNAS_inte_noll_axlar(tmp_path):
    """Noll axlar ar ett pastaende. Saknas ar ett svar.

    En komponent utan bade JointMap och Dof-block far INTE bli "0
    frihetsgrader" - det talet ser ut som en matning och ar en tystnad.
    """
    rsc = robot_rsc(styrenhet=False, leder=0)
    assert "Dof" not in rsc
    b = D.las(skriv_vcmx(str(tmp_path / "tom.vcmx"), rsc), "X")
    assert b.familj != "robot"          # ingen styrenhet -> ingen robotfamilj
    # Frihetsgrader hor da inte ens till familjen, och det ar ett tredje svar.
    with pytest.raises(D.Databladsfel):
        b["frihetsgrader"]


def test_TRASIG_robot_utan_ledblock_ger_SAKNAS_inte_noll(tmp_path):
    """Samma fixtur, men med styrenheten kvar sa familjen blir robot."""
    rsc = robot_rsc(leder=0)
    b = D.las(skriv_vcmx(str(tmp_path / "tom.vcmx"), rsc), "X")
    assert b.familj == "robot"
    v = b["frihetsgrader"]
    assert v.harkomst == D.SAKNAS
    assert v.varde is None
    assert b["ledtyper"].harkomst == D.SAKNAS
    assert b["ledgranser"].harkomst == D.SAKNAS
    assert b["maxhastighet"].harkomst == D.SAKNAS


def test_TRASIG_utan_kinematikblock_ger_ingen_rackvidd(tmp_path):
    rsc = robot_rsc(kinematik=False)
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), rsc), "X")
    assert b["rackvidd"].harkomst == D.SAKNAS
    assert b["rackvidd"].varde is None


def test_TRASIG_kinematik_utan_lanklangder_ger_ingen_rackvidd(tmp_path):
    """Blocket finns men bar inga matt - 506 robotar ar sa (M-59)."""
    rsc = robot_rsc()
    for rad in ("L12X 350", "L23Z 1145"):
        rsc = rsc.replace(rad, "")
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), rsc), "X")
    assert b["rackvidd"].harkomst == D.SAKNAS
    assert "L12X" in b["rackvidd"].kalla


# ---------------------------------------------------------------------------
# TRASIG FIXTUR 2: faltet finns men ar tomt
# ---------------------------------------------------------------------------

def test_TRASIG_tomt_falt_ger_SAKNAS_inte_noll(tmp_path):
    """ConveyorLength finns i filen men bar en tom strang.

    Det ar den farligaste av de tre: `float("")` faller, men en lasare som
    fangar felet och satter 0 far ett band som ar noll millimeter langt och
    som SER matt ut.
    """
    rsc = transportor_rsc(langd='""')
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), rsc), "Item")
    v = b["langd"]
    assert v.harkomst == D.SAKNAS
    assert v.varde is None
    assert "finns men bar" in v.kalla
    # och de andra falten pa samma komponent ar opaverkade
    assert b["bredd"].varde == 500.0


def test_TRASIG_falt_med_text_i_stallet_for_tal_ger_SAKNAS(tmp_path):
    rsc = transportor_rsc(fart='"Auto"')
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), rsc), "Item")
    assert b["hastighet"].harkomst == D.SAKNAS
    assert "Auto" in b["hastighet"].kalla


def test_TRASIG_maxload_som_inte_ar_en_massa_ger_SAKNAS(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"),
                         robot_rsc(maxload="0")), "X")
    assert b["nyttolast"].harkomst == D.SAKNAS
    assert "inte ar en massa" in b["nyttolast"].kalla


def test_ett_helt_saknat_falt_och_ett_tomt_falt_sager_OLIKA_saker(tmp_path):
    """Bada ar saknas - men skalet skiljer, och skalet ar hela poangen."""
    tomt = D.las(skriv_vcmx(str(tmp_path / "a.vcmx"),
                            transportor_rsc(langd='""')), "Item")["langd"]
    borta = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"),
                             transportor_rsc(langd=None)), "Item")["langd"]
    assert tomt.harkomst == borta.harkomst == D.SAKNAS
    assert tomt.kalla != borta.kalla
    assert "finns men bar" in tomt.kalla
    assert "ingen av rotvariablerna" in borta.kalla


# ---------------------------------------------------------------------------
# TRASIG FIXTUR 3: en storhet som inte hor till familjen
# ---------------------------------------------------------------------------

def test_TRASIG_storhet_utanfor_familjen_FALLER_och_svarar_inte_saknas(tmp_path):
    """En robots bandhastighet ar ingen fraga som har ett varde.

    Skulle den svara "saknas" hade databladet sagt att VC:s robotfiler kunde
    burit en bandhastighet men inte gjorde det. Det ar ett pastaende om
    datan, och det ar falskt.
    """
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    with pytest.raises(D.Databladsfel) as fel:
        b["hastighet"]
    assert "hor inte till familjen" in str(fel.value)
    assert "robot" in str(fel.value)
    assert not b.har("hastighet")


def test_TRASIG_storhet_utanfor_ORDFORRADET_faller_med_listan(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    with pytest.raises(D.Databladsfel) as fel:
        b["payload"]
    assert "ordforradet" in str(fel.value)
    assert "nyttolast" in str(fel.value)


def test_transportoren_har_ingen_rackvidd_att_saknas(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), transportor_rsc()), "Item")
    with pytest.raises(D.Databladsfel):
        b["rackvidd"]


# ---------------------------------------------------------------------------
# Trasiga arkiv
# ---------------------------------------------------------------------------

def test_en_trasig_vcmx_faller_med_skal(tmp_path):
    p = tmp_path / "trasig.vcmx"
    p.write_bytes(b"det har ar inte ett zip-arkiv")
    with pytest.raises(D.Databladsfel):
        D.las(str(p))


def test_en_vcmx_utan_metadata_faller_med_skal(tmp_path):
    p = tmp_path / "utan.vcmx"
    with zipfile.ZipFile(str(p), "w") as z:
        z.writestr("geo-1", b"\x00")
    with pytest.raises(D.Databladsfel) as fel:
        D.las(str(p))
    assert "component.rsc" in str(fel.value)


def test_bygg_raknar_olasliga_i_stallet_for_att_tiga(tmp_path):
    rot = tmp_path / "bib"
    skriv_vcmx(str(rot / "ABB" / "r.vcmx"), robot_rsc())
    (rot / "ABB" / "trasig.vcmx").write_bytes(b"nej")
    blad, olasliga = D.bygg(str(rot))
    assert len(blad) == 1 and len(olasliga) == 1
    assert blad[0].tillverkare == "ABB"


def test_saknad_rot_faller(tmp_path):
    with pytest.raises(D.Databladsfel):
        D.bygg(str(tmp_path / "finns-inte"))


# ---------------------------------------------------------------------------
# De tva formerna
# ---------------------------------------------------------------------------

def test_korta_formen_ar_mindre_an_den_fulla(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    assert len(b.kort_text()) < len(b.full_text())
    assert len(json.dumps(b.kort())) < len(json.dumps(b.fullt()))


def test_korta_formen_behaller_harkomsten_pa_varje_falt(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "r.vcmx"), robot_rsc()), "ABB")
    for namn, v in b.kort().items():
        if isinstance(v, dict):
            assert "harkomst" in v, namn


def test_korta_formen_bar_bara_familjens_egna_storheter(tmp_path):
    b = D.las(skriv_vcmx(str(tmp_path / "b.vcmx"), transportor_rsc()), "Item")
    assert set(D.KORTA_STORHETER["transportor"]) >= {
        k for k in b.kort() if k in D.STORHETER}


def test_ordforradet_ar_slutet():
    """Ordforradet ar hela ytan mot en sprakmodell. Vaxer det utan matning
    kan ingen lara sig det."""
    for familj, storheter in D.FAMILJENS_STORHETER.items():
        for s in storheter:
            assert s in D.STORHETER, (familj, s)
    for familj, storheter in D.KORTA_STORHETER.items():
        for s in storheter:
            assert s in D.FAMILJENS_STORHETER[familj], (familj, s)


def test_varje_storhet_i_ordforradet_har_en_enhet_eller_ett_skal():
    for namn, (enhet, beskrivning) in D.STORHETER.items():
        assert enhet or beskrivning, namn


# ---------------------------------------------------------------------------
# Tackningen
# ---------------------------------------------------------------------------

def test_tackningen_raknar_last_harledd_och_saknas_med_namnare(tmp_path):
    rot = tmp_path / "bib"
    skriv_vcmx(str(rot / "ABB" / "r1.vcmx"), robot_rsc(maxload="20000"))
    skriv_vcmx(str(rot / "ABB" / "r2.vcmx"), robot_rsc())
    skriv_vcmx(str(rot / "Item" / "b1.vcmx"), transportor_rsc())
    blad, _ = D.bygg(str(rot))
    t = D.tackning(blad)
    assert t["nyttolast"]["tillamplig"] == 2      # bara robotarna
    assert t["nyttolast"]["last"] == 1
    assert t["nyttolast"]["saknas"] == 1
    assert t["rackvidd"] == {"tillamplig": 2, "last": 0, "harledd": 2,
                             "saknas": 0}
    assert t["hastighet"]["tillamplig"] == 1     # bara transportoren
    assert t["egenvikt"]["saknas"] == 3


def test_tackningens_rader_summerar_till_namnaren(tmp_path):
    rot = tmp_path / "bib"
    skriv_vcmx(str(rot / "ABB" / "r.vcmx"), robot_rsc())
    skriv_vcmx(str(rot / "Item" / "b.vcmx"), transportor_rsc())
    blad, _ = D.bygg(str(rot))
    for storhet, r in D.tackning(blad).items():
        assert r["last"] + r["harledd"] + r["saknas"] == r["tillamplig"], storhet


# ---------------------------------------------------------------------------
# Lasaren sjalv
# ---------------------------------------------------------------------------

def test_radbrytning_mitt_i_en_strang_lases_hel():
    """VC bryter langa uttryck med ett bakstreck. Den som laser rad for rad
    far ett halvt uttryck och ser det inte."""
    trad = D.las_trad('Offset\n{\n  Expression "Tz(A).Tx(B)\\\n.Ry(C)"\n}\n')
    assert trad.sok("Offset")[0].strang("Expression") == "Tz(A).Tx(B).Ry(C)"


def test_geometrifeatures_hoppas_over_men_strukturen_halls_hel():
    trad = D.las_trad('Node "rSimResource"\n{\n' + _geometrilada() +
                      '\nFunctionality "rSimInterface"\n{\nName "X"\n}\n}\n')
    assert D.funktionsnamn(trad) == ["rSimInterface"]
    assert trad.alla("Feature") == []


# ---------------------------------------------------------------------------
# Matningen ska ga att kora om
# ---------------------------------------------------------------------------

def test_tackningstabellen_skriver_ut_namnaren(tmp_path):
    """Aldrig bara procent. En procent utan namnare gar inte att prova om."""
    rot = tmp_path / "bib"
    skriv_vcmx(str(rot / "ABB" / "r.vcmx"), robot_rsc())
    blad, _ = D.bygg(str(rot))
    tabell = D.tackningstabell(blad)
    assert "tillamplig" in tabell
    for storhet in D.STORHETER:
        assert storhet in tabell


def test_kommandoraden_bygger_tabellen_ur_den_levererade_koden(tmp_path, capsys):
    rot = tmp_path / "bib"
    skriv_vcmx(str(rot / "ABB" / "r.vcmx"), robot_rsc(maxload="20000"))
    skriv_vcmx(str(rot / "Item" / "b.vcmx"), transportor_rsc())
    assert D.main(["--rot", str(rot)]) == 0
    ut = capsys.readouterr().out
    assert "2 datablad, 0 olasliga" in ut
    assert "robot 1" in ut and "transportor 1" in ut
    assert "kort text" in ut and "full JSON" in ut


def test_kommandoraden_pa_en_rot_som_inte_finns_faller(tmp_path):
    with pytest.raises(D.Databladsfel):
        D.main(["--rot", str(tmp_path / "finns-inte")])


def test_kommandoraden_visar_ett_enskilt_datablad(tmp_path, capsys):
    rot = tmp_path / "bib"
    skriv_vcmx(str(rot / "ABB" / "r.vcmx"), robot_rsc(namn="IRB 6700"))
    assert D.main(["--rot", str(rot), "--visa", "6700"]) == 0
    ut = capsys.readouterr().out
    assert "IRB 6700" in ut and "rackvidd" in ut
    assert "ledgranser" not in ut          # kort ar standard
    capsys.readouterr()
    assert D.main(["--rot", str(rot), "--visa", "6700", "--fullt"]) == 0
    assert "ledgranser" in capsys.readouterr().out
