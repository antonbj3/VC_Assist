# -*- coding: utf-8 -*-
"""A5/M-154: svepet bakom talen i M-154.

Tre frågor, tre oberoende domare, ingen av dem vår egen jämförelse:

1. **Tur och retur.** `Enhet -> PLCopen XML -> Enhet` över bankens 63 program
   och 14 handbyggda konstruktioner. Domare: modelljämförelse (`==`).
2. **Schemat.** Varje fil mot det officiella `tc6_xml_v201.xsd`. Domare: `lxml`.
3. **Ett främmande verktyg.** Varje fil genom **Beremiz egen laddare**
   (`plcopen.plcopen.LoadProjectXML`), och den ST som kommer tillbaka ur vår
   egen import genom **matiec** (OpenPLC:s kompilator). Domare: någon annans
   kod, i båda fallen.

Beremiz-modulerna ligger INTE i repot. Hämta dem så här (de importerar ingen
wxPython — kontrollerat, inte antaget):

    S=<katalog>
    mkdir -p $S/plcopen $S/xmlclass $S/util
    B=https://raw.githubusercontent.com/beremiz/beremiz/master
    for f in plcopen/__init__.py plcopen/plcopen.py plcopen/structures.py \\
             plcopen/definitions.py plcopen/tc6_xml_v201.xsd \\
             plcopen/TC6_XML_V10_B.xsd plcopen/TC6_XML_V10.xsd \\
             xmlclass/__init__.py xmlclass/xmlclass.py xmlclass/xsdschema.py \\
             util/__init__.py util/paths.py; do
      curl -sS -f -o "$S/$f" "$B/$f"; done

    VC_ASSIST_BEREMIZ=$S python3 docs/matningar/radata/m154_svep.py

Utan `$VC_ASSIST_BEREMIZ` hoppas del 3a över och säger det. Utan matiec
(`/tmp/opencode/matiec/iec2c`) hoppas del 3b över och säger det. Ett svep som
tyst utelämnar sin externa domare är ett falskt grönt.
"""
import os
import sys

_ROT = "/home/anton/projects/VC_Assist"
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, os.path.join(_ROT, "bank"))

from vc_assist_svc.st import las, skriv_enhet          # noqa: E402
from vc_assist_svc.plc import plcopen as PX            # noqa: E402
import baslinjebank as BB                              # noqa: E402
from vc_assist_svc.plc.baslinje import Baslinje        # noqa: E402


def konstruktioner():
    """De handbyggda konstruktionerna, lästa ur provfilen så att svepet och
    provet aldrig kan mäta två olika listor."""
    txt = open(os.path.join(_ROT, "tests", "enhet", "test_plc_plcopen.py"),
               encoding="utf-8").read()
    ns = {}
    exec(txt[txt.index("KONSTRUKTIONER = ["):txt.index("\ndef _las(")], ns)
    return [(n, k.strip() + "\n") for n, k in ns["KONSTRUKTIONER"]]


def bankprogram():
    b = Baslinje()
    ut = []
    for post in BB.las_uppgifter():
        ut.append((post.get("task_id"), BB.bygg(post, b).st_kalla))
    return ut


def _beremiz_laddare():
    stig = os.environ.get("VC_ASSIST_BEREMIZ")
    if not stig or not os.path.isdir(stig):
        return None
    sys.path.insert(0, stig)
    from plcopen.plcopen import LoadProjectXML
    return LoadProjectXML


def _matiec():
    from vc_assist_svc.plc import matiec as MT
    try:
        MT.hitta_binar()
    except Exception:
        return None
    return MT


def main():
    fall = [("KONSTR", n, k) for n, k in konstruktioner()]
    fall += [("BANK", n, k) for n, k in bankprogram()]

    laddare = _beremiz_laddare()
    mt = _matiec()

    rakning = dict(fall=0, st_kontroll=0, tur=0, schema=0, beremiz=0,
                   matiec_samma=0, matiec_ja=0)
    avvikande = []

    for grupp, namn, kalla in fall:
        rakning["fall"] += 1
        e = las(kalla)
        if las(skriv_enhet(e)) == e:
            rakning["st_kontroll"] += 1
        else:
            avvikande.append((grupp, namn, "ST-lagrets egen tur och retur höll inte"))
            continue
        try:
            xml = PX.exportera(e, projektnamn=namn)
        except PX.ExportFel as fel:
            avvikande.append((grupp, namn, "EXPORTEN FÄLLDE: %s" % str(fel)[:200]))
            continue
        rakning["tur"] += 1
        fel_schema = PX.validera_schema(xml)
        if fel_schema == ():
            rakning["schema"] += 1
        else:
            avvikande.append((grupp, namn, "SCHEMA: %s" % fel_schema[0][:200]))
        if laddare is not None:
            trad, fel = laddare(xml)
            if fel is None and trad is not None:
                rakning["beremiz"] += 1
            else:
                avvikande.append((grupp, namn, "BEREMIZ: %s" % str(fel)[:200]))
        if mt is not None:
            fore = mt.kompilera(kalla).accepterad
            efter = mt.kompilera(PX.till_st(xml)).accepterad
            if fore == efter:
                rakning["matiec_samma"] += 1
            else:
                avvikande.append((grupp, namn,
                                  "MATIEC: fore=%s efter=%s" % (fore, efter)))
            if fore:
                rakning["matiec_ja"] += 1
        print("%-6s %-32s tur=OK schema=%s" % (grupp, namn,
                                               "OK" if fel_schema == () else "FEL"))

    n = rakning["fall"]
    print()
    print("fall totalt:                          %d" % n)
    print("ST-lagrets egen tur och retur höll:   %d av %d" % (rakning["st_kontroll"], n))
    print("PLCopen tur och retur höll:           %d av %d" % (rakning["tur"], n))
    print("giltiga mot tc6_xml_v201.xsd:         %d av %d" % (rakning["schema"], n))
    if laddare is None:
        print("Beremiz egen laddare:                 EJ KÖRD ($VC_ASSIST_BEREMIZ saknas)")
    else:
        print("godtagna av Beremiz egen laddare:     %d av %d" % (rakning["beremiz"], n))
    if mt is None:
        print("matiec:                               EJ KÖRD (iec2c hittades inte)")
    else:
        print("matiec: samma dom före och efter:     %d av %d" % (rakning["matiec_samma"], n))
        print("matiec: accepterade originalet:       %d av %d" % (rakning["matiec_ja"], n))
    print()
    for rad in avvikande:
        print("AVVIKER", rad)
    return 0 if not avvikande else 1


if __name__ == "__main__":
    sys.exit(main())
