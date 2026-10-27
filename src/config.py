"""Loading and validation for the application INI configuration."""

import configparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class AppConfig:
    package_name: str
    repository: str
    test_mode: bool
    version: str
    output_file: str


class ConfigError(ValueError):
    """Raised when the INI file is missing, malformed, or invalid."""


def _read_settings(config_path: Path) -> dict[str, str]:
    parser = configparser.ConfigParser()
    try:
        with config_path.open(encoding="utf-8") as config_file:
            parser.read_file(config_file)
    except OSError as error:
        message = "Не удалось прочитать конфигурационный файл: "
        raise ConfigError(f"{message}{error}") from error
    except configparser.Error as error:
        raise ConfigError(f"Некорректный INI-файл: {error}") from error

    if not parser.has_section("settings"):
        raise ConfigError(
            "В конфигурационном файле отсутствует секция [settings]."
        )

    names = (
        "package_name",
        "repository",
        "test_mode",
        "version",
        "output_file",
    )
    values: dict[str, str] = {}
    errors: list[str] = []
    for name in names:
        if parser.has_option("settings", name):
            values[name] = parser.get("settings", name).strip()
        else:
            errors.append(
                f"Не задан обязательный параметр [settings] {name}."
            )
    if errors:
        raise ConfigError("\n".join(errors))
    return values


def _validate_package_name(value: str, errors: list[str]) -> str:
    if not value:
        errors.append("Параметр package_name не может быть пустым.")
    elif any(character.isspace() for character in value):
        errors.append(
            "Параметр package_name не должен содержать пробелы."
        )
    return value


def _parse_test_mode(value: str, errors: list[str]) -> bool | None:
    raw_value = value.lower()
    if raw_value not in {"true", "false"}:
        errors.append("Параметр test_mode должен быть true или false.")
        return None
    return raw_value == "true"


def _validate_repository(
    repository: str,
    test_mode: bool | None,
    errors: list[str],
) -> None:
    if not repository:
        errors.append("Параметр repository не может быть пустым.")
        return

    if test_mode is None:
        return

    if test_mode:
        repository_path = Path(repository).expanduser()
        if not repository_path.is_file():
            message = (
                "В режиме test_mode=true параметр repository должен указывать "
                "на существующий файл тестового репозитория: "
            )
            errors.append(f"{message}{repository}.")
        return

    parsed_url = urlparse(repository)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        message = (
            "В режиме test_mode=false параметр repository должен быть "
            "полным HTTP(S) URL с именем хоста."
        )
        errors.append(message)


def _validate_version(value: str, errors: list[str]) -> str:
    if not value:
        errors.append("Параметр version не может быть пустым.")
    elif any(character.isspace() for character in value):
        errors.append("Параметр version не должен содержать пробелы.")
    return value


def _validate_output_file(value: str, errors: list[str]) -> str:
    output_path = Path(value)
    if not value:
        errors.append("Параметр output_file не может быть пустым.")
    elif output_path.name != value or value in {".", ".."}:
        errors.append(
            "Параметр output_file должен содержать только имя файла."
        )
    elif output_path.suffix.lower() not in {".png", ".svg"}:
        errors.append(
            "Параметр output_file должен иметь расширение .png или .svg."
        )
    return value


def load_config(config_path: str | Path) -> AppConfig:
    """Load an INI file and report all invalid user-configurable parameters."""
    path = Path(config_path)
    values = _read_settings(path)
    errors: list[str] = []

    package_name = _validate_package_name(values["package_name"], errors)
    parsed_test_mode = _parse_test_mode(values["test_mode"], errors)
    test_mode = parsed_test_mode if parsed_test_mode is not None else False
    repository = values["repository"]
    _validate_repository(repository, parsed_test_mode, errors)
    version = _validate_version(values["version"], errors)
    output_file = _validate_output_file(values["output_file"], errors)

    if errors:
        raise ConfigError("\n".join(errors))

    return AppConfig(
        package_name=package_name,
        repository=repository,
        test_mode=test_mode,
        version=version,
        output_file=output_file,
    )
