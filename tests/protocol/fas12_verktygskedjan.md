# FAS 12 ACCEPTANS — verktygskedjan i repot

**beskriver:** `install/verktygskedjan.py`, `install/strucpp-0.6.6-package-lock.json`
**kontrakt:** `docs/spec/70_faser.md` — *"Ett skript i repot hämtar STruC++,
OpenPLC v4 och node, med fastspikad version och kontrollerad hash, och grind 1
kör efteråt. Trasigt fall: en manipulerad nedladdning måste avvisas på hashen"*
**mätning:** `docs/matningar/M-56_verktygskedjan_i_repot.md`

## Status: PASSERAD för Linux, ÖPPEN för resten

## Vad som är kört och grönt

| Krav | Läge |
|---|---|
| skript i repot hämtar STruC++ | **klart** — `install/verktygskedjan.py` |
| fastspikad version | **klart** — v0.6.6, sju artefakter med sha256 och storlek |
| kontrollerad hash | **klart** — båda måtten krävs, filen tas bort när den inte stämmer |
| OpenPLC låst | **klart** — digest, inte tagg |
| grind 1 kör efteråt | **klart** — `paket.kompilera` ur hämtarens egen utdata ger alla fyra artefakterna |
| **trasigt fall: manipulerad nedladdning avvisas** | **klart** — `test_en_manipulerad_fil_falls_OCH_tas_bort` |

Nitton prov i `tests/enhet/test_verktygskedjan.py`, alla utan nät.

Utöver hashfallet fäller de: rätt hash men fel storlek, en arkivpost som pekar
utanför målet (både tar och zip), en okänd plattform som **inte** gissar
`linux-x64`, en cachad fil som kontrolleras ändå, och en saknad låsfil som
stoppar installationen i stället för att köra ett olåst `npm install`.

## Vad som gör fasen ÖPPEN

* **node är inte fastspikat.** Kedjan använder det `node` som finns på maskinen.
  Det är en verklig lucka i löftet "ren maskin", och den är inte lagad.
* **Bara Linux är kört.** Manifestet bär posterna för Windows och macOS; ingen
  har kört dem. Det binder fasen till fas 13.
* **Windows ARM64 kan inte fungera.** Utgivarens ARM64-paket är x64-bygget
  (M-56). Vår hämtare varnar, men kan inte laga det.

## Trasigt fall som INTE går att skriva än

En manipulerad **OpenPLC-avbild** avvisas av docker på digesten, inte av oss.
Att prova det kräver att man matar docker en förfalskad avbild, och det är inte
gjort. Raden står här så att den inte ser prövad ut.
