"""Stage 2 offers Topics from a model, then keeps one only if a real search agrees."""

import datetime as dt

import pytest

from fynd import reasons
from fynd.models import OpenCopy, Paper, SearchResult, Topic
from fynd.openalex import Resolution, WorkNotRead
from fynd.stages.stage2 import (
    MAXIMUM_TOPICS_TO_SHOW,
    MINIMUM_TOPICS_TO_SHOW,
    OPEN_PAPER_THRESHOLD,
    TOPICS_TO_ASK_FOR,
    TopicBelowThreshold,
    TopicKept,
    TopicListUnusable,
    TopicNotOffered,
    accept_topic,
    first_year_in_window,
    offer_topics,
    slugify,
    topics_from_answer,
)


def answer_with(labels: list[str]):
    """Builds a model answer that holds one item for each label."""
    return {"topics": [{"label": label, "query": f"{label} search"} for label in labels]}


def model_that_returns(*answers, calls: list):
    """Builds a fake ask_model that returns each answer in turn.

    A test spends no tokens and reaches no network. ADR 0006 asks for exactly
    this, which is why the Stage takes the model as an argument.
    """

    def ask_model(filled_prompt, prompt_sha256, schema, schema_version):
        calls.append(filled_prompt)
        return answers[len(calls) - 1]

    return ask_model


def search_that_returns(open_copies: int, calls: list):
    """Builds a fake search that returns a fixed number of Papers with an Open copy.

    Every Paper carries the Semantic Scholar link and a digital object
    identifier, because the gate now looks each identifier up.
    """

    def search(query: str, year_from: int) -> SearchResult:
        calls.append((query, year_from))
        papers = []
        for number in range(open_copies):
            papers.append(
                Paper(
                    paper_id=f"p{number}",
                    title=f"Paper {number}",
                    doi=f"10.0/p{number}",
                    open_copy_url=f"https://repository.example/{number}.pdf",
                )
            )
        return SearchResult(query=query, total=open_copies, papers=papers)

    return search


def resolve_that_gives(candidates: int, calls: list | None = None):
    """Builds a fake lookup that names a candidate for the first few Papers.

    The fake answers for the identifiers `10.0/p0` upward, which is what
    `search_that_returns` hands out.
    """

    def resolve(doi: str) -> Resolution:
        if calls is not None:
            calls.append(doi)
        number = int(doi.rsplit("p", 1)[-1])
        if number < candidates:
            found = OpenCopy(url=f"https://repository.example/{number}.pdf", host="x")
            return Resolution(found=True, candidates=(found,))
        return Resolution(found=True, reason=reasons.NO_PDF_LINK)

    return resolve


def test_the_evidence_window_starts_five_years_back_counting_this_year() -> None:
    # A 5 year window in 2026 starts in 2022, which is five calendar years.
    assert first_year_in_window(dt.date(2026, 10, 8)) == 2022


def test_a_slug_holds_letters_digits_and_hyphens_only() -> None:
    assert slugify("Household energy forecasting (UK)") == "household-energy-forecasting-uk"
    assert slugify("Demand response: 2026!") == "demand-response-2026"


def test_offer_topics_turns_a_model_answer_into_topics() -> None:
    calls: list = []
    labels = ["Household energy forecasting", "Heat pump sizing", "Fuel poverty mapping"]
    labels += ["Grid flexibility markets", "Smart meter data quality"]

    topics = offer_topics("energy", model_that_returns(answer_with(labels), calls=calls))

    assert len(topics) == 5
    assert topics[0] == Topic(
        slug="household-energy-forecasting",
        label="Household energy forecasting",
        query="Household energy forecasting search",
    )


def test_offer_topics_names_the_domain_in_the_prompt() -> None:
    calls: list = []
    labels = [f"Topic {number}" for number in range(MINIMUM_TOPICS_TO_SHOW)]

    offer_topics("energy", model_that_returns(answer_with(labels), calls=calls))

    assert "Domain: energy" in calls[0]
    assert "none" in calls[0]


