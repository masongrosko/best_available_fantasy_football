"""Create a draft rating."""

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
    DraftSharksADPDraftOrderExtractor,
    DraftType,
    EspnDraftOrderExtractor,
    ManualDraftOrderExtractor,
    YahooHtmlDraftOrderExtractor,
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


def husky_supreme_2023():
    """Return the husky supreme rating."""
    draft_picks = Path("rankings/draft_day/2023-08-05.html")
    draft_table = YahooHtmlDraftOrderExtractor().extract_draft_order(draft_picks)
    bdge_ratings = Path("rankings/bdge_rankings/2023-08-02/2023-08-02-clean.csv")
    bdge_table = pd.read_csv(bdge_ratings, index_col=0)
    reports_path = Path("docs/content/docs/2023/reports/husky_supreme/draft_reports")

    return draft_table, bdge_table, reports_path


def husky_supreme_2022():
    """Return the husky supreme rating."""
    draft_picks = Path("rankings/draft_day/2022-08-13.csv")
    draft_table = ManualDraftOrderExtractor().extract_draft_order(draft_picks)
    bdge_ratings = Path("rankings/bdge_rankings/2022-08-13/rankings.html")
    bdge_table = BDGEDraftOrderExtractor(DraftType.SUPERFLEX).extract_draft_order(
        bdge_ratings
    )
    reports_path = Path("docs/content/docs/2022/reports/husky_supreme/draft_reports")

    return draft_table, bdge_table, reports_path


def grosko_and_co():
    """Return the grosko-and-co rating."""
    draft_picks = Path("rankings/draft_day/grosko_and_co.csv")
    draft_table = EspnDraftOrderExtractor().extract_draft_order(draft_picks)
    bdge_ratings = Path("rankings/bdge_rankings/2022-08-23/rankings.html")
    bdge_table = BDGEDraftOrderExtractor(DraftType.SINGLE_QB).extract_draft_order(
        bdge_ratings
    )
    reports_path = Path("docs/content/docs/2022/reports/grosko_and_co/draft_reports")

    return draft_table, bdge_table, reports_path


def grosko_and_co_2023():
    """Return the grosko-and-co rating."""
    draft_picks = Path("rankings/draft_day/grosko_and_co_2023.csv")
    draft_table = EspnDraftOrderExtractor().extract_draft_order(draft_picks)
    bdge_ratings = Path("rankings/bdge_rankings/2023-08-27/2023-08-27-clean.csv")
    bdge_table = pd.read_csv(bdge_ratings, index_col=0)
    reports_path = Path("docs/content/docs/2023/reports/grosko_and_co/draft_reports")

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
    reports_path = Path("docs/content/docs/2022/reports/man_vs_machine/draft_reports")

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


def report_per_ranking(draft_table, ratings, reports_path):
    """Write out a report per ranking provided."""
    # Prep tables
    pd.options.display.float_format = "{:,.0f}".format

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


