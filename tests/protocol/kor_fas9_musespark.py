# -*- coding: utf-8 -*-
"""Fas 9 driven av Muse Spark via `opencode run` — EGEN ARM, inte Sonnet-armen.

`kor_fas9_slingan.py --modell sonnet` ar blockerard har: `claude` ar inte
inloggad (M-110 arm 1: 21/21 KORNINGSFEL, 0 USD). Den har korningen svarar pa
en ANNAN fraga — vad en gratis modell (Muse Spark 1.3) gor med samma slinga —
och talen far aldrig blandas med M-96:s Sonnet-tal. Samma promptbygge, samma
grindar, samma JSON-form; annan `modell`-etikett i utfilen.

Sparren mot facitlakning (svagare an Claudes, och det star i M-110):
  1. `opencode run` kors i en tom katalog UTANFOR repot (samma `_neka_repot`
     som ClaudeCLI) och utan `-f`-bilagor — modellen far inga sokvagar.
  2. Prompten namner inga filer eller sokvagar.
  3. Fail-closed: syns NAGON handelse som inte ar ren text (verktygsanrop,
     filasning, exekvering) i `--format json`-strommen kastas `Modellfel`
     och uppgiften blir KORNINGSFEL med orsaken i klartext — aldrig ett
     tyst godkannande av ett svar som kan ha last facit.

    python3 tests/protocol/kor_fas9_musespark.py [--lage rent]
        [--uppgift T-07] [--json ut.json]
"""
from __future__ import annotations

BANKPOST = {
    "pastar":
        "Reparationsslingan driven av Muse Spark (gratis) loser bankens "
        "sparfacituppgifter inom M-52:s tak pa fyra varv, och kostnaden per "
        "uppgift skrivs ut. EGNA tal — jamfors inte med M-96:s Sonnet-tal.",
    "under_prov": (
        "svc/vc_assist_svc/plc/reparation.py",
        "tests/protocol/kor_fas9_musespark.py",
    ),
    "facit":
        "uppgiftens handskrivna sparfacit avgor om en uppgift ar LOST, och "
        "taket ar fyra varv (M-52)",
    "facitkalla":
        "bankens uppgifter, med facit skrivet av en manniska fore forsoket; "
        "taket pa fyra varv kommer ur M-52, en tidigare matning",
    "facitkalla_filer": (
        "bank/uppgifter/T-07.json",
        "bank/uppgifter/S-05.json",
        "docs/matningar/M-52_reparationsslingan.md",
    ),
    "trasiga_fall": (
        "ett modellsvar som anvant verktyg MASTE bli KORNINGSFEL, aldrig ett "
        "godkant varv — svaret kan ha last facit",
        "en uppgift som slar i taket rapporteras som slog_i_taket, aldrig som "
        "lost",
        "ett korningsfel far inte doljas: talen ar da inte hela banken och "
        "det skrivs ut",
    ),
    "kraver": ("modell",),
    "matningar": ("M-110",),
}

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

_ROT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(_ROT, "svc"))
sys.path.insert(0, _ROT)

from bank import reparationsbank as RB                              # noqa: E402
from vc_assist_svc import modellklient                              # noqa: E402
from vc_assist_svc.claudeadapter import _en_strang, _utan_kodstaket  # noqa: E402
from vc_assist_svc.harness.modell import Modellsvar                  # noqa: E402
from vc_assist_svc.plc import reparation as R                       # noqa: E402

MODELL_ID = "opencode/muse-spark-1.3-contributor-free"

# Transporttillägg — del av APPARATEN, inte av prompten: haller verktygen
# borta utan att andra vad slingan ber om. Samma for varje varv i armen.
_TRANSPORTSUFFIX = (
    "\n\nSvara med enbart kodens rader som vanlig text. "
    "Anvand inga verktyg, las inga filer, kor ingen kod.")


