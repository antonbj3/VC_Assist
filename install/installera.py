#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kommandoraden for installationen av VC Assist-tillagget.

    python3 install/installera.py sok
    python3 install/installera.py installera
    python3 install/installera.py verifiera
    python3 install/installera.py avinstallera

Utan flaggor soker den upp VC sjalv och tar den NYASTE versionen den hittar.
Alla funna versioner skrivs ut, sa valet gar att gora om med --vc-version.

Endast standardbiblioteket, ren ASCII i utskrifterna, ingenting Wine-specifikt.
Slutkoder: 0 = klart, 1 = fel, 2 = hittade ingen VC-installation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from install import paket, upptackt
else:
    from . import paket, upptackt

KLART = 0
FEL = 1
INGEN_VC = 2


# --------------------------------------------------------------------------
# Mal
# --------------------------------------------------------------------------

class Mal(object):
    """En plats att installera i, med allt som behovs for att beratta om den."""

    def __init__(self, malmapp, pythonniva="", nivakalla="", vc_version="",
                 motivering=""):
        self.malmapp = os.path.abspath(malmapp)
        self.pythonniva = pythonniva
        self.nivakalla = nivakalla
        self.vc_version = vc_version
        self.motivering = motivering

    @property
    def matt_sokvag(self):
        return upptackt.sokvagen_ar_matt(self.vc_version, self.pythonniva)

    def sokvagsdom(self):
        if self.matt_sokvag:
            return "MATT: exakt den har sokvagen ar kord i VC 4.10 (M-01)"
        return ("OPROVAD SOKVAG: %s + %s ar inte kord av oss. Kontrollera att "
                "bryggan loggar sin start - VC sager inget om ett tillagg som "
                "inte laddas (M-01, M-09)" % (self.vc_version or "okand version",
                                              self.pythonniva or "okand niva"))


def _harled_ur_malsokvag(malmapp):
    """Niva och version ur en sokvag som anvandaren angav sjalv.

    Formen ar ``.../<version>/My Commands/<Python N>/<paket>``. Stammer den
    inte lamnas faltet tomt - vi hittar pa ingenting.
    """
    delar = os.path.abspath(malmapp).replace("\\", "/").split("/")
    niva = ""
    version = ""
    if len(delar) >= 2 and upptackt.pythonnivanamn(delar[-2]):
        niva = delar[-2]
    if len(delar) >= 4 and delar[-3] == upptackt.MY_COMMANDS:
        version = delar[-4]
    return niva, version


def mal_ur_argument(args, miljo):
    """(mal att arbeta mot, alla funna VC-mappar). Kastar med lasbart skal."""
    if args.mal:
        niva, version = _harled_ur_malsokvag(args.mal)
        return [Mal(args.mal,
                    pythonniva=args.python_niva or niva,
                    nivakalla="--mal" if not args.python_niva else "vald",
                    vc_version=version,
                    motivering="angiven med --mal")], []

    mappar = upptackt.vcmappar(miljo)
    if not mappar:
        return [], []

    if args.alla:
        valda = mappar
    else:
        vald = upptackt.valj_vcmapp(mappar, getattr(args, "vc_version", None))
        if vald is None:
            raise paket.InstallationsFel(
                "ingen VC-mapp med versionen %r. Funna: %s"
                % (args.vc_version, ", ".join(sorted({m.version for m in mappar}))))
        valda = [vald]

    ut = []
    for m in valda:
        val = upptackt.valj_pythonniva(m, getattr(args, "python_niva", None))
        ut.append(Mal(os.path.join(m.my_commands, val.namn, paket.PAKETNAMN),
                      pythonniva=val.namn, nivakalla=val.kalla,
                      vc_version=m.version, motivering=val.motivering))
    return ut, mappar


# --------------------------------------------------------------------------
# sok
# --------------------------------------------------------------------------