def summary_chart(merged, images_path, report):
    drafter_scores = (
        merged.groupby("drafter")
        .agg(
            Rating=(
                "overall_delta",
                lambda x: get_grade(x.mean(), merged["drafter"].nunique()).split("\n")[
                    0
                ],
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
        color=(drafter_scores["Mean"] > 0).map({True: "tab:blue", False: "tab:orange"}),
        alpha=0.75,
        rot=90,
    ).get_figure()  # type: ignore
    plt.ylabel("Mean Delta")
    plt.tight_layout()
    plt.savefig(images_path / fig_name)
    plt.cla()
    report.append(f"![summary_drafter_scores](draft_reports/images/{fig_name})")
    report.append(drafter_scores.reset_index().to_html(index=False))

    return report


def create_comparison(draft_table, rankings_table, reports_path, adp_table=None):
    """Create comparison of draft_table to some set ratings."""
    # Create images folder
    images_path = reports_path / "images"
    for leftover_file in list(images_path.glob("*")):
        leftover_file.unlink()
    images_path.rmdir() if images_path.exists() else ...
    images_path.mkdir(parents=True)

    # Merge ratings
    merged = rankings_table.merge(
        draft_table, how="outer", left_on="Name", right_on="pick"
    )
    merged = merged.sort_values(by="pick_number")
    merged["name"] = np.where(
        merged["name"].isna(), merged["original_name"], merged["name"]
    )
    merged["Name"] = np.where(merged["Name"].isna(), merged["pick"], merged["Name"])
    if adp_table is not None:
        merged = merged.merge(
            adp_table[["clean_name", "adp"]],
            how="left",
            left_on="Name",
            right_on="clean_name",
        )
        merged["ADP"] = merged["adp"].copy()
        del merged["adp"]

    merged["overall_delta"] = merged["pick_number"] - merged["Overall Rank"].astype(
        float
    )
    merged["adp_delta"] = merged["pick_number"] - merged["ADP"].astype(float)

    merged["round_picked"] = merged["round"].copy()
    merged["overall_rank"] = merged["Overall Rank"].copy()
    merged["position_rank"] = merged["Positional Rank"].copy()

    clean_names = {
        "overall_rank": "Overall Rank",
        "position_rank": "Positional Rank",
        # "Name",
        # "Team",
        # "ADP",
        "pick_number": "Pick Number",
        # "pick",
        "drafter": "Drafter",
        "original_name": "Player Name",
        "overall_delta": "Overall Delta",
        "adp_delta": "ADP Delta",
        "round_picked": "round",
    }

    # Summary report
    with open(reports_path / ".." / "_index.md") as f:
        report = f.read()

    report = [report.split("\n---\n")[0] + "\n---"]
    report = summary_chart(merged, images_path, report)

    with open(reports_path / ".." / "_index.md", "w") as f:
        f.write(
            "\n\n".join(report)
            .replace('border="1"', "")
            .replace('style="text-align: right;"', 'style="text-align: left;"')
        )

    groups = merged.groupby("drafter")
    round_len = len(groups)
    for drafter, details in groups:
        report = []
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
        report.append(f"![rating_of_{drafter}_viz](../images/{fig_name})")

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
                        "ADP",
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
                        "ADP",
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
                f"not rated by Mason."
            )
            report.append(
                unrated_picks[
                    [
                        "round_picked",
                        "name",
                        "pick_number",
                        "ADP",
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
                "ADP",
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
                        if pick_details["overall_rank"] == pick_details["overall_rank"]
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
                        if pick_details["overall_rank"] == pick_details["overall_rank"]
                        else float(pick_details["pick_number"])
                    )
                )
                & (merged["pick_number"] > pick_details["pick_number"])
                & (merged["position"] == str(pick_details["position"]))
            ]
            better_position_picks = better_position_picks.sort_values("overall_rank")

            if len(better_picks) > 0:
                report.append(
                    '{{< details "Picks on the board '
                    'that would have been better" >}}'
                )
                report.append(
                    better_picks[["name", "overall_rank", "pick_number", "ADP"]]
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
                            "ADP",
                        ]
                    ]
                    .rename(columns=presentable_headers(list(better_position_picks)))
                    .to_html(index=False)
                )
                report.append("{{< /details >}}")

            report.append("{{< /details >}}")

        report.append("{{< /details >}}")

        # Write out report
        report_location = reports_path / f"{drafter}_draft_report.md"
        with open(report_location, "w") as f:
            f.write(
                re.sub(
                    r"\n\s+",
                    "\n",
                    f"""---
                    title: "{drafter} Draft Report"
                    description: "2023 Draft Report for {drafter}"
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
                .replace(".0<", "<")
            )


def grosko_and_co_main_2023():
    """Sample script."""
    draft_table, bdge_table, reports_path = grosko_and_co_2023()
    adp_table = DraftSharksADPDraftOrderExtractor().extract_draft_order(
        "rankings/draft_sharks_adp/2023-08-27-1qb.html"
    )

    draft_table["drafter"] = draft_table["drafter"].map(  # type: ignore
        {
            "G-Unit": "Gordon",
            "Sherlock_Mahomes": "Zach",
            "Fresh_Start_-_Lam_3:23": "Mike",
            "H-TOWN": "Hannah",
            "ShakeitOffense_(Mack'sVersion)": "Mackenzie",
            "The_Gridiron_Chefs": "Austin",
            "Here_Botz": "Ryan",
            "Mason_Grosko": "Mason",
            "Team_Youngerbuehler": "Dallas",
            "Team_Rowe": "TJ",
            "Finding_Deebo": "Garrett",
            "Arby's_Roast_Beef": "Riley",
            "Joe_Buck_Yourself": "Cody",
            "We_Were_Winners_Once": "Ethan",
        }
    )

    adp_table["clean_name"] = _clean_player_name_col(adp_table["player_name"])
    bdge_table["Name"] = _clean_player_name_col(bdge_table["name"])
    bdge_table["Overall Rank"] = bdge_table.index
    bdge_table["Positional Rank"] = bdge_table["position"] + (
        bdge_table.groupby("position").cumcount() + 1
    ).astype(str)
    draft_table["original_name"] = draft_table["pick"].copy()
    draft_table["pick"] = _clean_player_name_col(draft_table["pick"])
    draft_table["Team"] = draft_table["player_team"]

    draft_table["round"] = (
        (draft_table["pick_number"].astype(int) - 1) // draft_table["drafter"].nunique()
    ) + 1

    create_comparison(
        draft_table=draft_table,
        rankings_table=bdge_table,
        reports_path=reports_path,
        adp_table=adp_table,
    )


def main_2023():
    """Sample script."""
    draft_table, bdge_table, reports_path = husky_supreme_2023()
    adp_table = DraftSharksADPDraftOrderExtractor().extract_draft_order(
        "rankings/draft_sharks_adp/2023-08-19-superflex.html"
    )

    draft_table["drafter"] = draft_table["drafter_team_name"].map(  # type: ignore
        {
            "Till The Whe...": "Kevin",
            "The Hungry H...": "Devin",
            "mAIson": "Mason",
            "SoCalZen": "Toby",
            "Dijon Moeste...": "Penner",
            "GOBBLE DEEZ": "Nick",
            "Prestige Wor...": "Shouse",
            "Bijan Mustar...": "Sam N",
            "Fields did 9/11": "Drew",
            "smell my Kupp": "Megan",
        }
    )

    adp_table["clean_name"] = _clean_player_name_col(adp_table["player_name"])
    bdge_table["Name"] = _clean_player_name_col(bdge_table["name"])
    bdge_table["Overall Rank"] = bdge_table.index
    bdge_table["Positional Rank"] = bdge_table["position"] + (
        bdge_table.groupby("position").cumcount() + 1
    ).astype(str)
    draft_table["original_name"] = draft_table["player_name"].copy()
    draft_table["pick"] = _clean_player_name_col(draft_table["player_name"])
    draft_table["Team"] = draft_table["player_team"]

    draft_table["pick_number"] = (
        (draft_table["round"].astype(int) - 1) * 10
    ) + draft_table["pick_number"]

    create_comparison(
        draft_table=draft_table,
        rankings_table=bdge_table,
        reports_path=reports_path,
        adp_table=adp_table,
    )


def main_2022():
    """Sample script."""
    # draft_table, bdge_table, reports_path = husky_supreme()
    draft_table, bdge_table, reports_path = grosko_and_co()

    bdge_table["Name"] = _clean_player_name_col(bdge_table["Name"])
    draft_table["original_name"] = draft_table["pick"].copy()
    draft_table["pick"] = _clean_player_name_col(draft_table["pick"])

    create_comparison(
        draft_table=draft_table,
        rankings_table=bdge_table,
        reports_path=reports_path,
    )
