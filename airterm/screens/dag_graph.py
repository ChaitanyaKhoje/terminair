"""DAG Graph screen - ASCII dependency visualization."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class DAGGraphScreen(Screen):
    """ASCII rendering of task dependencies."""

    CSS = """
    DAGGraphScreen {
        layout: grid;
        grid-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="graph-content")
        yield Static("Press g to view graph", id="graph-empty")

    def render_graph(self, tasks: list, edges: list):
        if not tasks:
            empty = self.query_one("#graph-empty")
            empty.show()
            return

        graph = self.query_one("#graph-content")
        ranks = self._compute_ranks(tasks, edges)
        lines = self._render_lines(tasks, ranks)
        graph.update("\n".join(lines))

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

    def _render_lines(self, tasks: list, ranks: dict) -> list:
        if not ranks:
            return ["No graph data"]
        max_rank = max(ranks.values()) if ranks else 0
        lines = []
        for rank in range(max_rank + 1):
            rank_tasks = [t for t in tasks if ranks.get(t["id"]) == rank]
            if rank_tasks:
                row = " -> ".join([t["id"] for t in rank_tasks])
                lines.append(row)
        return lines or ["No tasks"]
