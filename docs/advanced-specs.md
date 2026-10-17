# Napredni cilj: specifikacije dodatnih promena

Svaka promena se meri u odnosu na rezultat prethodne (`after.json` → `adv1.json` → ...). Svaka specifikacija je commitovana pre svoje izmene koda.

## A1: sečenje po rečenicama (M1)

| Polje | Sadržaj |
| --- | --- |
| Propust | **E04** i **E09**: pravi dokument `hb-01` je nađen, ali „5 business days“ je u `hb-01-chunk-1`, koji je tek peti po oceni. Sečenje na 140 znakova kida reči („op is set up“, „iness days“, „Report lost or sto“), pa chunk nosi krhotine koje se ne poklapaju sa pitanjem. Tip: chunkovanje. |
| Hipoteza | Ako su chunk-ovi cele rečenice, rečenica sa „5 business days“ ostaje cela i sadrži reči iz pitanja („replacement“, „laptop“, „take“, „business“, „days“), pa ulazi u top-2. |
| Promena | Implementirati `split_text_by_sentences` (rečenice se pakuju do `CHUNK_SIZE` znakova, a duža rečenica postaje svoj chunk) i postaviti `CHUNK_STRATEGY = "sentences"`. `CHUNK_OVERLAP` se tada ne koristi, ali se ne menja. |
| Očekivani efekat | E04 i E09 → PASS. Ostala podržana pitanja ostaju PASS, jer su činjenice u kratkim rečenicama. |
| Rizik regresije | Menja se svaki chunk, pa i sve ocene. Duže rečenice dobijaju nižu ocenu (deljenje dužinom), pa se drugi citati i rang mogu promeniti bilo gde. E10 i E11 mogu dobiti drugačiji vrh. |
| Provera | `pytest`, `python -m src.eval_runner --out results/adv1.json`, `eval_compare results/after.json results/adv1.json`, CLI za E04. |
