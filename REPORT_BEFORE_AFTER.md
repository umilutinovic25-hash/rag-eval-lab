# Nedelja 7: izveštaj pre/posle

**Par:** Uroš Milutinović i [drugi član para]  
**Demonstraciju na Sesiji 2 vodi:** [ime]  
**Promena:** M5, filter važeće verzije (`CURRENT_ONLY = True`)  
**Commitovi:** `ee583f3` početno stanje → `2ceaced` specifikacija → `45b8172` promena

> Obavezni deo (odeljci 1–11) odnosi se na commit `45b8172`. Posle njega su odvojeno dodate i izmerene napredne promene A1–A4 (odeljak 12). Za reprodukciju obaveznog dela: `git checkout 45b8172`, zatim obrisati `src/__pycache__` (ili pokrenuti sa `PYTHONDONTWRITEBYTECODE=1`). Promena `0.02` → `0.12` ne menja veličinu fajla, pa Python posle brzog `checkout`-a može da učita stari bytecode i prikaže pogrešan rezultat; to nam se desilo pri proveri.

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

Claude Code (AI asistent) je korišćen da pročita kod checkpointa, pokrene testove i eval, izdvoji ocene iz `top_k` radi dijagnoze propusta, napiše nacrt specifikacije i implementira filter sa testom, a u naprednom delu i promene A1–A4, kontrolnu proveru i automatski pregled koda (odeljak 12). Sve tvrdnje su proverene merenjem, a ne na osnovu reči asistenta: `results/before.json` i `results/after.json` su napravljeni istom komandom, `eval_compare` potvrđuje isti otisak i samo jedno promenjeno podešavanje, a E06 je ručno proveren preko CLI-ja pre i posle (izlazi u `evidence/`). [Dopuniti: šta je svako od nas ručno proverio.]

## 11. Doprinos

| Član | Doprinos |
| --- | --- |
| Uroš Milutinović | [dopuniti] |
| [drugi član para] | [dopuniti] |

## 12. Napredni cilj (odvojeno od obaveznog dela)

Četiri dodatne promene. Svaka ima svoju specifikaciju, commitovanu pre izmene koda (`docs/advanced-specs.md`), i meri se u odnosu na rezultat **prethodne** promene, istom komandom i sa istim `eval_set_sha256`. Izlazi poređenja su u `evidence/advanced/compare-*.txt`.

| Korak | Promena | Spec / kod | Poređenje sa | Passed | Fixed | Regressed | Promenjena podešavanja |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M5 (obavezno) | filter važeće verzije | `2ceaced` / `45b8172` | `before` | 6 → 7 | E06 | none | `CURRENT_ONLY` |
| A1 | sečenje po rečenicama (M1) | `66ea2ff` / `57895a8` | `after` | 7 → 9 | E04, E09 | none | `CHUNK_STRATEGY` |
| A2 | prag odbijanja 0.02 → 0.12 (M3) | `235ff78` / `b604373` | `adv1` | 9 → 10 | E10 | none | `REFUSAL_THRESHOLD` |
| A3a | infrastruktura za embeddinge, režim ostaje `lexical` | `acd95d0` / `a246b7c` | `adv2` | 10 → 10 | none | none | 3 nova (vidi niže) |
| A3b | semantička pretraga, `bge-m3` preko Ollama | `acd95d0` / `cff812f` | `adv3a` | 10 → 12 | E05, E11 | none | `RETRIEVAL_MODE` |
| A4 | prag za citate 0.65 (M4) | `8cc7213` / `0781d3f` | `adv3b` | 12 → 12 | none | none | `CITATION_MIN_SCORE` (posle pregleda koda: `SEMANTIC_CITATION_MIN_SCORE`) |

Ukupno (`evidence/advanced/compare-before-vs-A4.txt`): **6/12 → 12/12**, behaviour accuracy 0.83 → 1.00, retrieval hit rate 0.78 → 1.00, mean citation precision 0.45 → 1.00. Ovo poređenje upozorava na više promenjenih podešavanja, jer zbirno obuhvata svih pet koraka. Pojedinačni doprinosi su u tabeli iznad.