def test_a_re_roll_names_the_topics_to_avoid() -> None:
    # Temperature is zero, so round 2 must ask a different question or the cache
    # serves the same list back. See ADR 0004.
    calls: list = []
    labels = [f"Topic {number}" for number in range(MINIMUM_TOPICS_TO_SHOW)]

    offer_topics(
        "energy",
        model_that_returns(answer_with(labels), calls=calls),
        avoid=["Heat pump sizing", "Fuel poverty mapping"],
    )

    assert "Heat pump sizing, Fuel poverty mapping" in calls[0]


def test_two_labels_that_make_one_slug_keep_the_first_topic() -> None:
    # A Pick names a slug, so two Topics with the same slug are one Topic.
    answer = answer_with(["Heat pumps", "Heat pumps!", "Fuel poverty", "Grid", "Meters"])

    topics = topics_from_answer(answer)

    assert [topic.slug for topic in topics] == [
        "heat-pumps",
        "fuel-poverty",
        "grid",
        "meters",
    ]


def test_an_item_with_an_empty_field_is_dropped() -> None:
    answer = {"topics": [{"label": "", "query": "q"}, {"label": "Grid", "query": ""}]}

    assert topics_from_answer(answer) == []


def test_a_short_list_gets_one_retry() -> None:
    calls: list = []
    good = answer_with([f"Topic {number}" for number in range(MINIMUM_TOPICS_TO_SHOW)])

    topics = offer_topics(
        "energy",
        model_that_returns(answer_with(["Only one"]), good, calls=calls),
    )

    assert len(calls) == 2
    assert len(topics) == MINIMUM_TOPICS_TO_SHOW


def test_the_retry_asks_a_different_question() -> None:
    # This is the regression test for a real bug. The model is deterministic and
    # every reply is cached, so a retry that sends the same text reads the first
    # unusable answer straight back from disk and fails for ever. The round 2
    # prompt must differ, which is what makes the second ask a real ask.
    calls: list = []
    good = answer_with([f"Topic {number}" for number in range(MINIMUM_TOPICS_TO_SHOW)])

    offer_topics("energy", model_that_returns(answer_with(["Only one"]), good, calls=calls))

    assert calls[0] != calls[1]
    assert "earlier answer" in calls[1]


def test_the_prompt_names_the_number_of_topics_to_ask_for() -> None:
    # The constant and the prompt file must not drift apart.
    calls: list = []
    labels = [f"Topic {number}" for number in range(MINIMUM_TOPICS_TO_SHOW)]

    offer_topics("energy", model_that_returns(answer_with(labels), calls=calls))

    assert f"Propose {TOPICS_TO_ASK_FOR} Topics" in calls[0]


def test_the_offered_list_never_passes_the_prd_maximum() -> None:
    # The PRD promises the student 5 to 8 Topics, and the model is asked for 10
    # so the shape check has items to drop.
    calls: list = []
    labels = [f"Topic {number}" for number in range(TOPICS_TO_ASK_FOR)]

    topics = offer_topics("energy", model_that_returns(answer_with(labels), calls=calls))

    assert len(topics) == MAXIMUM_TOPICS_TO_SHOW


def test_a_slug_drops_a_character_that_is_not_ascii() -> None:
    # A slug travels in a link, so an accented letter does not belong in one.
    assert slugify("Modelisation energetique") == "modelisation-energetique"
    assert slugify("Modélisation énergétique") == "mod-lisation-nerg-tique"


def test_a_short_list_twice_breaks_the_stage() -> None:
    # A broken model answer is a failed Stage, and not a decision for the student.
    calls: list = []
    short = answer_with(["Only one"])

    with pytest.raises(TopicListUnusable):
        offer_topics("energy", model_that_returns(short, short, calls=calls))

    assert len(calls) == 2


