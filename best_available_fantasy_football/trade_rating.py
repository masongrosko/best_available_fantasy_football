"""Create a trade rating."""

from pathlib import Path
import datetime
import re
import pandas as pd

from best_available_fantasy_football.rankings_extraction import (
    BDGEDraftOrderExtractor,
)


def main():
    """Sample script."""
    trades_csv = Path("trades/husky-supreme-2022.csv")
    bdge_ratings = Path("rankings/bdge_rankings/2022-08-13/rankings.html")
    reports_path = Path("docs/content/docs/reports/husky_supreme/trade_reports")

    bdge_table = BDGEDraftOrderExtractor().extract_draft_order(bdge_ratings)

    trades = pd.read_csv(trades_csv, index_col=0)
    trades = trades.loc[::-1]

    bdge_table["Name"] = (
        bdge_table["Name"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_")
        .str.replace(r"\W", "")
    )

    trades["original_names_a_to_b"] = trades["traded_a_to_b"]
    trades["original_names_b_to_a"] = trades["traded_b_to_a"]

    trades["traded_a_to_b"] = (
        trades["traded_a_to_b"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_")
        .str.replace(r"\W", "")
    )
    trades["traded_b_to_a"] = (
        trades["traded_b_to_a"]
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_")
        .str.replace(r"\W", "")
    )

    merged = trades.merge(
        bdge_table.add_suffix("_a_to_b"),
        left_on="traded_a_to_b",
        right_on="Name_a_to_b",
    )
    merged = merged.merge(
        bdge_table.add_suffix("_b_to_a"),
        left_on="traded_b_to_a",
        right_on="Name_b_to_a",
    )

    clean_names = {
        "original_names_b_to_a": "Name",
        "original_names_a_to_b": "Name",
        "Positional Rank_b_to_a": "Positional Rank",
        "Positional Rank_a_to_b": "Positional Rank",
        "Overall Rank_b_to_a": "Overall Rank",
        "Overall Rank_a_to_b": "Overall Rank",
        "ADP_b_to_a": "ADP",
        "ADP_a_to_b": "ADP",
    }

    grades = {
        "A+": (5, "![A+](/images/draft_grades/a_plus.png)"),
        "A": (0, "![A](/images/draft_grades/a.png)"),
        "B": (-5, "![B](/images/draft_grades/b.png)"),
        "C": (-10, "![C](/images/draft_grades/c.png)"),
        "D": (-15, "![D](/images/draft_grades/d.png)"),
        "F": (-20, "![F](/images/draft_grades/f.png)"),
    }

    def get_grade(score, grades=grades):
        """Get grade letter from score."""
        for grade in grades.items():
            if score > grade[1][0]:
                return f"{grade[0]}\n\n{grade[1][1]}"
        return "F"

    report = []
    groups = merged.groupby("trade_id")
    for trade_id, details in groups:

        report.append(f"## Trade {trade_id} made on {details['date'].unique()[0]}")
        report.append(f"{details['trader_a'].unique()[0]} receives the following:")
        report.append(
            details[
                [
                    "original_names_b_to_a",
                    "Positional Rank_b_to_a",
                    "Overall Rank_b_to_a",
                    "ADP_b_to_a",
                ]
            ].rename(columns=clean_names)
            .to_html()
        )

        report.append(f"{details['trader_b'].unique()[0]} receives the following:")
        report.append(
            details[
                [
                    "original_names_a_to_b",
                    "Positional Rank_a_to_b",
                    "Overall Rank_a_to_b",
                    "ADP_a_to_b",
                ]
            ].rename(columns=clean_names)
            .to_html()
        )

    report_location = reports_path / f"trade_report.md"
    if not report_location.exists():
        with open(report_location, "w") as f:
            f.write(
                re.sub(
                    r"\n\s+",
                    "\n",
                    f"""
                    ---
                    title: "Trade Report"
                    description: "2022 Trade Reports"
                    weight: 50
                    ---
                    """,
                )
            )
    with open(report_location, "a") as f:
        f.write(f"#### Trade review as of {datetime.datetime.now().date()}\n")
        f.write("\n\n".join(report).replace('border="1"', ""))


if __name__ == "__main__":
    main()
