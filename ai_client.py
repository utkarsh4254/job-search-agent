"""
ai_client.py — Free AI Client (Groq + Gemini Fallback)
========================================================
Replaces the paid Claude API with 100% free alternatives:

  Primary:  Groq  (Llama 3.3 70B) — fastest, free forever
  Fallback: Gemini 1.5 Flash       — Google's free tier

How to get free API keys:
  Groq:   https://console.groq.com  (no credit card)
  Gemini: https://aistudio.google.com/app/apikey (no credit card)

Install:
  pip install groq google-generativeai
"""

import os
import json
import time
import logging

log = logging.getLogger("AIClient")

# ─── Free API Keys (set as environment variables) ──────────────────────────────
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ─── Models ────────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"   # Best free Groq model
GEMINI_MODEL = "gemini-1.5-flash-8b"   # Best free tier limits           # Free Gemini tier


# ═══════════════════════════════════════════════════════════════════════════════
# GROQ CLIENT
# ═══════════════════════════════════════════════════════════════════════════════
class GroqClient:
    """Wrapper around Groq API with tool-calling support."""

    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not set")
        try:
            from groq import Groq
            self.client = Groq(api_key=GROQ_API_KEY)
            self.available = True
        except ImportError:
            raise ImportError("Run: pip install groq")

    def chat(self, messages: list, tools: list, system: str = "") -> dict:
        """
        Send messages to Groq and return a normalized response dict:
        {
          "content": str,          # text response (if end_turn)
          "tool_calls": [...],     # list of tool calls (if tool_use)
          "stop_reason": str       # "end_turn" | "tool_use"
        }
        """
        # Groq uses OpenAI-compatible format
        groq_messages = []

        if system:
            groq_messages.append({"role": "system", "content": system})

        for msg in messages:
            if isinstance(msg.get("content"), list):
                # Handle tool result messages
                for block in msg["content"]:
                    if block.get("type") == "tool_result":
                        groq_messages.append({
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": str(block["content"])
                        })
            else:
                role    = msg["role"]
                content = msg.get("content", "")

                # Handle assistant messages with tool calls
                if role == "assistant" and isinstance(content, list):
                    tool_calls = []
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use":
                                tool_calls.append({
                                    "id": block["id"],
                                    "type": "function",
                                    "function": {
                                        "name": block["name"],
                                        "arguments": json.dumps(block["input"])
                                    }
                                })
                            elif block.get("type") == "text":
                                text_parts.append(block["text"])
                    msg_out = {"role": "assistant", "content": " ".join(text_parts)}
                    if tool_calls:
                        msg_out["tool_calls"] = tool_calls
                    groq_messages.append(msg_out)
                else:
                    groq_messages.append({"role": role, "content": str(content)})

        # Convert tools to Groq/OpenAI format
        groq_tools = []
        for tool in tools:
            groq_tools.append({
                "type": "function",
                "function": {
                    "name":        tool["name"],
                    "description": tool["description"],
                    "parameters":  tool["input_schema"]
                }
            })

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=groq_messages,
            tools=groq_tools if groq_tools else None,
            tool_choice="auto",
            max_tokens=4096,
            temperature=0.1
        )

        choice  = response.choices[0]
        message = choice.message

        # Normalize to our standard format
        if choice.finish_reason == "tool_calls" and message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "id":    tc.id,
                    "name":  tc.function.name,
                    "input": args
                })
            return {
                "stop_reason": "tool_use",
                "content":     message.content or "",
                "tool_calls":  tool_calls
            }
        else:
            return {
                "stop_reason": "end_turn",
                "content":     message.content or "",
                "tool_calls":  []
            }


# ═══════════════════════════════════════════════════════════════════════════════
# GEMINI CLIENT
# ═══════════════════════════════════════════════════════════════════════════════
class GeminiClient:
    """Wrapper around Google Gemini API with function-calling support."""

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            self.genai   = genai
            self.available = True
        except ImportError:
            raise ImportError("Run: pip install google-generativeai")

    def _build_tools(self, tools: list):
        """Convert our tool format to Gemini function declarations."""
        from google.generativeai.types import FunctionDeclaration, Tool

        declarations = []
        for tool in tools:
            # Convert JSON Schema to Gemini format
            params = tool.get("input_schema", {})
            declarations.append(
                FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=params
                )
            )
        return [Tool(function_declarations=declarations)]

    def chat(self, messages: list, tools: list, system: str = "") -> dict:
        """Send messages to Gemini and return normalized response."""
        gemini_tools = self._build_tools(tools) if tools else None

        model = self.genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system,
            tools=gemini_tools
        )

        # Convert messages to Gemini format
        history   = []
        last_user = None

        for msg in messages:
            role    = msg["role"]
            content = msg.get("content", "")

            if isinstance(content, list):
                # Tool results
                parts = []
                for block in content:
                    if block.get("type") == "tool_result":
                        parts.append(
                            self.genai.protos.Part(
                                function_response=self.genai.protos.FunctionResponse(
                                    name=block.get("tool_use_id", "tool"),
                                    response={"result": str(block["content"])}
                                )
                            )
                        )
                history.append({"role": "user", "parts": parts})
            else:
                gemini_role = "model" if role == "assistant" else "user"
                history.append({"role": gemini_role, "parts": [str(content)]})
                if gemini_role == "user":
                    last_user = str(content)

        # Extract the last user message to send
        send_message = last_user or "Continue."
        chat_history = history[:-1] if history else []

        chat = model.start_chat(history=chat_history)
        # Retry once on rate limit
        try:
            response = chat.send_message(send_message)
        except Exception as rate_err:
            if "429" in str(rate_err) or "quota" in str(rate_err).lower():
                import time
                log.warning("Gemini rate limit — waiting 60s then retrying...")
                time.sleep(60)
                response = chat.send_message(send_message)
            else:
                raise

        # Parse response
        candidate = response.candidates[0]
        part = candidate.content.parts[0] if candidate.content.parts else None

        if part and hasattr(part, "function_call") and part.function_call.name:
            fc   = part.function_call
            args = dict(fc.args)
            return {
                "stop_reason": "tool_use",
                "content": "",
                "tool_calls": [{
                    "id":    f"gemini_{int(time.time())}",
                    "name":  fc.name,
                    "input": args
                }]
            }
        else:
            text = response.text if hasattr(response, "text") else str(part)
            return {
                "stop_reason": "end_turn",
                "content": text,
                "tool_calls": []
            }


