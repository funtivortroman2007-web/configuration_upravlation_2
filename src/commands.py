"""Command-line entry point for the dependency graph prototype."""

import argparse
import sys
from collections.abc import Sequence

from src.config import ConfigError, load_config


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

    print(f"package_name={config.package_name}")
    print(f"repository={config.repository}")
    print(f"test_mode={str(config.test_mode).lower()}")
    print(f"version={config.version}")
    print(f"output_file={config.output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())