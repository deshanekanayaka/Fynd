"""The checks that decide whether a Source text is Usable text.

Usable text is a Source text that passes the checks, so Fynd reads Claims from
it. Two checks ship today. The third check of ADR 0007, which looks for a
section word, waits for the first measurement, because a threshold tuned on no
data drops a good file in silence.
"""

from typing import Final

from fynd import reasons

# A starting value, replaced by the first measurement. A real paper runs to
# tens of thousands of characters, and a cookie page runs to a few hundred.
MIN_CHARACTERS: Final = 3000

# The share of characters that must be ordinary. A PDF that extracted badly
# comes back full of control characters and private use glyphs.
MIN_ORDINARY_SHARE: Final = 0.80

# What counts as ordinary beside a letter, a digit, and a space.
ORDINARY_PUNCTUATION: Final = ".,;:!?'\"()[]{}<>-–—/\\|%&@#£$€+=*^~`_"


def is_ordinary(character: str) -> bool:
    """Says whether one character belongs in a readable text."""
    if character.isalnum() or character.isspace():
        return True
    return character in ORDINARY_PUNCTUATION


def ordinary_share(text: str) -> float:
    """Returns the share of characters that belong in a readable text."""
    if not text:
        return 0.0
    # A plain loop over the text. The longest Source text is a few hundred
    # thousand characters, which costs a fraction of one extraction.
    ordinary = 0
    for character in text:
        if is_ordinary(character):
            ordinary += 1
    return ordinary / len(text)


def reason_against(text: str) -> str:
    """Returns the reason this text is not usable, or an empty string.

    An empty answer means the text is Usable text.
    """
    if len(text) < MIN_CHARACTERS:
        return reasons.TEXT_TOO_SHORT
    if ordinary_share(text) < MIN_ORDINARY_SHARE:
        return reasons.TEXT_NOT_TEXTUAL
    return ""
