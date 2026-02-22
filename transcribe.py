"""Speech-to-text using OpenAI Whisper API."""

import io
import wave
from openai import OpenAI


class Transcriber:
    def __init__(self, provider: str = "openai", api_key: str = "", model: str = "whisper-1"):
        self.provider = provider
        self.model = model
        self.client = OpenAI(api_key=api_key)

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw PCM audio bytes to text.
        
        Args:
            audio_bytes: Raw PCM 16-bit mono audio
            sample_rate: Sample rate of the audio
            
        Returns:
            Transcribed text string
        """
        # Convert raw PCM to WAV in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)

        wav_buffer.seek(0)
        wav_buffer.name = "recording.wav"  # OpenAI needs a filename

        try:
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=wav_buffer,
            )
            return result.text
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
