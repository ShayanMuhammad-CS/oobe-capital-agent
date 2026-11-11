import unittest
import time
from oobe_agent.risk_guardrails import (
    RiskGuardrailEngine,
    CircuitBreakerTriggered,
    SingleTradeLimitExceeded,
    ReserveFloorViolation,
    DrainerAddressDetected,
    SlippageViolation,
    DailyVolumeLimitExceeded,
    RiskViolation
)

class TestRiskGuardrailEngineHarsh(unittest.TestCase):
    """
    Harsh invariant & adversarial tests for the Risk Guardrail Engine.
    """

    def setUp(self):
        self.guardrails = RiskGuardrailEngine(
            min_sol_reserve=1.0,
            max_single_trade_sol=5.0,
            max_daily_volume_sol=20.0,
            max_slippage_bps=50,
            blocked_addresses=["Drainer111111111111111111111111111111111111"]
        )

    def test_reject_zero_or_negative_trade(self):
        """Must reject 0 or negative trades immediately."""
        with self.assertRaises(RiskViolation):
            self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=0.0)

        with self.assertRaises(RiskViolation):
            self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=-1.5)

    def test_single_trade_limit_enforcement(self):
        """Must reject any trade exceeding max_single_trade_sol."""
        # 5.0 SOL is fine
        self.assertTrue(self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=5.0))
        
        # 5.0001 SOL must be harshly rejected
        with self.assertRaises(SingleTradeLimitExceeded):
            self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=5.0001)

    def test_reserve_floor_invariant(self):
        """Must never allow balance to drop below min_sol_reserve."""
        # Current balance 3.0, trade 2.0 -> leaves 1.0 (meets reserve floor) -> PASS
        self.assertTrue(self.guardrails.validate_transaction(current_balance_sol=3.0, trade_amount_sol=2.0))

        # Current balance 3.0, trade 2.01 -> leaves 0.99 (violates reserve floor) -> FAIL
        with self.assertRaises(ReserveFloorViolation):
            self.guardrails.validate_transaction(current_balance_sol=3.0, trade_amount_sol=2.01)

    def test_anti_drainer_blacklist(self):
        """Must immediately block transactions to known drainer addresses."""
        with self.assertRaises(DrainerAddressDetected):
            self.guardrails.validate_transaction(
                current_balance_sol=10.0,
                trade_amount_sol=1.0,
                destination_address="Drainer111111111111111111111111111111111111"
            )

    def test_anti_drainer_malformed_address(self):
        """Must reject malformed or suspicious address lengths."""
        with self.assertRaises(DrainerAddressDetected):
            self.guardrails.validate_transaction(
                current_balance_sol=10.0,
                trade_amount_sol=1.0,
                destination_address="TooShort"
            )

    def test_slippage_bound_enforcement(self):
        """Must reject transactions with slippage higher than max tolerance."""
        # 50 bps is max tolerated -> PASS
        self.assertTrue(self.guardrails.validate_transaction(
            current_balance_sol=10.0, trade_amount_sol=1.0, expected_slippage_bps=50
        ))

        # 51 bps -> FAIL
        with self.assertRaises(SlippageViolation):
            self.guardrails.validate_transaction(
                current_balance_sol=10.0, trade_amount_sol=1.0, expected_slippage_bps=51
            )

    def test_daily_volume_limit_rolling(self):
        """Must track cumulative trades and reject when 24h limit breached."""
        self.guardrails.record_executed_trade(amount_sol=10.0)
        self.guardrails.record_executed_trade(amount_sol=8.0)
        self.assertEqual(self.guardrails.get_rolling_24h_volume(), 18.0)

        # Trying to trade 3.0 SOL when 18.0 already spent (limit 20.0) must FAIL
        with self.assertRaises(DailyVolumeLimitExceeded):
            self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=3.0)

        # 2.0 SOL keeps it exactly at 20.0 -> PASS
        self.assertTrue(self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=2.0))

    def test_circuit_breaker_emergency_halt(self):
        """When circuit breaker is triggered, ALL operations must raise CircuitBreakerTriggered."""
        self.guardrails.trigger_emergency_stop(reason="Abnormal market volatility detected")
        self.assertTrue(self.guardrails.is_circuit_breaker_active)

        with self.assertRaises(CircuitBreakerTriggered):
            self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=0.1)

        # Resume operations clears the breaker
        self.guardrails.resume_operations()
        self.assertFalse(self.guardrails.is_circuit_breaker_active)
        self.assertTrue(self.guardrails.validate_transaction(current_balance_sol=10.0, trade_amount_sol=0.1))

if __name__ == "__main__":
    unittest.main()
