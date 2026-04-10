from paper_radar.synthesis import build_one_liner


def test_build_one_liner_returns_text():
    abstract = (
        "We developed a multimodal model using CT and pathology features. "
        "The proposed approach significantly improved prediction accuracy."
    )
    line = build_one_liner("Example paper", abstract)
    assert "Method" in line
    assert "Innovation" in line or "Method/innovation" in line
