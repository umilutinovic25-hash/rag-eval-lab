# Rezultati D1–D6 — 18.10.2026.

Specifikacija: `improvements-spec.md`, zabeležena pre promena. Svi skupovi su viđeni. Ovo su kontrolisana razvojna poređenja i replay, a ne nova nezavisna slepa provera.

## Zadržano u podrazumevanoj verziji

- **D1:** prekid provere nakon TOP_K prihvaćenih kandidata. Pre i posle odgovori i kompletni originalni eval redovi bili su identični. Broj judge odluka: 270 → 261 na 102 pitanja (10/100/70/90 → 10/95/67/89 po skupovima). To su odluke o pasusima, ne nužno mrežni pozivi; keš i either grana menjaju broj model poziva.
- **D2:** RagAnswer.trace beleži kandidate, prihvatanja/odbijanja, izabrani kontekst, tekst generisanja, metadata završetka i razlog fallback-a. Eksperiment čuva odgovore, uspehe/neuspehe, greške i sirove cold cache snapshotove. done_reason=length za generisani odgovor vodi na izvorni tekst. Za istorijski keš razlog završetka ostaje unknown.
- **D3:** zaseban nacrt rubrike za potpunost E09/H20/U17/U13 i ljudski pregled dvosmislenog T02. status je assistant_draft_not_human_approved; nije predstavljeno kao ljudski odobren referentni skup.
- **D4b:** CONTEXT_NEIGHBORS=1, CONTEXT_POLICY=references. Samo izričite reference same/that/this form/policy/procedure/process dobijaju prethodni pasus istog dokumenta, verzije i statusa. Ne širi se svaki rezultat.
- **D6:** cifre i najčešći engleski brojevi 0–99 sa jedinicama proveravaju se prema navedenom citatu. Promena 90 days u 90 years ili ninety years i direktna promena obaveze u zabranu aktiviraju fallback. Negacija različite radnje nije automatska kontradikcija. Provera citata razdvaja klauze; kosinus je stabilan i za ekstremne konačne vrednosti. Ovo su konzervativne heuristike, ne semantička garancija.

## Poređenja

| Verzija | eval | holdout | test1 | test2 | Odluka |
| --- | --- | --- | --- | --- | --- |
| Pre D koraka | 12/12 | 34/34 | 23/24 | 29/32 | polazno |
| D4 svi susedi | 12/12 | 33/34 | 23/24 | 30/32 | odbijeno zbog regresije H14 |
| D4b samo izričite reference | 12/12 | 34/34 | 23/24 | 29/32 | zadržano; H20 potpuniji |
| D5 strogi JSON judge | 11/12 | 21/34 | 16/24 | 20/32 | odbijeno |
| D5b isti model/upit, parsiranje celog JSON omotača | 12/12 | 33/34 | 21/24 | 30/32 | odbijeno; nove regresije |

Tačna popravljena/pokvarena pitanja i metrike nalaze se u `evidence/improvements/experiment-comparisons.json`. Sintaksni omotač više ne izaziva odbacivanje validnog JSON objekta, ali ni taj popravak nije opravdao zamenu podrazumevanog either judge-a. Opcija structured ostaje dostupna za istraživanje i isključena.

D4b popravlja sadržaj H20: sada se vidi IT portal / Hardware. Ranije je odgovor govorio samo „isti formular“. D3 podnizna rubrika sada nalazi obe lokacione činjenice u rečenici modela i izabranim izvorima. U13 i dalje nema dovoljno dobar odgovor. Širenje svih suseda može da pretvori U13 u PASS samo zato što je pravi dokaz negde među citatima; to nije isto što i ispravna rečenica modela.

D4b menja tekst 11 odgovora (H05,H17,H20,H21,T03,T09,T10,T12,U06,U15,U17), jer može dodati kontekst ili promeniti redosled konteksta unutar dokumenta. Nema novih originalnih PASS regresija; to nije dokaz da je svaki od 11 tekstova semantički bolji. Nema automatske garancije tačnog pripisivanja svake tvrdnje svakom markeru: H20 model navodi marker za formular, dok dodatni izvorni citat sadrži lokaciju. Oba izvora su prikazana, ali precizno claim-level pripisivanje zahteva nezavisan pregled.

## Stvarna proba bez keša

`evidence/improvements/cold-smoke.json` je pravi lokalni cold-run sa jednom ranije viđenom stavkom H20, ne novi test generalizacije. Izolovan prazan keš, 1 uspešan embedding poziv i 10 uspešnih LLM poziva, bez grešaka i fallback-a. Odgovor navodi lokaciju. Sirovi odgovori, trag odluka, identitet lokalnih modela, snapshotovi i njihovi hash-evi su sačuvani. Nije izveden cold-run svih 102 pitanja.

Živi D4/D4b/D5/D5b eksperimenti koristili su izdvojen keš koji je počeo kopijom istorijskog keša. Novi konteksti i novi judge promptovi izazvali su stvarne lokalne generacije; zato to nije potpuno cold merenje. Sačuvana je odvojena experiment-cache kopija, a u podrazumevani data keš preneto je samo 11 potrebnih novih generisanja za zadržani D4b, uz dostupnu metadata evidenciju. Istorijski model digesti nisu naknadno izmišljeni.

## Ograničenja

T02,U07,U11,U13 ostaju neuspešni u zadržanoj verziji. T02 ima i dvosmislenu referencu za ljudski pregled. Broj+jedinica, negacija i potpunost nisu opšti entailment model. Strukturisani JSON sam po sebi nije dovoljan. Nije odobrena nova ljudska rubrika, nije izmišljena kontribucija para i nisu slati mejlovi/poruke. Obavezni M5 i originalni eval/metrics kod nisu menjani.
