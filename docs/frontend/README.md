# izvor. — lokalni web radni prostor

## Pokretanje i rad

Iz korena projekta pokrenite `./start-web.command` i otvorite `http://localhost:8767`. Server ostaje aktivan dok je terminal otvoren; Ctrl+C ga zaustavlja. Na macOS-u skripta se može pokrenuti dvoklikom. Posle prvog build-a dovoljno je `.venv/bin/python -m src.web`. Port se može promeniti: `./start-web.command --port 8768`.

Prvo instaliranje npm paketa zahteva internet. Izgrađen interfejs koristi samo lokalne fontove, CSS, ikone, skripte i API. Postojeći keš omogućava tri engleska početna primera (izbor jezika English) i evaluaciju bez mreže ili model servera. Srpski ekstraktivni tok radi bez modela kada je izabran profil „Bez modela”. Modele aplikacija ne preuzima i ne pokreće sama.

Za nova pitanja u naprednom režimu potrebno je lokalno instalirati modele `bge-m3`, `qwen2.5:7b` i `gemma3:4b` i pokrenuti `ollama serve`. Status je dostupan kroz „Lokalni sistem”. Ako servisa ili modela nema, interfejs daje grešku i omogućava povratak pitanja u unos i izbor „Bez modela”. Taj profil ima slabiju leksičku pretragu, može uključiti dodatne nerelevantne odlomke i ne predstavlja kvalitet naprednog sistema. Pitanja mogu biti na engleskom ili srpskom, latinicom i ćirilicom. Izbor Auto prepoznaje najčešće srpske reči/pismo, a eksplicitni izbor Srpski/English otklanja dvosmislenost kratkih upita. Srpski odgovori su na latinici, kao prevedeni odlomci vezani za SHA-256 originala; originalni engleski citati i oznaka da prevod čeka ljudski pregled ostaju vidljivi. Napredni profil zadržava semantičku pretragu i judge; srpski tekst odgovora se ne parafrazira modelom. Auto/Srpski početni predlozi šalju stvarno srpsko pitanje, English njihove engleske verzije.

Svako pitanje obrađuje se nezavisno. Istorija razgovora nije kontekst modela. Browser čuva poslednjih 10 razgovora sa najviše 30 pitanja po razgovoru. Markdown izvoz čuva pitanje, odgovor, citate, verzije, profil i vreme. Statusni dijalog ima komandu za brisanje lokalne istorije. Osvežavanje stranice ne prekida pozadinski posao. Nedovršen zapis sa ID-jem posla ima „Proveri pozadinski posao”, koje nastavlja proveru istog zahteva bez ponovnog slanja. Posao je u memoriji servera i nestaje pri restartu ili isteku; tada je potrebno ponovo postaviti pitanje.

Istoriju je moguće pretražiti i pojedinačno ukloniti razgovor. Dugme „Vrati” vraća poslednji uklonjeni razgovor dok se obaveštenje ne zatvori, stranica ne osveži ili se ne ukloni drugi razgovor. Iz panela citata „Ceo dokument” otvara pravi dokument i označava citirani odlomak; „Nazad na razgovor” ostaje vidljiv pri skrolovanju. Kopiranje odlomka uključuje originalni tekst, naslov, verziju i oznaku izvora. Tokom novog zahteva panel prikazuje stanje obrade tog pitanja, a pri grešci daje uputstvo za oporavak. Oštećeni pojedinačni zapisi u browseru ne uklanjaju ostalu ispravnu istoriju.

Istorija v2 koristi Web Locks za read/merge/write i `storage` događaje za automatsko osvežavanje drugih tabova istog origin-a. Stari nizovi v1 se čitaju i migriraju pri sledećem upisu. Spajanje koristi ID razgovora i ID pitanja: dva nova razgovora ili dva paralelna pitanja u istom razgovoru ostaju sačuvani. Oznake brisanja sprečavaju oživljavanje iz zastarelog taba, a „Vrati” izričito vraća uklonjeni razgovor. Ako browser nema Web Locks ili zabrani skladištenje, razgovor ostaje u memoriji uz upozorenje za izvoz. Posle ažuriranja osvežiti stare tabove da svi koriste isti format. `localhost` i `127.0.0.1` imaju odvojene istorije jer su različiti origin-i.

