# M-02 — testprefixets isolering, mätt

**Datum:** 2026-09-04

## Fyndet
`drive_c/users/anton/Documents` i ett Wine-prefix är som standard en **symlänk
till värdens `~/Documents`**. En kopia av prefixet delar därför `My Commands`
med originalet. Att kopiera prefixet ger alltså **ingen isolering för tillägg**.

## Åtgärd
Testprefixets `Documents` pekas om till `~/vc-test-documents`.

| Prefix | Documents |
|---|---|
| `~/.wine-vc` (arbete) | `/home/anton/Documents` |
| `~/.wine-vc-test` (test) | `/home/anton/vc-test-documents` |

## Regel som följer
Ett testprefix är inte isolerat förrän **både** prefixet och de mappar
prefixet länkar ut till är egna. Kontrollen ska ingå i fas 0:s acceptans.

## Vad som INTE är mätt

* Exakt **en** utlänkad mapp är prövad: `Documents`. Regeln mätningen skriver ned
  — att både prefixet och de mappar prefixet länkar ut till ska vara egna — är
  alltså formulerad ur ett enda fall. Vilka andra länkar `dosdevices` och
  användarprofilen bär är inte uppräknat, så regeln är inte kontrollerad ens för
  det prefix den mättes i.
* Att omdirigeringen faktiskt **ger** isolering är inte efterprövat. Ingen mätning
  lade ett tillägg i `~/vc-test-documents` och visade att arbetsprefixet inte ser
  det. Det som är mätt är att symlänken fanns, inte att bytet håller.
* Påståendet att en kopia av prefixet delar `My Commands` med originalet är
  **härlett** ur symlänken. Inget prefix kopierades och ingen delad fil
  observerades.
* Mätt under Wine 11.16 på den här maskinen. Att en färsk `wineboot` i en annan
  Wine-version lägger symlänken likadant är inte mätt.
* *"Kontrollen ska ingå i fas 0:s acceptans"* är ett förslag i den här texten.
  Den här mätningen byggde ingen sådan kontroll.
