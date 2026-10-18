"""Run experiments against copies of the caches so committed caches only grow after a candidate is accepted."""

import shutil
from pathlib import Path

from . import embeddings, llm

DATA = embeddings.CACHE_PATH.parent
NAMES = ("embedding_cache.json", "llm_cache.json", "llm_cache-metadata.json")


def use_scratch_caches(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        target = directory / name
        if not target.exists():
            shutil.copyfile(DATA / name, target)
    embeddings.CACHE_PATH = directory / "embedding_cache.json"
    llm.CACHE_PATH = directory / "llm_cache.json"
    return directory
