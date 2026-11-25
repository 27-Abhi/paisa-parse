"""Command-line interface for paisa-parse."""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from collections.abc import Sequence

from paisa_parse.engine import parse
from paisa_parse.policy import ConfirmPolicy
from paisa_parse.types import EntityType


def _configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            with contextlib.suppress(Exception):
                stream.reconfigure(encoding="utf-8")


def _make_policy(name: str, language: str) -> ConfirmPolicy:
    lang = "hinglish" if language == "hinglish" else "en-IN"
    if name == "strict":
        return ConfirmPolicy.strict(language=lang)
    if name == "permissive":
        return ConfirmPolicy.permissive(language=lang)
    return ConfirmPolicy.balanced(language=lang)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paisa-parse",
        description="Parse Hinglish & Indian-English spoken financial entities with confidence scores.",
    )
    parser.add_argument(
        "text",
        help="Input utterance/transcript to parse.",
    )
    parser.add_argument(
        "--policy",
        choices=("balanced", "strict", "permissive"),
        default="balanced",
        help="Confirm-back policy preset (default: balanced).",
    )
    parser.add_argument(
        "--lang",
        choices=("en-IN", "hinglish"),
        default="en-IN",
        help="Confirm-back prompt language (default: en-IN).",
    )
    parser.add_argument(
        "--kinds",
        default=None,
        help="Comma-separated entity kinds to extract (amount,digits,upi_id,ifsc).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit structured JSON output.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_stdio()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    policy = _make_policy(args.policy, args.lang)
    kinds = (
        [EntityType(k.strip()) for k in args.kinds.split(",") if k.strip()]
        if args.kinds
        else None
    )

    result = parse(args.text, policy=policy, kinds=kinds)
    if args.as_json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"Input:      {result.text}")
    print(f"Normalized: {result.normalized_text}")
    if not result.entities:
        print("Entities:   (none)")
        return 0

    print(f"Entities ({len(result.entities)}):")
    for idx, ent in enumerate(result.entities, start=1):
        print(
            f"  {idx}. [{ent.kind.value}] {ent.formatted} "
            f"(raw={ent.span.raw!r}, conf={ent.confidence:.2f}, action={ent.action.value})"
        )
        if ent.confirm_prompt:
            print(f"     prompt: {ent.confirm_prompt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
