"""The edge must not carry a fact that goes stale on its own.

See the `bugs.md` entry "A fixed comparison number stays wrong on every
later run". A constant that names one run's count and one run's prediction
never updates itself, so a later run would keep repeating old history.
"""

import pathlib


def test_the_measure_command_hardcodes_no_comparison_numbers() -> None:
    source = pathlib.Path("src/fynd/cli.py").read_text(encoding="utf-8")
    assert "previous=" not in source
    assert "predicted=" not in source
