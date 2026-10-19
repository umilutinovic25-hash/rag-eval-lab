"""Cold and warm cost of the main profiles on the original eval set: time, local model calls, dependencies.

    PYTHONPATH=. python scripts/measure_cost.py evidence/upgrade/cost-profiles.json

Each profile starts from empty caches in results/cost-<profile>/, so the cold run pays for every embedding and model
call; the warm run repeats it from that cache. Committed caches are never touched.
"""
import json
import shutil
import sys
import time
from pathlib import Path

from src import config, embeddings, jev, llm
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.eval_runner import evaluate_item, load_eval_set
from src.rag import build_grounded_answer

PROFILES = {
    "M5 offline (lexical, extractive)": {"profile": "offline"},
    "semantic retrieval, extractive answer": {"overrides": {"RERANK": None, "ANSWER_MODE": "extractive", "ANSWER_QUOTES": False}},
    "shipped (semantic + LLM judge + LLM answer)": {},
}


def counting(module, name, counter):
    original = getattr(module, name)

    def wrapper(*args, **kwargs):
        counter[name] = counter.get(name, 0) + 1
        return original(*args, **kwargs)
    setattr(module, name, wrapper)
    return original


def run(chunks, items):
    by_id = {c.chunk_id: c for c in chunks}
    started = time.perf_counter()
    passed = sum(evaluate_item(i, build_grounded_answer(i["question"], chunks), by_id)["pass"] for i in items)
    return passed, time.perf_counter() - started


def main():
    out = Path(sys.argv[1])
    items = load_eval_set(Path("eval/eval_set.json"))
    baseline = config.snapshot()
    rows = []
    for label, spec in PROFILES.items():
        for key, value in baseline.items():
            setattr(config, key, value)
        if "profile" in spec:
            config.apply_profile(spec["profile"])
        for key, value in spec.get("overrides", {}).items():
            setattr(config, key, value)
        folder = Path("results") / ("cost-" + label.split()[0].lower())
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        for name in ("embedding_cache.json", "llm_cache.json", "llm_cache-metadata.json"):
            (folder / name).write_text("{}")
        embeddings.CACHE_PATH = folder / "embedding_cache.json"
        llm.CACHE_PATH = folder / "llm_cache.json"
        jev.CACHE_PATH = folder / "jev_cache.json"
        counter = {}
        originals = [counting(llm, "request_generation", counter), counting(embeddings, "request_embeddings", counter)]
        chunks = build_chunks(load_corpus())
        passed, cold = run(chunks, items)
        cold_calls = dict(counter)
        counter.clear()
        _, warm = run(chunks, items)
        llm.request_generation, embeddings.request_embeddings = originals
        models = sorted({config.EMBEDDING_MODEL} if config.RETRIEVAL_MODE in config.COSINE_MODES else set())
        if config.RERANK:
            models += [config.RERANK_MODEL, config.RERANK_YESNO_MODEL, config.YESNO_QUESTION_MODEL]
        if config.ANSWER_MODE == "llm":
            models += [config.GENERATION_MODEL]
        if config.POLARITY_CHECK and config.ANSWER_MODE == "llm":
            models += [config.POLARITY_MODEL]
        row = {"profile": label, "passed": f"{passed}/{len(items)}", "cold_seconds": round(cold, 1),
               "cold_per_question_s": round(cold / len(items), 2), "warm_seconds": round(warm, 2),
               "llm_calls_cold": cold_calls.get("request_generation", 0),
               "embedding_requests_cold": cold_calls.get("request_embeddings", 0),
               "local_models": sorted(set(models)), "needs_ollama": bool(models), "paid_api": False}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    out.write_text(json.dumps(rows, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
