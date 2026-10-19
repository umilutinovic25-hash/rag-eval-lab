"""Run selected questions (set:id) and whole sets under two flag settings and report pass changes."""
import json
import sys
from pathlib import Path

from src import config
from src.chunking import build_chunks
from src.corpus import Document, load_corpus
from src.eval_runner import evaluate_item
from src.rag import build_grounded_answer
from src.retrieval_metrics import CORPORA, EVAL_DIR, SETS
from src.scratch import use_scratch_caches


def items(spec):
    name, _, qid = spec.partition(":")
    data = json.loads((EVAL_DIR / SETS[name]).read_text())
    return name, [x for x in data if not qid or x["id"] == qid]


def main():
    flag, out, specs = sys.argv[1], Path(sys.argv[2]), sys.argv[3:]
    use_scratch_caches(Path("results/scratch"))
    handbook = build_chunks(load_corpus())
    rows = []
    for spec in specs:
        name, selected = items(spec)
        chunks = handbook if name not in CORPORA else build_chunks(
            [Document(**d) for d in json.loads((EVAL_DIR / CORPORA[name]).read_text())])
        by_id = {c.chunk_id: c for c in chunks}
        for item in selected:
            row = {"set": name, "id": item["id"]}
            for value in (False, True):
                setattr(config, flag, value)
                result = build_grounded_answer(item["question"], chunks)
                row[str(value)] = {"pass": evaluate_item(item, result, by_id)["pass"],
                                   "answer": str(result.answer).split("\nSource")[0][:200]}
            rows.append(row)
            print(f"{name}:{item['id']} before={row['False']['pass']} after={row['True']['pass']} | {row['True']['answer'][:110]}", flush=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    fixed = [f"{r['set']}:{r['id']}" for r in rows if r["True"]["pass"] and not r["False"]["pass"]]
    broken = [f"{r['set']}:{r['id']}" for r in rows if r["False"]["pass"] and not r["True"]["pass"]]
    print("fixed", fixed, "regressed", broken)


if __name__ == "__main__":
    main()
