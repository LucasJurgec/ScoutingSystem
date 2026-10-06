// Shared stat definitions and helpers, used by Stats and StatCompare.

export const STAT_LABELS = {
    appearances: 'Appearances',
    minutes_played: 'Minutes Played',
    points_per_match: 'Points per Match',
    plus_minus: 'Plus/Minus',
    goals: 'Goals',
    assists: 'Assists',
    xg: 'xG',
    xa: 'xA',
    shots_total: 'Total Shots',
    shots_on_target: 'Shots on Target',
    key_passes: 'Key Passes',
    crosses: 'Crosses',
    penalty_scored: 'Penalties Scored',
    penalty_attempts: 'Penalties Taken',
    tackles_won: 'Tackles Won',
    interceptions: 'Interceptions',
    saves: 'Saves',
    save_pct: 'Save %',
    shots_on_target_against: 'Shots on Target Faced',
    goals_conceded: 'Goals Conceded',
    clean_sheets: 'Clean Sheets',
    penalties_faced: 'Penalties Faced',
    penalty_saved: 'Penalties Saved',
    penalty_conceded: 'Penalties Conceded',
    penalty_missed: 'Opp. Penalties Missed',
    yellow_cards: 'Yellow Cards',
    red_cards: 'Red Cards',
    fouls_committed: 'Fouls Committed',
    fouls_drawn: 'Fouls Drawn',
    offsides: 'Offsides',
    own_goals: 'Own Goals',
};

export const STAT_SECTIONS = {
    general:     { title: 'General',     keys: ['appearances', 'minutes_played', 'points_per_match', 'plus_minus'] },
    attacking:   { title: 'Attacking',   keys: ['goals', 'assists', 'xg', 'xa', 'shots_total', 'shots_on_target', 'key_passes', 'crosses', 'penalty_scored', 'penalty_attempts'] },
    defending:   { title: 'Defending',   keys: ['tackles_won', 'interceptions'] },
    goalkeeping: { title: 'Goalkeeping', keys: ['saves', 'save_pct', 'shots_on_target_against', 'goals_conceded', 'clean_sheets', 'penalties_faced', 'penalty_saved', 'penalty_conceded', 'penalty_missed'] },
    discipline:  { title: 'Discipline',  keys: ['yellow_cards', 'red_cards', 'fouls_committed', 'fouls_drawn', 'offsides', 'own_goals'] },
};

const DECIMAL_STATS = ['xg', 'xa', 'points_per_match'];

// Nulls show as a dash, since coverage differs between seasons/sources
export function formatStat(key, value) {
    if (value === null || value === undefined) return '–';
    if (key === 'save_pct') return `${Number(value).toFixed(1)}%`;
    if (key === 'plus_minus') return value > 0 ? `+${value}` : `${value}`;
    if (DECIMAL_STATS.includes(key)) return Number(value).toFixed(2);
    return value;
}

// Primary position = player.position_advanced. Falls back to a sensible
// default from position_general if the specific one is missing.
const GENERAL_TO_SPECIFIC = { Goalkeeper: 'GK', Defender: 'CB', Midfielder: 'CM', Attacker: 'ST' };

export function primaryPosition(player) {
    return player.position_advanced || GENERAL_TO_SPECIFIC[player.position_general] || null;
}

// ---------- merging seasons ----------

// Everything except points_per_match gets summed when a season is split across clubs
const SUM_KEYS = [
    'appearances', 'minutes_played', 'goals', 'assists', 'penalty_scored', 'penalty_attempts',
    'yellow_cards', 'red_cards', 'own_goals', 'shots_total', 'shots_on_target', 'crosses',
    'fouls_committed', 'fouls_drawn', 'offsides', 'tackles_won', 'interceptions', 'plus_minus',
    'xg', 'xa', 'key_passes',
    'goals_conceded', 'shots_on_target_against', 'saves', 'clean_sheets', 'penalties_faced',
    'penalty_conceded', 'penalty_saved', 'penalty_missed',
];

// Sum ignoring nulls; if every row is null the result stays null (not 0)
function sumOf(rows, key) {
    const values = rows.map(r => r[key]).filter(v => v !== null && v !== undefined);
    if (values.length === 0) return null;
    return Math.round(values.reduce((total, v) => total + Number(v), 0) * 100) / 100;
}

function weightedPointsPerMatch(rows) {
    let points = 0;
    let apps = 0;
    rows.forEach(r => {
        if (r.points_per_match != null && r.appearances) {
            points += Number(r.points_per_match) * r.appearances;
            apps += r.appearances;
        }
    });
    return apps ? Math.round((points / apps) * 100) / 100 : null;
}

// The API returns one row per season PER CLUB, so a mid-season move gives
// two rows for the same season. This merges them into one season total.
export function mergeSeasons(stats = []) {
    const bySeason = new Map();
    stats.forEach(row => {
        if (!bySeason.has(row.season_id)) bySeason.set(row.season_id, []);
        bySeason.get(row.season_id).push(row);
    });

    return [...bySeason.values()]
        .map(rows => {
            const merged = {
                season_id: rows[0].season_id,
                season_name: rows[0].season_name,
                start_year: rows[0].start_year,
                clubs: rows.map(r => r.club_name),
            };
            SUM_KEYS.forEach(key => { merged[key] = sumOf(rows, key); });

            merged.points_per_match = rows.length === 1
                ? (rows[0].points_per_match ?? null)
                : weightedPointsPerMatch(rows);

            merged.save_pct = merged.saves != null && merged.shots_on_target_against
                ? Math.round((merged.saves / merged.shots_on_target_against) * 1000) / 10
                : null;

            return merged;
        })
        .sort((a, b) => a.start_year - b.start_year);
}
