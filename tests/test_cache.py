"""The cache has to return what it stored, and the key has to be stable."""

from fynd import cache


def test_write_then_read_returns_the_same_value(tmp_path, monkeypatch):
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    key = cache.cache_key("s2-search", {"query": "energy", "limit": 5})

    assert cache.read(key) is None
    cache.write(key, {"total": 1})
    assert cache.read(key) == {"total": 1}


def test_the_same_parameters_give_the_same_key():
    # The order of the keys in the dictionary must not change the file name,
    # or the second run of the same search misses the cache.
    first = cache.cache_key("s2-search", {"query": "energy", "limit": 5})
    second = cache.cache_key("s2-search", {"limit": 5, "query": "energy"})
    assert first == second


def test_different_parameters_give_different_keys():
    first = cache.cache_key("s2-search", {"query": "energy", "limit": 5})
    second = cache.cache_key("s2-search", {"query": "energy", "limit": 6})
    assert first != second
