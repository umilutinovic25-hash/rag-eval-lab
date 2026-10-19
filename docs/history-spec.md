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

Napomena: refuse stavke su dopunjene poljima `expected_doc_ids: []` i `expected_fact: null` (format eval_runner-a) pre prvog merenja i pre izmene koda; pitanja i očekivanja nisu menjana.

## Rezultat (posle implementacije)

| Skup | Pre (`shipped`) | Posle (`historical`) | Popravljeno | Regresije |
| --- | ---: | ---: | --- | --- |
| history | 5/10 | 10/10 | HV01, HV02, HV03, HV04, HV08 | nema |
| history2 | 4/10 | 8/10 | HR01, HR02, HR04, HR08 | nema |
| eval | 12/12 | 12/12 | | nema |
| holdout | 34/34 | 34/34 | | nema |

**Izmena pravila pre prihvatanja.** Prva verzija pravila reči prošlosti je na postojećim skupovima pogrešno aktivirala istorijski režim kod 10 pitanja („is used to reserve“, „previous instructions“, „17-year-old“). Pre merenja tih skupova pravilo je suženo: reč prošlosti važi samo uz imenicu kao policy, rules, version, limit. Posle toga nijedno od 458 pitanja van istorijskih skupova ne dobija drugačiju listu kandidata (`evidence/upgrade/history-trigger-audit.json`), pa njihov rezultat ne može da se promeni. Puno merenje svih 15 skupova dvaput je prekinuto padom Ollama servera; ova provera ga zamenjuje.

**Preostalo.** HR03 („before the current policy“) dobija staru verziju među kandidatima, ali pretraga izabere drugi dokument. HR09 (stara cena koja ne postoji u korpusu) sistem ne može da prepozna. Oba su sada viđena pitanja.

Dokazi: `evidence/upgrade/history-before.json`, `history-final.json`, `history-final.log`, `history-trigger-audit.json`, `history-cli.txt`.

## Druga promena: proveravač vidi verziju odlomka u istorijskom režimu

**Propust (HR03, viđeno):** pretraga stavi `sh-02` na prvo mesto, ali proveravač odlomka ne zna da je to stara verzija i odbije ga jer pitanje traži „before the current policy“. Zatim prihvati nebitan `sh-07`.

**Promena (`HISTORICAL_JUDGE_CONTEXT`):** kada `searchable_chunks` radi u istorijskom režimu, proveravač dobija isti kontekst verzije koji već postoji za `VERSION_CONTEXT` („Document: …; version: …; status: …“). Van istorijskog režima ništa se ne menja.

**Slepi skup:** `eval/history3_set.json` (8 pitanja, corpus2), commitovan pre koda i pokrenut jednom posle implementacije. Uključuje „before the current“ formulacije, jednu nepostojeću godinu i kontrolu sa godinom u drugom značenju (HB08).

**Pravilo prihvatanja:** bez regresija na history, history2, eval, holdout i bez promene liste kandidata van istorijskih skupova; history3 se meri jednom.

### Rezultat druge promene: odbijena

| Skup | `historical` (uključeno) | `historical-judge` | Popravljeno | Regresije |
| --- | ---: | ---: | --- | --- |
| eval / holdout | 12/12, 34/34 | 12/12, 34/34 | | nema |
| history | 10/10 | 9/10 | | HV09 |
| history2 | 8/10 | 9/10 | HR03 | |
| history3 (slepi, jedno pokretanje) | 8/8 | 8/8 | | |

Kontekst verzije popravlja HR03, ali na HV09 („old annual leave allowance“) proveravač prihvata važeću politiku godišnjeg odmora kao odgovor na pitanje o staroj verziji koja ne postoji. Ukupno je izjednačeno, a promena ima regresiju, pa `HISTORICAL_JUDGE_CONTEXT` ostaje `False`. Slepi history3 potvrđuje prihvaćenu prvu promenu: 8/8 na pitanjima koja ranije nisu viđena. Dokazi: `evidence/upgrade/history-judge.json`, `history-judge.log`.
