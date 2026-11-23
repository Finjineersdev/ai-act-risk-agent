"""Run the golden set against the real agent and write evals/results/assessments.md.

uv run python evals/run.py      # calls Claude; needs ANTHROPIC_API_KEY
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from riskagent.agent import MAX_QUESTIONS, AgentError

ROOT = Path(__file__).resolve().parent
GENERIC = "No more details are available; please assess from the description."


def run_case(case: dict, retriever, client, assess_fn) -> dict:
    """Run one case, answering the agent's questions from the case (in order) until it finishes."""
    supply = list(case["answers"])
    answers: list[dict] = []
    asked = 0
    t0 = time.time()
    row = {"id": case["id"], "kind": case["kind"], "expected": case["expected_tier"]}
    try:
        while True:
            o = assess_fn(case["description"], answers, retriever, client)
            if o.status != "needs_info" or len(answers) >= MAX_QUESTIONS:
                break
            asked += 1
            answers.append({"question": o.question, "answer": supply.pop(0) if supply else GENERIC})
    except AgentError as e:
        return row | {
            "status": e.code,
            "tier": None,
            "asked": asked,
            "asked_ok": False,
            "tier_ok": False,
            "deciding_verified": False,
            "submitted": 0,
            "valid": 0,
            "seconds": time.time() - t0,
        }
    tier = (o.assessment or {}).get("tier")
    anchors = {
        e["chunk_id"].split("#")[0]
        for s in (o.assessment or {}).get("steps", [])
        for e in s["evidence"]
    }
    return row | {
        "status": o.status,
        "tier": tier,
        "asked": asked,
        "asked_ok": asked >= 1 if case["should_ask"] else asked == 0,
        "tier_ok": o.status == "assessed" and tier == case["expected_tier"],
        "deciding_verified": bool(anchors & set(case["deciding"])),
        "submitted": o.checked.submitted if o.checked else 0,
        "valid": o.checked.valid if o.checked else 0,
        "seconds": time.time() - t0,
    }


def report(rows: list[dict], model: str) -> str:
    def pct(xs):
        xs = list(xs)
        return f"{sum(xs) / len(xs):.0%} ({sum(xs)}/{len(xs)})" if xs else "n/a"

    ambiguous = [r for r in rows if r["kind"] == "ambiguous"]
    clear = [r for r in rows if r["kind"] != "ambiguous"]
    submitted = sum(r["submitted"] for r in rows)
    valid = sum(r["valid"] for r in rows)
    lines = [
        f"# Assessment eval · {model}",
        "",
        (
            f"Run on {date.today().isoformat()} · {len(rows)} golden cases "
            "([golden.jsonl](../golden.jsonl))"
        ),
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Correct tier, with the tier's deciding steps verified | {pct(r['tier_ok'] for r in rows)} |",
        (
            f"| Asked a question when the description was too vague | "
            f"{pct(r['asked_ok'] for r in ambiguous)} |"
        ),
        f"| Didn't ask when the description was clear | {pct(r['asked_ok'] for r in clear)} |",
        f"| Evidence quotes accepted (in the retrieved text, from the right provision) | "
        f"{valid / submitted:.1%} ({valid}/{submitted}) |"
        if submitted
        else "| Evidence | none |",
        (
            f"| Deciding provision among the verified evidence | "
            f"{pct(r['deciding_verified'] for r in rows)} |"
        ),
        (
            f"| Rejected by the checker (unverified) | "
            f"{sum(r['status'] == 'unverified' for r in rows)} |"
        ),
        (
            f"| Errors (truncated, refused, too many steps, no decision) | "
            f"{sum(r['status'] not in ('assessed', 'unverified', 'undetermined') for r in rows)} |"
        ),
        "",
        "| Case | Kind | Expected | Got | Status | Asked | Pass | Time |",
        "|---|---|---|---|---|---|---|---|",
    ]
    lines += [
        f"| {r['id']} | {r['kind']} | {r['expected']} | {r['tier'] or '—'} | {r['status']} | "
        f"{r['asked']} | {'✓' if r['tier_ok'] else '✗'} | {r['seconds']:.0f}s |"
        for r in rows
    ]
    return "\n".join(lines) + "\n"


def report_name(base: str, model: str) -> str:
    """The Opus report keeps its name; other models get their own file."""
    if model == "claude-opus-5-5":
        return base
    stem, ext = base.rsplit(".", 1)
    return f"{stem}-{model}.{ext}"


def main() -> None:
    import anthropic
    from actrag.retrieve import Retriever

    from riskagent.agent import MODEL, assess

    cases = [json.loads(line) for line in (ROOT / "golden.jsonl").read_text().splitlines()]
    retriever, client = Retriever.load(), anthropic.Anthropic()
    rows = []
    for c in cases:
        rows.append(run_case(c, retriever, client, assess))
        r = rows[-1]
        print(
            f"{r['id']}: {r['status']} {r['tier']} asked={r['asked']} ok={r['tier_ok']}", flush=True
        )
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    text = report(rows, MODEL)
    (out / report_name("assessments.md", MODEL)).write_text(text)
    (out / report_name("assessments.jsonl", MODEL)).write_text(
        "".join(json.dumps(r) + "\n" for r in rows)
    )
    print(text)


if __name__ == "__main__":
    main()
