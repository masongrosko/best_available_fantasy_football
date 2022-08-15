"""Create a draft rating."""

from pathlib import Path
import re
import datetime
import uuid
import matplotlib.pyplot as plt

from best_available_fantasy_football.rankings_extraction import (
    BDGEDraftOrderExtractor,
    ManualDraftOrderExtractor,
)


def main():
    """Sample script."""
    draft_picks = Path("rankings/draft_day/2022-08-13.csv")
    bdge_ratings = Path("rankings/bdge_rankings/2022-08-13/rankings.html")
    reports_path = Path("docs/content/docs/reports/husky_supreme/draft_reports")

    bdge_table = BDGEDraftOrderExtractor().extract_draft_order(bdge_ratings)
    draft_table = ManualDraftOrderExtractor().extract_draft_order(draft_picks)

    bdge_table["Name"] = (
        bdge_table["Name"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_")
        .str.replace(r"\W", "")
    )
    draft_table["original_name"] = draft_table["pick"]
    draft_table["pick"] = (
        draft_table["pick"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_")
        .str.replace(r"\W", "")
    )

    merged = bdge_table.merge(draft_table, how="outer", left_on="Name", right_on="pick")

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
        # "bdge_diff",
        # "adp_diff",
    }

    grades = {
        "A+": (10, "![A+](/images/draft_grades/a_plus.png)"),
        "A": (0, "![A](/images/draft_grades/a.png)"),
        "B": (-10, "![B](/images/draft_grades/b.png)"),
        "C": (-20, "![C](/images/draft_grades/c.png)"),
        "D": (-30, "![D](/images/draft_grades/d.png)"),
        "F": (-40, "![F](/images/draft_grades/f.png)"),
    }

    def get_grade(score, grades=grades):
        """Get grade letter from score."""
        for grade in grades.items():
            if score > grade[1][0]:
                return f"{grade[0]}\n\n{grade[1][1]}"
        return "F"

    groups = merged.groupby("drafter")
    round_len = len(groups)
    for drafter, details in groups:
        report = []

        report.append("## Overall Rating")
        report.append("### Mason")
        report.append(f"{get_grade(details['bdge_diff'].mean())}")
        fig_name = f"{uuid.uuid4()}.png"
        details.reset_index()["bdge_diff"].plot.bar(
            color=(details["bdge_diff"] > 0).map({True: "tab:blue", False: "tab:orange"})
        ).get_figure().savefig(
            reports_path / fig_name
        )
        plt.cla()
        report.append(f"![mason_rating_viz](../{fig_name})")

        report.append("### ADP")
        report.append(f"{get_grade(details['adp_diff'].mean())}")
        fig_name = f"{uuid.uuid4()}.png"
        details.reset_index()["adp_diff"].plot.bar(
            color=(details["adp_diff"] > 0).map({True: "tab:blue", False: "tab:orange"})
        ).get_figure().savefig(
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
                great_picks[["original_name", "Overall Rank", "pick_number"]]
                .rename(columns=clean_names)
                .reset_index(drop=True)
                .to_html()
            )

        report.append("## Reach picks - Mason")
        reach_picks = details.loc[details["bdge_diff"] < (-1 * round_len)]
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

        report.append("## Deep cut (BAD) picks")
        deep_cut_picks = details.loc[details["Name"].isna(), "original_name"].to_list()
        report.append(
            f"Of the {len(details)} players drafted by {drafter}, "
            f"{len(deep_cut_picks)} {'picks' if len(deep_cut_picks) != 1 else 'pick'} "
            f"{deep_cut_picks} {'were' if len(deep_cut_picks) > 1 else 'was'} "
            f"not even found in the provided rankings as a viable candidate!"
        )

        report.append("## Pick by pick breakdown")

        for pick in details.iterrows():
            pick_details = pick[1]

            report.append(
                f"### {pick_details['original_name']} - {pick_details['pick_number']}"
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
