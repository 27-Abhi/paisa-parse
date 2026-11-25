"""Model Context Protocol (MCP) stdio tool server for paisa-parse."""

from __future__ import annotations

from typing import Any, Literal

from paisa_parse.engine import parse
from paisa_parse.policy import ConfirmPolicy
from paisa_parse.types import EntityType


def _select_policy(
    policy_mode: Literal["balanced", "strict", "permissive"],
    language: Literal["en-IN", "hinglish"],
) -> ConfirmPolicy:
    if policy_mode == "strict":
        return ConfirmPolicy.strict(language=language)
    if policy_mode == "permissive":
        return ConfirmPolicy.permissive(language=language)
    return ConfirmPolicy.balanced(language=language)


def tool_parse_financial_text(
    text: str,
    policy_mode: Literal["balanced", "strict", "permissive"] = "balanced",
    language: Literal["en-IN", "hinglish"] = "en-IN",
) -> dict[str, Any]:
    """Parse all Hinglish/Indian-English financial entities (amounts, digits, UPI IDs, IFSC codes)."""
    policy = _select_policy(policy_mode, language)
    return parse(text, policy=policy).to_dict()


def tool_parse_amount(
    text: str,
    language: Literal["en-IN", "hinglish"] = "en-IN",
) -> dict[str, Any]:
    """Parse Hinglish or Indian-English spoken monetary amounts (e.g. 'dedh lakh', 'sava do crore')."""
    policy = ConfirmPolicy.balanced(language=language)
    return parse(text, policy=policy, kinds=(EntityType.AMOUNT,)).to_dict()


def tool_validate_upi_id(
    text: str,
    language: Literal["en-IN", "hinglish"] = "en-IN",
) -> dict[str, Any]:
    """Extract and validate a written or spoken UPI ID against known NPCI PSP handles."""
    policy = ConfirmPolicy.balanced(language=language)
    return parse(text, policy=policy, kinds=(EntityType.UPI_ID,)).to_dict()


def tool_validate_ifsc_code(
    text: str,
    language: Literal["en-IN", "hinglish"] = "en-IN",
) -> dict[str, Any]:
    """Extract and validate a written or spoken 11-character Indian IFSC code."""
    policy = ConfirmPolicy.balanced(language=language)
    return parse(text, policy=policy, kinds=(EntityType.IFSC,)).to_dict()


def _import_fastmcp() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP

        return FastMCP
    except ImportError:
        try:
            from fastmcp import FastMCP

            return FastMCP
        except ImportError as exc:
            raise ImportError(
                "MCP SDK is not installed. Install with: pip install 'paisa-parse[mcp]'"
            ) from exc


def create_mcp_server(name: str = "paisa-parse") -> Any:
    """Create and configure a FastMCP server exposing paisa-parse tools."""
    fastmcp_cls = _import_fastmcp()
    mcp = fastmcp_cls(name)

    mcp.tool()(tool_parse_financial_text)
    mcp.tool()(tool_parse_amount)
    mcp.tool()(tool_validate_upi_id)
    mcp.tool()(tool_validate_ifsc_code)
    return mcp


def main() -> None:
    """Entrypoint for the `paisa-parse-mcp` stdio server."""
    server = create_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
