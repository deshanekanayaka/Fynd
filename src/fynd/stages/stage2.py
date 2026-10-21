"""Stage 2: the student picks a Topic.

`offer_topics` asks a model for Topics. `accept_topic` searches for the picked
one and decides whether Fynd keeps it. ADR 0006 keeps the saving in the runner.
"""

import datetime as dt
from dataclasses import dataclass
from typing import Any, Final, Protocol

from fynd import prompts
from fynd.models import SearchResult, Topic
from fynd.openalex import Resolve, WorkNotRead

# Ask for 10 and show 5 to 8. The extra two cover the items the shape check
# drops, and 5 to 8 is the PRD promise to the student.
TOPICS_TO_ASK_FOR: Final = 10
MINIMUM_TOPICS_TO_SHOW: Final = 5
MAXIMUM_TOPICS_TO_SHOW: Final = 8

# The threshold moved from 5 to 3 on 2026-10-07. See ADR 0002.
OPEN_PAPER_THRESHOLD: Final = 3

# The Evidence window of ADR 0008, in years.
EVIDENCE_WINDOW_YEARS: Final = 5

# The one Topic fixed in the repository, which every published number of the
# retrieval work is measured on. It lives here so one string has one home, as
# SEEDED_DOMAINS does in stage1.py. See CONTEXT.md.
#
# Two strings and not one. The label is what a student reads, and it names the
# place, because the Problem belongs to a place and a Statistic proves it. The
# query is what a search and a ranking read, and it names the subject alone,
# because a method a student copies does not change at a border. The measured
# table of 2026-10-22 is the evidence: ranking with the label found 12 of the
# 39 relevant Papers and ranking with the query found 20. See ADR 0015.
SEEDED_TOPIC: Final = "United Kingdom household energy forecasting"
SEEDED_TOPIC_QUERY: Final = "household energy forecasting"

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
    """Returns the first year the Evidence window accepts."""
    # The caller passes the date, so this file holds no clock. A 5 year window
    # in 2026 starts in 2022, which is why the sum subtracts one less.
    return today.year - (EVIDENCE_WINDOW_YEARS - 1)


def slugify(label: str) -> str:
    """Turns a label into the slug a Pick names."""
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
    """Turns a model answer into Topics, dropping every item Fynd cannot use."""
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
    """Returns the Topics the student chooses from.

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


def count_papers_with_a_candidate(result: SearchResult, resolve: Resolve) -> int:
    """Counts the Papers of one search that offer a file Fynd may fetch.

    A Paper counts when OpenAlex names an open location with a PDF link on a
    host that holds a file, which is the candidate list the stage 4 pipeline
    fetches. It costs one cached lookup for each Paper and no download.

    A Paper with no identifier is not looked up and does not count, although
    the pipeline would still try its Semantic Scholar link as a last resort.
    The gate counts low on purpose, because a promise the pipeline cannot keep
    is the failure this gate exists to prevent. See ADR 0012 and issue 18.
    """
    count = 0
    for paper in result.papers:
        if not paper.doi:
            continue
        try:
            answer = resolve(paper.doi)
        except WorkNotRead:
            # One lookup that fails is not a broken Stage. ADR 0006 asks this
            # function for a decision, and a Paper Fynd could not ask about is
            # a Paper it cannot promise, so the count errs low as it does for
            # a Paper with no identifier.
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
    """Keeps the picked Topic when enough Papers offer a file Fynd may fetch.

    `offered` is the list the runner saved for this Project, and never a list
    the caller sent, because the secret link is the only access control.

    `resolve` is the OpenAlex lookup, and it has no default value, because the
    threshold rule belongs to the Stage and the edge wires the real one.
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
    # Semantic Scholar names a link for a Paper whose only address is a doi.org
    # lookup, and it claimed 14 of these 20 Papers while 10 hold a file. A
    # student who passes on the claimed number meets the truth two Stages
    # later, which is the failure this product exists to prevent.
    count = count_papers_with_a_candidate(result, resolve)
    if count >= OPEN_PAPER_THRESHOLD:
        return TopicKept(topic=picked, open_paper_count=count)
    return TopicBelowThreshold(topic=picked, open_paper_count=count)
