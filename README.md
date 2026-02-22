# Clawd Voice

**Local voice assistant for OpenClaw** — Wake word detection, Speech-to-Text, AI processing, and Text-to-Speech, all running locally (except cloud STT/TTS APIs).

```
Wake Word → VAD Recording → Whisper STT → OpenClaw Agent → ElevenLabs TTS → Speaker
```

## Features

- 🎤 **Wake word detection** with Picovoice Porcupine (offline, local)
- 🔇 **Voice Activity Detection (VAD)** using Silero VAD (stops recording on silence)
- 🗣️ **Speech-to-Text** via OpenAI Whisper API
- 🤖 **AI processing** through OpenClaw Gateway (local agent orchestration)
- 🔊 **Text-to-Speech** with ElevenLabs streaming API (high-quality voices)
- 🖥️ **Cross-platform** audio playback (macOS, Linux, Windows)

## Requirements

- **Python 3.10+**
- **Picovoice account** (free tier) — [Get key here](https://console.picovoice.ai/)
- **OpenAI API key** (for Whisper STT) — [Get key here](https://platform.openai.com/api-keys)
- **ElevenLabs API key** (for TTS) — [Get key here](https://elevenlabs.io/)
- **OpenClaw Gateway** running locally — [Install OpenClaw](https://github.com/openclaw/openclaw)

### Optional (for certain playback backends)
- **Linux:** `aplay` (ALSA, usually pre-installed) or `ffmpeg` for MP3 support
- **All platforms:** `ffplay` (FFmpeg) if you want to use the ffplay backend

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/joetomasone/clawd-voice.git
   cd clawd-voice
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure:**
   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your API keys and settings
   ```

5. **Run:**
   ```bash
   python3 main.py
   ```

## Configuration

Edit `config.yaml` to customize:

### Wake Word
```yaml
wake_word: "jarvis"  # Built-in options: jarvis, alexa, computer, hey google, etc.
porcupine_access_key: "YOUR_PICOVOICE_KEY"
```

### Voice Activity Detection (VAD)
```yaml
vad:
  threshold: 0.3              # Speech probability threshold (0-1)
  silence_timeout_sec: 2.0    # Seconds of silence before stopping
  max_recording_sec: 30       # Maximum recording duration
```

### Speech-to-Text (Whisper)
```yaml
stt:
  provider: openai
  openai_api_key: "YOUR_OPENAI_KEY"
  model: whisper-1
```

### OpenClaw Gateway
```yaml
gateway:
  url: "http://localhost:18789"
  token: "YOUR_GATEWAY_TOKEN"
  agent: "clawd"
  session: "agent:clawd:main"
```

### Text-to-Speech (ElevenLabs)
```yaml
tts:
  provider: elevenlabs
  api_key: "YOUR_ELEVENLABS_KEY"
  voice_id: "JBFqnCBsd6RMkjVDRZzb"  # George (British male)
  model: "eleven_turbo_v2_5"
  stability: 0.6
  similarity_boost: 0.8
```

### Audio Settings
```yaml
audio:
  input_device: -1        # -1 = default, or specific device index
  pyaudio_device: -1      # PyAudio device index (for VAD recorder)
  sample_rate: 16000
  chime_on_wake: true
  
  # playback_backend options:
  #   auto = auto-detect platform (default)
  #   afplay = macOS native (WAV, MP3, AAC, etc.)
  #   aplay = Linux ALSA (WAV only, ffmpeg for MP3)
  #   sounddevice = Python library (universal fallback)
  #   ffplay = FFmpeg player (requires ffmpeg)
  playback_backend: auto
```

## Platform Support

| Platform | Default Backend | Notes |
|----------|----------------|-------|
| **macOS** | `afplay` | Native, supports all common formats |
| **Linux** | `aplay` | ALSA (WAV only), auto-converts MP3 via ffmpeg if available, falls back to sounddevice |
| **Windows** | `sounddevice` | Python library, works universally |

### Platform-Specific Notes

**macOS:**
- `.app` bundle and `com.clawd.voice.plist` are macOS-only launch helpers
- Use `launchctl` to run as background service (see `.plist` file)

**Linux:**
- Install `ffmpeg` for MP3 support with aplay: `sudo apt install ffmpeg`
- Or let it fall back to `sounddevice` (pure Python)

**Windows:**
- Uses `sounddevice` + `soundfile` by default (no external dependencies)

## Usage

1. **Start the assistant:**
   ```bash
   python3 main.py
   ```

2. **Say the wake word** (default: "jarvis")

3. **Speak your request** (VAD will auto-detect when you stop talking)

4. **Listen to the response** (text is sent to OpenClaw, response is spoken via TTS)

### Example Session
```
🐾 Clawd Voice starting up...
  ✓ Audio backend: afplay
  ✓ Wake word: 'jarvis'
  ✓ VAD recorder ready
  ✓ Whisper STT ready
  ✓ ElevenLabs TTS ready
  ✓ Gateway client ready

🎤 Listening for 'jarvis'... (Ctrl+C to quit)

⚡ Wake word detected!
🎙️  Listening...
📝 Transcribing...
   You: What's the weather like today?
🤔 Thinking...
   Clawd: It's currently 72°F and partly cloudy in Tampa.

🎤 Listening for 'jarvis'...
```

## Troubleshooting

### No audio playback
- Check `playback_backend` in `config.yaml`
- Try switching to `sounddevice` backend (most universal)
- Ensure `sounddevice` and `soundfile` are installed

### Microphone not detected
- List devices: `python3 -c "import pvrecorder; print(pvrecorder.PvRecorder.get_available_devices())"`
- Set `input_device` in `config.yaml` to the correct index

### Wake word not triggering
- Speak clearly and closer to the microphone
- Try different built-in wake words (see [Porcupine docs](https://picovoice.ai/docs/porcupine/))

### OpenClaw connection fails
- Ensure OpenClaw Gateway is running: `openclaw gateway status`
- Check `gateway.url` and `gateway.token` in `config.yaml`

## Development

**Project structure:**
```
clawd-voice/
├── main.py              # Main loop and orchestration
├── wake.py              # Porcupine wake word detector
├── recorder.py          # Silero VAD-gated recorder
├── transcribe.py        # OpenAI Whisper STT
├── speak.py             # ElevenLabs TTS
├── gateway_client.py    # OpenClaw Gateway client
├── audio_player.py      # Cross-platform audio playback
├── config.yaml          # Configuration (not in git, use config.yaml.example)
├── chime.wav            # Wake acknowledgment sound
├── one_moment.wav       # "Processing" acknowledgment
└── requirements.txt     # Python dependencies
```

## License

MIT License — see LICENSE file for details.

## Credits

Built with:
- [Picovoice Porcupine](https://picovoice.ai/) (wake word)
- [Silero VAD](https://github.com/snakers4/silero-vad) (voice activity detection)
- [OpenAI Whisper](https://platform.openai.com/docs/guides/speech-to-text) (STT)
- [ElevenLabs](https://elevenlabs.io/) (TTS)
- [OpenClaw](https://github.com/openclaw/openclaw) (agent orchestration)

---

**Made for Joe's OpenClaw setup** 🐾
