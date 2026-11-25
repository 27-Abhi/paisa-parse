# paisa-parse Stress-Test Benchmark Results

- **Dataset**: `stress_test.json` (130 Hinglish & Indian-English utterances)
- **Policy**: `ConfirmPolicy.balanced()` (auto-accept >= 0.85, confirm >= 0.55 or >= ₹50,000, reprompt < 0.55)
- **Utterance Exact-Match Accuracy**: **100.00%** (130/130)
- **Entity Precision / Recall / F1**: **1.0000 / 1.0000 / 1.0000** (TP=134, FP=0, FN=0)
- **Confirm-Back Policy Accuracy**: **100.00%** (134 matched entities)
- **Latency**: p50 = **0.250 ms**, p95 = **0.544 ms**, p99 = **0.809 ms**

## Per-Category Accuracy

| Category | Exact / Total | Accuracy |
| --- | ---: | ---: |
| `colloquial_fractions` | 25 / 25 | 100.00% |
| `compound_amounts` | 20 / 20 | 100.00% |
| `spoken_digits` | 20 / 20 | 100.00% |
| `upi_ids` | 20 / 20 | 100.00% |
| `ifsc_codes` | 15 / 15 | 100.00% |
| `multi_entity` | 15 / 15 | 100.00% |
| `adversarial_negatives` | 15 / 15 | 100.00% |

## Failures

None (0 failures on this run).
