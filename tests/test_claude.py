"""The model client must not turn a broken reply into an answer, or cache one."""

import json

import pytest

from fynd import cache
from fynd.claude import HAIKU, ModelRefused, ask_for_json

SCHEMA = {"type": "object", "properties": {"topics": {"type": "array"}}}


class Block:
    """One content block of a reply."""

    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class Reply:
    """One reply from the API, with only the fields this client reads."""

    def __init__(self, text: str, stop_reason: str = "end_turn") -> None:
        self.content = [Block(text)] if text else []
        self.stop_reason = stop_reason


def client_that_replies(reply: Reply, calls: list):
    """Build a stand in for anthropic.Anthropic that answers from memory."""

    class Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return reply

    class Client:
        def __init__(self) -> None:
            self.messages = Messages()

    return Client


def test_a_good_reply_is_parsed_and_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    reply = Reply(json.dumps({"topics": ["a"]}))
    monkeypatch.setattr("fynd.claude.anthropic.Anthropic", client_that_replies(reply, calls))

    value = ask_for_json("a prompt", "aaa", SCHEMA, 1)

    assert value == {"topics": ["a"]}
    assert len(calls) == 1
    # The second ask reads the answer from disk and reaches no client.
    assert ask_for_json("a prompt", "aaa", SCHEMA, 1) == {"topics": ["a"]}
    assert len(calls) == 1


def test_the_request_fixes_the_model_and_the_temperature(tmp_path, monkeypatch) -> None:
    # ADR 0004 fixes decoding, so the same question returns the same answer.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    reply = Reply(json.dumps({"topics": []}))
    monkeypatch.setattr("fynd.claude.anthropic.Anthropic", client_that_replies(reply, calls))

    ask_for_json("a prompt", "aaa", SCHEMA, 1)

    assert calls[0]["model"] == HAIKU
    assert calls[0]["temperature"] == 0
    assert calls[0]["output_config"]["format"]["schema"] == SCHEMA


def test_a_changed_prompt_hash_is_a_different_cache_entry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    reply = Reply(json.dumps({"topics": []}))
    monkeypatch.setattr("fynd.claude.anthropic.Anthropic", client_that_replies(reply, calls))

    ask_for_json("a prompt", "aaa", SCHEMA, 1)
    ask_for_json("a prompt", "bbb", SCHEMA, 1)

    assert len(calls) == 2


def test_a_reply_that_hit_the_token_ceiling_is_refused(tmp_path, monkeypatch) -> None:
    # A truncated reply still carries text, so the stop reason is the only
    # honest check. Without it the broken JSON raises far from the cause.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    reply = Reply('{"topics": [{"label": "half a top', stop_reason="max_tokens")
    monkeypatch.setattr("fynd.claude.anthropic.Anthropic", client_that_replies(reply, []))

    with pytest.raises(ModelRefused):
        ask_for_json("a prompt", "aaa", SCHEMA, 1)

    assert list(tmp_path.iterdir()) == []


def test_text_that_is_not_json_is_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    reply = Reply("I cannot help with that.")
    monkeypatch.setattr("fynd.claude.anthropic.Anthropic", client_that_replies(reply, []))

    with pytest.raises(ModelRefused):
        ask_for_json("a prompt", "aaa", SCHEMA, 1)


def test_an_empty_reply_is_refused(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("fynd.claude.anthropic.Anthropic", client_that_replies(Reply(""), []))

    with pytest.raises(ModelRefused):
        ask_for_json("a prompt", "aaa", SCHEMA, 1)


def test_a_refused_reply_is_never_cached(tmp_path, monkeypatch) -> None:
    # ADR 0004: a failed reply is never cached, so the next run asks again.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    monkeypatch.setattr(
        "fynd.claude.anthropic.Anthropic", client_that_replies(Reply("not json"), calls)
    )

    for _ in (1, 2):
        with pytest.raises(ModelRefused):
            ask_for_json("a prompt", "aaa", SCHEMA, 1)

    assert len(calls) == 2
    assert cache.read(cache.cache_key("claude", {})) is None
