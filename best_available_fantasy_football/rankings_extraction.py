"""Pull rankings into a dataframe."""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Union

import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import ResultSet, Tag

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


class YahooHtmlDraftOrderExtractor(DraftOrderExtractor):
    """Extractor for draft order files from yahoo."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        # Get table from file path
        table = self.get_tables_from_html_file(file_path)

        # Grab table rows
        data = self.get_rows(table)

        # Return data with headers
        return pd.DataFrame(data)

    def get_tables_from_html_file(self, html_file: PathLike) -> ResultSet:
        """Get table from HTML file."""
        # Read in file
        with open(html_file, encoding="utf-8") as f:
            html = f.read()

        # Parse the data
        soup = BeautifulSoup(html, features="lxml")
        tables = soup.find_all(
            "table",
        )
        if not isinstance(tables, ResultSet):
            raise ValueError(f"Could not find draft order for {html_file}")

        return tables

    def get_rows(self, tables: ResultSet) -> list:
        """Get content from all table rows."""
        data = []
        for draft_round, table in enumerate(tables):
            draft_round += 1
            table_body = table.find("tbody")
            if not isinstance(table_body, Tag):
                raise ValueError(f"Could not find body of table: {table}, {table_body}")

            rows = table_body.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                cols = [ele.text.strip() for ele in cols]

                # Pick number
                pick_number = int(cols[0].strip("."))

                # Pick
                name, pos = cols[1].split("(")
                name = name.strip()
                team, position = pos.split(" - ")
                position = position.strip(")")

                # Drafter
                drafter = cols[2]

                # Turn this into a data row
                data.append(
                    {
                        "round": draft_round,
                        "pick_number": pick_number,
                        "player_name": name,
                        "player_team": team,
                        "player_position": position,
                        "drafter_team_name": drafter,
                    }
                )

        return data


class DraftSharksADPDraftOrderExtractor(DraftOrderExtractor):
    """Extractor for DraftSharks ADP."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Extract draft order from provided file into a dataframe."""
        # Get table from file path
        table = self.get_table_from_html_file(file_path)

        # Grab table rows
        data = self.get_rows(table)

        # Return data with headers
        return pd.DataFrame(data)

    def get_table_from_html_file(self, html_file: PathLike) -> Tag:
        """Get table from HTML file."""
        # Read in file
        with open(html_file, encoding="utf-8") as f:
            html = f.read()

        # Parse the data
        soup = BeautifulSoup(html, features="lxml")
        table = soup.find_all(
            "table",
        )[0]
        if not isinstance(table, Tag):
            raise ValueError(f"Could not find draft order for {html_file}")

        return table

    def get_rows(self, table: Tag) -> list:
        """Get content from table rows."""
        data = []

        table_body = table.find("tbody")
        if not isinstance(table_body, Tag):
            raise ValueError(f"Could not find body of table: {table}, {table_body}")

        rows = table_body.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            player_info = [x.strip() for x in cols[0].prettify().split("\n")]

            player_rank = int(float(player_info[3]))
            player_name = player_info[6]
            player_position = player_info[8]

            adp_round, adp_pick = cols[1].text.split("\xa0")[0].split(".")

            adp = ((int(adp_round) - 1) * 12) + int(adp_pick)

            # Turn this into a data row
            data.append(
                {
                    "player_rank": player_rank,
                    "player_name": player_name,
                    "player_position": player_position,
                    "adp": adp,
                }
            )

        return data
