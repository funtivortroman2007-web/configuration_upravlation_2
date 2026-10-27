"""Command-line entry point for the dependency graph prototype."""

import argparse
import sys
from collections.abc import Sequence

from src.apk_repository import RepositoryError, get_direct_dependencies
from src.config import ConfigError, load_config


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Проверить конфигурацию визуализатора графа зависимостей."
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
        print(f"Ошибка конфигурации:\n{error}", file=sys.stderr)
        return 2

    try:
        dependencies = get_direct_dependencies(
            config.repository,
            config.package_name,
            config.version,
            config.test_mode,
        )
    except RepositoryError as error:
        print(f"Ошибка репозитория APK:\n{error}", file=sys.stderr)
        return 3

    print(f"Прямые зависимости {config.package_name} версии {config.version}:")
    if dependencies:
        for dependency in dependencies:
            print(dependency)
    else:
        print("(нет)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())