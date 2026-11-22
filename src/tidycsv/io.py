"""Reading CSVs whose encoding and delimiter are unknown."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")
DELIMITERS = ",;\t|"


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]]
    encoding: str
    delimiter: str


def detect_encoding(raw: bytes) -> str:
    for encoding in ENCODINGS:
        try:
            raw.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"  # never fails


def detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=DELIMITERS).delimiter
    except csv.Error:
        # Fall back to the delimiter that appears most often in the first line.
        first_line = sample.splitlines()[0] if sample else ""
        return max(DELIMITERS, key=first_line.count)


def read_table(path: Path) -> Table:
    raw = path.read_bytes()
    encoding = detect_encoding(raw)
    text = raw.decode(encoding)
    delimiter = detect_delimiter(text[:20_000])
    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    rows = [row for row in reader]
    if not rows:
        return Table(header=[], rows=[], encoding=encoding, delimiter=delimiter)
    header, *body = rows
    width = len(header)
    # Pad short rows and keep extra cells visible instead of silently dropping them.
    normalized = [row + [""] * (width - len(row)) if len(row) < width else row for row in body]
    return Table(header=header, rows=normalized, encoding=encoding, delimiter=delimiter)


def write_table(path: Path, header: list[str], rows: list[list[str]], delimiter: str = ",") -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(header)
        writer.writerows(rows)
