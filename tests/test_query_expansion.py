from paper_radar.query_expansion import build_expanded_query


class DummyMesh:
    def find_best_descriptor(self, keyword: str):
        mapping = {
            "gallbladder cancer": {"label": "Gallbladder Neoplasms", "uri": "mesh:g"},
            "pathology": {"label": "Pathology", "uri": "mesh:p"},
        }
        return mapping.get(keyword)

    def get_entry_terms(self, uri: str):
        mapping = {
            "mesh:g": ["Gallbladder Neoplasm"],
            "mesh:p": ["Histopathology"],
        }
        return mapping.get(uri, [])


def test_build_expanded_query_grouped_mode():
    expanded = build_expanded_query(
        '(gallbladder cancer OR gallbladder neoplasms) AND (multimodal) AND (pathology OR histopathology)',
        DummyMesh(),
    )
    assert expanded.query_mode == "grouped"
    assert expanded.parsed_groups[0] == ["gallbladder cancer", "gallbladder neoplasms"]
    assert len(expanded.expanded_groups) == 3
    assert "AND" in expanded.pubmed_query
    assert "+AND+" in expanded.arxiv_query
