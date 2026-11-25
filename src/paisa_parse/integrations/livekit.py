"""LiveKit Agents integration hook & Agent mixin for paisa-parse."""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterable, Callable, Iterable
from typing import Any, Literal

from paisa_parse.engine import parse
from paisa_parse.policy import ConfirmPolicy
from paisa_parse.types import EntityType, ParseResult

LiveKitMode = Literal["annotate", "replace", "callback_only"]


def _extract_message_text(message: Any) -> str:
    content = getattr(message, "text_content", None)
    if callable(content):
        return str(content() or "")
    if isinstance(content, str):
        return content
    raw = getattr(message, "content", "")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return " ".join(str(part) for part in raw if isinstance(part, str))
    return ""


def _build_system_guidance(result: ParseResult) -> str:
    summary = [
        {
            "kind": e.kind.value,
            "value": e.to_dict()["value"],
            "formatted": e.formatted,
            "confidence": round(e.confidence, 3),
            "action": e.action.value,
            "confirm_prompt": e.confirm_prompt,
        }
        for e in result.entities
    ]
    guidance = (
        "[paisa_parse] Parsed Indian financial entities: "
        + json.dumps(summary, ensure_ascii=False)
    )
    prompts = [e.confirm_prompt for e in result.entities if e.confirm_prompt]
    if prompts:
        guidance += " Confirmation policy advises asking the user: " + " | ".join(prompts)
    return guidance


class PaisaParseHook:
    """Reusable hook for LiveKit Agents `on_user_turn_completed` and `stt_node`."""

    def __init__(
        self,
        *,
        policy: ConfirmPolicy | None = None,
        kinds: Iterable[EntityType | str] | None = None,
        mode: LiveKitMode = "annotate",
        inject_context: bool = True,
        on_parsed: Callable[[ParseResult, Any, Any], Any] | None = None,
    ) -> None:
        self.policy = policy if policy is not None else ConfirmPolicy.balanced()
        self.kinds = tuple(kinds) if kinds is not None else None
        self.mode: LiveKitMode = mode
        self.inject_context = inject_context
        self.on_parsed = on_parsed
        self.last_result: ParseResult | None = None

    async def on_user_turn_completed(self, turn_ctx: Any, new_message: Any) -> ParseResult:
        """Parse the finalized user message and optionally inject system guidance into `turn_ctx`."""
        text = _extract_message_text(new_message)
        result = parse(text, policy=self.policy, kinds=self.kinds)
        self.last_result = result

        if result.entities and self.inject_context and hasattr(turn_ctx, "add_message"):
            turn_ctx.add_message(
                role="system",
                content=_build_system_guidance(result),
            )

        if self.on_parsed is not None:
            maybe_coro = self.on_parsed(result, turn_ctx, new_message)
            if inspect.isawaitable(maybe_coro):
                await maybe_coro

        return result

    async def wrap_stt_stream(self, stt_stream: AsyncIterable[Any]) -> AsyncIterable[Any]:
        """Wrap a LiveKit `stt_node` async stream to normalize final transcripts on the fly."""
        async for event in stt_stream:
            event_type = getattr(event, "type", None)
            type_name = getattr(event_type, "name", str(event_type))
            alternatives = getattr(event, "alternatives", None)

            if "FINAL_TRANSCRIPT" in type_name and alternatives:
                alt0 = alternatives[0]
                raw_text = getattr(alt0, "text", "") or ""
                result = parse(raw_text, policy=self.policy, kinds=self.kinds)
                self.last_result = result
                if result.entities and self.mode == "replace":
                    alt0.text = result.normalized_text
                elif result.entities and self.mode == "annotate":
                    tag = "; ".join(f"{e.kind.value}={e.formatted}" for e in result.entities)
                    alt0.text = f"{raw_text} [paisa_parse: {tag}]".strip()

                if self.on_parsed is not None:
                    maybe_coro = self.on_parsed(result, None, event)
                    if inspect.isawaitable(maybe_coro):
                        await maybe_coro

            yield event


class PaisaParseAgentMixin:
    """Mixin for `livekit.agents.Agent` subclasses to run paisa-parse on every user turn."""

    paisa_hook: PaisaParseHook

    def init_paisa_hook(self, **kwargs: Any) -> PaisaParseHook:
        self.paisa_hook = PaisaParseHook(**kwargs)
        return self.paisa_hook

    async def on_user_turn_completed(self, turn_ctx: Any, new_message: Any) -> None:
        if not hasattr(self, "paisa_hook"):
            self.paisa_hook = PaisaParseHook()
        await self.paisa_hook.on_user_turn_completed(turn_ctx, new_message)
        super_method = getattr(super(), "on_user_turn_completed", None)
        if super_method is not None:
            await super_method(turn_ctx, new_message)
