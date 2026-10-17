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

Napomenuti: pragovi su kalibrisani na istom skupu, a kontrolna provera van skupa daje 10/10 (semantic) prema 6/10 (lexical).
