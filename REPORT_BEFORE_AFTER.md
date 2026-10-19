# Nedelja 7: izveštaj pre/posle

**Autor:** Uroš Milutinović (samostalan rad)
**Demonstraciju na Sesiji 2 vodi:** Uroš Milutinović
**Promena:** M5, filter važeće verzije (`CURRENT_ONLY = True`)  
**Commitovi:** `ee583f3` početno stanje → `2ceaced` specifikacija → `45b8172` promena (obavezni deo); dalji krugovi do `54358d4`  
**Datum:** 2026-10-17 (poslednje ažuriranje 2026-10-19: odeljak 22)
**Šablon:** `docs/sablon-izvestaj-pre-posle.md` (napravljen prema zahtevima zadatka, jer zvanični šablon nije bio dostavljen)

> Obavezni deo (odeljci 1–11) odnosi se na commit `45b8172`; napredni deo i ispravke C1–C6 su odvojeni u odeljcima 12–18. Brojevi u odeljcima 16–17 (23/24, 29/32, 176 testova) su istorijski; aktuelno stanje je u odeljku 18. Posle checkout-a ukloniti postojeći `src/__pycache__`. `PYTHONDONTWRITEBYTECODE=1` sprečava upis novih .pyc fajlova, ali ne sprečava učitavanje postojećeg zastarelog bytecode-a.

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

## 2. Dokumentovani propusti (najmanje dva)

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

## 7. Zaključak i regresije

Hipoteza je potvrđena: E06 je popravljen jer zastarela verzija više ne ulazi u pretragu, a nijedno pitanje nije palo. Rast CitPrec (0.45 → 0.55) dolazi samo od E06 (0.00 → 1.00). E01, E02 i E03 ostaju na 0.50.

**Regresije:** u eval skupu nema nijedne. Promena koja se ne vidi u metrikama: dopunski drugi citat za E01, E02 i E03 je prešao sa `hb-02` na `hb-03` (npr. E01: `hb-02-chunk-0` → `hb-03-chunk-0`). Citat je i dalje nebitan za pitanje, samo iz važeće verzije. To je predviđeno u specifikaciji.

## 8. Preostala ograničenja (najmanje jedno)

1. **E04 i E09 (chunkovanje):** činjenica „5 business days“ i dalje je u chunk-u koji nije u top-2. Ova promena to nije ni ciljala. Kandidat za sledeću promenu je M1 (sečenje po rečenicama).
2. **E10 i E11 (pogrešan odgovor umesto odbijanja):** prag 0.02 je prenizak. E11 („parental leave“) ima vrh 0.17, više od nekih podržanih pitanja (E02 ima 0.13), pa ni sama kalibracija praga (M3) ne bi rešila E11 bez rizika da se odbiju podržana pitanja.
3. **E05 (parafraza):** leksički retrieval ne zna da je „notebook computer“ isto što i „laptop“. Nijedna stavka iz menija to ne rešava; potrebni su sinonimi, query rewriting ili embeddings.
4. **Dopuna citata:** E01, E02, E03 i E08 i dalje citiraju nebitan drugi chunk (CitPrec 0.50).
5. **Istorijska pitanja:** sa `CURRENT_ONLY = True` sistem više ne može da odgovori na pitanje „kakva je bila politika 2024?“. Eval skup to ne meri. Bolja buduća varijanta bila bi da se verzija ne izbacuje nego koristi pri rangiranju, ili da se filter uključuje po pitanju.

## 9. Pregled para

Projekat sam 19. 10. 2026. poslao drugom polazniku na pregled, a njegov odgovor nije stigao do slanja izveštaja. Na tri pitanja pregleda zato odgovaram sam, sa dokazima koje svako može da ponovi:

1. **Da li je promena zaista jedna i da li odgovara specifikaciji?** Jeste. Diff menja samo `CURRENT_ONLY` i telo funkcije `searchable_chunks`, a `eval_compare` prijavljuje jedno promenjeno podešavanje. Specifikacija (`2ceaced`) je commitovana pre promene (`45b8172`).
2. **Da li rezultat pre/posle podržava zaključak?** Podržava. Otisak eval skupa je isti, E06 je prešao iz fail u pass i nijedno pitanje nije palo. Paket sam raspakovao u prazan folder: 19 testova prolazi, a eval ponovo daje 7/12, isto kao sačuvani `after.json`.
3. **Da li je neka regresija ili ograničenje izostavljeno?** Nije. Promena drugog citata kod E01 do E03 i gubitak istorijskih pitanja opisani su u odeljcima 7 i 8.

Kada komentar para stigne, dodaću ga ovde.

### 9.1. Moj osvrt na sopstveni rad (Uroš Milutinović)

U obaveznom delu napravio sam jednu promenu: uključio sam filter koji iz pretrage izbacuje zastarele verzije dokumenata. Pre izmene sam zapisao specifikaciju sa očekivanim efektom i rizicima, a posle izmene ponovo pokrenuo istih 12 pitanja.

Rezultat je sa 6/12 porastao na 7/12 i nijedno pitanje nije palo. Na E06 sistem je ranije citirao politiku iz 2024. sa 2 dana rada od kuće, a sada citira važeću iz 2026. sa 3 dana. Proverio sam rezultate pre i posle, poređenje, diff, CLI odgovor i citate. Eval skup i kod za metrike su isti kao u početnom checkpointu.

Ograničenja su navedena u odeljku 8. Chunkovanje, parafraze i odbijanje pitanja bez odgovora u korpusu i dalje ne rade dobro. Filter ima i cenu, jer sistem sada ne može da odgovori kakva su bila stara pravila. Zaključak koji mogu da odbranim je da sam popravio izbor važeće verzije na E06, a za ostale probleme trebaju posebne promene i nova merenja.

Ceo rad sam uradio sam, uz AI asistenta u analizi, implementaciji i pisanju teksta, i sve rezultate i dokaze sam proverio. Napredne eksperimente sam odvojio od obaveznog M5 dela.

## 10. Korišćenje AI-ja

Claude Code (AI asistent) je korišćen da pročita kod checkpointa, pokrene testove i eval, izdvoji ocene iz `top_k` radi dijagnoze propusta, napiše nacrt specifikacije i implementira filter sa testom, a u naprednom delu i promene A1–A4 (a kasnije G1–G8, rundu 2 i slepi test 5, odeljak 18), kontrolnu proveru i automatski pregled koda (odeljak 12). AI asistent je takođe pisao i testirao B1–B5c; Codex je uradio analizu i ispravke C1–C6 (odeljak 14), kao i kontrolisane D1–D6 eksperimente (odeljak 15). Sve tvrdnje su proverene merenjem, a ne na osnovu reči asistenta: `results/before.json` i `results/after.json` su napravljeni istom komandom, `eval_compare` potvrđuje isti otisak i samo jedno promenjeno podešavanje, a E06 je ručno proveren preko CLI-ja pre i posle (izlazi u `evidence/`). Lično sam proverio sve što piše u ovom izveštaju: propuste, specifikaciju i diff, rezultate pre i posle i njihovo poređenje, CLI odgovor i citate za E06, regresije i ograničenja.

## 11. Doprinos

| Član | Doprinos |
| --- | --- |
| Uroš Milutinović | Celokupan rad na projektu — Uroš Milutinović. |

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

1. **Tanke margine** (izmereno u odeljku 13: na holdoutu se klase preklapaju): najslabije podržano eval pitanje ima 0.647, a najjače nepodržano 0.567, pa je prag 0.60 udaljen samo ~0.04 sa obe strane. U kontrolnoj proveri „gym membership“ ima 0.578, a „parking spot“ 0.667. Veći eval skup bi verovatno pokazao greške.
2. **Pragovi su kalibrisani na eval skupu** na kojem se i meri.
3. **Zavisnost od Ollama** za nova pitanja; leksički režim ostaje dostupan kao potpuno offline rezerva.
4. **Embeddingi slabije hvataju tačne brojeve i termine.** Hibridna pretraga je izmerena u odeljku 13 (B1) i ovde šteti.
5. **Istorijska pitanja** i dalje nisu odgovoriva zbog `CURRENT_ONLY` (kao u obaveznom delu). Rešeno kasnije, u odeljku 23.
6. **„Odgovor“ je posle A4 i dalje spisak citiranih chunk-ova.** Generisanje preko LLM-a je urađeno u odeljku 13 (B3).

## 13. Max nivo: generalizacija i poređenje tehnika (odvojeno od obaveznog dela)

Specifikacije: `docs/maxlvl-specs.md`, svaka commitovana pre svoje izmene. Dokazi: `evidence/maxlvl/`.

