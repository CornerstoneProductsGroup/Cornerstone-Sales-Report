import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

from modules.tab_month_year_compare import _build_comparison_detail


APP = """
import pandas as pd
import streamlit as st
from modules.tab_month_year_compare import _render_comparison_detail, render_standard_view

columns = ["Retailer", "Vendor", "SKU", "Sales", "Units"]
current = pd.DataFrame([
    ["Depot", "Alpha", "Shared", 100.0, 10],
    ["Depot", "Alpha", "New", 30.0, 3],
    ["Depot", "Beta", "Other", 50.0, 5],
    ["Amazon", "Alpha", "Shared", 900.0, 90],
], columns=columns)
previous = pd.DataFrame([
    ["Depot", "Alpha", "Shared", 80.0, 8],
    ["Depot", "Alpha", "Lost", 20.0, 2],
    ["Depot", "Legacy", "Old", 40.0, 4],
    ["Amazon", "Alpha", "Shared", 600.0, 60],
    ["Closed", "Legacy", "Retired", 10.0, 1],
], columns=columns)
if st.session_state.get("empty_current", False):
    current = current.iloc[:0]
if st.session_state.get("empty_previous", False):
    previous = previous.iloc[:0]
if st.session_state.get("remove_depot", False):
    current = current[current["Retailer"] != "Depot"]
    previous = previous[previous["Retailer"] != "Depot"]
if st.session_state.get("full_view", False):
    from modules.shared_core import calc_kpis
    render_standard_view(
        current, previous, calc_kpis(current), calc_kpis(previous),
        "Current", "Previous", "Prior Year", 0.0,
    )
else:
    _render_comparison_detail(current, previous, "Current", "Previous")
"""


