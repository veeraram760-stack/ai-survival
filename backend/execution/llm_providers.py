import os
import time
import httpx
from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from config.settings import settings
import logging

logger = logging.getLogger("ai_survival.llm")


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                key = self.api_key or settings.openai_api_key
                if not key:
                    raise RuntimeError("OPENAI_API_KEY not set")
                kwargs = {"api_key": key}
                if self.base_url or settings.openai_base_url:
                    kwargs["base_url"] = self.base_url or settings.openai_base_url
                self._client = AsyncOpenAI(**kwargs)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize OpenAI client: {e}")
        return self._client

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            client = self._get_client()
        except RuntimeError as e:
            return {"status": "failed", "error": str(e), "model": self.model}
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
            )
            return {
                "status": "success",
                "output": response.choices[0].message.content,
                "model": self.model,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e), "model": self.model}


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-haiku-20240307"):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                key = self.api_key or settings.anthropic_api_key
                if not key:
                    raise RuntimeError("ANTHROPIC_API_KEY not set")
                self._client = anthropic.AsyncAnthropic(api_key=key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Anthropic client: {e}")
        return self._client

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            client = self._get_client()
        except RuntimeError as e:
            return {"status": "failed", "error": str(e), "model": self.model}
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
                messages=[{"role": "user", "content": prompt}],
            )
            return {
                "status": "success",
                "output": response.content[0].text,
                "model": self.model,
            }
        except Exception as e:
            return {"status": "failed", "error": str(e), "model": self.model}


class GoogleProvider(LLMProvider):
    # Model fallback chain: prioritize confirmed working models (tested 2026-09-07)
    # Working: gemini-3.7-flash, gemini-flash-lite-latest, gemini-3.5-flash, gemini-3.5-flash-lite
    # Rate limited (429): gemini-3.6-flash, gemini-3.8-flash, gemini-flash-latest
    # Deprecated (404): gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.5-pro
    MODEL_FALLBACKS = [
        "gemini-3.7-flash",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-flash-latest",
    ]

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                key = self.api_key or settings.google_api_key or settings.google_cloud_api_key
                if not key:
                    raise RuntimeError("GOOGLE_API_KEY not set")
                self._client = genai.Client(api_key=key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Google client: {e}")
        return self._client

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            client = self._get_client()
        except RuntimeError as e:
            return {"status": "failed", "error": str(e), "model": self.model}

        # Build model chain: primary first, then fallbacks not already tried
        primary = self.model
        tried = {primary}
        model_chain = [primary] + [m for m in self.MODEL_FALLBACKS if m not in tried]

        max_retries = kwargs.get("max_retries", 3)
        base_delay = kwargs.get("retry_delay", 2.0)
        last_error = None

        for model in model_chain:
            for attempt in range(1, max_retries + 1):
                try:
                    response = await client.aio.models.generate_content(
                        model=model,
                        contents=prompt,
                        config={
                            "max_output_tokens": kwargs.get("max_tokens", 2000),
                            "temperature": kwargs.get("temperature", 0.7),
                        },
                    )
                    return {
                        "status": "success",
                        "output": response.text,
                        "model": model,
                    }
                except Exception as e:
                    last_error = e
                    error_text = str(e)
                    # Rate limit: wait and retry same model
                    if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                        wait = base_delay * attempt
                        logger.warning(f"Google rate limit on {model}, retry {attempt}/{max_retries} in {wait}s")
                        time.sleep(wait)
                        continue
                    # Model not found: break to next model in chain
                    if "404" in error_text or "NOT_FOUND" in error_text:
                        logger.warning(f"Model {model} not found ({error_text[:80]}), trying next fallback")
                        break
                    # Other error: retry a couple times then break to next model
                    if attempt == max_retries:
                        break
                    logger.warning(f"Google LLM error on {model}, retry {attempt}/{max_retries}: {e}")
                    time.sleep(base_delay)
            # If we exhausted retries on this model, continue to next fallback
            continue

        return {"status": "failed", "error": str(last_error), "model": primary}


class OllamaProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "llama3.2"):
        self.api_key = api_key
        self.model = model
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self.api_key or "ollama",
                    base_url=f"{self.base_url}/v1",
                )
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Ollama client: {e}")
        return self._client

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            client = self._get_client()
        except RuntimeError as e:
            return {"status": "failed", "error": str(e), "model": self.model}
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
            )
            return {
                "status": "success",
                "output": response.choices[0].message.content,
                "model": f"ollama/{self.model}",
            }
        except Exception as e:
            return {"status": "failed", "error": str(e), "model": self.model}


class GroqProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "llama3-8b-8192"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                if not self.api_key:
                    raise RuntimeError("GROQ_API_KEY not set")
                self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Groq client: {e}")
        return self._client

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            client = self._get_client()
        except RuntimeError as e:
            return {"status": "failed", "error": str(e), "model": self.model}
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=kwargs.get("max_tokens", 2000),
                temperature=kwargs.get("temperature", 0.7),
            )
            return {
                "status": "success",
                "output": response.choices[0].message.content,
                "model": f"groq/{self.model}",
            }
        except Exception as e:
            return {"status": "failed", "error": str(e), "model": self.model}


class HuggingFaceProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: str = "mistralai/Mistral-7B-Instruct-v0.2"):
        from config.settings import settings
        self.api_key = api_key or os.getenv("HF_API_KEY") or settings.hf_api_key
        self.model = model
        self.base_url = "https://api-inference.huggingface.co"
        logger.info(f"HuggingFaceProvider initialized with api_key={'set' if self.api_key else 'MISSING'}, model={self.model}")

    async def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        if not self.api_key:
            return {"status": "failed", "error": "HF_API_KEY not set", "model": self.model}
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/models/{self.model}",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"inputs": prompt, "parameters": {"max_new_tokens": kwargs.get("max_tokens", 2000), "temperature": kwargs.get("temperature", 0.7)}},
                )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, list) and data:
                    return {"status": "success", "output": data[0].get("generated_text", ""), "model": self.model}
                if isinstance(data, dict):
                    return {"status": "success", "output": data.get("generated_text", ""), "model": self.model}
                return {"status": "failed", "error": "Unexpected Hugging Face response format", "model": self.model}
        except Exception as e:
            return {"status": "failed", "error": str(e), "model": self.model}


def get_llm_provider(provider: Optional[str] = None) -> LLMProvider:
    provider_name = (provider or settings.llm_provider or "auto").lower()
    if provider_name == "openai":
        return OpenAIProvider(base_url=settings.openai_base_url)
    if provider_name == "anthropic":
        return AnthropicProvider()
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name == "groq":
        return GroqProvider()
    if provider_name == "huggingface":
        return HuggingFaceProvider()
    if provider_name == "google":
        return GoogleProvider()

    if provider_name == "auto":
        ollama = OllamaProvider()
        try:
            async def check():
                async with httpx.AsyncClient(timeout=5.0) as client:
                    r = await client.get(f"{ollama.base_url}/api/tags")
                    return r.status_code == 200
            import asyncio
            if asyncio.run(check()):
                logger.info("Auto-selected Ollama provider")
                return ollama
        except Exception:
            pass
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            logger.info("Auto-selected Groq provider")
            return GroqProvider()
        hf = HuggingFaceProvider()
        if hf.api_key:
            logger.info("Auto-selected HuggingFace provider")
            return hf
        logger.info("Auto-selected Google provider")
        return GoogleProvider()

    return GoogleProvider()
