"""Provider-neutral contract and Google Gemini implementation for AI dashboard generation.

The framework keeps model invocation outside the core renderer.
The Gemini adapter interprets intent, selects relevant metrics and layouts,
and emits a structured Dashboard Specification JSON that must pass
schema and policy validation before being passed to Terraform rendering.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Protocol


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]


class StructuredAIClient(Protocol):
    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return structured JSON only; the caller owns validation."""


class GeminiAIClient:
    """Google Gemini client using standard library HTTP for zero external dependencies."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_GEMINI_MODEL):
        self.api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("AI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY or AI_API_KEY in your environment, "
                "or pass it via --api-key. You can get a free key at https://aistudio.google.com/apikey"
            )
        self.model = model

    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        models_to_try = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]
        last_error: Exception | None = None

        for current_model in models_to_try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent"
                f"?key={self.api_key}"
            )

            payload = {
                "system_instruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_prompt}],
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.2,
                },
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError(f"No response candidates returned by Gemini: {data}")

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise RuntimeError("Gemini response contained no content parts")

                text = parts[0].get("text", "").strip()
                try:
                    self.model = current_model
                    return json.loads(text)
                except json.JSONDecodeError as err:
                    raise RuntimeError(f"Gemini output was not valid JSON:\n{text}") from err

            except urllib.error.HTTPError as err:
                body = err.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"Gemini API error ({current_model}, HTTP {err.code}): {body}")
                # If high demand (503) or not found (404), try next model in fallback list
                if err.code in (503, 404):
                    time.sleep(1)
                    continue
                raise last_error from err
            except urllib.error.URLError as err:
                raise RuntimeError(f"Network error connecting to Gemini API: {err.reason}") from err

        if last_error:
            raise last_error
        raise RuntimeError("Failed to generate content with Gemini models")


class AIDashboardGenerator:
    """Interprets dashboard requirements and outputs a governed specification."""

    def __init__(self, client: StructuredAIClient):
        self.client = client

    def generate_from_request(
        self, application: dict[str, Any], request: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate specification from a structured request YAML."""
        system_prompt = self._build_system_prompt()
        user_prompt = (
            f"Application Manifest:\n{json.dumps(application, indent=2)}\n\n"
            f"Dashboard Request:\n{json.dumps(request, indent=2)}\n\n"
            "Task: Generate a dashboard specification complying with the schema."
        )
        spec = self.client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        spec["generator"] = "ai-gemini"
        return spec

    def generate_from_prompt(
        self, application: dict[str, Any], natural_language_prompt: str, dashboard_name: str | None = None
    ) -> dict[str, Any]:
        """Generate specification from a free-form natural language user prompt."""
        system_prompt = self._build_system_prompt()
        user_prompt = (
            f"Application Manifest:\n{json.dumps(application, indent=2)}\n\n"
            f"User Requirement:\n\"{natural_language_prompt}\"\n\n"
            f"Requested Dashboard Name (if provided): {dashboard_name or 'Derive a clean kebab-case name'}\n\n"
            "Task: Interpret the user's intent, select only allowed metrics and services from the manifest, "
            "and produce a comprehensive, structured dashboard specification complying with the schema."
        )
        spec = self.client.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        spec["generator"] = "ai-gemini"
        if dashboard_name:
            spec.setdefault("dashboard", {})["name"] = dashboard_name
        return spec

    @staticmethod
    def _build_system_prompt() -> str:
        return (
            "You are an expert Observability & Dynatrace Architect specializing in GitOps and dashboard standards.\n"
            "Your job is to generate a standardized Dynatrace Dashboard Specification in JSON.\n\n"
            "STRICT GOVERNANCE RULES:\n"
            "1. ONLY use metric names that exist in the supplied Application Manifest under `metrics`. Never invent or hallucinate metrics.\n"
            "2. ONLY use service names that exist in the supplied Application Manifest under `services`.\n"
            "3. The output MUST strictly follow this JSON structure:\n"
            "{\n"
            '  "schema_version": "1.0",\n'
            '  "generator": "ai-gemini",\n'
            '  "application": "<application name from manifest>",\n'
            '  "dashboard": {\n'
            '    "name": "<kebab-case-dashboard-name>",\n'
            '    "description": "<detailed purpose of this dashboard>",\n'
            '    "owner": "<owner from application manifest>",\n'
            '    "tags": ["application:<app>", "domain:<domain>", "managed-by:dashboard-factory"],\n'
            '    "services": ["<list of involved service names>"],\n'
            '    "tiles": [\n'
            '      {\n'
            '        "id": "metric_1",\n'
            '        "title": "<Human Readable Chart Title>",\n'
            '        "type": "metric",\n'
            '        "metric": "<exact metric name from manifest>",\n'
            '        "service_filter": ["<service names>"],\n'
            '        "position": {"x": 0, "y": 0, "w": 4, "h": 3}\n'
            '      }\n'
            '    ]\n'
            '  }\n'
            "}\n\n"
            "LAYOUT RULES:\n"
            "- Grid has a width of 12 columns.\n"
            "- Standard tile width `w` is 4 (3 tiles per row) or 6 (2 tiles per row).\n"
            "- Standard tile height `h` is 3.\n"
            "- Tile positions must not overlap. Advance `x` across the row, then reset `x=0` and increase `y`.\n"
            "- Arrange tiles logically: e.g. throughput/volume on top, failure rates / errors next, then latency and duration.\n"
            "OUTPUT FORMAT: Return raw JSON only, no markdown wrapping, no explanation."
        )
