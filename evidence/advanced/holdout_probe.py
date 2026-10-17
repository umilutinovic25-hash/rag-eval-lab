import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from src import config, embeddings
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.rag import build_grounded_answer
embeddings.CACHE_PATH = Path(sys.argv[2])
Q = [
    ("answer", "hb-05", "Is two-factor login needed for the VPN?"),
    ("answer", "hb-09", "How do I book a parking spot?"),
    ("answer", "hb-04", "What is the deadline for handing in expense receipts after a trip?"),
    ("answer", "hb-10", "My computer will not turn on, where do I take it?"),
    ("answer", "hb-07", "Can I move unused vacation days to next year?"),
    ("answer", "hb-06", "Who helps me during my first week?"),
    ("refuse", None, "What is the dress code at the office?"),
    ("refuse", None, "How much is the maternity pay?"),
    ("refuse", None, "Is there a company gym membership?"),
    ("refuse", None, "What is the capital of Australia?"),
]
chunks = build_chunks(load_corpus())
for mode in ("lexical", "semantic"):
    config.RETRIEVAL_MODE = mode
    ok = 0
    print(f"--- {mode}")
    for exp, doc, q in Q:
        r = build_grounded_answer(q, chunks)
        got = "refuse" if r.refused else "answer"
        top = r.retrieved[0] if r.retrieved else None
        good = got == exp and (exp == "refuse" or (top and top.chunk.doc_id == doc))
        ok += good
        print(f"{'OK ' if good else 'BAD'} {exp:6} got={got:6} top={top.chunk.doc_id if top else '-'} {top.score if top else 0:.3f}  {q}")
    print(f"{mode}: {ok}/{len(Q)}")
