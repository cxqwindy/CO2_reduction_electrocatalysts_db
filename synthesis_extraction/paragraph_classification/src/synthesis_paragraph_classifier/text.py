"""Dependency-light text processing for scientific prose."""

from __future__ import annotations

import re
from collections.abc import Iterable

_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+(?=(?:[A-Z0-9]|\(|\[))")
_TOKEN_RE = re.compile(r"(?u)[A-Za-z0-9][A-Za-z0-9_+./°−–-]*")


def normalize_text(text: str) -> str:
    """Collapse whitespace while retaining scientific symbols."""
    return _WHITESPACE_RE.sub(" ", str(text or "")).strip()


def sentence_split(text: str) -> list[str]:
    """Split scientific prose without external tokenizer model downloads."""
    clean = normalize_text(text)
    if not clean:
        return []
    sentences = [part.strip() for part in _SENTENCE_BOUNDARY_RE.split(clean)]
    return [sentence for sentence in sentences if len(sentence) >= 2]


def chemistry_tokenizer(text: str) -> list[str]:
    """Tokenize words, formulae, numbers, units, and common chemical punctuation."""
    return [token.lower() for token in _TOKEN_RE.findall(text) if len(token) > 1]


def _chunk_long_text(text: str, max_chars: int) -> list[str]:
    sentences = sentence_split(text)
    if not sentences:
        return []
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for sentence in sentences:
        if current and size + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current))
            current, size = [], 0
        current.append(sentence)
        size += len(sentence) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks


def split_paragraphs(
    text: str,
    *,
    min_chars: int = 120,
    max_chars: int = 3500,
) -> list[str]:
    """Recover coherent paragraph-like chunks from parsed PDF section text.

    Parser outputs are inconsistent: a newline may indicate either a paragraph or
    merely a PDF layout wrap. Joining a section first avoids emitting half-lines;
    long sections are then bounded at sentence boundaries for tractable modeling.
    """
    block = normalize_text(" ".join(str(text or "").splitlines()))
    if len(block) < min_chars:
        return []
    candidates = _chunk_long_text(block, max_chars) if len(block) > max_chars else [block]
    return [candidate for candidate in candidates if len(candidate) >= min_chars]


def iter_sentences(texts: Iterable[str]) -> Iterable[str]:
    """Yield sentences from a text iterable."""
    for text in texts:
        yield from sentence_split(text)
