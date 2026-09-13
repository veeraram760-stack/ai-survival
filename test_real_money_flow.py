#!/usr/bin/env python3
"""
End-to-end test for real money affiliate agent flow:
web_search -> affiliate_link -> generate_content -> publish_content -> conversion tracking
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest

from decimal import Decimal
from uuid import uuid4

from backend.database.connection import init_db, DBSessionFactory
from backend.agents.orchestrator import AgentOrchestrator
from backend.agents.ceo import CEODecisionMaker
from backend.revenue.simulation import RevenueEngine
from backend.risk.manager import RiskManager
from backend.finance.ledger import CapitalLedger
from backend.execution.engine import ExecutionEngine
from backend.tools import tool_registry
from config.settings import settings


@pytest.mark.skip(
    reason="End-to-end real-money smoke script; requires live Postgres, LLM, and API "
    "keys. Run manually via `python test_real_money_flow.py`."
)
async def test_affiliate_flow():
    """Test the full affiliate agent flow with real API calls"""
    print("=" * 60)
    print("TESTING REAL MONEY AFFILIATE AGENT FLOW")
    print("=" * 60)
    print(f"Real money only mode: {settings.real_money_only}")
    print(f"LLM Provider: {settings.llm_provider}")
    print()

    # Initialize database
    await init_db()
    db_factory = DBSessionFactory()

    # Initialize components
    capital_ledger = CapitalLedger(starting_capital=50.0)
    risk_manager = RiskManager(capital_ledger)
    orchestrator = AgentOrchestrator(capital_ledger, risk_manager)
    ceo = CEODecisionMaker(orchestrator, capital_ledger, risk_manager)
    revenue_engine = RevenueEngine()
    execution_engine = ExecutionEngine(capital_ledger)

    orchestrator.ceo = ceo
    orchestrator.revenue_engine = revenue_engine
    orchestrator.execution_engine = execution_engine
    orchestrator.set_db_factory(db_factory.session)

    print("\n1. Creating affiliate agent...")
    async with db_factory.session() as db:
        agent = await orchestrator.factory.create_agent(
            db=db,
            agent_type="affiliate",
            strategy="niche_affiliate",
        )
        orchestrator.agents[agent.id] = agent
        await db.commit()
        print(f"   Created agent: {agent.id} ({agent.agent_type}:{agent.strategy})")

    # Test individual tools first
    print("\n2. Testing individual tools...")

    # Test web_search
    print("\n   a) web_search tool:")
    web_search_tool = tool_registry.get("web_search")
    if web_search_tool:
        result = await web_search_tool.execute(query="best productivity tools 2024", max_results=3)
        print(f"      Status: {result.get('status')}")
        print(f"      Results: {len(result.get('results', []))} items")
        if result.get('results'):
            print(f"      First result: {result['results'][0].get('title', 'N/A')[:60]}")
    else:
        print("      Tool not found!")

    # Test affiliate_link with Amazon
    print("\n   b) affiliate_link tool (Amazon):")
    affiliate_tool = tool_registry.get("affiliate_link")
    if affiliate_tool:
        result = await affiliate_tool.execute(
            product_url="https://www.amazon.com/dp/B09V3KXJPB",
            network="amazon",
            campaign_id="test_campaign_001",
            agent_id=agent.id
        )
        print(f"      Status: {result.get('status')}")
        print(f"      Affiliate URL: {result.get('affiliate_url', 'N/A')[:80]}")
        print(f"      Tracking params: {result.get('tracking_params', {})}")
    else:
        print("      Tool not found!")

    # Test affiliate_link with ShareASale
    print("\n   c) affiliate_link tool (ShareASale):")
    if affiliate_tool:
        result = await affiliate_tool.execute(
            product_url="https://www.example.com/product/123",
            network="shareasale",
            merchant_id="12345",
            campaign_id="test_campaign_002",
            agent_id=agent.id
        )
        print(f"      Status: {result.get('status')}")
        print(f"      Affiliate URL: {result.get('affiliate_url', 'N/A')[:80]}")
    else:
        print("      Tool not found!")

    # Test generate_content
    print("\n   d) generate_content tool:")
    content_tool = tool_registry.get("generate_content")
    if content_tool:
        result = await content_tool.execute(
            topic="best productivity tools for remote work",
            content_type="blog_post",
            tone="informative",
            length="medium",
            affiliate_url="https://amzn.to/test123?ref=test_campaign_001&agent=aff_agent_001"
        )
        print(f"      Status: {result.get('status')}")
        print(f"      Content preview: {result.get('content', '')[:150]}...")
        print(f"      Word count: {result.get('word_count', 0)}")
    else:
        print("      Tool not found!")

    # Test publish_content to webhook
    print("\n   e) publish_content tool (webhook):")
    publish_tool = tool_registry.get("publish_content")
    if publish_tool:
        content_result = await content_tool.execute(
            topic="best productivity tools for remote work",
            content_type="tweet",
            tone="engaging",
            length="short",
            affiliate_url="https://amzn.to/test123?ref=test_campaign_001&agent=aff_agent_001"
        )

        result = await publish_tool.execute(
            content=content_result.get("content", ""),
            platform="webhook",
            affiliate_url="https://amzn.to/test123?ref=test_campaign_001&agent=aff_agent_001",
            campaign_id="test_campaign_001",
            agent_id=agent.id
        )
        print(f"      Status: {result.get('status')}")
        print(f"      Platform: {result.get('platform')}")
        print(f"      URL: {result.get('url')}")
    else:
        print("      Tool not found!")

    # Test execution engine full task
    print("\n3. Testing execution engine with affiliate_marketing task...")
    async with db_factory.session() as db:
        task_data = {
            "agent_type": "affiliate",
            "strategy": "niche_affiliate",
            "days_alive": 1,
            "capabilities": ["web_search", "affiliate_link", "generate_content", "publish_content"],
        }
        result = await execution_engine.execute_agent_task(
            db, agent.id, "affiliate_marketing", task_data
        )
        print(f"   Status: {result.get('status')}")
        print(f"   Revenue: ${result.get('revenue', 0):.2f}")
        print(f"   Expenses: ${result.get('expenses', 0):.2f}")
        print(f"   Real: {result.get('real', False)}")
        if result.get('tool_results'):
            print("   Tool results:")
            for tool_name, tool_result in result['tool_results'].items():
                print(f"      {tool_name}: {tool_result.get('status', 'N/A')}")

    # Test conversion tracking tool
    print("\n4. Testing conversion tracking tool...")
    conversion_tool = tool_registry.get("track_conversions")
    if conversion_tool:
        result = await conversion_tool.execute(network="amazon")
        print(f"   Status: {result.get('status')}")
        if result.get('networks'):
            for net, data in result['networks'].items():
                print(f"   {net}: {data.get('status')}")
    else:
        print("   Tool not found!")

    # Test webhook conversion endpoint simulation
    print("\n5. Simulating webhook conversion...")
    from backend.main import webhook_conversion
    from starlette.requests import Request
    from starlette.datastructures import Headers

    # Create a mock request
    class MockRequest:
        def __init__(self, json_data):
            self._json = json_data
            self.app = type('obj', (object,), {
                'state': type('obj', (object,), {
                    'capital_ledger': capital_ledger,
                    'orchestrator': orchestrator
                })()
            })()

        async def json(self):
            return self._json

    mock_request = MockRequest({
        "source": "amazon",
        "transaction_id": "TEST_TXN_12345",
        "amount": 49.99,
        "commission": 2.50,
        "currency": "USD",
        "campaign_id": "test_campaign_001",
        "agent_id": agent.id
    })

    # We need to mock the DB session - skip this test for now
    print("   (Skipping full webhook test - requires DB session)")

    # Print final state
    print("\n6. Final system state:")
    snapshot = capital_ledger.get_capital_snapshot()
    print(f"   Total Capital: ${snapshot['total_capital']:.2f}")
    print(f"   Survival Reserve: ${snapshot['survival_reserve']:.2f}")
    print(f"   Operating Capital: ${snapshot['operating_capital']:.2f}")
    print(f"   Growth Capital: ${snapshot['growth_capital']:.2f}")

    print(f"\n   Agent {agent.id}:")
    print(f"      Revenue: ${agent.revenue:.2f}")
    print(f"      Expenses: ${agent.expenses:.2f}")
    print(f"      Profit: ${agent.profit:.2f}")
    print(f"      ROI: {agent.roi:.2f}")
    print(f"      Status: {agent.status.value}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_affiliate_flow())