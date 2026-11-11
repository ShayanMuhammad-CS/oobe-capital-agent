import time
import json
from typing import Dict, Any, Optional, List
from .solana_wallet import SolanaWalletManager
from .risk_guardrails import RiskGuardrailEngine
from .memory import AgentMemoryEngine
from .mcp_gateway import SAPMCPGateway
from .strategies.treasury_rebalancer import TreasuryRebalancer

class OOBECapitalAgent:
    """
    Main Autonomous Capital & Treasury Agent for OOBE Protocol on Solana.
    Orchestrates memory, MCP tools, risk guardrails, and automated strategy cycles.
    """

    def __init__(
        self,
        public_key: str = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        rpc_endpoint: str = "https://api.mainnet-beta.solana.com",
        min_sol_reserve: float = 0.5,
        max_single_trade_sol: float = 10.0,
        max_daily_volume_sol: float = 50.0,
        storage_path: Optional[str] = "agent_state_memory.json"
    ):
        self.public_key = public_key
        self.guardrails = RiskGuardrailEngine(
            min_sol_reserve=min_sol_reserve,
            max_single_trade_sol=max_single_trade_sol,
            max_daily_volume_sol=max_daily_volume_sol
        )
        self.wallet = SolanaWalletManager(
            public_key=public_key,
            rpc_endpoint=rpc_endpoint,
            guardrails=self.guardrails
        )
        self.memory = AgentMemoryEngine(storage_path=storage_path)
        self.mcp = SAPMCPGateway(wallet=self.wallet, memory=self.memory)
        self.rebalancer = TreasuryRebalancer(wallet=self.wallet)

    def run_autonomous_cycle(self) -> Dict[str, Any]:
        """
        Executes one full autonomous decision cycle:
        1. Evaluate portfolio balance and drift.
        2. Execute rebalancing if threshold breached.
        3. Record cryptographic execution receipt with Merkle state update.
        4. Return cycle telemetry.
        """
        start_time = time.time()
        
        # 1. Inspect state
        initial_summary = self.wallet.get_portfolio_summary()
        
        # 2. Evaluate strategy
        strategy_result = self.rebalancer.evaluate_and_rebalance()

        # 3. Log to verifiable memory
        receipt = self.memory.record_action(
            action="AUTONOMOUS_CYCLE",
            details={
                "strategy": "TreasuryRebalancer",
                "result": strategy_result,
                "portfolio_before": initial_summary["balances"]
            },
            status="CONFIRMED" if "error" not in strategy_result else "FAILED"
        )

        cycle_duration = time.time() - start_time

        return {
            "cycle_status": "COMPLETED",
            "execution_duration_sec": round(cycle_duration, 4),
            "merkle_root": self.memory.get_merkle_root(),
            "receipt_hash": receipt.receipt_hash,
            "strategy_outcome": strategy_result,
            "current_portfolio": self.wallet.get_portfolio_summary()
        }

    def export_audit_report(self) -> Dict[str, Any]:
        """Exports cryptographic audit log for bounty verification."""
        return {
            "agent_pubkey": self.public_key,
            "merkle_root": self.memory.get_merkle_root(),
            "total_receipts": len(self.memory.receipts),
            "risk_status": {
                "circuit_breaker_active": self.guardrails.is_circuit_breaker_active,
                "rolling_24h_volume": self.guardrails.get_rolling_24h_volume()
            },
            "recent_actions": self.memory.get_history(limit=20)
        }
