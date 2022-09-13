"""Create a draft rating."""

import datetime
import re
import uuid
from pathlib import Path
from typing import Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from espn_api.football import League

from best_available_fantasy_football.rankings_extraction import (
    BDGEDraftOrderExtractor,
    DraftType,
    EspnDraftOrderExtractor,
    ManualDraftOrderExtractor,
)

GRADES = {
    "A+": (1, "![A+](/images/draft_grades/a_plus.png)"),
    "A": (0, "![A](/images/draft_grades/a.png)"),
    "B": (-0.5, "![B](/images/draft_grades/b.png)"),
    "C": (-1, "![C](/images/draft_grades/c.png)"),
    "D": (-1.5, "![D](/images/draft_grades/d.png)"),
    "F": (-2, "![F](/images/draft_grades/f.png)"),
}


def get_grade(
    score,
    number_of_participants,
    grades=GRADES,
):
    """Get grade letter from score."""
    grade_letter = "F"
    for grade_letter, grade_details in grades.items():
        if score > (grade_details[0] * number_of_participants):
            break
    return f"{grade_letter}\n\n{grades.get(grade_letter, ('',''))[1]}"


def presentable_headers(columns: list) -> dict:
    """Return a dict of orig columns to presentable headers."""
    return {x: " ".join([y.title() for y in x.split("_")]) for x in columns}


def husky_supreme():
    """Return the husky supreme rating."""
    draft_picks = Path("rankings/draft_day/2022-08-13.csv")
    draft_table = ManualDraftOrderExtractor().extract_draft_order(draft_picks)
    bdge_ratings = Path("rankings/bdge_rankings/2022-08-13/rankings.html")
    bdge_table = BDGEDraftOrderExtractor(DraftType.SUPERFLEX).extract_draft_order(
        bdge_ratings
    )
    reports_path = Path("docs/content/docs/reports/husky_supreme/draft_reports")

    return draft_table, bdge_table, reports_path


def grosko_and_co():
    """Return the grosko-and-co rating."""
    draft_picks = Path("rankings/draft_day/grosko_and_co.csv")
    draft_table = EspnDraftOrderExtractor().extract_draft_order(draft_picks)
    bdge_ratings = Path("rankings/bdge_rankings/2022-08-23/rankings.html")
    bdge_table = BDGEDraftOrderExtractor(DraftType.SINGLE_QB).extract_draft_order(
        bdge_ratings
    )
    reports_path = Path("docs/content/docs/reports/grosko_and_co/draft_reports")

    return draft_table, bdge_table, reports_path


def man_vs_machine() -> Tuple[pd.DataFrame, Sequence[Path], Path]:
    """Return the man-vs-machine rating."""
    draft_picks = League(league_id=1030704919, year=2022).draft
    draft_table = pd.DataFrame(
        {
            "drafter": [x.team.team_name for x in draft_picks],
            "pick": [x.playerName for x in draft_picks],
            "pick_number": [*range(len(draft_picks))],
        }
    )
    ratings = list(
        Path("../espn_best_ball/espn_best_ball/draft/draft_order").glob("*csv")
    )
    reports_path = Path("docs/content/docs/reports/man_vs_machine/draft_reports")

    return draft_table, ratings, reports_path


def _clean_player_name_col(player_name_col: pd.Series) -> pd.Series:
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


