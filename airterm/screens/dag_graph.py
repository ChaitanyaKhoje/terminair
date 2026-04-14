"""DAG Graph screen - ASCII dependency visualization with critical path."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static

from airterm.metrics.critical_path import build_dag_graph, find_critical_path


class DAGGraphScreen(Screen):
    """ASCII rendering of task dependencies with critical path highlighted."""

    CSS = """
    DAGGraphScreen {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 3;
    }

    #graph-content {
        height: 100%;
        overflow-y: auto;
        padding: 1 2;
    }

    #graph-legend {
        height: 100%;
        background: $panel;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="graph-content")
        yield Static("", id="graph-legend")

    def render_graph(self, tasks: list, edges: list):
        if not tasks:
            self.query_one("#graph-content").update("No tasks found for this DAG.")
            return

        # Build graph using upstream representation for critical_path module
        # edges are (src, dst) i.e. downstream direction
        # critical_path module uses upstream_task_ids
        tasks_for_cp = []
        for t in tasks:
            tid = t["id"]
            upstream = [src for src, dst in edges if dst == tid]
            tasks_for_cp.append({"task_id": tid, "upstream_task_ids": upstream})

        graph = build_dag_graph(tasks_for_cp)
        critical_path = set(find_critical_path(graph))

        ranks = self._compute_ranks(tasks, edges)
        lines = self._render_lines(tasks, ranks, critical_path)

        self.query_one("#graph-content").update("\n".join(lines))
        cp_str = " → ".join(find_critical_path(graph)) if critical_path else "n/a"
        self.query_one("#graph-legend").update(
            f"[bold]Critical Path[/bold] (★): {cp_str}  |  Esc to go back"
        )

    def _compute_ranks(self, tasks: list, edges: list) -> dict:
        in_degree = {t["id"]: 0 for t in tasks}
        for src, dst in edges:
            in_degree[dst] = in_degree.get(dst, 0) + 1

        ranks = {}
        queue = [(t["id"], 0) for t in tasks if in_degree[t["id"]] == 0]
        while queue:
            node, rank = queue.pop(0)
            ranks[node] = max(ranks.get(node, 0), rank)
            for src, dst in edges:
                if src == node:
                    new_rank = rank + 1
                    if dst in ranks:
                        ranks[dst] = max(ranks[dst], new_rank)
                    else:
                        ranks[dst] = new_rank
                    queue.append((dst, new_rank))
        return ranks

    def _render_lines(self, tasks: list, ranks: dict, critical_path: set) -> list:
        if not ranks:
            return ["No graph data"]
        max_rank = max(ranks.values()) if ranks else 0
        lines = []
        for rank in range(max_rank + 1):
            rank_tasks = [t for t in tasks if ranks.get(t["id"]) == rank]
            if rank_tasks:
                parts = []
                for t in rank_tasks:
                    tid = t["id"]
                    label = f"★ {tid}" if tid in critical_path else tid
                    parts.append(label)
                lines.append("  →  ".join(parts))
        return lines or ["No tasks"]
