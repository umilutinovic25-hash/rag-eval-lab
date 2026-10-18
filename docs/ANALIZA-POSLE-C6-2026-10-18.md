# Analiza posle C1–C6: sledeća poboljšanja

Datum: 18.10.2026. Polazni commit: `f430863`. Skillovi: `ai-evidence-review` i `llm-evaluation`.

Nisu menjani kod, konfiguracija, zaključani skupovi, keševi ili istorijski rezultati. Ovaj pregled sadrži dijagnozu i predlog eksperimenata, ne tvrdnju da su predložena poboljšanja implementirana. Sve oznake test pitanja sada su viđene; ovaj pregled nije slepo testiranje.

## 1. Provereno stanje

- Svež `python -m pytest -q`: **107 passed**.
- Poslednji manifest C6 beleži replay: 12/12 eval, 34/34 holdout, 23/24 test1, 29/32 test2. U ovom pregledu nisu ponovo pokretani modeli uživo.
- Ponovo su pročitani keširani odgovori za preostale padove i jedan nepotpun PASS odgovor.
- Determinističke probe: `python evidence/audit2-2026-10-18/probe.py`.
- Stvaran izlaz: `evidence/audit2-2026-10-18/output.txt`.

Statusi: sintetički primeri su dokaz o granicama koda, ne dokaz da je model takve odgovore zaista proizveo uživo. Lokalna simulacija cold rada ne kontaktira Ollama.

## 2. Najvažniji nalaz: retrieval već nalazi očekivani dokaz

| Pad | Položaj pasusa sa referentnom činjenicom u top-5 | Keširani span odgovor | Keširani yes/no odgovor |
| --- | --- | --- | --- |
| T02 | 2 | NONE | No. |
| U07 | 1 | per person | No. |
| U11 | 1 | NONE | No. |
| U13 | 2 | NONE | No. |

To direktno sužava dijagnozu: za ova četiri slučaja dokaz nije van skupa kandidata. Problem je u odgovorljivosti, formatu dokaza i izboru citata. Menjanje embedding modela ili dodavanje vektorske baze nije prvi korak koji nalazi opravdavaju.

U07: span model koristi semantički ispravnu parafrazu „per person“, ali to nisu doslovne reči pasusa „Each employee...“, pa stroga provera odbacuje rezultat. Ne treba zbog ovog pitanja ponovo dozvoliti netačno prepisivanje. Odlučivanje da li izvor podržava odgovor i doslovno izdvajanje dokaza jesu različiti zadaci.

U13: sistem odgovara, ali izbacuje pasus sa „up to 3 days per week“. Potrebna je kontrola potpunosti/potkrepljenosti, ne samo broj odbijanja.

## 3. PASS može da bude nepotpun odgovor

**Stvaran keširani primer H20:**

Pitanje: „Where do I order a new headset?“

Odgovor: „You order a new headset through the same form used for ordering accessories like a mouse.“ Citira samo `hb-01-chunk-3`: „...ordered through that same form.“

Korisnik nije saznao gde je formular. Prethodni chunk, `hb-01-chunk-2`, sadrži „IT portal under Hardware“. Postojeća referentna činjenica za H20 je „ordered through that same form“, pa odgovor prolazi iako je mesto formulara izostavljeno.

**Zaključak:** prvo treba dopuniti značenje dodatne procene kvaliteta. Ne menjati originalni eval skup. U odvojenom referentnom fajlu navesti obavezne činjenice po delovima odgovora, na primer:

| Pitanje | Potrebne činjenice u zasebnoj proveri potpunosti |
| --- | --- |
| E09 | IT portal / Hardware i do 5 business days |
| H20 | lokacija formulara u IT portalu / Hardware i veza sa naručivanjem dodatne opreme |
| U17 | kraj prvog meseca i posle tri meseca |
| U13 | ograničenje do tri dana, pa četiri nisu dozvoljena po navedenom pravilu |

U17 trenutno daje oba termina; primer je predlog kako uhvatiti buduće izostavljanje, ne dodatni otkriveni pad.

