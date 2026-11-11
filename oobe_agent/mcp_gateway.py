import json
from typing import Dict, Any, List, Callable, Optional
from .solana_wallet import SolanaWalletManager
from .memory import AgentMemoryEngine

class MCPToolDefinition:
    """Represents an SAP MCP tool definition conforming to Model Context Protocol."""
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.handler = handler

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


class SAPMCPGateway:
    """
    Solana Agent Protocol (SAP) & Model Context Protocol (MCP) Gateway.
    Allows LLMs and autonomous coordinators to discover and safely execute capital operations.
    """

    def __init__(self, wallet: SolanaWalletManager, memory: AgentMemoryEngine):
        self.wallet = wallet
        self.memory = memory
        self.tools: Dict[str, MCPToolDefinition] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        # Tool 1: Balance inquiry
        self.register_tool(
            name="get_treasury_balance",
            description="Returns current token balances, 24h rolling volume, and circuit breaker status.",
            input_schema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "Token symbol (SOL, USDC, BONK) or 'ALL'"}
                }
            },
            handler=self._handle_get_balance
        )

        # Tool 2: Simulate Transfer
        self.register_tool(
            name="simulate_capital_transfer",
            description="Simulates a SOL capital transfer against risk guardrails without broadcasting.",
            input_schema={
                "type": "object",
                "properties": {
                    "amount_sol": {"type": "number", "description": "Amount of SOL to simulate"},
                    "destination": {"type": "string", "description": "Destination Solana public key"}
                },
                "required": ["amount_sol", "destination"]
            },
            handler=self._handle_simulate_transfer
        )

        # Tool 3: Execute Transfer
        self.register_tool(
            name="execute_capital_transfer",
            description="Executes a verified SOL transfer protected by hard risk limits.",
            input_schema={
                "type": "object",
                "properties": {
                    "amount_sol": {"type": "number", "description": "Amount of SOL to transfer"},
                    "destination": {"type": "string", "description": "Destination Solana public key"},
                    "memo": {"type": "string", "description": "Audit memo string"}
                },
                "required": ["amount_sol", "destination"]
            },
            handler=self._handle_execute_transfer
        )

        # Tool 4: Jupiter Swap
        self.register_tool(
            name="execute_jupiter_swap",
            description="Executes an automated token swap via Jupiter aggregator with slippage bounds.",
            input_schema={
                "type": "object",
                "properties": {
                    "input_token": {"type": "string", "description": "Token to sell (e.g., SOL)"},
                    "output_token": {"type": "string", "description": "Token to buy (e.g., USDC)"},
                    "input_amount": {"type": "number", "description": "Amount of input token to swap"},
                    "slippage_bps": {"type": "integer", "description": "Max slippage in basis points (50 = 0.5%)"}
                },
                "required": ["input_token", "output_token", "input_amount"]
            },
            handler=self._handle_jupiter_swap
        )

        # Tool 5: Verifiable Audit Proof
        self.register_tool(
            name="get_verifiable_audit_proof",
            description="Returns rolling Merkle root hash and cryptographic execution receipt history.",
            input_schema={"type": "object", "properties": {}},
            handler=self._handle_audit_proof
        )

        # Tool 6: Emergency Stop
        self.register_tool(
            name="trigger_emergency_killswitch",
            description="Instantly halts all automated transactions and trading via hard circuit breaker.",
            input_schema={
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for triggering killswitch"}
                },
                "required": ["reason"]
            },
            handler=self._handle_emergency_stop
        )

    def register_tool(self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable) -> None:
        self.tools[name] = MCPToolDefinition(name, description, input_schema, handler)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns MCP-compliant tool catalog."""
        return [tool.to_dict() for tool in self.tools.values()]

    def invoke_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool call and records verifiable execution receipt."""
        if tool_name not in self.tools:
            raise KeyError(f"Unknown tool: '{tool_name}'")

        handler = self.tools[tool_name].handler
        try:
            result = handler(arguments)
            receipt = self.memory.record_action(
                action=tool_name,
                details={"arguments": arguments, "result": result},
                status="CONFIRMED"
            )
            return {
                "success": True,
                "result": result,
                "receipt_hash": receipt.receipt_hash,
                "merkle_root": self.memory.get_merkle_root()
            }
        except Exception as e:
            self.memory.record_action(
                action=tool_name,
                details={"arguments": arguments, "error": str(e)},
                status="FAILED"
            )
            return {
                "success": False,
                "error": str(e),
                "merkle_root": self.memory.get_merkle_root()
            }

    # Handler implementations
    def _handle_get_balance(self, args: Dict[str, Any]) -> Dict[str, Any]:
        token = args.get("token", "ALL").upper()
        query_live = bool(args.get("query_live", False))
        if token == "ALL":
            return self.wallet.get_portfolio_summary(query_live_rpc=query_live)
        res = {"token": token, "balance": self.wallet.get_balance(token)}
        if token == "SOL" and query_live:
            res["live_onchain_sol"] = self.wallet.fetch_live_sol_balance()
        return res

    def _handle_simulate_transfer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.wallet.simulate_transaction(
            transaction_type="TRANSFER",
            amount_sol=float(args["amount_sol"]),
            destination=args["destination"]
        )

    def _handle_execute_transfer(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.wallet.execute_sol_transfer(
            destination_address=args["destination"],
            amount_sol=float(args["amount_sol"]),
            memo=args.get("memo", "SAP-MCP-Transfer")
        )

    def _handle_jupiter_swap(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self.wallet.execute_jupiter_swap(
            input_token=args["input_token"],
            output_token=args["output_token"],
            input_amount=float(args["input_amount"]),
            slippage_bps=int(args.get("slippage_bps", 20))
        )

    def _handle_audit_proof(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "merkle_root": self.memory.get_merkle_root(),
            "total_receipts": len(self.memory.receipts),
            "recent_history": self.memory.get_history(limit=10)
        }

    def _handle_emergency_stop(self, args: Dict[str, Any]) -> Dict[str, Any]:
        reason = args.get("reason", "Manual trigger via MCP")
        self.wallet.guardrails.trigger_emergency_stop(reason)
        return {"status": "EMERGENCY_STOP_ACTIVE", "reason": reason}
