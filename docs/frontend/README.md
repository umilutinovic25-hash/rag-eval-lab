# izvor. — lokalni web radni prostor

## Pokretanje i rad

Iz korena projekta pokrenite `./start-web.command` i otvorite `http://localhost:8767`. Server ostaje aktivan dok je terminal otvoren; Ctrl+C ga zaustavlja. Na macOS-u skripta se može pokrenuti dvoklikom. Posle prvog build-a dovoljno je `.venv/bin/python -m src.web`. Port se može promeniti: `./start-web.command --port 8768`.

Prvo instaliranje npm paketa zahteva internet. Izgrađen interfejs koristi samo lokalne fontove, CSS, ikone, skripte i API. Postojeći keš omogućava sva tri početna primera i evaluaciju bez mreže ili model servera. Modele aplikacija ne preuzima i ne pokreće sama.

Za nova pitanja u naprednom režimu potrebno je lokalno instalirati modele `bge-m3`, `qwen2.5:7b` i `gemma3:4b` i pokrenuti `ollama serve`. Status je dostupan kroz „Lokalni sistem”. Ako servisa ili modela nema, interfejs daje grešku i omogućava povratak pitanja u unos i izbor „Bez modela”. Taj profil ima slabiju leksičku pretragu, može uključiti dodatne nerelevantne odlomke i ne predstavlja kvalitet naprednog sistema. Pitanja se postavljaju na engleskom; srpski početni predlozi šalju odgovarajuće englesko pitanje i ono je vidljivo u razgovoru.

Svako pitanje obrađuje se nezavisno. Istorija razgovora nije kontekst modela. Browser čuva poslednjih 10 razgovora sa najviše 30 pitanja po razgovoru. Markdown izvoz čuva pitanje, odgovor, citate, verzije, profil i vreme. Statusni dijalog ima komandu za brisanje lokalne istorije. Prekid zahteva osvežavanjem stranice ne prekida već započetu lokalnu obradu; nedovršen zapis je označen za ponovno slanje.

Istoriju je moguće pretražiti i pojedinačno ukloniti razgovor. Dugme „Vrati” vraća poslednji uklonjeni razgovor dok se obaveštenje ne zatvori, stranica ne osveži ili se ne ukloni drugi razgovor. Iz panela citata „Ceo dokument” otvara pravi dokument i označava citirani odlomak; „Nazad na razgovor” ostaje vidljiv pri skrolovanju. Kopiranje odlomka uključuje originalni tekst, naslov, verziju i oznaku izvora. Tokom novog zahteva panel prikazuje stanje obrade tog pitanja, a pri grešci daje uputstvo za oporavak. Oštećeni pojedinačni zapisi u browseru ne uklanjaju ostalu ispravnu istoriju.

Upis istorije koristi Web Locks i proveru prethodno učitane verzije. Ako drugi tab promeni istoriju, zastareli tab prikazuje upozorenje i čuva razgovor u memoriji za izvoz; ne prepisuje sačuvanu istoriju. Pre osvežavanja tog taba treba preuzeti njegov razgovor. Ovo je zaštita od konflikta, a automatsko spajanje razgovora između tabova nije implementirano. Ako browser nema Web Locks ili zabrani skladištenje, razgovor radi u memoriji uz upozorenje da se preuzme. Posle ažuriranja aplikacije osvežiti otvorene tabove da svi koriste ovu zaštitu.

Iznad unosa se vidi da li se istorija još čuva ili je sačuvana. Dok postoje nesačuvane promene, napuštanje stranice aktivira standardno upozorenje browsera. Treba sačekati potvrdu čuvanja pre osvežavanja; prinudno zatvaranje browsera ili procesa i dalje može izgubiti nesačuvane promene.

API odgovori se proveravaju pre prikaza, uključujući odlomke i evaluacione rezultate. Neispravna struktura daje poruku za oporavak. Izvori prikazuju stvarni status dokumenta; promena pretrage ili filtera verzije zatvara prethodni izbor dokumenta. Nedostupna preciznost citata (`null`) ostaje „—” i ne tumači se kao dokaz pogrešnih citata.

