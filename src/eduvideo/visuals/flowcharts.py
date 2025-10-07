from __future__ import annotations
from pathlib import Path
from typing import List
from graphviz import Digraph

from ..models import FlowchartSpec
from ..utils import unique_path


def render_flowchart(flowchart: FlowchartSpec, out_dir: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    stem = (flowchart.title or "flowchart").lower().replace(" ", "-")[:40] or "flowchart"
    out_png = unique_path(out_dir, stem, ".png")

    dot = Digraph(comment=flowchart.title or "Flowchart", format="png")
    dot.attr(rankdir="LR", fontsize="12", labelloc="t", label=flowchart.title or "")

    # Ensure unique node ids
    node_ids: List[str] = []
    for idx, label in enumerate(flowchart.nodes):
        node_id = f"n{idx}"
        node_ids.append(node_id)
        dot.node(node_id, label)

    # Map labels to ids for edges when possible
    label_to_id = {label: node_ids[i] for i, label in enumerate(flowchart.nodes)}
    for edge in flowchart.edges:
        src = label_to_id.get(edge.source, edge.source)
        tgt = label_to_id.get(edge.target, edge.target)
        if edge.label:
            dot.edge(src, tgt, label=edge.label)
        else:
            dot.edge(src, tgt)

    tmp = Path(out_png).with_suffix("")
    dot.render(filename=str(tmp), cleanup=True)
    return out_png
