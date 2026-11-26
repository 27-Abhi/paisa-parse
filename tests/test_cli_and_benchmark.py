"""Tests for the CLI and the 130-case stress-test benchmark gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from paisa_parse.cli import main as cli_main

ROOT = Path(__file__).resolve().parent.parent


def test_cli_json_output(capsys: Any) -> None:
    exit_code = cli_main(
        [
            "dedh lakh bhejo rahul dot verma at ok icici",
            "--policy",
            "balanced",
            "--lang",
            "hinglish",
            "--json",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["needs_confirmation"] is True
    assert len(payload["entities"]) == 2
    assert payload["entities"][0]["value"] == 150000
    assert payload["entities"][1]["value"] == "rahul.verma@okicici"


def test_cli_human_output_and_kinds_filter(capsys: Any) -> None:
    exit_code = cli_main(
        [
            "dedh lakh bhejo rahul@okicici",
            "--kinds",
            "amount",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "₹1,50,000" in out
    assert "Entities (1):" in out
    assert "[upi_id]" not in out


def test_stress_test_benchmark_meets_quality_gate() -> None:
    bench_dir = ROOT / "benchmarks"
    if str(bench_dir) not in sys.path:
        sys.path.insert(0, str(bench_dir))
    from run_benchmark import run_benchmark

    report = run_benchmark(write_outputs=False)
    assert report["total_cases"] == 130
    assert report["utterance_accuracy"] >= 0.95
    assert report["entity_metrics"]["f1"] >= 0.96
    assert report["policy_accuracy"] >= 0.95


def test_package_version_and_py_typed() -> None:
    import paisa_parse

    assert paisa_parse.__version__ == "0.1.1"
    assert (ROOT / "src" / "paisa_parse" / "py.typed").is_file()
