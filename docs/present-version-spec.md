# Pitanja o važećoj verziji: specifikacija (napisana pre izmene koda)

**Polazni commit:** `842273a`.

## Propust

Y05 („What is the current return window?“), Y32 („Is the 14 day return period still valid?“) i Z06 („Has the current refund waiting period remained fourteen business days?“): pretraga nađe `sh-01`, ali proveravač odlomka ga odbije, pa sistem odbija odgovor. Pitanje traži važeću verziju, a proveravač ne vidi da je odlomak važeći.

## Raniji pokušaj

`VERSION_CONTEXT` (odeljak 21) davao je kontekst verzije svakom pitanju sa rečima kao current, now, still ili godinom. Popravio je Y05 i Z07, ali pokvario V25, pa je odbijen.

## Promena (`PRESENT_VERSION_CONTEXT`)

Kontekst verzije („Document: …; version: …; status: …“) dobija proveravač samo kada su ispunjena oba uslova:

1. pitanje ima reč sadašnjosti ili važenja (current, currently, now, today, still, in force, valid, remained, stayed);
2. najbolji kandidat pretrage pripada dokumentu koji postoji u više verzija.

Odgovor i generator se ne menjaju.

## Skupovi (zamrznuti pre koda, pokreću se jednom)

`eval/present_set.json` (handbook, 6) i `eval/present2_set.json` (corpus2, 6): po 4 pitanja o važećoj verziji, jedna kontrola na dokumentu sa jednom verzijom i jedno pitanje bez odgovora.

## Pravilo prihvatanja

Bez regresija. Pitanja van ovih skupova koja ulaze u novi režim mere se pojedinačno pre i posle (ostala ne mogu da se promene). Uključuje se samo uz popravke i bez ijedne regresije.

## Rezultat: odbijeno

Novi režim zahvata 20 postojećih pitanja (`evidence/upgrade/present-trigger-audit.json`). Pre i posle (`evidence/upgrade/present-selected.json`): popravljen Y05, pokvareni V25 i PS01 (slepi). Slepi skupovi present/present2 su sa trenutnim sistemom već 11/12. Promena ostaje isključena. Ovo je drugo nezavisno merenje (posle `VERSION_CONTEXT`, odeljak 21) koje pokazuje da kontekst verzije za proveravača kod pitanja o važećoj verziji kvari V25.
