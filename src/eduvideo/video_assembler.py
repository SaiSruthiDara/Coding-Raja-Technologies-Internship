from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips

from .config import CONFIG
from .models import ProjectSpec, SceneSpec, VisualSpec
from .tts import get_tts_provider
from .visuals.flowcharts import render_flowchart
from .visuals.graphs import render_graph
from .slides import render_slide_image
from .utils import ensure_dir


@dataclass
class SceneOutput:
    slide_path: str
    audio_path: str
    duration: float


def render_visuals(scene: SceneSpec, out_dir: str) -> List[str]:
    visual_paths: List[str] = []
    vdir = Path(out_dir) / "visuals"
    vdir.mkdir(parents=True, exist_ok=True)
    for v in scene.visuals:
        if v.kind == "flowchart" and v.flowchart:
            visual_paths.append(render_flowchart(v.flowchart, str(vdir)))
        elif v.kind == "graph" and v.graph:
            visual_paths.append(render_graph(v.graph, str(vdir)))
    return visual_paths


def render_scene_assets(scene: SceneSpec, out_dir: str, tts_provider: str | None = None) -> SceneOutput:
    out_dir = ensure_dir(out_dir)
    tts = get_tts_provider(tts_provider)

    # 1) visuals -> 2) slide -> 3) audio
    visuals = render_visuals(scene, out_dir)
    slide_path = render_slide_image(scene, visuals, out_dir)
    audio_path = tts.synthesize(scene.narration, out_dir)

    audio_clip = AudioFileClip(audio_path)
    duration = float(audio_clip.duration)
    audio_clip.close()

    return SceneOutput(slide_path=slide_path, audio_path=audio_path, duration=duration)


def assemble_video(project: ProjectSpec, out_dir: str, tts_provider: str | None = None) -> str:
    out_path = Path(ensure_dir(out_dir))
    clips = []

    scene_outputs: List[SceneOutput] = []
    for idx, scene in enumerate(project.scenes, start=1):
        sdir = out_path / f"scene_{idx:02d}"
        sdir.mkdir(parents=True, exist_ok=True)
        scene_output = render_scene_assets(scene, str(sdir), tts_provider=tts_provider)
        scene_outputs.append(scene_output)

    # Build video clips
    for so in scene_outputs:
        img_clip = ImageClip(so.slide_path, duration=so.duration)
        audio_clip = AudioFileClip(so.audio_path)
        img_clip = img_clip.set_audio(audio_clip).set_duration(audio_clip.duration)
        img_clip = img_clip.resize((CONFIG.width, CONFIG.height))
        clips.append(img_clip)

    final = concatenate_videoclips(clips, method="compose")
    out_mp4 = str(out_path / "video.mp4")
    final.write_videofile(out_mp4, fps=CONFIG.fps, codec="libx264", audio_codec="aac")

    # Close resources
    final.close()
    for c in clips:
        try:
            c.audio.close()
        except Exception:
            pass
        c.close()

    return out_mp4
