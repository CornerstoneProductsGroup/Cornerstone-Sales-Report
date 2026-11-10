import unittest
from unittest.mock import patch

import pandas as pd

from modules.tab_weekly_goals import render_recent_month_goals


class RecentMonthGoalsTests(unittest.TestCase):
    def render_goals(self, rows):
        frame = pd.DataFrame(rows, columns=["WeekEnd", "Sales"])
        with (
            patch("modules.tab_weekly_goals.st.markdown") as markdown,
            patch("modules.tab_weekly_goals.st.progress") as progress,
            patch("modules.tab_weekly_goals.st.info") as info,
        ):
            render_recent_month_goals(frame)
        return markdown, progress, info

    def test_annual_row_includes_all_current_year_sales_only(self):
        markdown, progress, _ = self.render_goals([
            ("2026-11-06", 520_000),
            ("2025-12-26", 900_000),
            ("2026-01-02", 260_000),
            ("2026-11-06", 780_000),
        ])

        self.assertEqual(progress.call_count, 8)
        self.assertEqual(markdown.call_args.args[0], "**2026 Year to Date**")
        self.assertEqual(progress.call_args.args, (0.5,))
        self.assertEqual(
            progress.call_args.kwargs["text"],
            r"\$1,560,000 / \$3,120,000 (50%)",
        )
        self.assertEqual(markdown.call_args_list[1].args[0], "**May 2026**")
        self.assertEqual(markdown.call_args_list[7].args[0], "**Nov 2026**")
        self.assertEqual(progress.call_args_list[0].args, (0.0,))
        self.assertEqual(progress.call_args_list[6].args, (1.0,))
        self.assertEqual(
            progress.call_args_list[6].kwargs["text"],
            r"\$1,300,000 / \$260,000 (500%)",
        )

    def test_annual_progress_caps_bar_but_preserves_actual_percentage(self):
        _, progress, _ = self.render_goals([("2026-11-06", 3_900_000)])
        self.assertEqual(progress.call_args.args, (1.0,))
        self.assertEqual(
            progress.call_args.kwargs["text"],
            r"\$3,900,000 / \$3,120,000 (125%)",
        )

    def test_annual_progress_resets_for_latest_data_year(self):
        markdown, progress, _ = self.render_goals([
            ("2026-12-25", 3_120_000),
            ("2027-01-01", 31_200),
        ])
        self.assertEqual(markdown.call_args.args[0], "**2027 Year to Date**")
        self.assertAlmostEqual(progress.call_args.args[0], 0.01)
        self.assertEqual(
            progress.call_args.kwargs["text"],
            r"\$31,200 / \$3,120,000 (1%)",
        )

    def test_negative_annual_sales_keep_bar_in_valid_range(self):
        _, progress, _ = self.render_goals([
            ("2026-01-02", -100),
            ("2026-11-06", 0),
        ])
        self.assertEqual(progress.call_args.args, (0.0,))

    def test_empty_data_has_no_progress_rows(self):
        _, progress, info = self.render_goals([])
        progress.assert_not_called()
        info.assert_called_once_with("No monthly sales available.")


if __name__ == "__main__":
    unittest.main()
