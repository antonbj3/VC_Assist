# -*- coding: utf-8 -*-
"""Klient mot OpenPLC Runtime v4:s REST-API. Endast standardbiblioteket.

Alla ändpunkter nedan är **MÄTTA** mot ghcr.io/autonomy-logic/openplc-runtime
v4.2.1 den 2026-09-04, inte lästa ur ett dokument. Se
docs/matningar/M-20_plcbandet.md för kommandon och svar.

    GET  /api/version              utan inloggning -> {"version": "v4.2.1"}
    GET  /api/capabilities         utan inloggning
    POST /api/create-user          första kontot skapas utan inloggning och
                                   blir admin; därefter krävs admin
    POST /api/login                {"username","password"} -> access_token
    GET  /api/status[?include_stats=true]
    GET  /api/ping
    GET  /api/compilation-status   {"status","exit_code","logs"}
    GET  /api/start-plc            {"status":"START:OK"}
    GET  /api/stop-plc
    GET  /api/runtime-logs[?id=&level=]
    POST /api/upload-file          multipart, fältnamn "file", ZIP-arkivet

Två fällor är mätta och hanteras här i stället för i varje anropare:

1. **`START:OK` betyder inte att PLC:n kör.** Runtimen svarar OK på
   begäran och misslyckas sedan asynkront. En körning som laddade ett .so
   utan debugtabell gav `START:OK` följt av
   `undefined symbol: ..debug_array_count` och status EMPTY. Därför finns
   `starta_och_vanta()`, som läser tillbaka status och fäller på EMPTY.
2. **Certifikatet är självsignerat.** Runtimen genererar det vid start.
   Att strunta i verifieringen måste därför sägas uttryckligen
   (`tillat_osignerat=True`); den vägen är inte tyst.
"""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# PLC-tillstånd som runtimen rapporterar. Strängarna är runtimens egna, med
# prefix: "STATUS:RUNNING". Prefixet skalas av i status().
KOR = "RUNNING"
TOM = "EMPTY"          # inget program laddat, eller laddningen föll
STOPPAD = "STOPPED"

# Kompileringens tillstånd, runtimens egna ord (plcapp_management.BuildStatus).
KOMPILERAR = ("IDLE", "UNZIPPING", "COMPILING")
KLAR = "SUCCESS"
FALLEN = "FAILED"

# Standardtidsgräns per HTTP-anrop. Uppladdningen kompilerar inte synkront —
# den svarar direkt med COMPILING — så inget anrop är långt. 30 s är alltså
# rundlig marginal, inte en mätning.
TIDSGRANS = 30.0


class OpenPlcFel(Exception):
    """Ett anrop mot runtimen gick inte igenom, eller svarade något annat än
    det som efterfrågades."""


@dataclass(frozen=True)
class Kompilering:
    status: str
    exit_kod: Optional[int]
    logg: str

    @property
    def klar(self) -> bool:
        return self.status == KLAR

    @property
    def pagar(self) -> bool:
        return self.status in KOMPILERAR


