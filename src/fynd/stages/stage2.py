"""Offers AI-generated Topics and checks the student's Topic Pick.

The CLI supplies model, search, and DOI-lookup functions. This Stage fills
the Topic prompt, filters the returned entries, and requires three Papers
with OpenAlex file candidates for a Pick. It returns decisions; the future
runner will own Project persistence and Re-roll limits (ADR 0006)."""

import datetime as dt
from dataclasses import dataclass
from typing import Any, Final, Protocol

from fynd import prompts
from fynd.models import SearchResult, Topic
from fynd.openalex import Resolve, WorkNotRead

# Ask for 10 so filtering can still leave the 5–8 Topics promised to the student.
TOPICS_TO_ASK_FOR: Final = 10
MINIMUM_TOPICS_TO_SHOW: Final = 5
MAXIMUM_TOPICS_TO_SHOW: Final = 8

# Require 3 candidate-bearing Papers before keeping the Topic (ADR 0002).
OPEN_PAPER_THRESHOLD: Final = 3

# Count calendar years including the current one, as specified in ADR 0008.
EVIDENCE_WINDOW_YEARS: Final = 5

# Keep the display label separate from the subject-only search query (ADR 0015).
SEEDED_TOPIC: Final = "United Kingdom household energy forecasting"
SEEDED_TOPIC_QUERY: Final = "household energy forecasting"

TOPIC_PROMPT_NAME: Final = "propose-topics-v1"

# Bump this when the response schema changes so cached old shapes are not reused.
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

# Change the second request text so it does not replay the first unusable list.
RETRY_NOTE: Final = (
    "Your earlier answer held too few usable Topics. "
    "Every Topic needs a label and a query, and neither field is empty."
)


class AskModel(Protocol):
    """A supplied model function accepting filled instructions and a response schema."""

    def __call__(
        self,
        filled_prompt: str,
        prompt_sha256: str,
        schema: dict[str, Any],
        schema_version: int,
    ) -> Any: ...


class Search(Protocol):
    """A supplied Paper search function accepting subject words and a first year."""

    def __call__(self, query: str, year_from: int) -> SearchResult: ...


class TopicListUnusable(Exception):
    """Raised when two returned lists both contain fewer than five usable Topics."""


@dataclass(frozen=True)
class TopicKept:
    """An accepted Topic Pick with its qualifying Paper count."""

    topic: Topic
    open_paper_count: int


@dataclass(frozen=True)
class TopicBelowThreshold:
    """A Topic Pick with fewer than three Papers offering file candidates."""

    topic: Topic
    open_paper_count: int


@dataclass(frozen=True)
class TopicNotOffered:
    """A refused Pick whose slug was absent from the offered Topics."""

    pick: str


TopicDecision = TopicKept | TopicBelowThreshold | TopicNotOffered


def first_year_in_window(today: dt.date) -> int:
    """Returns the first year of the five-calendar-year Evidence window."""
    # Including the current year means 2026 accepts Papers from 2022 onward.
    return today.year - (EVIDENCE_WINDOW_YEARS - 1)


def slugify(label: str) -> str:
    """Converts a label to lowercase ASCII letters, digits, and single hyphens."""
    kept_characters = []
    for character in label.lower():
        # Use a predictable ASCII slug even when the label contains other characters.
        if character.isascii() and character.isalnum():
            kept_characters.append(character)
        else:
            # Collapse consecutive separators into one hyphen.
            if kept_characters and kept_characters[-1] != "-":
                kept_characters.append("-")
    return "".join(kept_characters).strip("-")


def topics_from_answer(answer: Any) -> list[Topic]:
    """Builds Topics from returned entries, dropping empty fields and duplicate slugs."""
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
        # Duplicate slugs would make a Pick ambiguous, so retain only the first.
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        topics.append(Topic(slug=slug, label=label, query=query))
    return topics


def offer_topics(domain: str, ask_model: AskModel, avoid: list[str] | None = None) -> list[Topic]:
    """Returns five to eight Topics, retrying once if too few usable entries survive."""
    prompt = prompts.load(TOPIC_PROMPT_NAME)
    avoid_list = "none" if not avoid else ", ".join(avoid)

    for attempt in (1, 2):
        filled = prompts.fill(
            prompt,
            {
                "TOPIC_COUNT": str(TOPICS_TO_ASK_FOR),
                "DOMAIN_NAME": domain,
                "AVOID_LIST": avoid_list,
                # Change the input hash so the second attempt uses a different cache entry.
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


def count_papers_with_a_candidate(result: SearchResult, resolve: Resolve) -> int:
    """Counts Papers whose DOI lookup returns at least one file candidate."""
    count = 0
    for paper in result.papers:
        if not paper.doi:
            continue
        try:
            answer = resolve(paper.doi)
        except WorkNotRead:
            # A failed HTTP lookup cannot confirm a candidate; omit this Paper from the count.
            continue
        if answer.candidates:
            count += 1
    return count


def accept_topic(
    pick: str,
    offered: list[Topic],
    search: Search,
    resolve: Resolve,
    today: dt.date,
) -> TopicDecision:
    """Checks an offered Pick and keeps it when at least three Papers offer candidates."""
    picked = None
    for topic in offered:
        if topic.slug == pick:
            picked = topic
            break
    if picked is None:
        return TopicNotOffered(pick=pick)

    # Keep the literature threshold inside the Stage rather than its caller.
    result = search(query=picked.query, year_from=first_year_in_window(today))
    # Count OpenAlex file candidates, not Semantic Scholar’s unverified open-link field.
    count = count_papers_with_a_candidate(result, resolve)
    if count >= OPEN_PAPER_THRESHOLD:
        return TopicKept(topic=picked, open_paper_count=count)
    return TopicBelowThreshold(topic=picked, open_paper_count=count)
