import argparse
import json
import sys

from .generator import generate_dashboard_spec
from .io import load_yaml, write_yaml_or_json
from .terraform import render_terraform
from .validation import validate_inputs


def main() -> int:
    parser = argparse.ArgumentParser(prog="dashboard-factory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--application", required=True)
    validate.add_argument("--request", required=True)

    generate = subparsers.add_parser("generate")
    generate.add_argument("--application", required=True)
    generate.add_argument("--request", required=True)
    generate.add_argument("--output", required=True)

    render = subparsers.add_parser("render")
    render.add_argument("--spec", required=True)
    render.add_argument("--output", required=True)

    args = parser.parse_args()
    if args.command == "validate":
        errors = validate_inputs(args.application, args.request)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print("Inputs are valid")
        return 0
    if args.command == "generate":
        errors = validate_inputs(args.application, args.request)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        spec = generate_dashboard_spec(load_yaml(args.application), load_yaml(args.request))
        write_yaml_or_json(args.output, spec)
        print(f"Generated {args.output}")
        return 0
    if args.command == "render":
        spec = load_yaml(args.spec) if not args.spec.endswith(".json") else json.loads(open(args.spec, encoding="utf-8").read())
        render_terraform(spec, args.output)
        print(f"Rendered {args.output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
