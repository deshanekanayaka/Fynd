"""Stage 2: the student picks a Topic.

Two named jobs, as ADR 0006 requires. `offer_topics` asks a model for the
Topics the student chooses from, and `accept_topic` runs the real search for
the picked Topic and decides whether Fynd keeps it.

The rules of stage 2 live here and nowhere else. This file knows nothing about
HTTP, nothing about the command line, and nothing about Postgres. The runner
saves the offered list and the answer.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Protocol

from fynd import prompts
from fynd.models import SearchResult, Topic

# Fynd asks the model for 10 Topics, and shows the ones that survive the shape
# check. The PRD promises the student 5 to 8, so a list that falls under 5 is a
# broken reply and not a short list.
TOPICS_TO_ASK_FOR = 10
MINIMUM_TOPICS_TO_SHOW = 5

# A Topic is kept only when the real search returns this many Papers with an
# Open copy. The threshold moved from 5 to 3 on 2026-10-07. See ADR 0002.
OPEN_PAPER_THRESHOLD = 3

# The Evidence window from ADR 0008. A Claim that proves a Problem is real must
# come from a Source inside it, so stage 2 counts only Papers inside it too.
EVIDENCE_WINDOW_YEARS = 5

# The prompt file, and the shape its answer must take. Both belong to the cache
# key, so a change to either one misses the cache. See ADR 0004.
TOPIC_PROMPT_NAME = "propose-topics-v1"
TOPIC_LIST_SCHEMA_VERSION = 1
TOPIC_LIST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["label", "query"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["topics"],
    "additionalProperties": False,
}


class AskModel(Protocol):
    """How stage 2 reaches a model.

    A real run passes `fynd.claude.ask_for_json`. A test passes a function of
    three lines that returns a fixed answer, so the test spends no tokens.
    """

    def __call__(
        self,
        filled_prompt: str,
        prompt_sha256: str,
        schema: dict[str, Any],
        schema_version: int,
    ) -> Any: ...


class Search(Protocol):
    """How stage 2 reaches the search. A test passes a function instead."""

    def __call__(self, query: str, year_from: int) -> SearchResult: ...


class TopicListUnusable(Exception):
    """Raised when the model returns no usable Topic list twice in a row.

    This is a broken Stage and not a decision, so the runner writes a failed
    `stage_run` row. A Topic under the Open copy threshold is a decision, and
    it never arrives here.
    """


@dataclass(frozen=True)
class TopicKept:
    """The search found enough Papers with an Open copy, so Fynd keeps the Topic."""

    topic: Topic
    open_paper_count: int


@dataclass(frozen=True)
class TopicBelowThreshold:
    """The Topic was offered, and the search found too few Papers with an Open copy.

    This is not a failure. The count shows next to that Topic, the rest of the
    list stays pickable, and the Re-roll is not spent. See ADR 0002.
    """

    topic: Topic
    open_paper_count: int


@dataclass(frozen=True)
class TopicNotOffered:
    """The Pick names a Topic this Stage never offered."""

    pick: str


# What `accept_topic` returns. One class for each answer, so no answer carries
# a field that means nothing. Stage 1 does the same with two classes.
TopicDecision = TopicKept | TopicBelowThreshold | TopicNotOffered


def first_year_in_window(today: dt.date) -> int:
    """Return the first year the Evidence window accepts.

    The caller passes the date, so this file holds no clock and a test needs no
    patching. A 5 year window in 2026 starts in 2022, which is why the sum
    subtracts one less than the window.
    """
    return today.year - (EVIDENCE_WINDOW_YEARS - 1)


def slugify(label: str) -> str:
    """Turn a label into the value a Pick names.

    A Pick travels in a request body and in a link, so it holds lower case
    letters, digits, and hyphens only. ADR 0003 says stage 2 names a Topic slug.
    """
    kept_characters = []
    for character in label.lower():
        if character.isalnum():
            kept_characters.append(character)
        else:
            # Any run of other characters becomes one hyphen.
            if kept_characters and kept_characters[-1] != "-":
                kept_characters.append("-")
    return "".join(kept_characters).strip("-")


def topics_from_answer(answer: Any) -> list[Topic]:
    """Turn one model answer into Topics, and drop every unusable item.

    A model returns an item with an empty field, or two labels that produce one
    slug. Two Topics with the same slug are the same Topic to a Pick, so the
    first one stays and the second is dropped.
    """
    if not isinstance(answer, dict):
        return []

    topics: list[Topic] = []
    seen_slugs = set()
    for item in answer.get("topics") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        query = str(item.get("query") or "").strip()
        if not label or not query:
            continue
        slug = slugify(label)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        topics.append(Topic(slug=slug, label=label, query=query))
    return topics


def offer_topics(domain: str, ask_model: AskModel, avoid: list[str] | None = None) -> list[Topic]:
    """Return the Topics the student chooses from.

    `avoid` holds the labels of a list the student already saw. The round 2
    prompt names them, so a Re-roll asks the model a different question and the
    cache serves no stale list. See ADR 0004.

    A reply that does not match the shape gets one retry, because a second ask
    costs one call and a failed Stage costs the student the whole round.
    """
    prompt = prompts.load(TOPIC_PROMPT_NAME)
    avoid_list = "none" if not avoid else ", ".join(avoid)
    filled = prompts.fill(
        prompt,
        {"DOMAIN_NAME": domain, "AVOID_LIST": avoid_list},
    )

    for attempt in (1, 2):
        answer = ask_model(
            filled_prompt=filled,
            prompt_sha256=prompt.sha256,
            schema=TOPIC_LIST_SCHEMA,
            schema_version=TOPIC_LIST_SCHEMA_VERSION,
        )
        topics = topics_from_answer(answer)
        if len(topics) >= MINIMUM_TOPICS_TO_SHOW:
            return topics
        if attempt == 2:
            raise TopicListUnusable(
                f"The model returned {len(topics)} usable Topics for the Domain "
                f"{domain}, and stage 2 shows at least {MINIMUM_TOPICS_TO_SHOW}."
            )
    raise AssertionError("unreachable")


def accept_topic(
    pick: str,
    offered: list[Topic],
    search: Search,
    today: dt.date,
) -> TopicDecision:
    """Decide what happens to the Topic the student picked.

    `offered` is the list the runner saved for this Project, and never a list
    the caller sent with the Pick. The secret link is the only access control,
    so a caller can send any slug it likes.

    The search runs here, because "a Topic is kept only when a real search
    returns enough open Papers" is a rule of this Stage. See ADR 0006.
    """
    picked = None
    for topic in offered:
        if topic.slug == pick:
            picked = topic
            break
    if picked is None:
        return TopicNotOffered(pick=pick)

    result = search(query=picked.query, year_from=first_year_in_window(today))
    count = result.open_copy_count
    if count >= OPEN_PAPER_THRESHOLD:
        return TopicKept(topic=picked, open_paper_count=count)
    return TopicBelowThreshold(topic=picked, open_paper_count=count)
