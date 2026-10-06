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

// ---------- grouping seasons ----------

// save % isn't stored, so work it out per row
function withDerivedStats(row) {
    const save_pct = row.saves != null && row.shots_on_target_against
        ? Math.round((row.saves / row.shots_on_target_against) * 1000) / 10
        : null;
    return { ...row, save_pct };
}

// The API returns one row per season PER CLUB. This groups them by season
// without adding anything up, so a mid-season move keeps its two club rows:
// [{ season_id, season_name, start_year, rows: [arsenalRow, chelseaRow] }, ...]
export function groupSeasons(stats = []) {
    const bySeason = new Map();
    [...stats]
        .sort((a, b) => a.start_year - b.start_year || a.stat_id - b.stat_id)
        .forEach(row => {
            if (!bySeason.has(row.season_id)) {
                bySeason.set(row.season_id, {
                    season_id: row.season_id,
                    season_name: row.season_name,
                    start_year: row.start_year,
                    rows: [],
                });
            }
            bySeason.get(row.season_id).rows.push(withDerivedStats(row));
        });
    return [...bySeason.values()];
}

// 140000000 -> "€140M", 350000 -> "€350K"
export function formatEuro(value) {
    if (value === null || value === undefined) return '–';
    return new Intl.NumberFormat('en-GB', {
        style: 'currency',
        currency: 'EUR',
        notation: 'compact',
        minimumFractionDigits: 0,
        maximumFractionDigits: 1,
    }).format(value);
}
