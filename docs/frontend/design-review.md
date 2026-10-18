# Koncept i završna vizuelna provera

Datum: 18.10.2026. Alati: `frontend-app-builder`, `frontend-design`, built-in Image Gen, IAB, Playwright i `view_image`.

## Referenca i specifikacija

Koncept: [concept.png](concept.png), generisan built-in Image Gen alatom kao `ui-mockup`, bez transparentne pozadine. Originalna dimenzija je **1505 × 1045**. To je vizuelna referenca; PNG nije interfejs niti pozadinska slika aplikacije. Sav tekst, navigacija, obrasci i podaci implementirani su kao stvarni React/HTML elementi.

Smer: beli radni prostor, tamnozelena leva navigacija, veliki serifni naslov, tri početna pitanja, donji unos i desni panel dokaza. Boje: `#123c35`, `#246555`, bela i blaga sivozelena. Georgia za uredničke naslove i izvorni tekst; lokalni DM Sans za kontrole. Raster foto/ilustracije nisu potrebne; ikone su vektorske. Izvorna ilustracija dokumenata izvedena je kao čist skalabilan SVG sa četiri papira, ne kao raster ili slika ekrana.

Funkcionalne potrebe koje nadograđuju prazan koncept: istorija posle prvog pitanja, zauzeto stanje, greška servisa, originalni citati i trag odluke, sadržaj dokumenata, evaluaciona tabela, preuzimanje, statusni dijalog i mobilna navigacija. Te celine proizlaze iz traženog web interfejsa za postojeći RAG.

## Evidencija poređenja

IAB je prvo korišćen za stvarne klikove: E06, citat, tok odluke, E11 odbijanje, offline profil, stara verzija dokumenta i replay sa neuspesima U07/U11/U13. IAB je proverio i mobilni ekran. Njegov API ne nudi putanju za čuvanje screenshot datoteke, pa su trajni snimci i dodatni automatizovani testovi urađeni Playwright-om. Koncept i završni snimci su otvoreni kroz `view_image` u istoj završnoj QA proveri.

| Tačka | Koncept / dokaz | Provera i ispravka |
| --- | --- | --- |
| Geometrija | `concept.png`, `desktop.png` | Na 1505 × 1045 leva traka meri 264 px, desni panel 345 px; centralni radni prostor odgovara referenci. Prvobitno preuske bočne trake su proširene. |
| Tipografija | Naslov i opis, kontrole, sidebar, izvori, tabela | Serifna hijerarhija je zadržana; naslov više ne preliva preko panela. Izmerena širina teksta ostaje u centralnom prostoru na 1280, 1366, 1440, 1505 i 1920 px. Kontrole imaju eksplicitne veličine i težine, bez browser podrazumevanog fonta. |
| Paleta | Bela glavna površina, zelena traka, svetli panel | Nije dodat gradijent, krem pozadina, dekorativni efekat niti rasterski overlay. Pomoćni tekst je namerno potamnjen zbog WCAG kontrasta. |
| Razmaci i kontrole | Tri reda pitanja, blok dokaza, donji unos | Redovi, granice, radijusi i vertikalni ritam usklađeni sa konceptom. Unos ostaje vidljiv, a dugačak razgovor i sadržaj stranica skroluju se unutar radnog prostora. |
| Ikone | Knjiga, dokumenti, chat, grafikon, štit, slanje | Jedinstvene outline ikone i fino nacrtani dokumenti; sve strelice su SVG. Prazno dugme za slanje je sivo i onemogućeno, a strelica nagore menja konceptualni avion kao namerna konvencija za chat. |
| Tekst | `desktop.png` i spisak ispod | Svi osnovni vidljivi natpisi koncepta su zadržani. Nisu dodati marketinški slogani, bedževi ili izmišljene metrike. |
| Mobilni prikaz | `mobile.png`, 390 × 844 | Navigacija se otvara dugmetom; skrivene kontrole nisu fokusabilne. Izvori se otvaraju preko radnog prostora uz dostupno zatvaranje. Nema horizontalnog prelivanja. |
| Stvarni podaci | `chat.png`, `evaluation.png` | Citat prikazuje politiku iz 2026. i originalni tekst. Evaluacija prikazuje tri neuspeha test2 i razlog U13, bez tvrdnje da su rešeni. |

