from types import SimpleNamespace as NS

import pytest

from riskagent.agent import MAX_CALLS, AgentError, assess

CV = "We sell software that screens CVs and ranks applicants for interviews."
QUOTE = "AI systems intended to be used for the recruitment or selection of natural persons"


class FakeClient:
    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []
        self.messages = NS(create=self._create)

    def _create(self, **kw):
        self.calls.append({**kw, "messages": list(kw["messages"])})
        return self.replies.pop(0)


def msg(stop, *blocks):
    return NS(stop_reason=stop, content=list(blocks))


def use(name, inp, id_="t1"):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def search(q="recruitment", id_="s1"):
    return msg("tool_use", use("search_act", {"query": q}, id_))


def submit(chunk_id="anx_III#4", quote=QUOTE, tier="high_risk", id_="t9"):
    ev = [{"chunk_id": chunk_id, "quote": quote}]
    steps = [
        {"test": "annex_iii", "finding": "f", "outcome": "applies", "evidence": ev},
        {
            "test": "article_6_3",
            "finding": "f",
            "outcome": "does_not_apply",
            "evidence": [
                {
                    "chunk_id": "art_6#2",
                    "quote": "an AI system referred to in Annex III shall not be "
                    "considered to be high-risk",
                }
            ],
        },
    ]
    return use(
        "submit_assessment",
        {
            "tier": tier,
            "role": "provider",
            "gpai_based": False,
            "profiles_people": True,
            "transparency_duties": False,
            "summary": "s",
            "steps": steps,
            "obligations": [],
        },
        id_,
    )


def test_request_shape(retriever):
    c = FakeClient(search(), msg("tool_use", submit()))
    assess(CV, [], retriever, c)
    kw = c.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["thinking"] == {"type": "adaptive"}
    assert kw["max_tokens"] == 16000
    assert all(t["strict"] for t in kw["tools"])
    assert not {"temperature", "top_p", "top_k", "tool_choice"} & kw.keys()
    assert {t["name"] for t in kw["tools"]} == {"search_act", "ask_user", "submit_assessment"}


def test_search_then_submit_assessed(retriever):
    out = assess(CV, [], retriever, FakeClient(search(), msg("tool_use", submit())))
    assert out.status == "assessed"
    assert out.assessment["tier"] == "high_risk"
    assert (out.searches, out.calls) == (1, 2)


def test_search_results_sent_as_text_with_chunk_ids(retriever):
    c = FakeClient(search(), msg("tool_use", submit()))
    assess(CV, [], retriever, c)
    result = c.calls[1]["messages"][-1]["content"][0]
    assert result["type"] == "tool_result" and result["tool_use_id"] == "s1"
    assert "[anx_III#4] Annex III, point 4" in result["content"]


def test_unverified_when_evidence_fails(retriever):
    out = assess(
        CV,
        [],
        retriever,
        FakeClient(search(), msg("tool_use", submit(quote="not in the act " * 3))),
    )
    assert out.status == "unverified"


def test_evidence_from_unsearched_chunk_rejected(retriever):
    out = assess(CV, [], retriever, FakeClient(msg("tool_use", submit())))
    assert out.status == "unverified"


def test_ask_user_returns_needs_info(retriever):
    q = use("ask_user", {"question": "Does it make the decision?", "why": "6(3)"})
    out = assess("An AI tool for HR teams.", [], retriever, FakeClient(msg("tool_use", q)))
    assert (out.status, out.question) == ("needs_info", "Does it make the decision?")


def test_cannot_ask_after_three_answers(retriever):
    answers = [{"question": f"q{i}", "answer": f"a{i}"} for i in range(3)]
    c = FakeClient(msg("tool_use", use("cannot_determine", {"missing": ["who decides"]})))
    out = assess("An AI tool for HR teams.", answers, retriever, c)
    names = {t["name"] for t in c.calls[0]["tools"]}
    assert "ask_user" not in names and "cannot_determine" in names
    assert (out.status, out.missing) == ("undetermined", ["who decides"])


def test_answers_rendered_in_first_message(retriever):
    c = FakeClient(search(), msg("tool_use", submit()))
    assess(CV, [{"question": "Who decides?", "answer": "A recruiter."}], retriever, c)
    first = c.calls[0]["messages"][0]["content"]
    assert CV in first and "Q: Who decides?" in first and "A: A recruiter." in first


def test_parallel_tools_all_answered(retriever):
    two = msg(
        "tool_use", use("search_act", {"query": "a"}, "s1"), use("search_act", {"query": "b"}, "s2")
    )
    c = FakeClient(two, msg("tool_use", submit()))
    assess(CV, [], retriever, c)
    ids = [r["tool_use_id"] for r in c.calls[1]["messages"][-1]["content"]]
    assert ids == ["s1", "s2"]


def test_submit_beats_ask(retriever):
    both = msg("tool_use", use("ask_user", {"question": "q", "why": "w"}, "a1"), submit())
    out = assess(CV, [], retriever, FakeClient(search(), both))
    assert out.status == "assessed"


def test_max_tokens_raises_truncated(retriever):
    with pytest.raises(AgentError) as e:
        assess(CV, [], retriever, FakeClient(msg("max_tokens")))
    assert e.value.code == "truncated"


def test_refusal_raises_refused(retriever):
    with pytest.raises(AgentError) as e:
        assess(CV, [], retriever, FakeClient(msg("refusal")))
    assert e.value.code == "refused"


def test_call_cap_raises_too_many_steps(retriever):
    c = FakeClient(*[search(id_=f"s{i}") for i in range(MAX_CALLS + 1)])
    with pytest.raises(AgentError) as e:
        assess(CV, [], retriever, c)
    assert e.value.code == "too_many_steps"
    assert len(c.calls) == MAX_CALLS


def test_reprompt_once_then_no_decision(retriever):
    talk = msg("end_turn", NS(type="text", text="It is probably high-risk."))
    c = FakeClient(talk, talk)
    with pytest.raises(AgentError) as e:
        assess(CV, [], retriever, c)
    assert e.value.code == "no_decision"
    assert c.calls[1]["messages"][-1]["role"] == "user"


def test_reprompt_recovers(retriever):
    talk = msg("end_turn", NS(type="text", text="Thinking out loud."))
    out = assess(CV, [], retriever, FakeClient(search(), talk, msg("tool_use", submit())))
    assert out.status == "assessed"
