import json
import logging
from typing import Dict, Any, List
from openai import AsyncOpenAI
from .base import BaseLLMProvider, AIDecisionResponse
from ...config import get_settings

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI LLM provider implementation.
    Supports GPT-4 and GPT-3.5 models.
    """

    def __init__(self):
        settings = get_settings()

        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Use configured model or default to gpt-4
        self.model = settings.LLM_MODEL or "gpt-4"

        logger.info(f"Initialized OpenAI provider with model: {self.model}")

    async def get_decision(
        self,
        machine_data: Dict[str, Any],
        maintenance_history: List[Dict[str, Any]],
        existing_work_orders: List[Dict[str, Any]]
    ) -> AIDecisionResponse:
        """
        Get AI decision using OpenAI API.

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

        try:
            logger.info(f"Requesting decision from OpenAI for machine {machine_data.get('machine_id')}")

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,  # Lower temperature for more consistent decisions
                max_tokens=500
            )

            # Extract JSON response
            content = response.choices[0].message.content
            logger.debug(f"OpenAI raw response: {content}")

            # Parse JSON
            decision_data = json.loads(content)

            # Validate and create response
            ai_response = AIDecisionResponse(**decision_data)

            logger.info(
                f"OpenAI decision: {ai_response.decision} "
                f"(confidence: {ai_response.confidence}, priority: {ai_response.priority})"
            )

            return ai_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")

        except Exception as e:
            logger.error(f"Error getting decision from OpenAI: {e}")
            raise

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "OpenAI"

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model
