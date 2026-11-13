"""The cache has to be stable on the same parts, and tell different parts apart."""

import json

import pytest

from fynd import cache

A_PDF = b"%PDF-1.7 hello"
A_PDF_URL = "https://example.org/paper.pdf"


def stored_pdf(data: bytes = A_PDF) -> tuple[str, dict]:
    """Writes one PDF into the cache, and hands back its key and its parts."""
    parts = {"url": A_PDF_URL}
    key = cache.cache_key("fetch", parts)
    cache.write_bytes(key, parts, data, "application/pdf")
    return key, parts


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


def test_reading_a_missing_key_returns_none() -> None:
    assert cache.read("claude-0000000000000000.json") is None


def test_a_written_answer_reads_back() -> None:
    parts = {"model": "claude-haiku-4-5"}
    key = cache.cache_key("claude", parts)
    cache.write(key, parts, {"topics": []})
    assert cache.read(key) == {"topics": []}


def test_the_file_holds_the_parts_beside_the_answer(tmp_path) -> None:
    # A human reading the cache directory must be able to tell which prompt and
    # which model produced a reply. ADR 0004 asks for that.
    parts = {"model": "claude-haiku-4-5", "prompt_sha256": "aaa"}
    key = cache.cache_key("claude", parts)
    cache.write(key, parts, "an answer")
    stored = json.loads((tmp_path / key).read_text(encoding="utf-8"))
    assert stored["parts"] == parts
    assert stored["value"] == "an answer"


def test_a_file_in_an_older_shape_reads_as_a_miss(tmp_path) -> None:
    # One such file is on disk from day 2. A miss costs one fetch, and a raised
    # error costs the whole Stage.
    (tmp_path / "old.json").write_text(json.dumps({"total": 20}), encoding="utf-8")
    assert cache.read("old.json") is None


def test_written_bytes_read_back() -> None:
    # A fetched PDF reaches 20 megabytes, which is no JSON value. The bytes go
    # in a sidecar file, and the parts stay in the JSON file beside it.
    key, _ = stored_pdf()
    answer = cache.read_bytes(key)
    assert answer is not None
    assert answer.data == A_PDF
    assert answer.content_type == "application/pdf"


def test_the_bytes_file_sits_beside_the_parts(tmp_path) -> None:
    key, parts = stored_pdf()
    stored = json.loads((tmp_path / key).read_text(encoding="utf-8"))
    assert stored["parts"] == parts
    assert stored["value"]["byte_count"] == len(A_PDF)
    assert (tmp_path / stored["value"]["file"]).read_bytes() == A_PDF


def test_reading_missing_bytes_returns_none() -> None:
    assert cache.read_bytes("fetch-0000000000000000.json") is None


def test_bytes_with_no_sidecar_read_as_a_miss(tmp_path) -> None:
    # A run that died between the two writes. A miss costs one fetch.
    key, _ = stored_pdf()
    stored = json.loads((tmp_path / key).read_text(encoding="utf-8"))
    (tmp_path / stored["value"]["file"]).unlink()
    assert cache.read_bytes(key) is None


def test_a_refusal_reads_back_as_a_refusal() -> None:
    # A 403 from a publisher is a fact about a host, and the measurement counts
    # it. It is not a hit with no body, and not a miss either.
    parts = {"url": "https://www.sciencedirect.com/paper.pdf"}
    key = cache.cache_key("fetch", parts)
    cache.write_refusal(key, parts, status=403, content_type="text/html", reason="fetch_refused")
    value = cache.read(key)
    assert cache.is_refusal(value)
    assert value["status"] == 403
    assert value["content_type"] == "text/html"
    assert value["reason"] == "fetch_refused"
    assert cache.read_bytes(key) is None


def test_bytes_are_not_a_refusal() -> None:
    key, _ = stored_pdf()
    assert not cache.is_refusal(cache.read(key))


def test_a_rate_limit_is_never_cached(tmp_path) -> None:
    # ADR 0004: a failed reply is never cached. A 429 and a timeout are a
    # failure, and a 403 is an answer. The rule lives here, where every caller
    # of the cache passes through.
    parts = {"url": "https://example.org/paper.pdf"}
    key = cache.cache_key("fetch", parts)
    with pytest.raises(ValueError):
        cache.write_refusal(key, parts, status=429, content_type="text/html")
    assert not (tmp_path / key).exists()


def test_a_truncated_file_reads_as_a_miss(tmp_path) -> None:
    # write is one plain write, so a run killed inside it leaves half a file.
    # A miss costs one fetch, and a raised error costs the whole Stage.
    (tmp_path / "half.json").write_text('{"parts": {"a": 1}, "val', encoding="utf-8")

    assert cache.read("half.json") is None
    assert cache.read_parts("half.json") == {}
    assert cache.read_bytes("half.json") is None


def test_truncated_bytes_read_as_a_miss(tmp_path) -> None:
    key, _ = stored_pdf(b"%PDF-1.7 a whole file")
    stored = json.loads((tmp_path / key).read_text(encoding="utf-8"))
    (tmp_path / stored["value"]["file"]).write_bytes(b"%PDF-1.7 half")

    assert cache.read_bytes(key) is None
