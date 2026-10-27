import unittest
from unittest.mock import patch

from modules.tab_kpi_dashboard import _render_exec_kpi_table


class DashboardSKUSummaryTests(unittest.TestCase):
    def render_table(self, compare_label="Prior 8W", lost_tile=None):
        with patch("modules.tab_kpi_dashboard.st.markdown") as markdown:
            _render_exec_kpi_table(
                kA={"Sales": 532777},
                kB={"Sales": 447278},
                current_label="Current 8W",
                compare_label=compare_label,
                new_sku_tile={"value": "19", "delta": "Total Sales: $98"},
                lost_sku_tile=lost_tile,
            )
        return markdown.call_args.args[0]

    def test_summary_is_boxed_after_totals_with_both_metrics(self):
        output = self.render_table(lost_tile={
            "value": "117", "delta": "Total Lost Sales: $6,462",
        })
        self.assertIn("sales-exec-kpi-ribbon sales-exec-sku-summary", output)
        for text in ("New SKUs", "19", "Total Sales: $98", "Lost SKUs", "117", "Total Lost Sales: $6,462"):
            self.assertIn(text, output)
        self.assertLess(output.index("</table>"), output.index("sales-exec-sku-summary"))
        self.assertLess(output.index("sales-exec-sku-summary"), output.rindex("sales-exec-accent"))

    def test_no_comparison_hides_summary(self):
        output = self.render_table(compare_label=None)
        self.assertNotIn("sales-exec-sku-summary", output)
        self.assertNotIn("New SKUs", output)

    def test_missing_lost_tile_renders_only_new_skus(self):
        output = self.render_table()
        self.assertIn("New SKUs", output)
        self.assertNotIn("Lost SKUs", output)


if __name__ == "__main__":
    unittest.main()
