"""The model client must not turn a broken reply into an answer, or cache one."""

import json

import pytest

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
    """Builds a stand in for anthropic.Anthropic that answers from memory."""

    class Messages:
        def create(self, **kwargs):
            calls.append(kwargs)
            return reply

    class Client:
        def __init__(self) -> None:
            self.messages = Messages()

    return Client


@pytest.fixture
def replying(monkeypatch):
    """Points the client at one reply from memory, and records the requests.

    Every test needs this, and the returned list is the requests the client
    tried to send, so a test can count them.
    """

    def use(text: str, stop_reason: str = "end_turn") -> list:
        calls: list = []
        monkeypatch.setattr(
            "fynd.claude.anthropic.Anthropic",
            client_that_replies(Reply(text, stop_reason), calls),
        )
        return calls

    return use


def ask(prompt_sha256: str = "aaa"):
    """Asks the one question every test here asks."""
    return ask_for_json("a prompt", prompt_sha256, SCHEMA, 1)


def test_a_good_reply_is_parsed_and_cached(replying) -> None:
    calls = replying(json.dumps({"topics": ["a"]}))

    value = ask()

    assert value == {"topics": ["a"]}
    assert len(calls) == 1
    # The second ask reads the answer from disk and reaches no client.
    assert ask() == {"topics": ["a"]}
    assert len(calls) == 1


def test_the_request_names_the_model_and_sends_no_decoding_parameter(replying) -> None:
    # Replay comes from the cache; the request sends no decoding settings.
    calls = replying(json.dumps({"topics": []}))

    ask()

    assert calls[0]["model"] == HAIKU
    # Preserve the request shape established by the live-run regression.
    assert "temperature" not in calls[0]
    assert "top_p" not in calls[0]
    assert "top_k" not in calls[0]
    assert calls[0]["output_config"]["format"]["schema"] == SCHEMA


def test_a_changed_prompt_hash_is_a_different_cache_entry(replying) -> None:
    calls = replying(json.dumps({"topics": []}))

    ask()
    ask(prompt_sha256="bbb")

    assert len(calls) == 2


@pytest.mark.parametrize(
    ("text", "stop_reason"),
    [
        # A truncated reply still carries text, so the stop reason is the only
        # honest check. Without it the broken JSON raises far from the cause.
        ('{"topics": [{"label": "half a top', "max_tokens"),
        ("I cannot help with that.", "end_turn"),
        ("", "end_turn"),
    ],
    ids=["the token ceiling", "text that is not json", "an empty reply"],
)
def test_a_reply_that_is_not_an_answer_is_refused_and_not_cached(
    replying, tmp_path, text: str, stop_reason: str
) -> None:
    replying(text, stop_reason)

    with pytest.raises(ModelRefused):
        ask()

    assert list(tmp_path.iterdir()) == []


def test_a_refused_reply_is_asked_again_on_the_next_run(replying, tmp_path) -> None:
    # ADR 0004: a failed reply is never cached, so the next run asks again.
    calls = replying("not json")

    for _ in (1, 2):
        with pytest.raises(ModelRefused):
            ask()

    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == []
