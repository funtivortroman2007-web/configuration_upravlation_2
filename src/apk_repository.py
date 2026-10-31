"""Read package metadata and direct dependencies from Alpine APKINDEX files."""

from io import BytesIO
from pathlib import Path
import tarfile
from urllib.error import URLError
from urllib.request import urlopen

from src.dependency_graph import DependencyGraph, parse_dependency_names


class RepositoryError(ValueError):
    """Raised when an APK repository cannot provide the requested package."""


def _read_index(data: bytes) -> str:
    try:
        with tarfile.open(fileobj=BytesIO(data), mode="r:*") as archive:
            index_member = next(
                (
                    member
                    for member in archive.getmembers()
                    if Path(member.name).name == "APKINDEX" and member.isfile()
                ),
                None,
            )
            if index_member is None:
                raise RepositoryError("В архиве репозитория отсутствует файл APKINDEX.")
            index_file = archive.extractfile(index_member)
            if index_file is None:
                raise RepositoryError("Не удалось прочитать файл APKINDEX из архива.")
            return index_file.read().decode("utf-8")
    except tarfile.TarError as error:
        raise RepositoryError(f"Некорректный архив APKINDEX: {error}") from error
    except (OSError, EOFError, UnicodeDecodeError) as error:
        raise RepositoryError(f"Не удалось прочитать APKINDEX: {error}") from error


def _load_index(repository: str, test_mode: bool) -> str:
    if test_mode:
        path = Path(repository).expanduser()
        try:
            return _read_index(path.read_bytes())
        except OSError as error:
            raise RepositoryError(
                f"Не удалось прочитать тестовый репозиторий {repository}: {error}"
            ) from error

    index_url = (
        repository.rstrip("/")
        if repository.rstrip("/").endswith("/APKINDEX.tar.gz")
        else f"{repository.rstrip('/')}/APKINDEX.tar.gz"
    )
    try:
        with urlopen(index_url, timeout=30) as response:
            return _read_index(response.read())
    except URLError as error:
        raise RepositoryError(
            f"Не удалось загрузить APKINDEX по адресу {index_url}: {error}"
        ) from error
    except (OSError, EOFError) as error:
        raise RepositoryError(f"Не удалось прочитать ответ {index_url}: {error}") from error

def get_direct_dependencies(
    repository: str,
    package_name: str,
    version: str,
    test_mode: bool = False,
) -> list[str]:
    """Return the direct dependency entries for an exact package name and version."""
    index_text = _load_index(repository, test_mode)
    for entry in index_text.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in entry.splitlines():
            if len(line) >= 2 and line[1] == ":":
                fields[line[0]] = line[2:].strip()
        if fields.get("P") == package_name and fields.get("V") == version:
            dependencies = fields.get("D", "")
            return dependencies.split() if dependencies else []

    raise RepositoryError(
        f"Пакет {package_name} версии {version} не найден в репозитории."
    )


def get_package_graph(
    repository: str,
    package_name: str,
    version: str,
) -> DependencyGraph:
    """Read package dependencies from APKINDEX for recursive graph traversal."""
    index_text = _load_index(repository, test_mode=False)
    package_records: dict[str, tuple[str, str]] = {}
    provided_by: dict[str, set[str]] = {}
    root_record: tuple[str, str] | None = None

    for entry in index_text.strip().split("\n\n"):
        fields: dict[str, str] = {}
        for line in entry.splitlines():
            if len(line) >= 2 and line[1] == ":":
                fields[line[0]] = line[2:].strip()

        name = fields.get("P")
        if not name:
            continue
        record = (
            fields.get("D", ""),
            fields.get("p", ""),
        )
        package_records[name] = record
        if fields.get("V") == version and name == package_name:
            root_record = record
        for provided_name in parse_dependency_names(fields.get("p", "")):
            provided_by.setdefault(provided_name, set()).add(name)

    if root_record is None:
        raise RepositoryError(
            f"Пакет {package_name} версии {version} не найден в репозитории."
        )
    package_records[package_name] = root_record

    package_graph: DependencyGraph = {}
    for name, (raw_dependencies, _) in package_records.items():
        dependencies = parse_dependency_names(raw_dependencies)
        package_graph[name] = [
            dependency
            if dependency in package_records
            or len(provided_by.get(dependency, ())) != 1
            else next(iter(provided_by[dependency]))
            for dependency in dependencies
        ]
    return package_graph