T02 je potrebno nezavisno anotirati: „Sick leave follows a separate policy“ nije detaljno pravilo o tome kako se odsustva računaju. Da li to dovoljno podržava kategoričko „ne umanjuje annual leave“ mora da odluči ljudski reviewer. Nije opravdano silom dovesti PASS za dvosmislenu oznaku.

## 4. Preostale granice formalnih zaštita

### P1 — Ista cifra nije isti iskaz

`src/rag.py:49`, `generation_issue` pravilno dokumentuje da radi strukturne i numeričke provere. Posle C2 odbija novi broj 900, ali sledeći sintetički odgovori i dalje prolaze bez upozorenja kada izvor kaže „Passwords must be changed every 90 days“:

- „Passwords must be changed every 90 years [a].“
- „Do not change passwords every 90 days [a].“
- „Passwords must be changed every ninety years [a].“

C2 time nije opovrgnut: obećava proveru markera i novih cifara, ne semantičku garanciju. Sledeća granica je veza **činjenica–jedinica–uslov–negacija**, vezana uz konkretan citat. Broj u bilo kom izabranom pasusu nije dovoljan dokaz za svaku tvrdnju koja ga koristi.

Predlog: eksplicitni strukturisani odgovor sa tvrdnjama i pripadajućim dokazom, dodatne provere jedinica/negacije, a zatim nezavisan pregled. Takav format olakšava proveru, ali sam JSON ne garantuje istinitost.

### P2 — Prekinuti odgovor se ne razlikuje od završenog

`src/llm.py:27` preuzima samo `response`; ignoriše `done_reason`. Simuliran serverski odgovor sa `done_reason="length"` i tekstom „According to [a], you may“ prolazi i `request_generation` i `generation_issue`.

Predlog: sačuvati razlog završetka i broj izlaznih tokena. Za generisanje odgovora prekinut izlaz zameniti izvornim tekstom. Za kratki judge sa tri tokena potreban je drugačiji ugovor: validirati ceo dozvoljeni odgovor, ne automatski odbacivati svaki završetak na ograničenju.

### P2 — Globalna negacija rečenice može odbaciti ispravan lokalni dokaz

`src/llm.py:62` odbija span „parking costs 10 EUR“ iz „No annual fee applies; parking costs 10 EUR.“ zato što ista rečenica sadrži „No“ za drugi iskaz.

Ovo je sintetički lažni negativni rezultat. C1 je svesno konzervativan i ne treba ga oslabiti samo da prođe ovaj primer. Sledeći korak je dokaz sa punim kontekstom ili preciznije granice iskaza, uz testove da se „Never“ i „not“ ne izgube. Doslovni citat i semantička potkrepljenost ostaju odvojeni.

### P3 — Konačni ulazi ipak mogu izazvati numerički overflow

`src/embeddings.py:100`: `cosine([1e308], [1e308])` vraća NaN zbog preliva pri množenju. Ulazni brojevi su konačni, pa C3 ulazna validacija ne odbija primer. Realni keširani embedding vektori nisu ovakvih razmera; prioritet je niži od problema odgovorljivosti.

Predlog: stabilno normiranje pre skalarnog proizvoda i provera konačnog izlaza. Izmeriti da normalni embedding vektori ne menjaju rangiranje.

## 5. Cold eksperiment nije dovoljno dijagnostičan

`src/experiment_runner.py:65` beleži pokušaje poziva i metrike, ali ne broj uspešnih generisanja, grešaka, razloga fallback-a niti tekst generisanog odgovora. Originalne eval metrike to ne sadrže.

**Simulirana proba:** preflight prijavljuje dostupan lokalni server; sva četiri pokušaja generisanja zatim padaju. Rag vraća izvorne pasuse. Eksperiment završava uz četiri LLM poziva i bez eksplicitnog broja uspeha/neuspeha u manifestu. Fallback je dobro ponašanje za korisnika, ali takav rezultat nije dokaz kvaliteta LLM generisanja.

Pored toga, cold keševi se nalaze u TemporaryDirectory i brišu na izlazu. Hash ostaje u manifestu, ali odgovor modela nije sačuvan u rezultatima, pa nema dovoljno sirovog materijala za naknadni pregled.

