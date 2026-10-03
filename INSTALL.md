# Installing wordcount

`wordcount` is a single-file Python CLI. The tool itself imports only the
Python standard library, so **it runs with zero installation**; the setup script
below exists to add the `wordcount` console entry point and the test runner.

## 1. Prerequisites (already on most machines — nothing is installed for you)

| Requirement | Version | Why | Check |
|---|---|---|---|
| Python | 3.8 or newer | runs the tool | `python3 --version` |
| bash | any | runs `install.sh` / `demo.sh` | `bash --version` |
| pip | bundled with Python | installs the entry point and the test runner | `python3 -m pip --version` |

No compiler, no `libsqlite3-dev`, no database and no network service is
required. Do not install system packages: `install.sh` never needs root.

## 2. Package manager

The one package manager for this project is **pip**, driven by the manifest at
the project root:

```
requirements.txt     # the declared dependencies (pytest, the test runner)
pyproject.toml       # the console entry point and the pytest configuration
```

## 3. Install (one command, then it exits)

```bash
bash install.sh
```

It performs, in order:

1. `python3 -m pip install --upgrade pip setuptools wheel`
2. `python3 -m pip install -r requirements.txt`
3. `python3 -m pip install -e .` — adds the `wordcount` command to `PATH`
4. `python3 -c "import wordcount"` and `python3 -m wordcount --version` — a
   cheap self-check so a broken environment fails here, not at first use

No long-running process is started, no prompt is shown, and the script exits
`0` on success / non-zero on failure. It is idempotent: re-run it at any time.

There is no migration and no seed step: this tool keeps no state, so there is
nothing to migrate and nothing to seed. The sample input it demonstrates
against is committed in `examples/`.

## 4. Verify the install

```bash
python3 wordcount.py examples/sample.txt   # examples/sample.txt: 137 words
wordcount examples/sample.txt              # same, via the console entry point
bash demo.sh                               # full transcript of every code path
```

## 5. Run the tests

```bash
python3 -m pytest      # or: python3 -m unittest
```

Expected result: `27 passed, 1 skipped` under pytest (`OK (skipped=1)` under
`unittest`). The skipped case is the `chmod 000` permission test, which is
skipped only when the suite runs as root, because root can read any file
regardless of its permission bits.

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `wordcount: command not found` | the editable install did not run, or `~/.local/bin` is not on `PATH` | re-run `bash install.sh`, or just use `python3 wordcount.py FILE` |
| `ModuleNotFoundError: No module named 'wordcount'` when a test imports it | running the suite from outside the project root | `cd` to the project root and re-run `python3 -m pytest` |
| `pip: command not found` | pip is not installed for this interpreter | `python3 -m ensurepip --upgrade`, then re-run `bash install.sh` |
| Count is lower than your editor's | your editor counts hyphenated or apostrophised words differently | the documented rule is runs of whitespace: `well-known, that's it` is 3 words |

## Uninstall

```bash
python3 -m pip uninstall wordcount
```

Removing the package deletes only the entry point; `wordcount.py` keeps working
on its own.
