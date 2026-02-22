"""OpenClaw Gateway client using OpenAI-compatible chat completions endpoint."""

import requests


class GatewayClient:
    def __init__(self, url: str, token: str, agent: str = "clawd",
                 session: str = "agent:clawd:main"):
        self.url = url.rstrip("/")
        self.token = token
        self.agent = agent
        self.session = session
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "x-openclaw-agent-id": agent,
        }

    def _build_system_prompt(self) -> str:
        """Build system prompt, incorporating voice context if available."""
        import os
        context_path = "/Users/joe/.openclaw/workspace/state/voice-context-prompt.txt"
        context = ""
        if os.path.exists(context_path):
            with open(context_path) as f:
                context = f.read().strip()

        rules = """
VOICE RESPONSE RULES (MANDATORY):
- Default: 1-3 sentences max, concise and conversational.
- If the answer would be long (status reports, lists, detailed info), ASK: "That's a longer answer. Want a quick summary or should I send the full details to Signal?"
- If the user says "brief" or "quick" or "summary": give a 2-3 sentence spoken summary.
- If the user says "Signal" or "send it" or "full": use the message tool to send the detailed answer to Joe on Signal (action=send, channel=signal, target=+18137849913) and say "Sent to Signal."
- Never make up information. If you don't know, say so.
- Be direct, British Jarvis vibe. No AI filler."""

        if context:
            return context + "\n" + rules
        return "You are Clawd, Joe's AI assistant on a Mac Mini. Be concise — responses are spoken aloud." + rules

    def send(self, message: str) -> str:
        """Send a message to Clawd via chat completions endpoint.
        
        Args:
            message: Text to send
            
        Returns:
            Clawd's text response, or empty string on error
        """
        payload = {
            "model": f"openclaw:{self.agent}",
            "user": "clawd-voice-persistent",
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": message}
            ],
        }

        try:
            response = requests.post(
                f"{self.url}/v1/chat/completions",
                json=payload,
                headers=self.headers,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            # OpenAI format: choices[0].message.content
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except requests.Timeout:
            print("Gateway timeout — Clawd may be busy")
            return "I'm still thinking. Check Signal for my response."
        except Exception as e:
            print(f"Gateway error: {e}")
            return ""
