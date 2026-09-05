"""
crud.py — Data access layer for Kasi Pitchside database warehouse.
"""

import logging
from typing import Any, Dict
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class WarehouseCRUD:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create_season(self, season_name: str) -> int:
        """Fetch season ID or insert new record if it does not exist."""
        query = text("SELECT id FROM season WHERE name = :name")
        res = self.session.execute(query, {"name": season_name}).fetchone()
        if res:
            return res[0]

        insert_stmt = text(
            "INSERT INTO season (name) VALUES (:name) RETURNING id"
        )
        new_id = self.session.execute(
            insert_stmt, {"name": season_name}
        ).fetchone()[0]
        logger.info(f"Created season: {season_name} (id={new_id})")
        return new_id

    def get_or_create_team(self, team_name: str) -> int:
        """Fetch team ID or insert record if it does not exist."""
        if not team_name:
            raise ValueError("Team name cannot be empty when creating team record.")

        query = text("SELECT id FROM team WHERE name = :name")
        res = self.session.execute(query, {"name": team_name}).fetchone()
        if res:
            return res[0]

        insert_stmt = text(
            "INSERT INTO team (name) VALUES (:name) RETURNING id"
        )
        new_id = self.session.execute(
            insert_stmt, {"name": team_name}
        ).fetchone()[0]
        logger.info(f"Created team: {team_name} (id={new_id})")
        return new_id

    def upsert_match(self, match_data: Dict[str, Any]) -> None:
        """Safely upsert match data into the warehouse."""
        home_name = match_data.get("home_team_name") or match_data.get("home_team")
        away_name = match_data.get("away_team_name") or match_data.get("away_team")

        # 1. Resolve foreign keys for teams
        home_team_id = self.get_or_create_team(home_name)
        away_team_id = self.get_or_create_team(away_name)

        # 2. Extract match ID (fallback to composite key if missing)
        raw_id = match_data.get("match_id") or match_data.get("external_id") or match_data.get("id")
        if not raw_id or raw_id == "None":
            # Fallback unique identifier if raw payload has no match ID
            raw_id = f"m_{match_data['season_id']}_{match_data.get('matchday', 1)}_{home_team_id}_{away_team_id}"

        params = {
            "id": str(raw_id),
            "season_id": int(match_data["season_id"]),
            "matchday": int(match_data.get("matchday", 1)),
            "kickoff_time": match_data.get("kickoff_time"),
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_score": match_data.get("home_score"),
            "away_score": match_data.get("away_score"),
            "status": str(match_data.get("status", "FINISHED")).upper(),
            "venue": match_data.get("venue"),
        }

        # 3. Query targeting 'id' instead of 'external_id'
        upsert_query = text("""
            INSERT INTO match (
                id, season_id, matchday, kickoff_time,
                home_team_id, away_team_id, home_score, away_score, status, venue
            ) VALUES (
                :id, :season_id, :matchday, :kickoff_time,
                :home_team_id, :away_team_id, :home_score, :away_score, :status, :venue
            )
            ON CONFLICT (id) DO UPDATE SET
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                status = EXCLUDED.status,
                kickoff_time = EXCLUDED.kickoff_time;
        """)

        self.session.execute(upsert_query, params)