from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ExpandedQuery:
    original_keyword: str
    mesh_descriptor: str | None = None
    mesh_uri: str | None = None
    mesh_terms: list[str] = field(default_factory=list)
    free_terms: list[str] = field(default_factory=list)
    pubmed_query: str = ""
    arxiv_query: str = ""
    query_mode: str = "simple"
    parsed_groups: list[list[str]] = field(default_factory=list)
    expanded_groups: list[dict[str, Any]] = field(default_factory=list)
    mesh_descriptors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PaperRecord:
    source: str
    source_id: str
    title: str
    abstract: str
    url: str
    published: str
    authors: list[str] = field(default_factory=list)
    journal_or_category: str | None = None
    doi: str | None = None
    publication_types: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    relevance_score: float = 0.0
    coverage_score: float = 0.0
    freshness_score: float = 0.0
    evidence_score: float = 0.0
    source_score: float = 0.0
    completeness_score: float = 0.0
    final_score: float = 0.0
    score_breakdown: dict[str, float] = field(default_factory=dict)

    method_innovation_one_liner: str = ""
    matched_terms: list[str] = field(default_factory=list)
    matched_groups: list[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
