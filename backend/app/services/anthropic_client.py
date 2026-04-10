from dataclasses import dataclass
from decimal import Decimal
import anthropic
from anthropic import Anthropic
from app.config import settings

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-4-6"
CONFIDENCE_THRESHOLD = Decimal("0.7")


class AnthropicClassificationError(Exception):
    """Raised when Anthropic API call fails or returns unexpected response."""


@dataclass
class ClassificationResult:
    category_name: str
    confidence: Decimal
    reasoning: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class AnthropicClient:
    def __init__(self):
        self._client = Anthropic(api_key=settings.anthropic_api_key)

    def _call(self, model: str, prompt: str) -> ClassificationResult:
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
                tools=[{
                    "name": "classify_transaction",
                    "description": "Classify a bank transaction into a category.",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Category name from the provided list"},
                            "confidence": {"type": "number", "description": "Confidence 0.0 to 1.0"},
                            "reasoning": {"type": "string", "description": "One-sentence explanation"},
                        },
                        "required": ["category", "confidence", "reasoning"],
                    },
                }],
                tool_choice={"type": "tool", "name": "classify_transaction"},
            )
            tool_use = next(
                (b for b in response.content if b.type == "tool_use"), None
            )
            if tool_use is None:
                raise AnthropicClassificationError(
                    f"Model {model} returned no tool_use block"
                )
            data = tool_use.input
            usage = response.usage
            return ClassificationResult(
                category_name=data["category"],
                confidence=Decimal(str(data["confidence"])),
                reasoning=data["reasoning"],
                model=model,
                prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens,
            )
        except AnthropicClassificationError:
            raise
        except Exception as exc:
            raise AnthropicClassificationError(f"Anthropic API error ({model}): {exc}") from exc

    def classify(
        self,
        counterparty: str | None,
        description: str | None,
        amount: Decimal,
        categories: list[str],
    ) -> ClassificationResult:
        prompt = (
            f"Classify this bank transaction into one of the categories listed below.\n\n"
            f"Counterparty: {counterparty or 'unknown'}\n"
            f"Description: {description or 'none'}\n"
            f"Amount: {amount} CZK\n\n"
            f"Available categories:\n" + "\n".join(f"- {c}" for c in categories)
        )
        result = self._call(HAIKU, prompt)
        if result.confidence >= CONFIDENCE_THRESHOLD:
            return result
        # Escalate to Sonnet
        return self._call(SONNET, prompt)
