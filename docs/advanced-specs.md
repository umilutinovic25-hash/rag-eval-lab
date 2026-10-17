# Napredni cilj: specifikacije dodatnih promena

Svaka promena se meri u odnosu na rezultat prethodne (`after.json` → `adv1.json` → ...). Svaka specifikacija je commitovana pre svoje izmene koda.

## A1: sečenje po rečenicama (M1)

| Polje | Sadržaj |
| --- | --- |
| Propust | **E04** i **E09**: pravi dokument `hb-01` je nađen, ali „5 business days“ je u `hb-01-chunk-1`, koji je tek peti po oceni. Sečenje na 140 znakova kida reči („op is set up“, „iness days“, „Report lost or sto“), pa chunk nosi krhotine koje se ne poklapaju sa pitanjem. Tip: chunkovanje. |
| Hipoteza | Ako su chunk-ovi cele rečenice, rečenica sa „5 business days“ ostaje cela i sadrži reči iz pitanja („replacement“, „laptop“, „take“, „business“, „days“), pa ulazi u top-2. |
| Promena | Implementirati `split_text_by_sentences` (rečenice se pakuju do `CHUNK_SIZE` znakova, a duža rečenica postaje svoj chunk) i postaviti `CHUNK_STRATEGY = "sentences"`. `CHUNK_OVERLAP` se tada ne koristi, ali se ne menja. |
| Očekivani efekat | E04 i E09 → PASS. Ostala podržana pitanja ostaju PASS, jer su činjenice u kratkim rečenicama. |
| Rizik regresije | Menja se svaki chunk, pa i sve ocene. Duže rečenice dobijaju nižu ocenu (deljenje dužinom), pa se drugi citati i rang mogu promeniti bilo gde. E10 i E11 mogu dobiti drugačiji vrh. |
| Provera | `pytest`, `python -m src.eval_runner --out results/adv1.json`, `eval_compare results/after.json results/adv1.json`, CLI za E04. |

## A2: kalibracija praga odbijanja (M3)

| Polje | Sadržaj |
| --- | --- |
| Propust | **E10** „What is the current company stock price?“ treba da bude odbijeno, ali sistem odgovara sa vrhom 0.077 (`hb-05-chunk-1`, `hb-09-chunk-1`), jer chunk-ovi sa pitanjem dele samo reč „is“. Tip: pogrešan odgovor (prag 0.02 je prenizak). |
| Hipoteza | U `results/adv1.json` najniži vrh podržanog pitanja je 0.207 (E04), a E10 ima 0.077. Prag između te dve vrednosti razdvaja ih. Biram 0.12, otprilike sredinu, da ostane margina za podržana pitanja sa drugačijom formulacijom. |
| Promena | `REFUSAL_THRESHOLD = 0.02` → `0.12`. Bez promene koda. |
| Očekivani efekat | E10 → PASS (odbijanje). Behaviour accuracy 0.83 → 0.92. |
| Rizik regresije | Prag je kalibrisan na istom skupu na kojem se meri, pa je rezultat optimističan. Kratko podržano pitanje sa malo zajedničkih reči moglo bi da bude pogrešno odbijeno. E11 (vrh 0.22) **neće** biti popravljen, jer je iznad vrha E04. |
| Provera | `python -m src.eval_runner --out results/adv2.json`, `eval_compare results/adv1.json results/adv2.json`, CLI za E10. |

## A3: semantička pretraga sa lokalnim embeddingima (napredna tehnika)

Promena ide u dva koraka da bi razlika pripadala jednoj odluci:

- **A3a** dodaje infrastrukturu (`src/embeddings.py`, `RETRIEVAL_MODE`, `EMBEDDING_MODEL`, `SEMANTIC_REFUSAL_THRESHOLD`) sa podrazumevanim `RETRIEVAL_MODE = "lexical"`. Očekivano: rezultat identičan `adv2.json`. Poređenje će prijaviti tri nova podešavanja, ali nijedno ne utiče na leksički režim.
- **A3b** menja samo `RETRIEVAL_MODE = "lexical"` → `"semantic"`.

