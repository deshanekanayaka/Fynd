"""The edge must not carry a fact that goes stale on its own.

See the `bugs.md` entry "A fixed comparison number stays wrong on every
later run". A constant that names one run's count and one run's prediction
never updates itself, so a later run would keep repeating old history.

This test reads the source of `cli.py` on purpose, because the promise is
about what the command passes to `report`, and running the command needs the
network and a key. It reads the parsed code and not the text, so renaming an
argument or reformatting the file cannot make it pass by accident.
"""

import ast
import pathlib

STALE = {"previous", "predicted"}


def test_the_measure_command_passes_no_comparison_number() -> None:
    source = pathlib.Path("src/fynd/cli.py").read_text(encoding="utf-8")

    passed = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            passed.update(keyword.arg for keyword in node.keywords if keyword.arg)

    assert passed & STALE == set()
