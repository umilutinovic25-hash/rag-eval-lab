# Nedeljni izveštaj — Nedelja 7

**Polaznik:** Uroš Milutinović  
**Projekat:** izvor. — kontrolisano poboljšanje RAG sistema  
**Način rada:** samostalan rad  
**Demonstraciju vodi:** Uroš Milutinović  
**Pregled para:** komentar drugog para nije dostavljen do roka; status u odeljku 9 izveštaja pre/posle

## Šta sam uradio

Analizirao sam propuste početnog RAG sistema, dokumentovao konkretna pitanja i izabrao jednu promenu za obavezni deo: filter važeće verzije dokumenata (M5, CURRENT_ONLY). Specifikaciju sam commitovao pre implementacije (2ceaced), a zatim sam implementirao promenu (45b8172). Moj doprinos obuhvata celokupan projekat, uz pomoć AI asistenta opisanu u izveštaju pre/posle.

## Rezultat i dokazi

Ponovio sam merenje na istih 12 pitanja i dobio poboljšanje sa 6/12 na 7/12, bez regresija. E06 sada pronalazi politiku iz 2026. sa 3 dana rada na daljinu umesto zastarele verzije sa 2 dana. Retrieval hit rate raste sa 0,7778 na 0,8889, a prosečna preciznost citata sa 0,4545 na 0,5455. Otisak skupa je isti pre i posle. Eval skup i kod metrika nisu menjani u odnosu na originalni checkpoint.

Paket sadrži pre/posle JSON, poređenje, diff, specifikaciju, testove (18 pre / 19 posle) i CLI izlaze za E06. Napredni rad u glavnom repou odvojen je od ovog eksperimenta i ne predstavlja dokaz jedne promene.

## Šta sam lično proverio i moj komentar

Lično sam proverio sve što je navedeno u izveštaju: dokumentovane propuste, specifikaciju i diff, rezultate pre/posle, poređenje, CLI odgovor i citate za E06, kao i navedena ograničenja. Rezultati podržavaju zaključak da filter rešava izbor zastarele politike na E06, a ne da rešava sve probleme sistema.

Ostaju problemi sa granicama chunkova, parafrazama, nepodržanim pitanjima i nebitnim dodatnim citatima. Filter otežava odgovaranje o istorijskim pravilima, što osnovni eval ne pokriva. To su ograničenja za naredne odvojene eksperimente.

## Korišćenje AI-ja

AI je pomagao u analizi, nacrtu specifikacije i izveštaja, implementaciji i pokretanju provera. Tekst ovog izveštaja pripremljen je uz pomoć AI-ja. Zaključke sam proverio prema sačuvanim rezultatima i kodu; moja potvrda nije nezavisni pregled drugog para niti pojedinačno označavanje odgovora na naprednim skupovima.

## Plan demonstracije za Sesiju 2

Prvo ću pokazati propust E06 i odgovor iz zastarele politike. Zatim ću prikazati specifikaciju (2ceaced), diff jedne promene (45b8172), rezultate pre/posle na istom skupu i CLI izlaz sa važećim citatom. Na kraju ću objasniti ograničenje istorijskih pitanja, preostale propuste i svoj doprinos.
