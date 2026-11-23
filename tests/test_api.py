import anthropic
import httpx
import pytest
from fastapi.testclient import TestClient

from riskagent import api
from riskagent.agent import AgentError, Outcome

FAKE_LLM = object()
DESC = "We sell software that screens CVs and ranks applicants for interviews."


@pytest.fixture
def make(retriever, monkeypatch):
    def _make(result=None, llm=FAKE_LLM):
        def fake_assess(description, answers, r, client):
            if isinstance(result, Exception):
                raise result
            fake_assess.seen = (description, answers)
            return result

        monkeypatch.setattr(api, "assess", fake_assess)
        client = TestClient(api.create_app(retriever, llm))
        client.__enter__()
        client.seen = fake_assess
        return client

    return _make


def test_assessed_response(make):
    c = make(Outcome("assessed", {"tier": "high_risk"}))
    r = c.post("/assess", json={"description": DESC})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "assessed" and body["assessment"]["tier"] == "high_risk"
    assert body["disclaimer"].endswith("Not legal advice.")
    assert body["model"] and body["corpus_date"] == "2024-10-17"


def test_needs_info_response(make):
    c = make(Outcome("needs_info", question="Who decides?"))
    answers = [{"question": "Is it used in the EU?", "answer": "Yes"}]
    body = c.post("/assess", json={"description": DESC, "answers": answers}).json()
    assert (body["status"], body["question"]) == ("needs_info", "Who decides?")
    assert c.seen.seen == (DESC, answers)


def test_undetermined_response(make):
    body = (
        make(Outcome("undetermined", missing=["who decides"]))
        .post("/assess", json={"description": DESC})
        .json()
    )
    assert body["missing"] == ["who decides"]


@pytest.mark.parametrize("code", ["truncated", "refused", "too_many_steps", "no_decision"])
def test_agent_errors_map_to_502(make, code):
    r = make(AgentError(code)).post("/assess", json={"description": DESC})
    assert (r.status_code, r.json()) == (502, {"error": code})


def test_no_key_503(retriever, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    with TestClient(api.create_app(retriever, None)) as c:
        r = c.post("/assess", json={"description": DESC})
    assert (r.status_code, r.json()) == (503, {"error": "no_api_key"})


def test_upstream_503(make):
    err = anthropic.APIConnectionError(request=httpx.Request("POST", "https://x"))
    r = make(err).post("/assess", json={"description": DESC})
    assert (r.status_code, r.json()) == (503, {"error": "upstream"})


def test_too_many_answers_422(make):
    answers = [{"question": "q", "answer": "a"}] * 4
    r = make(Outcome("assessed", {})).post(
        "/assess", json={"description": DESC, "answers": answers}
    )
    assert r.status_code == 422


def test_empty_answer_422(make):
    answers = [{"question": "q", "answer": "   "}]
    r = make(Outcome("assessed", {})).post(
        "/assess", json={"description": DESC, "answers": answers}
    )
    assert r.status_code == 422


def test_short_description_422(make):
    assert (
        make(Outcome("assessed", {})).post("/assess", json={"description": "AI"}).status_code == 422
    )


def test_health(make):
    assert make().get("/health").json()["status"] == "ok"


def test_index_served(make):
    r = make().get("/")
    assert r.status_code == 200 and "<title>" in r.text
