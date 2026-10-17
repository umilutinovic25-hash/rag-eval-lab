# Šablon za izveštaj pre/posle: Nedelja 7

Šablon je napravljen prema zahtevima iz `weekly-assignment.md` (obavezni rezultat, kriterijumi prihvatanja, provera, pregled para i dokaz za predaju). Zvanični šablon nije bio dostupan. Popunite svaki odeljak; uglaste zagrade zamenite sadržajem.

---

# Nedelja 7: izveštaj pre/posle

**Par:** [ime i prezime] i [ime i prezime]  
**Demonstraciju na Sesiji 2 vodi:** [ime]  
**Promena:** [ID iz menija i kratak naziv, npr. M5 filter važeće verzije]  
**Commitovi / link:** [početno stanje] → [specifikacija] → [promena]  
**Datum:** [YYYY-MM-DD]

## 1. Početna provera

- `python -m pytest`: [broj] passed
- `python -m src.eval_runner --out results/before.json`: [X]/12
- `eval_set_sha256`: [hash]

```
[nalepiti tabelu i sažetak iz eval_runner-a]
```

## 2. Dokumentovani propusti (najmanje dva)

| ID | Očekivano | Dobijeno | Tip propusta |
| --- | --- | --- | --- |
| [E..] | [ponašanje, dokument, činjenica] | [šta je sistem uradio, citati i ocene] | [chunkovanje / retrieval / citat / pogrešan odgovor / pogrešno odbijanje] |
| [E..] | | | |

## 3. Specifikacija jedne promene

Napisana pre izmene koda: [commit ili fajl].

| Polje | Sadržaj |
| --- | --- |
| Propust | [ID pitanja i šta ne radi] |
| Hipoteza | [zašto se to dešava] |
| Promena | [tačno šta se menja i koje podešavanje] |
| Očekivani efekat | [koja pitanja i metrike treba da se promene] |
| Rizik regresije | [šta može da se pokvari] |
| Provera | [komande i očekivani rezultat] |

## 4. Primenjena promena

```diff
[git diff]
```

[Zašto je ovo jedna namera. Ako se menja više podešavanja, objasniti.]

## 5. Ponovno merenje

Ista komanda: `python -m src.eval_runner --out results/after.json`

```
[tabela i sažetak]
```

## 6. Poređenje

`python -m src.eval_compare results/before.json results/after.json`

```
[izlaz: Fixed, Regressed, Unchanged, Summary, Changed settings]
```

- Otisak eval skupa isti pre i posle: [da/ne]
- Upozorenje o više podešavanja: [nema / objašnjenje]

**Ručna provera CLI-jem** za jedno promenjeno pitanje ([ID]):

- Pre: [citati, verzija, odgovor]
- Posle: [citati, verzija, odgovor]
- Slaže se sa eval rezultatom: [da/ne]

## 7. Zaključak i regresije

- Hipoteza: [potvrđena / nije potvrđena], jer [dokaz iz merenja].
- Regresije: [ID i objašnjenje, ili „nema u eval skupu“ i promene koje se ne vide u metrikama].

## 8. Preostala ograničenja (najmanje jedno)

1. [ograničenje vezano za ID pitanja ili ponašanje]

## 9. Pregled para

Pregledao: [par / imena]. Komentar iz Discord niti „Nedelja 7: pregled para“:

1. Da li je promena zaista jedna i da li odgovara specifikaciji? [odgovor]
2. Da li rezultat pre/posle podržava zaključak? [odgovor]
3. Da li je neka regresija ili ograničenje izostavljeno? [odgovor]

Naš odgovor na komentar: [šta smo promenili ili zašto nismo]

## 10. Korišćenje AI-ja

- Za šta: [razumevanje koda, specifikacija, implementacija...]
- Kako je provereno: [koja merenja i ručne provere; tvrdnja asistenta nije dokaz]

## 11. Doprinos

| Član | Doprinos |
| --- | --- |
| [ime] | [šta je uradio] |
| [ime] | [šta je uradio] |

## 12. Napredni cilj (opciono, odvojeno od obaveznog dela)

[Druga promena izmerena u odnosu na rezultat posle prve, ili poređenje napredne tehnike uz trošak i zavisnosti.]

## Dokazi

- [before.json, after.json]
- [izlaz poređenja]
- [diff ili link na commit]
- [CLI izlazi]

## Kontrolna lista pre predaje

- [ ] `python -m pytest` prolazi posle promene
- [ ] Eval pokrenut pre i posle istom komandom
- [ ] Poređenje ne prijavljuje različit otisak eval skupa
- [ ] Oba propusta vezana za konkretna eval pitanja
- [ ] Specifikacija napisana pre izmene i promena joj odgovara
- [ ] Diff sadrži jednu promenu po nameri
- [ ] `eval/eval_set.json` i kod metrika nisu menjani
- [ ] Svaka regresija navedena i objašnjena
- [ ] Navedeno bar jedno preostalo ograničenje
- [ ] Ručna CLI provera jednog promenjenog pitanja
- [ ] Komentar para unet
- [ ] Beleška o AI-ju
- [ ] Doprinos oba člana i ime osobe koja vodi demonstraciju
- [ ] Nedeljni izveštaj poslat tutoru do utorka 20.10.2026. u 12:00 (`[Nedeljni izveštaj] Ime Prezime – Nedelja 7`)
