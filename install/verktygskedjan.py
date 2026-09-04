# -*- coding: utf-8 -*-
"""Hamtar verktygskedjan, med fastspikad version och kontrollerad hash.

Fas 12 i docs/spec/70_faser.md. Bakgrunden ar M-48: STruC++ lag i en
sessionskatalog och npm-paketet fanns inte langre pa maskinen. Grind 1 gick att
kora dar och da, men INTE pa en ren maskin utifran repots egna instruktioner -
vilket ar precis vad fas 10 lovar.

Ren ASCII, inklusive utskrifterna, av samma skal som resten av install/: en
Windows-konsol med cp437 kastar UnicodeEncodeError pa a-ring, och ett skript som
kraschar pa sin egen utskrift ar varre an ett som ser torftigt ut.

VARFOR HASHEN AR OBLIGATORISK
-----------------------------
En nedladdning ar den enda punkt i hela bygget dar innehallet kommer utifran.
En version som "senaste" i stallet for ett nummer, eller ett nummer utan hash,
gor bygget beroende av vad nagon annan lade upp i gar. Hashen ar inte ett skydd
mot en angripare i forsta hand - den ar ett skydd mot att kedjan tyst byter
egenskaper under oss och att en matning fran forra veckan slutar galla.

En fil som inte stammer TAS BORT och hamtningen falls. Att lamna kvar en fil
som inte stammer ar att bjuda in nasta korning att anvanda den.

MATT 2026-09-04, och det hor hemma har
--------------------------------------
strucpp-win32-arm64.zip och strucpp-win32-x64.zip i v0.6.6 har SAMMA sha256 och
samma storlek. De ar byte-identiska, och innehallet ar

    strucpp/strucpp.exe: PE32+ executable (console) x86-64, for MS Windows

ARM64-paketet ar alltsa x64-bygget. Det ar ett fel hos utgivaren, inte hos oss,
men det traffar fas 13 rakt: en Windows-maskin pa ARM skulle hamta ett paket som
inte kan kora. Posten star darfor kvar i manifestet med en uttalad varning i
stallet for att tyst utelamnas - en utelamnad post ser ut som ett format vi inte
stodjer, och det ar en annan sak an ett paket som ar fel.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile

STRUCPP_VERSION = "0.6.6"
_BAS = ("https://github.com/Autonomy-Logic/STruCpp/releases/download/v%s/"
        % STRUCPP_VERSION)

# Sa manga byte i taget nedladdningen laser. Talet ar en buffertstorlek och
# ingen troskel: det paverkar ingen dom, bara minnesatgangen.
_BLOCK = 1 << 16


class Kedjefel(Exception):
    """Hamtningen gick inte att lita pa."""


class Post(object):
    """En artefakt i kedjan.

    sort: "tar" eller "zip" for det som packas upp, "fil" for det som bara
    laddas ned. varning ar en text som ALLTID skrivs ut nar posten hamtas.
    """

    def __init__(self, namn, url, sha256, storlek, sort, ger, varning=None):
        self.namn = namn
        self.url = url
        self.sha256 = sha256
        self.storlek = storlek
        self.sort = sort
        self.ger = ger
        self.varning = varning


MANIFEST = {
    # npm-paketet. Det ar det ENDA som bar dist/index.js, och dist/index.js ar
    # det enda som skriver generated_debug.cpp och debug-map.json. Utan dem
    # bygger OpenPLC:s .so men vagrar laddas, och OPC UA-pluginet hittar inte
    # (arr, elem). Se plc/strucpp_bygg.mjs.
    "npm": Post(
        "strucpp-%s.tgz" % STRUCPP_VERSION,
        _BAS + "strucpp-%s.tgz" % STRUCPP_VERSION,
        "64baa588a70a8d36771820d8fb756fe3048fdd5f111aab38ffa7627c4e6d3519",
        2382939, "tar", "package/dist/index.js och package/libs/"),
    "linux-x64": Post(
        "strucpp-linux-x64.tar.gz", _BAS + "strucpp-linux-x64.tar.gz",
        "24e0a8108ebbdf43385635e562465050fef8370e12ed8279f28206e21f6030d1",
        27938622, "tar", "strucpp/strucpp och strucpp/runtime/include"),
    "linux-arm64": Post(
        "strucpp-linux-arm64.tar.gz", _BAS + "strucpp-linux-arm64.tar.gz",
        "7dcc1b78f297c09240f7bde506a32e7c731953ef50f9a9f826f4bc141edf1825",
        27449063, "tar", "strucpp/strucpp och strucpp/runtime/include"),
    "win32-x64": Post(
        "strucpp-win32-x64.zip", _BAS + "strucpp-win32-x64.zip",
        "13ea67232f1e7023be605b8f659152c632a040afd94b786b25bdafcdba9c13f3",
        22256729, "zip", "strucpp/strucpp.exe och strucpp/runtime/include"),
    "win32-arm64": Post(
        "strucpp-win32-arm64.zip", _BAS + "strucpp-win32-arm64.zip",
        "13ea67232f1e7023be605b8f659152c632a040afd94b786b25bdafcdba9c13f3",
        22256729, "zip", "strucpp/strucpp.exe och strucpp/runtime/include",
        varning=("VARNING: MATT 2026-09-04. Den har filen ar BYTE-IDENTISK med "
                 "win32-x64, och innehallet ar en PE32+ x86-64-binar. "
                 "ARM64-paketet ar x64-bygget. Utgivarens fel, inte vart. "
                 "Anvand den inte pa Windows ARM.")),
    "darwin-x64": Post(
        "strucpp-darwin-x64.zip", _BAS + "strucpp-darwin-x64.zip",
        "2257c960bfcb355c65b0602822f534dd68531428fefcd05f3fe33babf83e6ab0",
        23816569, "zip", "strucpp/strucpp och strucpp/runtime/include"),
    "darwin-arm64": Post(
        "strucpp-darwin-arm64.zip", _BAS + "strucpp-darwin-arm64.zip",
        "65c49874b56f2553667ea0765e0d35a7362dc0b4f06db86d2f6af542f32b61ce",
        22636388, "zip", "strucpp/strucpp och strucpp/runtime/include"),
}

# OpenPLC Runtime v4. Avbilden hamtas av docker och inte av oss, sa posten ar
# en LAST DIGEST och inte en fil. En tagg ar inget lofte; digesten ar det.
OPENPLC_AVBILD = ("ghcr.io/autonomy-logic/openplc-runtime@sha256:"
                  "40726c99d041ae9d7e21172e9cf5b0d740e8b0bd01b8b77e4c524cc738bc1435")

# npm-paketets lasfil, vendorad i repot.
#
# MATT 2026-09-04: paketet levereras UTAN package-lock.json och deklarerar
# "chevrotain": "^11.0.0" - ett intervall, inte ett nummer. Ett npm install mot
# det intervallet hamtar vad som rakar vara senast, vilket ar exakt det den har
# modulen finns for att hindra. Lasfilen ar skapad en gang, granskad, och ligger
# nu i repot; npm ci laser den och kontrollerar varje paket mot dess
# integritetshash.
#
# --ignore-scripts ar inte pynt: paketets prepare-skript kor husky, som faller
# har och som i vilket fall inte ska fa kora godtycklig kod under en
# installation. Med --omit=dev blir det 7 paket och 5,0 MB.
LASFIL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "strucpp-%s-package-lock.json" % STRUCPP_VERSION)


def plattformsnyckel(plattform=None, maskin=None):
    """Nyckeln i MANIFEST for den har maskinen.

    Fails closed: en okand kombination far inget svar. Att gissa "det ar nog
    linux-x64" ar att lada ned fel binar och upptacka det langt senare.
    """
    p = (plattform or sys.platform).lower()
    m = (maskin or os.uname().machine if hasattr(os, "uname") else "").lower()
    if p.startswith("linux"):
        familj = "linux"
    elif p.startswith("win"):
        familj = "win32"
    elif p == "darwin":
        familj = "darwin"
    else:
        raise Kedjefel("okand plattform %r; manifestet har %s"
                       % (p, ", ".join(sorted(MANIFEST))))
    if m in ("x86_64", "amd64", "x64"):
        arkitektur = "x64"
    elif m in ("aarch64", "arm64"):
        arkitektur = "arm64"
    else:
        raise Kedjefel("okand arkitektur %r" % (m,))
    nyckel = "%s-%s" % (familj, arkitektur)
    if nyckel not in MANIFEST:
        raise Kedjefel("ingen post for %s" % nyckel)
    return nyckel


def _summa(sokvag):
    h = hashlib.sha256()
    with open(sokvag, "rb") as f:
        while True:
            bit = f.read(_BLOCK)
            if not bit:
                break
            h.update(bit)
    return h.hexdigest()


def kontrollera(sokvag, post):
    """Sant om filen stammer. Fels om den inte gor det, och TAR BORT den."""
    storlek = os.path.getsize(sokvag)
    summa = _summa(sokvag)
    if storlek == post.storlek and summa == post.sha256:
        return True
    os.remove(sokvag)
    raise Kedjefel(
        "%s stammer inte och ar borttagen.\n  vantade %d byte, sha256 %s\n"
        "  fick    %d byte, sha256 %s"
        % (post.namn, post.storlek, post.sha256, storlek, summa))


def hamta(nyckel, cache, skriv=print):
    """Hamtar posten om den saknas, kontrollerar den alltid, lamnar sokvagen."""
    if nyckel not in MANIFEST:
        raise Kedjefel("okand post %r; manifestet har %s"
                       % (nyckel, ", ".join(sorted(MANIFEST))))
    post = MANIFEST[nyckel]
    if post.varning:
        skriv(post.varning)
    os.makedirs(cache, exist_ok=True)
    mal = os.path.join(cache, post.namn)
    if os.path.exists(mal):
        kontrollera(mal, post)
        skriv("redan hamtad och kontrollerad: %s" % post.namn)
        return mal
    skriv("hamtar %s (%.1f MB)" % (post.namn, post.storlek / 1e6))
    delvis = mal + ".delvis"
    try:
        with urllib.request.urlopen(post.url, timeout=300) as svar, \
                open(delvis, "wb") as ut:
            shutil.copyfileobj(svar, ut, _BLOCK)
    except (urllib.error.URLError, OSError) as fel:
        if os.path.exists(delvis):
            os.remove(delvis)
        raise Kedjefel("kunde inte hamta %s: %s" % (post.url, fel))
    os.rename(delvis, mal)
    kontrollera(mal, post)
    skriv("kontrollerad: %s" % post.namn)
    return mal


def packa_upp(arkiv, post, mal):
    """Packar upp under `mal`. Vagrar poster som pekar utanfor.

    En arkivpost som heter ../../nagot ar inte en egenhet utan ett angrepp, och
    tarfile gor det glatt om ingen sager ifran.
    """
    os.makedirs(mal, exist_ok=True)
    absmal = os.path.abspath(mal)
    if post.sort == "tar":
        with tarfile.open(arkiv, "r:gz") as t:
            for medlem in t.getmembers():
                dit = os.path.abspath(os.path.join(absmal, medlem.name))
                if not dit.startswith(absmal + os.sep) and dit != absmal:
                    raise Kedjefel("arkivposten %r pekar utanfor malet"
                                   % medlem.name)
            # filter="data" finns fran 3.12 och blir standard i 3.14. Den
            # avvisar specialfiler, absoluta sokvagar och lankar utat. Var egen
            # kontroll ovan star kvar: tva grindar pa samma sak ar rimligt nar
            # den ena kommer fran biblioteket och kan andras under oss.
            if sys.version_info >= (3, 12):
                t.extractall(absmal, filter="data")
            else:
                t.extractall(absmal)
    elif post.sort == "zip":
        with zipfile.ZipFile(arkiv) as z:
            for namn in z.namelist():
                dit = os.path.abspath(os.path.join(absmal, namn))
                if not dit.startswith(absmal + os.sep) and dit != absmal:
                    raise Kedjefel("arkivposten %r pekar utanfor malet" % namn)
            z.extractall(absmal)
    else:
        raise Kedjefel("posten %s packas inte upp" % post.namn)
    return absmal


def installera_beroenden(paketkatalog, npm="npm", skriv=print):
    """Kor npm ci mot den vendorade lasfilen. Utan den gar dist/index.js inte.

    Paketet importerar chevrotain vid korning, och utan node_modules faller
    kompilatorn med ERR_MODULE_NOT_FOUND mitt i ett bygge - alltsa langt efter
    att hamtningen sagt sig ha lyckats. Steget hor darfor till hamtningen.
    """
    if not os.path.exists(LASFIL):
        raise Kedjefel("lasfilen saknas pa %s" % LASFIL)
    shutil.copyfile(LASFIL, os.path.join(paketkatalog, "package-lock.json"))
    skriv("installerar beroenden med npm ci (last, utan skript)")
    try:
        k = subprocess.run(
            [npm, "ci", "--omit=dev", "--ignore-scripts", "--no-audit",
             "--no-fund"],
            cwd=paketkatalog, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=900)
    except OSError as fel:
        raise Kedjefel("kunde inte starta %s: %s. Node behovs for STruC++."
                       % (npm, fel))
    except subprocess.TimeoutExpired:
        raise Kedjefel("npm ci svarade inte inom 900 s")
    if k.returncode != 0:
        raise Kedjefel("npm ci foll (kod %d):\n%s"
                       % (k.returncode,
                          k.stdout.decode("utf-8", "replace").strip()))
    moduler = os.path.join(paketkatalog, "node_modules")
    if not os.path.isdir(moduler):
        raise Kedjefel("npm ci sa lyckat men lamnade ingen node_modules")
    return moduler


def stall_upp(cache, mal, nyckel=None, skriv=print, npm="npm"):
    """Hela kedjan for den har maskinen: npm-paketet och plattformsbygget."""
    nyckel = nyckel or plattformsnyckel()
    ut = {}
    for n in ("npm", nyckel):
        arkiv = hamta(n, cache, skriv=skriv)
        ut[n] = packa_upp(arkiv, MANIFEST[n], os.path.join(mal, n))
    paketkatalog = os.path.join(ut["npm"], "package")
    installera_beroenden(paketkatalog, npm=npm, skriv=skriv)
    ut["strucpp_paket"] = paketkatalog
    ut["openplc_avbild"] = OPENPLC_AVBILD
    ut["plattform"] = nyckel
    return ut


def _argument(argv=None):
    p = argparse.ArgumentParser(
        description="Hamtar verktygskedjan med kontrollerad hash.")
    p.add_argument("--cache", default=os.path.join(
        os.path.expanduser("~"), ".cache", "vc_assist", "verktygskedjan"))
    p.add_argument("--mal", default=None,
                   help="dit arkiven packas upp (standard: <cache>/uppackat)")
    p.add_argument("--plattform", default=None,
                   help="tvinga en manifestnyckel, t.ex. win32-x64")
    p.add_argument("--lista", action="store_true",
                   help="skriv manifestet och sluta")
    return p.parse_args(argv)


def main(argv=None):
    a = _argument(argv)
    if a.lista:
        for nyckel in sorted(MANIFEST):
            post = MANIFEST[nyckel]
            print("%-14s %-32s %10d  %s" % (nyckel, post.namn, post.storlek,
                                            post.sha256[:16]))
            if post.varning:
                print("               %s" % post.varning)
        print("openplc        %s" % OPENPLC_AVBILD)
        return 0
    mal = a.mal or os.path.join(a.cache, "uppackat")
    try:
        ut = stall_upp(a.cache, mal, a.plattform)
    except Kedjefel as fel:
        print("FEL: %s" % fel)
        return 1
    print(json.dumps(ut, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
