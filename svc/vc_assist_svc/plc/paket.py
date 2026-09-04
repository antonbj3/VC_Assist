# -*- coding: utf-8 -*-
"""Från ST-text till det projektarkiv OpenPLC v4 tar emot.

Kedjan, mätt hela vägen 2026-09-04 (docs/matningar/M-20_plcbandet.md):

    ST-text --STruC++--> generated.cpp/.hpp + generated_debug.cpp + debug-map.json
            --paket-->   projekt.zip
            --REST-->    runtime: kompilerar .so, laddar, kör

Vad arkivet **måste** innehålla, var och en mätt genom att den saknades och
bygget föll med det citerade felet:

* `generated.hpp` och minst en `.cpp` — `scripts/compile.sh` i runtimen
  kontrollerar dem uttryckligen och avbryter med "Missing required source files".
* `defines.h` med `PROGRAM_MD5` — annars:
  "No rule to make target 'core/generated/defines.h'".
* `generated_debug.cpp` — annars bygger .so:n men laddas inte:
  "undefined symbol: _ZN7strucpp5debug17debug_array_countE".
* `strucpp_runtime/include/` — runtimen vendorar inte strucpp:s headers, de
  följer med varje uppladdning (core/strucpp_runtime/README.md).
* `conf/opcua.json` — utan en conf-katalog stängs **alla** plugins av:
  "No conf directory found in core/generated, disabling all plugins".
  Med filen på plats: "Final state - opcua: enabled=True".

Endast standardbiblioteket. Kompilatorn är en extern binär och körs som en
delprocess; det är grind 1 i docs/spec/50_grindar.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# Namnen runtimen letar efter. KOD@HEAD: scripts/compile.sh och
# scripts/Makefile.strucpp i OpenPLC v4.2.1.
GENERERAD_CPP = "generated.cpp"
GENERERAD_HPP = "generated.hpp"
DEBUGTABELL = "generated_debug.cpp"
DEBUGKARTA = "debug-map.json"
DEFINES = "defines.h"
RUNTIME_UNDERKATALOG = os.path.join("strucpp_runtime", "include")
CONF_UNDERKATALOG = "conf"

# Filer som ligger i arkivet men inte i core/generated hos runtimen. debug-map
# är vår egen bokföring: runtimen läser den aldrig, den binder mot
# generated_debug.cpp. Att skicka med den vore att lägga en fil i
# byggkatalogen som ingen konsument har (regel S3).
EJ_I_ARKIVET = (DEBUGKARTA,)

# Bastick för PLC-uppgiften. 20 ms är OpenPLC-editorns egen standardperiod och
# den period hela M-20:s tur-och-retur-mätning är gjord med; talet är alltså
# mätningens förutsättning, inte ett optimum. Byts det måste M-20 mätas om.
TASKINTERVALL = "T#20ms"

# Pragmat ST-lagrets skrivare sätter på en säkerhetsmärkt deklaration
# ({SAKERHET}, invariant I15). **MÄTT 2026-09-04:** STruC++ 0.6.6 känner inte
# igen IEC 61131-3:s pragmaklamrar och avvisar filen:
#   unexpected character: ->{<- at offset: 52, skipped 1 characters.
# Märket bärs alltså av signalkartan och av texten i repot, men skalas av på
# vägen till kompilatorn. Exakt den strängen tas bort, inte allt inom klamrar:
# en bredare regel hade kunnat äta ett strängliteral.
SAKERHETSPRAGMA = "{SAKERHET}"

# Programinstansens namn i CONFIGURATION. Det syns i debugkartans sökvägar
# ("INST0.UT"), så det är inte kosmetiskt: uppslaget mot kartan använder det.
INSTANSNAMN = "Inst0"


class Byggfel(Exception):
    """Bygget vägrar leverera ett halvt paket."""


@dataclass(frozen=True)
class Lov:
    """Ett löv i kompilatorns debugkarta: en variabel med sin plats.

    (arr, elem) är precis det par OPC UA-plugin adresserar minnet med
    (core/src/drivers/plugins/python/opcua/opcua_memory.py). Paret går inte
    att härleda ur den lokaliserade adressen — det är kompilatorns numrering
    av programmets variabler.
    """

    sokvag: str
    arr: int
    elem: int
    typ: str
    storlek: int


@dataclass(frozen=True)
class Debugkarta:
    version: int
    md5: str
    lov: Tuple[Lov, ...]

    def slag_upp(self, sokvag: str) -> Optional[Lov]:
        nyckel = sokvag.upper()
        for l in self.lov:
            if l.sokvag.upper() == nyckel:
                return l
        return None

    def for_tagg(self, tagg: str, instans: str = INSTANSNAMN) -> Lov:
        """Löv för en tagg i stationens programinstans.

        Kastar hellre än returnerar None: ett saknat löv betyder att OPC
        UA-noden hade pekat på fel minne, och en nod som pekar fel är värre
        än ingen nod (I3).
        """
        sokvag = "%s.%s" % (instans, tagg)
        lov = self.slag_upp(sokvag)
        if lov is None:
            kanda = ", ".join(l.sokvag for l in self.lov)
            raise Byggfel("debugkartan har inget löv för %s; den känner %s"
                          % (sokvag, kanda or "ingenting"))
        return lov

    @staticmethod
    def fran_json(data: object) -> "Debugkarta":
        if not isinstance(data, dict) or "leaves" not in data:
            raise Byggfel("debug-map.json saknar leaves")
        lov = []
        for l in data["leaves"]:
            lov.append(Lov(sokvag=l["path"], arr=int(l["arrayIdx"]),
                           elem=int(l["elemIdx"]), typ=l["type"],
                           storlek=int(l["size"])))
        return Debugkarta(int(data.get("version", 0)), str(data.get("md5", "")),
                          tuple(lov))

    @staticmethod
    def las_fil(sokvag: str) -> "Debugkarta":
        with open(sokvag, "r", encoding="utf-8") as f:
            return Debugkarta.fran_json(json.load(f))


def konfigurationstext(station: str, instans: str = INSTANSNAMN,
                       intervall: str = TASKINTERVALL) -> str:
    """CONFIGURATION-delen. ST-lagrets modell beskriver POU:er, inte
    konfigurationer, så den här delen är text och ingenting annat.

    Ett program utan CONFIGURATION har ingen uppgift att köra i, och
    STruC++ ger då en .so utan tasks: runtimen startar och gör ingenting.
    """
    return ("\nCONFIGURATION Config0\n"
            "    RESOURCE Res0 ON PLC\n"
            "        TASK Main(INTERVAL := %s, PRIORITY := 0);\n"
            "        PROGRAM %s WITH Main : %s;\n"
            "    END_RESOURCE\n"
            "END_CONFIGURATION\n" % (intervall, instans, station))


def for_kompilator(st_text: str) -> str:
    """Texten som STruC++ ska få: samma program, utan säkerhetspragmat.

    Det är en avsiktlig, mätt asymmetri och inte två sanningar: märket säger
    "agenten får inte skriva den här taggen", vilket är en regel för grind 2
    och 3, inte för kodgenereringen. Kompilatorn får samma deklarationer,
    samma adresser och samma kropp.
    """
    return st_text.replace(" " + SAKERHETSPRAGMA, "").replace(SAKERHETSPRAGMA, "")


@dataclass(frozen=True)
class Kompileringsdom:
    """Grind 1:s svar, och kompilatorns EGNA ord (I1).

    `ok` är kompilatorns utgångskod, inte vår tolkning av dess text.
    """

    ok: bool
    utdata: str
    returkod: int

    def __str__(self) -> str:
        return ("GRIND 1 GODKAND" if self.ok
                else "GRIND 1 FALLDE (kod %d)\n%s" % (self.returkod, self.utdata))


def granska_kompilering(st_text: str, utkatalog: str, strucpp_cli: str,
                        tidsgrans: float = 300.0,
                        fullt_bygge: bool = True) -> Kompileringsdom:
    """Grind 1 med STruC++:s CLI: kompilerar koden, ja eller nej.

    **Detta är inte `kompilera`.** CLI:t i 0.6.6 skriver bara generated.cpp och
    generated.hpp; det skriver aldrig generated_debug.cpp eller debug-map.json,
    och båda behövs för att LADDA koden i OpenPLC (se strucpp_bygg.mjs). Den
    här funktionen svarar alltså på grind 1:s fråga — *går den att bygga?* —
    och på ingenting mer. Att låta den svara på driftsättningsfrågan hade varit
    en grind som blir billig och slutar mäta sin egen storhet.

    Skälet att den ändå finns: grind 1 ska kunna köras av var och en som har
    kompilatorn, utan npm-paketet och utan en OpenPLC-container. En grind som
    kräver hela driftmiljön körs sällan, och en grind som körs sällan mäter
    ingenting.

    **MÄTT (M-48):** CLI:t returnerar 0 vid lyckad kompilering och 1 vid fel,
    och skriver ingen utdatafil när det faller. Utgångskoden är alltså läsbar,
    och texten behöver inte tolkas.

    ## Varför `fullt_bygge` är sant som standard

    **MÄTT (M-54).** Enbart översättning är en svagare grind än den ser ut. Ett
    program med `c(CU := i, RESET := r, PV := 3)` översätts med utgångskod **0**
    och texten "Compilation successful!" — men den C++ som skrevs går inte att
    bygga: `class strucpp::CTU has no member named RESET`. Grinden hade alltså
    sagt GODKÄND om kod som ingen PLC kan köra.

    Med `--build` kompileras C++:en också, och samma program faller med kod 1.

    Kostnaden är mätt över tre körningar vardera: **0,32–0,34 s** för enbart
    översättning mot **1,97–2,02 s** för fullt bygge. Sex gånger dyrare, och
    värt det: 1,7 sekunder är billigare än ett reparationsvarv mot en modell,
    och oändligt mycket billigare än ett falskt godkänt program.

    Sätt `fullt_bygge=False` bara när frågan verkligen är "går den att
    översätta" och inte "går den att köra" — och skriv då ut vilken fråga som
    ställdes.
    """
    if not os.path.exists(strucpp_cli):
        raise Byggfel("hittar inte STruC++-CLI:t på %s" % strucpp_cli)
    os.makedirs(utkatalog, exist_ok=True)
    stfil = os.path.join(utkatalog, "program.st")
    with open(stfil, "w", encoding="ascii", newline="\n") as f:
        f.write(for_kompilator(st_text))
    argv = [strucpp_cli, stfil, "-o", os.path.join(utkatalog, "generated.cpp")]
    if fullt_bygge:
        argv.append("--build")
    try:
        korning = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=tidsgrans)
    except OSError as fel:
        raise Byggfel("kunde inte starta %s: %s" % (strucpp_cli, fel))
    except subprocess.TimeoutExpired:
        raise Byggfel("STruC++ svarade inte inom %.0f s" % tidsgrans)
    return Kompileringsdom(korning.returncode == 0,
                           korning.stdout.decode("utf-8", "replace").strip(),
                           korning.returncode)


def kompilera(st_text: str, utkatalog: str, strucpp_paket: str,
              node: str = "node", tidsgrans: float = 300.0) -> Debugkarta:
    """Grind 1: kompilera ST till C++ och skriv de fyra artefakterna.

    `strucpp_paket` är den uppackade npm-katalogen för strucpp (den som har
    dist/ och libs/). Sökvägen är ett argument, aldrig en konstant: koden ska
    gå på Windows och under Wine lika väl (I16).
    """
    for vad, sokvag in (("strucpp-paketet", strucpp_paket),
                        ("dist/index.js", os.path.join(strucpp_paket, "dist", "index.js"))):
        if not os.path.exists(sokvag):
            raise Byggfel("hittar inte %s på %s" % (vad, sokvag))
    os.makedirs(utkatalog, exist_ok=True)
    kompilatortext = for_kompilator(st_text)
    stfil = os.path.join(utkatalog, "program.st")
    # newline="\n" ar inte kosmetik. Utan den oversatter Python textlaget varje
    # \n till \r\n pa Windows, och da ar filen kompilatorn laser INTE de bytes
    # md5:n raknas over pa raden efter. PROGRAM_MD5 skulle beskriva en text som
    # aldrig funnits pa disk. Satt av M-44.
    with open(stfil, "w", encoding="ascii", newline="\n") as f:
        f.write(kompilatortext)
    md5 = hashlib.md5(kompilatortext.encode("ascii")).hexdigest()
    omslag = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "strucpp_bygg.mjs")
    try:
        korning = subprocess.run([node, omslag, strucpp_paket, stfil, utkatalog, md5],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=tidsgrans)
    except OSError as fel:
        raise Byggfel("kunde inte starta %s: %s" % (node, fel))
    except subprocess.TimeoutExpired:
        raise Byggfel("STruC++ svarade inte inom %.0f s" % tidsgrans)
    if korning.returncode != 0:
        raise Byggfel("STruC++ föll (kod %d):\n%s"
                      % (korning.returncode,
                         korning.stderr.decode("utf-8", "replace").strip()))
    # PROGRAM_MD5 ska vara programmets hash. Den räknas här och inte i omslaget
    # så att samma tal går in i defines.h och i debugkartan; två hashar med
    # samma namn hade varit en tyst avvikelse att felsöka senare.
    with open(os.path.join(utkatalog, DEFINES), "w", encoding="ascii",
              newline="\n") as f:
        f.write("#ifndef DEFINES_H\n#define DEFINES_H\n"
                "#define PROGRAM_MD5 \"%s\"\n#endif\n" % md5)
    return Debugkarta.las_fil(os.path.join(utkatalog, DEBUGKARTA))


def _kopiera_runtimeheaders(utkatalog: str, runtime_include: str) -> int:
    mal = os.path.join(utkatalog, RUNTIME_UNDERKATALOG)
    os.makedirs(mal, exist_ok=True)
    antal = 0
    for namn in sorted(os.listdir(runtime_include)):
        kalla = os.path.join(runtime_include, namn)
        if not os.path.isfile(kalla):
            continue
        with open(kalla, "rb") as f:
            data = f.read()
        with open(os.path.join(mal, namn), "wb") as f:
            f.write(data)
        antal += 1
    if antal == 0:
        raise Byggfel("inga headers i %s; runtimen kompilerar inte utan dem"
                      % runtime_include)
    return antal


def bygg_projekt(st_text: str, utkatalog: str, strucpp_paket: str,
                 runtime_include: str, opcua_konfig=None,
                 node: str = "node") -> Tuple[str, Debugkarta]:
    """Bygg hela projektarkivet. Returnerar (zip-sökväg, debugkarta).

    `opcua_konfig` är listan som ska bli conf/opcua.json (se opcuakonfig.py).
    Utelämnas den stängs varje plugin av vid uppladdningen — det är runtimens
    beteende, inte vårt, och det är mätt.
    """
    debugkarta = kompilera(st_text, utkatalog, strucpp_paket, node=node)
    _kopiera_runtimeheaders(utkatalog, runtime_include)
    if opcua_konfig is not None:
        confkatalog = os.path.join(utkatalog, CONF_UNDERKATALOG)
        os.makedirs(confkatalog, exist_ok=True)
        with open(os.path.join(confkatalog, "opcua.json"), "w",
                  encoding="ascii", newline="\n") as f:
            json.dump(opcua_konfig, f, indent=2, sort_keys=True)
    zipvag = os.path.join(utkatalog, "projekt.zip")
    skriv_arkiv(utkatalog, zipvag)
    return zipvag, debugkarta


def arkivnamn(rel: str, sep: Optional[str] = None,
              altsep: Optional[str] = None) -> str:
    """En relativ sökväg som ZIP-postnamn: alltid `/`, aldrig `os.sep`.

    ZIP-formatet skriver ut det (APPNOTE 4.4.17.1: "forward slashes"), och
    `zipfile.ZipInfo.from_file` gör INTE översättningen åt oss — den kör
    `normpath` och kapar inledande separatorer, ingenting mer. På Windows ger
    `os.path.relpath` `strucpp_runtime\\include\\foo.h`, och det hamnar som ett
    postnamn med bakstreck i arkivet. Uppackat i runtimens Linux-container blir
    det EN fil vars namn innehåller bakstreck, i arkivets rot — inte en katalog.
    `scripts/compile.sh` hittar då inga headers och bygget faller på
    "Missing required source files".

    Separatorerna är argument så att Windows-grenen går att pröva från Linux.
    Satt av M-44.
    """
    if sep is None:
        sep = os.sep
    if altsep is None:
        altsep = os.altsep
    ut = rel.replace(sep, "/")
    if altsep:
        ut = ut.replace(altsep, "/")
    return ut


def skriv_arkiv(katalog: str, zipvag: str) -> List[str]:
    """Zippa byggkatalogen. Deterministisk ordning: arkivet är ett kontrakt.

    Källfilen program.st och debug-map.json följer inte med — de hör till
    bygget, inte till runtimen.

    Posterna namnges med `/` oavsett värdplattform; se `arkivnamn`.
    """
    utelamna = set(EJ_I_ARKIVET) | {"program.st", os.path.basename(zipvag)}
    poster: List[str] = []
    for rot, kataloger, filer in os.walk(katalog):
        kataloger.sort()
        for namn in sorted(filer):
            full = os.path.join(rot, namn)
            rel = os.path.relpath(full, katalog)
            if rel in utelamna:
                continue
            poster.append(arkivnamn(rel))
    if GENERERAD_HPP not in poster:
        raise Byggfel("arkivet saknar %s; runtimen avvisar det" % GENERERAD_HPP)
    if DEBUGTABELL not in poster:
        raise Byggfel("arkivet saknar %s; .so:n laddas inte utan den"
                      % DEBUGTABELL)
    if DEFINES not in poster:
        raise Byggfel("arkivet saknar %s; make hittar inget mål" % DEFINES)
    with zipfile.ZipFile(zipvag, "w", zipfile.ZIP_DEFLATED) as z:
        for post in poster:
            z.write(os.path.join(katalog, *post.split("/")), post)
    return poster
