import json
from pathlib import Path

import pytest
from actrag.ingest import load_corpus

from riskagent.verify import TIERS

GOLDEN = Path(__file__).parents[1] / "evals" / "golden.jsonl"
KINDS = {
    "prohibited",
    "high_risk_annex_iii",
    "high_risk_annex_i",
    "exempted",
    "transparency",
    "minimal",
    "ambiguous",
    "adversarial",
}
CASES = [json.loads(line) for line in GOLDEN.read_text().splitlines()] if GOLDEN.exists() else []


def test_golden_set_size_and_ids():
    assert 25 <= len(CASES) <= 40
    assert len({c["id"] for c in CASES}) == len(CASES)


def test_every_kind_covered():
    from collections import Counter

    n = Counter(c["kind"] for c in CASES)
    assert set(n) == KINDS
    assert all(v >= 3 for k, v in n.items() if k != "adversarial")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_case_is_well_formed(case):
    anchors = {c.anchor for c in load_corpus()}
    assert case["expected_tier"] in TIERS
    assert case["deciding"] and set(case["deciding"]) <= anchors
    assert len(case["description"]) >= 20
    if case["kind"] == "ambiguous":
        assert case["should_ask"] and case["answers"]
    else:
        assert not case["should_ask"]
