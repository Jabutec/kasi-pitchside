from datetime import date
from typing import Callable


def transform_standing_row(
    raw: dict,
    season_id: int,
    matchday: int,
    team_id_resolver: Callable[[str], int],
    recorded_date: date | None = None,
):

    return {
        "season_id": season_id,
        "team_id": team_id_resolver(raw["team"]),
        "matchday": matchday,
        "position": raw["rank"],
        "points": raw["points"],
        "played": raw["played"],
        "wins": raw["wins"],
        "draws": raw["draws"],
        "losses": raw["losses"],
        "goals_for": raw["goals_for"],
        "goals_against": raw["goals_against"],
        "goal_difference": raw["goal_difference"],
        "recorded_date": recorded_date or date.today(),
    }


def transform_standings(
    raw_standings: list[dict],
    season_id: int,
    matchday: int,
    team_id_resolver: Callable[[str], int],
    recorded_date: date | None = None,
) -> list[dict]:
    """Transform a full parse_standings() list into STANDING_SNAPSHOT dicts."""
    return [
        transform_standing_row(row, season_id, matchday, team_id_resolver, recorded_date)
        for row in raw_standings
    ]