"""Stage 1 offers a closed set of Domains, and refuses anything else."""

import pytest

from fynd.stages.stage1 import DomainKept, DomainNotOffered, accept_domain, offer_domains


def test_offer_domains_returns_the_two_seeded_domains() -> None:
    assert offer_domains() == ["technology", "energy"]


def test_offer_domains_returns_a_fresh_list_each_call() -> None:
    # A caller that edits the list must not change what the next Project sees.
    first = offer_domains()
    first.append("healthcare")
    assert offer_domains() == ["technology", "energy"]


def test_accept_domain_keeps_an_offered_domain() -> None:
    assert accept_domain("energy", offer_domains()) == DomainKept(domain="energy")


@pytest.mark.parametrize(
    ("pick", "offered"),
    [
        # ADR 0009 cut Healthcare. A caller that still sends it gets a refusal.
        ("healthcare", None),
        ("", None),
        # The comparison is exact, so a capital letter is a different word.
        ("Energy", None),
        # The gate reads the saved offered list, and not the constant in the
        # file. This is the case that proves it.
        ("energy", ["technology"]),
    ],
    ids=["a cut domain", "an empty pick", "a capital letter", "a domain this project never saw"],
)
def test_accept_domain_refuses_anything_the_project_was_not_offered(
    pick: str, offered: list[str] | None
) -> None:
    assert accept_domain(pick, offered or offer_domains()) == DomainNotOffered(pick=pick)
