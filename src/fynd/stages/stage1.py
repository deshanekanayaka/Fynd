"""Stage 1: the student picks a Domain.

ADR 0006 gives every Stage two jobs and no saving. The runner writes the rows.
"""

from dataclasses import dataclass
from typing import Final

# ADR 0009 cut Healthcare. The `project` check constraint holds the same two.
SEEDED_DOMAINS: Final = ("technology", "energy")


@dataclass(frozen=True)
class DomainKept:
    """Stage 1 kept the picked Domain."""

    domain: str


@dataclass(frozen=True)
class DomainNotOffered:
    """Stage 1 refused the Pick, because it was not in the offered list."""

    # The refused value travels with the answer, because the route puts it in
    # the 4xx message it sends back.
    pick: str


# What `accept_domain` returns. One class for each answer, so no answer carries
# a field that means nothing.
DomainDecision = DomainKept | DomainNotOffered


def offer_domains() -> list[str]:
    """Return the Domains the student chooses from."""
    # A new list every call, so a caller that edits it cannot edit the constant.
    return list(SEEDED_DOMAINS)


def accept_domain(pick: str, offered: list[str]) -> DomainDecision:
    """Keep the Pick when it is in `offered`, and refuse it when it is not.

    `offered` is the list the runner saved for this Project, and never a list
    the caller sent, because the secret link is the only access control.
    """
    for domain in offered:
        # Exact comparison. Repairing the case would hide a real mismatch
        # between what Fynd offered and what came back.
        if domain == pick:
            return DomainKept(domain=domain)
    return DomainNotOffered(pick=pick)