class OpencodeCLI(modellklient.Modellklient):
    """`opencode run -m <modell> --format json` som modellklient."""

    namn = "opencode-cli"

    def __init__(self, modell=MODELL_ID, tidsgrans=600, korbar=None):
        self.modell = modell
        self.tidsgrans = tidsgrans
        self.korbar = korbar or shutil.which("opencode")
        self.verktygslarm = 0

    def tillganglig(self):
        return bool(self.korbar) and os.path.exists(self.korbar)

    def fraga(self, prompt):
        if not self.tillganglig():
            raise modellklient.Modellfel(
                "hittar ingen korbar `opencode`.")
        katalog = tempfile.mkdtemp(prefix="vcassist-modell-")
        try:
            modellklient._neka_repot(katalog)
            try:
                k = subprocess.run(
                    [self.korbar, "run", "-m", self.modell,
                     "--format", "json", prompt + _TRANSPORTSUFFIX],
                    cwd=katalog, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=self.tidsgrans)
            except subprocess.TimeoutExpired:
                raise modellklient.Modellfel(
                    "modellen svarade inte inom %d s" % self.tidsgrans)
            if k.returncode != 0:
                raise modellklient.Modellfel(
                    "opencode gav slutkod %d: %s" % (
                        k.returncode,
                        k.stderr.decode("utf-8", "replace")[:400]))
            textdelar = []
            token = {"in": 0, "ut": 0}
            for rad in k.stdout.decode("utf-8", "replace").splitlines():
                try:
                    h = json.loads(rad)
                except ValueError:
                    continue
                typ = h.get("type")
                if typ == "text":
                    textdelar.append(h.get("part", {}).get("text", ""))
                elif typ in ("step_start", "step_finish", "session"):
                    info = h.get("part", {})
                    tok = info.get("tokens") or {}
                    token["in"] += int(tok.get("input") or 0)
                    token["ut"] += int(tok.get("output") or 0)
                else:
                    self.verktygslarm += 1
                    raise modellklient.Modellfel(
                        "opencode anvande verktyg (%s) — svaret kan ha "
                        "last facit och raknas inte" % typ)
            text = "".join(textdelar)
            if not text.strip():
                raise modellklient.Modellfel(
                    "opencode gav ingen text tillbaka")
            return modellklient.Svar(
                text=text, modell=self.modell, kostnad_usd=0.0,
                ratt={"tokens_in": token["in"], "tokens_ut": token["ut"]})
        finally:
            shutil.rmtree(katalog, ignore_errors=True)


class OpencodeModell(object):
    """`opencode run` bakom slingans `Modell`-yta. Ren text in, ren text ut."""

    leverantor = "opencode/muse-spark"

    def __init__(self, klient=None, modell=MODELL_ID):
        self._klient = klient or OpencodeCLI(modell=modell)
        self.namn = modell
        self.kostnad_usd = 0.0
        self.anrop = 0
        self.tokens_in = 0
        self.tokens_ut = 0

    def svara(self, systemprompt, meddelanden, verktyg):
        if verktyg:
            raise modellklient.Modellfel(
                "OpencodeModell fick %d verktyg men kan inte bara dem." %
                len(verktyg))
        fraga = _en_strang(systemprompt, meddelanden)
        svar = self._klient.fraga(fraga)
        text = _utan_kodstaket(svar.text)
        self.kostnad_usd += svar.kostnad_usd or 0.0
        ratt = svar.ratt or {}
        self.tokens_in += int(ratt.get("tokens_in") or 0)
        self.tokens_ut += int(ratt.get("tokens_ut") or 0)
        self.anrop += 1
        return Modellsvar(text=text, anrop=(), leverantor=self.leverantor)