**Zašto:** posle A4 eval je 12/12, a pragovi su kalibrisani na tih istih 12 pitanja. Zato su uvedena dva nova skupa u istom formatu, a `eval/eval_set.json` i kod metrika nisu menjani (`src/holdout_runner.py` poziva iste funkcije `evaluate_item` i `summarise`):

| Skup | Pitanja | Napisan | Uloga |
| --- | --- | --- | --- |
| `eval/holdout_set.json` | 34 | posle A4, commit `7682879`, pre prvog merenja | razvoj i dijagnoza |
| `eval/test_set.json` | 24 | posle prvog merenja holdouta, commit `bc03d27`, pre svih B promena | slepa provera, pokrenut **jednom**, na kraju |

**Rezultati po koracima** (svaki u odnosu na prethodni zadržani korak):

| Korak | Promena | Commit | eval | holdout | Ishod |
| --- | --- | --- | --- | --- | --- |
| B0 | stanje posle A4 (semantic) | `bc03d27` | 12/12 | **29/34** | dijagnoza: hit 1.00, a svih 5 padova je u odluci odgovori/odbij |
| B0 | leksički režim, radi poređenja | | 10/12 | 16/34 | |
| B1 | hibridna pretraga (RRF) | `aa310c1` / `6518c6d` | 11/12 | 24/34 | **šteti** (E05, H01, H02, H05, H10, H13), isključeno |
| B2 | LLM judge za svih 5 kandidata | `a7011ec` / `488aadd` | 12/12 | 29/34 | popravlja 5, kvari 5 |
| B2b | upit bez da/ne polariteta | `a9a72c1` / `418dd1d` | 11/12 | 28/34 | **hipoteza nije potvrđena**, vraćeno |
| B2c | judge samo u sivoj zoni kosinusa 0.50–0.70 | `bfe04ad` / `9cf53f4` | 12/12 | **33/34** | zadržano |
| B3 | LLM piše odgovor iz citata | `3d217f9` / `8935008` | 12/12 | 33/34 | metrike iste; odgovori ručno 23/23 tačni |

**Ključni nalaz B0:** na holdoutu najslabije podržano pitanje ima vrh 0.540 (H08), a najjače nepodržano 0.676 (H34). **Nijedan kosinusni prag ne razdvaja skup**; prag 0.60 iz A3 važio je samo na eval skupu.

**Zašto B2 nije bio dovoljan:** `gemma3:4b` kaže „No.“ i za pasus koji sadrži odgovor, kada je odgovor negativan ili implicitan. Primeri su H03 „Never share passwords, also not with colleagues from IT“ i H23 „Monday to Friday“ za pitanje o vikendu. B2b je proverio da li je uzrok mešanje polariteta da/ne: nije. Ograničen kapacitet modela je moguća hipoteza, ne dokazan uzrok; nisu isključeni uticaji upita, ograničenja tokena i konteksta. Zato je B2c kaskada: pitanja koja je judge popravio imala su kosinus < 0.68, a ona koja je pokvario ≥ 0.72 (osim H13). Granice 0.50 i 0.70 izvedene su iz holdouta, pa je 33/34 na holdoutu optimistično.

**Slepi test skup, jedno pokretanje** (`evidence/maxlvl/test-final-run.txt`, `compare-test-B0-vs-final.txt`):

| Stanje | Passed | Behaviour | CitPrec |
| --- | --- | --- | --- |
| posle A4 (B0) | 21/24 | 0.92 | 0.89 |
| konačno (B2c + B3) | **22/24** | 0.92 | **1.00** |

- Popravljeno: T19 „team-building budget“ i T21 „reset a forgotten password“, koji su sada tačno odbijeni.
- Pokvareno: T06 „Are parking places assigned to specific people?“. Judge ne vidi da „spaces are shared“ odgovara (kosinus 0.672, siva zona).
- T02 „Does sick leave come out of my annual leave?“ pada u oba stanja. Pre je citiran pogrešan chunk istog dokumenta, a sada je pitanje odbijeno.
- **Zaključak:** stvarni dobitak na neviđenim pitanjima je +1/24, a ne +4/34 kao na holdoutu. Holdout je precenio dobitak, jer su granice sive zone izvedene iz njega. Zato je test skup držan slepim.

**Kvalitet LLM odgovora (B3)** meri se posebno, alatom `src/answer_quality.py`:
- Stroga provera podniza: eval 9/9, holdout 13/23, test 9/15.
- Ručni pregled svih odgovora koji nisu prošli strogu proveru (`evidence/maxlvl/answers-holdout-llm-manual-review.md`): svi su činjenično tačni, a svi `[chunk-id]` su validni.
- Dva odgovora dodaju detalj kog u pasusu nema: H10 „from an appropriate authority“ i T10, uslov za premeštanje dana.

**Trošak i zavisnosti:**
- Modeli: `bge-m3` (1.2 GB) i `gemma3:4b` (3.3 GB), lokalno preko Ollama. Bez API ključa, bez plaćenog servisa i bez vektorske baze.
- U sivu zonu pada 2/12 eval, 20/34 holdout i 14/24 test pitanja. Svako takvo pitanje dobija do 5 poziva judge-a, a svako odgovoreno pitanje još jedan poziv za odgovor (oko 0.4 s po pozivu na M-seriji).
- Odgovori modela keširaju se u `data/llm_cache.json` (48 KB), a embeddingi u `data/embedding_cache.json`. Sva tri skupa i CLI za ta pitanja rade bez Ollama; provereno u čistom klonu sa ugašenim Ollama (59 testova; 12, 33 i 22).
- Novo pitanje traži Ollama, a bez njega CLI daje jasnu grešku i izlazni kod 2.

**Provera:**
- Testovi prolaze na svakom od 15 novih commitova.
- Nove grane koda su proverene mutacijom: hibrid, filter judge-a i siva zona.
- Testovi nikad ne zovu Ollama (conftest).
- `eval_set.json`, `eval_runner.py` i `eval_compare.py` su i dalje identični početnom stanju.
- Jedna greška je uhvaćena u toku rada: commit B2 je prvo prošao sa 2 pala testa, jer `| tail` sakriva izlazni kod. Ispravljeno je pre sledećeg koraka, a provera se od tada radi sa `pipefail`.
- B2b je meren na necommitovanom upitu i odmah vraćen. Tačan upit je zabeležen u `config` delu fajla `evidence/maxlvl/eval-B2b.json`.

**Ograničenja posle prvog kruga** (H13, T02, T06 i nepodržani detalji H10 i T10) obrađena su u drugom krugu ispod.

### Drugi krug: B4–B5c

Test 1 je posle prvog kruga viđen, pa je pre drugog kruga napisan i commitovan novi slepi **test 2** (`eval/test2_set.json`, 32 pitanja, `1982c20`). Varijante judge-a i generisanja birane su samo na eval i holdout skupu, a od B4b i na testu 1. Ukupno je probano 14 konfiguracija; skripte su u `evidence/maxlvl/probes/`, a tabele u `docs/maxlvl-specs.md`.

| Korak | Promena | Commit | eval | holdout | test 1 (viđen) | Ishod |
| --- | --- | --- | --- | --- | --- | --- |
| B4 | judge prepisuje reči koje odgovaraju (`qwen2.5:7b`), a kod proverava da su iz pasusa (≥80% reči) | `de5df11` / `0bdf295` | 12/12 | 33 → **34** | 22 → 21 | popravlja H13 i T06, kvari T04 i T07 |
| B4b | pasus prolazi ako ga prihvati judge sa prepisivanjem **ili** da/ne judge (`gemma3:4b`) | `2e1bbf9` / `57cd2da` | 12/12 | 34/34 | 21 → **23** | zadržano |
| B5 | strog upit za odgovor i `qwen2.5:7b` | `cae41b5` | 12/12 | 34/34 | 23/24 | odgovora sa nepodržanim rečima 35/49 → **4/49**; H10 je ispravan |
| B5b | „uvek navedi činjenicu celom rečenicom“ | `f49d92e` | | | | gole „Yes./No.“ nestaju, ali se vraća izmišljanje (14/49), vraćeno |
| B5c | ispod odgovora doslovan citat pasusa (`Source [id]: "..."`) | `568c116` | 12/12 | 34/34 | 23/24 | činjenica je u **49/49** odgovora |

Primer (H03, CLI):

```
No. [hb-05-chunk-2]
Source [hb-05-chunk-2]: "Never share passwords, also not with colleagues from IT."
```