**A3a upozorenje o više podešavanja:** A3a dodaje `RETRIEVAL_MODE = "lexical"`, `EMBEDDING_MODEL` i `SEMANTIC_REFUSAL_THRESHOLD`. Poslednja dva se koriste samo u semantičkom režimu, pa je rezultat identičan `adv2` (Fixed none, Regressed none, sve metrike +0.0). Zatim A3b menja **samo** `RETRIEVAL_MODE` i poređenje ne upozorava. Tako je efekat semantičke pretrage pripisan jednoj odluci.

**Zašto semantička pretraga ima sopstveni prag:** kosinusne ocene (0.36–0.81) nisu na istoj skali kao leksičke (0.07–0.58). Zato `REFUSAL_THRESHOLD = 0.12` iz A2 u semantičkom režimu više ne važi i prestaje da utiče na rezultat; E10 se sada odbija pragom 0.60 (vrh 0.458).

**Ručna provera (CLI):**

- E05 (`evidence/advanced/cli-E05-semantic.txt`): citira `hb-01-chunk-1` (0.6474), *Equipment replacement (2026, current)*: „…handover can take up to 5 business days“.
- E11 (`evidence/advanced/cli-E11-semantic.txt`): `Refused: True`, vrh `hb-07-chunk-1` sa 0.5673, ispod praga 0.60.

Oba izlaza se slažu sa `results/adv3b.json`. CLI izlazi su snimljeni pre A4, pa E05 tu još ima drugi citat `hb-06-chunk-0` (0.5698); u `adv4.json` taj citat je uklonjen.

**Kontrolna provera van eval skupa:** pragovi 0.60 i 0.65 su birani gledajući isti eval skup, pa 12/12 može biti preoptimistično. Napravio sam zato 10 novih pitanja (6 podržanih parafraza, 4 nepodržana) **izvan** `eval/eval_set.json`, koji nije menjan (`evidence/advanced/holdout_probe.py`, izlaz u `holdout-probe.txt`). Rezultat: leksički režim (A2 stanje) **6/10**, semantički **10/10**. Ovo je mala, ručno napisana provera, a ne zamena za veći eval skup.

**Trošak i zavisnosti semantičke pretrage:** Ollama i model `bge-m3` (1.2 GB) za svako pitanje koje nije u kešu; prvi eval bez keša traje oko 2 s na M-seriji Maca, a sa kešom kao i leksički. Keš (`data/embedding_cache.json`, 36 vektora, ~380 KB) je commitovan, pa eval i CLI za 12 eval pitanja rade bez mreže. To je provereno sa ugašenim Ollama: rezultat je identičan. Bez API ključa, bez plaćenog servisa i bez vektorske baze.

**Greške pronađene i ispravljene usput:**

1. **Sečenje usred reči** (početni kod): `chars` strategija pravi krhotine kao „op is set up“, „iness days“ i „ardware“, pa se tokeni nikad ne poklapaju sa pitanjem. Rešeno u A1.
2. **Moja greška u A3a:** `load_cache`/`save_cache` su imali podrazumevani argument `path=CACHE_PATH`, koji se vezuje pri definisanju funkcije. Zato `monkeypatch` u testu nije delovao i test je upisao lažne vektore u pravi keš. Ispravljeno pre commita (putanja se čita pri pozivu), a lažni keš je obrisan.
3. **Testovi su zavisili od režima:** posle A3b `test_retrieve_top_k_returns_empty_for_unrelated_query` je pao i pozvao Ollama. Test nije oslabljen. Dodat je `tests/conftest.py`, koji testove drži u leksičkom režimu i blokira svaki mrežni poziv. Keš je zatim napravljen ponovo, samo iz eval pokretanja.
4. **CLI bez Ollama** je pucao sa traceback-om. Sada ispisuje jasnu poruku i izlazi sa kodom 2.

**Završna provera i pregled koda (posle A4):**

