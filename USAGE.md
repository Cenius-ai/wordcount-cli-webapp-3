# Using wordcount

Every example below is copy-pasteable and uses the bundled files in `examples/`
so you can compare your output with this page.

## Count the words in a file

```console
$ python3 wordcount.py examples/sample.txt
examples/sample.txt: 137 words
```

The count is the number of non-empty tokens produced by splitting the file's
text on any run of whitespace (spaces, tabs, newlines). Punctuation stays
attached, so `well-known, that's it.` is three words, and an accented word like
`café` stays one word — the file is decoded as UTF-8 before it is split.

## Empty and whitespace-only files

```console
$ python3 wordcount.py examples/empty.txt
examples/empty.txt: 0 words
$ python3 wordcount.py examples/whitespace.txt
examples/whitespace.txt: 0 words
```

`0 words` is printed rather than a blank line, and the exit status is still `0`:
an empty file is a successful count, not an error.

## Scripting: one JSON object per run

```console
$ python3 wordcount.py --json examples/notes.md
{"file": "examples/notes.md", "words": 110}
```

```bash
# The counting pipeline this tool is built for:
total=0
for f in chapters/*.txt; do
  n=$(python3 wordcount.py --json "$f" | python3 -c 'import json,sys; print(json.load(sys.stdin)["words"])')
  total=$((total + n))
done
echo "manuscript: $total words"
```

Results always go to **stdout** and diagnostics always go to **stderr**, so
`wordcount … > count.txt` never captures an error message.

## Help and version

```console
$ wordcount --help          # same as: wordcount -h
usage: wordcount [-h] [--json] [--no-color] [--version] FILE
...
```

`--help` (and `-h`) prints the usage line naming the required `FILE` argument,
worked examples and the exit-code table, then exits `0`.

```console
$ wordcount --version
wordcount 1.0.0
```

## Running with no argument

```console
$ python3 wordcount.py
usage: wordcount [-h] [--json] [--no-color] [--version] FILE
wordcount: error: the following arguments are required: FILE
hint: run 'wordcount --help' for usage and examples.
$ echo $?
2
```

## Errors: one line, non-zero exit, no traceback

```console
$ python3 wordcount.py examples/no-such-file.txt
wordcount: error: examples/no-such-file.txt: no such file or directory (check the path)
$ echo $?
1

$ python3 wordcount.py examples
wordcount: error: examples: is a directory, not a text file (pass a file path)
$ echo $?
4

$ printf '\xff\xfe\x00' > /tmp/notes.bin
$ python3 wordcount.py /tmp/notes.bin
wordcount: error: /tmp/notes.bin: not valid UTF-8 text (save it as UTF-8 and retry)
$ echo $?
5

$ printf 'private draft' > /tmp/noperm.txt && chmod 000 /tmp/noperm.txt
$ python3 wordcount.py /tmp/noperm.txt
wordcount: error: /tmp/noperm.txt: permission denied (check the file's permissions)
$ echo $?
3
```

Every failure message names the file, says what went wrong and (where a fix
exists) how to fix it. The full table lives in `README.md` and in `--help`.

## Colour

Output is coloured only when stdout (or stderr) is an interactive terminal, and
only to mark the count itself. Turn it off for good with either of:

```bash
python3 wordcount.py --no-color examples/sample.txt
NO_COLOR=1 python3 wordcount.py examples/sample.txt
```

Piped and redirected output is never coloured, so files and `jq` stay clean.

## The guided tour

```bash
bash demo.sh
```

`demo.sh` runs the real tool against `examples/` and prints the exact output and
exit status of every path above, including the four error classes, followed by
an aligned one-view table of every bundled file (the shell does the looping;
the tool still counts exactly one file per run). It needs no
arguments, prompts for nothing and writes only to a temporary directory that it
removes on exit. When it runs as root it skips the `chmod 000` case (root can
read any file regardless of its permission bits) and says so.
