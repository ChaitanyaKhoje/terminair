"""Dark theme CSS for AirTerm."""

DARK_CSS = """
$success: #50fa7b;
$error: #ff5555;
$warning: #f1fa8c;
$info: #8be9fd;
$accent: #bd93f9;
$surface: #282a36;
$panel: #44475a;
$text: #f8f8f2;
$text-muted: #6272a4;

Screen {
    background: $surface;
}

DataTable {
    background: $surface;
}

DataTable > .datatable--header {
    background: $panel;
    color: $text;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $accent;
    color: $text;
}

.state-success { color: $success; }
.state-failed { color: $error; text-style: bold; }
.state-running { color: $warning; }
.state-queued { color: $info; }
.state-up_for_retry { color: $warning; }
.state-skipped { color: $text-muted; }
.state-upstream_failed { color: $error; }
.state-deferred { color: $accent; }
.state-paused { color: $text-muted; }

.modal {
    background: $panel;
    border: solid $accent;
}

.modal-title {
    color: $text;
    text-style: bold;
}

.confirm-modal {
    width: 60;
    height: auto;
    background: $panel;
    border: solid $accent;
    padding: 1 2;
}

.command-palette {
    dock: top;
    height: 3;
    background: $panel;
    border-bottom: solid $accent;
}
"""
