import pytest

from riskagent.verify import tier_problems, verify_assessment

Q = {  # exact sentences from the fixture chunks
    "art_5#6": "the use of AI systems to infer emotions of a natural person in the areas of "
    "workplace and education institutions",
    "anx_III#4": "AI systems intended to be used for the recruitment or selection of natural persons",
    "art_6#2": "an AI system referred to in Annex III shall not be considered to be high-risk",
    "art_50#0": "Providers shall ensure that AI systems intended to interact directly with natural "
    "persons",
    "art_6#1": "AI systems referred to in Annex III shall be considered to be high-risk",
}


def ev(cid, quote=None):
    return {"chunk_id": cid, "quote": quote if quote is not None else Q[cid]}


def step(test, outcome, *evidence):
    return {
        "test": test,
        "finding": f"{test} {outcome}",
        "outcome": outcome,
        "evidence": list(evidence),
    }


def assessment(tier, steps, profiles_people=False, obligations=()):
    return {
        "tier": tier,
        "role": "provider",
        "gpai_based": False,
        "profiles_people": profiles_people,
        "transparency_duties": False,
        "summary": "s",
        "steps": list(steps),
        "obligations": list(obligations),
    }


NEG = [
    step("article_5", "does_not_apply", ev("art_5#6")),
    step("annex_iii", "does_not_apply", ev("anx_III#4")),
]


def test_valid_evidence_kept_with_ref_and_url(by_id):
    r = verify_assessment(
        assessment("prohibited", [step("article_5", "applies", ev("art_5#6"))]), by_id
    )
    assert r.status == "assessed"
    e = r.assessment["steps"][0]["evidence"][0]
    assert e["ref"] == "Article 5(1)(f)"
    assert e["url"].endswith("#art_5")


def test_quote_not_in_chunk_dropped(by_id):
    s = step(
        "article_5", "applies", ev("art_5#6"), ev("art_5#6", "employers may never use AI at all")
    )
    r = verify_assessment(assessment("prohibited", [s]), by_id)
    assert len(r.assessment["steps"][0]["evidence"]) == 1
    assert (r.submitted, r.valid) == (2, 1)


def test_whitespace_and_unicode_drift_tolerated(by_id):
    drift = Q["art_5#6"].replace(" ", "  \n", 3)
    r = verify_assessment(
        assessment("prohibited", [step("article_5", "applies", ev("art_5#6", drift))]), by_id
    )
    assert r.status == "assessed"


def test_short_quote_rejected(by_id):
    r = verify_assessment(
        assessment("prohibited", [step("article_5", "applies", ev("art_5#6", "AI systems"))]), by_id
    )
    assert r.valid == 0


def test_unknown_chunk_evidence_dropped(by_id):
    s = step("article_5", "applies", ev("art_5#6"), ev("art_99#0", Q["art_5#6"]))
    r = verify_assessment(assessment("prohibited", [s]), by_id)
    assert r.valid == 1 and r.status == "assessed"


def test_step_without_valid_evidence_removed(by_id):
    bad = step("article_5", "applies", ev("art_5#6", "this text is not in the Act anywhere"))
    r = verify_assessment(assessment("prohibited", [bad]), by_id)
    assert r.assessment["steps"] == []
    assert r.removed == 1
    assert r.status == "unverified" and r.problems


def test_obligation_without_valid_evidence_removed(by_id):
    good = {"text": "ok", "applies_to": "provider", "evidence": [ev("art_50#0")]}
    bad = {"text": "made up", "applies_to": "provider", "evidence": [ev("art_50#0", "x" * 30)]}
    a = assessment(
        "transparency",
        NEG + [step("article_50", "applies", ev("art_50#0"))],
        obligations=[good, bad],
    )
    r = verify_assessment(a, by_id)
    assert [o["text"] for o in r.assessment["obligations"]] == ["ok"]
    assert r.removed == 1


