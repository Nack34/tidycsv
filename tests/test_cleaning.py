from datetime import date

import pytest

from tidycsv.cleaning import (
    CleanOptions,
    clean,
    infer_type,
    parse_date,
    parse_number,
    snake_case,
    unique_names,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.234,56", 1234.56),
        ("$ 1.234.567", 1234567.0),
        ("12,5", 12.5),
        ("1,234.56", 1234.56),
        ("1234", 1234.0),
        ("-3.5", -3.5),
        ("abc", None),
        ("1.2.3", None),
    ],
)
def test_parse_number_handles_argentine_and_us_formats(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("25/12/2024", date(2024, 12, 25)),
        ("1-3-2025", date(2025, 3, 1)),
        ("2024-02-29", date(2024, 2, 29)),
        ("31/02/2024", None),
        ("12/25/2024", None),
        ("ayer", None),
    ],
)
def test_parse_date_is_day_first(raw, expected):
    assert parse_date(raw) == expected


def test_headers_become_unique_snake_case():
    names = [snake_case(h) for h in ["Fecha de Alta (DD/MM)", "Importe $", "importe", "  "]]
    assert unique_names(names) == ["fecha_de_alta_dd_mm", "importe", "importe_2", "column"]


def test_infer_type_ignores_nulls():
    assert infer_type(["1", "2", "N/A", ""]) == "integer"
    assert infer_type(["1,5", "2"]) == "number"
    assert infer_type(["01/01/2024", "s/d"]) == "date"
    assert infer_type(["a", "1"]) == "text"
    assert infer_type(["", "-"]) == "empty"


def test_clean_end_to_end():
    header = ["Nombre", "Monto", "Fecha"]
    rows = [
        ["  Ana ", "1.500,50", "05/01/2024"],
        ["Beto", "200", "N/A"],
        ["", "", ""],
        ["Beto", "200", "N/A"],
    ]
    new_header, out, report = clean(header, rows)
    assert new_header == ["nombre", "monto", "fecha"]
    assert out == [["Ana", "1500.5", "2024-01-05"], ["Beto", "200", ""]]
    assert report.empty_rows_dropped == 1
    assert report.duplicates_dropped == 1
    assert report.column_types == {"nombre": "text", "monto": "number", "fecha": "date"}


def test_options_can_turn_steps_off():
    header, out, report = clean(
        ["A"], [["x"], ["x"]], CleanOptions(normalize_headers=False, drop_duplicates=False, standardize=False)
    )
    assert header == ["A"] and out == [["x"], ["x"]] and report.duplicates_dropped == 0
