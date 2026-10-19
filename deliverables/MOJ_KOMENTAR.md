# Moj komentar, Nedelja 7

**Uroš Milutinović**

U obaveznom delu napravio sam jednu promenu: uključio sam filter koji iz pretrage izbacuje zastarele verzije dokumenata. Pre izmene sam zapisao specifikaciju sa očekivanim efektom i rizicima, a posle izmene ponovo pokrenuo istih 12 pitanja.

Rezultat je sa 6/12 porastao na 7/12 i nijedno pitanje nije palo. Na E06 sistem je ranije citirao politiku iz 2024. sa 2 dana rada od kuće, a sada citira važeću iz 2026. sa 3 dana. Proverio sam rezultate pre i posle, poređenje, diff, CLI odgovor i citate. Eval skup i kod za metrike su isti kao u početnom checkpointu.

Ograničenja su navedena u odeljku 8. Chunkovanje, parafraze i odbijanje pitanja bez odgovora u korpusu i dalje ne rade dobro. Filter ima i cenu, jer sistem sada ne može da odgovori kakva su bila stara pravila. Zaključak koji mogu da odbranim je da sam popravio izbor važeće verzije na E06, a za ostale probleme trebaju posebne promene i nova merenja.

Ceo rad sam uradio sam, uz AI asistenta u analizi, implementaciji i pisanju teksta, i sve rezultate i dokaze sam proverio. Napredne eksperimente sam odvojio od obaveznog M5 dela.
