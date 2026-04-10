from __future__ import annotations

import os
from pathlib import Path

from paper_radar.plotting import build_trend_dataframe, make_trend_figure
from paper_radar.query_expansion import build_expanded_query
from paper_radar.ranking import apply_ranking
from paper_radar.reporting import render_report, write_csv
from paper_radar.sources import ArxivClient, MeSHClient, PubMedClient
from paper_radar.synthesis import build_one_liner
from paper_radar.utils import ensure_dir, json_dump, stable_paper_id, utc_now


def dedupe_papers(papers):
    seen = {}
    out = []
    for paper in papers:
        key = (paper.doi or "").lower().strip()
        if not key:
            normalized_title = paper.title.lower().strip()
            key = f"title:{normalized_title}"
        if key in seen:
            continue
        seen[key] = True
        out.append(paper)
    return out


def run_topic(
    *,
    keyword: str,
    days: int,
    weights_path: str | Path,
    outdir: str | Path,
    max_results_pubmed: int = 120,
    max_results_arxiv: int = 80,
    ncbi_email: str | None = None,
) -> dict:
    from paper_radar.config import load_yaml

    cfg = load_yaml(weights_path)
    outdir = ensure_dir(outdir)

    mesh = MeSHClient()
    pubmed = PubMedClient(
        email=ncbi_email,
        api_key=os.getenv("NCBI_API_KEY"),
    )
    arxiv = ArxivClient()

    expanded = build_expanded_query(keyword, mesh)

    papers = []
    papers.extend(pubmed.search(expanded.pubmed_query, days=days, retmax=max_results_pubmed))
    papers.extend(arxiv.search(expanded.arxiv_query, days=days, max_results=max_results_arxiv))
    papers = dedupe_papers(papers)

    for paper in papers:
        paper.method_innovation_one_liner = build_one_liner(paper.title, paper.abstract)

    papers = apply_ranking(papers, expanded, cfg, horizon_days=days)

    serializable = []
    for p in papers:
        obj = p.to_dict()
        obj["record_uid"] = stable_paper_id(p.source, p.source_id, p.title)
        serializable.append(obj)

    csv_path = write_csv(serializable, outdir)

    trend_df = build_trend_dataframe(serializable)
    fig = make_trend_figure(trend_df, cfg)
    chart_html_fragment = fig.to_html(
        include_plotlyjs="cdn",
        full_html=False,
        config={
            "displayModeBar": False,
            "responsive": True,
            "scrollZoom": False,
        },
    )

    report_html, report_md = render_report(
        outdir=outdir,
        keyword=keyword,
        expanded_query=expanded.to_dict(),
        papers=serializable,
        cfg=cfg,
        chart_html_fragment=chart_html_fragment,
    )

    for stale_name in ("papers.json", "trend.html", "trend.png", "report.pdf"):
        stale_path = outdir / stale_name
        if stale_path.exists():
            stale_path.unlink()

    metadata = {
        "keyword": keyword,
        "days": days,
        "expanded_query": expanded.to_dict(),
        "n_records": len(serializable),
        "generated_at_utc": utc_now().isoformat(),
        "files": {
            "csv": csv_path.name,
            "report_html": report_html.name,
            "report_md": report_md.name,
        },
    }
    json_dump(outdir / "run_metadata.json", metadata)
    return metadata
