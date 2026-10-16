# The files the extraction tests read

Every file here is a test input. Two are saved web pages, and three are written by hand. The licence of each one is below, because the repository is public and [ADR 0011](../../docs/adr/0011-the-public-repository-holds-the-text-and-not-the-files.md) keeps content Fynd has no right to republish out of git.

| File | Where it comes from | Licence |
|---|---|---|
| `two-column-paper.pdf` | `make_two_column_pdf.py` beside it | Deshan owns it |
| `product-page.html` | Written by hand on 2026-10-09 | Deshan owns it |
| `statistics-table.html` | Written by hand on 2026-10-09 | Deshan owns it |
| `ons-energy-efficiency.html` | Office for National Statistics, saved 2026-10-09 | Open Government Licence v3.0, stated in the page |
| `govuk-energy-consumption.html` | Department for Energy Security and Net Zero on gov.uk, saved 2026-10-09 | Open Government Licence v3.0, stated in the page |
| `pool-2026-10-09.json` | The cached Semantic Scholar search of 2026-10-09 | Facts about 20 Papers, and no abstract |

The two saved pages carry the Open Government Licence, which allows a copy with an attribution. The attribution is the table above.

## Why the Product page is written and not saved

The design round of day 4 asked for one real commercial product page. A commercial page is copyright of its owner, and a copy of it in a public repository is the redistribution that ADR 0011 refuses for a publisher PDF. So `product-page.html` is written by hand with the parts that matter to the test, which are a cookie banner, a navigation list, marketing copy, and a footer.

## What the two real pages are for

`ons-energy-efficiency.html` is a statistics article that gives 31,415 characters of text. It is the good case.

`govuk-energy-consumption.html` is a statistics release page that gives 1,898 characters. The numbers live in a spreadsheet behind a link, so the page itself holds almost nothing. It is the case the usable text checks exist to catch.

## Why the pool file holds no abstract

`pool-2026-10-09.json` is the 20 Papers of the Seeded Topic run of 2026-10-09,
with the identifier, the title, the year, the digital object identifier and the
Semantic Scholar link of each one. The abstracts stay out, because [ADR 0011](../../docs/adr/0011-the-public-repository-holds-the-text-and-not-the-files.md)
keeps the Semantic Scholar replies out of git for that reason. A title and an
identifier are facts about a Paper, and the test needs nothing more.