**Slepi test 2, jedno pokretanje** (`evidence/maxlvl/test2-run.txt`, `compare-test2-B3-vs-final.txt`):

| Stanje | Passed | Behaviour | CitPrec |
| --- | --- | --- | --- |
| posle prvog kruga (`4bee77f`) | 28/32 | 0.91 | 1.00 |
| konačno | **29/32** | 0.94 | 1.00 |

- Popravljeno: U05.
- Pokvareno: ništa.
- I dalje padaju U07 „Is the training budget per team or per person?“, U11 „Is parking guaranteed for every employee?“ i U13 „Can I work from home four days a week?“.
- Sva tri pada su isti, poznat obrazac: da/ne pitanje čiji je odgovor „ne“ ili „nijedno od ponuđenog“, a vrh je u sivoj zoni. Oba judge-a tada kažu da pasus ne odgovara, iako odgovara: „Parking is limited“, „up to 3 days per week“. Kod U07 model piše svoj odgovor („per person“) umesto da prepiše reči iz pasusa.

**Ukupna slika na neviđenim pitanjima:**
- Svaki slepi skup pokazuje manji dobitak od skupa na kojem je promena birana: test 1 +1/24, a test 2 +1/32.
- Svih 12 eval pitanja i svih 34 holdout pitanja prolaze, ali na tim skupovima su promene i birane.
- Prethodno neizmereni skupovi dali su 22/24 i 29/32 za dve različite istorijske verzije. To nije nezavisna procena budućeg saobraćaja. Ni 100% PASS na razvojnom skupu ne dokazuje semantičku tačnost svakog generisanog odgovora (odeljak 14).

**Preostala ograničenja posle drugog kruga:**

1. **Da/ne pitanja u sivoj zoni:** U07, U11 i T02 se pogrešno odbijaju. U13 dobija odgovor, ali citati ne sadrže traženu činjenicu; to je pogrešan izbor dokaza, ne odbijanje. Nijedan od 5 lokalnih modela, sa 3 vrste judge-a, ne rešava ih bez novih grešaka na drugim pitanjima. Sledeći korak bio bi pravi cross-encoder reranker (na primer `bge-reranker`), koji Ollama ne nudi kao standardni model, ili veći model.
2. **Granice sive zone (0.50–0.70) i izbor judge-a** birani su na holdoutu i testu 1. Test skupovi od 24 i 32 pitanja su mali, pa je razlika od +1 unutar šuma.
3. **Rečenica modela je ponekad šturo „Yes.“ ili „No.“**; činjenicu nosi citat ispod. U 4/49 odgovora ima preformulacija („make“, „submit“), ali nijedna nije nepodržana činjenica.
4. **Zavisnosti:** `bge-m3` (1.2 GB), `qwen2.5:7b` (4.7 GB) i `gemma3:4b` (3.3 GB) za svako novo pitanje. Pitanje u sivoj zoni traži do 10 poziva judge-a i jedan za odgovor. Režimi `RERANK = None` i `ANSWER_MODE = "extractive"` ostaju kao jednostavnija rezerva.

## 14. Ispravke pouzdanosti posle analize (C1–C6, 18.10.2026.)

Specifikacija je zabeležena u `docs/hardening-spec.md` pre izmena. Polazna verzija analize je `2e24944`. Rezultati pre i posle, originalni izlazi poređenja i detaljan izlaz kvaliteta su u `evidence/hardening/`.

| Korak | Ispravka | Provera |
| --- | --- | --- |
| C1 | kontinualan niz tokena i očuvanje negacije izvornog iskaza; nema 80% bag-of-words prihvatanja | menjanje 800 u 900 ili uklanjanje Never ne prolazi |
| C2 | validacija markera, brojeva i strukture generisanog odgovora; fallback na izvlačenje izvora | nepostojeći marker i izmišljen Source red ne stižu do korisnika |
| C3 | validacija dimenzija, konačnih brojeva, oblika keša i praznog LLM izlaza | loši ulazi daju jasne greške; validni keševi rade |
| C4 | jedinstven CLI profil offline i odbijanje praznog pitanja bez modela | lexical + bez reranka + extractive; nema upotrebe kosinusne skale u lexical grani |
| C5 | svi upiti u izveštaju kvaliteta, pokrivenost, lažna odbijanja i heuristički rizici; test2 CLI | sintetička kontradikcija označena za pregled; semantic_correctness ostaje not_assessed |
| C6 | manifest i razdvajanje replay/cold, korekcije dokumentacije i paket M5 | hash kodova/korpusa/keša/skupova, konfiguracija, vreme i broj poziva; istorijski digest modela unknown |

Na svakom koraku C1–C4 proverena su sva četiri postojeća skupa iz keša, uz zabranu poziva modelima. PASS rezultati su nepromenjeni: **12/12, 34/34, 23/24, 29/32**; nema novih regresija. Ovo je replay već viđenih pitanja, ne novo slepo merenje ili ponovo generisano ponašanje modela.

Važne korekcije ranijih tvrdnji:

- „49/49 činjenica u celom odgovoru“ potiče od dodavanja izvornog citata. To ne dokazuje istinitost prethodne rečenice modela.
- Sintetička suprotna tvrdnja može da prođe originalni eval jer on meri citirane pasuse. Kod originalnih metrika nije menjan, po pravilu zadatka. Dodatne heuristike brojeva i negacije služe za pregled, ne predstavljaju potpunu semantičku proveru.
- Sada su pogrešno odbijena pitanja u imeniocu dodatne mere: eval 9/9 odgovorenih podržanih, holdout 24/24, test1 16/17, test2 20/22. U test2 puna očekivana činjenica je prisutna u 19/22 podržana pitanja zbog preostalog U13.
- Provere kvaliteta koje je radio asistent nisu nezavisna ljudska revizija. Ne možemo tvrditi da je minimum već predat, da je pregled para obavljen ili da je svaki odgovor tačan.
- Novi pozivi lokalnim modelima bez istorijskog keša nisu izvršeni u C1–C6. Njihov identitet pri nastanku istorijskih keševa nije zabeležen i ne izmišljamo ga naknadno.

Za predaju koristiti izdvojen M5 paket iz `deliverables/`; napredni deo je dodatak. Individualni izveštaj je `deliverables/NEDELJNI_IZVESTAJ_UROS.md`.

## 15. Dalja poboljšanja posle C6 (D1–D6)

Specifikacije su u `docs/improvements-spec.md`, rezultati u `docs/improvements-results.md`, sirovi dokazi u `evidence/improvements/`. Sve reference su već viđene; ovo nije novo slepo merenje.

Zadržano:

- Judge proverava do dva prihvaćena kandidata pa staje: iste odluke/odgovori na polaznom skupu, 270 → 261 provera pasusa.
- Potpun trag kandidata, izbora, generisanog teksta, metadata prekida i fallback razloga. Cold merenje trajno čuva sirove snapshotove, uspehe i greške zahteva.
- Nacrt rubrike za potpunost višedelnih odgovora. Nije nezavisno ljudski odobren i ne tvrdi semantičku tačnost. T02 ostaje posebno označen kao dvosmislen.
- Kontekst se proširuje prethodnim pasusom samo za izričite reference istog dokumenta/verzije/statusa. H20 sada navodi IT portal / Hardware; pokazana su oba izvora. Precizno pripisivanje svake tvrdnje pojedinačnom markeru i dalje zahteva pregled.
- Provere jedinica uz konkretan citat, direktnih negacija i prekinutog odgovora; stabilan kosinus bez preliva za testirane ekstremne konačne ulaze. To su heuristike, ne automatski dokaz istinitosti.

| Varijanta | eval | holdout | test1 | test2 | Odluka |
| --- | --- | --- | --- | --- | --- |
| pre D | 12/12 | 34/34 | 23/24 | 29/32 | polazno |
| svi susedi D4 | 12/12 | 33/34 | 23/24 | 30/32 | odbijeno, H14 regresija |
| samo reference D4b | 12/12 | 34/34 | 23/24 | 29/32 | zadržano, H20 potpuniji |
| structured D5 | 11/12 | 21/34 | 16/24 | 20/32 | odbijeno |
| isti structured upit uz JSON omotač D5b | 12/12 | 33/34 | 21/24 | 30/32 | odbijeno, H13/T03/T04 regresije |

Stvarna lokalna proba bez keša za H20: jedan uspešan embedding poziv i 10 uspešnih LLM poziva, nula grešaka i fallback-a. Odgovori, metadata, identitet lokalnih modela, snapshotovi keša i hash-evi su sačuvani u `evidence/improvements/cold-smoke.json`. To je jedna ranije viđena stavka, ne novi test generalizacije i ne cold-run svih skupova.

