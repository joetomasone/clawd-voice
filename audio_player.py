"""Cross-platform audio playback for Clawd Voice."""

import os
import platform
import subprocess
import tempfile
from typing import Optional


class AudioPlayer:
    """Cross-platform audio player with auto-detection and config override.
    
    Supported backends:
    - afplay: macOS native (default on Darwin)
    - aplay: Linux ALSA (default on Linux)
    - sounddevice: Universal fallback (Windows default, Linux fallback)
    - ffplay: FFmpeg-based (optional, works everywhere if installed)
    """
    
    def __init__(self, backend: str = "auto"):
        """Initialize audio player.
        
        Args:
            backend: Playback backend — "auto" | "afplay" | "aplay" | "sounddevice" | "ffplay"
        """
        self.backend = self._resolve_backend(backend)
        
        # Lazy-load sounddevice/soundfile only if needed
        self._sd = None
        self._sf = None
        
    def _resolve_backend(self, backend: str) -> str:
        """Resolve 'auto' to platform-appropriate backend."""
        if backend != "auto":
            return backend
            
        system = platform.system()
        if system == "Darwin":
            return "afplay"
        elif system == "Linux":
            # Try aplay first, fall back to sounddevice
            if self._command_exists("aplay"):
                return "aplay"
            return "sounddevice"
        elif system == "Windows":
            return "sounddevice"
        else:
            # Unknown platform — try sounddevice
            return "sounddevice"
    
    def _command_exists(self, cmd: str) -> bool:
        """Check if a shell command exists."""
        try:
            subprocess.run(
                ["which", cmd] if platform.system() != "Windows" else ["where", cmd],
                capture_output=True,
                check=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def _load_sounddevice(self):
        """Lazy-load sounddevice and soundfile."""
        if self._sd is None:
            try:
                import sounddevice as sd
                import soundfile as sf
                self._sd = sd
                self._sf = sf
            except ImportError as e:
                raise RuntimeError(
                    "sounddevice backend requires 'sounddevice' and 'soundfile' packages. "
                    "Install with: pip install sounddevice soundfile"
                ) from e
    
    def play(self, path: str, wait: bool = True):
        """Play audio file.
        
        Args:
            path: Path to audio file (WAV, MP3, etc.)
            wait: Block until playback finishes (default True)
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Audio file not found: {path}")
        
        if self.backend == "afplay":
            self._play_afplay(path, wait)
        elif self.backend == "aplay":
            self._play_aplay(path, wait)
        elif self.backend == "sounddevice":
            self._play_sounddevice(path)
        elif self.backend == "ffplay":
            self._play_ffplay(path, wait)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")
    
    def _play_afplay(self, path: str, wait: bool):
        """Play with macOS afplay (native, handles WAV/MP3/etc.)."""
        cmd = ["afplay", path]
        if wait:
            subprocess.run(cmd, capture_output=True, check=True)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def _play_aplay(self, path: str, wait: bool):
        """Play with Linux aplay (ALSA, WAV only).
        
        For MP3/other formats, converts via ffmpeg if available, else falls back to sounddevice.
        """
        ext = os.path.splitext(path)[1].lower()
        
        if ext == ".wav":
            # WAV — direct playback
            cmd = ["aplay", "-q", path]
            if wait:
                subprocess.run(cmd, check=True)
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            # Non-WAV (MP3, etc.) — try ffmpeg conversion, else fallback to sounddevice
            if self._command_exists("ffmpeg"):
                # Convert to WAV in temp file, then play
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", path, "-ar", "44100", "-ac", "2", tmp_path],
                        capture_output=True,
                        check=True,
                    )
                    cmd = ["aplay", "-q", tmp_path]
                    if wait:
                        subprocess.run(cmd, check=True)
                    else:
                        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
            else:
                # No ffmpeg — fall back to sounddevice
                print(f"  [aplay] Non-WAV format and ffmpeg not found, using sounddevice fallback")
                self._play_sounddevice(path)
    
    def _play_sounddevice(self, path: str):
        """Play with sounddevice (universal Python library, always blocking)."""
        self._load_sounddevice()
        
        data, samplerate = self._sf.read(path)
        self._sd.play(data, samplerate)
        self._sd.wait()  # Block until playback finishes
    
    def _play_ffplay(self, path: str, wait: bool):
        """Play with ffplay (FFmpeg's player, cross-platform but requires FFmpeg install)."""
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]
        if wait:
            subprocess.run(cmd, check=True)
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
