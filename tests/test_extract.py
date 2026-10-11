"""Extraction has to read a two column page in the order a human reads it."""

import pathlib

import pytest

from fynd import cache, extract
from fynd.extract import PAGE_SEPARATOR, extract_pdf, read_pdf

TWO_COLUMN_PDF = pathlib.Path(__file__).parent / "files" / "two-column-paper.pdf"
OFFSET_ORIGIN_PDF = pathlib.Path(__file__).parent / "files" / "offset-origin-paper.pdf"


@pytest.fixture
def pdf_bytes() -> bytes:
    return TWO_COLUMN_PDF.read_bytes()


def test_a_two_column_page_reads_down_one_column_then_the_other(pdf_bytes) -> None:
    # Plain pdfplumber returns "Household energy demand in the We fit a model",
    # which is one line of each column joined. A Claim quoted from that line
    # says something no author wrote.
    answer = read_pdf(pdf_bytes)

    assert "United Kingdom rose for three years." in answer.text
    assert "We fit a model to half hourly meter" in answer.text
    assert "in the We fit" not in answer.text
    assert answer.text.index("1 Introduction") < answer.text.index("2 Method")
    assert answer.text.index("United Kingdom rose") < answer.text.index("2 Method")


def test_the_page_spans_cover_the_text_with_no_gap(pdf_bytes) -> None:
    answer = read_pdf(pdf_bytes)

    assert len(answer.structure) == 2
    first, second = answer.structure
    assert first.kind == "page"
    assert first.label == "1"
    assert answer.text[first.start : first.end].startswith("1 Introduction")
    assert answer.text[second.start : second.end].startswith("3 Results")
    # The gap between two spans is the page separator and nothing else.
    assert answer.text[first.end : second.start] == PAGE_SEPARATOR
    assert second.end == len(answer.text)


def test_the_extractor_name_carries_its_version(pdf_bytes) -> None:
    answer = read_pdf(pdf_bytes)
    assert answer.extractor.startswith("pdfplumber ")
    assert answer.extractor != "pdfplumber "


def test_a_second_extraction_reads_the_cache(pdf_bytes, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    first = extract_pdf(pdf_bytes)
    second = extract_pdf(pdf_bytes)

    assert first == second
    assert len(list(tmp_path.glob("extract-*.json"))) == 1


def test_the_extraction_key_holds_the_bytes_and_the_extractor(
    pdf_bytes, tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    extract_pdf(pdf_bytes)
    stored = list(tmp_path.glob("extract-*.json"))[0]
    parts = cache.read_parts(stored.name)

    assert parts["bytes_sha256"] == cache.sha256_of(pdf_bytes)
    assert parts["extractor"].startswith("pdfplumber ")


class FakePage:
    """One page of words, which is all the gutter test reads."""

    def __init__(self, words: list[dict], width: float = 600.0) -> None:
        self.width = width
        self.height = 800.0
        self.words = words

    @property
    def bbox(self):
        return (0.0, 0.0, self.width, self.height)

    def extract_words(self) -> list[dict]:
        return self.words


def test_one_column_of_text_has_no_gutter() -> None:
    # A page whose lines run the whole width must never be cut in half, because
    # a cut mid sentence is worse than an interleaved two column page.
    words = [{"x0": 50.0, "x1": 550.0}, {"x0": 50.0, "x1": 540.0}]
    assert extract.gutter_of(FakePage(words)) is None


def test_a_wide_gap_in_the_middle_is_a_gutter() -> None:
    words = [{"x0": 50.0, "x1": 280.0}, {"x0": 320.0, "x1": 550.0}]
    gutter = extract.gutter_of(FakePage(words))
    assert gutter is not None
    assert 280.0 < gutter < 320.0


def test_a_narrow_word_space_is_not_a_gutter() -> None:
    # The gap here is 8 points, which is one word space and not a column break.
    words = [{"x0": 50.0, "x1": 296.0}, {"x0": 304.0, "x1": 550.0}]
    assert extract.gutter_of(FakePage(words)) is None


def test_a_page_with_no_words_has_no_gutter() -> None:
    assert extract.gutter_of(FakePage([])) is None


def test_a_page_whose_origin_is_not_zero_reads_the_same() -> None:
    # A real page box starts where it likes. A crop that assumes an origin of
    # zero raises, and one bad Paper then ends the whole measurement run.
    plain = read_pdf(TWO_COLUMN_PDF.read_bytes())
    offset = read_pdf(OFFSET_ORIGIN_PDF.read_bytes())

    assert offset.text == plain.text
    assert "in the We fit" not in offset.text


def test_a_two_column_page_with_an_offset_origin_finds_its_gutter() -> None:
    import pdfplumber

    with pdfplumber.open(OFFSET_ORIGIN_PDF) as pdf:
        page = pdf.pages[0]
        gutter = extract.gutter_of(page)

    assert gutter is not None
    # The words of the left column end at 20 + 275, and the right column starts
    # at 20 + 330, so the gap sits inside that band and not at the page middle.
    assert 295.0 < gutter < 350.0


class FakeOffsetPage(FakePage):
    """A page whose box starts at x of 100, as a real page box may."""

    @property
    def bbox(self):
        return (100.0, 0.0, 700.0, 800.0)


def test_the_gutter_band_follows_the_page_box() -> None:
    # Words sit from 150 to 380 and from 420 to 650, so the gap is near 400.
    # A band measured from the width alone would scan 198 to 402 and miss it.
    words = [{"x0": 150.0, "x1": 380.0}, {"x0": 420.0, "x1": 650.0}]
    gutter = extract.gutter_of(FakeOffsetPage(words))
    assert gutter is not None
    assert 380.0 < gutter < 420.0
