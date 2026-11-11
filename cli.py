import argparse
import json
import os
import sys
from oobe_agent.core import OOBECapitalAgent

def main():
    default_storage = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_state_memory.json")
    parser = argparse.ArgumentParser(
        description="OOBE Autonomous Capital & Treasury Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py --cycle        # Execute one autonomous rebalance cycle
  python cli.py --portfolio    # Display current portfolio balances & risk status
  python cli.py --audit        # Export cryptographic Merkle audit log
  python cli.py --list-tools   # List SAP Model Context Protocol (MCP) tools
  python cli.py --killswitch "Anomaly detected" # Halt agent operations
        """
    )
    parser.add_argument("--cycle", action="store_true", help="Run autonomous decision cycle")
    parser.add_argument("--portfolio", action="store_true", help="Display treasury portfolio")
    parser.add_argument("--live", action="store_true", help="Query live Solana RPC during portfolio check")
    parser.add_argument("--audit", action="store_true", help="Generate verifiable Merkle audit proof")
    parser.add_argument("--list-tools", action="store_true", help="List registered SAP MCP tools")
    parser.add_argument("--killswitch", type=str, metavar="REASON", help="Trigger emergency stop")
    parser.add_argument("--storage", type=str, default=default_storage, help="Path to memory persistence file")

    args = parser.parse_args()
    agent = OOBECapitalAgent(storage_path=args.storage)

    print("\n" + "="*65)
    print(" 🦅 OOBE PROTOCOL: AUTONOMOUS CAPITAL & TREASURY AGENT")
    print(" Solana Mainnet & SAP MCP Execution Runtime")
    print("="*65 + "\n")

    if args.portfolio:
        summary = agent.wallet.get_portfolio_summary(query_live_rpc=args.live)
        print(f"Agent Vault: {summary['public_key']}")
        print(f"RPC Endpoint: {summary['rpc_endpoint']}")
        print("\nToken Balances:")
        for token, bal in summary['balances'].items():
            print(f"  • {token:<6}: {bal:>12,.4f}")
        if args.live:
            live_bal = summary.get('live_onchain_sol')
            if live_bal is not None:
                print(f"\n🌐 Live On-Chain Balance: {live_bal:.4f} SOL")
            else:
                print("\n🌐 Live On-Chain Balance: (RPC Unreachable / Offline)")
        print(f"\n24h Rolling Volume: {summary['rolling_24h_volume']:.4f} SOL")
        print(f"Circuit Breaker Active: {summary['circuit_breaker_active']}")

    elif args.cycle:
        print("🔄 Executing Autonomous Strategy Cycle...")
        cycle = agent.run_autonomous_cycle()
        print(f"Status: {cycle['cycle_status']} in {cycle['execution_duration_sec']}s")
        print(f"Merkle Root: {cycle['merkle_root']}")
        print(f"Action Taken: {cycle['strategy_outcome']['action']}")
        print(f"New Balances: {cycle['current_portfolio']['balances']}")

    elif args.audit:
        print("🔐 Cryptographic Merkle State Audit Report:")
        report = agent.export_audit_report()
        print(json.dumps(report, indent=2))

    elif args.list_tools:
        print("🛠️ Registered SAP Model Context Protocol (MCP) Tools:")
        tools = agent.mcp.list_tools()
        for t in tools:
            print(f"\n  [{t['name']}]")
            print(f"    Description: {t['description']}")
            print(f"    Schema: {json.dumps(t['inputSchema'])}")

    elif args.killswitch:
        print(f"🚨 Triggering Emergency Killswitch: {args.killswitch}")
        res = agent.mcp.invoke_tool("trigger_emergency_killswitch", {"reason": args.killswitch})
        print(f"Result: {res}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
