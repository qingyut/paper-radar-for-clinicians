from paper_radar.boolean_query import parse_keyword_groups


def test_parse_simple_phrase():
    assert parse_keyword_groups("gallbladder cancer") == [["gallbladder cancer"]]


def test_parse_grouped_boolean_expression():
    parsed = parse_keyword_groups(
        '(gallbladder cancer OR gallbladder neoplasms) AND (multimodal OR "multi-modal") AND (pathology OR histopathology)'
    )
    assert parsed == [
        ["gallbladder cancer", "gallbladder neoplasms"],
        ["multimodal", "multi-modal"],
        ["pathology", "histopathology"],
    ]
