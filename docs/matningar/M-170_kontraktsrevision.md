# M-170 — Kontraktsrevision: klassning av bankens 63 uppgifter och mekanisering av kallklass

**Datum:** 2026-09-05
**Rigg:**
**Prövar:**

# M-170 — Kontraktsrevision: klassning av bankens 63 uppgifter och mekanisering av kallklass

**Datum:** 2026-09-05 (kö B, punkt B7)
**Rigg:** python 3.13.11, bank/schema.py, tests/protocol/kor_bankens_facit.py
**Prövar:**
1. Att samtliga 63 uppgifter i banken klassas mot `docs/spec/85_bankkontraktet.md` §2.
2. Att klassningen mekaniseras som ett obligatoriskt fält `kallklass` i `facit_spar`.
3. Att `facitkalla får aldrig ligga i under_prov` mekaniseras och låses med trasig fixtur.

## Resultat

### 1. Klassning av bankens 63 uppgifter

Bankens 63 uppgifter har klassats mot de fem lagliga källorna i `85_bankkontraktet.md` §2:
- **49 uppgifter bär `facit_spar`:**
  - `RAKNAD`: 35 uppgifter (geometri eller fysik beräknad ur scenens egna mått och tider, likhetstecken visat).
  - `STANDARD+RAKNAD`: 9 uppgifter (citerar publicerad standardparagraf från M-106 kombinerat med stationsberäkning).
  - `STANDARD`: 4 uppgifter (citerar publicerade standardparagrafer, t.ex. IEC 60204-1:2016 9.2.3.7, ISO 10218-2:2011 5.6.3.4.2).
  - `DATABLAD+RAKNAD`: 1 uppgift (T-08, pulverugn med härdschema ur tillverkardatablad).
- **14 uppgifter är trasiga fixturer (`*-90`, `*-91`, `*-92`):**
  - Dessa saknar `facit_spar` per konstruktion eftersom de bär `broken`-fält och finns för att fällas av förgrindarna. De ska aldrig ha ett facit.

### 2. Mekanisering av `kallklass`

1. **`SPARFACITFALT` i `bank/schema.py`** utökades med `"kallklass"` som obligatoriskt fält.
2. **`_validera_sparfacit` i `bank/schema.py`** validerar:
   - Att `facit_spar.kallklass` finns och inte är tom.
   - Att samtliga delar (vid sammansatta klasser som `STANDARD+RAKNAD`) tillhör de lagliga källklasserna: `STANDARD`, `RAKNAD`, `DATABLAD`, `SPAR`, `ANNAN_IMPLEMENTATION`.
   - Att ingen del av facitkällan pekar in i `under_prov` (`EGEN_KOD`: `svc/`, `bank/domare.py`, `bank/schema.py`, `st/tolk.py`, etc.).
3. **`tests/protocol/kor_bankens_facit.py`** uppdaterades med kontrollen `KALLKLASS_SAKNAS` och `OKAND_KALLKLASS`, samt fixturen `FIX-8` i `trasiga_fall`.
4. **`tests/enhet/test_bankens_facit.py`** uppdaterades med enhetstesterna `test_saknad_kallklass_falls` och `test_okand_kallklass_falls` (21 av 21 gröna tester).
5. Samtliga 49 uppgifter med spårfacit har uppdaterats med det explicita fältet `"kallklass"` i `facit_spar`.

## LIMITS

- `kallklass` deklarerar källans typ men garanterar inte i sig att räkningen eller standardparagrafen är felfri. Det kontrolleras separat av räkningslintern och paragrafuppslaget mot M-106.
- De 14 trasiga fixturerna klassas inte med `kallklass` eftersom de inte har något facit att härleda. Deras artefakter kontrolleras i stället av förgrindarna.
