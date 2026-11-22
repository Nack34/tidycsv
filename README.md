# tidycsv

Command-line tool to **inspect and clean messy CSV files**, with first-class support for the formats you get from Argentine systems and spreadsheets: `;` delimiters, Windows-1252 encoding, numbers like `1.234,56`, dates like `25/12/2024` and null markers like `s/d`.

```bash
pip install tidycsv-ar
```

## Usage

```bash
tidycsv inspect ventas.csv
```

```
ventas.csv  encoding=cp1252  delimiter=';'  rows=4  columns=3
1 duplicated row(s)
┏━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ column        ┃ type   ┃ nulls   ┃ examples         ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ Nombre        │ text   │ 1 (25%) │ Ana, Beto        │
│ Importe       │ number │ 1 (25%) │ 1.500,50, 200    │
│ Fecha de pago │ date   │ 3 (75%) │ 05/01/2024       │
└───────────────┴────────┴─────────┴──────────────────┘
```

```bash
tidycsv clean ventas.csv            # writes ventas.clean.csv
tidycsv clean ventas.csv -o out.tsv --delimiter $'\t' --keep-headers
```

`clean` does, in order:

1. Detects encoding (UTF-8, UTF-8 with BOM, Windows-1252, Latin-1) and delimiter (`,` `;` tab `|`)
2. Converts headers to unique `snake_case` (`Fecha de pago` → `fecha_de_pago`)
3. Trims spaces in every cell
4. Drops empty rows and duplicated rows
5. Infers each column's type and standardizes values: `1.234,56` → `1234.56`, `25/12/2024` → `2024-12-25`, `N/A` / `s/d` / `-` → empty

Each step can be turned off: `--keep-headers`, `--keep-duplicates`, `--no-standardize`. The output is always UTF-8.

## Design

- `cleaning.py` holds pure functions (no files, no printing), so every rule is unit-tested; `io.py` handles encodings and delimiters; `cli.py` is a thin Typer layer.
- Number parsing decides between `1.234,56` and `1,234.56` by the position of separators, so both conventions work in the same tool.
- Dates are read day-first, as written in Argentina; `12/25/2024` is rejected rather than guessed.
- Only two dependencies: Typer and Rich.

## Development

```bash
pip install -e ".[dev]"
pytest --cov=tidycsv     # 26 tests, 97% coverage
python -m build          # wheel + sdist in dist/
```

Releases: push a tag `v1.0.1` and GitHub Actions builds and publishes to PyPI using trusted publishing (configure the project on pypi.org first).

## License

MIT
