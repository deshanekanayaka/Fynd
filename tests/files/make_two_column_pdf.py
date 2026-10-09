"""Builds the two column PDF the extraction tests read.

Run it from the repository root to rebuild the file:

    uv run python tests/files/make_two_column_pdf.py

The file is written by hand, with no library, for two reasons. Deshan owns every
byte of it, so the public repository carries no licensing question. The text is
also plain enough that a reader of a failing test can see what the extractor
was supposed to return.
"""

import pathlib
from typing import Final

OUTPUT: Final = pathlib.Path(__file__).with_name("two-column-paper.pdf")

# Each page holds two columns. The reading order is the whole left column, then
# the whole right column, which is what a human reads and what the test asks
# the extractor to produce.
PAGES: Final = [
    {
        "left": [
            "1 Introduction",
            "Household energy demand in the",
            "United Kingdom rose for three years.",
        ],
        "right": [
            "2 Method",
            "We fit a model to half hourly meter",
            "readings from 400 homes.",
        ],
    },
    {
        "left": [
            "3 Results",
            "The model beats the seasonal naive",
            "baseline by 14 percent.",
        ],
        "right": [
            "4 Conclusion",
            "A cheap model serves a household",
            "without a smart meter.",
        ],
    },
]

PAGE_WIDTH: Final = 612
PAGE_HEIGHT: Final = 792
LEFT_COLUMN_X: Final = 60
RIGHT_COLUMN_X: Final = 330
FIRST_LINE_Y: Final = 700
LINE_HEIGHT: Final = 18
FONT_SIZE: Final = 11


def content_stream(page: dict[str, list[str]]) -> str:
    """Returns the PDF drawing commands for one page."""
    parts = ["BT", f"/F1 {FONT_SIZE} Tf"]
    for column, x in (("left", LEFT_COLUMN_X), ("right", RIGHT_COLUMN_X)):
        y = FIRST_LINE_Y
        for line in page[column]:
            # Td moves the text position in absolute page coordinates, so each
            # line is placed where a two column layout would put it.
            parts.append(f"1 0 0 1 {x} {y} Tm")
            parts.append(f"({line}) Tj")
            y -= LINE_HEIGHT
    parts.append("ET")
    return "\n".join(parts)


def build() -> bytes:
    """Returns the bytes of the whole PDF."""
    objects: list[str] = []

    page_count = len(PAGES)
    # Object numbers: 1 catalog, 2 page tree, 3 font, then one page object and
    # one content object for each page.
    page_ids = [4 + index * 2 for index in range(page_count)]
    content_ids = [5 + index * 2 for index in range(page_count)]

    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for index, page in enumerate(PAGES):
        stream = content_stream(page)
        objects.append(
            "<< /Type /Page /Parent 2 0 R "
            f"/MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            "/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {content_ids[index]} 0 R >>"
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")

    start_of_table = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("latin-1")
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{start_of_table}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(out)


if __name__ == "__main__":
    OUTPUT.write_bytes(build())
    print(f"wrote {OUTPUT} with {OUTPUT.stat().st_size} bytes")
