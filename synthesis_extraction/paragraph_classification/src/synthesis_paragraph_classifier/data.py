"""Training-data construction from parsed scientific-article JSON files."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .text import normalize_text, split_paragraphs

_POSITIVE_HEADING_RE = re.compile(
    r"(?i)\b(synth(?:esis|esized)?|prepar(?:ation|ed)?|fabricat(?:ion|ed)?|"
    r"electrodeposit(?:ion|ed)?|deposition|growth|catalyst preparation|"
    r"electrode preparation|materials? and methods?)\b"
)
_METHOD_HEADING_RE = re.compile(r"(?i)\b(experimental|methods?|materials?)\b")
_NEGATIVE_HEADING_RE = re.compile(
    r"(?i)\b(introduction|background|results?|discussion|conclusions?|abstract|"
    r"characteri[sz]ation|performance|product analysis|acknowledg|references?)\b"
)
_ACTION_RE = re.compile(
    r"(?i)\b(prepared|synthesi[sz]ed|fabricated|grown|deposited|electroplated|"
    r"dissolved|dispersed|mixed|added|stirred|heated|calcined|annealed|sintered|"
    r"dried|washed|filtered|centrifuged|sonicated|immersed|cooled|ground|milled|"
    r"loaded|coated|treated|reacted|transferred)\b"
)
_RECIPE_CUE_RE = re.compile(
    r"(?i)\b(briefly|in a typical (?:synthesis|procedure|experiment)|was then|"
    r"followed by|dropwise|under stirring|obtained (?:product|material|sample)|"
    r"the resulting|the mixture|the solution)\b"
)
_MEASUREMENT_RE = re.compile(
    r"(?i)\b(measured|characterized|spectroscop|microscop|xrd|xps|raman|"
    r"electrolysis|faradaic|current density|chromatograph|voltamm|impedance)\b"
)


@dataclass(frozen=True)
class ParagraphRecord:
    """One paragraph and its provenance."""

    id: str
    doi: str
    source_path: str
    section_heading: str
    text: str
    label: int | None = None
    selection_score: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_value(value: str, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _record_id(path: Path, section_index: int, paragraph_index: int) -> str:
    key = f"{path.as_posix()}:{section_index}:{paragraph_index}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]


def iter_gold_paragraphs(gold_data_dir: str | Path) -> Iterable[ParagraphRecord]:
    """Yield paragraph records from valid JSON files; malformed files are skipped."""
    root = Path(gold_data_dir)
    for path in sorted(root.rglob("*.json")):
        try:
            with path.open(encoding="utf-8") as handle:
                article = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(article, dict):
            continue
        sections = article.get("sections")
        if not isinstance(sections, list):
            continue
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        doi = relative[:-5].replace("/", "/", 1)
        for section_index, section in enumerate(sections):
            if not isinstance(section, dict):
                continue
            heading = normalize_text(section.get("heading", ""))
            for paragraph_index, text in enumerate(split_paragraphs(section.get("text", ""))):
                yield ParagraphRecord(
                    id=_record_id(Path(relative), section_index, paragraph_index),
                    doi=doi,
                    source_path=relative,
                    section_heading=heading,
                    text=text,
                )


def synthesis_score(record: ParagraphRecord) -> int:
    """Score whether a paragraph is a concrete material preparation recipe."""
    heading = record.section_heading
    text = record.text
    actions = len(set(match.lower() for match in _ACTION_RE.findall(text)))
    score = min(actions, 7)
    if _POSITIVE_HEADING_RE.search(heading):
        score += 5
    elif _METHOD_HEADING_RE.search(heading):
        score += 2
    if _RECIPE_CUE_RE.search(text):
        score += 2
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:mg|g|kg|mL|ml|L|M|mM|°C|K|h|min)\b", text):
        score += 1
    if _NEGATIVE_HEADING_RE.search(heading) and not _POSITIVE_HEADING_RE.search(heading):
        score -= 4
    if _MEASUREMENT_RE.search(text) and actions <= 2:
        score -= 2
    return score


def _deduplicate(records: Iterable[ParagraphRecord]) -> list[ParagraphRecord]:
    seen: set[str] = set()
    result: list[ParagraphRecord] = []
    for record in records:
        key = normalize_text(record.text).casefold()
        if key not in seen:
            seen.add(key)
            result.append(record)
    return result


def generate_positive_examples(
    gold_data_dir: str | Path,
    *,
    count: int = 228,
    seed: int = 17,
    max_per_article: int = 2,
) -> list[ParagraphRecord]:
    """Deterministically select likely synthesis recipes for model reproduction."""
    candidates = [record for record in iter_gold_paragraphs(gold_data_dir) if synthesis_score(record) >= 7]
    candidates = _deduplicate(candidates)
    candidates.sort(key=lambda r: (-synthesis_score(r), _stable_value(r.id, seed)))

    selected: list[ParagraphRecord] = []
    per_article: dict[str, int] = {}
    deferred: list[ParagraphRecord] = []
    for record in candidates:
        if per_article.get(record.doi, 0) < max_per_article:
            selected.append(record)
            per_article[record.doi] = per_article.get(record.doi, 0) + 1
        else:
            deferred.append(record)
        if len(selected) == count:
            break
    if len(selected) < count:
        selected_ids = {record.id for record in selected}
        selected.extend(record for record in deferred if record.id not in selected_ids)
        selected = selected[:count]
    if len(selected) != count:
        raise ValueError(f"Only {len(selected)} positive candidates available; requested {count}")
    return [ParagraphRecord(**{**record.to_dict(), "label": 1, "selection_score": synthesis_score(record)}) for record in selected]


def generate_negative_examples(
    gold_data_dir: str | Path,
    *,
    count: int = 532,
    seed: int = 17,
    excluded_ids: set[str] | None = None,
) -> list[ParagraphRecord]:
    """Deterministically select paragraphs that do not describe concrete synthesis.

    Negative candidates favor introductions, results, characterization, and other
    non-recipe sections. Paragraphs with several synthesis actions or recipe cues
    are excluded to minimize noisy labels.
    """
    excluded_ids = excluded_ids or set()
    strict: list[ParagraphRecord] = []
    fallback: list[ParagraphRecord] = []
    for record in iter_gold_paragraphs(gold_data_dir):
        if record.id in excluded_ids:
            continue
        score = synthesis_score(record)
        action_count = len(set(match.lower() for match in _ACTION_RE.findall(record.text)))
        has_positive_heading = bool(_POSITIVE_HEADING_RE.search(record.section_heading))
        if score <= 1 and action_count <= 1 and not has_positive_heading:
            strict.append(record)
        elif score <= 3 and not has_positive_heading:
            fallback.append(record)
    candidates = _deduplicate(strict)
    candidate_ids = {record.id for record in candidates}
    candidates.extend(record for record in _deduplicate(fallback) if record.id not in candidate_ids)
    candidates.sort(
        key=lambda r: (
            0 if _NEGATIVE_HEADING_RE.search(r.section_heading) else 1,
            synthesis_score(r),
            _stable_value(r.id, seed),
        )
    )
    selected = candidates[:count]
    if len(selected) != count:
        raise ValueError(f"Only {len(selected)} negative candidates available; requested {count}")
    return [ParagraphRecord(**{**record.to_dict(), "label": 0, "selection_score": synthesis_score(record)}) for record in selected]


def write_jsonl(records: Iterable[ParagraphRecord], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")


def load_jsonl(path: str | Path) -> list[ParagraphRecord]:
    records: list[ParagraphRecord] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if "text" not in value:
                raise ValueError(f"Missing text at {path}:{line_number}")
            records.append(ParagraphRecord(**value))
    return records


def build_training_dataset(
    gold_data_dir: str | Path,
    output_dir: str | Path,
    *,
    positive_count: int = 228,
    negative_count: int = 532,
    seed: int = 17,
) -> tuple[list[ParagraphRecord], list[ParagraphRecord]]:
    """Build and save the paper-sized 228/532 binary classification dataset."""
    positives = generate_positive_examples(gold_data_dir, count=positive_count, seed=seed)
    negatives = generate_negative_examples(
        gold_data_dir,
        count=negative_count,
        seed=seed,
        excluded_ids={record.id for record in positives},
    )
    output = Path(output_dir)
    write_jsonl(positives, output / "positive_examples.jsonl")
    write_jsonl(negatives, output / "negative_examples.jsonl")
    combined = [*positives, *negatives]
    combined.sort(key=lambda record: _stable_value(record.id, seed))
    write_jsonl(combined, output / "paragraph_classification_training_data.jsonl")
    metadata = {
        "positive_examples": len(positives),
        "negative_examples": len(negatives),
        "total_examples": len(combined),
        "seed": seed,
        "source": str(Path(gold_data_dir)),
        "note": "Deterministic weak labels reconstructed from local gold_data; not the unavailable original copyrighted annotations.",
    }
    (output / "dataset_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return positives, negatives
