import unittest
import asyncio

from mcp import Client

from server import server


class MCPServerContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        asyncio.get_running_loop().slow_callback_duration = 1.0

    async def test_client_discovers_tools_and_calls_summary(self):
        async with Client(server) as client:
            tools = await client.list_tools()
            discovered = {tool.name: tool for tool in tools.tools}
            names = set(discovered)
            self.assertEqual(names, {
                "list_available_data",
                "get_portfolio_summary",
                "compare_portfolio_periods",
                "get_program_detail",
            })
            self.assertTrue(discovered["get_portfolio_summary"].annotations.read_only_hint)
            self.assertIsNotNone(discovered["get_portfolio_summary"].output_schema)
            result = await client.call_tool("get_portfolio_summary", {"period": "2026-09"})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content["spend_usd"], 342000)

    async def test_invalid_period_returns_actionable_tool_result(self):
        async with Client(server) as client:
            result = await client.call_tool("get_portfolio_summary", {"period": "2026-10"})
            self.assertFalse(result.is_error)
            self.assertIn("Unknown period", result.structured_content["error"])

    async def test_server_exposes_resource_and_prompt(self):
        async with Client(server) as client:
            resources = await client.list_resources()
            prompts = await client.list_prompts()
            self.assertEqual(resources.resources[0].uri, "analytics://portfolio/data-dictionary")
            self.assertEqual(prompts.prompts[0].name, "monthly_portfolio_review")


if __name__ == "__main__":
    unittest.main()
