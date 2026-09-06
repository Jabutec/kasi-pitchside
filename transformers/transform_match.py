"""
transform_match.py — raw fixture/result dict -> MATCH dict.

MATCHDAY CAVEAT (read before using): PSL's fixtures/results pages group
matches by date, not by an explicit round number — neither parse_fixtures()
nor parse_results() has a real "Matchday N" value to give us. True round
numbers likely live on individual match detail pages, which are still
blocked pending the JS-render check.

Until that's unblocked, matchday is derived as a per-team-pair occurrence
counter (1st meeting this season = 1, 2nd meeting = 2) — this is NOT the
real PSL round number, but it correctly satisfies the MATCH table's
uniqueness constraint (season_id + home_team_id + away_team_id + matchday),
which exists to stop a duplicate fixture from being inserted twice, not
to encode the exact round. Swap this for real round numbers once match
detail pages are reachable.
"""

from datetime import date
from typing import Callable

_SEASON_START_MONTH = 7  # PSL season runs roughly Aug-May; treat Jul as the cutover


def resolve_full_date(day: str, month_abbr: str, season_start_year: int) -> date:
    """
    Combine a day+month (no year, as given by parse_fixtures/parse_results)
    with the season's start year to get a real date. PSL's season spans
    two calendar years (e.g. "2026/27" runs Aug 2026 - May 2027) — months
    Jan-Jun belong to the second half of the season and get the later year.
    """
    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    month_num = month_map[month_abbr]
    year = season_start_year if month_num >= _SEASON_START_MONTH else season_start_year + 1
    return date(year, month_num, int(day))


class MatchdayTracker:
    """
    Tracks per-team-pair occurrence counts within a single ingestion run,
    to derive the matchday placeholder described above. One instance per
    season/ingestion run — does not persist across runs, so re-running
    ingestion on the same season should query existing MATCH rows first
    to seed correct counts (not handled here — see ingest script).
    """

    def __init__(self, starting_counts: dict[tuple[str, str], int] | None = None):
        self._counts = dict(starting_counts or {})

    def next_matchday(self, home_team: str, away_team: str) -> int:
        key = (home_team, away_team)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]


def transform_match(
    raw: dict,
    season_id: int,
    season_start_year: int,
    team_id_resolver: Callable[[str], int],
    venue_id_resolver: Callable[[str], int | None],
    matchday_tracker: MatchdayTracker,
    status: str = "scheduled",
) -> dict:
    """
    Transform one raw fixture or result dict into a MATCH dict.

    Accepts either shape:
        fixture: {"home_team", "away_team", "day", "month", "time", "venue"}
        result:  {"home_team", "away_team", "home_score", "away_score",
                   "day", "month", "year", "venue"}  (from parse_results)
    """
    home_team = raw["home_team"]
    away_team = raw["away_team"]

    # parse_results() gives an explicit year; parse_fixtures() doesn't
    if "year" in raw:
        match_date = date(int(raw["year"]), _month_num(raw["month"]), int(raw["day"]))
    else:
        match_date = resolve_full_date(raw["day"], raw["month"], season_start_year)

    matchday = matchday_tracker.next_matchday(home_team, away_team)

    return {
        "season_id": season_id,
        "venue_id": venue_id_resolver(raw.get("venue")),
        "home_team_id": team_id_resolver(home_team),
        "away_team_id": team_id_resolver(away_team),
        "match_date": match_date,
        "kickoff_time": raw.get("time") if raw.get("time") not in (None, "N/A") else None,
        "matchday": matchday,
        "home_score": raw.get("home_score"),
        "away_score": raw.get("away_score"),
        "status": status,
    }


def _month_num(month_abbr: str) -> int:
    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    return month_map[month_abbr]