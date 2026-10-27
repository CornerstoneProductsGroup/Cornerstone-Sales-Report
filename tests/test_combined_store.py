import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from modules import shared_core as core


class CombinedStoreTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store_path = Path(directory.name) / "sales_store.csv"
        self.state_path = Path(directory.name) / "state_totals_store.csv"
        for name, value in (
            ("DEFAULT_STORE_CSV", self.store_path),
            ("DEFAULT_STATE_TOTALS_CSV", self.state_path),
        ):
            mock = patch.object(core, name, value)
            mock.start()
            self.addCleanup(mock.stop)
        mock = patch.object(core, "load_retailer_renames", return_value={})
        mock.start()
        self.addCleanup(mock.stop)
        self.sales = pd.DataFrame([{
            "Retailer": "Depot", "SKU": "NB4", "Units": 5, "UnitPrice": 22.0,
            "StartDate": "2026-10-19", "EndDate": "2026-10-23", "SourceFile": "week.xlsx",
        }])
        self.states = self.sales.drop(columns="UnitPrice").assign(State="TX", Units=3)

    def test_sales_and_state_saves_preserve_each_other(self):
        core.save_store(self.sales)
        core.save_state_totals(self.states)
        core.save_store(self.sales.assign(Units=9))
        self.assertEqual(core.load_store()["Units"].tolist(), [9])
        self.assertEqual(core.load_state_totals()["Units"].tolist(), [3])
        core.save_state_totals(self.states.assign(Units=7))
        self.assertEqual(core.load_store()["Units"].tolist(), [9])
        self.assertEqual(core.load_state_totals()["Units"].tolist(), [7])
        self.assertFalse(self.state_path.exists())
        self.assertEqual(set(pd.read_csv(self.store_path)["RecordType"]), {"Sales", "State Totals"})

    def test_download_restore_and_repository_restart_round_trip(self):
        core.save_store(self.sales)
        core.save_state_totals(self.states)
        backup = core.store_backup_bytes()
        parsed = pd.read_csv(io.BytesIO(backup))
        self.assertEqual(core.restore_store_backup(parsed), (1, 1))
        # A fresh deployment has only the repository CSV, no separate state file.
        self.store_path.write_bytes(backup)
        self.assertEqual(core.load_store()["Units"].sum(), 5)
        self.assertEqual(core.load_state_totals()["Units"].sum(), 3)
        self.assertEqual(core.load_state_totals()["State"].tolist(), ["TX"])
        self.assertEqual(core.load_store()["UnitPrice"].tolist(), [22.0])

    def test_legacy_state_file_is_migrated_and_not_reused(self):
        self.sales.to_csv(self.store_path, index=False)
        self.states.to_csv(self.state_path, index=False)
        self.assertEqual(core.load_state_totals()["Units"].sum(), 3)
        backup = pd.read_csv(io.BytesIO(core.store_backup_bytes()))
        self.assertEqual(backup["RecordType"].tolist(), ["Sales", "State Totals"])
        core.save_store(self.sales)
        core.save_state_totals(self.states.iloc[:0])
        self.assertTrue(core.load_state_totals().empty)
        # The old file must not resurrect cleared state records.
        self.assertTrue(self.state_path.exists())

    def test_sales_only_restore_preserves_existing_states(self):
        core.save_state_totals(self.states)
        counts = core.restore_store_backup(self.sales)
        self.assertEqual(counts, (1, 1))
        self.assertEqual(core.load_state_totals()["Units"].sum(), 3)

    def test_invalid_combined_backup_does_not_overwrite_data(self):
        core.save_store(self.sales)
        original = self.store_path.read_bytes()
        for invalid in (
            self.sales.assign(RecordType="Invalid"),
            self.sales.assign(RecordType="State Totals"),
        ):
            with self.assertRaises(ValueError):
                core.restore_store_backup(invalid)
            self.assertEqual(self.store_path.read_bytes(), original)

    def test_price_updates_only_sales_and_keeps_state_rows(self):
        core.save_store(self.sales)
        core.save_state_totals(self.states)
        states_before = pd.read_csv(self.store_path).query("RecordType == 'State Totals'").reset_index(drop=True)
        map_path = self.store_path.parent / "vendor_map.xlsx"
        pd.DataFrame([{
            "Retailer": "Depot", "SKU": "NB4", "Vendor": "Nisus", "Price": 22.0,
        }]).to_excel(map_path, index=False)
        counts = core.update_sku_price(
            "Depot", "NB4", 30.0, vendor_map_path=map_path, store_path=self.store_path,
        )
        self.assertEqual(counts, (1, 1))
        self.assertEqual(core.load_store()["UnitPrice"].tolist(), [30.0])
        states_after = pd.read_csv(self.store_path).query("RecordType == 'State Totals'").reset_index(drop=True)
        pd.testing.assert_frame_equal(states_before, states_after)


if __name__ == "__main__":
    unittest.main()
