# M-92 — sömmen mellan VC:s 2.7 och tjänstens 3.x, mätt i stället för läst

**Datum:** 2026-09-05
**Rigg:** `python:2.7-slim` (2.7.18) i container, mot värdens 3.13.11
**Prövar:** `ext/vc_addon/vc_assist/plats.py` — antagandet modulen är byggd på

## Antagandet som stod som läst men inte mätt

`plats.py`:s docstring säger, ordagrant, att skillnaden mellan de två
standardbiblioteken *"är låst och läsbar; att den faktiskt biter på en
Windows-maskin är **OPROVAT** (M-44)"*. Påståendet kom ur bpo-36264, inte ur en
körning.

Det går att köra. `ntpath` finns på Linux, och Python 2.7 finns i en container.

## Vad de två faktiskt gör

`ntpath.expanduser("~")`, samma tre miljöer i båda:

| miljö | **2.7.18** | **3.13.11** |
|---|---|---|
| `HOME=H:\hem` + `USERPROFILE=C:\Users\PC` | `H:\hem` | `C:\Users\PC` |
| bara `USERPROFILE=C:\Users\PC` | `C:\Users\PC` | `C:\Users\PC` |
| bara `HOME=H:\hem` | `H:\hem` | **`~`** |

Rad 1 är den dokumenterade divergensen, nu mätt: med båda satta pekar VC:s 2.7
och tjänstens 3.x på **olika mappar**. Modulens val — `USERPROFILE` före `HOME`
— gör att båda sidor svarar lika, och det valet är nu prövat och inte bara
motiverat.

**Rad 3 stod ingenstans, och den är värre.** Python 3 lämnar strängen **orörd**
när den inte kan lösa den. Svaret blir tecknet `~`.

## Vad ett orört `~` betyder i den här koden

`anvandarmapp()` returnerade det rakt igenom. Ett `~` som mapp är en **relativ**
sökväg: tillägget skapar en katalog som *heter* `~` där VC:s arbetskatalog råkar
ligga, skriver sin token dit, och tjänsten letar någon annanstans. Resultatet är
`E_AUTH` utan en logg som säger varför — exakt den felbild modulens egen
docstring beskriver för `HOME`-fallet, framme genom en annan dörr.

Rättat: sista utvägen prövar sitt eget svar. Ett svar som är tomt eller börjar
med `~` är ingen härledning utan ett misslyckande, och blir
`HemsokningMisslyckades` med vad som saknades och vad man ska sätta i stället
(`VC_ASSIST_HEM`). Fem trasiga fixturer, plus två som visar att vakten inte
fyrar på riktiga svar.

## Coverage: två Windows-vägar fanns men kördes aldrig

`install/` är på **84 %**, `upptackt.py` på **92 %**. Bland de okörda raderna
låg två block som inte är okörbara utan bara oprövade — `Miljo` tar miljö och
plattform som data, så båda går att driva härifrån:

* **OneDrive-rötterna** (`%OneDrive%\Documents`, `OneDriveCommercial`,
  `OneDriveConsumer`). Det är M-44:s huvudfynd — tilläggsmappen hittas inte när
  Dokument ligger i OneDrive — och koden för det hade **ingen grind över sig**.
* **Program Files-rötterna** (`ProgramFiles`, `ProgramW6432`,
  `ProgramFiles(x86)`, `SystemDrive`). Så VC hittas på Windows.

Nu prövade: alla tre OneDrive-varianterna med källa, en tom variabel som inte
får bli den relativa sökvägen `Documents`, båda bitbredderna, avdubbleringen när
två variabler pekar på samma mapp, och att en rot som inte finns inte släpps
igenom.

**Mitt eget fel på vägen:** första provet av programrötterna pekade på
`C:\Program Files` och fick tom lista, och jag höll på att kalla det ett fel i
koden. Filtret är rätt — en rot som inte finns är ingen rot. Provet mätte
filtret i stället för grenen. Rättat till riktiga kataloger, och skälet står i
provet.

## 2.7-giltigheten kompileras nu av en 2.7

Den befintliga grinden prövade 2.7-giltighet med en **handskriven lista** över
konstruktioner som inte finns i 2.7: f-strängar, `unicode_literals`, `exec` i en
nästlad funktion. Listan är byggd ur vad någon råkade komma ihåg — samma form
som M-70:s mönster, som hade åtta döda grenar i månader.

`tests/enhet/test_tillagg_py27_pa_riktigt.py` kör `py_compile` i en riktig
2.7.18 över varje fil i tillägget. Trasig fixtur: en f-sträng, en
typannotering och en valross-operator prövas var för sig, och 2.7 avvisar alla
tre. Alla tilläggsfiler kompilerar.

Provet hoppas över **med skäl** när avbilden saknas. Ett hopp är inget
godkännande, och det står i utskriften vilket det var.

## LIMITS

* **Ingen Windows-maskin.** Divergensen är mätt mellan två `ntpath` på Linux,
  vilket är samma kod som på Windows men inte samma miljö. Att en verklig
  Windows-maskin i drift har `HOME` satt — Git for Windows, Cygwin, MSYS — är
  fortfarande **oprövat**, och det är det ledet M-44 pekar på.
* **`%OneDrive%`-rötterna är prövade som logik, inte mot en OneDrive.** Ingen
  omdirigerad dokumentmapp har funnits att mäta mot (se M-91).
* **Coverage mättes över `tests/enhet`**, inte över protokollsviten. Rader som
  bara körs under en VC-körning räknas som okörda här.
* **`verktygskedjan.py` ligger på 58 %** och är inte åtgärdad. Den gör
  nätverks-I/O; vad som saknas är inte undersökt i den här mätningen.
* **2.7-grinden prövar syntax, inte semantik.** En fil som kompilerar i 2.7 kan
  ändå göra fel saker där — Stackless 2.7 inne i VC är ytterligare ett steg bort
  från `python:2.7-slim`.