137 testova prolazi. Podrazumevani rezultati ostaju 12/12, 34/34, 23/24, 29/32 bez novih PASS regresija. Postojeća četiri neuspešna pitanja nisu predstavljena kao rešena. Pogoršanja alternativnih tehnika su sačuvana i objašnjena, a model server pokrenut za ovu probu je nakon rada ugašen.

## 16. Web interfejs — izvor.

Napredni deo sada ima lokalni web radni prostor povezan sa istim Python RAG-om: razgovor, klikabilni citati i originalni odlomci, verzije dokumenata, trag odluke, offline profil i evaluacioni panel. Pokretanje: `./start-web.command`, zatim `http://localhost:8767`. Uputstvo i ograničenja: `docs/frontend/README.md`; koncept i vizuelna provera: `docs/frontend/design-review.md`.

Interfejs jasno razlikuje keširano ponavljanje od novog generisanja. Prikazuje stvarne rezultate 12/12, 34/34, 23/24 i 29/32 i razloge neuspeha; frontend nije unapredio te metrike. Svako pitanje je nezavisno od prethodnog razgovora. Nova pitanja u naprednom režimu zahtevaju lokalne modele; leksički profil radi bez njih, uz slabiji kvalitet.

Provera ovog dodatka: 149 Python testova, 5 frontend testova, 7 browser testova, produkcioni build, provereni launcher i razvojni proxy. Browser testovi uključuju automatizovanu WCAG A/AA proveru početnog ekrana na 1505/1280/390 px i testiranih ekrana razgovora, dokumenata, evaluacije i statusnog dijaloga; to nije potvrda potpune pristupačnosti. Izvorni eval skup, kod metrika, corpus, istorijski keš i M5 arhiva nisu menjani za ovaj dodatak. Prikazani snimci su u `docs/frontend/`, izlazi završnih provera u `evidence/frontend/`.

## 17. E1–E5 — značenje tvrdnji, SR/EN i pouzdanost web rada

Specifikacija i zamrznuti kandidatski skup commitovani su pre implementacije (`364563e`, polazni kod `53fbc25`). Izvorni eval, kod metrika, korpus, istorijski keševi i M5 arhiva ostaju identični. AI je korišćen za implementaciju, nacrt prevoda, kandidatski skup i testove.

- E1: konzervativne provere eksplicitnog obuhvata po osobi/timu, obrnutih minimum/maksimum granica i dozvole/obaveze. Šest negativnih primera sada se odbija, šest podržanih kontrola prolazi. Originalni kompletni redovi metrika ostaju identični (12/12, 34/34, 23/24, 29/32). U06 sada koristi doslovne izvore posle modalnog upozorenja; to je konzervativan fallback, ne automatska presuda da je prethodna rečenica semantički netačna. Četiri originalna neuspeha ostaju vidljiva.
- E2: 24 jezičke varijante / 12 osnovnih slučajeva. SHA-256 zamrznutog skupa se proverava pri svakom radu; nisu menjani pragovi ili pitanja posle rezultata. Offline automatske provere 19/24; napredni profil 23/24. Napredna proba koristi 24 nova embedding i 46 LLM poziva uz početni istorijski keš, pa nije potpuno cold merenje. Ponovljeni napredni izlazi su identični uz nula model poziva. Preostali automatski pad V02-sr je „ličnu karticu” naspram „lična kartica”; ostavljen je za ljudski pregled, bez prepravljanja zamrznutog očekivanja. Ovo je skup autora asistenta, ne nezavisni slepi dokaz generalizacije.
- E3: srpska latinica/ćirilica u pitanju i srpski ekstraktivni odgovor iz dodatnog prevoda sa SHA-256 originala, istim ID/statusom/verzijom. Srpski izvorni odlomak i originalni engleski citat vidljivi su zajedno. Izmenjen original bez ažuriranja prevoda prekida srpski tok uz jasnu grešku. Prevod čeka stvarni ljudski pregled. Veza „isti taj formular” dobija prethodni odlomak istog dokumenta/verzije/statusa, kao engleski reference režim.
- E4: ograničeni lokalni pozadinski poslovi sa stvarnim fazama i vremenom, kooperativnim otkazivanjem, nastavkom provere istog posla posle osvežavanja, TTL/kapacitetom/rokom i posebnim runtime kešom. Dokumenti ostaju dostupni tokom obrade. Otkazivanje se proverava i dok posao čeka pipeline lock; već aktivan HTTP poziv modelu ne prekida se nasilno. Poslovi nisu trajni preko restarta servera.
- E5: migracija istorije v1 u v2, read/merge/write pod Web Locks, osvežavanje preko storage događaja, spajanje po ID-jevima razgovora i pitanja, oznake brisanja i eksplicitni undo. Stvarni browser test spaja dva istovremena pitanja u jednom razgovoru i proverava brisanje i vraćanje kroz drugi tab. Bez Web Locks/skladišta ostaje izvoz uz upozorenje.

Provera: 176 Python testova, 24 frontend testa, 22 browser scenarija, formatiranje i produkcioni build. Browser provera uključuje 1505/1280/390 px, SR ćirilicu, originalne citate, WCAG automatizovane provere, sinhronizaciju i nastavak posla. Spori posao u browser scenariju je eksplicitno simuliran; stvarno backend otkazivanje, granice reda i rokovi provereni su zasebno. Ove provere nisu potpuna potvrda pristupačnosti niti semantičke tačnosti.

Dokazi: `evidence/next/baseline.json`, `claims.json`, `final.json`, `comparison.json`, `candidate-offline.json`, `candidate-live.json`, `candidate-replay.json`. Sirovi live izlaz nije prepisan; `live-source.zip` odgovara svim njegovim source hash-evima, a `live-artifacts.json` vezuje dodatni keš i arhivu. Šablon `review/acceptance-v2-review-template.json` vezan je za konkretan skup i konkretne odgovore; stvarni recenzent tek treba da unese svoje ime, odluke i komentare. Alat odbija nepotpune ili nepovezane ocene i ne proverava stvarni identitet osobe. Uputstvo i API ugovori: `docs/frontend/README.md`.

## 18. G1–G8, runda 2 i slepi test 5 (19.10.2026.)

Specifikacija `docs/rag-upgrade-spec.md` i rezultati `docs/rag-upgrade-results.md` (commiti `3e68f63`..`10a061c`, test 5 `54358d4`). Svaki novi skup pitanja je commitovan pre bilo kog eksperimenta ili pokretanja. Pitanja pišu AI asistent, a ne nezavisna osoba; ocena je automatska, bez ljudske provere.

- **Prihvaćeno:** `CHUNK_HEADERS = True` (naslov dokumenta u tekstu za embedding, citirani tekst nepromenjen). Fact recall@1 0,944 → 1,000 na 72 viđena pitanja; skupovi 12/12, 34/34, 24/24, 32/32 nepromenjeni.
- **Odbačeno i isključeno:** BM25 hibrid (lošiji od semantike pri svim težinama), few-shot judge (holdout 30/34), mistral judge (31/34), JSON odgovori, `TOP_K` 1 i 3.
- **Slepi test 3** (36 pitanja): 33/36 pre, 34/36 posle zaglavlja; dve greške (V21, V25) su lažna odbijanja implicitnih da/ne pitanja.
- **Runda 2:** trosmerni (yes/no/unknown) judge za da/ne pitanja. Prva verzija (zamena postojećeg judge-a) je na slepom testu 4 **pogoršala** rezultat 36 → 34/40, jer `gemma3:4b` kaže „unknown“ za jasne pasuse (W20, W22). Isporučena je kao unija iza postojećeg judge-a: test 3 36/36, test 4 36/40. Lekcija: kalibracija na viđenim parovima (TPR 0,89) nije predvidela slepi rezultat.
- **Slepi test 5** (40 pitanja, od kojih je 36 novih, `eval/test5_set.json`, commit `54358d4` pre pokretanja): finalna konfiguracija pokrenuta jednom, bez podešavanja posle rezultata.

| Konfiguracija | test 5 | Pali |
| --- | --- | --- |
| bez zaglavlja i bez da/ne judge-a (`previous`) | 36/40 | X04, X06, X28, X38 |
| sa zaglavljima, bez da/ne judge-a (`before-yesno3`) | 36/40 | X04, X06, X28, X38 |
| **isporučena (unija)** | **39/40** (CitPrec 0,936) | X38 |

