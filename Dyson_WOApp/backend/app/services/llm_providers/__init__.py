from .base import BaseLLMProvider, AIDecisionResponse
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .gemini_provider import GeminiProvider
from ...config import get_settings
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "BaseLLMProvider",
    "AIDecisionResponse",
    "OpenAIProvider",
    "ClaudeProvider",
    "GeminiProvider",
    "get_llm_provider"
]


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory function to get the configured LLM provider.

    Returns:
        Instance of the configured LLM provider

    Raises:
        ValueError: If the configured provider is not supported
    """
    settings = get_settings()

    provider_map = {
        "openai": OpenAIProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider
    }

    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name not in provider_map:
        available = ", ".join(provider_map.keys())
        raise ValueError(
            f"Unknown LLM provider: '{settings.LLM_PROVIDER}'. "
            f"Available providers: {available}"
        )

    provider_class = provider_map[provider_name]

    try:
        provider = provider_class()
        logger.info(f"Successfully initialized {provider.get_provider_name()} provider")
        return provider
    except ValueError as e:
        logger.error(f"Failed to initialize {provider_name} provider: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing {provider_name} provider: {e}")
        raise
