"""VAD-gated audio recording using Silero VAD."""

import pyaudio
import torch
import numpy as np

torch.set_num_threads(1)


class VadRecorder:
    def __init__(self, vad_threshold: float = 0.5, silence_timeout: float = 1.5,
                 max_duration: float = 30, sample_rate: int = 16000, device_index: int = -1):
        """Initialize VAD-gated recorder.
        
        Args:
            vad_threshold: Speech probability threshold (0-1)
            silence_timeout: Seconds of silence before stopping
            max_duration: Maximum recording duration in seconds
            sample_rate: Audio sample rate (must be 16000 for Silero)
        """
        self.sample_rate = sample_rate
        self.vad_threshold = vad_threshold
        self.silence_timeout = silence_timeout
        self.max_duration = max_duration
        # Silero VAD requires 512 samples at 16kHz (32ms chunks)
        self.chunk_size = 512
        self.device_index = device_index if device_index >= 0 else None

        # Load Silero VAD model from local cache (avoid network check)
        import os
        os.environ.setdefault('TORCH_HOME', os.path.expanduser('~/.cache/torch'))
        try:
            self.vad_model, _ = torch.hub.load(
                os.path.expanduser('~/.cache/torch/hub/snakers4_silero-vad_master'),
                'silero_vad', source='local', trust_repo=True
            )
        except Exception:
            # Fallback to network load
            self.vad_model, _ = torch.hub.load(
                'snakers4/silero-vad', 'silero_vad', trust_repo=True
            )
        self.vad_model.eval()

    def _is_speech(self, audio_chunk: bytes) -> bool:
        """Check if audio chunk contains speech using Silero VAD."""
        audio_array = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        audio_tensor = torch.from_numpy(audio_array)
        with torch.no_grad():
            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
        return speech_prob > self.vad_threshold

    def record(self) -> bytes:
        """Record audio, stopping after silence_timeout of no speech.
        
        Returns:
            Raw PCM bytes (16-bit, 16kHz, mono)
        """
        pa = pyaudio.PyAudio()
        open_kwargs = dict(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            frames_per_buffer=self.chunk_size,
            input=True,
        )
        if self.device_index is not None:
            open_kwargs['input_device_index'] = self.device_index
        stream = pa.open(**open_kwargs)

        audio_buffer = bytearray()
        silence_chunks = 0
        chunks_per_second = self.sample_rate / self.chunk_size
        silence_threshold = int(self.silence_timeout * chunks_per_second)
        max_chunks = int(self.max_duration * chunks_per_second)
        # Wait up to 5 seconds for speech to actually start
        max_wait_chunks = int(5.0 * chunks_per_second)
        speech_detected = False
        chunk_count = 0
        # Pre-buffer: keep last 0.5s of audio to capture speech onset
        from collections import deque
        pre_buffer_size = int(0.5 * chunks_per_second)
        pre_buffer = deque(maxlen=pre_buffer_size)

        try:
            for _ in range(max_chunks):
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                chunk_count += 1

                is_speech = self._is_speech(chunk)
                if chunk_count <= 3 or (chunk_count % 30 == 0):
                    import numpy as np
                    arr = np.frombuffer(chunk, dtype=np.int16)
                    rms = np.sqrt(np.mean(arr.astype(float)**2))
                    print(f"    [VAD] chunk={chunk_count} speech={is_speech} rms={rms:.0f}")
                if is_speech:
                    if not speech_detected:
                        # First speech — flush pre-buffer to capture onset
                        for pre_chunk in pre_buffer:
                            audio_buffer.extend(pre_chunk)
                        pre_buffer.clear()
                    speech_detected = True
                    silence_chunks = 0
                    audio_buffer.extend(chunk)
                elif speech_detected:
                    silence_chunks += 1
                    audio_buffer.extend(chunk)
                    if silence_chunks >= silence_threshold:
                        break
                else:
                    # No speech yet — store in rolling pre-buffer
                    pre_buffer.append(chunk)
                    if chunk_count >= max_wait_chunks:
                        print("  (no speech detected, giving up)")
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        # Reset VAD state for next recording
        self.vad_model.reset_states()

        return bytes(audio_buffer)
