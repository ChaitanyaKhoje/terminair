"""Tests to enforce read-only contract for AirflowBridge."""

from __future__ import annotations

import ast
import inspect
import textwrap

# Exact HTTP-verb names and common write-operation prefixes to scan for.
_WRITE_HTTP_METHODS = {"post", "put", "delete", "patch"}
_WRITE_PREFIXES = (
    "post_", "put_", "delete_", "patch_",
    "create_", "update_", "trigger_", "enable_", "disable_",
    "unpause_", "clear_",
)


def _source_calls_write_http(fn: object) -> bool:
    """Return True if the callable source contains .post(/.put(/.delete(/.patch( calls."""
    try:
        src = textwrap.dedent(inspect.getsource(fn))  # type: ignore[arg-type]
        tree = ast.parse(src)
    except (OSError, SyntaxError, TypeError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _WRITE_HTTP_METHODS:
            return True
    return False


def test_airflow_bridge_has_no_write_methods():
    """AirflowBridge must expose zero write methods.

    Checks:
    - Exact HTTP-verb names: post, put, delete, patch
    - Common write-operation name prefixes (post_, create_, trigger_, etc.)
    - Method bodies that call .post(/.put(/.delete(/.patch( via AST analysis
    - Covers regular methods, classmethods, and staticmethods (isroutine)
    """
    from terminair.dbt.airflow_bridge import AirflowBridge

    members = inspect.getmembers(AirflowBridge, predicate=inspect.isroutine)
    violations = [
        name
        for name, fn in members
        if not name.startswith("_")
        and (
            name.lower() in _WRITE_HTTP_METHODS
            or any(name.lower().startswith(p) for p in _WRITE_PREFIXES)
            or _source_calls_write_http(fn)
        )
    ]
    assert not violations, f"Found write methods on AirflowBridge: {violations}"
