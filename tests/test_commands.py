import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.commands import main


class CommandTests(unittest.TestCase):
    def test_prints_all_configured_parameters_as_key_value_pairs(self) -> None:
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
                result = main(["--config", str(config_path)])

        self.assertEqual(result, 0)
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "package_name=demo",
                "repository=https://example.org/packages",
                "test_mode=false",
                "version=1.2.3",
                "output_file=graph.png",
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


if __name__ == "__main__":
    unittest.main()
