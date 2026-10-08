"""The cache has to be stable on the same parts, and tell different parts apart."""

import json

from fynd import cache


def test_the_same_parts_give_the_same_key() -> None:
    parts = {"model": "claude-haiku-4-5", "input_sha256": "abc"}
    assert cache.cache_key("claude", parts) == cache.cache_key("claude", parts)


def test_a_changed_part_gives_a_different_key() -> None:
    first = cache.cache_key("claude", {"prompt_sha256": "aaa"})
    second = cache.cache_key("claude", {"prompt_sha256": "bbb"})
    assert first != second


def test_the_key_order_of_the_parts_does_not_matter() -> None:
    # The key is written by hand in two places over the life of the project, so
    # the order of the keys must not change the answer.
    first = cache.cache_key("claude", {"a": 1, "b": 2})
    second = cache.cache_key("claude", {"b": 2, "a": 1})
    assert first == second


def test_reading_a_missing_key_returns_none(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    assert cache.read("claude-0000000000000000.json") is None


def test_a_written_answer_reads_back(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    parts = {"model": "claude-haiku-4-5"}
    key = cache.cache_key("claude", parts)
    cache.write(key, parts, {"topics": []})
    assert cache.read(key) == {"topics": []}


def test_the_file_holds_the_parts_beside_the_answer(tmp_path, monkeypatch) -> None:
    # A human reading the cache directory must be able to tell which prompt and
    # which model produced a reply. ADR 0004 asks for that.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    parts = {"model": "claude-haiku-4-5", "prompt_sha256": "aaa"}
    key = cache.cache_key("claude", parts)
    cache.write(key, parts, "an answer")
    stored = json.loads((tmp_path / key).read_text(encoding="utf-8"))
    assert stored["parts"] == parts
    assert stored["value"] == "an answer"


def test_a_file_in_an_older_shape_reads_as_a_miss(tmp_path, monkeypatch) -> None:
    # One such file is on disk from day 2. A miss costs one fetch, and a raised
    # error costs the whole Stage.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    (tmp_path / "old.json").write_text(json.dumps({"total": 20}), encoding="utf-8")
    assert cache.read("old.json") is None
