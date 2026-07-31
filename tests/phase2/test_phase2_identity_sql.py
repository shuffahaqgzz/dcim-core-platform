from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.phase2.identity_sql import (
    IdentityRejected,
    PreparedIdentity,
    prepare_identity,
    render_identity_dml,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "fixtures/synthetic/events/p1-redfish-health.json"
CLOCK = "2026-07-29T00:00:00Z"


class IdentitySqlPreparationTests(unittest.TestCase):
    def test_identity_preparation_is_total_and_quoting_is_safe(self) -> None:
        candidate = json.loads(SOURCE.read_text(encoding="utf-8"))
        candidate["enrichment"]["asset_identity"] = "Véndor O'Brien:SER:EXTRA"
        candidate["enrichment"]["ci_identity"] = "Système:device:extra"
        candidate["source"]["instance"] = "host'o"
        prepared = prepare_identity(candidate, CLOCK)
        self.assertIsInstance(prepared, PreparedIdentity)
        if isinstance(prepared, PreparedIdentity):
            sql = render_identity_dml(prepared)
            self.assertIn("O''Brien", sql)
            self.assertIn("host''o", sql)
            self.assertIn("SER:EXTRA", sql)
            self.assertIn("device:extra", sql)

        rejected_values = (
            ("enrichment", "asset_identity", ":serial"),
            ("enrichment", "asset_identity", "vendor:"),
            ("enrichment", "ci_identity", ":device"),
            ("enrichment", "ci_identity", "system:"),
            ("enrichment", "asset_identity", "vendor:serial\u0000"),
            ("enrichment", "ci_identity", "system:device\u0000"),
            ("source", "instance", "host\u0000"),
            ("source", "instance", "host\ud800"),
        )
        for section, field, value in rejected_values:
            with self.subTest(section=section, field=field, value_length=len(value)):
                rejected = json.loads(SOURCE.read_text(encoding="utf-8"))
                rejected[section][field] = value
                self.assertIsInstance(
                    prepare_identity(rejected, CLOCK),
                    IdentityRejected,
                )
        missing_identity = json.loads(SOURCE.read_text(encoding="utf-8"))
        missing_identity["enrichment"].pop("asset_identity")
        missing_identity["enrichment"].pop("ci_identity")
        missing_identity["source"]["instance"] = "host\u0000"
        self.assertIsInstance(
            prepare_identity(missing_identity, CLOCK),
            IdentityRejected,
        )


if __name__ == "__main__":
    unittest.main()
