# ADR-005: Provider-Agnostic LLM Abstraction Layer

**Date:** 2026-06-16
**Status:** Accepted
**Deciders:** Engineering Team

## Context

Auto Code uses a Large Language Model (LLM) as the "reasoning engine" in its RAG pipeline. After retrieving relevant ICD-10-CM codes from the vector database, the LLM receives the retrieved context and the user's clinical description, then produces a structured coding recommendation with explanations.

The LLM landscape is evolving rapidly:

1. **Model capabilities vary.** Anthropic Claude excels at following complex instructions and structured output. OpenAI GPT models have strong general reasoning. New models emerge frequently.
2. **Pricing varies significantly.** Claude 3.5 Sonnet vs. GPT-4o vs. Claude 3 Haiku represent 10x+ cost differences. Different customers may have different cost sensitivity.
3. **Provider availability.** API outages happen. A single-provider dependency creates a single point of failure for the core product function.
4. **Customer preferences.** Some healthcare organizations have existing agreements with specific AI providers. Some may require specific models for compliance reasons.
5. **Critical safety requirement.** The LLM must NEVER generate medical codes from its training data. It must ONLY use codes from the retrieved context. Hallucinated codes could lead to billing fraud, claim denials, or patient safety issues.

## Decision

Implement a **provider-agnostic LLM abstraction layer** using the Factory pattern with an abstract base class (ABC). Support Anthropic Claude and OpenAI GPT as initial providers, with the architecture enabling additional providers without modifying existing code.

### Architecture

```
┌─────────────────────────────────────────────────┐
│                  RAG Pipeline                    │
│                                                  │
│  retrieve_codes() -> LLMProvider.generate()      │
│                                                  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  LLMProviderABC │  (Abstract Base Class)
              │                 │
              │  + generate()   │
              │  + stream()     │
              │  + health()     │
              └────────┬────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
   ┌────────────┐ ┌──────────┐ ┌──────────┐
   │  Claude    │ │  OpenAI  │ │  Future  │
   │  Provider  │ │  Provider│ │  Provider│
   └────────────┘ └──────────┘ └──────────┘
          │            │
          ▼            ▼
   ┌────────────┐ ┌──────────┐
   │ Anthropic  │ │ OpenAI   │
   │ API        │ │ API      │
   └────────────┘ └──────────┘

              ┌─────────────────┐
              │  LLMFactory     │
              │                 │
              │  + create()     │  <- Reads provider config
              │  + get_default()│     from env/tenant settings
              └─────────────────┘
```

