"""Extracts Source text from PDF and HTML bytes for
 the Open copy pipeline and CLI.

PDFs use pdfplumber; HTML uses trafilatura. The result holds the extracted
string, the library version, and PDF page ranges for display. Later Claims
must point into this exact string, not the original file bytes (ADR 0005).
"""

import io
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

import pdfplumber
import trafilatura

from fynd import cache

# Keep page boundaries visible instead of joining their text directly.
PAGE_SEPARATOR: Final = "\n\n"

# The split supports two columns; other counts would need different crop boundaries.
MAX_COLUMNS: Final = 2

# Require an 18-point gap to avoid mistaking ordinary word spacing for a column break.
MIN_GUTTER_POINTS: Final = 18.0
GUTTER_SEARCH_START: Final = 0.33
GUTTER_SEARCH_END: Final = 0.67
GUTTER_STEP_POINTS: Final = 2.0

# Bump this when our extraction rules or stored result shape change.
EXTRACT_SHAPE_VERSION: Final = 1


@dataclass(frozen=True)
class Span:
    """A labelled character range in Source text, used for display."""

    kind: str
    label: str
    start: int
    end: int


@dataclass(frozen=True)
class Extracted:
    """Extracted Source text with its library version and display ranges."""

    text: str
    extractor: str
    structure: list[Span] = field(default_factory=list)


class Reader(Protocol):
    """A supplied function that converts bytes into an Extracted value."""

    def __call__(self, data: bytes) -> "Extracted": ...


def pdf_extractor_name() -> str:
    """Returns the installed PDF extraction library's name and version."""
    return f"pdfplumber {pdfplumber.__version__}"


def html_extractor_name() -> str:
    """Returns the installed HTML extraction library's name and version."""
    return f"trafilatura {trafilatura.__version__}"


def crossing_words(words: list[dict[str, Any]], x: float) -> bool:
    """Checks whether a word's bounding box crosses a vertical line."""
    for word in words:
        if word["x0"] < x < word["x1"]:
            return True
    return False


def words_on_both_sides(words: list[dict[str, Any]], x: float) -> bool:
    """Checks for words on both sides of a proposed column split."""
    left = False
    right = False
    for word in words:
        if word["x1"] <= x:
            left = True
        elif word["x0"] >= x:
            right = True
    return left and right


def gutter_of(page: Any) -> float | None:
    """Finds a likely column-gap position, or returns None when none qualifies."""
    words = page.extract_words()
    if not words:
        return None

    # Include the page origin because PDF coordinates do not always start at zero.
    left, _, right, _ = page.bbox
    width = right - left
    start = left + width * GUTTER_SEARCH_START
    end = left + width * GUTTER_SEARCH_END
    best_run = (0.0, 0.0)
    run_start: float | None = None
    x = start
    # Scan 33–67% of the page width in 2-point increments for the widest clear gap.
    while x <= end:
        if crossing_words(words, x):
            run_start = None
        else:
            if run_start is None:
                run_start = x
            if x - run_start > best_run[1] - best_run[0]:
                best_run = (run_start, x)
        x += GUTTER_STEP_POINTS

    if best_run[1] - best_run[0] < MIN_GUTTER_POINTS:
        return None
    middle = (best_run[0] + best_run[1]) / 2
    # A clear margin is not a column gap unless text sits on both sides.
    if not words_on_both_sides(words, middle):
        return None
    return middle


def page_text(page: Any) -> str:
    """Reads a page whole or as left and right columns when a gap is found."""
    gutter = gutter_of(page)
    if gutter is None:
        return page.extract_text() or ""

    columns = []
    left, top, right, bottom = page.bbox
    edges = [left, gutter, right]
    # Read down the left column before the right to avoid interleaving sentences.
    for index in range(MAX_COLUMNS):
        # Use actual page coordinates so cropping also works with a nonzero origin.
        box = (edges[index], top, edges[index + 1], bottom)
        text = page.crop(box).extract_text() or ""
        if text:
            columns.append(text)
    return "\n".join(columns)


def read_pdf(data: bytes) -> Extracted:
    """Reads PDF bytes into Source text with a display span for each page."""
    texts = []
    spans = []
    position = 0
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for number, page in enumerate(pdf.pages, start=1):
            text = page_text(page)
            texts.append(text)
            spans.append(
                Span(
                    kind="page",
                    label=str(number),
                    start=position,
                    end=position + len(text),
                )
            )
            # Count the two-newline separator so the next page's offsets stay correct.
            position += len(text) + len(PAGE_SEPARATOR)

    return Extracted(
        text=PAGE_SEPARATOR.join(texts),
        extractor=pdf_extractor_name(),
        structure=spans,
    )


def read_html(data: bytes) -> Extracted:
    """Extracts main text and table values from HTML bytes, without display spans."""
    # Pass bytes so trafilatura can detect encoding instead of assuming UTF-8.
    text = trafilatura.extract(data, output_format="txt", include_tables=True)
    # No HTML character ranges are produced by this extraction path.
    return Extracted(text=text or "", extractor=html_extractor_name(), structure=[])


def cached_extraction(
    step: str, data: bytes, extractor: str, reader: Reader
) -> Extracted:
    """Reuses cached extraction or calls the supplied reader and saves its result."""
    # Changed bytes or library versions must not reuse text with different offsets.
    parts = {
        "step": step,
        "bytes_sha256": cache.sha256_of(data),
        "extractor": extractor,
        "shape": EXTRACT_SHAPE_VERSION,
    }
    key = cache.cache_key("extract", parts)
    stored = cache.read(key)
    if stored is None:
        answer = reader(data)
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


def extract_pdf(data: bytes) -> Extracted:
    """Returns the Source text of a PDF, from the cache when possible."""
    return cached_extraction("extract-pdf", data, pdf_extractor_name(), read_pdf)


def extract_html(data: bytes) -> Extracted:
    """Returns the Source text of a web page, from the cache when possible."""
    return cached_extraction("extract-html", data, html_extractor_name(), read_html)
