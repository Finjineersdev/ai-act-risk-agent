# Assessment eval · claude-opus-5-5

Run on 2026-11-23 · 30 golden cases ([golden.jsonl](../golden.jsonl))

| Metric | Result |
|---|---|
| Correct tier, with the tier's deciding steps verified | 100% (30/30) |
| Asked a question when the description was too vague | 100% (4/4) |
| Didn't ask when the description was clear | 92% (24/26) |
| Evidence quotes accepted (in the retrieved text, from the right provision) | 98.8% (340/344) |
| Deciding provision among the verified evidence | 100% (30/30) |
| Rejected by the checker (unverified) | 0 |
| Errors (truncated, refused, too many steps, no decision) | 0 |

| Case | Kind | Expected | Got | Status | Asked | Pass | Time |
|---|---|---|---|---|---|---|---|
| P1 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 23s |
| P2 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 18s |
| P3 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 16s |
| P4 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 26s |
| P5 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 16s |
| H1 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 25s |
| H2 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 34s |
| H3 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 38s |
| H4 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 34s |
| H5 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 41s |
| H6 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 32s |
| I1 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 34s |
| I2 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 34s |
| I3 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 35s |
| E1 | exempted | minimal | minimal | assessed | 0 | ✓ | 25s |
| E2 | exempted | minimal | minimal | assessed | 0 | ✓ | 26s |
| E3 | exempted | minimal | minimal | assessed | 1 | ✓ | 40s |
| T1 | transparency | transparency | transparency | assessed | 0 | ✓ | 26s |
| T2 | transparency | transparency | transparency | assessed | 0 | ✓ | 29s |
| T3 | transparency | transparency | transparency | assessed | 0 | ✓ | 27s |
| T4 | transparency | transparency | transparency | assessed | 0 | ✓ | 26s |
| M1 | minimal | minimal | minimal | assessed | 0 | ✓ | 20s |
| M2 | minimal | minimal | minimal | assessed | 0 | ✓ | 23s |
| M3 | minimal | minimal | minimal | assessed | 0 | ✓ | 18s |
| M4 | minimal | minimal | minimal | assessed | 0 | ✓ | 24s |
| A1 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 48s |
| A2 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 40s |
| A3 | ambiguous | transparency | transparency | assessed | 1 | ✓ | 32s |
| A4 | ambiguous | minimal | minimal | assessed | 1 | ✓ | 30s |
| X1 | adversarial | minimal | minimal | assessed | 0 | ✓ | 22s |