Iznad unosa se vidi da li se istorija još čuva ili je sačuvana. Dok postoje nesačuvane promene, napuštanje stranice aktivira standardno upozorenje browsera. Treba sačekati potvrdu čuvanja pre osvežavanja; prinudno zatvaranje browsera ili procesa i dalje može izgubiti nesačuvane promene.

API odgovori se proveravaju pre prikaza, uključujući odlomke i evaluacione rezultate. Neispravna struktura daje poruku za oporavak. Izvori prikazuju stvarni status dokumenta; promena pretrage ili filtera verzije zatvara prethodni izbor dokumenta. Nedostupna preciznost citata (`null`) ostaje „—” i ne tumači se kao dokaz pogrešnih citata.

## Funkcionalne celine

- Razgovor: unos preko Enter, novi red preko Shift+Enter, SR/EN jezik, primeri, faze obrade sa servera, otkazivanje, nastavak postojećeg posla, izvoz i kopiranje, vidljive greške, rezervni ekstraktivni odgovor i odbijanje bez dokaza.
- Izvori: numerički markeri otvaraju tačan originalni odlomak; prikaz verzije i statusa, tok odluke i pronađeni kandidati. Sličnost nije predstavljena kao procenat pouzdanosti. Izvorni citati su prikazani odvojeno od generisanog teksta, bez izmene sadržaja API odgovora/izvoza.
- Dokumenti: pretraga teksta, filter aktuelnih i arhiviranih verzija, originalni tekst i odlomci. Stara politika iz 2024. ostaje dostupna za poređenje, isključena iz odgovaranja.
- Evaluacija: 12/12, 34/34, 23/24 i 29/32; filter neuspeha i razlog neuspeha. Dugme za ponavljanje poziva postojeći runner u režimu `replay`; stvarne metrike, bez poziva modelima. JSON izvoz uključuje identitet skupa, koda/keša, commit i status radne kopije.

Preciznost citata u originalnoj metrici meri očekivani dokument, ne dokazuje tačnost svake tvrdnje. Četiri preostala neuspeha nisu uklonjena niti sakrivena ovim interfejsom. Keširan izlaz nije dokaz svežeg generisanja, a testni skupovi su ranije viđeni. Aplikacija je lokalni demo za jednog korisnika; server nema javni hosting, autentifikaciju niti trajni produkcioni sistem poslova. Zahtevi se serijalizuju zato što postojeći CLI koristi globalnu konfiguraciju.

## Struktura i ugovori

- `frontend/src/`: React, TypeScript, lokalni DM Sans, CSS tokeni, Lucide SVG ikone. Sav vidljivi interfejs je HTML/CSS; koncept PNG se ne koristi kao UI.
- `src/web.py`: standardna Python biblioteka, bez novih runtime paketa. Služi samo frontend build i eksplicitne API putanje, vezan za `127.0.0.1`. Provera Host/Origin, ograničenje veličine JSON-a i pitanja, sprečavanje izlaska iz static direktorijuma, CSP i bez logovanja sadržaja pitanja.
- `GET /api/status`, `GET /api/documents`, `GET /api/evaluations`.
- Status računa ukupan broj dokumenata i aktuelnih verzija iz učitanog korpusa, bez fiksnih brojeva.
- `POST /api/chat`: kompatibilni sinhroni API, `{ "question": "...", "profile": "current" | "offline", "language": "auto" | "sr" | "en" }`.
- `POST /api/jobs`: isti unos, odmah vraća 202 i nepredvidiv ID posla. `GET /api/jobs/<id>` vraća fazu, proteklo vreme i rezultat; `POST /api/jobs/<id>/cancel` zahteva kooperativno otkazivanje. ID nije trajni nalog niti produkciona autentifikacija.
- Jedan worker, najviše 16 nezavršenih poslova, ograničen red, zadržavanje do 64 završenih poslova i TTL 15 minuta, rok obrade 5 minuta uključujući čekanje. Pun red vraća 429; istekao/nepoznat posao 404. Otkazivanje ne prekida nasilno već otvoreni HTTP poziv Ollama-i; sledeći korak se ne pokreće, a rezultat otkazanog zahteva se ne objavljuje. Faze i trajanja su opaženi podaci, bez izmišljenog procenta napretka.
- `data/runtime/` sadrži zasebne web keševe, inicijalno kopirane iz istorijskih; novi upiti ne prepisuju istorijske dokaze. Jedna instanca servera koristi taj direktorijum. `data/sr-handbook.json` je dodatni prevod, a originalni korpus nije menjan.
- `POST /api/evaluations/run`: `{}`. Ponavlja sve četiri evaluacije iz keša; rezultat se vraća browseru, istorijski dokaz se ne prepisuje.
- Profil se primenjuje pod zajedničkim zaključavanjem i konfiguracija se vraća u `finally`, uključujući greške i paralelne zahteve. Replay koristi isti lock. Dokumenti su snimak pripremljen pri startu servera i mogu se čitati dok model obrađuje zahtev; status takođe ostaje dostupan. Posle izmene korpusa server treba restartovati.

