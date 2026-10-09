"""Dashboard specification generation.

The template generator is deterministic and works without an AI key. An AI
adapter can implement the same input/output contract later; its output must
still pass the dashboard specification schema before Terraform is rendered.
"""

from typing import Any


def generate_dashboard_spec(application: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    services = application.get("services", [])
    service_names = [service["name"] for service in services]
    metric_names = request.get("metrics") or [metric["name"] for metric in application.get("metrics", [])]
    selected_services = request.get("services") or service_names
    tiles = []
    for index, metric in enumerate(metric_names):
        tiles.append({
            "id": f"metric_{index + 1}",
            "title": metric,
            "type": "metric",
            "metric": metric,
            "service_filter": selected_services,
            "position": {"x": (index % 3) * 4, "y": (index // 3) * 3, "w": 4, "h": 3},
        })
    return {
        "schema_version": "1.0",
        "generator": "template",
        "application": application["application"]["name"],
        "dashboard": {
            "name": request["name"],
            "description": request.get("description", "Generated Dynatrace dashboard"),
            "owner": application["application"].get("owner", "observability"),
            "tags": request.get("tags", []),
            "services": selected_services,
            "tiles": tiles,
        },
    }
