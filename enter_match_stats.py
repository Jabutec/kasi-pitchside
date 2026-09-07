"""
enter_match_stats.py — weekly player-match-stat entry, once or twice a week.

Looks up an EXISTING match (already created by the automated fixtures/
results pipeline) rather than creating one — this tool only adds the
player-level layer on top of a match that's already in the database.

Usage:
    python enter_match_stats.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.db import get_session
from warehouse.crud import WarehouseCRUD
from warehouse.models import Match, Team
from transformers.transform_player_stat import transform_player_stat


def find_match(session, home_team_name: str, away_team_name: str):
    home = session.query(Team).filter_by(name=home_team_name).first()
    away = session.query(Team).filter_by(name=away_team_name).first()
    if not home or not away:
        return None
    return (
        session.query(Match)
        .filter_by(home_team_id=home.id, away_team_id=away.id)
        .order_by(Match.match_date.desc())
        .first()
    )


def yes_no(prompt: str) -> bool:
    return input(f"{prompt} (y/n): ").strip().lower().startswith("y")


def main() -> None:
    with get_session() as session:
        crud = WarehouseCRUD(session)

        home_team_name = input("Home team: ").strip()
        away_team_name = input("Away team: ").strip()

        match = find_match(session, home_team_name, away_team_name)
        if not match:
            print(f"\nNo match found for {home_team_name} vs {away_team_name}.")
            print("This tool only adds stats to a match that already exists —")
            print("check the fixtures/results pipeline has loaded it first.")
            return

        print(f"\nFound match: {home_team_name} vs {away_team_name} on {match.match_date} "
              f"(status={match.status}, score={match.home_score}-{match.away_score})\n")

        if not yes_no("Is this the correct match?"):
            print("Aborted.")
            return

        print("\nEnter stats one player at a time. Blank name to finish.\n")
        count = 0
        while True:
            player_name = input("Player name: ").strip()
            if not player_name:
                break

            team_name = input(f"  Team ({home_team_name}/{away_team_name}): ").strip()

            raw = {
                "player_name": player_name,
                "team_name": team_name,
                "goals": int(input("  Goals [0]: ").strip() or 0),
                "assists": int(input("  Assists [0]: ").strip() or 0),
                "shots": int(input("  Shots [0]: ").strip() or 0),
                "minutes_played": int(input("  Minutes played [90]: ").strip() or 90),
                "motm": yes_no("  Man of the match?"),
                "saves": int(input("  Saves (GK only) [0]: ").strip() or 0),
                "goals_conceded": int(input("  Goals conceded (GK only) [0]: ").strip() or 0),
                "clean_sheet": yes_no("  Clean sheet (GK only)?"),
                "yellow_cards": int(input("  Yellow cards [0]: ").strip() or 0),
                "red_cards": int(input("  Red cards [0]: ").strip() or 0),
            }

            def resolve_team_id(name: str) -> int:
                t = crud.get_or_create_team(name)
                return t.id

            def resolve_player_id(name: str, team_id: int) -> int:
                p = crud.get_or_create_player(name, team_id)
                return p.id

            stat_dict = transform_player_stat(raw, match.id, resolve_team_id, resolve_player_id)
            crud.upsert_player_stat(stat_dict)
            print(f"  Saved stats for {player_name}.\n")
            count += 1

        print(f"\nDone. {count} player stat row(s) saved for this match.")


if __name__ == "__main__":
    main()