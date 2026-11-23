import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest
from actrag.ingest import Chunk

FIXTURE = Path(__file__).parent / "fixtures" / "chunks.jsonl"


def fake_embed(text: str) -> np.ndarray:
    """Hashed bag-of-words vector: deterministic, no model download."""
    v = np.zeros(256, dtype=np.float32)
    for w in re.findall(r"\w+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1
    n = np.linalg.norm(v)
    return v / n if n else v


@pytest.fixture(scope="session")
def chunks() -> list[Chunk]:
    return [Chunk(**json.loads(line)) for line in FIXTURE.read_text().splitlines()]


@pytest.fixture(scope="session")
def by_id(chunks) -> dict[str, Chunk]:
    return {c.id: c for c in chunks}


@pytest.fixture(scope="session")
def retriever(chunks):
    from actrag.retrieve import Retriever

    return Retriever(chunks, np.stack([fake_embed(c.text) for c in chunks]), fake_embed)