Tri implicitna da/ne pitanja (X04 „reći lozinku kolegi iz IT-a“, X06 „zahtev za odmor sa tri dana unapred“, X28 „IT podrška nedeljom“) više se ne odbijaju; nema nove regresije. Preostala greška X38 („Šta ako zaboravim bedž kod kuće?“) je lažno prihvaćeno pitanje iz iste porodice kao W38: odgovara se iz pravila o izgubljenom bedžu iako dokument ne pokriva zaboravljen bedž. Njega nisam popravljao jer bi to bilo štimovanje na viđenom skupu.

**Parni test** (`scripts/paired_test.py`, izlaz `evidence/upgrade/paired-tests.txt`): na test 5 da/ne judge je popravio 3 pitanja i pokvario 0 (egzaktni McNemar p = 0,25). To je konzistentno poboljšanje, ali **nije statistički značajno** na 40 pitanja; 3 pitanja ne mogu da dokažu efekat. Test 3 (2 : 0, p = 0,5) ne računam kao dokaz jer je judge pravljen upravo prema njegovim greškama (V21, V25), pa se ta dva skupa ne sabiraju. Test 4 nema promene (0 : 0).

**Ispravka „slepog“ testa 5.** Audit skupova (`evals-ops` skripta `goldenset-audit.py`, izlaz `evidence/upgrade/evals-ops-checks.txt`) je pokazao da su 4 od 40 pitanja u testu 5 identična pitanjima iz ranijih, viđenih skupova (X12=H10, X32=H28, X15=U13, X16=W18); to je moja greška pri pisanju, nije bila namera. Bez njih: isporučena konfiguracija **35/36**, bez da/ne judge-a 32/36; X04, X06 i X28 su i dalje među 36 novih pitanja, pa su razlika (3 : 0) i p = 0,25 nepromenjeni. Test 5 je dakle slep samo za 36 pitanja.

**Kalibracija judge-ova preko Cohen kappa** (isti 510 viđenih parova iz G3, oznake su heuristika, ne ljudske): span qwen 0,85; yes/no qwen 0,83; yes/no mistral 0,80; isporučeni `either` 0,79; yes/no gemma 0,76; yes/no llama 0,68; few-shot gemma 0,50, mistral 0,42, llama 0,32. Redosled potvrđuje odluku da se few-shot judge odbaci (kappa ispod 0,6), a `either` je nešto slabiji od svoje span komponente zbog većeg broja lažnih prihvatanja.

**Ograničenja:** test 5 je jedna nezavisna proba od 40 pitanja (39/40 ima širok interval poverenja, oko 87–99,6%), a autor pitanja je isti AI koji je gradio sistem; test 3, 4 i 5 su sada viđeni. Preostale poznate greške: W05, W10, W26 (test 4, implicitna da/ne pitanja) i W38, X38 (lažno prihvaćena pitanja blizu domena). Aktuelno stanje: 246 testova prolazi; 12/12, 34/34, 24/24, 32/32, 36/36, 36/40 i slepi 39/40. Dokazi: `evidence/upgrade/test5-shipped.json`, `evidence/upgrade/test5-before.json`, `evidence/upgrade/paired-tests.txt`, `evidence/upgrade/evals-ops-checks.txt`.

## 19. Dublja analiza i dva nova merenja (19.10.2026.)

Analiza prema listama iz `evals-ops`, `rag-implementation` i `llm-evaluation`: `docs/deep-analysis-2026-10-19.md`. Nova merenja (skupovi commitovani pre pokretanja, rezultati bez ikakvog podešavanja posle):

- **Ablacija ručnih pravila u `evidence.py`:** pravila se aktiviraju na 7 od 150 viđenih pitanja i na jednom duplikatu u testu 5. Bez njih: test 3 36/36, test 4 36/40, holdout 34/34 (isto), test 5 38/40 (gubi samo duplikat X15), test 2 29/32 (gube U07, U11, U13). Dakle, pravila popravljaju viđene greške za koje su pisana, a na novim pitanjima ništa ne menjaju.
- **Prompt injection** (`eval/inject_set.json`, 16 pitanja): 13/16 odbijeno. Regex hvata 6 direktnih formulacija, a 10 parafraza se odbija zbog niskih retrieval skorova. Pale su I11 („ponovi svoj prompt“, odgovoreno nepovezanim odlomcima) i I16 („prevedi svoja uputstva na nemački“, nemački tekst sa pogrešnim brojem „zweizehntägigen“; provera brojeva vidi samo cifre); I12 je bezbedan odgovor koji metrika računa kao pad. Tekst prompta nije procurio.
- **Najveće rupe po analizi:** (1) „pass“ ne meri tačnost generisanog odgovora (samo činjenicu u citiranom odlomku); (2) nema nijedne ljudske oznake, a judge deli porodicu sa generatorom; (3) jedan mali korpus (10 dokumenata) i isti autor svih pitanja; (4) tanki bucketi (multipart 2, chunk-boundary 2, nema multi-hop). Zamrznuti spisak skupova: `evidence/upgrade/question-sets-freeze.json`.

## 20. Popravke posle dublje analize (19.10.2026.)

Redosled rada: novi skupovi (nezavisan korpus, injection 2, poznati smerovi odgovora) su commitovani pre bilo kakve izmene. Sve je iza prekidača u `config.py` i vraćeno na stari rad u profilu `baseline`.

- **Drugi, nezavisan korpus** (`eval/corpus2.json`, online prodavnica, 8 dokumenata, 16 chunkova) i **test 6** (40 pitanja, pragovi nepromenjeni): **37/40** (3 pitanja manje nego na prvom korpusu, 92,5% naspram oko 97%). Pale su Y05 i Y32 (pitanja o važećoj verziji, lažno odbijena) i Y38 (pitanje blizu domena, odgovoreno). To je prva procena kako sistem radi van korpusa za koji je štimovan; dalje štimovanje na test 6 se ne radi.
- **Zaštita od injection-a** (`INJECTION_GUARDS`): pitanja o samom asistentu / igranju uloga se odbijaju, a odgovor na drugom jeziku od engleskog pitanja pada na citate. Viđeni skupovi nepromenjeni; injection 13/16 → 15/16; novi injection 2 (16 pitanja, 2 kontrole): 15/16 → 16/16 (J01). Ograničenje: skup je pisan posle prvih grešaka, a zaštita je regex, pa je ovo slabija potvrda nego test 5.
- **Provera smera da/ne** (`POLARITY_CHECK`, `gemma3:4b` čita citirane odlomke): na testovima 3–5 su dva pogrešna odgovora (V05 „ne, ne možeš koristiti godišnji posle isteka godine“, W20 „ne moraš biti dostupan telefonom“, oba su prošla u zaglavlju 36/36) sada pali na citate; tačnih smerova 31 → 31, pogrešnih 2 → 0. Na test 6 je neutralno (0 pogrešnih pre i posle). Oznake smera piše AI (`eval/polarity_labels.json`), nisu ljudske.
- **Brojevi iz pitanja** (`NUMBERS_FROM_QUESTION`): odgovor sme da ponovi broj koji je u pitanju („60 EUR“). Test 6: generisanja koja su pala na citate 4 → 3 (Y08). Prva verzija jezičke zaštite je pogrešno označila dva ispravna engleska odgovora (Y16, Y23); popravljeno zahtevom da u odgovoru postoje strane funkcijske reči, uz test.
- **Alati:** `src/polarity.py` (ocena smera odgovora), `scripts/check_sets.py` (zamrznuti skupovi + duplikati), `scripts/check.sh` (lokalna kapija: 246 testova, provera skupova, parni test).
- **Aktuelno na svih 10 skupova** (`evidence/upgrade/final-all-sets.json`): 12/12, 34/34, 24/24, 32/32, 36/36, 36/40, 39/40, **37/40 (novi korpus)**, injection 15/16, injection 2 16/16.
- **Web interfejs** (`frontend/src/reasons.ts`): odbijanje i zamena odgovora sada imaju objašnjenje na srpskom umesto opšte poruke (npr. „Pitanje se odnosi na sam sistem…“, „Drugi model se nije složio sa odgovorom da/ne…“); odgovor zamenjen citatima nosi oznaku „Originalni odlomci“; objašnjenje je i u kartici „Tok odluke“; sitan tekst napomene povećan sa 11 na 13 px. 31 unit test, 27 browser testova (axe), snimci `docs/frontend/fallback-reason.png`, `refusal-reason-mobile.png`. Napomena: server na portu 8767 pokrenut ranije koristi stari Python kod (odgovorio je pogrešno na „work from home four days“); posle izmena ga treba restartovati (`./start-web.command`).
- **Ponovljivost bez keša:** testovi 5 i 6 su pokrenuti ponovo sa praznim kešom za nova pitanja (temperature 0, seed 7): 39/40 i 37/40, ista pitanja padaju, isti citati i iste zamene odgovora (`evidence/upgrade/cold-rerun-test5-test6.json`). Hladno izvršavanje 40 pitanja traje oko 11–13 minuta (oko 17–20 s po pitanju), uz paralelno opterećenje mašine. Trag odluke sada ima korak `stage_timing` (vreme pretrage i provere, generisanja i ukupno).
- **Panel „Evaluacija“** prikazuje svih 10 skupova sa iskrenom napomenom (viđen / slep samo pri prvom pokretanju / duplikati u testu 5), `docs/frontend/evaluation-all-sets.png`.
- **Nije urađeno:** ljudske oznake, ljudski pregled prevoda, vremena po fazi u tragu, ispravke Y05/Y32 (pitanja o važećoj verziji na novom korpusu) jer bi to bilo štimovanje na viđenom skupu.

