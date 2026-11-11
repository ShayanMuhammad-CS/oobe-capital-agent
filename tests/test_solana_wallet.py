import unittest
from oobe_agent.solana_wallet import SolanaWalletManager
from oobe_agent.risk_guardrails import RiskGuardrailEngine, ReserveFloorViolation

class TestSolanaWalletManager(unittest.TestCase):
    """
    Tests for Solana wallet transactions, simulations, and Jupiter swaps.
    """

    def setUp(self):
        self.guardrails = RiskGuardrailEngine(min_sol_reserve=1.0, max_single_trade_sol=10.0)
        self.wallet = SolanaWalletManager(
            public_key="9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
            guardrails=self.guardrails
        )
        # Seed test balances
        self.wallet._balances = {"SOL": 15.0, "USDC": 1000.0, "BONK": 1000000.0}

    def test_balance_retrieval(self):
        self.assertEqual(self.wallet.get_balance("SOL"), 15.0)
        self.assertEqual(self.wallet.get_balance("USDC"), 1000.0)
        self.assertEqual(self.wallet.get_balance("NON_EXISTENT"), 0.0)

    def test_simulation_passes_and_calculates_fees(self):
        sim = self.wallet.simulate_transaction(
            transaction_type="TRANSFER",
            amount_sol=2.0,
            destination="Destination111111111111111111111111111111111"
        )
        self.assertEqual(sim["simulation_status"], "SUCCESS")
        self.assertGreater(sim["compute_units_consumed"], 0)
        self.assertAlmostEqual(sim["post_simulation_balance_sol"], 15.0 - 2.0 - 0.000005, places=5)

    def test_execute_sol_transfer_updates_balances_and_records_volume(self):
        initial_sol = self.wallet.get_balance("SOL")
        transfer_amt = 3.0
        res = self.wallet.execute_sol_transfer(
            destination_address="ValidDestinationAddress11111111111111111111",
            amount_sol=transfer_amt
        )
        self.assertEqual(res["status"], "CONFIRMED")
        self.assertAlmostEqual(self.wallet.get_balance("SOL"), initial_sol - transfer_amt - 0.000005, places=5)
        self.assertEqual(self.guardrails.get_rolling_24h_volume(), transfer_amt)

    def test_execute_jupiter_swap_sol_to_usdc(self):
        initial_sol = self.wallet.get_balance("SOL")
        initial_usdc = self.wallet.get_balance("USDC")
        swap_sol = 2.0

        res = self.wallet.execute_jupiter_swap(
            input_token="SOL",
            output_token="USDC",
            input_amount=swap_sol,
            slippage_bps=20
        )
        self.assertEqual(res["status"], "CONFIRMED")
        self.assertLess(self.wallet.get_balance("SOL"), initial_sol - swap_sol)
        self.assertGreater(self.wallet.get_balance("USDC"), initial_usdc)
        self.assertIn("JUP4_", res["signature"])

    def test_reject_swap_with_insufficient_balance(self):
        with self.assertRaises(ValueError):
            self.wallet.execute_jupiter_swap(
                input_token="SOL",
                output_token="USDC",
                input_amount=999.0  # Far more than available
            )

    def test_live_rpc_offline_graceful_handling(self):
        # Point to invalid/offline RPC to verify graceful None return
        offline_wallet = SolanaWalletManager(
            public_key="9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
            rpc_endpoint="http://127.0.0.1:9999/unreachable"
        )
        bal = offline_wallet.fetch_live_sol_balance(timeout_sec=0.1)
        self.assertIsNone(bal)

        blockhash = offline_wallet.fetch_live_blockhash(timeout_sec=0.1)
        self.assertIsNone(blockhash)

        summary = offline_wallet.get_portfolio_summary(query_live_rpc=True)
        self.assertIsNone(summary.get("live_onchain_sol"))

if __name__ == "__main__":
    unittest.main()
