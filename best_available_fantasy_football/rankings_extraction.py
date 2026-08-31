"""Pull rankings into a dataframe."""

import json
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

        out_data = {
            "pick_number": [],
            "pick": [],
            "player_team": [],
            "player_position": [],
            "drafter": [],
        }
        for row in base_file.iterrows():
            pick_number = int(row[0]) + 1
            drafts = row[1]
            pick = " ".join(drafts["player"].split(",")[0].split(" ")[:-1])
            team = drafts["player"].split(",")[-2].rsplit(" ", 1)[-1]
            position = drafts["player"].split(",")[-1].strip()

            out_data["drafter"].append(drafts["team"])
            out_data["pick"].append(pick)
            out_data["pick_number"].append(pick_number)
            out_data["player_team"].append(team)
            out_data["player_position"].append(position)

        return pd.DataFrame(out_data)


class SleeperDraftOrderExtractor(DraftOrderExtractor):
    """Extract a common draft table from a Sleeper draft-picks snapshot."""

    def __init__(self, users_file: PathLike, manager_names: dict[str, str] | None = None):
        self.users_file = Path(users_file)
        self.manager_names = manager_names or {}

    @staticmethod
    def _load_json(path: Path) -> list[dict]:
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = path.read_text(encoding="windows-1252")
        data = json.loads(text)
        return data.get("value", data) if isinstance(data, dict) else data

    @staticmethod
    def _ascii(value: str) -> str:
        return value.encode("ascii", "ignore").decode()

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        """Return Sleeper picks using the same schema as the other handlers."""
        users = {
            str(user["user_id"]): user
            for user in self._load_json(self.users_file)
        }
        rows = []
        for pick in self._load_json(Path(file_path)):
            user_id = str(pick["picked_by"])
            user = users.get(user_id, {})
            user_metadata = user.get("metadata") or {}
            metadata = pick.get("metadata") or {}
            player_name = " ".join(
                part for part in (metadata.get("first_name"), metadata.get("last_name")) if part
            )
            sleeper_team = self._ascii(
                user_metadata.get("team_name")
                or user.get("display_name")
                or user_id
            )
            rows.append(
                {
                    "pick_number": int(pick["pick_no"]),
                    "round": int(pick["round"]),
                    "pick": player_name,
                    "original_name": player_name,
                    "drafter": self.manager_names.get(
                        user_id, self._ascii(user.get("display_name") or sleeper_team)
                    ),
                    "sleeper_team_name": sleeper_team,
                    "player_team": metadata.get("team", ""),
                    "player_position": metadata.get("position", ""),
                }
            )
        return pd.DataFrame(rows).sort_values("pick_number").reset_index(drop=True)


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


class DraftSharksEmbeddedADPExtractor(DraftOrderExtractor):
    """Extract the selected Sleeper ADP set embedded in a current ADP page."""

    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        page = Path(file_path).read_text(encoding="utf-8-sig")
        marker = "var vueAppData = "
        if marker not in page:
            raise ValueError(f"DraftSharks data was not found in {file_path}")
        data, _ = json.JSONDecoder().raw_decode(page.split(marker, 1)[1])
        selected = data["selected"]
        descriptor = next(
            item
            for item in data["availability"]
            if item["type"] == selected["type"]
            and int(item["superflex"]) == int(selected["superflex"])
            and item["scoring"] == selected["scoring"]
            and item["source"] == "sleeper"
            and int(item["size"]) == int(selected["size"])
        )
        players = data["seed"]["players"]
        rows = []
        for adp_row in data["seed"]["adpSets"][descriptor["key"]]:
            player = players[str(adp_row["id"])]
            rows.append(
                {
                    "player_name": f'{player["fn"]} {player["ln"]}',
                    "player_position": player["fp"],
                    "adp": float(adp_row["pick"]),
                }
            )
        return pd.DataFrame(rows)

class DraftSharksStraightRead(DraftOrderExtractor):
    def extract_draft_order(self, file_path: PathLike) -> pd.DataFrame:
        return pd.read_csv(file_path)
