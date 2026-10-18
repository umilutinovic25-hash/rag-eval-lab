# Rezultati C1–C6 — 18.10.2026.

Specifikacija: hardening-spec.md. Polazni audit: 2e24944. Originalni skupovi, originalne metrike i keševi nisu menjani.

- C1: sintetička zamena 800→900 i uklanjanje Never odbijaju se; ne tvrdi se semantička relevantnost iz doslovnog podniza.
- C2: prazan/neispravno referenciran odgovor, generisani Source i broj kog nema u izvoru zamenjuju se izvornim tekstom. Fallback razlog je vidljiv na RagAnswer.
- C3: različite dimenzije, NaN, Infinity, boolean i nebrojčani elementi odbijaju se. Neispravna struktura keša i prazan LLM odgovor daju jasnu grešku.
- C4: CLI offline profil uspeva na novom pitanju bez modela; prazno pitanje ne poziva retrieval. Gray-zone ne može da se kombinuje sa lexical skalom.
- C5: sva pitanja ulaze u izveštaj, a semantička tačnost ostaje eksplicitno not_assessed. Sintetička promena negacije dobija review flag. Flag je heuristika, ne presuda.
- C6: replay sa manifestom i nula poziva modelima; cold režim je implementiran ali nije izvršen protiv modela u ovom radu. Istorijski model digesti ostaju unknown.

## Stvarne provere

107 testova prolazi. Za nove regresione slučajeve potvrđeno je crveno stanje pre popravke, pa zeleno posle nje. Prikaz testa i replay rezultati su u evidence/hardening/.

| Skup | Pre | Posle | Redovi rezultata |
| --- | --- | --- | --- |
| eval | 12/12 | 12/12 | identični |
| holdout | 34/34 | 34/34 | identični |
| test1 | 23/24 | 23/24 | identični |
| test2 | 29/32 | 29/32 | identični |

Za replay je kodom zabranjena svaka model request funkcija, a brojači su 0 za sva četiri skupa. Nijedan od postojećih keširanih odgovora nije aktivirao novi fallback. To ne umanjuje važnost testiranih negativnih slučajeva, ali ne znači da je kvalitet odgovora na nove upite izmeren.

Paket deliverables/week07-M5-minimum.zip raspakovan je u privremeni direktorijum: 19 testova prolazi, eval 7/12, popravljen E06, nema regresija, promenjen samo CURRENT_ONLY. Nema naprednih modela u njegovom kodu. Ljudska polja u priloženom izveštaju ostaju prazna i paket treba ponovo izgraditi posle njihovog popunjavanja.

## Šta ostaje

T02, U07 i U11 su pogrešna odbijanja. U13 je odgovor sa neodgovarajućim dokazom. Nismo menjali ponašanje prema ovim viđenim pitanjima da bismo prikazali 100% rezultat. Nema potpune automatske semantičke garancije; nema nezavisne ljudske revizije dok je stvarni par ne uradi. Fiksni eval ostaje mera citiranih pasusa, ne istinitosti svih rečenica.
