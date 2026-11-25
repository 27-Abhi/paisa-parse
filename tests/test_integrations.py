"""Tests for Pipecat, LiveKit Agents, and MCP integrations."""

from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass
from enum import Enum
from typing import Any

from paisa_parse import ConfirmPolicy
from paisa_parse.integrations import livekit as livekit_mod
from paisa_parse.integrations import mcp_server as mcp_mod
from paisa_parse.integrations import pipecat as pipecat_mod


def _run_coro(coro: Any) -> Any:
    """Drive a pure-Python coroutine without creating an OS event-loop socketpair."""
    try:
        while True:
            coro.send(None)
    except StopIteration as exc:
        return exc.value


def test_pipecat_pure_helpers() -> None:
    from paisa_parse import parse

    res = parse("dedh hazaar bhejo")
    annotated = pipecat_mod.apply_pipecat_mode("dedh hazaar bhejo", res, "annotate")
    replaced = pipecat_mod.apply_pipecat_mode("dedh hazaar bhejo", res, "replace")
    unchanged = pipecat_mod.apply_pipecat_mode("dedh hazaar bhejo", res, "callback_only")

    assert "[paisa_parse:" in annotated
    assert "₹1,500" in annotated
    assert replaced == "₹1,500 bhejo"
    assert unchanged == "dedh hazaar bhejo"


def test_pipecat_processor_with_mocked_pipecat(monkeypatch: Any) -> None:
    # Build minimal fake pipecat modules matching real FrameProcessor / TranscriptionFrame APIs
    frames_mod = types.ModuleType("pipecat.frames.frames")
    proc_mod = types.ModuleType("pipecat.processors.frame_processor")
    pipecat_pkg = types.ModuleType("pipecat")
    frames_pkg = types.ModuleType("pipecat.frames")
    proc_pkg = types.ModuleType("pipecat.processors")

    class Frame:
        pass

    class TranscriptionFrame(Frame):
        def __init__(self, text: str) -> None:
            self.text = text

    class FrameDirection(Enum):
        DOWNSTREAM = 1

    class FrameProcessor:
        def __init__(self, **kwargs: Any) -> None:
            self.pushed: list[tuple[Any, Any]] = []

        async def process_frame(self, frame: Any, direction: Any) -> None:
            pass

        async def push_frame(self, frame: Any, direction: Any) -> None:
            self.pushed.append((frame, direction))

    frames_mod.Frame = Frame  # type: ignore[attr-defined]
    frames_mod.TranscriptionFrame = TranscriptionFrame  # type: ignore[attr-defined]
    proc_mod.FrameDirection = FrameDirection  # type: ignore[attr-defined]
    proc_mod.FrameProcessor = FrameProcessor  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "pipecat", pipecat_pkg)
    monkeypatch.setitem(sys.modules, "pipecat.frames", frames_pkg)
    monkeypatch.setitem(sys.modules, "pipecat.frames.frames", frames_mod)
    monkeypatch.setitem(sys.modules, "pipecat.processors", proc_pkg)
    monkeypatch.setitem(sys.modules, "pipecat.processors.frame_processor", proc_mod)

    reloaded = importlib.reload(pipecat_mod)
    try:
        seen: list[str] = []
        proc = reloaded.PaisaParseProcessor(
            mode="replace",
            on_parsed=lambda res, frame: seen.append(res.normalized_text),
        )
        t_frame = TranscriptionFrame("dedh lakh bhejo")
        other_frame = Frame()

        _run_coro(proc.process_frame(t_frame, FrameDirection.DOWNSTREAM))
        _run_coro(proc.process_frame(other_frame, FrameDirection.DOWNSTREAM))

        assert t_frame.text == "₹1,50,000 bhejo"
        assert seen == ["₹1,50,000 bhejo"]
        assert len(proc.pushed) == 2
        assert proc.last_result is not None
        assert proc.last_result.best().formatted == "₹1,50,000"
    finally:
        monkeypatch.undo()
        importlib.reload(pipecat_mod)