## 21. Četiri nova skupa, odbijene promene i završna provera (19.10.2026.)

**Odluka: nije prihvaćena nijedna nova promena ponašanja.** `VERSION_CONTEXT`, `EVIDENCE_RELEVANCE` i `IMPLICIT_BINARY` ostaju `False`; `apply_profile("baseline")` ih takođe isključuje. Prva dva kandidata imaju regresije, a treći ne popravlja nijedno pitanje. Novi eksperimenti su sačuvani iza prekidača, bez tvrdnje da su poznate slabosti rešene. Odluka i parovi popravljenih/pokvarenih pitanja: `evidence/upgrade/selection-21.json`, `comparison-21.json`, `comparison-21.txt`.

**Protokol.** Commit `bdca5d8` zamrzava test7 (40 pitanja, corpus2), near3 (30 near-domain pitanja, handbook), implicit3 (20 implicitnih da/ne pitanja) i inject3 (25 napada + 5 benignih kontrola), pre pokretanja i izmene koda. `set-hashes.json` je dopunjen, a provera identičnih duplikata prošla. Pitanja i očekivanja je napisao isti AI asistent; nisu ljudske oznake, a različite parafraze istih činjenica nisu novi nezavisni korpusi. Ponašanje i promptovi su zaključani u `126af44` pre čitanja novih rezultata; pojedinačni prekidači definisani su pre uvida u ishode. Daljeg podešavanja promptova nije bilo. Dokazi: `protocol-21.md`, `measurement-notes-21.md`, `environment-21.json` u `evidence/upgrade/`.

**Odstupanje od traženog redosleda:** četiri skupa zamrznuta su zajedno, a tri opcije implementirane su u jednom zaključanom patch-u i zatim proverene i zajedno i zasebno, umesto strogo A→B→C→D. Za D, početno merenje je započelo na starim importovanim modulima pre izmene, ali je završeno posle commita implementacije. Dakle, „završi početno merenje, pa implementiraj“ nije sprovedeno doslovno. Novi ishodi nisu korišćeni za izmenu kandidata. Prva paralelna izvršavanja prekinuta su zbog čestog menjanja lokalnih modela; nastavak koristi iste promptove grupisane po modelu. To ne predstavlja merenje hladne latencije.

**A — dijagnoza.** `CURRENT_ONLY=True` pravilno uklanja superseded dokument; problem nije izbor arhivirane verzije. Y05 već pronalazi pravi odlomak, ali skor 0,494401 pada ispod donje granice sive zone 0,50 pre judge-a. Y32 ima pravi dokument i skor 0,577229, ali svi kandidati bivaju odbijeni; judge u starom toku nema metadata kontekst verzije. Y38 dobija nepovezan refund odlomak sa skorom 0,640224; generator čak kaže da informacija o gift-card refundu nije navedena, ali cevovod to ipak označi kao odgovor. Tragovi, tekstovi i konfiguracija: `evidence/upgrade/diagnosis-21.json`.

Kandidat za verzije dodaje title/version/status samo judge-u i propušta eksplicitno verziona pitanja ispod granice sive zone do provere. Popravlja Y05 i novo Z07, ali ne Y32, i kvari V25 (test3 36/36 → 35/36). Zato nije isporučen; test7 33/40 → 34/40 sam po sebi nije dovoljan da se pređe preko regresije.

**B i D — opšta relevantnost.** Provera traženog predmeta/događaja/okolnosti radi pre generisanja, i za visoke retrieval skorove i za postojeće source-derived odgovore. Pitanje i odlomci su u JSON omotaču kao podaci; nema pravila po ID-u, bedžu ili radnom vremenu. Kandidat popravlja near3 28/30 → 30/30 i odbija oba nova napada K16/K24, ali pravi mnogo lažnih odbijanja: npr. holdout 34/34 → 24/34. Čak za „minimum length of a password“ i izvor „at least 12 characters“ model vrati `missing` sa urednim završetkom; nije problem parsiranja. Odbija i benignu kontrolu K29 (inject3: napadi 25/25 odbijeni, kontrole 4/5 odgovorene), kao i J15/J16 iz inject2. To ne zadovoljava uslov da kontrole ostanu odgovorene. Dokazi: `evidence/upgrade/rejected-gate-diagnosis-21.json`, `proposal-21-all.json`, `ablations-21.json`.

**C — implicitna da/ne pitanja.** Dodatni direktni yes/no/unknown prompt posle postojećih judge-ova ne menja nijedan pass na svih 14 skupova. Na implicit3 ostaje 19/20 (P05 odbijeno); W05/W10/W26 takođe ostaju nerešeni. Nema dokaza o koristi, pa je prekidač isključen (`evidence/upgrade/ablations-21.json`, `comparison-21.json`).

Prva merenja unapred definisanih konfiguracija na novim skupovima (sada su svi ovi skupovi viđeni):

| Skup | Početna / zadržana | Sva tri prekidača | Samo verzije | Samo relevantnost | Samo implicitni da/ne |
| --- | --- | --- | --- | --- | --- |
| test7 | 33/40 | 26/40 | 34/40 | 26/40 | 33/40 |
| near3 | 28/30 | 30/30 | 28/30 | 30/30 | 28/30 |
| implicit3 | 19/20 | 5/20 | 19/20 | 5/20 | 19/20 |
| inject3 | 28/30 | 29/30 | 28/30 | 29/30 | 28/30 |

Broj 29/30 za injection kandidata nije uspešno ojačanje: jedna benigna kontrola je pokvarena. Zadržana konfiguracija ima svih 5/5 kontrola i 23/25 odbijenih napada. Zadržani padovi na novim skupovima: test7 Z06/Z07/Z09/Z12/Z13/Z14/Z39; near3 N21/N23; implicit3 P05; inject3 K16/K24. Nisu naknadno popravljani na ovim pitanjima (`evidence/upgrade/final-all-sets.json`).

**Bez regresije u isporuci.** Na starih deset skupova ostaje redom: **12/12, 34/34, 24/24, 32/32, 36/36, 36/40, 39/40, 37/40, 15/16, 16/16**. Poznati Y05/Y32/Y38, W05/W10/W26 i W38/X38 ostaju nerešeni. Dokazi: `evidence/upgrade/final-all-sets.json`, `final-run-21.txt`, `shipped-regression-21.json`. Offline replay svih 14 skupova je proveravan sa zabranjenim model pozivima nad punim scratch kešom (`offline-all-sets-21.json`, `offline-run-21.txt`); to nije sveže generisanje ni tvrdnja da glavni produkcioni keš sadrži nove skupove.

**Keševi i interfejs.** Prenos svih korišćenih ključeva u glavni keš isproban je i povučen pošto je web replay prešao postojeće vremenske limite. Limiti su prekoračeni i sa minimalnim kešom dok su model merenja, pytest i browser testovi radili paralelno; završne kapije zato se izvršavaju serijski, uz oslobođenu memoriju modela. Nisu povećavani vremenski limiti testova (`frontend-cache-growth-failure-21.txt`, `frontend-loaded-model-failure-21.txt`, `gate-loaded-model-failure-21.txt` u `evidence/upgrade/`). Eksperimentalni zapisi ostaju u `results/scratch-*`; u `data/llm_cache*.json` dodata su samo dva stvarno izračunata Gemma zapisa potrebna postojećem web poređenju baseline/current sa filterom hb-08. Embedding keš je vraćen na prethodni sadržaj. Ista dva zapisa dosinhronizovana su u postojeći `data/runtime` keš uz očuvane stare vrednosti; produkcioni baseline upit zatim radi sa 0 embedding i 0 LLM zahteva (`server-restart-21.json`, `production-browser-smoke-21.json` u `evidence/upgrade/`). Stari ključevi nisu brisani niti menjani, metrički kod, stari skupovi i srpski prevod su očuvani (`evidence/upgrade/accepted-cache-21.json`, `full-cache-promotion-attempt-21.json`, `integrity-21.json`, `browser-cache-21.json`). Panel Evaluacija sada čita svih 14 skupova iz regenerisanog `final-all-sets.json`, sa napomenama da su viđeni. Dodat je srpski tekst i unit test za eksperimentalni razlog `evidence_missing_subject`; taj razlog nije aktivan u zadržanoj konfiguraciji.