| Polje | Sadržaj |
| --- | --- |
| Propust | **E05** „How long until I get a new notebook computer?“: leksički retrieval nema poklapanje „notebook computer“ ↔ „laptop“, pa je vrh `hb-06` (Onboarding). Tip: retrieval (parafraza). **E11** „What is the parental leave policy?“: deli „leave policy“ sa `hb-07` i dobija 0.22, iznad najslabijeg podržanog pitanja, pa ga nijedan leksički prag ne odbija. Tip: pogrešan odgovor. |
| Hipoteza | Embedding model `bge-m3` (lokalno, preko Ollama) poredi značenje, pa „notebook computer“ nalazi rečenicu o zameni laptopa. Za E11 kosinusna sličnost sa „Annual leave“ je niža nego za stvarno podržana pitanja. Provera pre specifikacije (sonda u scratchpad-u, bez izmene repoa): najniži vrh podržanog pitanja je 0.647 (E05), najviši vrh nepodržanog 0.567 (E11). |
| Promena | Kada je `RETRIEVAL_MODE = "semantic"`, ocena chunk-a je kosinusna sličnost embeddinga pitanja i chunk-a, a odbijanje koristi `SEMANTIC_REFUSAL_THRESHOLD = 0.60` (sredina između 0.567 i 0.647; leksički prag 0.12 nije na istoj skali). Embeddingi se keširaju u `data/embedding_cache.json`, pa eval posle prvog pokretanja radi bez mreže i bez Ollama. |
| Očekivani efekat | E05 i E11 → PASS. Ostala pitanja ostaju PASS. Očekivano 12/12. |
| Rizik regresije | Prag je kalibrisan na istom skupu (margina samo 0.04 sa obe strane), pa je rezultat optimističan. Novo pitanje može biti pogrešno odbijeno ili pogrešno odgovoreno. Embeddingi slabije hvataju tačne termine i brojeve. Nova zavisnost: Ollama + model od 1.2 GB i sporiji odgovor za pitanje koje nije u kešu. Testovi ne smeju zavisiti od Ollama. |
| Provera | `pytest` (lažni embedder), `eval_runner --out results/adv3a.json` (mora biti isto kao `adv2`), zatim `--out results/adv3b.json` i `eval_compare results/adv3a.json results/adv3b.json`, CLI za E05 i E11. |

## A4: prag za citate (M4)

| Polje | Sadržaj |
| --- | --- |
| Propust | U `results/adv3b.json` E01, E05 i E07 imaju CitPrec 0.50, jer se uvek citiraju oba top-2 chunk-a. Drugi citat je iz nebitnog dokumenta: E01 `hb-03-chunk-0` (0.571), E05 `hb-06-chunk-0` (0.570), E07 `hb-03-chunk-3` (0.624). Tip: citat (dopuna). |
| Hipoteza | Dopunski citati imaju kosinus ≤ 0.624, a drugi citati iz pravog dokumenta koji nose dodatni kontekst (E06 0.745, E08 0.678, E09 0.686) su iznad 0.65. Prag 0.65 uklanja dopunu i zadržava ih. |
| Promena | Implementirati `select_citations` u `src/rag.py`: citiraju se rezultati sa ocenom ≥ `CITATION_MIN_SCORE`, a prvi rezultat se uvek citira kada se odgovara. Postaviti `CITATION_MIN_SCORE = 0.65`. |
| Očekivani efekat | E01, E05 i E07 dobijaju CitPrec 1.00. Mean citation precision 0.83 → 1.00. Passed ostaje 12/12, jer je činjenica u svakom slučaju u prvom citatu. |
| Rizik regresije | Prag je na kosinusnoj skali i kalibrisan na eval skupu (margina 0.026 iznad najjačeg dopunskog citata). U leksičkom režimu ista vrednost bi izbacila skoro sve druge citate. Ako je činjenica samo u drugom chunk-u sa ocenom ispod 0.65, biće izgubljena (na ovom skupu to se ne dešava, ali E02, E03 i E04 gube drugi citat iz pravog dokumenta). |
| Provera | `pytest`, `eval_runner --out results/adv4.json`, `eval_compare results/adv3b.json results/adv4.json`. |
