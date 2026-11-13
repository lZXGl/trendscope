"""JSON Schema validation for the build (same jsonschema check as scripts/validate_schema.py)."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"
RESULT_SCHEMA_PATH = SCHEMAS_DIR / "trend_result.schema.json"
INDEX_SCHEMA_PATH = SCHEMAS_DIR / "index.schema.json"


class SchemaError(ValueError):
    """A payload does not match its JSON Schema."""


def validate_payload(payload: object, schema_path: Path, label: str) -> None:
    """Raise SchemaError listing every schema violation in `payload`."""
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: e.json_path)
    if errors:
        details = "\n".join(f"  {e.json_path}: {e.message}" for e in errors)
        raise SchemaError(f"{label} does not match {schema_path.name}:\n{details}")
