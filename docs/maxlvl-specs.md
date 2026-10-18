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

**Rezultat B2b:** hipoteza nije potvrđena (eval 12 → 11, E09; holdout 29 → 28, H20). Model i dalje kaže „IRRELEVANT“ za „Never share passwords, also not with colleagues from IT“. Uzrok nije polaritet, nego to što model od 4B ne povezuje implicitan ili negativan dokaz sa pitanjem. Upit je vraćen na B2.

## B2c: kaskada (LLM odlučuje samo u sivoj zoni)

| Polje | Sadržaj |
| --- | --- |
| Propust | Kao B2: judge popravlja pitanja sa niskim kosinusom (H06 0.548, H08 0.540, H24 0.553, H25 0.622, H34 0.676), a kvari pitanja sa visokim (H03 0.732, H07 0.756, H17 0.719, H23 0.721, H13 0.620). |
| Hipoteza | Kada je kosinus visok, retrieval je pouzdan i judge samo unosi grešku. Kada je nizak, pitanje nije podržano. Judge vredi samo tamo gde se klase preklapaju. Granice iz B0 (eval + holdout): najviši vrh nepodržanog je 0.676 (H34), najniži vrh podržanog 0.540 (H08). Biram **0.70** i **0.50**, zaokruženo izvan tog opsega. |
| Promena | `RERANK = "llm-gray-zone"`, `RERANK_GRAY_ZONE = (0.50, 0.70)`. Vrh ≥ 0.70: odgovor i citati kao bez rerankinga (prag citata 0.65). Vrh < 0.50: odbijanje. Između: B2 judge sa B2 upitom. |
| Očekivani efekat | holdout 29 → 33 (ostaje H13, 0.620, jer judge kaže „no“); eval 12/12, jer su E05 (0.647) i E11 (0.567) u sivoj zoni i B2 judge ih rešava tačno. Pozivi modela samo za pitanja u sivoj zoni. |
| Rizik regresije | Granice su izvedene iz holdouta, pa je holdout rezultat optimističan. Pravi sud daje samo slepi test skup. Pitanje sa visokim kosinusom koje ipak nije podržano (sinonim teme) biće odgovoreno bez provere. |
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

## Drugi krug: B4 i B5

Posle prvog kruga ostali su padovi H13, T02 i T06 (judge pogrešno odbija) i nepodržani detalji u odgovorima H10 i T10. Test skup 1 je sada viđen, pa se ubuduće koristi kao razvojni. Novi slepi skup `eval/test2_set.json` (32 pitanja) napisan je i commitovan (`1982c20`) pre B4 i B5, a pokreće se jednom, na kraju.

**Izbor je rađen samo na eval i holdout skupu** (proba u scratchpad-u, sa privremenim kešom; repo nije menjan):

| Judge u sivoj zoni | eval | holdout | Padovi |
| --- | --- | --- | --- |
| gemma3:4b, B2 upit (sadašnje stanje) | 12/12 | 33/34 | H13 |
| gemma3:4b, upit sa 3 opšta primera | 12/12 | 33/34 | H25 |
| qwen2.5:7b, B2 upit | 11/12 | 31/34 | E05, H01, H11, H13 |
| mistral, upit sa primerima | 12/12 | 32/34 | H25, H33 |
| llama3.2, B2 upit | 11/12 | 33/34 | E11, H25 |
| gemma3:4b, verovatnoća „yes“ preko logprob, prag 0.5 / 0.2 / 0.05 / 0.01 | 12/12 | 33/34 | H13 (svaki prag) |
| izvlačenje + provera, gemma3:4b | 11/12 | 34/34 | E11 |
| **izvlačenje + provera, qwen2.5:7b** | **12/12** | **34/34** | nema |
| izvlačenje + provera, mistral | 12/12 | 30/34 | H02, H06, H13, H24 |
| izvlačenje + provera, qwen2.5:7b, ali za **svako** pitanje (bez sive zone) | 11/12 | 31/34 | E09, H03, H17, H23 |

## B4: judge izvlači tačne reči iz pasusa, a kod ih proverava

