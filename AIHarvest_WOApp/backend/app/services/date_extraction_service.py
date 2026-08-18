import json
import re
import logging
from ..services.llm_providers import get_llm_provider

logger = logging.getLogger(__name__)


class DateExtractionService:
    """Service to extract dates from email using AI"""

    def __init__(self):
        self.llm_provider = get_llm_provider()
        self.confidence_threshold = 0.7

    async def extract_date_from_email(self, email_body: str) -> dict:
        """
        Extract scheduled maintenance date from email body using AI.

        Args:
            email_body: Email body text

        Returns:
            dict with keys:
                - selected_date: ISO format date string (YYYY-MM-DD) or None
                - confidence: float (0.0-1.0)
                - explanation: string describing the extraction
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(email_body)

        try:
            # Use existing LLM provider pattern
            provider_name = self.llm_provider.get_provider_name()

            if provider_name == "OpenAI":
                result = await self._extract_with_openai(system_prompt, user_prompt)
            elif provider_name == "Claude":
                result = await self._extract_with_claude(system_prompt, user_prompt)
            elif provider_name == "Gemini":
                result = self._extract_with_gemini(system_prompt, user_prompt)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider_name}")

            logger.info(f"Date extraction result: {result}")
            return result

        except Exception as e:
            logger.error(f"Error extracting date from email: {e}")
            return {
                "selected_date": None,
                "confidence": 0.0,
                "explanation": f"Error during extraction: {str(e)}"
            }

    async def _extract_with_openai(self, system_prompt: str, user_prompt: str) -> dict:
        """Extract date using OpenAI provider"""
        response = await self.llm_provider.client.chat.completions.create(
            model=self.llm_provider.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500
        )
        content = response.choices[0].message.content
        return json.loads(content)

    async def _extract_with_claude(self, system_prompt: str, user_prompt: str) -> dict:
        """Extract date using Claude provider"""
        message = await self.llm_provider.client.messages.create(
            model=self.llm_provider.model,
            max_tokens=1024,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        content = message.content[0].text
        # Extract JSON from markdown if needed
        content = self._extract_json_from_response(content)
        return json.loads(content)

    def _extract_with_gemini(self, system_prompt: str, user_prompt: str) -> dict:
        """Extract date using Gemini provider"""
        # Combine system and user prompts for Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"

        # Gemini's generate_content is synchronous, not async
        response = self.llm_provider.client.models.generate_content(
            model=self.llm_provider.model_name,
            contents=full_prompt,
            config=self.llm_provider.generation_config
        )

        content = response.text
        # Extract JSON from markdown if needed
        content = self._extract_json_from_response(content)
        return json.loads(content)

    def _extract_json_from_response(self, content: str) -> str:
        """Extract JSON from Claude response (may have markdown)"""
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # Try generic code block
        code_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # Find JSON object in content
        json_object_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
        if json_object_match:
            return json_object_match.group(0)

        return content.strip()

    def _build_system_prompt(self) -> str:
        """Build system prompt for date extraction"""
        return """You are a date extraction assistant for maintenance scheduling emails.
Your task is to extract the scheduled maintenance date from email content.

**Instructions:**
1. Look for explicit dates in the email (e.g., "January 15, 2024", "2024-01-15", "15/01/2024")
2. Identify dates that refer to scheduled work, appointments, or planned maintenance
3. Ignore email timestamps, past events, or unrelated dates
4. Return the date in ISO format (YYYY-MM-DD)
5. Only select dates that are in the future or today

**Confidence Guidelines:**
- 0.9-1.0: Clear, explicit scheduled date mentioned
- 0.7-0.89: Likely date but some ambiguity
- 0.5-0.69: Uncertain, multiple dates or unclear context
- Below 0.5: No clear scheduled date found

**Response Schema (JSON only):**
{
  "selected_date": "2024-01-15",
  "confidence": 0.95,
  "explanation": "Found scheduled maintenance date mentioned explicitly in email"
}

If no clear date is found, return:
{
  "selected_date": null,
  "confidence": 0.0,
  "explanation": "No scheduled date found in email"
}"""

    def _build_user_prompt(self, email_body: str) -> str:
        """Build user prompt with email body"""
        return f"""**Email Body:**
{email_body}

**Your Task:**
Extract the scheduled maintenance date from this email. Return your analysis in JSON format only."""
