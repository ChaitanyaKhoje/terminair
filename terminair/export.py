"""Export functionality for read-only data output."""

import csv
import json
from io import StringIO
from typing import Any


def export_json(data: list[dict[str, Any]], pretty: bool = True) -> str:
    if pretty:
        return json.dumps(data, indent=2, default=str)
    return json.dumps(data, default=str)


def export_csv(data: list[dict[str, Any]]) -> str:
    if not data:
        return ""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def export_clipboard(data: list[dict[str, Any]]) -> str:
    return export_tsv(data)


def export_tsv(data: list[dict[str, Any]]) -> str:
    if not data:
        return ""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter="\t")
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
