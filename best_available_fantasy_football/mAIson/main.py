"""Run the functions within."""

import json

import elevenlabs
import openai
import pandas as pd

from .refactor import AIPlayerDraft
from .static_values import USEFUL_STATS
from .utils import clean_player_name_col, fetch_player_data, fetch_player_stats


def authenticate():
    """Authenticate with APIs."""
    with open("elevenlabs_secret.json") as f:
        elevenlabs.set_api_key(json.load(f)["api_key"])

    with open("gpt_secret.json") as f:
        openai.api_key = json.load(f)["api_key"]


def main():
    """Run main loop."""
    with open("fantasy_data_secrets.json") as f:
        api_key = json.load(f)["api_key"]

    authenticate()

    player_data = fetch_player_data(api_key)
    player_stats = fetch_player_stats(api_key)

    player_df = pd.DataFrame(player_data)
    player_df["clean_name"] = clean_player_name_col(
        player_df["FirstName"] + " " + player_df["LastName"]
    )
    player_df = player_df[
        [
            "PlayerID",
            "clean_name",
            "Height",
            "Weight",
            "BirthDate",
            "College",
            "Experience",
            "PhotoUrl",
            "AverageDraftPosition",
            "InjuryStatus",
            "FantasyPosition",
        ]
    ]

    player_stats_df = pd.DataFrame(player_stats)[["PlayerID"] + USEFUL_STATS]

    rankings = pd.read_csv("rankings/bdge_rankings/2023-08-02/2023-08-02-clean.csv")
    rankings["clean_name"] = clean_player_name_col(rankings["name"])

    buffed_rankings = rankings.merge(
        player_df,
        how="left",
        left_on=["clean_name", "position"],
        right_on=["clean_name", "FantasyPosition"],
    )

    buffed_rankings_w_stats = buffed_rankings.merge(
        player_stats_df, how="left", on=["PlayerID"]
    )

    ai_player_draft = AIPlayerDraft()
    ai_player_draft.draft_loop(buffed_rankings_w_stats)


def backup_loop():
    """In case things break."""
    authenticate()

    ai_player_draft = AIPlayerDraft()
    rankings = pd.read_csv("backup.csv")
    try:
        drafted_players = pd.read_csv("drafted_backup.csv")
    except Exception:
        drafted_players = pd.DataFrame()

    ai_player_draft.draft_loop(
        rankings[[x for x in rankings.columns if "Unnamed" not in str(x)]],
        drafted_players[
            [x for x in drafted_players.columns if "Unnamed" not in str(x)]
        ],
    )


def play_audio(audio):
    """Play audio file."""
    ai_player_draft = AIPlayerDraft()
    return ai_player_draft.play_audio(audio)


"""
if __name__ == "__main__":
    backup_loop()

"""
