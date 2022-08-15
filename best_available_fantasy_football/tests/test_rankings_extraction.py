"""Unit tests for ranking_extractions.py."""

import unittest
import pandas as pd

from best_available_fantasy_football.rankings_extraction import (
    BDGEDraftOrderExtractor,
    ManualDraftOrderExtractor,
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


if __name__ == "__main__":
    unittest.main()
