"""Error extraction from task logs."""

import re
from typing import Optional


ERROR_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\):(.+?)(?:[\n]?\Z|\n\n|\r\n\r\n)", re.DOTALL),
    re.compile(r"(\w+Exception): (.+)$", re.MULTILINE),
    re.compile(r"(\w+Error): (.+)$", re.MULTILINE),
]


def extract_error(log_content: str) -> dict:
    lines = log_content.strip().split("\n")

    for pattern in ERROR_PATTERNS:
        match = pattern.search(log_content)
        if match:
            return {
                "summary": match.group(0).strip().split("\n")[-1].strip()[:200],
                "traceback": match.group(0)[:5000] if match.lastindex else None,
            }

    if lines:
        last_line = lines[-1].strip()
        if last_line:
            return {
                "summary": last_line[:200],
                "traceback": None,
            }

    return {
        "summary": "No error information found",
        "traceback": None,
    }


def parse_traceback_line(line: str) -> Optional[str]:
    if "File " in line and ", line " in line:
        match = re.search(r'File "([^"]+)", line (\d+)', line)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
    return None