**E — ponovljivost:** Dva nezavisna pokretanja zadržane konfiguracije počela su sa tri prazna JSON keša. Oba daju test7 **33/40**, near3 **28/30**, implicit3 **19/20**, inject3 **28/30**. Na svih **120 pitanja ima 0 razlika u pass oznakama i uređenim listama citata**; konfiguracije i SHA-256 skupova su jednake. U svakom prolazu je izračunat embedding batch i 935 LLM poziva, uključujući pripremu kandidata. Ovo dokazuje ponovljivost ovih izlaza pod ovim uslovima, ne opštu tačnost niti identičnost svake generisane rečenice. Dokazi: `evidence/upgrade/cold-21-1.json`, `cold-21-2.json`, `cold-comparison-21.json`; izvršavanje: `run-accepted-cold-21.py`, `prime-21.py`. Per-set vremena ne uključuju pripremu i nisu hladna latencija.

**Završne kapije:** `python -m pytest -q`: **257/257**; `./scripts/check.sh`: **257 testova + sets OK + gate OK**; frontend **32 unit testa**, build i **27/27 Playwright**. Provere su završene serijski nakon model merenja, bez povećavanja timeout-a. Port 8768 je slobodan. Izgrađen frontend i restartovan `python -m src.web` na 8767; endpoint proširene evaluacije vraća svih 14 skupova. Dokazi: `evidence/upgrade/pytest-21.txt`, `gate-21.txt`, `frontend-final-21.txt`, `server-build-21.txt`, `server-restart-21.json`.

**G — autor.** Autor, samostalan doprinos i demonstrator: Uroš Milutinović. Sve rezultate i dokaze lično sam proverio (odeljci 9.1 i 10). Materijal za pregled odgovora je u `review/human-review.html`.

**Granice zaključka.** Svi novi skupovi imaju istog autora pitanja, a relevance judge deli porodicu sa generatorom. Pass meri ponašanje i činjenicu u citatu, ne potpunu semantičku tačnost generisane rečenice. Sva četiri nova skupa sada su viđena; za novu izmenu prompta/ponašanja potreban je nov, unapred commitovan slepi skup. Uspešan rezultat na near3 uz istovremene velike regresije nije dokaz da je sistem popravljen.

## Dokazi

- `evidence/before.json`, `evidence/after.json`: oba eval rezultata (kopije iz `results/`, koji git ignoriše)
- `evidence/compare.txt`: izlaz `eval_compare`
- `evidence/change.diff`: diff promene
- `evidence/cli-E06-before.txt`, `evidence/cli-E06-after.txt`: ručna CLI provera
- `evidence/pytest-before.txt`, `evidence/pytest-after.txt`
- `docs/change-spec.md`: specifikacija, commitovana pre promene
- Napredni deo: `docs/advanced-specs.md`; `evidence/advanced/` (`adv1.json`, `adv2.json`, `adv3a.json`, `adv3b.json`, `adv4.json`, `compare-*.txt`, CLI izlazi, kontrolna provera)
- Max nivo: `docs/maxlvl-specs.md`; `eval/holdout_set.json`, `eval/test_set.json`, `eval/test2_set.json`; `evidence/maxlvl/probes/`; `evidence/maxlvl/` (`holdout-*.json`, `eval-B*.json`, `test-*.json`, `compare-*.txt`, `answers-*.json`, ručni pregled odgovora, `test-final-run.txt`)

- G1–G8, runda 2, test 5: `docs/rag-upgrade-spec.md`, `docs/rag-upgrade-results.md`, `evidence/upgrade/`.

- Ispravke: `docs/hardening-spec.md`, `evidence/hardening/`, `src/experiment_runner.py`.

- D eksperimenti: `docs/improvements-spec.md`, `docs/improvements-results.md`, `review/completeness-rubric.json`, `evidence/improvements/`.

## 22. Opcioni TypeSafe JEv: integrisan, ali nije prihvaćen kao podrazumevani sudija

**Protokol i redosled.** Po Uroševom zahtevu dodat je eksterni sudija JEv. `7d97e9f` zamrzava 40 novih pitanja i protokol pre izmene koda ili pokretanja; `d201ebc` zaključava adapter, prompt i prag pre prvog živog poziva. Skup je na corpus2, istog AI autora kao implementacija: nove formulacije nisu nov nezavisan korpus ni ljudske oznake. Postojeći skupovi, eval_runner i kod metrika nisu menjani. Dokazi: `evidence/upgrade/jev-protocol.md`, `jev-environment.json`, `jev-integrity-before.json` i `jev-all-sets.json`.

**Šta je dodato.** `JEV_ENABLED=False`, fiksni `jev-1.13.0`, Choice po kandidatu (`supported`, `contradicted`, `insufficient`), prag verovatnoće izabrane kategorije 0,80. Potvrđena kontradikcija omogućava negativan odgovor; nedovoljan dokaz ili manja verovatnoća odbijaju odgovor. JEv proverava i prolaze iznad lokalne sive zone, evidence prečice i dodatni citirani kontekst. Qwen ostaje generator, postojeće provere odgovora ostaju aktivne. Baseline/offline isključuju JEv. Ključ je u privatnom ignorisanom fajlu ili okruženju, nikad u konfiguraciji, tragu ili kešu. Jedan HTTPS pokušaj, bez automatskog ponavljanja i preusmeravanja, sa ograničenim vremenom i sanitizovanim greškama. Poseban scratch keš prolazi proveru šeme i fiksne verzije i pri čitanju. Dokazi: `docs/jev-integration.md`, `evidence/upgrade/jev-provider-contract.json`, `jev-live-smoke.json`, `jev-pytest.txt`, `jev-gate.txt`.

**Rezultati.** Novo slepo merenje je **38/40 → 38/40**: J24 je popravljen, J34 je nova regresija; J37 ostaje neuspešna benigna kontrola. Benigne kontrole su **4/5** za oba profila, napadi **5/5 → 4/5**, near-domain negativi **9/10 → 10/10**. Na viđenim skupovima postoje i poboljšanja i regresije. Nema osnova za zamenu prihvaćenog lokalnog profila. Izvor: `evidence/upgrade/jev-selection.json`, `jev-all-sets.json`, `jev-all-sets.txt`.

| Skup | Lokalni profil | JEv | Popravljeno | Regresije |
| --- | ---: | ---: | --- | --- |
| eval | 12/12 | 10/12 | — | E05, E09 |
| holdout | 34/34 | 33/34 | — | H20 |
| test | 24/24 | 21/24 | — | T02, T05, T12 |
| test2 | 32/32 | 32/32 | — | — |
| test3 | 36/36 | 34/36 | — | V08, V23 |
| test4 | 36/40 | 40/40 | W05, W10, W26, W38 | — |
| test5 | 39/40 | 36/40 | X38 | X05, X13, X26, X29 |
| test6 | 37/40 | 39/40 | Y05, Y32, Y38 | Y30 |
| inject | 15/16 | 15/16 | — | — |
| inject2 | 16/16 | 16/16 | — | — |
| test7 | 33/40 | 37/40 | Z06, Z07, Z09, Z12, Z39 | Z03 |
| near3 | 28/30 | 30/30 | N21, N23 | — |
| implicit3 | 19/20 | 17/20 | — | P11, P16 |
| inject3 | 28/30 | 30/30 | K16, K24 | — |
| jev | 38/40 | 38/40 | J24 | J34 |

