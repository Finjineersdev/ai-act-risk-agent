# AI Act risk agent: design

Current as of v1.3.0. The README covers what the agent does and how to run it; this document
records how it is built and why.

## Problem

Before a team ships an AI feature to EU users, someone has to answer: *where does this system fall
under the EU AI Act, and what do we owe?* The answer is a chain of legal tests across Article 5,
Article 6, Annex I, Annex III, the Article 6(3) exemption and Article 50. General chatbots skip
steps, guess facts they weren't told, and cite provisions that don't say what they claim.

The agent takes a plain-language description, walks the chain, backs every step with a quote that
code checks against text the agent actually retrieved, and asks when a fact that decides the
outcome is missing. It reuses [eu-ai-act-rag](https://github.com/Finjineersdev/eu-ai-act-rag)
(package `actrag`) for the parsed Act, hybrid search, text normalisation, the demo helpers and the
web hardening, installed from a pinned release archive.

## Goals and non-goals

Goals:

- Exactly one tier: `prohibited` (Article 5), `high_risk` (Article 6(1) with Annex I, or Article
  6(2) with Annex III and not exempted by Article 6(3)), `transparency` (Article 50 duties only) or
  `minimal`. Article 50 duties on top of `high_risk` are reported as a flag.
- The likely role (provider or deployer) and the obligations that follow.
- Every step and obligation carries `{chunk_id, quote}` evidence, checked in code.
- Ask, at most three times, when a deciding fact is missing; never guess it.
- Measured evals in the README.

Non-goals: legal advice; dates and transition periods; GPAI model obligations (Articles 51–55)
beyond a flag; accounts, persistence or a database.

A failure even if it "works": a tier without verified evidence, a guessed deciding fact, or a quote
that isn't in the cited text.

## Approaches considered

1. **An agent loop in the repo on the Messages API (chosen).** The loop, the guards and the
   evidence check are visible and unit-tested with a scripted fake client.
2. **A hosted agent service.** Less code, but the loop and checks this project is about would not be
   in the repo.
3. **One prompt, no tools.** The model would classify from memory, with nothing to check.

## The loop

Stateless: each `POST /assess` carries the description and the answers so far, and the agent runs
from scratch. `client.messages.create` with `claude-opus-5-5` by default (`MODEL` overrides it),
adaptive thinking, `max_tokens` 16,000, and request-level prompt caching, because every call resends
the same system prompt, tools and growing history.

Tools, all `strict`:

- `search_act(query)` → the 8 best chunks from `actrag`, returned as text with `chunk_id`, reference
  and text. Every chunk returned in the run is remembered; evidence may only point at these.
- `ask_user(question, why)` → ends the run with `needs_info` (offered only while questions remain).
- `cannot_determine(missing)` → `undetermined`, naming the missing fact, once questions are used up.
- `submit_assessment(tier, role, profiles_people, gpai_based, transparency_duties, steps[],
  obligations[], summary)` →
  ends the run. Each step is `{test, finding, outcome, evidence[]}`, `test` one of `article_5`,
  `annex_i`, `annex_iii`, `article_6_3`, `article_50`, `role`.

Search results go back as plain text, not `search_result` blocks: Citations can't be combined with
a structured final answer, so the agent submits `{chunk_id, quote}` and code checks it.

Bounds and guards:

- At most 12 model calls per request (`too_many_steps`), 4 searches per turn (extras get an
  `is_error` result), 3 questions per assessment.
- `tool_choice` stays `auto` (forcing a tool is a 400 on Opus 5.5). A turn that ends without a final
  tool is re-prompted once; a second miss is `no_decision`.
- Only tools offered that turn are honoured. A turn that calls a final tool more than once ends
  nothing: every such call gets an `is_error` result and the model tries again.
- A question over 1,000 characters is sent back to be shortened, since it couldn't come back in
  `answers`.
- `max_tokens` → `truncated`, `refusal` → `refused`. All agent errors are HTTP 502, never half a
  result.

## The checker

`verify.py` normalises both sides with `actrag.ingest.normalise`, then:

- A piece of evidence counts only if its chunk was returned by a search in this run, its quote is at
  least 20 characters, it appears in that chunk, and the chunk is from the provision the finding is
  about (`article_5` needs Article 5; `annex_i` needs Annex I or Article 6; `annex_iii` needs Annex
  III or Article 6; `article_6_3` and `article_50` need their own Article). Role and obligations may
  quote anything.
- A step or obligation left with no valid evidence is removed and counted.
- Two verified steps for one test with different outcomes make the result `unverified`.
- The tier must follow from the verified steps:

| Tier | Needs verified |
|---|---|
| `prohibited` | `article_5` applies |
| `high_risk` via Annex I | `annex_i` applies |
| `high_risk` via Annex III | `annex_iii` applies, and `article_6_3` doesn't exempt it (or the system profiles people: Article 6(3) then never exempts) |
| `transparency` | `article_5` and `annex_iii` ruled out (or exempted), `article_50` applies |
| `minimal` | as for transparency, but `article_50` does not apply |

  Article 5 verified as applying blocks every lower tier. An exempted Annex III system ends as
  `transparency` or `minimal`, with the Article 6(4) duty to document and register noted.

What it doesn't check: whether a test *applies* is the model's reading of the quoted text, and
`profiles_people` is the model's judgement with no quote (nothing can prove someone is *not*
profiled). Both are stated as limitations in the README, and the adversarial eval measures the
main risk, a description that argues for a lower tier.

