from paper_radar.models import ExpandedQuery, PaperRecord
from paper_radar.ranking import apply_ranking


def _cfg():
    return {
        "ranking": {
            "weights": {
                "relevance": 0.5,
                "coverage": 0.2,
                "freshness": 0.14,
                "evidence": 0.1,
                "source": 0.04,
                "completeness": 0.02,
            },
            "coverage_hit_threshold": 0.55,
            "publication_type_scores": {"preprint": 0.46},
            "heuristic_text_boosts": {},
            "source_priors": {"pubmed": 0.88, "arxiv": 0.52},
        }
    }


def test_coverage_penalizes_partial_match():
    expanded = ExpandedQuery(
        original_keyword='(gallbladder cancer OR gallbladder neoplasms) AND (multimodal) AND (pathology OR histopathology)',
        query_mode='grouped',
        parsed_groups=[
            ["gallbladder cancer", "gallbladder neoplasms"],
            ["multimodal"],
            ["pathology", "histopathology"],
        ],
        expanded_groups=[
            {"original_terms": ["gallbladder cancer", "gallbladder neoplasms"], "mesh_descriptors": [], "mesh_terms": [], "free_terms": ["gallbladder cancer", "gallbladder neoplasms"]},
            {"original_terms": ["multimodal"], "mesh_descriptors": [], "mesh_terms": [], "free_terms": ["multimodal"]},
            {"original_terms": ["pathology", "histopathology"], "mesh_descriptors": [], "mesh_terms": [], "free_terms": ["pathology", "histopathology"]},
        ],
    )
    broad = PaperRecord(
        source="pubmed",
        source_id="1",
        title="Gallbladder cancer multimodal pathology study",
        abstract="A multimodal pathology pipeline for gallbladder cancer.",
        url="x",
        published="2026-01-01",
    )
    partial = PaperRecord(
        source="pubmed",
        source_id="2",
        title="Gallbladder surgery outcomes",
        abstract="An observational study.",
        url="x",
        published="2026-01-01",
    )

    ranked = apply_ranking([partial, broad], expanded, _cfg(), horizon_days=30)
    assert ranked[0].source_id == "1"
    assert ranked[0].coverage_score == 1.0
    assert ranked[1].coverage_score < 1.0
