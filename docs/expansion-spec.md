# F1–F22: puna lista predloženih unapređenja

Polazni commit: 1b68204. Korisnik traži sve predloge iz prethodne tri poruke. Originalni eval skupovi/kod metrika, korpus, istorijski keševi i M5 minimum se ne menjaju. Novi dokumenti i metapodaci pripadaju lokalnoj eksperimentalnoj biblioteci. Ne preuzimati nove modele niti servise. Sva čuvanja ostaju lokalna.

| ID | Isporuka / kriterijum |
| --- | --- |
| F1 | Četiri poznata propusta: opšti izvorno zasnovani obrasci za ograničenja, raspodelu, dostupnost i odnos politika; bez ID-jeva eval pitanja ili fiksnih odgovora. T02 daje samo ono što izvor eksplicitno kaže i obeležava da zaključak o odbijanju dana nije naveden. Isti originalni eval pre/posle; dodatne kontrole sa drugim ID/iznosom/granicom i nepodržanim upitima. |
| F2 | Provera traženih delova odgovora; doslovni dokazi za svaku podržanu lokaciju/trajanje, bez pretvaranja dopunskih citata u dokaz potpunosti rečenice modela. |
| F3 | Audit pojedinačnih tvrdnji i njihovih citata: doslovno podržano / rizik / potreban pregled. Heuristike nisu dokaz entailment-a. |
| F4 | Dopunski srpski grader za padeže/ASCII/ćirilicu, sa negativnim kontrolama za brojeve i negaciju; istorijski 23/24 izveštaj i zamrznuti skup ostaju neizmenjeni. |
| F5 | SQLite trajni poslovi: oporavak queued/running posle restarta uz postojeći rok, trajni rezultat, očuvano otkazivanje i TTL; bez neograničenog reda ili tihog ponavljanja otkazanog posla. |
| F6 | Stres test tri taba, povratka mreže, quota greške i istovremenog brisanja. Očuvanje ili jasna poruka/izvoz, bez lažnog 'sačuvano'. |
| F7 | Panel kvaliteta: audit tvrdnji/potpunosti, upozorenja, fallback, lokalne ljudske ocene; bez izmišljenih ljudskih ocena. |
| F8 | Poređenje izabranih verzija politika, diff i citati obe verzije; arhivirana verzija ne postaje dokaz aktuelne politike. |
| F9 | Razjašnjenje neodređenog upita kroz ponuđene teme; bez izmišljanja činjenica. |
| F10 | Detekcija mogućih sukoba istovremeno važećih izvora iste politike i prikaz oba dokaza; blokirati proizvoljan izbor pobednika. Obeležiti heurističku prirodu. |
| F11 | Kontrolisan unos TXT/MD/JSON dokumenata u sandbox: pregled teksta/metapodataka, eksplicitna aktivacija, ograničenja veličine, bez izvršavanja sadržaja. |
| F12 | Filter teme i dokumenta za upit; isti filteri važe u poređenju konfiguracija. |
| F13 | Dve konfiguracije na istom pitanju/korpusu, oba odgovora/izvori/podešavanja/trošak i razlike. |
| F14 | Testovi prompt injection-a u pitanju i izvoru; sumnjivi izvori ostaju izolovani. Sistem nema model alat za komande/slanje/pisanje. Ne tvrditi potpunu bezbednosnu garanciju. |
| F15 | JSON backup i uvoz istorije: verzija/checksum, pregled pre uvoza, očuvanje postojećih razgovora, bez prenosa aktivnih job ID-jeva na drugi server. |
| F16 | Kontrolisana normalizacija kucanja/skraćenica/SR bez dijakritike/mešanog jezika; prikaz pretrage i originalnog pitanja; ne menjati brojeve, negaciju ili proizvoljna imena. |
| F17 | Keš vezan za opaženi digest modela i parametre; drugi digest ne koristi prethodan odgovor. Istorijski replay ostaje izdvojen i jasno označen kao unknown provenance. Offline zapis identiteta ne glumi novu potvrdu aktivnog modela. |
| F18 | Datum objave odvojen od početka/kraja važenja; ISO datumi, validni intervali i pregled izvora na izabrani datum. Nepoznat datum je nepoznat. |
| F19 | Zdravlje korpusa: duplikati, prazni izvori, nepoznati statusi, nedostajuće reference, datumi, sumnjive instrukcije; čitljiv prikaz upozorenja. |
| F20 | Runner ponovljivosti sa praznim aplikacionim kešom po ponavljanju, stvarnim brojem poziva, model identitetom, varijacijama odgovora/citata/odbijanja i latencijom. Model može ostati učitan u Ollama-i; to nije hardverski cold-start. |
| F21 | Stvarni pozivi/cache hits/prompt i output tokeni/vreme po fazama; nedostupni tokeni su null, ne izmišljena nula. Keširani istorijski tokeni nisu potrošnja novog zahteva. |
| F22 | Lokalne prijave netačno/nepotpuno/pogrešan citat, komentar, tačan odgovor i provenance/hash; pregled/izvoz bez slanja trećim licima. |

Arhitektura: originalni RAG i CLI ostaju osnova. Kontrolisan evidence sloj dodaje opšte tekstualne obrasce; ne menja reference. Lokalni SQLite čuva biblioteku, metapodatke, poslove i feedback. Web dobija radionicu za biblioteku, poređenje i kvalitet; chat dobija audit/feedback i backup. `baseline` profil čuva staro ponašanje, `verified` dodaje digest vezivanje. Nema novih spoljašnjih servisa.

Provera: TDD za kritična ponašanja; pytest; frontend unit/format/build; izolovani Playwright server i stanje u privremenom direktorijumu, IAB ručna provera bez pisanja u korisničku istoriju; desktop/mobilni prikaz/WCAG/konzola; originalni eval pre/posle; dopunski grader pored istorijskih rezultata; zabeležena mala proba ponovljivosti postojećih modela. Ne potvrđivati opštu semantičku tačnost niti nezavisan ljudski pregled. Ljudsku rubriku/prevode može stvarno odobriti samo osoba koja ih pregleda.
