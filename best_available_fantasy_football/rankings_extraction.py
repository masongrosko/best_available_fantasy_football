"""Pull rankings into a dataframe."""

import pandas as pd
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union
from bs4 import BeautifulSoup
from bs4.element import Tag

PathLike = Union[Path, str]


class DraftOrderExtractor(ABC):
    """Extract draft order from provided file into a dataframe."""

    @abstractmethod
    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""


class BDGEDraftOrderExtractor(DraftOrderExtractor):
    """Extract draft order from provided BDGE file into a dataframe."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        # Get table from file path
        table = self.get_table_from_html_file(file_path)

        # Grab table rows
        data = self.get_rows(table)

        # Return data with headers
        return pd.DataFrame(data, columns=self.get_headers(table))

    def get_table_from_html_file(self, html_file: PathLike) -> Tag:
        """Get table from HTML file."""
        # Read in file
        with open(html_file) as f:
            html = f.read()

        # Parse the data
        soup = BeautifulSoup(html, features="lxml")
        table = soup.find(
            "table",
            attrs={
                "class": "table is-hoverable is-fullwidth is-striped has-sticky-header"
            },
        )
        if not isinstance(table, Tag):
            raise ValueError(f"Could not find draft order for {html_file}")

        return table

    def get_rows(self, table: Tag) -> list:
        """Get content from all table rows."""
        data = []
        table_body = table.find("tbody")
        if not isinstance(table_body, Tag):
            raise ValueError(f"Could not find body of table: {table}, {table_body}")

        rows = table_body.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            cols = [ele.text.strip() for ele in cols]
            data.append([ele for ele in cols if ele])  # Get rid of empty value

        return data

    def get_headers(self, table: Tag) -> list:
        """Get headers fro html table."""
        return [x.text.strip() for x in table.find_all("th")]


class ManualDraftOrderExtractor(DraftOrderExtractor):
    """Extractor for draft order files."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        base_file = pd.read_csv(file_path, index_col=0)

        out_data = {
            "pick_number": [],
            "pick": [],
            "drafter": []
        }
        for row in base_file.iterrows():
            draft_round = int(row[0])
            drafts = row[1]
            round_start = (draft_round - 1) * len(row[1])

            if draft_round % 2 == 0:
                drafts = drafts.loc[::-1]

            for n, i in enumerate(drafts.iteritems()):
                out_data["drafter"].append(i[0])
                out_data["pick"].append(i[1])
                out_data["pick_number"].append(round_start + n)

        return pd.DataFrame(out_data)