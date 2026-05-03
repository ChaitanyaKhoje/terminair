"""Critical path discovery for DAGs."""

from collections import deque


class DAGNode:
    def __init__(self, task_id: str, upstream: list | None = None):
        self.task_id = task_id
        self.upstream = upstream or []


def build_dag_graph(tasks: list) -> dict:
    graph = {}
    for task in tasks:
        task_id = task.get("task_id", "")
        upstream = task.get("upstream_task_ids", [])
        graph[task_id] = DAGNode(task_id, upstream)
    return graph


def find_critical_path(graph: dict) -> list:
    if not graph:
        return []

    roots = [tid for tid, node in graph.items() if not node.upstream]
    if not roots:
        roots = list(graph.keys())[:1]

    def dfs(node: DAGNode, visited: set) -> tuple[list[str], int]:
        if node.task_id in visited:
            return [], 0

        visited.add(node.task_id)
        path = [node.task_id]

        children = [tid for tid, n in graph.items() if node.task_id in n.upstream]

        if not children:
            return path, 1

        longest = []
        max_len = 0
        for child_id in children:
            if child_id in visited:
                continue
            child = graph.get(child_id)
            if child:
                sub_path, sub_len = dfs(child, visited.copy())
                if sub_len > max_len:
                    max_len = sub_len
                    longest = sub_path

        return path + longest, max_len + 1

    all_paths = []
    for root_id in roots:
        root = graph.get(root_id)
        if root:
            path, _ = dfs(root, set())
            if path:
                all_paths.append(path)

    all_paths.sort(key=len, reverse=True)
    return all_paths[0] if all_paths else []


def get_task_depth(graph: dict, task_id: str) -> int:
    node = graph.get(task_id)
    if not node:
        return 0

    if not node.upstream:
        return 0

    max_depth = 0
    for upstream_id in node.upstream:
        depth = get_task_depth(graph, upstream_id)
        max_depth = max(max_depth, depth)

    return max_depth + 1


def topological_sort(graph: dict) -> list:
    in_degree = {tid: 0 for tid in graph}
    for tid, node in graph.items():
        for upstream in node.upstream:
            if upstream in in_degree:
                in_degree[tid] += 1

    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    result = []

    while queue:
        current = queue.popleft()
        result.append(current)

        for tid, node in graph.items():
            if current in node.upstream:
                in_degree[tid] -= 1
                if in_degree[tid] == 0:
                    queue.append(tid)

    return result
