"""Factory for creating LLM provider instances."""

from __future__ import annotations

from app.rag.llm.base import BaseLLMProvider


class LLMFactory:
    """Creates LLM provider instances based on a provider name string."""

    _registry: dict[str, type[BaseLLMProvider]] = {}

    @classmethod
    def _ensure_registered(cls) -> None:
        if cls._registry:
            return
        from app.rag.llm.anthropic import AnthropicProvider
        from app.rag.llm.openai import OpenAIProvider

        cls._registry["anthropic"] = AnthropicProvider
        cls._registry["openai"] = OpenAIProvider

    @classmethod
    def register(cls, name: str, provider_class: type[BaseLLMProvider]) -> None:
        cls._registry[name] = provider_class

    @classmethod
    def create(cls, provider: str, **kwargs) -> BaseLLMProvider:
        cls._ensure_registered()
        provider_cls = cls._registry.get(provider)
        if provider_cls is None:
            available = ", ".join(sorted(cls._registry.keys()))
            raise ValueError(
                f"Unknown LLM provider '{provider}'. Available: {available}"
            )
        return provider_cls(**kwargs)

    @classmethod
    def available_providers(cls) -> list[str]:
        cls._ensure_registered()
        return sorted(cls._registry.keys())
