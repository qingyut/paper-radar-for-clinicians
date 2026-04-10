from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from paper_radar.config import load_yaml
from paper_radar.emailing import send_email_with_attachments
from paper_radar.engine import run_topic
from paper_radar.utils import ensure_dir, slugify

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _print_result_table(metadata: dict, outdir: Path) -> None:
    table = Table(title=f"paper-radar • {metadata['keyword']}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Days", str(metadata["days"]))
    table.add_row("Records", str(metadata["n_records"]))
    table.add_row("Output", str(outdir))
    descriptors = metadata["expanded_query"].get("mesh_descriptors") or []
    if descriptors:
        table.add_row("MeSH descriptors", ", ".join(descriptors[:4]) + (" ..." if len(descriptors) > 4 else ""))
    else:
        table.add_row("MeSH descriptors", "—")
    table.add_row("Query mode", str(metadata["expanded_query"].get("query_mode", "simple")))
    console.print(table)


def _send_report_email_if_requested(outdir: Path, keyword: str, email_to: str | None) -> None:
    if not email_to:
        return

    html = (outdir / "report.html").read_text(encoding="utf-8")
    send_email_with_attachments(
        to_email=email_to,
        subject=f"paper-radar digest • {keyword}",
        html_body=html,
        attachment_paths=[
            outdir / "report.html",
            outdir / "report.md",
            outdir / "papers.csv",
        ],
    )


@app.command()
def search(
    keyword: str = typer.Argument(..., help="Keyword to monitor."),
    days: int = typer.Option(30, "--days", min=1, help="Lookback window in days."),
    weights: Path = typer.Option("configs/default_weights.yml", "--weights", exists=True, readable=True),
    outdir: Path = typer.Option("outputs", "--outdir", help="Output directory."),
    max_results_pubmed: int = typer.Option(120, "--max-results-pubmed"),
    max_results_arxiv: int = typer.Option(80, "--max-results-arxiv"),
    ncbi_email: str | None = typer.Option(None, "--ncbi-email", help="Email passed to NCBI E-utilities."),
):
    final_outdir = ensure_dir(outdir / slugify(keyword))
    metadata = run_topic(
        keyword=keyword,
        days=days,
        weights_path=weights,
        outdir=final_outdir,
        max_results_pubmed=max_results_pubmed,
        max_results_arxiv=max_results_arxiv,
        ncbi_email=ncbi_email,
    )
    _print_result_table(metadata, final_outdir)


@app.command()
def report(
    keyword: str = typer.Argument(..., help="Keyword to monitor."),
    days: int = typer.Option(30, "--days", min=1, help="Lookback window in days."),
    weights: Path = typer.Option("configs/default_weights.yml", "--weights", exists=True, readable=True),
    outdir: Path = typer.Option("outputs", "--outdir", help="Output directory."),
    max_results_pubmed: int = typer.Option(120, "--max-results-pubmed"),
    max_results_arxiv: int = typer.Option(80, "--max-results-arxiv"),
    ncbi_email: str | None = typer.Option(None, "--ncbi-email"),
    email_to: str | None = typer.Option(None, "--email-to", help="Optional recipient email for this run."),
):
    final_outdir = ensure_dir(outdir / slugify(keyword))
    metadata = run_topic(
        keyword=keyword,
        days=days,
        weights_path=weights,
        outdir=final_outdir,
        max_results_pubmed=max_results_pubmed,
        max_results_arxiv=max_results_arxiv,
        ncbi_email=ncbi_email,
    )
    _print_result_table(metadata, final_outdir)
    console.print(f"[green]Report written:[/green] {final_outdir / 'report.html'}")

    if email_to:
        _send_report_email_if_requested(final_outdir, keyword, email_to)
        console.print(f"[green]Email requested:[/green] {email_to}")
    else:
        console.print("[yellow]No email sent.[/yellow] Add --email-to and SMTP env vars to deliver the report.")


@app.command()
def update(
    topics: Path = typer.Option(..., "--topics", exists=True, readable=True, help="Topic YAML file."),
    weights: Path = typer.Option("configs/default_weights.yml", "--weights", exists=True, readable=True),
    outdir: Path = typer.Option("weekly_reports", "--outdir"),
    email_to: str | None = typer.Option(None, "--email-to", help="Optional recipient email."),
    ncbi_email: str | None = typer.Option(None, "--ncbi-email"),
):
    cfg = load_yaml(topics)
    all_topics = cfg.get("topics", [])
    if not all_topics:
        raise typer.BadParameter("No topics found in topic YAML.")

    root_out = ensure_dir(outdir)
    summary_rows = []

    for item in all_topics:
        keyword = item["keyword"]
        topic_outdir = ensure_dir(root_out / item.get("out_slug", slugify(keyword)))
        metadata = run_topic(
            keyword=keyword,
            days=int(item.get("days", 30)),
            weights_path=weights,
            outdir=topic_outdir,
            max_results_pubmed=int(item.get("max_results_pubmed", 120)),
            max_results_arxiv=int(item.get("max_results_arxiv", 80)),
            ncbi_email=ncbi_email,
        )
        summary_rows.append((keyword, metadata["n_records"], str(topic_outdir / "report.html")))

        if email_to:
            _send_report_email_if_requested(topic_outdir, keyword, email_to)

    table = Table(title="Weekly update complete")
    table.add_column("Keyword", style="cyan")
    table.add_column("Records", justify="right")
    table.add_column("Report")
    for row in summary_rows:
        table.add_row(str(row[0]), str(row[1]), str(row[2]))
    console.print(table)

    if email_to:
        console.print(f"[green]Email requested:[/green] {email_to}")
    else:
        console.print("[yellow]No email sent.[/yellow] Add --email-to and SMTP env vars to deliver weekly digests.")


if __name__ == "__main__":
    app()
