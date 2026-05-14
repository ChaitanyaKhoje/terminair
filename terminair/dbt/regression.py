"""RegressionAnalyzer — detects row count and grain regressions across dbt model runs."""

from __future__ import annotations

from terminair.dbt.models import ModelState, RegressionSignal, Severity

_SEVERITY_ORDER = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}


class RegressionAnalyzer:
    """Detect regressions in row counts, grain columns, and upstream schema changes.

    Supported signal types:
        row_drop              — row count fell by more than 10%
        row_spike             — row count rose by more than 50%
        grain_added           — grain_columns list grew (more granular)
        grain_removed         — grain_columns list shrank (less granular, data loss risk)
        upstream_schema_change — upstream model materialization or grain changed
        new_model_no_baseline  — model succeeded but rows_previous is None

    Thresholds (locked in CONTEXT.md):
        row_drop < -30%  → CRITICAL
        row_drop < -10%  → WARNING
        row_spike > +50% → WARNING
        grain_added      → WARNING
        grain_removed    → CRITICAL
        upstream_schema_change → WARNING
        new_model_no_baseline  → INFO

    Usage::

        ra = RegressionAnalyzer(current_models)
        signals = ra.analyze(previous_models)
        for signal in signals:
            print(signal.severity, signal.signal_type, signal.name)
    """

    def __init__(self, current: list[ModelState], manifest=None) -> None:
        """Store current model list.

        Args:
            current: Current-run list of ModelState instances.
            manifest: Optional ManifestLoader for upstream_schema_change detection
                      (currently unused; placeholder for future enrichment).
        """
        self._current = current
        self._manifest = manifest
        self._last_signals: list[RegressionSignal] = []

    def analyze(
        self, previous: list[ModelState] | None = None
    ) -> list[RegressionSignal]:
        """Detect all regression signals across self._current.

        Args:
            previous: Optional previous-run ModelState list for grain comparison.

        Returns:
            List of RegressionSignal sorted CRITICAL → WARNING → INFO.
        """
        signals: list[RegressionSignal] = []
        prev_map = {m.node_id: m for m in previous} if previous else {}

        for model in self._current:
            # ---------------------------------------------------------- #
            # row_drop / row_spike
            # ---------------------------------------------------------- #
            if model.row_delta_pct is not None:
                delta = model.row_delta_pct
                if delta < -30.0:
                    signals.append(
                        RegressionSignal(
                            node_id=model.node_id,
                            name=model.name,
                            signal_type="row_drop",
                            severity=Severity.CRITICAL,
                            description=(
                                f"Row count dropped {delta:.1f}% — exceeds -30% threshold"
                            ),
                            row_delta_pct=delta,
                        )
                    )
                elif delta < -10.0:
                    signals.append(
                        RegressionSignal(
                            node_id=model.node_id,
                            name=model.name,
                            signal_type="row_drop",
                            severity=Severity.WARNING,
                            description=(
                                f"Row count dropped {delta:.1f}% — exceeds -10% threshold"
                            ),
                            row_delta_pct=delta,
                        )
                    )

                if delta > 50.0:
                    signals.append(
                        RegressionSignal(
                            node_id=model.node_id,
                            name=model.name,
                            signal_type="row_spike",
                            severity=Severity.WARNING,
                            description=(
                                f"Row count spiked {delta:.1f}% — exceeds +50% threshold"
                            ),
                            row_delta_pct=delta,
                        )
                    )

            # ---------------------------------------------------------- #
            # new_model_no_baseline
            # ---------------------------------------------------------- #
            if model.rows_previous is None and model.status == "success":
                signals.append(
                    RegressionSignal(
                        node_id=model.node_id,
                        name=model.name,
                        signal_type="new_model_no_baseline",
                        severity=Severity.INFO,
                        description="No previous run baseline — cannot compute delta",
                    )
                )

            # ---------------------------------------------------------- #
            # grain_added / grain_removed (requires previous snapshot)
            # ---------------------------------------------------------- #
            if model.node_id in prev_map:
                prev_model = prev_map[model.node_id]
                prev_grain = prev_model.grain_columns
                curr_grain = model.grain_columns

                if len(curr_grain) > len(prev_grain):
                    signals.append(
                        RegressionSignal(
                            node_id=model.node_id,
                            name=model.name,
                            signal_type="grain_added",
                            severity=Severity.WARNING,
                            description=(
                                f"Grain expanded: {prev_grain} → {curr_grain}"
                            ),
                            grain_before=prev_grain,
                            grain_after=curr_grain,
                        )
                    )
                elif len(curr_grain) < len(prev_grain):
                    signals.append(
                        RegressionSignal(
                            node_id=model.node_id,
                            name=model.name,
                            signal_type="grain_removed",
                            severity=Severity.CRITICAL,
                            description=(
                                f"Grain contracted: {prev_grain} → {curr_grain}"
                            ),
                            grain_before=prev_grain,
                            grain_after=curr_grain,
                        )
                    )

            # ---------------------------------------------------------- #
            # upstream_schema_change
            # ---------------------------------------------------------- #
            for dep_id in model.upstream_deps:
                curr_dep = next(
                    (m for m in self._current if m.node_id == dep_id), None
                )
                prev_dep = prev_map.get(dep_id)

                if curr_dep is not None and prev_dep is not None:
                    mat_changed = (
                        curr_dep.materialization != prev_dep.materialization
                    )
                    grain_changed = curr_dep.grain_columns != prev_dep.grain_columns
                    if mat_changed or grain_changed:
                        signals.append(
                            RegressionSignal(
                                node_id=model.node_id,
                                name=model.name,
                                signal_type="upstream_schema_change",
                                severity=Severity.WARNING,
                                description=(
                                    f"Upstream '{dep_id.split('.')[-1]}' changed: "
                                    f"materialization={mat_changed}, grain={grain_changed}"
                                ),
                                detail=dep_id,
                            )
                        )

        # Sort: CRITICAL (0) → WARNING (1) → INFO (2)
        signals.sort(key=lambda s: _SEVERITY_ORDER[Severity(s.severity)])

        # Cache for signals_for_model()
        self._last_signals = signals
        return signals

    def signals_for_model(self, node_id: str) -> list[RegressionSignal]:
        """Return cached signals for a specific node_id.

        Must call analyze() before signals_for_model() to populate the cache.
        """
        return [s for s in self._last_signals if s.node_id == node_id]
