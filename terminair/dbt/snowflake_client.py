"""SnowflakeClient — bytes_scanned per model. Real connection deferred to v2; mock via DI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from terminair.logging_utils import get_logger

_log = get_logger(__name__)


class SnowflakeClient:
    """Retrieves bytes_scanned per dbt model from Snowflake query history.

    In v1, only mock mode is implemented.  Set TERMINAIR_MOCK_SNOWFLAKE=1 (or
    'true', 'yes', 'on') to load fixture data from query_history.json.  Without
    that env var, all lookups return None (no real Snowflake connection is made).

    The *fixture_path* kwarg supports dependency injection in tests — pass an
    explicit Path to override the default fixture location.

    Usage::

        sc = SnowflakeClient()
        bytes_val = sc.get_bytes_scanned("fct_revenue_daily")  # int | None
    """

    def __init__(self, fixture_path: Path | None = None) -> None:
        self._mock = (
            os.environ.get("TERMINAIR_MOCK_SNOWFLAKE", "").strip().lower()
            in {"1", "true", "yes", "on"}
        )
        self._fixture_path: Path = fixture_path or (
            Path(__file__).parent / "fixtures" / "query_history.json"
        )
        self._mock_data: dict[str, int] | None = None

        if self._mock:
            with open(self._fixture_path) as f:
                self._mock_data = json.load(f)
            _log.debug(
                "SnowflakeClient loaded mock data: %d models",
                len(self._mock_data),
            )

    def get_bytes_scanned(self, model_name: str) -> int | None:
        """Return bytes scanned for *model_name* (short name, not full unique_id).

        Returns None when mock mode is disabled or the model is not in the
        fixture.  Real Snowflake connection is deferred to v2.
        """
        if self._mock and self._mock_data is not None:
            return self._mock_data.get(model_name)
        return None
