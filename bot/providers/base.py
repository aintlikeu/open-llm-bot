from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int


class BaseProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self, messages: list[dict[str, str]], model: str
    ) -> LLMResponse: ...

    @abstractmethod
    async def close(self) -> None: ...
