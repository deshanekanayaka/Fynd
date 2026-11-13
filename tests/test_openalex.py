"""The second lookup has to find every open file, and rank a repository first."""

import httpx
import pytest

from fynd import reasons
from fynd.contact import ContactEmailMissing
from fynd.openalex import (
    OpenAlex,
    WorkNotRead,
    holds_no_file,
    open_candidates,
    reason_for_no_candidate,
)


def location(
    pdf_url: str | None = None,
    kind: str = "journal",
    rights: str | None = "cc-by",
    is_oa: bool = True,
    landing_page_url: str | None = None,
) -> dict:
    """Builds one OpenAlex location, holding only the fields Fynd reads."""
    return {
        "is_oa": is_oa,
        "pdf_url": pdf_url,
        "landing_page_url": landing_page_url,
        "license": rights,
        "source": {"type": kind},
    }


def work(*locations: dict, best: dict | None = None) -> dict:
    """Builds one OpenAlex work from its locations."""
    return {"best_oa_location": best, "locations": list(locations)}


JOURNAL = location("https://www.sciencedirect.com/aaa.pdf")
REPOSITORY = location("https://dro.dur.ac.uk/aaa.pdf", kind="repository")

# A real work carries a journal location and a repository location, and both
# are candidates now. The journal is also `best_oa_location`. See ADR 0012.
RECORDED_WORK = work(JOURNAL, REPOSITORY, best=JOURNAL)


