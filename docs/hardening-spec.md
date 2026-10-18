# Ispravke posle analize — 18.10.2026.

Polazna verzija: 2e24944. Dokazi: evidence/hardening/*-before.json.

Svaki korak ima jednu nameru; konfiguracija modela i zaključani eval skupovi ostaju isti.

| Korak | Propust / promena | Hipoteza i očekivanje | Rizik / provera |
| --- | --- | --- | --- |
| C1 | 80% preklapanja prihvata 900 umesto 800 i uklanjanje Never. Zahtevati kontinualan niz tokena iz rečenice izvora, uz očuvanje njene negacije. | Oba sintetička slučaja moraju biti odbijena. | Više odbijanja parafraza: ponoviti sva 4 skupa iz keša i prijaviti svaki pad. Ovo ne proverava odgovorljivost pitanja. |
| C2 | Nevalidirani markeri, prazan odgovor i izmišljeni Source redovi. Pre prikaza proveriti tekst i reference; ako ne prolaze, prikazati izvlačenje iz citiranih pasusa. | Nema prikaza nepostojećeg markera; ne menjati izbor citata. | Formalna validacija ne garantuje istinitost; lažni model u testu, sva 4 skupa. |
| C3 | Različite dimenzije, nebrojčani elementi i NaN nisu provereni. Validirati vektore, strukturu keša i prazan izlaz LLM-a. | Jasne greške umesto lažnog kosinusa. | Stari neispravni keš se odbija; negativni testovi, svi validni keševi i postojeći testovi. |
| C4 | Lexical sam ne isključuje modele. Dodati CLI profil offline koji zajedno bira lexical, bez reranka i extractive; prazno pitanje odbiti bez modela. | Novi upit radi bez keša/modela u offline profilu. | Podrazumevani model profil ostaje isti; test mrežne zabrane i subprocess CLI. |
| C5 | answer_quality skriva odbijene upite i ne detektuje negaciju; test2 nije dostupan. Dodati pokrivenost svih upita, heurističke rizike brojeva/negacije i eksplicitno neocenjenu semantičku tačnost. | Sintetička kontradikcija označena za pregled, imenilac uključuje odbijene upite. | Heuristike daju lažne alarme, nisu semantički sudija; originalne metrike se ne menjaju. |
| C6 | Nedostaje manifest i precizna dokumentacija. Zapisati hash kodova/korpusa/keša/upita, konfiguraciju, režim replay i opcioni identitet lokalnih modela; upakovati minimum zasebno. | Rezultati se mogu povezati sa tačnim ulazima; keš se ne predstavlja kao novo generisanje. | Digest istorijskih keševa nije dokaz istorijskog modela: obeležiti unknown. Ne izmišljati ljudsku proveru ni doprinose. |

Ne povećavati PASS brojeve slabljenjem provera. Preostali padovi i ljudske obaveze ostaju eksplicitni. Novi cold-run modela nije neophodan za popravku ovih determinističkih provera i nije deo ovog eksperimenta.
