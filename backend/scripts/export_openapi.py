"""Generate or check the contract directly from the FastAPI application."""

import argparse
import json
import sys
from pathlib import Path

from scope_guard.core.config import Settings
from scope_guard.main import create_app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--check", type=Path)
    arguments = parser.parse_args()
    contract = (
        json.dumps(create_app(Settings(_env_file=None)).openapi(), indent=2, ensure_ascii=False)
        + "\n"
    )

    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(contract, encoding="utf-8")
        return 0

    if not arguments.check.is_file():
        print(f"Missing OpenAPI contract: {arguments.check}", file=sys.stderr)
        return 1
    if arguments.check.read_text(encoding="utf-8") != contract:
        print(f"Stale OpenAPI contract: {arguments.check}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
