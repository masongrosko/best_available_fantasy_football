"""mAIson utils."""

import elevenlabs
import openai
import pandas as pd
import requests

from .static_values import USEFUL_STATS


def clean_player_name_col(player_name_col: pd.Series) -> pd.Series:
    """Clean player name column."""
    return (
        player_name_col.str.strip()
        .str.lower()
        .str.replace(". ", "", regex=False)
        .str.replace(r"\s+", "_", regex=True)
        .str.replace(r"\W", "", regex=True)
        .str.split("_")
        .str[0:2]
        .str.join("_")
        .str.replace("gabe_davis", "gabriel_davis")
    )


def fetch_player_data(api_key):
    """Fetch all player data."""
    api_url = f"https://api.sportsdata.io/api/nfl/fantasy/json/Players?key={api_key}"

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Check for errors in the response

        player_data = response.json()
        return player_data
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def fetch_player_stats(api_key, season=2022):
    """Fetch all player stats."""
    api_url = (
        f"https://api.sportsdata.io/api/nfl/fantasy/json/PlayerSeasonStats/"
        f"{season}?key={api_key}"
    )

    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Check for errors in the response

        player_stats = response.json()
        return player_stats
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None


def return_first_matches(df: pd.DataFrame, names: pd.Series):
    """Return first matches."""
    matched = df.index == -1

    for name in names:
        if (df["clean_name"] == name).sum() > 1:
            matched[df[df["clean_name"] == name].first_valid_index()] = True
        else:
            matched |= df["clean_name"] == name

    return matched


def draft_round_from_pick_number(pick_number, number_of_teams=10):
    """Return draft round from pick number."""
    return (pick_number // number_of_teams) + 1


def generate_ai_audio(script: str, voice_name: str):
    """Read script using AI voice."""
    print("\n...generating ai audio message\n")
    audio = elevenlabs.generate(text=script, voice=voice_name)

    return audio


def get_last_ai_audio():
    """Get last ai audio."""
    last_audio = elevenlabs.api.History.from_api()[0]
    return get_audio_from_history_item(last_audio)


def get_audio_from_history_item(history_item):
    """Get audio from history item."""
    url = (
        f"{elevenlabs.api.base.api_base_url_v1}/"
        f"history/{history_item.history_item_id}/audio"
    )
    return elevenlabs.api.base.API.get(url).content


def chat_gpt_draft_message(my_pick, prior_picks, round_picked, overall_pick):
    """Chat gpt trash talks."""
    print("\n...generating gpt message\n")
    my_pick_info_cols = [x for x in my_pick.index if x not in USEFUL_STATS]

    returned_message = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are mAIson, a member of a very competitive fantasy "
                "football league. You will "
                "hype up your player before you announce the name of the pick, "
                "mention stats and potential in the style of Bruce Buffer, "
                "2022 was the most recent year and those "
                "stats will be provided in csv format. "
                "After announcing the pick, in the style of an unreasonable NFL fan "
                "on reddit, talk trash on just one of the previous "
                "picks. Previous picks will be provided in csv form. Make sure to use "
                "the specific player's name and act as if that player has no upside "
                "using the stats provided."
                "Max of two paragraphs. MAKE SURE TO NOT write more than 2 paragraphs."
                "Over the top trash talk is necessary to fit in, but keep it "
                "terse! "
                "Informal writing. Variation in sentence structure is needed."
                "If the rank of a previous player is a larger number than the current "
                "pick number make sure to let the league know it was a REACH PICK.",
            },
            {
                "role": "user",
                "content": f"You are picking the following player "
                f"{my_pick[my_pick_info_cols].to_csv()} "
                f"for the overall pick number {overall_pick} taken in "
                f"round {round_picked} of the 2023 draft",
            },
            {
                "role": "assistant",
                "content": "What did their previous season stats look like? ",
            },
            {
                "role": "user",
                "content": f"The 2022 season stats looked like the following "
                f"{my_pick[['name'] + USEFUL_STATS].to_csv()}",
            },
            {
                "role": "assistant",
                "content": "Who did the people before me draft, "
                "I will mention one of these players by name in my trash talk.",
            },
            {
                "role": "user",
                "content": (
                    f"They drafted the following players in this "
                    f"order, {prior_picks.to_csv()}"
                    if len(prior_picks > 1)
                    else "No players drafted yet, skip the trash talk."
                ),
            },
        ],
    )

    return returned_message


def clean_bdge_ranking(path_to_file):
    """Clean bdge ranking."""
    df = pd.read_csv(path_to_file, names=["temp", "position"])
    df["position"] = df["position"].str.strip()
    x = df["temp"].str.split(" - ", expand=True)
    df["team"] = x[1].str.strip()
    x = x[0].str.split(r"(\d+)[.] ", expand=True)

    df["rank"] = x[1].astype(int)
    df["name"] = x[2].str.strip()

    df[["rank", "name", "team", "position"]].sort_values("rank").to_csv(
        path_to_file.replace(".csv", "-clean.csv"), index=False
    )