### Abstract Base Class

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class CodingResult(BaseModel):
    """Structured output from the LLM coding recommendation."""
    primary_code: str
    primary_description: str
    confidence: float  # 0.0 - 1.0
    reasoning: str
    additional_codes: list[AdditionalCode]
    warnings: list[CodingWarning]  # Excludes1 conflicts, Code First reminders
    source_chunks_used: list[str]  # IDs of retrieved chunks actually referenced

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        clinical_description: str,
        retrieved_context: list[RetrievedChunk],
        system_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> CodingResult:
        """Generate a coding recommendation from retrieved context."""
        ...

    @abstractmethod
    async def stream(
        self,
        clinical_description: str,
        retrieved_context: list[RetrievedChunk],
        system_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream a coding recommendation for real-time UI updates."""
        ...

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Check provider API availability and latency."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def model_name(self) -> str: ...

    @property
    @abstractmethod
    def max_context_window(self) -> int: ...
```

### Factory

```python
class LLMFactory:
    """Creates LLM provider instances based on configuration."""

    _providers: dict[str, type[LLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[LLMProvider]):
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, provider_name: str, **kwargs) -> LLMProvider:
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        return cls._providers[provider_name](**kwargs)

    @classmethod
    def get_default(cls) -> LLMProvider:
        """Create default provider from environment configuration."""
        provider = os.getenv("LLM_PROVIDER", "anthropic")
        model = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        return cls.create(provider, model=model)
```

### Initial Provider Implementations

| Provider | Default Model | Context Window | Strengths for This Use Case |
|---|---|---|---|
| **Anthropic Claude** | `claude-sonnet-4-20250514` | 200K tokens | Excellent instruction following, structured output, low hallucination rate. System prompt adherence is strong -- critical for the "only use retrieved context" constraint. |
| **OpenAI GPT** | `gpt-4o` | 128K tokens | Strong general reasoning, JSON mode for structured output, function calling. Wide enterprise adoption. |

### Negative Prompting: The Critical Safety Layer

The most important aspect of the LLM integration is **preventing hallucinated codes**. The system prompt enforces strict grounding:

```
SYSTEM PROMPT (core directives):

You are a medical coding assistant. Your ONLY job is to recommend
ICD-10-CM codes from the RETRIEVED CONTEXT provided below. You must
follow these rules absolutely:

1. NEVER generate, suggest, or reference any ICD-10-CM code that does
   not appear in the RETRIEVED CONTEXT section below. If a code is not
   in the retrieved context, it does not exist for the purposes of
   this interaction.

2. If the retrieved context does not contain a suitable code for the
   clinical description, respond with:
   "NO_MATCH: The retrieved context does not contain a code that
   matches this clinical description. Please refine the description
   or consult the ICD-10-CM manual."

3. NEVER use your training data knowledge of ICD-10-CM codes. Your
   training data may contain outdated codes, incorrect mappings, or
   codes from different code systems (ICD-9, CPT, HCPCS). Only the
   retrieved context is authoritative.

4. For every code you recommend, cite the specific chunk from the
   retrieved context that supports it. Include the chunk ID in your
   response.

5. Check for Excludes1 conflicts between recommended codes. If two
   recommended codes have an Excludes1 relationship (visible in the
   retrieved context), flag this as a WARNING and explain why they
   cannot be coded together.

6. If a code has a "Code First" or "Use Additional Code" instruction
   in the retrieved context, include this in your recommendation with
   the specific additional code(s) to consider.

7. Assign a confidence score (0.0-1.0) based on how well the clinical
   description matches the retrieved code descriptions:
   - 0.9-1.0: Near-exact match between description and code
   - 0.7-0.89: Strong semantic match with minor ambiguity
   - 0.5-0.69: Partial match, multiple codes could apply
   - Below 0.5: Weak match, recommend manual review

RETRIEVED CONTEXT:
{retrieved_chunks_formatted}

CLINICAL DESCRIPTION:
{user_query}
```

### Output Validation

Even with negative prompting, the LLM output is validated programmatically:

1. **Code existence check.** Every code in the LLM's response is verified against the retrieved context chunk IDs. Any code not present in the retrieved set is stripped from the response and logged as a hallucination attempt.
2. **Code format validation.** Regex validation ensures codes match ICD-10-CM format (`[A-Z][0-9]{2}(\.[A-Z0-9]{1,4})?`).
3. **Billable status check.** If the LLM recommends a non-billable (category) code, a warning is appended suggesting the user review child codes.
4. **Excludes1 cross-check.** Retrieved chunk payloads contain `excludes1_codes`. If the LLM recommends two codes that exclude each other, a warning is injected even if the LLM missed it.
5. **Structured output parsing.** Response is parsed into the `CodingResult` Pydantic model. If parsing fails, the raw response is returned with a parsing_error flag for debugging.

### Per-Tenant Configuration

Tenants can configure their preferred LLM provider and model:

```python
# tenant_settings table
{
    "tenant_id": "uuid",
    "llm_provider": "anthropic",       # or "openai"
    "llm_model": "claude-sonnet-4-20250514",  # or "gpt-4o"
    "temperature": 0.0,                 # most tenants should use 0
    "max_tokens": 2048,
    "custom_system_prompt_addendum": "..." # tenant-specific instructions
}
```

The factory reads tenant settings and creates the appropriate provider at request time. Provider instances are pooled and reused for the same configuration.

### Fallback and Retry

```python
class LLMOrchestrator:
    """Manages provider selection, fallback, and retry logic."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider | None):
        self.primary = primary
        self.fallback = fallback

    async def generate(self, ...) -> CodingResult:
        try:
            return await self.primary.generate(...)
        except (ProviderUnavailableError, RateLimitError) as e:
            if self.fallback:
                log.warning(f"Primary provider failed: {e}. Falling back.")
                return await self.fallback.generate(...)
            raise
```

## Alternatives Considered

### LangChain / LlamaIndex Abstraction
- **Rejected.** Both are large, opinionated frameworks with extensive dependency trees. They provide abstractions over LLM providers but also impose patterns (chains, agents, indices) that we do not need. Our use case is a focused RAG pipeline with specific medical coding constraints -- a thin custom abstraction is simpler, more testable, and has no unnecessary dependencies.
- LangChain's LLM abstraction changes frequently across versions, creating maintenance burden.

### Direct SDK Calls (No Abstraction)
- **Rejected.** Using `anthropic` and `openai` SDKs directly in the RAG pipeline would couple business logic to specific providers. Switching or adding providers would require modifying core pipeline code. The abstraction layer is lightweight (~200 lines) and pays for itself immediately.

### Single Provider (Anthropic Only)
- **Rejected.** While Claude is the preferred model for instruction following, a single-provider dependency creates availability risk and limits customer flexibility. The abstraction cost is minimal and the optionality is valuable.

### Open-Source Models (Llama, Mistral) via vLLM/Ollama
- **Deferred.** Self-hosted open-source models would eliminate API costs and keep all data on-premises. However, current open-source models at the 7-70B parameter range do not match Claude/GPT-4o in structured output reliability and instruction following for medical coding tasks. Plan to evaluate as models improve. The abstraction layer makes adding a `VLLMProvider` straightforward.

## Consequences

### Positive
- **Provider flexibility.** Switch between Anthropic and OpenAI with a configuration change. No code modifications.
- **Fallback resilience.** If the primary provider is down, the system falls back to the secondary automatically.
- **Per-tenant customization.** Different tenants can use different models based on their needs and agreements.
- **Testability.** The ABC enables a `MockLLMProvider` for deterministic testing without API calls.
- **Safety layer.** Negative prompting + programmatic validation creates defense-in-depth against hallucinated codes.

### Negative
- **Prompt divergence.** Optimal prompts may differ between Claude and GPT. A single system prompt may not extract the best performance from both. Mitigation: allow provider-specific prompt templates with shared core directives.
- **Feature parity challenges.** Providers have different capabilities (Claude's extended thinking vs. GPT's function calling). The abstraction may need provider-specific paths for advanced features.
- **Additional testing surface.** Must test the same user scenarios against each supported provider to ensure consistent output quality.

### Mitigations
- Maintain a provider-specific prompt template system with shared core directives and provider-optimized formatting.
- Run automated evaluation suites with a fixed set of clinical descriptions against each provider to measure code recommendation accuracy.
- Log all LLM interactions (prompt, response, latency, cost, hallucination flags) for quality monitoring and cost tracking.

## References

- [Anthropic Claude API Documentation](https://docs.anthropic.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [Factory Method Pattern](https://refactoring.guru/design-patterns/factory-method)
- ADR-001: Vector Database Selection (Qdrant)
- ADR-002: Chunking Strategy
- ADR-003: Embedding Model Selection
