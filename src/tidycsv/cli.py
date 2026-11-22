"""Command-line interface: `tidycsv inspect` and `tidycsv clean`."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table as RichTable

from tidycsv import __version__
from tidycsv.cleaning import CleanOptions, clean, infer_type, is_null
from tidycsv.io import read_table, write_table

app = typer.Typer(help="Inspect and clean messy CSV files.", no_args_is_help=True, add_completion=False)
console = Console()

InputFile = Annotated[
    Path, typer.Argument(exists=True, dir_okay=False, readable=True, help="CSV file to read")
]


def _version(value: bool) -> None:
    if value:
        console.print(f"tidycsv {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version, is_eager=True, help="Show the version")
    ] = False,
) -> None:
    """Inspect and clean messy CSV files."""


@app.command()
def inspect(
    path: InputFile, sample: Annotated[int, typer.Option(help="Example values per column")] = 3
) -> None:
    """Show encoding, delimiter, rows, and per-column type, nulls and examples."""
    table = read_table(path)
    console.print(
        f"[bold]{path.name}[/]  encoding={table.encoding}  delimiter={table.delimiter!r}  "
        f"rows={len(table.rows)}  columns={len(table.header)}"
    )
    duplicates = len(table.rows) - len({tuple(r) for r in table.rows})
    if duplicates:
        console.print(f"[yellow]{duplicates} duplicated row(s)[/]")
    out = RichTable("column", "type", "nulls", "examples")
    for i, name in enumerate(table.header):
        values = [row[i] if i < len(row) else "" for row in table.rows]
        nulls = sum(is_null(v) for v in values)
        examples = ", ".join(list(dict.fromkeys(v.strip() for v in values if not is_null(v)))[:sample])
        out.add_row(name, infer_type(values), f"{nulls} ({nulls / max(1, len(values)):.0%})", examples)
    console.print(out)


@app.command(name="clean")
def clean_command(
    path: InputFile,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Where to write (default: <name>.clean.csv)")
    ] = None,
    keep_headers: Annotated[bool, typer.Option(help="Don't convert headers to snake_case")] = False,
    keep_duplicates: Annotated[bool, typer.Option(help="Don't drop duplicated rows")] = False,
    no_standardize: Annotated[
        bool, typer.Option(help="Don't rewrite numbers, dates and null tokens")
    ] = False,
    delimiter: Annotated[str, typer.Option(help="Delimiter for the output file")] = ",",
) -> None:
    """Trim cells, normalize headers, drop empty and duplicated rows, and standardize numbers and dates."""
    table = read_table(path)
    options = CleanOptions(
        normalize_headers=not keep_headers,
        drop_duplicates=not keep_duplicates,
        standardize=not no_standardize,
    )
    header, rows, report = clean(table.header, table.rows, options)
    target = output or path.with_name(f"{path.stem}.clean.csv")
    write_table(target, header, rows, delimiter=delimiter)

    console.print(f"[green]Wrote {target}[/]")
    console.print(
        f"rows {report.rows_in} -> {report.rows_out}  (empty: {report.empty_rows_dropped}, "
        f"duplicates: {report.duplicates_dropped})  cells changed: {report.cells_changed}"
    )
    types = RichTable("column", "type")
    for name, kind in report.column_types.items():
        types.add_row(name, kind)
    console.print(types)


if __name__ == "__main__":
    app()
