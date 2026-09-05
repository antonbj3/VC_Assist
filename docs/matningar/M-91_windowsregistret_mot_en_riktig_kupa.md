# M-91 — installeraren läste fel registernyckel, mätt mot en riktig Windows-kupa

**Datum:** 2026-09-05
**Källa:** `/dev/nvme1n1p3`, Windows 10 build 19041, monterad `ro,noexec`
**Prövar:** `install/upptackt.py:skalmapp_windows` — vägen till dokumentmappen när Windows flyttat den

## Varför en monterad partition räknas

Fas 13 väntar på en Windows-maskin, och `M-44` har 16 numrerade protokollpunkter
som inte får besvaras med *"borde fungera"*. Maskinen här har en Windows
10-installation som **inte** kan köras (operatören vill det inte, och ingen VC
finns där) — men dess **filsystem och registerkupa är riktiga**. Det räcker för
att avgöra ett par av punkterna, och för ingenting mer.

## Vad kupan sa

Användaren `PC` har `Documents` med 102 poster i den klassiska sökvägen, och en
`OneDrive`-mapp med **1** post. **Dokumentmappen är alltså inte omdirigerad** på
den här maskinen — den kan därför inte visa det fall M-44 varnade för.

Två saker den däremot avgör:

* **Mappen heter `Documents` på disken, på engelska.** Lokaliseringen sker bara
  genom `desktop.ini` → `LocalizedResourceName=@%SystemRoot%\system32\shell32.dll,-21770`.
  Ett svenskt Windows visar *Dokument* men skriver `Documents`. Installerarens
  sökning efter `("Documents", "My Documents")` är alltså rätt, och en sökning
  efter det visade namnet hade varit fel. Inga svenska mappnamn finns på disken.
* **Båda registernycklarna finns i kupan** — `Shell Folders` och
  `User Shell Folders`, en gång var — och båda formerna av sökvägen ligger där:
  `%USERPROFILE%\Documents` oexpanderad och `C:\Users\PC\Documents` expanderad.

## Fyndet

`skalmapp_windows` läste `Shell Folders\Personal`.

Det är den **bakåtkompatibla cachen**. `User Shell Folders` är den nyckel
Windows själv skriver till när mappen flyttas eller omdirigeras — alltså exakt
det OneDrive-fall funktionen är skriven för. Koden läste den nyckel som kan
släpa efter, i just det scenario den skulle lösa.

**Och funktionen hade inget prov alls.** Den importerar `winreg`, som inte finns
på Linux, så den gick varken att köra eller fälla härifrån. Ingen grind hade
någonsin läst den — och den är enda vägen till dokumentmappen när Windows flyttat
den. Den låg i skuldregistrets hink `moduler_utan_prov`, men som en rad bland
många, inte som en risk någon vägt.

## Rättelsen, och fällan i den

Nycklarna prövas nu i ordning: `User Shell Folders` först, `Shell Folders` som
reserv, och ett fel som nämner **båda** om ingen svarar. Källsträngen namnger
den nyckel som faktiskt svarade — konsumenten skrev tidigare den fasta strängen
`"registret: Shell Folders\Personal"` oavsett varifrån värdet kom, vilket blivit
ett falskt härkomstpåstående så fort reserven användes.

Fällan låg i rättelsen själv, och provet gick på den:

**`User Shell Folders` levererar `REG_EXPAND_SZ`** — värdet är
`%USERPROFILE%\Documents`, inte en färdig sökväg. Att byta nyckel utan att
expandera hade gett en sökväg med ett procenttecken i: fortfarande fel, bara
tystare än förut.

Första expansionen skrevs med `os.path.expandvars`. På Windows är `os.path`
lika med `ntpath` och det hade fungerat — men på Linux är det `posixpath`, som
bara känner `$VAR` och lämnar `%USERPROFILE%` orört. Provets första rad jämförde
då `os.path.expandvars(x)` mot resultatet, alltså **oexpanderat mot
oexpanderat**, och passerade utan att mäta någonting. Andra raden fällde det.

Koden använder nu `ntpath.expandvars` explicit, vilket gör Windows-expansionen
på båda plattformarna. Rätt på Windows men oprövbar från Linux är samma sak som
oprövad.

Sex prov, varav fyra är trasiga fixturer som föll före rättelsen.

## LIMITS

* **Ingen omdirigering fanns att mäta.** Den här maskinen har `Documents` på
  klassisk plats. Att `Shell Folders` verkligen släpar efter `User Shell Folders`
  efter en OneDrive-omdirigering är **inte mätt** — det är skälet till att den
  nyare nyckeln läses först, inte ett resultat.
* **Ingenting kördes på Windows.** Kupan lästes som en fil från Linux, med
  `strings -e l` och `strings -a`. Nyckelnamnen finns i kupan; att de sitter
  under exakt den sökväg koden öppnar är **inte** verifierat — det kräver en
  registerläsare eller en körning på Windows.
* **`winreg` självt är fortfarande aldrig kört.** Proven matar en attrapp. Att
  den riktiga modulens `QueryValueEx` returnerar typen i andra elementet är
  taget ur dokumentationen, inte mätt.
* **Ingen VC på den partitionen**, så ingenting säger något om fas 13:s
  VC-relaterade punkter.
* **En användare, en Windows-build** (19041, en-US). Säger inget om andra
  builds, domänprofiler eller flyttade profiler.
