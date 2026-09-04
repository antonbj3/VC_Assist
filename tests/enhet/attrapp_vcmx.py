# -*- coding: utf-8 -*-
"""Attrapperade .vcmx-arkiv for L1. Ingen VC, inget riktigt bibliotek.

Arkiven byggs med de riktiga posterna och de riktiga formaten: `model.xml`
som XML, `component.rsc` i VC:s eget textformat, geometrin som Autodesk 3DS
och rackviddsprofilen i BADA de format biblioteket faktiskt bar. En attrapp
som forenklar formatet provar inte lasaren utan bara sig sjalv.
"""
import struct
import zipfile

MODELXML = ('﻿<?xml version="1.0" encoding="utf-8"?>\n'
            '<VcModel version="1">\n  <Properties>\n%s'
            '  </Properties>\n  <ModelUrl>component.rsc</ModelUrl>\n'
            '</VcModel>\n')


def modelxml(**egenskaper):
    rader = "".join('    <Property name="%s">%s</Property>\n' % (k, v)
                    for k, v in egenskaper.items() if v is not None)
    return MODELXML % rader


def tds_geometri(horn, namn="Prov", trianglar=None):
    """En Autodesk 3DS-blobb med en hornlista och valfri triangellista.

    `trianglar` ar [(a, b, c), ...] med index in i hornlistan. Ett index
    utanfor listan ar precis det som `tds_kontroll` ska fanga.
    """
    kropp = struct.pack("<H", len(horn))
    for p in horn:
        kropp += struct.pack("<3f", *p)
    v = struct.pack("<HI", 0x4110, 6 + len(kropp)) + kropp
    if trianglar is not None:
        tk = struct.pack("<H", len(trianglar))
        for a, b, c in trianglar:
            tk += struct.pack("<4H", a, b, c, 7)
        v += struct.pack("<HI", 0x4120, 6 + len(tk)) + tk
    mesh = struct.pack("<HI", 0x4100, 6 + len(v)) + v
    n = namn.encode("latin-1") + b"\0"
    obj = struct.pack("<HI", 0x4000, 6 + len(n) + len(mesh)) + n + mesh
    redigering = struct.pack("<HI", 0x3D3D, 6 + len(obj)) + obj
    return struct.pack("<HI", 0x4D4D, 6 + len(redigering)) + redigering


def tds_envelope(segment):
    """`envelopeprofile` i 3DS-varianten: chunk 0x8001 i objektet TRACE."""
    kropp = struct.pack("<HH", 0, len(segment))
    for punkter in segment:
        kropp += struct.pack("<H", len(punkter))
        for p in punkter:
            kropp += struct.pack("<3d", *p)
    chunk = struct.pack("<HI", 0x8001, 6 + len(kropp)) + kropp
    n = b"TRACE\0"
    obj = struct.pack("<HI", 0x4000, 6 + len(n) + len(chunk)) + n + chunk
    redigering = struct.pack("<HI", 0x3D3D, 6 + len(obj)) + obj
    return struct.pack("<HI", 0x4D4D, 6 + len(redigering)) + redigering


def tds_envelope_polylinje(punkter, skrap_efter_namn=b""):
    """`envelopeprofile` i den ANDRA 3DS-varianten: en enda polylinje.

    `skrap_efter_namn` laggs in mellan objektnamnet och chunken, precis som i
    de sju filer dar tradgangen gar sonder och lasaren maste bytesoka.
    """
    kropp = struct.pack("<IIH", 0, 1, len(punkter))
    for p in punkter:
        kropp += struct.pack("<3d", *p)
    chunk = struct.pack("<HI", 0x8001, 6 + len(kropp)) + kropp
    n = b"TRACE\0" + skrap_efter_namn
    obj = struct.pack("<HI", 0x4000, 6 + len(n) + len(chunk)) + n + chunk
    redigering = struct.pack("<HI", 0x3D3D, 6 + len(obj)) + obj
    return struct.pack("<HI", 0x4D4D, 6 + len(redigering)) + redigering


def text_envelope(punkter):
    """`envelopeprofile` i textvarianten: rakneord, punkter och kanter."""
    rader = ["9", "0", "0", "0", "1", "-2", str(len(punkter))]
    rader += ["%g %g %g" % p for p in punkter]
    rader.append(str(max(len(punkter) - 1, 0)))
    rader += ["%d %d" % (i, i + 1) for i in range(len(punkter) - 1)]
    rader += ["0", "0 ", ""]
    return "\n".join(rader).encode("latin-1")


