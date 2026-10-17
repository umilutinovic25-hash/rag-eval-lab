# Demonstracija na Sesiji 2 (podsetnik)

Zadatak traži da demonstracija pokaže: propust, specifikaciju, `diff`, rezultat pre/posle na istom skupu, regresiju ili ograničenje i doprinos oba člana. Redosled ispod pokriva svih šest stavki, oko 5 minuta.

Priprema (jednom, pre sesije):

```bash
cd rag-week-7-weak-checkpoint
. .venv/bin/activate
export PYTHONDONTWRITEBYTECODE=1
```

## 1. Propust (E06): sistem citira zastarelu politiku

```bash
git checkout -q ee583f3 && find src -name __pycache__ -exec rm -rf {} +
python -m src.cli --question "How many days per week can I work remotely?"
python -m src.eval_runner --out results/demo-before.json
```

Pokazati: `Remote work policy (version 2024, superseded)` i „2 days per week“, a važeće je 3 dana; eval 6/12.

## 2. Specifikacija, napisana pre koda

```bash
git log --oneline ee583f3..45b8172   # spec commit 2ceaced je PRE promene 45b8172
git show 2ceaced:docs/change-spec.md
```

## 3. Diff: jedna namera

```bash
git diff ee583f3 45b8172 -- src
```

## 4. Pre/posle na istom skupu

```bash
git checkout -q 45b8172 && find src -name __pycache__ -exec rm -rf {} +
python -m src.cli --question "How many days per week can I work remotely?"
python -m src.eval_runner --out results/demo-after.json
python -m src.eval_compare results/demo-before.json results/demo-after.json
```

Pokazati: `version 2026, current`; `Fixed: E06`, `Regressed: none`, isti `eval_set_sha256`, promenjeno samo `CURRENT_ONLY`.

## 5. Ograničenje

- E04 i E09 (granica chunk-a), E10 i E11 (odgovara umesto da odbije), E05 (parafraza) i dalje padaju.
- Pitanje o politici iz 2024. više ne može da se odgovori.

## 6. Doprinos oba člana

Tabela u odeljku 11 izveštaja.

## Bonus: napredni deo (ako ima vremena)

```bash
git checkout -q master
find src -name __pycache__ -exec rm -rf {} +
python -m src.eval_runner --out results/demo.json    # 12/12, radi bez Ollama
cat evidence/advanced/compare-before-vs-A4.txt
```

Napomenuti: pragovi su kalibrisani na istom skupu, pa je 12/12 optimistično.

## Bonus 2: max nivo, generalizacija (ako ima vremena)

```bash
python -m src.holdout_runner --out results/demo-holdout.json                         # 33/34
python -m src.holdout_runner --set eval/test_set.json --out results/demo-test.json  # 22/24
cat evidence/maxlvl/compare-test-B0-vs-final.txt
python -m src.cli --question "How many days per week can I work remotely?"         # LLM odgovor sa [chunk-id]
```

Poruka: na novim pitanjima prag od 0.60 ne radi (klase se preklapaju: 0.540 prema 0.676). Hibrid je štetio, a LLM judge je pomogao tek kao kaskada u sivoj zoni. Na slepom testu dobitak je samo +1/24, što je pošten rezultat (odeljak 13 izveštaja).
