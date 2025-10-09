from __future__ import annotations

import os
from typing import Iterable, List, Optional, Tuple

from gtts import gTTS

try:
    from elevenlabs import generate, save, set_api_key as eleven_set_api_key
except Exception:  # pragma: no cover
    generate = None
    save = None
    eleven_set_api_key = None

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


def _safe_filename(index: int) -> str:
    return f"seg_{index:03d}.mp3"


def synthesize_speech(
    texts: Iterable[str],
    out_dir: str,
    engine: str = "gtts",
    voice: Optional[str] = None,
) -> tuple[list[str], list[float]]:
    os.makedirs(out_dir, exist_ok=True)

    audio_paths: list[str] = []
    durations: list[float] = []

    for idx, text in enumerate(texts, start=1):
        filename = _safe_filename(idx)
        out_path = os.path.join(out_dir, filename)

        if engine == "gtts":
            tts = gTTS(text=text or " ", lang="en")
            tts.save(out_path)
        elif engine == "elevenlabs" and generate is not None and save is not None:
            api_key = os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY")
            if api_key and eleven_set_api_key is not None:
                eleven_set_api_key(api_key)
            audio = generate(text=text or " ", voice=voice or "Rachel", model="eleven_monolingual_v1")
            save(audio, out_path)
        elif engine == "polly" and boto3 is not None:
            polly = boto3.client("polly")
            voice_id = voice or "Joanna"
            response = polly.synthesize_speech(Text=text or " ", OutputFormat="mp3", VoiceId=voice_id)
            with open(out_path, "wb") as f:
                f.write(response["AudioStream"].read())
        elif engine == "none":
            # Create a silent placeholder of fixed length
            from pydub import AudioSegment  # type: ignore
            silence = AudioSegment.silent(duration=1500)  # 1.5 seconds
            silence.export(out_path, format="mp3")
        else:
            # fallback to gtts
            tts = gTTS(text=text or " ", lang="en")
            tts.save(out_path)

        # Compute duration via mutagen
        try:
            from mutagen.mp3 import MP3  # type: ignore

            audio = MP3(out_path)
            durations.append(float(audio.info.length))
        except Exception:
            durations.append(1.5)

        audio_paths.append(out_path)

    return audio_paths, durations
