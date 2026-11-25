"""Example: Invoking paisa-parse MCP tool handlers or starting the stdio server."""

import json

from paisa_parse.integrations.mcp_server import tool_parse_financial_text


def main() -> None:
    payload = tool_parse_financial_text(
        "bhai rahul dot verma at ok icici pe dedh lakh bhej do, IFSC SBIN triple zero ek do teen chaar",
        policy_mode="balanced",
        language="hinglish",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
