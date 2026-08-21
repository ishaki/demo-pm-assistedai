import json
import logging

from .base import BaseDateExtractor, RESPONSE_SCHEMA, EXTRACTION_RULES

logger = logging.getLogger(__name__)


class GeminiDateExtractor(BaseDateExtractor):
    """Date extraction via the Google GenAI API."""

    def build_system_prompt(self) -> str:
        """
        extract() sets response_mime_type="application/json", so the format is
        enforced by the config rather than by prose -- no anti-fence wording
        needed, as with OpenAI.

        The call path used here has no separate system role, so this text is
        prepended to the user turn. That is why it names the delimiters the
        email body will arrive in: without a role boundary, the model needs to
        be told where the instructions stop and the data starts.
        """
        return "\n\n".join([
            self.today_line(),
            "Return a JSON object matching this schema:\n" + RESPONSE_SCHEMA,
            "The message to read is delimited by <email_body> tags.",
            EXTRACTION_RULES,
        ])

    async def extract(self, email_body: str) -> dict:
        """
        Async to match the interface, though generate_content is synchronous.

        Builds a config of its own rather than reusing the provider's shared
        generation_config: that one is tuned for the decision call, and this
        adds a response mime type. Mutating the shared object would change
        decision behaviour as a side effect.
        """
        from google.genai import types

        prompt = f"{self.build_system_prompt()}\n\n{self.build_user_prompt(email_body)}"

        response = self.llm_provider.client.models.generate_content(
            model=self.llm_provider.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
                response_mime_type="application/json",
            ),
        )

        return json.loads(self.json_from_response(response.text))
