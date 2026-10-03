#!/usr/bin/env python3
"""wordcount -- count the words in one UTF-8 text file.

A single-file, standard-library-only command line tool: you hand it the path of
a text file, it prints ``<file>: <n> words`` on stdout and exits 0. Every
failure -- a missing path, a permission-denied file, a directory, bytes that are
not UTF-8 -- is reported as one readable line on stderr with a non-zero exit
status, never as a Python traceback, so the tool is safe inside a pipeline.

Committed design direction for this build (calm-precise / terminal dark / mono):

    accent     oklch(0.58 0.12 43)  ==  #b4603c   -- the ONE accent
    neutrals   the terminal's own foreground, bold and dim; no second palette
    type       system monospace (the terminal font -- nothing is downloaded)
    layout     aligned columns, box-drawing separators, help-first output
    signal     colour is never the only signal: every coloured token is also
               spelled out in words and carried by an exit code

Run ``wordcount --help`` for usage, examples and the exit-code table.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import NoReturn, Sequence, TextIO

__version__ = "1.0.0"
PROG = "wordcount"

# ---------------------------------------------------------------------------
# Design tokens.  The CSS-facing equivalent of these values is documented above;
# the terminal cannot parse oklch(), so the accent is committed here once, as
# truecolor ANSI built from its hex form, and used for exactly one meaning:
# the value the user came for.
# ---------------------------------------------------------------------------
ACCENT_HEX = "#b4603c"


def _truecolor(hex_color: str) -> str:
    """ANSI foreground for a #rrggbb token (the terminal cannot parse oklch())."""
    red, green, blue = (int(hex_color[index:index + 2], 16) for index in (1, 3, 5))
    return f"\x1b[38;2;{red};{green};{blue}m"


ANSI_STYLES = {
    "accent": _truecolor(ACCENT_HEX),
    "bold": "\x1b[1m",
    "dim": "\x1b[2m",
}
ANSI_RESET = "\x1b[0m"
RULE = "\u2500"  # box-drawing separator

# Exit statuses: 0 on success, distinct non-zero codes per failure class.
EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_USAGE = 2
EXIT_PERMISSION = 3
EXIT_IS_DIRECTORY = 4
EXIT_NOT_UTF8 = 5
EXIT_UNREADABLE = 6


def styled(text: str, *styles: str, enabled: bool) -> str:
    """Wrap *text* in ANSI *styles*, or return it untouched when colour is off."""
    if not enabled or not styles:
        return text
    prefix = "".join(ANSI_STYLES[style] for style in styles)
    return f"{prefix}{text}{ANSI_RESET}"


def wants_color(stream: TextIO, arguments: Sequence[str]) -> bool:
    """Colour only for an interactive terminal that has not opted out."""
    if "--no-color" in arguments or os.environ.get("NO_COLOR", "") != "":
        return False
    try:
        return bool(stream.isatty())
    except (AttributeError, ValueError):
        return False


@dataclass(frozen=True)
class Failure:
    """A human-readable failure message and the exit status it maps to."""

    message: str
    exit_code: int


def count_words_in_file(path: str) -> int:
    """Return the number of whitespace-separated non-empty tokens in *path*.

    The file is read as UTF-8 text; ``str.split()`` with no argument splits on
    any run of whitespace and drops empty tokens, so an empty or whitespace-only
    file counts 0 and ``caf\u00e9 au lait`` counts 3.
    """
    with open(path, "r", encoding="utf-8") as handle:
        return len(handle.read().split())


def describe_failure(error: BaseException, path: str) -> Failure:
    """Map a read error onto one readable line and its exit status."""
    if isinstance(error, FileNotFoundError):
        return Failure(f"{path}: no such file or directory (check the path)", EXIT_NOT_FOUND)
    if isinstance(error, PermissionError):
        return Failure(f"{path}: permission denied (check the file's permissions)", EXIT_PERMISSION)
    if isinstance(error, IsADirectoryError):
        return Failure(f"{path}: is a directory, not a text file (pass a file path)", EXIT_IS_DIRECTORY)
    if isinstance(error, UnicodeDecodeError):
        return Failure(f"{path}: not valid UTF-8 text (save it as UTF-8 and retry)", EXIT_NOT_UTF8)
    detail = getattr(error, "strerror", None) or str(error)
    return Failure(f"{path}: {detail.lower()}", EXIT_UNREADABLE)