| Polje | Sadržaj |
| --- | --- |
| Propust | H13 „car space“ ↔ „parking“: da/ne judge kaže „no“, iako pasus sadrži odgovor. Tip: pogrešno odbijanje. |
| Hipoteza | Pitanje „da li pasus sadrži odgovor?“ model rešava površno. Zadatak „prepiši reči koje odgovaraju, ili NONE“ prisiljava ga da pronađe dokaz. Kod zatim proverava da je ono što je model prepisao zaista u pasusu (najmanje 80% reči), pa izmišljen dokaz ne prolazi. Prag 0.8 je izabran unapred, a ne na osnovu rezultata. |
| Promena | `RERANK_JUDGE = "span"` (`"yesno"` je B2 ponašanje), `RERANK_MODEL = "qwen2.5:7b"`, `RERANK_SPAN_PROMPT` = „Copy the exact words from the passage that answer the question. If the passage does not contain the answer, reply NONE.“ Siva zona 0.50–0.70 se ne menja. |
| Očekivani efekat | eval 12/12, holdout 34/34 (kao u probi). |
| Rizik regresije | Model menja `gemma3:4b` (3.3 GB) za `qwen2.5:7b` (4.7 GB), a poziv je duži (do 40 tokena), pa je sporiji. Na da/ne pitanjima sa visokim kosinusom ovaj judge i dalje greši, ali ih siva zona propušta bez provere. |
| Provera | `pytest` (lažni model; provera da izmišljen dokaz ne prolazi), eval, holdout, test 1 (viđen), `eval_compare`. |

## B5: strog upit za generisanje i isti model

| Polje | Sadržaj |
| --- | --- |
| Propust | H10 („from an appropriate authority“) i T10 (dodat uslov) sadrže detalje kojih nema u pasusu. Tip: nepodržan sadržaj u odgovoru. |
| Hipoteza | Izričita zabrana dodavanja uslova, ljudi, koraka i detalja, uz jači model, smanjuje izmišljanje. Proba na eval i holdout skupu meri udeo odgovora sa sadržajnim rečima kojih nema ni u pasusu ni u pitanju: gemma sa sadašnjim upitom 24/32, gemma sa strogim 12/32, qwen sa strogim 3/32 (sve tri su bezazlene preformulacije: „make“, „submit“, „ordering“). |
| Promena | `GENERATION_MODEL = "qwen2.5:7b"` i strog `GENERATION_PROMPT`. `answer_quality` dobija i novu meru, `unsupported_words`: sadržajne reči kojih nema u citiranim pasusima ni u pitanju. |
| Očekivani efekat | Metrike eval i holdout iste kao B4; manje odgovora sa nepodržanim rečima; H10 bez „appropriate authority“. |
| Rizik regresije | Stroži odgovori su kraći i mogu da izostave koristan kontekst. Mera reči je gruba (sinonim se računa kao nova reč), pa se pregleda ručno. |
| Provera | `pytest`, eval i holdout metrike identične B4, `answer_quality` za sve skupove, ručni pregled. |

## Završno, drugi krug: test 2 (jednom)

`holdout_runner --set eval/test2_set.json` za stanje posle B3 i za konačno stanje, u istom pokretanju i bez daljih izmena posle toga.

**Rezultat B4:** eval 12/12; holdout 33 → 34 (popravljen H13); viđeni test 1 22 → 21 (popravljen T06; pokvareni T04 „How much can I spend on conferences“ i T07 „Do I need my badge at every door?“). Kod T07 model piše odgovor („Yes, you need your badge at every entrance.“) umesto da prepiše reči, pa provera padne (5/8 reči). Kod T04 kaže NONE za „training budget of 800 EUR per year for courses, conferences“. Dakle, judge sa izvlačenjem greši **na drugim** pitanjima nego da/ne judge.

## B4b: unija dva judge-a

Proba na eval + holdout + test 1 (test 1 je ovde razvojni; slepi je test 2):

| Judge | eval | holdout | test 1 | Padovi |
| --- | --- | --- | --- | --- |
| izvlačenje (B4) | 12/12 | 34/34 | 21/24 | T02, T04, T07 |
| izvlačenje, uz odbacivanje „yes/no“ na početku | 12/12 | 34/34 | 21/24 | T02, T04, T07 |
| izvlačenje, upit „...or that directly help answer it“ | 12/12 | 34/34 | 21/24 | T02, T04, T07 |
| **da/ne (gemma3:4b) ILI izvlačenje (qwen2.5:7b)** | **12/12** | **34/34** | **23/24** | T02 |

