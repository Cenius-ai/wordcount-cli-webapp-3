#!/usr/bin/env bash
# install.sh -- prepare wordcount for this machine, then exit.
#
# It installs the project's own Python packages with pip (the test runner and
# the console entry point), verifies the module imports, and stops there: it
# never starts anything long-running and never prompts for input.
#
# Run it as a normal user; it does not need root and never installs system
# packages.  Prerequisites (a Python 3.8+ interpreter, bash) are listed in
# INSTALL.md and are NOT installed here.
#
# Usage: bash install.sh
set -euo pipefail

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

echo "==> Using interpreter: $("$PY" --version 2>&1)"

# 1. Fresh packaging tooling: old pip silently fails modern editable installs.
echo "==> Upgrading pip, setuptools and wheel"
"$PY" -m pip install --upgrade pip setuptools wheel

# 2. Declared dependencies (the pytest test runner; pin lives in requirements.txt).
echo "==> Installing dependencies from requirements.txt"
"$PY" -m pip install -r requirements.txt

# 3. The console entry point: `wordcount FILE`. Safe to re-run (idempotent).
echo "==> Installing the wordcount console entry point"
"$PY" -m pip install -e .

# 4. Cheap self-check so an incomplete environment fails here, not at first use.
echo "==> Verifying the module imports and the CLI answers"
"$PY" -c "import wordcount; print('    wordcount', wordcount.__version__, 'importable')"
"$PY" -m wordcount --version

cat <<'EOF'

Setup complete. Nothing is running in the background.

  Count a file       python3 wordcount.py examples/sample.txt
  Or, if the entry point is on PATH:
                     wordcount examples/sample.txt
  See the full tour  bash demo.sh
  Run the tests      python3 -m pytest      (or: python3 -m unittest)
  Usage and examples python3 wordcount.py --help
EOF
