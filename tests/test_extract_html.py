"""The HTML extractor has to drop the page furniture and keep the numbers."""

import pathlib

import pytest

from fynd.extract import extract_html, read_html

FILES = pathlib.Path(__file__).parent / "files"


def page(name: str) -> bytes:
    return (FILES / f"{name}.html").read_bytes()


def test_a_product_page_loses_its_navigation_and_cookie_banner() -> None:
    answer = read_html(page("product-page"))

    assert "See where your energy goes" in answer.text
    assert "cookies" not in answer.text
    assert "Accept all" not in answer.text
    assert "Sign in" not in answer.text
    assert "Privacy" not in answer.text


def test_a_table_keeps_its_numbers() -> None:
    # A Statistic is a number, so a reader that drops a table drops the Claim.
    answer = read_html(page("statistics-table"))

    assert "3900" in answer.text
    assert "14200" in answer.text
    assert "Detached house" in answer.text


def test_the_structure_of_a_web_page_is_empty() -> None:
    # trafilatura returns headings with no character positions, and nothing
    # before the handover reads a section label.
    answer = read_html(page("product-page"))
    assert answer.structure == []
    assert answer.extractor.startswith("trafilatura ")


def test_a_statistics_article_gives_a_long_text() -> None:
    answer = read_html(page("ons-energy-efficiency"))
    assert len(answer.text) > 20000
    assert "energy efficiency" in answer.text.lower()


def test_a_statistics_release_page_gives_almost_nothing() -> None:
    # The measured finding of day 4. The numbers of this release live in a
    # spreadsheet behind a link, so the page holds under 2,000 characters and
    # the usable text checks must refuse it.
    answer = read_html(page("govuk-energy-consumption"))
    assert len(answer.text) < 3000


def test_a_page_with_no_article_gives_a_short_text() -> None:
    # trafilatura returns the little text that is there and never raises, so
    # the usable text checks are what refuses a page like this one.
    answer = read_html(b"<html><body><nav>Home</nav></body></html>")
    assert answer.text == "Home"


def test_a_second_extraction_reads_the_cache(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    data = page("product-page")
    first = extract_html(data)
    second = extract_html(data)

    assert first == second
    assert len(list(tmp_path.glob("extract-*.json"))) == 1


def test_the_two_extractors_do_not_share_a_cache_entry(tmp_path, monkeypatch) -> None:
    # The key holds the step and the extractor, so the same bytes read by two
    # libraries are two answers and never one.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    from fynd.extract import extract_pdf

    pdf = (FILES / "two-column-paper.pdf").read_bytes()
    extract_html(page("product-page"))
    extract_pdf(pdf)
    assert len(list(tmp_path.glob("extract-*.json"))) == 2


@pytest.mark.parametrize(
    "name", ["ons-energy-efficiency", "govuk-energy-consumption", "product-page"]
)
def test_every_saved_page_reads_without_raising(name: str) -> None:
    read_html(page(name))


def test_a_page_in_another_encoding_keeps_its_letters() -> None:
    # A decode to utf-8 with a replacement turns every accented letter into one
    # glyph that no check counts as ordinary.
    html = (
        '<html><head><meta charset="iso-8859-1"><title>Preise</title></head>'
        "<body><article><h1>Preise</h1>"
        "<p>Preis in Euro f\xfcr W\xe4rme und K\xe4lte in jedem Haushalt.</p>"
        "</article></body></html>"
    ).encode("iso-8859-1")

    answer = read_html(html)

    assert "für Wärme und Kälte" in answer.text
    assert "\ufffd" not in answer.text
