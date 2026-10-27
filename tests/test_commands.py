import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.apk_repository import RepositoryError
from src.commands import main


class CommandTests(unittest.TestCase):
    def test_prints_direct_dependencies(self) -> None:
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
                    "src.commands.get_direct_dependencies",
                    return_value=["libc.so.6", "so:libssl.so.3"],
                ) as get_dependencies:
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 0)
        get_dependencies.assert_called_once_with(
            "https://example.org/packages", "demo", "1.2.3", False
        )
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "Прямые зависимости demo версии 1.2.3:",
                "libc.so.6",
                "so:libssl.so.3",
            ],
        )

    def test_reports_configuration_errors_on_stderr(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stderr(output):
            result = main(["--config", "nonexistent-config.ini"])

        self.assertEqual(result, 2)
        self.assertIn("Ошибка конфигурации", output.getvalue())

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
                    "src.commands.get_direct_dependencies",
                    side_effect=RepositoryError("Пакет не найден."),
                ):
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 3)
        self.assertIn("Ошибка репозитория APK", output.getvalue())

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
                    "src.commands.get_direct_dependencies", return_value=[]
                ):
                    result = main(["--config", str(config_path)])

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue().splitlines(),
            ["Прямые зависимости standalone версии 1.0:", "(нет)"],
        )


if __name__ == "__main__":
    unittest.main()
