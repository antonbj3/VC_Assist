# Bänken

Ärver strukturen ur källans kanonmallar: 526 mallar, varav 314 med `CP-`-namn
för scenbygge, resten dialogkanonikaler. Lintern är 1540 rader och avvisar på
regelkoder. Den strukturen bär över; innehållet är nytt.

## Mallformat

Kärnfält, obligatoriska för alla:
`task_id`, `goal`, `tools_used`, `thoughts`, `code`, `failure_modes`

För en scenariomall tillkommer:
`scene` (vad som byggs), `signals` (signalkarta), `sequence` (avsedd ordning),
`timing` (krav på uppehåll och cykeltid), `verify_args`, `simulate_args`,
`verified_status`

`task_id` matchar filnamnet. Avvikelse är ett linterfel, precis som i källan.

## Scenarier

Industrirealistiska, i stigande svårighet. Var och en med facit.

| Grupp | Scenarier |
|---|---|
| Transport | transportör med stopp, indexerad matning, sammanflöde av två banor |
| Plock | plocka från band till låda, plocka ur ostrukturerad hög, plock med lägesgivare |
| Palletering | mönster i lager, blandade lager, avpalletering |
| Sortering | två utgångar på givarsignal, tre utgångar, omsortering vid fel |
| Buffert | ackumulerande buffert, först in först ut, svält och blockering |
| Montering | två delar i fixtur, skruvning i sekvens, förregling mellan stationer |
| Överlämning | robot till robot, robot till transportör med handskakning |
| Cell | komplett cell med två stationer och en buffert |

## Facit

Ett scenario är godkänt när **alla** håller:

1. **Körbart**: modellen kör i simulatorn utan handpåläggning, N oberoende körningar
2. **Målet nått**: uppmätt genomflöde vid stationär drift, med upprepningar, inte en enda körning
3. **Fysiskt giltigt**: noll kollisioner, mätt geometriskt, inte påstått av modellen
4. **Sekvens rätt**: ögats timingdel utan kapplöpning och utan för kort uppehåll
5. **Ärligt**: alla hederlighetsgrindar gröna

## Tal vi rapporterar

- andel som klarar **första försöket**
- andel efter **k varv**, med k redovisat
- **fel per klass**: syntax, taggnamn, sekvens, timing, kapplöpning, annat
- tokens och sekunder per godkänd station
- varians över upprepade körningar med samma uppgift

## Baslinjen som ska slås

Samma simulator, samma scenarier, styrda av en klassisk metod under **samma
budget i simuleringskörningar**. Utan den jämförelsen är ett tal bara ett tal.

## Regel

Ett scenario utan facit hör inte hemma i bänken. Facit skrivs **före** man
låter modellen försöka.
