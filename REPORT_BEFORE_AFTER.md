# Nedelja 7: izveštaj pre/posle

**Par:** Uroš Milutinović i [drugi član para]  
**Demonstraciju na Sesiji 2 vodi:** [ime]  
**Promena:** M5, filter važeće verzije (`CURRENT_ONLY = True`)  
**Commitovi:** `ee583f3` početno stanje → `2ceaced` specifikacija → `45b8172` promena

## 1. Početna provera

- `python -m pytest`: **18 passed** (`evidence/pytest-before.txt`)
- `python -m src.eval_runner --out results/before.json`: **6/12**
- `eval_set_sha256`: `afe46db1e75a0b85bb5c9a93b6763e3b96e5cd7b289e12da6d2671e4d8650064`

```
ID   Category                 Expected Got     Hit  Fact  CitPrec Pass
----------------------------------------------------------------------
E01  supported                answer   answer  yes  yes   0.50    PASS
E02  supported                answer   answer  yes  yes   0.50    PASS
E03  supported                answer   answer  yes  yes   0.50    PASS
E04  chunk-boundary           answer   answer  yes  no    1.00    FAIL
E05  paraphrase               answer   answer  no   no    0.00    FAIL
E06  versioned                answer   answer  no   no    0.00    FAIL
E07  supported                answer   answer  yes  yes   1.00    PASS
E08  supported                answer   answer  yes  yes   0.50    PASS
E09  chunk-boundary           answer   answer  yes  no    1.00    FAIL
E10  unsupported              refuse   answer  -    -     0.00    FAIL
E11  unsupported-near-domain  refuse   answer  -    -     0.00    FAIL
E12  unsupported              refuse   refuse  -    -     -       PASS

Passed: 6/12
Behaviour accuracy: 0.83
Retrieval hit rate (supported): 0.78
Mean citation precision (answered): 0.45
```

## 2. Dokumentovani propusti

Ocene su iz `top_k` polja u `results/before.json`.

| ID | Očekivano | Dobijeno | Tip propusta |
| --- | --- | --- | --- |
| **E06** | Odgovor iz `hb-03` (2026, current): „3 days per week“ | Citira `hb-02-chunk-0` (0.48) i `hb-02-chunk-1` (0.40), verziju 2024 koja je `superseded`, sa „2 days per week“. Važeći `hb-03-chunk-0` ima 0.37 i ispada iz top-2. | Retrieval (pogrešno rangiranje po verziji), posledica je pogrešan odgovor |
| **E04**, **E09** | Citat sa „5 business days“ iz `hb-01` | Pravi dokument je nađen (Hit = yes, CitPrec 1.00), ali su citirani `hb-01-chunk-0` i `hb-01-chunk-2`. Činjenica je u `hb-01-chunk-1`, koji je tek peti po oceni. Sečenje na 140 znakova deli rečenicu („…set up by IT staff with \| your files…“). | Chunkovanje |
| **E10** | Odbijanje (cena akcija nije u priručniku) | Odgovara sa 0.059 iz `hb-09-chunk-1` i `hb-05-chunk-1`, koji dele samo česte reči. | Pogrešan odgovor (prag odbijanja 0.02 je prenizak) |
| **E11** | Odbijanje (parental leave ne postoji u korpusu) | Odgovara sa 0.17 iz `hb-07` (Annual leave), jer deli reči „leave“ i „policy“. | Pogrešan odgovor (pitanje blisko domenu) |
| **E05** | `hb-01`, „5 business days“ | „notebook computer“ nema leksičko preklapanje sa „laptop“; vrh je `hb-06` (Onboarding). Hit = no. | Retrieval (parafraza) |

Uz to, E01, E02, E03 i E08 imaju CitPrec 0.50 jer se uvek citiraju oba top-2 rezultata, i kada je drugi nebitan (propust citata, dopuna).

## 3. Specifikacija jedne promene

Napisana i commitovana pre izmene koda (`docs/change-spec.md`, commit `2ceaced`).

