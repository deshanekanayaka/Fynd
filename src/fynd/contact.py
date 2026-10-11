"""The operator address that every outbound request carries.

ADR 0007 asks for a user agent that names Fynd, the repository, and a human. A
repository administrator who sees an unknown program pulling files must be able
to find the operator. OpenAlex also serves a request with an email from a
faster queue.
"""

import os
from typing import Final

CONTACT_VARIABLE: Final = "FYND_CONTACT_EMAIL"

REPOSITORY_URL: Final = "https://github.com/deshanekanayaka/Fynd"


class ContactEmailMissing(Exception):
    """Raised when the operator address is not in the environment."""


def contact_email() -> str:
    """Returns the operator address, and raises when it is not set.

    Raises ContactEmailMissing when the variable is empty or absent.
    """
    # No default value. The repository is public, so an address in the source
    # is an address a scraper reads.
    address = os.environ.get(CONTACT_VARIABLE, "").strip()
    if not address:
        raise ContactEmailMissing(
            f"Set {CONTACT_VARIABLE} in your .env file. Every request Fynd makes "
            "names a human, so a repository administrator can reach the operator."
        )
    return address


def user_agent() -> str:
    """Returns the user agent for every outbound request."""
    return f"Fynd/0.1 (+{REPOSITORY_URL}; {contact_email()})"