def test_accept_topic_keeps_a_topic_the_lookup_agrees_with() -> None:
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]
    calls: list = []

    answer = accept_topic(
        "grid",
        offered,
        search_that_returns(OPEN_PAPER_THRESHOLD, calls=calls),
        resolve_that_gives(OPEN_PAPER_THRESHOLD),
        today=dt.date(2026, 10, 8),
    )

    assert answer == TopicKept(topic=offered[0], open_paper_count=OPEN_PAPER_THRESHOLD)


def test_accept_topic_searches_with_the_query_and_the_window() -> None:
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]
    calls: list = []

    accept_topic(
        "grid",
        offered,
        search_that_returns(3, calls=calls),
        resolve_that_gives(3),
        today=dt.date(2026, 1, 1),
    )

    assert calls == [("grid flexibility", 2022)]


def test_the_gate_counts_the_papers_with_a_candidate_and_not_the_search_field() -> None:
    # Semantic Scholar names a link for every Paper here, and only two of them
    # hold a file Fynd may fetch. The student sees the two. See ADR 0012.
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]
    search = search_that_returns(6, calls=[])

    answer = accept_topic(
        "grid", offered, search, resolve_that_gives(2), today=dt.date(2026, 10, 8)
    )

    assert search(query="grid flexibility", year_from=2022).open_copy_count == 6
    assert answer == TopicBelowThreshold(topic=offered[0], open_paper_count=2)


def test_a_topic_under_the_threshold_is_not_a_failure() -> None:
    # The count shows next to the Topic, the list stays pickable, and the
    # Re-roll is not spent. See ADR 0002.
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]

    answer = accept_topic(
        "grid",
        offered,
        search_that_returns(OPEN_PAPER_THRESHOLD, calls=[]),
        resolve_that_gives(OPEN_PAPER_THRESHOLD - 1),
        today=dt.date(2026, 10, 8),
    )

    assert answer == TopicBelowThreshold(
        topic=offered[0], open_paper_count=OPEN_PAPER_THRESHOLD - 1
    )


def test_a_paper_with_no_identifier_costs_no_lookup_and_does_not_count() -> None:
    # OpenAlex is asked by identifier alone. The pipeline would still try the
    # Semantic Scholar link of such a Paper, so the gate counts low, which is
    # the safe side of a promise.
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]
    looked_up: list = []

    def search(query: str, year_from: int) -> SearchResult:
        return SearchResult(
            query=query,
            total=2,
            papers=[
                Paper(paper_id="a", title="A", open_copy_url="https://repo.example/a.pdf"),
                Paper(paper_id="b", title="B", open_copy_url="https://repo.example/b.pdf"),
            ],
        )

    answer = accept_topic(
        "grid",
        offered,
        search,
        resolve_that_gives(0, calls=looked_up),
        today=dt.date(2026, 10, 8),
    )

    assert answer == TopicBelowThreshold(topic=offered[0], open_paper_count=0)
    assert looked_up == []


def test_a_lookup_that_fails_counts_low_and_does_not_break_the_stage() -> None:
    # ADR 0006 asks accept_topic for a decision. One Paper OpenAlex refused to
    # answer about is a Paper Fynd cannot promise, so it does not count.
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]
    working = resolve_that_gives(4)

    def resolve(doi: str) -> Resolution:
        if doi == "10.0/p1":
            raise WorkNotRead("OpenAlex answered 503 for the identifier 10.0/p1.")
        return working(doi)

    answer = accept_topic(
        "grid", offered, search_that_returns(4, calls=[]), resolve, today=dt.date(2026, 10, 8)
    )

    assert answer == TopicKept(topic=offered[0], open_paper_count=3)


def test_a_pick_the_stage_never_offered_is_refused_without_a_search() -> None:
    # The gate reads the saved offered list, because the secret link is the only
    # access control and a caller sends any slug it likes.
    calls: list = []
    offered = [Topic(slug="grid", label="Grid", query="grid flexibility")]

    answer = accept_topic(
        "nuclear-fusion",
        offered,
        search_that_returns(9, calls=calls),
        resolve_that_gives(9),
        today=dt.date(2026, 10, 8),
    )

    assert answer == TopicNotOffered(pick="nuclear-fusion")
    assert calls == []
