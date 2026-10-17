# Max nivo: generalizacija i poređenje naprednih tehnika

Ovo je nastavak naprednog cilja (A1–A4), odvojen od obaveznog dela. Na fiksnom eval skupu sistem je već 12/12, a pragovi su kalibrisani na tih istih 12 pitanja. Dalje merenje samo na njemu ne bi dokazalo ništa, pa se uvode dva nova skupa u istom formatu:

| Skup | Fajl | Pitanja | Kada je napisan | Kako se koristi |
| --- | --- | --- | --- | --- |
| eval | `eval/eval_set.json` | 12 | dat uz zadatak | regresija, ne sme da padne |
| holdout | `eval/holdout_set.json` | 34 | posle A4, commit `7682879`, pre prvog merenja | razvoj: dijagnoza B0, merenje svake promene |
| test | `eval/test_set.json` | 24 | posle B0, commit `bc03d27`, pre svih B promena | **jedno** pokretanje na kraju, za sistem pre i posle B promena |

Oba skupa pokreće `python -m src.holdout_runner --set ... --out ...`, koji koristi iste funkcije za metrike kao `eval_runner` (`evaluate_item`, `summarise`), bez izmene koda metrika.

## B0: dijagnoza (sistem posle A4, bez izmene)

| Skup | lexical | semantic (A4) |
| --- | --- | --- |
| eval | 10/12 | 12/12 |
| holdout | 16/34 | 29/34 |

Na holdoutu semantic ima retrieval hit 1.00, ali pada 5 pitanja i svi padovi su u odluci da li odgovoriti ili odbiti:

- pogrešno odbijena: H06 (0.548), H08 (0.540), H24 (0.553), jer je vrh ispod praga 0.60;
- pogrešno odgovorena: H25 (0.622), H34 (0.676), jer su iznad praga.

Najslabije podržano pitanje (0.540) je ispod najjačeg nepodržanog (0.676), pa **nijedan kosinusni prag ne razdvaja skup**. Prag 0.60 iz A3 važi samo za eval skup.

Svaka promena ispod meri se u odnosu na prethodnu. Ako promena pogorša holdout, ostaje u kodu kao opcija, ali isključena, a sledeća promena se meri u odnosu na najbolje stanje.

## B1: hibridna pretraga (RRF)

| Polje | Sadržaj |
| --- | --- |
| Propust | Nema propusta u retrievalu na eval ni holdoutu (hit 1.00). Ovo je poređenje tehnike koju zadatak navodi, a ne popravka. |
| Hipoteza | Spajanje leksičkog i semantičkog ranga pomaže pitanjima sa tačnim terminom (broj, naziv aplikacije), ali leksička pristrasnost ka kratkim chunk-ovima može da ubaci nebitan chunk u top-2 i smanji CitPrec. Očekujem da ne pomaže, a moguće je i da šteti. |
| Promena | `RETRIEVAL_MODE = "hybrid"`: redosled po Reciprocal Rank Fusion, `1/(60+rang_lexical) + 1/(60+rang_semantic)`, a `score` rezultata ostaje kosinus, pa pragovi ostaju na istoj skali. |
| Očekivani efekat | eval 12/12 i holdout 29/34 bez promene, ili blagi pad CitPrec. |
| Rizik regresije | Leksički rang vuče kratke chunk-ove u vrh. |
| Provera | `pytest`, `eval_runner`, `holdout_runner`, `eval_compare` za oba skupa. |

## B2: reranking i provera odgovorljivosti lokalnim LLM-om

| Polje | Sadržaj |
| --- | --- |
| Propust | H06, H08 i H24 su pogrešno odbijena, a H25 i H34 pogrešno odgovorena. Tip: pogrešno odbijanje i pogrešan odgovor. Uzrok je to što kosinus meri sličnost teme, a ne to da li pasus sadrži odgovor. |
| Hipoteza | LLM koji čita pitanje i pasus zajedno (kao cross-encoder) razlikuje „ista tema“ od „sadrži odgovor“: „sick leave follows a separate policy“ nije broj dana bolovanja. Proba na 4 pasusa iz holdouta, pre ovog spec-a: `gemma3:4b` 4/4, `qwen2.5:7b` 3/4, `qwen2.5:3b` 2/4. |
| Promena | `RERANK = "llm"`, `RERANK_MODEL = "gemma3:4b"`, `RERANK_CANDIDATES = 5`. Za prvih 5 kandidata model dobija upit „Does the passage contain the information needed to answer the question? Answer only yes or no.“ (temperature 0, seed 7). Zadržavaju se pasusi sa „yes“, po redosledu retrievala, do `TOP_K`. Ako nijedan nije „yes“, sistem odbija. Kosinusni pragovi se tada ne koriste. Model, upit i broj kandidata su fiksirani ovde i **ne podešavaju se** prema holdoutu. |
| Očekivani efekat | holdout: H06, H08, H24, H25 i H34 → PASS; eval ostaje 12/12. |
| Rizik regresije | Model može reći „no“ za pasus kome treba kontekst susednog chunk-a (E04, E09) ili „yes“ za pasus koji je samo blizu (E11 „parental leave“ ↔ „annual leave“). Novi troškovi: model od 3.3 GB i oko 5 poziva po pitanju (~2 s). Odgovori modela keširaju se u `data/llm_cache.json`, pa eval radi offline i deterministički. |
| Provera | `pytest` (lažni LLM), `eval_runner`, `holdout_runner`, `eval_compare`, CLI za H06 i H34. |

