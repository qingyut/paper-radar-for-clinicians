from __future__ import annotations

import math
import re
from typing import Any

from paper_radar.models import ExpandedQuery, PaperRecord
from paper_radar.utils import dedupe_preserve_order, days_since, normalize_whitespace


def _match_term_score(term: str, text_lower: str, title_lower: str) -> float:
    norm = normalize_whitespace(term).lower()
    if not norm:
        return 0.0

    if norm in text_lower:
        return 1.0 if norm not in title_lower else 1.08

    tokens = [t for t in re.split(r"[^a-z0-9]+", norm) if t]
    if not tokens:
        return 0.0

    present = sum(tok in text_lower for tok in tokens)
    if present >= len(tokens):
        return 0.92
    if present >= max(1, len(tokens) - 1):
        return 0.62
    if len(tokens) >= 3 and present >= math.ceil(len(tokens) / 2):
        return 0.38
    return 0.0


def _group_variants(group: dict[str, Any]) -> list[str]:
    variants: list[str] = []
    variants.extend(group.get("original_terms", []))
    variants.extend(group.get("mesh_descriptors", []))
    variants.extend(group.get("mesh_terms", []))
    variants.extend(group.get("free_terms", []))
    return dedupe_preserve_order(variants)


def score_relevance_and_coverage(
    paper: PaperRecord,
    expanded: ExpandedQuery,
    cfg: dict[str, Any],
) -> tuple[float, float, list[str], list[list[str]]]:
    text = normalize_whitespace(" ".join([paper.title, paper.abstract] + paper.mesh_terms + paper.keywords)).lower()
    title_lower = normalize_whitespace(paper.title).lower()
    coverage_threshold = float(cfg.get("ranking", {}).get("coverage_hit_threshold", 0.55))

    group_scores: list[float] = []
    matched_terms: list[str] = []
    matched_groups: list[list[str]] = []

    groups = expanded.expanded_groups or [{
        "original_terms": [expanded.original_keyword],
        "mesh_descriptors": ([expanded.mesh_descriptor] if expanded.mesh_descriptor else []),
        "mesh_terms": expanded.mesh_terms,
        "free_terms": expanded.free_terms,
    }]

    for group in groups:
        best_score = 0.0
        best_terms: list[str] = []
        for variant in _group_variants(group):
            term_score = _match_term_score(variant, text, title_lower)
            if term_score > best_score + 1e-9:
                best_score = term_score
                best_terms = [variant]
            elif term_score > 0 and abs(term_score - best_score) <= 1e-9:
                best_terms.append(variant)

        normalized_best = min(1.0, best_score)
        group_scores.append(normalized_best)
        if best_terms:
            deduped = dedupe_preserve_order(best_terms)
            matched_terms.extend(deduped)
            matched_groups.append(deduped)
        else:
            matched_groups.append([])

    if not group_scores:
        return 0.0, 0.0, [], []

    relevance = sum(group_scores) / len(group_scores)
    coverage_hits = sum(score >= coverage_threshold for score in group_scores)
    coverage = coverage_hits / len(group_scores)

    return (
        min(1.0, relevance),
        min(1.0, coverage),
        dedupe_preserve_order(matched_terms),
        matched_groups,
    )


def score_freshness(paper: PaperRecord, horizon_days: int) -> float:
    age = days_since(paper.published)
    if age is None:
        return 0.35
    if horizon_days <= 0:
        return 0.0
    return max(0.0, min(1.0, math.exp(-age / max(1, horizon_days / 2.2))))


def score_evidence(paper: PaperRecord, cfg: dict[str, Any]) -> float:
    type_scores = cfg["ranking"].get("publication_type_scores", {})
    boosts = cfg["ranking"].get("heuristic_text_boosts", {})

    values = []
    for pub_type in paper.publication_types:
        score = type_scores.get(pub_type.strip().lower())
        if score is not None:
            values.append(float(score))

    if paper.source == "arxiv":
        values.append(float(type_scores.get("preprint", 0.46)))

    base = max(values) if values else (0.55 if paper.source == "pubmed" else 0.46)

    body = normalize_whitespace(" ".join([paper.title, paper.abstract])).lower()
    extra = 0.0
    for needle, delta in boosts.items():
        if needle.lower() in body:
            extra += float(delta)

    return max(0.0, min(1.0, base + min(extra, 0.18)))


def score_source(paper: PaperRecord, cfg: dict[str, Any]) -> float:
    priors = cfg["ranking"].get("source_priors", {})
    return float(priors.get(paper.source, 0.5))


def score_completeness(paper: PaperRecord) -> float:
    fields = [
        bool(paper.abstract),
        bool(paper.authors),
        bool(paper.published),
        bool(paper.url),
        bool(paper.publication_types or paper.keywords or paper.mesh_terms),
        bool(paper.doi),
    ]
    return sum(fields) / len(fields)


def apply_ranking(
    papers: list[PaperRecord],
    expanded: ExpandedQuery,
    cfg: dict[str, Any],
    horizon_days: int,
) -> list[PaperRecord]:
    weights = cfg["ranking"]["weights"]
    coverage_weight = float(weights.get("coverage", 0.0))

    for paper in papers:
        (
            paper.relevance_score,
            paper.coverage_score,
            paper.matched_terms,
            paper.matched_groups,
        ) = score_relevance_and_coverage(paper, expanded, cfg)
        paper.freshness_score = score_freshness(paper, horizon_days)
        paper.evidence_score = score_evidence(paper, cfg)
        paper.source_score = score_source(paper, cfg)
        paper.completeness_score = score_completeness(paper)

        paper.score_breakdown = {
            "relevance": round(paper.relevance_score, 4),
            "coverage": round(paper.coverage_score, 4),
            "freshness": round(paper.freshness_score, 4),
            "evidence": round(paper.evidence_score, 4),
            "source": round(paper.source_score, 4),
            "completeness": round(paper.completeness_score, 4),
        }

        paper.final_score = round(
            weights["relevance"] * paper.relevance_score
            + coverage_weight * paper.coverage_score
            + weights["freshness"] * paper.freshness_score
            + weights["evidence"] * paper.evidence_score
            + weights["source"] * paper.source_score
            + weights["completeness"] * paper.completeness_score,
            6,
        )

    return sorted(papers, key=lambda x: x.final_score, reverse=True)
