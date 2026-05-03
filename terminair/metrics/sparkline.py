"""Sparkline renderer for duration trends."""

SPARKLINE_CHARS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def compute_sparkline(durations: list[float], length: int = 20) -> str:
    if not durations:
        return ""

    durations = durations[-length:]
    max_dur = max(durations)
    if max_dur == 0:
        return " " * len(durations)

    sparkline = []
    for d in durations:
        idx = int((d / max_dur) * (len(SPARKLINE_CHARS) - 1))
        sparkline.append(SPARKLINE_CHARS[idx])

    return "".join(sparkline)


def render_pattern(states: list) -> str:
    symbols = []
    for state in states:
        if state == "success":
            symbols.append("✓")
        elif state == "failed":
            symbols.append("✗")
        else:
            symbols.append("?")
    return " ".join(symbols)
