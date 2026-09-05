# 85 — Bänkkontraktet: hur allt benchas på samma sätt

Repot har **26 körningar** under `tests/protocol/`. Var och en mäter något
riktigt. Ingen av dem svarar på samma form, ingen vet om de andra finns, och
ingen kan säga vad som **inte** är benchat.

Det här dokumentet gör dem till en bänk.

---

## 1. Vad en bänkpost är

En bänkpost är ett **påstående med ett facit och ett sätt att falla**. Fem fält
är obligatoriska. Saknas ett är posten ogiltig, och en ogiltig post får inte
räknas som en grön.

| Fält | Vad det är | Varför det är obligatoriskt |
|---|---|---|
| `pastar` | En mening om vad förmågan gör | Ett påstående går att motbevisa. En etikett gör det inte |
| `under_prov` | Modulerna som döms | Utan den vet ingen vad ett grönt gäller |
| `facit` | Vad det rätta svaret är | En körning utan facit mäter att koden kör, inte att den har rätt |
| `facitkalla` | **Var facit kommer ifrån** | Se §2. Det här fältet är hela poängen |
| `trasiga_fall` | Vad som måste fällas | En grind utan trasigt fall är en förhoppning som fått ett filnamn |

---

## 2. Regeln som bär allt: facit hör utanför koden som prövas

`BENCH-4` i ett annat projekt: en grind stod grön i **månader** mot ett facit
som räknades fram av samma algoritm som dömdes. Talet var perfekt. Det mätte
ingenting.

**`facitkalla` får aldrig peka på något i `under_prov`.** Det är en mekanisk
kontroll, inte en uppmaning, och den körs på varje post.

Fem lagliga sorters facitkälla, i fallande styrka:

1. **En annan implementation.** STruC++ dömer vår ST-tolk (`M-54`). Två
   oberoende program som är oense pekar ut ett fel hos den ena.
2. **En mätning av verkligheten.** Ett inspelat I/O-spår från en riktig
   anläggning (`M-89`). Verkligheten argumenterar inte.
3. **Geometri eller fysik räknad ur scenens egna mått.** Fas 8:s överlämning:
   5,45 s ur avstånd och hastighet, mätt utfall 5,1–6,0 s.
4. **En människas facit, skrivet före körningen.** Bänkens spårfacit. Svagast
   av de fyra första, för människan kan ha fel — men hon kan inte ha *samma*
   fel som koden.
5. **En tidigare mätning**, med M-nummer. Bara för regressioner, och bara när
   den mätningen själv hade en starkare källa.

En sjätte sort finns och är **förbjuden**: facit räknat av koden som döms.

---

## 3. Vad `kraver` är till för

En bänk som bara kan köras på en maskin är ingen bänk. Varje post säger vad den
behöver: `inget`, `strucpp`, `vc`, `openplc`, `modell`, `windows`.

Det gör två saker. Den som kör vet vad som hoppas över **och varför** — ett
hopp är aldrig ett godkännande. Och rapporten kan säga *"18 av 26 körda här,
8 kräver VC"* i stället för att låtsas att åtta körningar inte finns.

---

## 4. Fullständigheten, och den är mekanisk

Två kontroller gör registret komplett **av konstruktion**:

* **Ingen föräldralös körning.** Varje `tests/protocol/kor_*.py` måste ha en
  post. En körning utan post är en mätning ingen vet om.
* **Ingen post utan körning.** Varje post måste peka på en fil som finns. En
  post utan körning är ett påstående utan täckning.

Det är de två som gör att *"bencha allting"* betyder något. Utan dem är
registret en lista någon minns att uppdatera — och ett verktyg man måste minnas
är redan glömt.

---

## 5. Vad bänken INTE gör

Den kör inte om det som kräver VC när VC inte finns, och den låtsas inte att
resultatet är känt.

Den säger inte att ett grönt är ett bevis. Ögat är felfinnande, aldrig bevis,
och det gäller varje post.

Och den kan inte se ett facit som är fel. Den kan bara se att facit kommer
någon annanstans ifrån än koden — vilket är den enda kontroll som går att
mekanisera, och exakt den som saknades när `BENCH-4` stod grön i månader.

---

## 6. Vilken domare som gäller när två domare är oense

Banken har sedan `M-146` **två** domare över samma spårfacit: `bank/domare.py`
genom vår egen ST-tolk, och `bank/domare_openplc.py` genom OpenPLC Runtime v4.
`M-153` körde hela banken genom båda — 185 enheter, n = 3, 1110 körningar — och
regeln nedan är skriven ur den mätningen, inte ur en princip.

**Auktoriteten ligger hos motorn, inte hos domarmekaniken.** Ett spår ur
OpenPLC är en laglig facitkälla (§2 sort 1); tolkens spår är det inte, för
tolken är både den som prövas och den som dömer. Men ett spår är ingen dom.
Domen gäller bara när de två domarna ställer **samma fråga** om spåret, och
`M-153` mätte att de inte alltid gör det.

I tre led:

1. **Domarna är överens** — domen står, oavsett vilken som fällde den. Så är
   det för 107 av 184 jämförbara enheter och för 151 av bankens 152 motbevis.
2. **De skiljer sig, och domarreglerna är desamma** — då gäller
   OpenPLC-domaren. Skälet är §2 och `M-125`, **inte** `M-153`: den mätningen
   hittade inget sådant fall, så ledet står oemotsagt men obelagt.
3. **De skiljer sig därför att REGLERNA skiljer sig** — då gäller ingen av dem.
   `M-153` namnger tre sådana ställen: flankfönstrets ensidiga tolerans
   (`domare.py` räknar i `[från, till]`, `domare_openplc.py` i
   `[från, till + 4 scan]`), sekvensens startvillkor (OpenPLC-domaren kör PLC:n
   150 ms med nollade ingångar före klockan, tolken börjar med `t=0`-stimulit
   redan verkställt) och `tolkfel:*`, som OpenPLC-domaren aldrig kan lämna
   (1 av bankens 152 motbevis). Skillnaden är bänkens egen defekt och ska
   lagas, inte vinnas. Nio av `M-153`:s tio utfallsoenigheter fälls på
   `flank:*` och den tionde på en flankräknare; tre av dem (A-07, P-03, C-04)
   är spårade hela vägen till en av de tre mekanismerna, resten är inte
   enskilt utredda.

Och över alla tre: **en dom ur OpenPLC-domaren gäller bara om den är stabil
över n ≥ 3.** Den domaren var oense med sig själv om 13 av 185 enheter och bytte
utfall på 4 av dem, och omprov visar att det inte beror på maskinens last. En
enhet som är grön i två körningar av tre är inte grön — den är omätt tills
instabiliteten är förklarad.
