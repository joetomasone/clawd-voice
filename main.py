#!/usr/bin/env python3
"""Clawd Voice — local voice assistant for OpenClaw.

Wake word → VAD recording → Whisper STT → Clawd → ElevenLabs TTS → Speaker
"""

import sys
import os
import time
import yaml

from wake import WakeWordDetector
from recorder import VadRecorder
from transcribe import Transcriber
from speak import Speaker
from gateway_client import GatewayClient
from audio_player import AudioPlayer


def main():
    # Load config
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Validate Porcupine key
    if not config.get('porcupine_access_key'):
        print("ERROR: porcupine_access_key not set in config.yaml")
        print("Get a free key at https://console.picovoice.ai/")
        sys.exit(1)

    # Initialize modules
    print("🐾 Clawd Voice starting up...")

    device_index = config['audio'].get('input_device') or -1
    pyaudio_device = config['audio'].get('pyaudio_device') or -1

    # Cross-platform audio playback
    playback_backend = config['audio'].get('playback_backend', 'auto')
    audio_player = AudioPlayer(backend=playback_backend)
    print(f"  ✓ Audio backend: {audio_player.backend}")

    wake = WakeWordDetector(
        access_key=config['porcupine_access_key'],
        keyword=config['wake_word'],
        device_index=device_index,
    )
    print(f"  ✓ Wake word: '{config['wake_word']}'")

    recorder = VadRecorder(
        vad_threshold=config['vad']['threshold'],
        silence_timeout=config['vad']['silence_timeout_sec'],
        max_duration=config['vad']['max_recording_sec'],
        sample_rate=config['audio']['sample_rate'],
        device_index=pyaudio_device,
    )
    print("  ✓ VAD recorder ready")

    transcriber = Transcriber(
        provider=config['stt']['provider'],
        api_key=config['stt']['openai_api_key'],
        model=config['stt']['model'],
    )
    print("  ✓ Whisper STT ready")

    speaker = Speaker(
        api_key=config['tts']['api_key'],
        voice_id=config['tts']['voice_id'],
        model=config['tts']['model'],
        stability=config['tts']['stability'],
        similarity_boost=config['tts']['similarity_boost'],
        audio_player=audio_player,
    )
    print("  ✓ ElevenLabs TTS ready")

    gateway = GatewayClient(
        url=config['gateway']['url'],
        token=config['gateway']['token'],
        agent=config['gateway']['agent'],
        session=config['gateway']['session'],
    )
    print("  ✓ Gateway client ready")
    print(f"\n🎤 Listening for '{config['wake_word']}'... (Ctrl+C to quit)\n")

    try:
        while True:
            # 1. Wait for wake word
            wake.listen()
            print("⚡ Wake word detected!")

            # 2. Play chime + brief delay so chime doesn't bleed into mic
            if config['audio']['chime_on_wake']:
                chime_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chime.wav')
                audio_player.play(chime_path)
                time.sleep(0.3)

            # 3. Record speech (VAD-gated)
            print("🎙️  Listening...")
            audio_data = recorder.record()

            # 4. Check minimum audio length (~0.5s at 16kHz, 16-bit = 16000 bytes)
            min_bytes = int(0.5 * config['audio']['sample_rate'] * 2)
            if len(audio_data) < min_bytes:
                print("  (too short, ignoring)")
                print(f"\n🎤 Listening for '{config['wake_word']}'...\n")
                continue

            # 5. Acknowledge end of speech (pre-recorded for instant playback)
            ack_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'one_moment.wav')
            audio_player.play(ack_path)

            # 6. Transcribe
            print("📝 Transcribing...")
            text = transcriber.transcribe(audio_data, config['audio']['sample_rate'])

            if not text or not text.strip():
                print("  (empty transcript, ignoring)")
                print(f"\n🎤 Listening for '{config['wake_word']}'...\n")
                continue

            print(f"   You: {text}")

            # 7. Send to Clawd
            print("🤔 Thinking...")
            reply = gateway.send(text)

            if not reply:
                speaker.speak("Sorry, I couldn't get a response. Try again.")
                print(f"\n🎤 Listening for '{config['wake_word']}'...\n")
                continue

            # 7. Respond — speak the full reply, system prompt handles length
            print(f"   Clawd: {reply}")
            speaker.speak(reply)

            print(f"\n🎤 Listening for '{config['wake_word']}'...\n")

    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        wake.cleanup()


if __name__ == "__main__":
    main()
