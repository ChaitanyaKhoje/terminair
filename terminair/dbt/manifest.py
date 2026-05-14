"""dbt manifest.json loader — node lookup, lineage, grain extraction, var() parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from terminair.logging_utils import get_logger

_log = get_logger(__name__)
_VAR_PATTERN = re.compile(r"""var\(['"](\w+)['"](?:,\s*([^)]+))?\)""")


class ManifestLoader:
    """Load and query a dbt manifest.json artifact.

    Provides node lookup, lineage traversal, grain column detection, var()
    extraction, and tag indexing. All data is loaded eagerly in __init__.
    """

    def __init__(self, manifest_path: Path) -> None:
        """Load manifest from the given path.

        Args:
            manifest_path: Path to manifest.json.

        Raises:
            FileNotFoundError: If manifest_path does not exist.
        """
        manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found: {manifest_path}")

        with open(manifest_path) as f:
            data = json.load(f)

        self._nodes: dict[str, dict] = data.get("nodes", {})
        self._parent_map: dict[str, list[str]] = data.get("parent_map", {})
        self._child_map: dict[str, list[str]] = data.get("child_map", {})

        _log.debug(
            "ManifestLoader loaded %d nodes from %s",
            len(self._nodes),
            manifest_path,
        )

    # ------------------------------------------------------------------
    # Node access
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> dict | None:
        """Return the node dict for the given unique_id, or None if not found."""
        return self._nodes.get(node_id)

    def get_all_node_ids(self) -> list[str]:
        """Return all node unique_ids in the manifest."""
        return list(self._nodes.keys())

    # ------------------------------------------------------------------
    # Tag queries
    # ------------------------------------------------------------------

    def get_nodes_by_tag(self, tag: str) -> list[dict]:
        """Return all nodes that have the given tag."""
        return [n for n in self._nodes.values() if tag in n.get("tags", [])]

    def get_all_tags(self) -> list[str]:
        """Return a sorted list of unique tags across all nodes."""
        tags: set[str] = set()
        for node in self._nodes.values():
            tags.update(node.get("tags", []))
        return sorted(tags)

    def build_tag_index(self) -> dict[str, list[str]]:
        """Return a mapping of tag → list of node_ids that carry that tag."""
        return {
            tag: [
                node_id
                for node_id, node in self._nodes.items()
                if tag in node.get("tags", [])
            ]
            for tag in self.get_all_tags()
        }

    # ------------------------------------------------------------------
    # Dependency queries
    # ------------------------------------------------------------------

    def get_upstream_deps(self, node_id: str) -> list[str]:
        """Return upstream node_ids for node_id.

        Uses parent_map if available; falls back to depends_on.nodes in the
        node dict when the parent_map has no entry for this node.
        """
        if node_id in self._parent_map:
            return list(self._parent_map[node_id])
        node = self._nodes.get(node_id, {})
        return list(node.get("depends_on", {}).get("nodes", []))

    def get_downstream_deps(self, node_id: str) -> list[str]:
        """Return downstream node_ids for node_id from child_map."""
        return list(self._child_map.get(node_id, []))

    def get_full_lineage(
        self,
        node_id: str,
        depth: int = -1,
        *,
        _visited: frozenset[str] | None = None,
    ) -> dict:
        """Return a recursive lineage dict for node_id.

        Args:
            node_id: The node to build lineage for.
            depth: Maximum traversal depth. -1 means unlimited. 0 returns the
                node with empty upstream/downstream lists.
            _visited: Internal cycle-guard set (do not pass from outside).

        Returns:
            Dict with keys: node_id, upstream (list of lineage dicts),
            downstream (list of lineage dicts).
        """
        if _visited is None:
            _visited = frozenset()

        visited = _visited | {node_id}

        if depth == 0:
            return {"node_id": node_id, "upstream": [], "downstream": []}

        next_depth = depth - 1 if depth > 0 else -1

        upstream = []
        for up_id in self.get_upstream_deps(node_id):
            if up_id not in visited:
                upstream.append(
                    self.get_full_lineage(up_id, next_depth, _visited=visited)
                )

        downstream = []
        for dn_id in self.get_downstream_deps(node_id):
            if dn_id not in visited:
                downstream.append(
                    self.get_full_lineage(dn_id, next_depth, _visited=visited)
                )

        return {"node_id": node_id, "upstream": upstream, "downstream": downstream}

    # ------------------------------------------------------------------
    # Grain extraction
    # ------------------------------------------------------------------

    def get_grain_columns(self, node_id: str) -> list[str]:
        """Detect the grain columns for a node.

        Precedence (locked in CONTEXT.md):
        1. config.unique_key (string or list)
        2. config.partition_by.field
        3. Fallback: []

        Returns:
            List of grain column name strings, possibly empty.
        """
        node = self._nodes.get(node_id, {})
        config = node.get("config", {})

        # Step 1: config.unique_key
        unique_key = config.get("unique_key")
        if isinstance(unique_key, str) and unique_key:
            return [unique_key]
        if isinstance(unique_key, list) and unique_key:
            return list(unique_key)

        # Step 2: config.partition_by.field
        partition_by = config.get("partition_by")
        if isinstance(partition_by, dict) and partition_by.get("field"):
            return [partition_by["field"]]

        # Step 4: fallback
        return []

    # ------------------------------------------------------------------
    # Code and variable extraction
    # ------------------------------------------------------------------

    def get_dbt_vars(self, node_id: str) -> dict[str, str]:
        """Extract var() calls from a node's raw_code or compiled_code.

        Returns:
            Dict of {var_name: default_value_or_"REQUIRED"}.
        """
        node = self._nodes.get(node_id, {})
        raw_code = node.get("raw_code")
        compiled_code = node.get("compiled_code")
        sql = raw_code or compiled_code or ""

        result: dict[str, str] = {}
        for match in _VAR_PATTERN.finditer(sql):
            var_name = match.group(1)
            default = match.group(2)
            result[var_name] = (
                default.strip().strip("'\"") if default else "REQUIRED"
            )
        return result

    # ------------------------------------------------------------------
    # Refs and sources
    # ------------------------------------------------------------------

    def get_refs(self, node_id: str) -> list[str]:
        """Return flat list of model names referenced via ref() in a node.

        Each entry in node["refs"] is a list of one element: the model name.
        """
        node = self._nodes.get(node_id, {})
        refs = node.get("refs", [])
        return [r[0] for r in refs if r]

    def get_sources(self, node_id: str) -> list[str]:
        """Return formatted source strings for a node.

        Each entry in node["sources"] is [source_name, table_name].
        Returns strings formatted as "source_name.table_name".
        """
        node = self._nodes.get(node_id, {})
        sources = node.get("sources", [])
        return [".".join(s) for s in sources if len(s) >= 2]

    # ------------------------------------------------------------------
    # Config access
    # ------------------------------------------------------------------

    def get_config(self, node_id: str) -> dict:
        """Return the config block for a node, or empty dict if not found."""
        return self._nodes.get(node_id, {}).get("config", {})
