"""Confirmation modal widget."""

from textual.reactive import reactive
from textual.widget import Widget


class ConfirmModal(Widget):
    title = reactive("")
    body = reactive("")
    visible = reactive(False)

    def __init__(self):
        super().__init__()
        self.display = False

    def show(self, title: str, body: str):
        self.title = title
        self.body = body
        self.display = True

    def hide(self):
        self.display = False
