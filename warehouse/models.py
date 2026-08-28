from datetime import date, time
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# Dimensions
class Season(Base):
    __tablename__ = "season"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    matches: Mapped[List["Match"]] = relationship(back_populates="season")
    snapshots: Mapped[List["StandingSnapshot"]] = relationship(
        back_populates="season"
    )


class Venue(Base):
    __tablename__ = "venue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100))

    matches: Mapped[List["Match"]] = relationship(back_populates="venue")


class Team(Base):
    __tablename__ = "team"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_code: Mapped[Optional[str]] = mapped_column(String(10))

    players: Mapped[List["Player"]] = relationship(back_populates="team")
    home_matches: Mapped[List["Match"]] = relationship(
        foreign_keys=["Match.home_team_id"], back_populates="home_team"
    )
    away_matches: Mapped[List["Match"]] = relationship(
        foreign_keys=["Match.away_team_id"], back_populates="away_team"
    )
    snapshots: Mapped[List["StandingSnapshot"]] = relationship(
        back_populates="team"
    )


class Player(Base):
    __tablename__ = "player"
    __table_args__ = (
        CheckConstraint(
            "position IN ('GK', 'DEF', 'MID', 'FWD')",
            name="ck_player_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("team.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[Optional[str]] = mapped_column(String(10))
    yellow_card: Mapped[int] = mapped_column(Integer, default=0)
    red_card: Mapped[int] = mapped_column(Integer, default=0)

    team: Mapped["Team"] = relationship(back_populates="players")
    stats: Mapped[List["PlayerMatchStat"]] = relationship(
        back_populates="player"
    )


# Facts
class Match(Base):
    __tablename__ = "match"
    __table_args__ = (
        UniqueConstraint(
            "season_id", "home_team_id", "away_team_id", "matchday",
            name="uix_match_natural_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id"), nullable=False
    )
    venue_id: Mapped[Optional[int]] = mapped_column(ForeignKey("venue.id"))
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("team.id"), nullable=False
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("team.id"), nullable=False
    )
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    kickoff_time: Mapped[Optional[time]] = mapped_column(Time)
    matchday: Mapped[int] = mapped_column(Integer, nullable=False)
    home_score: Mapped[Optional[int]] = mapped_column(Integer)
    away_score: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled"
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    season: Mapped["Season"] = relationship(back_populates="matches")
    venue: Mapped[Optional["Venue"]] = relationship(back_populates="matches")
    home_team: Mapped["Team"] = relationship(
        foreign_keys=[home_team_id], back_populates="home_matches"
    )
    away_team: Mapped["Team"] = relationship(
        foreign_keys=[away_team_id], back_populates="away_matches"
    )
    player_stats: Mapped[List["PlayerMatchStat"]] = relationship(
        back_populates="match"
    )


class PlayerMatchStat(Base):
    __tablename__ = "player_match_stat"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "player_id", name="uix_pms_natural_key"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("team.id"), nullable=False
    )
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    shots: Mapped[int] = mapped_column(Integer, default=0)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    motm: Mapped[bool] = mapped_column(Boolean, default=False)
    saves: Mapped[int] = mapped_column(Integer, default=0)
    goals_conceded: Mapped[int] = mapped_column(Integer, default=0)
    clean_sheet: Mapped[bool] = mapped_column(Boolean, default=False)

    match: Mapped["Match"] = relationship(back_populates="player_stats")
    player: Mapped["Player"] = relationship(back_populates="stats")


class StandingSnapshot(Base):
    __tablename__ = "standing_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "season_id", "team_id", "matchday",
            name="uix_standing_natural_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("season.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("team.id"), nullable=False
    )
    matchday: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0)
    played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    goal_difference: Mapped[int] = mapped_column(Integer, default=0)
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)

    season: Mapped["Season"] = relationship(back_populates="snapshots")
    team: Mapped["Team"] = relationship(back_populates="snapshots")