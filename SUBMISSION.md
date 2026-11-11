# 🦅 Superteam Earn Bounty Submission: OOBE Protocol Autonomous Capital Agent

- **Bounty:** OOBE Protocol: Build an Autonomous Capital Agent on Solana ($500 USDC)
- **Author:** Shayan Muhammad
- **Institution:** University of Engineering and Technology (UET) Mardan
- **Target Runtime:** Solana Mainnet & Devnet / SAP Model Context Protocol (MCP)

---

## 🎯 Executive Summary & Vision

Most autonomous agents deployed in Web3 suffer from a fatal design flaw: **prompt-dependent execution**. If an LLM is persuaded, hallucinates, or miscalculates, it can issue an unbounded on-chain transaction that completely drains the treasury vault or routes through malicious liquidity pools.

The **OOBE Autonomous Capital Agent** resolves this vulnerability through **Code-Enforced Invariant Interception**. All actions initiated by an autonomous planner, scheduler, or MCP client must first pass through a deterministic, zero-trust risk guardrail engine before touching the transaction builder. Furthermore, every state change generates an immutable execution receipt anchored to a **rolling binary Merkle tree root hash**, enabling external supervisors to mathematically verify treasury actions without parsing gigabytes of raw logs.

---

## 🏛️ Architecture & Component Design

The agent is organized into modular layers conforming to the Solana Agent Protocol (SAP) and Model Context Protocol (MCP):

```
oobe_capital_agent/
├── oobe_agent/
│   ├── risk_guardrails.py        # Hard programmatic safety shields & circuit breaker
│   ├── solana_wallet.py          # Zero-dependency RPC balance queries & Jupiter swap routing
│   ├── memory.py                 # Verifiable execution receipts & rolling Merkle trees
│   ├── mcp_gateway.py            # SAP Model Context Protocol (MCP) JSON-RPC 2.0 tools
│   ├── core.py                   # Orchestrator unifying memory, tools, and guardrails
│   └── strategies/
│       └── treasury_rebalancer.py # Autonomous drift evaluation & order tranching
├── tests/
│   ├── test_risk_guardrails.py   # Invariant tests: reserve floors, drainer filters, limits
│   ├── test_solana_wallet.py     # Wallet simulations, swaps, and offline RPC handling
│   ├── test_memory_merkle.py     # Merkle root parity, odd/even leaves, UTF-8 persistence
│   ├── test_mcp_gateway.py       # MCP tool discovery, execution receipts, and killswitch
│   └── test_autonomous_loop.py   # Full autonomous strategy cycles and audit exports
├── cli.py                        # Interactive CLI for operators and automated daemons
├── pyproject.toml / setup.py     # Pip-installable package definition
├── README.md                     # Architecture diagrams and system manual
└── SUBMISSION.md                 # Bounty evaluation guide
```

---

## 🛡️ Deterministic Safety Invariants (Zero-Trust)

| Invariant | Code Enforcement | Test Coverage |
| :--- | :--- | :--- |
| **Reserve Floor Invariant** | Vault SOL balance cannot drop below `min_sol_reserve` (default: 0.5 SOL). Prevents gas depletion. | `test_reserve_floor_invariant` |
| **Single Trade Limit** | No single transaction can exceed `max_single_trade_sol` (default: 10.0 SOL). Large drift rebalances are automatically tranched. | `test_single_trade_limit_enforcement`, `test_rebalance_trigger_on_heavy_drift` |
| **Rolling 24h Velocity Cap** | Sliding window rejects trades if 24-hour cumulative volume exceeds threshold (default: 50.0 SOL). | `test_daily_volume_limit_rolling` |
| **Anti-Drainer Sanitizer** | Base58 addresses are verified for format, length, and checked against blacklists before signing. | `test_anti_drainer_blacklist`, `test_anti_drainer_malformed_address` |
| **Slippage Bounds** | Swaps with slippage exceeding tolerance (default: 200 bps) are aborted before broadcast. | `test_slippage_bound_enforcement` |
| **Circuit Breaker** | Global killswitch immediately freezes all signing operations and tool executions across the agent. | `test_circuit_breaker_emergency_halt`, `test_invoke_emergency_killswitch` |

---

## 📜 Verifiable Execution Receipts & Merkle State Proofs

Every transaction or autonomous cycle produces an immutable `VerifiableExecutionReceipt`:

```
ReceiptHash = SHA256(Action : Status : Timestamp : CanonicalJSON(Details))
```

The memory engine builds a rolling binary Merkle tree across all receipts. When an odd number of receipts exists, the rightmost leaf is duplicated per RFC 6962 / Bitcoin Merkle tree standards. The resulting 32-byte Merkle root (`merkle_root`) acts as a succinct cryptographic state proof of the agent's historical integrity.

---

## ⚡ Quick 1-Command Verification for Judges

### 1. Run the Complete Test Suite (26 Tests)
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
*Expected Output:*
```text
Ran 26 tests in ~2.2s
OK
```

### 2. Inspect Portfolio with Live On-Chain Solana RPC Check
```bash
python cli.py --portfolio --live
```
*Queries the live Solana Mainnet RPC for current on-chain balance while reporting local treasury balances.*

### 3. Run Autonomous Strategy Cycle (Rebalancer)
```bash
python cli.py --cycle
```
*Evaluates portfolio drift, calculates optimal swap tranching, executes swap, and logs cryptographic receipt.*

### 4. Export Verifiable Merkle Audit Log
```bash
python cli.py --audit
```
*Displays full Merkle root and tamper-evident history.*

### 5. Inspect Model Context Protocol (MCP) Tool Schemas
```bash
python cli.py --list-tools
```

---

## 🌟 Superteam Earn Evaluation Highlights

1. **Native SAP & MCP Compliance:** Fully compatible with LLM tool calling (Anthropic, OpenAI, Antigravity, Ollama) via standard JSON schemas.
2. **Zero Bulky Dependencies:** Core agent runs entirely on Python 3.10+ standard libraries (`urllib`, `hashlib`, `json`, `argparse`), ensuring zero installation friction or Rust build toolchain failures.
3. **Resilient Hybrid Architecture:** Seamlessly executes in offline/simulated test environments and connects to live Solana mainnet endpoints.
4. **Code vs. Prompt Security:** Eliminates prompt injection vulnerabilities by guaranteeing invariants in Python code, not prompt text.