def client_that_returns(status: int, reply: dict | None, calls: list) -> httpx.Client:
    """Builds an httpx client that answers every request from memory."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if reply is None:
            return httpx.Response(status)
        return httpx.Response(status, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler))


def resolve(reply: dict | None, doi: str = "10.1000/aaa", status: int = 200, calls=None):
    """Looks one identifier up against a client that answers from memory."""
    return OpenAlex(
        client=client_that_returns(status, reply, calls if calls is not None else [])
    ).resolve(doi)


def urls(answer) -> list[str]:
    return [copy.url for copy in answer.candidates]


def test_a_repository_ranks_before_a_journal() -> None:
    answer = resolve(RECORDED_WORK)

    assert answer.found is True
    assert answer.reason == ""
    assert urls(answer) == [
        "https://dro.dur.ac.uk/aaa.pdf",
        "https://www.sciencedirect.com/aaa.pdf",
    ]
    assert answer.candidates[0].host == "dro.dur.ac.uk"
    assert answer.candidates[0].license == "cc-by"


def test_one_location_is_not_offered_twice() -> None:
    # The journal location is both `best_oa_location` and the first entry of
    # `locations`. Two attempts at one link would spend the cap of 3 on it.
    assert len(resolve(RECORDED_WORK).candidates) == 2


def test_a_journal_pdf_is_a_candidate() -> None:
    # The rule this reverses refused 7 open PDF links at journals in the pool
    # of 2026-10-09, and OpenAlex states a cc-by licence for 5 of them.
    answer = resolve(work(location("https://www.mdpi.com/eee.pdf")))

    assert urls(answer) == ["https://www.mdpi.com/eee.pdf"]
    assert answer.candidates[0].license == "cc-by"


def test_candidates_keep_the_openalex_order_inside_one_rank() -> None:
    # No licence sort and no known good host sort. 4 of the 18 open PDF links
    # of the measured pool state no licence, and one of those gave 75,457
    # characters of Usable text.
    answer = resolve(
        work(
            location("https://eprints.whiterose.ac.uk/fff.pdf", kind="repository", rights=None),
            location("https://serval.unil.ch/fff.pdf", kind="repository"),
        )
    )

    assert urls(answer) == [
        "https://eprints.whiterose.ac.uk/fff.pdf",
        "https://serval.unil.ch/fff.pdf",
    ]


def test_the_best_location_wins_when_it_is_a_repository() -> None:
    answer = resolve(work(best=location("https://arxiv.org/pdf/2201.00001", kind="repository")))

    assert answer.candidates[0].url == "https://arxiv.org/pdf/2201.00001"
    assert answer.candidates[0].host == "arxiv.org"


def test_a_blocklisted_link_is_dropped_and_the_rest_stay() -> None:
    answer = resolve(
        work(
            location("https://doi.org/10.1000/hhh"),
            location("https://discovery.ucl.ac.uk/hhh.pdf", kind="repository"),
        )
    )

    assert urls(answer) == ["https://discovery.ucl.ac.uk/hhh.pdf"]
    assert answer.reason == ""


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        # A found record with no file is a fact about the Paper, and the reason
        # table counts it apart from a Paper OpenAlex never heard of.
        (
            work(
                location(
                    landing_page_url="https://www.sciencedirect.com/ccc", is_oa=False, rights=None
                )
            ),
            reasons.NO_OPEN_LOCATION,
        ),
        # Issue 16 is closed, so nothing follows a landing page to its file.
        (
            work(
                location(
                    kind="repository",
                    rights="cc-by-nc",
                    landing_page_url="https://www.research.ed.ac.uk/ddd",
                )
            ),
            reasons.NO_PDF_LINK,
        ),
        # One Paper of the measured pool names exactly one PDF link, and it is
        # a doi.org address. doi.org holds no file, so nothing is left to try.
        (
            work(
                location("https://doi.org/10.1000/ggg"),
                location("https://doaj.org/article/ggg.pdf", kind="repository", rights="cc-by-sa"),
            ),
            reasons.BLOCKLISTED_ONLY,
        ),
    ],
)
def test_a_work_with_no_candidate_says_why(reply: dict, expected: str) -> None:
    answer = resolve(reply)

    assert answer.found is True
    assert answer.candidates == ()
    assert answer.reason == expected


def test_an_open_location_with_no_link_at_all_is_still_open() -> None:
    # OpenAlex calls this location open, so the Paper is not closed. The
    # reason table must not read it as a Paper with no open copy anywhere.
    reply = work({"is_oa": True, "source": {"type": "repository"}})

    assert open_candidates(reply) == []
    assert reason_for_no_candidate(reply) == reasons.NO_PDF_LINK


def test_an_unknown_identifier_is_not_found() -> None:
    answer = resolve(None, doi="10.1000/nothing", status=404)

    assert answer.found is False
    assert answer.candidates == ()


def test_every_answer_is_cached() -> None:
    calls: list = []
    resolver = OpenAlex(client=client_that_returns(200, RECORDED_WORK, calls))
    resolver.resolve("10.1000/aaa")
    resolver.resolve("10.1000/aaa")
    assert len(calls) == 1

    # A 404 is an answer too, so a second lookup must not ask again.
    missing: list = []
    absent = OpenAlex(client=client_that_returns(404, None, missing))
    absent.resolve("10.1000/nothing")
    absent.resolve("10.1000/nothing")
    assert len(missing) == 1


def test_the_request_carries_the_contact_email() -> None:
    # Identify Fynd and its operator in the request, as required by ADR 0007.
    calls: list = []
    resolve(RECORDED_WORK, calls=calls)

    request = calls[0]
    assert request.url.params["mailto"] == "deshan@example.org"
    assert "deshan@example.org" in request.headers["user-agent"]
    assert "Fynd" in request.headers["user-agent"]


def test_a_broken_reply_stops_with_a_sentence() -> None:
    with pytest.raises(WorkNotRead):
        resolve(None, status=500)


def test_a_broken_reply_is_not_cached() -> None:
    with pytest.raises(WorkNotRead):
        resolve(None, status=500)

    calls: list = []
    answer = resolve(RECORDED_WORK, calls=calls)

    assert len(calls) == 1
    assert answer.found is True


def test_a_missing_contact_email_stops_the_lookup(monkeypatch) -> None:
    monkeypatch.delenv("FYND_CONTACT_EMAIL", raising=False)
    calls: list = []

    with pytest.raises(ContactEmailMissing):
        resolve(RECORDED_WORK, calls=calls)
    assert calls == []


def test_an_identifier_with_a_hash_is_escaped() -> None:
    # A doi with a `#` or a `?` in it ends the URL path early. The request then
    # asks about a different work, whose file is measured as this one.
    calls: list = []
    resolve(RECORDED_WORK, doi="10.1000/a#b?c=1", calls=calls)

    asked = str(calls[0].url)
    assert "10.1000%2Fa%23b%3Fc%3D1" in asked
    assert asked.count("#") == 0


def test_the_blocklist_reads_a_host_in_any_spelling() -> None:
    # doaj.org answered 2 fetches with a 403 on 2026-10-09. The same index
    # under `www.` is the same index.
    assert holds_no_file("https://doaj.org/article/aaa.pdf") is True
    assert holds_no_file("https://www.doaj.org/article/aaa.pdf") is True
    assert holds_no_file("https://DOI.org/10.1000/aaa") is True
    assert holds_no_file("https://discovery.ucl.ac.uk/aaa.pdf") is False
