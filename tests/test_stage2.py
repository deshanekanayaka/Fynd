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


GRID = Topic(slug="grid", label="Grid", query="grid flexibility")
A_DAY = dt.date(2026, 10, 8)
ENOUGH_LABELS = [f"Topic {number}" for number in range(MINIMUM_TOPICS_TO_SHOW)]


def ask(*answers, avoid: list[str] | None = None) -> tuple[list[Topic], list[str]]:
    """Offers Topics from fake model answers, and hands back the prompts sent."""
    prompts: list = []
    topics = offer_topics("energy", model_that_returns(*answers, calls=prompts), avoid=avoid)
    return topics, prompts


def pick(
    slug: str = "grid",
    found: int = OPEN_PAPER_THRESHOLD,
    with_candidate: int | None = None,
    today: dt.date = A_DAY,
    searches: list | None = None,
    looked_up: list | None = None,
    search=None,
    resolve=None,
):
    """Picks one Topic against a fake search and a fake lookup.

    `found` is how many Papers the search returns, and `with_candidate` is how
    many of those OpenAlex names a free file for. They are the same number
    unless a test says otherwise.
    """
    return accept_topic(
        slug,
        [GRID],
        search or search_that_returns(found, calls=searches if searches is not None else []),
        resolve
        or resolve_that_gives(found if with_candidate is None else with_candidate, calls=looked_up),
        today=today,
    )


def test_the_evidence_window_starts_five_years_back_counting_this_year() -> None:
    # A 5 year window in 2026 starts in 2022, which is five calendar years.
    assert first_year_in_window(dt.date(2026, 10, 8)) == 2022


def test_a_slug_holds_letters_digits_and_hyphens_only() -> None:
    assert slugify("Household energy forecasting (UK)") == "household-energy-forecasting-uk"
    assert slugify("Demand response: 2026!") == "demand-response-2026"
    # A slug travels in a link, so an accented letter does not belong in one.
    assert slugify("Modelisation energetique") == "modelisation-energetique"
    assert slugify("Modélisation énergétique") == "mod-lisation-nerg-tique"


def test_offer_topics_turns_a_model_answer_into_topics() -> None:
    labels = ["Household energy forecasting", "Heat pump sizing", "Fuel poverty mapping"]
    labels += ["Grid flexibility markets", "Smart meter data quality"]

    topics, _ = ask(answer_with(labels))

    assert len(topics) == 5
    assert topics[0] == Topic(
        slug="household-energy-forecasting",
        label="Household energy forecasting",
        query="Household energy forecasting search",
    )


def test_offer_topics_names_the_domain_in_the_prompt() -> None:
    _, prompts = ask(answer_with(ENOUGH_LABELS))

    assert "Domain: energy" in prompts[0]
    assert "none" in prompts[0]


def test_the_prompt_names_the_number_of_topics_to_ask_for() -> None:
    # The constant and the prompt file must not drift apart.
    _, prompts = ask(answer_with(ENOUGH_LABELS))

    assert f"Propose {TOPICS_TO_ASK_FOR} Topics" in prompts[0]


def test_a_re_roll_names_the_topics_to_avoid() -> None:
    # Temperature is zero, so round 2 must ask a different question or the cache
    # serves the same list back. See ADR 0004.
    _, prompts = ask(answer_with(ENOUGH_LABELS), avoid=["Heat pump sizing", "Fuel poverty mapping"])

    assert "Heat pump sizing, Fuel poverty mapping" in prompts[0]


def test_two_labels_that_make_one_slug_keep_the_first_topic() -> None:
    # A Pick names a slug, so two Topics with the same slug are one Topic.
    answer = answer_with(["Heat pumps", "Heat pumps!", "Fuel poverty", "Grid", "Meters"])

    topics = topics_from_answer(answer)

    assert [topic.slug for topic in topics] == ["heat-pumps", "fuel-poverty", "grid", "meters"]


def test_an_item_with_an_empty_field_is_dropped() -> None:
    answer = {"topics": [{"label": "", "query": "q"}, {"label": "Grid", "query": ""}]}

    assert topics_from_answer(answer) == []


