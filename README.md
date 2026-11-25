# paisa-parse

**Zero-dependency Hinglish & Indian-English spoken financial entity parser** with confidence scores, a confirm-back policy, and drop-in plugins for **Pipecat**, **LiveKit Agents**, and **MCP**.

Turns noisy ASR transcripts into structured Indian financial values:

- `"dedh lakh"` -> `Decimal("150000")`, formatted `"₹1,50,000"`, `action="confirm"` (`high_value_threshold`)
- `"paune do hazaar"` -> `Decimal("1750")`, formatted `"₹1,750"`
- `"nau aath saat chhe paanch chaar teen do ek shunya"` -> `"9876543210"` (`subtype="phone"`)
- `"rahul dot verma at ok icici"` -> `"rahul.verma@okicici"` (validated against ~75 NPCI PSP handles)
- `"IFSC SBIN triple zero ek do teen chaar"` -> `"SBIN0001234"` (RBI structure + bank prefix check + 5th-char `O->0` repair)

---

## Installation

Core library (pure Python 3.10+, **zero runtime dependencies**):

```bash
pip install paisa-parse
```

With optional voice-agent / tool integrations:

```bash
pip install "paisa-parse[pipecat]"
pip install "paisa-parse[livekit]"
pip install "paisa-parse[mcp]"
pip install "paisa-parse[all]"
```

---

## Quickstart

```python
from paisa_parse import ConfirmPolicy, parse

result = parse(
    "bhai rahul dot verma at ok icici pe dedh lakh bhej do",
    policy=ConfirmPolicy.balanced(language="hinglish"),
)

print(result.normalized_text)
# bhai rahul.verma@okicici pe ₹1,50,000 bhej do

for entity in result.entities:
    print(entity.kind.value, entity.value, entity.confidence, entity.action.value)
    if entity.confirm_prompt:
        print("  TTS confirm-back:", entity.confirm_prompt)
```

### Confirm-Back Policy Presets

Voice agents should not blindly execute a `₹1,50,000` transfer or trust an ambiguous ASR token like `"ded sau"` or `"SBINO001234"`. `ConfirmPolicy` outputs one of three actions (`accept`, `confirm`, `reprompt`) plus a TTS-ready `confirm_prompt` in `"en-IN"` or `"hinglish"`:

- `ConfirmPolicy.balanced()` (default): auto-accept `>= 0.85`, confirm `0.55–0.85` or amounts `>= ₹50,000`, reprompt `< 0.55`.
- `ConfirmPolicy.strict()`: always confirms `upi_id` and `ifsc`, and escalates amounts `>= ₹10,000`.
- `ConfirmPolicy.permissive()`: lower friction (`accept >= 0.75`, `high_value >= ₹5,00,000`).

---

## Framework Integrations

### 1. Pipecat (`FrameProcessor`)

Place `PaisaParseProcessor` right after your STT service in a Pipecat pipeline (`examples/pipecat_demo.py`):

```python
from paisa_parse import ConfirmPolicy
from paisa_parse.integrations.pipecat import PaisaParseProcessor

processor = PaisaParseProcessor(
    policy=ConfirmPolicy.balanced(language="hinglish"),
    mode="annotate",  # "annotate" | "replace" | "callback_only"
)
```

### 2. LiveKit Agents (`Agent` mixin & `stt_node` hook)

Attach `PaisaParseAgentMixin` to your `livekit.agents.Agent` subclass (`examples/livekit_demo.py`):

```python
from livekit.agents import Agent
from paisa_parse import ConfirmPolicy
from paisa_parse.integrations.livekit import PaisaParseAgentMixin, PaisaParseHook

class HinglishBankingAgent(PaisaParseAgentMixin, Agent):
    def __init__(self) -> None:
        super().__init__()
        self.paisa_hook = PaisaParseHook(
            policy=ConfirmPolicy.strict(language="en-IN"),
            inject_context=True,
        )
```

### 3. Model Context Protocol (MCP) Server