# --- component.rsc-bitar ---------------------------------------------------

GRANSSNITT_FLODE = '''Functionality "rSimInterface"
{
Id 7
Name "%(namn)s"
Visible 1
Section 
{
Name "Section"
Frame "%(ram)s"
Fields
{
rSimFlowField
{
Name "%(faltnamn)s"
Func "TwoWayPath"
Port %(port)d
}
}
}
}
'''

GRANSSNITT_MONTERING = '''Functionality "rSimInterface"
{
Id 13
Name "%(namn)s"
Visible 1
Section 
{
Name "Hierarchy"
Frame "%(ram)s"
Fields
{
rSimHierarchyField
{
Name "Hierarchy"
Mount %(mount)d
Node "%(nod)s"
Frame "%(ram)s"
}
}
}
}
'''

RAM_UTTRYCK = '''Feature "rTransformFeature"
{
Name "Transform_%(namn)s"

Transform 
{
  Expression "Tx(%(uttryck)s)"
}
Feature "rFrameFeature"
{
Name "%(namn)s"

Visible 1
}
}
'''

RAM_MATRIS = '''Feature "rFrameFeature"
{
Name "%(namn)s"

Matrix 1 0 0 0 0 1 0 0 0 0 1 0 %(x)g %(y)g %(z)g 1 
Visible 1
}
'''

GEO_KONSTANT = '''Feature "rGeoFeature"
{
Name "%(namn)s"

Visible 1
VariableSpace
{
  Variable "rTVariable<rUri>"
  {
    Name "Uri"
    Value "%(uri)s"
  }
}
}
'''

GEO_I_UTTRYCK = '''Feature "rTransformFeature"
{
Name "Transform_geo"

Transform 
{
  Expression "Tz(Height-500)"
}
''' + GEO_KONSTANT + '''}
'''

TRANSFORM_TOMT_UTTRYCK_MED_MATRIS = '''Feature "rTransformFeature"
{
Name "Transform_%(namn)s"

Matrix 1 0 0 0 0 1 0 0 0 0 1 0 %(x)g %(y)g %(z)g 1 
Transform 
{
  Expression ""
}
%(kropp)s}
'''

TRANSFORM_TOMT_UTTRYCK_UTAN_MATRIS = '''Feature "rTransformFeature"
{
Name "Transform_%(namn)s"

Transform 
{
  Expression ""
}
%(kropp)s}
'''

RAM_BAR = '''Feature "rFrameFeature"
{
Name "%(namn)s"

Visible 1
}
'''

NOD_UTAN_OFFSET = '''Node "rSimLink"
{
Name "%(nod)s"
Id 2
NodeClass 
{
Id 2
%(kropp)s}
}
'''

NOD_MED_UTTRYCK = '''Node "rSimLink"
{
Name "%(nod)s"
Id 2
Dof  "Fixed"
Offset 
{
  Expression "Tx(BaseLength)"
}
NodeClass 
{
Id 2
%(kropp)s}
}
'''

LED = '''Node "rSimLink"
{
Name "%(namn)s"
Dof  "%(sort)s"
{
  Name "%(namn)s"
  MinLimit
  {
    Expression "%(min)g"
  }
  MaxLimit
  {
    Expression "%(max)g"
  }
}
}
'''


def rsc(namn="Prov", kropp=""):
    return ('VCMD0028041000000000COMPONENT          \n'
            'Node "rSimResource"\n{\nName "%s"\nId 1\nNodeClass \n{\nId 1\n'
            '%s}\n}\n' % (namn, kropp))


def skriv(sokvag, xml, rsc_text, extra=None):
    """Skriv ett .vcmx-arkiv. `extra` ar {postnamn: bytes}."""
    with zipfile.ZipFile(str(sokvag), "w") as z:
        z.writestr("component.rsc", rsc_text)
        z.writestr("model.xml", xml)
        z.writestr("component.dat", b'VcId "x"\n')
        z.writestr("materials.dat", b"")
        z.writestr("layout_icon.tga", b"")
        z.writestr("component_icon_preview.tga", b"")
        for namn, data in (extra or {}).items():
            z.writestr(namn, data)
    return str(sokvag)


def lada_horn(langd, bredd, hojd, x0=0.0, y0=0.0, z0=0.0):
    """De atta hornen i en ratblocksgeometri, i millimeter."""
    return [(x0 + dx * langd, y0 + dy * bredd, z0 + dz * hojd)
            for dx in (0.0, 1.0) for dy in (0.0, 1.0) for dz in (0.0, 1.0)]
