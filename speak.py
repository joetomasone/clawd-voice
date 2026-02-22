"""Text-to-speech using ElevenLabs with streaming playback."""

import io
import tempfile
import requests


class Speaker:
    def __init__(self, api_key: str, voice_id: str, model: str = "eleven_turbo_v2_5",
                 stability: float = 0.6, similarity_boost: float = 0.8, audio_player=None):
        self.api_key = api_key
        self.voice_id = voice_id
        self.model = model
        self.stability = stability
        self.similarity_boost = similarity_boost
        self.audio_player = audio_player
        self.url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    def speak(self, text: str):
        """Convert text to speech and play through system audio.
        
        Uses ElevenLabs streaming API → saves to temp file → plays with cross-platform player.
        """
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": {
                "stability": self.stability,
                "similarity_boost": self.similarity_boost,
            },
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                stream=True,
                timeout=15,
            )
            response.raise_for_status()

            # Write streaming MP3 to temp file, then play
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        f.write(chunk)
                temp_path = f.name

            # Play with cross-platform audio player
            if self.audio_player:
                self.audio_player.play(temp_path)
            else:
                # Fallback for backwards compatibility
                import subprocess
                subprocess.run(["afplay", temp_path], check=True)

            # Clean up
            import os
            os.unlink(temp_path)

        except Exception as e:
            print(f"TTS/playback error: {e}")
