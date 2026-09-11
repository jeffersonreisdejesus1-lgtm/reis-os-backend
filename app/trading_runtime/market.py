from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen

from .strategy import Candle


@dataclass(frozen=True)
class BinancePublicClient:
    base_url: str = "https://api.binance.com"
    timeout_seconds: float = 5.0

    def klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> list[Candle]:
        params = urlencode({"symbol": symbol.replace("/", ""), "interval": interval, "limit": limit})
        url = f"{self.base_url}/api/v3/klines?{params}"
        with urlopen(url, timeout=self.timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        candles: list[Candle] = []
        for row in payload:
            candles.append(
                Candle(
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    close_time_ms=int(row[6]),
                )
            )
        return candles
