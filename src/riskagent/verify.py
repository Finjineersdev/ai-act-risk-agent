"""Check a submitted assessment against the text the agent actually retrieved.

- An evidence entry is valid only if its chunk was returned by a search in this run and its quote
  (at least MIN_QUOTE characters) appears in that chunk's text, after the same normalisation.
- A step or obligation left with no valid evidence is removed.
- The tier must follow from the verified steps (docs/design.md, "Tier rules"); otherwise the
  result is "unverified".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from actrag.ingest import Chunk, normalise
from actrag.verify import EURLEX

TESTS = ("article_5", "annex_i", "annex_iii", "article_6_3", "article_50", "role")
OUTCOMES = ("applies", "does_not_apply", "exempted")
TIERS = ("prohibited", "high_risk", "transparency", "minimal")
MIN_QUOTE = 20  # a shorter quote ("AI systems") proves nothing
# a finding must quote the provision it is about (role and obligations may quote anything)
SOURCES = {
    "article_5": ("art_5",),
    "annex_i": ("anx_I", "art_6"),
    "annex_iii": ("anx_III", "art_6"),
    "article_6_3": ("art_6",),
    "article_50": ("art_50",),
}


@dataclass
class Checked:
    status: Literal["assessed", "unverified"]
    assessment: dict
    submitted: int = 0
    valid: int = 0
    removed_steps: int = 0
    problems: list[str] = field(default_factory=list)


def tier_problems(tier: str, outcomes: dict[str, str], profiles_people: bool) -> list[str]:
    """What is missing for the verified outcomes to support this tier ([] means supported)."""
    o = outcomes.get
    if tier == "prohibited":
        return [] if o("article_5") == "applies" else ["Article 5 must apply"]
    if o("article_5") == "applies":
        return ["Article 5 applies, so the system is prohibited"]
    if tier == "high_risk":
        annex_iii = o("annex_iii") == "applies" and (
            o("article_6_3") == "does_not_apply" or profiles_people
        )
        if o("annex_i") == "applies" or annex_iii:
            return []
        return ["needs Annex I, or Annex III without an Article 6(3) exemption"]
    if tier not in ("transparency", "minimal"):
        return [f"unknown tier {tier!r}"]
    problems = []
    if o("article_5") != "does_not_apply":
        problems.append("Article 5 must be ruled out")
    if o("annex_i") == "applies":
        problems.append("Annex I applies, so the system is high-risk")
    exempted = (
        o("annex_iii") == "applies" and o("article_6_3") == "exempted" and not profiles_people
    )
    if o("annex_iii") != "does_not_apply" and not exempted:
        problems.append("Annex III must be ruled out or exempted under Article 6(3)")
    want = "applies" if tier == "transparency" else "does_not_apply"
    if o("article_50") != want:
        problems.append(f"Article 50 must be {want}")
    return problems


def verify_assessment(a: dict, retrieved: dict[str, Chunk]) -> Checked:
    submitted = valid = removed = 0

    def keep_valid(evidence: list[dict], test: str | None = None) -> list[dict]:
        nonlocal submitted, valid
        kept = []
        for e in evidence:
            submitted += 1
            chunk = retrieved.get(e.get("chunk_id", ""))
            quote = normalise(e.get("quote", ""))
            if chunk is None or len(quote) < MIN_QUOTE or quote not in chunk.text:
                continue
            if test in SOURCES and chunk.anchor not in SOURCES[test]:
                continue
            valid += 1
            url = EURLEX.format(anchor=chunk.anchor)
            kept.append({"chunk_id": chunk.id, "quote": quote, "ref": chunk.ref, "url": url})
        return kept

    def clean(items: list[dict]) -> list[dict]:
        nonlocal removed
        out = []
        for item in items:
            evidence = keep_valid(item.get("evidence", []), item.get("test"))
            if evidence:
                out.append({**item, "evidence": evidence})
            else:
                removed += 1
        return out

    steps = clean(a.get("steps", []))
    obligations = clean(a.get("obligations", []))
    seen: dict[str, set[str]] = {}
    for s in steps:
        seen.setdefault(s["test"], set()).add(s["outcome"])
    outcomes = {t: next(iter(v)) for t, v in seen.items() if len(v) == 1}
    problems = [f"conflicting findings for {t}" for t, v in seen.items() if len(v) > 1]
    problems += tier_problems(a.get("tier", ""), outcomes, bool(a.get("profiles_people")))
    return Checked(
        status="unverified" if problems else "assessed",
        assessment={**a, "steps": steps, "obligations": obligations},
        submitted=submitted,
        valid=valid,
        removed_steps=removed,
        problems=problems,
    )
