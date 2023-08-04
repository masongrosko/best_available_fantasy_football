"""Create an AI to draft during the 2023 season."""

import subprocess
import threading
import tkinter as tk
from functools import partial
from typing import Union

import pandas as pd
import requests
from PIL import Image, ImageTk

from .static_values import PLAYER_INFO, TEAM_COLORS, USEFUL_STATS, VOICE_NAME
from .utils import (
    chat_gpt_draft_message,
    clean_player_name_col,
    draft_round_from_pick_number,
    generate_ai_audio,
    return_first_matches,
)


class AIPlayerDraft:
    """AI Player Draft Class."""

    def __init__(self):
        """Initialize the class."""
        self.ffplay_process = None

    def play_audio(self, audio):
        """Play audio file and return the process object."""
        print("\n...playing audio message\n")
        args = ["ffplay", "-autoexit", "-", "-nodisp"]
        self.ffplay_process = subprocess.Popen(
            args=args,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.ffplay_process.stdin.write(audio)  # type: ignore
        self.ffplay_process.stdin.close()  # type: ignore

        print("\n...done with play audio\n")

    def display_player_splash_screen(
        self, player_name, player_image_url, partial_func, **stats
    ):
        """Display player splash screen with professional graphics."""
        # Create the Tkinter window for each player
        root = tk.Tk()
        root.title(f"{player_name} - NFL Player Stats - Splash Screen")

        # Add parallel partial function call
        def _run_function():
            """Wrap function."""
            threading.Thread(target=partial_func).start()

        # Set the background color based on the team name
        team_color = TEAM_COLORS.get(
            stats["Team"], "white"
        )  # Default to white if team color not found
        root.configure(background=team_color)

        # Load the image from the URL and set it as the background
        try:
            background_image = Image.open("images/nfl-draft-image.png")
            width, height = background_image.size
            background_photo = ImageTk.PhotoImage(background_image)
            background_label = tk.Label(root, image=background_photo)
            background_label.place(x=0, y=0, relwidth=1, relheight=1)
            root.geometry(f"{width}x{height}")  # Set the size of the window
        except Exception as e:
            print("Error loading background image:", e)

        # Fetch the player image from the online URL using PIL
        player_image = Image.open(requests.get(player_image_url, stream=True).raw)
        player_image = player_image.resize(
            (200, 200)
        )  # Resize the image to fit the screen
        player_photo = ImageTk.PhotoImage(player_image)

        # Create a Label widget to display the player image with a border
        player_image_label = tk.Label(root, image=player_photo, bd=5, relief=tk.RAISED)
        player_image_label.pack(pady=20)

        # Add labels to display player name and team in bold font
        player_name_label = tk.Button(
            root,
            text=player_name,
            font=("Helvetica", 24, "bold"),
            fg="white",
            bg=team_color,
            command=_run_function,
        )
        player_name_label.pack(pady=10)

        team_label = tk.Label(
            root,
            text=stats["Team"],
            font=("Helvetica", 18, "bold"),
            fg="white",
            bg=team_color,
        )
        team_label.pack(pady=10)

        # Prepare the stats to display as a formatted string
        stats_text = "\n".join([f"{key}: {value}" for key, value in stats.items()])

        # Add labels to display player stats with sporty font style
        stats_label = tk.Label(
            root, text=stats_text, font=("Helvetica", 14), bg=team_color, fg="white"
        )
        stats_label.pack(pady=20)

        def close_splash_screen():
            # Kill the ffplay process if it is running
            if self.ffplay_process and self.ffplay_process.poll() is None:
                print("\n...closing audio\n")
                self.ffplay_process.kill()

            print("\n...closing dsiplay screen\n")
            root.destroy()

        # Bind the window's close event (clicking the exit button)
        # to close_splash_screen
        root.protocol("WM_DELETE_WINDOW", close_splash_screen)
        print("\n...splash screen is displayed\n")

        # Start the Tkinter main loop
        root.update()
        root.mainloop()

    def generate_and_play_ai_audio(self, my_pick, prior_picks, number_of_teams=10):
        """Generate and play ai audio."""
        chat_gpt_message = chat_gpt_draft_message(
            my_pick[PLAYER_INFO + USEFUL_STATS],
            (
                prior_picks.iloc[-(number_of_teams - 1) :][  # noqa: E203
                    PLAYER_INFO + USEFUL_STATS
                ]
            ),
            round_picked=draft_round_from_pick_number(
                len(prior_picks) + 1, number_of_teams
            ),
            overall_pick=len(prior_picks) + 1,
        )
        script = chat_gpt_message["choices"][0]["message"]["content"]  # type: ignore
        print(script)
        audio = generate_ai_audio(script, voice_name=VOICE_NAME)
        self.play_audio(audio)

        return audio

    def draft_loop(
        self, rankings: pd.DataFrame, drafted_players: Union[pd.DataFrame, None] = None
    ) -> None:
        """Inner loop where we draft."""
        done_drafting = False
        current_draft_board = rankings.copy()
        if drafted_players is None:
            drafted_df: pd.DataFrame = pd.DataFrame(columns=current_draft_board.columns)
        else:
            drafted_df = drafted_players
        while done_drafting is not True:
            current_draft_board.to_csv("backup.csv", index=False)
            drafted_df.to_csv("drafted_backup.csv", index=False)
            my_turn = False
            done_drafting = False
            drafted = ""

            (
                current_draft_board.set_index("rank")[
                    ["name", "team", "position", "FantasyPoints"]
                ]
                .groupby("position")
                .apply(lambda x: print(x.head()))  # type: ignore
            )

            drafted = input("-->who has been drafted\n")

            if len(drafted) > 1:
                drafted_series = clean_player_name_col(pd.Series(drafted.split(",")))

                drafted_df = pd.concat(
                    [
                        drafted_df,
                        current_draft_board.loc[
                            return_first_matches(current_draft_board, drafted_series)
                        ],
                    ]
                )

                current_draft_board = current_draft_board.loc[
                    ~return_first_matches(current_draft_board, drafted_series)
                ]

            best_at_pos = current_draft_board.drop_duplicates("position", keep="first")

            print(
                best_at_pos[["rank", "name", "team", "position"]].reset_index(drop=True)
            )

            my_turn = input("\n-->my turn?\n")

            if my_turn:
                my_pick = -1
                while my_pick not in {0, 1, 2, 3}:
                    my_pick = input("\n-->which row to draft: 0, 1, 2, 3\n")
                    try:
                        my_pick = int(my_pick)
                    except Exception:
                        print("not an int")

                my_pick_row = best_at_pos.iloc[my_pick]

                player_name = my_pick_row["name"]
                player_image_url = my_pick_row["PhotoUrl"]

                generate_audio_partial = partial(
                    self.generate_and_play_ai_audio,
                    my_pick=my_pick_row,
                    prior_picks=drafted_df,
                )

                stats = {
                    "Height": my_pick_row["Height"],
                    "Weight": my_pick_row["Weight"],
                    "Position": my_pick_row["position"],
                    "Team": my_pick_row["team"],
                    "ADP": my_pick_row["AverageDraftPosition"],
                    "College": my_pick_row["College"],
                }

                self.display_player_splash_screen(
                    player_name, player_image_url, generate_audio_partial, **stats
                )

                current_draft_board = current_draft_board.loc[
                    ~return_first_matches(
                        current_draft_board, pd.Series(my_pick_row["clean_name"])
                    )
                ]

            done_drafting = input("\n-->done drafting?\n") == "True"
