# Istorijska pitanja: specifikacija (napisana pre izmene koda)

**Polazni commit:** `637718a`. Originalni `eval/eval_set.json`, kod metrika, korpusi i M5 paket ostaju netaknuti.

## Propust

Sa `CURRENT_ONLY = True` (M5) zastarele verzije su potpuno izbačene iz pretrage. Pitanje „koliko dana rada od kuće je dozvoljavala politika iz 2024?“ zato dobija odgovor iz važeće politike (3 dana) ili odbijanje, iako korpus sadrži tačan odgovor (`hb-02`, 2 dana). Isto važi za `sh-02` (stara politika povraćaja) u corpus2. To je ograničenje 5 iz odeljka 8 izveštaja.

## Hipoteza

Filter je ispravan za obična pitanja, ali treba da zavisi od pitanja. Kada pitanje eksplicitno traži staru verziju (godina ili reči kao previous, old, former, before, earlier, used to), pretraga treba da za dokumente koji imaju više verzija koristi traženu verziju umesto važeće.

## Promena (jedna, iza prekidača `HISTORICAL_VERSIONS`)

`searchable_chunks(chunks, query)`:

- Bez istorijske namere: isto kao M5 (samo važeće verzije).
- Pitanje sadrži godinu: za naslove koji imaju više verzija zadržava se samo verzija te godine. Ako te godine nema, nijedna verzija tog naslova ne ulazi u pretragu (sistem treba da odbije).
- Pitanje ima reč prošlosti i nema reč sadašnjosti (now, currently, today, still): za naslove sa više verzija zadržava se samo zastarela verzija.
- Dokumenti sa jednom verzijom se ne menjaju.

Isti `query` se prosleđuje svim pozivaocima (`retrieve_top_k`, `evidence.select`, metrički alati).

## Skupovi (zamrznuti u ovom commitu, pre koda)

- `eval/history_set.json` (handbook, 10 pitanja): 4 istorijska sa odgovorom iz `hb-02`, 1 sa godinom važeće verzije, 3 kontrole sadašnjosti, 2 istorijska bez odgovora u korpusu (verzija 2022 ne postoji; za godišnji odmor ne postoji stara verzija).
- `eval/history2_set.json` (corpus2, 10 pitanja): isti raspored nad `sh-01`/`sh-02`.

## Očekivani efekat

Istorijska pitanja sa odgovorom (8) prelaze iz fail u pass. Pitanja o nepostojećoj verziji godine (HV08, HR08) se odbijaju. HV09 i HR09 (stara verzija koja ne postoji, bez godine) su teški slučajevi: sistem ne može da zna da se pravilo nije menjalo, pa mogu ostati neuspešni i pre i posle.

## Rizik regresije

Pitanja sa godinom ili rečima kao „before“ u drugom značenju („must be approved before booking“, „two weeks in advance“) mogu pogrešno aktivirati istorijski režim. Pošto se menjaju samo naslovi sa više verzija (Remote work policy, Returns policy), rizik je ograničen na ta dva dokumenta.

## Provera i pravilo prihvatanja

Kandidat `historical` protiv `shipped` na svim registrovanim skupovima (`python -m src.candidate_runner --candidates shipped historical --sets ...`). Uključuje se podrazumevano samo ako na postojećim skupovima nema nijedne nove regresije, a na istorijskim skupovima ima popravki. U suprotnom ostaje isključen i rezultat se dokumentuje. Uz to `pytest`, `scripts/check.sh` i frontend testovi.