Za razvoj pokrenuti API na 8767 i `npm --prefix frontend run dev`. Vite na loopback-u prosleđuje API i prilagođava lokalni Host/Origin. Proizvodni server prihvata isključivo isti lokalni origin, bez CORS dozvola za tuđe sajtove.

## Ponovljiva provera

```bash
.venv/bin/python -m pytest -q
npm --prefix frontend ci
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run format:check
cd frontend
npx playwright install chromium --only-shell  # samo za browser testove
npm run test:e2e
npm audit
```

Browser testovi pokreću lokalni Python server ako već nije aktivan i koriste keš; ne zahtevaju Ollama. Testovi pokrivaju odgovor/citat, nezavisno odbijanje, izvoz, verzije dokumenata, neuspešne evaluacije, pravi replay, offline profil, istoriju i tri širine ekrana. Posebne regresije pokrivaju neispravne API strukture, uklanjanje zastarelog izbora dokumenta, objašnjenje odbijanja bez citata automatsko spajanje dva taba, paralelna pitanja u istom razgovoru, brisanje/undo, srpsku ćirilicu, nastavak posla i simulirani spori posao sa otkazivanjem. Stvarni backend otkazivanja, ograničenja reda i rokovi proveravaju se Python testovima. Axe provera obuhvata automatizovane WCAG A/AA kriterijume na početnom ekranu i testiranim ekranima razgovora, dokumenata, evaluacije i statusnog dijaloga; ona ne predstavlja potpunu potvrdu pristupačnosti.

Originalni `eval/eval_set.json`, `src/eval_runner.py`, `src/eval_compare.py`, corpus i istorijski keš nisu menjani radi web interfejsa. Specifikacija M5, njen dokaz i arhiva ostaju izdvojeni.

Vizuelni koncept, provera i odstupanja: [design-review.md](design-review.md).

## Dopunski kandidatski skup i pregled

`review/acceptance-v2.json` ima 24 jezičke varijante za 12 slučajeva, zamrznute pre implementacije i zaštićene `.sha256` otiskom. Autor je asistent; nema nezavisne ljudske potvrde. Rezultati su 19/24 automatskih provera u offline profilu i 23/24 u naprednom profilu. Drugi rezultat uključuje 24 nova embedding i 46 LLM poziva, uz keš prethodnih eksperimenata; nije potpuno cold merenje. Jedini napredni pad je podniz „ličnu karticu” naspram odgovora „lična kartica”, za ljudsku procenu. Skup i pragovi nisu prepravljani da bi se taj broj podigao.

```bash
.venv/bin/python -m src.acceptance_runner --profile current --mode replay --cache-dir evidence/next/candidate-cache --out results/acceptance-replay.json
```

`review/acceptance-v2-review-template.json` vezuje stvarne odgovore i skup njihovim hash-evima. Stvarni recenzent upisuje ime, odluku i komentar za svaku stavku, u posebnoj kopiji. Opcija `--review putanja.json` proverava kompletnost i identitet procenjenih odgovora; ne potvrđuje identitet osobe niti pretvara ovaj razvojni skup u nezavisan slepi test. Neizvršena ljudska provera ostaje eksplicitno neizvršena.
