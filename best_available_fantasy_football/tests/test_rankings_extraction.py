"""Unit tests for ranking_extractions.py."""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from best_available_fantasy_football.rankings_extraction import (
    BDGEDraftOrderExtractor,
    DraftSharksEmbeddedADPExtractor,
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


class TestDraftSharksEmbeddedADPExtractor(unittest.TestCase):
    """The embedded extractor should select consensus rather than Sleeper ADP."""

    def test_extracts_consensus_source(self):
        data = {
            "selected": {
                "type": "",
                "superflex": 0,
                "scoring": "half-ppr",
                "size": 12,
            },
            "availability": [
                {
                    "key": "consensus",
                    "type": "",
                    "superflex": 0,
                    "scoring": "half-ppr",
                    "source": "consensus",
                    "size": 12,
                },
                {
                    "key": "sleeper",
                    "type": "",
                    "superflex": 0,
                    "scoring": "half-ppr",
                    "source": "sleeper",
                    "size": 12,
                },
            ],
            "seed": {
                "players": {
                    "1": {"fn": "Josh", "ln": "Allen", "fp": "QB"}
                },
                "adpSets": {
                    "consensus": [{"id": 1, "pick": 23}],
                    "sleeper": [{"id": 1, "pick": 20}],
                },
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            page = Path(directory) / "adp.html"
            page.write_text(
                f"<script>var vueAppData = {json.dumps(data)};</script>",
                encoding="utf-8",
            )
            output = DraftSharksEmbeddedADPExtractor().extract_draft_order(page)

        self.assertEqual(output.loc[0, "player_name"], "Josh Allen")
        self.assertEqual(output.loc[0, "adp"], 23)


if __name__ == "__main__":
    unittest.main()
