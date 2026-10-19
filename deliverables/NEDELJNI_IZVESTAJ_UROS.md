# Nedeljni izveštaj, Nedelja 7

**Polaznik:** Uroš Milutinović  
**Projekat:** izvor. (kontrolisano poboljšanje RAG sistema)  
**Način rada:** samostalno  
**Demonstraciju vodi:** Uroš Milutinović  
**Pregled para:** projekat sam poslao drugom polazniku na pregled (odeljak 9 izveštaja pre/posle)

## Šta sam uradio

Prošao sam kroz propuste početnog sistema i za svaki zapisao konkretno pitanje iz eval skupa. Za obavezni deo izabrao sam M5, filter važeće verzije dokumenata (`CURRENT_ONLY`). Specifikaciju sam commitovao pre bilo kakve izmene koda (`2ceaced`), pa tek onda implementirao promenu (`45b8172`). Ceo projekat sam radio sam, uz AI asistenta kako je opisano u izveštaju.

## Rezultat i dokazi

Na istih 12 pitanja rezultat je porastao sa 6/12 na 7/12, bez regresija. Na E06 sistem je ranije vadio staru politiku iz 2024. sa 2 dana rada od kuće, a sada vadi važeću iz 2026. sa 3 dana. Retrieval hit rate je sa 0,7778 porastao na 0,8889, a prosečna preciznost citata sa 0,4545 na 0,5455. Otisak eval skupa je isti pre i posle, a eval skup i kod za metrike nisam dirao.

U paketu su JSON rezultati pre i posle, izlaz poređenja, diff, specifikacija, izlazi testova (18 pre, 19 posle) i CLI izlazi za E06. Napredne eksperimente držim odvojeno u glavnom repou, jer nisu deo ove jedne promene.

## Šta sam proverio i moj komentar

Proverio sam sve što je u izveštaju: propuste, specifikaciju i diff, rezultate pre i posle, poređenje, CLI odgovor i citate za E06 i ograničenja. Po mom mišljenju rezultati pokazuju da filter rešava izbor zastarele politike na E06. Ostale probleme sistema ne rešava.

I dalje ostaju problemi sa granicama chunkova, parafrazama, pitanjima na koja korpus nema odgovor i nebitnim drugim citatom. Filter ima i cenu: posle M5 sistem više ne može da odgovori kakva je bila stara politika, a osnovni eval to ne meri. Svaki od ovih problema traži posebnu promenu i novo merenje, pa sam ih rešavao u naprednom delu, odvojeno od M5. Istorijska pitanja sam na kraju rešio filterom koji zavisi od pitanja: na dva nova skupa rezultat je porastao sa 9/20 na 18/20, bez regresija na postojećim pitanjima.

## Korišćenje AI-ja

AI mi je pomagao u analizi, pisanju nacrta specifikacije i izveštaja, implementaciji i pokretanju provera. I ovaj tekst sam pisao uz njegovu pomoć. Zaključke sam proverio sam, na sačuvanim rezultatima, u kodu i ručnim pokretanjem CLI-ja.

## Plan demonstracije za Sesiju 2

Počeću od propusta na E06, gde sistem odgovara iz zastarele politike. Onda ću pokazati specifikaciju (`2ceaced`), diff promene (`45b8172`) i rezultate pre i posle na istom skupu, pa CLI izlaz koji sada citira važeću verziju. Na kraju ću objasniti zašto M5 filter gubi istorijska pitanja, kako sam to rešio filterom koji poštuje traženu verziju (9/20 → 18/20) i koji propusti ostaju posle ove jedne promene. Ukratko ću pokazati i kako sam ih rešio u naprednom delu, gde je svaka promena merena posebno: sečenje po rečenicama (7 → 9/12), viši prag odbijanja (9 → 10/12), semantička pretraga (10 → 12/12) i minimalna ocena citata (preciznost citata 1.00).
