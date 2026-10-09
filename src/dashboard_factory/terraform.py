from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _resource_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", value.lower()).strip("_") or "dashboard"


def _classic_dashboard_payload(spec: dict[str, Any]) -> dict[str, Any]:
    dashboard = spec["dashboard"]
    tiles: dict[str, Any] = {}
    layouts: dict[str, Any] = {}
    for tile in dashboard["tiles"]:
        tile_id = tile["id"]
        tiles[tile_id] = {
            "name": tile["title"],
            "tileType": "CUSTOM_CHART",
            "configured": True,
            "customName": tile["title"],
            "queries": [{"metric": tile["metric"]}],
        }
        layouts[tile_id] = tile["position"]
    return {
        "dashboardMetadata": {
            "name": dashboard["name"],
            "shared": True,
            "owner": dashboard["owner"],
            "tags": dashboard.get("tags", []),
        },
        "tiles": tiles,
        "layouts": layouts,
    }


def render_terraform(spec: dict[str, Any], output_path: str | Path) -> None:
    dashboard = spec["dashboard"]
    resource = _resource_name(dashboard["name"])
    payload = json.dumps(_classic_dashboard_payload(spec), indent=2)
    content = (
        f'resource "dynatrace_json_dashboard" "{resource}" {{\n'
        f"  contents = jsonencode({payload})\n"
        "}\n"
    )
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
