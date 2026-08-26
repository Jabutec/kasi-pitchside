# Kasi Pitchside — PSL data pipeline ERD

## Entities

### SEASON

| Field | Type   | Notes          |
| ----- | ------ | -------------- |
| id    | int    | PK             |
| name  | string | e.g. "2026/27" |

### VENUE

| Field | Type   | Notes |
| ----- | ------ | ----- |
| id    | int    | PK    |
| name  | string |       |
| city  | string |       |

### TEAM

| Field      | Type   | Notes             |
| ---------- | ------ | ----------------- |
| id         | int    | PK                |
| name       | string |                   |
| short_code | string | e.g. "AMZ", "SUN" |

### MATCH

| Field        | Type   | Notes                        |
| ------------ | ------ | ---------------------------- |
| id           | int    | PK                           |
| season_id    | int    | FK → SEASON                  |
| venue_id     | int    | FK → VENUE                   |
| home_team_id | int    | FK → TEAM                    |
| away_team_id | int    | FK → TEAM                    |
| match_date   | date   |                              |
| kickoff_time | time   |                              |
| matchday     | int    | round number                 |
| home_score   | int    |                              |
| away_score   | int    |                              |
| status       | string | scheduled / live / full-time |

### PLAYER

| Field       | Type   | Notes                |
| ----------- | ------ | -------------------- |
| id          | int    | PK                   |
| team_id     | int    | FK → TEAM            |
| name        | string |                      |
| position    | string | GK / DEF / MID / FWD |
| yellow_card | int    |                      |
| red_card    | int    |                      |

### PLAYER_MATCH_STAT

| Field          | Type | Notes            |
| -------------- | ---- | ---------------- |
| id             | int  | PK               |
| match_id       | int  | FK → MATCH       |
| player_id      | int  | FK → PLAYER      |
| team_id        | int  | FK - TEAM        |
| goals          | int  |                  |
| assists        | int  |                  |
| shots          | int  |                  |
| minutes_played | int  |                  |
| motm           | bool | man of the match |
| saves          | int  | GK only          |
| goals_conceded | int  | GK only          |
| clean_sheet    | bool | GK only          |

### STANDING_SNAPSHOT

| Field           | Type | Notes                               |
| --------------- | ---- | ----------------------------------- |
| id              | int  | PK                                  |
| season_id       | int  | FK → SEASON                         |
| team_id         | int  | FK → TEAM                           |
| matchday        | int  | round this snapshot was taken after |
| position        | int  | league position                     |
| points          | int  |                                     |
| played          | int  |                                     |
| wins            | int  |                                     |
| draws           | int  |                                     |
| losses          | int  |                                     |
| goal_difference | int  |                                     |
| recorded_date   | date | write once per completed matchday   |

## Relationships

- SEASON ||--o{ MATCH — contains
- VENUE ||--o{ MATCH — hosts
- TEAM ||--o{ MATCH — plays home (via home_team_id)
- TEAM ||--o{ MATCH — plays away (via away_team_id)
- TEAM ||--o{ PLAYER — squads
- MATCH ||--o{ PLAYER_MATCH_STAT — records
- PLAYER ||--o{ PLAYER_MATCH_STAT — produces
- SEASON ||--o{ STANDING_SNAPSHOT — tracks
- TEAM ||--o{ STANDING_SNAPSHOT — ranked_in

## Query → entity mapping

| #   | Graphic                               | Source table(s)          | Approach                                                                                 |
| --- | ------------------------------------- | ------------------------ | ---------------------------------------------------------------------------------------- |
| 1   | This week's fixtures                  | MATCH + TEAM + VENUE     | Filter MATCH by date range                                                               |
| 2   | Team last 5 games (form, goals)       | MATCH                    | Filter by home_team_id or away_team_id = team, order by match_date desc, limit 5         |
| 3   | Home vs away form                     | MATCH                    | Split by whether team was home_team_id or away_team_id                                   |
| 4   | Best defence (conceded, clean sheets) | MATCH, PLAYER_MATCH_STAT | Aggregate goals_against from MATCH; clean_sheet counts from PLAYER_MATCH_STAT (GK)       |
| 5   | Player(s) on form                     | PLAYER_MATCH_STAT        | Aggregate goals/assists/shots/motm over recent matches                                   |
| 6   | Top scorers/assisters                 | PLAYER_MATCH_STAT        | Sum goals/assists across season                                                          |
| 7   | Goalkeeper form                       | PLAYER_MATCH_STAT        | Filter position = GK; clean_sheet, goals_conceded, saves, minutes_played                 |
| 8   | Best home records                     | MATCH                    | Filter home_team_id = team, aggregate wins/points                                        |
| 9   | Table movement                        | STANDING_SNAPSHOT        | Compare position across matchdays for a team                                             |
| 10  | H2H last 5                            | MATCH                    | Filter where team pair appears as home/away in either order, order by date desc, limit 5 |

**Note:** STANDING_SNAPSHOT must be written once per completed matchday (not recalculated live) — it's the only entity that lets you answer "movement" questions later, since a single current-state table can't show history.
