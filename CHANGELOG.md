# Changelog

All notable changes to `paisa-parse` are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1] - 2026-11-26

### Added
- PEP 561 `py.typed` marker and `"Typing :: Typed"` classifier for type-checker support (`mypy` / `pyright`).
- `python -m paisa_parse` (`__main__.py`) module execution support.
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and GitHub Actions Trusted Publishing workflow (`.github/workflows/publish.yml`).
- PyPI version, downloads, Python version, license, and CI badges in `README.md`.

### Changed
- Updated `pyproject.toml` author metadata and project URLs (`Homepage`, `Repository`, `Documentation`, `Changelog`, `Issues`) to `https://github.com/27-Abhi/paisa-parse`.

## [0.1.0] - 2026-11-25

### Added
- Zero-dependency core parser for Hinglish & Indian-English spoken financial entities (`amount`, `digits`, `upi_id`, `ifsc`).
- Colloquial Hindi fraction support (`dedh`, `dhai`, `sava`, `paune`, `saade`, `aadha`, `paav`), Indian comma formatting (`format_inr`), and Devanagari normalization.
- Confidence scoring & `ConfirmPolicy` (`balanced`, `strict`, `permissive`) with `en-IN` and `hinglish` TTS readback prompts.
- Drop-in integrations for Pipecat (`PaisaParseProcessor`), LiveKit Agents (`PaisaParseHook`, `PaisaParseAgentMixin`), and MCP (`paisa-parse-mcp`).
- 82 unit/integration tests and a 130-case Hinglish stress-test benchmark (`benchmarks/stress_test.json`).
