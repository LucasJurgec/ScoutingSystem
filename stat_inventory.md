# Stat inventory

League: **ENG-Premier League** &nbsp;&nbsp; Season: **2324**

Generated: 2026-09-14 23:52

---

## FBref — player season stats

### stat_type = `standard`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `shooting`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `passing`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']`

### stat_type = `passing_types`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']`

### stat_type = `goal_shot_creation`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']`

### stat_type = `defense`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']`

### stat_type = `possession`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']`

### stat_type = `playing_time`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `misc`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `keeper`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `keeper_adv`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['standard', 'keeper', 'shooting', 'playing_time', 'misc']`

---

## FBref — player match stats

_Per-match rows. Aggregate these yourself if you want season totals not covered above._

### schedule

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `summary`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `keepers`

**Failed:** `ValueError: not enough values to unpack (expected 1, got 0)`

### stat_type = `passing`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['summary', 'keepers']`

### stat_type = `passing_types`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['summary', 'keepers']`

### stat_type = `defense`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['summary', 'keepers']`

### stat_type = `possession`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['summary', 'keepers']`

### stat_type = `misc`

**Failed:** `TypeError: Invalid argument: stat_type should be in ['summary', 'keepers']`

---

## Understat

### read_player_season_stats()

Rows: 570 &nbsp;&nbsp; Columns: 19

Index levels: `league, season, team, player`

| Column | Type | Filled | Example |
|---|---|---|---|
| `league_id` | string | 100% | 1 |
| `season_id` | Int64 | 100% | 2023 |
| `team_id` | Int64 | 100% | 83 |
| `player_id` | Int64 | 100% | 5603 |
| `position` | string | 100% | GK |
| `matches` | Int64 | 100% | 6 |
| `minutes` | Int64 | 100% | 540 |
| `goals` | Int64 | 100% | 0 |
| `xg` | Float64 | 100% | 0.0 |
| `np_goals` | Int64 | 100% | 0 |
| `np_xg` | Float64 | 100% | 0.0 |
| `assists` | Int64 | 100% | 0 |
| `xa` | Float64 | 100% | 0.0 |
| `shots` | Int64 | 100% | 0 |
| `key_passes` | Int64 | 100% | 0 |
| `yellow_cards` | Int64 | 100% | 0 |
| `red_cards` | Int64 | 100% | 0 |
| `xg_chain` | Float64 | 100% | 0.7832736372947693 |
| `xg_buildup` | Float64 | 100% | 0.7832736372947693 |

### read_team_match_stats()

_Team level, not player — included for completeness._

Rows: 380 &nbsp;&nbsp; Columns: 26

Index levels: `league, season, game`

| Column | Type | Filled | Example |
|---|---|---|---|
| `league_id` | string | 100% | 1 |
| `season_id` | Int64 | 100% | 2023 |
| `game_id` | Int64 | 100% | 22275 |
| `date` | datetime64[us] | 100% | 2023-08-11 19:00:00 |
| `home_team_id` | Int64 | 100% | 92 |
| `away_team_id` | Int64 | 100% | 88 |
| `home_team` | string | 100% | Burnley |
| `away_team` | string | 100% | Manchester City |
| `away_team_code` | string | 100% | MCI |
| `home_team_code` | string | 100% | BUR |
| `away_points` | Int64 | 100% | 3 |
| `away_expected_points` | Float64 | 100% | 2.7761 |
| `away_goals` | Int64 | 100% | 3 |
| `away_xg` | Float64 | 100% | 2.40074 |
| `away_np_xg` | Float64 | 100% | 2.40074 |
| `away_np_xg_difference` | Float64 | 100% | 2.089708 |
| `away_ppda` | Float64 | 100% | 15.8 |
| `away_deep_completions` | Int64 | 100% | 9 |
| `home_points` | Int64 | 100% | 0 |
| `home_expected_points` | Float64 | 100% | 0.1385 |
| `home_goals` | Int64 | 100% | 0 |
| `home_xg` | Float64 | 100% | 0.311032 |
| `home_np_xg` | Float64 | 100% | 0.311032 |
| `home_np_xg_difference` | Float64 | 100% | -2.089708 |
| `home_ppda` | Float64 | 100% | 33.07142857142857 |
| `home_deep_completions` | Int64 | 100% | 4 |
