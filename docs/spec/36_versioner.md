# Versionsstöd — universalitet

Kravet är samma som för Windows mot Linux: tillägget ska **anpassa sig efter
det det hittar**, inte byggas för en version. Ingen version är den privilegierade.

## Grundregeln: förmåga, inte versionsnummer

Koden frågar **vad som finns**, inte **vilken version det är**.

```python
if hasattr(app, "executeFrameGrab"):
    ...
else:
    raise Unsupported("executeFrameGrab saknas i denna VC-version")
```

Versionsnumret används till exakt tre saker:
1. välja rätt API-index
2. härleda sökvägen till tilläggsmappen
3. märka mätresultat

Allt annat avgörs av förmågeprövning. Skälet: en okänd framtida version ska
fungera i det den kan, inte falla på att den inte står i en lista.

## Tre svarsformer, aldrig fler

| Läge | Beteende |
|---|---|
| Förmågan finns | kör |
| Förmågan saknas | **kasta ett tydligt fel** som namnger förmågan |
| Okänt | behandlas som saknad. Aldrig gissa |

En saknad förmåga får aldrig ge tyst nedgradering. Det är samma regel som
S1 i `96_ingen_skuld.md`: en ofärdig väg kastar, den returnerar aldrig framgång.

## Självbeskrivning vid start

Bryggan skriver vid uppstart en förmågerapport: VC-version, Python-version,
plattform, och vilka av de ytor tillägget behöver som faktiskt finns.
Rapporten är det första tjänsten läser, och den avgör vilka verktyg som
exponeras för modellen.

Motiv, mätt: trasiga tillägg misslyckas **tyst** i VC. Bryggan måste därför
själv säga att den lever och vad den kan.

---

Kravet: tillägget ska gå på **4.10 och på de senaste versionerna**, i första hand 5.0.

## Den bindande skillnaden

| | VC 4.x | VC 5.0 |
|---|---|---|
| Inbäddad Python | **2.7** | **3.x** |
| Licensserver | 2.1.2 | 3.0 |
| Python 2 | standard | utfasad, borttagen i 6.0 |

Att Python-versionen skiljer betyder att **all kod som körs inne i VC måste
vara giltig i både 2.7 och 3.x**. Det är ett hårt krav på bryggan och ögat,
inte en ambition.

## Regler för dubbelkompatibel kod

| Regel | Fel | Rätt |
|---|---|---|
| Undantag | `except E, e:` | `except E as e:` |
| Utskrift | `print x` | `from __future__ import print_function`, `print(x)` |
| Division | `a / b` när heltal avses | `a // b` |
| Ordböcker | `d.iteritems()` | `d.items()` |
| Strängar | implicit unicode-blandning | `from __future__ import unicode_literals` |
| Textformat | f-strängar | `"%s" % x` eller `.format()` |
| Heltalstyper | `long` | `int` |
| Sortering | `cmp=` | `key=` |
| Import | implicit relativ | `from __future__ import absolute_import` |

Varje fil som körs inne i VC inleds med:

```python
from __future__ import absolute_import, division, print_function, unicode_literals
```

**Kontroll:** L0-linter kör både en 2.7-syntaxkontroll och en 3.x-kontroll på
varje fil under `ext/`. Fel i endera fäller bygget.

*Rättelse:* sonderna i M-01 använde `except Exception, e` och hade alltså
inte gått på 5.0. Rättat innan bryggan skrivs.

## Vad som måste mätas per version

| Sak | 4.10 | 5.0 |
|---|---|---|
| Sökväg för tillägg | `My Commands/Python 2/<paket>` **MÄTT** | okänd, sannolikt `Python 3`. **Ska mätas** |
| `OnAppInitialized` | fyrar **MÄTT** | ska mätas |
| Två scope | bekräftat **MÄTT** | ska mätas |
| API-yta | 204 typer, 966 metoder **MÄTT** | ska mätas |
| `getSimulation` | finns **MÄTT** | ska mätas |
| `executeFrameGrab` | finns **MÄTT** | ska mätas |

## Hur 5.0 mäts utan licens

Installationen kan läsas utan att programmet startas. `api.xml` under
`Python 3/Auto Complete` ger hela API-ytan, och mappstrukturen ger sökvägen.
**Licens behövs bara för att köra**, inte för att inspektera.

Skolans licensserver har 4.10, så 5.0 kan inte köras här. Det som kräver
körning märks därför `oprövad på 5.0` tills någon med 5.0-licens kör det.

## Versionsdetektering vid körning

Tillägget läser versionen ur sin egen sökväg och ur installationen, och väljer
API-index därefter. Ett anrop som bara finns i en version ska aldrig skickas
till den andra.

## Konsekvens för kunskapsindexet

`api_symbol.vc_version` bär redan versionen. Indexet byggs per version och
frågor filtreras. Två versioner får aldrig blandas i ett svar.