| Polje | Sadržaj |
| --- | --- |
| Propust | B4 kvari T04 i T07, koje je B2 judge (da/ne) rešavao, a B2 judge kvari H13 i T06, koje B4 rešava. Tip: pogrešno odbijanje. |
| Hipoteza | Dva judge-a greše na različitim pitanjima (pogrešno odbijanje), a na eval, holdout i test 1 nijedan nije pogrešno prihvatio nepodržano pitanje u sivoj zoni. Ako pasus prolazi kada ga prihvati **bilo koji**, gube se greške odbijanja, a ne dobijaju greške prihvatanja. |
| Promena | `RERANK_JUDGE = "either"`: pasus prolazi ako da/ne judge (`RERANK_YESNO_MODEL = "gemma3:4b"`, B2 upit) **ili** judge sa izvlačenjem (`RERANK_MODEL = "qwen2.5:7b"`, B4 upit) kaže da odgovara. Da/ne judge se poziva samo kada izvlačenje kaže ne. |
| Očekivani efekat | eval 12/12, holdout 34/34, test 1 23/24. |
| Rizik regresije | Unija je blaža, pa svaka greška prihvatanja bilo kog judge-a prolazi. Dva LLM-a (8 GB ukupno). |
| Ostaje | **T02** „Does sick leave come out of my annual leave days?“ ↔ „Sick leave follows a separate policy.“ Isti pasus treba prihvatiti za T02, a odbiti za H25 („How many sick days do I get per year?“). Od 5 lokalnih modela tu razliku prave samo izvlačenje sa gemma3:4b (koje na eval-u pogrešno prihvata E11) i da/ne sa llama3.2 (koje pogrešno prihvata E11 i H25). Dodavanje trećeg judge-a samo zbog T02 značilo bi štimovanje sistema na jedno pitanje, pa to nije urađeno. |
| Provera | `pytest`, eval, holdout, test 1, `eval_compare` u odnosu na B4. |

**Rezultat B5:**
- Metrike su iste na eval, holdout i testu 1 (12/12, 34/34, 23/24).
- Odgovora sa rečima kojih nema u pasusima ni u pitanju sada je 4/49 (bilo je 35/49). Sve četiri reči su preformulacije: „make“, „submit“, „ordering/used/like“, „basis“.
- Ručni pregled svih 49 odgovora: svi su činjenično tačni, a nijedan nema izmišljen detalj. H10 sada kaže „must be approved before booking“.
- Novi problem su previše šturi odgovori: H03, T01 i T13 („No.“ / „Yes.“) i T14 („IT staff“). T11 je u pogrešnom licu („I agree...“), a T09 izostavlja „chat“.

## B5b: odgovor uvek navodi činjenicu

| Polje | Sadržaj |
| --- | --- |
| Propust | H03, T01 i T13 odgovaraju samo „Yes.“ ili „No.“, T14 samo „IT staff“, a T11 je u prvom licu. Tačno je, ali korisnik ne vidi činjenicu. Tip: kvalitet odgovora. |
| Hipoteza | Strog upit traži „one or two short sentences“, pa model skraćuje do kraja. Izričit zahtev da odgovor bude cela rečenica sa činjenicom iz pasusa, upućena korisniku („you“), uklanja gole „yes/no“ odgovore, a ne vraća izmišljanje. |
| Promena | Samo `GENERATION_PROMPT`: dodaje se „Always state the supporting fact from the passages in a full sentence addressed to the user as "you"; never reply with only yes or no.“ |
| Očekivani efekat | Nema golih „Yes.“ ili „No.“ odgovora; „fact in answer“ raste; odgovora sa nepodržanim rečima ostaje oko 4/49; eval i holdout metrike iste. |
| Rizik regresije | Duži odgovor može ponovo da doda detalje. |
| Provera | `answer_quality` za eval, holdout i test 1, ručni pregled, metrike identične B5. |