def _installationsrad(malmapp):
    try:
        manifest = paket.las_manifest(malmapp)
    except paket.InstallationsFel as e:
        return "manifest trasigt: %s" % e
    if manifest is None:
        if os.path.isdir(malmapp):
            return ("mappen finns men saknar manifest - nagon har lagt dit "
                    "filer for hand; en installation harifran tar over den")
        return "inte installerat"
    return "installerat %s (%d filer)" % (manifest.get("installerad", "?"),
                                          len(manifest.get("filer", {})))


def kommando_sok(args, miljo, skriv):
    res = upptackt.sok(miljo)

    if args.json:
        skriv(json.dumps({
            "plattform": miljo.plattform,
            "dokumentrotter": [{"sokvag": r.sokvag, "kallor": list(r.kallor)}
                               for r in res.dokumentrotter],
            "vcmappar": [{"foretag": m.foretag, "version": m.version,
                          "my_commands": m.my_commands,
                          "pythonnivaer": list(m.pythonnivaer),
                          "kallor": list(m.kallor)} for m in res.vcmappar],
            "programinstallationer": [{"sokvag": p.sokvag, "produkt": p.produkt,
                                       "pythonnivaer": list(p.pythonnivaer)}
                                      for p in res.programinstallationer],
            "varningar": res.varningar,
        }, indent=2, sort_keys=True))
        return KLART if res.vcmappar else INGEN_VC

    skriv("plattform: %s" % miljo.plattform)
    skriv("")
    skriv("Dokumentmappar (%d):" % len(res.dokumentrotter))
    for r in res.dokumentrotter:
        skriv("  %s" % r.sokvag)
        for kalla in r.kallor:
            skriv("      hittad via %s" % kalla)
    if not res.dokumentrotter:
        skriv("  (ingen)")

    skriv("")
    skriv("VC-mappar (%d), nyaste forst:" % len(res.vcmappar))
    for m in res.vcmappar:
        skriv("  %s %s" % (m.foretag, m.version))
        skriv("      %s" % m.my_commands)
        skriv("      Python-nivaer pa disk: %s"
              % (", ".join(m.pythonnivaer) if m.pythonnivaer else "ingen"))
        for niva in (m.pythonnivaer or ()):
            malmapp = os.path.join(m.my_commands, niva, paket.PAKETNAMN)
            skriv("      %s/%s: %s" % (niva, paket.PAKETNAMN, _installationsrad(malmapp)))
    if not res.vcmappar:
        skriv("  (ingen)")

    skriv("")
    skriv("VC-installationer pa disk (%d):" % len(res.programinstallationer))
    for p in res.programinstallationer:
        skriv("  %s" % p.produkt)
        skriv("      %s" % p.sokvag)
        skriv("      Python-nivaer med api.xml: %s" % ", ".join(p.pythonnivaer))
    if not res.programinstallationer:
        skriv("  (ingen)")

    if res.varningar:
        skriv("")
        skriv("Varningar (%d):" % len(res.varningar))
        for v in res.varningar:
            skriv("  %s" % v)

    if not res.vcmappar:
        skriv("")
        skriv("Ingen VC-mapp hittad. Peka ut malet sjalv:")
        skriv("  python3 install/installera.py installera "
              "--mal '<Documents>/Visual Components/<version>/My Commands/Python 2/%s'"
              % paket.PAKETNAMN)
        return INGEN_VC
    return KLART


# --------------------------------------------------------------------------
# installera / avinstallera / verifiera
# --------------------------------------------------------------------------

def _skriv_ovriga(mal, vcmappar, skriv):
    """Allt annat som hittades rapporteras aven nar bara ett mal installerades.

    Versionen racker inte som skiljetecken: pa den har maskinen finns TVA
    mappar for 4.10, en i arbetsprefixet och en i testprefixet, och en rapport
    som bara namner versioner hade sett ut som om det fanns ett enda val.
    """
    ovriga = [m for m in vcmappar
              if os.path.abspath(m.my_commands) != os.path.dirname(
                  os.path.dirname(mal.malmapp))]
    if not ovriga:
        return
    skriv("  Ovriga funna VC-mappar (%d), INTE rorda:" % len(ovriga))
    for m in ovriga:
        skriv("      %s  %s" % (m.version, m.my_commands))
    skriv("  Valj en annan med --vc-version, ta alla med --alla, eller peka "
          "ut mappen med --mal.")


