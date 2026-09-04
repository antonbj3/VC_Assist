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
