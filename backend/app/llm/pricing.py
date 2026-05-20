from app.core.config import settings


def estimate_openai_cost_usd(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> tuple[float, float, float]:
    rates = settings.openai_model_pricing_usd_per_1m_tokens.get(model, {})
    input_rate = rates.get("input", 0.0)
    output_rate = rates.get("output", 0.0)

    input_cost = (input_tokens / 1_000_000) * input_rate
    output_cost = (output_tokens / 1_000_000) * output_rate
    return input_cost, output_cost, input_cost + output_cost