class ComparisonDetailTests(unittest.TestCase):
    def app(self, **state):
        app = AppTest.from_string(APP)
        for key, value in state.items():
            app.session_state[key] = value
        app.run()
        self.assertFalse(app.exception)
        return app

    def table(self, app, index):
        self.assertFalse(app.exception)
        return app.dataframe[index].value

    def test_numeric_comparison_aggregates_and_keeps_both_periods(self):
        current = pd.DataFrame({"Vendor": ["Alpha", "Alpha", "New"], "Sales": [100.0, 30.0, 50.0]})
        previous = pd.DataFrame({"Vendor": ["Alpha", "Lost"], "Sales": [80.0, 20.0]})
        before = current.copy(deep=True)
        result = _build_comparison_detail(current, previous, "Vendor").set_index("Vendor")
        self.assertEqual(result.index.tolist(), ["Alpha", "New", "Lost"])
        self.assertEqual(result.loc["Alpha", "Sales_A"], 130.0)
        self.assertEqual(result.loc["Alpha", "Difference"], 50.0)
        self.assertEqual(result.loc["Alpha", "% Change"], 0.625)
        self.assertTrue(pd.isna(result.loc["New", "% Change"]))
        self.assertEqual(result.loc["Lost", "% Change"], -1.0)
        pd.testing.assert_frame_equal(current, before)

    def test_retailer_vendor_sku_path_preserves_comparison_and_totals(self):
        app = self.app()
        top = self.table(app, 0).copy()
        self.assertEqual(top.columns.tolist(), [
            "Retailer", "Sales (Current)", "Sales (Previous)", "Difference", "% Change",
        ])
        self.assertEqual(top.iloc[-1].tolist(), ["Total", "$1,080", "$750", "$330", "44.0%"])
        app.selectbox[1].select("Depot").run()
        vendors = self.table(app, 1).set_index("Vendor")
        self.assertEqual(set(vendors.index), {"Alpha", "Beta", "Legacy", "Total"})
        self.assertEqual(vendors.loc["Total", "Sales (Current)"], "$180")
        self.assertEqual(vendors.loc["Total", "Sales (Previous)"], "$140")
        app.selectbox[2].select("Alpha").run()
        skus = self.table(app, 2).set_index("SKU")
        self.assertEqual(set(skus.index), {"Shared", "New", "Lost", "Total"})
        self.assertEqual(skus.loc["Shared", "Sales (Current)"], "$100")
        self.assertEqual(skus.loc["Lost", "% Change"], "-100.0%")
        self.assertEqual(skus.loc["Total", "Difference"], "$30")
        self.assertEqual(skus.loc["Total", "% Change"], "30.0%")
        pd.testing.assert_frame_equal(self.table(app, 0), top)

    def test_vendor_retailer_sku_path(self):
        app = self.app()
        app.selectbox[0].select("Vendor").run()
        app.selectbox[1].select("Alpha").run()
        retailers = self.table(app, 1).set_index("Retailer")
        self.assertEqual(set(retailers.index), {"Amazon", "Depot", "Total"})
        self.assertEqual(retailers.loc["Total", "Sales (Current)"], "$1,030")
        app.selectbox[2].select("Depot").run()
        skus = self.table(app, 2).set_index("SKU")
        self.assertEqual(skus.loc["Shared", "Sales (Current)"], "$100")
        self.assertEqual(skus.loc["Total", "Sales (Previous)"], "$100")

    def test_comparison_only_parent_and_child_are_selectable(self):
        app = self.app()
        self.assertIn("Closed", app.selectbox[1].options)
        app.selectbox[1].select("Closed").run()
        app.selectbox[2].select("Legacy").run()
        skus = self.table(app, 2).set_index("SKU")
        self.assertEqual(skus.loc["Retired", "Sales (Current)"], "$0")
        self.assertEqual(skus.loc["Retired", "Sales (Previous)"], "$10")
        self.assertEqual(skus.loc["Total", "% Change"], "-100.0%")

    def test_changing_parent_or_dimension_clears_downstream_selection(self):
        app = self.app()
        app.selectbox[1].select("Depot").run()
        app.selectbox[2].select("Legacy").run()
        app.selectbox[1].select("Amazon").run()
        self.assertEqual(len(app.dataframe), 2)
        self.assertIsNone(app.selectbox[2].value)
        self.assertEqual(app.selectbox[2].options, ["Alpha"])
        app.selectbox[0].select("Vendor").run()
        self.assertEqual(len(app.dataframe), 1)
        self.assertIsNone(app.selectbox[1].value)
        self.assertEqual(app.selectbox[1].label, "Select Vendor for Level 2")
        self.assertFalse(app.exception)

    def test_period_changes_remove_stale_selection(self):
        app = self.app()
        app.selectbox[1].select("Depot").run()
        app.selectbox[2].select("Alpha").run()
        app.session_state["remove_depot"] = True
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.dataframe), 1)
        self.assertIsNone(app.selectbox[1].value)
        self.assertNotIn("Depot", app.selectbox[1].options)

    def test_empty_periods(self):
        for empty_current, empty_previous in [(True, False), (False, True), (True, True)]:
            with self.subTest(current=empty_current, previous=empty_previous):
                app = self.app(empty_current=empty_current, empty_previous=empty_previous)
                if empty_current and empty_previous:
                    self.assertEqual(len(app.selectbox), 1)
                    self.assertIn("No data available", app.info[0].value)
                else:
                    app.selectbox[1].select("Depot").run()
                    app.selectbox[2].select("Alpha").run()
                    skus = self.table(app, 2).set_index("SKU")
                    empty_col = "Sales (Current)" if empty_current else "Sales (Previous)"
                    self.assertTrue((skus[empty_col] == "$0").all())
                self.assertFalse(app.exception)

    def test_full_standard_view_wires_drilldown_and_keeps_other_sections(self):
        app = self.app(full_view=True)
        headers = [header.value for header in app.subheader]
        self.assertIn("Comparison Detail", headers)
        self.assertIn("Movers", headers)
        self.assertIn("Current Only / Compare Only Activity", headers)
        app.selectbox[1].select("Depot").run()
        app.selectbox[2].select("Alpha").run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Level 3" in text.value for text in app.markdown))


if __name__ == "__main__":
    unittest.main()
