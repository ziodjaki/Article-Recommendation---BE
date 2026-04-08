import json

import pytest

from app.main import load_journals_data


def test_load_journals_data_uses_markdown_when_available(tmp_path):
    markdown_path = tmp_path / "journals.md"
    output_path = tmp_path / "journals.json"
    markdown_path.write_text("# Journal A\nFocus\nAI\nScope\nEducation\n", encoding="utf-8")

    journals = load_journals_data(source_path=markdown_path, output_path=output_path)

    assert len(journals) == 1
    assert journals[0]["name"] == "Journal A"
    assert output_path.exists()


def test_load_journals_data_falls_back_to_cached_json(tmp_path):
    markdown_path = tmp_path / "missing.md"
    output_path = tmp_path / "journals.json"
    cached = [
        {
            "id": "journal-a",
            "name": "Journal A",
            "focus": "AI",
            "scope": "Education",
            "full_text": "AI\n\nEducation",
        }
    ]
    output_path.write_text(json.dumps(cached), encoding="utf-8")

    journals = load_journals_data(source_path=markdown_path, output_path=output_path)

    assert journals == cached


def test_load_journals_data_raises_when_no_source_and_no_cache(tmp_path):
    markdown_path = tmp_path / "missing.md"
    output_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_journals_data(source_path=markdown_path, output_path=output_path)


def test_load_journals_data_falls_back_when_parse_write_fails(monkeypatch, tmp_path):
    markdown_path = tmp_path / "journals.md"
    output_path = tmp_path / "journals.json"
    markdown_path.write_text("# Journal A\nFocus\nAI\nScope\nEducation\n", encoding="utf-8")

    def _raise_oserror(*args, **kwargs):
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr("app.main.parse_file_to_json", _raise_oserror)

    journals = load_journals_data(source_path=markdown_path, output_path=output_path)

    assert len(journals) == 1
    assert journals[0]["name"] == "Journal A"
