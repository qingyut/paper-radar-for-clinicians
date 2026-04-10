from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from paper_radar.utils import parse_date_guess


def build_trend_dataframe(papers: list[dict]) -> pd.DataFrame:
    rows = []
    for p in papers:
        dt = parse_date_guess(p.get("published"))
        if dt is None:
            continue
        rows.append(
            {
                "date": dt.date().isoformat(),
                "source": p.get("source"),
                "count": 1,
            }
        )

    if not rows:
        return pd.DataFrame(columns=["date", "source", "count"])

    df = pd.DataFrame(rows)
    df = df.groupby(["date", "source"], as_index=False)["count"].sum()
    return df.sort_values(["date", "source"])


def make_trend_figure(df: pd.DataFrame, cfg: dict) -> go.Figure:
    colors = cfg["visual"]["theme"]
    fig = go.Figure()

    if df.empty:
        fig.add_annotation(
            text="No dated records available for trend chart",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(size=18, color=colors["text_dark"]),
        )
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="white",
        )
        return fig

    pivot = (
        df.pivot_table(index="date", columns="source", values="count", aggfunc="sum", fill_value=0)
        .reset_index()
        .sort_values("date")
    )
    pivot["total"] = pivot.drop(columns=["date"]).sum(axis=1)
    pivot["rolling_7d"] = pivot["total"].rolling(7, min_periods=1).mean()

    if "pubmed" in pivot.columns:
        fig.add_trace(
            go.Bar(
                x=pivot["date"],
                y=pivot["pubmed"],
                name="PubMed",
                marker=dict(
                    color=colors["pubmed"],
                    line=dict(color="rgba(255,255,255,0.9)", width=1),
                    pattern=dict(shape=""),
                ),
                opacity=0.92,
                hovertemplate="Date=%{x}<br>PubMed=%{y}<extra></extra>",
            )
        )
    if "arxiv" in pivot.columns:
        fig.add_trace(
            go.Bar(
                x=pivot["date"],
                y=pivot["arxiv"],
                name="arXiv",
                marker=dict(
                    color=colors["arxiv"],
                    line=dict(color="rgba(255,255,255,0.9)", width=1),
                ),
                opacity=0.90,
                hovertemplate="Date=%{x}<br>arXiv=%{y}<extra></extra>",
            )
        )

    fig.add_trace(
        go.Scatter(
            x=pivot["date"],
            y=pivot["rolling_7d"],
            name="7-day rolling mean",
            mode="lines+markers",
            line=dict(color=colors["accent"], width=4, shape="spline", smoothing=0.55),
            marker=dict(size=7, color=colors["accent"], line=dict(color="white", width=1.5)),
            yaxis="y2",
            hovertemplate="Date=%{x}<br>Rolling mean=%{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        barmode="stack",
        template="plotly_white",
        title=dict(
            text="Recent publication volume",
            x=0.01,
            xanchor="left",
            font=dict(size=24, color=colors["text_dark"]),
        ),
        paper_bgcolor="rgba(255,255,255,0)",
        plot_bgcolor="white",
        font=dict(color=colors["text_dark"], family="Inter, Segoe UI, Arial, sans-serif"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            bgcolor="rgba(255,255,255,0.75)",
            bordercolor="rgba(148,163,184,0.18)",
            borderwidth=1,
        ),
        margin=dict(l=30, r=30, t=80, b=30),
        xaxis=dict(
            title=None,
            showgrid=False,
            tickangle=-25,
            showline=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="Papers per day",
            showgrid=True,
            gridcolor="rgba(148,163,184,0.18)",
            zeroline=False,
            rangemode="tozero",
        ),
        yaxis2=dict(
            title="7-day rolling mean",
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            rangemode="tozero",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.94)",
            font_color="white",
            bordercolor="rgba(15,23,42,0.94)",
        ),
    )
    return fig
