"""Breadcrumb navigation bar widget."""

from textual.widgets import Static


class Breadcrumb(Static):
    def __init__(self):
        super().__init__("DAGs")

    def set_path(self, path: str):
        self.update(f"DAGs > {path}" if path else "DAGs")

    def clear(self):
        self.update("DAGs")
