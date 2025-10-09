from __future__ import annotations

import os
from typing import Iterable

from graphviz import Digraph


def render_flowchart(steps: Iterable[str], output_path: str) -> None:
    """
    Render a simple top-down flowchart with rectangular nodes.
    """
    steps = [s.strip() for s in steps if s and s.strip()]
    if not steps:
        raise ValueError("No steps provided for flowchart")

    base, ext = os.path.splitext(output_path)
    fmt = ext.lstrip(".") or "png"

    dot = Digraph(format=fmt)
    dot.attr(rankdir="TB", nodesep="0.4", ranksep="0.6")
    dot.attr("node", shape="box", style="rounded,filled", color="#334155", fillcolor="#e2e8f0", fontname="DejaVu Sans")
    dot.attr("edge", color="#64748b")

    prev_name = None
    for idx, step in enumerate(steps, start=1):
        node_name = f"n{idx}"
        dot.node(node_name, label=step)
        if prev_name is not None:
            dot.edge(prev_name, node_name)
        prev_name = node_name

    # Graphviz render writes to <base>.<fmt>
    tmp_path = dot.render(filename=base, cleanup=True)
    if tmp_path != output_path:
        # Ensure final extension matches requested output_path
        if os.path.exists(output_path):
            os.remove(output_path)
        os.replace(tmp_path, output_path)
