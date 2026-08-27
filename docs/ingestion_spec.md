# Kasi Pitchside — ETL / Ingestion Spec

## Sources

- LiveScore
- FlashScore
- Google search engine (fallback / discovery, e.g. for news-triggered lookups or when a primary source is blocked)
- PSL official website

Each source gets its own fetcher module so a block/change on one source doesn't take down the pipeline.

## 1. Fetch layer (per-source clients)

```
fetchers/
  livescore_client.py
  flashscore_client.py
  google_search_client.py
  psl_website_client.py
```

- Each client exposes narrow functions: `get_fixtures(date_range)`, `get_match_stats(match_id)`, `get_standings(season_id)` — returns **raw JSON/HTML**, does no transforming.
- Every response is cached to disk before anything touches the DB: `raw/{source}/{endpoint}_{timestamp}.json`. This is the safety net — if a transform bug corrupts data, replay from raw instead of re-hitting the site.
- Rate limiting: sleep/backoff wrapper per client (undocumented endpoints — getting throttled or IP-blocked kills the whole pipeline). Go conservative, e.g. 1 request per 2-3 seconds.
- Retry logic: 3 attempts with exponential backoff on network failure, then log-and-skip (don't crash the whole run over one bad request).
- Source priority/fallback order: if LiveScore or FlashScore is blocked/down for an endpoint, fall back to PSL website, then Google search as last resort for discovery-style lookups (e.g. finding a news item or confirming a postponed fixture).

## 2. Transform layer (raw → schema)

```
transformers/
  transform_match.py       # raw fixture data -> MATCH dict
  transform_player_stat.py # raw match stats -> PLAYER_MATCH_STAT dicts
  transform_standing.py    # raw table data -> STANDING_SNAPSHOT dict
```

- Input: raw JSON/HTML dict. Output: dict matching ERD column names exactly. No DB calls here — keeps it unit-testable without a live DB.
- Resolves foreign keys here — e.g. matching "Kaizer Chiefs" (site's spelling) to internal `team_id` via a name-lookup table, since sources format team/player names differently.

### Entity resolution — `aliases.json` / lookup table

Never auto-create a new TEAM or PLAYER row from an unrecognized raw-feed name — that's how you end up with "Kaizer Cheifs" as a phantom duplicate team three months in.

```
lookups/
  team_aliases.json    # {"Kaizer Cheifs": 12, "AmaZulu FC": 4, ...}
  player_aliases.json  # {"T. Zwane": 88, "Zwane, T": 88, ...}
```

- On lookup miss: **do not insert**. Log an `UNMAPPED_ENTITY_WARNING` (raw name, source, timestamp, raw match/player ID) and skip that record's load.
- A separate manual-review step (a small script or just eyeballing the warning log) resolves unmapped entities into the alias file — either mapping to an existing ID or deliberately creating a new TEAM/PLAYER row for a genuinely new entity (e.g. a promoted club, a new signing).
- This keeps the alias file as the single source of truth for name variants across all four sources, rather than each source silently drifting the canonical name.

## 3. Load layer (upsert logic)

- **MATCH**: upsert on natural key (`season_id + home_team_id + away_team_id + matchday`) — fixtures get updated (score, status) as the match progresses, not re-inserted.
- **PLAYER_MATCH_STAT**: upsert on (`match_id + player_id`) — stats can be corrected post-match, so overwrite, don't duplicate.
- **STANDING_SNAPSHOT**: **insert-only, never update** — each snapshot is a historical record. This is the one table where duplicates-over-time are wanted, since overwriting defeats the "table movement" purpose.
- **TEAM / PLAYER / VENUE**: insert-if-not-exists (get-or-create pattern) — these rarely change.

## 4. Orchestration (scheduling)

| Job                               | Frequency                                                    | Why                                                                                                                                             |
| --------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Fixtures (upcoming)               | Daily                                                        | Kickoff times/venues can shift                                                                                                                  |
| Live scores                       | Every 2-5 min, matchdays only                                | Only run during actual match windows                                                                                                            |
| Post-match stats (initial)        | Once, ~2hrs after final whistle                              | Let the source's data settle                                                                                                                    |
| Post-match stats (reconciliation) | Once, T+24hrs after final whistle                            | Catches official stat corrections (e.g. a goal reassigned to a different scorer, an own-goal reclassified) before weekly graphics render off it |
| Standings snapshot                | Once per matchday, after matchday is "completed" (see below) | Triggers the STANDING_SNAPSHOT insert                                                                                                           |

A single `run_pipeline.py --job=fixtures` triggered via cron (or Task Scheduler) is enough at this scale — no need for Airflow/Prefect yet.

### Definition: "completed matchday"

A matchday is treated as completed — and eligible for its STANDING_SNAPSHOT — when **either**:

1. All fixtures for that matchday are `status = full-time`, **or**
2. The current date has passed the final scheduled kickoff window for that matchday.

Condition 2 exists so a single postponed fixture doesn't permanently block snapshot generation for the rest of the league. A postponed match's stats simply arrive later and update via the normal upsert path (MATCH is upsertable) — the snapshot isn't blocked waiting on it.

## 5. Data quality guardrail

Before load, run a lightweight check:

- Does `home_score`/`away_score` exist for a match marked "full-time"?
- Does the player's `team_id` match a real team for that match date?
- Are duplicate STANDING_SNAPSHOT rows for the same team/matchday being prevented (should only ever insert once per matchday)?

Log and skip bad records rather than letting them corrupt a graphic.
