from pathlib import Path

from app.services.parser import parse_file_to_json


def test_parser_outputs_expected_journal_count(tmp_path: Path):
    source = Path(__file__).resolve().parents[2] / "jurnal.md"
    output = tmp_path / "journals.json"

    journals = parse_file_to_json(source_path=source, output_path=output)

    assert len(journals) == 7
    assert output.exists()
    assert all(item.get("id", "").startswith("journal-") for item in journals)


def test_parser_tolerates_read_only_output(monkeypatch, tmp_path: Path):
    source = Path(__file__).resolve().parents[2] / "jurnal.md"
    output = tmp_path / "journals.json"
    original_write_text = Path.write_text

    def _raise_read_only(self: Path, data: str, encoding: str = "utf-8", errors=None, newline=None):
        if self == output:
            raise OSError(30, "Read-only file system")
        return original_write_text(self, data, encoding=encoding, errors=errors, newline=newline)

    monkeypatch.setattr(Path, "write_text", _raise_read_only)

    journals = parse_file_to_json(source_path=source, output_path=output)

    assert len(journals) == 7
    assert all(item.get("id", "").startswith("journal-") for item in journals)
