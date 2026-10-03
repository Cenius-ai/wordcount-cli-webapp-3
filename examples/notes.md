Release notes — 1.4.0
====================

Added
-----
- `wordcount --json FILE` prints a single JSON object for scripting.
- Distinct exit codes for each failure class, listed in `--help`.

Fixed
-----
- A file that is a directory now reports "is a directory, not a text file"
  instead of leaking an IsADirectoryError traceback.

Known limits
------------
- UTF-8 only; other encodings are reported as unreadable rather than guessed.
- One file per run; globs and stdin are deliberately out of scope.

Notes for the release manager: bump the version in wordcount.py, run the suite
with `python3 -m pytest`, then re-run `bash demo.sh` and paste the transcript
into the release ticket.