Provera sadržaja prvog ekrana: `izvor.`, `RAG radni prostor`, `Razgovor`, `Dokumenti`, `Evaluacija`, `Novi razgovor`, `Lokalni sistem`, `Week 07`, `Radni prostor / Razgovor`, `Lokalno`, `Odgovori počinju izvorom.`, `Pitajte interni priručnik. Proverite svaki odgovor.`, `Predlozi za početak`, sva tri pitanja, `Svaki odgovor ima trag.`, tekst o izvorima/verzijama/odlukama, placeholder unosa, `Napredni RAG`, `Enter za slanje`, napomena o engleskom jeziku, `Izvori i odluke`, `Dokaz uz svaki odgovor`, objašnjenje panela i blok priručnika. **Nema nenamernog dodatog/uklonjenog teksta ni promene redosleda.** Posle razgovora prikazuje se istorija kao funkcionalna dopuna. Prelom opisa i naslova na telefonu je nameran.

Preostala namerna odstupanja: tamniji sitan tekst radi čitljivosti, ravna zelena površina umesto generisanog raster šuma, lokalni DM Sans za app kontrole, disabled slanje i chat strelica nagore, responsive navigacija i prikaz aktivnog razgovora. Geometrija pojedinačnih fontskih glifova nije pixel-identična generisanoj slici. Nema preostalih materijalnih vizuelnih neusaglašenosti, odsečenog primarnog teksta, placeholder UI-ja ili inertnih glavnih kontrola. Implementacija je proverena prema konceptu, uključujući funkcionalne tokove, a ne samo uspešan build.

## Završni prompt koncepta

Built-in Image Gen, `transparent_background=false`, bez referentnih slika:

> Use case: ui-mockup. Create one high fidelity desktop web application design concept, 1440x1000 pixels, for a Serbian local RAG research app called 'izvor.' A serious beautifully typeset editorial software workspace, crisp white canvas, pale cool gray dividers, deep forest green #123c35 sidebar 218px wide, emerald #246555 primary buttons, restrained soft green accents. No gradients, no photos, no decorative art. Thin outline icons. Sidebar brand izvor. in large white serif, small 'RAG radni prostor', navigation 'Razgovor' selected, 'Dokumenti', 'Evaluacija', button '+ Novi razgovor', bottom local status 'Lokalni sistem' and 'Week 07'. Main content header at x218 has breadcrumb 'Radni prostor / Razgovor' and right green dot 'Lokalno'. Main content column from x260 to1070; right inspector x1100 to1440 light gray-white separated by line. Main area spacious title in large elegant serif 'Odgovori počinju izvorom.' and secondary sentence 'Pitajte interni priručnik. Proverite svaki odgovor.' Under title small muted text 'Predlozi za početak' and three open ruled rows with arrow icons: 'Koliko dana mogu da radim od kuće?', 'Kako da zamenim laptop?', 'Koji je budžet za obuke?'. Then generous whitespace and a green subtle callout with shield icon 'Svaki odgovor ima trag.' and small text 'Izvori, verzije dokumenata i odluke sistema na jednom mestu.' Bottom main area a white rounded composer with border, placeholder 'Postavite pitanje o priručniku…', below composer toolbar a select 'Napredni RAG', text 'Enter za slanje' and green square send arrow button. Below fine caption 'Odgovori se zasnivaju samo na dokumentima. Modeli obrađuju pitanja na engleskom.' Right inspector top label 'Izvori i odluke', icon book, empty state elegant small stacked document outline icon, title 'Dokaz uz svaki odgovor' text 'Ovde ćete videti korišćene odlomke, njihove verzije i tok odluke.' Bottom inspector a pale green bordered area 'Priručnik kompanije' then rows '10 dokumenata', '9 aktuelnih · 1 arhiviran', link 'Pregledaj dokumente →'. Overall polished real usable app screen, typography sophisticated like Geist Sans with Georgia serif headline, airy spacing, correct Serbian diacritics, clear hierarchy, subtle radius 8-16px, no huge card grids, readable exact labels.

Generator je vratio 1505 × 1045 umesto dimenzije navedene u promptu; QA je urađena u stvarnoj dimenziji vraćenog koncepta. Merodavna je sačuvana slika, ne pretpostavljena veličina iz prompta.
