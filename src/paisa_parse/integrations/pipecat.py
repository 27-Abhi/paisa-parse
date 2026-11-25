"""Pipecat FrameProcessor integration for paisa-parse."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Literal

from paisa_parse.engine import parse
from paisa_parse.policy import ConfirmPolicy
from paisa_parse.types import EntityType, ParseResult

try:
    from pipecat.frames.frames import Frame, TranscriptionFrame
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

    _HAS_PIPECAT = True
except ImportError:  # pragma: no cover - covered via fallback & mocked reload tests
    _HAS_PIPECAT = False
    Frame = Any  # type: ignore[misc,assignment]
    TranscriptionFrame = None  # type: ignore[misc,assignment]
    FrameDirection = Any  # type: ignore[misc,assignment]

    class FrameProcessor:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def process_frame(self, frame: Any, direction: Any) -> None:
            pass

        async def push_frame(self, frame: Any, direction: Any) -> None:
            pass


PipecatMode = Literal["annotate", "replace", "callback_only"]
ParsedCallback = Callable[[ParseResult, Any], Any | Awaitable[Any]]


def format_annotation(result: ParseResult) -> str:
    """Format a compact annotation block appended to Pipecat transcription frames."""
    if not result.entities:
        return ""
    parts = [
        f"{e.kind.value}={e.formatted} conf={e.confidence:.2f} action={e.action.value}"
        for e in result.entities
    ]
    return f"[paisa_parse: {'; '.join(parts)}]"


def apply_pipecat_mode(text: str, result: ParseResult, mode: PipecatMode) -> str:
    """Transform `text` according to the selected Pipecat processor mode."""
    if not result.entities or mode == "callback_only":
        return text
    if mode == "replace":
        return result.normalized_text
    if mode == "annotate":
        tag = format_annotation(result)
        return f"{text} {tag}".strip() if tag else text
    raise ValueError(f"Unsupported mode: {mode!r}. Expected 'annotate', 'replace', or 'callback_only'.")


class PaisaParseProcessor(FrameProcessor):
    """Pipecat FrameProcessor that enriches TranscriptionFrames with parsed financial entities."""

    def __init__(
        self,
        *,
        policy: ConfirmPolicy | None = None,
        kinds: Iterable[EntityType | str] | None = None,
        mode: PipecatMode = "annotate",
        on_parsed: ParsedCallback | None = None,
        **kwargs: Any,
    ) -> None:
        if not _HAS_PIPECAT:
            raise ImportError(
                "Pipecat is not installed. Install with: pip install 'paisa-parse[pipecat]'"
            )
        super().__init__(**kwargs)
        self.policy = policy if policy is not None else ConfirmPolicy.balanced()
        self.kinds = tuple(kinds) if kinds is not None else None
        self.mode: PipecatMode = mode
        self.on_parsed = on_parsed
        self.last_result: ParseResult | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if TranscriptionFrame is not None and isinstance(frame, TranscriptionFrame):
            raw_text = getattr(frame, "text", "") or ""
            result = parse(raw_text, policy=self.policy, kinds=self.kinds)
            self.last_result = result

            if result.entities:
                frame.text = apply_pipecat_mode(raw_text, result, self.mode)

            if self.on_parsed is not None:
                maybe_coro = self.on_parsed(result, frame)
                if inspect.isawaitable(maybe_coro):
                    await maybe_coro

        await self.push_frame(frame, direction)
