"""Loading and validation for the application INI configuration."""

from configparser import ConfigParser, Error as ConfigParserError
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
    parser = ConfigParser()
    try:
        with config_path.open(encoding="utf-8") as config_file:
            parser.read_file(config_file)
    except OSError as error:
        raise ConfigError(f"Не удалось прочитать конфигурационный файл: {error}") from error
    except ConfigParserError as error:
        raise ConfigError(f"Некорректный INI-файл: {error}") from error

    if not parser.has_section("settings"):
        raise ConfigError("В конфигурационном файле отсутствует секция [settings].")

    names = ("package_name", "repository", "test_mode", "version", "output_file")
    values: dict[str, str] = {}
    errors: list[str] = []
    for name in names:
        if parser.has_option("settings", name):
            values[name] = parser.get("settings", name).strip()
        else:
            errors.append(f"Не задан обязательный параметр [settings] {name}.")
    if errors:
        raise ConfigError("\n".join(errors))
    return values


def load_config(config_path: str | Path) -> AppConfig:
    """Load an INI file and report all invalid user-configurable parameters."""
    path = Path(config_path)
    values = _read_settings(path)
    errors: list[str] = []

    package_name = values["package_name"]
    if not package_name:
        errors.append("Параметр package_name не может быть пустым.")
    elif any(character.isspace() for character in package_name):
        errors.append("Параметр package_name не должен содержать пробелы.")

    raw_test_mode = values["test_mode"].lower()
    if raw_test_mode not in {"true", "false"}:
        errors.append("Параметр test_mode должен быть true или false.")
        test_mode = False
    else:
        test_mode = raw_test_mode == "true"

    repository = values["repository"]
    if not repository:
        errors.append("Параметр repository не может быть пустым.")
    elif raw_test_mode in {"true", "false"}:
        if test_mode:
            repository_path = Path(repository).expanduser()
            if not repository_path.is_file():
                errors.append(
                    "В режиме test_mode=true параметр repository должен указывать "
                    f"на существующий файл тестового репозитория: {repository}."
                )
        else:
            parsed_url = urlparse(repository)
            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                errors.append(
                    "В режиме test_mode=false параметр repository должен быть "
                    "полным HTTP(S) URL с именем хоста."
                )

    version = values["version"]
    if not version:
        errors.append("Параметр version не может быть пустым.")
    elif any(character.isspace() for character in version):
        errors.append("Параметр version не должен содержать пробелы.")

    output_file = values["output_file"]
    output_path = Path(output_file)
    if not output_file:
        errors.append("Параметр output_file не может быть пустым.")
    elif output_path.name != output_file or output_file in {".", ".."}:
        errors.append("Параметр output_file должен содержать только имя файла.")
    elif output_path.suffix.lower() not in {".png", ".svg"}:
        errors.append("Параметр output_file должен иметь расширение .png или .svg.")

    if errors:
        raise ConfigError("\n".join(errors))

    return AppConfig(
        package_name=package_name,
        repository=repository,
        test_mode=test_mode,
        version=version,
        output_file=output_file,
    )
