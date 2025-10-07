import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass
class AppConfig:
    output_dir: str = os.getenv("OUTPUT_DIR", "outputs")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    tts_provider: str = os.getenv("TTS_PROVIDER", "gtts").lower()

    # ElevenLabs
    elevenlabs_api_key: str | None = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_voice_id: str | None = os.getenv("ELEVENLABS_VOICE_ID")

    # AWS
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")

    # Video
    width: int = int(os.getenv("VIDEO_WIDTH", "1280"))
    height: int = int(os.getenv("VIDEO_HEIGHT", "720"))
    fps: int = int(os.getenv("FPS", "24"))

    def ensure_output(self) -> str:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        return self.output_dir


CONFIG = AppConfig()