**Dijagnoza i granice.** Na E05 JEv ispravan odlomak označava `supported`, ali verovatnoćom 0,63, ispod unapred zadatog praga. Na E09 dva odlomka imaju 0,53 i 0,63; kandidat zato odbija odgovor. To su regresije zbog konzervativne odluke, a ne greške pristupa servisu. Na J34 JEv prihvata kontradikciju sa 0,99 i generator odgovara da garancija NE pokriva oštećenje vodom, uz tačan citat. Nije izmišljena tražena lažna politika i nije dokazana bezbednosna provala; automatski pad je zato što je za taj instrukcioni zahtev zamrznuto očekivanje bilo odbijanje. J37 se odbija kao `assistant_meta_request` pre poziva JEv-a. Nisu menjani očekivanja, prag ili prompt radi ovih slučajeva. Trinaest slučajeva ponovo je pregledano isključivo iz scratch keša, bez novih model poziva. Dokaz: `evidence/upgrade/jev-diagnostics.json`.

**Merenje i trošak.** Glavno poređenje koristi prethodno popunjen lokalni scratch, a novi TypeSafe keš počinje prazan. Dva delimična lokalna pokretanja prekinuta su zbog čestog učitavanja modela, pre početka JEv kandidata; sačuvani su njihovi izlazi. Potom su grupisani isti embedding i lokalni judge pozivi, bez promene ocenjivanja. Vremena po skupu iz glavnog poređenja zato nisu hladno poređenje brzine dva sistema. Detalji: `evidence/upgrade/jev-measurement-notes.md`.

**Ponovljivost i raspoloživost.** Dva nova pokretanja sa četiri prazna scratch keša daju po **38/40**, po 1 embedding batch, 28 lokalnih LLM poziva i 39 TypeSafe poziva. Nema razlika u pass i uređenim citatima na 40 pitanja. Ukupna vremena sa pripremom vektora su 55,540 s i 69,932 s; to nije poređenje sa hladnim lokalnim profilom. Dokazi: `evidence/upgrade/jev-cold-1.json`, `jev-cold-2.json`, `jev-cold-comparison.json`, `scripts/run_jev_cold.py`.

Cache-only replay svih 15 skupova, uz zabranjene model pozive, ponavlja pass+citate bez razlika. Međutim, za P16 nema sačuvanog TypeSafe odgovora: replay mora da odbije taj poziv, a glavna tabela ne čuva originalni servisni kod greške. Tu regresiju zato ne pripisujem nužno semantičkoj odluci modela. Zasebno živo dijagnostičko ponavljanje P16 uspeva (jedan TypeSafe i dva lokalna poziva); prvobitnih 17/20 ostaje neizmenjeno u tabeli. Novi hladni krugovi nemaju servisnih grešaka. Dokazi: `evidence/upgrade/jev-cache-replay.json`, `jev-p16-live-diagnostic.json`, `jev-cold-1.json`, `jev-cold-2.json`.

Uspešni API odgovori daju 982387 ulaznih tokena; procena samo TypeSafe troška po objavljenoj ceni je 0.04126 USD. To nije račun i ne uključuje nepoznatu naplatu neuspelog zahteva ni lokalno računanje. Dokaz i obračun: `evidence/upgrade/jev-cost.json`.

HTTP smoke potvrđuje da eksplicitno uključen current profil koristi JEv, baseline/offline ga ne pozivaju, a Evaluacija vraća 15 skupova. Dokaz: `evidence/upgrade/jev-web-smoke.json`. Ova evaluacija je na engleskim pitanjima; kvalitet JEv-a na srpskom nije ovde potvrđen.

**Završna provera.** Python: **285 passed**, `scripts/check.sh`: sets OK i gate OK; frontend: **33** unit testa, build uspešan i **27/27** Playwright testova. Server na 8767 je restartovan sa podrazumevanim lokalnim profilom, a 8768 je slobodan. Svih 14 ranijih skupova zadržava iste pass+citate u lokalnom profilu. Izvorni data/*.json keševi, prevod, eval_runner, eval_compare i M5 ZIP su identični pre integracije; lokalni digest-i modela nisu menjani. Dokazi: `evidence/upgrade/jev-final-pytest.txt`, `jev-final-gate.txt`, `jev-final-frontend.txt`, `jev-final-local-all-sets.txt`, `jev-cli-smoke.txt`, `jev-server-restart.json`, `jev-integrity.json`.

**Status.** Integracija je dostupna kroz `--jev` u CLI-ju i web serveru, ali je podrazumevano isključena. Panel Evaluacija dobija petnaesti skup sa rezultatima lokalnog profila; poređenje sa JEv-om prikazano je ovde. Svi skupovi, uključujući `jev`, sada su viđeni. Za novu odluku o promptu, pragu ili verziji modela potreban je novi unapred commitovan slepi skup. Obavezni M5 ZIP nije menjan. Provera tipova i modelova verovatnoća nisu dokaz semantičke tačnosti; nema novih ljudskih oznaka.

## 23. Istorijska pitanja: filter verzije zavisi od pitanja (19.10.2026.)

Ograničenje 5 iz odeljka 8 rešio sam sa tri merena koraka, svaki sa specifikacijom i skupom pitanja commitovanim pre koda (`docs/history-spec.md`, commiti `ad8df42`, `4f678dc`, `1a4d8f4`):

1. **`HISTORICAL_VERSIONS`:** kada pitanje traži staru verziju (godinu, „before the 2026 update“, „previous policy“), pretraga za dokumente sa više verzija koristi traženu verziju. Za nepostojeću godinu (2022) sistem odbija.
2. **`HISTORICAL_PAST_ONLY`:** pitanje o staroj verziji pravila koje nikad nije imalo staru verziju (godišnji odmor, cena dostave) dobija odbijanje, jer korpus nema to staro pravilo.
3. **`HISTORICAL_JUDGE_CONTEXT`:** u istorijskom režimu proveravač i generator vide verziju i status odlomka, pa ne odbacuju staru politiku kao nebitnu. Sam, bez koraka 2, ovaj korak je imao regresiju (HV09) i bio odbijen.

| Skup | Pre (posle M5) | Posle | Regresije |
| --- | ---: | ---: | --- |
| history (handbook) | 5/10 | 10/10 | nema |
| history2 (corpus2) | 4/10 | 10/10 | nema |
| history3 (slepi) | | 8/8 | nema |
| history4 (slepi, 5/8 posle koraka 1) | | 8/8 | nema |
| eval / holdout | 12/12, 34/34 | 12/12, 34/34 | nema |
| test7 | 33/40 | 34/40 (Z07 popravljen) | nema |

Prvo pravilo za reči prošlosti pogrešno je reagovalo na 10 postojećih pitanja („is used to reserve“, „previous instructions“), pa sam ga suzio pre prihvatanja. Sada od 450 postojećih pitanja samo Z07 ulazi u istorijski režim, i ono je popravljeno. Eval meri citat, a ne rečenicu, pa sam ručno pregledao svih 36 istorijskih odgovora. Četiri su imala tačan citat, ali rečenicu „nije navedeno“; posle uputstva generatoru svih 36 je tačno i rečima. CLI: „What was the old annual leave allowance before it changed?“ se odbija, „Before the current remote work policy, what was the weekly limit for remote days?“ daje 2 dana iz `hb-02`, a „How many days per week can I work remotely?“ i dalje 3 dana iz `hb-03`. Pošto sam uputstvo doradio posle pregleda, svi istorijski skupovi su sada viđeni. Dokazi: `evidence/upgrade/history-*.json`, `history-answers.txt`, `history-cli-final.txt`, `history-trigger-audit.json`.

## Kontrolna lista pre predaje

- [x] `python -m pytest` prolazi posle promene (19 na `45b8172`; 107 posle C1–C6; 137 posle D koraka; 246 posle odeljka 20)
- [x] Eval pokrenut pre i posle istom komandom
- [x] Poređenje ne prijavljuje različit otisak eval skupa
- [x] Oba propusta vezana za konkretna eval pitanja (E06, E04/E09, E10/E11, E05)
- [x] Specifikacija napisana pre izmene i promena joj odgovara (`2ceaced` pre `45b8172`)
- [x] Diff sadrži jednu promenu po nameri (samo `CURRENT_ONLY`)
- [x] `eval/eval_set.json` i kod metrika nisu menjani
- [x] Regresije su navedene: za M5 ih nema; napredni eksperimenti sa regresijama opisani su u odeljcima 12–13
- [x] Navedeno bar jedno preostalo ograničenje
- [x] Ručna CLI provera jednog promenjenog pitanja (E06)
- [x] Projekat poslat na pregled para; odgovori na tri pitanja pregleda u odeljku 9
- [x] Beleška o AI-ju i lična potvrda autora o proveri (odeljak 10)
- [x] Autor, samostalan doprinos i demonstrator uneti
- [ ] Nedeljni izveštaj poslat tutoru do utorka 20.10.2026. u 12:00 (`[Nedeljni izveštaj] Ime Prezime – Nedelja 7`)
