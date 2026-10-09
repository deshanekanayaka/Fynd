"""Turn the bytes of an Open copy into a Source text.

The Source text is the one exact string a Claim points into with two character
offsets, so this file produces the value every later guard depends on. See
ADR 0005 and ADR 0007.

An extractor returns the flat text plus the structure, which is the page spans.
It returns no offset map into the bytes, because a PDF holds no reading order,
so a byte position names no sentence.
"""

import io
from dataclasses import dataclass, field
from typing import Any, Final

import pdfplumber

from fynd import cache

# What separates one page from the next in the Source text. Two newlines, so a
# sentence never runs across a page break by accident.
PAGE_SEPARATOR: Final = "\n\n"

# Two columns is the normal shape of an energy paper, and the widest shape Fynd
# reads. A page with three columns gives one column of the three, which the
# measurement shows and a later day fixes.
MAX_COLUMNS: Final = 2

# The gutter test. Fynd looks for a vertical band with no words in it, inside
# the middle third of the page, and at least this wide in points. 18 points is
# about three characters, which is wider than any word space.
MIN_GUTTER_POINTS: Final = 18.0
GUTTER_SEARCH_START: Final = 0.33
GUTTER_SEARCH_END: Final = 0.67
GUTTER_STEP_POINTS: Final = 2.0

EXTRACT_SHAPE_VERSION: Final = 1


@dataclass(frozen=True)
class Span:
    """One labelled range of the Source text, held for display only."""

    kind: str
    label: str
    start: int
    end: int


@dataclass(frozen=True)
class Extracted:
    """The Source text of one Open copy, with the structure and the extractor."""

    text: str
    extractor: str
    structure: list[Span] = field(default_factory=list)


def extractor_name() -> str:
    """Returns the extractor and its version, for example `pdfplumber 0.11.4`."""
    # The name travels with the text, because a text hash says that the text
    # changed and nothing else says what changed it.
    return f"pdfplumber {pdfplumber.__version__}"


def crossing_words(words: list[dict[str, Any]], x: float) -> bool:
    """Says whether any word on the page crosses this vertical line."""
    for word in words:
        if word["x0"] < x < word["x1"]:
            return True
    return False


def words_on_both_sides(words: list[dict[str, Any]], x: float) -> bool:
    """Says whether words sit to the left of this line and to the right of it."""
    left = False
    right = False
    for word in words:
        if word["x1"] <= x:
            left = True
        elif word["x0"] >= x:
            right = True
    return left and right


def gutter_of(page: Any) -> float | None:
    """Returns the x of the gap between two columns, or None for one column.

    A two column page is read as a whole page by pdfplumber, which puts the
    first line of the left column and the first line of the right column on one
    line. A Claim quoted from such a line is nonsense, so the gap is found and
    each column is read on its own.
    """
    words = page.extract_words()
    if not words:
        return None

    # Walk the middle third of the page and keep the longest run of positions
    # that no word crosses. A plain loop, because the page is a few hundred
    # points wide and clarity matters more than speed here.
    start = page.width * GUTTER_SEARCH_START
    end = page.width * GUTTER_SEARCH_END
    best_run = (0.0, 0.0)
    run_start: float | None = None
    x = start
    while x <= end:
        if crossing_words(words, x):
            run_start = None
        else:
            if run_start is None:
                run_start = x
            if x - run_start > best_run[1] - best_run[0]:
                best_run = (run_start, x)
        x += GUTTER_STEP_POINTS

    width = best_run[1] - best_run[0]
    if width < MIN_GUTTER_POINTS:
        return None
    middle = (best_run[0] + best_run[1]) / 2
    if not words_on_both_sides(words, middle):
        return None
    return middle


def page_text(page: Any) -> str:
    """Returns the text of one page, one column at a time."""
    gutter = gutter_of(page)
    if gutter is None:
        return page.extract_text() or ""

    columns = []
    edges = [0.0, gutter, page.width]
    for index in range(MAX_COLUMNS):
        box = (edges[index], 0, edges[index + 1], page.height)
        text = page.crop(box).extract_text() or ""
        if text:
            columns.append(text)
    return "\n".join(columns)


def read_pdf(data: bytes) -> Extracted:
    """Turns PDF bytes into a Source text with one span for each page."""
    texts = []
    spans = []
    position = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page_text(page)
            texts.append(text)
            spans.append(
                Span(kind="page", label=str(number), start=position, end=position + len(text))
            )
            position += len(text) + len(PAGE_SEPARATOR)

    return Extracted(
        text=PAGE_SEPARATOR.join(texts),
        extractor=extractor_name(),
        structure=spans,
    )


def extract_pdf(data: bytes) -> Extracted:
    """Returns the Source text for these bytes, from the cache when possible.

    The key holds the hash of the bytes and the extractor with its version, so
    a new library version misses this cache and reads the stored bytes again.
    """
    parts = {
        "step": "extract-pdf",
        "bytes_sha256": cache.sha256_of(data),
        "extractor": extractor_name(),
        "shape": EXTRACT_SHAPE_VERSION,
    }
    key = cache.cache_key("extract", parts)
    stored = cache.read(key)
    if stored is None:
        answer = read_pdf(data)
        cache.write(
            key,
            parts,
            {
                "text": answer.text,
                "extractor": answer.extractor,
                "structure": [vars(span) for span in answer.structure],
            },
        )
        return answer

    return Extracted(
        text=str(stored.get("text") or ""),
        extractor=str(stored.get("extractor") or ""),
        structure=[Span(**span) for span in stored.get("structure") or []],
    )
