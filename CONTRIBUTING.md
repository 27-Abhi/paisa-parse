# Contributing to `paisa-parse`

Contributions—especially real-world Hinglish ASR transcripts, regional number/fraction spellings, and new NPCI UPI/RBI IFSC entries—are very welcome.

## Local Development Setup

```bash
git clone https://github.com/27-Abhi/paisa-parse.git
cd paisa-parse
python -m pip install -e ".[dev]"
```

## Running Checks

```bash
ruff check src tests benchmarks examples
pytest -v
python benchmarks/run_benchmark.py --check
```

## Adding New Test Cases

- Add unit tests under `tests/`.
- Add realistic or adversarial utterances (with expected entities and `ConfirmAction`) to `benchmarks/stress_test.json` and re-run `python benchmarks/run_benchmark.py --check`.
