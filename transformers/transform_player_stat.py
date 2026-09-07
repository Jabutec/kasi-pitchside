from typing import Callable


def transform_player_stat(
    raw: dict,
    match_id: int,
    team_id_resolver: Callable[[str], int],
    player_id_resolver: Callable[[str, int], int],
) -> dict:
    
    team_id = team_id_resolver(raw["team_name"])
    player_id = player_id_resolver(raw["player_name"], team_id)

    return {
        "match_id": match_id,
        "player_id": player_id,
        "team_id": team_id,
        "goals": raw.get("goals", 0),
        "assists": raw.get("assists", 0),
        "shots": raw.get("shots", 0),
        "minutes_played": raw.get("minutes_played", 0),
        "motm": raw.get("motm", False),
        "saves": raw.get("saves", 0),
        "goals_conceded": raw.get("goals_conceded", 0),
        "clean_sheet": raw.get("clean_sheet", False),
        "yellow_cards": raw.get("yellow_cards", 0),
        "red_cards": raw.get("red_cards", 0),
    }


def transform_player_stats(
    raw_stats: list[dict],
    match_id: int,
    team_id_resolver: Callable[[str], int],
    player_id_resolver: Callable[[str, int], int],
) -> list[dict]:
    """Transform a full list of raw player-match-stat dicts (one match's worth)."""
    return [
        transform_player_stat(raw, match_id, team_id_resolver, player_id_resolver)
        for raw in raw_stats
    ]