"""Put the project root on sys.path so the suite runs from a clean checkout.

``python3 -m pytest`` collects this file from ``tests/``; without the editable
install performed by install.sh, ``import wordcount`` would not resolve.  The
CLI is standard library only, so this is the whole of the test bootstrap.
"""

import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
