"""A prompt is a file, and its hash is what the cache key carries."""

import pytest

from fynd import prompts


def write_prompt(directory, name: str, text: str) -> None:
    (directory / f"{name}.md").write_text(text, encoding="utf-8")


def test_load_returns_the_text_and_a_hash(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_PROMPTS_DIR", str(tmp_path))
    write_prompt(tmp_path, "test-v1", "Propose Topics for {{DOMAIN_NAME}}.")
    prompt = prompts.load("test-v1")
    assert prompt.name == "test-v1"
    assert prompt.text == "Propose Topics for {{DOMAIN_NAME}}."
    assert len(prompt.sha256) == 64


def test_a_typo_fixed_without_a_rename_changes_the_hash(tmp_path, monkeypatch) -> None:
    # This is the whole reason the hash exists. ADR 0004 says a published number
    # must never belong to a prompt that no longer exists.
    monkeypatch.setenv("FYND_PROMPTS_DIR", str(tmp_path))
    write_prompt(tmp_path, "test-v1", "Propose Topics.")
    before = prompts.load("test-v1").sha256
    write_prompt(tmp_path, "test-v1", "Propose 10 Topics.")
    after = prompts.load("test-v1").sha256
    assert before != after


def test_fill_replaces_every_placeholder(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_PROMPTS_DIR", str(tmp_path))
    write_prompt(tmp_path, "test-v1", "Domain: {{DOMAIN_NAME}}. Avoid: {{AVOID_LIST}}.")
    prompt = prompts.load("test-v1")
    filled = prompts.fill(prompt, {"DOMAIN_NAME": "energy", "AVOID_LIST": "none"})
    assert filled == "Domain: energy. Avoid: none."


def test_fill_refuses_a_placeholder_the_file_does_not_hold(tmp_path, monkeypatch) -> None:
    # A renamed placeholder must break loudly, and not fill nothing in silence.
    # DOMAIN is also a prefix of DOMAIN_NAME, so this test proves that the
    # braces stop a half replacement.
    monkeypatch.setenv("FYND_PROMPTS_DIR", str(tmp_path))
    write_prompt(tmp_path, "test-v1", "Domain: {{DOMAIN_NAME}}.")
    prompt = prompts.load("test-v1")
    with pytest.raises(KeyError):
        prompts.fill(prompt, {"DOMAIN": "energy"})


def test_fill_refuses_to_leave_a_placeholder_behind(tmp_path, monkeypatch) -> None:
    # An unfilled placeholder would travel to the model as braces, and the
    # prompt hash would not show the mistake.
    monkeypatch.setenv("FYND_PROMPTS_DIR", str(tmp_path))
    write_prompt(tmp_path, "test-v1", "Domain: {{DOMAIN_NAME}}. Avoid: {{AVOID_LIST}}.")
    prompt = prompts.load("test-v1")
    with pytest.raises(KeyError):
        prompts.fill(prompt, {"DOMAIN_NAME": "energy"})


def test_the_real_topic_prompt_holds_every_placeholder() -> None:
    # The shipped prompt and the Stage that fills it must agree.
    prompt = prompts.load("propose-topics-v1")
    for placeholder in ("{{TOPIC_COUNT}}", "{{DOMAIN_NAME}}", "{{AVOID_LIST}}", "{{RETRY_NOTE}}"):
        assert placeholder in prompt.text
