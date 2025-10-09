from __future__ import annotations

import argparse
import json
import os
import time
from typing import List, Optional, Tuple

from .pdf import extract_text_from_pdf
from .llm import Plan, Section, structure_content
from .visuals.textslides import render_text_slide
from .visuals.flowcharts import render_flowchart
from .visuals.charts import render_chart_from_spec
from .tts import synthesize_speech
from .video import build_video


DEFAULT_RESOLUTION = (1280, 720)


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an educational video from a topic or PDF"
    )
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--topic", type=str, help="Topic to generate a video for")
    g.add_argument("--pdf", type=str, help="Path to a PDF file (<=60MB)")

    parser.add_argument("--output", type=str, default="outputs", help="Output root directory")
    parser.add_argument("--engine", type=str, default="gtts", choices=["gtts", "elevenlabs", "polly", "none"], help="TTS engine")
    parser.add_argument("--voice", type=str, default=None, help="Voice name/id for TTS engine")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second")
    parser.add_argument("--transition", type=float, default=0.6, help="Crossfade duration in seconds")
    parser.add_argument("--resolution", type=str, default="1280x720", help="Resolution WxH, e.g. 1920x1080")
    parser.add_argument("--mock-llm", action="store_true", help="Force mock content structuring (no external API)")
    parser.add_argument("--max-mb", type=int, default=60, help="Max PDF size in MB")

    return parser.parse_args()


def _parse_resolution(s: str) -> tuple[int, int]:
    try:
        w, h = s.lower().split("x")
        return int(w), int(h)
    except Exception:
        return DEFAULT_RESOLUTION


def _collect_narration_for_slide(section: Section, slide_kind: str) -> str:
    if slide_kind == "text":
        return f"{section.title}. " + ". ".join(section.bullets)
    if slide_kind == "flowchart" and section.flowchart:
        return f"{section.flowchart.title}. " + ". ".join(section.flowchart.steps)
    return section.title


def main() -> None:
    args = parse_args()

    resolution = _parse_resolution(args.resolution)
    ts = time.strftime("%Y%m%d_%H%M%S")

    # Prepare output directories
    out_root = os.path.abspath(args.output)
    frames_dir = os.path.join(out_root, "frames", ts)
    audio_dir = os.path.join(out_root, "audio", ts)
    video_dir = os.path.join(out_root, "videos")
    plan_dir = os.path.join(out_root, "plans")

    for d in (frames_dir, audio_dir, video_dir, plan_dir):
        _ensure_dir(d)

    # Step 1: Get source text
    topic: Optional[str] = None
    raw_text: Optional[str] = None
    if args.topic:
        topic = args.topic
    else:
        raw_text = extract_text_from_pdf(args.pdf, max_megabytes=args.max_mb)
        topic = os.path.splitext(os.path.basename(args.pdf))[0]

    print("Structuring content ...")
    plan: Plan = structure_content(topic=topic, raw_text=raw_text, use_mock=args.mock_llm)

    # Persist plan for reproducibility
    plan_path = os.path.join(plan_dir, f"{ts}_{plan.topic.replace(' ', '_')}.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan.model_dump_json(indent=2))

    # Step 2: Generate slides and narration texts
    slide_paths: list[str] = []
    narration_texts: list[str] = []

    section_index = 0
    for section in plan.sections:
        section_index += 1
        # Text slide
        text_slide_path = os.path.join(frames_dir, f"{section_index:02d}_text.png")
        render_text_slide(section.title, section.bullets, text_slide_path, size=resolution)
        slide_paths.append(text_slide_path)
        narration_texts.append(_collect_narration_for_slide(section, "text"))

        # Flowchart slide if present
        if section.flowchart:
            flow_path = os.path.join(frames_dir, f"{section_index:02d}_flow.png")
            try:
                render_flowchart(section.flowchart.steps, flow_path)
                slide_paths.append(flow_path)
                narration_texts.append(_collect_narration_for_slide(section, "flowchart"))
            except Exception as e:
                # Fallback: render a text slide describing the flowchart
                fallback_path = os.path.join(frames_dir, f"{section_index:02d}_flow_fallback.png")
                bullets = [f"Flowchart: {section.flowchart.title}"] + section.flowchart.steps
                render_text_slide(section.title, bullets, fallback_path, size=resolution)
                slide_paths.append(fallback_path)
                narration_texts.append(_collect_narration_for_slide(section, "flowchart"))

        # Chart slides if present
        if section.charts:
            chart_idx = 0
            for chart in section.charts:
                chart_idx += 1
                chart_path = os.path.join(frames_dir, f"{section_index:02d}_chart_{chart_idx}.png")
                try:
                    render_chart_from_spec(chart, chart_path, size=resolution)
                except Exception:
                    # fallback to text slide describing chart
                    bullets = [
                        f"Chart: {chart.title}",
                        f"Type: {chart.chart_type}",
                    ]
                    chart_path = os.path.join(frames_dir, f"{section_index:02d}_chart_{chart_idx}_fallback.png")
                    render_text_slide(section.title, bullets, chart_path, size=resolution)
                slide_paths.append(chart_path)
                narration_texts.append(section.title + ". " + chart.title)

    # Step 3: TTS generation
    print("Generating narration audio ...")
    audio_paths, durations = synthesize_speech(
        texts=narration_texts,
        out_dir=audio_dir,
        engine=args.engine,
        voice=args.voice,
    )

    # Step 4: Video assembly
    video_filename = f"{ts}_{plan.topic.replace(' ', '_')}.mp4"
    output_video_path = os.path.join(video_dir, video_filename)
    print("Assembling video ...")
    build_video(
        slide_image_paths=slide_paths,
        audio_paths=audio_paths,
        durations=durations,
        output_path=output_video_path,
        fps=args.fps,
        resolution=resolution,
        transition=args.transition,
    )

    print(f"Done. Video saved to: {output_video_path}")


if __name__ == "__main__":
    main()
