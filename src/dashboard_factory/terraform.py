from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _resource_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", value.lower()).strip("_") or "dashboard"


def _classic_dashboard_payload(spec: dict[str, Any]) -> dict[str, Any]:
    dashboard = spec["dashboard"]
    tiles: list[dict[str, Any]] = []
    for tile in dashboard["tiles"]:
        position = tile["position"]
        tiles.append({
            "name": tile["title"],
            "tileType": "CUSTOM_CHARTING",
            "configured": True,
            "bounds": {
                "top": position["y"] * 100,
                "left": position["x"] * 80,
                "width": position["w"] * 80,
                "height": position["h"] * 80,
            },
            "tileFilter": {},
            "filterConfig": {
                "type": "MIXED",
                "customName": tile["title"],
                "chartConfig": {
                    "type": "LINE",
                    "series": [
                        {
                            "metric": tile["metric"],
                            "aggregation": "SUM",
                            "aggregationRate": "TOTAL",
                            "type": "LINE",
                        }
                    ],
                },
            },
        })
    return {
        "dashboardMetadata": {
            "name": dashboard["name"],
            "shared": True,
            "owner": dashboard["owner"],
            "tags": dashboard.get("tags", []),
        },
        "tiles": tiles,
    }


def render_terraform(spec: dict[str, Any], output_path: str | Path) -> None:
    dashboard = spec["dashboard"]
    resource = _resource_name(dashboard["name"])
    payload_lines = json.dumps(_classic_dashboard_payload(spec), indent=2).splitlines()
    payload = "\n".join(
        [payload_lines[0]]
        + [f"  {line}" for line in payload_lines[1:-1]]
        + [f"  {payload_lines[-1]}"]
    )
    content = (
        f'resource "dynatrace_json_dashboard" "{resource}" {{\n'
        f"  contents = jsonencode({payload})\n"
        "}\n"
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
