import json
import hashlib
import os
import time
from typing import List, Dict, Any, Optional

class VerifiableExecutionReceipt:
    """
    Cryptographic execution receipt capturing action, state diff, and timestamp.
    """
    def __init__(self, action: str, details: Dict[str, Any], status: str = "CONFIRMED", timestamp: Optional[float] = None, receipt_hash: Optional[str] = None):
        self.action = action
        self.details = details
        self.status = status
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.receipt_hash = receipt_hash if receipt_hash is not None else self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.action}:{self.status}:{self.timestamp}:{json.dumps(self.details, sort_keys=True)}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "status": self.status,
            "timestamp": self.timestamp,
            "receipt_hash": self.receipt_hash,
            "details": self.details
        }


class AgentMemoryEngine:
    """
    OOBE-compliant persistent memory & verifiable state engine.
    Computes rolling Merkle root hashes over execution receipts and preserves state.
    """

    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.receipts: List[VerifiableExecutionReceipt] = []
        if self.storage_path and os.path.exists(self.storage_path):
            self._load()

    def _load(self) -> None:
        """Loads state from storage_path if it exists."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for r in data.get("receipts", []):
                    receipt = VerifiableExecutionReceipt(
                        action=r["action"],
                        details=r.get("details", {}),
                        status=r.get("status", "CONFIRMED"),
                        timestamp=r.get("timestamp"),
                        receipt_hash=r.get("receipt_hash")
                    )
                    self.receipts.append(receipt)
        except Exception:
            pass

    def record_action(self, action: str, details: Dict[str, Any], status: str = "CONFIRMED") -> VerifiableExecutionReceipt:
        """Records an execution receipt and updates state."""
        receipt = VerifiableExecutionReceipt(action=action, details=details, status=status)
        self.receipts.append(receipt)
        if self.storage_path:
            self.persist()
        return receipt

    def get_merkle_root(self) -> str:
        """
        Computes binary Merkle tree root hash across all recorded receipts.
        Guarantees cryptographic auditability of agent trade history.
        """
        if not self.receipts:
            return hashlib.sha256(b"EMPTY_OOBE_MEMORY").hexdigest()

        hashes = [r.receipt_hash for r in self.receipts]

        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])  # Duplicate last element if odd
            
            next_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i+1]
                parent_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
                next_level.append(parent_hash)
            hashes = next_level

        return hashes[0]

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns recent execution receipts."""
        return [r.to_dict() for r in self.receipts[-limit:]]

    def persist(self) -> None:
        """Writes memory state to disk using UTF-8 without BOM."""
        if not self.storage_path:
            return
        data = {
            "version": "1.0.0",
            "merkle_root": self.get_merkle_root(),
            "total_receipts": len(self.receipts),
            "receipts": [r.to_dict() for r in self.receipts]
        }
        # UTF-8 without BOM strictly enforced
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
