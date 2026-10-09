from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _resource_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", value.lower()).strip("_") or "dashboard"


def _dql_metric_query(metric: str, services: list[str]) -> str:
    """Build a DQL timeseries query for a metric with optional service filter."""
    if services:
        service_filter = "|".join(services)
        return (
            f'timeseries sum(`{metric}`), '
            f'filter: dt.entity.service matchesPhrase "{service_filter}"'
        )
    return f"timeseries sum(`{metric}`)"


def _new_dashboard_payload(spec: dict[str, Any]) -> dict[str, Any]:
    """
    Build a Dynatrace platform dashboard document (version 21, DQL-based).
    This format is required for Grail/newer Dynatrace SaaS environments.
    Used by the dynatrace_document Terraform resource.
    """
    dashboard = spec["dashboard"]
    tiles: dict[str, Any] = {}
    layouts: dict[str, Any] = {}

    for tile in dashboard["tiles"]:
        tile_id = str(tile["id"].split("_")[-1])  # e.g. "metric_1" → "1"
        pos = tile["position"]
        services = tile.get("service_filter", [])

        tiles[tile_id] = {
            "type": "data",
            "title": tile["title"],
            "query": _dql_metric_query(tile["metric"], services),
            "visualization": "lineChart",
            "visualizationSettings": {
                "lineChart": {
                    "legend": {"position": "bottom", "toggleValuesAction": "filter"},
                    "yAxis": {"label": tile["title"]},
                }
            },
            "queryConfig": {
                "enableHighPrecision": False,
                "timeframe": "",
                "withoutDefaultFiltering": False,
            },
        }

        layouts[tile_id] = {
            "x": pos["x"],
            "y": pos["y"],
            "w": pos["w"] * 2,   # grid units: spec uses 4-col, DT uses 8-col wide units
            "h": pos["h"],
        }

    return {
        "version": 21,
        "variables": [],
        "tiles": tiles,
        "layouts": layouts,
    }


def render_terraform(spec: dict[str, Any], output_path: str | Path) -> None:
    """
    Renders a dynatrace_document Terraform resource for Grail/newer Dynatrace
    SaaS environments (replaces the legacy dynatrace_json_dashboard resource
    which only works with classic Config API v1 environments).
    """
    dashboard = spec["dashboard"]
    resource = _resource_name(dashboard["name"])
    payload = json.dumps(_new_dashboard_payload(spec), indent=2)

    content = (
        f'resource "dynatrace_document" "{resource}" {{\n'
        f'  type    = "dashboard"\n'
        f'  name    = {json.dumps(dashboard["name"])}\n'
        f'  private = false\n'
        f'  content = jsonencode({payload})\n'
        "}\n"
    )

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
