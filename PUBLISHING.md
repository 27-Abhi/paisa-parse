# Publishing & Community Launch Checklist

This guide covers releasing `paisa-parse` to PyPI, listing the adapters on Pipecat & LiveKit community pages, and tracking honest adoption numbers.

## 1. Pre-Publish Verification

```bash
ruff check src tests benchmarks examples
pytest -v
python benchmarks/run_benchmark.py --check
```

## 2. Build & Upload to PyPI

Install build/publish tooling (or use `uv`):

```bash
python -m pip install --upgrade build twine
python -m build
twine check dist/*
```

Test on TestPyPI first:

```bash
twine upload --repository testpypi dist/*
```

Publish to PyPI:

```bash
twine upload dist/*
# Or with uv:
# uv build && uv publish
```

Verify fresh install in a clean environment:

```bash
pip install paisa-parse
paisa-parse "bhai dedh lakh bhej do rahul dot verma at ok icici pe" --json
```

## 3. Submit to Pipecat & LiveKit Community Pages

1. **Pipecat**: Open a PR or community showcase post linking `PaisaParseProcessor` (`src/paisa_parse/integrations/pipecat.py`) and `examples/pipecat_demo.py`.
2. **LiveKit Agents**: Share `PaisaParseHook` and `PaisaParseAgentMixin` (`src/paisa_parse/integrations/livekit.py`) in the LiveKit community plugins/recipes forum or showcase PR.
3. **MCP Registry / Directories**: Submit `paisa-parse-mcp` (`src/paisa_parse/integrations/mcp_server.py`) with its four tool schemas.

## 4. Track Real Usage Numbers Honestly

Once published, record real metrics in `README.md`:

```bash
pip install pypistats
pypistats recent paisa-parse
pypistats overall paisa-parse
```

Update `README.md` with actual PyPI download counts, GitHub stars/issues, and live community listing URLs.
