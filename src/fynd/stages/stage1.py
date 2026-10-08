"""Stage 1: the student picks a Domain.

Two named jobs, as ADR 0006 requires. `offer_domains` produces what the student
chooses from, and `accept_domain` refuses a Pick the Stage never offered. The
runner does every save, so nothing here touches the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# The two Domains of version 1. ADR 0009 cut Healthcare, and the check
# constraint on the `project` table holds these same two values.
SEEDED_DOMAINS = ("technology", "energy")


@dataclass(frozen=True)
class DomainVerdict:
    """What `accept_domain` decided about one Pick.

    A verdict is a value and not an exception, because "the Stage never offered
    this" is an answer the caller has to turn into a 4xx reply. A frozen
    dataclass means nobody edits the decision after the Stage returned it.
    """

    kind: Literal["kept", "not_offered"]
    domain: str = ""


def offer_domains() -> list[str]:
    """Return the Domains the student chooses from.

    Stage 1 offers a closed set, so no model and no search is involved. A new
    list is built on every call, because a caller that edits the returned list
    must not be able to edit the constant behind it.
    """
    return list(SEEDED_DOMAINS)


def accept_domain(pick: str, offered: list[str]) -> DomainVerdict:
    """Decide whether the Pick is one of the Domains this Stage offered.

    The `offered` list is the one the runner saved for this Project, and never
    a list the caller sent with the Pick. The secret link is the only access
    control, so a caller can send any value it likes.

    The comparison is exact. The student sends back one of the values Fynd
    offered, so a quiet repair of the case would hide a real mismatch.
    """
    for domain in offered:
        if domain == pick:
            return DomainVerdict(kind="kept", domain=domain)
    return DomainVerdict(kind="not_offered")
