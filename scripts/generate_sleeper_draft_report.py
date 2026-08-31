"""Generate the 2026 report through the repository's shared report pipeline."""

from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "baff-matplotlib")
)

import pandas as pd

from best_available_fantasy_football.draft_rating import (
    _clean_player_name_col,
    create_comparison,
)
from best_available_fantasy_football.rankings_extraction import (
    DraftSharksEmbeddedADPExtractor,
    SleeperDraftOrderExtractor,
)


MANAGER_NAMES = {
    "636686945900126208": "Mason",
    "1129135186521808896": "Mike",
    "1129229805326655488": "Mackenzie",
    "1130659838989746176": "TJ",
    "1130340208676814848": "Austin",
    "1129227028848353280": "Hannah",
    "735368631902388224": "Zach",
    "637788655506960384": "Ethan",
    "731333840525737984": "Ryan",
    "1129228168029757440": "Riley",
    "1128798651033231360": "Cody",
    "731231306880528384": "Garrett",
}


def prepare_rankings(path: Path) -> pd.DataFrame:
    """Adapt the 2026 rankings CSV to create_comparison's common schema."""
    rankings = pd.read_csv(path)
    rankings["name"] = rankings["Player"]
    rankings["Name"] = _clean_player_name_col(rankings["Player"])
    rankings["Overall Rank"] = pd.to_numeric(rankings["Rank"])
    rankings["Positional Rank"] = rankings["Pos Rank"]
    rankings["position"] = rankings["Pos"]
    rankings["team_name"] = rankings["Team"]
    return rankings


def prepare_draft(picks: Path, users: Path) -> pd.DataFrame:
    """Load Sleeper through the common DraftOrderExtractor interface."""
    draft = SleeperDraftOrderExtractor(users, MANAGER_NAMES).extract_draft_order(picks)
    draft["pick"] = _clean_player_name_col(draft["pick"])
    draft["Team"] = draft["player_team"]
    return draft


def prepare_adp(path: Path) -> pd.DataFrame:
    """Adapt the current DraftSharks page to the historical ADP schema."""
    adp = DraftSharksEmbeddedADPExtractor().extract_draft_order(path)
    # DraftSharks also embeds aggregate team-QB and team-kicker rows whose names
    # collide with defenses (for example, three "Baltimore Ravens" records).
    adp = adp[adp["player_position"].isin({"QB", "RB", "WR", "TE", "K", "DEF"})]
    adp["clean_name"] = _clean_player_name_col(adp["player_name"])
    return adp.drop_duplicates(["clean_name", "player_position"], keep="first")


def save_inputs(rankings_path: Path, draft: pd.DataFrame) -> None:
    """Keep third-party input ignored while retaining our league snapshot."""
    proprietary_dir = Path("rankings/bdge_rankings/2026-08-30")
    proprietary_dir.mkdir(parents=True, exist_ok=True)
    saved_rankings = proprietary_dir / "bdge-draft-rankings-half-ppr.csv"
    if rankings_path.resolve() != saved_rankings.resolve():
        shutil.copyfile(rankings_path, saved_rankings)

    data_dir = Path("rankings/2026")
    data_dir.mkdir(parents=True, exist_ok=True)
    old_tracked_rankings = data_dir / "bdge-draft-rankings-half-ppr.csv"
    if old_tracked_rankings.exists():
        old_tracked_rankings.unlink()
    columns = [
        "pick_number",
        "round",
        "drafter",
        "sleeper_team_name",
        "original_name",
        "player_position",
        "player_team",
    ]
    draft[columns].to_csv(data_dir / "grosko-and-co-sleeper-draft.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rankings", type=Path, required=True)
    parser.add_argument("--picks", type=Path, required=True)
    parser.add_argument("--users", type=Path, required=True)
    parser.add_argument("--adp-html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--league-id", default="1389707918529540097")
    args = parser.parse_args()

    draft = prepare_draft(args.picks, args.users)
    rankings = prepare_rankings(args.rankings)
    adp = prepare_adp(args.adp_html)
    save_inputs(args.rankings, draft)

    reports_path = args.output / "draft_reports"
    reports_path.mkdir(parents=True, exist_ok=True)
    for old_report in reports_path.glob("*.md"):
        old_report.unlink()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "_index.md").write_text(
        '---\n'
        'title: "Grosko & Co. 2026 Draft Ratings"\n'
        'description: "2026 half-PPR draft ratings"\n'
        'weight: 10\n'
        '---\n',
        encoding="utf-8",
    )

    create_comparison(
        draft_table=draft,
        rankings_table=rankings,
        reports_path=reports_path,
        adp_table=adp,
        report_year=2026,
    )
    print(
        f"Generated {draft['drafter'].nunique()} reports from {len(draft)} picks "
        "using the shared report pipeline."
    )


if __name__ == "__main__":
    main()