class OpenPlcV4(object):
    """Ett fönster mot en OpenPLC v4-runtime över REST.

    Klienten håller sin JWT och loggar in när den saknas. Den återanvänder
    ingen sessionscookie: API:t är tillståndslöst med Bearer-token, och att
    blanda in cookies hade gett två sanningar om vem som är inloggad.
    """

    def __init__(self, basadress: str, anvandare: str, losenord: str,
                 tillat_osignerat: bool = False, tidsgrans: float = TIDSGRANS,
                 cafil: Optional[str] = None):
        self.bas = basadress.rstrip("/")
        self.anvandare = anvandare
        self.losenord = losenord
        self.tidsgrans = tidsgrans
        self._token: Optional[str] = None
        if cafil:
            self._ssl = ssl.create_default_context(cafile=cafil)
        elif tillat_osignerat:
            # Runtimen genererar sitt certifikat vid start (loggen:
            # "Generating self-signed certificate for localhost"). Det finns
            # ingen utfärdare att lita på. Valet är därför uttryckligt.
            self._ssl = ssl._create_unverified_context()
        else:
            self._ssl = ssl.create_default_context()

    # ---- transport ------------------------------------------------------

    def _oppna(self, forfragan: urllib.request.Request) -> Tuple[int, bytes]:
        try:
            with urllib.request.urlopen(forfragan, timeout=self.tidsgrans,
                                        context=self._ssl) as svar:
                return svar.getcode(), svar.read()
        except urllib.error.HTTPError as fel:
            return fel.code, fel.read()
        except urllib.error.URLError as fel:
            raise OpenPlcFel("could not reach %s: %s" % (self.bas, fel.reason))
        except OSError as fel:
            raise OpenPlcFel("could not reach %s: %s" % (self.bas, fel))

    def _json(self, kod: int, kropp: bytes, vad: str) -> object:
        try:
            data = json.loads(kropp.decode("utf-8", "replace"))
        except ValueError:
            raise OpenPlcFel("%s answered %d with something that is not JSON: %r"
                             % (vad, kod, kropp[:200]))
        if kod >= 400:
            raise OpenPlcFel("%s answered %d: %s" % (vad, kod, data))
        return data

    def _hamta(self, stig: str, parametrar: Optional[Dict[str, str]] = None,
               kraver_token: bool = True) -> object:
        url = self.bas + stig
        if parametrar:
            url += "?" + urllib.parse.urlencode(parametrar)
        huvuden = {}
        if kraver_token:
            huvuden["Authorization"] = "Bearer " + self.token()
        kod, kropp = self._oppna(urllib.request.Request(url, headers=huvuden))
        return self._json(kod, kropp, "GET " + stig)

    def _posta_json(self, stig: str, kropp: object,
                    kraver_token: bool = False) -> Tuple[int, object]:
        huvuden = {"Content-Type": "application/json"}
        if kraver_token:
            huvuden["Authorization"] = "Bearer " + self.token()
        forfragan = urllib.request.Request(
            self.bas + stig, data=json.dumps(kropp).encode("utf-8"),
            headers=huvuden, method="POST")
        kod, svar = self._oppna(forfragan)
        try:
            data = json.loads(svar.decode("utf-8", "replace"))
        except ValueError:
            data = svar.decode("utf-8", "replace")
        return kod, data

    # ---- inloggning -----------------------------------------------------

    def token(self) -> str:
        if self._token is None:
            self._token = self.logga_in()
        return self._token

    def logga_in(self) -> str:
        kod, data = self._posta_json("/api/login",
                                     {"username": self.anvandare,
                                      "password": self.losenord})
        if kod != 200 or not isinstance(data, dict) or "access_token" not in data:
            raise OpenPlcFel("login as %s was rejected (%d): %s"
                             % (self.anvandare, kod, data))
        return data["access_token"]

    def skapa_forsta_anvandare(self) -> bool:
        """Skapa startkontot. Sant om det skapades, falskt om det fanns.

        MÄTT: en färsk runtime har **noll** användare i /run/runtime/restapi.db,
        och varken openplc/openplc eller admin/openplc fungerar. Det första
        kontot får skapas utan inloggning och blir admin; därefter krävs en
        inloggad admin. Runtimen är alltså osäkrad tills någon tagit kontot.
        """
        kod, data = self._posta_json("/api/create-user",
                                     {"username": self.anvandare,
                                      "password": self.losenord})
        if kod == 201:
            return True
        if kod == 409:
            return False
        if kod == 401:
            # Det finns redan användare och vi är inte inloggade. Det är inte
            # ett fel här: kontot vi vill ha kan mycket väl vara ett av dem.
            return False
        raise OpenPlcFel("create-user answered %d: %s" % (kod, data))

    # ---- läsningar utan inloggning --------------------------------------

    def version(self) -> str:
        data = self._hamta("/api/version", kraver_token=False)
        if not isinstance(data, dict) or "version" not in data:
            raise OpenPlcFel("/api/version answered without a version: %s" % (data,))
        return data["version"]

    def formagor(self) -> Dict[str, object]:
        data = self._hamta("/api/capabilities", kraver_token=False)
        if not isinstance(data, dict):
            raise OpenPlcFel("/api/capabilities answered %s" % (data,))
        return data

    # ---- PLC-styrning ---------------------------------------------------

    def status(self, med_statistik: bool = False) -> str:
        param = {"include_stats": "true"} if med_statistik else None
        data = self._hamta("/api/status", param)
        if not isinstance(data, dict) or "status" not in data:
            raise OpenPlcFel("/api/status answered without a status: %s" % (data,))
        return _efter_kolon(data["status"])

    def statistik(self) -> Dict[str, object]:
        data = self._hamta("/api/status", {"include_stats": "true"})
        if not isinstance(data, dict):
            raise OpenPlcFel("/api/status answered %s" % (data,))
        return data.get("timing_stats", {})

    def svarar(self) -> bool:
        data = self._hamta("/api/ping")
        return isinstance(data, dict) and _efter_kolon(data.get("status", "")) == "OK"

    def starta(self) -> str:
        data = self._hamta("/api/start-plc")
        return _efter_kolon(data.get("status", "")) if isinstance(data, dict) else ""

    def stoppa(self) -> str:
        data = self._hamta("/api/stop-plc")
        return _efter_kolon(data.get("status", "")) if isinstance(data, dict) else ""

    def starta_och_vanta(self, tidsgrans: float = 30.0,
                         paus: float = 0.5) -> str:
        """Starta och läs tillbaka tillståndet tills det inte är i övergång.

        Finns därför att START:OK är ett kvitto på begäran, inte på körning.
        Fail-closed: EMPTY efter en start är ett fel, inte ett väntläge.
        """
        svar = self.starta()
        if svar != "OK":
            raise OpenPlcFel("start-plc answered %r" % (svar,))
        slut = time.time() + tidsgrans
        senaste = ""
        while time.time() < slut:
            senaste = self.status()
            if senaste == KOR:
                return senaste
            if senaste == TOM:
                raise OpenPlcFel(
                    "the runtime went to EMPTY after start; the program was not "
                    "loaded. Last log lines:\n%s" % self.logg(rader=12))
            time.sleep(paus)
        raise OpenPlcFel("the runtime did not reach RUNNING within %.0f s (last: %s)"
                         % (tidsgrans, senaste))

    def logg(self, rader: int = 40, niva: Optional[str] = None) -> str:
        """Runtimeloggens sista rader, som text.

        MÄTT 2026-09-05 (M-178): `/api/runtime-logs` svarar
        `{"runtime-logs": [{"id","level","message","timestamp"}, …]}`, medan
        den här metoden bara letade efter nyckeln `"logs"`. Den har alltså
        ALLTID lämnat en tom sträng — också i `starta_och_vanta`:s felmeddelande
        ("Senaste loggrader:") och i `domare_openplc`:s Domsfel. Två fynd låg
        i den loggen och lästes aldrig: OpenPLC skriver
        `[task MAIN] terminated by signal 8` vid nolldivision (M-169) och
        `[task MAIN] scan overrun #N: body exceeds its 20 ms period` när
        kroppen inte hinner (M-178).

        Alla tre svarsformer läses därför nu: en ren lista, `{"logs": …}` och
        `{"runtime-logs": …}`. En post som är en dict skrivs som
        `[NIVÅ] meddelande` i stället för som JSON — en logg ingen orkar läsa
        är en logg ingen läser.
        """
        param = {}
        if niva:
            param["level"] = niva
        data = self._hamta("/api/runtime-logs", param or None)
        if isinstance(data, list):
            poster = data
        elif isinstance(data, dict):
            poster = (data.get("runtime-logs") or data.get("runtime_logs")
                      or data.get("logs") or [])
        else:
            poster = []
        text = [p if isinstance(p, str) else _loggrad(p) for p in poster]
        return "\n".join(text[-rader:])

    # ---- program --------------------------------------------------------

    def kompileringsstatus(self) -> Kompilering:
        data = self._hamta("/api/compilation-status")
        if not isinstance(data, dict) or "status" not in data:
            raise OpenPlcFel("/api/compilation-status answered %s" % (data,))
        loggar = data.get("logs") or []
        return Kompilering(data["status"], data.get("exit_code"),
                           "".join(loggar))

    def ladda_upp(self, zipvag: str) -> Dict[str, object]:
        """POST /api/upload-file med arkivet som multipart-fält "file".

        Svaret kommer **innan** kompileringen är klar; det bär bara
        CompilationStatus i det ögonblicket. Använd `vanta_pa_kompilering()`.
        """
        with open(zipvag, "rb") as f:
            innehall = f.read()
        grans = "----vcassist" + uuid.uuid4().hex
        namn = os.path.basename(zipvag)
        kropp = b"".join([
            ("--%s\r\n" % grans).encode("ascii"),
            ('Content-Disposition: form-data; name="file"; filename="%s"\r\n'
             % namn).encode("ascii"),
            b"Content-Type: application/zip\r\n\r\n",
            innehall,
            ("\r\n--%s--\r\n" % grans).encode("ascii"),
        ])
        forfragan = urllib.request.Request(
            self.bas + "/api/upload-file", data=kropp, method="POST",
            headers={"Authorization": "Bearer " + self.token(),
                     "Content-Type": "multipart/form-data; boundary=" + grans,
                     "Content-Length": str(len(kropp))})
        kod, svar = self._oppna(forfragan)
        data = self._json(kod, svar, "POST /api/upload-file")
        if isinstance(data, dict) and data.get("UploadFileFail"):
            raise OpenPlcFel("the upload was rejected: %s"
                             % data["UploadFileFail"])
        return data if isinstance(data, dict) else {}

    def vanta_pa_kompilering(self, tidsgrans: float = 300.0,
                             paus: float = 2.0) -> Kompilering:
        """Vänta tills kompileringen inte längre pågår.

        Tidsgränsen 300 s är rundlig: mätt byggtid för ett enkelt program på
        den här maskinen var under 5 s. Runtimens egen kod varnar för att en
        krasch i byggtråden annars kan låsa status på COMPILING för alltid,
        så väntan är avgränsad och fäller hellre än hänger.
        """
        slut = time.time() + tidsgrans
        senaste = self.kompileringsstatus()
        while senaste.pagar and time.time() < slut:
            time.sleep(paus)
            senaste = self.kompileringsstatus()
        if senaste.pagar:
            raise OpenPlcFel("the compilation stayed in %s after %.0f s"
                             % (senaste.status, tidsgrans))
        if not senaste.klar:
            raise OpenPlcFel("the compilation failed (%s, exit %s):\n%s"
                             % (senaste.status, senaste.exit_kod,
                                senaste.logg[-2000:]))
        return senaste

    def ladda_och_starta(self, zipvag: str) -> str:
        """Hela vägen: ladda upp, vänta ut bygget, starta, läs tillbaka."""
        self.ladda_upp(zipvag)
        self.vanta_pa_kompilering()
        return self.starta_och_vanta()


def _loggrad(post) -> str:
    """En loggpost som en läsbar rad. Aldrig JSON åt en människa."""
    if not isinstance(post, dict):
        return str(post)
    niva = post.get("level") or post.get("niva") or ""
    text = post.get("message") or post.get("meddelande") or ""
    tid = post.get("timestamp") or ""
    if not text:
        return json.dumps(post, ensure_ascii=False)
    delar = [d for d in (tid, "[%s]" % niva if niva else "", text) if d]
    return " ".join(delar)


def _efter_kolon(text: str) -> str:
    """"STATUS:RUNNING" -> "RUNNING". Runtimen prefixar sina svar med
    kommandots namn; prefixet bär ingen information anroparen saknar."""
    if not isinstance(text, str):
        return ""
    return text.split(":", 1)[1].strip() if ":" in text else text.strip()
