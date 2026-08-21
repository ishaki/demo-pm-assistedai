from .base import (
    BaseDateExtractor,
    CONFIDENCE_SCORES,
    RESPONSE_SCHEMA,
    EXTRACTION_RULES,
)
from .openai_extractor import OpenAIDateExtractor
from .claude_extractor import ClaudeDateExtractor
from .gemini_extractor import GeminiDateExtractor
import logging

logger = logging.getLogger(__name__)

__all__ = [
    "BaseDateExtractor",
    "CONFIDENCE_SCORES",
    "RESPONSE_SCHEMA",
    "EXTRACTION_RULES",
    "OpenAIDateExtractor",
    "ClaudeDateExtractor",
    "GeminiDateExtractor",
    "get_date_extractor",
]

# Keyed on BaseLLMProvider.get_provider_name(), so adding a fourth provider
# means adding a module and one line here -- not editing a branch in the
# service, which is what this replaced.
EXTRACTOR_MAP = {
    "OpenAI": OpenAIDateExtractor,
    "Claude": ClaudeDateExtractor,
    "Gemini": GeminiDateExtractor,
}


def get_date_extractor(llm_provider) -> BaseDateExtractor:
    """
    Pick the date extraction strategy for an already-resolved LLM provider.

    Deliberately takes the provider rather than reading settings itself: the
    extractor reuses that provider's configured client and model, so resolving
    the two independently could pair a Claude extractor with an OpenAI client
    if LLM_PROVIDER changed between the two calls.

    Args:
        llm_provider: An instance from get_llm_provider()

    Returns:
        The matching BaseDateExtractor subclass, constructed

    Raises:
        ValueError: If no extractor exists for that provider
    """
    provider_name = llm_provider.get_provider_name()

    extractor_class = EXTRACTOR_MAP.get(provider_name)

    if extractor_class is None:
        available = ", ".join(EXTRACTOR_MAP.keys())
        raise ValueError(
            f"No date extractor for LLM provider: '{provider_name}'. "
            f"Available: {available}"
        )

    logger.debug(f"Using {extractor_class.__name__} for provider {provider_name}")
    return extractor_class(llm_provider)
