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

## D4b — kontekst samo za izričite reference

Dodato posle prvih rezultata D4, pre implementacije D4b. D4 zadržava 12/12 eval, ali holdout pada 34→33: H14 ima dokaz, ali se uz nebitan drugi dokument proširenjem dodaje više nebitnih chunk-ova, pa CitPrec pada na 0.40. Zato D4 all-neighbors ostaje isključen. D5 se meri u odnosu na najbolju verziju sa CONTEXT_NEIGHBORS=0, ne na ovu regresiju.

D4b hipoteza: proširenje je potrebno samo kada izabrani pasus izričito upućuje na prethodni (same/that/this form, policy, procedure, process). CONTEXT_POLICY=references dodaje samo do CONTEXT_NEIGHBORS prethodnih pasusa u istoj verziji/dokumentu/statusu. Nema širenja za obične samostalne pasuse ili sledeće pasuse. Ovo nije pravilo za ID H20, nego pravilo za tekstualne reference.

Očekivanje: H20 dobija lokaciju formulara, a H14 nema nove citate. Prihvatiti samo bez novih PASS regresija na četiri skupa i uz lokacione činjenice u model odgovoru ili njegovom jasnom izvoru. Rizici: drugi tipovi anafore nisu obuhvaćeni; prethodni pasus može biti šum. Jedna ova varijanta, bez daljih prompt sweep-ova.

## D5b — strogo parsiranje JSON-a sa opcionim Markdown omotačem

D5 već pokazuje regresije (eval 11/12, holdout 21/34). Sirovi E05 odgovor jeste validan supported JSON sa dokazom, ali je obavijen tačno jednim ```json ... ``` blokom pa ga parser odbacuje. H06/H13 su stvarni insufficient odgovori i ovaj format popravak ih ne može rešiti.

Pre izmene: dozvoliti samo opcioni, ceo Markdown JSON blok oko jednog JSON objekta; sav spoljašnji tekst i neispravna šema ostaju odbačeni. Ne menjati upit/model/status kriterijume niti izmišljati dokaz. Očekivanje je vraćanje E05 bez novih poziva judge-u, koristeći isti sačuvani tekst. Na sva 4 skupa meriti D5b; default uključiti samo uz originalni uslov bez regresija i uz dobitak. Ovo nije novi nezavisni ili slepi test.
