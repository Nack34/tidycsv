"""Pure cleaning functions: no I/O, easy to test."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

_NUMBER_AR = re.compile(r"^-?\$?\s?\d{1,3}(\.\d{3})+(,\d+)?$|^-?\$?\s?\d+,\d+$")
_NUMBER_US = re.compile(r"^-?\$?\s?\d{1,3}(,\d{3})+(\.\d+)?$|^-?\$?\s?\d+(\.\d+)?$")
_DATE_DMY = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")
_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NULL_TOKENS = {"", "na", "n/a", "null", "none", "-", "--", "s/d", "sin dato"}


def snake_case(name: str) -> str:
    """'Fecha de Alta (DD/MM)' -> 'fecha_de_alta_dd_mm'."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()
    return text or "column"


def unique_names(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for name in names:
        count = seen.get(name, 0)
        result.append(name if count == 0 else f"{name}_{count + 1}")
        seen[name] = count + 1
    return result


def is_null(value: str) -> bool:
    return value.strip().lower() in NULL_TOKENS


def parse_number(value: str) -> float | None:
    """Understands 1.234,56 (Argentina/Europe) and 1,234.56 (US). Returns None if it isn't a number."""
    text = value.strip().replace(" ", "")
    if _NUMBER_AR.match(text) and not _NUMBER_US.match(text):
        text = text.replace("$", "").replace(".", "").replace(",", ".")
    elif _NUMBER_US.match(text):
        text = text.replace("$", "").replace(",", "")
    else:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_date(value: str) -> date | None:
    """Day-first dates (25/12/2024, 1-3-2025) and ISO dates."""
    text = value.strip()
    if _DATE_ISO.match(text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    if m := _DATE_DMY.match(text):
        day, month, year = map(int, m.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def infer_type(values: list[str]) -> str:
    """'empty', 'integer', 'number', 'date' or 'text', looking at the non-null values."""
    present = [v for v in values if not is_null(v)]
    if not present:
        return "empty"
    if all(parse_date(v) for v in present):
        return "date"
    numbers = [parse_number(v) for v in present]
    if all(n is not None for n in numbers):
        return "integer" if all(float(n).is_integer() for n in numbers) else "number"
    return "text"


@dataclass
class CleanOptions:
    normalize_headers: bool = True
    trim: bool = True
    drop_empty_rows: bool = True
    drop_duplicates: bool = True
    standardize: bool = True  # numbers -> 1234.56, dates -> 2024-12-25, null tokens -> ""


@dataclass
class CleanReport:
    rows_in: int = 0
    rows_out: int = 0
    empty_rows_dropped: int = 0
    duplicates_dropped: int = 0
    cells_changed: int = 0
    column_types: dict[str, str] = field(default_factory=dict)


def _format_number(n: float) -> str:
    return str(int(n)) if n.is_integer() else repr(n)


def clean(
    header: list[str], rows: list[list[str]], options: CleanOptions | None = None
) -> tuple[list[str], list[list[str]], CleanReport]:
    opts = options or CleanOptions()
    report = CleanReport(rows_in=len(rows))
    new_header = unique_names([snake_case(h) for h in header]) if opts.normalize_headers else list(header)

    work = [[cell.strip() if opts.trim else cell for cell in row] for row in rows]
    report.cells_changed += sum(
        a != b for row, new in zip(rows, work, strict=True) for a, b in zip(row, new, strict=False)
    )

    if opts.drop_empty_rows:
        kept = [row for row in work if not all(is_null(c) for c in row)]
        report.empty_rows_dropped = len(work) - len(kept)
        work = kept

    if opts.drop_duplicates:
        seen: set[tuple[str, ...]] = set()
        unique = []
        for row in work:
            key = tuple(row)
            if key not in seen:
                seen.add(key)
                unique.append(row)
        report.duplicates_dropped = len(work) - len(unique)
        work = unique

    columns = list(zip(*work, strict=False)) if work else [() for _ in new_header]
    for name, values in zip(new_header, columns, strict=False):
        report.column_types[name] = infer_type(list(values))

    if opts.standardize:
        types = [report.column_types.get(name, "text") for name in new_header]
        for row in work:
            for i, cell in enumerate(row[: len(types)]):
                new = cell
                if is_null(cell):
                    new = ""
                elif types[i] in ("integer", "number"):
                    new = _format_number(parse_number(cell))  # type: ignore[arg-type]
                elif types[i] == "date":
                    new = parse_date(cell).isoformat()  # type: ignore[union-attr]
                if new != cell:
                    row[i] = new
                    report.cells_changed += 1

    report.rows_out = len(work)
    return new_header, work, report