def test_the_offered_list_never_passes_the_prd_maximum() -> None:
    # The PRD promises the student 5 to 8 Topics, and the model is asked for 10
    # so the shape check has items to drop.
    topics, _ = ask(answer_with([f"Topic {number}" for number in range(TOPICS_TO_ASK_FOR)]))

    assert len(topics) == MAXIMUM_TOPICS_TO_SHOW


def test_a_short_list_gets_one_retry_and_the_retry_asks_a_different_question() -> None:
    # This is the regression test for a real bug. The model is deterministic and
    # every reply is cached, so a retry that sends the same text reads the first
    # unusable answer straight back from disk and fails for ever. The round 2
    # prompt must differ, which is what makes the second ask a real ask.
    topics, prompts = ask(answer_with(["Only one"]), answer_with(ENOUGH_LABELS))

    assert len(topics) == MINIMUM_TOPICS_TO_SHOW
    assert len(prompts) == 2
    assert prompts[0] != prompts[1]
    assert "earlier answer" in prompts[1]


def test_a_short_list_twice_breaks_the_stage() -> None:
    # A broken model answer is a failed Stage, and not a decision for the student.
    short = answer_with(["Only one"])
    prompts: list = []

    with pytest.raises(TopicListUnusable):
        offer_topics("energy", model_that_returns(short, short, calls=prompts))

    assert len(prompts) == 2


def test_accept_topic_keeps_a_topic_the_lookup_agrees_with() -> None:
    assert pick() == TopicKept(topic=GRID, open_paper_count=OPEN_PAPER_THRESHOLD)


def test_accept_topic_searches_with_the_query_and_the_window() -> None:
    searches: list = []

    pick(found=3, today=dt.date(2026, 1, 1), searches=searches)

    assert searches == [("grid flexibility", 2022)]


def test_the_gate_counts_the_papers_with_a_candidate_and_not_the_search_field() -> None:
    # Semantic Scholar names a link for every Paper here, and only two of them
    # hold a file Fynd may fetch. The student sees the two. See ADR 0012.
    search = search_that_returns(6, calls=[])

    answer = pick(search=search, with_candidate=2)

    assert search(query="grid flexibility", year_from=2022).open_copy_count == 6
    assert answer == TopicBelowThreshold(topic=GRID, open_paper_count=2)


def test_a_topic_under_the_threshold_is_not_a_failure() -> None:
    # The count shows next to the Topic, the list stays pickable, and the
    # Re-roll is not spent. See ADR 0002.
    answer = pick(with_candidate=OPEN_PAPER_THRESHOLD - 1)

    assert answer == TopicBelowThreshold(topic=GRID, open_paper_count=OPEN_PAPER_THRESHOLD - 1)


def test_a_paper_with_no_identifier_costs_no_lookup_and_does_not_count() -> None:
    # OpenAlex is asked by identifier alone. The pipeline would still try the
    # Semantic Scholar link of such a Paper, so the gate counts low, which is
    # the safe side of a promise.
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

    answer = pick(search=search, with_candidate=0, looked_up=looked_up)

    assert answer == TopicBelowThreshold(topic=GRID, open_paper_count=0)
    assert looked_up == []


def test_a_lookup_that_fails_counts_low_and_does_not_break_the_stage() -> None:
    # ADR 0006 asks accept_topic for a decision. One Paper OpenAlex refused to
    # answer about is a Paper Fynd cannot promise, so it does not count.
    working = resolve_that_gives(4)

    def resolve(doi: str) -> Resolution:
        if doi == "10.0/p1":
            raise WorkNotRead("OpenAlex answered 503 for the identifier 10.0/p1.")
        return working(doi)

    assert pick(found=4, resolve=resolve) == TopicKept(topic=GRID, open_paper_count=3)


def test_a_pick_the_stage_never_offered_is_refused_without_a_search() -> None:
    # The gate reads the saved offered list, because the secret link is the only
    # access control and a caller sends any slug it likes.
    searches: list = []

    answer = pick(slug="nuclear-fusion", found=9, searches=searches)

    assert answer == TopicNotOffered(pick="nuclear-fusion")
    assert searches == []
