"""Count what the Open copy pipeline produced, and write the published table.

Every number Fynd publishes lives under `docs/measurements`, and one command
anyone runs produces it. That is the difference between a number and a claim.
See ADR 0007.
"""

import datetime as dt
from typing import Final

from fynd import reasons
from fynd.open_copy import OpenCopyResult

# The host a row gets when a Paper never reached a link. Such a Paper is left
# out of the host table and counted in one sentence below it, because no link
# was tried for it.
NO_HOST: Final = "no link"


def host_of_result(result: OpenCopyResult) -> str:
    """Returns the host a result belongs to in the host table."""
    if result.open_copy is None:
        return NO_HOST
    return result.open_copy.host or NO_HOST


def host_rows(results: list[OpenCopyResult]) -> list[dict[str, object]]:
    """Counts the links tried, the files received, and the texts that passed."""
    # A plain dictionary of counters, one entry for each host, built in the
    # order the hosts first appear.
    rows: dict[str, dict[str, object]] = {}
    for result in results:
        host = host_of_result(result)
        if host not in rows:
            rows[host] = {"host": host, "tried": 0, "files": 0, "usable": 0}
        row = rows[host]
        row["tried"] = int(row["tried"]) + 1
        if result.extracted is not None:
            row["files"] = int(row["files"]) + 1
        if result.is_usable:
            row["usable"] = int(row["usable"]) + 1
    return list(rows.values())


def reason_counts(results: list[OpenCopyResult]) -> dict[str, int]:
    """Counts every reason in `reasons.ALL`, including the ones at zero."""
    counts = {reason: 0 for reason in reasons.ALL}
    for result in results:
        counts[result.reason] = counts.get(result.reason, 0) + 1
    return counts


def share(part: int, whole: int) -> str:
    """Returns a share as a percentage, or a dash when nothing was tried."""
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
) -> str:
    """Returns the whole measurement file as one string.

    `limit` is the size of the searched pool, and `dropped` is the number of
    Papers whose run broke, so the denominator is the pool and never the rows
    that survived.
    """
    lines = [
        "# The Open copy of a Paper, by host",
        "",
        f"Measured on {today.isoformat()} by `uv run python -m fynd.cli measure-open-copies`.",
        f"The pool is the Seeded Topic query `{query}`, limit {limit}, "
        f"from {year_from} onward.",
        "",
        "The Evidence window applies, because the table says what stage 4 will really see.",
        "The day 1 numbers in [ADR 0007](../adr/0007-the-open-copy-is-resolved-then-measured.md) "
        "came from a search with no window, so the two pools hold different Papers.",
        "",
        "The fetched files are not in git. A reader runs the command again to get them. "
        "See [ADR 0011](../adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).",
        "",
        "## By host",
        "",
        "| Host | Links tried | Files received | Usable text | Share usable |",
        "|---|---|---|---|---|",
    ]
    for row in host_rows(results):
        if row["host"] == NO_HOST:
            # No link was tried for these Papers, so a row of links would read
            # as a host that refused 10 fetches it never received.
            continue
        tried = int(row["tried"])
        files = int(row["files"])
        usable = int(row["usable"])
        lines.append(f"| {row['host']} | {tried} | {files} | {usable} | {share(usable, tried)} |")

    total = len(results) + dropped
    usable_total = sum(1 for result in results if result.is_usable)
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
        "| Paper | Year | Host | Reason | Characters |",
        "|---|---|---|---|---|",
    ]
    for result in results:
        characters = len(result.extracted.text) if result.extracted is not None else 0
        title = result.paper.title.replace("|", " ")
        year = result.paper.year if result.paper.year is not None else "-"
        lines.append(
            f"| {title[:70]} | {year} | {host_of_result(result)} | "
            f"`{result.reason}` | {characters} |"
        )

    lines.append("")
    return "\n".join(lines)
