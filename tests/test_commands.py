import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.apk_repository import RepositoryError
from src.commands import main
from src.dependency_graph import GraphError


class CommandTests(unittest.TestCase):
    def test_prints_transitive_graph_for_real_repository(self) -> None:
        content = """\
[settings]
package_name = demo
repository = https://example.org/packages
test_mode = false
version = 1.2.3
output_file = graph.png
"""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.ini"
            config_path.write_text(content, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                with patch(
                    "src.commands.get_package_graph",
                    return_value={
                        "demo": ["libc.so.6", "libssl"],
                        "libc.so.6": [],
                        "libssl": ["libc.so.6"],
                    },
                ) as get_package_graph:
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 0)
        get_package_graph.assert_called_once_with(
            "https://example.org/packages", "demo", "1.2.3"
        )
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "Граф зависимостей demo:",
                "demo -> libc.so.6, libssl",
                "libc.so.6 -> (нет)",
                "libssl -> libc.so.6",
            ],
        )

    def test_reports_configuration_errors_on_stderr(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            result = main(["--config", "nonexistent-config.ini"])

        self.assertEqual(result, 2)
        self.assertIn(
            "Ошибка конфигурации",
            output.getvalue(),
        )

    def test_reports_repository_errors_on_stderr(self) -> None:
        content = """\
[settings]
package_name = demo
repository = https://example.org/packages
test_mode = false
version = 1.2.3
output_file = graph.png
"""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.ini"
            config_path.write_text(content, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                with patch(
                    "src.commands.get_package_graph",
                    side_effect=RepositoryError("Пакет не найден."),
                ):
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 3)
        self.assertIn("Ошибка репозитория APK", output.getvalue())

    def test_uses_graph_file_when_test_mode_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository.txt"
            repository.write_text("A: B\nB: C\nC:\n", encoding="utf-8")
            config_path = Path(directory) / "config.ini"
            config_path.write_text(
                f"""\
[settings]
package_name = A
repository = {repository}
test_mode = true
version = ignored-in-test-mode
output_file = graph.png
""",
                encoding="utf-8",
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--config", str(config_path)])

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "Граф зависимостей A:",
                "A -> B",
                "B -> C",
                "C -> (нет)",
            ],
        )

    def test_reports_graph_errors_on_stderr(self) -> None:
        content = """\
[settings]
package_name = demo
repository = https://example.org/packages
test_mode = false
version = 1.2.3
output_file = graph.png
"""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.ini"
            config_path.write_text(content, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stderr(output):
                with patch(
                    "src.commands.get_package_graph",
                    side_effect=GraphError("Package root absent"),
                ):
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 4)
        self.assertIn("Ошибка тестового графа", output.getvalue())

    def test_reports_packages_without_dependencies(self) -> None:
        content = """\
[settings]
package_name = standalone
repository = https://example.org/packages
test_mode = false
version = 1.0
output_file = graph.png
"""
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.ini"
            config_path.write_text(content, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                with patch(
                    "src.commands.get_package_graph",
                    return_value={"standalone": []},
                ):
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue().splitlines(),
            ["Граф зависимостей standalone:", "standalone -> (нет)"],
        )


if __name__ == "__main__":
    unittest.main()
