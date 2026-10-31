import tempfile
import unittest
from pathlib import Path

from src.dependency_graph import (
    GraphError,
    load_test_graph,
    reachable_graph,
)


class DependencyGraphTests(unittest.TestCase):
    def load_graph(self, content: str) -> dict[str, list[str]]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "repository.txt"
            path.write_text(content, encoding="utf-8")
            return load_test_graph(path)

    def test_builds_transitive_graph_through_diamond(self) -> None:
        graph = self.load_graph("A: B C\nB: D\nC: D\nD:\n")

        self.assertEqual(
            reachable_graph(graph, "A"),
            {"A": ["B", "C"], "B": ["D"], "D": [], "C": ["D"]},
        )

    def test_cycles_do_not_recurse_forever_and_keep_cycle_edges(self) -> None:
        graph = self.load_graph("A: B\nB: C\nC: A D\nD:\n")

        self.assertEqual(
            reachable_graph(graph, "A"),
            {"A": ["B"], "B": ["C"], "C": ["A", "D"], "D": []},
        )

    def test_unreachable_nodes_are_not_included(self) -> None:
        graph = self.load_graph("A: B\nB:\nX: Y\nY:\n")

        self.assertEqual(reachable_graph(graph, "A"), {"A": ["B"], "B": []})

    def test_rejects_non_uppercase_package_names(self) -> None:
        with self.assertRaisesRegex(GraphError, "больших латинских букв"):
            self.load_graph("A: B\nb:\n")

    def test_rejects_duplicate_package_definitions(self) -> None:
        with self.assertRaisesRegex(GraphError, "указан повторно"):
            self.load_graph("A: B\nA:\n")

    def test_rejects_unknown_root(self) -> None:
        graph = self.load_graph("A:\n")

        with self.assertRaisesRegex(GraphError, "отсутствует"):
            reachable_graph(graph, "B")

    def test_supports_comments_and_implicit_leaf_nodes(self) -> None:
        graph = self.load_graph("# sample\nA: B C # root\n")

        self.assertEqual(graph, {"A": ["B", "C"], "B": [], "C": []})


if __name__ == "__main__":
    unittest.main()