def report_per_ranking():
    """Write out a report per ranking provided."""
    # Prep tables
    pd.options.display.float_format = "{:,.0f}".format

    # Grab data
    draft_table, ratings, reports_path = man_vs_machine()

    # Clean draft_table
    draft_table["name"] = draft_table["pick"].copy()
    draft_table["pick"] = _clean_player_name_col(draft_table["pick"])

    for rating in ratings:
        # Read in rating
        rater = rating.name.split(".")[0]
        rating_df = pd.read_csv(rating)

        # Create images folder
        images_path = reports_path / "images" / rater
        for leftover_file in list(images_path.glob("*")):
            leftover_file.unlink()
        images_path.rmdir() if images_path.exists() else ...
        images_path.mkdir(parents=True)

        # Clean rating
        rating_df = rating_df.dropna(how="all").copy()
        rating_df["pick"] = (
            rating_df["player_first_name"].str.lower()
            + "_"
            + rating_df["player_last_name"].str.lower()
        )
        rating_df["pick"] = _clean_player_name_col(rating_df["pick"])
        rating_df = rating_df.drop_duplicates(subset="pick", keep="first")

        # Merge draft to rating
        merged = draft_table.merge(rating_df, how="left", on="pick")
        merged = merged.sort_values("pick_number")

        # Create pick diff from value
        merged["overall_delta"] = merged["pick_number"] - merged["overall_rank"]

        # Calculate round_picked
        merged["round_picked"] = (
            merged["pick_number"] / merged["drafter"].nunique()
        ).apply(np.floor) + 1

        # Create report to write to
        report = []

        # Drafter scores
        drafter_scores = (
            merged.groupby("drafter")
            .agg(
                Rating=(
                    "overall_delta",
                    lambda x: get_grade(x.mean(), merged["drafter"].nunique()).split(
                        "\n"
                    )[0],
                ),
                Mean=("overall_delta", "mean"),
                Median=("overall_delta", "median"),
                Min=("overall_delta", "min"),
                Max=("overall_delta", "max"),
                Missing=("overall_delta", lambda x: x.isna().sum()),
            )
            .sort_values("Mean", ascending=False)
        )
        drafter_scores.index = drafter_scores.index.rename("Drafter")
        fig_name = f"{uuid.uuid4()}.png"
        plot_to_make = drafter_scores["Mean"]
        plot_to_make.plot.bar(
            color=(drafter_scores["Mean"] > 0).map(
                {True: "tab:blue", False: "tab:orange"}
            ),
            alpha=0.75,
            rot=90,
        ).get_figure()  # type: ignore
        plt.ylabel("Mean Delta")
        plt.tight_layout()
        plt.savefig(images_path / fig_name)
        plt.cla()
        report.append(f"![{rater}_drafter_scores](../images/{rater}/{fig_name})")
        report.append(drafter_scores.reset_index().to_html(index=False))

        # Rate each players draft based on rating
        groups = merged.groupby("drafter")
        round_len = len(groups)
        for drafter, details in groups:
            # Header
            report.append(f"## {drafter}")

            # Overall rating
            report.append(
                "### Overall Rating "
                f"{{#overall-rating-{str(drafter).lower().replace(' ', '-')}}}"
            )
            report.append(f"{get_grade(details['overall_delta'].mean(), round_len)}")
            fig_name = f"{uuid.uuid4()}.png"
            plot_to_make = details.reset_index()["overall_delta"]
            plot_to_make.index += 1
            plot_to_make.plot.bar(
                color=(details["overall_delta"] > 0).map(
                    {True: "tab:blue", False: "tab:orange"}
                ),
                alpha=0.75,
                rot=0,
            ).get_figure()  # type: ignore
            plt.ylabel("Overall Delta")
            plt.xlabel("Pick Number")
            plt.tight_layout()
            plt.savefig(images_path / fig_name)
            plt.cla()
            report.append(
                f"![{rater}_rating_of_{drafter}_viz](../images/{rater}/{fig_name})"
            )

            # Great picks
            report.append(
                "### Great picks "
                f"{{#great-picks-{str(drafter).lower().replace(' ', '-')}}}"
            )
            report.append('{{< details "Great picks" >}}')

            great_picks = details.loc[details["overall_delta"] > round_len]
            if len(great_picks) == 0:
                report.append("No great picks found")
            else:
                report.append(
                    f"Of the {len(details)} players drafted by {drafter}, "
                    f"{len(great_picks)} "
                    f"{'picks' if len(great_picks) != 1 else 'pick'} "
                    f"{'were' if len(great_picks) != 1 else 'was'} "
                    f"picked more than a full round later than expected."
                )
                report.append(
                    great_picks[
                        [
                            "round_picked",
                            "name",
                            "overall_rank",
                            "pick_number",
                            "overall_delta",
                        ]
                    ]
                    .rename(columns=presentable_headers(list(great_picks)))
                    .to_html(index=False)
                )

            report.append("{{< /details >}}")

            # Reach picks
            report.append(
                "### Reach picks "
                f"{{#reach-picks-{str(drafter).lower().replace(' ', '-')}}}"
            )
            report.append('{{< details "Reach picks" >}}')

            reach_picks = details.loc[details["overall_delta"] < (-1 * round_len)]
            if len(reach_picks) == 0:
                report.append("No reach picks found")
            else:
                report.append(
                    f"Of the {len(details)} players drafted by {drafter}, "
                    f"{len(reach_picks)} "
                    f"{'picks' if len(reach_picks) != 1 else 'pick'} "
                    f"{'were' if len(reach_picks) != 1 else 'was'} "
                    f"picked more than a full round earlier than expected."
                )
                report.append(
                    reach_picks[
                        [
                            "round_picked",
                            "name",
                            "overall_rank",
                            "pick_number",
                            "overall_delta",
                        ]
                    ]
                    .rename(columns=presentable_headers(list(reach_picks)))
                    .to_html(index=False)
                )

            report.append("{{< /details >}}")

            # Unrated picks
            report.append(
                "### Unrated picks "
                f"{{#unrated-picks-{str(drafter).lower().replace(' ', '-')}}}"
            )
            report.append('{{< details "Unrated picks" >}}')

            unrated_picks = details.loc[details["overall_rank"].isna()]
            if len(unrated_picks) == 0:
                report.append("No unrated picks")
            else:
                report.append(
                    f"Of the {len(details)} players drafted by {drafter}, "
                    f"{len(unrated_picks)} "
                    f"{'picks' if len(unrated_picks) != 1 else 'pick'} "
                    f"{'were' if len(unrated_picks) != 1 else 'was'} "
                    f"not rated by {rater}."
                )
                report.append(
                    unrated_picks[
                        [
                            "round_picked",
                            "name",
                            "pick_number",
                        ]
                    ]
                    .rename(columns=presentable_headers(list(unrated_picks)))
                    .to_html(index=False)
                )

            report.append("{{< /details >}}")

            # Pick by pick breakdown
            report.append(
                "### Pick by pick breakdown "
                f"{{#pick-by-pick-breakdown-{str(drafter).lower().replace(' ', '-')}}}"
            )
            report.append('{{< details "Pick by pick breakdown" >}}')

            for pick in details.iterrows():
                pick_details = pick[1]

                report.append(
                    '{{< details "'
                    f"{int(pick_details['round_picked'])}: "
                    f"{pick_details['name']}"
                    '" >}}'
                )

                columns = [
                    "name",
                    "team_name",
                    "pick_number",
                    "overall_rank",
                    "position_rank",
                    "overall_delta",
                ]
                columns = [x for x in columns if x in pick_details.index]
                report.append(
                    pick_details[columns]
                    .to_frame()
                    .T.rename(columns=presentable_headers(list(pick_details.index)))
                    .to_html(index=False)
                )

                better_picks = merged.loc[
                    (
                        merged["overall_rank"].astype(float)
                        < (
                            float(pick_details["overall_rank"])
                            if pick_details["overall_rank"]
                            == pick_details["overall_rank"]
                            else float(pick_details["pick_number"])
                        )
                    )
                    & (merged["pick_number"] > pick_details["pick_number"])
                ]
                better_picks = better_picks.sort_values("overall_rank")
                better_position_picks = merged.loc[
                    (
                        merged["overall_rank"].astype(float)
                        < (
                            float(pick_details["overall_rank"])
                            if pick_details["overall_rank"]
                            == pick_details["overall_rank"]
                            else float(pick_details["pick_number"])
                        )
                    )
                    & (merged["pick_number"] > pick_details["pick_number"])
                    & (merged["position"] == str(pick_details["position"]))
                ]
                better_position_picks = better_position_picks.sort_values(
                    "overall_rank"
                )

                if len(better_picks) > 0:
                    report.append(
                        '{{< details "Picks on the board '
                        'that would have been better" >}}'
                    )
                    report.append(
                        better_picks[["name", "overall_rank", "pick_number"]]
                        .rename(columns=presentable_headers(list(better_picks)))
                        .to_html(index=False)
                    )
                    report.append("{{< /details >}}")
                else:
                    report.append("This was the best pick available!")

                if len(better_position_picks) > 0:
                    report.append(
                        '{{< details "Picks on the board that '
                        'were better in that position!" >}}'
                    )
                    report.append(
                        better_position_picks[
                            [
                                "name",
                                "position_rank",
                                "overall_rank",
                                "pick_number",
                            ]
                        ]
                        .rename(
                            columns=presentable_headers(list(better_position_picks))
                        )
                        .to_html(index=False)
                    )
                    report.append("{{< /details >}}")

                report.append("{{< /details >}}")

            report.append("{{< /details >}}")

        # Write out report
        report_location = reports_path / f"{rater}_draft_reports.md"
        with open(report_location, "w") as f:
            f.write(
                re.sub(
                    r"\n\s+",
                    "\n",
                    f"""---
                    title: "{rater} Draft Reports"
                    description: "2022 Draft Reports according to {rater}"
                    weight: 50
                    ---

                    """,
                )
            )
        with open(report_location, "a") as f:
            f.write(
                "\n\n".join(report)
                .replace('border="1"', "")
                .replace('style="text-align: right;"', 'style="text-align: left;"')
            )