class _UsageParser(argparse.ArgumentParser):
    """ArgumentParser whose usage errors stay readable and non-zero."""

    def __init__(self, *args: object, use_color: bool = False, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.use_color = use_color

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        label = styled(f"{PROG}: error:", "accent", "bold", enabled=self.use_color)
        print(f"{label} {message}", file=sys.stderr)
        print(f"hint: run '{PROG} --help' for usage and examples.", file=sys.stderr)
        raise SystemExit(EXIT_USAGE)


def _help_description(use_color: bool) -> str:
    """The help banner: aligned label column, one accent, no second palette."""

    def label(text: str) -> str:
        return styled(text, "accent", enabled=use_color)

    return "\n".join(
        [
            "Count the words in one UTF-8 text file, from the terminal.",
            "",
            f"  {label('reads ')}  the file named by FILE, decoded as UTF-8 text",
            f"  {label('counts')}  runs of whitespace between non-empty tokens",
            f"  {label('prints')}  \"<file>: <n> words\" on stdout, and 0 words for an",
            "          empty or whitespace-only file",
        ]
    )


def _help_epilog(use_color: bool) -> str:
    """Examples and the exit-code table, columns aligned."""

    def heading(text: str) -> str:
        return styled(text, "accent", "bold", enabled=use_color)

    rule = styled(RULE * 62, "dim", enabled=use_color)
    return "\n".join(
        [
            rule,
            heading("examples"),
            "  wordcount essay.txt              count the words in essay.txt",
            "  wordcount --json essay.txt       print {\"file\": \"essay.txt\", \"words\": 412}",
            "  wordcount -h                     show this help",
            "",
            heading("exit codes"),
            "  0  the file was read and its word count printed",
            "  1  no such file or directory",
            "  2  the FILE argument is missing, or the flags are wrong",
            "  3  permission denied reading the file",
            "  4  the path is a directory, not a file",
            "  5  the file is not valid UTF-8 text",
            "  6  the file could not be read for another reason",
            "",
            heading("environment"),
            "  NO_COLOR=1  disable ANSI colour (the same as --no-color)",
        ]
    )


def build_parser(use_color: bool) -> argparse.ArgumentParser:
    """Build the parser: one required positional FILE argument, -h and --help."""
    parser = _UsageParser(
        prog=PROG,
        description=_help_description(use_color),
        epilog=_help_epilog(use_color),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        use_color=use_color,
    )
    parser.add_argument(
        "file",
        metavar="FILE",
        help="path to the UTF-8 text file whose words should be counted (required)",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="print the result as JSON on one line instead of the human line",
    )
    parser.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        help="disable ANSI colour (also honoured: NO_COLOR=1)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
        help="show the version and exit",
    )
    return parser


def format_count(path: str, words: int, use_color: bool) -> str:
    """The one-line success result: '<file>: <n> words'."""
    number = styled(str(words), "accent", "bold", enabled=use_color)
    unit = "word" if words == 1 else "words"
    return f"{path}: {number} {unit}"


def format_error(message: str, use_color: bool) -> str:
    """The one-line failure result, written to stderr."""
    label = styled(f"{PROG}: error:", "accent", "bold", enabled=use_color)
    return f"{label} {message}"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit status."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    out_color = wants_color(sys.stdout, arguments)
    err_color = wants_color(sys.stderr, arguments)

    parser = build_parser(out_color)
    args = parser.parse_args(arguments)

    try:
        words = count_words_in_file(args.file)
    except (OSError, UnicodeDecodeError) as error:
        failure = describe_failure(error, args.file)
        print(format_error(failure.message, err_color), file=sys.stderr)
        return failure.exit_code

    if args.json_output:
        print(json.dumps({"file": args.file, "words": words}))
    else:
        print(format_count(args.file, words, out_color))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
