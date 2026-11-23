# AI Act risk agent: design

Status: approved in conversation on 2026-11-23.

## Intent

Teams building AI products ask one question before any other: *where does our system fall under the
EU AI Act, and what do we owe?* The answer is a chain of legal tests across Article 5, Article 6,
Annex I, Annex III, Article 6(3) and Article 50, and generic chatbots skip steps and invent citations.

This agent takes a plain-language description of an AI system and walks the chain. Every step it
reports is backed by a quote that code has checked against text the agent actually retrieved. When a
fact that decides the outcome is missing, it asks instead of guessing.

It is the second public portfolio repo. It **reuses** the first one (`eu-ai-act-rag`, package
`actrag`) for retrieval and text normalisation, installed as a pinned git dependency. The two repos
visibly build on each other.

## Goals

- Classify a described system into exactly one tier:
  `prohibited` (Article 5) · `high_risk` (Article 6(1) with Annex I, or Article 6(2) with Annex III,
  not exempted by Article 6(3)) · `transparency` (Article 50 duties only) · `minimal`.
  A system can also carry Article 50 duties on top of `high_risk`; that is reported as a flag.
- Report the likely role (provider or deployer, Article 3 definitions; Article 25 noted when it
  applies) and the obligations that follow for that tier and role.
- Every reported step carries evidence: `{chunk_id, quote}`. Code checks that the chunk was returned
  by a search in this run and that the normalised quote is a substring of the chunk's text. Steps with
  no valid evidence are dropped; if the tier-deciding step has none, the result is `unverified`.
- Ask a clarifying question when a deciding fact is missing (for example: does the tool make the
  hiring decision, or only rank candidates for a human?). At most 3 questions per assessment.
- Measured evals published in the README, as in repo 1.

## Non-goals

- Legal advice. The same disclaimer as repo 1 is shown on every response.
- Dates and transition periods (when each obligation starts applying). Amendments after the corpus
  version of repo 1 (2024-10-17) are not included; the README says so.
- GPAI model obligations (Articles 51–55) beyond a flag that the system is built on a GPAI model.
- Multi-user accounts, persistence, a database.

## Anti-goals (failure even if it "works")

- A tier with no verified evidence behind it.
- Guessing a deciding fact instead of asking.
- Showing a quote that isn't in the cited text.

## Approaches considered

1. **Agent loop written in the repo on the Claude Messages API (chosen).** Tools are plain Python
   functions; the loop, the guards and the evidence check are visible and unit-tested with a fake
   client. One API key runs everything locally.
2. **Claude Managed Agents.** Less code (Anthropic hosts the loop and sandbox), but the loop, the
   guards and the checks a recruiter wants to read would not be in the repo.
3. **Single prompt, no tools.** Cheapest, but the model would classify from memory: no retrieval, no
   checkable evidence. Rejected.

The user approved approach 1.

## How it works

Stateless HTTP API. Each request carries the description plus any answers to earlier questions; the
agent runs from scratch each time (no server-side session).

```
POST /assess {description, answers: [{question, answer}]}
  -> {status: "assessed", assessment, steps[], disclaimer, ...}
  |  {status: "needs_info", question}
  |  {status: "unverified", ...}            tier-deciding step had no valid evidence
  |  {status: "undetermined", missing}      3 questions used, a deciding fact still unknown
  |  502 {error: truncated|refused|too_many_steps|no_decision}
```

Agent loop (manual loop on `client.messages.create`, model `claude-opus-5-5`, configurable by
`MODEL` env var):

- Tools (all `strict: true`):
  - `search_act(query)` → top chunks from `actrag.retrieve.Retriever`, returned as text listing
    `chunk_id`, `ref` and text for each. The run keeps every returned chunk in a dict.
  - `ask_user(question, why)` → ends the run with `needs_info`.
  - `submit_assessment(tier, role, gpai_based, transparency_duties, steps[], obligations[],
    summary)` → ends the run. Each step: `{test, finding, outcome, evidence: [{chunk_id, quote}]}`
    where `test` is one of `article_5`, `annex_i`, `annex_iii`, `article_6_3`, `article_50`, `role`.
    Each obligation: `{text, evidence: [...]}`.
- Search results go back as plain text, not `search_result` blocks: Anthropic Citations cannot be
  combined with a structured final answer, and the evidence check gives the same guarantee in code.
