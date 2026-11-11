import unittest
from oobe_agent.solana_wallet import SolanaWalletManager
from oobe_agent.risk_guardrails import RiskGuardrailEngine
from oobe_agent.memory import AgentMemoryEngine
from oobe_agent.mcp_gateway import SAPMCPGateway

class TestSAPMCPGateway(unittest.TestCase):
    """
    Tests for Model Context Protocol (MCP) conformance, tool registration, and dispatch.
    """

    def setUp(self):
        self.guardrails = RiskGuardrailEngine(min_sol_reserve=1.0, max_single_trade_sol=10.0)
        self.wallet = SolanaWalletManager(
            public_key="TestPubKey1111111111111111111111111111111111",
            guardrails=self.guardrails
        )
        self.wallet._balances = {"SOL": 20.0, "USDC": 2000.0}
        self.memory = AgentMemoryEngine()
        self.mcp = SAPMCPGateway(wallet=self.wallet, memory=self.memory)

    def test_list_tools_schema_conformance(self):
        tools = self.mcp.list_tools()
        self.assertGreaterEqual(len(tools), 5)
        for tool in tools:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_invoke_get_treasury_balance(self):
        res = self.mcp.invoke_tool("get_treasury_balance", {"token": "SOL"})
        self.assertTrue(res["success"])
        self.assertEqual(res["result"]["balance"], 20.0)
        self.assertIsNotNone(res["receipt_hash"])

    def test_invoke_emergency_killswitch(self):
        res = self.mcp.invoke_tool("trigger_emergency_killswitch", {"reason": "Test Killswitch"})
        self.assertTrue(res["success"])
        self.assertTrue(self.guardrails.is_circuit_breaker_active)

        # Subsequent transfers must fail
        fail_res = self.mcp.invoke_tool("execute_capital_transfer", {
            "amount_sol": 1.0,
            "destination": "Dest11111111111111111111111111111111111111"
        })
        self.assertFalse(fail_res["success"])
        self.assertIn("Circuit breaker active", fail_res["error"])

    def test_invoke_unknown_tool_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.mcp.invoke_tool("non_existent_tool", {})

if __name__ == "__main__":
    unittest.main()
