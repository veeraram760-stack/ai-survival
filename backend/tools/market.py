"""
Real market data tools for agents using free public APIs.
"""
import os
import httpx
from typing import Dict, Any, Optional, List
from .base import Tool, tool_registry
import logging

logger = logging.getLogger("ai_survival.tools.market")


class MarketDataTool(Tool):
    """Fetch real market data from free public APIs"""

    def __init__(self):
        super().__init__(
            name="market_data",
            description="Fetch real market prices and trends from public APIs",
            cost=0.0,
        )

    async def execute(
        self,
        symbol: Optional[str] = None,
        source: str = "coingecko",
        days: int = 7,
        **kwargs,
    ) -> Dict[str, Any]:
        if not symbol:
            return {"status": "failed", "error": "symbol is required"}
        if source == "coingecko":
            return await self._coingecko(symbol, days)
        return {"status": "failed", "error": f"Unsupported source: {source}"}

    async def _coingecko(self, symbol: str, days: int) -> Dict[str, Any]:
        try:
            coin_id = symbol.lower()
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                params = {"vs_currency": "usd", "days": days}
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                prices = data.get("prices", [])
                if not prices:
                    return {"status": "failed", "error": "No price data returned"}

                latest_price = prices[-1][1]
                prev_price = prices[0][1] if len(prices) > 1 else latest_price
                change_pct = ((latest_price - prev_price) / prev_price * 100) if prev_price else 0.0

                return {
                    "status": "success",
                    "source": "coingecko",
                    "symbol": symbol,
                    "latest_price": latest_price,
                    "change_pct": change_pct,
                    "prices": prices,
                }
        except Exception as e:
            logger.error(f"Market data fetch failed: {e}")
            return {"status": "failed", "error": str(e)}


tool_registry.register(MarketDataTool())
