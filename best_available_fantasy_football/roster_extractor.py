"""Get roster data."""

from abc import ABC, abstractmethod
from typing import Mapping, TypedDict, Union

Roster = Mapping


class YahooSecrets(TypedDict):
    """Dictionary to hold required secrets."""

    access_token: str
    guid: Union[str, None]
    refresh_token: str
    token_time: float
    token_type: str
    consumer_key: str
    consumer_secret: str


class RosterExtractor(ABC):
    """Base class for RosterExtractor."""

    @abstractmethod
    def get_roster(self, team) -> Roster:
        """Get roster for specified team."""


class YahooRosterExtractor(RosterExtractor):
    """RosterExtractor for Yahoo leagues."""

    def __init__(
        self,
        yahoo_secrets: YahooSecrets,
        league_id: str,
    ):
        """Initialize the extractor."""
        import yahoo_fantasy_api
        import yahoo_oauth

        self.league_id = league_id

        # Authenticate with OAuth
        oauth = yahoo_oauth.OAuth2(**yahoo_secrets)
        if not oauth.token_is_valid():
            oauth.refresh_access_token()

        # Get league info
        self.league = yahoo_fantasy_api.League(sc=oauth, league_id=self.league_id)

    def get_roster(self, team):
        """Get roster for specified team."""
        team = self.league.to_team(team_key=f"{self.league_id}.t.{team}")

        return team.roster()


def main():
    """Example script."""
    from pathlib import Path

    import pandas as pd
    import yahoo_fantasy_api
    import yahoo_oauth
    import yaml

    from best_available_fantasy_football.draft_rating import BDGEDraftOrderExtractor

    with open(Path("yahoo_secrets.json")) as f:
        yahoo_secrets = yaml.safe_load(f)
    with open(Path("secrets.json")) as f:
        yahoo_secrets.update(yaml.safe_load(f))

    oauth = yahoo_oauth.OAuth2(**yahoo_secrets)
    if not oauth.token_is_valid():
        oauth.refresh_access_token()

    YAHOO_ENDPOINT = "https://fantasysports.yahooapis.com/fantasy/v2"

    league_id = yahoo_fantasy_api.Game(oauth, "nfl").league_ids(year=2022)[0]
    league = yahoo_fantasy_api.League(sc=oauth, league_id=league_id)
    roster_extractor = YahooRosterExtractor(yahoo_secrets, league_id)

    team_info = {}
    for n in range(1, 17):
        team_summary = oauth.session.get(
            f"{YAHOO_ENDPOINT}/team/{league_id}.t.{n}", params={"format": "json"}
        ).json()
        if team_summary.get("error") is not None:
            break
        team_info[str(n)] = {
            "manager": team_summary["fantasy_content"]["team"][0][-1]["managers"][0][
                "manager"
            ]["nickname"],
            "roster": roster_extractor.get_roster(n),
        }

    rosters = pd.DataFrame()
    for team in team_info.values():
        df = pd.DataFrame(team["roster"])
        df["manager"] = team["manager"]
        rosters = rosters.append(df)

    rostered_players = pd.DataFrame(league.taken_players()).sort_values(
        "percent_owned", ascending=False
    )
    rostered_players = rostered_players.merge(
        rosters[["player_id", "manager"]], on="player_id"
    )
    free_agents = pd.DataFrame(league.free_agents("O")).sort_values(
        "percent_owned", ascending=False
    )
    free_agents["clean_name"] = (
        free_agents["name"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"\W", "", regex=True)
        .str.split("_")
        .str[0:2]
        .str.join("_")
        .str.replace("eli_mitchell", "elijah_mitchell")
    )
    rostered_players["clean_name"] = (
        rostered_players["name"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"\W", "", regex=True)
        .str.split("_")
        .str[0:2]
        .str.join("_")
        .str.replace("eli_mitchell", "elijah_mitchell")
    )

    bdge_ratings = Path(
        "rankings/bdge_rankings/season-long-draft-rankings-superflex-08-26-2022.csv"
    )
    bdge_table = BDGEDraftOrderExtractor().extract_draft_order(bdge_ratings)
    bdge_table["clean_name"] = (
        bdge_table["name"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"\W", "", regex=True)
        .str.split("_")
        .str[0:2]
        .str.join("_")
    )
    bdge_table["position"] = bdge_table["positional_rank"].str[:2]
    bdge_table["rank"] = bdge_table["positional_rank"].str[2:].astype(int)

    rostered = rostered_players.merge(bdge_table, on="clean_name")
    free_agent = free_agents.merge(bdge_table, on="clean_name")

    best_avail = free_agent.loc[
        free_agent.groupby("position")["rank"].idxmin(), ["position", "name_x", "rank"]
    ]
    best_avail.columns = ["position", "best_avail_name", "best_avail_rank"]

    rostered = rostered.merge(best_avail, on="position")
    should_be_replaced = rostered.loc[rostered["best_avail_rank"] < rostered["rank"]]

    should_be_replaced[
        [
            "name_x",
            "percent_owned",
            "position",
            "rank",
            "best_avail_rank",
            "best_avail_name",
            "manager",
        ]
    ].to_csv("test.csv", index=False)
