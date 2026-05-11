import httpx

from bot.providers.base import BaseProvider, LLMResponse

PRICING: dict[str, dict[str, float]] = {
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
}


class DeepSeekProvider(BaseProvider):
    BASE_URL = "https://api.deepseek.com"

    def __init__(self, api_key: str) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120.0,
        )

    async def chat_completion(
        self, messages: list[dict[str, str]], model: str
    ) -> LLMResponse:
        response = await self.client.post(
            "/chat/completions",
            json={"model": model, "messages": messages, "stream": False},
        )
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]["message"]
        usage = data.get("usage", {})
        content = choice.get("content") or choice.get("reasoning_content") or ""
        return LLMResponse(
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
        )

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def calculate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
        prices = PRICING.get(model, {"input": 0.0, "output": 0.0})
        return (
            prompt_tokens * prices["input"] / 1_000_000
            + completion_tokens * prices["output"] / 1_000_000
        )
