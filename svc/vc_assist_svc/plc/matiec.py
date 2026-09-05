# -*- coding: utf-8 -*-
"""Klient mot matiec (OpenPLC:s IEC 61131-3-kompilator, iec2c).

Bakgrund och disciplin (M-121 §T-04, M-124):
  - matiec är typfacit för OpenPLC-kedjan: kompilatorn implementerar strikt
    IEC 61131-3:2003 §2.5.1.4, där blandade typer över generiska operatorer
    (t.ex. `4.0 * antal` med `antal : INT`) kräver uttrycklig typkonvertering
    (`4.0 * INT_TO_REAL(antal)`).
  - STruC++ tillåter tyst blandade typer och t.o.m. `b := 4.0 * i` (BOOL).
    Därför är matiec den strikta auktoriteten när typfelet ska fångas innan
    koden når runtime.
  - OBS: iec2c:s returkod kan i vissa äldre lägen vara 0 även vid fel. Domen
    läses därför alltid ur felsträngarna ('error' / 'Bailing out'), aldrig
    enbart ur returkoden.

Använda standardflaggor (strikt läge / M-121-doktrin):
  - `-f` : Visa fullständig tokenposition (rad, kolumn) vid felmeddelanden.
  - `-I <lib_katalog>` : Sökväg till IEC-standardbiblioteket (`lib/ieclib.txt` m.fl.).
  - `-T <arbetskatalog>` : Målkatalog för genererade C-filer.
  - INGA avslappnande flaggor (`-l` för relaxed datatypes, `-p` för forward refs,
    `-r`/`-R` för referenser, `-a` för icke-literala fältgränser används INTE).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

# Standardtidsgräns för kompilering (sekunder).
# Fail-closed: svarar kompilatorn inte inom tidsgränsen avvisas koden.
# MÄTT i M-165: 44 av bankens referenser, median 0,066 s, max 0,087 s (P-06).
# 30 s är alltså 340x det långsammaste observerade. Talet är ingen
# prestandagräns utan en spärr mot en hängd process, och står som det.
STANDARD_TIDSGRANS = 30.0  # M-165: max uppmatt 0,087 s over 44 referenser

# Standardflaggor: strikt IEC 61131-3-läge med fullständig felposition.
DEFAULT_FLAGGOR = ("-f",)

# Mönster för iec2c felrader:
# Exempel:
#   "test.st:6-11..6-16: error: Data type mismatch for '*' expression."
#   "/tmp/test.st:5-8..5-10: error: no expression defined..."
#   "test.st:5: error: invalid variable..."
_FEL_RAD_REGEX = re.compile(
    r"^(?:.*?):(?P<rad>\d+)(?:-(?P<kol>\d+))?(?:\.\.(?P<slutrad>\d+)-(?P<slutkol>\d+))?:\s*error:\s*(?P<msg>.+)$",
    re.M,
)


class MatiecFel(Exception):
    """Fel vid uppstart, lokalisering eller exekvering av matiec."""


@dataclass(frozen=True)
class MatiecFelRad:
    """Ett enskilt fel från matiec."""

    rad: int
    kol: int
    meddelande: str

    def __iter__(self):
        return iter((self.rad, self.kol, self.meddelande))

    def __getitem__(self, index):
        return (self.rad, self.kol, self.meddelande)[index]


@dataclass(frozen=True)
class MatiecResultat:
    """Resultat av kompilering genom matiec.

    Stöder både fältåtkomst (.accepterad, .fel) och uppackning:
        accepterad, fel = matiec.kompilera(...)
    """

    accepterad: bool
    fel: List[Tuple[int, int, str]]

    def __iter__(self):
        return iter((self.accepterad, self.fel))

    def __getitem__(self, index):
        return (self.accepterad, self.fel)[index]


def extrahera_ur_docker(
    avbild: str = "wzy318/openplc:latest",
    mal_katalog: Optional[str] = None,
) -> Tuple[str, str]:
    """Extrahera iec2c och lib/ ur OpenPLC:s docker-avbild.

    Anropas endast om lokal binär varken finns i miljövariabel eller på standardväg.
    """
    if mal_katalog is None:
        mal_katalog = os.path.join(
            os.path.expanduser("~"), ".cache", "vc_assist", "matiec"
        )
    os.makedirs(mal_katalog, exist_ok=True)

    binar = os.path.join(mal_katalog, "iec2c")
    lib = os.path.join(mal_katalog, "lib")

    if (
        os.path.isfile(binar)
        and os.access(binar, os.X_OK)
        and os.path.isdir(lib)
        and os.path.isfile(os.path.join(lib, "ieclib.txt"))
    ):
        return binar, lib

    namn = "matiec_extract_" + uuid.uuid4().hex[:8]
    try:
        subprocess.run(
            ["docker", "create", "--name", namn, avbild],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60.0,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise MatiecFel(
            f"could not create a temporary docker container from {avbild}: {e}"
        )

    try:
        subprocess.run(
            ["docker", "cp", f"{namn}:/workdir/webserver/iec2c", binar],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60.0,
        )
        subprocess.run(
            ["docker", "cp", f"{namn}:/workdir/webserver/lib", mal_katalog],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=60.0,
        )
        os.chmod(binar, 0o755)
    except (subprocess.SubprocessError, OSError) as e:
        raise MatiecFel(f"could not extract files from container {namn}: {e}")
    finally:
        subprocess.run(
            ["docker", "rm", "-f", namn],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    if not (
        os.path.isfile(binar)
        and os.path.isdir(lib)
        and os.path.isfile(os.path.join(lib, "ieclib.txt"))
    ):
        raise MatiecFel(
            f"extraction from {avbild} did not produce the expected files in {mal_katalog}"
        )

    return binar, lib


def hitta_binar() -> Tuple[str, str]:
    """Hitta matiec-binären (iec2c) och dess lib-katalog.

    Sökordning:
      1. Miljövariabel $VC_ASSIST_MATIEC (antingen fil eller katalog).
      2. /tmp/opencode/matiec/iec2c (+ /tmp/opencode/matiec/lib).
      3. Extrahera ur docker-avbilden wzy318/openplc:latest.
    """
    # 1. $VC_ASSIST_MATIEC
    env_stig = os.environ.get("VC_ASSIST_MATIEC")
    if env_stig:
        env_stig = os.path.abspath(os.path.expanduser(env_stig))
        if os.path.isfile(env_stig) and os.access(env_stig, os.X_OK):
            lib_katalog = os.path.join(os.path.dirname(env_stig), "lib")
            if os.path.isdir(lib_katalog):
                return env_stig, lib_katalog
        elif os.path.isdir(env_stig):
            binar = os.path.join(env_stig, "iec2c")
            lib_katalog = os.path.join(env_stig, "lib")
            if (
                os.path.isfile(binar)
                and os.access(binar, os.X_OK)
                and os.path.isdir(lib_katalog)
            ):
                return binar, lib_katalog

    # 2. /tmp/opencode/matiec/iec2c
    tmp_binar = "/tmp/opencode/matiec/iec2c"
    tmp_lib = "/tmp/opencode/matiec/lib"
    if (
        os.path.isfile(tmp_binar)
        and os.access(tmp_binar, os.X_OK)
        and os.path.isdir(tmp_lib)
        and os.path.isfile(os.path.join(tmp_lib, "ieclib.txt"))
    ):
        return tmp_binar, tmp_lib

    # 3. Docker-extrahering
    return extrahera_ur_docker()


def _tolka_fel(utdata: str, returkod: int) -> Tuple[bool, List[Tuple[int, int, str]]]:
    """Tolka iec2c:s utdata till (accepterad, fel_lista).

    Fail-closed:
      - Om 'error' eller 'Bailing out' förekommer, är koden underkänd.
      - Om returkod != 0 är koden underkänd.
      - Om koden är underkänd garanteras minst ett element i fel_listan.
    """
    fel_lista: List[Tuple[int, int, str]] = []

    for match in _FEL_RAD_REGEX.finditer(utdata):
        rad = int(match.group("rad"))
        kol = int(match.group("kol")) if match.group("kol") else 0
        msg = match.group("msg").strip()
        fel_lista.append((rad, kol, msg))

    # Ytterligare kontroll av icke-regex-matchade felrader (t.ex. biblioteksfel)
    har_felord = False
    for rad_text in utdata.splitlines():
        rad_clean = rad_text.strip()
        if not rad_clean:
            continue
        if "error:" in rad_clean.lower() or "bailing out" in rad_clean.lower():
            har_felord = True
            # Om raden inte fångades av regexen och inte bara är "1 error(s) found..."
            if not any(f[2] in rad_clean for f in fel_lista) and not re.match(
                r"^\d+\s+error\(s\)\s+found", rad_clean, re.I
            ):
                # Försök parsa rad/kol eller sätt (0, 0)
                m = re.match(r"^(?:.*?):(?P<rad>\d+)(?:-(?P<kol>\d+))?:", rad_clean)
                if m:
                    r_num = int(m.group("rad"))
                    k_num = int(m.group("kol")) if m.group("kol") else 0
                else:
                    r_num, k_num = 0, 0
                fel_lista.append((r_num, k_num, rad_clean))

    ar_fel = (returkod != 0) or har_felord or bool(fel_lista)

    if ar_fel:
        if not fel_lista:
            # Reserv om kompilatorn avvisade men inte gav strukturerade rader
            msg = utdata.strip() or f"matiec avvisade källkoden (returkod {returkod})"
            fel_lista.append((0, 0, msg))
        return False, fel_lista

    return True, []


def kompilera(
    kalla: str,
    binar: Optional[str] = None,
    lib_kat: Optional[str] = None,
    tidsgrans: float = STANDARD_TIDSGRANS,
    extra_flaggor: Optional[Sequence[str]] = None,
) -> MatiecResultat:
    """Kör matiec (iec2c) i en isolerad temporärkatalog.

    Parametrar:
      kalla: ST-källkod som komplett PROGRAM / CONFIGURATION.
      binar: Sökväg till iec2c (om None slås den upp via `hitta_binar()`).
      lib_kat: Sökväg till standardbiblioteket (om None från `hitta_binar()`).
      tidsgrans: Timeout i sekunder (fail-closed).
      extra_flaggor: Valfria extra CLI-argument.

    Returnerar:
      MatiecResultat(accepterad: bool, fel: List[Tuple[int, int, str]])
    """
    if binar is None or lib_kat is None:
        try:
            hittad_bin, hittad_lib = hitta_binar()
            binar = binar or hittad_bin
            lib_kat = lib_kat or hittad_lib
        except MatiecFel as e:
            return MatiecResultat(False, [(0, 0, f"kunde inte hitta matiec: {e}")])

    temp_kat = tempfile.mkdtemp(prefix="matiec_iso_")
    st_fil = os.path.join(temp_kat, "program.st")

    try:
        with open(st_fil, "w", encoding="utf-8") as f:
            f.write(kalla)

        kommando = (
            [binar]
            + list(DEFAULT_FLAGGOR)
            + ["-I", lib_kat, "-T", temp_kat, st_fil]
            + list(extra_flaggor or [])
        )

        try:
            k = subprocess.run(
                kommando,
                cwd=temp_kat,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=tidsgrans,
            )
        except subprocess.TimeoutExpired:
            return MatiecResultat(
                False,
                [
                    (
                        0,
                        0,
                        f"matiec svarade inte inom tidsgränsen ({tidsgrans:.1f} s)",
                    )
                ],
            )
        except OSError as e:
            return MatiecResultat(
                False,
                [(0, 0, f"kunde inte starta matiec ({binar}): {e}")],
            )

        kombinerad_utdata = (k.stdout or "") + "\n" + (k.stderr or "")
        accepterad, fel = _tolka_fel(kombinerad_utdata, k.returncode)
        return MatiecResultat(accepterad, fel)

    finally:
        shutil.rmtree(temp_kat, ignore_errors=True)
