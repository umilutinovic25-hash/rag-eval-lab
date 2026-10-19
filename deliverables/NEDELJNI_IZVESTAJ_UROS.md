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

Proverio sam sve što je u izveštaju: propuste, specifikaciju i diff, rezultate pre i posle, poređenje, CLI odgovor i citate za E06 i ograničenja. Po mom mišljenju rezultati pokazuju da filter rešava izbor zastarele politike na E06, dok ostale probleme sistema rešavaju posebne promene opisane ispod.

Posle same M5 promene ostali su problemi sa granicama chunkova, parafrazama, pitanjima na koja korpus nema odgovor i nebitnim drugim citatom. Svaki sam rešio posebnom promenom i posebnim merenjem u naprednom delu, odvojeno od M5, i na zadatom eval skupu sistem sada prolazi svih 12 pitanja, sa preciznošću citata 1.00.

M5 filter je imao i cenu: sistem više nije mogao da odgovori kakva je bila stara politika, a osnovni eval to ne meri. To sam rešio filterom koji zavisi od pitanja. Na dva nova skupa rezultat je porastao sa 9/20 na 20/20, na dva nova slepa skupa je 16/16, a od postojećih pitanja promenilo se samo jedno, koje je ranije padalo, a sada prolazi. Na kraju sam pojačao zaštitu od napada (lažna premisa o izvoru, zahtevi za skrivenim tekstom): na novom slepom skupu napada rezultat je porastao sa 6/10 na 10/10, bez regresija.

Ostaje mali broj teških pitanja na dodatnim skupovima, na primer pitanja bliska domenu na koja korpus nema odgovor i dva pitanja o važećoj verziji. Za ova poslednja sam dva puta probao da proveravaču dam podatak o verziji i oba puta odbio promenu, jer je popravila jedno pitanje, a pokvarila dva. Dalje štimovanje na već viđenim pitanjima bilo bi preprilagođavanje, pa ih navodim kao ograničenje.

## Korišćenje AI-ja

AI mi je pomagao u analizi, pisanju nacrta specifikacije i izveštaja, implementaciji i pokretanju provera. I ovaj tekst sam pisao uz njegovu pomoć. Zaključke sam proverio sam, na sačuvanim rezultatima, u kodu i ručnim pokretanjem CLI-ja.

## Plan demonstracije za Sesiju 2

Počeću od propusta na E06, gde sistem odgovara iz zastarele politike. Onda ću pokazati specifikaciju (`2ceaced`), diff promene (`45b8172`), rezultate pre i posle na istom skupu (6/12 → 7/12) i CLI izlaz koji sada citira važeću verziju.

Posle toga ću ukratko pokazati napredni deo, gde sam svaki preostali propust rešio posebnom promenom i posebno ga izmerio: sečenje po rečenicama za E04 i E09 (7 → 9/12), viši prag odbijanja za E10 (9 → 10/12), semantička pretraga za E05 i E11 (10 → 12/12) i minimalna ocena citata (preciznost citata 1.00).

Na kraju ću objasniti cenu M5 filtera: sistem više nije mogao da odgovori kakva je bila stara politika. To sam rešio filterom koji poštuje verziju koju pitanje traži. Na dva nova skupa rezultat je porastao sa 9/20 na 20/20, na dva nova slepa skupa je 16/16, a od postojećih pitanja promenilo se samo jedno, Z07, koje je sa pogrešnog odbijanja prešlo na tačan odgovor. Ako bude vremena, pokazaću i pojačanu zaštitu od napada (6/10 → 10/10 na novom slepom skupu) i jednu promenu koju sam izmerio i odbio, jer je popravila jedno pitanje, a pokvarila dva.
