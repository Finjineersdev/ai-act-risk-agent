# Assessment eval · claude-opus-5-5

Run on 2026-11-23 · 30 golden cases ([golden.jsonl](../golden.jsonl))

| Metric | Result |
|---|---|
| Correct tier, with the tier's deciding steps verified | 100% (30/30) |
| Asked a question when the description was too vague | 100% (4/4) |
| Didn't ask when the description was clear | 88% (23/26) |
| Evidence quotes found in the retrieved text | 99.7% (350/351) |
| Deciding provision among the verified evidence | 100% (30/30) |
| Rejected by the checker (unverified) | 0 |
| Errors (truncated, refused, too many steps, no decision) | 0 |

| Case | Kind | Expected | Got | Status | Asked | Pass | Time |
|---|---|---|---|---|---|---|---|
| P1 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 29s |
| P2 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 17s |
| P3 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 23s |
| P4 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 17s |
| P5 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 19s |
| H1 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 30s |
| H2 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 32s |
| H3 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 42s |
| H4 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 35s |
| H5 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 45s |
| H6 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 37s |
| I1 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 38s |
| I2 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 37s |
| I3 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 34s |
| E1 | exempted | minimal | minimal | assessed | 0 | ✓ | 24s |
| E2 | exempted | minimal | minimal | assessed | 0 | ✓ | 32s |
| E3 | exempted | minimal | minimal | assessed | 1 | ✓ | 48s |
| T1 | transparency | transparency | transparency | assessed | 0 | ✓ | 25s |
| T2 | transparency | transparency | transparency | assessed | 0 | ✓ | 31s |
| T3 | transparency | transparency | transparency | assessed | 0 | ✓ | 23s |
| T4 | transparency | transparency | transparency | assessed | 0 | ✓ | 26s |
| M1 | minimal | minimal | minimal | assessed | 0 | ✓ | 30s |
| M2 | minimal | minimal | minimal | assessed | 0 | ✓ | 24s |
| M3 | minimal | minimal | minimal | assessed | 0 | ✓ | 24s |
| M4 | minimal | minimal | minimal | assessed | 0 | ✓ | 24s |
| A1 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 35s |
| A2 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 39s |
| A3 | ambiguous | transparency | transparency | assessed | 1 | ✓ | 33s |
| A4 | ambiguous | minimal | minimal | assessed | 1 | ✓ | 24s |
| X1 | adversarial | minimal | minimal | assessed | 0 | ✓ | 20s |
