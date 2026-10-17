# The Open copy of a Paper, by host

Measured on 2026-10-17 by `uv run python -m fynd.cli measure-open-copies`.
The pool is the Seeded Topic query `United Kingdom household energy forecasting`, limit 20, from 2022 onward.

The Evidence window applies, because the table says what stage 4 will really see.
The day 1 numbers in [ADR 0007](../adr/0007-the-open-copy-is-resolved-then-measured.md) came from a search with no window, so the two pools hold different Papers.

The fetched files are not in git. A reader runs the command again to get them. See [ADR 0011](../adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).

The previous run reached 5 of 20 Papers. The rule fix predicted 10. This run reached 5 of 20.

## By host

| Host | Links tried | Files received | Usable text | Share usable |
|---|---|---|---|---|
| eprints.whiterose.ac.uk | 1 | 1 | 1 | 100% |
| www.repository.cam.ac.uk | 1 | 1 | 1 | 100% |
| pmc.ncbi.nlm.nih.gov | 1 | 0 | 0 | 0% |
| journals.plos.org | 1 | 0 | 0 | 0% |
| researchonline.lshtm.ac.uk | 1 | 1 | 1 | 100% |
| pdpublishers.com | 1 | 1 | 1 | 100% |
| www.mdpi.com | 2 | 0 | 0 | 0% |
| ruj.uj.edu.pl | 1 | 0 | 0 | 0% |
| sro.sussex.ac.uk | 1 | 0 | 0 | 0% |
| www.sciencedirect.com | 1 | 0 | 0 | 0% |
| discovery.ucl.ac.uk | 1 | 0 | 0 | 0% |
| www.ijspe.com | 1 | 1 | 1 | 100% |

5 of 20 Papers reached Usable text, which is 25%.

10 Papers never reached a link, so no host row holds them. The reason table below says why.

## By reason

| Reason | Papers |
|---|---|
| `usable` | 5 |
| `no_doi` | 0 |
| `no_openalex_record` | 0 |
| `no_open_location` | 6 |
| `no_pdf_link` | 3 |
| `blocklisted_only` | 1 |
| `robots_refused` | 2 |
| `fetch_refused` | 3 |
| `not_a_pdf` | 0 |
| `text_too_short` | 0 |
| `text_not_textual` | 0 |
| `no_section_word` | 0 |

## By Paper

| Paper | Year | Host | Reason | Characters | Attempts |
|---|---|---|---|---|---|
| What Data Do You Really Need? Feature-Level Privacy Analysis for House | 2026 | no link | `no_open_location` | 0 | 0 |
| Deep Learning-Based Probabilistic Forecasting of Household Energy Cons | 2024 | no link | `no_open_location` | 0 | 0 |
| Social outcomes of energy use in the United Kingdom: Household energy  | 2023 | eprints.whiterose.ac.uk | `usable` | 75457 | 1 |
| What really matters to reduce the energy demand of household electroni | 2023 | www.repository.cam.ac.uk | `usable` | 60363 | 1 |
| Can household energy efficiency dampen crude oil price volatility in t | 2025 | journals.plos.org | `robots_refused` | 0 | 2 |
| Forecasting United Kingdom's energy consumption using machine learning | 2022 | no link | `no_open_location` | 0 | 0 |
| Understandings of ultra-processed foods among adults with responsibili | 2026 | researchonline.lshtm.ac.uk | `usable` | 89456 | 1 |
| A Comparative Evaluation of Statistical, Hybrid, and Deep Learning Mod | 2026 | pdpublishers.com | `usable` | 91205 | 1 |
| Energy and Climate Policy in a DSGE Model of the United Kingdom | 2024 | no link | `no_pdf_link` | 0 | 0 |
| Gathering baseline data to assess household energy interventions' impa | 2025 | no link | `no_pdf_link` | 0 | 0 |
| Multi-Step Ahead Natural Gas Consumption Forecasting Based on a Hybrid | 2022 | www.mdpi.com | `fetch_refused` | 0 | 1 |
| Timing of energy intake and ultra-processed food consumption are assoc | 2025 | no link | `no_open_location` | 0 | 0 |
| A Hybrid BERT-ELM Framework for Robust Time Series Forecasting of Sola | 2025 | no link | `blocklisted_only` | 0 | 0 |
| Renewable Energy and Load Demand Forecasting Using Multivariate Time S | 2025 | no link | `no_open_location` | 0 | 0 |
| Artificial Intelligence Governance and Cybersecurity Trust: A Comparat | 2026 | no link | `no_pdf_link` | 0 | 0 |
| Climate Change Adaptation through Renewable Energy: The Cases of Austr | 2024 | www.mdpi.com | `fetch_refused` | 0 | 1 |
| ‘We're going all out for shale:’ explaining shale gas energy policy fa | 2022 | www.sciencedirect.com | `fetch_refused` | 0 | 3 |
| On the Effectiveness of Smart Metering Technology Adoption: Evidence f | 2023 | no link | `no_open_location` | 0 | 0 |
| Performing energy justice futures: How visions of just futures shape d | 2024 | discovery.ucl.ac.uk | `robots_refused` | 0 | 1 |
| Helping the poor and the vulnerable with their energy bills during the | 2022 | www.ijspe.com | `usable` | 10113 | 1 |
