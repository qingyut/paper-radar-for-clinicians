from __future__ import annotations

from urllib.parse import quote_plus

from paper_radar.boolean_query import parse_keyword_groups
from paper_radar.models import ExpandedQuery
from paper_radar.sources.mesh import MeSHClient
from paper_radar.utils import dedupe_preserve_order, normalize_whitespace


def _pubmed_title_abstract_term(term: str) -> str:
    return f'"{term}"[Title/Abstract]'


def _arxiv_term_clause(term: str) -> str:
    phrase = quote_plus(f'"{term}"')
    return f'(ti:{phrase}+OR+abs:{phrase})'


def _expand_leaf(term: str, mesh: MeSHClient) -> dict:
    term = normalize_whitespace(term)
    mesh_match = mesh.find_best_descriptor(term)
    mesh_descriptor = None
    mesh_uri = None
    mesh_terms: list[str] = []

    if mesh_match:
        mesh_descriptor = mesh_match["label"]
        mesh_uri = mesh_match["uri"]
        mesh_terms = dedupe_preserve_order(
            [mesh_descriptor] + mesh.get_entry_terms(mesh_uri)
        )

    free_terms = dedupe_preserve_order([term])

    pubmed_terms = []
    if mesh_descriptor:
        pubmed_terms.append(f'"{mesh_descriptor}"[MeSH Terms]')
    pubmed_terms.extend(_pubmed_title_abstract_term(t) for t in (mesh_terms or free_terms))

    arxiv_terms = [_arxiv_term_clause(t) for t in dedupe_preserve_order(mesh_terms or free_terms)]

    return {
        "original_term": term,
        "mesh_descriptor": mesh_descriptor,
        "mesh_uri": mesh_uri,
        "mesh_terms": mesh_terms,
        "free_terms": free_terms,
        "pubmed_terms": dedupe_preserve_order(pubmed_terms),
        "arxiv_terms": dedupe_preserve_order(arxiv_terms),
    }


def build_expanded_query(keyword: str, mesh: MeSHClient) -> ExpandedQuery:
    keyword = normalize_whitespace(keyword)
    parsed_groups = parse_keyword_groups(keyword)
    query_mode = "grouped" if len(parsed_groups) > 1 or any(len(g) > 1 for g in parsed_groups) else "simple"

    expanded_groups: list[dict] = []
    flat_mesh_descriptors: list[str] = []
    flat_mesh_terms: list[str] = []
    flat_free_terms: list[str] = []

    for group_terms in parsed_groups:
        leaf_expansions = [_expand_leaf(term, mesh) for term in group_terms]

        group_mesh_descriptors = dedupe_preserve_order(
            [leaf["mesh_descriptor"] for leaf in leaf_expansions if leaf.get("mesh_descriptor")]
        )
        group_mesh_terms = dedupe_preserve_order(
            term for leaf in leaf_expansions for term in leaf.get("mesh_terms", [])
        )
        group_free_terms = dedupe_preserve_order(
            term for leaf in leaf_expansions for term in leaf.get("free_terms", [])
        )
        group_pubmed_terms = dedupe_preserve_order(
            term for leaf in leaf_expansions for term in leaf.get("pubmed_terms", [])
        )
        group_arxiv_terms = dedupe_preserve_order(
            term for leaf in leaf_expansions for term in leaf.get("arxiv_terms", [])
        )

        expanded_groups.append(
            {
                "original_terms": group_terms,
                "mesh_descriptors": group_mesh_descriptors,
                "mesh_terms": group_mesh_terms,
                "free_terms": group_free_terms,
                "pubmed_clause": "(" + " OR ".join(group_pubmed_terms) + ")",
                "arxiv_clause": "(" + "+OR+".join(group_arxiv_terms) + ")",
                "leaf_expansions": leaf_expansions,
            }
        )

        flat_mesh_descriptors.extend(group_mesh_descriptors)
        flat_mesh_terms.extend(group_mesh_terms)
        flat_free_terms.extend(group_free_terms)

    pubmed_query = " AND ".join(group["pubmed_clause"] for group in expanded_groups)
    arxiv_query = "+AND+".join(group["arxiv_clause"] for group in expanded_groups)

    mesh_descriptors = dedupe_preserve_order(flat_mesh_descriptors)
    mesh_terms = dedupe_preserve_order(flat_mesh_terms)
    free_terms = dedupe_preserve_order(flat_free_terms)

    return ExpandedQuery(
        original_keyword=keyword,
        mesh_descriptor=mesh_descriptors[0] if len(mesh_descriptors) == 1 else None,
        mesh_uri=None,
        mesh_terms=mesh_terms,
        free_terms=free_terms,
        pubmed_query=pubmed_query,
        arxiv_query=arxiv_query,
        query_mode=query_mode,
        parsed_groups=parsed_groups,
        expanded_groups=expanded_groups,
        mesh_descriptors=mesh_descriptors,
    )
