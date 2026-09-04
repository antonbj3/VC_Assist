# VC Assist — systemdokument

En LLM-assistent som bygger en produktionslina i Visual Components, genererar
styrkoden till en mjuk-PLC, kör den mot scenen, och låter **scenen** avgöra om
sekvensen och timingen fungerar.

Ärver observations- och grinddoktrinen ur Isaac Assist. Bygger de tre saker
som är specade men obyggda där.

## Varför det här kan fungera

Fältets styrkodsgeneratorer mäts mot blinda grindar: kompilatorn ser bara syntax,
och formell verifiering kan inte avgöra timersemantik. Tid och sekvens är
just där PLC-logik bor, och där finns ingen domare.

Simuleringen är den domaren. Den kör koden i tid mot en mekanik som beter sig.

Det som ska vara hundra procent är **det som släpps igenom**, inte det som
genereras. Ingenting levereras förrän ögat sagt att det fungerar.
Kostnaden betalas i varv.

## Sömmen

```
tjänst (Python 3)  ──kodsträngar över TCP──►  brygga (Python 2.7 inne i VC)
                   ◄──JSON-rad på stdout────
```

Tjänsten talar aldrig med scenen direkt. Allt ovanför sömmen är generiskt,
allt under är VC-specifikt. Bryggan är så liten att den aldrig behöver ändras.

Kravet som tvingar formen: **VC har inget externt API**, och dess skript kör i
inbäddad Python 2.7. Agenten måste bo utanför.

## Loopen, hela vägen

1. **Uppgift.** "Bygg en plockstation som klarar 400 detaljer i timmen."
2. **Val ur katalog.** Modellen söker i katalogindexet och väljer komponenter.
   Den får bara välja ur träfflistan. Uppfunnen URI är ett hårt fel.
3. **Komposition.** Modellen anger **relationer**, aldrig koordinater.
   `canConnect` innan `connect`. VC:s plug and play räknar geometrin.
4. **Kontroll av bygget.** Kollisionsdetektorn ger minsta avstånd, inte bara
   träff eller inte. Noll kollisioner krävs, mätt geometriskt.
5. **Signalkarta.** Scenens signaler läses ut och blir OPC UA-noder, som blir
   **färdiga variabeldeklarationer** i strukturerad text.
6. **Styrkod.** Modellen skriver bara sekvenslogiken, i ett skelett med
   deklarationerna ifyllda. Den kan inte stava fel på en tagg.
7. **Grindkedjan.** Kompilering, statisk analys, deklarationsmatchning,
   AST-validering mot verktygsschemat.
8. **Inladdning.** Kod till OpenPLC v4 över REST. VC ansluter som OPC UA-klient.
9. **Körning och observation.** Ögat provtar per simuleringssteg och lägger
   PLC:ns variabler på **samma tidslinje** som scenens fysik. Ett tidsfel blir
   ett fasförhållande som går att läsa av.
10. **Dom.** Ögat skriver sin egen dom. Grinden parsar den utan att tolka om något.
11. **Varv.** Faller den får modellen en åtgärdbar formulering: griparen stängde
    0,4 sekunder för tidigt, uppehållet var 0,2 sekunder för kort, två utgångar
    gick höga i samma scan. Inte "sekvensen fel".
12. **Guld.** L1 per station, L2 för hela linan. Endast en körning i VC befordrar.

## De tre sakerna vi bygger som källan aldrig byggde

| Sak | Läge i källan | Här |
|---|---|---|
| Dokumentindex över plattformens API | `rag_index.db` = 0 byte | primärt, byggt ur mätt API-yta |
| Godkännandekö | `pop_pending_patch` har noll anropare | tömmare från dag ett |
| Modellförfattad byggväg | hard-instantiate, modellen rapporterar | medvetet val, inte drift |

## Bärande invarianter

Ögat fäller domen. Varje tröskel bär sin incident. Fail-closed. Facit före
försöket. Modellen anger relationer, aldrig koordinater. Modellen väljer bara
ur indexet. Modellen skriver aldrig deklarationer. Modellen är aldrig sin egen
domare. `effect=write` ger kö. Ingen genererad kod i en säkerhetsfunktion.

Fullständig lista i `docs/spec/90_invarianter.md`.

## Kartan

| Dokument | Frågan det svarar på |
|---|---|
| `01_kalldisciplin.md` | Hur vet vi att ett påstående håller? |
| `10_matta_fakta.md` | Vad är mätt om VC, Wine och OpenPLC? |
| `20_arv.md` | Vad ärvs, och i vilket skick är det? |
| `30_arkitektur.md` | Vilka processer finns och vad går emellan? |
| `31_brygga_protokoll.md` | Exakt vad går över tråden? |
| `35_plattformar.md` | Vad krävs för att gå både på Windows och Wine? |
| `40_ogat.md` / `41_ogat_kontrakt.md` | Vad mäts, och hur ser domen ut? |
| `45_verktyg.md` | Vad kan modellen göra? |
| `46_kunskapsindex.md` | Hur hindras uppfunna API-namn? |
| `50_grindar.md` | Vad fångar varje grind, och vad fångar den inte? |
| `60_plc.md` | Hur hänger PLC och scen ihop? |
| `70_faser.md` | I vilken ordning byggs det, och vad stänger varje fas? |
| `80_bank.md` / `81` / `82` / `83` | Hur mäts det, och mot vilket facit? |
| `90_invarianter.md` | Vad bryts aldrig? |
| `95_testprotokoll.md` | Hur prövas allt? |
| `96_ingen_skuld.md` | Vad får aldrig lämnas efter sig? |

## Räckvidd, ärligt

Simuleringen saknar sensorstuds, ställdonsdynamik, fältbussjitter och verklig
hårdvara. Ögat är felfinnande, aldrig bevis. Och ingenting genererat rör en
säkerhetsfunktion: nödstopp och skyddskretsar ligger på certifierad säkerhets-PLC,
i begränsat variabelt språk, skrivet av människa.
