from __future__ import annotations

import unittest

from scripts.phase2.errors import DispositionImbalanceError
from scripts.phase2.ledger import DispositionLedger


class DispositionLedgerTests(unittest.TestCase):
    def test_assert_balanced_when_all_received_items_are_disposed(self) -> None:
        ledger = DispositionLedger()
        for _ in range(6):
            ledger.record("received")
        for _ in range(5):
            ledger.record("accepted")
        ledger.record("quarantined")

        ledger.assert_balanced()
        self.assertEqual(
            {
                "received": 6,
                "accepted": 5,
                "quarantined": 1,
                "duplicate": 0,
            },
            ledger.to_json(),
        )

    def test_assert_balanced_when_received_exceeds_dispositions_raises(self) -> None:
        ledger = DispositionLedger()
        for _ in range(3):
            ledger.record("received")
        ledger.record("accepted")
        ledger.record("accepted")

        with self.assertRaises(DispositionImbalanceError):
            ledger.assert_balanced()
