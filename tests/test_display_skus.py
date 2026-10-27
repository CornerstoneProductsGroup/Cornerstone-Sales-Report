import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from modules import shared_core as core


class DisplaySKUTests(unittest.TestCase):
    def setUp(self):
        self.renames = patch.object(core, "load_retailer_renames", return_value={})
        self.renames.start()
        self.addCleanup(self.renames.stop)
        self.mapping = pd.DataFrame({
            "Retailer": ["Depot"] * 4,
            "SKU": ["DECOMIA-53", "DECOMIA-953", "OTHER", "UNLABELED"],
            "Price": [10.0, 20.0, 5.0, 3.0],
            "Vendor": ["Vendor"] * 4,
            "Display SKU": ["Deco Mia-953", "Deco Mia-953", "Other", ""],
        })
        self.raw = pd.DataFrame({
            "Retailer": ["Depot"] * 6,
            "SKU": ["DECOMIA-53", "DECOMIA-953", "Deco Mia-953", "OTHER", "UNLABELED", "UNKNOWN"],
            "Units": [1, 2, 3, 4, 5, 6],
            "UnitPrice": [None, None, 25.0, None, None, 7.0],
            "StartDate": ["2026-10-19"] * 6,
            "EndDate": ["2026-10-23"] * 6,
            "SourceFile": ["weekly.xlsx"] * 6,
        })

    def test_sales_preserve_labels_and_combine_historical_aliases(self):
        original = self.raw.copy(deep=True)
        result = core.enrich_sales(self.raw, self.mapping)
        self.assertEqual(result["SKU"].tolist(), [
            "Deco Mia-953", "Deco Mia-953", "Deco Mia-953", "Other", "UNLABELED", "UNKNOWN",
        ])
        self.assertEqual(len(result), len(self.raw))
        self.assertEqual(result["Units"].sum(), 21)
        self.assertEqual(result["Sales"].sum(), 202.0)
        grouped = result.groupby("SKU")[["Units", "Sales"]].sum()
        self.assertEqual(grouped.loc["Deco Mia-953", "Units"], 6)
        self.assertEqual(grouped.loc["Deco Mia-953", "Sales"], 125.0)
        self.assertEqual(result.loc[5, "Vendor"], "Unknown")
        pd.testing.assert_frame_equal(self.raw, original)
        exported = pd.read_csv(io.StringIO(result.to_csv(index=False)))
        self.assertEqual(exported["SKU"].iloc[0], "Deco Mia-953")

    def test_loading_three_alias_entries_does_not_duplicate_sales(self):
        mapping = pd.DataFrame({
            "Retailer": ["Depot"] * 3,
            "SKU": ["DECOMIA-53", "DECOMIA-953", "Deco Mia-953"],
            "Price": [10.0] * 3,
            "Vendor": ["Vendor"] * 3,
            "Display SKU": ["Deco Mia-953"] * 3,
        })
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "vendor_map.xlsx"
            mapping.to_excel(map_path, index=False)
            with patch.object(core, "DEFAULT_VENDOR_MAP", map_path):
                loaded = core.load_vendor_map()
            result = core.enrich_sales(self.raw.iloc[:3], loaded)
            self.assertEqual(result["SKU"].tolist(), ["Deco Mia-953"] * 3)
            self.assertEqual(len(result), 3)
            self.assertEqual(result["Units"].sum(), 6)
            self.assertEqual(result["Sales"].sum(), 105.0)

    def test_column_e_overrides_b_and_blank_e_preserves_column_b(self):
        mapping = pd.DataFrame({
            "Retailer": ["Depot", "Lowes", "Tractor Supply", "Walmart", "Depot"],
            "SKU": ["Niban4lbShaker", "NIBAN4LBSHAKER", "NB4", "NB4", "Deco Mia-953"],
            "Price": [22.0, 22.0, 23.68, 35.0, 10.0],
            "Vendor": ["Nisus"] * 4 + ["Vendor"],
            "Display SKU": [None, "Niban4lbShaker", "Niban4lbShaker", "Niban4lbShaker", "  "],
        })
        raw = self.raw.iloc[:5].copy()
        raw["Retailer"] = mapping["Retailer"]
        raw["SKU"] = ["NIBAN4LBSHAKER", "NIBAN4LBSHAKER", "NB4", "NB4", "DECOMIA-953"]
        raw["Units"] = [833, 4, 547, 0, 2]
        raw["UnitPrice"] = None
        original = raw.copy(deep=True)
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "vendor_map.xlsx"
            mapping.to_excel(map_path, index=False)
            workbook_before = map_path.read_bytes()
            with patch.object(core, "DEFAULT_VENDOR_MAP", map_path):
                loaded = core.load_vendor_map()
            self.assertEqual(loaded["SKU"].tolist(), raw["SKU"].tolist())
            for result in (
                core.enrich_sales(raw, loaded),
                core.enrich_state_totals(raw.assign(State="TX"), loaded),
            ):
                self.assertEqual(result["SKU"].tolist(), ["Niban4lbShaker"] * 4 + ["Deco Mia-953"])
                self.assertEqual(sorted(result["SKU"].unique()), ["Deco Mia-953", "Niban4lbShaker"])
                grouped = result.groupby("SKU")["Units"].sum()
                self.assertEqual(grouped["Niban4lbShaker"], 1384)
                self.assertEqual(len(result), len(raw))
            sales = core.enrich_sales(raw, loaded)
            self.assertAlmostEqual(sales["Sales"].sum(), 31386.96)
            pd.testing.assert_frame_equal(raw, original)
            self.assertEqual(map_path.read_bytes(), workbook_before)

    def test_legacy_map_without_column_e_preserves_column_b(self):
        mapping = self.mapping.drop(columns="Display SKU").copy()
        mapping.loc[0, "SKU"] = "Deco Mia-53"
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "vendor_map.xlsx"
            mapping.to_excel(map_path, index=False)
            with patch.object(core, "DEFAULT_VENDOR_MAP", map_path):
                loaded = core.load_vendor_map()
            result = core.enrich_sales(self.raw, loaded)
            self.assertEqual(result.loc[0, "SKU"], "Deco Mia-53")
            self.assertEqual(loaded.loc[0, "SKU"], "DECOMIA-53")

    def test_state_totals_use_same_labels_including_sku_only_fallback(self):
        raw = self.raw.assign(State="TX")
        raw.loc[2, "Retailer"] = ""
        result = core.enrich_state_totals(raw, self.mapping)
        self.assertEqual(result["SKU"].tolist(), [
            "Deco Mia-953", "Deco Mia-953", "Deco Mia-953", "Other", "UNLABELED", "UNKNOWN",
        ])
        self.assertEqual(result.groupby("SKU")["Units"].sum()["Deco Mia-953"], 6)
        self.assertEqual(result.loc[2, "Vendor"], "Vendor")
        self.assertEqual(result["Units"].sum(), raw["Units"].sum())

    def test_state_totals_support_legacy_and_empty_maps(self):
        raw = self.raw.assign(State="TX")
        for mapping in (self.mapping.drop(columns="Display SKU"), self.mapping.iloc[:0]):
            with self.subTest(columns=mapping.columns.tolist(), rows=len(mapping)):
                result = core.enrich_state_totals(raw, mapping)
                self.assertEqual(result["SKU"].iloc[0], "DECOMIA-53")
                self.assertEqual(result["Units"].sum(), 21)

    def test_save_preserves_display_text_and_source_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "vendor_map.xlsx"
            store_path = Path(directory) / "sales_store.csv"
            self.mapping.to_excel(map_path, index=False)
            self.raw.to_csv(store_path, index=False)
            matched, updated = core.update_sku_price(
                "Depot", "Deco Mia-953", 30.0, display_sku="  Deco Mia-953  ",
                vendor_map_path=map_path, store_path=store_path,
            )
            self.assertEqual((matched, updated), (2, 3))
            saved = pd.read_excel(map_path).fillna("")
            self.assertEqual(saved["Display SKU"].iloc[:2].tolist(), ["Deco Mia-953"] * 2)
            self.assertEqual(saved["SKU"].tolist(), self.mapping["SKU"].tolist())
            store = pd.read_csv(store_path)
            self.assertEqual(store["SKU"].tolist(), self.raw["SKU"].tolist())
            self.assertEqual(store["UnitPrice"].iloc[:3].tolist(), [30.0] * 3)
            result = core.enrich_sales(store, saved)
            self.assertEqual(result["SKU"].iloc[:3].tolist(), ["Deco Mia-953"] * 3)

    def test_new_map_entry_preserves_display_text(self):
        with tempfile.TemporaryDirectory() as directory:
            map_path = Path(directory) / "vendor_map.xlsx"
            self.mapping.to_excel(map_path, index=False)
            matched, updated = core.update_sku_price(
                "Depot", "NEW-SKU", 12.0, display_sku="New SKU",
                vendor_map_path=map_path, store_path=Path(directory) / "missing.csv",
            )
            self.assertEqual((matched, updated), (0, 0))
            saved = pd.read_excel(map_path)
            self.assertEqual(saved.iloc[-1]["SKU"], "NEW-SKU")
            self.assertEqual(saved.iloc[-1]["Display SKU"], "New SKU")


if __name__ == "__main__":
    unittest.main()
