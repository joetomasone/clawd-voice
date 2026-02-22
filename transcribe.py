"""Speech-to-text using FluidAudio (local) or OpenAI Whisper API (fallback)."""

import io
import os
import wave
import time
import subprocess
import tempfile
from openai import OpenAI


class FluidSTTEngine:
    """Local STT using FluidAudio/Parakeet (Apple Neural Engine)."""
    
    def __init__(self, binary_path: str):
        self.binary_path = os.path.expanduser(binary_path)
        if not os.path.exists(self.binary_path):
            raise FileNotFoundError(f"FluidSTT binary not found: {self.binary_path}")
    
    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio using local FluidSTT binary.
        
        Args:
            audio_bytes: Raw PCM 16-bit mono audio
            sample_rate: Sample rate of the audio
            
        Returns:
            Transcribed text string
        """
        # Create temporary WAV file (FluidSTT needs a file path)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit = 2 bytes
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)
        
        try:
            start = time.time()
            result = subprocess.run(
                [self.binary_path, tmp_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            elapsed = time.time() - start
            
            if result.returncode != 0:
                print(f"FluidSTT error (exit {result.returncode}): {result.stderr}")
                return ""
            
            # Parse output: timing info, then "---", then transcription on last line
            lines = result.stdout.strip().split('\n')
            if not lines:
                return ""
            
            # Find the separator line
            try:
                sep_idx = lines.index('---')
                # Transcription is everything after "---"
                transcript_lines = lines[sep_idx + 1:]
                transcript = ' '.join(transcript_lines).strip()
            except ValueError:
                # No separator found, assume last line is transcript
                transcript = lines[-1].strip()
            
            print(f"  FluidSTT: {elapsed:.2f}s")
            return transcript
            
        except subprocess.TimeoutExpired:
            print("FluidSTT timeout")
            return ""
        except Exception as e:
            print(f"FluidSTT error: {e}")
            return ""
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except:
                pass


class WhisperSTTEngine:
    """Cloud STT using OpenAI Whisper API."""
    
    def __init__(self, api_key: str, model: str = "whisper-1"):
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
            start = time.time()
            result = self.client.audio.transcriptions.create(
                model=self.model,
                file=wav_buffer,
            )
            elapsed = time.time() - start
            print(f"  Whisper API: {elapsed:.2f}s")
            return result.text
        except Exception as e:
            print(f"Whisper API error: {e}")
            return ""


class Transcriber:
    """STT wrapper that selects engine based on config."""
    
    def __init__(self, provider: str = "fluidaudio", **kwargs):
        self.provider = provider
        
        if provider == "fluidaudio":
            binary_path = kwargs.get('binary_path', '~/fluid-stt-test/.build/release/FluidSTT')
            try:
                self.engine = FluidSTTEngine(binary_path)
                print(f"  ✓ FluidSTT ready: {binary_path}")
            except FileNotFoundError as e:
                print(f"  ⚠️  FluidSTT not found, falling back to Whisper API")
                print(f"     {e}")
                # Fall back to Whisper
                api_key = kwargs.get('openai_api_key', '')
                model = kwargs.get('openai_model', 'whisper-1')
                self.engine = WhisperSTTEngine(api_key, model)
                self.provider = "openai"
        
        elif provider == "openai":
            api_key = kwargs.get('openai_api_key', '')
            model = kwargs.get('openai_model', 'whisper-1')
            self.engine = WhisperSTTEngine(api_key, model)
        
        else:
            raise ValueError(f"Unknown STT provider: {provider}")
    
    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio to text using configured engine."""
        return self.engine.transcribe(audio_bytes, sample_rate)
