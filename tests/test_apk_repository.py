import contextlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.apk_repository import (
    RepositoryError,
    get_direct_dependencies,
    get_package_graph,
)


INDEX_TEXT = """\
C:123
P:demo
V:1.2.3-r0
D:libc.so.6 so:libssl.so.3

C:456
P:other
V:2.0-r0
D:demo
"""


def make_index_archive(index_text: str = INDEX_TEXT) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        index_bytes = index_text.encode("utf-8")
        member = tarfile.TarInfo("APKINDEX")
        member.size = len(index_bytes)
        archive.addfile(member, io.BytesIO(index_bytes))
    return output.getvalue()


class ApkRepositoryTests(unittest.TestCase):
    def test_reads_direct_dependencies_from_local_apkindex_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "APKINDEX.tar.gz"
            path.write_bytes(make_index_archive())

            dependencies = get_direct_dependencies(
                str(path), "demo", "1.2.3-r0", test_mode=True
            )

        self.assertEqual(dependencies, ["libc.so.6", "so:libssl.so.3"])

    def test_matches_the_requested_version_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "APKINDEX.tar.gz"
            path.write_bytes(make_index_archive())

            with self.assertRaisesRegex(RepositoryError, "1.2.3"):
                get_direct_dependencies(
                    str(path), "demo", "1.2.3", test_mode=True
                )

    def test_reports_package_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "APKINDEX.tar.gz"
            path.write_bytes(make_index_archive())

            with self.assertRaisesRegex(RepositoryError, "missing"):
                get_direct_dependencies(
                    str(path), "missing", "1.2.3-r0", test_mode=True
                )

    def test_reports_invalid_archive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "APKINDEX.tar.gz"
            path.write_bytes(b"not an APK index")

            with self.assertRaisesRegex(RepositoryError, "архив"):
                get_direct_dependencies(
                    str(path), "demo", "1.2.3-r0", test_mode=True
                )

    def test_fetches_index_from_repository_url(self) -> None:
        archive = make_index_archive()

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()

        with patch(
            "src.apk_repository.urlopen", return_value=Response(archive)
        ) as open_url:
            dependencies = get_direct_dependencies(
                "https://repo.example/alpine/main",
                "demo",
                "1.2.3-r0",
            )

        open_url.assert_called_once_with(
            "https://repo.example/alpine/main/APKINDEX.tar.gz", timeout=30
        )
        self.assertEqual(dependencies, ["libc.so.6", "so:libssl.so.3"])

    def test_accepts_repository_url_pointing_to_index_archive(self) -> None:
        with patch(
            "src.apk_repository.urlopen",
            return_value=io.BytesIO(make_index_archive()),
        ) as open_url:
            get_direct_dependencies(
                "https://repo.example/main/APKINDEX.tar.gz",
                "demo",
                "1.2.3-r0",
            )

        self.assertEqual(
            open_url.call_args.args[0],
            "https://repo.example/main/APKINDEX.tar.gz",
        )

    def test_returns_empty_list_for_package_without_dependencies(self) -> None:
        index = "P:standalone\nV:1-r0\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "APKINDEX.tar.gz"
            path.write_bytes(make_index_archive(index))

            dependencies = get_direct_dependencies(
                str(path), "standalone", "1-r0", test_mode=True
            )

        self.assertEqual(dependencies, [])

    def test_package_graph_resolves_unique_provided_dependencies(self) -> None:
        index = """\
P:demo
V:1-r0
D:so:libc.musl-x86_64.so.1

P:musl
V:1-r0
p:so:libc.musl-x86_64.so.1=1
D:kernel

P:kernel
V:1-r0
"""
        with patch("src.apk_repository._load_index", return_value=index):
            graph = get_package_graph("https://example.org/repository", "demo", "1-r0")

        self.assertEqual(graph["demo"], ["musl"])
        self.assertEqual(graph["musl"], ["kernel"])
        self.assertEqual(graph["kernel"], [])


if __name__ == "__main__":
    unittest.main()
