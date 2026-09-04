# Invarianter

Regler som aldrig bryts. Om en av dem står i vägen är det designen som är fel,
inte regeln.

## Om mätning

**I1. Ögat fäller domen.** Grinden parsar ögats egen utdata och implementerar
aldrig om måttet. Mätt skäl: en omimplementerad positionsdom underkände 2 av 4
medan ögat visade 4 av 4.

**I2. Varje tröskel bär sin incident.** Ett tal utan hänvisning till mätningen
som satte det är ett linterfel.

**I3. Fail-closed.** Okänd klass, avhuggen rapport, obesvarad fråga: allt är
"inte guld". Tystnad är aldrig ett godkännande.

**I4. Facit skrivs före försöket.** Ett scenario utan mätbart krav hör inte
hemma i bänken.

**I5. Minst tre oberoende körningar** bakom varje rapporterat tal, med
uppvärmning som inte räknas.

## Om källor

**I6. KOD@HEAD, MÄTT eller DOK.** Ett dokumentpåstående blir aldrig ensamt ett
designbeslut. Dokument åldras snabbare än kod.

**I7. Siffror ur andras mätuppställningar är inte gränser för vår.** De beskriver
system med blinda grindar.

## Om modellen

**I8. Modellen anger relationer, aldrig koordinater.** Geometrin räknas av VC:s
plug and play och kontrolleras av kollisionsdetektorn.

**I9. Modellen väljer bara ur indexet.** Uppfunnen URI eller uppfunnet API-namn
är ett hårt fel, inte en varning.

**I10. Modellen skriver aldrig deklarationer.** Variabler och taggnamn genereras
ur scenens signalkarta.

**I11. Modellen är aldrig sin egen domare.**

## Om exekvering

**I12. `effect=write` ⇒ godkännandekö.** Ingen handlare väljer själv.

**I13. Bryggan blockerar aldrig VC:s tråd**, och rör aldrig VC:s API från
bakgrundstråden.

**I14. Ingen oprövad kod i operatörens prefix.** Mätt skäl: en uppstartskrok
fällde VC mitt i arbete och gav ett blinkande svart fönster.

## Om säkerhet

**I15. Ingen genererad kod i en säkerhetsfunktion.** Nödstopp och skyddskretsar
ligger på certifierad säkerhets-PLC, i begränsat variabelt språk, skrivet av
människa. Genererad logik får ligga bredvid och vara förreglad av den.
Taggar märkta säkerhet är skrivskyddade för agenten.

## Om plattform

**I16. VC-sidans kod är plattformsneutral.** Inga hårdkodade sökvägar, TCP som
transport, bara medföljande standardbibliotek. Ska gå på Windows och under Wine.

**I17. En fas är klar först när grinden körts på den plattform den påstås gälla.**
Tills Windows-körningen finns heter det "klar på Linux, oprövad på Windows".
