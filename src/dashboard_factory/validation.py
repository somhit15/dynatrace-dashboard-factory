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
