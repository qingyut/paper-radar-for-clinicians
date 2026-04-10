from __future__ import annotations

import re

from paper_radar.utils import normalize_whitespace

_METHOD_PATTERNS = [
    r"\bwe (developed|propose|present|introduce|built|evaluate|evaluated|designed)\b",
    r"\b(methods?|patients?|participants?|materials and methods)\b",
    r"\b(using|by combining|based on|retrospective|prospective|randomized|multicenter|multi-center)\b",
]

_INNOVATION_PATTERNS = [
    r"\b(novel|innovative|first|state-of-the-art|outperform|improved|significantly|superior|validated)\b",
    r"\b(demonstrate|show|shows|showed|achieve|achieved|improves|improved)\b",
]


def split_sentences(text: str) -> list[str]:
    text = normalize_whitespace(text)
    if not text:
        return []
    parts = re.split(r"(?<=[\.\!\?])\s+(?=[A-Z0-9])", text)
    return [normalize_whitespace(p) for p in parts if normalize_whitespace(p)]


def _first_matching(sentences: list[str], patterns: list[str]) -> str | None:
    for sentence in sentences:
        for pattern in patterns:
            if re.search(pattern, sentence, flags=re.IGNORECASE):
                return sentence
    return None


def build_one_liner(title: str, abstract: str) -> str:
    sentences = split_sentences(abstract)
    if not sentences:
        return normalize_whitespace(title)

    method = _first_matching(sentences, _METHOD_PATTERNS) or sentences[0]
    innovation = _first_matching(sentences, _INNOVATION_PATTERNS)

    if innovation and innovation != method:
        line = f"Method: {method} Innovation: {innovation}"
    else:
        line = f"Method/innovation: {method}"

    return normalize_whitespace(line)
