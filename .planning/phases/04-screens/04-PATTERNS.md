# Phase 4: Screens - Pattern Map

**Mapped:** 2026-05-15
**Files analyzed:** 3 modified files (no new files — all screens pre-exist)
**Analogs found:** 3 / 3

## File Classification

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `terminair/screens/model_list.py` | screen | request-response | `terminair/app.py` (set_interval clock pattern) + `terminair/screens/problems.py` (RegressionAnalyzer) | role-match |
| `terminair/screens/lineage.py` | screen | transform | self (single-line `__init__` fix) | exact — trivial change |
| `terminair/screens/detail.py` | screen | request-response | `terminair/screens/model_list.py` (BINDINGS pattern) + RESEARCH.md (VerticalScroll) | role-match |

## Pattern Assignments

---

### `terminair/screens/model_list.py` (screen, request-response)

**Changes required:**
1. Add connection URL + live clock to the existing `#model-list-header` Static
2. Add a bottom `#model-list-status` Static with model count and regression warning count

**Analog for RegressionAnalyzer import:** `terminair/screens/problems.py`

**Imports pattern** (`problems.py` lines 1-13 — copy the RegressionAnalyzer import):
```python
from terminair.dbt.regression import RegressionAnalyzer
```
This import is already used in `problems.py` line 10. Add it to `model_list.py`'s import block.

**Analog for set_interval clock:** `terminair/app.py`

**Clock/interval pattern** (`app.py` lines 183-186):
```python
sec = float(self._config.settings.refresh_interval)
self._live_timer = self.set_interval(sec, self._schedule_live_reload, name="terminair_live")
```
Adapt to a 1-second interval in `ModelListScreen.on_mount`:
```python
self.set_interval(1.0, self._update_header)
```

**Analog for get_config() access:** `terminair/app.py` lines 291-292:
```python
def get_config(self) -> Config:
    return self._config
```
From a Screen, access via `self.app_typed.get_config()`. The `app_typed` property is defined in `terminair/screens/base.py` lines 37-38:
```python
@property
def app_typed(self) -> TerminairApp:
    return self.app  # type: ignore[return-value]
```

**Analog for connection URL extraction:** `terminair/app.py` lines 96-99:
```python
active_connection = self._config.connections.get(
    self._config.settings.default_connection
)
if active_connection is None or active_connection.dbt is None:
```
The `Connection.url` field (config.py line 44) is always present on a non-None Connection.

**Core pattern — `_update_header()` method to add** (modeled after `_update_meta()`, `model_list.py` lines 124-128):
```python
def _update_header(self) -> None:
    config = self.app_typed.get_config()
    conn = config.connections.get(config.settings.default_connection)
    url = conn.url if conn else "demo"
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    self.query_one("#model-list-header", Static).update(
        f"dbt models  |  {url}  |  {ts}"
    )
```

**Core pattern — `_update_statusbar()` method to add** (modeled after `_update_meta()` and `problems.py` `_render()` lines 67-75):
```python
def _update_statusbar(self) -> None:
    signals = RegressionAnalyzer(self._models).analyze()
    warnings = sum(1 for s in signals if s.severity in ("critical", "warning"))
    self.query_one("#model-list-status", Static).update(
        f"{len(self._models)} models  |  {warnings} regression warnings"
    )
```

**Existing `_render()` call site** (model_list.py lines 116-117 — add `_update_statusbar()` here):
```python
self._update_meta()
self._update_tag_bar()
# ADD: self._update_statusbar()
```

**Existing `compose()` method** (model_list.py lines 72-79 — add the bottom Static):
```python
def compose(self):
    with Vertical():
        yield Static("dbt models", id="model-list-header")
        yield Static("", id="model-list-meta")
        yield Static("", id="model-list-tags")
        yield FilterInput()
        yield DataTable(id="model-table")
        # ADD: yield Static("", id="model-list-status")
```

**Existing `on_mount()`** (model_list.py line 80-81 — add interval call):
```python
async def on_mount(self) -> None:
    await self._load_models()
    # ADD: self.set_interval(1.0, self._update_header)
```

**CSS to add** for the new Static (modeled after `#model-list-meta` CSS in model_list.py lines 43-48):
```css
#model-list-status {
    height: auto;
    padding: 0 1 1 1;
    color: #a5b4fc;
    background: #24263a;
}
```

**Warning — clock pitfall** (RESEARCH.md Pitfall 4): `_update_header()` must ONLY update the header Static. Do NOT call `_render()` or `_load_models()` from it.

---

### `terminair/screens/lineage.py` (screen, transform)

**Change required:** One-line fix in `__init__` — change `self._depth = 3` to `self._depth = 4`.

**Exact location** (lineage.py line 55):
```python
def __init__(self) -> None:
    super().__init__()
    self._mode = "model"
    self._depth = 3          # <-- change to 4
    self._model_map: dict[str, ModelState] = {}
```

**Why this is correct** (lineage.py lines 103-110): The `visit()` function returns early at `if depth >= self._depth`. Root is at depth 0. With `_depth=4`, the tree renders depths 0-4 (root + 4 child levels = 4-hop default per SCR-03).

