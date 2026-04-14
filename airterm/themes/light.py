"""Light theme CSS for AirTerm."""

LIGHT_CSS = """
/* Light theme - AirTerm */

Screen {
    background: #ffffff;
}

#breadcrumb {
    dock: top;
    height: 1;
    background: #e0e0e0;
    color: #424242;
    padding: 0 1;
}

#status-bar {
    dock: bottom;
    height: 1;
    background: #e0e0e0;
    color: #424242;
}

DataTable {
    background: #ffffff;
}

DataTable > .datatable--header {
    background: #f5f5f5;
    color: #424242;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #bbdefb;
    color: #424242;
}

/* State colors - Light theme */
.state-success { color: #2e7d32; }
.state-failed { color: #c62828; text-style: bold; }
.state-running { color: #f9a825; }
.state-queued { color: #1565c0; }
.state-up_for_retry { color: #ef6c00; }
.state-skipped { color: #757575; }
.state-upstream_failed { color: #ad1457; }
.state-deferred { color: #7b1fa2; }
.state-paused { color: #757575; }

.modal {
    background: #f5f5f5;
    border: solid #1976d2;
}

.modal-title {
    color: #424242;
    text-style: bold;
}

.confirm-modal {
    width: 60;
    height: auto;
    background: #f5f5f5;
    border: solid #1976d2;
    padding: 1 2;
}

.command-palette {
    dock: top;
    height: 3;
    background: #e0e0e0;
    border-bottom: solid #1976d2;
}

.hel-overlay {
    background: #f5f5f5;
    border: solid #1976d2;
}

.hel-overlay .key {
    color: #1976d2;
    text-style: bold;
}

.hel-overlay .action {
    color: #424242;
}
"""
