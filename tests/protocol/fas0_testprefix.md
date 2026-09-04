# FAS 0 ACCEPTANS — eget testprefix

**beskriver:** `~/.wine-vc-test`, `~/bin/vc-test.sh`

## Förutsättning
- Arbetsprefixet `~/.wine-vc` fungerar: VC Premium 4.10 startar och når licensservern
- Ingen VC-process kör
- Minst 8 GB fritt efter kopiering

## Steg
1. Verifiera att inga VC-processer kör
2. Kopiera `~/.wine-vc` till `~/.wine-vc-test` med bevarade rättigheter och länkar
3. Kontrollera att `dosdevices/c:` pekar rätt i kopian
4. Skriv `~/bin/vc-test.sh` som startar VC ur testprefixet
5. Starta VC ur testprefixet
6. Läs licensraden ur motorloggen i **testprefixet**
7. Räkna renderingsfel i testprefixets logg

## Mätning
| Storhet | Enhet | Var |
|---|---|---|
| licenssvar | textrad | `AppData/Local/.../Logs/log-file-VisualComponents.Engine.txt` |
| renderingsfel | antal | samma logg, `DxViewError` |
| diskutrymme efter | GB | `df -h /` |

## Godkänt när
- Testprefixets logg innehåller `License available on server`
- Renderingsfel = **0**
- Arbetsprefixet `~/.wine-vc` är **oförändrat**: ingen ny fil, ingen ändrad tidsstämpel i `My Commands`
- `vc-test.sh` startar testprefixet, `vc.sh` startar arbetsprefixet, och de kan inte förväxlas

## Trasigt fall
Lägg en avsiktligt trasig `__init__.py` i **testprefixets** `My Commands`.
VC ska falla eller starta utan tillägget. **Arbetsprefixet ska vara opåverkat.**
Det är hela poängen med fasen: en trasig krok fällde tidigare operatörens VC.

## Plattform
Linux ☐   Windows ☐ (ej tillämpligt för denna fas — prefix är ett Wine-begrepp)
