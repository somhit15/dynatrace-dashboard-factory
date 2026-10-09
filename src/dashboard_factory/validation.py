from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .io import load_yaml


ROOT = Path(__file__).resolve().parents[2]


def validate_document(document: dict[str, Any], schema_path: str | Path) -> list[str]:
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return [error.message for error in sorted(validator.iter_errors(document), key=str)]


def validate_inputs(application_path: str, request_path: str) -> list[str]:
    errors: list[str] = []
    application = load_yaml(application_path)
    request = load_yaml(request_path)
    errors.extend(f"application: {error}" for error in validate_document(application, ROOT / "schemas/application.schema.json"))
    errors.extend(f"request: {error}" for error in validate_document(request, ROOT / "schemas/dashboard-request.schema.json"))
    known_services = {service["name"] for service in application.get("services", []) if isinstance(service, dict) and "name" in service}
    known_metrics = {metric["name"] for metric in application.get("metrics", []) if isinstance(metric, dict) and "name" in metric}
    for service in request.get("services", []):
        if service not in known_services:
            errors.append(f"request: unknown service '{service}'")
    for metric in request.get("metrics", []):
        if metric not in known_metrics:
            errors.append(f"request: unknown metric '{metric}'")
    return errors


def validate_spec(spec: dict[str, Any], application: dict[str, Any] | None = None) -> list[str]:
    """Validates that a generated dashboard specification satisfies schema and application constraints."""
    errors: list[str] = []
    errors.extend(f"spec: {error}" for error in validate_document(spec, ROOT / "schemas/dashboard-spec.schema.json"))

    if application:
        known_services = {service["name"] for service in application.get("services", []) if isinstance(service, dict) and "name" in service}
        known_metrics = {metric["name"] for metric in application.get("metrics", []) if isinstance(metric, dict) and "name" in metric}
        dashboard = spec.get("dashboard", {})
        for tile in dashboard.get("tiles", []):
            metric = tile.get("metric")
            if metric and known_metrics and metric not in known_metrics:
                errors.append(f"spec: tile '{tile.get('title')}' references unknown metric '{metric}'")
            for svc in tile.get("service_filter", []):
                if known_services and svc not in known_services:
                    errors.append(f"spec: tile '{tile.get('title')}' references unknown service '{svc}'")
    return errors
