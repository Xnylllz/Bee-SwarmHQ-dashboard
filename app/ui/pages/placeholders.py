from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FutureToolDefinition:
    name: str
    description: str


FUTURE_TOOLS = [
    FutureToolDefinition("graphs_tab", "Expanded multi-series production and session charts."),
    FutureToolDefinition("compare_accounts_tab", "Compare two or more accounts side by side."),
    FutureToolDefinition("alerts_tab", "Central rule-based alerts and downtime history."),
    FutureToolDefinition("image_gallery_tab", "Full screenshot browser with filtering and tags."),
]