- `tool_choice` stays `auto` (forcing a tool returns 400 on Opus 5.5). If the model ends a turn
  without calling `ask_user` or `submit_assessment`, it is re-prompted once; a second miss is
  `no_decision`.
- Guards: `stop_reason == "max_tokens"` → `truncated`; `refusal` → `refused`; more than 12 model
  calls → `too_many_steps`. All map to HTTP 502, never a half result. Missing key → 503
  `no_api_key`; `anthropic.APIError` → 503 `upstream` (same as repo 1).
- Evidence check (`verify_assessment`): uses `actrag.ingest.normalise` on both sides. Invalid
  evidence entries are removed; a step or obligation left with none is removed and counted. The
  tier-deciding step is the one whose `test` matches the tier (`article_5` for prohibited,
  `annex_i`/`annex_iii` for high-risk, `article_50` for transparency); `minimal` needs verified
  negative findings for `article_5`, `annex_iii` and `article_50`. Missing → `unverified`.

### Tier rules (decided after the builder check; *builder's calls, made from the Act's text*)

Each step's `outcome` is one of `applies`, `does_not_apply`, `exempted`. The tier and the steps that
must be verified for it:

| Tier | Deciding steps (all must have verified evidence) |
|---|---|
| `prohibited` | `article_5` = applies |
| `high_risk` via Annex I | `annex_i` = applies |
| `high_risk` via Annex III | `annex_iii` = applies, and `article_6_3` = does_not_apply (or the system profiles people: Article 6(3) last subparagraph says it is then always high-risk) |
| `transparency` | `article_5` and `annex_iii` = does_not_apply (or `annex_iii` = applies with `article_6_3` = exempted), and `article_50` = applies |
| `minimal` | same as `transparency`, but `article_50` = does_not_apply |

An Annex III system exempted under Article 6(3) therefore ends as `transparency` or `minimal`, and the
result notes the Article 6(4) duty to document the assessment and register it. `annex_i` is only
required when the description involves a regulated product; otherwise its absence is not a gap.

### When questions run out (builder's call)

After 3 answered questions, the agent may not ask again. If a deciding fact is still missing, it
returns `status: "undetermined"` with `missing: [fact]` and no tier. It never guesses. The eval
counts `undetermined` on an ambiguous case as a pass only if the stored answers genuinely leave the
fact open (no golden case is built that way, so in practice it is a fail).

Role is not a deciding fact for the tier: when the description doesn't make it clear, `role` is
`unclear` and obligations are listed for both provider and deployer. It never uses up a question.

## Evals

`evals/golden.jsonl`, about 30 cases written from the Act's own text and examples, each with the
expected tier and the Articles/Annex points that decide it:
- prohibited (e.g. emotion recognition at work, social scoring, untargeted face scraping)
- high-risk via Annex III (CV screening, credit scoring, exam proctoring, benefits eligibility)
- high-risk via Annex I (AI safety component of a medical device or machinery)
- Article 6(3) exemption (narrow procedural task that doesn't influence the decision)
- transparency only (customer-service chatbot, deepfake generator)
- minimal (spam filter, inventory forecasting)
- ambiguous, where the right move is to ask (e.g. "an AI tool for HR" with no detail); the answers
  to supply on the follow-up are stored in the case, so the eval can finish the assessment.

Metrics: tier accuracy; asked when it should (ambiguous cases) and didn't ask when it shouldn't;
evidence validity (valid / submitted quotes); deciding step verified. A unit-test suite runs with a
fake client in CI; the paid eval runs locally (`uv run python evals/run.py`) and its report is
committed. No GitHub secret: the user chose not to store the key there.

## Packaging

Same as repo 1: FastAPI API + one static page (description box, follow-up question flow, tier badge,
step-by-step evidence), Dockerfile, docker compose bound to 127.0.0.1, CI (ruff, pytest, docker build
+ /health), MIT licence, README with demo GIF, vertical Mermaid diagram, measured evals.

Repo 1 change needed, done as the first task of this plan: its data files move inside the package
(`src/actrag/data/`) so `actrag` works when installed from git; version goes 0.1.0 → 1.1.0, tagged
and released as `v1.1.0` (the first GitHub release, v1.0.0, has no matching package version, so the
package version jumps to match). Repo 1 is public, so CI here installs it with no secret. The
fastembed model is baked into the Docker image at build time, as in repo 1.

## Left to the builder

System prompt wording; exact `search_act` k (default 8, reuses repo 1 settings); UI layout details;
how many golden cases per category (about 30 total).
