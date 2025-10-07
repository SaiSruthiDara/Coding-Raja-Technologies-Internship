from __future__ import annotations
import io
import os
from pathlib import Path
from typing import Optional

from gtts import gTTS

from .config import CONFIG
from .utils import unique_path


class TTSProvider:
    def synthesize(self, text: str, out_dir: str, voice: Optional[str] = None) -> str:
        raise NotImplementedError


class GTTSProvider(TTSProvider):
    def synthesize(self, text: str, out_dir: str, voice: Optional[str] = None) -> str:
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        out_mp3 = unique_path(out_dir, "narration", ".mp3")
        tts = gTTS(text=text)
        tts.save(out_mp3)
        return out_mp3


class ElevenLabsProvider(TTSProvider):
    def __init__(self):
        try:
            from elevenlabs.client import ElevenLabs
        except Exception:  # pragma: no cover - optional dependency
            self._client = None
            return
        api_key = CONFIG.elevenlabs_api_key
        self._client = ElevenLabs(api_key=api_key) if api_key else None

    def synthesize(self, text: str, out_dir: str, voice: Optional[str] = None) -> str:
        if not self._client:
            raise RuntimeError("ElevenLabs not configured. Set ELEVENLABS_API_KEY.")
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        out_mp3 = unique_path(out_dir, "narration", ".mp3")
        voice_id = voice or CONFIG.elevenlabs_voice_id
        audio = self._client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format={"codec": "mp3", "sample_rate": 44100},
            text=text,
        )
        with open(out_mp3, "wb") as f:
            for chunk in audio:
                if chunk:
                    f.write(chunk)
        return out_mp3


class PollyProvider(TTSProvider):
    def __init__(self):
        try:
            import boto3
        except Exception:  # pragma: no cover
            self._client = None
            return
        self._client = boto3.client("polly", region_name=CONFIG.aws_region)

    def synthesize(self, text: str, out_dir: str, voice: Optional[str] = None) -> str:
        if not self._client:
            raise RuntimeError("AWS Polly not configured. Install boto3 and set AWS creds.")
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        out_mp3 = unique_path(out_dir, "narration", ".mp3")
        voice_id = voice or "Joanna"
        response = self._client.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId=voice_id)
        audio_stream = response.get("AudioStream")
        if audio_stream:
            with open(out_mp3, "wb") as f:
                f.write(audio_stream.read())
        return out_mp3


def get_tts_provider(name: str | None = None) -> TTSProvider:
    provider = (name or CONFIG.tts_provider).lower()
    if provider == "elevenlabs":
        return ElevenLabsProvider()
    if provider == "polly":
        return PollyProvider()
    return GTTSProvider()
