from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_synthetic_fixtures.py"
SPEC = importlib.util.spec_from_file_location("fixture_validation", SCRIPT)
assert SPEC and SPEC.loader
fixture_validation = importlib.util.module_from_spec(SPEC)
sys.path.insert(0, str(SCRIPT.parent))
SPEC.loader.exec_module(fixture_validation)


class SyntheticFixtureValidationTests(unittest.TestCase):
    def safe_row(self) -> dict[str, str]:
        return {
            "asset_id": "SYNTHETIC-ASSET-0001",
            "manufacturer": "ExampleVendor",
            "serial_number": "SYNTHETIC-SERIAL-0001",
            "hostname": "server-001.example.com",
            "ip_address": "198.51.100.41",
            "location": "GENERIC-LOCATION-01",
        }

    def test_public_safe_asset_row_passes(self) -> None:
        self.assertEqual([], fixture_validation.validate_asset_row(self.safe_row()))

    def test_live_looking_asset_provenance_is_rejected(self) -> None:
        row = self.safe_row()
        row.update(
            {
                "asset_id": "ASSET-0001",
                "manufacturer": "Vendor",
                "serial_number": "SERIAL-0001",
                "hostname": "device" + ".corp",
                "ip_address": "10." + "1.2.3",
                "location": "Site Rack 1",
            }
        )
        self.assertEqual(6, len(fixture_validation.validate_asset_row(row)))


if __name__ == "__main__":
    unittest.main()
