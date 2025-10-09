from __future__ import annotations

from typing import Tuple
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from ..llm import ChartSpec


sns.set_theme(style="whitegrid")


def render_chart_from_spec(chart: ChartSpec, output_path: str, size: Tuple[int, int] = (1280, 720)) -> None:
    width, height = size
    dpi = 100
    fig_width = width / dpi
    fig_height = height / dpi

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=dpi)
    ax.set_title(chart.title)

    if chart.chart_type.lower() == "bar":
        for idx, series in enumerate(chart.series):
            sns.barplot(x=chart.x_labels, y=series.values, ax=ax, label=series.name)
    elif chart.chart_type.lower() == "line":
        for series in chart.series:
            ax.plot(chart.x_labels, series.values, marker="o", label=series.name)
    else:
        raise ValueError(f"Unsupported chart type: {chart.chart_type}")

    if any(s.name for s in chart.series) and len(chart.series) > 1:
        ax.legend()

    plt.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
