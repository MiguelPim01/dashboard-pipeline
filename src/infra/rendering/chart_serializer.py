from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.domain.models.widgets import ChartWidget


@dataclass(frozen=True, slots=True)
class ChartSerializer:
    """Convert chart widgets into JSON payloads consumable by browser code."""

    def serialize(self, widget: ChartWidget) -> str:
        payload = self.to_dict(widget)
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def to_dict(widget: ChartWidget) -> dict[str, Any]:
        return {
            "id": widget.widget_id,
            "title": widget.title,
            "subtitle": widget.subtitle,
            "type": widget.chart_type.value,
            "labels": list(widget.labels),
            "datasets": [
                {"label": dataset.label, "data": list(dataset.values)}
                for dataset in widget.datasets
            ],
            "stacked": widget.stacked,
            "heightPx": widget.height_px,
        }
