"""Database CRUD operations"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from warehouse.models import (
    Match,
    Player,
    PlayerMatchStat,
    Season,
    StandingSnapshot,
    Team,
    Venue,
)

logger = logging.getLogger(__name__)


class WarehouseCRUD:
    """High-level CRUD for the PSL warehouse."""

    def __init__(self, session: Session):
        self.session = session

    # Dimensions
    def get_or_create_team(self, name: str, short_code: Optional[str] = None) -> Team:
        team = self.session.query(Team).filter_by(name=name).first()
        if team:
            return team
        team = Team(name=name, short_code=short_code)
        self.session.add(team)
        self.session.flush()
        logger.info(f"Created team: {name} (id={team.id})")
        return team

    def get_or_create_player(
        self, name: str, team_id: int, position: Optional[str] = None
    ) -> Player:
        player = (
            self.session.query(Player)
            .filter_by(name=name, team_id=team_id)
            .first()
        )
        if player:
            return player
        player = Player(name=name, team_id=team_id, position=position)
        self.session.add(player)
        self.session.flush()
        logger.info(f"Created player: {name} (id={player.id})")
        return player

    def get_or_create_season(self, name: str) -> Season:
        season = self.session.query(Season).filter_by(name=name).first()
        if season:
            return season
        season = Season(name=name)
        self.session.add(season)
        self.session.flush()
        logger.info(f"Created season: {name} (id={season.id})")
        return season

    def get_or_create_venue(self, name: str, city: Optional[str] = None) -> Venue:
        venue = self.session.query(Venue).filter_by(name=name).first()
        if venue:
            return venue
        venue = Venue(name=name, city=city)
        self.session.add(venue)
        self.session.flush()
        logger.info(f"Created venue: {name} (id={venue.id})")
        return venue

    # Facts — upsert
    def upsert_match(self, match_data: Dict[str, Any]) -> Match:
        """Upsert MATCH on natural key, compatible with both PostgreSQL & SQLite engines."""
        bind = self.session.get_bind()
        insert_fn = sqlite_insert if bind.dialect.name == "sqlite" else pg_insert

        stmt = (
            insert_fn(Match)
            .values(**match_data)
            .on_conflict_do_update(
                index_elements=[
                    "season_id",
                    "home_team_id",
                    "away_team_id",
                    "matchday",
                ],
                set_={
                    "venue_id": match_data.get("venue_id"),
                    "match_date": match_data.get("match_date"),
                    "kickoff_time": match_data.get("kickoff_time"),
                    "home_score": match_data.get("home_score"),
                    "away_score": match_data.get("away_score"),
                    "status": match_data.get("status"),
                },
            )
        )
        self.session.execute(stmt)
        self.session.flush()

        match = (
            self.session.query(Match)
            .filter_by(
                season_id=match_data["season_id"],
                home_team_id=match_data["home_team_id"],
                away_team_id=match_data["away_team_id"],
                matchday=match_data["matchday"],
            )
            .one()
        )
        logger.info(f"Upserted match: {match.id} (status={match.status})")
        return match

    def upsert_player_stat(self, stat_data: Dict[str, Any]) -> None:
        """Upsert PLAYER_MATCH_STAT on (match_id, player_id) for PostgreSQL & SQLite."""
        bind = self.session.get_bind()
        insert_fn = sqlite_insert if bind.dialect.name == "sqlite" else pg_insert

        stmt = (
            insert_fn(PlayerMatchStat)
            .values(**stat_data)
            .on_conflict_do_update(
                index_elements=["match_id", "player_id"],
                set_={
                    "team_id": stat_data.get("team_id"),
                    "goals": stat_data.get("goals", 0),
                    "assists": stat_data.get("assists", 0),
                    "shots": stat_data.get("shots", 0),
                    "minutes_played": stat_data.get("minutes_played", 0),
                    "motm": stat_data.get("motm", False),
                    "saves": stat_data.get("saves", 0),
                    "goals_conceded": stat_data.get("goals_conceded", 0),
                    "clean_sheet": stat_data.get("clean_sheet", False),
                },
            )
        )
        self.session.execute(stmt)
        logger.info(
            f"Upserted player stat: match={stat_data['match_id']}, "
            f"player={stat_data['player_id']}"
        )
    def insert_standing_snapshot(self, snapshot_data: Dict[str, Any]) -> bool:
        """Insert STANDING_SNAPSHOT. Automatically ignores duplicates at the DB level."""
        bind = self.session.get_bind()
        insert_fn = sqlite_insert if bind.dialect.name == "sqlite" else pg_insert

        stmt = (
            insert_fn(StandingSnapshot)
            .values(**snapshot_data)
            .on_conflict_do_nothing(
                index_elements=["season_id", "team_id", "matchday"]
            )
        )
        result = self.session.execute(stmt)
        
        if result.rowcount == 0:
            logger.warning(
                f"Skipped duplicate standing snapshot: "
                f"season={snapshot_data['season_id']}, "
                f"team={snapshot_data['team_id']}, "
                f"matchday={snapshot_data['matchday']}"
            )
            return False

        logger.info(
            f"Inserted standing snapshot: "
            f"matchday={snapshot_data['matchday']}, "
            f"team={snapshot_data['team_id']}"
        )
        return True

    # Batch helpers
    def bulk_upsert_matches(self, matches: List[Dict[str, Any]]) -> None:
        """Bulk upsert matches for performance."""
        for m in matches:
            self.upsert_match(m)

    def bulk_upsert_player_stats(self, stats: List[Dict[str, Any]]) -> None:
        """Bulk upsert player stats."""
        for s in stats:
            self.upsert_player_stat(s)

    def bulk_insert_snapshots(self, snapshots: List[Dict[str, Any]]) -> None:
        """Bulk insert standing snapshots (skips duplicates individually)."""
        for snap in snapshots:
            self.insert_standing_snapshot(snap)