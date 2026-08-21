import json
import logging

from .base import BaseDateExtractor, RESPONSE_SCHEMA, EXTRACTION_RULES

logger = logging.getLogger(__name__)


class OpenAIDateExtractor(BaseDateExtractor):
    """Date extraction via the OpenAI chat completions API."""

    def build_system_prompt(self) -> str:
        """
        The call sets response_format={"type": "json_object"}, so the API will
        not return anything that is not valid JSON. Telling the model to avoid
        markdown fences would be describing an impossibility, so that line is
        absent here and present in the Claude variant.

        JSON mode does require the literal word "JSON" somewhere in the
        messages -- the schema line supplies it. Reword that line without the
        word and the request 400s.
        """
        return "\n\n".join([
            self.today_line(),
            "Respond with a JSON object matching this schema:\n" + RESPONSE_SCHEMA,
            EXTRACTION_RULES,
        ])

    async def extract(self, email_body: str) -> dict:
        response = await self.llm_provider.client.chat.completions.create(
            model=self.llm_provider.model,
            messages=[
                {"role": "system", "content": self.build_system_prompt()},
                {"role": "user", "content": self.build_user_prompt(email_body)},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=500,
        )
        return json.loads(response.choices[0].message.content)
