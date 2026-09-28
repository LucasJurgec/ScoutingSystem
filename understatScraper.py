# This script is being used to get soccer data from understats API
# The stats it gets are: xG, xA, shots and key passes for the top 5 leagues
# It will get data from 2017-18 to 2025-26 seasons
# The data will be saved to a CSV file so that it can be combined with other data sources later on

import pandas as pd
import soccerdata as sd
 
# Top 5 leagues
LEAGUES = [
    "ENG-Premier League",
    "ESP-La Liga",
    "ITA-Serie A",
    "GER-Bundesliga",
    "FRA-Ligue 1",
]
 
# Seasons as "YYZZ"
SEASONS = ["2627", "2526", "2425", "2324", "2223", "2122", "2021", "1920", "1819", "1718"]
OUTPUT_FILE = "understat_player_stats.csv"
STAT_COLS = ["minutes", "xg", "xa", "shots", "key_passes"]
 
 
def find_movers(understat):
    """Players whose Understat season row lists more than one club."""
    movers = []
    for (league, season), row in understat.read_seasons().iterrows():
        # Uses the cached league data downloaded by read_player_season_stats
        data = understat._read_league_season(
            row["url"], row["league_id"], row["season_id"], no_cache=False
        )
        title_to_id = {t["title"]: int(t["id"]) for t in data["teamsData"].values()}
        for p in data["playersData"]:
            if "," in p["team_title"]:
                clubs = [c.strip() for c in p["team_title"].split(",")]
                movers.append({
                    "league": league,
                    "season": season,
                    "player_id": int(p["id"]),
                    "team_ids": [title_to_id[c] for c in clubs if c in title_to_id],
                })
    return movers
 
 
def split_movers(understat, movers):
    """Rebuild per-club season totals for movers from match-level stats."""
    schedule = understat.read_schedule(include_matches_without_data=False).reset_index()
 
    game_ids = set()
    for m in movers:
        s = schedule[(schedule["league"] == m["league"]) & (schedule["season"] == m["season"])]
        mask = s["home_team_id"].isin(m["team_ids"]) | s["away_team_id"].isin(m["team_ids"])
        game_ids.update(s.loc[mask, "game_id"].astype(int).tolist())
 
    print(f"Fetching {len(game_ids)} matches to split {len(movers)} mid-season movers "
          f"(slow the first time, cached after)...")
    match_stats = understat.read_player_match_stats(match_id=sorted(game_ids)).reset_index()
 
    mover_keys = {(m["league"], m["season"], m["player_id"]) for m in movers}
    keep = match_stats.apply(
        lambda r: (r["league"], r["season"], int(r["player_id"])) in mover_keys, axis=1
    )
    return (
        match_stats[keep]
        .groupby(["league", "season", "team", "player", "player_id"], as_index=False)[STAT_COLS]
        .sum()
    )
 
 
def main():
    understat = sd.Understat(leagues=LEAGUES, seasons=SEASONS)
 
    stats = understat.read_player_season_stats().reset_index()
    stats = stats[["season", "league", "team", "player", "player_id"] + STAT_COLS]
    stats["split_from_matches"] = False
 
    movers = find_movers(understat)
    if movers:
        split = split_movers(understat, movers)
        split["split_from_matches"] = True
 
        # Sanity check: per-club rows should add back up to the season totals
        mover_ids = {(m["league"], m["season"], m["player_id"]) for m in movers}
        is_mover = stats.apply(
            lambda r: (r["league"], r["season"], int(r["player_id"])) in mover_ids, axis=1
        )
        totals = stats[is_mover].set_index(["league", "season", "player_id"])["xg"].astype(float)
        rebuilt = split.groupby(["league", "season", "player_id"])["xg"].sum().astype(float)
        diff = (totals - rebuilt).abs()
        bad = diff[diff > 0.05]
        if len(bad):
            print(f"Warning: {len(bad)} movers' split xG doesn't match their season total:")
            print(bad)
 
        stats = pd.concat([stats[~is_mover], split], ignore_index=True)
 
    stats["xg"] = stats["xg"].astype(float).round(2)
    stats["xa"] = stats["xa"].astype(float).round(2)
    stats = stats.sort_values(["season", "league", "team", "player"])
    stats.to_csv(OUTPUT_FILE, index=False, encoding="utf-8")
 
    print(f"Saved {len(stats)} rows to {OUTPUT_FILE} "
          f"({int(stats['split_from_matches'].sum())} rebuilt from match data)")
 
 
if __name__ == "__main__":
    main()

# once the dataset was created it was moved to a seperate folder outside 
# this repo so it can be combined with the other datasets using KNIME