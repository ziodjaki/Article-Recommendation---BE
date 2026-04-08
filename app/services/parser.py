from __future__ import annotations

import errno
import json
import re
import unicodedata
from pathlib import Path


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return slug or "journal"


def _is_focus_label(line: str) -> bool:
    normalized = re.sub(r"[^a-z]+", "", line.lower())
    return normalized in {"focus"}


def _is_scope_label(line: str) -> bool:
    normalized = re.sub(r"[^a-z]+", "", line.lower())
    return normalized in {"scope"}


def _is_focus_scope_label(line: str) -> bool:
    normalized = re.sub(r"[^a-z]+", "", line.lower())
    return normalized in {"focusandscope", "focusscope"}


def _clean_lines(lines: list[str]) -> str:
    compact = [line.strip() for line in lines if line.strip()]
    return "\n".join(compact)


def _extract_focus_scope(block_lines: list[str]) -> tuple[str, str]:
    focus_lines: list[str] = []
    scope_lines: list[str] = []
    fallback_lines: list[str] = []
    current_section: str | None = None

    for line in block_lines:
        stripped = line.strip()
        if not stripped:
            continue

        if _is_focus_label(stripped):
            current_section = "focus"
            continue
        if _is_scope_label(stripped):
            current_section = "scope"
            continue
        if _is_focus_scope_label(stripped):
            current_section = None
            continue

        if stripped.lower().startswith("focus:"):
            current_section = "focus"
            payload = stripped.split(":", 1)[1].strip()
            if payload:
                focus_lines.append(payload)
            continue
        if stripped.lower().startswith("scope:"):
            current_section = "scope"
            payload = stripped.split(":", 1)[1].strip()
            if payload:
                scope_lines.append(payload)
            continue

        fallback_lines.append(stripped)
        if current_section == "focus":
            focus_lines.append(stripped)
        elif current_section == "scope":
            scope_lines.append(stripped)

    focus = _clean_lines(focus_lines)
    scope = _clean_lines(scope_lines)

    if not focus and fallback_lines:
        focus = fallback_lines[0]
    if not scope and fallback_lines:
        scope = _clean_lines(fallback_lines[1:]) or fallback_lines[0]

    return focus, scope


def parse_journal_markdown(markdown_text: str) -> list[dict]:
    heading_pattern = re.compile(r"^#\s+(.+)$", re.MULTILINE)
    matches = list(heading_pattern.finditer(markdown_text))
    journals: list[dict] = []
    seen_ids: set[str] = set()

    for index, match in enumerate(matches):
        name = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        block = markdown_text[start:end].strip()
        if not block:
            continue

        block_lines = block.splitlines()
        focus, scope = _extract_focus_scope(block_lines)
        full_text = "\n\n".join(item for item in [focus, scope] if item)

        base_id = f"journal-{_slugify(name)}"
        candidate_id = base_id
        suffix = 2
        while candidate_id in seen_ids:
            candidate_id = f"{base_id}-{suffix}"
            suffix += 1
        seen_ids.add(candidate_id)

        journals.append(
            {
                "id": candidate_id,
                "name": name,
                "focus": focus,
                "scope": scope,
                "full_text": full_text,
            }
        )

    return journals


def parse_file_to_json(source_path: Path, output_path: Path) -> list[dict]:
    markdown_text = source_path.read_text(encoding="utf-8")
    journals = parse_journal_markdown(markdown_text)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(journals, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as exc:
        # Serverless platforms may mount code directories as read-only.
        if exc.errno != errno.EROFS:
            raise

    return journals
