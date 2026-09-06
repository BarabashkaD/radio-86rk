"""Launcher for the KiCad verification harness.

Run as:  python3 tools/kicad-verify.py <command>
On Windows:  py tools\\kicad-verify.py <command>

There is no install step. This file exists so the invocation is the same
instruction on every platform: no shebang, no PATH entry, no PYTHONPATH.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kicadverify.__main__ import main  # noqa: E402  (path must be set first)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
