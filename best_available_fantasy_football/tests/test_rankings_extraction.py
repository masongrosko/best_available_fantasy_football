"""Unit tests for ranking_extractions.py."""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from best_available_fantasy_football.rankings_extraction import (
    BDGEDraftOrderExtractor,
    ManualDraftOrderExtractor,
    SleeperDraftOrderExtractor,
)


class TestBDGEDraftOrderExtractor(unittest.TestCase):
    """Tests for the BDGEDraftOrderExtractor class."""

    def test_df_output(self):
        """Test to see if outputs a df."""
        file_path = "rankings/bdge_rankings/2022-08-14/rankings.html"

        extractor = BDGEDraftOrderExtractor()
        output = extractor.extract_draft_order(file_path)

        self.assertIsInstance(output, pd.DataFrame)


class TestManualDraftOrderExtractor(unittest.TestCase):
    """Tests for the ManualDraftOrderExtractor class."""

    def test_df_output(self):
        """Test to see if outputs a df."""
        file_path = "rankings/draft_day/2022-08-13.csv"

        extractor = ManualDraftOrderExtractor()
        output = extractor.extract_draft_order(file_path)

        self.assertIsInstance(output, pd.DataFrame)


class TestSleeperDraftOrderExtractor(unittest.TestCase):
    """Tests for normalizing Sleeper snapshots to the shared draft schema."""

    def test_extract_draft_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            users = root / "users.json"
            picks = root / "picks.json"
            users.write_text(
                json.dumps(
                    [
                        {
                            "user_id": "42",
                            "display_name": "sleeper_user",
                            "metadata": {"team_name": "Changing Team Name"},
                        }
                    ]
                ),
                encoding="utf-8",
            )
            picks.write_text(
                json.dumps(
                    [
                        {
                            "pick_no": 1,
                            "round": 1,
                            "picked_by": "42",
                            "metadata": {
                                "first_name": "Test",
                                "last_name": "Player",
                                "team": "MIN",
                                "position": "WR",
                            },
                        }
                    ]
                ),
                encoding="utf-8",
            )

            output = SleeperDraftOrderExtractor(
                users, {"42": "Mason"}
            ).extract_draft_order(picks)

        self.assertEqual(output.loc[0, "drafter"], "Mason")
        self.assertEqual(output.loc[0, "sleeper_team_name"], "Changing Team Name")
        self.assertEqual(output.loc[0, "pick"], "Test Player")
        self.assertEqual(output.loc[0, "pick_number"], 1)


if __name__ == "__main__":
    unittest.main()
