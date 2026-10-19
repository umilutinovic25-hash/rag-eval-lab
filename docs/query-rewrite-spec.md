# Query rewriting: specifikacija (napisana pre merenja)

Zadatak u naprednom cilju navodi četiri tehnike: reranking, query rewriting, hibridnu pretragu i embeddings. Reranking (LLM proveravač u sivoj zoni), hibridna pretraga (RRF i BM25, odbijeni) i embeddings (`bge-m3`) već su izmereni. Ovo je merenje četvrte.

**Promena (`QUERY_REWRITE`):** pre pretrage lokalni model (`qwen2.5:7b`) prepiše pitanje u kratak upit rečima kakve koristi pravilnik. Ocena pretrage koristi prepisan upit, a sve ostalo (proveravač, odgovor) originalno pitanje.

**Hipoteza:** parafraze („notebook computer“, „work from home“) bi trebalo da se bolje poklope sa tekstom pravilnika. Semantička pretraga to već delom rešava, pa očekujem mali ili nikakav dobitak.

**Merenje:** `python -m src.retrieval_metrics --variants headers headers+rewrite rewrite baseline --sets <handbook skupovi>`; MRR, doc_hit@1/2, fact_recall@1/2/5. Uključuje se samo ako fact_recall@2 raste bez pada na nekom skupu; inače ostaje kao izmereno poređenje sa troškom (jedan dodatni LLM poziv po pitanju).

## Rezultat: odbijeno

174 pitanja sa odgovorom na 10 handbook skupova (`evidence/upgrade/rewrite-metrics.json`):

| | Bez preformulisanja | Sa preformulisanjem |
| --- | ---: | ---: |
| MRR | 0.9789 | 0.9670 |
| doc_hit@1 | 0.9943 | 0.9770 |
| fact_recall@1 | 0.9598 | 0.9368 |
| fact_recall@2 | 0.9943 | 0.9943 |
| fact_recall@5 | 1.0000 | 1.0000 |

Prva činjenica je rangirana bolje kod 6 pitanja, a lošije kod 10. Semantička pretraga sa naslovom dokumenta već pokriva parafraze, a preformulisanje ponekad izgubi detalj iz pitanja. Trošak je jedan dodatni poziv `qwen2.5:7b` po pitanju. `QUERY_REWRITE` ostaje `False`.