def test_livekit_hook_and_agent_mixin() -> None:
    class FakeChatCtx:
        def __init__(self) -> None:
            self.messages: list[tuple[str, str]] = []

        def add_message(self, *, role: str, content: str) -> None:
            self.messages.append((role, content))

    @dataclass
    class FakeMsg:
        text_content: str

    class BaseAgent:
        def __init__(self) -> None:
            self.base_called = False

        async def on_user_turn_completed(self, turn_ctx: Any, new_message: Any) -> None:
            self.base_called = True

    class MyAgent(livekit_mod.PaisaParseAgentMixin, BaseAgent):
        def __init__(self) -> None:
            super().__init__()
            self.init_paisa_hook(policy=ConfirmPolicy.balanced(language="hinglish"))

    agent = MyAgent()
    ctx = FakeChatCtx()
    msg = FakeMsg("rahul dot verma at ok icici pe dedh lakh bhejo")
    _run_coro(agent.on_user_turn_completed(ctx, msg))

    assert agent.base_called is True
    assert len(ctx.messages) == 1
    role, content = ctx.messages[0]
    assert role == "system"
    assert "rahul.verma@okicici" in content
    assert "150000" in content


def test_livekit_stt_stream_wrapper() -> None:
    class EventType(Enum):
        INTERIM_TRANSCRIPT = 1
        FINAL_TRANSCRIPT = 2

    @dataclass
    class Alt:
        text: str

    @dataclass
    class Event:
        type: EventType
        alternatives: list[Alt]

    async def fake_stream():
        yield Event(EventType.INTERIM_TRANSCRIPT, [Alt("dedh")])
        yield Event(EventType.FINAL_TRANSCRIPT, [Alt("dedh hazaar bhejo")])

    hook = livekit_mod.PaisaParseHook(mode="replace")

    async def collect():
        return [ev async for ev in hook.wrap_stt_stream(fake_stream())]

    events = _run_coro(collect())
    assert events[0].alternatives[0].text == "dedh"
    assert events[1].alternatives[0].text == "₹1,500 bhejo"


def test_mcp_tool_handlers_and_server_factory(monkeypatch: Any) -> None:
    res = mcp_mod.tool_parse_financial_text(
        "IFSC SBIN0001234 pe sava lakh bhejo rahul@okicici",
        policy_mode="strict",
        language="hinglish",
    )
    assert res["needs_confirmation"] is True
    assert len(res["entities"]) == 3

    amt = mcp_mod.tool_parse_amount("dhai crore")
    assert amt["entities"][0]["value"] == 25000000

    upi = mcp_mod.tool_validate_upi_id("amit at ybl")
    assert upi["entities"][0]["value"] == "amit@ybl"

    ifsc = mcp_mod.tool_validate_ifsc_code("SBINO001234")
    assert ifsc["entities"][0]["value"] == "SBIN0001234"
    assert ifsc["entities"][0]["action"] == "confirm"

    # Mock mcp.server.fastmcp.FastMCP to verify tool registration
    mcp_pkg = types.ModuleType("mcp")
    srv_pkg = types.ModuleType("mcp.server")
    fastmcp_mod = types.ModuleType("mcp.server.fastmcp")

    class FakeFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools: list[str] = []

        def tool(self):
            def decorator(fn: Any) -> Any:
                self.tools.append(fn.__name__)
                return fn

            return decorator

    fastmcp_mod.FastMCP = FakeFastMCP  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "mcp", mcp_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server", srv_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_mod)

    server = mcp_mod.create_mcp_server("paisa-parse-test")
    assert server.name == "paisa-parse-test"
    assert set(server.tools) == {
        "tool_parse_financial_text",
        "tool_parse_amount",
        "tool_validate_upi_id",
        "tool_validate_ifsc_code",
    }
