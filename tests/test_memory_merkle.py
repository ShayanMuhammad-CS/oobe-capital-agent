import unittest
import os
import json
from oobe_agent.memory import AgentMemoryEngine, VerifiableExecutionReceipt

class TestAgentMemoryEngine(unittest.TestCase):
    """
    Tests for cryptographic Merkle tree integrity, receipt immutability, and state persistence.
    """

    def setUp(self):
        self.test_storage = "scratch_test_memory.json"
        self.memory = AgentMemoryEngine(storage_path=self.test_storage)

    def tearDown(self):
        if os.path.exists(self.test_storage):
            os.remove(self.test_storage)

    def test_empty_memory_merkle_root(self):
        root = self.memory.get_merkle_root()
        self.assertIsInstance(root, str)
        self.assertEqual(len(root), 64)

    def test_single_receipt_merkle_root_matches_receipt_hash(self):
        receipt = self.memory.record_action("TEST_ACTION", {"key": "val1"})
        self.assertEqual(self.memory.get_merkle_root(), receipt.receipt_hash)

    def test_merkle_tree_handles_odd_and_even_counts(self):
        # 2 receipts (even)
        r1 = self.memory.record_action("ACT_1", {"v": 1})
        r2 = self.memory.record_action("ACT_2", {"v": 2})
        root2 = self.memory.get_merkle_root()
        self.assertNotEqual(root2, r1.receipt_hash)
        self.assertNotEqual(root2, r2.receipt_hash)

        # 3 receipts (odd - tests duplicate right-child leaf handling)
        r3 = self.memory.record_action("ACT_3", {"v": 3})
        root3 = self.memory.get_merkle_root()
        self.assertNotEqual(root3, root2)
        self.assertEqual(len(root3), 64)

    def test_persistence_writes_valid_utf8_without_bom(self):
        self.memory.record_action("PERSIST_ACTION", {"token": "SOL", "amount": 5.0})
        self.memory.persist()

        self.assertTrue(os.path.exists(self.test_storage))
        with open(self.test_storage, "rb") as f:
            raw_bytes = f.read()
            # Verify NO BOM header (0xEF, 0xBB, 0xBF)
            self.assertFalse(raw_bytes.startswith(b'\xef\xbb\xbf'))
            # Verify starts with ASCII '{'
            self.assertTrue(raw_bytes.startswith(b'{'))

        with open(self.test_storage, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertEqual(data["total_receipts"], 1)
            self.assertEqual(data["merkle_root"], self.memory.get_merkle_root())

    def test_persistence_reloads_existing_receipts(self):
        r1 = self.memory.record_action("PERSIST_ACTION_1", {"v": 100})
        expected_root = self.memory.get_merkle_root()

        # Instantiate second memory engine pointing to same storage file
        reloaded_memory = AgentMemoryEngine(storage_path=self.test_storage)
        self.assertEqual(len(reloaded_memory.receipts), 1)
        self.assertEqual(reloaded_memory.receipts[0].action, "PERSIST_ACTION_1")
        self.assertEqual(reloaded_memory.get_merkle_root(), expected_root)

if __name__ == "__main__":
    unittest.main()
