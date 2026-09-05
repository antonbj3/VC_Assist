# -*- coding: utf-8 -*-
"""Rendera en markdownfil lokalt med Mermaid-diagrammen ritade.

Varfor: GitHub ritar ```mermaid-block, en textredigerare gor det inte. Utan
det har ar en granskning av ett diagram en granskning av dess kallkod, och
den som ska godkanna presentationen ser inte det lasaren ser.

  python3 scripts/forhandsvisa.py docs/PRESENTATION_UTKAST.md [--oppna]

Skriver en fristaende HTML-fil bredvid kallan och kan oppna den i webblasaren.
Kraver internet for markdown- och mermaid-biblioteken (unpkg/jsdelivr).
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

MALL = u"""<!doctype html>
<meta charset="utf-8">
<title>%(titel)s</title>
<style>
  :root { color-scheme: light dark; }
  body { max-width: 860px; margin: 3rem auto; padding: 0 1.5rem;
         font: 16px/1.65 -apple-system, "Segoe UI", Roboto, sans-serif; }
  h1 { border-bottom: 1px solid #8884; padding-bottom: .3em; }
  h2 { margin-top: 2.4em; border-bottom: 1px solid #8883; padding-bottom: .25em; }
  code { background: #8882; padding: .15em .35em; border-radius: 3px;
         font-size: .9em; }
  pre { background: #8881; padding: 1rem; border-radius: 6px; overflow-x: auto; }
  pre code { background: none; padding: 0; }
  table { border-collapse: collapse; }
  td, th { border: 1px solid #8884; padding: .35em .7em; }
  blockquote { border-left: 3px solid #1f6feb; margin-left: 0;
               padding: .6rem 1rem; background: #1f6feb14; }
  blockquote p { margin: .4em 0; }
  .mermaid { text-align: center; margin: 2rem 0; }
</style>
<div id="ut">Renderar...</div>
<script type="module">
import { marked } from "https://cdn.jsdelivr.net/npm/marked@12/lib/marked.esm.js";
import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
const kalla = %(kalla)s;
marked.use({ renderer: { code(kod, sprak) {
  if (sprak === "mermaid") return '<div class="mermaid">' + kod + '</div>';
  return false;
}}});
document.getElementById("ut").innerHTML = marked.parse(kalla);
const mork = matchMedia("(prefers-color-scheme: dark)").matches;
mermaid.initialize({ startOnLoad: true, theme: mork ? "dark" : "default" });
</script>
"""


def rendera(kalla_fil: str) -> str:
    with io.open(kalla_fil, encoding="utf-8") as f:
        text = f.read()
    ut = os.path.splitext(kalla_fil)[0] + ".forhandsvisning.html"
    with io.open(ut, "w", encoding="utf-8") as f:
        f.write(MALL % {"titel": os.path.basename(kalla_fil),
                        "kalla": json.dumps(text)})
    return ut


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("fil")
    p.add_argument("--oppna", action="store_true")
    a = p.parse_args()
    if not os.path.exists(a.fil):
        print("hittar inte %s" % a.fil)
        return 1
    ut = rendera(a.fil)
    antal = sum(1 for r in io.open(a.fil, encoding="utf-8") if r.startswith("```mermaid"))
    print("skrev %s  (%d mermaid-diagram)" % (ut, antal))
    if a.oppna:
        subprocess.Popen(["xdg-open", ut],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
