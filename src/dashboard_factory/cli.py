from __future__ import annotations

import argparse
import json
import sys

from .ai import AIDashboardGenerator, GeminiAIClient
from .generator import generate_dashboard_spec
from .io import load_yaml, write_yaml_or_json
from .terraform import render_terraform
from .validation import validate_inputs, validate_spec


def main() -> int:
    parser = argparse.ArgumentParser(prog="dashboard-factory", description="AI-driven GitOps Dynatrace Dashboard Factory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate application manifest and dashboard request")
    validate.add_argument("--application", required=True, help="Path to application.yaml")
    validate.add_argument("--request", required=True, help="Path to dashboard-request.yaml")

    generate = subparsers.add_parser("generate", help="Generate dashboard specification (deterministic or AI-powered)")
    generate.add_argument("--application", required=True, help="Path to application.yaml")
    generate.add_argument("--request", required=True, help="Path to dashboard-request.yaml")
    generate.add_argument("--output", required=True, help="Output path for dashboard-spec.yaml")
    generate.add_argument("--ai", action="store_true", help="Use Google Gemini AI generator instead of template")
    generate.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY/AI_API_KEY env var)")

    ai_cmd = subparsers.add_parser("ai", help="Generate dashboard specification directly from natural language prompt")
    ai_cmd.add_argument("--application", required=True, help="Path to application.yaml")
    ai_cmd.add_argument("--prompt", required=True, help="Natural language dashboard requirement prompt")
    ai_cmd.add_argument("--output", required=True, help="Output path for dashboard-spec.yaml")
    ai_cmd.add_argument("--name", help="Optional override for dashboard name")
    ai_cmd.add_argument("--save-request", help="Optional path to also save the generated dashboard request YAML")
    ai_cmd.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY/AI_API_KEY env var)")

    ai_req = subparsers.add_parser("ai-request", help="Generate dashboard request YAML from natural language prompt")
    ai_req.add_argument("--application", required=True, help="Path to application.yaml")
    ai_req.add_argument("--prompt", required=True, help="Natural language dashboard requirement prompt")
    ai_req.add_argument("--output", required=True, help="Output path for request YAML")
    ai_req.add_argument("--name", help="Optional override for request name")
    ai_req.add_argument("--api-key", help="Gemini API key (or set GEMINI_API_KEY/AI_API_KEY env var)")

    render = subparsers.add_parser("render", help="Render validated specification to Terraform")
    render.add_argument("--spec", required=True, help="Path to dashboard-spec.yaml or .json")
    render.add_argument("--output", required=True, help="Output path for Terraform .tf file")
    render.add_argument("--application", help="Optional path to application.yaml to cross-validate metrics")

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

        app_data = load_yaml(args.application)
        req_data = load_yaml(args.request)

        if args.ai:
            try:
                client = GeminiAIClient(api_key=args.api_key)
                generator = AIDashboardGenerator(client)
                print(f"Calling Google Gemini ({client.model}) to generate dashboard specification...")
                spec = generator.generate_from_request(app_data, req_data)
            except Exception as e:
                print(f"AI generation failed: {e}", file=sys.stderr)
                return 1
        else:
            spec = generate_dashboard_spec(app_data, req_data)

        # Enforce specification validation gate
        spec_errors = validate_spec(spec, app_data)
        if spec_errors:
            print("Generated specification failed schema/policy validation:\n" + "\n".join(spec_errors), file=sys.stderr)
            return 1

        write_yaml_or_json(args.output, spec)
        print(f"Generated and validated {args.output} (generator: {spec.get('generator', 'unknown')})")
        return 0

    if args.command == "ai":
        app_data = load_yaml(args.application)
        try:
            client = GeminiAIClient(api_key=args.api_key)
            generator = AIDashboardGenerator(client)
            print(f"Interpreting intent with Google Gemini ({client.model})...")
            spec = generator.generate_from_prompt(app_data, args.prompt, dashboard_name=args.name)
        except Exception as e:
            print(f"AI prompt generation failed: {e}", file=sys.stderr)
            return 1

        # Enforce specification validation gate
        spec_errors = validate_spec(spec, app_data)
        if spec_errors:
            print("AI-generated specification failed schema/policy validation:\n" + "\n".join(spec_errors), file=sys.stderr)
            return 1

        write_yaml_or_json(args.output, spec)
        print(f"Successfully generated {args.output} from natural language prompt!")

        if getattr(args, "save_request", None):
            req = generator.generate_request_from_prompt(app_data, args.prompt, request_name=args.name or spec.get("dashboard", {}).get("name"))
            write_yaml_or_json(args.save_request, req)
            print(f"AI-generated dashboard request saved to {args.save_request}")
        return 0

    if args.command == "ai-request":
        app_data = load_yaml(args.application)
        try:
            client = GeminiAIClient(api_key=args.api_key)
            generator = AIDashboardGenerator(client)
            print(f"Generating dashboard request with Google Gemini ({client.model})...")
            req = generator.generate_request_from_prompt(app_data, args.prompt, request_name=args.name)
        except Exception as e:
            print(f"AI request generation failed: {e}", file=sys.stderr)
            return 1

        write_yaml_or_json(args.output, req)
        print(f"Successfully created {args.output} from natural language prompt via Gemini AI!")
        return 0

    if args.command == "render":
        spec = load_yaml(args.spec) if not args.spec.endswith(".json") else json.loads(open(args.spec, encoding="utf-8").read())
        app_data = load_yaml(args.application) if args.application else None

        spec_errors = validate_spec(spec, app_data)
        if spec_errors:
            print("Specification failed validation before rendering:\n" + "\n".join(spec_errors), file=sys.stderr)
            return 1

        render_terraform(spec, args.output)
        print(f"Rendered {args.output}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
