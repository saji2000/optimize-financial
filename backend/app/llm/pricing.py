from app.core.config import settings


def estimate_openai_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_hit_tokens: int = 0,
) -> tuple[float, float, float]:
    rates = settings.openai_model_pricing_usd_per_1m_tokens.get(model, {})
    input_rate = rates.get("input", 0.0)
    # Cached prompt tokens are billed at a lower rate when the provider exposes
    # them (e.g. DeepSeek prompt_cache_hit_tokens). Falls back to the standard
    # input rate, preserving single-rate behavior for providers without it.
    cache_hit_rate = rates.get("input_cache_hit", input_rate)
    output_rate = rates.get("output", 0.0)

    cache_hit_tokens = max(0, min(cache_hit_tokens, input_tokens))
    cache_miss_tokens = input_tokens - cache_hit_tokens

    input_cost = (
        (cache_miss_tokens / 1_000_000) * input_rate
        + (cache_hit_tokens / 1_000_000) * cache_hit_rate
    )
    output_cost = (output_tokens / 1_000_000) * output_rate
    return input_cost, output_cost, input_cost + output_cost
