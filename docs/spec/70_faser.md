# Faser

Regel: **varje fas stängs av en mätt grind, inte av en demo.** Ingen fas
förklaras klar på en observation. Ärvt arbetssätt ur källprojektets
commit-konventioner, där mätning och motbevisning är egna leverabler.

Planen är i två delar, och skillnaden är viktig.

**Uppstartsstegen (0–10)** svarar på frågan *finns kedjan?* Den bygger vägen
från en tom VC till ett nedladdningsbart tillägg som genererar PLC-kod. Den
frågan är nästan besvarad.

**Djupstegen (11–17)** svarar på frågan *är det bra?* Den frågan är knappt
påbörjad, och den är den som avgör om det här blir ett verktyg någon vill
använda. Operatörens krav — *"vi ska bygga världens bästa app"*, *"inget
slarv"*, *"missa ingenting"* — bor där, inte i uppstartsstegen.

---

## Uppstartsstegen

| # | Fas | Levererar | Grind som stänger fasen | Läge |
|---|---|---|---|---|
| 0 | **Eget testprefix** | `~/.wine-vc-test`, klon av det fungerande, med VC + licens | VC startar i testprefixet och når licensservern. Operatörens prefix rörs aldrig av oprövad kod | **stängd** |
| 1 | **Bryggan** | `vc_assist/__init__.py` + `bridge.py`, TCP 8901 | Tur och retur från tjänsten: skickad kodsträng ger JSON-rad tillbaka. **Provtagningstakten mätt i Hz** | **stängd** |
| 2 | **Ögat** | `vc_eyes.py`, provtagning + analys + domstext | På en handbyggd bra och en handbyggd trasig cell: ögats dom matchar facit i båda. Trasig cell **måste** fällas | **stängd** |
| 3 | **Grinden** | `vc_eyes_gate.py` som parsar ögats utdata | Guld endast när varje cell passerar. Okänd klass ⇒ inte guld | **stängd** |
| 4 | **API-index** | sökbart index ur `vc_python_api.json` + AST-validering mot schemat | Modellen kan inte anropa ett verktyg eller argument som inte finns. Mätt över N försök: noll uppfunna namn | **stängd** |
| 5 | **Scenbygge** | katalogindex, spawn via URI, koppling via `canConnect`/`connect` | N mållayouter byggda: noll kollisioner, alla gränssnitt kopplade | **stängd** |
| 6 | **PLC-bandet** | OpenPLC v4, OPC UA, genererad signalkarta och deklarationer | Handskriven ST styr scenen genom OPC UA. Tur och retur mätt i ms | **stängd** (M-39) |
| 7 | **ST för en station** | skelett + deklarationer genererade, modellen skriver sekvensen | Grind 1–5 gröna. Ögat säger PASS. **L1-guld** | grind 1–4 gröna (M-48); ögat återstår |
| 8 | **Komposition** | flera stationer | Guld per station, sedan guld för linan. **L2** | öppen |
| 9 | **Bänken** | scenariosamling med facit | Tre tal rapporterade: första försöket, efter k varv, fel per klass. **Kräver fas 11** | öppen |
| 10 | **Paketering** | nedladdningsbart tillägg | Ren maskin: klona, installera, kör. Fungerar utan handpåläggning. **Kräver fas 12** | byggd, oprövad på ren maskin |

## Fas 0 är inte valfri

Skälet är mätt: en oprövad uppstartskrok i operatörens `My Commands` fällde
VC:s uppstart och gav ett blinkande svart fönster mitt i arbetet.
Ingen oprövad kod går in i det prefix operatören använder.

## Ordningen är inte godtycklig

Ögat före generatorn. Utan domare är resten en kodgenerator utan dom, och
då mäter vi ingenting. Källprojektets egen historia visar samma sak:
positionsproxyn fick ljuga i flera veckor tills ögat fanns att jämföra mot.

---

## Djupstegen

Var och en av dessa är tillagd därför att en **mätning** visade att den
behövdes. Ingen av dem är en idé; varje rad pekar på talet som föranledde den.

