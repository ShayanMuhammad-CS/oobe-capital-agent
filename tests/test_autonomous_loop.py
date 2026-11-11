import unittest
import os
from oobe_agent.core import OOBECapitalAgent

class TestOOBECapitalAgentLoop(unittest.TestCase):
    """
    End-to-end tests for the Autonomous Capital Agent lifecycle.
    """

    def setUp(self):
        self.test_state = "scratch_test_agent_state.json"
        self.agent = OOBECapitalAgent(
            public_key="AgentVault111111111111111111111111111111111",
            storage_path=self.test_state
        )

    def tearDown(self):
        if os.path.exists(self.test_state):
            os.remove(self.test_state)

    def test_autonomous_cycle_execution(self):
        cycle = self.agent.run_autonomous_cycle()
        self.assertEqual(cycle["cycle_status"], "COMPLETED")
        self.assertIn("merkle_root", cycle)
        self.assertIn("receipt_hash", cycle)
        self.assertIn("strategy_outcome", cycle)
        self.assertGreater(cycle["execution_duration_sec"], 0.0)

    def test_export_audit_report(self):
        # Run 2 cycles to generate verifiable history
        self.agent.run_autonomous_cycle()
        self.agent.run_autonomous_cycle()

        report = self.agent.export_audit_report()
        self.assertEqual(report["agent_pubkey"], "AgentVault111111111111111111111111111111111")
        self.assertGreaterEqual(report["total_receipts"], 2)
        self.assertEqual(len(report["merkle_root"]), 64)
        self.assertIn("recent_actions", report)

    def test_rebalance_trigger_on_heavy_drift(self):
        # Artificially skew balances to trigger rebalance
        # 40 SOL * 180 = $7200 vs 100 USDC = $100 -> ~98% SOL weight (target 60%)
        self.agent.wallet._balances = {"SOL": 40.0, "USDC": 100.0}
        
        cycle = self.agent.run_autonomous_cycle()
        outcome = cycle["strategy_outcome"]
        self.assertEqual(outcome["action"], "REBALANCE_SELL_SOL")
        self.assertIn("swap_result", outcome)
        self.assertEqual(outcome["swap_result"]["status"], "CONFIRMED")
        # Check that USDC balance increased
        self.assertGreater(self.agent.wallet.get_balance("USDC"), 100.0)

if __name__ == "__main__":
    unittest.main()
