import json
import logging
import re
from typing import Dict, Any, List
from anthropic import AsyncAnthropic
from .base import BaseLLMProvider, AIDecisionResponse
from ...config import get_settings

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseLLMProvider):
    """
    Anthropic Claude LLM provider implementation.
    Defaults to Claude Sonnet 5; override with LLM_MODEL.
    """

    def __init__(self):
        settings = get_settings()

        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")

        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Use configured model or default to Claude Sonnet 5
        self.model = settings.LLM_MODEL or "claude-sonnet-5"

        logger.info(f"Initialized Claude provider with model: {self.model}")

    async def get_decision(
        self,
        machine_data: Dict[str, Any],
        maintenance_history: List[Dict[str, Any]],
        existing_work_orders: List[Dict[str, Any]]
    ) -> AIDecisionResponse:
        """
        Get AI decision using Claude API.

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
            logger.info(f"Requesting decision from Claude for machine {machine_data.get('machine_id')}")

            # No temperature: sampling parameters were removed on Sonnet 5 and the
            # rest of the 4.6+ family, and sending one is rejected with a 400.
            #
            # max_tokens covers thinking as well as the visible reply. Thinking is
            # adaptive-on by default on these models, so the old 1024 ceiling could
            # be spent reasoning and truncate the JSON payload mid-object.
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract content from Claude's response. Take the first *text* block
            # rather than content[0]: with thinking on, the first block is a
            # thinking block, which carries no .text attribute at all.
            content = next(
                (block.text for block in message.content if block.type == "text"),
                None
            )

            if content is None:
                raise ValueError(
                    f"Claude returned no text block (stop_reason={message.stop_reason})"
                )

            logger.debug(f"Claude raw response: {content}")

            # Claude might return JSON in markdown code blocks, so we need to extract it
            json_content = self._extract_json_from_response(content)

            # Parse JSON
            decision_data = json.loads(json_content)

            # Validate and create response
            ai_response = AIDecisionResponse(**decision_data)

            logger.info(
                f"Claude decision: {ai_response.decision} "
                f"(confidence: {ai_response.confidence}, priority: {ai_response.priority})"
            )

            return ai_response

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.error(f"Content: {content}")
            raise ValueError(f"Invalid JSON response from Claude: {str(e)}")

        except Exception as e:
            logger.error(f"Error getting decision from Claude: {e}")
            raise

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extract JSON from Claude's response.
        Claude sometimes wraps JSON in markdown code blocks.

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

        # If no code blocks, try to find JSON object in the content
        json_object_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
        if json_object_match:
            return json_object_match.group(0)

        # If all else fails, assume the entire content is JSON
        return content.strip()

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Claude"

    def get_model_name(self) -> str:
        """Get model name"""
        return self.model