| Polje | Sadržaj |
| --- | --- |
| Propust | E06: sistem citira zastarelu politiku rada od kuće (2024, `superseded`) i daje „2 days per week“ umesto „3 days per week“. |
| Hipoteza | Tekstovi 2024. i 2026. su skoro isti, a stari chunk-ovi su kraći, pa `lexical_score` (preklapanje / dužina chunk-a) daje višu ocenu staroj verziji. Pipeline ne koristi metapodatak `status`. |
| Promena | Implementirati `CURRENT_ONLY` u `searchable_chunks` (izbaciti `status == "superseded"`) i uključiti ga u `config.py`. |
| Očekivani efekat | E06 → PASS sa `hb-03-chunk-0`, CitPrec 1.00. Hit rate 0.78 → 0.89. E01–E03 ostaju PASS (dopunski citat `hb-02` zamenjuje drugi chunk). |
| Rizik regresije | Pitanja o istoriji ili starim pravilima više nisu odgovoriva (eval to ne pokriva). Dopunski citat za E01–E03 može postati drugi nebitan chunk. Za E04, E05, E09, E10 i E11 ne očekujem promenu. |
| Provera | `pytest`, ista eval komanda sa `--out results/after.json`, `eval_compare`, ručni CLI za E06. |

## 4. Primenjena promena

`evidence/change.diff` (`git diff ee583f3 HEAD -- src tests`):

```diff
--- a/src/config.py
-CURRENT_ONLY = False
+CURRENT_ONLY = True
--- a/src/retrieval.py
 def searchable_chunks(chunks: list[Chunk]) -> list[Chunk]:
     if config.CURRENT_ONLY:
-        raise NotImplementedError("CURRENT_ONLY = True is not implemented yet.")
+        return [chunk for chunk in chunks if chunk.status != "superseded"]
     return chunks
```

Dodat je i jedan test mehanike (`test_current_only_excludes_superseded_chunks` u `tests/test_retrieval.py`). Test ne menja ponašanje sistema, samo proverava da filter radi u oba položaja. Kod koji računa metrike i `eval/eval_set.json` nisu menjani.

## 5. Ponovno merenje

- `python -m pytest`: **19 passed** (`evidence/pytest-after.txt`)
- `python -m src.eval_runner --out results/after.json`: **7/12**, isti `eval_set_sha256`

```
ID   Category                 Expected Got     Hit  Fact  CitPrec Pass
----------------------------------------------------------------------
E01  supported                answer   answer  yes  yes   0.50    PASS
E02  supported                answer   answer  yes  yes   0.50    PASS
E03  supported                answer   answer  yes  yes   0.50    PASS
E04  chunk-boundary           answer   answer  yes  no    1.00    FAIL
E05  paraphrase               answer   answer  no   no    0.00    FAIL
E06  versioned                answer   answer  yes  yes   1.00    PASS
E07  supported                answer   answer  yes  yes   1.00    PASS
E08  supported                answer   answer  yes  yes   0.50    PASS
E09  chunk-boundary           answer   answer  yes  no    1.00    FAIL
E10  unsupported              refuse   answer  -    -     0.00    FAIL
E11  unsupported-near-domain  refuse   answer  -    -     0.00    FAIL
E12  unsupported              refuse   refuse  -    -     -       PASS

Passed: 7/12
Behaviour accuracy: 0.83
Retrieval hit rate (supported): 0.89
Mean citation precision (answered): 0.55
eval_set_sha256: afe46db1e75a0b85bb5c9a93b6763e3b96e5cd7b289e12da6d2671e4d8650064
```

## 6. Poređenje

`python -m src.eval_compare results/before.json results/after.json` (`evidence/compare.txt`):

```
Fixed (fail -> pass): E06
Regressed (pass -> fail): none
Unchanged: E01, E02, E03, E04, E05, E07, E08, E09, E10, E11, E12

Summary:
  passed: 6 -> 7 (+1)
  total: 12 -> 12 (+0)
  behaviour_accuracy: 0.8333 -> 0.8333 (+0.0)
  retrieval_hit_rate: 0.7778 -> 0.8889 (+0.1111)
  mean_citation_precision: 0.4545 -> 0.5455 (+0.091)

Changed settings:
  CURRENT_ONLY: False -> True
```

Promenjeno je samo jedno podešavanje, pa alat ne upozorava na više promena. Otisak eval skupa je isti, pa je poređenje prihvaćeno.

**Ručna provera (E06):** `python -m src.cli --question "How many days per week can I work remotely?" --show-retrieved`

