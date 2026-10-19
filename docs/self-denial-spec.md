# Odgovor koji poriče sopstveni citat: specifikacija (napisana pre pregleda skupova)

## Propust

Eval meri ponašanje i činjenicu u citatu, ne rečenicu odgovora. Kod istorijskih pitanja (odeljak 23) četiri odgovora su imala tačan citat i rečenicu „The passage does not provide information …“. Eval ih je računao kao prolaz, a korisnik je dobio netačnu tvrdnju da odgovora nema.

## Promena (`SELF_DENIAL_CHECK`)

Nova provera u `generation_issue`: ako tekst odgovora (bez oznaka citata) tvrdi da izvor nema informaciju, a odgovor nije odbijen, generisani tekst se ne prikazuje. Umesto njega ide postojeći rezervni odgovor sa doslovnim citatom izvora (`fallback = "self_denial"`), isto kao kod pogrešnog broja ili citata.

Pravilo (zamrznuto u ovom commitu, pre pregleda):

```
does not (provide|mention|specify|state|contain|include|say)
| (is|are) not (stated|specified|mentioned|provided|given|included)
| cannot be (answered|determined)
| no information
| not enough information
| (doesn't|don't) (provide|mention|specify|say)
```

## Očekivani efekat

Pass/fail se ne menja (citati ostaju isti). Menja se tekst odgovora kod pogođenih pitanja: umesto netačne rečenice korisnik vidi doslovan citat.

## Rizik

Odgovor koji ispravno kaže da izvor nema jedan deo višedelnog pitanja, a drugi deo odgovara, biće zamenjen citatom. Citat sadrži sve što izvor kaže, pa se informacija ne gubi, samo se gubi lepša rečenica.

## Provera

Svi odgovori na svim skupovima iz keša, sa proverom isključenom i uključenom: broj pogođenih odgovora, ručni pregled svakog i pass/fail po skupu pre i posle.

## Rezultat: ostaje isključeno

Na 508 pitanja (svi registrovani skupovi) provera menja tekst samo kod 3 odgovora; pass/fail se ne menja nigde (`evidence/upgrade/selfdenial-all.json`).

| Pitanje | Očekivano | Generisan odgovor | Ocena |
| --- | --- | --- | --- |
| Y07 „What does next-day delivery cost?“ | odgovor (9 EUR) | „Next-day delivery is not mentioned“ | generator greši; citat je bolji |
| Y38 „How long does a refund take for a gift card purchase?“ | odbijanje | „does not specify the refund process for gift card purchases“ | generator je u pravu; sistem je trebalo da odbije |
| N21 „What happens to training funds when I change teams?“ | odbijanje | „does not provide information about … changes teams“ | generator je u pravu; sistem je trebalo da odbije |

Prikaz citata (po specifikaciji) popravlja Y07, ali kod Y38 i N21 briše tačnu napomenu i ostavlja nebitan citat. Pretvaranje u odbijanje popravilo bi Y38 i N21, ali pokvarilo Y07. Nijedna varijanta nije čista pobeda, pa `SELF_DENIAL_CHECK` ostaje `False`.

**Nalaz.** Kod dva od tri slučaja generator ispravno prepoznaje da odgovora nema. Problem pitanja bliskih domenu je dakle u proveravaču odlomka, koji prihvati srodan odlomak, a ne u generatoru. To je koristan pravac za sledeću nedelju: signal „generator kaže da nema informacije“ kao jedan od ulaza u odluku o odbijanju, uz poseban slepi skup.
