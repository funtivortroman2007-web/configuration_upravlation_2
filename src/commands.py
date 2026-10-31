"""Command-line entry point for the dependency graph prototype."""

import argparse
import sys
from collections.abc import Sequence

from src.apk_repository import RepositoryError, get_package_graph
from src.config import ConfigError, load_config
from src.dependency_graph import GraphError, load_test_graph, reachable_graph


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Проверить конфигурацию визуализатора графа зависимостей."
        )
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.ini",
        help="путь к INI-файлу (по умолчанию: config.ini)",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(
            f"Ошибка конфигурации:\n{error}",
            file=sys.stderr,
        )
        return 2

    try:
        if config.test_mode:
            repository_graph = load_test_graph(config.repository)
        else:
            repository_graph = get_package_graph(
                config.repository,
                config.package_name,
                config.version,
            )
        graph = reachable_graph(repository_graph, config.package_name)
    except RepositoryError as error:
        print(f"Ошибка репозитория APK:\n{error}", file=sys.stderr)
        return 3
    except GraphError as error:
        print(f"Ошибка тестового графа:\n{error}", file=sys.stderr)
        return 4

    print(f"Граф зависимостей {config.package_name}:")
    for package, dependencies in graph.items():
        values = ", ".join(dependencies) if dependencies else "(нет)"
        print(f"{package} -> {values}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())