Predlog: sačuvati tekst odgovora, izabrani kontekst, razloge odluka, uspešne i neuspešne pozive, fallback stopu i model identitet. Keš ili minimalne sirove odgovore hladnog eksperimenta trajno vezati uz ID tog eksperimenta. Zatim uraditi jednu stvarnu fresh-generaciju, bez biranja modela po novom rezultatu. Ovaj pregled to nije izvršio.

## 6. Jednostavna optimizacija: zaustaviti proveru kada postoje dva prihvaćena kandidata

`src/rag.py:82` pravi celu listu prihvaćenih pasusa pa je tek onda skraćuje na TOP_K.

Sintetička proba sa pet prihvaćenih kandidata i TOP_K=2: **pet poziva judge-a za dva izabrana citata**. Ako se redosled i pojedinačne odluke ne menjaju, petlja može stati posle drugog prihvaćenog pasusa i dati isti izbor uz dva poziva. Ako se kandidati odbijaju, i dalje se proverava do pet.

Ovo je najjednostavnija naredna promena za brzinu. Dokaz prihvatanja: identični kompletni rezultat i citati na sva četiri skupa; testirani redosled poziva; manji broj poziva kada su prvi kandidati prihvaćeni. Broj poziva judge-a nije isto što i broj poziva modela, jer either može da pozove jedan ili dva modela, a keš može ukloniti oba mrežna poziva.

## 7. Predlog narednih kontrolisanih koraka

| Redosled | Promena | Šta meriti | Rizik i kriterijum odluke |
| --- | --- | --- | --- |
| D1 | rano zaustavljanje judge provere | broj odluka/model poziva i vreme; identični rezultati | ne menjati redosled kandidata; nema regresija u kompletnim redovima |
| D2 | trag odluka i potpun zapis cold eksperimenta | kandidati pre/posle filtera, razlozi, tekst odgovora, prekid, greške i fallback | originalne metrike ne menjati; proveriti i otkaz servera |
| D3 | dodatne referentne činjenice i ljudski rubric za potpunost | broj tačno pokrivenih delova pitanja, negativne i dvosmislene tvrdnje | reference treba da odobri drugi par; nema menjanja originalnog evala |
| D4 | kontrolisano proširenje susednim chunk-om iz iste važeće verzije | H20 lokacija formulara, višedelna pitanja, nepodržani odgovori i broj tokena | više konteksta dodaje šum; ne spajati verzije ili dokumente |
| D5 | strukturisana provera podržava/protivreči/nema dovoljno dokaza | U07/U11/U13 tipovi upita, oznake dokaza i novi lažni odgovori | negativan odgovor treba razlikovati od nepodržanog pitanja; novo nezavisno merenje |
| D6 | zaštita jedinica, negacije i prekida izlaza | promena 90 dana→godina, promena zabrane/dozvole, prekinut odgovor | leksičke heuristike nisu semantički sud; meriti i lažna odbijanja |

D4 je naročito opravdan H20 primerom, ali ne obećava da će rešiti U07 i U11: njihov očekivani odgovor je već u jednom pasusu. D5 zato mora biti zaseban eksperiment.

## 8. Šta ne bih sada dodavao

- Novu vektorsku bazu: za četiri preostala pada očekivani dokaz je u top-2, a korpus ima samo deset dokumenata.
- Još lokalnih modela pre merenja troška i grešaka postojećih poziva.
- Još jedan asistentov test skup koji bi se predstavljao kao nezavisna ljudska validacija.
- Tvrdnju da svaki rezultat 100% PASS znači tačan i potpun korisnički odgovor.

Za predaju ostaje dovoljno izdvojen obavezni M5; sva dalja poboljšanja pripadaju naprednom dodatku. Stvarne doprinose, vođu demonstracije i komentar para i dalje moraju dati ljudi.

## Ishod pregleda

Potvrđeno: C1–C6 imaju prolazne testove, ali preostaju granice značenja, potpunosti, telemetrije i nekoliko rubnih ulaza. Nisu testirani novi modeli uživo, nije izvedeno novo slepo poređenje i nijedna predložena izmena nije implementirana u ovom pregledu. Dodati su samo ovaj dokument, reproduktivne probe i njihov stvaran izlaz.
