"""Summarises Open copy pipeline results as Markdown measurement tables.

The CLI supplies each Paper's retained outcome and a count of dropped runs.
This file counts hosts, reasons, and Usable text, then formats a report and
its dated index link. The CLI writes those strings to docs/measurements.
"""

import datetime as dt
from typing import Final

from fynd import reasons
from fynd.open_copy import OpenCopyResult

# Keep results without a location distinct from real hosts in report counts.
NO_HOST: Final = "no link"

# Supply the heading when the measurement index does not exist yet.
README_HEADER: Final = (
    "# The measurement runs",
    "",
    "One line for each live measurement run, oldest first.",
    "",
)

# Distinct filename prefixes keep the two report types separate on the same date.
OPEN_COPY_STEM: Final = "open-copy-hosts"
RETRIEVAL_STEM: Final = "retrieval-table"


def readme_line(today: dt.date, stem: str) -> str:
    """Formats a dated report link for the measurement index."""
    return f"- [{today.isoformat()}]({stem}-{today.isoformat()}.md)"


def readme_with(existing: str, today: dt.date, stem: str) -> str:
    """Appends a report link to the index text unless that link already exists."""
    lines = list(README_HEADER) if not existing else existing.splitlines()
    line = readme_line(today, stem)
    # Repeated runs of one report type and date should not duplicate its link.
    if line not in lines:
        lines.append(line)
    return "\n".join(lines) + "\n"


def host_of_result(result: OpenCopyResult) -> str:
    """Returns the retained result's host, or the no-link marker."""
    if result.open_copy is None:
        return NO_HOST
    return result.open_copy.host or NO_HOST


def host_rows(results: list[OpenCopyResult]) -> list[dict[str, object]]:
    """Counts candidate attempts and retained file/text outcomes by host."""
    rows: dict[str, dict[str, object]] = {}

    def row_for(host: str) -> dict[str, object]:
        """Returns a host's counters, creating them when needed."""
        if host not in rows:
            rows[host] = {"host": host, "tried": 0, "files": 0, "usable": 0}
        return rows[host]

    for result in results:
        # Count every candidate attempt, not just the one whose outcome was retained.
        for host in result.tried_hosts or (host_of_result(result),):
            row = row_for(host or NO_HOST)
            row["tried"] = int(row["tried"]) + 1
        answered = row_for(host_of_result(result))
        # A result retains only one extracted file, not a full download history.
        if result.extracted is not None:
            answered["files"] = int(answered["files"]) + 1
        if result.is_usable:
            answered["usable"] = int(answered["usable"]) + 1
    return list(rows.values())


def reason_counts(results: list[OpenCopyResult]) -> dict[str, int]:
    """Counts retained reasons, starting every configured reason at zero."""
    counts = {reason: 0 for reason in reasons.ALL}
    for result in results:
        counts[result.reason] = counts.get(result.reason, 0) + 1
    return counts


def share(part: int, whole: int) -> str:
    """Formats a rounded percentage, or a dash for a zero denominator."""
    if whole == 0:
        return "-"
    return f"{round(100 * part / whole)}%"


def report(
    results: list[OpenCopyResult],
    query: str,
    year_from: int,
    limit: int,
    today: dt.date,
    dropped: int = 0,
    previous: int | None = None,
    predicted: int | None = None,
) -> str:
    """Formats the host, reason, and Paper tables with run metadata."""
    # Include dropped runs so failures cannot inflate the overall success share.
    total = len(results) + dropped
    usable_total = sum(1 for result in results if result.is_usable)

    lines = [
        "# The Open copy of a Paper, by host",
        "",
        f"Measured on {today.isoformat()} by `uv run python -m fynd.cli measure-open-copies`.",
        f"The pool is the Seeded Topic query `{query}`, limit {limit}, from {year_from} onward.",
        "",
        "The Evidence window applies, because the table says what stage 4 will really see.",
        "The day 1 numbers in [ADR 0007](../adr/0007-the-open-copy-is-resolved-then-measured.md) "
        "came from a search with no window, so the two pools hold different Papers.",
        "",
        "The fetched files are not in git. A reader runs the command again to get them. "
        "See [ADR 0011](../adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).",
    ]
    # Print the optional comparison only when both prior and predicted counts exist.
    if previous is not None and predicted is not None:
        lines += [
            "",
            f"The previous run reached {previous} of {limit} Papers. The rule fix predicted "
            f"{predicted}. This run reached {usable_total} of {total}.",
        ]
    lines += [
        "",
        "## By host",
        "",
        "| Host | Links tried | Files received | Usable text | Share usable |",
        "|---|---|---|---|---|",
    ]
    for row in host_rows(results):
        if row["host"] == NO_HOST:
            # A missing location is not a host that received a failed request.
            continue
        tried = int(row["tried"])
        files = int(row["files"])
        usable = int(row["usable"])
        lines.append(f"| {row['host']} | {tried} | {files} | {usable} | {share(usable, tried)} |")

    lines += [
        "",
        f"{usable_total} of {total} Papers reached Usable text, which is "
        f"{share(usable_total, total)}.",
    ]
    if dropped:
        lines.append("")
        lines.append(
            f"{dropped} Papers are missing from the tables below. Their run broke with a "
            "rate limit or a timeout, which is a failure and not an answer, so nothing of "
            "it is cached and no row names a reason."
        )
    no_link = sum(1 for result in results if result.open_copy is None)
    lines += [
        "",
        f"{no_link} Papers never reached a link, so no host row holds them. "
        "The reason table below says why.",
    ]

    lines += [
        "",
        "## By reason",
        "",
        "| Reason | Papers |",
        "|---|---|",
    ]
    counts = reason_counts(results)
    for reason in reasons.ALL:
        lines.append(f"| `{reason}` | {counts[reason]} |")

    lines += [
        "",
        "## By Paper",
        "",
        "| Paper | Year | Host | Reason | Characters | Attempts |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        characters = len(result.extracted.text) if result.extracted is not None else 0
        # A title's pipe character would otherwise create an extra Markdown column.
        title = result.paper.title.replace("|", " ")
        year = result.paper.year if result.paper.year is not None else "-"
        lines.append(
            f"| {title[:70]} | {year} | {host_of_result(result)} | "
            f"`{result.reason}` | {characters} | {result.attempts} |"
        )

    lines.append("")
    return "\n".join(lines)
