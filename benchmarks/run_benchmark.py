"""Reproducible stress-test benchmark runner for paisa-parse."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from paisa_parse import ConfirmPolicy, EntityType, parse  # noqa: E402


def _norm_value(kind: str, val: Any) -> str:
    if kind == EntityType.AMOUNT.value:
        d = Decimal(str(val))
        if d == d.to_integral_value():
            return str(int(d))
        return f"{d:f}".rstrip("0").rstrip(".")
    return str(val)


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(round((pct / 100.0) * (len(sorted_vals) - 1))))
    return sorted_vals[idx]


def run_benchmark(
    dataset_path: Path | None = None,
    write_outputs: bool = True,
) -> dict[str, Any]:
    """Run the stress-test suite and compute exact-match, F1, policy, and latency metrics."""
    ds_path = dataset_path or (Path(__file__).resolve().parent / "stress_test.json")
    cases = json.loads(ds_path.read_text(encoding="utf-8"))
    policy = ConfirmPolicy.balanced()

    total = len(cases)
    exact_matches = 0
    tp = fp = fn = 0
    policy_total = 0
    policy_correct = 0
    latencies_ms: list[float] = []
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "exact": 0})
    failures: list[dict[str, Any]] = []

    # Warm up regex/lexicon tables
    parse("dedh lakh", policy=policy)

    for case in cases:
        t0 = time.perf_counter_ns()
        res = parse(case["text"], policy=policy)
        dt_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
        latencies_ms.append(dt_ms)

        expected = [
            (e["kind"], _norm_value(e["kind"], e["value"]), e.get("action"))
            for e in case["expected"]
        ]
        actual = [
            (e.kind.value, _norm_value(e.kind.value, e.value), e.action.value)
            for e in res.entities
        ]

        cat = case["category"]
        by_cat[cat]["total"] += 1

        exp_kv = [(k, v) for k, v, _ in expected]
        act_kv = [(k, v) for k, v, _ in actual]

        # Match entities in order/bag for P/R/F1 and policy accuracy
        remaining_act = list(actual)
        matched_here = 0
        for ek, ev, ea in expected:
            hit_idx = next(
                (idx for idx, (ak, av, _) in enumerate(remaining_act) if ak == ek and av == ev),
                None,
            )
            if hit_idx is not None:
                _, _, aa = remaining_act.pop(hit_idx)
                tp += 1
                matched_here += 1
                if ea is not None:
                    policy_total += 1
                    if aa == ea:
                        policy_correct += 1
            else:
                fn += 1
        fp += len(remaining_act)

        is_exact = exp_kv == act_kv and all(
            (ea is None or aa == ea)
            for (_, _, ea), (_, _, aa) in zip(expected, actual, strict=False)
        )
        if is_exact:
            exact_matches += 1
            by_cat[cat]["exact"] += 1
        else:
            failures.append(
                {
                    "id": case["id"],
                    "category": cat,
                    "text": case["text"],
                    "expected": expected,
                    "actual": actual,
                }
            )

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 1.0
    latencies_ms.sort()

    category_summary = {
        cat: {
            "total": stats["total"],
            "exact": stats["exact"],
            "accuracy": round(stats["exact"] / stats["total"], 4) if stats["total"] else 1.0,
        }
        for cat, stats in by_cat.items()
    }

    report: dict[str, Any] = {
        "dataset": str(ds_path.name),
        "total_cases": total,
        "exact_matches": exact_matches,
        "utterance_accuracy": round(exact_matches / total, 4) if total else 0.0,
        "entity_metrics": {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "policy_accuracy": round(policy_correct / policy_total, 4) if policy_total else 1.0,
        "policy_matched_entities": policy_total,
        "latency_ms": {
            "p50": round(_percentile(latencies_ms, 50), 3),
            "p95": round(_percentile(latencies_ms, 95), 3),
            "p99": round(_percentile(latencies_ms, 99), 3),
            "mean": round(sum(latencies_ms) / len(latencies_ms), 3) if latencies_ms else 0.0,
        },
        "categories": category_summary,
        "failures": failures,
    }

    if write_outputs:
        out_dir = ds_path.parent
        (out_dir / "results.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (out_dir / "RESULTS.md").write_text(_render_markdown(report), encoding="utf-8")

    return report


def _render_markdown(report: dict[str, Any]) -> str:
    em = report["entity_metrics"]
    lat = report["latency_ms"]
    lines = [
        "# paisa-parse Stress-Test Benchmark Results",
        "",
        f"- **Dataset**: `{report['dataset']}` ({report['total_cases']} Hinglish & Indian-English utterances)",
        "- **Policy**: `ConfirmPolicy.balanced()` (auto-accept >= 0.85, confirm >= 0.55 or >= ₹50,000, reprompt < 0.55)",
        f"- **Utterance Exact-Match Accuracy**: **{report['utterance_accuracy'] * 100:.2f}%** ({report['exact_matches']}/{report['total_cases']})",
        f"- **Entity Precision / Recall / F1**: **{em['precision']:.4f} / {em['recall']:.4f} / {em['f1']:.4f}** (TP={em['true_positives']}, FP={em['false_positives']}, FN={em['false_negatives']})",
        f"- **Confirm-Back Policy Accuracy**: **{report['policy_accuracy'] * 100:.2f}%** ({report['policy_matched_entities']} matched entities)",
        f"- **Latency**: p50 = **{lat['p50']:.3f} ms**, p95 = **{lat['p95']:.3f} ms**, p99 = **{lat['p99']:.3f} ms**",
        "",
        "## Per-Category Accuracy",
        "",
        "| Category | Exact / Total | Accuracy |",
        "| --- | ---: | ---: |",
    ]
    for cat, stats in report["categories"].items():
        lines.append(
            f"| `{cat}` | {stats['exact']} / {stats['total']} | {stats['accuracy'] * 100:.2f}% |"
        )
    lines.append("")
    if report["failures"]:
        lines.append(f"## Failures ({len(report['failures'])})")
        lines.append("")
        for fail in report["failures"]:
            lines.append(
                f"- `{fail['id']}` ({fail['category']}): {fail['text']!r} -> expected `{fail['expected']}`, got `{fail['actual']}`"
            )
    else:
        lines.append("## Failures")
        lines.append("")
        lines.append("None (0 failures on this run).")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run paisa-parse stress-test benchmark.")
    parser.add_argument("--check", action="store_true", help="Exit non-zero if accuracy < 90% or F1 < 0.92.")
    parser.add_argument("--no-write", action="store_true", help="Do not overwrite results.json / RESULTS.md.")
    args = parser.parse_args()

    report = run_benchmark(write_outputs=not args.no_write)
    print(
        f"Utterance exact-match: {report['exact_matches']}/{report['total_cases']} "
        f"({report['utterance_accuracy'] * 100:.2f}%), "
        f"F1={report['entity_metrics']['f1']:.4f}, "
        f"Policy={report['policy_accuracy'] * 100:.2f}%, "
        f"p50={report['latency_ms']['p50']:.3f}ms"
    )
    if report["failures"]:
        for fail in report["failures"]:
            print(f"  FAIL {fail['id']}: expected={fail['expected']} actual={fail['actual']}")

    if args.check and (
        report["utterance_accuracy"] < 0.90 or report["entity_metrics"]["f1"] < 0.92
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
