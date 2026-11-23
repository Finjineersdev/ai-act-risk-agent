# Assessment eval · claude-opus-5-5

Run on 2026-11-23 · 30 golden cases ([golden.jsonl](../golden.jsonl))

| Metric | Result |
|---|---|
| Correct tier, with the tier's deciding steps verified | 100% (30/30) |
| Asked a question when the description was too vague | 100% (4/4) |
| Didn't ask when the description was clear | 92% (24/26) |
| Evidence quotes accepted (in the retrieved text, from the right provision) | 97.8% (316/323) |
| Deciding provision among the verified evidence | 97% (29/30) |
| Rejected by the checker (unverified) | 0 |
| Errors (truncated, refused, too many steps, no decision) | 0 |

| Case | Kind | Expected | Got | Status | Asked | Pass | Time |
|---|---|---|---|---|---|---|---|
| P1 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 23s |
| P2 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 14s |
| P3 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 16s |
| P4 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 16s |
| P5 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 12s |
| H1 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 27s |
| H2 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 30s |
| H3 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 43s |
| H4 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 31s |
| H5 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 48s |
| H6 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 38s |
| I1 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 40s |
| I2 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 35s |
| I3 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 31s |
| E1 | exempted | minimal | minimal | assessed | 0 | ✓ | 24s |
| E2 | exempted | minimal | minimal | assessed | 0 | ✓ | 26s |
| E3 | exempted | minimal | minimal | assessed | 1 | ✓ | 36s |
| T1 | transparency | transparency | transparency | assessed | 0 | ✓ | 27s |
| T2 | transparency | transparency | transparency | assessed | 0 | ✓ | 29s |
| T3 | transparency | transparency | transparency | assessed | 0 | ✓ | 24s |
| T4 | transparency | transparency | transparency | assessed | 0 | ✓ | 28s |
| M1 | minimal | minimal | minimal | assessed | 0 | ✓ | 25s |
| M2 | minimal | minimal | minimal | assessed | 0 | ✓ | 26s |
| M3 | minimal | minimal | minimal | assessed | 0 | ✓ | 20s |
| M4 | minimal | minimal | minimal | assessed | 0 | ✓ | 19s |
| A1 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 35s |
| A2 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 45s |
| A3 | ambiguous | transparency | transparency | assessed | 1 | ✓ | 34s |
| A4 | ambiguous | minimal | minimal | assessed | 1 | ✓ | 26s |
| X1 | adversarial | minimal | minimal | assessed | 0 | ✓ | 17s |
