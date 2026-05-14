"""Tests for ManifestLoader — node lookup, grain extraction, var() parsing, lineage."""

from __future__ import annotations

from pathlib import Path

import pytest

from terminair.dbt.manifest import ManifestLoader

FIXTURES = Path(__file__).parent.parent.parent / "dbt" / "fixtures"


def test_manifest_loads_all_nodes():
    """ManifestLoader loads all 10 nodes from the fixture manifest."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    assert len(ml.get_all_node_ids()) == 10


def test_get_node_returns_dict():
    """get_node() returns the node dict for a known node_id."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    node = ml.get_node("model.my_project.fct_revenue_daily")
    assert node is not None
    assert node["name"] == "fct_revenue_daily"


def test_get_node_returns_none_for_unknown():
    """get_node() returns None (not KeyError) for unknown node_id."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    assert ml.get_node("nonexistent.model.id") is None


def test_missing_manifest_raises_file_not_found(tmp_path):
    """ManifestLoader raises FileNotFoundError for a missing manifest path."""
    with pytest.raises(FileNotFoundError, match="manifest.json"):
        ManifestLoader(tmp_path / "missing.json")


def test_grain_columns_string_unique_key():
    """get_grain_columns returns [str] for a node with a string unique_key."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    grain = ml.get_grain_columns("model.my_project.fct_revenue_daily")
    assert grain == ["revenue_date"]


def test_grain_columns_list_unique_key():
    """get_grain_columns returns a list for a node with a list unique_key."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    grain = ml.get_grain_columns("model.my_project.fct_risk_exposure")
    assert isinstance(grain, list)
    assert len(grain) == 2
    assert "risk_date" in grain
    assert "entity_id" in grain


def test_grain_columns_fallback_empty():
    """get_grain_columns returns [] when no grain can be detected."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    # mart_finance_summary has no unique_key or partition_by
    grain = ml.get_grain_columns("model.my_project.mart_finance_summary")
    assert grain == []


def test_get_dbt_vars_with_default():
    """get_dbt_vars extracts var with a default value."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    vars_dict = ml.get_dbt_vars("model.my_project.fct_revenue_daily")
    assert "run_date" in vars_dict
    assert vars_dict["run_date"] == "CURRENT_DATE"


def test_get_dbt_vars_empty_for_no_sql():
    """get_dbt_vars returns a dict (possibly empty) for nodes without vars."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    # stg_payments has no var() calls in its raw_code
    vars_dict = ml.get_dbt_vars("model.my_project.stg_payments")
    assert isinstance(vars_dict, dict)


def test_build_tag_index():
    """build_tag_index returns dict with correct tag groupings."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    idx = ml.build_tag_index()
    assert "finance" in idx
    assert len(idx["finance"]) == 3
    assert "marketing" in idx
    assert len(idx["marketing"]) == 2


def test_get_all_tags_sorted():
    """get_all_tags returns sorted unique tag list."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    tags = ml.get_all_tags()
    assert isinstance(tags, list)
    assert tags == sorted(set(tags))
    assert "finance" in tags


def test_get_nodes_by_tag():
    """get_nodes_by_tag returns nodes matching a given tag."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    finance_nodes = ml.get_nodes_by_tag("finance")
    assert len(finance_nodes) == 3


def test_get_upstream_deps():
    """get_upstream_deps returns upstream node_ids for a known node."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    deps = ml.get_upstream_deps("model.my_project.fct_revenue_daily")
    assert isinstance(deps, list)
    assert len(deps) >= 1


def test_get_downstream_deps():
    """get_downstream_deps returns downstream node_ids from child_map."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    # stg_orders or stg_payments should have downstream deps
    deps = ml.get_downstream_deps("model.my_project.stg_orders")
    assert isinstance(deps, list)


def test_get_full_lineage_depth_one():
    """get_full_lineage with depth=1 returns only one upstream level."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    lineage = ml.get_full_lineage("model.my_project.fct_revenue_daily", depth=1)
    assert lineage["node_id"] == "model.my_project.fct_revenue_daily"
    assert "upstream" in lineage
    for up in lineage["upstream"]:
        # At depth=1, upstream items should have empty upstream themselves
        assert up["upstream"] == []


def test_get_full_lineage_unlimited():
    """get_full_lineage with default depth traverses the full DAG."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    lineage = ml.get_full_lineage("model.my_project.fct_revenue_daily")
    assert lineage["node_id"] == "model.my_project.fct_revenue_daily"
    assert "upstream" in lineage
    assert "downstream" in lineage


def test_get_refs():
    """get_refs returns model names referenced by a node."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    refs = ml.get_refs("model.my_project.fct_revenue_daily")
    assert isinstance(refs, list)
    # fct_revenue_daily refs stg_orders and stg_payments
    assert "stg_orders" in refs or "stg_payments" in refs


def test_get_sources():
    """get_sources returns source.table formatted strings."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    # stg_orders sources raw.orders
    sources = ml.get_sources("model.my_project.stg_orders")
    assert isinstance(sources, list)
    assert len(sources) >= 1
    assert any("raw" in s for s in sources)


def test_get_config():
    """get_config returns the node's config dict."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    config = ml.get_config("model.my_project.fct_revenue_daily")
    assert isinstance(config, dict)
    assert "materialized" in config


def test_var_extraction_required(tmp_path):
    """get_dbt_vars returns REQUIRED for vars without a default value."""
    # Write a minimal manifest with a node that has var('some_var') — no default
    manifest_data = {
        "nodes": {
            "model.test.my_model": {
                "unique_id": "model.test.my_model",
                "name": "my_model",
                "tags": [],
                "config": {"materialized": "view"},
                "raw_code": "SELECT {{ var('some_var') }} AS val",
                "depends_on": {"nodes": []},
                "refs": [],
                "sources": [],
            }
        },
        "parent_map": {},
        "child_map": {},
    }
    import json
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data))

    ml = ManifestLoader(manifest_path)
    vars_dict = ml.get_dbt_vars("model.test.my_model")
    assert "some_var" in vars_dict
    assert vars_dict["some_var"] == "REQUIRED"


def test_tag_index_all_tags_covered():
    """build_tag_index returns entries for all expected tags."""
    ml = ManifestLoader(FIXTURES / "manifest.json")
    idx = ml.build_tag_index()
    for tag in ("finance", "marketing", "core", "platform", "risk"):
        assert tag in idx, f"Expected tag '{tag}' in tag index"
