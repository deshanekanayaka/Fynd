"""Stage 2: the student picks a Topic.

`offer_topics` asks a model for Topics. `accept_topic` searches for the picked
one and decides whether Fynd keeps it. ADR 0006 keeps the saving in the runner.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Any, Final, Protocol

from fynd import prompts
from fynd.models import SearchResult, Topic

# Ask for 10 and show 5 to 8. The extra two cover the items the shape check
# drops, and 5 to 8 is the PRD promise to the student.
TOPICS_TO_ASK_FOR: Final = 10
MINIMUM_TOPICS_TO_SHOW: Final = 5
MAXIMUM_TOPICS_TO_SHOW: Final = 8

# The threshold moved from 5 to 3 on 2026-10-07. See ADR 0002.
OPEN_PAPER_THRESHOLD: Final = 3

# The Evidence window of ADR 0008, in years.
EVIDENCE_WINDOW_YEARS: Final = 5

TOPIC_PROMPT_NAME: Final = "propose-topics-v1"

# The cache key carries this version, so a changed shape misses the cache.
TOPIC_LIST_SCHEMA_VERSION: Final = 1

TOPIC_LIST_SCHEMA: Final[dict[str, Any]] = {
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

# What the retry adds to the prompt. The text differs from round 1, so the
# input hash differs, so the retry misses the cache and reaches the model.
# Without it the second ask reads the first unusable answer back from disk.
RETRY_NOTE: Final = (
    "Your earlier answer held too few usable Topics. "
    "Every Topic needs a label and a query, and neither field is empty."
)


class AskModel(Protocol):
    """The model call stage 2 needs, which the edge supplies."""

    def __call__(
        self,
        filled_prompt: str,
        prompt_sha256: str,
        schema: dict[str, Any],
        schema_version: int,
    ) -> Any: ...


class Search(Protocol):
    """The search call stage 2 needs, which the edge supplies."""

    def __call__(self, query: str, year_from: int) -> SearchResult: ...


class TopicListUnusable(Exception):
    """Raised when the model returns no usable Topic list twice in a row.

    This is a broken Stage, so the runner writes a failed `stage_run` row. A
    Topic under the threshold is a decision instead, and never arrives here.
    """


@dataclass(frozen=True)
class TopicKept:
    """An accepted Topic Pick, holding the Topic and its Open copy count."""

    topic: Topic
    open_paper_count: int


@dataclass(frozen=True)
class TopicBelowThreshold:
    """A Topic Pick with too few Papers that have an Open copy.

    Not a failure. The count shows next to the Topic, the rest of the list stays
    pickable, and the Re-roll is not spent. See ADR 0002.
    """

    topic: Topic
    open_paper_count: int


@dataclass(frozen=True)
class TopicNotOffered:
    """A refused Topic Pick, holding the slug that was refused."""

    pick: str


TopicDecision = TopicKept | TopicBelowThreshold | TopicNotOffered


def first_year_in_window(today: dt.date) -> int:
    """Return the first year the Evidence window accepts."""
    # The caller passes the date, so this file holds no clock. A 5 year window
    # in 2026 starts in 2022, which is why the sum subtracts one less.
    return today.year - (EVIDENCE_WINDOW_YEARS - 1)


def slugify(label: str) -> str:
    """Turn a label into the slug a Pick names."""
    kept_characters = []
    for character in label.lower():
        # isalnum alone is true for an accented letter and for CJK, and a slug
        # travels in a link, so the test also asks for plain ASCII.
        if character.isascii() and character.isalnum():
            kept_characters.append(character)
        else:
            # Any run of other characters becomes one hyphen.
            if kept_characters and kept_characters[-1] != "-":
                kept_characters.append("-")
    return "".join(kept_characters).strip("-")


def topics_from_answer(answer: Any) -> list[Topic]:
    """Turn a model answer into Topics, dropping every item Fynd cannot use."""
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
        # Two labels that make one slug are one Topic to a Pick, so the first
        # one stays and the second is dropped.
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        topics.append(Topic(slug=slug, label=label, query=query))
    return topics


def offer_topics(domain: str, ask_model: AskModel, avoid: list[str] | None = None) -> list[Topic]:
    """Return the Topics the student chooses from.

    `avoid` holds the labels of a list the student already saw, which is a
    Re-roll. An answer Fynd cannot use gets one retry, then the Stage breaks.
    """
    prompt = prompts.load(TOPIC_PROMPT_NAME)
    avoid_list = "none" if not avoid else ", ".join(avoid)

    for attempt in (1, 2):
        filled = prompts.fill(
            prompt,
            {
                "TOPIC_COUNT": str(TOPICS_TO_ASK_FOR),
                "DOMAIN_NAME": domain,
                "AVOID_LIST": avoid_list,
                # Round 1 says nothing. Round 2 says why it is asking again,
                # and that difference is what makes the retry a real ask.
                "RETRY_NOTE": "" if attempt == 1 else RETRY_NOTE,
            },
        )
        answer = ask_model(
            filled_prompt=filled,
            prompt_sha256=prompt.sha256,
            schema=TOPIC_LIST_SCHEMA,
            schema_version=TOPIC_LIST_SCHEMA_VERSION,
        )
        topics = topics_from_answer(answer)
        if len(topics) >= MINIMUM_TOPICS_TO_SHOW:
            return topics[:MAXIMUM_TOPICS_TO_SHOW]
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
    """Keep the picked Topic when a real search finds enough open Papers.

    `offered` is the list the runner saved for this Project, and never a list
    the caller sent, because the secret link is the only access control.
    """
    picked = None
    for topic in offered:
        if topic.slug == pick:
            picked = topic
            break
    if picked is None:
        return TopicNotOffered(pick=pick)

    # The search runs here, because the threshold rule belongs to the Stage.
    result = search(query=picked.query, year_from=first_year_in_window(today))
    count = result.open_copy_count
    if count >= OPEN_PAPER_THRESHOLD:
        return TopicKept(topic=picked, open_paper_count=count)
    return TopicBelowThreshold(topic=picked, open_paper_count=count)
