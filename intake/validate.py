#!/usr/bin/env python3
"""Validate a JSON file against the IntakeSubmission schema.

Usage:
    python3 validate.py <file.json> [--schema openapi.yaml] [--definition IntakeSubmission]

Exits 0 if the file conforms, 1 otherwise (printing each validation error).
"""
import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError as exc:  # pragma: no cover
    sys.exit(
        f"Missing dependency: {exc.name}. Install with: "
        "pip install -r requirements.txt"
    )

DEFAULT_SCHEMA = Path(__file__).parent / "openapi.yaml"


def build_validator(schema_path: Path, definition: str) -> Draft202012Validator:
    """Build a validator for a single component schema within an OpenAPI doc.

    The whole OpenAPI document is registered so that internal
    ``#/components/schemas/...`` references resolve correctly.
    """
    openapi = yaml.safe_load(schema_path.read_text())

    if definition not in openapi.get("components", {}).get("schemas", {}):
        sys.exit(f"Schema '{definition}' not found in {schema_path}")

    # Register the whole OpenAPI doc under a distinct base URI, then reference
    # the target schema absolutely.  Internal "#/components/schemas/..." refs
    # then resolve against the doc rather than the anonymous wrapper schema.
    base_uri = "urn:openapi"
    resource = Resource(contents=openapi, specification=DRAFT202012)
    registry = Registry().with_resource(uri=base_uri, resource=resource)
    ref = f"{base_uri}#/components/schemas/{definition}"
    return Draft202012Validator({"$ref": ref}, registry=registry)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", type=Path, help="JSON file to validate")
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="OpenAPI document containing the schema (default: openapi.yaml)",
    )
    parser.add_argument(
        "--definition",
        default="IntakeSubmission",
        help="Component schema name to validate against (default: IntakeSubmission)",
    )
    args = parser.parse_args()

    try:
        data = json.loads(args.json_file.read_text())
    except FileNotFoundError:
        sys.exit(f"File not found: {args.json_file}")
    except json.JSONDecodeError as exc:
        sys.exit(f"Invalid JSON in {args.json_file}: {exc}")

    validator = build_validator(args.schema, args.definition)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    if not errors:
        print(f"OK: {args.json_file} conforms to {args.definition}")
        return 0

    print(f"INVALID: {args.json_file} ({len(errors)} error(s))")
    for err in errors:
        location = "/".join(str(p) for p in err.absolute_path) or "(root)"
        print(f"  - {location}: {err.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
