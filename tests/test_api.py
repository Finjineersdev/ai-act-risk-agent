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
        def fake_assess(description, answers, r, client, model=None):
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


# --- demo mode -------------------------------------------------------------------------

from actrag.demo import DEMO_MODEL, FULL_MODEL

KEY = "sk-ant-visitor-secret-123"
ANS = {"question": "What does it do?", "answer": "It ranks CVs."}


def status_error(cls, status, message):
    r = httpx.Response(status, request=httpx.Request("POST", "https://api.anthropic.com"))
    return cls(message, response=r, body={"type": "error", "error": {"message": message}})


@pytest.fixture
def demo(monkeypatch, retriever):
    monkeypatch.setenv("DEMO", "1")
    seen = {"clients": []}

    def fake_assess(description, answers, r, client, model=None):
        seen["model"], seen["client"] = model, client
        if "spend" in description:
            raise status_error(
                anthropic.BadRequestError, 400, "You have reached your specified API usage limits."
            )
        if "nobilling" in description:
            raise status_error(anthropic.PermissionDeniedError, 403, "not allowed")
        if "badkey" in description:
            raise status_error(anthropic.AuthenticationError, 401, "invalid x-api-key")
        return Outcome("assessed", {"tier": "minimal"})

    def factory(api_key):
        seen["clients"].append(api_key)
        return ("visitor-client", api_key)

    monkeypatch.setattr(api, "assess", fake_assess)
    c = TestClient(api.create_app(retriever, "owner-client", client_factory=factory))
    c.__enter__()
    c.seen = seen
    return c


def test_demo_uses_haiku_without_key(demo):
    r = demo.post("/assess", json={"description": DESC})
    assert r.status_code == 200 and r.json()["model"] == DEMO_MODEL
    assert demo.seen["model"] == DEMO_MODEL and demo.seen["client"] == "owner-client"


def test_demo_rate_limited_after_5(demo):
    codes = [demo.post("/assess", json={"description": DESC}).status_code for _ in range(6)]
    assert codes == [200] * 5 + [429]
    assert demo.post("/assess", json={"description": DESC}).json() == {"error": "rate_limited"}


def test_needs_info_followup_counts_toward_limit(demo):
    for _ in range(5):
        demo.post("/assess", json={"description": DESC, "answers": [ANS]})
    r = demo.post("/assess", json={"description": DESC, "answers": [ANS, ANS]})
    assert r.status_code == 429


def test_byok_uses_opus_and_skips_limit(demo):
    for _ in range(5):
        demo.post("/assess", json={"description": DESC})
    r = demo.post("/assess", json={"description": DESC}, headers={"X-Anthropic-Key": KEY})
    assert r.status_code == 200 and r.json()["model"] == FULL_MODEL
    assert demo.seen["clients"] == [KEY] and demo.seen["model"] == FULL_MODEL


def test_bad_key_401_never_echoed(demo):
    body = {"description": DESC + " badkey"}
    r = demo.post("/assess", json=body, headers={"X-Anthropic-Key": KEY})
    assert r.status_code == 401 and r.json() == {"error": "bad_key"}
    assert KEY not in r.text


def test_spend_cap_paused(demo):
    r = demo.post("/assess", json={"description": DESC + " spend"})
    assert r.status_code == 503 and r.json() == {"error": "paused"}


def test_config_endpoint(demo):
    assert demo.get("/config").json() == {"demo": True, "model": DEMO_MODEL, "byok": True}


def test_demo_off_unchanged(make):
    c = make(Outcome("assessed", {"tier": "minimal"}))
    assert all(c.post("/assess", json={"description": DESC}).status_code == 200 for _ in range(7))
    assert c.get("/config").json()["demo"] is False


def test_byok_served_when_global_cap_full(demo):
    from actrag.demo import Limiter

    demo.app.state.limiter = Limiter(per_ip=5, total=0)
    assert demo.post("/assess", json={"description": DESC}).json() == {"error": "busy"}
    r = demo.post("/assess", json={"description": DESC}, headers={"X-Anthropic-Key": KEY})
    assert r.status_code == 200


def test_byok_has_its_own_looser_limit(demo):
    h = {"X-Anthropic-Key": KEY}
    codes = [
        demo.post("/assess", json={"description": DESC}, headers=h).status_code for _ in range(31)
    ]
    assert codes == [200] * 30 + [429]


def test_visitor_key_without_permission_is_bad_key(demo):
    body = {"description": DESC + " nobilling"}
    r = demo.post("/assess", json=body, headers={"X-Anthropic-Key": KEY})
    assert r.status_code == 401 and r.json() == {"error": "bad_key"}


def test_key_never_logged(demo, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    for extra in ("", " badkey", " spend"):
        body = {"description": DESC + extra}
        demo.post("/assess", json=body, headers={"X-Anthropic-Key": KEY})
    assert KEY not in caplog.text