def kor_en(post, lage, modellnamn, max_varv, forhandsregler=True,
           exempel=None):
    upps = RB.bygg_uppsattning(post)
    prompt = R.SYSTEMPROMPT if forhandsregler else R._GRUNDPROMPT
    if exempel:
        tid_exempel, kropp_exempel = exempel
        prompt = prompt + (
            "\n\nSa har ser en godkand kropp ut. Den loser en ANNAN uppgift"
            " (%s) - kopiera inte dess logik, bara dess form.\n\n%s\n"
            % (tid_exempel, kropp_exempel))
    slinga = R.Reparationsslinga(upps["skelett"], upps["grindar"],
                                 lage=lage, max_varv=max_varv,
                                 systemprompt=prompt)
    modell = OpencodeModell(modell=modellnamn)
    t0 = time.time()
    protokoll = slinga.kor(modell, upps["prompt"], uppgift=post["task_id"])
    return {
        "uppgift": post["task_id"],
        "lage": lage,
        "utfall": protokoll.utfall,
        "lost": bool(protokoll.lost),
        "varv_korda": len(protokoll.varv),
        "varv_till_lost": protokoll.varv_till_lost,
        "slog_i_taket": len(protokoll.varv) >= max_varv and not protokoll.lost,
        "max_varv": max_varv,
        "forhandsregler": bool(forhandsregler),
        "anrop": modell.anrop,
        "kostnad_usd": round(modell.kostnad_usd, 4),
        "tokens_in": modell.tokens_in,
        "tokens_ut": modell.tokens_ut,
        "sekunder": round(time.time() - t0, 1),
        "domar_per_varv": [
            [d.utdata[:300] for d in getattr(v, "domar", ())]
            for v in protokoll.varv],
        "kroppar_per_varv": [getattr(v, "kropp", "") for v in protokoll.varv],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--modell", default=MODELL_ID)
    p.add_argument("--lage", default=R.LAGE_RENT, choices=list(R.LAGEN))
    p.add_argument("--uppgift", action="append",
                   help="kor bara den har uppgiften (kan upprepas)")
    p.add_argument("--max-varv", type=int, default=R.MAX_VARV)
    p.add_argument("--utan-forhandsregler", action="store_true")
    p.add_argument("--upprepa", type=int, default=1)
    p.add_argument("--json")
    a = p.parse_args(argv)

    k = OpencodeCLI(modell=a.modell)
    if not k.tillganglig():
        print("INGEN MODELLKLIENT. `opencode` finns inte i PATH.",
              file=sys.stderr)
        return 2

    poster = RB.uppgifter_med_sparfacit()
    if a.uppgift:
        valda = set(a.uppgift)
        poster = [x for x in poster if x["task_id"] in valda]
    if not poster:
        print("inga uppgifter valda", file=sys.stderr)
        return 2

    print("=== FAS 9: slingan driven av Muse Spark (EGEN ARM) ===\n")
    print("  modell: %s   lage: %s   tak: %d varv (M-52)   forhandsregler: %s\n"
          % (a.modell, a.lage, a.max_varv,
             "nej" if a.utan_forhandsregler else "ja"))

    resultat = []
    bank_vid_start = [x["task_id"] for x in poster]

    def skriv_delresultat():
        # Inkrementell flush efter VARJE uppgift: en avbruten korning tappar
        # hogst en uppgift, aldrig hela armen (M-110 lar av avbruten fullarm).
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump({"modell": a.modell, "lage": a.lage,
                           "forhandsregler": not a.utan_forhandsregler,
                           "max_varv": a.max_varv,
                           "bank_vid_start": bank_vid_start,
                           "resultat": resultat,
                           "lost": len([r for r in resultat if r["lost"]]),
                           "slog_i_taket": len(
                               [r for r in resultat
                                if r.get("slog_i_taket")])}, f,
                          indent=2, ensure_ascii=False)
        for varv_nr in range(1, a.upprepa + 1):
            etikett = post["task_id"] if a.upprepa == 1 else "%s #%d" % (
                post["task_id"], varv_nr)
            print("  %s ..." % etikett, end="", flush=True)
            try:
                r = kor_en(post, a.lage, a.modell, a.max_varv,
                           forhandsregler=not a.utan_forhandsregler)
                r["upprepning"] = varv_nr
            except Exception as e:                          # noqa: BLE001
                r = {"uppgift": post["task_id"], "lage": a.lage,
                     "utfall": "KORNINGSFEL", "lost": False, "fel": repr(e),
                     "varv_korda": 0, "varv_till_lost": None,
                     "upprepning": varv_nr, "slog_i_taket": False,
                     "kostnad_usd": 0.0}
                print(" FEL: %r" % e)
        else:
            print(" %s efter %d varv, %d/%d tokens, %.0f s"
                  % (r["utfall"], r["varv_korda"], r["tokens_in"],
                     r["tokens_ut"], r["sekunder"]))
        resultat.append(r)
        skriv_delresultat()

    losta = [r for r in resultat if r["lost"]]
    taket = [r for r in resultat if r.get("slog_i_taket")]
    fel = [r for r in resultat if r["utfall"] == "KORNINGSFEL"]

    print("\n  %-22s %s" % ("lost:", "%d av %d" % (len(losta), len(resultat))))
    if losta:
        varv = [r["varv_till_lost"] for r in losta]
        print("  %-22s %s  (median %s)"
              % ("varv till lost:", varv, sorted(varv)[len(varv) // 2]))
    print("  %-22s %d av %d" % ("slog i taket:", len(taket), len(resultat)))
    if fel:
        print("  %-22s %d - talen ovan ar INTE hela banken"
              % ("korningsfel:", len(fel)))

    print("\n  Vad korningen INTE visar:")
    print("    Annan modell an M-96:s Sonnet — talen jamfors inte.")
    print("    Domen kommer ur var ST-tolk, inte ur OpenPLC.")

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"modell": a.modell, "lage": a.lage,
                       "forhandsregler": not a.utan_forhandsregler,
                       "max_varv": a.max_varv, "resultat": resultat,
                       "lost": len(losta), "slog_i_taket": len(taket)},
                      f, indent=2, ensure_ascii=False)
        print("\n  skrivet: %s" % a.json)
    return 0 if not fel else 1


if __name__ == "__main__":
    sys.exit(main())
