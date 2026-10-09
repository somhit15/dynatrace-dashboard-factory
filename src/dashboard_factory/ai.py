"""Provider-neutral contract for AI dashboard generation.

The framework deliberately keeps model invocation outside the core renderer.
An adapter can call a selected model and must return a JSON object that is
validated before it is passed to Terraform rendering.
"""

from __future__ import annotations

from typing import Any, Protocol


class StructuredAIClient(Protocol):
    def generate_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Return structured JSON only; the caller owns validation."""


class AIDashboardGenerator:
    def __init__(self, client: StructuredAIClient):
        self.client = client

    def generate(self, application: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
        return self.client.generate_json(
            system_prompt=(
                "Generate only a dashboard specification. Use only services and metrics "
                "present in the supplied application manifest. Never produce secrets or Terraform."
            ),
            user_prompt=f"Application manifest:\n{application}\n\nDashboard request:\n{request}",
        )