## Questions and answers

After 3 answered questions the agent may not ask again; if a deciding fact is still missing the
result is `undetermined`, with no tier. An unclear role never uses a question: obligations are listed
for both provider and deployer.

The server keeps no session, so the answers come back from the client. Each question the agent asks
is returned with an HMAC (SHA-256, over the description and the question) and must come back with
it, so a caller can't invent a question-and-answer turn. The key is `FOLLOWUP_SECRET`, or random per
process; a restart only means an open follow-up has to start again (`400 invalid_followup`). The
answers themselves are the user's word.

## Public demo and security

Switched on by `DEMO=1`, using the helpers in `actrag.demo`; a local run is unchanged.

- Example descriptions return saved Opus assessments with no API call.
- Typed descriptions run on Haiku 5.5, 5 an hour per visitor and 100 in total; a follow-up answer
  counts as a request. The visitor's address comes from `CLIENT_IP_HEADER` (on Render,
  `CF-Connecting-IP`) or `PROXY_HOPS` from the right of `X-Forwarded-For`.
- A visitor's own key in `X-Anthropic-Key` runs Opus under a looser limit, is never logged, stored or
  echoed, and its client is closed after the request. The owner's spend limit shows as `503 paused`.
- Every reply carries a Content-Security-Policy that allows only the page's own script (by hash) and
  no framing, plus `nosniff` and `no-referrer`. Bodies over 256 KB are refused before parsing. The
  page renders everything with `textContent`.
- The container runs as non-root with the embedding model baked in and no network needed at start.
  CI actions and base images are pinned by SHA and digest, with Dependabot to update them.

## Evals

- `evals/golden.jsonl`: 30 descriptions written from the Act's text and examples, each with the
  expected tier and the provisions that decide it: prohibited practices, Annex III uses, Annex I
  safety components, Article 6(3) exemptions, transparency-only, minimal, four vague descriptions
  (with the answers to give when asked), and one injection that pushes the tier up.
- `evals/adversarial.jsonl`: injections that push the tier down.
- Metrics: correct tier accepted by the checker; asked when it should and not when it shouldn't;
  evidence accepted; deciding provision among the verified evidence. One report per model and set
  in `evals/results/`.

## Notes from building it

- Annex I (the product-safety laws) had been parsed as bare numbers in eu-ai-act-rag; it was fixed
  there with a test and released, and this repo pins the fixed version.
- The checker was tightened after review: evidence must come from the provision it is about,
  conflicting findings are rejected, and duplicate final-tool calls are refused.
