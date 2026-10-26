import tempfile
import unittest
from pathlib import Path

from src.config import ConfigError, load_config


VALID_CONFIG = """\
[settings]
package_name = demo
repository = https://example.org/packages
test_mode = false
version = 1.2.3
output_file = graph.svg
"""


class LoadConfigTests(unittest.TestCase):
    def write_config(self, directory: str, content: str) -> Path:
        path = Path(directory) / "config.ini"
        path.write_text(content, encoding="utf-8")
        return path

    def test_loads_valid_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(self.write_config(directory, VALID_CONFIG))

        self.assertEqual(config.package_name, "demo")
        self.assertEqual(config.repository, "https://example.org/packages")
        self.assertFalse(config.test_mode)
        self.assertEqual(config.version, "1.2.3")
        self.assertEqual(config.output_file, "graph.svg")

    def test_test_repository_must_be_an_existing_file(self) -> None:
        content = VALID_CONFIG.replace(
            "repository = https://example.org/packages", "repository = missing.json"
        ).replace("test_mode = false", "test_mode = true")
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, content)

            with self.assertRaisesRegex(ConfigError, "repository"):
                load_config(path)

    def test_accepts_existing_test_repository_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository.json"
            repository.write_text("{}", encoding="utf-8")
            content = VALID_CONFIG.replace(
                "https://example.org/packages", str(repository)
            ).replace("test_mode = false", "test_mode = true")
            config = load_config(self.write_config(directory, content))

        self.assertTrue(config.test_mode)
        self.assertEqual(config.repository, str(repository))

    def test_reports_invalid_values_for_each_parameter(self) -> None:
        invalid_config = """\
[settings]
package_name =
repository =
test_mode = yes
version =
output_file = ../graph.gif
"""
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, invalid_config)

            with self.assertRaises(ConfigError) as context:
                load_config(path)

        message = str(context.exception)
        for parameter in (
            "package_name",
            "repository",
            "test_mode",
            "version",
            "output_file",
        ):
            with self.subTest(parameter=parameter):
                self.assertIn(parameter, message)

    def test_rejects_invalid_repository_url(self) -> None:
        content = VALID_CONFIG.replace(
            "https://example.org/packages", "ftp://example.org/packages"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, content)

            with self.assertRaisesRegex(ConfigError, "repository"):
                load_config(path)

    def test_reports_missing_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_config(directory, "[settings]\n")

            with self.assertRaises(ConfigError) as context:
                load_config(path)

        for parameter in (
            "package_name",
            "repository",
            "test_mode",
            "version",
            "output_file",
        ):
            with self.subTest(parameter=parameter):
                self.assertIn(parameter, str(context.exception))


if __name__ == "__main__":
    unittest.main()
