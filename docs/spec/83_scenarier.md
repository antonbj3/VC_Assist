# Scenariokatalogen

Tjugo scenarier i sju grupper. Var och en **isolerar en felklass** ur
`82_felklasser.md`, så bänken blir diagnostisk och inte bara en hög med prov.

Kolumnen "fångar" är den klass scenariot är byggt för att avslöja.

## T — transport

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `T-01` | band med stoppgrind, en givare, ett don | släpp fram en detalj per givarflank | `F5` sekvens |
| `T-02` | indexerad matning | flytta ett steg, vänta, upprepa | `F6` timing |
| `T-03` | två banor som flyter samman | släpp fram en i taget, aldrig två | `F7` kapplöpning |
| `T-04` | ackumulerande buffert | stoppa inflöde vid full, återuppta vid plats | `F8` förregling |

## P — plock

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `P-01` | robot plockar från stillastående fixtur | plocka och lägg i låda | baslinje |
| `P-02` | robot plockar från **rörligt band** | plocka utan att missa | `F10` grepp, `F6` timing |
| `P-03` | plock utlöst av lägesgivare | plocka på flank, inte på tid | `F5`, `F6` |
| `P-04` | plock ur ostrukturerad hög | plocka tills högen är tom | `F10` |

## L — palletering

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `L-01` | ett lager i mönster | lägg N i rutmönster | `F9` geometri |
| `L-02` | flera lager med förskjutning | bygg tre lager | `F9`, `F5` |
| `L-03` | avpalletering | töm i omvänd ordning | `F5` |

## S — sortering

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `S-01` | två utgångar, en givare | dela flödet på givarsignal | `F5` |
| `S-02` | tre utgångar | dela på tre | `F7` |
| `S-03` | omsortering vid fel | skicka avvikare till kassation | `F8` |

## A — montering

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `A-01` | två delar i fixtur | placera A, sedan B | `F5` |
| `A-02` | skruvning i sekvens | fyra skruvar i bestämd ordning, med moment | `F6` |
| `A-03` | förregling mellan två stationer | station 2 startar aldrig före station 1 klar | `F8` |

## H — överlämning

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `H-01` | robot till band med handskakning | lämna över utan att tappa | `F7`, `F10` |
| `H-02` | robot till robot | överlämning i luften | `F7`, `F10` |

## C — cell

| Id | Scen | Styruppgift | Fångar |
|---|---|---|---|
| `C-01` | två stationer och en buffert, komplett cell | nå kapacitetsmål över en simulerad timme | `F11` genomflöde, allt ovan |

`C-01` är den enda som mäter kapacitet. Övriga mäter korrekthet.

## Regler för katalogen

1. **Facit skrivs före försöket.** Ett scenario utan `expect` hör inte hemma här.
2. **Minst tre oberoende körningar** per mätning, med uppvärmning som inte räknas.
3. **Varje scenario ska kunna misslyckas.** Ett scenario som ingen rimlig
   generator kan fälla mäter ingenting. En medvetet trasig variant byggs för
   `T-01`, `P-02` och `A-03` som kontroll på att grindarna faktiskt fäller.
4. **Svårighetsgrad 1 till 5** sätts efter att den mätts, inte gissats.

## Baslinjen

Samma tjugo scenarier körs med en klassisk metod under **samma budget i
simuleringskörningar**. Utan den jämförelsen är våra tal bara tal.
Baslinjen definieras i fas 9 och är en del av leveransen, inte en efterhandsidé.

## Rapportform

Per scenario: klarade första försöket, klarade efter k varv, felklass vid fall,
tokens och sekunder. Per katalog: samma, aggregerat, plus varians över
upprepning med samma uppgift.
