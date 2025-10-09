from __future__ import annotations

import os
from typing import Iterable, List, Sequence, Tuple

try:
    # Prefer MoviePy v2 API
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, vfx as VFX  # type: ignore
except Exception:  # pragma: no cover
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, vfx as VFX  # type: ignore


def build_video(
    slide_image_paths: Sequence[str],
    audio_paths: Sequence[str],
    durations: Sequence[float],
    output_path: str,
    fps: int = 30,
    resolution: Tuple[int, int] = (1280, 720),
    transition: float = 0.6,
) -> None:
    if not slide_image_paths:
        raise ValueError("No slides provided")
    if not audio_paths or len(audio_paths) != len(slide_image_paths):
        # Allow mismatch by padding silence handled by duration
        pass

    width, height = resolution

    def _with_duration(clip, seconds: float):
        try:
            return clip.with_duration(seconds)
        except Exception:
            return clip.set_duration(seconds)

    def _with_audio(clip, audio):
        try:
            return clip.with_audio(audio)
        except Exception:
            return clip.set_audio(audio)

    def _resize(clip, size):
        # Try applying resize via effect API
        try:
            return clip.fx(VFX.resize, newsize=size)
        except Exception:
            pass
        # Try v2 effects list API
        try:
            return clip.with_effects([VFX.resize(newsize=size)])  # type: ignore[attr-defined]
        except Exception:
            pass
        # Fallback to legacy resize
        try:
            return clip.resize(newsize=size)
        except Exception:
            return clip

    def _fade(clip, fin: float, fout: float):
        out = clip
        # Try effect function API
        try:
            if fin > 0:
                out = out.fx(VFX.fadein, fin)
            if fout > 0:
                out = out.fx(VFX.fadeout, fout)
            return out
        except Exception:
            pass
        # Try v2 with_effects API
        try:
            effects = []
            if fin > 0:
                effects.append(VFX.fadein(fin))
            if fout > 0:
                effects.append(VFX.fadeout(fout))
            if effects:
                out = out.with_effects(effects)  # type: ignore[attr-defined]
            return out
        except Exception:
            pass
        # Fallback to legacy methods
        try:
            if fin > 0:
                out = out.fadein(fin)
            if fout > 0:
                out = out.fadeout(fout)
            return out
        except Exception:
            return clip

    clips: list = []
    for idx, slide_path in enumerate(slide_image_paths):
        duration = max(2.0, durations[idx] if idx < len(durations) else 2.0)
        img_clip = ImageClip(slide_path)
        img_clip = _with_duration(img_clip, duration)
        img_clip = _resize(img_clip, resolution)
        if idx < len(audio_paths):
            try:
                audio_clip = AudioFileClip(audio_paths[idx])
                img_clip = _with_audio(img_clip, audio_clip)
            except Exception:
                pass
        img_clip = _fade(img_clip, 0.2, transition)
        clips.append(img_clip)

    try:
        final = concatenate_videoclips(clips, method="compose", padding=-transition)
    except Exception:
        final = concatenate_videoclips(clips, method="compose")

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")

    # Close resources
    for c in clips:
        try:
            if c.audio:
                c.audio.close()
            c.close()
        except Exception:
            pass
    try:
        final.close()
    except Exception:
        pass
