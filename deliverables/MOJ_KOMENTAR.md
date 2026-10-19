# Moj komentar — Nedelja 7

**Uroš Milutinović**

U obaveznom delu uradio sam jednu promenu: uključio sam filter važeće verzije dokumenata. Pre izmene sam zapisao specifikaciju, očekivani efekat i rizike, a zatim sam implementirao promenu i proverio rezultat na istih 12 pitanja.

Rezultat je porastao sa 6/12 na 7/12, bez regresija na tom skupu. Na pitanju E06 sistem je ranije citirao zastarelu politiku sa 2 dana rada na daljinu. Posle promene citira važeću politiku iz 2026. sa 3 dana. Proverio sam rezultate pre i posle, poređenje, diff, CLI odgovor i citate. Evaluacioni skup i kod za metrike ostali su isti.

Ograničenja sam naveo u izveštaju. Ostaju problemi sa chunkovanjem, parafrazama i odbijanjem pitanja za koja nema odgovora u korpusu. Filter isključuje zastarele dokumente, pa ograničava i odgovaranje o istorijskim pravilima. Zato zaključujem da sam popravio izbor važeće verzije na dokumentovanom primeru, dok ostali problemi zahtevaju zasebne promene i nova merenja.

Celokupan rad uradio sam samostalno, uz pomoć AI asistenta u analizi, implementaciji i pripremi teksta. Lično sam proverio navedene rezultate i dokaze. Napredne eksperimente prikazao sam odvojeno od obaveznog M5 eksperimenta.
