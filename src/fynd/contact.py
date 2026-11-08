"""Builds contact details for OpenAlex lookups and file downloads.

OpenAlex and the fetcher use these helpers to identify Fynd and its operator
in requests. The CLI checks the address before starting work that needs it.
The address comes from the environment rather than committed code (ADR 0007).
"""

import os
from typing import Final

CONTACT_VARIABLE: Final = "FYND_CONTACT_EMAIL"

REPOSITORY_URL: Final = "https://github.com/deshanekanayaka/Fynd"


class ContactEmailMissing(Exception):
    """Raised when the operator email is missing or blank."""


def contact_email() -> str:
    """Returns the configured operator email, rejecting missing or blank values."""
    # Require an explicit address so requests never identify an unrelated default operator.
    address = os.environ.get(CONTACT_VARIABLE, "").strip()
    if not address:
        raise ContactEmailMissing(
            f"Set {CONTACT_VARIABLE} in your .env file. OpenAlex and file-fetching "
            "requests need an operator address so a host administrator can contact you."
        )
    return address


def user_agent() -> str:
    """Builds the User-Agent used by OpenAlex and the fetcher."""
    return f"Fynd/0.1 (+{REPOSITORY_URL}; {contact_email()})"
