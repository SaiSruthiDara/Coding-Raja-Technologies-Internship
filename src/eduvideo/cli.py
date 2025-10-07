from __future__ import annotations
import argparse
import json
from pathlib import Path

from .config import CONFIG
from .pdf_extractor import extract_text_from_pdf
from .summarizer import summarize
from .models import ProjectSpec
from .video_assembler import assemble_video
from .utils import ensure_dir


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate educational video from topic or PDF")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--topic", type=str, help="Topic prompt")
    src.add_argument("--pdf", type=str, help="Path to input PDF")
    src.add_argument("--text", type=str, help="Raw text input or path to .txt")

    parser.add_argument("--provider", type=str, default=None, help="Summarization provider: gemini|offline")
    parser.add_argument("--tts", type=str, default=None, help="TTS provider: gtts|elevenlabs|polly")
    parser.add_argument("--out", type=str, default=None, help="Output directory (default: outputs/<slug>)")

    args = parser.parse_args(argv)

    # Prepare input text and topic
    if args.pdf:
        text = extract_text_from_pdf(args.pdf)
        topic = args.topic or Path(args.pdf).stem
    elif args.text:
        if Path(args.text).exists():
            text = Path(args.text).read_text(encoding="utf-8")
            topic = args.topic or Path(args.text).stem
        else:
            text = args.text
            topic = args.topic or text.split(" ")[0][:40]
    else:
        # Topic-only -> treat topic as text too
        topic = args.topic
        text = args.topic

    out_dir = args.out or (Path(CONFIG.output_dir) / Path(topic.replace(" ", "-").lower()).stem).as_posix()
    ensure_dir(out_dir)

    # Summarize/structure
    project: ProjectSpec = summarize(topic=topic, text=text, provider=args.provider)

    # Persist structure
    struct_path = Path(out_dir) / "structure.json"
    struct_path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    # Assemble video
    video_path = assemble_video(project, out_dir=out_dir, tts_provider=args.tts)

    print(f"Video saved to: {video_path}")


if __name__ == "__main__":
    main()