def test_prohibited_needs_article_5():
    assert tier_problems("prohibited", {"article_5": "applies"}, False) == []
    assert tier_problems("prohibited", {"article_5": "does_not_apply"}, False)
    assert tier_problems("prohibited", {}, False)


def test_high_risk_annex_iii_needs_6_3_not_exempt():
    ok = {"annex_iii": "applies", "article_6_3": "does_not_apply"}
    assert tier_problems("high_risk", ok, False) == []
    assert tier_problems("high_risk", {"annex_iii": "applies"}, False)
    assert tier_problems("high_risk", {"annex_iii": "applies", "article_6_3": "exempted"}, False)
    assert tier_problems("high_risk", {"annex_i": "applies"}, False) == []


def test_profiling_overrides_exemption():
    exempt = {
        "article_5": "does_not_apply",
        "annex_iii": "applies",
        "article_6_3": "exempted",
        "article_50": "does_not_apply",
    }
    assert tier_problems("minimal", exempt, profiles_people=True)
    assert tier_problems("high_risk", {"annex_iii": "applies"}, profiles_people=True) == []


def test_exempted_annex_iii_can_be_minimal():
    o = {
        "article_5": "does_not_apply",
        "annex_iii": "applies",
        "article_6_3": "exempted",
        "article_50": "does_not_apply",
    }
    assert tier_problems("minimal", o, False) == []


@pytest.mark.parametrize("missing", ["article_5", "annex_iii", "article_50"])
def test_minimal_needs_negatives(missing):
    o = {
        "article_5": "does_not_apply",
        "annex_iii": "does_not_apply",
        "article_50": "does_not_apply",
    }
    del o[missing]
    assert tier_problems("minimal", o, False)


def test_transparency_needs_article_50():
    o = {"article_5": "does_not_apply", "annex_iii": "does_not_apply"}
    assert tier_problems("transparency", o, False)
    assert tier_problems("transparency", o | {"article_50": "applies"}, False) == []
    assert tier_problems("minimal", o | {"article_50": "applies"}, False)


def test_annex_i_applies_blocks_minimal():
    o = {
        "article_5": "does_not_apply",
        "annex_iii": "does_not_apply",
        "article_50": "does_not_apply",
        "annex_i": "applies",
    }
    assert tier_problems("minimal", o, False)


def test_unknown_tier_is_a_problem():
    assert tier_problems("medium", {}, False)


def test_counts(by_id):
    steps = NEG + [step("article_50", "applies", ev("art_50#0"), ev("art_50#0", "nope" * 10))]
    r = verify_assessment(assessment("transparency", steps), by_id)
    assert (r.submitted, r.valid, r.removed) == (4, 3, 0)
    assert r.status == "assessed"


def test_conflicting_outcomes_unverified(by_id):
    steps = [
        *NEG,
        step("article_5", "applies", ev("art_5#6")),
        step("article_50", "does_not_apply", ev("art_50#0")),
    ]
    r = verify_assessment(assessment("minimal", steps), by_id)
    assert r.status == "unverified"
    assert any("article_5" in p for p in r.problems)


@pytest.mark.parametrize("tier", ["high_risk", "transparency", "minimal"])
def test_article_5_applies_blocks_lower_tiers(tier):
    o = {
        "article_5": "applies",
        "annex_i": "applies",
        "annex_iii": "does_not_apply",
        "article_50": "applies" if tier == "transparency" else "does_not_apply",
    }
    assert tier_problems(tier, o, False)


def test_evidence_must_come_from_the_tests_provision(by_id):
    wrong = step("article_5", "does_not_apply", ev("art_50#0"))
    steps = [
        wrong,
        step("annex_iii", "does_not_apply", ev("anx_III#4")),
        step("article_50", "applies", ev("art_50#0")),
    ]
    r = verify_assessment(assessment("transparency", steps), by_id)
    assert r.status == "unverified"
    assert [s["test"] for s in r.assessment["steps"]] == ["annex_iii", "article_50"]