def main():
    """Sample script."""
    # draft_table, bdge_table, reports_path = husky_supreme()
    draft_table, bdge_table, reports_path = grosko_and_co()

    bdge_table["Name"] = _clean_player_name_col(bdge_table["Name"])
    draft_table["original_name"] = draft_table["pick"].copy()
    draft_table["pick"] = _clean_player_name_col(draft_table["pick"])

    merged = bdge_table.merge(draft_table, how="outer", left_on="Name", right_on="pick")
    merged = merged.sort_values(by="pick_number")

    merged["bdge_diff"] = merged["pick_number"] - merged["Overall Rank"].astype(float)
    merged["adp_diff"] = merged["pick_number"] - merged["ADP"].astype(float)

    clean_names = {
        # "Overall Rank",
        # "Positional Rank",
        # "Name",
        # "Team",
        # "ADP",
        # "ADP Delta",
        "pick_number": "Pick Number",
        # "pick",
        "drafter": "Drafter",
        "original_name": "Player Name",
        "bdge_diff": "Overall Delta",
        "adp_diff": "ADP Delta",
    }

    groups = merged.groupby("drafter")
    round_len = len(groups)
    for drafter, details in groups:
        report = []

        report.append("## Overall Rating")
        report.append("### Mason")
        report.append(f"{get_grade(details['bdge_diff'].mean(), round_len)}")
        fig_name = f"{uuid.uuid4()}.png"
        details.reset_index()["bdge_diff"].plot.bar(
            color=(details["bdge_diff"] > 0).map(
                {True: "tab:blue", False: "tab:orange"}
            )
        ).get_figure().savefig(  # type: ignore
            reports_path / fig_name
        )
        plt.cla()
        report.append(f"![mason_rating_viz](../{fig_name})")

        report.append("### ADP")
        report.append(f"{get_grade(details['adp_diff'].mean(), round_len)}")
        fig_name = f"{uuid.uuid4()}.png"
        details.reset_index()["adp_diff"].plot.bar(
            color=(details["adp_diff"] > 0).map({True: "tab:blue", False: "tab:orange"})
        ).get_figure().savefig(  # type: ignore
            reports_path / fig_name
        )
        plt.cla()
        report.append(f"![adp_rating_viz](../{fig_name})")

        report.append("## Great picks - Mason")
        great_picks = details.loc[details["bdge_diff"] > round_len]
        if len(great_picks) == 0:
            report.append("No great picks found")
        else:
            report.append(
                f"Of the {len(details)} players drafted by {drafter}, "
                f"{len(great_picks)} {'picks' if len(great_picks) != 1 else 'pick'} "
                f"{great_picks['original_name'].to_list()} "
                f"{'were' if len(great_picks) != 1 else 'was'} "
                f"picked more than a full round later than expected."
            )
            report.append(
                great_picks[["original_name", "Overall Rank", "pick_number"]]
                .rename(columns=clean_names)
                .reset_index(drop=True)
                .to_html()
            )

        report.append("## Great picks - ADP")
        great_picks = details.loc[details["adp_diff"] > round_len]
        if len(great_picks) == 0:
            report.append("No great picks found")
        else:
            report.append(
                f"Of the {len(details)} players drafted by {drafter}, "
                f"{len(great_picks)} {'picks' if len(great_picks) != 1 else 'pick'} "
                f"{great_picks['original_name'].to_list()} "
                f"{'were' if len(great_picks) != 1 else 'was'} "
                f"picked more than a full round later than expected."
            )
            report.append(
                great_picks[["original_name", "ADP", "pick_number"]]
                .rename(columns=clean_names)
                .reset_index(drop=True)
                .to_html()
            )

        report.append("## Reach picks - Mason")
        reach_picks = details.loc[details["bdge_diff"] < (-1 * round_len)]
        if len(reach_picks) == 0:
            report.append("No reach picks found")
        else:
            report.append(
                f"Of the {len(details)} players drafted by {drafter}, "
                f"{len(reach_picks)} {'picks' if len(reach_picks) != 1 else 'pick'} "
                f"{reach_picks['original_name'].to_list()} "
                f"{'were' if len(reach_picks) != 1 else 'was'} "
                f"picked more than a full round earlier than expected."
            )
            report.append(
                reach_picks[["original_name", "Overall Rank", "pick_number"]]
                .rename(columns=clean_names)
                .reset_index(drop=True)
                .to_html()
            )

        report.append("## Reach picks - ADP")
        reach_picks = details.loc[details["adp_diff"] < (-1 * round_len)]
        if len(reach_picks) == 0:
            report.append("No reach picks found")
        else:
            report.append(
                f"Of the {len(details)} players drafted by {drafter}, "
                f"{len(reach_picks)} {'picks' if len(reach_picks) != 1 else 'pick'} "
                f"{reach_picks['original_name'].to_list()} "
                f"{'were' if len(reach_picks) != 1 else 'was'} "
                f"picked more than a full round earlier than expected."
            )
            report.append(
                reach_picks[["original_name", "ADP", "pick_number"]]
                .rename(columns=clean_names)
                .reset_index(drop=True)
                .to_html()
            )

        report.append("## Deep cut (BAD) picks")
        deep_cut_picks = details.loc[details["Name"].isna(), "original_name"].to_list()
        if len(reach_picks) == 0:
            report.append("No deep cut picks found")
        else:
            report.append(
                f"Of the {len(details)} players drafted by {drafter}, "
                f"{len(deep_cut_picks)} "
                f"{'picks' if len(deep_cut_picks) != 1 else 'pick'} "
                f"{deep_cut_picks} {'were' if len(deep_cut_picks) > 1 else 'was'} "
                f"not even found in the provided rankings as a viable candidate!"
            )

        report.append("## Pick by pick breakdown")

        for pick in details.iterrows():
            pick_details = pick[1]

            report.append(
                f"### {pick_details['original_name']} - {pick_details['pick_number']}"
            )

            report.append(
                pick_details[
                    [
                        "original_name",
                        "Team",
                        "pick_number",
                        "Overall Rank",
                        "ADP",
                        "Positional Rank",
                        "bdge_diff",
                        "adp_diff",
                    ]
                ]
                .rename(clean_names)
                .to_frame()
                .T.to_html()
            )

            better_picks = merged.loc[
                (
                    merged["Overall Rank"].astype(float)
                    < (
                        float(pick_details["Overall Rank"])
                        if pick_details["Overall Rank"] == pick_details["Overall Rank"]
                        else float(pick_details["pick_number"])
                    )
                )
                & (merged["pick_number"] > pick_details["pick_number"])
            ]
            better_position_picks = merged.loc[
                (
                    merged["Overall Rank"].astype(float)
                    < (
                        float(pick_details["Overall Rank"])
                        if pick_details["Overall Rank"] == pick_details["Overall Rank"]
                        else float(pick_details["pick_number"])
                    )
                )
                & (merged["pick_number"] > pick_details["pick_number"])
                & (
                    merged["Positional Rank"].astype(str).str[:2]
                    == str(pick_details["Positional Rank"])[:2]
                )
            ]

            if len(better_picks) > 0:
                report.append("Picks on the board that would have been better:")
                report.append(
                    better_picks[["original_name", "Overall Rank", "pick_number"]]
                    .rename(columns=clean_names)
                    .reset_index(drop=True)
                    .to_html()
                )
            else:
                report.append("This was the best pick available!")

            if len(better_position_picks) > 0:
                report.append("Picks on the board that were better in that position!")
                report.append(
                    better_position_picks[
                        [
                            "original_name",
                            "Positional Rank",
                            "Overall Rank",
                            "pick_number",
                        ]
                    ]
                    .rename(columns=clean_names)
                    .reset_index(drop=True)
                    .to_html()
                )

        report_location = reports_path / f"{drafter}_draft_report.md"
        if not report_location.exists():
            with open(report_location, "w") as f:
                f.write(
                    re.sub(
                        r"\n\s+",
                        "\n",
                        f"""
                        ---
                        title: "{drafter} Draft Report"
                        description: "2022 Draft Report for {drafter}"
                        weight: 50
                        ---
                        """,
                    )
                )
        with open(report_location, "a") as f:
            f.write(f"#### Draft review as of {datetime.datetime.now().date()}\n")
            f.write("\n\n".join(report).replace('border="1"', ""))


if __name__ == "__main__":
    main()
