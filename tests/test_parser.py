from pathlib import Path

from app.services.parser import parse_file_to_json


def test_parser_outputs_expected_journal_count(tmp_path: Path):
    source = Path(__file__).resolve().parents[2] / "jurnal.md"
    output = tmp_path / "journals.json"

    journals = parse_file_to_json(source_path=source, output_path=output)

    assert len(journals) == 7
    assert output.exists()
    assert all(item.get("id", "").startswith("journal-") for item in journals)
