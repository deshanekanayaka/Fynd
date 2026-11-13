"""Setup that every test file shares, so no file repeats it.

pytest reads this file before it reads the tests, and an autouse fixture runs
for every test in this folder without being asked for. The cache directory is
the one that matters most: a test that wrote into the real cache would change
what a later run of Fynd reads back.

A test that wants the opposite can still have it. `monkeypatch.delenv` inside a
test undoes a value set here, which is how the two tests that check a missing
contact address work.
"""

import pytest


@pytest.fixture(autouse=True)
def a_cache_and_an_address(tmp_path, monkeypatch):
    """Gives every test its own cache directory and an operator address."""
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    # Pacing is measured by counting the waits, so no test waits on a real clock.
    monkeypatch.setattr("fynd.fetcher.time.sleep", lambda seconds: None)
    monkeypatch.setattr("fynd.voyage.time.sleep", lambda seconds: None)
    return tmp_path
