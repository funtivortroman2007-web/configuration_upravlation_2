"""Parse test graphs and build reachable dependency subgraphs with DFS."""

import re
from pathlib import Path
from typing import TypeAlias

DependencyGraph: TypeAlias = dict[str, list[str]]
_PACKAGE_NAME = re.compile(r"[A-Z]+\Z")


class GraphError(ValueError):
    """Raised when a test graph is invalid or does not contain its root."""


def load_test_graph(path: str | Path) -> DependencyGraph:
    """Load an adjacency-list graph from a UTF-8 test repository file."""
    graph: DependencyGraph = {}
    try:
        lines = Path(path).expanduser().read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise GraphError(f"Не удалось прочитать файл тестового графа: {error}") from error

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.split("#", maxsplit=1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise GraphError(
                f"Строка {line_number}: ожидается формат «ПАКЕТ: ЗАВИСИМОСТЬ ...»."
            )

        package, dependency_text = line.split(":", maxsplit=1)
        package = package.strip()
        dependencies = dependency_text.split()
        if not _PACKAGE_NAME.fullmatch(package):
            raise GraphError(
                f"Строка {line_number}: имя пакета должно состоять "
                "из больших латинских букв."
            )
        if package in graph:
            raise GraphError(
                f"Строка {line_number}: пакет {package} указан повторно."
            )
        invalid_dependencies = [
            dependency
            for dependency in dependencies
            if not _PACKAGE_NAME.fullmatch(dependency)
        ]
        if invalid_dependencies:
            raise GraphError(
                f"Строка {line_number}: зависимости должны состоять "
                "из больших латинских букв."
            )
        graph[package] = dependencies

    if not graph:
        raise GraphError("Файл тестового графа не содержит пакетов.")

    referenced_packages = {
        dependency
        for dependencies in graph.values()
        for dependency in dependencies
    }
    for package in referenced_packages:
        graph.setdefault(package, [])
    return graph


def reachable_graph(graph: DependencyGraph, root: str) -> DependencyGraph:
    """Return all dependency edges reachable from root using recursive DFS."""
    if root not in graph:
        raise GraphError(f"Пакет {root} отсутствует в графе репозитория.")

    reachable: DependencyGraph = {}
    visited: set[str] = set()

    def visit(package: str) -> None:
        if package in visited:
            return
        visited.add(package)
        dependencies = graph.get(package, [])
        reachable[package] = list(dependencies)
        for dependency in dependencies:
            visit(dependency)

    visit(root)
    return reachable


def parse_dependency_names(dependencies: str) -> list[str]:
    """Extract package names from APK dependency constraints."""
    names = []
    for dependency in dependencies.split():
        if dependency.startswith("!"):
            continue
        name = re.split(r"[<>=]", dependency, maxsplit=1)[0]
        if name:
            names.append(name)
    return names
