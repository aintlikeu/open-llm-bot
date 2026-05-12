from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class BalanceInfo:
    currency: str
    total_balance: float
    granted_balance: float
    topped_up_balance: float


class BaseProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self, messages: list[dict[str, str]], model: str
    ) -> LLMResponse: ...

    @abstractmethod
    async def get_balance(self) -> list[BalanceInfo]: ...

    @abstractmethod
    async def close(self) -> None: ...
