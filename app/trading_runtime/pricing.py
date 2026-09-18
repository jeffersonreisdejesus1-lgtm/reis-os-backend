from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProviderPrice:
    provider: str
    model: str
    input_price: Decimal
    cached_input_price: Decimal
    output_price: Decimal
    currency: str
    effective_at: str
    source: str


class ProviderPricingRegistry:
    def __init__(self) -> None:
        self._prices: dict[tuple[str, str], ProviderPrice] = {}

    def register(self, price: ProviderPrice) -> None:
        if min(price.input_price, price.cached_input_price, price.output_price) < 0:
            raise ValueError("prices must be non-negative")
        self._prices[(price.provider, price.model)] = price

    def get(self, provider: str, model: str) -> ProviderPrice:
        try:
            return self._prices[(provider, model)]
        except KeyError as exc:
            raise KeyError("provider/model pricing is not configured") from exc