| # | Fas | Varför den finns | Grind som stänger fasen |
|---|---|---|---|
| 11 | **Klassisk baslinje** | `R-01`: ingen har publicerat vår loop, ingen leverantör publicerar ett korrekthetstal, och varje akademiskt tal är kompileringsgrad på en annan uppgiftsmängd. Att ställa vårt tal mot LLM4PLC:s 72 % vore samma kategorifel operatören redan fångat en gång | En regelbaserad generator utan språkmodell körd över **samma** bank med **samma** domare. Fas 9:s tal rapporteras alltid som par: vårt mot baslinjens. Ett tal utan baslinje publiceras inte |
| 12 | **Verktygskedjan i repot** | `M-48`: STruC++ ligger i en sessionskatalog, och npm-paketet som `paket.kompilera` kräver finns inte längre på maskinen. Grind 1 går att köra här och nu, men **inte på en ren maskin utifrån repots egna instruktioner** | Ett skript i repot hämtar STruC++, OpenPLC v4 och node, med **fastspikad version och kontrollerad hash**, och grind 1 kör efteråt. Trasigt fall: en manipulerad nedladdning måste avvisas på hashen |
| 13 | **Windows** | `M-44`: nio fynd med fil och rad, varav ett tyst och totalt — tilläggsmappen hittas inte när Dokument ligger i OneDrive, och hela systemet dör efter en lograd. Allt är byggt och mätt under Wine | M-44:s **16 numrerade protokollpunkter** körda på en riktig Windows-maskin, var och en med sitt förutbestämda gröna svar. Ingen punkt får besvaras med "borde fungera" |
| 14 | **Harnessens hårdhet** | `M-46`: **17 av 46 regler är mekaniserade, 29 är bara bedda**. Blocket om mätta fällor är sämst, 2 av 8 — och det är fällor som ger tal som *ser rimliga ut* | Kvoten mekaniserat/bett mätt om vid varje körning, med ett **golv som bara får gå uppåt** (samma spärr som tröskelskulden). Varje mekanism har en trasig fixtur som föll före den fanns. En regel som ärligt inte går att mekanisera står som `EJ_MEKANISK` med skäl |
| 15 | **Ögat på djupet** | Operatörens krav: *"programmatiskt kunna förstå vad som pågår i en scen … detta måste bli riktigt jävla bra"*, och tidsserier över **alla objekts positioner**. `M-42` lade PLC-värdena på ögats tidsaxel; resten av `42_ogat_utbyggt.md` är ospecificerat i faser | Tidsserie över varje objekt i scenen, PLC-värdena på samma axel, och domar som fäller på sekvens, timing, grepp, kollision och genomflöde — var och en med en trasig cell som måste fällas. Hopfogningens osäkerhet mätt, inte antagen |
| 16 | **Planeringslagret** | Operatörens krav, ordagrant: *"Man ska kunna sätta upp instruktioner, bygga denna scen, med dessa, med villkor och ordning av processer osv, där spec ska kunna detaljeras från grundrequest"*. `22_planeringslagret.md` är 384 rader spec utan en fas som bygger den | En grundbeställning i fritext blir en detaljerad, körbar byggplan med villkor och processordning — och planen **avvisas** när den är omöjlig, i stället för att byggas halvt. Trasigt fall: en beställning som motsäger sig själv måste fällas med vilket villkor som krockar |
| 17 | **Vad användaren ser** | Operatörens krav: *"användaren vill förmodligen också gärna kunna veta vad som händer också när saker arbetar"*. Hela systemet rapporterar i dag till loggar och mätfiler, alltså till oss, inte till användaren | Medan en körning pågår kan användaren se vad som händer, vilken grind som fällde och varför, och vad systemet **inte** vet. Trasigt fall: ett fällt läge får aldrig se ut som ett arbetande |

## Varför djupstegen ligger i den ordningen

**11 och 12 före 9 och 10.** Ett bänktal utan baslinje går inte att tolka, och
en paketering som inte kan hämta sin egen verktygskedja är inte paketerad. De
två är förutsättningar, inte förbättringar.

**13 kan köras när som helst** — den väntar bara på en Windows-maskin. Den är
skriven som ett protokoll just därför: den dagen maskinen finns ska ingen behöva
tänka ut vad som ska provas.

**14 före 16.** Planeringslagret låter en språkmodell fatta fler beslut. Att
utöka modellens frihet innan reglerna är mekaniserade är att lita på prosa i
precis det läge där prosa är svagast.

**17 sist, men inte minst.** Den är den enda fasen som riktar sig till någon
utanför det här bygget.

## Vad som ännu inte har en fas, och varför

* **Verktygsbiblioteket** växer i rundor (`M-47`: 33 % av API-ytan rörd, 4 av
  58 arbetssteg utan Python-yta alls). Rundorna har ingen slutpunkt att stänga,
  så det är ett löpande arbete och inte en fas. Täckningstalet rapporteras vid
  varje runda.
* **Robotytorna i `formaga.YTOR`** kräver först en mekanism som skriver om
  förmågerapporten när scenen ändras. Skälet står i `verktyg/robotik.py`.
* **Fler PLC-fabrikat.** Beckhoff ADS och S7 finns som .NET-dll:er i VC, men vår
  väg går utanför VC:s uppkopplingslager. Ingen efterfrågan är mätt.

## Regeln som gäller alla faser, också de nya

En fas är klar först när dess acceptansprotokoll i `tests/protocol/` är **körd
och grön, inklusive de trasiga fallen**. Ett protokoll utan trasiga fall är
ingen grind — det är en förhoppning som har fått ett filnamn.