def kommando_installera(args, miljo, skriv):
    mal, vcmappar = mal_ur_argument(args, miljo)
    if not mal:
        skriv("Hittade ingen VC-mapp att installera i. Kor 'python3 install/installera.py sok' for att se vad som hittades, eller ange malet direkt med --mal '<sokvag>'.")
        return INGEN_VC

    for m in mal:
        skriv("Installerar i %s" % m.malmapp)
        skriv("  VC-version: %s   niva: %s (%s: %s)"
              % (m.vc_version or "okand", m.pythonniva or "okand",
                 m.nivakalla or "?", m.motivering or "-"))
        skriv("  %s" % m.sokvagsdom())
        rapport = paket.installera(
            m.malmapp, kalla=args.kalla, pythonniva=m.pythonniva,
            vc_version=m.vc_version, nivakalla=m.nivakalla,
            sokvagen_ar_matt=m.matt_sokvag)
        skriv("  nya: %d   uppdaterade: %d   oforandrade: %d   borttagna: %d"
              % (len(rapport.nya), len(rapport.uppdaterade),
                 len(rapport.oforandrade), len(rapport.borttagna)))
        if rapport.borttagna:
            skriv("  borttagna foraldralosa: %s" % ", ".join(rapport.borttagna))
        skriv("  verifierat pa plats: %d filer parsar och kompilerar" % rapport.antal)
        if not args.alla and not args.mal:
            _skriv_ovriga(m, vcmappar, skriv)

    skriv("")
    skriv("Klart. Starta VC och las vc_assist_boot.log i VC:s egen "
          "anvandarmapp (under Wine: <prefix>/drive_c/users/<du>/). Star det "
          "ingenting dar har tillagget inte laddats - VC sager inget sjalv "
          "om ett tillagg som inte gick att ladda (M-01, M-09).")
    return KLART


def kommando_avinstallera(args, miljo, skriv):
    mal, _vcmappar = mal_ur_argument(args, miljo)
    if not mal:
        skriv("Hittade ingen VC-mapp. Kor 'python3 install/installera.py sok' for detaljer, eller ange --mal.")
        return INGEN_VC
    hittade_nagot = False
    for m in mal:
        if paket.las_manifest(m.malmapp) is None:
            skriv("%s: ingen installation (inget manifest funnet). Ange mappen dar tillagget installerats med --mal." % m.malmapp)
            continue
        hittade_nagot = True
        rapport = paket.avinstallera(m.malmapp)
        skriv("Avinstallerade %s" % m.malmapp)
        skriv("  borttagna filer: %d   bytekod: %d"
              % (len(rapport.borttagna), len(rapport.bytekod)))
        if rapport.saknades:
            skriv("  stod i manifestet men fanns inte: %s" % ", ".join(rapport.saknades))
        if rapport.andrade:
            skriv("  andrade sedan installationen (togs bort anda): %s"
                  % ", ".join(rapport.andrade))
        if rapport.kvar:
            skriv("  LAMNADE KVAR (inte vara): %s" % ", ".join(rapport.kvar))
            skriv("  mappen star kvar for de filernas skull")
        for mapp in rapport.mappar_borttagna:
            skriv("  tog bort tom mapp: %s" % mapp)
    return KLART if hittade_nagot else FEL