# ═══════════════════════════════════════════════════════════════════════════════
# SMART CLIENT — Groq first, Gemini fallback
# ═══════════════════════════════════════════════════════════════════════════════
class FreeAIClient:
    """
    Smart client that tries Groq first (fastest/free),
    falls back to Gemini if Groq fails or hits rate limits.
    """

    def __init__(self):
        self.groq   = None
        self.gemini = None
        self._init_clients()

    def _init_clients(self):
        # Try Groq
        if GROQ_API_KEY:
            try:
                self.groq = GroqClient()
                log.info("✅ Groq client ready (Llama 3.3 70B)")
            except Exception as e:
                log.warning(f"Groq unavailable: {e}")
        else:
            log.warning("GROQ_API_KEY not set — Groq disabled")

        # Try Gemini
        if GEMINI_API_KEY:
            try:
                self.gemini = GeminiClient()
                log.info("✅ Gemini client ready (fallback)")
            except Exception as e:
                log.warning(f"Gemini unavailable: {e} — will rely on Groq only")
                self.gemini = None
        else:
            log.warning("GEMINI_API_KEY not set — running on Groq only")

        if not self.groq and not self.gemini:
            raise RuntimeError(
                "No AI client available! Set GROQ_API_KEY in GitHub Secrets.\n"
                "Get free key at: https://console.groq.com"
            )
        if self.groq:
            log.info(f"Primary AI: Groq (Llama 3.3 70B)")
        if self.gemini:
            log.info(f"Fallback AI: Gemini")

    def chat(self, messages: list, tools: list, system: str = "") -> dict:
        """
        Try Groq first. If it fails (rate limit, error), fall back to Gemini.
        """
        # ── Try Groq ────────────────────────────────────────────
        if self.groq:
            try:
                result = self.groq.chat(messages, tools, system)
                log.debug("Used: Groq")
                return result
            except Exception as e:
                err = str(e).lower()
                if "rate" in err or "limit" in err or "429" in err:
                    log.warning("⚠️  Groq rate limit hit — switching to Gemini")
                elif "quota" in err:
                    log.warning("⚠️  Groq quota exceeded — switching to Gemini")
                else:
                    log.warning(f"⚠️  Groq error ({e}) — switching to Gemini")

        # ── Fall back to Gemini ──────────────────────────────────
        if self.gemini:
            try:
                result = self.gemini.chat(messages, tools, system)
                log.debug("Used: Gemini (fallback)")
                return result
            except Exception as e:
                err = str(e)
                if "quota" in err.lower() or "429" in err or "limit: 0" in err:
                    log.warning("Gemini quota exhausted for today — Groq is required")
                    raise RuntimeError(
                        "Groq failed AND Gemini quota exhausted.\n"
                        "The Groq error is the root cause — check GROQ_API_KEY is valid."
                    )
                log.error(f"Gemini also failed: {e}")
                raise RuntimeError(f"Both AI providers failed. Last error: {e}")

        raise RuntimeError("No AI provider available — check GROQ_API_KEY in GitHub Secrets")

    def status(self) -> str:
        parts = []
        if self.groq:
            parts.append("Groq ✅")
        if self.gemini:
            parts.append("Gemini ✅")
        return " | ".join(parts) or "No AI configured ❌"


# ─── Singleton ────────────────────────────────────────────────────────────────
_client = None

def get_client() -> FreeAIClient:
    """Get or create the shared AI client."""
    global _client
    if _client is None:
        _client = FreeAIClient()
    return _client


if __name__ == "__main__":
    print("Testing free AI client...\n")
    try:
        client = get_client()
        print(f"Active providers: {client.status()}\n")

        result = client.chat(
            messages=[{"role": "user", "content": "Say hello in one sentence."}],
            tools=[],
            system="You are a helpful assistant."
        )
        print(f"Response: {result['content']}")
    except Exception as e:
        print(f"Error: {e}")
