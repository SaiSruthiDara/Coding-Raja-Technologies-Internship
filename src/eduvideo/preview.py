from __future__ import annotations
from pathlib import Path
from typing import Optional

from .config import CONFIG
from .pdf_extractor import extract_text_from_pdf
from .summarizer import summarize
from .visuals.flowcharts import render_flowchart
from .visuals.graphs import render_graph
from .slides import render_slide_image
from .models import SceneSpec
from .utils import ensure_dir


def preview_from_pdf(pdf_path: str, out_dir: Optional[str] = None, provider: Optional[str] = None) -> str:
    text = extract_text_from_pdf(pdf_path)
    topic = Path(pdf_path).stem
    return preview_from_text(topic=topic, text=text, out_dir=out_dir, provider=provider)


def preview_from_text(topic: str, text: str, out_dir: Optional[str] = None, provider: Optional[str] = None) -> str:
    out_dir = out_dir or (Path(CONFIG.output_dir) / (topic.replace(" ", "-").lower() + "-preview")).as_posix()
    ensure_dir(out_dir)

    project = summarize(topic=topic, text=text, provider=provider)
    if not project.scenes:
        raise RuntimeError("No scenes generated for preview")
    scene: SceneSpec = project.scenes[0]

    vdir = Path(out_dir) / "scene_01"
    vdir.mkdir(parents=True, exist_ok=True)

    # Render visuals without importing moviepy
    visual_paths = []
    for v in scene.visuals:
        if v.kind == "flowchart" and v.flowchart:
            visual_paths.append(render_flowchart(v.flowchart, str(vdir)))
        elif v.kind == "graph" and v.graph:
            visual_paths.append(render_graph(v.graph, str(vdir)))
    slide_path = render_slide_image(scene, visual_paths, str(vdir))

    struct_path = Path(out_dir) / "structure.json"
    struct_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    return slide_path
