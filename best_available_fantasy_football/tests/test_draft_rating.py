"""Tests for shared draft-rating behavior."""

import unittest

import pandas as pd

from best_available_fantasy_football.draft_rating import (
    _clean_player_name_col,
    _draft_pick_table,
)


class TestCleanPlayerName(unittest.TestCase):
    """Player names from different providers should share one merge key."""

    def test_initial_variants_match(self):
        names = pd.Series(["DJ Moore", "D.J. Moore", "D. J. Moore"])

        cleaned = _clean_player_name_col(names)

        self.assertEqual(cleaned.nunique(), 1)
        self.assertEqual(cleaned.iloc[0], "dj_moore")

    def test_other_punctuated_initials(self):
        names = pd.Series(["J.K. Dobbins", "JK Dobbins", "A.J. Brown", "AJ Brown"])

        cleaned = _clean_player_name_col(names)

        self.assertEqual(cleaned.tolist(), ["jk_dobbins", "jk_dobbins", "aj_brown", "aj_brown"])


class TestDraftPickTable(unittest.TestCase):
    """Compact report tables should keep their stable mobile column contract."""

    def test_column_order_and_delta_formatting(self):
        rows = pd.DataFrame(
            {
                "round_picked": [8],
                "name": ["Kyle Monangai"],
                "pick_number": [85],
                "overall_rank": [120],
                "ADP": [91],
                "tier": [14],
                "overall_delta": [-35],
                "adp_delta": [-6],
                "tier_delta": [-4],
            }
        )

        html = _draft_pick_table(rows)

        headers = [
            "Round", "Name", "Pick", "Rank", "Tier",
            "Rank Δ", "Tier Δ", "ADP", "ADP Δ",
        ]
        self.assertEqual([html.index(f"<th>{header}</th>") for header in headers], sorted(html.index(f"<th>{header}</th>") for header in headers))
        for value in ["Kyle Monangai", "-35", ">-6</strong>", "-4"]:
            self.assertIn(value, html)
        self.assertIn("color: #ff7f0e", html)

        positive_html = _draft_pick_table(
            pd.DataFrame({"name": ["Value Pick"], "adp_delta": [6]})
        )
        self.assertIn("color: #1f77b4", positive_html)

    def test_zero_delta_uses_em_dash(self):
        rows = pd.DataFrame({"name": ["Player"], "overall_delta": [0]})

        html = _draft_pick_table(rows)
        self.assertIn("—", html)
        self.assertNotIn("color:", html)

    def test_optional_total_row_sums_rank_and_adp_deltas(self):
        rows = pd.DataFrame(
            {
                "name": ["One", "Two"],
                "overall_delta": [10, -3],
                "adp_delta": [-4, -2],
            }
        )

        html = _draft_pick_table(rows, include_totals=True)

        self.assertIn("<td>Total</td>", html)
        self.assertIn(">7</strong>", html)
        self.assertIn(">-6</strong>", html)


if __name__ == "__main__":
    unittest.main()
