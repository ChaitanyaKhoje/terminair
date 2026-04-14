"""Error extraction from task logs."""

import re
from difflib import SequenceMatcher
from typing import Optional


ERROR_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\):(.+?)(?:[\n]?\Z|\n\n|\r\n\r\n)", re.DOTALL),
    re.compile(r"(\w+Exception): (.+)$", re.MULTILINE),
    re.compile(r"(\w+Error): (.+)$", re.MULTILINE),
]

SIMILARITY_THRESHOLD = 0.80


def normalize_error(error_msg: str) -> str:
    normalized = re.sub(r"\d+", "N", error_msg)
    normalized = re.sub(r"0x[0-9a-f]+", "0xN", normalized)
    normalized = re.sub(r"/[^/]+/", "/PATH/", normalized)
    normalized = re.sub(r"['\"]+", "'", normalized)
    return normalized


def cluster_errors(errors: list[dict]) -> list[dict]:
    if not errors:
        return []

    clusters = []
    used = set()

    for i, error in enumerate(errors):
        if i in used:
            continue

        error_msg = normalize_error(error.get("summary", ""))
        cluster_dags = [error.get("dag_id", "?")]

        for j, other in enumerate(errors):
            if j <= i or j in used:
                continue

            other_msg = normalize_error(other.get("summary", ""))
            ratio = SequenceMatcher(None, error_msg, other_msg).ratio()

            if ratio >= SIMILARITY_THRESHOLD:
                used.add(j)
                cluster_dags.append(other.get("dag_id", "?"))

        used.add(i)
        clusters.append(
            {
                "representative": error_msg[:100],
                "count": len(cluster_dags),
                "dags": cluster_dags[:5],
            }
        )

    clusters.sort(key=lambda x: x["count"], reverse=True)
    return clusters


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
