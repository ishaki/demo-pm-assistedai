import json
import logging
import re
from typing import Dict, Any, List
from google import genai
from google.genai import types
from .base import BaseLLMProvider, AIDecisionResponse
from ...config import get_settings

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider implementation.
    Supports Gemini 1.5 Pro and other Gemini models.
    Uses the new google-genai SDK (GA as of May 2025).
    """

    def __init__(self):
        settings = get_settings()

        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured")

        # Initialize Gemini client with v1 API (stable)
        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            http_options=types.HttpOptions(api_version='v1')
        )

        # Use configured model or default to gemini-1.5-pro-002
        self.model_name = settings.LLM_MODEL or "gemini-1.5-pro-002"

        # Generation config
        self.generation_config = types.GenerateContentConfig(
            temperature=0.3,
            top_p=0.95,
            top_k=40,
            max_output_tokens=1024,
        )

        logger.info(f"Initialized Gemini provider with model: {self.model_name}")

    async def get_decision(
        self,
        machine_data: Dict[str, Any],
        maintenance_history: List[Dict[str, Any]],
        existing_work_orders: List[Dict[str, Any]]
    ) -> AIDecisionResponse:
        """
        Get AI decision using Gemini API.

        Args:
            machine_data: Machine information
            maintenance_history: Maintenance history
            existing_work_orders: Existing work orders

        Returns:
            AIDecisionResponse object
        """
        system_prompt = self.build_system_prompt()
        user_prompt = self.build_user_prompt(
            machine_data,
            maintenance_history,
            existing_work_orders
        )

        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        try:
            logger.info(f"Requesting decision from Gemini for machine {machine_data.get('machine_id')}")

            # Generate content using new SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config=self.generation_config
            )

            # Extract text from response
            content = response.text
            logger.debug(f"Gemini raw response: {content}")

            # Gemini might return JSON in various formats, extract it
            json_content = self._extract_json_from_response(content)

            # Parse JSON
            decision_data = json.loads(json_content)

            # Validate and create response
            ai_response = AIDecisionResponse(**decision_data)

            logger.info(
                f"Gemini decision: {ai_response.decision} "
                f"(confidence: {ai_response.confidence}, priority: {ai_response.priority})"
            )

            return ai_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Content: {content}")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")

        except Exception as e:
            logger.error(f"Error getting decision from Gemini: {e}")
            raise

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from Gemini's response.
        Gemini sometimes includes extra text or wraps JSON in code blocks.

        Args:
            content: Raw response content

        Returns:
            Extracted JSON string
        """
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # Try to extract JSON from generic code block
        code_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
        if code_match:
            potential_json = code_match.group(1).strip()
            # Check if it looks like JSON
            if potential_json.startswith('{') and potential_json.endswith('}'):
                return potential_json

        # Try to find JSON object in the content
        json_object_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if json_object_match:
            return json_object_match.group(0)

        # If all else fails, assume the entire content is JSON
        return content.strip()

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Gemini"

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model_name
