# Failure Heatmap Redesign: Color-Based Intensity and Accessibility

## Context

Current: The DAG "Failure Heatmap" in airterm/screens/dag_detail.py renders a 7×24 grid, with failure frequency for each hour indicated by darkness (“darker = more failures”).

Goal: Replace “darker” mapping with a color-based (ANSI/Textual) intensity mapping, a clear legend, dual accessibility (color & monochrome), and improved hover/focus details. No font/terminal assumptions beyond reasonable 2026 modern terminals.

---

## Design Overview

- **Grid:** 7 rows (days) × 24 cols (hours), each cell represents failures in that hour for a given day.
- **Primary encoding:**
  - **Color background (recommended):** Each cell displays a background color according to a severity gradient (green → yellow → orange → red; or customizable palette).
  - **Optional numeric overlay:** For cells with N > 0, show a single-digit count (or max/min symbol) in the cell if space permits.
  - **Hover/focus:** When focusing/hovering on a cell, show exact failure count, and optionally the top failing DAG(s) for that slot in a popover or sidebar.
- **Secondary encoding (fallback):** When color is not supported or for accessibility, use Unicode shade blocks:
    - ░ (low), ▒ (mod), ▓ (high), █ (max)
    - Legend text: “░ = 0–1, ▒ = 2–5, ▓ = 6–10, █ = 11+” (buckets configurable)
- **Legend:** Always include a dynamic legend mapping color/blocks to count buckets at the top of the heatmap display, e.g.:
    - “Heatmap: green (0–1) → yellow (2–5) → orange (6–10) → red (11+)”

---

## Rendering & Bucketing

- Buckets:
    - Default: 0–1 (green/░), 2–5 (yellow/▒), 6–10 (orange/▓), 11+ (red/█)
    - Option: support log-scale bucketing if failure rates are highly skewed
- **Implementation:**
    - Use Textual’s background color (ANSI truecolor) for cell coloring
    - Use spaces or fixed-width block characters for cell content
    - Add numeric overlay if space allows
    - For fallback: replace with appropriate Unicode shade
- **Accessibility:** Allow a toggle to switch color palette (colorblind-friendly) or to turn on monochrome blocks

---

## Integration

- Update airterm/screens/dag_detail.py:
    - In `heatmap_section`, change legend to “Failure Heatmap (color = failures — see legend)”
    - Add rendering logic for color intensity and Unicode fallback
    - Ensure keyboard focus selects a cell and updates detail view with count, time (and optionally top failing DAGs)
    - Preserve grid layout and tooltips/panels for detail
- **No change to data collection**, only to visualization

---

## Testing
- Confirm color and fallback rendering in at least one color and one non-color terminal
- Verify that the legend is descriptive and contextually accurate
- Check that keyboard navigation/focus works and always updates details
- Confirm accessibility toggle, if implemented, works

---

## Future (optional, out of initial scope)
- User-customizable color palette
- Exportable/printable version of heatmap (text and color)
- Tooltip analytics (failure trends, annotations)

---

## Summary (for README)

Old: “Failure Heatmap (darker = more failures)” → New: “Failure Heatmap (color = failures — see legend)” with dynamic ANSI coloring and a Unicode fallback for wide compatibility.
