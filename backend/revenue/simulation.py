import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from decimal import Decimal


class RevenueEngine:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.simulation_history: Dict[str, list] = {}

    def simulate_agent_earnings(self, agent_type: str, strategy: str, days_active: int) -> Dict[str, Any]:
        if agent_type == "content":
            return self._simulate_content(days_active)
        elif agent_type == "affiliate":
            return self._simulate_affiliate(days_active)
        elif agent_type == "sales":
            return self._simulate_sales(days_active)
        elif agent_type == "digital_product":
            return self._simulate_digital_product(days_active)
        elif agent_type == "market":
            return self._simulate_market(days_active)
        else:
            return self._simulate_generic(days_active)

    def _simulate_content(self, days_active: int) -> Dict[str, Any]:
        base_views = random.randint(50, 500) * days_active
        ctr = random.uniform(0.01, 0.05)
        clicks = int(base_views * ctr)
        conversion_rate = random.uniform(0.01, 0.04)
        conversions = int(clicks * conversion_rate)
        revenue_per_conversion = random.uniform(0.5, 3.0)
        revenue = round(conversions * revenue_per_conversion, 2)
        expenses = round(random.uniform(0.1, 1.5) * days_active, 2)
        return {
            "revenue": revenue,
            "expenses": expenses,
            "metrics": {
                "impressions": base_views,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": round(ctr, 4),
                "conversion_rate": round(conversion_rate, 4),
            },
        }

    def _simulate_affiliate(self, days_active: int) -> Dict[str, Any]:
        clicks = random.randint(10, 200) * days_active
        conversions = int(clicks * random.uniform(0.02, 0.08))
        commission_per_sale = random.uniform(2.0, 25.0)
        revenue = round(conversions * commission_per_sale, 2)
        expenses = round(random.uniform(0.05, 0.8) * days_active, 2)
        return {
            "revenue": revenue,
            "expenses": expenses,
            "metrics": {
                "clicks": clicks,
                "conversions": conversions,
                "commission_rate": round(random.uniform(0.05, 0.15), 4),
            },
        }

    def _simulate_sales(self, days_active: int) -> Dict[str, Any]:
        leads = random.randint(5, 50) * days_active
        replies = int(leads * random.uniform(0.1, 0.3))
        meetings = int(replies * random.uniform(0.2, 0.5))
        deals = int(meetings * random.uniform(0.1, 0.4))
        avg_deal_size = random.uniform(50.0, 500.0)
        revenue = round(deals * avg_deal_size, 2)
        expenses = round(random.uniform(0.2, 2.0) * days_active, 2)
        return {
            "revenue": revenue,
            "expenses": expenses,
            "metrics": {
                "leads": leads,
                "replies": replies,
                "meetings": meetings,
                "deals": deals,
                "avg_deal_size": round(avg_deal_size, 2),
            },
        }

    def _simulate_digital_product(self, days_active: int) -> Dict[str, Any]:
        views = random.randint(20, 300) * days_active
        purchases = int(views * random.uniform(0.01, 0.03))
        price = random.uniform(9.99, 49.99)
        revenue = round(purchases * price, 2)
        expenses = round(random.uniform(0.5, 3.0) * days_active, 2)
        return {
            "revenue": revenue,
            "expenses": expenses,
            "metrics": {
                "views": views,
                "purchases": purchases,
                "price": round(price, 2),
            },
        }

    def _simulate_market(self, days_active: int) -> Dict[str, Any]:
        trades = random.randint(1, 10) * days_active
        win_rate = random.uniform(0.4, 0.7)
        wins = int(trades * win_rate)
        losses = trades - wins
        avg_win = random.uniform(5.0, 50.0)
        avg_loss = random.uniform(2.0, 20.0)
        revenue = round(wins * avg_win - losses * avg_loss, 2)
        expenses = round(random.uniform(0.01, 0.1) * days_active, 2)
        return {
            "revenue": revenue,
            "expenses": expenses,
            "metrics": {
                "trades": trades,
                "wins": wins,
                "losses": losses,
                "win_rate": round(win_rate, 4),
            },
        }

    def _simulate_generic(self, days_active: int) -> Dict[str, Any]:
        revenue = round(random.uniform(0.0, 5.0) * days_active, 2)
        expenses = round(random.uniform(0.1, 1.0) * days_active, 2)
        return {
            "revenue": revenue,
            "expenses": expenses,
            "metrics": {},
        }

    def run_daily_simulation(self, agent) -> Dict[str, Any]:
        agent_key = f"{agent.agent_type}:{agent.strategy}"
        if agent_key not in self.simulation_history:
            self.simulation_history[agent_key] = []

        result = self.simulate_agent_earnings(agent.agent_type, agent.strategy, max(1, agent.days_alive))
        result["simulated_at"] = datetime.now(timezone.utc).isoformat()
        result["agent_type"] = agent.agent_type
        result["strategy"] = agent.strategy

        self.simulation_history[agent_key].append(result)
        return result
