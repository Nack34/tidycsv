from pathlib import Path

from typer.testing import CliRunner

from tidycsv import __version__
from tidycsv.cli import app
from tidycsv.io import detect_delimiter, read_table

runner = CliRunner()

MESSY = "Nombre;Importe;Fecha de pago\n Ana ;1.500,50;05/01/2024\nBeto;200;s/d\n;;\nBeto;200;s/d\n"


def write(tmp_path: Path, text: str, encoding: str = "utf-8") -> Path:
    path = tmp_path / "datos.csv"
    path.write_bytes(text.encode(encoding))
    return path


def test_reads_latin1_semicolon_files(tmp_path):
    path = write(tmp_path, "Año;Señal\n2024;Sí\n", encoding="cp1252")
    table = read_table(path)
    assert table.delimiter == ";"
    assert table.header == ["Año", "Señal"]
    assert table.rows == [["2024", "Sí"]]


def test_short_rows_are_padded(tmp_path):
    table = read_table(write(tmp_path, "a,b,c\n1,2\n"))
    assert table.rows == [["1", "2", ""]]


def test_detect_delimiter_fallback():
    assert detect_delimiter("a|b|c") == "|"


def test_inspect_shows_summary(tmp_path):
    result = runner.invoke(app, ["inspect", str(write(tmp_path, MESSY))])
    assert result.exit_code == 0, result.output
    assert "delimiter=';'" in result.output
    assert "rows=4" in result.output
    assert "1 duplicated row" in result.output
    assert "Importe" in result.output


def test_clean_writes_a_tidy_file(tmp_path):
    source = write(tmp_path, MESSY)
    result = runner.invoke(app, ["clean", str(source)])
    assert result.exit_code == 0, result.output
    output = tmp_path / "datos.clean.csv"
    assert output.read_text(encoding="utf-8").splitlines() == [
        "nombre,importe,fecha_de_pago",
        "Ana,1500.5,2024-01-05",
        "Beto,200,",
    ]
    assert "rows 4 -> 2" in result.output


def test_clean_options_and_output_path(tmp_path):
    source = write(tmp_path, MESSY)
    target = tmp_path / "out.tsv"
    result = runner.invoke(
        app,
        ["clean", str(source), "-o", str(target), "--keep-headers", "--keep-duplicates", "--delimiter", "\t"],
    )
    assert result.exit_code == 0, result.output
    lines = target.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "Nombre\tImporte\tFecha de pago"
    assert len(lines) == 4  # header + 3 rows (only the empty row was dropped)


def test_missing_file_fails_cleanly(tmp_path):
    result = runner.invoke(app, ["inspect", str(tmp_path / "nope.csv")])
    assert result.exit_code != 0


def test_version():
    result = runner.invoke(app, ["--version"])
    assert __version__ in result.output
