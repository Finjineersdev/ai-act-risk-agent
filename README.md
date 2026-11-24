<div align="center">

# AI Act risk agent

**Describe an AI system. Get its EU AI Act risk tier, with every step of the reasoning backed by a quote that code has checked against the official text.**

[![CI](https://github.com/Finjineersdev/ai-act-risk-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Finjineersdev/ai-act-risk-agent/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Opus_5.5-D97757)
[![MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

<p align="center"><img src="docs/demo.gif" alt="A vague description (an AI tool for hiring) gets a follow-up question; after the answer it is classified high-risk under Annex III point 4, with each step quoted and marked as found in the source" width="820"></p>

## Why

Before a team ships an AI feature to EU users, someone has to answer: *is this prohibited, high-risk,
or neither, and what do we owe?* The answer is a chain of legal tests across Article 5, Article 6,
Annex I, Annex III, the Article 6(3) exemption and Article 50. Ask a general chatbot and it skips
steps, guesses facts it wasn't told, and cites provisions that don't say what it claims.

This agent walks the chain the way a careful reviewer would. It searches the Act before every
finding, asks you when a fact that changes the outcome is missing, and submits its reasoning with
quotes. **Code then checks every quote against the text the agent actually retrieved**, and rejects
a tier that its verified steps don't support.

It builds on [eu-ai-act-rag](https://github.com/Finjineersdev/eu-ai-act-rag) (installed as a
pinned dependency) for the parsed Act, hybrid search and text normalisation.

## How it works

```mermaid
flowchart TB
    D(["System description<br/>+ answers so far"]) --> A["Claude Opus 5.5<br/>agent loop, adaptive thinking"]:::llm
    A -- "search_act" --> S["Hybrid search over the Act<br/><i>from eu-ai-act-rag</i>"]:::data
    S -- "excerpts with chunk ids" --> A
    A --> T{{"Which tool ends the turn?"}}
    T -- "ask_user" --> Q(["One question back to you"]):::ask
    T -- "cannot_determine" --> U["undetermined<br/>names the missing fact"]:::stop
    T -- "submit_assessment" --> C{{"Every quote in a chunk<br/>it actually retrieved?"}}
    C -- "unsupported steps removed" --> R{{"Do the verified steps<br/>support the tier?"}}
    R -- "yes" --> OK(["Tier + steps + obligations<br/>linked to EUR-Lex"]):::ok
    R -- "no" --> N["unverified"]:::stop
    Q -. "you answer, it runs again" .-> D

    classDef data fill:#e0f2fe,stroke:#0284c7,color:#0c4a6e
    classDef llm fill:#ede9fe,stroke:#7c3aed,color:#3b0764
    classDef ok fill:#dcfce7,stroke:#16a34a,color:#14532d
    classDef stop fill:#fee2e2,stroke:#dc2626,color:#7f1d1d
    classDef ask fill:#fef9c3,stroke:#ca8a04,color:#713f12
```

<sub>Purple: Claude · Blue: retrieval · Yellow: asks instead of guessing · Red: refuses to guess · Green: the only path to a tier.</sub>

The agent works through six tests, searching before each one:

| Test | Question |
|---|---|
| Article 5 | Is it a prohibited practice? |
| Annex I | Is it a safety component of a regulated product (machinery, medical devices, lifts...)? |
| Annex III | Is it used in a high-risk area (employment, credit, education, benefits, migration...)? |
| Article 6(3) | If Annex III applies, is it exempt (a narrow procedural task, and no profiling)? |
| Article 50 | Does it talk to people or generate synthetic content? |
| Role | Provider or deployer? |

### Tier rules, enforced in code

The agent proposes a tier; [`verify.py`](src/riskagent/verify.py) accepts it only if the steps that
survived quote-checking support it:

| Tier | Needs verified evidence that... |
|---|---|
| Prohibited | Article 5 applies |
| High-risk | Annex I applies, or Annex III applies and Article 6(3) doesn't exempt it (profiling is never exempt) |
| Transparency | Article 5 and Annex III are ruled out (or exempted), and Article 50 applies |
| Minimal | as above, and Article 50 doesn't apply |

A quote shorter than 20 characters doesn't count ("AI systems" appears everywhere and proves
nothing), evidence can only point at chunks the agent's own searches returned in that run, and a
finding must quote the provision it is about (an Article 50 quote can't settle Article 5).
Conflicting findings for the same test make the result `unverified`.

## Evals

Measured on 30 hand-written system descriptions with each model ([golden set](evals/golden.jsonl),
[Opus report](evals/results/assessments.md), [Haiku report](evals/results/assessments-claude-haiku-5-5.md)).
The live demo runs Haiku for typed descriptions.

| Metric | Claude Opus 5.5 | Claude Haiku 5.5 |
|---|---|---|
| Correct tier, accepted by the checker | **100%** (30/30) | **100%** (30/30) |
| Asked a question when the description was too vague | **100%** (4/4) | **100%** (4/4) |
| Didn't ask when the description was clear | 92% (24/26) | 81% (21/26) |
| Evidence quotes accepted: in the retrieved text, from the provision the finding is about | **97.8%** (316/323) | 93.9% (353/376) |
| Errors (cut off, refused, ran out of steps) | 0 | 0 |

The cases cover prohibited practices (emotion recognition at work, social scoring, face scraping),
Annex III uses (CV screening, credit scoring, exam proctoring, benefits, migration), Annex I safety
components (medical device, industrial robot, lifts), Article 6(3) exemptions, transparency-only
systems, minimal-risk systems, four deliberately vague descriptions, and one description that tries
to instruct the agent to say "prohibited". Whenever a clear case still got a question (2 for Opus,
5 for Haiku), it was a single question and the tier that followed was correct.

## Live demo

<!-- LIVE_LINK -->

The public demo keeps the bill bounded:

- The examples show **saved assessments from Claude Opus 5.5** (labelled with their date). No API call.
- Descriptions you type run on **Claude Haiku 5.5**, up to 5 per visitor per hour and 100 per hour in
  total. A follow-up answer counts as a request.
- Paste your own Anthropic key to run **Claude Opus 5.5**. It is used for your requests only, held in
  memory for that request, and never stored or logged.
- If the owner's monthly spend limit is reached, the demo says it is paused and the examples keep working.

All of this is switched on by `DEMO=1`; a local run is unchanged. `GET /config` reports the mode,
`GET /examples` serves the saved assessments, and an optional `X-Anthropic-Key` header on
`POST /assess` runs that request with the visitor's key. The per-visitor limit needs the visitor's real
address from behind the host's proxy: set `CLIENT_IP_HEADER` to a header the proxy sets and
overwrites (on Render: `CF-Connecting-IP`), or `PROXY_HOPS` to how many proxies append to
`X-Forwarded-For` (default 1). When a call to Anthropic fails, the log shows the error type and
status, never a key.

## Run it

```bash
cp .env.example .env          # add your ANTHROPIC_API_KEY
docker compose up --build     # http://localhost:8001
```

Without Docker:

```bash
uv sync
uv run uvicorn riskagent.api:app --reload
```

Tests and evals:

```bash
uv run pytest                 # 112 tests, fake model client, no network or API key
uv run python evals/run.py    # the 30-case golden set against Claude
```

## API

```bash
curl -s localhost:8001/assess -H 'content-type: application/json' \
  -d '{"description": "A chatbot on our website answers customer questions about orders and returns."}'
```

```json
{
  "status": "assessed",
  "assessment": {
    "tier": "transparency",
    "role": "unclear",
    "profiles_people": false,
    "summary": "A customer-service chatbot that answers questions about orders and returns is not a prohibited practice. …",
    "steps": [
      "…",
      {
        "test": "article_50",
        "finding": "The chatbot is intended to interact directly with natural persons, so Article 50(1) applies: users must be informed that they are talking to an AI system, unless that is obvious.",
        "outcome": "applies",
        "evidence": [
          {
            "chunk_id": "art_50#0",
            "quote": "1. Providers shall ensure that AI systems intended to interact directly with natural persons are designed and developed in such a way that the natural persons concerned are informed that they are interacting with an AI system, unless this is obvious from the point of view of a natural person who is reasonably well-informed, observant and circumspect, taking into account the circumstances and the context of use.",
            "ref": "Article 50(1)",
            "url": "https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng#art_50"
          }
        ]
      },
      "…"
    ],
    "obligations": [
      "…"
    ]
  },
  "model": "claude-opus-5-5",
  "corpus_date": "2024-10-17",
  "disclaimer": "Research aid based on the text of Regulation (EU) 2024/1689. Not legal advice."
}
```

| Status | Meaning |
|---|---|
| `assessed` | Tier, steps and obligations, every quote verified |
| `needs_info` | One `question`; send it back with your answer in `answers` (up to 3) |
| `undetermined` | Questions used up and a deciding fact is still `missing`; no tier is guessed |
| `unverified` | The verified steps don't support the proposed tier; `problems` says why |
| HTTP 502 | `truncated`, `refused`, `too_many_steps` (over 12 model calls) or `no_decision` |
| HTTP 503 | `no_api_key`, `upstream`, or `paused` (demo: the owner's monthly spend limit is reached) |
| HTTP 429 | demo only: `rate_limited` (this visitor's hourly limit) or `busy` (the hourly limit across all visitors) |
| HTTP 401 | `bad_key`: the key sent in `X-Anthropic-Key` was not accepted |

## Design decisions

Full design: [`docs/design.md`](docs/design.md).

- **The agent loop is in the repo**, on the Messages API, not a hosted agent service. The loop, the
  guards and the checks are the point, and they're unit-tested with a scripted fake client.
- **Checked evidence instead of built-in citations.** Anthropic Citations can't be combined with a
  structured final answer, so the agent submits `{chunk_id, quote}` pairs and code checks them,
  which gives the same guarantee.
- **Stateless.** Each request carries the description and the answers so far; the server keeps no
  sessions.
- **Asks only about facts that change the tier**, at most three times. An unclear role doesn't use a
  question: obligations are listed for both provider and deployer.
- **Found a bug upstream while building this.** Annex I (the product-safety laws) had been parsed
  as bare numbers in eu-ai-act-rag; fixed there with a test and released as v1.1.1.

## Source and licence

Text: Regulation (EU) 2024/1689 (Artificial Intelligence Act), via
[eu-ai-act-rag](https://github.com/Finjineersdev/eu-ai-act-rag) v1.2.2 (official text dated
2024-10-17). Amendments after that version, and the dates from which each obligation applies, are
not covered. EU legal texts are reused under Commission Decision 2011/833/EU.

**This is a research aid, not legal advice.**

Code: [MIT](LICENSE) © Haseeb Hanif
