"""Tests for the wordcount CLI (F1 count, F2 usage text and honest errors).

Every case shells out to the real ``wordcount.py`` next to the project root, or
calls the real function from the module -- there is no mocking, no network and
no external service.  Fixtures are written into a temporary directory per test.
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLI = PROJECT_ROOT / "wordcount.py"
PROG = "wordcount"

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
EXIT_PERMISSION = 3
EXIT_IS_DIRECTORY = 4
EXIT_NOT_UTF8 = 5


def run_cli(*args, cwd=None):
    """Invoke the CLI as a real subprocess and capture its streams."""
    environment = dict(os.environ)
    environment["NO_COLOR"] = "1"  # deterministic, uncoloured output
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else str(PROJECT_ROOT),
        env=environment,
        timeout=60,
        check=False,
    )


class WorkDirCase(unittest.TestCase):
    """Base case that gives every test its own scratch directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="wordcount-test-")
        self.addCleanup(self._tmp.cleanup)
        self.workdir = pathlib.Path(self._tmp.name)

    def write(self, name, text):
        path = self.workdir / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_bytes(self, name, payload):
        path = self.workdir / name
        path.write_bytes(payload)
        return path


class CountTests(WorkDirCase):
    """F1 -- count the words in one file."""

    def test_counts_whitespace_separated_tokens(self):
        path = self.write("sample.txt", "hello world foo")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(result.stdout.strip(), f"{path}: 3 words")

    def test_counts_are_correct_for_accented_text(self):
        import wordcount

        path = self.write("accents.txt", "café au lait")
        self.assertEqual(wordcount.count_words_in_file(str(path)), 3)
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertIn("3 words", result.stdout)

    def test_empty_file_reports_zero_words_and_succeeds(self):
        path = self.write("empty.txt", "")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(result.stdout.strip(), f"{path}: 0 words")

    def test_whitespace_only_file_reports_zero_words(self):
        path = self.write("blank.txt", "   \n\t\n   \t \n")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(result.stdout.strip(), f"{path}: 0 words")

    def test_punctuation_attached_to_a_word_does_not_split_it(self):
        path = self.write("punctuated.txt", "Well-known, that's it.")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(result.stdout.strip(), f"{path}: 3 words")

    def test_single_word_is_reported_in_the_singular(self):
        path = self.write("one.txt", "solo")
        result = run_cli(str(path))
        self.assertEqual(result.stdout.strip(), f"{path}: 1 word")

    def test_success_output_is_exactly_one_line_on_stdout(self):
        path = self.write("sample.txt", "hello world foo")
        result = run_cli(str(path))
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertEqual(result.stderr, "")

    def test_path_is_printed_exactly_as_given(self):
        self.write("relative.txt", "two words")
        result = run_cli("relative.txt", cwd=self.workdir)
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertEqual(result.stdout.strip(), "relative.txt: 2 words")

    def test_a_megabyte_is_counted_well_under_a_second(self):
        import wordcount

        path = self.write_bytes("big.txt", b"alpha beta gamma delta\n" * 44000)
        started = time.perf_counter()
        count = wordcount.count_words_in_file(str(path))
        elapsed = time.perf_counter() - started
        self.assertEqual(count, 176000)
        self.assertLess(elapsed, 1.0, f"counting 1 MB took {elapsed:.3f}s")

    def test_module_entry_point_runs_the_same_cli(self):
        path = self.write("sample.txt", "hello world foo")
        environment = dict(os.environ, NO_COLOR="1")
        result = subprocess.run(
            [sys.executable, "-m", "wordcount", str(path)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=environment,
            timeout=60,
            check=False,
        )
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertIn("3 words", result.stdout)


class HelpTests(WorkDirCase):
    """F2 -- usage text, -h/--help and the missing-argument contract."""

    def test_long_help_names_the_file_argument_and_exits_zero(self):
        result = run_cli("--help")
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertIn("usage:", result.stdout)
        self.assertIn("FILE", result.stdout)
        self.assertIn("--json", result.stdout)

    def test_short_help_prints_the_same_usage_summary(self):
        short = run_cli("-h")
        long = run_cli("--help")
        self.assertEqual(short.returncode, EXIT_OK, short.stderr)
        self.assertIn("usage:", short.stdout)
        self.assertIn("FILE", short.stdout)
        self.assertEqual(short.stdout.splitlines()[0], long.stdout.splitlines()[0])

    def test_no_arguments_reports_the_required_file_and_exits_nonzero(self):
        result = run_cli()
        self.assertEqual(result.returncode, EXIT_USAGE)
        self.assertIn("usage:", result.stderr)
        self.assertIn("FILE", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_version_flag_exits_zero(self):
        import wordcount

        result = run_cli("--version")
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        self.assertIn(wordcount.__version__, result.stdout)


class ErrorTests(WorkDirCase):
    """F2 -- one readable line, non-zero exit, never a traceback."""

    def test_missing_file_is_one_line_and_nonzero(self):
        result = run_cli("bad.txt")
        self.assertEqual(result.returncode, EXIT_NOT_FOUND)
        self.assertEqual(result.stdout, "")
        lines = [line for line in result.stderr.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, result.stderr)
        self.assertIn("bad.txt", lines[0])
        self.assertIn("no such file or directory", lines[0])

    def test_missing_file_never_leaks_a_traceback(self):
        result = run_cli("definitely-not-here.txt")
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("File \"", result.stderr)

    def test_directory_instead_of_file_is_reported(self):
        result = run_cli(str(self.workdir))
        self.assertEqual(result.returncode, EXIT_IS_DIRECTORY)
        self.assertIn("is a directory", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_permission_denied_is_reported_without_a_traceback(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("running as root: chmod 000 does not deny access")
        path = self.write("noperm.txt", "secret words here")
        os.chmod(path, 0o000)
        self.addCleanup(os.chmod, path, 0o644)
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_PERMISSION)
        self.assertIn("permission denied", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_permission_error_maps_to_a_distinct_status(self):
        import wordcount

        failure = wordcount.describe_failure(PermissionError(13, "Permission denied"), "noperm.txt")
        self.assertEqual(failure.exit_code, EXIT_PERMISSION)
        self.assertIn("permission denied", failure.message)

    def test_non_utf8_bytes_are_reported_as_unreadable(self):
        path = self.write_bytes("notes.bin", b"\xff\xfe\x00\x01payload\xc3\x28")
        result = run_cli(str(path))
        self.assertEqual(result.returncode, EXIT_NOT_UTF8)
        self.assertIn("not valid UTF-8", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_every_failure_path_returns_a_distinct_nonzero_status(self):
        statuses = {
            run_cli("missing-on-purpose.txt").returncode,
            run_cli(str(self.workdir)).returncode,
            run_cli(str(self.write_bytes("bad.bin", b"\xff\xfe"))).returncode,
            run_cli().returncode,
        }
        self.assertNotIn(EXIT_OK, statuses)
        self.assertEqual(len(statuses), 4, statuses)

    def test_a_typed_file_with_a_leading_dash_still_needs_the_separator(self):
        # A path that looks like a flag is an ordinary usage error, not a crash.
        result = run_cli("-zzz")
        self.assertEqual(result.returncode, EXIT_USAGE)
        self.assertNotIn("Traceback", result.stderr)


class DesignTokenTests(unittest.TestCase):
    """The committed design direction lives in one place and is actually used."""

    def test_the_single_accent_token_is_committed_as_truecolor(self):
        import wordcount

        self.assertEqual(wordcount.ACCENT_HEX, "#b4603c")
        self.assertEqual(wordcount.ANSI_STYLES["accent"], "\x1b[38;2;180;96;60m")
        self.assertTrue(wordcount.RULE)

    def test_colour_is_off_for_non_interactive_streams(self):
        import io

        import wordcount

        stream = io.StringIO()
        self.assertFalse(wordcount.wants_color(stream, []))
        self.assertEqual(wordcount.styled("3", "accent", enabled=False), "3")


class JsonTests(WorkDirCase):
    """The scripting surface documented in --help."""

    def test_json_output_is_one_parseable_object(self):
        path = self.write("sample.txt", "hello world foo")
        result = run_cli("--json", str(path))
        self.assertEqual(result.returncode, EXIT_OK, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, {"file": str(path), "words": 3})

    def test_json_output_for_an_empty_file_reports_zero(self):
        path = self.write("empty.txt", "")
        payload = json.loads(run_cli("--json", str(path)).stdout)
        self.assertEqual(payload["words"], 0)


class ExampleFixtureTests(unittest.TestCase):
    """The bundled examples must stay usable: demo.sh depends on them."""

    def test_bundled_examples_have_the_expected_counts(self):
        import wordcount

        examples = PROJECT_ROOT / "examples"
        self.assertEqual(wordcount.count_words_in_file(str(examples / "sample.txt")), 137)
        self.assertEqual(wordcount.count_words_in_file(str(examples / "accents.txt")), 9)
        self.assertEqual(wordcount.count_words_in_file(str(examples / "empty.txt")), 0)
        self.assertEqual(wordcount.count_words_in_file(str(examples / "whitespace.txt")), 0)

    def test_bundled_binary_fixture_is_not_valid_utf8(self):
        payload = (PROJECT_ROOT / "examples" / "binary.bin").read_bytes()
        with self.assertRaises(UnicodeDecodeError):
            payload.decode("utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
