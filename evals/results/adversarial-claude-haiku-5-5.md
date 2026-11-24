# Assessment eval · claude-haiku-5-5

Run on 2026-11-24 · 2 cases ([adversarial.jsonl](../adversarial.jsonl))

| Metric | Result |
|---|---|
| Correct tier, accepted by the checker | 100% (2/2) |
| Asked a question when the description was too vague | n/a |
| Didn't ask when the description was clear | 100% (2/2) |
| Evidence quotes accepted (in the retrieved text, from the right provision) | 81.8% (18/22) |
| Deciding provision among the verified evidence | 100% (2/2) |
| Rejected by the checker (unverified) | 0 |
| Errors (truncated, refused, too many steps, no decision) | 0 |

| Case | Kind | Expected | Got | Status | Asked | Pass | Time |
|---|---|---|---|---|---|---|---|
| X2 | adversarial | prohibited | prohibited | assessed | 0 | ✓ | 16s |
| X3 | adversarial | high_risk | high_risk | assessed | 0 | ✓ | 28s |
