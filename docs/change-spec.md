# Specifikacija promene: filter važeće verzije (M5)

Napisano posle početnog merenja (`results/before.json`, 6/12), a pre izmene koda.

| Polje | Sadržaj |
| --- | --- |
| Propust | **E06** „How many days per week can I work remotely?“ Očekivano: odgovor iz `hb-03` (Remote work policy 2026, `current`) sa činjenicom „3 days per week“. Dobijeno: sistem citira `hb-02-chunk-0` i `hb-02-chunk-1` (Remote work policy 2024, `superseded`) i vraća „2 days per week“. Hit = no, Fact = no, CitPrec = 0.00. Tip: retrieval (pogrešno rangiranje po verziji), posledica je pogrešan odgovor. |
| Hipoteza | Tekstovi iz 2024. i 2026. su skoro isti, a chunk-ovi stare verzije su kraći, pa `lexical_score` (preklapanje / dužina chunk-a) daje višu ocenu staroj verziji (0.48 i 0.40 prema 0.37 za `hb-03-chunk-0`). Sistem ne koristi metapodatak `status`, pa zastarela politika može da potisne važeću. |
| Promena | Implementirati `CURRENT_ONLY` u `searchable_chunks` (`src/retrieval.py`): kada je uključeno, chunk-ovi sa `status == "superseded"` se ne pretražuju. U `src/config.py` postaviti `CURRENT_ONLY = True`. Jedna namera: pretražuje se samo važeća verzija dokumenata. Ostala podešavanja se ne menjaju. |
| Očekivani efekat | E06 prelazi u PASS: top-2 postaje `hb-03-chunk-0` (sadrži „3 days per week“) i `hb-03-chunk-1`, CitPrec 1.00. Retrieval hit rate raste sa 0.78 na 0.89. E01, E02 i E03 trenutno imaju `hb-02` kao dopunski citat; on će biti zamenjen drugim chunk-om, ali činjenica ostaje u prvom citatu, pa očekujem da ostanu PASS. |
| Rizik regresije | (1) Pitanja o istoriji ili starim pravilima više ne mogu da se odgovore; eval skup nema takvo pitanje, pa se to neće videti u metrikama. (2) Drugi citat za E01–E03 može postati drugi nebitan chunk; CitPrec bi ostao 0.50, a ne bi trebalo da padne ispod 0.50. (3) Ne očekujem promenu za E04, E05, E09, E10 i E11, jer `hb-02` nije u njihovom top-2. |
| Provera | `python -m pytest`, zatim ista komanda `python -m src.eval_runner --out results/after.json` i `python -m src.eval_compare results/before.json results/after.json`. Očekivano: Fixed = E06, Regressed = none, Changed settings = samo `CURRENT_ONLY`, isti `eval_set_sha256`. Ručno: `python -m src.cli --question "How many days per week can I work remotely?" --show-retrieved` mora da citira `hb-03` (version 2026, current). |
