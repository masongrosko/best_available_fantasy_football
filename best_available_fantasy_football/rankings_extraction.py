"""Pull rankings into a dataframe."""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Union

import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import Tag

PathLike = Union[Path, str]


class DraftType(Enum):
    """Type of draft."""

    SUPERFLEX = 0
    SINGLE_QB = 1


class DraftOrderExtractor(ABC):
    """Extract draft order from provided file into a dataframe."""

    @abstractmethod
    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""


class BDGEDraftOrderExtractor(DraftOrderExtractor):
    """Extract draft order from provided BDGE file into a dataframe."""

    def __init__(self, draft_type: DraftType = DraftType.SUPERFLEX):
        """Initialize BDGE Draft Order Extractor."""
        self.draft_type: DraftType = draft_type

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        file_type = Path(file_path).suffix

        if file_type == ".csv":
            extractor = _BDGEcsvDraftOrderExtractor()
        elif file_type == ".html":
            extractor = _BDGEhtmlDraftOrderExtractor(self.draft_type)
        else:
            raise ValueError(f"file type: {file_type} not supported.")

        return extractor.extract_draft_order(file_path)


class _BDGEcsvDraftOrderExtractor(DraftOrderExtractor):
    """Extract draft order from provided BDGE csv file into a dataframe."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        return pd.read_csv(file_path)


class _BDGEhtmlDraftOrderExtractor(DraftOrderExtractor):
    """Extract draft order from provided BDGE html file into a dataframe."""

    def __init__(self, draft_type: DraftType = DraftType.SUPERFLEX):
        """Initialize BDGE Draft Order Extractor."""
        self.draft_type: DraftType = draft_type

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
        table = soup.find_all(
            "table",
            attrs={
                "class": "table is-hoverable is-fullwidth is-striped has-sticky-header"
            },
        )[self.draft_type.value]
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

        out_data = {"pick_number": [], "pick": [], "drafter": []}
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


class EspnDraftOrderExtractor(DraftOrderExtractor):
    """Extractor for draft order files from espn."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        base_file = pd.read_csv(file_path)
        base_file["team"] = base_file["team"].str.replace(r"\s+", "_", regex=True)

        out_data = {"pick_number": [], "pick": [], "drafter": []}
        for row in base_file.iterrows():
            pick_number = int(row[0]) + 1
            drafts = row[1]
            pick = " ".join(drafts["player"].split(",")[0].split(" ")[:-1])

            out_data["drafter"].append(drafts["team"])
            out_data["pick"].append(pick)
            out_data["pick_number"].append(pick_number)

        return pd.DataFrame(out_data)
