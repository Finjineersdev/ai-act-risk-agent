from evals.run import report_name, run_case
from riskagent.agent import AgentError, Outcome
from riskagent.verify import Checked

CASE = {
    "id": "A1",
    "kind": "ambiguous",
    "description": "An AI tool for hiring.",
    "expected_tier": "high_risk",
    "deciding": ["anx_III"],
    "should_ask": True,
    "answers": ["It ranks CVs."],
}
STEP = {
    "test": "annex_iii",
    "finding": "f",
    "outcome": "applies",
    "evidence": [{"chunk_id": "anx_III#4", "quote": "q", "ref": "r", "url": "u"}],
}
DONE = Outcome(
    "assessed",
    {"tier": "high_risk", "steps": [STEP]},
    checked=Checked("assessed", {}, submitted=3, valid=2),
)


def scripted(*outcomes):
    seen = []

    def fake(description, answers, r, client):
        seen.append(list(answers))
        o = outcomes[len(seen) - 1]
        if isinstance(o, Exception):
            raise o
        return o

    fake.seen = seen
    return fake


def test_answers_questions_in_order_then_scores():
    fake = scripted(Outcome("needs_info", question="What does it do?"), DONE)
    row = run_case(CASE, None, None, fake)
    assert fake.seen[1] == [{"question": "What does it do?", "answer": "It ranks CVs."}]
    assert row["asked"] == 1 and row["asked_ok"]
    assert row["tier_ok"] and row["deciding_verified"]
    assert (row["submitted"], row["valid"]) == (3, 2)


def test_unplanned_question_gets_generic_answer_and_counts_against():
    case = CASE | {"kind": "minimal", "should_ask": False, "answers": []}
    fake = scripted(Outcome("needs_info", question="q?"), DONE)
    row = run_case(case, None, None, fake)
    assert "assess from the description" in fake.seen[1][0]["answer"]
    assert not row["asked_ok"]


def test_agent_error_recorded():
    row = run_case(CASE, None, None, scripted(AgentError("truncated")))
    assert row["status"] == "truncated" and not row["tier_ok"]


def test_report_path_per_model():
    assert report_name("assessments.md", "claude-opus-5-5") == "assessments.md"
    assert (
        report_name("assessments.jsonl", "claude-haiku-5-5") == "assessments-claude-haiku-5-5.jsonl"
    )
