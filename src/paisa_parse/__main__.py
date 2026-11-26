"""Allow running `python -m paisa_parse` directly."""

from paisa_parse.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
