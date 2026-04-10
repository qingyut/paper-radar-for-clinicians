from __future__ import annotations

from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from paper_radar.utils import ensure_dir


def _env(template_dir: Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def write_csv(papers: list[dict], outdir: str | Path) -> Path:
    outdir = ensure_dir(outdir)
    csv_path = outdir / "papers.csv"

    df = pd.DataFrame(papers)
    df.to_csv(csv_path, index=False)

    return csv_path


def render_report(
    *,
    outdir: str | Path,
    keyword: str,
    expanded_query: dict,
    papers: list[dict],
    cfg: dict,
    chart_html_fragment: str | None = None,
) -> tuple[Path, Path]:
    outdir = ensure_dir(outdir)
    template_dir = Path(__file__).parent / "templates"
    env = _env(template_dir)
    template = env.get_template("report.html.j2")

    top_n = int(cfg["reporting"]["top_n_in_report"])
    highlight_n = int(cfg["reporting"]["top_n_highlight"])
    rendered = template.render(
        keyword=keyword,
        expanded_query=expanded_query,
        papers=papers[:top_n],
        highlights=papers[:highlight_n],
        chart_html_fragment=chart_html_fragment,
        weights=cfg["ranking"]["weights"],
        theme=cfg["visual"]["theme"],
    )
    html_path = outdir / "report.html"
    html_path.write_text(rendered, encoding="utf-8")

    md_lines = [f"# Literature radar: {keyword}", ""]
    md_lines.append("## Expanded query")
    md_lines.append("")
    md_lines.append(f"- Original keyword: {expanded_query.get('original_keyword')}")
    md_lines.append(f"- Query mode: {expanded_query.get('query_mode', 'simple')}")
    md_lines.append(f"- MeSH descriptors: {', '.join(expanded_query.get('mesh_descriptors', []))}")
    md_lines.append(f"- MeSH terms: {', '.join(expanded_query.get('mesh_terms', []))}")
    parsed_groups = expanded_query.get('parsed_groups', []) or []
    if parsed_groups:
        md_lines.append("- Parsed groups:")
        for idx, group in enumerate(parsed_groups, 1):
            md_lines.append(f"  - Group {idx}: {', '.join(group)}")
    md_lines.append("")
    md_lines.append("## Top papers")
    md_lines.append("")
    for i, p in enumerate(papers[:top_n], 1):
        md_lines.append(f"### {i}. {p['title']}")
        md_lines.append(f"- Source: {p['source']}")
        md_lines.append(f"- Published: {p['published']}")
        md_lines.append(f"- Score: {p['final_score']:.3f}")
        md_lines.append(f"- URL: {p['url']}")
        md_lines.append(f"- One-liner: {p['method_innovation_one_liner']}")
        md_lines.append("")

    md_path = outdir / "report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return html_path, md_path
