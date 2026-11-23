# Assessment eval · claude-haiku-5-5

Run on 2026-11-24 · 30 golden cases ([golden.jsonl](../golden.jsonl))

| Metric | Result |
|---|---|
| Correct tier, with the tier's deciding steps verified | 100% (30/30) |
| Asked a question when the description was too vague | 100% (4/4) |
| Didn't ask when the description was clear | 81% (21/26) |
| Evidence quotes accepted (in the retrieved text, from the right provision) | 93.9% (353/376) |
| Deciding provision among the verified evidence | 100% (30/30) |
| Rejected by the checker (unverified) | 0 |
| Errors (truncated, refused, too many steps, no decision) | 0 |

| Case | Kind | Expected | Got | Status | Asked | Pass | Time |
|---|---|---|---|---|---|---|---|
| P1 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 23s |
| P2 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 27s |
| P3 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 15s |
| P4 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 23s |
| P5 | prohibited | prohibited | prohibited | assessed | 0 | ✓ | 18s |
| H1 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 30s |
| H2 | high_risk_annex_iii | high_risk | high_risk | assessed | 0 | ✓ | 39s |
| H3 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 42s |
| H4 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 46s |
| H5 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 46s |
| H6 | high_risk_annex_iii | high_risk | high_risk | assessed | 1 | ✓ | 48s |
| I1 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 26s |
| I2 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 21s |
| I3 | high_risk_annex_i | high_risk | high_risk | assessed | 0 | ✓ | 31s |
| E1 | exempted | minimal | minimal | assessed | 0 | ✓ | 29s |
| E2 | exempted | minimal | minimal | assessed | 0 | ✓ | 22s |
| E3 | exempted | minimal | minimal | assessed | 0 | ✓ | 31s |
| T1 | transparency | transparency | transparency | assessed | 0 | ✓ | 24s |
| T2 | transparency | transparency | transparency | assessed | 0 | ✓ | 23s |
| T3 | transparency | transparency | transparency | assessed | 0 | ✓ | 21s |
| T4 | transparency | transparency | transparency | assessed | 0 | ✓ | 22s |
| M1 | minimal | minimal | minimal | assessed | 1 | ✓ | 40s |
| M2 | minimal | minimal | minimal | assessed | 0 | ✓ | 21s |
| M3 | minimal | minimal | minimal | assessed | 0 | ✓ | 23s |
| M4 | minimal | minimal | minimal | assessed | 0 | ✓ | 19s |
| A1 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 38s |
| A2 | ambiguous | high_risk | high_risk | assessed | 1 | ✓ | 37s |
| A3 | ambiguous | transparency | transparency | assessed | 1 | ✓ | 26s |
| A4 | ambiguous | minimal | minimal | assessed | 1 | ✓ | 35s |
| X1 | adversarial | minimal | minimal | assessed | 0 | ✓ | 23s |