- *Reprodukcija iz čistog klona*, novo `.venv`, ugašen Ollama: svih 7 commitova iz tabele (`ee583f3` … `0781d3f`) daje tačno iste redove kao sačuvani JSON-ovi (6, 7, 9, 10, 10, 12, 12).
- *`eval/eval_set.json`, `src/eval_runner.py` i `src/eval_compare.py`* su bajt-identični početnom stanju; SHA-256 eval skupa je isti kao u originalnom ZIP-u.
- *Red-green provera novih testova:* za svaki novi test popravka je privremeno uklonjena (10 mutacija); svaki put je bar jedan test pao.
- *Automatski pregled koda* (skill `code-review`, nivo high) dao je 10 nalaza. Ispravljeno u commitu `48159d4`:
  1. `CITATION_MIN_SCORE = 0.65` je bio na kosinusnoj skali, a važio je i u leksičkom režimu. Izmereno: povratak na `lexical` bi dao **9/12** umesto 10/12. Sada postoji `SEMANTIC_CITATION_MIN_SCORE = 0.65`, a `CITATION_MIN_SCORE` je vraćen na `None`; `lexical` ponovo daje 10/12.
  2. Timeout, neispravan JSON ili pogrešan broj vektora iz Ollama sada daju jasnu `EmbeddingError` umesto traceback-a.
  3. Keš se upisuje atomski (privremeni fajl + `os.replace`), a oštećen keš daje jasnu grešku.
  4. Novi test proverava da commitovani keš pokriva ceo eval skup u semantičkom režimu bez mreže.

  Posle ispravki eval je identičan `adv4` (`evidence/advanced/compare-A4-vs-review-fixes.txt`). Poređenje upozorava na dva podešavanja jer je prag samo premešten iz `CITATION_MIN_SCORE` u `SEMANTIC_CITATION_MIN_SCORE`; vrednost i rezultat su isti.

  Svesno nije menjano: `eval_runner` ne hvata `EmbeddingError` (kod koji računa metrike se ne sme menjati; greška ima jasnu poruku); `RETRIEVAL_MIN_SCORE = 0.01` nema efekta na kosinusnoj skali (filtriranje radi prag odbijanja); rečenica duža od `CHUNK_SIZE` postaje jedan duži chunk, kako meni M1 i propisuje, a `CHUNK_OVERLAP` se tada ne koristi iako se beleži u konfiguraciji; `CURRENT_ONLY` isključuje `superseded` umesto da uključuje samo `current` (korpus ima samo ta dva statusa, a meni M5 tako definiše filter); keš se čita pri svakom pitanju, što je zanemarljivo za 36 vektora.

**Preostala ograničenja posle A1–A4:**

1. **Tanke margine:** najslabije podržano eval pitanje ima 0.647, a najjače nepodržano 0.567, pa je prag 0.60 udaljen samo ~0.04 sa obe strane. U kontrolnoj proveri „gym membership“ ima 0.578, a „parking spot“ 0.667. Veći eval skup bi verovatno pokazao greške.
2. **Pragovi su kalibrisani na eval skupu** na kojem se i meri.
3. **Zavisnost od Ollama** za nova pitanja; leksički režim ostaje dostupan kao potpuno offline rezerva.
4. **Embeddingi slabije hvataju tačne brojeve i termine.** Hibridna pretraga (BM25 + embeddingi) bila bi sledeći korak, ali nije merena.
5. **Istorijska pitanja** i dalje nisu odgovoriva zbog `CURRENT_ONLY` (kao u obaveznom delu).
6. **„Odgovor“ je i dalje spisak citiranih chunk-ova**, ne generisana rečenica. Generisanje preko LLM-a nije rađeno.

## Dokazi

- `evidence/before.json`, `evidence/after.json`: oba eval rezultata (kopije iz `results/`, koji git ignoriše)
- `evidence/compare.txt`: izlaz `eval_compare`
- `evidence/change.diff`: diff promene
- `evidence/cli-E06-before.txt`, `evidence/cli-E06-after.txt`: ručna CLI provera
- `evidence/pytest-before.txt`, `evidence/pytest-after.txt`
- `docs/change-spec.md`: specifikacija, commitovana pre promene
- Napredni deo: `docs/advanced-specs.md`; `evidence/advanced/` (`adv1.json`, `adv2.json`, `adv3a.json`, `adv3b.json`, `adv4.json`, `compare-*.txt`, CLI izlazi, kontrolna provera)
