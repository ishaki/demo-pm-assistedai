import json
import logging

from .base import BaseDateExtractor, RESPONSE_SCHEMA, EXTRACTION_RULES

logger = logging.getLogger(__name__)

# Pulling one date out of one short email is a small, well-specified job, and
# Haiku does it as accurately as the larger models for a fraction of the cost
# and latency. Pinned rather than taken from LLM_MODEL on purpose: that setting
# picks the model for the *decision* call, which weighs maintenance history and
# wants the stronger model. The two jobs should be free to differ.
DATE_EXTRACTION_MODEL = "claude-haiku-4-5-20251001"


class ClaudeDateExtractor(BaseDateExtractor):
    """Date extraction via the Anthropic messages API."""

    model = DATE_EXTRACTION_MODEL

    def build_system_prompt(self) -> str:
        """
        There is no JSON mode here, so the instruction has to do the work:
        Claude will otherwise wrap the object in ```json fences or open with a
        sentence of preamble. json_from_response is the safety net, not the
        plan.

        The usual trick of prefilling the assistant turn with "{" is
        deliberately not used. Thinking is adaptive-on across the recent
        families, and prefill is rejected while thinking is active.
        """
        return "\n\n".join([
            self.today_line(),
            "Return ONLY a JSON object, no preamble, no markdown fences:\n" + RESPONSE_SCHEMA,
            EXTRACTION_RULES,
        ])

    async def extract(self, email_body: str) -> dict:
        """
        Kept deliberately in step with ClaudeProvider.get_decision, which
        learned all three of these the hard way:

        - No temperature. Sampling parameters were removed on Sonnet 5 and the
          rest of the 4.6+ family, and sending one is rejected -- as a 400 on
          older SDKs, and as a TypeError on newer ones that dropped the
          argument outright. Either way the caller's except block swallowed it
          and reported confidence 0.0, so every supplier reply looked like an
          unreadable one. Omitted here regardless of what this model would
          accept, so the call cannot break again when the pin moves.
        - max_tokens covers thinking as well as the visible reply, so a small
          ceiling can be spent reasoning and truncate the JSON mid-object.
        - The first content block is a thinking block when thinking runs, and
          it has no .text at all. Take the first *text* block instead.
        """
        message = await self.llm_provider.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.build_system_prompt(),
            messages=[{"role": "user", "content": self.build_user_prompt(email_body)}],
        )

        content = next(
            (block.text for block in message.content if block.type == "text"),
            None
        )

        if content is None:
            raise ValueError(
                f"Claude returned no text block (stop_reason={message.stop_reason})"
            )

        return json.loads(self.json_from_response(content))
