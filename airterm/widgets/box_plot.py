"""BoxPlot widget - visualizes statistical distribution of durations."""

from statistics import quantiles
from textual.widget import Widget
from textual.widgets import Static


class BoxPlot(Widget):
    """Widget to display duration distribution as ASCII box plot."""

    def __init__(self, durations: list[float] | None = None, **kwargs):
        super().__init__(**kwargs)
        self._durations = durations or []

    def update(self, durations: list[float]) -> None:
        self._durations = durations
        self.refresh()

    def render(self) -> None:
        if not self._durations:
            self.update_content("-- no data --")
            return

        pct = self._compute_percentiles(self._durations)
        if not pct:
            self.update_content("-- insufficient data --")
            return

        viz = self._draw_boxplot(pct)
        self.update_content(viz)

    def _compute_percentiles(self, data: list[float]) -> dict | None:
        if len(data) < 2:
            return None

        sorted_data = sorted(data)
        try:
            percentiles = quantiles(sorted_data, n=4)
        except ValueError:
            return None

        return {
            "min": min(sorted_data),
            "p25": percentiles[0],
            "p50": percentiles[1],
            "p75": percentiles[2],
            "max": max(sorted_data),
        }

    def _draw_boxplot(self, pct: dict) -> str:
        min_val = pct["min"]
        max_val = pct["max"]
        p25 = pct["p25"]
        p50 = pct["p50"]
        p75 = pct["p75"]

        range_width = max_val - min_val if max_val != min_val else 1

        def pos(v: float) -> int:
            return int(((v - min_val) / range_width) * 18) + 1

        min_pos = pos(min_val)
        p25_pos = pos(p25)
        p50_pos = pos(p50)
        p75_pos = pos(p75)
        max_pos = pos(max_val)

        bar = [" "] * 20
        for i in range(min_pos, max_pos + 1):
            if 0 <= i < 20:
                bar[i] = "─"

        if 0 <= p25_pos < 20:
            bar[p25_pos] = "├"
        if 0 <= p50_pos < 20:
            bar[p50_pos] = "●"
        if 0 <= p75_pos < 20:
            bar[p75_pos] = "┤"

        viz = "".join(bar)
        return f"[{viz}] p50:{p50:.0f}s p75:{p75:.0f}s"

    def update_content(self, text: str) -> None:
        try:
            static = self.query_one(Static)
            static.update(text)
        except Exception:
            pass