- Pre (`evidence/cli-E06-before.txt`): citati `hb-02-chunk-0` i `hb-02-chunk-1`, *Remote work policy (version 2024, superseded)*, tekst „up to 2 days per week“.
- Posle (`evidence/cli-E06-after.txt`): citati `hb-03-chunk-0` (0.3704) i `hb-03-chunk-1` (0.1429), *Remote work policy (version 2026, current)*, tekst „up to 3 days per week“.

To se slaže sa redom E06 u `results/after.json`.

## 7. Zaključak

Hipoteza je potvrđena: E06 je popravljen jer zastarela verzija više ne ulazi u pretragu, a nijedno pitanje nije palo. Rast CitPrec (0.45 → 0.55) dolazi samo od E06 (0.00 → 1.00). E01, E02 i E03 ostaju na 0.50.

**Regresije:** u eval skupu nema nijedne. Promena koja se ne vidi u metrikama: dopunski drugi citat za E01, E02 i E03 je prešao sa `hb-02` na `hb-03` (npr. E01: `hb-02-chunk-0` → `hb-03-chunk-0`). Citat je i dalje nebitan za pitanje, samo iz važeće verzije. To je predviđeno u specifikaciji.

## 8. Preostala ograničenja

1. **E04 i E09 (chunkovanje):** činjenica „5 business days“ i dalje je u chunk-u koji nije u top-2. Ova promena to nije ni ciljala. Kandidat za sledeću promenu je M1 (sečenje po rečenicama).
2. **E10 i E11 (pogrešan odgovor umesto odbijanja):** prag 0.02 je prenizak. E11 („parental leave“) ima vrh 0.17, više od nekih podržanih pitanja (E02 ima 0.13), pa ni sama kalibracija praga (M3) ne bi rešila E11 bez rizika da se odbiju podržana pitanja.
3. **E05 (parafraza):** leksički retrieval ne zna da je „notebook computer“ isto što i „laptop“. Nijedna stavka iz menija to ne rešava; potrebni su sinonimi, query rewriting ili embeddings.
4. **Dopuna citata:** E01, E02, E03 i E08 i dalje citiraju nebitan drugi chunk (CitPrec 0.50).
5. **Istorijska pitanja:** sa `CURRENT_ONLY = True` sistem više ne može da odgovori na pitanje „kakva je bila politika 2024?“. Eval skup to ne meri. Bolja buduća varijanta bila bi da se verzija ne izbacuje nego koristi pri rangiranju, ili da se filter uključuje po pitanju.

## 9. Pregled para

> [Komentar para koji je pregledao izveštaj, iz Discord niti „Nedelja 7: pregled para“]
>
> 1. Da li je promena zaista jedna i da li odgovara specifikaciji?
> 2. Da li rezultat pre/posle podržava zaključak?
> 3. Da li je neka regresija ili ograničenje izostavljeno?

## 10. Korišćenje AI-ja

Claude Code (AI asistent) je korišćen da pročita kod checkpointa, pokrene testove i eval, izdvoji ocene iz `top_k` radi dijagnoze propusta, napiše nacrt specifikacije i implementira filter sa testom. Sve tvrdnje su proverene merenjem, a ne na osnovu reči asistenta: `results/before.json` i `results/after.json` su napravljeni istom komandom, `eval_compare` potvrđuje isti otisak i samo jedno promenjeno podešavanje, a E06 je ručno proveren preko CLI-ja pre i posle (izlazi u `evidence/`). [Dopuniti: šta je svako od nas ručno proverio.]

## 11. Doprinos

| Član | Doprinos |
| --- | --- |
| Uroš Milutinović | [dopuniti] |
| [drugi član para] | [dopuniti] |

## Dokazi

- `evidence/before.json`, `evidence/after.json`: oba eval rezultata (kopije iz `results/`, koji git ignoriše)
- `evidence/compare.txt`: izlaz `eval_compare`
- `evidence/change.diff`: diff promene
- `evidence/cli-E06-before.txt`, `evidence/cli-E06-after.txt`: ručna CLI provera
- `evidence/pytest-before.txt`, `evidence/pytest-after.txt`
- `docs/change-spec.md`: specifikacija, commitovana pre promene
