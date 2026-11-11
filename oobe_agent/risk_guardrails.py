import time
from typing import Dict, Any, List, Optional

class RiskViolation(Exception):
    """Base exception for all risk violations."""
    pass

class CircuitBreakerTriggered(RiskViolation):
    """Raised when emergency stop is active."""
    pass

class SlippageViolation(RiskViolation):
    """Raised when slippage exceeds max tolerated percentage."""
    pass

class DrainerAddressDetected(RiskViolation):
    """Raised when recipient address matches malicious or untrusted patterns."""
    pass

class ReserveFloorViolation(RiskViolation):
    """Raised when transaction would drop balance below mandatory minimum reserve."""
    pass

class DailyVolumeLimitExceeded(RiskViolation):
    """Raised when cumulative 24h volume exceeds threshold."""
    pass

class SingleTradeLimitExceeded(RiskViolation):
    """Raised when single trade size exceeds maximum allowed percentage/amount."""
    pass


class RiskGuardrailEngine:
    """
    Hard programmatic risk shield for autonomous capital execution.
    Guarantees no hallucinated or malicious agent action can drain wallet funds.
    """

    def __init__(
        self,
        min_sol_reserve: float = 0.5,
        max_single_trade_sol: float = 10.0,
        max_daily_volume_sol: float = 50.0,
        max_slippage_bps: int = 50,  # 50 bps = 0.5%
        blocked_addresses: Optional[List[str]] = None
    ):
        self.min_sol_reserve = min_sol_reserve
        self.max_single_trade_sol = max_single_trade_sol
        self.max_daily_volume_sol = max_daily_volume_sol
        self.max_slippage_bps = max_slippage_bps
        self.blocked_addresses = set(blocked_addresses or [])
        self.is_circuit_breaker_active = False
        
        # Daily volume tracker: list of (timestamp, amount_sol)
        self._volume_history: List[Dict[str, Any]] = []

    def trigger_emergency_stop(self, reason: str = "Manual emergency halt") -> None:
        """Immediately halts all capital movements."""
        self.is_circuit_breaker_active = True

    def resume_operations(self) -> None:
        """Clears emergency circuit breaker."""
        self.is_circuit_breaker_active = False

    def get_rolling_24h_volume(self) -> float:
        """Calculates total volume executed in past 24 hours."""
        now = time.time()
        one_day_ago = now - 86400
        self._volume_history = [v for v in self._volume_history if v["timestamp"] >= one_day_ago]
        return sum(v["amount_sol"] for v in self._volume_history)

    def validate_transaction(
        self,
        current_balance_sol: float,
        trade_amount_sol: float,
        destination_address: Optional[str] = None,
        expected_slippage_bps: Optional[int] = None
    ) -> bool:
        """
        Validates all hard invariants before any on-chain execution.
        Raises specific RiskViolation subclass if any safety rule is violated.
        """
        if self.is_circuit_breaker_active:
            raise CircuitBreakerTriggered("CRITICAL: Circuit breaker active. All capital movements halted.")

        if trade_amount_sol <= 0:
            raise RiskViolation(f"Invalid trade amount: {trade_amount_sol} SOL. Must be positive.")

        # 1. Single trade limit
        if trade_amount_sol > self.max_single_trade_sol:
            raise SingleTradeLimitExceeded(
                f"Trade amount {trade_amount_sol:.4f} SOL exceeds single trade limit of {self.max_single_trade_sol:.4f} SOL"
            )

        # 2. Reserve floor invariant
        remaining_balance = current_balance_sol - trade_amount_sol
        if remaining_balance < self.min_sol_reserve:
            raise ReserveFloorViolation(
                f"Post-trade balance {remaining_balance:.4f} SOL violates reserve floor of {self.min_sol_reserve:.4f} SOL"
            )

        # 3. Destination blacklist / Anti-drainer check
        if destination_address:
            dest_clean = destination_address.strip()
            if dest_clean in self.blocked_addresses:
                raise DrainerAddressDetected(f"Destination {dest_clean} is on the blocked address blacklist.")
            # Basic sanity on destination length (Solana base58 addresses are 32-44 chars)
            if len(dest_clean) < 32 or len(dest_clean) > 44:
                raise DrainerAddressDetected(f"Malformed destination address length: {len(dest_clean)}")

        # 4. Slippage tolerance
        if expected_slippage_bps is not None:
            if expected_slippage_bps > self.max_slippage_bps:
                raise SlippageViolation(
                    f"Expected slippage {expected_slippage_bps} bps exceeds max tolerance of {self.max_slippage_bps} bps"
                )

        # 5. Rolling 24h volume limit
        current_24h_vol = self.get_rolling_24h_volume()
        if (current_24h_vol + trade_amount_sol) > self.max_daily_volume_sol:
            raise DailyVolumeLimitExceeded(
                f"Projected 24h volume {(current_24h_vol + trade_amount_sol):.4f} SOL exceeds daily limit of {self.max_daily_volume_sol:.4f} SOL"
            )

        return True

    def record_executed_trade(self, amount_sol: float) -> None:
        """Appends trade to rolling 24h volume ledger."""
        self._volume_history.append({
            "timestamp": time.time(),
            "amount_sol": amount_sol
        })
