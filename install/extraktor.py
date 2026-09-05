# -*- coding: utf-8 -*-
"""Extraktor: las API-ytan ur anvandarens egen VC-installation (E13).

Leverantorsdokumentationen far inte folja med i publika utgivningar. Den har
modulen extraherar API-symbolerna direkt ur anvandarens lokala installation
(<Program Files>/.../Auto Complete/) och bygger indexet lokalt vid installationen.
"""
from __future__ import annotations

import os
import shutil
from typing import Dict, List, Optional

from install import upptackt


class Extraktionsfel(Exception):
    """Extraktionen ur VC-installationen misslyckades."""


def hitta_autocomplete_mapp(produktmapp: Optional[str] = None,
                            pythonniva: str = "Python 2",
                            miljo=None) -> Optional[str]:
    """Hitta mappen Auto Complete i en lokal VC-installation."""
    if produktmapp:
        kandidat = os.path.join(produktmapp, pythonniva, "Auto Complete")
        if os.path.isdir(kandidat):
            return kandidat
        kandidat_utan_py = os.path.join(produktmapp, "Auto Complete")
        if os.path.isdir(kandidat_utan_py):
            return kandidat_utan_py
        return None

    inst = upptackt.programinstallationer(miljo=miljo)
    for p in inst:
        kandidat = os.path.join(p.sokvag, pythonniva, "Auto Complete")
        if os.path.isdir(kandidat):
            return kandidat
        if os.path.isdir(os.path.join(p.sokvag, "Auto Complete")):
            return os.path.join(p.sokvag, "Auto Complete")
    return None


def validera_autocomplete(mapp: str) -> List[str]:
    """Verifiera att Auto Complete innehaller de nodvandiga kllfilerna."""
    kravda = ("api.xml",)
    saknas = []
    for k in kravda:
        if not os.path.isfile(os.path.join(mapp, k)):
            saknas.append(k)
    return saknas


def extrahera(autocomplete_mapp: str, malmapp: str) -> Dict[str, str]:
    """Kopiera API-underlagen fran VC till en lokal datamapp."""
    if not os.path.isdir(autocomplete_mapp):
        raise Extraktionsfel("source folder %s does not exist" % autocomplete_mapp)
    saknas = validera_autocomplete(autocomplete_mapp)
    if saknas:
        raise Extraktionsfel("source folder is missing required files: %s" % ", ".join(saknas))
    os.makedirs(malmapp, exist_ok=True)
    kopierade = {}
    for fil in os.listdir(autocomplete_mapp):
        if fil.endswith(".xml") or fil.endswith(".json"):
            fran = os.path.join(autocomplete_mapp, fil)
            till = os.path.join(malmapp, fil)
            shutil.copyfile(fran, till)
            kopierade[fil] = till
    return kopierade


def granska_utgivningslista(filer: List[str]) -> List[str]:
    """Kontroll i utgivningen: ingen docs/referens/-fil far folja med ut (E13).

    Trasig fixtur: en referensfil i listan stoppar utgivningen.
    """
    forbjudna = []
    for f in filer:
        norm = f.replace("\\", "/").lstrip("/")
        if norm.startswith("docs/referens/") or "/docs/referens/" in norm:
            forbjudna.append(f)
    return forbjudna


def verifiera_utgivning(filer: List[str]) -> None:
    """Kastar Extraktionsfel om leverantorsfiler finns i utgivningen."""
    forbjudna = granska_utgivningslista(filer)
    if forbjudna:
        raise Extraktionsfel(
            "Vendor documentation found in the release tree! "
            "Files under docs/referens/ must not be distributed:\n  %s"
            % "\n  ".join(forbjudna)
        )
