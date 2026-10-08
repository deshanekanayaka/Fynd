"""Stage 1 offers a closed set of Domains, and refuses anything else."""

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


def test_accept_domain_refuses_a_cut_domain() -> None:
    # ADR 0009 cut Healthcare. A caller that still sends it gets a refusal.
    assert accept_domain("healthcare", offer_domains()) == DomainNotOffered(pick="healthcare")


def test_accept_domain_refuses_an_empty_pick() -> None:
    assert accept_domain("", offer_domains()) == DomainNotOffered(pick="")


def test_accept_domain_refuses_a_domain_this_project_was_not_offered() -> None:
    # The gate reads the saved offered list, not the constant in the file. This
    # is the test that proves it.
    assert accept_domain("energy", ["technology"]) == DomainNotOffered(pick="energy")


def test_accept_domain_compares_exactly() -> None:
    assert accept_domain("Energy", offer_domains()) == DomainNotOffered(pick="Energy")