## Funkcionalne celine

- Razgovor: unos preko Enter, novi red preko Shift+Enter, primeri iz keša, stanje obrade, izvoz i kopiranje, vidljive greške, rezervni ekstraktivni odgovor i odbijanje bez dokaza.
- Izvori: numerički markeri otvaraju tačan originalni odlomak; prikaz verzije i statusa, tok odluke i pronađeni kandidati. Sličnost nije predstavljena kao procenat pouzdanosti. Izvorni citati su prikazani odvojeno od generisanog teksta, bez izmene sadržaja API odgovora/izvoza.
- Dokumenti: pretraga teksta, filter aktuelnih i arhiviranih verzija, originalni tekst i odlomci. Stara politika iz 2024. ostaje dostupna za poređenje, isključena iz odgovaranja.
- Evaluacija: 12/12, 34/34, 23/24 i 29/32; filter neuspeha i razlog neuspeha. Dugme za ponavljanje poziva postojeći runner u režimu `replay`; stvarne metrike, bez poziva modelima. JSON izvoz uključuje identitet skupa, koda/keša, commit i status radne kopije.

Preciznost citata u originalnoj metrici meri očekivani dokument, ne dokazuje tačnost svake tvrdnje. Četiri preostala neuspeha nisu uklonjena niti sakrivena ovim interfejsom. Keširan izlaz nije dokaz svežeg generisanja, a testni skupovi su ranije viđeni. Aplikacija je lokalni demo za jednog korisnika; server nema javni hosting, autentifikaciju niti produkcioni sistem poslova. Zahtevi se serijalizuju zato što postojeći CLI koristi globalnu konfiguraciju.

## Struktura i ugovori

- `frontend/src/`: React, TypeScript, lokalni DM Sans, CSS tokeni, Lucide SVG ikone. Sav vidljivi interfejs je HTML/CSS; koncept PNG se ne koristi kao UI.
- `src/web.py`: standardna Python biblioteka, bez novih runtime paketa. Služi samo frontend build i eksplicitne API putanje, vezan za `127.0.0.1`. Provera Host/Origin, ograničenje veličine JSON-a i pitanja, sprečavanje izlaska iz static direktorijuma, CSP i bez logovanja sadržaja pitanja.
- `GET /api/status`, `GET /api/documents`, `GET /api/evaluations`.
- Status računa ukupan broj dokumenata i aktuelnih verzija iz učitanog korpusa, bez fiksnih brojeva.
- `POST /api/chat`: `{ "question": "...", "profile": "current" | "offline" }`.
- `POST /api/evaluations/run`: `{}`. Ponavlja sve četiri evaluacije iz keša; rezultat se vraća browseru, istorijski dokaz se ne prepisuje.
- Profil se primenjuje pod zajedničkim zaključavanjem i konfiguracija se vraća u `finally`, uključujući greške i paralelne zahteve. Pretraga dokumenata i replay koriste isti lock.

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

Browser testovi pokreću lokalni Python server ako već nije aktivan i koriste keš; ne zahtevaju Ollama. Testovi pokrivaju odgovor/citat, nezavisno odbijanje, izvoz, verzije dokumenata, neuspešne evaluacije, pravi replay, offline profil, istoriju i tri širine ekrana. Posebne regresije pokrivaju neispravne API strukture, uklanjanje zastarelog izbora dokumenta, objašnjenje odbijanja bez citata i konflikt dva taba sa očuvanim izvozom. Axe provera obuhvata automatizovane WCAG A/AA kriterijume na početnom ekranu i testiranim ekranima razgovora, dokumenata, evaluacije i statusnog dijaloga; ona ne predstavlja potpunu potvrdu pristupačnosti.

Originalni `eval/eval_set.json`, `src/eval_runner.py`, `src/eval_compare.py`, corpus i istorijski keš nisu menjani radi web interfejsa. Specifikacija M5, njen dokaz i arhiva ostaju izdvojeni.

Vizuelni koncept, provera i odstupanja: [design-review.md](design-review.md).