**No other changes needed.** The `_update_meta()` at line 154 will automatically display the new depth in the meta bar.

---

### `terminair/screens/detail.py` (screen, request-response)

**Changes required:**
1. Add 1-5 key bindings for tab switching to `BINDINGS`
2. Add `action_switch_tab()` method
3. Wrap the SQL `Static` in a `VerticalScroll` container

**Gap 1 — BINDINGS pattern** (modeled after model_list.py lines 62-65, the BINDINGS extension pattern):
```python
# Current (detail.py lines 49-51):
BINDINGS = DbtScreen.BINDINGS + [
    Binding("enter", "noop", "Open"),
]

# Replace with:
BINDINGS = DbtScreen.BINDINGS + [
    Binding("enter", "noop", "Open"),
    Binding("1", "switch_tab('tab-1')", "Status", show=False),
    Binding("2", "switch_tab('tab-2')", "Structure", show=False),
    Binding("3", "switch_tab('tab-3')", "Refs", show=False),
    Binding("4", "switch_tab('tab-4')", "SQL", show=False),
    Binding("5", "switch_tab('tab-5')", "Regression", show=False),
]
```
Note: `show=False` keeps the footer uncluttered. The `#detail-tabs` TabbedContent widget id is used for querying.

**Action method to add** (after the existing `action_noop()` at detail.py line 142):
```python
def action_switch_tab(self, tab_id: str) -> None:
    self.query_one("#detail-tabs", TabbedContent).active = tab_id
```

**Binding priority behavior** (RESEARCH.md lines 109-113): Screen-level bindings shadow app-level bindings. Keys 1-4 on this screen trigger tab switching, not screen navigation. This is intentional and correct per SCR-04.

**Gap 2 — VerticalScroll import** (add to imports at detail.py lines 1-13):
```python
from textual.containers import VerticalScroll, Vertical
```
`Vertical` is already used in compose; `VerticalScroll` must be added to the same import.

**Gap 2 — SQL TabPane replacement** (detail.py line 64 — current):
```python
yield TabPane("SQL", Static("", id="detail-sql", classes="detail-pane"))
```
Replace with:
```python
with TabPane("SQL"):
    with VerticalScroll(id="detail-sql-scroll"):
        yield Static("", id="detail-sql", classes="detail-pane")
```

**CSS to add** for the VerticalScroll (RESEARCH.md Pitfall 5 — must set height to avoid collapsing to 0):
```css
#detail-sql-scroll {
    height: 1fr;
}
```

**`_render()` update target remains unchanged** (detail.py line 82): The `query_one("#detail-sql", Static)` selector still works after wrapping in VerticalScroll because it queries by id, not by position.

---

## Shared Patterns

### `Static.update()` pattern
**Source:** `terminair/screens/model_list.py` lines 124-128 and `terminair/screens/problems.py` lines 142-146
**Apply to:** All new Static widget update methods in this phase
```python
def _update_meta(self) -> None:
    meta = self.query_one("#some-widget-id", Static)
    meta.update(f"... formatted string ...")
```

### `DbtScreen.BINDINGS` extension pattern
**Source:** `terminair/screens/model_list.py` lines 62-65
**Apply to:** `terminair/screens/detail.py` BINDINGS replacement
```python
BINDINGS = DbtScreen.BINDINGS + [
    Binding("key", "action_name", "Label"),
    Binding("key", "action_with_arg('value')", "Label", show=False),
]
```

### `set_interval` pattern
**Source:** `terminair/app.py` lines 183-184
**Apply to:** `terminair/screens/model_list.py` `on_mount()`
```python
self.set_interval(1.0, self._update_header)
```
Call in `on_mount()` after `await self._load_models()`. The callback must NOT trigger data reload.

### Error feedback pattern
**Source:** `terminair/screens/base.py` (inherited by all screens)
**Apply to:** Any new method that calls external data
```python
try:
    # ... operation ...
except Exception as e:
    self.app_typed._flash_error(f"context: {str(e)[:80]}")
```

### `app_typed.get_config()` pattern
**Source:** `terminair/app.py` lines 291-292; `terminair/screens/base.py` lines 37-38
**Apply to:** `terminair/screens/model_list.py` `_update_header()`
```python
config = self.app_typed.get_config()
conn = config.connections.get(config.settings.default_connection)
url = conn.url if conn else "demo"
```

### RegressionAnalyzer usage pattern
**Source:** `terminair/screens/problems.py` lines 10, 70
**Apply to:** `terminair/screens/model_list.py` `_update_statusbar()`
```python
from terminair.dbt.regression import RegressionAnalyzer
signals = RegressionAnalyzer(self._models).analyze()
warnings = sum(1 for s in signals if s.severity in ("critical", "warning"))
```

## No Analog Found

None. All three gaps map directly to patterns present in the existing codebase or in the Textual standard library (`VerticalScroll`).

## Metadata

**Analog search scope:** `terminair/screens/`, `terminair/app.py`, `terminair/config.py`
**Files scanned:** 7 (base.py, model_list.py, problems.py, lineage.py, detail.py, app.py, config.py)
**Pattern extraction date:** 2026-05-15
