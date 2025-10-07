from __future__ import annotations
from pathlib import Path
from typing import List
import matplotlib.pyplot as plt

from ..models import GraphSpec, GraphSeries
from ..utils import unique_path


def render_graph(graph: GraphSpec, out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    stem = (graph.title or f"graph-{graph.type}").lower().replace(" ", "-")[:40]
    out_png = unique_path(out_dir, stem or "graph", ".png")

    plt.figure(figsize=(12, 6), dpi=150)

    if graph.type in {"bar", "line", "scatter"}:
        for s in graph.series:
            _plot_series(graph.type, s)
        if graph.x_label:
            plt.xlabel(graph.x_label)
        if graph.y_label:
            plt.ylabel(graph.y_label)
        if graph.title:
            plt.title(graph.title)
        if len(graph.series) > 1:
            plt.legend()
    elif graph.type == "pie":
        series = graph.series[0] if graph.series else GraphSeries(name="values", x=[], y=[])
        plt.pie(series.y, labels=series.x, autopct="%1.1f%%")
        if graph.title:
            plt.title(graph.title)

    plt.tight_layout()
    plt.savefig(out_png)
    plt.close()
    return out_png


def _plot_series(kind: str, s: GraphSeries) -> None:
    if kind == "bar":
        plt.bar(s.x, s.y, label=s.name)
    elif kind == "line":
        plt.plot(s.x, s.y, marker="o", label=s.name)
    elif kind == "scatter":
        plt.scatter(s.x, s.y, label=s.name)
