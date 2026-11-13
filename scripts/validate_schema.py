"""Validate one or more JSON result files against schemas/trend_result.schema.json."""

import json
import sys
from pathlib import Path

from jsonschema import validate

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "trend_result.schema.json"


def main(paths: list[str]) -> int:
    if not paths:
        print("Usage: validate_schema.py <json-file> [<json-file> ...]", file=sys.stderr)
        return 2

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    for raw_path in paths:
        target = Path(raw_path)
        payload = json.loads(target.read_text(encoding="utf-8"))
        validate(instance=payload, schema=schema)
        print(f"OK: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
