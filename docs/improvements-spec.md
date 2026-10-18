# D1–D6: specifikacija pre implementacije

Polazna verzija: f430863. Nova analiza: ANALIZA-POSLE-C6-2026-10-18.md. Svi skupovi su sada viđeni; ovo su razvojni eksperimenti i replay, ne novi slepi test. Originalni eval skup i originalni kod metrika ostaju netaknuti.

| Korak | Promena i očekivanje | Rizik i kriterijum prihvatanja |
| --- | --- | --- |
| D1 | Prekinuti filtriranje posle TOP_K prihvaćenih kandidata; isti redosled i kompletan rezultat. | Prihvatiti samo uz identične redove/citate na sva 4 skupa i manje judge poziva na pozitivnim kandidatima. |
| D2 | RagAnswer dobija trag kandidata/odluka; eksperiment trajno čuva odgovore, request uspehe/greške i cache snapshotove. LLM response metadata beleži done_reason; prekinuto generisanje odgovora koristi izvorni tekst. | Sačuvati stare keševe, metadata istorijskog teksta je unknown. Replay ne glumi nove model pozive. Testirati otkaz servera, prekid i očuvanje sirovih artefakata. |
| D3 | Poseban nacrt rubrike sa obaveznim činjenicama za E09,H20,U17,U13 i pregledom dvosmislenog T02. Alat proverava sve delove i pravila dokaza. | Nacrt asistenta, bez lažne ljudske potvrde; automatski substring rezultat nije semantički sud. |
| D4 | Opcioni CONTEXT_NEIGHBORS=1 proširuje već izabrane citate susednim chunk-ovima istog dokumenta/verzije/statusa, u izvornom redosledu. Reranking ostaje isti. | Meriti sva 4 skupa i rubriku. Zadržati samo bez novih PASS regresija i uz bolji H20 lokacioni dokaz. Više konteksta može dodati šum, citate i tokene. |
| D5 | Opcioni RERANK_JUDGE=structured: qwen2.5:7b vraća JSON supported/contradicted/insufficient i listu doslovnih dokaznih rečenica. Supported i contradicted mogu da odgovore; insufficient odbija. | Fiksni upit, bez niza podešavanja po rezultatima. Izmeriti na sva 4 skupa uz D4. Default zadržati samo bez novih PASS regresija i uz poboljšanje bar jednog preostalog pada. Invalid JSON/evidence ne prolazi. |
| D6 | Jedinice i negacija vezane uz rečenicu/dokaz; sumnjiv generisani odgovor ide u izvorni tekst. Provera negacije razdvaja klauze; stabilan kosinus za ekstremne konačne ulaze. | Heuristička zaštita, ne semantička garancija. Brojevi ispisani rečima normalizuju se u najčešćim engleskim oblicima; uključiti negativne i pozitivne testove. Meriti učestalost fallback-a, tačne uslove i ne menjati originalne metrike. |

Lokalni modeli su već instalirani; ne preuzimati nove. Žive probe koriste izdvojen keš i jasnu provenance evidenciju. Ako D4/D5 pogoršaju kvalitet, čuvaju se kao isključene opcije uz rezultate. Nije dozvoljeno izmišljati ljudski pregled ili tvrdnju da je sve tačno.
