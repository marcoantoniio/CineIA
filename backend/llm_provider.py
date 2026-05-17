"""
LLM Provider Factory
====================

Returns a LangChain-compatible chat model based on LLM_PROVIDER env var.

Supported providers:
  - gemini  (default) — requires GOOGLE_API_KEY
  - bedrock           — requires AWS credentials + region

Env vars:
  LLM_PROVIDER        gemini | bedrock
  FAST_MODEL           model id for router (lightweight)
  PRIMARY_MODEL        model id for SQL agent (powerful)
  GOOGLE_API_KEY       required for gemini
  AWS_REGION           required for bedrock (default: us-east-1)
"""

import os
from typing import Optional
from langchain_core.runnables import Runnable

_cache: dict = {}

# Default models per provider
DEFAULTS = {
    "gemini": {
        "fast": "gemini-2.0-flash-lite",
        "primary": "gemini-2.0-flash-lite",  # Using lite version due to free tier quota limits
    },
    "bedrock": {
        "fast": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
        "primary": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    },
}


def get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").lower()


def get_llm(
    role: str = "primary",
    temperature: float = 0.0,
    max_tokens: int = 4096,
    stop_sequences: Optional[list] = None,
) -> Runnable:
    """
    Return a cached LangChain chat model.

    Args:
        role: 'fast' (router) or 'primary' (sql agent)
        temperature: sampling temperature
        max_tokens: max output tokens
        stop_sequences: optional stop sequences
    """
    provider = get_provider()
    defaults = DEFAULTS.get(provider, DEFAULTS["gemini"])
    model_id = os.getenv(
        "FAST_MODEL" if role == "fast" else "PRIMARY_MODEL",
        defaults[role],
    )

    cache_key = (provider, model_id, temperature, max_tokens, tuple(stop_sequences or []))
    if cache_key in _cache:
        return _cache[cache_key]

    print(f"[LLM] Creating {provider}/{model_id} (role={role})")

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=model_id,
            temperature=temperature,
            max_output_tokens=max_tokens,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    elif provider == "bedrock":
        try:
            from langchain_aws import ChatBedrock
            model_kwargs = {"temperature": temperature, "max_tokens": max_tokens}
            if stop_sequences:
                model_kwargs["stop_sequences"] = stop_sequences
            llm = ChatBedrock(
                model_id=model_id,
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                model_kwargs=model_kwargs,
            )
        except ImportError:
            raise ImportError("langchain-aws not installed. Install with: pip install langchain-aws")

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'gemini' or 'bedrock'.")

    _cache[cache_key] = llm
    print(f"[LLM] ✅ Ready: {provider}/{model_id}")
    return llm


def clear_cache():
    _cache.clear()
    print("[LLM] Cache cleared")
