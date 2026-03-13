from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from src.domain.models.report import Report


class ReportRenderer(ABC):
    """Transforms a :class:`Report` into HTML output."""

    @abstractmethod
    def render(self, report: Report) -> str:
        """Return the rendered HTML document."""

    def render_to_file(self, report: Report, output_path: Path) -> Path:
        """Render the report and write it to ``output_path``.

        Concrete renderers may override this for streaming or asset handling,
        but the default implementation is enough for static HTML generation.
        """
        html = self.render(report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        return output_path
