from typing import Dict, Any, List, Optional
from ..solana_wallet import SolanaWalletManager
from ..risk_guardrails import RiskViolation

class TreasuryRebalancer:
    """
    Autonomous Portfolio Rebalancing Strategy.
    Maintains target weights between SOL and stablecoins (USDC) with drift thresholds.
    """

    def __init__(
        self,
        wallet: SolanaWalletManager,
        target_sol_weight: float = 0.60,
        drift_threshold: float = 0.05,
        sol_price_usd: float = 180.0
    ):
        self.wallet = wallet
        self.target_sol_weight = target_sol_weight
        self.drift_threshold = drift_threshold
        self.sol_price_usd = sol_price_usd

    def calculate_current_allocation(self) -> Dict[str, Any]:
        """Calculates current dollar values and portfolio weights."""
        sol_bal = self.wallet.get_balance("SOL")
        usdc_bal = self.wallet.get_balance("USDC")

        sol_val_usd = sol_bal * self.sol_price_usd
        usdc_val_usd = usdc_bal * 1.0
        total_val_usd = sol_val_usd + usdc_val_usd

        if total_val_usd <= 0:
            return {"total_usd": 0, "sol_weight": 0, "usdc_weight": 0, "drift": 0}

        sol_weight = sol_val_usd / total_val_usd
        drift = sol_weight - self.target_sol_weight

        return {
            "total_usd": round(total_val_usd, 2),
            "sol_value_usd": round(sol_val_usd, 2),
            "usdc_value_usd": round(usdc_val_usd, 2),
            "current_sol_weight": round(sol_weight, 4),
            "target_sol_weight": self.target_sol_weight,
            "drift": round(drift, 4),
            "requires_rebalance": abs(drift) >= self.drift_threshold
        }

    def evaluate_and_rebalance(self) -> Dict[str, Any]:
        """
        Evaluates portfolio drift and executes rebalancing swap if threshold is breached.
        """
        alloc = self.calculate_current_allocation()
        if not alloc["requires_rebalance"]:
            return {
                "action": "HOLD",
                "reason": f"Drift {alloc['drift']*100:.2f}% is within acceptable threshold (+/- {self.drift_threshold*100:.1f}%)",
                "allocation": alloc
            }

        drift = alloc["drift"]
        total_usd = alloc["total_usd"]

        # If SOL weight is too high -> sell SOL for USDC (clamped by guardrail single trade limit)
        if drift > 0:
            usd_to_sell = drift * total_usd
            sol_to_sell = usd_to_sell / self.sol_price_usd
            # Intelligent tranche sizing: never exceed single trade limit
            max_allowed = self.wallet.guardrails.max_single_trade_sol
            actual_sol_to_sell = min(sol_to_sell, max_allowed)
            try:
                swap_res = self.wallet.execute_jupiter_swap(
                    input_token="SOL",
                    output_token="USDC",
                    input_amount=round(actual_sol_to_sell, 4),
                    slippage_bps=25
                )
                return {
                    "action": "REBALANCE_SELL_SOL",
                    "sol_sold": actual_sol_to_sell,
                    "target_sol_to_sell": sol_to_sell,
                    "tranched": actual_sol_to_sell < sol_to_sell,
                    "usd_rebalanced": actual_sol_to_sell * self.sol_price_usd,
                    "swap_result": swap_res,
                    "new_allocation": self.calculate_current_allocation()
                }
            except RiskViolation as e:
                return {
                    "action": "BLOCKED_BY_GUARDRAIL",
                    "error": str(e),
                    "allocation": alloc
                }

        # If SOL weight is too low -> sell USDC to buy SOL
        else:
            usd_to_spend = abs(drift) * total_usd
            # Max USDC equivalent to max_single_trade_sol
            max_usd_allowed = self.wallet.guardrails.max_single_trade_sol * self.sol_price_usd
            actual_usd_to_spend = min(usd_to_spend, max_usd_allowed)
            try:
                swap_res = self.wallet.execute_jupiter_swap(
                    input_token="USDC",
                    output_token="SOL",
                    input_amount=round(actual_usd_to_spend, 2),
                    slippage_bps=25
                )
                return {
                    "action": "REBALANCE_BUY_SOL",
                    "usdc_spent": actual_usd_to_spend,
                    "target_usdc_to_spend": usd_to_spend,
                    "tranched": actual_usd_to_spend < usd_to_spend,
                    "swap_result": swap_res,
                    "new_allocation": self.calculate_current_allocation()
                }
            except RiskViolation as e:
                return {
                    "action": "BLOCKED_BY_GUARDRAIL",
                    "error": str(e),
                    "allocation": alloc
                }