Run over stdio:

```bash
paisa-parse-mcp
```

Exposes four tools: `tool_parse_financial_text`, `tool_parse_amount`, `tool_validate_upi_id`, and `tool_validate_ifsc_code`.

### 4. CLI

```bash
paisa-parse "bhai rahul dot verma at ok icici pe dedh lakh bhej do, IFSC SBIN triple zero ek do teen chaar" --json
```

---

## Prior Art & Differentiation

**NVIDIA NeMo Text Processing** provides mature WFST-based Inverse Text Normalization (ITN) for Devanagari Hindi (`hi`), and is the right tool if you want general-purpose sentence-level WFST normalization inside a NeMo/Riva stack.

`paisa-parse` targets a distinct, voice-agent-specific gap:

1. **Romanized Hinglish + Mixed Indian-English**: handles what Whisper, Deepgram, Sarvam, and Google STT emit in practice (`dedh lakh`, `sava do crore`, `chhattees hazaar`, `teen baar shunya`, `rahul dot verma at ok icici`), alongside Devanagari digits/words.
2. **Colloquial Indian Fractions**: native support for `dedh` (1.5), `dhai` (2.5), `sava` (+0.25), `paune` (-0.25), `saade` (+0.5), `aadha` (0.5), and `paav` (0.25) across Indian scales.
3. **Domain Validators**: UPI ID parsing with ~75 NPCI PSP handles (and email rejection) plus 11-character IFSC parsing with RBI bank prefixes and 5th-character `O -> 0` repair.
4. **Confidence + Confirm-Back Policy**: calibrates confidence for ASR ambiguities (`oh` -> `0`, `so` -> `100`, unknown PSP/bank, truncated phone/IFSC) and produces ready-to-speak `accept` / `confirm` / `reprompt` prompts.
5. **Zero-Dependency Portability**: pure Python (`pip install paisa-parse`), sub-millisecond latency, with native Pipecat, LiveKit Agents, and MCP adapters.

---

## Stress-Test Benchmark Results

Evaluated on [`benchmarks/stress_test.json`](benchmarks/stress_test.json) (130 realistic & adversarial Hinglish financial utterances across 7 categories) using `python benchmarks/run_benchmark.py --no-write`:

- **Utterance Exact-Match Accuracy**: **100.00%** (`130/130`)
- **Entity Precision / Recall / F1**: **1.0000 / 1.0000 / 1.0000** (`TP=134, FP=0, FN=0`)
- **Confirm-Back Policy Accuracy**: **100.00%** (`134` matched entities)
- **Latency**: p50 = **0.250 ms**, p95 = **0.544 ms**, p99 = **0.809 ms**

| Category | Exact / Total | Accuracy |
| --- | ---: | ---: |
| `colloquial_fractions` | 25 / 25 | 100.00% |
| `compound_amounts` | 20 / 20 | 100.00% |
| `spoken_digits` | 20 / 20 | 100.00% |
| `upi_ids` | 20 / 20 | 100.00% |
| `ifsc_codes` | 15 / 15 | 100.00% |
| `multi_entity` | 15 / 15 | 100.00% |
| `adversarial_negatives` | 15 / 15 | 100.00% |

> **Scope note**: `stress_test.json` is an author-curated stress suite (not an external multi-vendor ASR corpus). Real-world audio transcripts with unseen regional spellings or severe acoustic misrecognitions may score lower; contributions of real failure utterances are welcome.

---

## Adoption & Community Status (Honest Reporting)

Current status as of **v0.1.0** (pre-publish local release):

- **PyPI Downloads**: `0` (package not yet uploaded to PyPI; see [`PUBLISHING.md`](PUBLISHING.md) for upload steps)
- **GitHub Stars / Open Issues**: `0 stars / 0 issues` (repository not yet pushed publicly)
- **Pipecat / LiveKit Community Listings**: `Pending submission` (adapters and demos included; community PR/listing links will be added once published)

---

## License

MIT
