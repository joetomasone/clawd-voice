"""Wake word detection using Picovoice Porcupine."""

import pvporcupine
from pvrecorder import PvRecorder


class WakeWordDetector:
    def __init__(self, access_key: str, keyword: str, device_index: int = -1):
        """Initialize Porcupine wake word detector.
        
        Args:
            access_key: Picovoice access key (free tier)
            keyword: Built-in keyword name (e.g., 'jarvis', 'alexa', 'computer')
            device_index: Audio input device index (-1 = default)
        """
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=[keyword],
        )
        self.recorder = PvRecorder(
            device_index=device_index,
            frame_length=self.porcupine.frame_length,
        )

    def listen(self) -> bool:
        """Block until wake word is detected. Returns True."""
        self.recorder.start()
        try:
            while True:
                pcm = self.recorder.read()
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    self.recorder.stop()
                    import time
                    time.sleep(0.1)  # Let OS release the audio device
                    return True
        except Exception:
            self.recorder.stop()
            raise

    def cleanup(self):
        """Release resources."""
        self.recorder.delete()
        self.porcupine.delete()