def kommando_verifiera(args, miljo, skriv):
    mal, _vcmappar = mal_ur_argument(args, miljo)
    if not mal:
        skriv("Hittade ingen VC-mapp. Kor 'python3 install/installera.py sok' for detaljer, eller ange --mal.")
        return INGEN_VC
    slutkod = KLART
    for m in mal:
        rapport = paket.kontrollera(m.malmapp, kalla=args.kalla)
        skriv("%s" % m.malmapp)
        if not rapport.installerad:
            skriv("  inte installerat (inget manifest funnet). Kor 'installera' forst eller ange --mal.")
            slutkod = FEL
            continue
        skriv("  installerad: %s" % rapport.manifest.get("installerad", "?"))
        skriv("  filer: %d" % len(rapport.manifest.get("filer", {})))
        skriv("  samma som repots kalla: %s" % ("ja" if rapport.aktuell else "NEJ"))
        if rapport.problem:
            slutkod = FEL
            for p in rapport.problem:
                skriv("  PROBLEM: %s" % p)
        else:
            skriv("  alla filer parsar och kompilerar")
    return slutkod


# --------------------------------------------------------------------------
# Kommandoraden
# --------------------------------------------------------------------------

def skapa_argparser():
    p = argparse.ArgumentParser(
        prog="installera.py",
        description="Installera VC Assist-tillagget i Visual Components.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Slutkoder: 0 klart, 1 fel, 2 ingen VC hittad.")
    under = p.add_subparsers(dest="kommando")

    def gemensamt(sp, med_val=True):
        sp.add_argument("--mal", metavar="MAPP",
                        help="exakt mappen dar paketet ska ligga, t.ex. "
                             "'.../My Commands/Python 2/%s'. Stanger av sokningen."
                             % paket.PAKETNAMN)
        sp.add_argument("--prefix", metavar="MAPP", action="append", default=[],
                        help="ytterligare wine-prefix att soka i (kan upprepas)")
        sp.add_argument("--json", action="store_true", help="maskinlasbar utdata")
        if med_val:
            sp.add_argument("--vc-version", metavar="X.Y",
                            help="valj version i stallet for den nyaste")
            sp.add_argument("--python-niva", metavar="'Python N'",
                            help="tvinga Python-nivan under My Commands")
            sp.add_argument("--alla", action="store_true",
                            help="arbeta mot alla funna VC-versioner")
            sp.add_argument("--kalla", metavar="MAPP", default=None,
                            help="annan kallmapp an ext/vc_addon/%s" % paket.PAKETNAMN)

    sok = under.add_parser("sok", help="visa vad som finns, skriv ingenting")
    gemensamt(sok, med_val=False)

    inst = under.add_parser("installera", help="lagg tillagget pa plats")
    gemensamt(inst)

    ver = under.add_parser("verifiera", help="kontrollera en befintlig installation")
    gemensamt(ver)

    av = under.add_parser("avinstallera", help="ta bort exakt det som installerades")
    gemensamt(av)
    return p


def main(argv=None, skriv=None, miljo=None):
    if skriv is None:
        def skriv(rad):
            print(rad)
    parser = skapa_argparser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if not args.kommando:
        parser.print_help()
        return FEL

    for namn, standard in (("vc_version", None), ("python_niva", None),
                           ("alla", False), ("kalla", None), ("mal", None)):
        if not hasattr(args, namn):
            setattr(args, namn, standard)

    if miljo is None:
        miljo = upptackt.Miljo(extra_prefix=args.prefix)
    kommandon = {
        "sok": kommando_sok,
        "installera": kommando_installera,
        "verifiera": kommando_verifiera,
        "avinstallera": kommando_avinstallera,
    }
    try:
        slutkod = kommandon[args.kommando](args, miljo, skriv)
    except paket.InstallationsFel as e:
        skriv("FEL: %s" % e)
        return FEL
    except upptackt.IngenNiva as e:
        skriv("FEL: %s" % e)
        return FEL

    if miljo.varningar and args.kommando != "sok" and not args.json:
        for v in miljo.varningar:
            skriv("varning: %s" % v)
    return slutkod


if __name__ == "__main__":
    sys.exit(main())
