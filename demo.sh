#!/usr/bin/env bash
# demo.sh -- a non-interactive end-to-end tour of the wordcount CLI.
#
# Runs the real tool against the bundled files in examples/, prints the exact
# output and the exit status of every invocation, and never prompts, never
# touches the network and never writes outside a temporary directory.
#
# Usage: bash demo.sh
set -euo pipefail

cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

run() {
  # Run `wordcount <args>` for real and report the exit status, stderr included.
  local status
  printf '\n$ python3 wordcount.py %s\n' "$*"
  set +e
  "$PY" wordcount.py "$@"
  status=$?
  set -e
  printf '[exit %d]\n' "$status"
}

printf '%s\n' "wordcount demo -- every line below is real output from the real tool."
printf '%s\n' "------------------------------------------------------------------"

run --version
run examples/sample.txt
run examples/accents.txt
run examples/empty.txt
run examples/whitespace.txt
run --json examples/notes.md

# A file that legitimately exists nowhere: the error must be one readable line.
run examples/no-such-file.txt

# Bytes that are not UTF-8 text.
run examples/binary.bin

# A directory passed where a file was expected.
run examples

# A file with the read bit removed (skipped when running as root, which can
# read anything regardless of the permission bits).
printf 'private draft, not for the demo' > "$WORKDIR/locked.txt"
chmod 000 "$WORKDIR/locked.txt"
if [ "$(id -u)" = "0" ]; then
  printf '\n$ chmod 000 locked.txt && python3 wordcount.py locked.txt\n'
  printf '[skipped: running as root, chmod 000 does not deny access]\n'
else
  run "$WORKDIR/locked.txt"
fi

# The same count, twice, so a reader can see the tool is deterministic.
run examples/sample.txt

printf '\n%s\n' "------------------------------------------------------------------"
printf '%s\n' "every bundled example at a glance (the shell loop is the demo's; the tool"
printf '%s\n' "still counts exactly one file per run, and its output is the count column)"
printf '\n  %-24s %8s\n' "file" "words"
printf '  %s\n' "--"
# binary.bin is skipped here on purpose: it is not UTF-8, and the loop drops
# any file the tool rejects, which is exactly what the error cases above show.
for sample in examples/*; do
  line="$("$PY" wordcount.py "$sample" 2>/dev/null)" || continue
  count="${line##*: }"
  count="${count%% *}"
  printf '  %-24s %8s\n' "${sample#examples/}" "$count"
done

printf '\n%s\n' "------------------------------------------------------------------"
printf '%s\n' "help (also reachable as: python3 wordcount.py --help)"

"$PY" wordcount.py -h

printf '\n%s\n' "Demo complete. Try it on your own file: python3 wordcount.py PATH"