## B2b: upit za proveru bez zamene polariteta

Dodato posle merenja B2, pre izmene. Holdout je ovde razvojni skup, pa je zato završni test skup slep.

| Polje | Sadržaj |
| --- | --- |
| Propust | B2 popravlja H06, H08, H24, H25 i H34, ali kvari H03, H07, H17, H23 i H13. Model kaže „No.“ za svih 5 kandidata, uključujući i pasus sa odgovorom. Tip: pogrešno odbijanje. |
| Hipoteza | Kod H03, H07, H17 i H23 pitanje je da/ne, a tačan odgovor je „ne“ („Is IT support available on weekends?“ → „Monday to Friday“). Model odgovara na **pitanje** umesto na **proveru**, jer obe stvari traže „yes/no“. Ako izlazne reči ne budu yes/no, nego RELEVANT/IRRELEVANT, uz napomenu da i negativan odgovor računa, polaritet se ne meša. H13 („car space“ ↔ „parking“) je obična greška modela, pa ga ova promena verovatno ne popravlja. |
| Promena | Samo `RERANK_PROMPT`: „Question: ... Passage: ... Does this passage contain the facts needed to answer the question? It still counts if the facts show that the answer is no. Reply with one word: RELEVANT or IRRELEVANT.“ Parser već prihvata „relevant“ kao prvu reč, a „irrelevant“ ne. |
| Očekivani efekat | H03, H07, H17 i H23 → PASS; holdout 29 → 33; eval 12/12. |
| Rizik regresije | Blaži kriterijum može da propusti nepodržana pitanja bliska temi: H25 „sick days“ ↔ „Sick leave follows a separate policy“, E11 „parental leave“ ↔ „Annual leave“. |
| Provera | `pytest`, `eval_runner`, `holdout_runner`, `eval_compare` u odnosu na B2. |

## B3: generisanje odgovora lokalnim LLM-om

| Polje | Sadržaj |
| --- | --- |
| Propust | Odgovor je samo spoj citiranih chunk-ova („Grounded response based on retrieved context: ...“), a ne odgovor na pitanje. Tip: kvalitet odgovora. Eval to ne meri, jer meri ponašanje i citate. |
| Hipoteza | Model koji dobije samo citirane pasuse napisaće kratak odgovor sa činjenicom i oznakom `[chunk-id]`, a citati i odluka o odbijanju ostaju isti kao u B2. |
| Promena | `ANSWER_MODE = "llm"`, `GENERATION_MODEL = "gemma3:4b"`. Upit: odgovori u jednoj ili dve rečenice samo iz pasusa i navedi `[chunk-id]`. Citati se ne menjaju. |
| Očekivani efekat | eval i holdout metrike identične B2, jer se ne menjaju citati ni odbijanje. Nova, posebna mera (`src/answer_quality.py`, ne dira kod metrika): udeo odgovora koji sadrže `expected_fact` i udeo odgovora čiji `[chunk-id]` postoje među citatima. |
| Rizik regresije | Halucinacija, odnosno činjenica koje nema u pasusima; preformulisana činjenica („90 days“ umesto „every 90 days“) pada na strogoj proveri podniza, pa se padovi pregledaju ručno. |
| Provera | `pytest`, eval i holdout identični B2, `answer_quality` za oba skupa, CLI za E06. |

## Završno: test skup (jednom)

`holdout_runner --set eval/test_set.json` za stanje B0 i za konačno stanje, u istom pokretanju i bez daljih izmena posle toga. Rezultat se prijavljuje kakav god da je.
