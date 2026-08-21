import logging

from .llm_providers import get_llm_provider
from .date_extractors import get_date_extractor

logger = logging.getLogger(__name__)


class DateExtractionService:
    """
    Reads the maintenance date out of a supplier's email reply.

    A thin façade over the date_extractors package. The per-provider prompt and
    SDK call live in a strategy class there, chosen by get_date_extractor;
    this class exists so callers have one stable entry point and one place
    where a failed extraction is turned into a safe result rather than an
    exception.
    """

    def __init__(self):
        self.llm_provider = get_llm_provider()
        self.extractor = get_date_extractor(self.llm_provider)
        self.confidence_threshold = 0.7

    async def extract_date_from_email(self, email_body: str) -> dict:
        """
        Extract the scheduled maintenance date from an email body.

        Never raises. Every failure -- an SDK rejection, a malformed response,
        an unconfigured provider -- comes back as confidence 0.0, which the
        webhook rejects. The exception text rides along in `explanation`,
        because the alternative is what happened with the deprecated
        `temperature` argument: a hard SDK error read on the wire as "the model
        was unsure", pointing every investigation at the supplier's wording
        instead of at the request.

        Args:
            email_body: Email body text

        Returns:
            dict with keys:
                - selected_date: ISO format date string (YYYY-MM-DD) or None
                - confidence: float (0.0-1.0)
                - explanation: human-readable account of the extraction
                - source_text: the snippet the date was read from, or None
        """
        try:
            raw = await self.extractor.extract(email_body)
            result = self.extractor.normalise(raw)
            logger.info(f"Date extraction result ({self.extractor.get_name()}): {result}")
            return result

        except Exception as e:
            logger.error(
                f"Error extracting date from email "
                f"({self.extractor.get_name()}): {e}"
            )
            return {
                "selected_date": None,
                "confidence": 0.0,
                "explanation": f"Error during extraction: {str(e)}",
                "source_text": None,
            }
